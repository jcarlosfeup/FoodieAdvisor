"""Collector configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from foodie_common.settings import DatabaseSettings


class GooglePlacesLabSettings(BaseSettings):
    """Settings for the Google Places lab. It never needs DATABASE_URL because it never persists."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_application_credentials: Path | None = None
    google_places_base_url: str = "https://places.googleapis.com/v1/places:searchText"
    google_field_mask: str = (
        "places.id,places.displayName,places.rating,places.userRatingCount,"
        "places.priceLevel,places.location,nextPageToken"
    )
    google_min_rating: float = 4.2
    google_pagination_delay_seconds: float = 2.0
    request_timeout_seconds: int = 30


class CollectorSettings(DatabaseSettings):
    """Settings for the OpenStreetMap and GeoNames ingestion jobs."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("data")

    overpass_url: str = "https://overpass-api.de/api/interpreter"
    overpass_query_timeout_seconds: int = 90
    overpass_request_delay_seconds: float = 5.0
    default_radius_km: float = 5.0

    geonames_base_url: str = "https://download.geonames.org/export/dump"
    geonames_cities_file: str = "cities5000"

    http_user_agent: str = "FoodieAdvisor-collector/0.1"
    http_timeout_seconds: float = 60.0
    http_max_attempts: int = 4
    http_backoff_seconds: float = 2.0
