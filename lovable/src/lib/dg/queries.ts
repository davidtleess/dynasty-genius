import { queryOptions } from "@tanstack/react-query";
import { alternativesFor, boardRows, readBundle, type DgBundle } from "./backend";
export type { BoardRow } from "./backend";
export type Scope = "mine" | "league" | "universe" | "available";

// One snapshot per page load: every view shares the same immutable response.
// Reload is explicit because this preview intentionally represents a saved research snapshot.
let snapshotRequest: Promise<DgBundle> | undefined;
function snapshot(): Promise<DgBundle> {
  if (!snapshotRequest)
    snapshotRequest = fetch("/data/dg-bundle.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("The saved DG snapshot could not be loaded.");
        return response.json();
      })
      .then(readBundle);
  return snapshotRequest;
}
const saved = {
  staleTime: Infinity,
  gcTime: Infinity,
  retry: false,
  refetchOnWindowFocus: false,
  enabled: typeof window !== "undefined",
} as const;
export const bundleQuery = queryOptions({
  ...saved,
  queryKey: ["dg", "bundle"],
  queryFn: snapshot,
});
export const healthQuery = queryOptions({
  ...saved,
  queryKey: ["dg", "health"],
  queryFn: async () => {
    const b = await snapshot();
    return {
      snapshot: b.snapshot,
      basis: b.basis,
      coverage: b.coverage,
      populations: b.populations,
    };
  },
});
export function boardQuery(scope: Scope, rosterId?: number) {
  return queryOptions({
    ...saved,
    queryKey: ["dg", "board", scope, rosterId ?? null],
    queryFn: async () => {
      const rows = boardRows(await snapshot());
      if (scope === "mine") return rows.filter((r) => r.on_roster);
      if (scope === "available") return rows.filter((r) => r.population === "default");
      if (scope === "league")
        return rows.filter((r) =>
          rosterId != null ? r.roster_id === rosterId : r.population === "owned" || r.on_roster,
        );
      return rows;
    },
  });
}
export function playerQuery(playerId: string | null) {
  return queryOptions({
    ...saved,
    enabled: saved.enabled && !!playerId,
    queryKey: ["dg", "player", playerId],
    queryFn: async () => {
      if (!playerId) return null;
      const b = await snapshot();
      const rows = boardRows(b);
      const current = rows.find((r) => r.player_id === playerId);
      return current
        ? {
            current,
            history: [],
            alternatives: alternativesFor(rows, playerId),
            snapshot: b.snapshot,
            basis: b.basis,
          }
        : null;
    },
  });
}
export function searchQuery(term: string) {
  return queryOptions({
    ...saved,
    enabled: saved.enabled && term.trim().length >= 2,
    queryKey: ["dg", "search", term],
    queryFn: async () => {
      const normalized = term.trim().toLocaleLowerCase();
      return boardRows(await snapshot())
        .filter((r) => r.full_name.toLocaleLowerCase().includes(normalized))
        .slice(0, 20);
    },
  });
}
// This first integration does not export team names or transactions. Routes must say so.
export const teamsQuery = queryOptions({
  ...saved,
  queryKey: ["dg", "teams"],
  queryFn: async (): Promise<never[]> => [],
});
export const transactionsQuery = queryOptions({
  ...saved,
  queryKey: ["dg", "transactions"],
  queryFn: async (): Promise<never[]> => [],
});
