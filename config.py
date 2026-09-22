"""Typed application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path


def _float_env(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _int_env(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    database_url: str
    google_credentials_file: Path | None
    google_base_url: str
    google_field_mask: str
    google_min_rating: float
    google_pagination_delay_seconds: float
    request_timeout_seconds: int
    cities_csv_path: Path
    restaurants_csv_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(os.getenv("APP_ROOT", Path(__file__).resolve().parent))
        credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is required. Configure a PostgreSQL URL, for example "
                "postgresql+psycopg://user:password@localhost:5432/foodie_advisor."
            )
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must use PostgreSQL (postgresql+psycopg://)")
        return cls(
            database_url=database_url,
            google_credentials_file=Path(credentials) if credentials else None,
            google_base_url=os.getenv(
                "GOOGLE_PLACES_BASE_URL", "https://places.googleapis.com/v1/places:searchText"
            ),
            google_field_mask=os.getenv(
                "GOOGLE_FIELD_MASK",
                "places.id,places.displayName,places.rating,places.userRatingCount,"
                "places.priceLevel,places.location,nextPageToken",
            ),
            google_min_rating=_float_env("GOOGLE_MIN_RATING", 4.3),
            google_pagination_delay_seconds=_float_env("GOOGLE_PAGINATION_DELAY_SECONDS", 2.0),
            request_timeout_seconds=_int_env("REQUEST_TIMEOUT_SECONDS", 30),
            cities_csv_path=Path(os.getenv("CITIES_CSV_PATH", root / "world_cities.csv")),
            restaurants_csv_path=Path(os.getenv("RESTAURANTS_CSV_PATH", root / "restaurants.csv")),
        )


settings = Settings.from_env()