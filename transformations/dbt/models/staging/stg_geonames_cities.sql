with source as (
    select * from {{ source('raw', 'geonames_cities') }}
)

select
    geonameid as city_id,
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
from source
