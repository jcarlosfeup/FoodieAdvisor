import type {
  Bounds,
  City,
  CityDetail,
  Country,
  ListResponse,
  RestaurantDetail,
  RestaurantPage,
  RestaurantSummary,
} from "./types";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

/** Largest page the API accepts (API_MAX_LIMIT). */
export const PAGE_SIZE = 500;
/** Upper bound on restaurants loaded for one map view, to keep the browser responsive. */
export const MAX_RESTAURANTS_PER_VIEW = 2000;

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Retry policy for TanStack Query: one retry for network errors and 5xx responses, none for
 * 4xx. Asking again for an unknown city or restaurant cannot succeed.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 1;
}

type QueryValue = string | number | undefined | null;

export function buildUrl(path: string, params: Record<string, QueryValue> = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return `${BASE_URL}${path}${query ? `?${query}` : ""}`;
}

async function getJson<T>(path: string, params?: Record<string, QueryValue>, signal?: AbortSignal): Promise<T> {
  const response = await fetch(buildUrl(path, params), { signal, headers: { Accept: "application/json" } });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep statusText
    }
    throw new ApiError(response.status, detail || `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchCountries(signal?: AbortSignal): Promise<Country[]> {
  return (await getJson<ListResponse<Country>>("/api/v1/countries", undefined, signal)).items;
}

export async function fetchCities(
  options: { country?: string; q?: string; limit?: number },
  signal?: AbortSignal,
): Promise<City[]> {
  const params = { country: options.country, q: options.q?.trim(), limit: options.limit ?? 20 };
  return (await getJson<ListResponse<City>>("/api/v1/cities", params, signal)).items;
}

export function fetchCity(cityId: number, signal?: AbortSignal): Promise<CityDetail> {
  return getJson<CityDetail>(`/api/v1/cities/${cityId}`, undefined, signal);
}

export function fetchRestaurant(restaurantId: string, signal?: AbortSignal): Promise<RestaurantDetail> {
  return getJson<RestaurantDetail>(`/api/v1/restaurants/${encodeURIComponent(restaurantId)}`, undefined, signal);
}

export interface RestaurantsInView {
  restaurants: RestaurantSummary[];
  /** True when more restaurants exist in the view than MAX_RESTAURANTS_PER_VIEW. */
  truncated: boolean;
}

/** All restaurants inside a map box, following next_cursor until done or the per-view cap. */
export async function fetchRestaurantsInBounds(
  bounds: Bounds,
  signal?: AbortSignal,
  maxRestaurants = MAX_RESTAURANTS_PER_VIEW,
): Promise<RestaurantsInView> {
  const restaurants: RestaurantSummary[] = [];
  let cursor: string | null = null;
  do {
    const page: RestaurantPage = await getJson<RestaurantPage>(
      "/api/v1/restaurants",
      {
        min_lat: bounds.min_latitude,
        max_lat: bounds.max_latitude,
        min_lon: bounds.min_longitude,
        max_lon: bounds.max_longitude,
        limit: PAGE_SIZE,
        cursor,
      },
      signal,
    );
    restaurants.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor && restaurants.length < maxRestaurants);
  const truncated = cursor !== null || restaurants.length > maxRestaurants;
  return { restaurants: restaurants.slice(0, maxRestaurants), truncated };
}
