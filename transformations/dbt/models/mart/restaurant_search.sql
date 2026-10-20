{{ config(indexes=[
    {'columns': ['geom'], 'type': 'gist'},
    {'columns': ['city_id']},
    {'columns': ['cuisines'], 'type': 'gin'},
]) }}

-- One row per restaurant, flattened for the API (bbox and city queries, cuisine filters).
-- Ratings are not stored: Google ratings are fetched live by the API and never persisted.
select
    restaurant.restaurant_id,
    restaurant.name,
    restaurant.city_id,
    city.name as city_name,
    city.country_code,
    country.country_name,
    restaurant.cuisines,
    -- Only build an address when OSM has a street; a bare city name is not useful.
    case
        when restaurant.street is not null then concat_ws(
            ', ',
            concat_ws(' ', restaurant.street, restaurant.housenumber),
            nullif(concat_ws(' ', restaurant.postcode, coalesce(restaurant.address_city, city.name)), '')
        )
    end as address,
    restaurant.website,
    restaurant.phone,
    restaurant.opening_hours,
    restaurant.latitude,
    restaurant.longitude,
    restaurant.geom,
    'https://www.openstreetmap.org/' || restaurant.source_restaurant_id as osm_url,
    restaurant.last_seen_at
from {{ ref('restaurant') }} as restaurant
join {{ ref('city') }} as city using (city_id)
left join {{ ref('country') }} as country using (country_code)
