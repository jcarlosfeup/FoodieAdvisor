{{ config(indexes=[
    {'columns': ['geom'], 'type': 'gist'},
    {'columns': ['city_id']},
]) }}

-- Clean, current, traditional restaurants assigned to a city. Source data © OpenStreetMap
-- contributors (ODbL). No Google content may ever be added here.
select
    restaurant_id,
    'openstreetmap' as source,
    osm_type || '/' || osm_id as source_restaurant_id,
    osm_type,
    osm_id,
    name,
    city_id,
    round(distance_to_city_centre_m::numeric, 1) as distance_to_city_centre_m,
    coalesce(string_to_array(cuisine_list, ';'), '{}'::text[]) as cuisines,
    street,
    housenumber,
    postcode,
    address_city,
    website,
    phone,
    opening_hours,
    latitude,
    longitude,
    st_setsrid(st_makepoint(longitude, latitude), 4326)::geometry(point, 4326) as geom,
    first_loaded_at,
    loaded_at,
    last_seen_at
from {{ ref('int_restaurant_classified') }}
where exclusion_reason is null
