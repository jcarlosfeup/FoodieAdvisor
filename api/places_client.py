"""Google Places HTTP client. It does not persist or transform responses."""

import logging
import time
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from config import Settings

logger = logging.getLogger(__name__)


class GooglePlacesClient:
    def __init__(self, config: Settings, session: requests.Session | None = None):
        if config.google_credentials_file is None:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is required for Google Places collection")
        self.config = config
        self.session = session or requests.Session()
        self.credentials = service_account.Credentials.from_service_account_file(
            str(config.google_credentials_file),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

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
                self.config.google_base_url,
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