// Trade Lab draft state — pure helpers + ephemeral localStorage persistence.
// No server-side UI state; v1 keeps the in-progress trade in the browser only.

export type CatalogEntry = {
  asset_id: string;
  label: string;
  [key: string]: unknown;
};

export type Side = "sent" | "received";

export type Trade = {
  sent: CatalogEntry[];
  received: CatalogEntry[];
  counterpartyRosterId: number | null;
};

const KEY = "dg.tradeLab.draft";

export const emptyTrade = (): Trade => ({
  sent: [],
  received: [],
  counterpartyRosterId: null,
});

export function addAsset(trade: Trade, side: Side, entry: CatalogEntry): Trade {
  return { ...trade, [side]: [...trade[side], entry] };
}

export function removeAsset(trade: Trade, side: Side, assetId: string): Trade {
  return { ...trade, [side]: trade[side].filter((a) => a.asset_id !== assetId) };
}

export function saveTrade(trade: Trade): void {
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify(trade));
  } catch {
    // Persistence is best-effort/ephemeral; never throw on a quota/availability error.
  }
}

function isValidTrade(value: unknown): value is Trade {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    Array.isArray(candidate.sent) &&
    Array.isArray(candidate.received) &&
    (candidate.counterpartyRosterId === null ||
      typeof candidate.counterpartyRosterId === "number")
  );
}

export function loadTrade(): Trade {
  try {
    const raw = globalThis.localStorage?.getItem(KEY);
    if (raw) {
      // "Corrupt" includes valid JSON with the wrong shape (e.g. "null",
      // {"sent":null}); guard the shape so TradeLab never renders a bad Trade.
      const parsed: unknown = JSON.parse(raw);
      if (isValidTrade(parsed)) {
        return parsed;
      }
    }
  } catch {
    // Invalid JSON syntax → fall back to an empty draft.
  }
  return emptyTrade();
}
