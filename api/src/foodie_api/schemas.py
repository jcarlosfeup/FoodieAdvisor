"""Response models. Field names are the public API contract."""

from datetime import datetime

from pydantic import BaseModel

OSM_ATTRIBUTION = (
    "Restaurant data © OpenStreetMap contributors, ODbL (https://www.openstreetmap.org/copyright)"
)
GEONAMES_ATTRIBUTION = "City data © GeoNames, CC BY 4.0 (https://www.geonames.org)"


class Country(BaseModel):
    country_code: str
    country_name: str | None
    city_count: int
    restaurant_count: int


class City(BaseModel):
    city_id: int
    name: str
    label: str
    country_code: str
    country_name: str | None
    latitude: float
    longitude: float
    restaurant_count: int


class BoundingBox(BaseModel):
    min_latitude: float
    min_longitude: float
    max_latitude: float
    max_longitude: float


class CityDetail(City):
    population: int | None
    restaurant_extent: BoundingBox


class RestaurantSummary(BaseModel):
    restaurant_id: str
    name: str
    city_id: int
    cuisines: list[str]
    address: str | None
    latitude: float
    longitude: float


class RestaurantDetail(RestaurantSummary):
    city_name: str
    country_code: str
    country_name: str | None
    website: str | None
    phone: str | None
    opening_hours: str | None
    osm_url: str
    last_seen_at: datetime
    attribution: str = OSM_ATTRIBUTION


class CountryList(BaseModel):
    items: list[Country]
    attribution: str = GEONAMES_ATTRIBUTION


class CityList(BaseModel):
    items: list[City]
    attribution: str = GEONAMES_ATTRIBUTION


class RestaurantPage(BaseModel):
    items: list[RestaurantSummary]
    next_cursor: str | None
    attribution: str = OSM_ATTRIBUTION


class Health(BaseModel):
    status: str
