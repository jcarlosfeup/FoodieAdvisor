"""Small persistence boundary used by the collection service and tests."""

import sqlite3
from pathlib import Path
from typing import Any
import polars as pl
from sqlalchemy import create_engine, text


class SQLiteRestaurantRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def save(self, restaurants: list[dict[str, Any]]) -> int:
        if not restaurants:
            return 0
        with sqlite3.connect(self.database_path) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(restaurant)")}
            if "google_place_id" not in columns:
                connection.execute("ALTER TABLE restaurant ADD COLUMN google_place_id TEXT")
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_restaurant_google_place_id "
                    "ON restaurant(google_place_id)"
                )
            connection.executemany(
                """
                INSERT INTO restaurant
                    (google_place_id, name, city, rating, price_level, ratings_count, latitude, longitude)
                VALUES (:google_place_id, :name, :city, :rating, :price_level, :ratings_count, :latitude, :longitude)
                ON CONFLICT(google_place_id) DO UPDATE SET
                    name=excluded.name, city=excluded.city, rating=excluded.rating,
                    price_level=excluded.price_level, ratings_count=excluded.ratings_count,
                    latitude=excluded.latitude, longitude=excluded.longitude
                """,
                restaurants,
            )
            return len(restaurants)

    def city_exists(self, city_name: str) -> bool:
        with sqlite3.connect(self.database_path) as connection:
            return connection.execute(
                "SELECT EXISTS (SELECT 1 FROM city WHERE name = ?)", (city_name,)
            ).fetchone()[0] == 1

    def add_city(self, metadata: dict[str, Any]) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO city
                    (name, country, iso, latitude, longitude, population)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (metadata.get("name"), metadata.get("country"), metadata.get("iso"),
                 metadata.get("latitude"), metadata.get("longitude"), metadata.get("population")),
            )

    def fetch_cities(self) -> pl.DataFrame:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute("""
                SELECT name, latitude, longitude, country, iso, population
                FROM city
                WHERE id IN (SELECT MIN(id) FROM city GROUP BY name)
                ORDER BY name
            """).fetchall()
        return pl.DataFrame(rows, schema=["name", "latitude", "longitude", "country", "iso", "population"], orient="row")

    def fetch_restaurants(self, city_name: str) -> pl.DataFrame:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute("SELECT * FROM restaurant WHERE city = ?", (city_name,))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
        return pl.DataFrame(rows, schema=columns, orient="row")

    def save_restaurants(self, restaurants: list[dict[str, Any]]) -> int:
        return self.save(restaurants)


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


def create_repository(database_url: str) -> PostgreSQLRepository | SQLiteRestaurantRepository:
    if database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        return PostgreSQLRepository(database_url)
    if database_url.startswith("sqlite:///"):
        return SQLiteRestaurantRepository(database_url.removeprefix("sqlite:///"))
    raise ValueError(f"Unsupported DATABASE_URL scheme: {database_url.split(':', 1)[0]}")