// Mirrors api/src/foodie_api/schemas.py (the public API contract).

export interface Country {
  country_code: string;
  country_name: string | null;
  city_count: number;
  restaurant_count: number;
}

export interface City {
  city_id: number;
  name: string;
  label: string;
  country_code: string;
  country_name: string | null;
  latitude: number;
  longitude: number;
  restaurant_count: number;
}

export interface Bounds {
  min_latitude: number;
  min_longitude: number;
  max_latitude: number;
  max_longitude: number;
}

export interface CityDetail extends City {
  population: number | null;
  restaurant_extent: Bounds;
}

export interface RestaurantSummary {
  restaurant_id: string;
  name: string;
  city_id: number;
  cuisines: string[];
  address: string | null;
  latitude: number;
  longitude: number;
}

export interface RestaurantDetail extends RestaurantSummary {
  city_name: string;
  country_code: string;
  country_name: string | null;
  website: string | null;
  phone: string | null;
  opening_hours: string | null;
  osm_url: string;
  last_seen_at: string;
  attribution: string;
}

export interface ListResponse<T> {
  items: T[];
  attribution: string;
}

export interface RestaurantPage extends ListResponse<RestaurantSummary> {
  next_cursor: string | null;
}
