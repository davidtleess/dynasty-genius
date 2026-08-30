import { PlayerNameButton } from "../player/playerSelection";
import type { CatalogEntry, Side } from "./tradeState";

// One side of the trade ("You send" / "You get"). The side header is a toggle:
// it sets which side the next searched asset lands on. Second person, per the
// voice guide — the product speaks as "we" to "you", so the columns are the
// manager's own sides rather than a third-person label about him.
export function TradeSideBuilder({
  side,
  label,
  entries,
  active,
  onActivate,
  onRemove,
  onSelectPlayer,
}: {
  side: Side;
  label: string;
  entries: CatalogEntry[];
  active: boolean;
  onActivate: (side: Side) => void;
  /** Take an asset back off this side. */
  onRemove: (side: Side, assetId: string) => void;
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
        <span className="dg-trade-side__label">{label}</span>
        <span className="dg-trade-side__count">
          {entries.length === 0
            ? "empty"
            : `${entries.length} ${entries.length === 1 ? "asset" : "assets"}`}
        </span>
      </button>
      {/* An empty side used to be blank space with no explanation of how the
          two columns relate to the search box above them. */}
      {entries.length === 0 ? (
        <p className="dg-trade-side__empty">
          {active
            ? "Nothing here yet. The next player you pick lands on this side."
            : "Nothing here yet. Press this column to add to it."}
        </p>
      ) : (
        <ul className="dg-trade-side__assets">
          {entries.map((entry) => (
            <li key={entry.asset_id} className="dg-trade-side__asset">
              {/* A player's name opens his card through the one selection sink;
                  a pick has no card and stays plain text (DG-110). */}
              {onSelectPlayer && entry.kind === "player" ? (
                <button
                  type="button"
                  className="dg-trade-side__chip"
                  onClick={() => onSelectPlayer(entry)}
                >
                  {entry.label}
                </button>
              ) : (
                <PlayerNameButton sleeperId={null} name={entry.label} />
              )}
              {/* Adding an asset by mistake used to be permanent for the life of
                  the saved draft — the remove helper existed and nothing called
                  it. */}
              <button
                type="button"
                className="dg-trade-side__remove"
                aria-label={`Remove ${entry.label} from ${label}`}
                onClick={() => onRemove(side, entry.asset_id)}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
