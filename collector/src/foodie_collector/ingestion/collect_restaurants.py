"""Load traditional OpenStreetMap restaurants around a GeoNames city into raw.osm_restaurants."""

from dataclasses import asdict
from typing import Protocol

from sqlalchemy import Engine

from foodie_collector.ingestion.raw_loader import OSM_RESTAURANTS, deduplicate, load_records
from foodie_collector.ingestion.runs import RunStats, record_rejections, tracked_run
from foodie_collector.models import BoundingBox, CityTarget
from foodie_collector.sources.openstreetmap import parse_elements
from foodie_collector.traditional import TraditionalRule, traditional_rule

SOURCE = "osm_overpass"


class RestaurantSource(Protocol):
    def fetch_restaurants(self, bbox: BoundingBox, rule: TraditionalRule) -> list[dict]: ...


def collect_restaurants(
    engine: Engine, source: RestaurantSource, city: CityTarget, radius_km: float
) -> RunStats:
    rule = traditional_rule(city.country_code)  # fails before a run is recorded
    bbox = BoundingBox.around(city.latitude, city.longitude, radius_km)
    parameters = {
        "geonameid": city.geonameid,
        "radius_km": radius_km,
        "bbox": asdict(bbox),
        "traditional_rule": rule.as_parameters(),
    }
    with tracked_run(engine, SOURCE, city.label, parameters) as stats:
        elements = source.fetch_restaurants(bbox, rule)
        parsed = parse_elements(elements)
        records, duplicates = deduplicate(OSM_RESTAURANTS, parsed.records)
        with engine.begin() as connection:
            stats.add(load_records(connection, OSM_RESTAURANTS, stats.run_id, records))
            stats.rejected = record_rejections(
                connection, stats.run_id, SOURCE, parsed.rejections + duplicates
            )
        stats.received = len(elements)
    return stats
