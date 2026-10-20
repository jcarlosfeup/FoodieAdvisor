"""Plain data types passed between sources and loaders."""

import math
from dataclasses import dataclass, field
from typing import Any

KM_PER_DEGREE_LATITUDE = 111.32


@dataclass(frozen=True)
class BoundingBox:
    south: float
    west: float
    north: float
    east: float

    @classmethod
    def around(cls, latitude: float, longitude: float, radius_km: float) -> "BoundingBox":
        if radius_km <= 0:
            raise ValueError("radius_km must be positive")
        dlat = radius_km / KM_PER_DEGREE_LATITUDE
        dlon = radius_km / (KM_PER_DEGREE_LATITUDE * max(math.cos(math.radians(latitude)), 0.01))
        return cls(
            south=max(latitude - dlat, -90.0),
            west=max(longitude - dlon, -180.0),
            north=min(latitude + dlat, 90.0),
            east=min(longitude + dlon, 180.0),
        )


@dataclass(frozen=True)
class CityTarget:
    """A GeoNames city used to scope a collection run."""

    geonameid: int
    name: str
    country_code: str
    latitude: float
    longitude: float

    @property
    def label(self) -> str:
        return f"{self.name}, {self.country_code} (geonameid {self.geonameid})"


@dataclass(frozen=True)
class Rejection:
    """A source record that could not be landed in the raw layer."""

    source_record_id: str | None
    reason: str
    payload: dict[str, Any] | None = None


@dataclass
class ParseResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
