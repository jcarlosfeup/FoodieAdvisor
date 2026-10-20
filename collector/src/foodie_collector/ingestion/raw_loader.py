"""Idempotent loading into raw tables.

Each record is hashed over its data columns. Existing hashes are read for the batch, then:
new keys are inserted, keys whose hash changed are updated, and unchanged keys only get their
_last_seen_* columns touched. Rerunning the same import therefore inserts and updates nothing.
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, TableClause, column, func, select, table, tuple_, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert

from foodie_collector.models import Rejection

BATCH_SIZE = 1000

Key = tuple[Any, ...]


@dataclass(frozen=True)
class RawTable:
    """Description of a raw landing table. Names are code constants, never user input."""

    name: str
    key: tuple[str, ...]
    columns: tuple[str, ...]
    json_columns: frozenset[str] = frozenset()

    @property
    def fields(self) -> tuple[str, ...]:
        return self.key + self.columns

    def sql_table(self) -> TableClause:
        data_columns = [
            column(name, JSONB) if name in self.json_columns else column(name) for name in self.fields
        ]
        metadata_columns = [
            column(name)
            for name in ("_payload_hash", "_run_id", "_loaded_at", "_last_seen_run_id", "_last_seen_at")
        ]
        return table(self.name, *data_columns, *metadata_columns, schema="raw")

    def key_of(self, record: dict[str, Any]) -> Key:
        return tuple(record[name] for name in self.key)


OSM_RESTAURANTS = RawTable(
    name="osm_restaurants",
    key=("osm_type", "osm_id"),
    columns=("latitude", "longitude", "tags"),
    json_columns=frozenset({"tags"}),
)

GEONAMES_CITIES = RawTable(
    name="geonames_cities",
    key=("geonameid",),
    columns=(
        "name",
        "asciiname",
        "alternatenames",
        "latitude",
        "longitude",
        "feature_class",
        "feature_code",
        "country_code",
        "cc2",
        "admin1_code",
        "admin2_code",
        "admin3_code",
        "admin4_code",
        "population",
        "elevation",
        "dem",
        "timezone",
        "modification_date",
    ),  # fmt: skip
)

GEONAMES_COUNTRIES = RawTable(
    name="geonames_countries",
    key=("iso_alpha2",),
    columns=(
        "iso_alpha3",
        "iso_numeric",
        "name",
        "capital",
        "area_sq_km",
        "population",
        "continent",
        "languages",
        "geonameid",
        "neighbours",
    ),  # fmt: skip
)


@dataclass(frozen=True)
class LoadCounts:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    def __add__(self, other: "LoadCounts") -> "LoadCounts":
        return LoadCounts(
            self.inserted + other.inserted, self.updated + other.updated, self.unchanged + other.unchanged
        )


def payload_hash(record: dict[str, Any], fields: Iterable[str]) -> str:
    canonical = json.dumps(
        {name: record[name] for name in fields},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def deduplicate(
    raw_table: RawTable, records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[Rejection]]:
    """Keep the first record per key; later duplicates become rejections (ON CONFLICT needs unique keys)."""
    seen: set[Key] = set()
    unique: list[dict[str, Any]] = []
    rejections: list[Rejection] = []
    for record in records:
        key = raw_table.key_of(record)
        if key in seen:
            rejections.append(Rejection("/".join(map(str, key)), "duplicate_in_batch", record))
            continue
        seen.add(key)
        unique.append(record)
    return unique, rejections


def classify(
    raw_table: RawTable, records: list[dict[str, Any]], existing_hashes: dict[Key, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Key]]:
    """Split hashed records into (new, changed, unchanged keys) against the stored hashes."""
    new, changed, unchanged = [], [], []
    for record in records:
        key = raw_table.key_of(record)
        stored = existing_hashes.get(key)
        if stored is None:
            new.append(record)
        elif stored != record["_payload_hash"]:
            changed.append(record)
        else:
            unchanged.append(key)
    return new, changed, unchanged


def _key_filter(sql_table: TableClause, raw_table: RawTable, keys: list[Key]):
    if len(raw_table.key) == 1:
        return sql_table.c[raw_table.key[0]].in_([key[0] for key in keys])
    return tuple_(*(sql_table.c[name] for name in raw_table.key)).in_(keys)


def _load_batch(
    connection: Connection, raw_table: RawTable, run_id: UUID, records: list[dict[str, Any]]
) -> LoadCounts:
    sql_table = raw_table.sql_table()
    hashed = [{**record, "_payload_hash": payload_hash(record, raw_table.fields)} for record in records]
    keys = [raw_table.key_of(record) for record in hashed]
    key_columns = [sql_table.c[name] for name in raw_table.key]
    existing = {
        tuple(row[:-1]): row[-1]
        for row in connection.execute(
            select(*key_columns, sql_table.c._payload_hash).where(_key_filter(sql_table, raw_table, keys))
        )
    }
    new, changed, unchanged = classify(raw_table, hashed, existing)

    to_write = [{**record, "_run_id": run_id, "_last_seen_run_id": run_id} for record in new + changed]
    if to_write:
        statement = pg_insert(sql_table)
        statement = statement.on_conflict_do_update(
            index_elements=list(raw_table.key),
            set_={
                **{name: statement.excluded[name] for name in raw_table.columns},
                "_payload_hash": statement.excluded._payload_hash,
                "_run_id": statement.excluded._run_id,
                "_loaded_at": func.now(),
                "_last_seen_run_id": statement.excluded._last_seen_run_id,
                "_last_seen_at": func.now(),
            },
        )
        connection.execute(statement, to_write)
    if unchanged:
        connection.execute(
            update(sql_table)
            .where(_key_filter(sql_table, raw_table, unchanged))
            .values(_last_seen_run_id=run_id, _last_seen_at=func.now())
        )
    return LoadCounts(inserted=len(new), updated=len(changed), unchanged=len(unchanged))


def load_records(
    connection: Connection, raw_table: RawTable, run_id: UUID, records: list[dict[str, Any]]
) -> LoadCounts:
    """Upsert deduplicated records in batches. Call inside engine.begin() for one transaction."""
    counts = LoadCounts()
    for start in range(0, len(records), BATCH_SIZE):
        counts += _load_batch(connection, raw_table, run_id, records[start : start + BATCH_SIZE])
    return counts
