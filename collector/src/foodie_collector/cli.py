"""foodie-collect: command-line entry point for the ingestion jobs.

foodie-collect cities [--refresh]
foodie-collect restaurants --city "Porto,PT" [--city "Lisbon,PT"] [--geonameid 2735943] [--radius-km 5]
"""

import argparse
import logging
import sys
import time

from foodie_collector.http import build_client
from foodie_collector.ingestion.collect_cities import collect_cities, collect_countries
from foodie_collector.ingestion.collect_restaurants import collect_restaurants
from foodie_collector.ingestion.targets import CityLookupError, city_by_geonameid, city_by_name
from foodie_collector.models import CityTarget
from foodie_collector.settings import CollectorSettings
from foodie_collector.sources.geonames import GeoNamesDownloader
from foodie_collector.sources.openstreetmap import OverpassClient
from foodie_collector.traditional import UnsupportedCountryError, traditional_rule
from foodie_common.db import make_engine
from foodie_common.logging import configure_logging

logger = logging.getLogger("foodie_collector")


def parse_city_argument(value: str) -> tuple[str, str]:
    name, separator, country_code = value.rpartition(",")
    if not separator or not name.strip() or len(country_code.strip()) != 2:
        raise argparse.ArgumentTypeError(f"expected 'City name,CC' (ISO country code), got {value!r}")
    return name.strip(), country_code.strip().upper()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="foodie-collect", description="FoodieAdvisor ingestion jobs")
    parser.add_argument("--log-level", default="INFO")
    commands = parser.add_subparsers(dest="command", required=True)

    cities = commands.add_parser("cities", help="load GeoNames countries and cities into raw")
    cities.add_argument(
        "--refresh", action="store_true", help="re-download files instead of using data/ cache"
    )

    restaurants = commands.add_parser(
        "restaurants", help="load traditional OSM restaurants around cities into raw"
    )
    restaurants.add_argument(
        "--city", action="append", default=[], type=parse_city_argument, metavar="'NAME,CC'",
        help="GeoNames city name and ISO country code, e.g. 'Porto,PT' (repeatable)",
    )  # fmt: skip
    restaurants.add_argument("--geonameid", action="append", default=[], type=int, help="(repeatable)")
    restaurants.add_argument("--radius-km", type=float, help="search radius around the city centre")
    return parser


def _run_cities(settings: CollectorSettings, args: argparse.Namespace) -> int:
    engine = make_engine(settings)
    with build_client(settings.http_user_agent, settings.http_timeout_seconds) as client:
        downloader = GeoNamesDownloader(
            client,
            settings.geonames_base_url,
            settings.data_dir / "geonames",
            settings.http_max_attempts,
            settings.http_backoff_seconds,
        )
        collect_countries(engine, downloader, args.refresh)
        collect_cities(engine, downloader, settings.geonames_cities_file, args.refresh)
    return 0


def _resolve_targets(settings: CollectorSettings, args: argparse.Namespace) -> list[CityTarget]:
    engine = make_engine(settings)
    with engine.connect() as connection:
        targets = [city_by_name(connection, name, country) for name, country in args.city]
        targets += [city_by_geonameid(connection, geonameid) for geonameid in args.geonameid]
    return targets


def _run_restaurants(settings: CollectorSettings, args: argparse.Namespace) -> int:
    if not args.city and not args.geonameid:
        logger.error("restaurants needs at least one --city or --geonameid")
        return 2
    try:
        targets = _resolve_targets(settings, args)
        for city in targets:
            traditional_rule(city.country_code)
    except (CityLookupError, UnsupportedCountryError) as error:
        logger.error(str(error))
        return 2
    radius_km = args.radius_km or settings.default_radius_km
    engine = make_engine(settings)
    failures = 0
    with build_client(settings.http_user_agent, settings.http_timeout_seconds) as client:
        overpass = OverpassClient(
            client,
            settings.overpass_url,
            settings.overpass_query_timeout_seconds,
            settings.http_max_attempts,
            settings.http_backoff_seconds,
        )
        for index, city in enumerate(targets):
            if index:
                time.sleep(settings.overpass_request_delay_seconds)
            try:
                collect_restaurants(engine, overpass, city, radius_km)
            except Exception:  # already logged and recorded as a failed run; continue with other cities
                failures += 1
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)
    settings = CollectorSettings()
    if args.command == "cities":
        return _run_cities(settings, args)
    return _run_restaurants(settings, args)


if __name__ == "__main__":
    sys.exit(main())
