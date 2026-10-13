# FoodieAdvisor

Discover restaurants in a city and explore them on an interactive map.

FoodieAdvisor is built as a small data platform:

- OpenStreetMap and GeoNames data is ingested into PostgreSQL/PostGIS.
- dbt transforms it into application-ready models.
- A FastAPI backend serves those models to a React + Leaflet frontend.
- Everything runs in Docker Compose, and later in local Kubernetes.

> **Status: Phase 1 (foundation).** The uv workspace, shared settings, the Google Places lab module and a development PostGIS database are in place. Ingestion, dbt, the API and the frontend arrive in later phases.

## Requirements (macOS)

- [uv](https://docs.astral.sh/uv/): `brew install uv`. It installs Python 3.12 automatically.
- Docker Desktop, or another Docker engine.

## Setup

```sh
uv sync                          # create .venv with all workspace packages and dev tools
cp .env.example .env             # set POSTGRES_PASSWORD and the matching DATABASE_URL
docker compose up -d db          # PostGIS 17 with the raw / core / mart schemas
```

Check the database:

```sh
docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -c "\dn" -c "SELECT postgis_version();"'
```

The SQL files in `db/init/` run only when the `pgdata` volume is first created.
`docker compose down` keeps your data. `docker compose down -v` deletes it.

## Tests and linting

```sh
uv run ruff check .
uv run pytest -q
```

## Repository layout

| Path | Purpose |
|---|---|
| `packages/foodie_common/` | Shared settings (`DATABASE_URL`), SQLAlchemy engine factory, JSON logging |
| `collector/` | Ingestion jobs. Currently contains the Google Places lab module |
| `db/init/` | Bootstrap SQL: PostGIS, `pg_trgm`, and the `raw`/`core`/`mart` schemas |
| `compose.yaml` | Development database |

## Google Places lab

`foodie_collector.sources.google_places_lab` is an isolated experiment and never writes to the database. Google's terms restrict storing Places content, so the application's restaurant data comes from OpenStreetMap instead.

To use the lab, put a service-account key under `secrets/` (gitignored) and set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.

## Data attribution

- Restaurant data © OpenStreetMap contributors, ODbL.
- City data © GeoNames, CC BY 4.0.
