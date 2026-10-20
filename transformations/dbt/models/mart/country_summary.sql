-- Countries with at least one restaurant: feeds the country selector.
select
    country_code,
    max(country_name) as country_name,
    count(*) as city_count,
    sum(restaurant_count) as restaurant_count
from {{ ref('city_summary') }}
group by country_code
