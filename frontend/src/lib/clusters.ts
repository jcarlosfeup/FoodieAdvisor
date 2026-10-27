import Supercluster, { type ClusterProperties } from "supercluster";
import type { RestaurantSummary } from "../api/types";

interface PointProperties {
  restaurantId: string;
}

export type ClusterIndex = Supercluster<PointProperties>;

export type MapFeature =
  | { kind: "cluster"; id: number; latitude: number; longitude: number; count: number }
  | { kind: "restaurant"; restaurantId: string; latitude: number; longitude: number };

export function buildClusterIndex(restaurants: RestaurantSummary[]): ClusterIndex {
  const index = new Supercluster<PointProperties>({ radius: 60, maxZoom: 17 });
  index.load(
    restaurants.map((restaurant) => ({
      type: "Feature" as const,
      properties: { restaurantId: restaurant.restaurant_id },
      geometry: { type: "Point" as const, coordinates: [restaurant.longitude, restaurant.latitude] },
    })),
  );
  return index;
}

/** Clusters and single restaurants visible at a zoom level inside [west, south, east, north]. */
export function visibleFeatures(
  index: ClusterIndex,
  bbox: [number, number, number, number],
  zoom: number,
): MapFeature[] {
  return index.getClusters(bbox, Math.round(zoom)).map((feature) => {
    const [longitude, latitude] = feature.geometry.coordinates as [number, number];
    const properties = feature.properties as Partial<ClusterProperties> & Partial<PointProperties>;
    if (properties.cluster) {
      return {
        kind: "cluster",
        id: properties.cluster_id as number,
        latitude,
        longitude,
        count: properties.point_count as number,
      };
    }
    return { kind: "restaurant", restaurantId: properties.restaurantId as string, latitude, longitude };
  });
}
