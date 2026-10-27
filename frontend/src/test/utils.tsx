import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";
import type { City, CityDetail, RestaurantDetail, RestaurantSummary } from "../api/types";

export function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

type Handler = (url: URL) => unknown;

/** Stub global fetch with JSON responses keyed by pathname. Returns the mock to inspect calls. */
export function mockApi(routes: Record<string, Handler | unknown>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), "http://localhost");
    const route = routes[url.pathname];
    if (route === undefined) return jsonResponse({ detail: `no mock for ${url.pathname}` }, 404);
    const body = typeof route === "function" ? (route as Handler)(url) : route;
    if (body instanceof Response) return body;
    return jsonResponse(body);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export const PORTO: City = {
  city_id: 2735943,
  name: "Porto",
  label: "Porto, Portugal",
  country_code: "PT",
  country_name: "Portugal",
  latitude: 41.1485,
  longitude: -8.611,
  restaurant_count: 214,
};

export const LISBON: City = {
  ...PORTO,
  city_id: 2267057,
  name: "Lisbon",
  label: "Lisbon, Portugal",
  latitude: 38.725,
  longitude: -9.15,
  restaurant_count: 597,
};

export const PORTO_DETAIL: CityDetail = {
  ...PORTO,
  population: 252687,
  restaurant_extent: { min_latitude: 41.1, min_longitude: -8.68, max_latitude: 41.19, max_longitude: -8.55 },
};

export function restaurant(id: string, name: string, cuisines: string[], address: string | null = null): RestaurantSummary {
  return { restaurant_id: id, name, city_id: PORTO.city_id, cuisines, address, latitude: 41.147, longitude: -8.61 };
}

export function restaurantDetail(summary: RestaurantSummary, extra: Partial<RestaurantDetail> = {}): RestaurantDetail {
  return {
    ...summary,
    city_name: "Porto",
    country_code: "PT",
    country_name: "Portugal",
    website: null,
    phone: null,
    opening_hours: null,
    osm_url: `https://www.openstreetmap.org/node/${summary.restaurant_id.slice(1)}`,
    last_seen_at: "2026-10-20T10:00:00Z",
    attribution: "Restaurant data © OpenStreetMap contributors, ODbL",
    ...extra,
  };
}
