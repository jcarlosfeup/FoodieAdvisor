import type { CuisineCount } from "../lib/cuisine";
import { formatCuisine } from "../lib/cuisine";

interface Props {
  cuisines: CuisineCount[];
  selected: ReadonlySet<string>;
  onToggle: (cuisine: string) => void;
  onClear: () => void;
  maxShown?: number;
}

export function CuisineFilter({ cuisines, selected, onToggle, onClear, maxShown = 12 }: Props) {
  if (cuisines.length === 0) return null;
  // Always keep selected cuisines visible even if they are not among the most frequent.
  const shown = cuisines.filter((item, index) => index < maxShown || selected.has(item.cuisine));
  return (
    <section className="cuisine-filter" aria-label="Filter by cuisine">
      <div className="section-heading">
        <h3>Cuisine</h3>
        {selected.size > 0 && (
          <button type="button" className="link-button" onClick={onClear}>
            Clear
          </button>
        )}
      </div>
      <div className="chips">
        {shown.map(({ cuisine, count }) => (
          <button
            key={cuisine}
            type="button"
            className="chip"
            aria-pressed={selected.has(cuisine)}
            onClick={() => onToggle(cuisine)}
          >
            {formatCuisine(cuisine)} <span className="muted">{count}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
