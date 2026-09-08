import { z } from "zod";
import type { MarketRanksAvailable } from "../lib/api";
import type { Watchlist } from "../research/availableHelpers";
import type { ComparisonPayload } from "../research/comparisonHelpers";
import type { WorkspaceOrder, WorkspacePlayer } from "./types";

const number = z.number().finite();
const player = z.object({
  sleeper_id: z.string().min(1),
  name: z.string().min(1),
  position: z.string(),
  team: z.string().nullable(),
  population: z.string(),
  status: z.string(),
  now_points: number.nullable(),
  future_points: number.nullable(),
  seasons: z.array(
    z.object({
      season: z.number().int(),
      points: number.nullable(),
      estimate_class: z.string().nullable(),
    }),
  ),
  starting_estimate: z.boolean(),
  missing_reason: z.string().nullable(),
  evidence_note: z.string(),
  taxi_or_reserve: z.boolean().nullable().default(null),
});
const schema = z.object({
  source: z.object({
    report_run: z.string(),
    report_sha256: z.string(),
    catalog_run: z.string(),
    ownership_as_of: z.string().nullable(),
    nfl_status_as_of: z.string().nullable(),
  }),
  forecast_years: z.array(z.number().int()).min(2),
  future_years: z.array(z.number().int()).min(1),
  scoring_note: z.string(),
  roster: z.array(player),
  available: z.array(player),
});

/** Combine only two views of the same frozen research report and league snapshot. */
export function validateComparison(
  raw: unknown,
  ranks: MarketRanksAvailable,
): ComparisonPayload {
  const data = schema.parse(raw);
  const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
  const rankMap = new Map(ranks.rows.map((p) => [p.sleeper_id, p]));
  const all = [...data.roster, ...data.available];
  if (
    data.source.report_run !== ranks.source.report_run ||
    data.source.report_sha256 !== ranks.source.report_sha256 ||
    data.source.ownership_as_of !== ranks.source.ownership_as_of ||
    !same(data.forecast_years, ranks.basis.years) ||
    !same(data.future_years, ranks.basis.years.slice(1)) ||
    !same(
      data.roster.map((p) => p.sleeper_id).sort(),
      ranks.rows
        .filter((p) => p.on_roster)
        .map((p) => p.sleeper_id)
        .sort(),
    ) ||
    new Set(all.map((p) => p.sleeper_id)).size !== all.length ||
    all.some(
      (p) =>
        rankMap.has(p.sleeper_id) && rankMap.get(p.sleeper_id)?.position !== p.position,
    )
  )
    throw new Error("The forecast and ranking snapshots do not match.");
  return data;
}

export function joinWorkspacePlayers(
  data: MarketRanksAvailable,
  comparison: ComparisonPayload | null,
  watched: Watchlist,
): WorkspacePlayer[] {
  const ranks = new Map(data.rows.map((p) => [p.sleeper_id, p]));
  const forecasts = new Map(
    [...(comparison?.roster ?? []), ...(comparison?.available ?? [])].map((p) => [
      p.sleeper_id,
      p,
    ]),
  );
  const unowned = new Set(comparison?.available.map((p) => p.sleeper_id) ?? []);
  const ids = new Set([...ranks.keys(), ...forecasts.keys(), ...watched.keys()]);
  return [...ids].map((id) => {
    const rank = ranks.get(id) ?? null;
    const forecast = forecasts.get(id) ?? null;
    const saved = watched.get(id);
    const ownership: WorkspacePlayer["ownership"] = rank?.on_roster
      ? "roster"
      : unowned.has(id)
        ? forecast?.population === "default"
          ? "available"
          : "outside"
        : rank?.league_ownership === "Rostered in your league"
          ? "league"
          : "unknown";
    return {
      id,
      name:
        rank?.name ??
        forecast?.name ??
        saved?.name ??
        "Saved player · identity unavailable",
      position: rank?.position ?? forecast?.position ?? saved?.position ?? "?",
      team: rank?.team ?? forecast?.team ?? saved?.team ?? null,
      ownership,
      rank,
      forecast,
      watched: watched.has(id),
      watchedAt: saved?.watched_at ?? null,
    };
  });
}

export function minimumGap(p: WorkspacePlayer): number | null {
  const c = p.rank?.comparison;
  if (!c || c.direction === "unavailable") return null;
  if (c.direction === "higher") return c.gap_min;
  if (c.direction === "lower") return c.gap_max === null ? null : Math.abs(c.gap_max);
  return 0;
}
export function orderValue(p: WorkspacePlayer, order: WorkspaceOrder): number | null {
  if (order === "ours") return p.rank?.our_rank?.start ?? null;
  if (order === "market") return p.rank?.market_rank?.start ?? null;
  if (order === "gap") return minimumGap(p);
  if (order === "now") return p.forecast?.now_points ?? null;
  if (order === "future") return p.forecast?.future_points ?? null;
  return 0;
}
export function sortWorkspacePlayers(
  players: WorkspacePlayer[],
  order: WorkspaceOrder,
): { ranked: WorkspacePlayer[]; missing: WorkspacePlayer[] } {
  const ranked: WorkspacePlayer[] = [],
    missing: WorkspacePlayer[] = [];
  for (const p of players) (orderValue(p, order) === null ? missing : ranked).push(p);
  const name = (a: WorkspacePlayer, b: WorkspacePlayer) =>
    a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
  const asc = order === "ours" || order === "market" ? 1 : -1;
  ranked.sort(
    (a, b) =>
      asc * ((orderValue(a, order) ?? 0) - (orderValue(b, order) ?? 0)) || name(a, b),
  );
  missing.sort(name);
  return { ranked, missing };
}

export function matchesWorkspacePlayer(
  p: WorkspacePlayer,
  query: string,
  position: string,
): boolean {
  const q = query.trim().toLocaleLowerCase();
  return (
    (position === "all" || p.position === position) &&
    (!q ||
      [p.name, p.team ?? "", p.position].some((s) => s.toLocaleLowerCase().includes(q)))
  );
}
