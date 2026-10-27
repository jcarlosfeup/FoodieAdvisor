import { useEffect, useRef } from "react";
import type { RestaurantSummary } from "../api/types";
import { formatCuisine } from "../lib/cuisine";

interface Props {
  restaurants: RestaurantSummary[];
  selectedId: string | null;
  onSelect: (restaurantId: string) => void;
}

export function RestaurantList({ restaurants, selectedId, onSelect }: Props) {
  const selectedRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    selectedRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [selectedId]);

  if (restaurants.length === 0) return null;

  return (
    <ul className="restaurant-list" aria-label="Restaurants in view">
      {restaurants.map((restaurant) => {
        const selected = restaurant.restaurant_id === selectedId;
        return (
          <li key={restaurant.restaurant_id}>
            <button
              type="button"
              ref={selected ? selectedRef : undefined}
              className={selected ? "restaurant-card selected" : "restaurant-card"}
              aria-current={selected ? "true" : undefined}
              onClick={() => onSelect(restaurant.restaurant_id)}
            >
              <span className="restaurant-name">{restaurant.name}</span>
              {restaurant.cuisines.length > 0 && (
                <span className="restaurant-cuisines">{restaurant.cuisines.map(formatCuisine).join(" · ")}</span>
              )}
              {restaurant.address && <span className="restaurant-address muted">{restaurant.address}</span>}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
