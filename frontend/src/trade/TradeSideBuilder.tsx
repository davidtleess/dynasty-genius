import type { CatalogEntry, Side } from "./tradeState";

// One side of the trade ("David sends" / "David receives"). The activate
// button sets which side the next searched asset is added to.
export function TradeSideBuilder({
  side,
  label,
  entries,
  active,
  onActivate,
  onSelectPlayer,
}: {
  side: Side;
  label: string;
  entries: CatalogEntry[];
  active: boolean;
  onActivate: (side: Side) => void;
  onSelectPlayer?: ((entry: CatalogEntry) => void) | undefined;
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
        {entries.map((entry) =>
          onSelectPlayer && entry.kind === "player" ? (
            // A player chip is an inspector entry point (opens the inspector).
            <li key={entry.asset_id}>
              <button
                type="button"
                className="dg-trade-side__chip"
                onClick={() => onSelectPlayer(entry)}
              >
                {entry.label}
              </button>
            </li>
          ) : (
            <li key={entry.asset_id}>{entry.label}</li>
          ),
        )}
      </ul>
    </section>
  );
}
