import { useEffect, useState } from "react";

import { zTradeAssetCatalogResponse } from "../lib/api/zod.gen";
import type { CatalogEntry } from "./tradeState";

// Each request parses a large catalog server-side, so responses resolve out of
// order; the debounce + per-request abort below keep the dropdown pinned to
// the text currently in the box (SR-15). One in-flight request at a time —
// deliberately no caching, no retry.
const DEBOUNCE_MS = 200;

// Reads the read-only asset catalog and validates the 200 at the SDK boundary
// with the generated Zod schema (same honest-degradation pattern as TrustStrip):
// any non-ok response or shape mismatch clears results rather than rendering raw.
export function AssetSearch({ onSelect }: { onSelect: (entry: CatalogEntry) => void }) {
  const [results, setResults] = useState<CatalogEntry[]>([]);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    // Min-length guard mirrors the backend OOM guard; never query the universe
    // on an empty/short input.
    if (debouncedQuery.trim().length < 3) {
      setResults([]);
      return;
    }
    const controller = new AbortController();

    async function run(): Promise<void> {
      try {
        const response = await fetch(
          `/api/trade/assets?q=${encodeURIComponent(debouncedQuery)}`,
          {
            signal: controller.signal,
          },
        );
        if (controller.signal.aborted) {
          return;
        }
        if (!response.ok) {
          setResults([]);
          return;
        }
        const body: unknown = await response.json();
        if (controller.signal.aborted) {
          return;
        }
        const parsed = zTradeAssetCatalogResponse.safeParse(body);
        setResults(parsed.success ? (parsed.data.results as CatalogEntry[]) : []);
      } catch {
        // Abort of a superseded request is not an error and must not clear
        // results; anything else on a live request degrades to empty.
        if (!controller.signal.aborted) {
          setResults([]);
        }
      }
    }

    void run();
    return () => controller.abort();
  }, [debouncedQuery]);

  return (
    <div className="dg-asset-search">
      <input
        type="search"
        aria-label="Search tradeable assets"
        onChange={(event) => setQuery(event.target.value)}
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
