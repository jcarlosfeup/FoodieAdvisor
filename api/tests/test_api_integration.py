"""End to end: raw rows -> real dbt models -> API, against an isolated PostGIS database."""

import pytest
from fastapi.testclient import TestClient

from foodie_api.main import create_app
from foodie_api.settings import ApiSettings

from .conftest import LISBON, PORTO

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client(mart_database_url):
    settings = ApiSettings(database_url=mart_database_url, _env_file=None)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def ids(body):
    return [item["restaurant_id"] for item in body["items"]]


def test_ready(client):
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_countries_only_list_countries_with_restaurants(client):
    items = client.get("/api/v1/countries").json()["items"]
    assert [(c["country_code"], c["city_count"], c["restaurant_count"]) for c in items] == [("PT", 2, 4)]


@pytest.mark.parametrize("search", ["oporto", "PORT", "porto"])
def test_city_search_matches_names_and_alternate_names(client, search):
    labels = [c["label"] for c in client.get("/api/v1/cities", params={"q": search}).json()["items"]]
    assert labels == ["Porto, Portugal"]  # Porto Alegre has no restaurants, so it is not offered


def test_city_search_escapes_like_wildcards(client):
    assert client.get("/api/v1/cities", params={"q": "%"}).json()["items"] == []


def test_city_detail_includes_restaurant_extent(client):
    city = client.get(f"/api/v1/cities/{PORTO}").json()
    assert city["restaurant_count"] == 3
    assert city["restaurant_extent"]["max_latitude"] == pytest.approx(41.16)


def test_restaurants_by_city_exclude_unnamed_and_stale_rows(client):
    body = client.get("/api/v1/restaurants", params={"city_id": PORTO}).json()
    assert ids(body) == ["w3", "n1", "n2"]  # ordered by name: Adega C, Tasca A, Tasca B
    assert body["next_cursor"] is None


def test_restaurants_by_bounding_box(client):
    params = {"min_lat": 41.14, "max_lat": 41.15, "min_lon": -8.62, "max_lon": -8.60}
    assert ids(client.get("/api/v1/restaurants", params=params).json()) == ["n1", "n2"]


def test_restaurants_filter_by_cuisine(client):
    params = {"city_id": PORTO, "cuisine": "regional"}
    assert ids(client.get("/api/v1/restaurants", params=params).json()) == ["n2"]


def test_restaurants_paginate_with_keyset_cursor(client):
    first = client.get("/api/v1/restaurants", params={"city_id": PORTO, "limit": 2}).json()
    second = client.get(
        "/api/v1/restaurants", params={"city_id": PORTO, "limit": 2, "cursor": first["next_cursor"]}
    ).json()
    assert ids(first) == ["w3", "n1"]
    assert ids(second) == ["n2"]
    assert second["next_cursor"] is None


def test_restaurant_detail(client):
    detail = client.get("/api/v1/restaurants/n1").json()
    assert detail["name"] == "Tasca A"
    assert detail["address"] == "Rua A 1, Porto"
    assert detail["website"] == "https://tasca-a.pt"
    assert detail["opening_hours"] == "Mo-Sa 12:00-22:00"
    assert detail["osm_url"] == "https://www.openstreetmap.org/node/1"
    assert detail["city_id"] == PORTO


def test_lisbon_restaurant_is_assigned_to_lisbon(client):
    assert ids(client.get("/api/v1/restaurants", params={"city_id": LISBON}).json()) == ["n6"]
