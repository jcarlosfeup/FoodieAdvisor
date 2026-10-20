"""OpenStreetMap restaurants via the Overpass API (data © OpenStreetMap contributors, ODbL).

Use the public Overpass instance only for modest, controlled requests. Larger recurring
imports should move to regional OSM extracts.
"""

import time
from collections.abc import Callable
from typing import Any

import httpx

from foodie_collector.http import request_with_retries
from foodie_collector.models import BoundingBox, ParseResult, Rejection
from foodie_collector.traditional import TraditionalRule

OSM_TYPES = frozenset({"node", "way", "relation"})


class OverpassError(RuntimeError):
    """Overpass answered but reported a runtime error (e.g. query timeout or out of memory)."""


def build_restaurant_query(bbox: BoundingBox, timeout_seconds: int, rule: TraditionalRule) -> str:
    """Overpass QL for traditional restaurants inside bbox.

    The union matches restaurants whose `cuisine` list contains one of the rule's cuisines, or
    whose `name` contains one of its keywords (both case-insensitive). Overpass removes
    duplicates from the union. The global [bbox:...] setting applies to both statements.
    """
    cuisines = "|".join(rule.cuisines)
    keywords = "|".join(rule.name_keywords)
    return (
        f"[out:json][timeout:{timeout_seconds}]"
        f"[bbox:{bbox.south:.6f},{bbox.west:.6f},{bbox.north:.6f},{bbox.east:.6f}];\n"
        "(\n"
        f'  nwr["amenity"="restaurant"]["cuisine"~"(^|;) *({cuisines}) *(;|$)",i];\n'
        f'  nwr["amenity"="restaurant"]["name"~"{keywords}",i];\n'
        ");\n"
        "out center;"
    )


def parse_elements(elements: list[dict[str, Any]]) -> ParseResult:
    """Convert Overpass elements to raw.osm_restaurants records.

    Nodes carry lat/lon; ways and relations carry a `center` from `out center`. Elements without
    usable coordinates or identity are rejected rather than silently dropped. Missing names are
    kept: raw stays close to the source and dbt decides what is usable.
    """
    result = ParseResult()
    for element in elements:
        osm_type, osm_id = element.get("type"), element.get("id")
        record_id = f"{osm_type}/{osm_id}"
        if osm_type not in OSM_TYPES or not isinstance(osm_id, int):
            result.rejections.append(Rejection(record_id, "invalid_osm_identity", element))
            continue
        point = element if osm_type == "node" else element.get("center") or {}
        latitude, longitude = point.get("lat"), point.get("lon")
        if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
            result.rejections.append(Rejection(record_id, "missing_coordinates", element))
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            result.rejections.append(Rejection(record_id, "invalid_coordinates", element))
            continue
        result.records.append(
            {
                "osm_type": osm_type,
                "osm_id": osm_id,
                "latitude": float(latitude),
                "longitude": float(longitude),
                "tags": element.get("tags") or {},
            }
        )
    return result


class OverpassClient:
    def __init__(
        self,
        client: httpx.Client,
        url: str,
        query_timeout_seconds: int,
        max_attempts: int,
        backoff_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.client = client
        self.url = url
        self.query_timeout_seconds = query_timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep

    def fetch_restaurants(self, bbox: BoundingBox, rule: TraditionalRule) -> list[dict[str, Any]]:
        response = request_with_retries(
            self.client,
            "POST",
            self.url,
            data={"data": build_restaurant_query(bbox, self.query_timeout_seconds, rule)},
            timeout=self.query_timeout_seconds + 30,
            max_attempts=self.max_attempts,
            backoff_seconds=self.backoff_seconds,
            sleep=self.sleep,
        )
        payload = response.json()
        remark = payload.get("remark") or ""
        if "error" in remark.lower():
            raise OverpassError(remark)
        return payload.get("elements", [])
