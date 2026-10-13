import json
import logging

import pytest
from pydantic import ValidationError

from foodie_common.db import make_engine
from foodie_common.logging import JsonFormatter
from foodie_common.settings import DatabaseSettings

PG_URL = "postgresql+psycopg://user:password@localhost:5432/foodie"


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        DatabaseSettings(_env_file=None)


def test_database_url_must_be_postgresql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///restaurants.db")
    with pytest.raises(ValidationError, match="must use PostgreSQL"):
        DatabaseSettings(_env_file=None)


def test_settings_accepts_postgresql_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", PG_URL)
    assert DatabaseSettings(_env_file=None).database_url == PG_URL


def test_make_engine_uses_psycopg_driver_for_plain_postgresql_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/foodie")
    engine = make_engine(DatabaseSettings(_env_file=None))
    assert engine.url.drivername == "postgresql+psycopg"


def test_json_formatter_includes_extra_fields():
    record = logging.makeLogRecord({"msg": "run finished", "levelname": "INFO", "run_id": "abc"})
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "run finished"
    assert payload["run_id"] == "abc"
