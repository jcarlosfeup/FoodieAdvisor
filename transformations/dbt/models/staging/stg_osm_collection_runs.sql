-- Latest successful traditional-restaurant collection per GeoNames city, with its search box.
-- Runs from before the traditional filter (no traditional_rule parameter) are ignored, so their
-- unfiltered restaurants are not treated as current.
with runs as (
    select * from {{ source('raw', 'ingestion_runs') }}
    where source = 'osm_overpass'
      and status = 'succeeded'
      and parameters ? 'traditional_rule'
)

select distinct on ((parameters ->> 'geonameid')::bigint)
    run_id,
    (parameters ->> 'geonameid')::bigint as city_id,
    target,
    started_at,
    (parameters -> 'bbox' ->> 'south')::float as bbox_south,
    (parameters -> 'bbox' ->> 'west')::float as bbox_west,
    (parameters -> 'bbox' ->> 'north')::float as bbox_north,
    (parameters -> 'bbox' ->> 'east')::float as bbox_east
from runs
order by (parameters ->> 'geonameid')::bigint, started_at desc
