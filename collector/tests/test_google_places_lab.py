import pytest

from foodie_collector.settings import GooglePlacesLabSettings
from foodie_collector.sources.google_places_lab import GooglePlacesClient, lab_search, transform_places


class FakeCredentials:
    valid = True
    token = "fake-token"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, pages):
        self.pages = list(pages)
        self.requests = []

    def post(self, url, headers, json, timeout):
        self.requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(self.pages.pop(0))


class FakeClient:
    def __init__(self, places):
        self.places = places
        self.queries = []

    def search_restaurants(self, search_text):
        self.queries.append(search_text)
        return self.places


def lab_settings(**overrides):
    return GooglePlacesLabSettings(_env_file=None, google_pagination_delay_seconds=0, **overrides)


def test_transform_places_flattens_google_response_and_keeps_place_id():
    result = transform_places(
        [
            {
                "id": "places/abc",
                "displayName": {"text": "Cafe"},
                "rating": 4.6,
                "userRatingCount": 12,
                "priceLevel": "PRICE_LEVEL_MODERATE",
                "location": {"latitude": 41.1, "longitude": -8.6},
            }
        ],
        "Porto",
    )
    assert result == [
        {
            "google_place_id": "places/abc",
            "name": "Cafe",
            "city": "Porto",
            "rating": 4.6,
            "ratings_count": 12,
            "price_level": "PRICE_LEVEL_MODERATE",
            "latitude": 41.1,
            "longitude": -8.6,
        }
    ]


def test_transform_places_skips_places_without_names():
    assert transform_places([{"id": "places/missing-name"}], "Porto") == []


def test_transform_places_tolerates_missing_location_and_counts():
    [result] = transform_places([{"id": "places/x", "displayName": {"text": "Tasca"}}], "Porto")
    assert result["latitude"] is None
    assert result["ratings_count"] == 0


def test_client_follows_pagination_and_sends_configured_field_mask():
    session = FakeSession(
        [
            {"places": [{"id": "a"}], "nextPageToken": "page-2"},
            {"places": [{"id": "b"}]},
        ]
    )
    client = GooglePlacesClient(lab_settings(google_field_mask="places.id"), session, FakeCredentials())

    assert client.search_restaurants("restaurants in Porto") == [{"id": "a"}, {"id": "b"}]
    assert [r["json"]["pageToken"] for r in session.requests] == ["", "page-2"]
    assert session.requests[0]["headers"]["X-Goog-FieldMask"] == "places.id"
    assert session.requests[0]["headers"]["Authorization"] == "Bearer fake-token"
    assert session.requests[0]["timeout"] == 30


def test_client_requires_credentials_file_when_no_credentials_injected():
    with pytest.raises(ValueError, match="GOOGLE_APPLICATION_CREDENTIALS"):
        GooglePlacesClient(lab_settings(google_application_credentials=None))


def test_lab_search_builds_query_and_returns_transformed_rows_without_persisting():
    client = FakeClient([{"id": "places/1", "displayName": {"text": "Adega"}}])

    rows = lab_search(client, "Porto", "Portugal")

    assert client.queries == ["Portugal traditional restaurants in Porto, Portugal"]
    assert [row["name"] for row in rows] == ["Adega"]
