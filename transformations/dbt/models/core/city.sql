{{ config(indexes=[{'columns': ['country_code']}]) }}

-- GeoNames cities (identified by geonameid, never by name alone).
select
    city_id,
    name,
    asciiname,
    alternatenames,
    country_code,
    admin1_code,
    feature_code,
    population,
    timezone,
    latitude,
    longitude
from {{ ref('stg_geonames_cities') }}
