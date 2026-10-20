-- Restaurants landed in raw but kept out of core.restaurant, with the reason. Inspect this
-- table instead of silently losing records.
select
    restaurant_id,
    osm_type || '/' || osm_id as source_restaurant_id,
    exclusion_reason,
    name,
    city_id,
    round(distance_to_city_centre_m::numeric, 1) as distance_to_city_centre_m,
    latitude,
    longitude,
    last_seen_at,
    tags
from {{ ref('int_restaurant_classified') }}
where exclusion_reason is not null
