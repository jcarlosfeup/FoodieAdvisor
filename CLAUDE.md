# FoodieAdvisor Repository Memory

## Purpose

FoodieAdvisor is a Streamlit restaurant discovery application. It displays restaurants for a selected city, reads cached restaurants from PostgreSQL, and queries Google Places only when the selected city has no stored restaurants.

The application is PostgreSQL-only. SQLite was the original implementation but has been removed from the active repository and should not be reintroduced unless the project direction explicitly changes.

## Runtime Architecture

- `main.py`
  - Streamlit entry point.
  - Creates a repository from `settings.database_url`.
  - Loads cities from PostgreSQL.
  - Reads cached restaurants first.
  - For a city with no restaurants, inserts the city if needed, calls Google Places, and reloads restaurants from PostgreSQL.
- `config.py`
  - Owns typed environment configuration.
  - `DATABASE_URL` is mandatory.
  - Only `postgresql://` and `postgresql+psycopg://` URLs are accepted.
  - Importing the module creates `settings`, so tests that import `config` must set `DATABASE_URL` first or deliberately test the failure behavior.
- `api/places_client.py`
  - Owns Google Places HTTP requests, authentication refresh, pagination, timeout, and field mask handling.
  - Must not persist data or transform response records.
- `api/transformer.py`
  - Converts Google Places response objects into application restaurant dictionaries.
  - Preserves `google_place_id` when Google provides `id`.
  - Skips records without a usable display name.
- `api/connect.py`
  - Compatibility facade around the Google client, transformer, and collection service.
  - Uses `create_repository(settings.database_url)`.
  - Do not add direct SQL or database-driver calls here.
- `services/collection.py`
  - Coordinates Google search, transformation, and repository persistence.
  - It expects a repository implementing `save_restaurants()`.
- `db/repositories.py`
  - Contains the PostgreSQL persistence boundary.
  - `PostgreSQLRepository` implements city lookup/insertion, city listing, restaurant listing, and restaurant upsert.
  - `create_repository()` accepts PostgreSQL URLs only.
- `scripts/import_seed_data.py`
  - Repeatable seed/import command for the CSV files.
- `migrations/001_initial.sql`
  - Initial PostgreSQL schema.
- `view/visualization.py`
  - Streamlit presentation and map visualization. Keep database/API concerns out of this module.

## Database Contract

The PostgreSQL schema consists of:

- `cities`: city metadata and a uniqueness constraint across name, country, ISO, latitude, and longitude.
- `restaurants`: restaurants linked to `cities`, with nullable stable `google_place_id`, ratings, coordinates, and source.
- `collection_jobs`: intended job tracking table with pending/running/succeeded/failed states. The current application does not yet create or update collection jobs.

Important invariants:

- Every restaurant must reference a city through `city_id`.
- A city must be inserted before Google restaurants are persisted for an uncached city.
- Google place IDs are the stable deduplication key when available.
- PostgreSQL uses the table names `cities` and `restaurants`; do not use the old SQLite singular table names `city` and `restaurant`.
- Use SQLAlchemy and parameterized SQL. Do not interpolate user or API data into SQL.
- Keep transactions around related writes. `engine.begin()` is the established pattern.

## Configuration

Required:

- `DATABASE_URL`: PostgreSQL URL, normally `postgresql+psycopg://user:password@host:5432/database`.

Google settings:

- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_PLACES_BASE_URL`
- `GOOGLE_FIELD_MASK`
- `GOOGLE_MIN_RATING`
- `GOOGLE_PAGINATION_DELAY_SECONDS`
- `REQUEST_TIMEOUT_SECONDS`

Paths:

- `CITIES_CSV_PATH`
- `RESTAURANTS_CSV_PATH`
- `APP_ROOT`

Never commit credentials or embed credential-file loading in Python modules. The current Compose file mounts the Google service-account JSON read-only at `/run/secrets/google_credentials.json`; treat that file as sensitive.

## Container Workflow

The intended local runtime is Docker Compose:

```sh
cp .env.example .env
# Set a non-default local POSTGRES_PASSWORD.
docker compose up --build
```

Services:

- `postgres`: `postgres:16-alpine`, persistent named volume `postgres_data`.
- `app`: Streamlit image built from `Dockerfile`.

Compose behavior:

- The app connects to hostname `postgres`, never `localhost`, because both services share the Compose network.
- PostgreSQL has a `pg_isready` health check.
- The app waits for the PostgreSQL health check through `depends_on`.
- `migrations/001_initial.sql` is mounted into `/docker-entrypoint-initdb.d/`.
- Initialization scripts run only when the PostgreSQL data directory is empty.
- `docker compose down` preserves data.
- `docker compose down -v` deletes the database volume and causes initialization SQL to run again.
- Seed after startup with:

```sh
docker compose run --rm app python -m scripts.import_seed_data
```

Useful commands:

```sh
docker compose config
docker compose ps
docker compose logs postgres
docker compose logs app
docker compose exec postgres psql -U foodie_advisor -d foodie_advisor
docker compose build app
docker compose up
```

If Docker on Linux reports `docker-credential-desktop.exe: exec format error`, inspect `~/.docker/config.json`. A Windows `credsStore` entry such as `desktop.exe` is invalid in Linux. Back up the file, remove that entry, and retry public-image pulls.

## Data and Seed Decisions

- `world_cities.csv` is the city catalog source. Import all records with deterministic deduplication based on the migration uniqueness fields.
- `restaurants.csv` contains 54 legacy Porto restaurant records. Import them with `source = 'csv'`.
- CSV restaurants do not have stable Google place IDs, so they are not treated as Google Places identity records.
- API-collected restaurants use Google place IDs when available and are upserted by that ID.
- Do not seed the checked-in historical database file; the application does not use it.

## Development Commands

Use the project virtual environment when working locally:

```sh
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pip install -e '.[postgres,test]'
python -m pytest -q
python -m compileall -q config.py api db services scripts tests main.py
```

The current verified test suite covers configuration, response transformation, and collection behavior. Run focused tests first when changing one area, then run the full suite.

## Testing Guidance

Tests should avoid real Google API calls and real production databases.

- Use fake clients for Google collection service tests.
- Use isolated PostgreSQL integration tests when testing SQL behavior that SQLite cannot model. The application SQL is PostgreSQL-specific.
- Test configuration with `DATABASE_URL` set before importing `config` when necessary.
- Test both cached and uncached city flows.
- Test stable Google place ID upserts and city foreign-key ordering.
- Test repeated seed imports for idempotency.
- Keep credentials, real API calls, and secrets out of tests.

## Design Rules

- Prefer the existing repository/service/client boundaries over adding logic to `main.py` or `api/connect.py`.
- Keep public function signatures stable unless a change is necessary.
- Use typed configuration and explicit failures for missing required settings.
- Preserve API response fields needed by persistence, especially `id`/`google_place_id`.
- Avoid broad refactors unrelated to the requested behavior.
- Do not reintroduce SQLite compatibility code, SQLite defaults, or old helper imports.
- Do not commit generated files such as `__pycache__`, `.pytest_cache`, editable-install metadata, local `.env`, credentials, or Docker build artifacts.
- Do not commit the Google service-account JSON file. If it is already tracked, treat that as a security issue and remove it from version control through the appropriate repository process.

## Known Gaps and Next Work

- `collection_jobs` exists in the schema but is not yet integrated into the collection service.
- There is no formal migration runner/version table; the current first migration relies on PostgreSQL container initialization.
- The seed importer uses SQLAlchemy and assumes the target schema has already been applied.
- PostgreSQL integration tests are still needed for repository SQL, especially `ON CONFLICT`, foreign keys, and repeatable imports.
- Google authentication currently uses a service-account credentials file. Prefer a secret manager or workload identity for production deployments.
- The container currently mounts the credential JSON from the host. This is acceptable only for local development.

## Change Checklist

Before changing persistence:

1. Read `migrations/001_initial.sql` and `db/repositories.py`.
2. Confirm whether the change affects city foreign keys, Google place ID uniqueness, or seed idempotency.
3. Add or update a focused test.
4. Run `python -m pytest -q`.
5. Run Python compilation checks.
6. If container behavior changes, run `docker compose config` and rebuild the affected image.

Before changing Google collection:

1. Read `api/places_client.py`, `api/transformer.py`, and `services/collection.py`.
2. Keep HTTP, transformation, and persistence responsibilities separate.
3. Test malformed/missing Google fields and pagination behavior without real network calls.
4. Verify the timeout and field mask remain configuration-driven.

Before changing container/database startup:

1. Check whether the PostgreSQL volume already exists; initialization SQL will not rerun automatically.
2. Prefer a new migration over editing an already-applied migration for shared environments.
3. Never delete `postgres_data` unless data loss is intended.
4. Verify the app URL uses `postgres` as the host inside Compose.
