CREATE TABLE IF NOT EXISTS cities (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT,
    iso TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    population BIGINT,
    UNIQUE (name, country, iso, latitude, longitude)
);

CREATE TABLE IF NOT EXISTS restaurants (
    id BIGSERIAL PRIMARY KEY,
    google_place_id TEXT UNIQUE,
    city_id BIGINT NOT NULL REFERENCES cities(id),
    name TEXT NOT NULL,
    rating NUMERIC(2, 1),
    ratings_count INTEGER NOT NULL DEFAULT 0,
    price_level TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source TEXT NOT NULL DEFAULT 'google_places'
);

CREATE TABLE IF NOT EXISTS collection_jobs (
    id BIGSERIAL PRIMARY KEY,
    city_id BIGINT NOT NULL REFERENCES cities(id),
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    records_collected INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_cities_name ON cities(name);
CREATE INDEX IF NOT EXISTS idx_restaurants_city_id ON restaurants(city_id);
CREATE INDEX IF NOT EXISTS idx_collection_jobs_city_id ON collection_jobs(city_id);