"""Integration tests against an isolated PostGIS database (see conftest.py)."""

import copy
import json
from pathlib import Path

import pytest
from sqlalchemy import text

from foodie_collector.ingestion.collect_cities import collect_cities, collect_countries
from foodie_collector.ingestion.collect_restaurants import collect_restaurants
from foodie_collector.ingestion.targets import CityLookupError, city_by_geonameid, city_by_name
from foodie_collector.models import CityTarget
from foodie_collector.traditional import UnsupportedCountryError

pytestmark = pytest.mark.integration

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "overpass_porto.json").read_text())
PORTO = CityTarget(2735943, "Porto", "PT", 41.14961, -8.61099)


class FakeOverpass:
    def __init__(self, elements=None, error=None):
        self.elements = elements if elements is not None else FIXTURE["elements"]
        self.error = error
        self.bboxes = []
        self.rules = []

    def fetch_restaurants(self, bbox, rule):
        self.bboxes.append(bbox)
        self.rules.append(rule)
        if self.error:
            raise self.error
        return copy.deepcopy(self.elements)


class FakeGeoNames:
    def countries(self, refresh=False):
        return [
            "#ISO\tcomment",
            "PT\tPRT\t620\tPO\tPortugal\tLisbon\t92391.0\t10281762\tEU\t.pt\tEUR\tEuro\t351\t\t\tpt-PT\t2264397\tES\t",
            "BR\tBRA\t076\tBR\tBrazil\tBrasilia\t8511965.0\t209469333\tSA\t.br\tBRL\tReal\t55\t\t\tpt-BR\t3469034\t\t",
        ]

    def cities(self, name, refresh=False):
        return [
            "2735943\tPorto\tPorto\tOporto\t41.14961\t-8.61099\tP\tPPLA\tPT\t\t17\t1312\t\t\t249633\t\t94\t"
            "Europe/Lisbon\t2024-05-14",
            "3452925\tPorto Alegre\tPorto Alegre\t\t-30.03283\t-51.23019\tP\tPPLA\tBR\t\t23\t\t\t\t"
            "1488252\t\t46\tAmerica/Sao_Paulo\t2023-01-01",
            "8010540\tSantiago\tSantiago\t\t41.0\t-8.0\tP\tPPL\tPT\t\t\t\t\t\t6000\t\t\tEurope/Lisbon\t2023-01-01",
            "8010541\tSantiago\tSantiago\t\t39.0\t-8.5\tP\tPPL\tPT\t\t\t\t\t\t5500\t\t\tEurope/Lisbon\t2023-01-01",
            "bad-row",
        ]


def scalar(engine, sql, **params):
    with engine.connect() as connection:
        return connection.execute(text(sql), params).scalar_one()


def test_restaurant_ingestion_is_idempotent(pg_engine):
    first = collect_restaurants(pg_engine, FakeOverpass(), PORTO, radius_km=5)
    second = collect_restaurants(pg_engine, FakeOverpass(), PORTO, radius_km=5)

    assert (first.received, first.inserted, first.updated, first.unchanged, first.rejected) == (6, 4, 0, 0, 2)
    assert (second.inserted, second.updated, second.unchanged, second.rejected) == (0, 0, 4, 2)
    assert scalar(pg_engine, "SELECT count(*) FROM raw.osm_restaurants") == 4
    assert (
        scalar(
            pg_engine,
            "SELECT count(*) FROM raw.osm_restaurants WHERE _last_seen_run_id = :r",
            r=second.run_id,
        )
        == 4
    )
    assert (
        scalar(pg_engine, "SELECT count(*) FROM raw.osm_restaurants WHERE _run_id = :r", r=first.run_id) == 4
    )


def test_changed_tags_update_the_row_and_payload_lineage(pg_engine):
    collect_restaurants(pg_engine, FakeOverpass(), PORTO, radius_km=5)
    elements = copy.deepcopy(FIXTURE["elements"])
    elements[0]["tags"]["name"] = "Tasca do Porto (renovated)"

    rerun = collect_restaurants(pg_engine, FakeOverpass(elements), PORTO, radius_km=5)

    assert (rerun.inserted, rerun.updated, rerun.unchanged) == (0, 1, 3)
    assert (
        scalar(
            pg_engine,
            "SELECT tags->>'name' FROM raw.osm_restaurants WHERE osm_type = 'node' AND osm_id = 101",
        )
        == "Tasca do Porto (renovated)"
    )
    assert scalar(pg_engine, "SELECT _run_id FROM raw.osm_restaurants WHERE osm_id = 101") == rerun.run_id


def test_run_is_recorded_with_counts_and_rejections(pg_engine):
    stats = collect_restaurants(pg_engine, FakeOverpass(), PORTO, radius_km=5)

    with pg_engine.connect() as connection:
        run = connection.execute(
            text("SELECT * FROM raw.ingestion_runs WHERE run_id = :r"), {"r": stats.run_id}
        ).one()
        reasons = connection.execute(
            text("SELECT source_record_id, reason FROM raw.rejected_records WHERE run_id = :r ORDER BY 1"),
            {"r": stats.run_id},
        ).all()
    assert run.status == "succeeded"
    assert run.source == "osm_overpass"
    assert run.finished_at >= run.started_at
    assert (run.received_count, run.inserted_count, run.rejected_count) == (6, 4, 2)
    assert run.parameters["geonameid"] == 2735943
    assert "portuguese" in run.parameters["traditional_rule"]["cuisines"]
    assert "tasca" in run.parameters["traditional_rule"]["name_keywords"]
    assert reasons == [("node/606", "invalid_coordinates"), ("way/505", "missing_coordinates")]


def test_collector_passes_the_city_country_rule_to_the_source(pg_engine):
    source = FakeOverpass()
    collect_restaurants(pg_engine, source, PORTO, radius_km=5)
    assert [rule.country_code for rule in source.rules] == ["PT"]


def test_unsupported_country_fails_before_recording_a_run(pg_engine):
    nowhere = CityTarget(1, "Nowhere", "ZZ", 0.0, 0.0)
    source = FakeOverpass()

    with pytest.raises(UnsupportedCountryError, match="ZZ"):
        collect_restaurants(pg_engine, source, nowhere, radius_km=5)

    assert source.bboxes == []
    assert scalar(pg_engine, "SELECT count(*) FROM raw.ingestion_runs") == 0


def test_failed_run_is_recorded_and_loads_nothing(pg_engine):
    with pytest.raises(TimeoutError):
        collect_restaurants(pg_engine, FakeOverpass(error=TimeoutError("overpass down")), PORTO, radius_km=5)

    with pg_engine.connect() as connection:
        run = connection.execute(text("SELECT status, error_message FROM raw.ingestion_runs")).one()
    assert run.status == "failed"
    assert "overpass down" in run.error_message
    assert scalar(pg_engine, "SELECT count(*) FROM raw.osm_restaurants") == 0


def test_geonames_load_is_idempotent_and_resolves_targets(pg_engine):
    countries = collect_countries(pg_engine, FakeGeoNames())
    first = collect_cities(pg_engine, FakeGeoNames(), "cities5000")
    second = collect_cities(pg_engine, FakeGeoNames(), "cities5000")

    assert countries.inserted == 2
    assert (first.inserted, first.rejected) == (4, 1)
    assert (second.inserted, second.updated, second.unchanged) == (0, 0, 4)

    with pg_engine.connect() as connection:
        assert city_by_name(connection, "porto", "pt").geonameid == 2735943
        assert city_by_geonameid(connection, 3452925).country_code == "BR"
        with pytest.raises(CityLookupError, match="ambiguous"):
            city_by_name(connection, "Santiago", "PT")
        with pytest.raises(CityLookupError, match="No GeoNames city"):
            city_by_name(connection, "Porto", "ES")
