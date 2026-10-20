"""Load GeoNames countries and cities into the raw layer."""

from sqlalchemy import Engine

from foodie_collector.ingestion.raw_loader import (
    GEONAMES_CITIES,
    GEONAMES_COUNTRIES,
    RawTable,
    deduplicate,
    load_records,
)
from foodie_collector.ingestion.runs import RunStats, record_rejections, tracked_run
from foodie_collector.models import ParseResult
from foodie_collector.sources.geonames import GeoNamesDownloader, parse_cities, parse_countries

SOURCE_COUNTRIES = "geonames_countries"
SOURCE_CITIES = "geonames_cities"


def _land(engine: Engine, stats: RunStats, raw_table: RawTable, source: str, parsed: ParseResult) -> None:
    records, duplicates = deduplicate(raw_table, parsed.records)
    rejections = parsed.rejections + duplicates
    with engine.begin() as connection:
        stats.add(load_records(connection, raw_table, stats.run_id, records))
        stats.rejected = record_rejections(connection, stats.run_id, source, rejections)
    stats.received = len(parsed.records) + len(parsed.rejections)


def collect_countries(engine: Engine, downloader: GeoNamesDownloader, refresh: bool = False) -> RunStats:
    with tracked_run(engine, SOURCE_COUNTRIES, "countryInfo.txt", {"refresh": refresh}) as stats:
        _land(
            engine,
            stats,
            GEONAMES_COUNTRIES,
            SOURCE_COUNTRIES,
            parse_countries(downloader.countries(refresh)),
        )
    return stats


def collect_cities(
    engine: Engine, downloader: GeoNamesDownloader, dataset: str, refresh: bool = False
) -> RunStats:
    with tracked_run(engine, SOURCE_CITIES, dataset, {"refresh": refresh}) as stats:
        _land(
            engine, stats, GEONAMES_CITIES, SOURCE_CITIES, parse_cities(downloader.cities(dataset, refresh))
        )
    return stats
