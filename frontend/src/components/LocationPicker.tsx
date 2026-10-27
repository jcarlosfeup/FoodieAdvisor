import { useQuery } from "@tanstack/react-query";
import { useId, useState, type KeyboardEvent } from "react";
import { fetchCities } from "../api/client";
import type { City, Country } from "../api/types";
import { useDebouncedValue } from "../hooks/useDebouncedValue";

interface Props {
  countries: Country[];
  country: string;
  onCountryChange: (country: string) => void;
  selectedCity: City | null;
  onSelectCity: (city: City) => void;
}

/** Country selector plus an accessible city autocomplete (ARIA combobox pattern). */
export function LocationPicker({ countries, country, onCountryChange, selectedCity, onSelectCity }: Props) {
  const [text, setText] = useState(selectedCity?.label ?? "");
  const [syncedLabel, setSyncedLabel] = useState(selectedCity?.label);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const listId = useId();

  // When the selected city changes from outside (URL, quick pick), show its label.
  if (selectedCity?.label !== syncedLabel) {
    setSyncedLabel(selectedCity?.label);
    setText(selectedCity?.label ?? "");
  }

  // Typing the selected label back is not a search; show the top cities instead.
  const searchTerm = text === selectedCity?.label ? "" : text.trim();
  const debouncedTerm = useDebouncedValue(searchTerm, 250);
  const cities = useQuery({
    queryKey: ["cities", country, debouncedTerm],
    queryFn: ({ signal }) => fetchCities({ country: country || undefined, q: debouncedTerm || undefined, limit: 10 }, signal),
    enabled: open,
    staleTime: 5 * 60_000,
  });
  // While the debounce is pending, the cached list belongs to an older term. Hide it so that
  // Enter or a click cannot pick a city that does not match what was typed.
  const settled = searchTerm === debouncedTerm;
  const options = settled ? (cities.data ?? []) : [];
  const searching = !settled || cities.isPending;

  function choose(city: City) {
    onSelectCity(city);
    setText(city.label);
    setOpen(false);
    setActiveIndex(-1);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => Math.min(index + 1, options.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      const city = options[activeIndex] ?? (options.length === 1 ? options[0] : undefined);
      if (open && city) {
        event.preventDefault();
        choose(city);
      }
    } else if (event.key === "Escape") {
      // Keep the typed text; only close the list.
      event.preventDefault();
      setOpen(false);
      setActiveIndex(-1);
    }
  }

  const activeOption = options[activeIndex];

  return (
    <section className="location-picker" aria-label="Choose a destination">
      <h2 className="picker-title">Where do you want to eat?</h2>
      {countries.length > 1 && (
        <label className="field">
          <span>Country</span>
          <select value={country} onChange={(event) => onCountryChange(event.target.value)}>
            <option value="">All countries</option>
            {countries.map((item) => (
              <option key={item.country_code} value={item.country_code}>
                {item.country_name ?? item.country_code}
              </option>
            ))}
          </select>
        </label>
      )}
      <div className="field combobox">
        <label htmlFor={`${listId}-input`}>City</label>
        <input
          id={`${listId}-input`}
          type="text"
          role="combobox"
          autoComplete="off"
          placeholder="Search a city, e.g. Porto or Lisboa"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={open && activeOption ? `${listId}-${activeOption.city_id}` : undefined}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={(event) => {
            event.target.select();
            setOpen(true);
          }}
          onBlur={() => setOpen(false)}
          onKeyDown={onKeyDown}
        />
        {open && (
          <ul id={listId} role="listbox" className="options" aria-label="Cities">
            {searching && <li className="option-status">Searching…</li>}
            {settled && cities.isError && <li className="option-status">Could not load cities</li>}
            {settled && cities.isSuccess && options.length === 0 && (
              <li className="option-status">No cities with restaurants</li>
            )}
            {options.map((city, index) => (
              <li
                key={city.city_id}
                id={`${listId}-${city.city_id}`}
                role="option"
                aria-selected={index === activeIndex}
                className={index === activeIndex ? "option active" : "option"}
                // mousedown keeps focus in the input so onBlur does not close the list first
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(city)}
              >
                <span>{city.label}</span>
                <span className="muted">{city.restaurant_count}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
