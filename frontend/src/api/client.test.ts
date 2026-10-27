import { describe, expect, it } from "vitest";
import { jsonResponse, mockApi, restaurant } from "../test/utils";
import { ApiError, buildUrl, fetchCities, fetchRestaurant, fetchRestaurantsInBounds, shouldRetry } from "./client";

const BOUNDS = { min_latitude: 41.14, min_longitude: -8.62, max_latitude: 41.15, max_longitude: -8.6 };

describe("api client", () => {
  it("builds URLs without empty parameters", () => {
    expect(buildUrl("/api/v1/cities", { country: "PT", q: "", limit: 5, cursor: null })).toBe(
      "/api/v1/cities?country=PT&limit=5",
    );
  });

  it("searches cities with trimmed text", async () => {
    const fetchMock = mockApi({ "/api/v1/cities": { items: [], attribution: "" } });
    await fetchCities({ q: "  lisboa ", country: "PT" });
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/v1/cities?country=PT&q=lisboa&limit=20");
  });

  it("follows next_cursor across pages for a map view", async () => {
    const fetchMock = mockApi({
      "/api/v1/restaurants": (url: URL) =>
        url.searchParams.get("cursor")
          ? { items: [restaurant("n2", "B", [])], next_cursor: null, attribution: "" }
          : { items: [restaurant("n1", "A", [])], next_cursor: "page-2", attribution: "" },
    });

    const result = await fetchRestaurantsInBounds(BOUNDS);

    expect(result.restaurants.map((r) => r.restaurant_id)).toEqual(["n1", "n2"]);
    expect(result.truncated).toBe(false);
    const firstUrl = new URL(String(fetchMock.mock.calls[0]?.[0]), "http://localhost");
    expect(Object.fromEntries(firstUrl.searchParams)).toEqual({
      min_lat: "41.14",
      max_lat: "41.15",
      min_lon: "-8.62",
      max_lon: "-8.6",
      limit: "500",
    });
    expect(new URL(String(fetchMock.mock.calls[1]?.[0]), "http://localhost").searchParams.get("cursor")).toBe("page-2");
  });

  it("stops at the per-view cap and reports truncation", async () => {
    const fetchMock = mockApi({
      "/api/v1/restaurants": { items: [restaurant("n1", "A", []), restaurant("n2", "B", [])], next_cursor: "more", attribution: "" },
    });
    const result = await fetchRestaurantsInBounds(BOUNDS, undefined, 3);
    expect(result.restaurants).toHaveLength(3);
    expect(result.truncated).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("retries network and server errors once, never 4xx", () => {
    expect(shouldRetry(0, new ApiError(404, "not found"))).toBe(false);
    expect(shouldRetry(0, new ApiError(422, "invalid"))).toBe(false);
    expect(shouldRetry(0, new ApiError(503, "unavailable"))).toBe(true);
    expect(shouldRetry(0, new TypeError("Failed to fetch"))).toBe(true);
    expect(shouldRetry(1, new TypeError("Failed to fetch"))).toBe(false);
  });

  it("raises ApiError with the API's detail message", async () => {
    mockApi({ "/api/v1/restaurants/n9": jsonResponse({ detail: "restaurant n9 not found" }, 404) });
    const error = await fetchRestaurant("n9").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, message: "restaurant n9 not found" });
  });
});
