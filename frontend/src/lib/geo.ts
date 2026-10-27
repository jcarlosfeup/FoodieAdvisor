import type { Bounds } from "../api/types";

/** Must match API_MAX_BBOX_SPAN_DEGREES; larger views are not queried. */
export const MAX_SPAN_DEGREES = 2;

export function isViewTooLarge(bounds: Bounds, maxSpan = MAX_SPAN_DEGREES): boolean {
  return (
    bounds.max_latitude - bounds.min_latitude > maxSpan || bounds.max_longitude - bounds.min_longitude > maxSpan
  );
}

/**
 * Round a map view outwards to a ~100 m grid and clamp it to valid coordinates. Small pans then
 * reuse the same query key (and cache) instead of refetching for every pixel moved.
 */
export function snapBounds(bounds: Bounds, step = 0.001): Bounds {
  const down = (value: number) => Math.floor(value / step) * step;
  const up = (value: number) => Math.ceil(value / step) * step;
  const clamp = (value: number, limit: number) => Number(Math.min(Math.max(value, -limit), limit).toFixed(6));
  return {
    min_latitude: clamp(down(bounds.min_latitude), 90),
    min_longitude: clamp(down(bounds.min_longitude), 180),
    max_latitude: clamp(up(bounds.max_latitude), 90),
    max_longitude: clamp(up(bounds.max_longitude), 180),
  };
}

export function containsPoint(bounds: Bounds, latitude: number, longitude: number): boolean {
  return (
    latitude >= bounds.min_latitude &&
    latitude <= bounds.max_latitude &&
    longitude >= bounds.min_longitude &&
    longitude <= bounds.max_longitude
  );
}
