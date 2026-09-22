"""Persistence boundary for the PostgreSQL application database."""

from typing import Any
import polars as pl
from sqlalchemy import create_engine, text


class PostgreSQLRepository:
    """Repository for the PostgreSQL schema defined in migrations/001_initial.sql."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, pool_pre_ping=True)

    def city_exists(self, city_name: str) -> bool:
        with self.engine.connect() as connection:
            return connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM cities WHERE name = :name)"),
                {"name": city_name},
            ).scalar_one()

    def add_city(self, metadata: dict[str, Any]) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO cities (name, country, iso, latitude, longitude, population)
                    VALUES (:name, :country, :iso, :latitude, :longitude, :population)
                    ON CONFLICT (name, country, iso, latitude, longitude) DO NOTHING
                """),
                metadata,
            )

    def fetch_cities(self) -> pl.DataFrame:
        with self.engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT name, latitude, longitude, country, iso, population
                FROM cities
                ORDER BY name
            """)).mappings().all()
        return pl.DataFrame([dict(row) for row in rows])

    def fetch_restaurants(self, city_name: str) -> pl.DataFrame:
        with self.engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT r.id, r.google_place_id, r.name, c.name AS city,
                       r.rating, r.price_level, r.ratings_count,
                       r.latitude, r.longitude
                FROM restaurants r
                JOIN cities c ON c.id = r.city_id
                WHERE c.name = :city_name
                ORDER BY r.name
            """), {"city_name": city_name}).mappings().all()
        return pl.DataFrame([dict(row) for row in rows])

    def save_restaurants(self, restaurants: list[dict[str, Any]]) -> int:
        if not restaurants:
            return 0
        with self.engine.begin() as connection:
            for restaurant in restaurants:
                connection.execute(text("""
                    INSERT INTO restaurants
                        (google_place_id, city_id, name, rating, price_level,
                         ratings_count, latitude, longitude)
                    SELECT :google_place_id, c.id, :name, :rating, :price_level,
                           :ratings_count, :latitude, :longitude
                    FROM cities c
                    WHERE c.name = :city
                    ON CONFLICT (google_place_id) DO UPDATE SET
                        city_id = EXCLUDED.city_id,
                        name = EXCLUDED.name,
                        rating = EXCLUDED.rating,
                        price_level = EXCLUDED.price_level,
                        ratings_count = EXCLUDED.ratings_count,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude
                """), restaurant)
        return len(restaurants)


def create_repository(database_url: str) -> PostgreSQLRepository:
    if database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        return PostgreSQLRepository(database_url)
    raise ValueError("DATABASE_URL must use PostgreSQL (postgresql+psycopg://)")