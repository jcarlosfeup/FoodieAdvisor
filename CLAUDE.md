# FoodieAdvisor Repository Memory

## Purpose

FoodieAdvisor is a small cloud-native data platform with a restaurant discovery web application on top of it. Users pick a city and explore its **traditional** restaurants (the cuisine of the city's own country) on an interactive map.

- **Data:** OpenStreetMap (Overpass) restaurants and GeoNames cities flow through PostgreSQL/PostGIS in three layers: `raw` (landing), `core` (cleaned) and `mart` (application-ready).
- **Application:** a read-only FastAPI backend and a React + TypeScript + Leaflet frontend.
- **Operations:** Docker Compose locally, then local Kubernetes (k3d), GitHub Actions CI/CD and Prometheus/Grafana.

The project is being built in eight phases, one at a time, with a review after each:

1. Environment
2. Ingestion
3. dbt
4. API
5. Frontend
6. Compose
7. k3d
8. CI/CD and observability

**Phases 1–5 are done** (foundation, ingestion into `raw`, dbt `core`/`mart`, FastAPI, React frontend). Next: Phase 6 (full Docker Compose stack). The Google place-ID linking job and the live-rating endpoint are still pending.

The Streamlit app, the SQLite database and the Google-centred `cities`/`restaurants` schema have been removed. Do not reintroduce them.

## Data source rules (non-negotiable)

- **Only traditional restaurants are collected.** The Overpass query is filtered per country by `foodie_collector/traditional.py`: a restaurant qualifies when its `cuisine` list contains the national cuisine (e.g. `portuguese`, `francesinha` for PT) or `regional`/`local`, or its `name` contains a traditional-eatery keyword (e.g. tasca, taberna, adega). Countries without a rule fail explicitly; add a `TraditionalRule` plus a test to support one. The rule used is stored in `raw.ingestion_runs.parameters.traditional_rule`.
- **Google Places: place IDs plus live ratings only.** The decided design:
  - Store only the Google place ID linked to an OSM restaurant (place IDs are exempt from Google's caching limits). Matching may use Google's name/location transiently, but they are never stored.
  - The API fetches ratings live by place ID at display time, shows them with Google attribution, and never persists them.
  - Google content (names, ratings, reviews, locations, or anything derived from them, such as "Google says this is traditional" or "rated above 4") must never decide which records are stored or enter `raw`, `core` or `mart`. Selection stays OSM-based.
  - `google_places_lab.py` remains the experiment module and never writes to the database. The place-ID linking job and the live-rating endpoint are not built yet (see Planned additions).
- **OpenStreetMap** (ODbL) is the restaurant source. Show the attribution "© OpenStreetMap contributors" wherever its data or tiles are displayed.
- **GeoNames** (`cities5000`, CC BY 4.0) is the city catalog. It needs attribution. Cities are identified by `geonameid`, never by name alone ("Porto, PT" ≠ "Porto, BR").
- **Ratings** come only from independently sourced reviews. Never present a calculated score as a Google rating. Any synthetic review data must be flagged `is_synthetic`.
- **Public Overpass service:** use it only for modest, controlled requests, with a timeout, backoff and a `User-Agent`.

## Repository layout

```
pyproject.toml              uv workspace root (virtual, package = false): dev group, ruff, pytest config
uv.lock                     single lockfile for the workspace — commit it
.python-version             3.12
packages/foodie_common/     shared library
  settings.py               DatabaseSettings (pydantic-settings): DATABASE_URL required, PostgreSQL-only
  db.py                     make_engine(): pooled SQLAlchemy engine, normalises postgresql:// to psycopg
  logging.py                JsonFormatter / configure_logging(): structured JSON logs; pass extras via `extra=`
  testing.py                temporary_database(): isolated PostGIS DB for integration tests
collector/                  foodie_collector: ingestion jobs (CLI `foodie-collect`)
  settings.py               CollectorSettings (DATABASE_URL + Overpass/GeoNames/HTTP), GooglePlacesLabSettings
  models.py                 BoundingBox.around(), CityTarget, Rejection, ParseResult
  traditional.py            TraditionalRule per country (cuisines + name keywords), traditional_rule()
  http.py                   build_client(), request_with_retries(): backoff on transport errors/429/5xx, Retry-After
  sources/openstreetmap.py  OverpassClient, build_restaurant_query(bbox, timeout, rule), parse_elements()
  sources/geonames.py       GeoNamesDownloader (cache in data/geonames), parse_cities(), parse_countries()
  sources/google_places_lab.py  GooglePlacesClient, transform_places(), lab_search() — never persists
  ingestion/raw_loader.py   RawTable specs + load_records(): hash-based idempotent upsert, deduplicate()
  ingestion/runs.py         tracked_run() context manager -> raw.ingestion_runs; record_rejections()
  ingestion/targets.py      city_by_name(name, CC) / city_by_geonameid() from raw.geonames_cities
  ingestion/collect_*.py    collect_restaurants(), collect_countries(), collect_cities()
  cli.py                    `foodie-collect cities|restaurants`
  tests/                    unit tests (fakes, httpx.MockTransport) + integration tests (marker `integration`)
db/init/                    bootstrap SQL run by the Postgres entrypoint on first init only
  00_extensions.sql         postgis, pg_trgm
  01_schemas.sql            raw, core, mart
  02_raw_tables.sql         raw.ingestion_runs, rejected_records, geonames_countries/cities, osm_restaurants
transformations/dbt/        dbt project (dbt-postgres, dbt_utils); profiles.yml reads POSTGRES_* env vars
  models/staging/           views in schema `staging`: stg_osm_restaurants, stg_geonames_cities/countries,
                            stg_osm_collection_runs (latest successful traditional run per city + bbox_*)
  models/intermediate/      int_restaurant_currency (is_current), int_restaurant_city (nearest collected city),
                            int_restaurant_classified (ephemeral: exclusion_reason)
  models/core/              tables in `core`: country, city, restaurant (geom + GiST), restaurant_excluded
  models/mart/              tables in `mart`: restaurant_search (geom GiST, cuisines GIN), city_summary
                            (search_text trigram index), country_summary — the only schema the API reads
  tests/                    singular tests (e.g. staged = core + excluded reconciliation)
  macros/generate_schema_name.sql  uses schema names as-is (staging/core/mart), no dbt prefixing
api/                        foodie_api: read-only FastAPI app (CLI `foodie-api`, docs at /docs)
  settings.py               ApiHttpSettings (no DB: host, port, CORS, limits) + ApiSettings (adds DATABASE_URL)
  main.py                   create_app(settings=None, repository=None): lifespan builds engine + PostgresRepository
  repository.py             Repository protocol, PostgresRepository: parameterized SQL over mart only
  routers/                  health (/health/live, /health/ready), places (/api/v1/countries, /cities, /cities/{id}),
                            restaurants (/api/v1/restaurants, /restaurants/{id})
  schemas.py                Pydantic response models (public contract) + attribution strings
  tests/                    test_api.py (FakeRepository, no DB) + test_api_integration.py (raw -> dbt run -> API)
frontend/                   Vite + React 19 + TypeScript 6 + react-leaflet 5 + TanStack Query 5; npm, package-lock.json
  src/api/                  types.ts (mirrors api schemas.py), client.ts (fetch wrappers, cursor paging, ApiError)
  src/components/           LocationPicker (ARIA combobox), RestaurantMap (Leaflet + Supercluster clusters),
                            RestaurantList, RestaurantDetails, CuisineFilter
  src/lib/                  geo (snapBounds, isViewTooLarge), cuisine, clusters, links, urlState (?city=&restaurant=)
  src/App.tsx               state owner: city, selected restaurant, map view, cuisine filter
  vite.config.ts            dev proxy /api + /health -> VITE_API_PROXY_TARGET (default 127.0.0.1:8000); Vitest config
compose.yaml                `db` service only until Phase 6
.github/workflows/ci.yaml   job python: PostGIS service; uv sync --frozen, ruff, dbt deps, pytest (incl. integration),
                            apply db/init, dbt build on empty raw tables. job frontend: npm ci, lint, typecheck, test, build
```

Planned additions:

| Phase | Addition |
|---|---|
| pending | Google place-ID linking job (`raw.google_place_links`: OSM key → place ID only), exposed via core/mart, then `GET /api/v1/restaurants/{id}/google-rating` (live lookup, never persisted) |
| 7 | `infra/kubernetes/` |

Keep these boundaries:

- Source modules fetch and parse; loaders persist.
- The API reads `mart` only.
- The frontend never talks to the database.

## Database contract

- **Image:** `imresamu/postgis:17-3.5`. This is the multi-arch build of docker-postgis; the official `postgis/postgis` image is amd64-only and the development machine is Apple Silicon. Keep the image identical across Compose, CI and Kubernetes.
- **Schema ownership:**
  - `db/init/*.sql` owns extensions, schemas, raw landing tables, and any application-written tables such as future user reviews.
  - **dbt owns everything in `core` and `mart`.** Do not hand-write DDL for those schemas.
- **Init scripts run only when the data volume is empty.** For a change to `db/init` on an existing volume, either apply the SQL manually with `psql` or recreate the volume. Recreating the volume (`docker compose down -v`) deletes data, so only do it when that's intended.
- **Raw layer** (`db/init/02_raw_tables.sql`):
  - `raw.ingestion_runs`: one row per run (UUID, source, target, `parameters` JSONB, status running/succeeded/failed, received/inserted/updated/unchanged/rejected counts, error). The run row is committed before data work, so failed runs stay visible.
  - `raw.rejected_records`: records that could not be landed (missing/invalid coordinates, bad rows, in-batch duplicates), with payload and reason.
  - `raw.geonames_countries` (PK `iso_alpha2`), `raw.geonames_cities` (PK `geonameid`, all GeoNames columns).
  - `raw.osm_restaurants`: PK `(osm_type, osm_id)`, lat/lon (node coords or way/relation `center`), all OSM `tags` as JSONB. Only traditional restaurants are fetched; rows from older, unfiltered runs or from earlier rule versions stop being "last seen", so dbt should only use rows seen by the latest successful run per city. No city column: restaurants can fall inside several cities' boxes (Porto and Gaia overlap heavily), so city assignment belongs to dbt.
  - Metadata on every data table: `_payload_hash`, `_run_id` (last change), `_first_loaded_at`, `_loaded_at`, `_last_seen_run_id`, `_last_seen_at` (use these to detect records that vanished from the source).
- **Ingestion is idempotent.** `load_records()` hashes each record's data columns, reads stored hashes, inserts new keys, updates changed ones and only touches `_last_seen_*` for unchanged ones. A rerun reports `inserted = updated = 0`. Keep that property for any new raw table by declaring a `RawTable` spec.
- **Raw stays close to the source.** Only reject records that cannot be stored (no coordinates or identity). Unnamed restaurants, odd tags, etc. are cleaned in dbt.
- **Adding a raw table:** add DDL to `db/init/` (new numbered file once shared environments exist), add a `RawTable` spec, then apply the SQL to existing volumes: `docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB' < db/init/NN_file.sql`.
- **dbt layer** (`transformations/dbt`):
  - `restaurant_id` is OSM's short id (`n123`, `w456`, `r789`), stable and URL-safe. `city_id` is the GeoNames geonameid.
  - A restaurant is **current** when it lies inside at least one city's latest successful *traditional-filtered* run box and every such latest run saw it (`_last_seen_at >= started_at`). Runs without `parameters.traditional_rule` (pre-filter) are ignored, so stale or unfiltered raw rows drop out without deleting raw data.
  - **City assignment:** nearest centre among the *collected* cities whose latest run box contains the restaurant. Do not use nearest-of-all-GeoNames-places: GeoNames lists neighbourhoods (Lisbon's Bairro Alto, Baixa...) as separate PPL places and would scatter cities. Real municipality boundaries are a possible later improvement.
  - `core.restaurant_excluded` holds every staged restaurant not in core, with `exclusion_reason` (`not_current`, `missing_name`, `no_collected_city`); `tests/assert_restaurant_counts_reconcile.sql` checks staged = core + excluded.
  - `core.restaurant.source` is tested to be `openstreetmap` only. No ratings are stored anywhere; `restaurant_score` / reviews are deferred until an independent review source exists.
  - **dbt unit-test limitation:** dbt-postgres casts unit-test values using `information_schema` type names, which are `ARRAY` and `USER-DEFINED` for arrays and PostGIS types and fail. Keep staging, intermediate and `core.city` free of array/geometry columns (use lat/lon and `;`-joined text, build geometry inside the logic); geometry/array columns exist only in `core.restaurant` and mart.
- **API contract** (`api/`):
  - Reads `mart` only, read-only, GET only. `restaurant_id` is the OSM short id (`^[nwr][0-9]+$`), `city_id` the geonameid.
  - `GET /api/v1/restaurants` needs `city_id` and/or a full bbox (`min_lat,max_lat,min_lon,max_lon`; each side ≤ `API_MAX_BBOX_SPAN_DEGREES`). Optional `cuisine` (GIN `@>`), `limit` (capped at `API_MAX_LIMIT`) and an opaque keyset `cursor` over `(name, restaurant_id)`; responses carry `next_cursor` and an OSM `attribution`.
  - City search uses `mart.city_summary.search_text` (name + ASCII + GeoNames alternate names, trigram index) with `LIKE` wildcards escaped.
  - `/health/live` never touches the DB; `/health/ready` returns 503 unless `mart.restaurant_search` exists.
  - Importing `foodie_api.main` must not need `DATABASE_URL` (CORS comes from `ApiHttpSettings`); settings and engine are created in the lifespan, or injected via `create_app(settings, repository)` in tests.
- **Frontend** (`frontend/`):
  - Talks only to the API, through same-origin relative URLs (`/api/...`): the Vite dev server proxies them, and nginx will in Phase 6. `VITE_API_BASE_URL` overrides the base.
  - Restaurants are loaded for the **visible map box** (snapped outwards to a ~0.001° grid so small pans reuse the TanStack Query cache), following `next_cursor` up to `MAX_RESTAURANTS_PER_VIEW` (2000). Views larger than 2° per side (`MAX_SPAN_DEGREES`, must match `API_MAX_BBOX_SPAN_DEGREES`) are not queried.
  - Cuisine filtering is client-side over the loaded view (chips show counts). No rating filter or rating display exists: "Not rated yet" until the Google live-rating endpoint is built.
  - Map tiles: OSM standard tiles by default (dev only), overridable via `VITE_TILE_URL`/`VITE_TILE_ATTRIBUTION`. Always keep "© OpenStreetMap contributors" (tiles, footer and details panel) and the GeoNames credit (footer).
  - Map view state lives in `App` (single source of truth). `ViewWatcher` attaches its `moveend` listener **once** with a ref'd callback: re-subscribing per render (react-leaflet `useMapEvents` with an inline object) misses the synchronous `moveend` fired by `fitBounds` in a sibling effect. That caused all of Lisbon to show as one cluster.
  - The selected restaurant is excluded from clustering and drawn on its own. Selection and city are mirrored to the URL (`?city=&restaurant=`) for shareable links.
  - Only `http(s)` websites are rendered as links (`safeWebsite`); directions use a plain Google Maps directions URL (a link, no Google data is fetched).
- Use SQLAlchemy with parameterized SQL (`text()` plus bind params). Never interpolate user or API data into SQL. Only fixed SQL fragments may be composed (as in `PostgresRepository`).
- Wrap related writes in `engine.begin()`.

## Configuration

- **`.env`** is gitignored, and `.env.example` documents every variable.
- **Settings classes** are pydantic-settings classes that read the environment and `.env`. They fail explicitly when a required value is missing.
- **Required for any database access:** `DATABASE_URL`.
  - On the host it is `postgresql+psycopg://foodie:<pw>@localhost:5432/foodie`.
  - Inside Compose the host is `db`, never `localhost`.
- **Compose:** `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (required; there is no default) and `POSTGRES_PORT`. The port is bound to `127.0.0.1`.
- **Collector** (`CollectorSettings`, all optional with defaults in `.env.example`): `DATA_DIR`, `OVERPASS_URL`, `OVERPASS_QUERY_TIMEOUT_SECONDS`, `OVERPASS_REQUEST_DELAY_SECONDS`, `DEFAULT_RADIUS_KM`, `GEONAMES_BASE_URL`, `GEONAMES_CITIES_FILE`, `HTTP_USER_AGENT`, `HTTP_TIMEOUT_SECONDS`, `HTTP_MAX_ATTEMPTS`, `HTTP_BACKOFF_SECONDS`.
- **API** (`ApiHttpSettings`/`ApiSettings`, defaults in `.env.example`): `API_HOST`, `API_PORT`, `API_CORS_ORIGINS` (JSON list), `API_DEFAULT_LIMIT`, `API_MAX_LIMIT`, `API_MAX_BBOX_SPAN_DEGREES`.
- **Tests:** `TEST_DATABASE_URL` points at a disposable server's maintenance DB (e.g. `.../postgres`); integration tests skip without it.
- **Google lab (optional):**
  - `GOOGLE_APPLICATION_CREDENTIALS`, which should point inside `secrets/`;
  - `GOOGLE_PLACES_BASE_URL`, `GOOGLE_FIELD_MASK`, `GOOGLE_MIN_RATING`, `GOOGLE_PAGINATION_DELAY_SECONDS` and `REQUEST_TIMEOUT_SECONDS`.

## Secrets

- **Never commit** credentials, `.env`, or service-account JSON. They belong in `secrets/`, which is gitignored, or in environment variables.
- **`.gitignore` doesn't ignore `*.json`,** so that `package.json` and `tsconfig.json` can be committed. Credential files are covered by explicit patterns: `secrets/`, `*service-account*.json` and `foodie-advisor-*.json`. Check `git status` before committing any JSON file.
- **Old keys are in git history.** Commit `1878a15` removed keys that had been committed earlier, so they remain in history. The keys are being rotated in GCP. Purging history would mean `git filter-repo` plus a force-push, and that needs explicit approval from the user.
- **Never bake credentials into images.** Mount them read-only (Compose) or use Secrets (Kubernetes).

## Development commands (macOS)

```sh
brew install uv                 # once
uv sync                         # creates .venv with all workspace members + dev tools
uv run ruff check .             # lint (add --fix for import sorting)
uv run pytest -q                # all tests (importlib mode, multiple tests/ dirs)
uv run pytest collector/tests -q

cp .env.example .env            # then set POSTGRES_PASSWORD and the matching DATABASE_URL
docker compose up -d db
docker compose ps
docker compose exec db sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB'
docker compose down             # keeps data (volume `pgdata`)

uv run ruff format .            # formatter (CI runs `ruff format --check`)

# Ingestion (needs DATABASE_URL; run cities first, restaurants resolve targets from it)
uv run foodie-collect cities                    # GeoNames countries + cities5000 (cached in data/geonames)
uv run foodie-collect restaurants --city "Porto,PT" --city "Vila Nova de Gaia,PT" --city "Lisbon,PT"
uv run foodie-collect restaurants --geonameid 2735943 --radius-km 3

# dbt (reads POSTGRES_* from .env; run after collecting)
uv run --env-file .env dbt deps  --project-dir transformations/dbt --profiles-dir transformations/dbt   # once
uv run --env-file .env dbt build --project-dir transformations/dbt --profiles-dir transformations/dbt   # models + tests
uv run --env-file .env dbt build --project-dir transformations/dbt --profiles-dir transformations/dbt --select +restaurant_search
uv run --env-file .env dbt source freshness --project-dir transformations/dbt --profiles-dir transformations/dbt

# API (reads .env; Swagger UI at http://127.0.0.1:8000/docs)
uv run foodie-api

# Frontend (Node >= 22; needs the API running for real data)
cd frontend && npm install        # once
npm run dev                       # http://localhost:5173 (proxies /api to 127.0.0.1:8000)
npm run lint && npm run typecheck && npm test && npm run build

# Integration tests: throwaway DB on the Compose server, dropped afterwards
set -a; . ./.env; set +a
TEST_DATABASE_URL="postgresql+psycopg://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$POSTGRES_PORT/postgres" uv run pytest -q
```

**Adding dependencies:**
- To a member: `uv add --package foodie-collector <pkg>`.
- Dev tools: `uv add --dev <pkg>`.
- Always commit `uv.lock`.

## Testing guidance

- **No real network calls or external services in unit tests.** Use fake sessions and clients, as `collector/tests/test_google_places_lab.py` does with `FakeSession` and `FakeCredentials`. `GooglePlacesClient` accepts injected `session` and `credentials` for this.
- **Settings tests** pass `_env_file=None` and set the environment with `monkeypatch`, so a developer's local `.env` can't leak into them.
- **SQL behaviour** (ON CONFLICT, PostGIS, FKs) is tested against an isolated PostGIS database, never a shared or production one. Use the `pg_engine` fixture (`collector/tests/conftest.py`), built on `foodie_common.testing.temporary_database()`: it creates a uniquely named database, applies `db/init/*.sql`, truncates raw tables between tests and drops the database at the end. Mark such modules `pytestmark = pytest.mark.integration`.
- **API:** unit tests use `create_app(settings, FakeRepository())` with `fastapi.testclient.TestClient` (needs the `httpx2` dev dependency). The end-to-end fixture `mart_database_url` (`api/tests/conftest.py`) inserts raw rows into a temporary database and runs the real `dbt run` in a subprocess, so API tests exercise the actual models; it runs `dbt deps` if `dbt_packages/` is missing.
- **Frontend:** Vitest + Testing Library in jsdom. Stub `fetch` with `mockApi()` from `src/test/utils.tsx`; never call the real API. Leaflet cannot render in jsdom, so `App.test.tsx` mocks `RestaurantMap` with a stub that exposes `onViewChange`/`onSelect`. Keep map logic in pure functions under `src/lib/` so it can be unit-tested. Check visual changes with headless Chrome screenshots (minimum headless width is 500 px).
- **HTTP sources** are tested with `httpx.MockTransport` and an injected `sleep` (no real waits); see `collector/tests/test_openstreetmap.py`.
- **dbt:** every model gets `unique`/`not_null` keys and relationship tests in its `_*.yml`; logic with edge cases gets a dbt unit test (see `_intermediate.yml`). `dbt build` must also pass on empty raw tables, as CI runs it that way.
- **Ingestion and dbt changes:**
  - test idempotency: a second run inserts 0 rows;
  - test missing and malformed source fields;
  - test rejected-record accounting.

## Design rules

- Prefer the source/loader/service boundaries over putting logic in CLIs or route handlers.
- Keep HTTP clients free of persistence and transformation, and keep timeouts and field masks configuration-driven.
- Keep each phase's scope tight: build a working slice before adding technology. No Spark, Kafka, Airflow, Redis or microservices without a demonstrated need.
- Use pinned image tags, never `latest`, in Compose and Kubernetes.
- Don't commit generated files: `.venv`, caches, `data/`, dbt `target/`, `node_modules/`, `dist/`. Do commit `frontend/package-lock.json`.
- Frontend dependency pins: TypeScript stays on `~6.0` until typescript-eslint supports TS 7. `supercluster` ships its own types (do not add `@types/supercluster`). The `fsevents` install script is left unapproved (optional macOS watcher with prebuilt binaries).

## Change checklist

1. Read the affected module and its tests, plus `db/init/*.sql` for persistence changes.
2. Check the data-source rules above, especially that no Google content reaches the database.
3. Add or update a focused test.
4. Run `uv run ruff format .`, `uv run ruff check .` and `uv run pytest -q` (with `TEST_DATABASE_URL` for SQL changes), and `dbt build` for raw-schema or model changes.
5. If `db/init` or `compose.yaml` changed, run `docker compose config`, and remember that init SQL doesn't rerun on an existing volume.
6. Update this file and `README.md` when the architecture or commands change.
