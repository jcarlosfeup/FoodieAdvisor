with source as (
    select * from {{ source('raw', 'geonames_countries') }}
)

select
    iso_alpha2 as country_code,
    iso_alpha3,
    name as country_name,
    capital,
    continent,
    population
from source
