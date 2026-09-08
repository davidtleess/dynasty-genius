/** Read-only consumer of the accepted DG snapshot. No scoring or market calibration. */
export type RankInterval = { start: number; end: number; total: number };
export type Gap = {
  direction: "higher" | "lower" | "same" | "overlap" | "unavailable";
  gap_min: number | null;
  gap_max: number | null;
};
type Source = {
  report_run: string;
  report_sha256: string;
  catalog_run?: string;
  ownership_as_of?: string;
  [key: string]: unknown;
};
type RankRow = {
  sleeper_id: string;
  name: string;
  position: string;
  team: string | null;
  on_roster: boolean;
  league_ownership: string;
  taxi_or_reserve: boolean | null;
  model_value: number | null;
  model_zero_tie: boolean;
  market_value: number | null;
  our_rank: RankInterval | null;
  market_rank: RankInterval | null;
  model_rank_all: RankInterval | null;
  comparison: Gap;
  missing_reason: string | null;
  reference_player: string | null;
};
type ForecastRow = {
  sleeper_id: string;
  name: string;
  position: string;
  team?: string | null;
  now_points: number | null;
  future_points: number | null;
  seasons: Array<{ season: number; points: number | null; estimate_class?: string | null }>;
  starting_estimate: boolean;
  missing_reason?: string | null;
  evidence_note?: string | null;
};
type AvailableRow = {
  sleeper_id: string;
  name: string;
  league_position: string;
  nfl_team: string | null;
  population: string;
  owned_now: boolean;
  roster_id: number | null;
  availability_class?: string;
  starting_estimate: boolean;
  missing_reason?: string | null;
};
export type DgBundle = {
  kind: "dg.read-model.bundle";
  bundle_version: 1;
  generated_at: string;
  snapshot: Source & { forecast_date: string; market_as_of: string; ownership_as_of: string };
  basis: {
    summary: string;
    years: number[];
    scoring_note?: string;
    market_proxy_note?: string;
    [key: string]: unknown;
  };
  coverage: {
    total_players: number;
    common_players: number;
    roster_players: number;
    [key: string]: unknown;
  };
  populations: {
    default: {
      total: number;
      with_forecast?: number;
      without_forecast?: number;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  identity: { kind: string; path_template: string; ids: string[] | null; note?: string };
  payloads: {
    market_ranks: { status: string; source: Source; rows: RankRow[] };
    comparison: {
      source: Source;
      roster: ForecastRow[];
      available: ForecastRow[];
      forecast_years?: number[];
      future_years?: number[];
    };
    available: { source: Source & { pinned: boolean }; rows: AvailableRow[] };
  };
};
export type BoardRow = {
  player_id: string;
  full_name: string;
  position: string | null;
  team: string | null;
  headshot_url: string;
  our_rank: RankInterval | null;
  market_rank: RankInterval | null;
  model_rank_all: RankInterval | null;
  projected_advantage: number | null;
  model_zero_tie: boolean;
  market_value: number | null;
  comparison: Gap;
  now_points: number | null;
  future_points: number | null;
  seasons: ForecastRow["seasons"];
  starting_estimate: boolean;
  on_roster: boolean;
  roster_id: number | null;
  population: string;
  ownership: string;
  status: string | null;
  missing_reason: string | null;
  forecast_note: string | null;
  reference_player: string | null;
};
function object(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
function requireThat(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(`DG snapshot unavailable: ${message}`);
}
function interval(v: unknown, total: number) {
  requireThat(
    object(v) &&
      Number.isInteger(v["start"]) &&
      Number.isInteger(v["end"]) &&
      v["total"] === total &&
      Number(v["start"]) >= 1 &&
      Number(v["end"]) >= Number(v["start"]) &&
      Number(v["end"]) <= total,
    "invalid comparable rank",
  );
}
function finiteOrMissing(v: unknown) {
  return v === null || (typeof v === "number" && Number.isFinite(v));
}
function distinct(rows: Array<{ sleeper_id: string }>, label: string) {
  requireThat(
    rows.every((r) => typeof r.sleeper_id === "string" && /^\d+$/.test(r.sleeper_id)),
    `${label} player identity missing`,
  );
  requireThat(
    new Set(rows.map((r) => r.sleeper_id)).size === rows.length,
    `${label} duplicate player`,
  );
}
export function readBundle(value: unknown): DgBundle {
  requireThat(
    object(value) && value["kind"] === "dg.read-model.bundle" && value["bundle_version"] === 1,
    "unsupported bundle",
  );
  requireThat(
    object(value["snapshot"]) &&
      object(value["payloads"]) &&
      object(value["coverage"]) &&
      object(value["basis"]) &&
      object(value["populations"]),
    "missing source context",
  );
  const b = value as unknown as DgBundle;
  requireThat(
    typeof b.generated_at === "string" && Number.isFinite(Date.parse(b.generated_at)),
    "export time missing",
  );
  for (const key of [
    "report_run",
    "report_sha256",
    "forecast_date",
    "market_as_of",
    "ownership_as_of",
  ])
    requireThat(typeof b.snapshot[key] === "string" && b.snapshot[key], `missing ${key}`);
  requireThat(/^[a-f\d]{64}$/.test(b.snapshot.report_sha256), "invalid forecast hash");
  for (const name of ["market_ranks", "comparison", "available"] as const) {
    const part = b.payloads[name];
    requireThat(object(part) && object(part.source), `${name} source missing`);
    for (const key of ["report_run", "report_sha256"])
      requireThat(part.source[key] === b.snapshot[key], `${name} mixed forecast source`);
    for (const key of [
      "ownership_as_of",
      "market_as_of",
      "market_sha256",
      "league_sha256",
      "catalog_content_sha256",
    ])
      if (part.source[key] !== undefined)
        requireThat(part.source[key] === b.snapshot[key], `${name} mixed ${key}`);
    if (part.source.catalog_run !== undefined && b.snapshot.catalog_run !== undefined)
      requireThat(part.source.catalog_run === b.snapshot.catalog_run, `${name} mixed catalog`);
  }
  requireThat(
    b.payloads.market_ranks.status === "available" && b.payloads.available.source.pinned === true,
    "unavailable or unpinned source",
  );
  requireThat(
    Array.isArray(b.payloads.market_ranks.rows) &&
      Array.isArray(b.payloads.available.rows) &&
      Array.isArray(b.payloads.comparison.roster) &&
      Array.isArray(b.payloads.comparison.available),
    "missing player rows",
  );
  const { market_ranks: ranks, comparison: forecasts, available } = b.payloads;
  distinct(ranks.rows, "rank");
  distinct(available.rows, "available");
  distinct(forecasts.roster, "roster");
  distinct(forecasts.available, "forecast");
  requireThat(
    Number.isInteger(b.coverage.common_players) &&
      b.coverage.common_players >= 0 &&
      ranks.rows.length === b.coverage.total_players,
    "rank population differs",
  );
  requireThat(
    object(b.populations.default) &&
      available.rows.filter((r) => r.population === "default").length ===
        b.populations.default.total,
    "available population differs",
  );
  requireThat(forecasts.roster.length === b.coverage.roster_players, "roster population differs");
  const rosterIds = new Set(forecasts.roster.map((r) => r.sleeper_id));
  for (const row of ranks.rows) {
    requireThat(
      finiteOrMissing(row.model_value) && finiteOrMissing(row.market_value),
      "invalid value",
    );
    requireThat(row.on_roster === rosterIds.has(row.sleeper_id), "conflicting roster membership");
    requireThat(object(row.comparison), "comparison missing");
    if (row.our_rank !== null) interval(row.our_rank, b.coverage.common_players);
    if (row.market_rank !== null) interval(row.market_rank, b.coverage.common_players);
    if (row.our_rank === null || row.market_rank === null)
      requireThat(
        row.comparison.direction === "unavailable" &&
          row.comparison.gap_min === null &&
          row.comparison.gap_max === null,
        "comparison without two ranks",
      );
    else {
      const min = row.market_rank.start - row.our_rank.end,
        max = row.market_rank.end - row.our_rank.start;
      const direction =
        min > 0 ? "higher" : max < 0 ? "lower" : min === 0 && max === 0 ? "same" : "overlap";
      requireThat(
        row.comparison.gap_min === min &&
          row.comparison.gap_max === max &&
          row.comparison.direction === direction,
        "comparison disagrees with rank intervals",
      );
    }
  }
  for (const row of available.rows)
    requireThat(
      row.population !== "default" || (!row.owned_now && row.roster_id === null),
      "owned player marked available",
    );
  for (const row of [...forecasts.roster, ...forecasts.available])
    requireThat(
      finiteOrMissing(row.now_points) && finiteOrMissing(row.future_points),
      "invalid forecast",
    );
  return b;
}
export function boardRows(bundle: DgBundle): BoardRow[] {
  const ranks = new Map(bundle.payloads.market_ranks.rows.map((r) => [r.sleeper_id, r]));
  const forecasts = new Map(
    [...bundle.payloads.comparison.available, ...bundle.payloads.comparison.roster].map((r) => [
      r.sleeper_id,
      r,
    ]),
  );
  const available = new Map(bundle.payloads.available.rows.map((r) => [r.sleeper_id, r]));
  const mine = new Set(bundle.payloads.comparison.roster.map((r) => r.sleeper_id));
  const ids = new Set([...ranks.keys(), ...forecasts.keys(), ...available.keys()]);
  return [...ids].map((id) => {
    const r = ranks.get(id),
      f = forecasts.get(id),
      a = available.get(id);
    return {
      player_id: id,
      full_name: r?.name ?? f?.name ?? a?.name ?? "Player unavailable",
      position: r?.position ?? f?.position ?? a?.league_position ?? null,
      team: r?.team ?? f?.team ?? a?.nfl_team ?? null,
      headshot_url: `/assets/headshots/${encodeURIComponent(id)}.jpg`,
      our_rank: r?.our_rank ?? null,
      market_rank: r?.market_rank ?? null,
      model_rank_all: r?.model_rank_all ?? null,
      projected_advantage: r?.model_value ?? null,
      model_zero_tie: r?.model_zero_tie === true,
      market_value: r?.market_value ?? null,
      comparison: r?.comparison ?? {
        direction: "unavailable" as const,
        gap_min: null,
        gap_max: null,
      },
      now_points: f?.now_points ?? null,
      future_points: f?.future_points ?? null,
      seasons: f?.seasons ?? [],
      starting_estimate: f?.starting_estimate ?? a?.starting_estimate ?? false,
      on_roster: mine.has(id),
      roster_id: a?.roster_id ?? null,
      population: a?.population ?? (mine.has(id) ? "owned" : "outside_available_catalog"),
      ownership: mine.has(id)
        ? "Your roster"
        : (r?.league_ownership ??
          (a?.owned_now
            ? "Rostered in your league"
            : a?.population === "default"
              ? "League free agent"
              : "Ownership not available")),
      status: a?.availability_class ?? null,
      missing_reason: r
        ? r.missing_reason
        : f
          ? (f.missing_reason ?? null)
          : (a?.missing_reason ?? null),
      forecast_note: f?.evidence_note ?? null,
      reference_player: r?.reference_player ?? null,
    };
  });
}
export function alternativesFor(rows: BoardRow[], playerId: string): BoardRow[] {
  const player = rows.find((r) => r.player_id === playerId);
  if (!player) return [];
  return rows
    .filter(
      (r) =>
        r.player_id !== playerId &&
        r.position === player.position &&
        r.population === "default" &&
        !r.on_roster &&
        r.roster_id === null,
    )
    .sort(
      (a, b) =>
        (b.now_points ?? -Infinity) - (a.now_points ?? -Infinity) ||
        a.full_name.localeCompare(b.full_name),
    );
}
export function comparisonPair(
  rows: BoardRow[],
  first: string,
  second: string,
): [BoardRow, BoardRow] {
  requireThat(first !== second, "choose two different players");
  const a = rows.find((r) => r.player_id === first),
    b = rows.find((r) => r.player_id === second);
  requireThat(a && b, "selected player missing");
  return [a, b];
}
export function rankLabel(rank: RankInterval | null): string {
  return rank ? (rank.start === rank.end ? String(rank.start) : `${rank.start}–${rank.end}`) : "—";
}
export function gapLabel(row: Pick<BoardRow, "comparison">): string {
  const c = row.comparison;
  if (c.direction === "unavailable") return "No comparison";
  if (c.direction === "overlap") return "Ranks overlap";
  if (c.direction === "same") return "Same rank";
  if (c.gap_min === null || c.gap_max === null) return "No comparison";
  const direction = c.direction;
  const min = Math.min(Math.abs(c.gap_min), Math.abs(c.gap_max));
  return c.gap_min === c.gap_max
    ? `${min} places ${direction}`
    : `${min}–${Math.max(Math.abs(c.gap_min), Math.abs(c.gap_max))} places ${direction}`;
}

export function forecastLabels(years: number[]): { current: string; future: string } {
  const first = years[0];
  const future = years.slice(1);
  const last = future.at(-1);
  return {
    current: first == null ? "Season points" : `${first} points`,
    future:
      future.length === 0
        ? "Future total"
        : future.length === 1
          ? `${last} total`
          : `${future[0]}–${last} total`,
  };
}

/** Match the accepted board's display rule: nonzero forecasts never round to zero. */
export function pointsLabel(value: number): string {
  if (value === 0) return "0.0";
  if (Math.abs(value) >= 0.1) return value.toFixed(1);
  for (const decimals of [2, 3, 4]) {
    const shown = value.toFixed(decimals);
    if (Number(shown) !== 0) return shown;
  }
  return value > 0 ? "+<0.0001" : "-<0.0001";
}
