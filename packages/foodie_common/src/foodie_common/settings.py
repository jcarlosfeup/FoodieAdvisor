"""Typed configuration shared by every service that talks to PostgreSQL."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

POSTGRES_URL_PREFIXES = ("postgresql://", "postgresql+psycopg://")


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    @field_validator("database_url")
    @classmethod
    def _require_postgresql(cls, value: str) -> str:
        if not value.startswith(POSTGRES_URL_PREFIXES):
            raise ValueError("DATABASE_URL must use PostgreSQL (postgresql+psycopg://)")
        return value
