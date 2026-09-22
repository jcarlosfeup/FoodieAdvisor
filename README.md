## Current runtime

Run the app with `streamlit run main.py` after setting `DATABASE_URL` to PostgreSQL.

- Cached flow: a city with local restaurants, such as Porto, reads PostgreSQL and does
	not call Google Places. Porto currently returns 60 rows.
- Uncached flow: a city with no local restaurants reads no rows, then calls Google
	Places, transforms the response, stores it, and reads the stored rows back. A
	missing `GOOGLE_APPLICATION_CREDENTIALS` now fails only when this flow is used.

## Configuration

Configuration is loaded by `config.py` from environment variables. `DATABASE_URL`
is required and must be a PostgreSQL URL. Set it along with
`GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_PLACES_BASE_URL`,
`GOOGLE_FIELD_MASK`, `GOOGLE_MIN_RATING`, `GOOGLE_PAGINATION_DELAY_SECONDS`,
`REQUEST_TIMEOUT_SECONDS`, `CITIES_CSV_PATH`, `RESTAURANTS_CSV_PATH`, and
application path variables as needed.

## PostgreSQL setup and seed data

Apply `migrations/001_initial.sql` to a PostgreSQL database, then run:

```sh
python -m scripts.import_seed_data
```

The repeatable import seeds the deduplicated city catalog from `world_cities.csv`
and all 54 legacy restaurant rows from `restaurants.csv` with `source = 'csv'`.
API-collected rows are not seed data because the CSV has no stable Google place IDs.

Install dependencies with `python -m pip install -e '.[test]'` or add the PostgreSQL
extra with `python -m pip install -e '.[postgres,test]'`.

## Local containers

Docker Compose creates both the PostgreSQL container and the Streamlit container:

```sh
cp .env.example .env
# Edit .env, especially POSTGRES_PASSWORD.
docker compose up --build
```

Open `http://localhost:8501`. PostgreSQL is available from the host at
`localhost:5432`, but the app must use the service name `postgres` in its internal
URL. The migration is mounted into PostgreSQL's initialization directory, so it is
executed automatically when the `postgres_data` volume is created for the first time.

To seed the database from a one-off app container:

```sh
docker compose run --rm app python -m scripts.import_seed_data
```

To connect directly to the database container:

```sh
docker compose exec postgres psql -U foodie_advisor -d foodie_advisor
```

The active Streamlit and Google collection paths use the PostgreSQL repository
selected by `DATABASE_URL`. `docker compose down`
preserves data; `docker compose down -v` deletes the database volume and causes
initialization SQL to run again on the next startup.

If Docker reports `docker-credential-desktop.exe: exec format error` while pulling
an image on Linux, Docker is using a Windows credential helper. Back up
`~/.docker/config.json`, remove the `credsStore` entry, and retry the build. Docker
can pull public images without that helper; authenticate later with `docker login`
if you need private images.

