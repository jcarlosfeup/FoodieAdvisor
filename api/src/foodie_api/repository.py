"""Read-only access to the mart schema. All SQL is parameterized; only fixed fragments are composed."""

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Engine, text

from foodie_api.schemas import BoundingBox, City, CityDetail, Country, RestaurantDetail, RestaurantSummary


@dataclass(frozen=True)
class RestaurantQuery:
    city_id: int | None = None
    bbox: BoundingBox | None = None
    cuisine: str | None = None
    limit: int = 100
    after: tuple[str, str] | None = None  # keyset cursor: (name, restaurant_id) of the last row seen


class Repository(Protocol):
    def is_ready(self) -> bool: ...
    def countries(self) -> list[Country]: ...
    def cities(self, country_code: str | None, search: str | None, limit: int) -> list[City]: ...
    def city(self, city_id: int) -> CityDetail | None: ...
    def restaurants(self, query: RestaurantQuery) -> list[RestaurantSummary]: ...
    def restaurant(self, restaurant_id: str) -> RestaurantDetail | None: ...


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_CITY_COLUMNS = """
    city_id, name, label, country_code, country_name, latitude, longitude, restaurant_count
"""

_RESTAURANT_SUMMARY_COLUMNS = """
    restaurant_id, name, city_id, cuisines, address, latitude, longitude
"""


class PostgresRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def is_ready(self) -> bool:
        with self.engine.connect() as connection:
            return bool(
                connection.execute(
                    text("SELECT to_regclass('mart.restaurant_search') IS NOT NULL")
                ).scalar_one()
            )

    def countries(self) -> list[Country]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT country_code, country_name, city_count, restaurant_count
                    FROM mart.country_summary
                    ORDER BY country_name, country_code
                """)
            ).mappings()
            return [Country.model_validate(dict(row)) for row in rows]

    def cities(self, country_code: str | None, search: str | None, limit: int) -> list[City]:
        conditions, params = ["TRUE"], {"limit": limit}
        if country_code:
            conditions.append("country_code = :country_code")
            params["country_code"] = country_code.upper()
        if search:
            # search_text holds name, ASCII name and GeoNames alternate names (trigram-indexed).
            conditions.append("search_text LIKE :pattern ESCAPE '\\'")
            params["pattern"] = f"%{_escape_like(search.lower())}%"
            params["prefix"] = f"{_escape_like(search.lower())}%"
            order = "(lower(name) LIKE :prefix ESCAPE '\\') DESC, restaurant_count DESC, name"
        else:
            order = "restaurant_count DESC, name"
        sql = f"""
            SELECT {_CITY_COLUMNS}
            FROM mart.city_summary
            WHERE {" AND ".join(conditions)}
            ORDER BY {order}
            LIMIT :limit
        """
        with self.engine.connect() as connection:
            return [
                City.model_validate(dict(row)) for row in connection.execute(text(sql), params).mappings()
            ]

    def city(self, city_id: int) -> CityDetail | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(f"""
                        SELECT {_CITY_COLUMNS}, population,
                               min_latitude, min_longitude, max_latitude, max_longitude
                        FROM mart.city_summary
                        WHERE city_id = :city_id
                    """),
                    {"city_id": city_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        data = dict(row)
        extent = BoundingBox(**{key: data.pop(key) for key in BoundingBox.model_fields})
        return CityDetail(**data, restaurant_extent=extent)

    def restaurants(self, query: RestaurantQuery) -> list[RestaurantSummary]:
        conditions, params = ["TRUE"], {"limit": query.limit}
        if query.city_id is not None:
            conditions.append("city_id = :city_id")
            params["city_id"] = query.city_id
        if query.bbox is not None:
            # && uses the GiST index on geom.
            conditions.append(
                "geom && ST_MakeEnvelope(:min_longitude, :min_latitude, :max_longitude, :max_latitude, 4326)"
            )
            params.update(query.bbox.model_dump())
        if query.cuisine:
            conditions.append("cuisines @> ARRAY[CAST(:cuisine AS text)]")  # GIN index on cuisines
            params["cuisine"] = query.cuisine.lower()
        if query.after is not None:
            conditions.append("(name, restaurant_id) > (:after_name, :after_id)")
            params["after_name"], params["after_id"] = query.after
        sql = f"""
            SELECT {_RESTAURANT_SUMMARY_COLUMNS}
            FROM mart.restaurant_search
            WHERE {" AND ".join(conditions)}
            ORDER BY name, restaurant_id
            LIMIT :limit
        """
        with self.engine.connect() as connection:
            rows = connection.execute(text(sql), params).mappings()
            return [RestaurantSummary.model_validate(dict(row)) for row in rows]

    def restaurant(self, restaurant_id: str) -> RestaurantDetail | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    text(f"""
                        SELECT {_RESTAURANT_SUMMARY_COLUMNS}, city_name, country_code, country_name,
                               website, phone, opening_hours, osm_url, last_seen_at
                        FROM mart.restaurant_search
                        WHERE restaurant_id = :restaurant_id
                    """),
                    {"restaurant_id": restaurant_id},
                )
                .mappings()
                .first()
            )
        return RestaurantDetail.model_validate(dict(row)) if row else None
