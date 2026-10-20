-- Every staged restaurant ends up exactly once in core.restaurant or core.restaurant_excluded.
select 'staged' as layer, count(*) from {{ ref('stg_osm_restaurants') }}
having count(*) <> (
    (select count(*) from {{ ref('restaurant') }}) + (select count(*) from {{ ref('restaurant_excluded') }})
)
