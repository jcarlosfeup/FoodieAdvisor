import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { Bounds, CityDetail, RestaurantSummary } from "../api/types";
import { buildClusterIndex, visibleFeatures } from "../lib/clusters";
import { containsPoint } from "../lib/geo";

const TILE_URL = import.meta.env.VITE_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
  import.meta.env.VITE_TILE_ATTRIBUTION ||
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Portugal, zoomed out: the first view before a city is chosen.
const DEFAULT_CENTER: [number, number] = [39.6, -8.2];
const DEFAULT_ZOOM = 6;
const DETAIL_ZOOM = 16;

export interface MapView {
  bounds: Bounds;
  zoom: number;
}

interface Props {
  restaurants: RestaurantSummary[];
  /** The current view as last reported through onViewChange (null before the map is ready). */
  view: MapView | null;
  selected: { restaurantId: string; latitude: number; longitude: number } | null;
  city: CityDetail | null;
  onViewChange: (view: MapView) => void;
  onSelect: (restaurantId: string) => void;
}

export function RestaurantMap({ restaurants, view, selected, city, onViewChange, onSelect }: Props) {
  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="map" aria-label="Restaurant map">
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} maxZoom={19} />
      <ViewWatcher onViewChange={onViewChange} />
      <FitCity city={city} />
      <FocusSelected selected={selected} />
      {view && (
        <ClusterLayer
          restaurants={restaurants}
          view={view}
          selectedId={selected?.restaurantId ?? null}
          onSelect={onSelect}
        />
      )}
    </MapContainer>
  );
}

function toBounds(map: L.Map): Bounds {
  const bounds = map.getBounds();
  return {
    min_latitude: bounds.getSouth(),
    min_longitude: bounds.getWest(),
    max_latitude: bounds.getNorth(),
    max_longitude: bounds.getEast(),
  };
}

/**
 * Reports the visible area after every pan/zoom (and once on load).
 *
 * The listener is attached once and never re-subscribed. Re-subscribing on each render (as
 * useMapEvents does with an inline handler object) leaves a gap during React's commit in which
 * a synchronous fitBounds/setView from a sibling effect fires moveend with nobody listening.
 */
function ViewWatcher({ onViewChange }: { onViewChange: (view: MapView) => void }) {
  const map = useMap();
  const callback = useRef(onViewChange);
  useEffect(() => {
    callback.current = onViewChange;
  }, [onViewChange]);
  useEffect(() => {
    const report = () => callback.current({ bounds: toBounds(map), zoom: map.getZoom() });
    map.on("moveend", report);
    map.whenReady(report);
    return () => {
      map.off("moveend", report);
    };
  }, [map]);
  return null;
}

/** Fits the map to the chosen city's restaurants whenever the city changes. */
function FitCity({ city }: { city: CityDetail | null }) {
  const map = useMap();
  const cityId = city?.city_id;
  useEffect(() => {
    if (!city) return;
    const extent = city.restaurant_extent;
    const bounds = L.latLngBounds(
      [extent.min_latitude, extent.min_longitude],
      [extent.max_latitude, extent.max_longitude],
    );
    if (bounds.getNorthEast().equals(bounds.getSouthWest())) map.setView(bounds.getCenter(), 15);
    else map.fitBounds(bounds, { padding: [24, 24], maxZoom: 15 });
    // Only refit when a different city is chosen, not on every re-render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityId, map]);
  return null;
}

/** Brings the selected restaurant into view when it is off-screen or the map is zoomed out. */
function FocusSelected({ selected }: { selected: Props["selected"] }) {
  const map = useMap();
  const key = selected ? `${selected.restaurantId}` : null;
  useEffect(() => {
    if (!selected) return;
    const inView = containsPoint(toBounds(map), selected.latitude, selected.longitude);
    if (!inView || map.getZoom() < 15) {
      map.flyTo([selected.latitude, selected.longitude], Math.max(map.getZoom(), DETAIL_ZOOM), { duration: 0.6 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, map]);
  return null;
}

function clusterIcon(count: number): L.DivIcon {
  const size = count < 10 ? 32 : count < 100 ? 40 : 48;
  return L.divIcon({
    html: `<span>${count}</span>`,
    className: "cluster-icon",
    iconSize: [size, size],
  });
}

function ClusterLayer({
  restaurants,
  view,
  selectedId,
  onSelect,
}: {
  restaurants: RestaurantSummary[];
  view: MapView;
  selectedId: string | null;
  onSelect: (restaurantId: string) => void;
}) {
  const map = useMap();

  // The selected restaurant is drawn on its own (never hidden inside a cluster).
  const index = useMemo(
    () => buildClusterIndex(restaurants.filter((r) => r.restaurant_id !== selectedId)),
    [restaurants, selectedId],
  );
  const byId = useMemo(() => new Map(restaurants.map((r) => [r.restaurant_id, r])), [restaurants]);
  const features = useMemo(
    () =>
      visibleFeatures(
        index,
        [view.bounds.min_longitude, view.bounds.min_latitude, view.bounds.max_longitude, view.bounds.max_latitude],
        view.zoom,
      ),
    [index, view],
  );

  const selectedRestaurant = selectedId ? byId.get(selectedId) : undefined;

  return (
    <>
      {features.map((feature) => {
        if (feature.kind === "cluster") {
          return (
            <Marker
              key={`cluster-${feature.id}`}
              position={[feature.latitude, feature.longitude]}
              icon={clusterIcon(feature.count)}
              title={`${feature.count} restaurants`}
              eventHandlers={{
                click: () =>
                  map.flyTo(
                    [feature.latitude, feature.longitude],
                    Math.min(index.getClusterExpansionZoom(feature.id), 18),
                    { duration: 0.5 },
                  ),
              }}
            />
          );
        }
        const restaurant = byId.get(feature.restaurantId);
        return (
          <CircleMarker
            key={feature.restaurantId}
            center={[feature.latitude, feature.longitude]}
            radius={7}
            pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#c2410c", fillOpacity: 0.95 }}
            eventHandlers={{ click: () => onSelect(feature.restaurantId) }}
          >
            {restaurant && <Tooltip direction="top" offset={[0, -6]}>{restaurant.name}</Tooltip>}
          </CircleMarker>
        );
      })}
      {selectedRestaurant && (
        <CircleMarker
          key={`selected-${selectedRestaurant.restaurant_id}`}
          center={[selectedRestaurant.latitude, selectedRestaurant.longitude]}
          radius={11}
          pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#b4232a", fillOpacity: 1 }}
        >
          <Tooltip direction="top" offset={[0, -8]} permanent>
            {selectedRestaurant.name}
          </Tooltip>
        </CircleMarker>
      )}
    </>
  );
}
