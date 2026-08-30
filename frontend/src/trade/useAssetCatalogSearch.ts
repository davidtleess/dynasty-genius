import { useEffect, useState } from "react";

import { zTradeAssetCatalogResponse } from "../lib/api/zod.gen";
import type { CatalogEntry } from "./tradeState";

// The read-only asset catalog search, extracted from AssetSearch (DG-110) so
// the shell's global player search, the Trade Lab box and the command palette
// all run ONE implementation of the SR-15 stale-response contract instead of
// three.
//
// Each request parses a large catalog server-side, so responses resolve out of
// order; the debounce + per-request abort keep results pinned to the text
// currently in the box. One in-flight request at a time — deliberately no
// caching, no retry.
const DEBOUNCE_MS = 200;
// Exported so a caller can SAY the rule rather than leave a short query looking
// like a search that found nothing (DG-114: the palette is the phone's only
// player finder, and silence there reads as absence).
export const MIN_QUERY_LENGTH = 3;

// The server sorts matches by xVAR descending and cuts the list here, so a
// broad query silently returns a top-N. We send the cap explicitly rather than
// leaning on the endpoint default, so callers can say "the first N" and have
// that number be true (DG-110 panel: undisclosed truncation).
export const CATALOG_PAGE_SIZE = 50;

// "No match" and "we could not read the list" are different facts and must not
// collapse into one silent empty list: idle (nothing asked yet / too short),
// ready (the catalog answered — results may legitimately be empty) and
// unavailable (not-ok, bad shape, or a network failure).
export type CatalogSearchState =
  | { status: "idle"; results: [] }
  | { status: "ready"; results: CatalogEntry[] }
  | { status: "unavailable"; results: [] };

const IDLE: CatalogSearchState = { status: "idle", results: [] };
const UNAVAILABLE: CatalogSearchState = { status: "unavailable", results: [] };

export function useAssetCatalogSearch(query: string): CatalogSearchState {
  const [state, setState] = useState<CatalogSearchState>(IDLE);
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    // Min-length guard mirrors the backend OOM guard; never query the universe
    // on an empty/short input.
    if (debouncedQuery.trim().length < MIN_QUERY_LENGTH) {
      setState(IDLE);
      return;
    }
    const controller = new AbortController();

    async function run(): Promise<void> {
      try {
        const response = await fetch(
          `/api/trade/assets?q=${encodeURIComponent(debouncedQuery)}&limit=${CATALOG_PAGE_SIZE}`,
          { signal: controller.signal },
        );
        if (controller.signal.aborted) {
          return;
        }
        if (!response.ok) {
          setState(UNAVAILABLE);
          return;
        }
        const body: unknown = await response.json();
        if (controller.signal.aborted) {
          return;
        }
        const parsed = zTradeAssetCatalogResponse.safeParse(body);
        setState(
          parsed.success
            ? { status: "ready", results: parsed.data.results as CatalogEntry[] }
            : UNAVAILABLE,
        );
      } catch {
        // Abort of a superseded request is not an error and must not clear
        // results; anything else on a live request degrades to unavailable.
        if (!controller.signal.aborted) {
          setState(UNAVAILABLE);
        }
      }
    }

    void run();
    return () => controller.abort();
  }, [debouncedQuery]);

  return state;
}
