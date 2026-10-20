{{ config(materialized='ephemeral') }}

-- Every staged restaurant with the reason it is excluded from core.restaurant (null = kept).
select
    restaurants.*,
    city.city_id,
    city.distance_to_city_centre_m,
    case
        when not coalesce(currency.is_current, false) then 'not_current'
        when restaurants.name is null then 'missing_name'
        when city.city_id is null then 'no_collected_city'
    end as exclusion_reason
from {{ ref('stg_osm_restaurants') }} as restaurants
left join {{ ref('int_restaurant_currency') }} as currency using (restaurant_id)
left join {{ ref('int_restaurant_city') }} as city using (restaurant_id)
