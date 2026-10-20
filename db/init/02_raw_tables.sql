-- Raw landing layer written by the collector. Records keep the source's natural key and
-- shape; cleaning and city assignment happen later in dbt (core/mart).
--
-- Metadata columns on every raw table:
--   _payload_hash      sha256 of the record's data columns; rows are only rewritten when it changes
--   _run_id            run that last inserted or changed the row
--   _first_loaded_at   when the row was first inserted
--   _loaded_at         when the row's payload last changed
--   _last_seen_run_id  latest run that received the record, changed or not
--   _last_seen_at      when that happened (detects records that disappeared from the source)

CREATE TABLE IF NOT EXISTS raw.ingestion_runs (
    run_id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    received_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_source_started
    ON raw.ingestion_runs (source, started_at DESC);

CREATE TABLE IF NOT EXISTS raw.rejected_records (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES raw.ingestion_runs (run_id),
    source TEXT NOT NULL,
    source_record_id TEXT,
    reason TEXT NOT NULL,
    payload JSONB,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rejected_records_run_id ON raw.rejected_records (run_id);

-- GeoNames countryInfo.txt
CREATE TABLE IF NOT EXISTS raw.geonames_countries (
    iso_alpha2 TEXT PRIMARY KEY,
    iso_alpha3 TEXT,
    iso_numeric TEXT,
    name TEXT NOT NULL,
    capital TEXT,
    area_sq_km DOUBLE PRECISION,
    population BIGINT,
    continent TEXT,
    languages TEXT,
    geonameid BIGINT,
    neighbours TEXT,
    _payload_hash TEXT NOT NULL,
    _run_id UUID NOT NULL REFERENCES raw.ingestion_runs (run_id),
    _first_loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _last_seen_run_id UUID NOT NULL REFERENCES raw.ingestion_runs (run_id),
    _last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- GeoNames cities5000.txt (cities with >5000 population). See https://www.geonames.org/export/
CREATE TABLE IF NOT EXISTS raw.geonames_cities (
    geonameid BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    asciiname TEXT,
    alternatenames TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    feature_class TEXT,
    feature_code TEXT,
    country_code TEXT,
    cc2 TEXT,
    admin1_code TEXT,
    admin2_code TEXT,
    admin3_code TEXT,
    admin4_code TEXT,
    population BIGINT,
    elevation INTEGER,
    dem INTEGER,
    timezone TEXT,
    modification_date DATE,
    _payload_hash TEXT NOT NULL,
    _run_id UUID NOT NULL REFERENCES raw.ingestion_runs (run_id),
    _first_loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _last_seen_run_id UUID NOT NULL REFERENCES raw.ingestion_runs (run_id),
    _last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_geonames_cities_country_name
    ON raw.geonames_cities (country_code, lower(name));

-- OpenStreetMap amenity=restaurant features from Overpass (ODbL). Ways and relations use
-- their Overpass `center` as coordinates
CREATE TABLE IF NOT EXISTS raw.osm_restaurants (
    osm_type TEXT NOT NULL CHECK (osm_type IN ('node', 'way', 'relation')),
    osm_id BIGINT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    _payload_hash TEXT NOT NULL,
    _run_id UUID NOT NULL REFERENCES raw.ingestion_runs (run_id),
    _first_loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    _last_seen_run_id UUID NOT NULL REFERENCES raw.ingestion_runs (run_id),
    _last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (osm_type, osm_id)
);
