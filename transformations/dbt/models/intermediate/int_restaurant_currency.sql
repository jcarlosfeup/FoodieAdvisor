-- A restaurant is current when it lies inside at least one city's latest collection box and
-- every such latest run saw it. Restaurants that disappeared from OSM, stopped matching the
-- traditional filter, or came from older unfiltered runs are therefore not current.
-- Box containment uses plain coordinates (boxes never cross the antimeridian at city scale).
with restaurants as (
    select restaurant_id, latitude, longitude, last_seen_at from {{ ref('stg_osm_restaurants') }}
),

covering_runs as (
    select
        restaurants.restaurant_id,
        restaurants.last_seen_at >= runs.started_at as seen_by_run
    from restaurants
    join {{ ref('stg_osm_collection_runs') }} as runs
        on restaurants.latitude between runs.bbox_south and runs.bbox_north
        and restaurants.longitude between runs.bbox_west and runs.bbox_east
)

select
    restaurants.restaurant_id,
    coalesce(bool_and(covering_runs.seen_by_run), false) as is_current,
    count(covering_runs.restaurant_id) as covering_run_count
from restaurants
left join covering_runs using (restaurant_id)
group by restaurants.restaurant_id
