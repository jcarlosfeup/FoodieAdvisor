import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  fetchCities,
  fetchCity,
  fetchCountries,
  fetchRestaurant,
  fetchRestaurantsInBounds,
  MAX_RESTAURANTS_PER_VIEW,
} from "./api/client";
import type { City } from "./api/types";
import { CuisineFilter } from "./components/CuisineFilter";
import { LocationPicker } from "./components/LocationPicker";
import { RestaurantDetails } from "./components/RestaurantDetails";
import { RestaurantList } from "./components/RestaurantList";
import { RestaurantMap, type MapView } from "./components/RestaurantMap";
import { countCuisines, filterByCuisines } from "./lib/cuisine";
import { isViewTooLarge, snapBounds } from "./lib/geo";
import { readUrlState, writeUrlState } from "./lib/urlState";

export function App() {
  const initial = useMemo(() => readUrlState(), []);
  const [country, setCountry] = useState("");
  const [cityId, setCityId] = useState<number | null>(initial.cityId);
  const [selectedId, setSelectedId] = useState<string | null>(initial.restaurantId);
  const [view, setView] = useState<MapView | null>(null);
  const [cuisines, setCuisines] = useState<ReadonlySet<string>>(new Set());

  useEffect(() => writeUrlState({ cityId, restaurantId: selectedId }), [cityId, selectedId]);

  const countries = useQuery({ queryKey: ["countries"], queryFn: ({ signal }) => fetchCountries(signal), staleTime: Infinity });
  const quickPicks = useQuery({
    queryKey: ["cities", "", ""],
    queryFn: ({ signal }) => fetchCities({ limit: 6 }, signal),
    staleTime: 5 * 60_000,
  });
  const city = useQuery({
    queryKey: ["city", cityId],
    queryFn: ({ signal }) => fetchCity(cityId as number, signal),
    enabled: cityId !== null,
    staleTime: 5 * 60_000,
  });

  const snapped = view ? snapBounds(view.bounds) : null;
  const tooLarge = snapped ? isViewTooLarge(snapped) : false;
  const restaurants = useQuery({
    queryKey: ["restaurants", snapped],
    queryFn: ({ signal }) => fetchRestaurantsInBounds(snapped!, signal),
    enabled: snapped !== null && !tooLarge,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

  const inView = useMemo(
    () => (tooLarge ? [] : (restaurants.data?.restaurants ?? [])),
    [restaurants.data, tooLarge],
  );
  const cuisineCounts = useMemo(() => countCuisines(inView), [inView]);
  const shown = useMemo(() => filterByCuisines(inView, cuisines), [inView, cuisines]);

  // Same query key as RestaurantDetails, so this shares its cache. It gives the map the
  // coordinates of a restaurant opened from a link before it is loaded in the current view.
  const selectedDetail = useQuery({
    queryKey: ["restaurant", selectedId],
    queryFn: ({ signal }) => fetchRestaurant(selectedId as string, signal),
    enabled: selectedId !== null,
    staleTime: 5 * 60_000,
  });
  const selectedSource = inView.find((r) => r.restaurant_id === selectedId) ?? selectedDetail.data;
  const selectedPoint =
    selectedId && selectedSource
      ? { restaurantId: selectedId, latitude: selectedSource.latitude, longitude: selectedSource.longitude }
      : null;

  const selectCity = useCallback((next: City) => {
    setCityId(next.city_id);
    setSelectedId(null);
    setCuisines(new Set());
  }, []);

  const toggleCuisine = useCallback((cuisine: string) => {
    setCuisines((current) => {
      const next = new Set(current);
      if (next.has(cuisine)) next.delete(cuisine);
      else next.add(cuisine);
      return next;
    });
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <span aria-hidden="true">🍽️</span> FoodieAdvisor
        </h1>
        <p className="tagline">Traditional restaurants, city by city</p>
      </header>

      <aside className="sidebar">
        <LocationPicker
          countries={countries.data ?? []}
          country={country}
          onCountryChange={setCountry}
          selectedCity={city.data ?? null}
          onSelectCity={selectCity}
        />

        {selectedId && <RestaurantDetails restaurantId={selectedId} onClose={() => setSelectedId(null)} />}

        <ViewStatus
          hasView={view !== null}
          tooLarge={tooLarge}
          loading={restaurants.isPending && !tooLarge}
          error={restaurants.isError}
          onRetry={() => void restaurants.refetch()}
          total={inView.length}
          shown={shown.length}
          truncated={restaurants.data?.truncated ?? false}
          quickPicks={cityId === null || tooLarge ? (quickPicks.data ?? []) : []}
          onPick={selectCity}
        />

        <CuisineFilter
          cuisines={cuisineCounts}
          selected={cuisines}
          onToggle={toggleCuisine}
          onClear={() => setCuisines(new Set())}
        />
        <RestaurantList restaurants={shown} selectedId={selectedId} onSelect={setSelectedId} />
      </aside>

      <main className="map-area">
        <RestaurantMap
          restaurants={shown}
          view={view}
          selected={selectedPoint}
          city={city.data ?? null}
          onViewChange={setView}
          onSelect={setSelectedId}
        />
        {restaurants.isFetching && !tooLarge && <div className="map-badge">Loading…</div>}
      </main>

      <footer className="app-footer">
        Restaurant data ©{" "}
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">
          OpenStreetMap contributors
        </a>{" "}
        (ODbL) · City data ©{" "}
        <a href="https://www.geonames.org" target="_blank" rel="noopener noreferrer">
          GeoNames
        </a>{" "}
        (CC BY 4.0)
      </footer>
    </div>
  );
}

interface ViewStatusProps {
  hasView: boolean;
  tooLarge: boolean;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  total: number;
  shown: number;
  truncated: boolean;
  quickPicks: City[];
  onPick: (city: City) => void;
}

function ViewStatus(props: ViewStatusProps) {
  const { hasView, tooLarge, loading, error, onRetry, total, shown, truncated, quickPicks, onPick } = props;
  let message: ReactNode;
  if (!hasView) message = "Loading map…";
  else if (tooLarge) message = "Choose a city or zoom in on the map to see restaurants.";
  else if (error)
    message = (
      <>
        Restaurants could not be loaded.{" "}
        <button type="button" className="link-button" onClick={onRetry}>
          Try again
        </button>
      </>
    );
  else if (loading) message = "Loading restaurants…";
  else if (total === 0) message = "No traditional restaurants in this area yet.";
  else
    message = (
      <>
        <strong>{shown}</strong> {shown === total ? "" : `of ${total} `}traditional restaurant{total === 1 ? "" : "s"} in
        view
        {truncated && ` (first ${MAX_RESTAURANTS_PER_VIEW}; zoom in to see all)`}
      </>
    );

  return (
    <div className="view-status">
      <p role="status" aria-live="polite">
        {message}
      </p>
      {quickPicks.length > 0 && (
        <div className="chips" aria-label="Popular cities">
          {quickPicks.map((pick) => (
            <button key={pick.city_id} type="button" className="chip" onClick={() => onPick(pick)}>
              {pick.name} <span className="muted">{pick.restaurant_count}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
