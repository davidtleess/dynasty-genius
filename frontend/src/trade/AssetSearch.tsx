import { useState } from "react";

import { zTradeAssetCatalogResponse } from "../lib/api/zod.gen";
import type { CatalogEntry } from "./tradeState";

// Reads the read-only asset catalog and validates the 200 at the SDK boundary
// with the generated Zod schema (same honest-degradation pattern as TrustStrip):
// any non-ok response or shape mismatch clears results rather than rendering raw.
export function AssetSearch({ onSelect }: { onSelect: (entry: CatalogEntry) => void }) {
  const [results, setResults] = useState<CatalogEntry[]>([]);

  async function run(query: string): Promise<void> {
    // Min-length guard mirrors the backend OOM guard; never query the universe
    // on an empty/short input.
    if (query.trim().length < 3) {
      setResults([]);
      return;
    }
    try {
      const response = await fetch(`/api/trade/assets?q=${encodeURIComponent(query)}`);
      if (!response.ok) {
        setResults([]);
        return;
      }
      const parsed = zTradeAssetCatalogResponse.safeParse(await response.json());
      setResults(parsed.success ? (parsed.data.results as CatalogEntry[]) : []);
    } catch {
      setResults([]);
    }
  }

  return (
    <div className="dg-asset-search">
      <input
        type="search"
        aria-label="Search tradeable assets"
        onChange={(event) => void run(event.target.value)}
      />
      <ul className="dg-asset-search__results">
        {results.map((entry) => (
          <li key={entry.asset_id}>
            <button type="button" onClick={() => onSelect(entry)}>
              {entry.label}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
