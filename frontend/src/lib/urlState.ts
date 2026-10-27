/** Shareable view state in the query string: ?city=<geonameid>&restaurant=<osm id>. */
export interface UrlState {
  cityId: number | null;
  restaurantId: string | null;
}

export function readUrlState(search: string = window.location.search): UrlState {
  const params = new URLSearchParams(search);
  const city = Number(params.get("city"));
  const restaurant = params.get("restaurant");
  return {
    cityId: Number.isInteger(city) && city > 0 ? city : null,
    restaurantId: restaurant && /^[nwr]\d{1,19}$/.test(restaurant) ? restaurant : null,
  };
}

export function writeUrlState(state: UrlState): void {
  const params = new URLSearchParams(window.location.search);
  if (state.cityId) params.set("city", String(state.cityId));
  else params.delete("city");
  if (state.restaurantId) params.set("restaurant", state.restaurantId);
  else params.delete("restaurant");
  const query = params.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
}
