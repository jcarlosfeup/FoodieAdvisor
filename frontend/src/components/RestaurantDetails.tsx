import { useQuery } from "@tanstack/react-query";
import { fetchRestaurant } from "../api/client";
import type { RestaurantDetail } from "../api/types";
import { formatCuisine } from "../lib/cuisine";
import { directionsUrl, phoneHref, safeWebsite } from "../lib/links";

interface Props {
  restaurantId: string;
  onClose: () => void;
}

export function RestaurantDetails({ restaurantId, onClose }: Props) {
  const query = useQuery({
    queryKey: ["restaurant", restaurantId],
    queryFn: ({ signal }) => fetchRestaurant(restaurantId, signal),
    staleTime: 5 * 60_000,
  });

  return (
    <section className="restaurant-details" aria-label="Restaurant details" aria-live="polite">
      <button type="button" className="close-button" onClick={onClose} aria-label="Close details">
        ×
      </button>
      {query.isPending && <p className="muted">Loading restaurant…</p>}
      {query.isError && <p role="alert">This restaurant could not be loaded.</p>}
      {query.data && <DetailsBody restaurant={query.data} />}
    </section>
  );
}

function DetailsBody({ restaurant }: { restaurant: RestaurantDetail }) {
  const website = safeWebsite(restaurant.website);
  const tel = phoneHref(restaurant.phone);
  return (
    <>
      <h2>{restaurant.name}</h2>
      <p className="muted">
        {restaurant.cuisines.length > 0 ? restaurant.cuisines.map(formatCuisine).join(" · ") : "Traditional"} ·{" "}
        {restaurant.city_name}
      </p>
      <dl className="facts">
        {restaurant.address && (
          <>
            <dt>Address</dt>
            <dd>{restaurant.address}</dd>
          </>
        )}
        {restaurant.opening_hours && (
          <>
            <dt>Opening hours</dt>
            <dd>{restaurant.opening_hours}</dd>
          </>
        )}
        {restaurant.phone && (
          <>
            <dt>Phone</dt>
            <dd>{tel ? <a href={tel}>{restaurant.phone}</a> : restaurant.phone}</dd>
          </>
        )}
        <dt>Rating</dt>
        <dd className="muted">Not rated yet</dd>
      </dl>
      <div className="actions">
        <a
          className="button primary"
          href={directionsUrl(restaurant.latitude, restaurant.longitude)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Directions
        </a>
        {website && (
          <a className="button" href={website} target="_blank" rel="noopener noreferrer">
            Website
          </a>
        )}
        <a className="button" href={restaurant.osm_url} target="_blank" rel="noopener noreferrer">
          View on OpenStreetMap
        </a>
      </div>
      <p className="attribution-note muted">
        Data ©{" "}
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">
          OpenStreetMap contributors
        </a>{" "}
        (ODbL)
      </p>
    </>
  );
}
