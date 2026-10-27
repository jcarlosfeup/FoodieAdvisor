import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LISBON, mockApi, PORTO, renderWithQuery, restaurant, restaurantDetail } from "../test/utils";
import { CuisineFilter } from "./CuisineFilter";
import { LocationPicker } from "./LocationPicker";
import { RestaurantDetails } from "./RestaurantDetails";
import { RestaurantList } from "./RestaurantList";

describe("LocationPicker", () => {
  function setup(onSelectCity = vi.fn()) {
    const fetchMock = mockApi({
      "/api/v1/cities": (url: URL) => ({
        items: url.searchParams.get("q") === "lisboa" ? [LISBON] : [LISBON, PORTO],
        attribution: "",
      }),
    });
    renderWithQuery(
      <LocationPicker countries={[]} country="" onCountryChange={vi.fn()} selectedCity={null} onSelectCity={onSelectCity} />,
    );
    return { fetchMock, onSelectCity, input: screen.getByRole("combobox", { name: "City" }) };
  }

  it("shows the top cities on focus and searches local names as you type", async () => {
    const user = userEvent.setup();
    const { input, fetchMock } = setup();

    await user.click(input);
    expect(await screen.findByRole("option", { name: /Porto, Portugal/ })).toBeInTheDocument();

    await user.type(input, "lisboa");
    expect(await screen.findByRole("option", { name: /Lisbon, Portugal/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Porto/ })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("q=lisboa"))).toBe(true);
  });

  it("selects with the keyboard", async () => {
    const user = userEvent.setup();
    const { input, onSelectCity } = setup();

    await user.click(input);
    await screen.findByRole("option", { name: /Porto/ });
    await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");

    expect(onSelectCity).toHaveBeenCalledWith(PORTO);
    expect(input).toHaveValue("Porto, Portugal");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("ignores Enter while the search for the typed text is still pending", async () => {
    const user = userEvent.setup();
    const { input, onSelectCity } = setup();
    await user.click(input);
    await screen.findByRole("option", { name: /Lisbon/ }); // top cities, Lisbon first

    // Type and press Enter inside the debounce window: the old list must not be used.
    await user.type(input, "lisboa{ArrowDown}{Enter}");
    expect(onSelectCity).not.toHaveBeenCalled();
    expect(screen.getByText("Searching…")).toBeInTheDocument();

    // Once the matching results arrive, Enter selects from them.
    await screen.findByRole("option", { name: /Lisbon/ });
    expect(screen.queryByRole("option", { name: /Porto/ })).not.toBeInTheDocument();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onSelectCity).toHaveBeenCalledWith(LISBON);
  });

  it("closes the list on Escape and keeps the typed text", async () => {
    const user = userEvent.setup();
    const { input } = setup();
    await user.click(input);
    await user.type(input, "lisboa");
    await screen.findByRole("listbox");
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(input).toHaveValue("lisboa");
  });

  it("selects with the mouse", async () => {
    const user = userEvent.setup();
    const { input, onSelectCity } = setup();
    await user.click(input);
    await user.click(await screen.findByRole("option", { name: /Lisbon/ }));
    expect(onSelectCity).toHaveBeenCalledWith(LISBON);
  });
});

describe("CuisineFilter", () => {
  it("toggles cuisines and offers clear only when something is selected", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const { rerender } = renderWithQuery(
      <CuisineFilter cuisines={[{ cuisine: "fish_and_chips", count: 2 }]} selected={new Set()} onToggle={onToggle} onClear={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: "Clear" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Fish and chips/ }));
    expect(onToggle).toHaveBeenCalledWith("fish_and_chips");

    rerender(
      <CuisineFilter
        cuisines={[{ cuisine: "fish_and_chips", count: 2 }]}
        selected={new Set(["fish_and_chips"])}
        onToggle={onToggle}
        onClear={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Fish and chips/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument();
  });

  it("renders nothing without cuisines", () => {
    const { container } = renderWithQuery(<CuisineFilter cuisines={[]} selected={new Set()} onToggle={vi.fn()} onClear={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("RestaurantList", () => {
  it("lists restaurants and marks the selected one", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderWithQuery(
      <RestaurantList
        restaurants={[restaurant("n1", "Tasca A", ["portuguese"], "Rua A 1, Porto"), restaurant("n2", "Tasca B", [])]}
        selectedId="n2"
        onSelect={onSelect}
      />,
    );
    const card = screen.getByRole("button", { name: /Tasca A/ });
    expect(within(card).getByText("Portuguese")).toBeInTheDocument();
    expect(within(card).getByText("Rua A 1, Porto")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tasca B/ })).toHaveAttribute("aria-current", "true");
    await user.click(screen.getByRole("button", { name: /Tasca A/ }));
    expect(onSelect).toHaveBeenCalledWith("n1");
  });
});

describe("RestaurantDetails", () => {
  it("shows details, safe links and the OSM attribution", async () => {
    const summary = restaurant("n1", "Tasca A", ["portuguese"], "Rua A 1, Porto");
    mockApi({
      "/api/v1/restaurants/n1": restaurantDetail(summary, {
        website: "https://tasca-a.pt",
        phone: "+351 22 000 0000",
        opening_hours: "Mo-Sa 12:00-22:00",
      }),
    });
    renderWithQuery(<RestaurantDetails restaurantId="n1" onClose={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Tasca A" })).toBeInTheDocument();
    expect(screen.getByText("Mo-Sa 12:00-22:00")).toBeInTheDocument();
    expect(screen.getByText("Not rated yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Directions" })).toHaveAttribute(
      "href",
      "https://www.google.com/maps/dir/?api=1&destination=41.147,-8.61",
    );
    expect(screen.getByRole("link", { name: "Website" })).toHaveAttribute("href", "https://tasca-a.pt/");
    expect(screen.getByRole("link", { name: "+351 22 000 0000" })).toHaveAttribute("href", "tel:+351220000000");
    expect(screen.getByRole("link", { name: "View on OpenStreetMap" })).toHaveAttribute(
      "href",
      "https://www.openstreetmap.org/node/1",
    );
    expect(screen.getByRole("link", { name: "OpenStreetMap contributors" })).toHaveAttribute(
      "href",
      "https://www.openstreetmap.org/copyright",
    );
  });

  it("reports a missing restaurant", async () => {
    mockApi({});
    renderWithQuery(<RestaurantDetails restaurantId="n404" onClose={vi.fn()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
