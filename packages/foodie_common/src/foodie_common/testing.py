"""Helpers for integration tests that need an isolated PostGIS database.

TEST_DATABASE_URL points at a maintenance database on a disposable server (e.g. the Compose db
with database `postgres`). Each test session creates a uniquely named database, applies db/init,
and drops it afterwards, so developer and shared data are never touched.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

from foodie_common.db import make_engine
from foodie_common.settings import DatabaseSettings


@contextmanager
def temporary_database(admin_url: str, init_dir: Path) -> Iterator[Engine]:
    url = make_url(DatabaseSettings(database_url=admin_url).database_url).set(drivername="postgresql+psycopg")
    name = f"foodie_test_{uuid4().hex[:12]}"
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = make_engine(
        DatabaseSettings(database_url=url.set(database=name).render_as_string(hide_password=False))
    )
    try:
        with engine.begin() as connection:
            for script in sorted(init_dir.glob("*.sql")):
                connection.exec_driver_sql(script.read_text())
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
