import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { MapView } from "./components/RestaurantMap";
import { LISBON, mockApi, PORTO, PORTO_DETAIL, renderWithQuery, restaurant, restaurantDetail } from "./test/utils";

// Leaflet needs a real browser layout; replace the map with a stub that exposes its props.
vi.mock("./components/RestaurantMap", () => ({
  RestaurantMap: (props: {
    restaurants: { restaurant_id: string }[];
    city: { name: string } | null;
    onViewChange: (view: MapView) => void;
    onSelect: (id: string) => void;
  }) => (
    <div data-testid="map">
      <span>map city: {props.city?.name ?? "none"}</span>
      <span>markers: {props.restaurants.map((r) => r.restaurant_id).join(",")}</span>
      <button
        onClick={() =>
          props.onViewChange({
            bounds: { min_latitude: 41.14, min_longitude: -8.62, max_latitude: 41.15, max_longitude: -8.6 },
            zoom: 15,
          })
        }
      >
        show Porto centre
      </button>
      <button
        onClick={() =>
          props.onViewChange({
            bounds: { min_latitude: 36, min_longitude: -10, max_latitude: 42, max_longitude: -6 },
            zoom: 6,
          })
        }
      >
        show all of Portugal
      </button>
      <button onClick={() => props.onSelect("n2")}>click marker n2</button>
    </div>
  ),
}));

const TASCA_A = restaurant("n1", "Tasca A", ["portuguese"], "Rua A 1, Porto");
const TASCA_B = restaurant("n2", "Tasca B", ["regional", "seafood"]);

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  mockApi({
    "/api/v1/countries": { items: [{ country_code: "PT", country_name: "Portugal", city_count: 2, restaurant_count: 811 }], attribution: "" },
    "/api/v1/cities": { items: [LISBON, PORTO], attribution: "" },
    "/api/v1/cities/2735943": PORTO_DETAIL,
    "/api/v1/restaurants": { items: [TASCA_A, TASCA_B], next_cursor: null, attribution: "" },
    "/api/v1/restaurants/n2": restaurantDetail(TASCA_B, { opening_hours: "Tu-Su 12:00-23:00" }),
  });
});

describe("App", () => {
  it("guides the user from city choice to restaurant details", async () => {
    const user = userEvent.setup();
    renderWithQuery(<App />);

    // Quick picks before a city is chosen.
    await user.click(await screen.findByRole("button", { name: /Porto 214/ }));
    expect(await screen.findByText("map city: Porto")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "City" })).toHaveValue("Porto, Portugal");

    // The map reports its view; restaurants in it are listed and drawn.
    await user.click(screen.getByRole("button", { name: "show Porto centre" }));
    expect(await screen.findByRole("status")).toHaveTextContent("2 traditional restaurants in view");
    expect(screen.getByText("markers: n1,n2")).toBeInTheDocument();

    // Cuisine filter narrows both the list and the map.
    await user.click(screen.getByRole("button", { name: /Regional 1/ }));
    expect(screen.getByRole("status")).toHaveTextContent("1 of 2 traditional restaurants in view");
    const list = screen.getByRole("list", { name: "Restaurants in view" });
    expect(within(list).getAllByRole("button").map((b) => b.textContent)).toEqual([expect.stringContaining("Tasca B")]);
    expect(screen.getByText("markers: n2")).toBeInTheDocument();

    // Selecting a restaurant shows its details and records it in the URL.
    await user.click(within(list).getByRole("button", { name: /Tasca B/ }));
    expect(await screen.findByText("Tu-Su 12:00-23:00")).toBeInTheDocument();
    expect(window.location.search).toBe("?city=2735943&restaurant=n2");

    await user.click(screen.getByRole("button", { name: "Close details" }));
    expect(screen.queryByText("Tu-Su 12:00-23:00")).not.toBeInTheDocument();
    expect(window.location.search).toBe("?city=2735943");
  });

  it("asks to zoom in instead of querying a view that is too large", async () => {
    const user = userEvent.setup();
    renderWithQuery(<App />);
    await user.click(screen.getByRole("button", { name: "show all of Portugal" }));
    expect(screen.getByRole("status")).toHaveTextContent("Choose a city or zoom in");
    const fetchMock = vi.mocked(fetch);
    expect(fetchMock.mock.calls.some(([url]) => String(url).startsWith("/api/v1/restaurants?"))).toBe(false);
  });

  it("selecting a marker opens its details", async () => {
    const user = userEvent.setup();
    renderWithQuery(<App />);
    await user.click(screen.getByRole("button", { name: "show Porto centre" }));
    await user.click(screen.getByRole("button", { name: "click marker n2" }));
    expect(await screen.findByRole("heading", { name: "Tasca B" })).toBeInTheDocument();
  });

  it("restores city and restaurant from a shared link", async () => {
    window.history.replaceState(null, "", "/?city=2735943&restaurant=n2");
    renderWithQuery(<App />);
    expect(await screen.findByText("map city: Porto")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Tasca B" })).toBeInTheDocument();
  });

  it("credits OpenStreetMap and GeoNames", () => {
    renderWithQuery(<App />);
    expect(screen.getByRole("link", { name: "OpenStreetMap contributors" })).toHaveAttribute(
      "href",
      "https://www.openstreetmap.org/copyright",
    );
    expect(screen.getByRole("link", { name: "GeoNames" })).toBeInTheDocument();
  });
});
