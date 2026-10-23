"""API behaviour with a fake repository: validation, paging, errors. No database."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from foodie_api.main import create_app
from foodie_api.repository import RestaurantQuery
from foodie_api.routers.restaurants import decode_cursor, encode_cursor
from foodie_api.schemas import BoundingBox, City, CityDetail, Country, RestaurantDetail, RestaurantSummary
from foodie_api.settings import ApiSettings

PORTO_ID = 2735943


def summary(index: int) -> RestaurantSummary:
    return RestaurantSummary(
        restaurant_id=f"n{index}",
        name=f"Tasca {index:02d}",
        city_id=PORTO_ID,
        cuisines=["portuguese"],
        address=None,
        latitude=41.15,
        longitude=-8.61,
    )


class FakeRepository:
    def __init__(self, ready=True, restaurant_count=5):
        self.ready = ready
        self.rows = [summary(index) for index in range(restaurant_count)]
        self.queries: list[RestaurantQuery] = []
        self.city_calls = []

    def is_ready(self):
        if isinstance(self.ready, Exception):
            raise self.ready
        return self.ready

    def countries(self):
        return [Country(country_code="PT", country_name="Portugal", city_count=1, restaurant_count=5)]

    def cities(self, country_code, search, limit):
        self.city_calls.append((country_code, search, limit))
        return [
            City(
                city_id=PORTO_ID,
                name="Porto",
                label="Porto, Portugal",
                country_code="PT",
                country_name="Portugal",
                latitude=41.15,
                longitude=-8.61,
                restaurant_count=5,
            )
        ]

    def city(self, city_id):
        if city_id != PORTO_ID:
            return None
        extent = BoundingBox(min_latitude=41.1, min_longitude=-8.7, max_latitude=41.2, max_longitude=-8.5)
        return CityDetail(
            **self.cities(None, None, 1)[0].model_dump(), population=250000, restaurant_extent=extent
        )

    def restaurants(self, query):
        self.queries.append(query)
        rows = self.rows
        if query.after:
            rows = [row for row in rows if (row.name, row.restaurant_id) > query.after]
        return rows[: query.limit]

    def restaurant(self, restaurant_id):
        if restaurant_id != "n1":
            return None
        return RestaurantDetail(
            **summary(1).model_dump(),
            city_name="Porto",
            country_code="PT",
            country_name="Portugal",
            website=None,
            phone=None,
            opening_hours="Mo-Su 12:00-15:00",
            osm_url="https://www.openstreetmap.org/node/1",
            last_seen_at=datetime(2026, 10, 20, tzinfo=UTC),
        )


def settings(**overrides):
    values = {"database_url": "postgresql+psycopg://user@localhost/foodie", "_env_file": None, **overrides}
    return ApiSettings(**values)


@pytest.fixture
def repository():
    return FakeRepository()


@pytest.fixture
def client(repository):
    with TestClient(create_app(settings(api_default_limit=2, api_max_limit=3), repository)) as test_client:
        yield test_client


def test_liveness_never_needs_the_database():
    with TestClient(create_app(settings(), FakeRepository(ready=RuntimeError("db down")))) as test_client:
        assert test_client.get("/health/live").json() == {"status": "ok"}


@pytest.mark.parametrize("ready", [False, RuntimeError("db down")])
def test_readiness_returns_503_when_database_or_mart_unavailable(ready):
    with TestClient(create_app(settings(), FakeRepository(ready=ready))) as test_client:
        assert test_client.get("/health/ready").status_code == 503


def test_readiness_ok(client):
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_countries_include_geonames_attribution(client):
    body = client.get("/api/v1/countries").json()
    assert body["items"][0]["country_code"] == "PT"
    assert "GeoNames" in body["attribution"]


def test_cities_pass_trimmed_search_and_country(client, repository):
    client.get("/api/v1/cities", params={"country": "pt", "q": "  lisboa ", "limit": 5})
    assert repository.city_calls == [("pt", "lisboa", 5)]


@pytest.mark.parametrize("params", [{"country": "PRT"}, {"q": ""}, {"limit": 0}, {"limit": 101}])
def test_cities_reject_invalid_parameters(client, params):
    assert client.get("/api/v1/cities", params=params).status_code == 422


def test_city_detail_and_404(client):
    assert client.get(f"/api/v1/cities/{PORTO_ID}").json()["restaurant_extent"]["max_latitude"] == 41.2
    assert client.get("/api/v1/cities/1").status_code == 404


def test_restaurants_require_city_or_bounding_box(client):
    response = client.get("/api/v1/restaurants")
    assert response.status_code == 422
    assert "city_id or a bounding box" in response.json()["detail"]


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"min_lat": 41.1, "max_lat": 41.2, "min_lon": -8.7}, "together"),
        ({"min_lat": 41.2, "max_lat": 41.1, "min_lon": -8.7, "max_lon": -8.5}, "lower than"),
        ({"min_lat": 38.0, "max_lat": 42.0, "min_lon": -9.0, "max_lon": -8.0}, "at most 2.0 degrees"),
    ],
)
def test_restaurants_validate_bounding_box(client, params, message):
    response = client.get("/api/v1/restaurants", params=params)
    assert response.status_code == 422
    assert message in response.json()["detail"]


@pytest.mark.parametrize(
    "params",
    [{"city_id": 0}, {"city_id": PORTO_ID, "min_lat": 91, "max_lat": 92, "min_lon": 0, "max_lon": 1}],
)
def test_restaurants_reject_out_of_range_values(client, params):
    assert client.get("/api/v1/restaurants", params=params).status_code == 422


def test_restaurants_reject_cuisine_with_unexpected_characters(client):
    assert (
        client.get("/api/v1/restaurants", params={"city_id": PORTO_ID, "cuisine": "x' OR 1=1"}).status_code
        == 422
    )


def test_restaurants_pass_filters_to_repository(client, repository):
    client.get(
        "/api/v1/restaurants",
        params={
            "city_id": PORTO_ID,
            "min_lat": 41.1,
            "max_lat": 41.2,
            "min_lon": -8.7,
            "max_lon": -8.5,
            "cuisine": "Portuguese",
        },
    )
    [query] = repository.queries
    assert query.city_id == PORTO_ID
    assert query.bbox == BoundingBox(
        min_latitude=41.1, min_longitude=-8.7, max_latitude=41.2, max_longitude=-8.5
    )
    assert query.cuisine == "Portuguese"


def test_restaurants_page_with_cursor_until_exhausted(client, repository):
    seen, cursor = [], None
    while True:
        params = {"city_id": PORTO_ID, **({"cursor": cursor} if cursor else {})}
        body = client.get("/api/v1/restaurants", params=params).json()
        seen += [item["restaurant_id"] for item in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == ["n0", "n1", "n2", "n3", "n4"]
    assert all(query.limit == 3 for query in repository.queries)  # default page size 2 + 1 look-ahead
    assert "OpenStreetMap" in body["attribution"]


def test_restaurant_limit_is_capped(client, repository):
    body = client.get("/api/v1/restaurants", params={"city_id": PORTO_ID, "limit": 1000}).json()
    assert len(body["items"]) == 3
    assert repository.queries[0].limit == 4


def test_invalid_cursor_is_rejected(client):
    response = client.get("/api/v1/restaurants", params={"city_id": PORTO_ID, "cursor": "not-a-cursor"})
    assert response.status_code == 400


def test_cursor_round_trip_handles_unicode_names():
    assert decode_cursor(encode_cursor("4.ª Geração", "n1")) == ("4.ª Geração", "n1")


def test_restaurant_detail_404_and_id_validation(client):
    detail = client.get("/api/v1/restaurants/n1").json()
    assert detail["opening_hours"] == "Mo-Su 12:00-15:00"
    assert "OpenStreetMap" in detail["attribution"]
    assert client.get("/api/v1/restaurants/n2").status_code == 404
    assert client.get("/api/v1/restaurants/x1").status_code == 422


def test_cors_allows_configured_origin_only_for_get():
    app = create_app(settings(api_cors_origins=["http://localhost:5173"]), FakeRepository())
    with TestClient(app) as test_client:
        allowed = test_client.get("/health/live", headers={"Origin": "http://localhost:5173"})
        denied = test_client.get("/health/live", headers={"Origin": "http://evil.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
