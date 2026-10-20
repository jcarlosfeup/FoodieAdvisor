-- Assign each restaurant to the nearest centre among the collected cities whose latest search
-- box contains it. Only collected cities are candidates: GeoNames lists many neighbourhoods
-- (e.g. Lisbon's Bairro Alto, Baixa) as separate places, and GeoNames has points, not
-- boundaries, so a nearest-of-all-places rule would scatter a city across its neighbourhoods.
with candidates as (
    select
        restaurants.restaurant_id,
        runs.city_id,
        st_distance(
            st_setsrid(st_makepoint(restaurants.longitude, restaurants.latitude), 4326)::geography,
            st_setsrid(st_makepoint(city.longitude, city.latitude), 4326)::geography
        ) as distance_to_city_centre_m
    from {{ ref('stg_osm_restaurants') }} as restaurants
    join {{ ref('stg_osm_collection_runs') }} as runs
        on restaurants.latitude between runs.bbox_south and runs.bbox_north
        and restaurants.longitude between runs.bbox_west and runs.bbox_east
    join {{ ref('city') }} as city
        on city.city_id = runs.city_id
)

select distinct on (restaurant_id)
    restaurant_id,
    city_id,
    distance_to_city_centre_m
from candidates
order by restaurant_id, distance_to_city_centre_m, city_id
