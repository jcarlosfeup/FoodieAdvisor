{{ config(
    indexes=[{'columns': ['country_code']}],
    post_hook="create index if not exists {{ this.name }}_search_trgm on {{ this }} using gin (search_text gin_trgm_ops)",
) }}

-- Cities that have at least one restaurant: feeds the city dropdown/autocomplete. The extent
-- columns let the map fit all restaurants of a city.
select
    city.city_id,
    city.name,
    city.asciiname,
    city.country_code,
    country.country_name,
    city.name || ', ' || coalesce(country.country_name, city.country_code) as label,
    -- Name, ASCII name and GeoNames alternate names (e.g. "Lisboa", "Oporto") for autocomplete.
    lower(concat_ws(',', city.name, city.asciiname, city.alternatenames)) as search_text,
    city.population,
    city.latitude,
    city.longitude,
    count(*) as restaurant_count,
    min(restaurant.latitude) as min_latitude,
    max(restaurant.latitude) as max_latitude,
    min(restaurant.longitude) as min_longitude,
    max(restaurant.longitude) as max_longitude
from {{ ref('restaurant') }} as restaurant
join {{ ref('city') }} as city using (city_id)
left join {{ ref('country') }} as country using (country_code)
group by
    city.city_id, city.name, city.asciiname, city.alternatenames, city.country_code, country.country_name,
    city.population, city.latitude, city.longitude
