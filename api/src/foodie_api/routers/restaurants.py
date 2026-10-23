import base64
import binascii
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from foodie_api.dependencies import get_repository, get_settings
from foodie_api.repository import Repository, RestaurantQuery
from foodie_api.schemas import BoundingBox, RestaurantDetail, RestaurantPage
from foodie_api.settings import ApiSettings

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])

RESTAURANT_ID_PATTERN = r"^[nwr][0-9]{1,19}$"


def encode_cursor(name: str, restaurant_id: str) -> str:
    return base64.urlsafe_b64encode(json.dumps([name, restaurant_id]).encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        name, restaurant_id = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except (binascii.Error, ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail="invalid cursor") from error
    if not isinstance(name, str) or not isinstance(restaurant_id, str):
        raise HTTPException(status_code=400, detail="invalid cursor")
    return name, restaurant_id


def _bounding_box(settings: ApiSettings, values: dict[str, float | None]) -> BoundingBox | None:
    provided = {key: value for key, value in values.items() if value is not None}
    if not provided:
        return None
    if len(provided) != len(values):
        raise HTTPException(
            status_code=422, detail="min_lat, max_lat, min_lon and max_lon must be given together"
        )
    bbox = BoundingBox(
        min_latitude=provided["min_lat"],
        max_latitude=provided["max_lat"],
        min_longitude=provided["min_lon"],
        max_longitude=provided["max_lon"],
    )
    if bbox.min_latitude >= bbox.max_latitude or bbox.min_longitude >= bbox.max_longitude:
        raise HTTPException(status_code=422, detail="bounding box minimums must be lower than maximums")
    span = settings.api_max_bbox_span_degrees
    if bbox.max_latitude - bbox.min_latitude > span or bbox.max_longitude - bbox.min_longitude > span:
        raise HTTPException(status_code=422, detail=f"bounding box sides must be at most {span} degrees")
    return bbox


@router.get("", response_model=RestaurantPage)
def list_restaurants(
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[ApiSettings, Depends(get_settings)],
    city_id: Annotated[int | None, Query(ge=1, description="GeoNames geonameid")] = None,
    min_lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    max_lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    min_lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    max_lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    cuisine: Annotated[
        str | None, Query(pattern=r"^[A-Za-z_]{1,40}$", description="OSM cuisine value, e.g. portuguese")
    ] = None,
    limit: Annotated[int | None, Query(ge=1, description="Page size (capped by API_MAX_LIMIT)")] = None,
    cursor: Annotated[
        str | None, Query(max_length=500, description="next_cursor from the previous page")
    ] = None,
) -> RestaurantPage:
    """Traditional restaurants in a city and/or inside the visible map box, ordered by name.

    Give `city_id`, a full bounding box (`min_lat`, `max_lat`, `min_lon`, `max_lon`), or both.
    """
    bbox = _bounding_box(
        settings, {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon}
    )
    if city_id is None and bbox is None:
        raise HTTPException(status_code=422, detail="give city_id or a bounding box")
    page_size = min(limit or settings.api_default_limit, settings.api_max_limit)
    query = RestaurantQuery(
        city_id=city_id,
        bbox=bbox,
        cuisine=cuisine,
        limit=page_size + 1,  # one extra row tells us whether another page exists
        after=decode_cursor(cursor) if cursor else None,
    )
    rows = repository.restaurants(query)
    items = rows[:page_size]
    next_cursor = encode_cursor(items[-1].name, items[-1].restaurant_id) if len(rows) > page_size else None
    return RestaurantPage(items=items, next_cursor=next_cursor)


@router.get(
    "/{restaurant_id}", response_model=RestaurantDetail, responses={404: {"description": "Not found"}}
)
def get_restaurant(
    repository: Annotated[Repository, Depends(get_repository)],
    restaurant_id: Annotated[
        str,
        Path(
            pattern=RESTAURANT_ID_PATTERN,
            description="OSM short id: n123 (node), w123 (way), r123 (relation)",
        ),
    ],
) -> RestaurantDetail:
    restaurant = repository.restaurant(restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail=f"restaurant {restaurant_id} not found")
    return restaurant
