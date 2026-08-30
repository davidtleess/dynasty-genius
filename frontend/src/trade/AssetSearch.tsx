import { useState } from "react";

import type { CatalogEntry } from "./tradeState";
import { useAssetCatalogSearch } from "./useAssetCatalogSearch";

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
  filter,
}: {
  onSelect: (entry: CatalogEntry) => void;
  /** Accessible name for the box — the shell's copy differs from Trade Lab's. */
  label?: string;
  placeholder?: string | undefined;
  /** Optional gate: offer only results this caller can actually open. */
  filter?: ((entry: CatalogEntry) => boolean) | undefined;
}) {
  const [query, setQuery] = useState("");
  const search = useAssetCatalogSearch(query);
  const results = filter === undefined ? search.results : search.results.filter(filter);

  return (
    <div className="dg-asset-search">
      <input
        type="search"
        className="dg-asset-search__input"
        aria-label={label}
        placeholder={placeholder}
        onChange={(event) => setQuery(event.target.value)}
      />
      {/* A silent empty box is a dead end and, after a failed read, a lie:
          an empty catalog answer and an unreadable one say different things. */}
      {search.status === "unavailable" && (
        <p className="dg-asset-search__notice" role="status">
          Search is down right now — we could not read the player list.
        </p>
      )}
      {search.status === "ready" && results.length === 0 && (
        <p className="dg-asset-search__notice" role="status">
          Nobody we track matches that.
        </p>
      )}
      <ul className="dg-asset-search__results">
        {results.map((entry) => (
          <li key={entry.asset_id}>
            <button type="button" onClick={() => onSelect(entry)}>
              {entry.label}
            </button>
            <ResultMeta entry={entry} />
          </li>
        ))}
      </ul>
    </div>
  );
}

// Position and the team that rosters him, when the catalog carries them —
// enough to tell two same-named players apart. Rendered OUTSIDE the button so
// the button's accessible name stays the player's name. Absence renders
// nothing: an unrostered player gets no invented "free agent" label.
function ResultMeta({ entry }: { entry: CatalogEntry }) {
  const position = typeof entry.position === "string" ? entry.position : null;
  const owner =
    typeof entry.roster_owner_name === "string" ? entry.roster_owner_name : null;
  const parts = [position, owner].filter((part): part is string => part !== null);
  if (parts.length === 0) {
    return null;
  }
  return <span className="dg-asset-search__meta">{parts.join(" · ")}</span>;
}
