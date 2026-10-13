# FoodieAdvisor Repository Memory

## Purpose

FoodieAdvisor is a small cloud-native data platform with a restaurant discovery web application on top of it. Users pick a city and explore its restaurants on an interactive map.

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

**Phase 1 (foundation) is the current state.**

The Streamlit app, the SQLite database and the Google-centred `cities`/`restaurants` schema have been removed. Do not reintroduce them.

## Data source rules (non-negotiable)

- **Google Places is a lab only.** `collector/src/foodie_collector/sources/google_places_lab.py` may call Google and transform responses, but it never writes to the database. Google Places content (names, ratings, reviews, locations) must never enter the `raw`, `core` or `mart` schemas. Google's storage terms and EEA terms restrict persistent copies; only place IDs may be stored.
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
collector/                  foodie_collector: ingestion jobs
  settings.py               GooglePlacesLabSettings (no DATABASE_URL — the lab never persists)
  sources/google_places_lab.py  GooglePlacesClient, transform_places(), lab_search()
db/init/                    bootstrap SQL run by the Postgres entrypoint on first init only
  00_extensions.sql         postgis, pg_trgm
  01_schemas.sql            raw, core, mart
compose.yaml                Phase 1: `db` service only
.github/workflows/ci.yaml   uv sync --frozen, ruff, pytest
```

Planned additions:

| Phase | Addition |
|---|---|
| 2 | `collector/sources/{openstreetmap,geonames}.py`, `collector/ingestion/`, a `foodie-collect` CLI, and `db/init/02_raw_tables.sql` |
| 3 | `transformations/dbt/` |
| 4 | `api/`, a FastAPI workspace member: add it to `[tool.uv.workspace].members` and the root dev group |
| 5 | `frontend/` |
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
- **Planned raw layer (Phase 2):**
  - `raw.ingestion_runs` holds run_id, source, target, timestamps, status, received/inserted/updated/rejected counts, and error.
  - `raw.osm_restaurants` has PK `(osm_type, osm_id)`, plus `tags` JSONB and `_payload_hash`.
  - `raw.geonames_cities` has PK `geonameid`.
- **Ingestion must be idempotent.** Upsert on the natural key, and only update when the payload hash changes.
- Use SQLAlchemy with parameterized SQL (`text()` plus bind params). Never interpolate user or API data into SQL.
- Wrap related writes in `engine.begin()`.

## Configuration

- **`.env`** is gitignored, and `.env.example` documents every variable.
- **Settings classes** are pydantic-settings classes that read the environment and `.env`. They fail explicitly when a required value is missing.
- **Required for any database access:** `DATABASE_URL`.
  - On the host it is `postgresql+psycopg://foodie:<pw>@localhost:5432/foodie`.
  - Inside Compose the host is `db`, never `localhost`.
- **Compose:** `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (required; there is no default) and `POSTGRES_PORT`. The port is bound to `127.0.0.1`.
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
```

**Adding dependencies:**
- To a member: `uv add --package foodie-collector <pkg>`.
- Dev tools: `uv add --dev <pkg>`.
- Always commit `uv.lock`.

## Testing guidance

- **No real network calls or external services in unit tests.** Use fake sessions and clients, as `collector/tests/test_google_places_lab.py` does with `FakeSession` and `FakeCredentials`. `GooglePlacesClient` accepts injected `session` and `credentials` for this.
- **Settings tests** pass `_env_file=None` and set the environment with `monkeypatch`, so a developer's local `.env` can't leak into them.
- **SQL behaviour** (ON CONFLICT, PostGIS, FKs) is tested against an isolated PostGIS database, never a shared or production one. Plan for this from Phase 2.
- **Ingestion and dbt changes:**
  - test idempotency: a second run inserts 0 rows;
  - test missing and malformed source fields;
  - test rejected-record accounting.

## Design rules

- Prefer the source/loader/service boundaries over putting logic in CLIs or route handlers.
- Keep HTTP clients free of persistence and transformation, and keep timeouts and field masks configuration-driven.
- Keep each phase's scope tight: build a working slice before adding technology. No Spark, Kafka, Airflow, Redis or microservices without a demonstrated need.
- Use pinned image tags, never `latest`, in Compose and Kubernetes.
- Don't commit generated files: `.venv`, caches, `data/`, dbt `target/`, `node_modules/`, `dist/`.

## Change checklist

1. Read the affected module and its tests, plus `db/init/*.sql` for persistence changes.
2. Check the data-source rules above, especially that no Google content reaches the database.
3. Add or update a focused test.
4. Run `uv run ruff check .` and `uv run pytest -q`.
5. If `db/init` or `compose.yaml` changed, run `docker compose config`, and remember that init SQL doesn't rerun on an existing volume.
6. Update this file and `README.md` when the architecture or commands change.
