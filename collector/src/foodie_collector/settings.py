"""Collector configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class GooglePlacesLabSettings(BaseSettings):
    """Settings for the Google Places lab. It never needs DATABASE_URL because it never persists."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_application_credentials: Path | None = None
    google_places_base_url: str = "https://places.googleapis.com/v1/places:searchText"
    google_field_mask: str = (
        "places.id,places.displayName,places.rating,places.userRatingCount,"
        "places.priceLevel,places.location,nextPageToken"
    )
    google_min_rating: float = 4.3
    google_pagination_delay_seconds: float = 2.0
    request_timeout_seconds: int = 30
