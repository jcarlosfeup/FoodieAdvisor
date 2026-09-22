"""Repeatable CSV seed import: python -m scripts.import_seed_data."""

import csv
from pathlib import Path

from sqlalchemy import create_engine, text

from config import settings


def _number(value: str, integer: bool = False):
    if not value.strip():
        return None
    return int(float(value)) if integer else float(value)


def import_seed_data() -> tuple[int, int]:
    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM restaurants WHERE source = 'csv'"))
        cities: dict[tuple, int] = {}
        with settings.cities_csv_path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                key = (row["city"], row["country"], row["iso"], row["latitude"], row["longitude"])
                if key in cities:
                    continue
                result = connection.execute(
                    text("""
                        INSERT INTO cities (name, country, iso, latitude, longitude, population)
                        VALUES (:name, :country, :iso, :latitude, :longitude, :population)
                        ON CONFLICT (name, country, iso, latitude, longitude) DO UPDATE
                        SET population = EXCLUDED.population
                        RETURNING id
                    """),
                    {"name": row["city"], "country": row["country"], "iso": row["iso"],
                     "latitude": _number(row["latitude"]), "longitude": _number(row["longitude"]),
                     "population": _number(row["population"], integer=True)},
                )
                cities[key] = result.scalar_one()

        restaurant_count = 0
        with settings.restaurants_csv_path.open(newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                city_id = connection.execute(
                    text("SELECT id FROM cities WHERE name = :name ORDER BY id LIMIT 1"),
                    {"name": row["city"]},
                ).scalar_one()
                connection.execute(
                    text("""
                        INSERT INTO restaurants
                            (city_id, name, rating, ratings_count, price_level, latitude, longitude, source)
                        VALUES (:city_id, :name, :rating, :ratings_count, :price_level, :latitude, :longitude, 'csv')
                    """),
                    {"city_id": city_id, "name": row["name"], "rating": _number(row["rating"]),
                     "ratings_count": _number(row["ratings_count"], integer=True) or 0,
                     "price_level": row["price_level"], "latitude": _number(row["latitude"]),
                     "longitude": _number(row["longitude"])},
                )
                restaurant_count += 1
    return len(cities), restaurant_count


if __name__ == "__main__":
    print(import_seed_data())