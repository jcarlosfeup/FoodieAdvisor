"""Resolve collection targets from raw.geonames_cities. Cities are identified by geonameid."""

from sqlalchemy import Connection, text

from foodie_collector.models import CityTarget


class CityLookupError(ValueError):
    pass


_SELECT_CITY = """
    SELECT geonameid, name, country_code, latitude, longitude, population
    FROM raw.geonames_cities
"""


def _target(row) -> CityTarget:
    return CityTarget(
        geonameid=row.geonameid,
        name=row.name,
        country_code=row.country_code,
        latitude=row.latitude,
        longitude=row.longitude,
    )


def city_by_geonameid(connection: Connection, geonameid: int) -> CityTarget:
    row = connection.execute(text(_SELECT_CITY + " WHERE geonameid = :id"), {"id": geonameid}).first()
    if row is None:
        raise CityLookupError(
            f"geonameid {geonameid} is not in raw.geonames_cities; run `foodie-collect cities` first"
        )
    return _target(row)


def city_by_name(connection: Connection, name: str, country_code: str) -> CityTarget:
    """Find a city by exact (case-insensitive) name or ASCII name within a country."""
    rows = connection.execute(
        text(
            _SELECT_CITY
            + """
            WHERE country_code = upper(:country_code)
              AND (lower(name) = lower(:name) OR lower(asciiname) = lower(:name))
            ORDER BY population DESC NULLS LAST, geonameid
            """
        ),
        {"name": name, "country_code": country_code},
    ).all()
    if not rows:
        raise CityLookupError(
            f"No GeoNames city named {name!r} in {country_code.upper()}; "
            "check the spelling or run `foodie-collect cities` first"
        )
    if len(rows) > 1:
        candidates = ", ".join(f"{row.geonameid} (population {row.population})" for row in rows)
        raise CityLookupError(
            f"{name!r} in {country_code.upper()} is ambiguous; use --geonameid: {candidates}"
        )
    return _target(rows[0])
