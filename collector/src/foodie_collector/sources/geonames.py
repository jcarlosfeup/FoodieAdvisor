"""GeoNames city and country reference data (© GeoNames, CC BY 4.0).

Format reference: https://download.geonames.org/export/dump/readme.txt
"""

import csv
import io
import time
import zipfile
from collections.abc import Callable, Iterable, Iterator
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from foodie_collector.http import request_with_retries
from foodie_collector.models import ParseResult, Rejection

CITY_COLUMNS = (
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1_code", "admin2_code",
    "admin3_code", "admin4_code", "population", "elevation", "dem", "timezone", "modification_date",
)  # fmt: skip

# countryInfo.txt columns, in file order, mapped to raw.geonames_countries (None = not kept).
COUNTRY_COLUMNS = (
    "iso_alpha2", "iso_alpha3", "iso_numeric", None, "name", "capital", "area_sq_km", "population",
    "continent", None, None, None, None, None, None, "languages", "geonameid", "neighbours", None,
)  # fmt: skip


def _text(value: str) -> str | None:
    return value or None


def _int(value: str) -> int | None:
    return int(value) if value else None


def _float(value: str) -> float | None:
    return float(value) if value else None


def _rows(lines: Iterable[str]) -> Iterator[list[str]]:
    # GeoNames files are plain tab-separated with no quoting; names may contain quote characters.
    return csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)


def parse_cities(lines: Iterable[str]) -> ParseResult:
    result = ParseResult()
    for row in _rows(lines):
        if not row:
            continue
        record_id = row[0] if row else None
        if len(row) != len(CITY_COLUMNS):
            result.rejections.append(Rejection(record_id, "unexpected_column_count", {"row": row}))
            continue
        raw = dict(zip(CITY_COLUMNS, row, strict=True))
        try:
            record: dict[str, Any] = {
                "geonameid": int(raw["geonameid"]),
                "name": raw["name"],
                "asciiname": _text(raw["asciiname"]),
                "alternatenames": _text(raw["alternatenames"]),
                "latitude": float(raw["latitude"]),
                "longitude": float(raw["longitude"]),
                "feature_class": _text(raw["feature_class"]),
                "feature_code": _text(raw["feature_code"]),
                "country_code": _text(raw["country_code"]),
                "cc2": _text(raw["cc2"]),
                "admin1_code": _text(raw["admin1_code"]),
                "admin2_code": _text(raw["admin2_code"]),
                "admin3_code": _text(raw["admin3_code"]),
                "admin4_code": _text(raw["admin4_code"]),
                "population": _int(raw["population"]),
                "elevation": _int(raw["elevation"]),
                "dem": _int(raw["dem"]),
                "timezone": _text(raw["timezone"]),
                "modification_date": date.fromisoformat(raw["modification_date"])
                if raw["modification_date"]
                else None,
            }
        except ValueError as error:
            result.rejections.append(Rejection(record_id, f"invalid_value: {error}", raw))
            continue
        if not record["name"]:
            result.rejections.append(Rejection(record_id, "missing_name", raw))
        elif not (-90 <= record["latitude"] <= 90 and -180 <= record["longitude"] <= 180):
            result.rejections.append(Rejection(record_id, "invalid_coordinates", raw))
        else:
            result.records.append(record)
    return result


def parse_countries(lines: Iterable[str]) -> ParseResult:
    result = ParseResult()
    for row in _rows(line for line in lines if not line.startswith("#")):
        if not row:
            continue
        record_id = row[0]
        if len(row) != len(COUNTRY_COLUMNS):
            result.rejections.append(Rejection(record_id, "unexpected_column_count", {"row": row}))
            continue
        raw = {name: value for name, value in zip(COUNTRY_COLUMNS, row, strict=True) if name}
        try:
            record = {
                "iso_alpha2": raw["iso_alpha2"],
                "iso_alpha3": _text(raw["iso_alpha3"]),
                "iso_numeric": _text(raw["iso_numeric"]),
                "name": raw["name"],
                "capital": _text(raw["capital"]),
                "area_sq_km": _float(raw["area_sq_km"]),
                "population": _int(raw["population"]),
                "continent": _text(raw["continent"]),
                "languages": _text(raw["languages"]),
                "geonameid": _int(raw["geonameid"]),
                "neighbours": _text(raw["neighbours"]),
            }
        except ValueError as error:
            result.rejections.append(Rejection(record_id, f"invalid_value: {error}", raw))
            continue
        if len(record["iso_alpha2"]) != 2 or not record["name"]:
            result.rejections.append(Rejection(record_id, "invalid_country", raw))
        else:
            result.records.append(record)
    return result


def read_zipped_text(path: Path, member: str) -> list[str]:
    with zipfile.ZipFile(path) as archive, archive.open(member) as handle:
        return io.TextIOWrapper(handle, encoding="utf-8", newline="").read().splitlines()


class GeoNamesDownloader:
    """Downloads GeoNames dump files into a local cache directory."""

    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        cache_dir: Path,
        max_attempts: int,
        backoff_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep

    def fetch(self, filename: str, refresh: bool = False) -> Path:
        target = self.cache_dir / filename
        if target.exists() and not refresh:
            return target
        response = request_with_retries(
            self.client,
            "GET",
            f"{self.base_url}/{filename}",
            max_attempts=self.max_attempts,
            backoff_seconds=self.backoff_seconds,
            sleep=self.sleep,
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        partial.write_bytes(response.content)
        partial.replace(target)
        return target

    def cities(self, name: str, refresh: bool = False) -> list[str]:
        return read_zipped_text(self.fetch(f"{name}.zip", refresh), f"{name}.txt")

    def countries(self, refresh: bool = False) -> list[str]:
        return self.fetch("countryInfo.txt", refresh).read_text(encoding="utf-8").splitlines()
