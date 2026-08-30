import { useId, useState } from "react";

import type { CatalogEntry } from "./tradeState";
import { CATALOG_PAGE_SIZE, useAssetCatalogSearch } from "./useAssetCatalogSearch";

// Reads the read-only asset catalog and validates the 200 at the SDK boundary
// with the generated Zod schema (same honest-degradation pattern as
// TrustStrip): any non-ok response or shape mismatch says so rather than
// rendering raw or going quietly blank. The fetch/debounce/abort contract
// lives in useAssetCatalogSearch, shared with the shell's global player search
// and the command palette (DG-110).
export function AssetSearch({
  onSelect,
  label = "Search tradeable assets",
  placeholder,
  visibleLabel = false,
  hint,
  filter,
  emptyNotice = "Nothing in the catalog matches that.",
  filteredNotice = "Some assets matched, but none this box can open.",
}: {
  onSelect: (entry: CatalogEntry) => void;
  /** Accessible name for the box — the shell's copy differs from Trade Lab's. */
  label?: string;
  placeholder?: string | undefined;
  /**
   * Draw `label` as a real, readable <label> above the box instead of hiding it
   * in an aria-label. The rail's box sits under a heading and reads fine with a
   * placeholder; Trade Lab's was a bare white rectangle with nothing on screen
   * saying what it was for (DG-116).
   */
  visibleLabel?: boolean;
  /** One line under the box explaining what selecting a result will do. */
  hint?: string | undefined;
  /** Optional gate: offer only results this caller can actually open. */
  filter?: ((entry: CatalogEntry) => boolean) | undefined;
  /**
   * What to say when the CATALOG itself came back with nothing. The honest
   * sentence names the scope this box actually covers, and that scope differs
   * per caller, so the caller owns the words (DG-110 panel: the old single
   * line claimed the whole tracked universe on a rostered-only catalog).
   */
  emptyNotice?: string;
  /** What to say when the catalog DID match but `filter` removed every row. */
  filteredNotice?: string;
}) {
  const inputId = useId();
  const [query, setQuery] = useState("");
  const search = useAssetCatalogSearch(query);
  // Three different facts, three different sentences. `answered` is what the
  // catalog said; `results` is what this box will offer. Collapsing the gap
  // between them into "nothing matched" states something untrue.
  const answered = search.results;
  const results = filter === undefined ? answered : answered.filter(filter);
  const ready = search.status === "ready";
  const filteredToEmpty = answered.length > 0 && results.length === 0;

  return (
    <div className="dg-asset-search">
      {visibleLabel && (
        <label className="dg-asset-search__label" htmlFor={inputId}>
          {label}
        </label>
      )}
      <input
        // With a visible <label> the aria-label would only compete with it, and
        // the spoken name should be the words on screen.
        {...(visibleLabel ? { id: inputId } : { "aria-label": label })}
        type="search"
        className="dg-asset-search__input"
        placeholder={placeholder}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      {hint !== undefined && <p className="dg-asset-search__hint">{hint}</p>}
      {/* A silent empty box is a dead end and, after a failed read, a lie:
          an empty catalog answer and an unreadable one say different things. */}
      {search.status === "unavailable" && (
        <p className="dg-asset-search__notice" role="status">
          Search is down right now — we could not read the player list.
        </p>
      )}
      {ready && filteredToEmpty && (
        <p className="dg-asset-search__notice" role="status">
          {filteredNotice}
        </p>
      )}
      {ready && answered.length === 0 && (
        <p className="dg-asset-search__notice" role="status">
          {emptyNotice}
        </p>
      )}
      <ul className="dg-asset-search__results">
        {results.map((entry) => (
          <li key={entry.asset_id}>
            <button
              type="button"
              onClick={() => {
                onSelect(entry);
                // Clear the box on selection: the list is a lookup, not a
                // permanent panel, and leaving it open buried the rail nav.
                setQuery("");
              }}
            >
              {entry.label}
            </button>
            <ResultMeta entry={entry} />
          </li>
        ))}
      </ul>
      {/* The server cut the list; saying so is cheaper than letting David read
          a top-50 as if it were everything. */}
      {ready && answered.length >= CATALOG_PAGE_SIZE && (
        <p className="dg-asset-search__notice" role="status">
          Showing the first {CATALOG_PAGE_SIZE} matches — type a bit more to narrow it
          down.
        </p>
      )}
    </div>
  );
}

// Position and the MANAGER who rosters him (a Sleeper handle, not an NFL team
// — the catalog carries no NFL team field), enough to tell two same-named
// players apart. Rendered OUTSIDE the button so the button's accessible name
// stays the player's name. Absence renders nothing rather than an invented
// label. Note the catalog is rostered-players-plus-picks, so every player row
// reaching here has an owner; a pick has neither field and renders no meta.
function ResultMeta({ entry }: { entry: CatalogEntry }) {
  const position = typeof entry.position === "string" ? entry.position : null;
  const owner =
    typeof entry.roster_owner_name === "string" ? entry.roster_owner_name : null;
  if (position === null && owner === null) {
    return null;
  }
  return (
    <span className="dg-asset-search__meta">
      {position}
      {position !== null && owner !== null ? " · " : null}
      {/* The manager's own team name is text the league wrote, not our
          vocabulary — DG-109's render rule exempts it by this marker. */}
      {owner !== null ? <span data-user-text="">{owner}</span> : null}
    </span>
  );
}
