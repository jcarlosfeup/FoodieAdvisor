"""API configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from foodie_common.settings import DatabaseSettings


class ApiHttpSettings(BaseSettings):
    """HTTP-level settings, readable without DATABASE_URL (needed when the app object is created)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    # Browser origins allowed to call the API (the Vite dev server by default). JSON list in env.
    api_cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    api_default_limit: int = 100
    api_max_limit: int = 500
    # Largest map box accepted, in degrees per side, to keep queries bounded.
    api_max_bbox_span_degrees: float = 2.0


class ApiSettings(ApiHttpSettings, DatabaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
