"""Integration fixture: throwaway PostGIS DB -> raw rows -> real dbt models -> API.

Needs TEST_DATABASE_URL (see foodie_common.testing); skipped otherwise.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from foodie_common.testing import temporary_database

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_DIR = REPO_ROOT / "transformations" / "dbt"

PORTO, LISBON, PORTO_ALEGRE = 2735943, 2267057, 3452925
TRADITIONAL_RULE = {"cuisines": ["portuguese", "regional", "local"], "name_keywords": ["tasca"]}

RAW_SQL = """
INSERT INTO raw.ingestion_runs (run_id, source, target, status, parameters, started_at, finished_at)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'osm_overpass', 'Porto', 'succeeded', CAST(:porto_params AS JSONB),
   now() - interval '1 hour', now() - interval '59 minutes'),
  ('00000000-0000-0000-0000-000000000002', 'osm_overpass', 'Lisbon', 'succeeded',
   CAST(:lisbon_params AS JSONB),
   now() - interval '1 hour', now() - interval '59 minutes'),
  ('00000000-0000-0000-0000-000000000003', 'geonames_cities', 'cities5000', 'succeeded', '{}',
   now() - interval '2 hours', now() - interval '2 hours');

INSERT INTO raw.geonames_countries
  (iso_alpha2, name, _payload_hash, _run_id, _last_seen_run_id)
VALUES
  ('PT', 'Portugal', 'h', '00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003'),
  ('BR', 'Brazil', 'h', '00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003');

INSERT INTO raw.geonames_cities
  (geonameid, name, asciiname, alternatenames, latitude, longitude, feature_code, country_code, population,
   _payload_hash, _run_id, _last_seen_run_id)
VALUES
  (:porto, 'Porto', 'Porto', 'Oporto,Porto', 41.14961, -8.61099, 'PPLA', 'PT', 249633, 'h',
   '00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003'),
  (:lisbon, 'Lisbon', 'Lisbon', 'Lisboa,Lisbonne', 38.72509, -9.1498, 'PPLC', 'PT', 517802, 'h',
   '00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003'),
  (:porto_alegre, 'Porto Alegre', 'Porto Alegre', '', -30.03283, -51.23019, 'PPLA', 'BR', 1488252, 'h',
   '00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000003');

INSERT INTO raw.osm_restaurants
  (osm_type, osm_id, latitude, longitude, tags, _payload_hash, _run_id, _last_seen_run_id, _last_seen_at)
VALUES
  ('node', 1, 41.1450, -8.6110, '{"name": "Tasca A", "cuisine": "portuguese", "addr:street": "Rua A",
    "addr:housenumber": "1", "website": "tasca-a.pt", "opening_hours": "Mo-Sa 12:00-22:00"}',
   'h', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', now()),
  ('node', 2, 41.1460, -8.6120, '{"name": "Tasca B", "cuisine": "regional;seafood"}',
   'h', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', now()),
  ('way', 3, 41.1600, -8.6300, '{"name": "Adega C", "cuisine": "portuguese"}',
   'h', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', now()),
  ('node', 4, 41.1470, -8.6130, '{"cuisine": "portuguese"}',
   'h', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', now()),
  ('node', 5, 41.1480, -8.6140, '{"name": "Closed long ago", "cuisine": "portuguese"}',
   'h', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001',
   now() - interval '30 days'),
  ('node', 6, 38.7100, -9.1400, '{"name": "Taberna Lisboa", "cuisine": "portuguese"}',
   'h', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', now());
"""


def _run_params(geonameid: int, latitude: float, longitude: float) -> str:
    bbox = {
        "south": latitude - 0.05,
        "west": longitude - 0.07,
        "north": latitude + 0.05,
        "east": longitude + 0.07,
    }
    return json.dumps(
        {"geonameid": geonameid, "radius_km": 5, "bbox": bbox, "traditional_rule": TRADITIONAL_RULE}
    )


def _dbt(args: list[str], env: dict[str, str]) -> None:
    dbt = Path(sys.executable).parent / "dbt"
    command = [str(dbt), *args, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"dbt {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")


@pytest.fixture(scope="session")
def mart_database_url():
    admin_url = os.getenv("TEST_DATABASE_URL")
    if not admin_url:
        pytest.skip("set TEST_DATABASE_URL to run PostGIS integration tests")
    with temporary_database(admin_url, REPO_ROOT / "db" / "init") as engine:
        with engine.begin() as connection:
            params = {
                "porto": PORTO,
                "lisbon": LISBON,
                "porto_alegre": PORTO_ALEGRE,
                "porto_params": _run_params(PORTO, 41.14961, -8.61099),
                "lisbon_params": _run_params(LISBON, 38.72509, -9.1498),
            }
            # psycopg runs one parameterized statement per call.
            for statement in RAW_SQL.split(";\n"):
                if statement.strip():
                    connection.execute(text(statement), params)
        url = engine.url
        env = {
            **os.environ,
            "DBT_POSTGRES_HOST": url.host or "localhost",
            "POSTGRES_PORT": str(url.port or 5432),
            "POSTGRES_USER": url.username or "",
            "POSTGRES_PASSWORD": url.password or "",
            "POSTGRES_DB": url.database or "",
        }
        if not (DBT_DIR / "dbt_packages").exists():
            _dbt(["deps"], env)
        _dbt(["run", "--quiet"], env)
        yield url.render_as_string(hide_password=False)
