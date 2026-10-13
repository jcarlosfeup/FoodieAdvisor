"""Google Places (New) lab integration.

Isolated experimentation module. Google's terms restrict persistent copies of
Places content, so nothing in this module writes to the database, and its output
must never be loaded into the raw, core, or mart schemas.
"""

import logging
import time
from typing import Any

import requests
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from foodie_collector.settings import GooglePlacesLabSettings

logger = logging.getLogger(__name__)


class GooglePlacesClient:
    def __init__(
        self,
        config: GooglePlacesLabSettings,
        session: requests.Session | None = None,
        credentials: Credentials | None = None,
    ):
        self.config = config
        self.session = session or requests.Session()
        if credentials is None:
            if config.google_application_credentials is None:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is required for the Google Places lab")
            credentials = service_account.Credentials.from_service_account_file(
                str(config.google_application_credentials),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        self.credentials = credentials

    def _access_token(self) -> str:
        if not self.credentials.valid or not self.credentials.token:
            self.credentials.refresh(Request())
        if not self.credentials.token:
            raise RuntimeError("Google credentials did not produce an access token")
        return self.credentials.token

    def search_restaurants(self, search_text: str) -> list[dict[str, Any]]:
        token = self._access_token()
        page_token = ""
        places: list[dict[str, Any]] = []
        while True:
            response = self.session.post(
                self.config.google_places_base_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Goog-FieldMask": self.config.google_field_mask,
                },
                json={
                    "textQuery": search_text,
                    "includedType": "restaurant",
                    "minRating": self.config.google_min_rating,
                    "pageToken": page_token,
                },
                timeout=self.config.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            places.extend(payload.get("places", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                return places
            time.sleep(self.config.google_pagination_delay_seconds)


def transform_places(data: list[dict[str, Any]], city_name: str) -> list[dict[str, Any]]:
    """Flatten Google Places payloads, skipping records without a display name."""
    transformed: list[dict[str, Any]] = []
    for place in data:
        location = place.get("location") or {}
        display_name = place.get("displayName") or {}
        name = display_name.get("text")
        if not name:
            continue
        transformed.append(
            {
                "google_place_id": place.get("id"),
                "name": name,
                "city": city_name,
                "rating": place.get("rating"),
                "ratings_count": place.get("userRatingCount", 0),
                "price_level": place.get("priceLevel"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            }
        )
    return transformed


def lab_search(
    client: GooglePlacesClient, city_name: str, country_name: str | None = None
) -> list[dict[str, Any]]:
    """Search and transform restaurants for display or inspection only. Never persists."""
    location = city_name if not country_name else f"{city_name}, {country_name}"
    cuisine = f"{country_name} traditional" if country_name else "local"
    raw_places = client.search_restaurants(f"{cuisine} restaurants in {location}")
    return transform_places(raw_places, city_name)
