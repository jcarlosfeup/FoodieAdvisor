import { describe, expect, it } from "vitest";
import { restaurant } from "../test/utils";
import { buildClusterIndex, visibleFeatures } from "./clusters";
import { countCuisines, filterByCuisines, formatCuisine } from "./cuisine";
import { containsPoint, isViewTooLarge, snapBounds } from "./geo";
import { directionsUrl, phoneHref, safeWebsite } from "./links";
import { readUrlState, writeUrlState } from "./urlState";

describe("geo", () => {
  const porto = { min_latitude: 41.1, min_longitude: -8.68, max_latitude: 41.19, max_longitude: -8.55 };

  it("flags views larger than the API's 2 degree limit", () => {
    expect(isViewTooLarge(porto)).toBe(false);
    expect(isViewTooLarge({ ...porto, max_longitude: -6.0 })).toBe(true);
  });

  it("snaps bounds outwards to a ~100 m grid so small pans reuse the cache", () => {
    const a = snapBounds({ min_latitude: 41.14012, min_longitude: -8.62077, max_latitude: 41.15093, max_longitude: -8.6004 });
    const b = snapBounds({ min_latitude: 41.14044, min_longitude: -8.62031, max_latitude: 41.15011, max_longitude: -8.60081 });
    expect(a).toEqual({ min_latitude: 41.14, min_longitude: -8.621, max_latitude: 41.151, max_longitude: -8.6 });
    expect(b).toEqual(a);
  });

  it("clamps to valid coordinates", () => {
    expect(snapBounds({ min_latitude: -95, min_longitude: -200, max_latitude: 95, max_longitude: 200 })).toEqual({
      min_latitude: -90,
      min_longitude: -180,
      max_latitude: 90,
      max_longitude: 180,
    });
  });

  it("checks point containment", () => {
    expect(containsPoint(porto, 41.15, -8.61)).toBe(true);
    expect(containsPoint(porto, 38.7, -9.1)).toBe(false);
  });
});

describe("cuisine", () => {
  const list = [
    restaurant("n1", "A", ["portuguese", "regional"]),
    restaurant("n2", "B", ["regional"]),
    restaurant("n3", "C", []),
    restaurant("n4", "D", ["fish_and_chips"]),
  ];

  it("formats OSM values for display", () => {
    expect(formatCuisine("fish_and_chips")).toBe("Fish and chips");
    expect(formatCuisine("portuguese")).toBe("Portuguese");
  });

  it("counts cuisines, most frequent first then alphabetical", () => {
    expect(countCuisines(list)).toEqual([
      { cuisine: "regional", count: 2 },
      { cuisine: "fish_and_chips", count: 1 },
      { cuisine: "portuguese", count: 1 },
    ]);
  });

  it("filters by any selected cuisine and keeps all when none selected", () => {
    expect(filterByCuisines(list, new Set())).toHaveLength(4);
    expect(filterByCuisines(list, new Set(["portuguese", "fish_and_chips"])).map((r) => r.restaurant_id)).toEqual([
      "n1",
      "n4",
    ]);
  });
});

describe("links", () => {
  it("builds a directions link from coordinates", () => {
    expect(directionsUrl(41.1, -8.6)).toBe("https://www.google.com/maps/dir/?api=1&destination=41.1,-8.6");
  });

  it("only renders http(s) websites", () => {
    expect(safeWebsite("https://tasca.pt")).toBe("https://tasca.pt/");
    expect(safeWebsite("javascript:alert(1)")).toBeNull();
    expect(safeWebsite("not a url")).toBeNull();
    expect(safeWebsite(null)).toBeNull();
  });

  it("links the first phone number", () => {
    expect(phoneHref("+351 22 123 4567; +351 91 000 0000")).toBe("tel:+351221234567");
    expect(phoneHref("n/a")).toBeNull();
  });
});

describe("clusters", () => {
  const near = [
    restaurant("n1", "A", []),
    { ...restaurant("n2", "B", []), latitude: 41.1471, longitude: -8.6101 },
    { ...restaurant("n3", "C", []), latitude: 38.72, longitude: -9.14 },
  ];
  const world: [number, number, number, number] = [-180, -85, 180, 85];

  it("groups nearby restaurants when zoomed out and splits them when zoomed in", () => {
    const index = buildClusterIndex(near);
    const zoomedOut = visibleFeatures(index, world, 6);
    expect(zoomedOut.filter((f) => f.kind === "cluster")).toEqual([
      expect.objectContaining({ kind: "cluster", count: 2 }),
    ]);
    const zoomedIn = visibleFeatures(index, world, 18);
    expect(zoomedIn.map((f) => (f.kind === "restaurant" ? f.restaurantId : "cluster")).sort()).toEqual(["n1", "n2", "n3"]);
  });
});

describe("url state", () => {
  it("reads only valid ids", () => {
    expect(readUrlState("?city=2735943&restaurant=n123")).toEqual({ cityId: 2735943, restaurantId: "n123" });
    expect(readUrlState("?city=abc&restaurant=x1")).toEqual({ cityId: null, restaurantId: null });
  });

  it("writes and clears the query string", () => {
    writeUrlState({ cityId: 2735943, restaurantId: "w5" });
    expect(window.location.search).toBe("?city=2735943&restaurant=w5");
    writeUrlState({ cityId: null, restaurantId: null });
    expect(window.location.search).toBe("");
  });
});
