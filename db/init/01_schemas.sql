-- raw:  landing tables written by the collector (bootstrap DDL lives in db/init).
-- core: cleaned, deduplicated models built by dbt.
-- mart: application-ready models built by dbt and read by the API.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;
