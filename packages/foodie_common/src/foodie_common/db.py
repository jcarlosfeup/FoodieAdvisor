"""SQLAlchemy engine factory. Use engine.begin() around related writes."""

from sqlalchemy import Engine, create_engine

from foodie_common.settings import DatabaseSettings


def make_engine(settings: DatabaseSettings | None = None, **kwargs) -> Engine:
    settings = settings or DatabaseSettings()
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return create_engine(url, pool_pre_ping=True, **kwargs)
