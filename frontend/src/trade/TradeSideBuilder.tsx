import type { CatalogEntry, Side } from "./tradeState";

// One side of the trade ("David sends" / "David receives"). The activate
// button sets which side the next searched asset is added to.
export function TradeSideBuilder({
  side,
  label,
  entries,
  active,
  onActivate,
}: {
  side: Side;
  label: string;
  entries: CatalogEntry[];
  active: boolean;
  onActivate: (side: Side) => void;
}) {
  return (
    <section className="dg-trade-side" aria-label={label} data-active={active}>
      <button
        type="button"
        className="dg-trade-side__activate"
        aria-pressed={active}
        onClick={() => onActivate(side)}
      >
        {label}
      </button>
      <ul className="dg-trade-side__assets">
        {entries.map((entry) => (
          <li key={entry.asset_id}>{entry.label}</li>
        ))}
      </ul>
    </section>
  );
}
