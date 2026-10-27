import type { RestaurantSummary } from "../api/types";

/** "fish_and_chips" -> "Fish and chips", "portuguese" -> "Portuguese". */
export function formatCuisine(value: string): string {
  const words = value.replace(/_/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export interface CuisineCount {
  cuisine: string;
  count: number;
}

/** Cuisines present in the given restaurants, most frequent first (ties alphabetical). */
export function countCuisines(restaurants: RestaurantSummary[]): CuisineCount[] {
  const counts = new Map<string, number>();
  for (const restaurant of restaurants) {
    for (const cuisine of restaurant.cuisines) counts.set(cuisine, (counts.get(cuisine) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([cuisine, count]) => ({ cuisine, count }))
    .sort((a, b) => b.count - a.count || a.cuisine.localeCompare(b.cuisine));
}

/** Restaurants having at least one of the selected cuisines (all when none is selected). */
export function filterByCuisines(restaurants: RestaurantSummary[], selected: ReadonlySet<string>): RestaurantSummary[] {
  if (selected.size === 0) return restaurants;
  return restaurants.filter((restaurant) => restaurant.cuisines.some((cuisine) => selected.has(cuisine)));
}
