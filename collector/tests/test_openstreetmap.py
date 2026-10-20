import json
from pathlib import Path

import httpx
import pytest

from foodie_collector.models import BoundingBox
from foodie_collector.sources.openstreetmap import (
    OverpassClient,
    OverpassError,
    build_restaurant_query,
    parse_elements,
)
from foodie_collector.traditional import TraditionalRule, traditional_rule

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "overpass_porto.json").read_text())
PORTO_BBOX = BoundingBox(41.10, -8.67, 41.19, -8.55)
PT = traditional_rule("PT")


def overpass_client(handler, sleeps=None, max_attempts=3):
    sleeps = sleeps if sleeps is not None else []
    return OverpassClient(
        httpx.Client(transport=httpx.MockTransport(handler)),
        "https://overpass.test/api/interpreter",
        query_timeout_seconds=25,
        max_attempts=max_attempts,
        backoff_seconds=1.0,
        sleep=sleeps.append,
    )


def test_bounding_box_around_porto_is_roughly_radius_wide():
    bbox = BoundingBox.around(41.1496, -8.6110, radius_km=5)
    assert bbox.north - bbox.south == pytest.approx(2 * 5 / 111.32)
    # Longitude degrees are shorter away from the equator, so the box is wider in degrees.
    assert (bbox.east - bbox.west) > (bbox.north - bbox.south)
    assert bbox.south < 41.1496 < bbox.north and bbox.west < -8.6110 < bbox.east


def test_bounding_box_rejects_non_positive_radius():
    with pytest.raises(ValueError):
        BoundingBox.around(41.0, -8.0, 0)


def test_query_sets_global_bbox_in_south_west_north_east_order_and_center_output():
    query = build_restaurant_query(PORTO_BBOX, 25, PT)
    assert query.startswith("[out:json][timeout:25][bbox:41.100000,-8.670000,41.190000,-8.550000];")
    assert query.endswith("out center;")


def test_query_unions_traditional_cuisines_and_name_keywords():
    query = build_restaurant_query(PORTO_BBOX, 25, PT)
    assert '["cuisine"~"(^|;) *(portuguese|francesinha|regional|local) *(;|$)",i]' in query
    assert '["name"~"tasca|tasquinha|taberna|adega|casa de pasto",i]' in query
    assert query.count('nwr["amenity"="restaurant"]') == 2


def test_query_follows_the_country_rule():
    rule = TraditionalRule("XX", national_cuisines=("testish",), name_keywords=("casa",))
    query = build_restaurant_query(PORTO_BBOX, 25, rule)
    assert "(testish|regional|local)" in query
    assert '["name"~"casa",i]' in query


def test_parse_elements_uses_node_coordinates_and_way_or_relation_center():
    result = parse_elements(FIXTURE["elements"])
    by_id = {(r["osm_type"], r["osm_id"]): r for r in result.records}

    assert by_id[("node", 101)]["latitude"] == 41.1455
    assert by_id[("node", 101)]["tags"]["cuisine"] == "portuguese;regional"
    assert by_id[("way", 202)]["longitude"] == -8.6080
    assert ("relation", 303) in by_id


def test_parse_elements_keeps_unnamed_records_with_empty_tags():
    result = parse_elements(FIXTURE["elements"])
    unnamed = next(r for r in result.records if r["osm_id"] == 404)
    assert unnamed["tags"] == {}


def test_parse_elements_rejects_missing_and_invalid_coordinates():
    result = parse_elements(FIXTURE["elements"])
    reasons = {r.source_record_id: r.reason for r in result.rejections}
    assert reasons == {"way/505": "missing_coordinates", "node/606": "invalid_coordinates"}
    assert len(result.records) == 4


def test_parse_elements_rejects_unknown_identity():
    result = parse_elements(
        [{"type": "area", "id": 1, "lat": 1, "lon": 1}, {"type": "node", "lat": 1, "lon": 1}]
    )
    assert [r.reason for r in result.rejections] == ["invalid_osm_identity", "invalid_osm_identity"]


def test_client_posts_query_and_returns_elements():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content.decode()
        return httpx.Response(200, json=FIXTURE)

    elements = overpass_client(handler).fetch_restaurants(PORTO_BBOX, PT)

    assert len(elements) == len(FIXTURE["elements"])
    assert seen["body"].startswith("data=")


def test_client_retries_rate_limits_and_gateway_errors_with_backoff():
    responses = iter([httpx.Response(429), httpx.Response(504), httpx.Response(200, json={"elements": []})])
    sleeps = []

    elements = overpass_client(lambda request: next(responses), sleeps).fetch_restaurants(PORTO_BBOX, PT)

    assert elements == []
    assert sleeps == [1.0, 2.0]


def test_client_honours_retry_after_header():
    responses = iter([httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={})])
    sleeps = []
    overpass_client(lambda request: next(responses), sleeps).fetch_restaurants(PORTO_BBOX, PT)
    assert sleeps == [7.0]


def test_client_retries_transport_errors_then_gives_up():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectTimeout("timed out", request=request)

    sleeps = []
    with pytest.raises(httpx.ConnectTimeout):
        overpass_client(handler, sleeps, max_attempts=3).fetch_restaurants(PORTO_BBOX, PT)
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]


def test_client_does_not_retry_bad_requests():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400, text="parse error")

    with pytest.raises(httpx.HTTPStatusError):
        overpass_client(handler).fetch_restaurants(PORTO_BBOX, PT)
    assert len(calls) == 1


def test_client_raises_on_overpass_runtime_error_remark():
    payload = {
        "elements": [],
        "remark": 'runtime error: Query timed out in "query" at line 2 after 26 seconds.',
    }
    with pytest.raises(OverpassError, match="timed out"):
        overpass_client(lambda request: httpx.Response(200, json=payload)).fetch_restaurants(PORTO_BBOX, PT)
