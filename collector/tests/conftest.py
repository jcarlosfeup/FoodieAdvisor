import os
from pathlib import Path

import pytest
from sqlalchemy import text

from foodie_common.testing import temporary_database

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def pg_engine_session():
    admin_url = os.getenv("TEST_DATABASE_URL")
    if not admin_url:
        pytest.skip("set TEST_DATABASE_URL to run PostGIS integration tests")
    with temporary_database(admin_url, REPO_ROOT / "db" / "init") as engine:
        yield engine


@pytest.fixture
def pg_engine(pg_engine_session):
    yield pg_engine_session
    with pg_engine_session.begin() as connection:
        connection.execute(
            text("""
                TRUNCATE raw.osm_restaurants, raw.geonames_cities, raw.geonames_countries,
                         raw.rejected_records, raw.ingestion_runs
            """)
        )
