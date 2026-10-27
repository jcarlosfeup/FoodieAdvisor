# FoodieAdvisor

Discover a city's traditional restaurants (its own country's cuisine) and explore them on an interactive map.

FoodieAdvisor is built as a small data platform:

- OpenStreetMap and GeoNames data is ingested into PostgreSQL/PostGIS.
- dbt transforms it into application-ready models.
- A FastAPI backend serves those models to a React + Leaflet frontend.
- Everything runs in Docker Compose, and later in local Kubernetes.

> **Status: Phase 5 (frontend).** Traditional restaurants and GeoNames cities load into `raw`, dbt builds tested `core` and `mart` tables, a read-only FastAPI service exposes them, and a React + Leaflet web app shows them on a map. Docker Compose for the whole stack comes in Phase 6.

## Requirements (macOS)

- [uv](https://docs.astral.sh/uv/): `brew install uv`. It installs Python 3.12 automatically.
- Docker Desktop, or another Docker engine.
- Node.js 22 or newer, for the frontend (`brew install node`).

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

The SQL files in `db/init/` run only when the `pgdata` volume is first created. To apply a new file to an existing database:

```sh
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB' < db/init/02_raw_tables.sql
```

`docker compose down` keeps your data. `docker compose down -v` deletes it.

## Loading data

Load the city catalog first. Restaurant targets are resolved from it.

```sh
uv run foodie-collect cities
uv run foodie-collect restaurants --city "Porto,PT" --city "Vila Nova de Gaia,PT" --city "Lisbon,PT"
```

- **`cities`** downloads GeoNames `countryInfo.txt` and `cities5000.zip` into `data/geonames/` (cached; `--refresh` re-downloads). It loads `raw.geonames_countries` and `raw.geonames_cities`.
- **`restaurants`** queries the public Overpass API for **traditional** restaurants inside a box around each city (`--radius-km`, default 5) and loads `raw.osm_restaurants`. A restaurant counts as traditional when its OSM `cuisine` tag contains the country's cuisine (e.g. `portuguese`) or `regional`/`local`, or its name contains a word such as *tasca*, *taberna* or *adega*. The rules per country are in `collector/src/foodie_collector/traditional.py`; supported countries are currently PT, ES, IT, FR, GR and BR. Pick a city by `"Name,CC"` or by `--geonameid` when a name is ambiguous.
- **Reruns are safe.** Unchanged records aren't rewritten; a rerun reports `inserted: 0, updated: 0`.

Every run is recorded in `raw.ingestion_runs`, and unusable records go to `raw.rejected_records`:

```sh
docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT source, target, status, received_count, inserted_count, updated_count, unchanged_count, rejected_count FROM raw.ingestion_runs ORDER BY started_at"'
```

The public Overpass service is shared, so keep requests modest. The collector retries busy responses (429/5xx) with backoff and waits between cities.

## Transforming data (dbt)

After collecting, build the cleaned and application-ready tables:

```sh
uv run --env-file .env dbt deps  --project-dir transformations/dbt --profiles-dir transformations/dbt   # once
uv run --env-file .env dbt build --project-dir transformations/dbt --profiles-dir transformations/dbt
```

| Schema | Tables | Purpose |
|---|---|---|
| `staging` | `stg_*` views | Typed, renamed source data |
| `core` | `country`, `city`, `restaurant`, `restaurant_excluded` | Clean restaurants assigned to a collected city; excluded ones with the reason |
| `mart` | `restaurant_search`, `city_summary`, `country_summary` | What the API reads: spatially indexed restaurants and the city/country selectors |

A restaurant appears in `core.restaurant` only if the latest collection of its city still returned it, and it is assigned to the nearest collected city centre. `dbt build` also runs the data tests and unit tests.

## Running the API

```sh
uv run foodie-api                # http://127.0.0.1:8000, interactive docs at /docs
```

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/countries` | Countries that have restaurants |
| `GET /api/v1/cities?country=PT&q=lisboa` | City search (also matches local names such as Lisboa or Oporto) |
| `GET /api/v1/cities/{city_id}` | City details and the extent of its restaurants, for fitting the map |
| `GET /api/v1/restaurants?city_id=2735943` | Restaurants in a city, ordered by name |
| `GET /api/v1/restaurants?min_lat=41.14&max_lat=41.15&min_lon=-8.62&max_lon=-8.60` | Restaurants inside the visible map area |
| `GET /api/v1/restaurants/{restaurant_id}` | Restaurant details (e.g. `n4813682932`) |
| `GET /health/live`, `GET /health/ready` | Liveness and database readiness |

Restaurant lists accept `cuisine` and `limit`. Use the response's `next_cursor` as `cursor` to fetch the next page. `city_id` is the GeoNames id; `restaurant_id` is the OpenStreetMap id (`n` node, `w` way, `r` relation).

## Running the web app

With the database loaded and the API running (`uv run foodie-api`):

```sh
cd frontend
npm install                      # once
npm run dev                      # http://localhost:5173
```

Pick a city (search also accepts local names such as *Lisboa* or *Oporto*) or use a quick pick. The map loads the traditional restaurants inside the visible area and clusters them; pan or zoom to load more. Filter by cuisine, click a marker or a card for details, opening hours, website and directions. The address bar keeps the city and restaurant, so links can be shared.

The dev server proxies `/api` to the API. Optional settings are in `frontend/.env.example`; the default map tiles are OpenStreetMap's standard tiles, which are meant for development, not heavy public traffic.

Frontend checks: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.

## Tests and linting

```sh
uv run ruff format .
uv run ruff check .
uv run pytest -q                 # unit tests; integration tests are skipped
```

Integration tests run against a temporary database that they create on the Compose PostGIS server and drop afterwards:

```sh
set -a; . ./.env; set +a
TEST_DATABASE_URL="postgresql+psycopg://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/postgres" uv run pytest -q
```

## Repository layout

| Path | Purpose |
|---|---|
| `packages/foodie_common/` | Shared settings (`DATABASE_URL`), SQLAlchemy engine factory, JSON logging |
| `collector/` | `foodie-collect` ingestion jobs (OpenStreetMap, GeoNames) and the Google Places lab module |
| `db/init/` | Bootstrap SQL: PostGIS, `pg_trgm`, the `raw`/`core`/`mart` schemas and the raw landing tables |
| `transformations/dbt/` | dbt project: `raw` → `staging` → `core` → `mart` models and tests |
| `api/` | `foodie-api`: read-only FastAPI service over the `mart` schema |
| `frontend/` | React + TypeScript + Leaflet web app (Vite) |
| `compose.yaml` | Development database |

## Google Places lab

`foodie_collector.sources.google_places_lab` is an isolated experiment and never writes to the database. Google's terms restrict storing Places content, so the application's restaurant data comes from OpenStreetMap instead.

Planned use of Google in the app: store only the Google place ID linked to each OpenStreetMap restaurant, and have the API fetch the Google rating live at display time (shown with Google attribution, never stored). Which restaurants are collected is always decided by OpenStreetMap data.

To use the lab, put a service-account key under `secrets/` (gitignored) and set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.

## Data attribution

- Restaurant data © OpenStreetMap contributors, ODbL.
- City data © GeoNames, CC BY 4.0.
