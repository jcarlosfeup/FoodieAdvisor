select
    country_code,
    iso_alpha3,
    country_name,
    capital,
    continent,
    population
from {{ ref('stg_geonames_countries') }}
