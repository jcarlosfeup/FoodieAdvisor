-- One row per OSM restaurant feature with typed, renamed columns extracted from its tags.
with source as (
    select * from {{ source('raw', 'osm_restaurants') }}
)

select
    -- OSM's own short notation (n123, w456, r789): stable, URL-safe, readable.
    left(osm_type, 1) || osm_id::text as restaurant_id,
    osm_type,
    osm_id,
    nullif(btrim(tags ->> 'name'), '') as name,
    -- Normalised cuisine list as text ("portuguese;regional"): lower-cased, trimmed, de-duplicated,
    -- sorted. core.restaurant turns it into an array (text here keeps dbt unit tests simple).
    nullif(
        array_to_string(
            array(
                select distinct lower(btrim(value))
                from regexp_split_to_table(tags ->> 'cuisine', ';') as value
                where btrim(value) <> ''
                order by 1
            ),
            ';'
        ),
        ''
    ) as cuisine_list,
    nullif(btrim(tags ->> 'addr:street'), '') as street,
    nullif(btrim(tags ->> 'addr:housenumber'), '') as housenumber,
    nullif(btrim(tags ->> 'addr:postcode'), '') as postcode,
    nullif(btrim(tags ->> 'addr:city'), '') as address_city,
    case
        when nullif(btrim(coalesce(tags ->> 'website', tags ->> 'contact:website')), '') is null then null
        when coalesce(tags ->> 'website', tags ->> 'contact:website') ~* '^https?://'
            then btrim(coalesce(tags ->> 'website', tags ->> 'contact:website'))
        else 'https://' || btrim(coalesce(tags ->> 'website', tags ->> 'contact:website'))
    end as website,
    nullif(btrim(coalesce(tags ->> 'phone', tags ->> 'contact:phone')), '') as phone,
    nullif(btrim(tags ->> 'opening_hours'), '') as opening_hours,
    latitude,
    longitude,
    tags,
    _first_loaded_at as first_loaded_at,
    _loaded_at as loaded_at,
    _last_seen_at as last_seen_at
from source
