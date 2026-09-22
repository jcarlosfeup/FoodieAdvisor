import pytest


def test_database_url_is_required(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:password@localhost:5432/foodie_advisor",
    )
    from config import Settings

    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        Settings.from_env()


def test_settings_accepts_postgresql_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:password@localhost:5432/foodie_advisor",
    )
    from config import Settings

    settings = Settings.from_env()
    assert settings.database_url.startswith("postgresql+psycopg://")