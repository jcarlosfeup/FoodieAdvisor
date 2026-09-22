from typing import Any


def transform_places(data: list[dict[str, Any]], city_name: str) -> list[dict[str, Any]]:
    """Transform Google Places payloads into the application's restaurant shape."""
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
