/**
 * DG-208 — one synthetic view per state the execution contract names.
 *
 * Published early and deliberately: root and DG-207 can correct the shape here while it is still
 * cheap, and every browser test drives one of these through an intercept rather than a live route.
 * Numbers are synthetic and the players are invented.
 *
 * Two rules these fixtures exist to hold the UI to:
 *   · `observations` is ALWAYS present, so an enrolled-but-ungraded reading can show its frozen
 *     forecasts and baselines with `outcome` and `error` null. That is not a grade.
 *   · An absent value is null and stays null. Nothing here lets the screen read a missing row as 0.
 */
export type SixSourceFields = {
  report_run: string;
  report_sha256: string;
  market_sha256: string;
  league_sha256: string;
  catalog_run: string;
  catalog_content_sha256: string;
};

export type ResultRow = {
  sleeper_id: string;
  name: string;
  position: string;
  producer: string | null;
  provenance: string;
  forecast: number | null;
  baseline: number | null;
  baseline_position_median?: number | null;
  outcome: number | null;
  error: number | null;
  reason: string | null;
};

export type StreamState =
  | "not_registered"
  | "awaiting_horizon"
  | "awaiting_capture"
  | "input_unavailable"
  | "cutoff_ineligible"
  | "insufficient_evidence"
  | "graded";

const SOURCE: SixSourceFields = {
  report_run: "20260906T214512Z",
  report_sha256: "a".repeat(64),
  market_sha256: "b".repeat(64),
  league_sha256: "c".repeat(64),
  catalog_run: "20260907T013635Z",
  catalog_content_sha256: "d".repeat(64),
};

export const receipt = (over: Partial<Record<string, unknown>> = {}) => ({
  snapshot_id: "e".repeat(64),
  saved_at: "2026-09-08T01:38:00+00:00",
  forecast_date: "2026-09-06",
  market_as_of: "2026-09-06T00:00:00+00:00",
  ownership_as_of: "2026-09-06T00:00:00+00:00",
  report_generated_at: "2026-09-06T21:45:12+00:00",
  catalog_generated_at: "2026-09-07T01:36:35+00:00",
  years: [2026, 2027, 2028, 2029, 2030],
  counts: {
    model: 825,
    market: 399,
    market_picks: 24,
    paired: 388,
    roster: 27,
    available: 433,
    available_total: 510,
    available_with_forecasts: 360,
    available_without_forecasts: 73,
    starting_estimates: 7,
  },
  source: { ...SOURCE },
  evaluation_status: "ungraded" as const,
  evaluation_plan: { claim: "football_production", declared_at: "2026-09-08T01:38:00+00:00" },
  ...over,
});

const observations: ResultRow[] = [
  {
    sleeper_id: "1",
    name: "Alpha Arms",
    position: "QB",
    producer: "engine_b.v7",
    provenance: "original",
    forecast: 402.5,
    baseline: 310.25,
    baseline_position_median: 288.0,
    outcome: null,
    error: null,
    reason: null,
  },
  {
    sleeper_id: "2",
    name: "Bravo Bolt",
    position: "RB",
    producer: "engine_b.v7",
    provenance: "starting_estimate",
    forecast: 120.75,
    baseline: 140.0,
    baseline_position_median: 96.5,
    outcome: null,
    error: null,
    reason: null,
  },
  // Absent is absent. A screen that renders this as 0 has invented a season.
  {
    sleeper_id: "3",
    name: "Charlie Cast",
    position: "WR",
    producer: null,
    provenance: "unforecast",
    forecast: null,
    baseline: null,
    baseline_position_median: 74.25,
    outcome: null,
    error: null,
    reason: "No forecast was carried for him in this reading.",
  },
];

/**
 * Market rows are NOT production rows. Per the execution contract the same three columns carry an
 * ordinal gap, a trailing price momentum and an adjusted return. Reusing the production rows here made
 * the market block render as a duplicate of the production block, which is how a reader concludes the
 * two claims are one claim.
 */
const marketObservations: ResultRow[] = [
  {
    sleeper_id: "1",
    name: "Alpha Arms",
    position: "QB",
    producer: null,
    provenance: "original",
    forecast: 37,
    baseline: -0.041,
    baseline_position_median: null,
    outcome: null,
    error: null,
    reason: null,
  },
  {
    sleeper_id: "2",
    name: "Bravo Bolt",
    position: "RB",
    producer: null,
    provenance: "original",
    forecast: -12,
    baseline: 0.118,
    baseline_position_median: null,
    outcome: null,
    error: null,
    reason: null,
  },
  {
    sleeper_id: "3",
    name: "Charlie Cast",
    position: "WR",
    producer: null,
    provenance: "original",
    forecast: null,
    baseline: null,
    baseline_position_median: null,
    outcome: null,
    error: null,
    reason: "He carries no market price in this reading.",
  },
];

const stream = (state: StreamState, over: Record<string, unknown> = {}) => ({
  state,
  reason: null as string | null,
  window: { label: "2026 regular season", start_at: "2026-09-04", end_at: "2027-01-04" },
  provenance_class: "contemporaneous",
  counts: { eligible: 3, scored: 0, missing: 1 },
  observations,
  result: null,
  ...over,
});

const gradedResult = {
  summary: "Our forecast beat the prior-season baseline on the two players with an outcome.",
  comparisons: [
    {
      id: "engine_b.v7:prior_season",
      label: "Against each player's prior season",
      units: "points",
      estimate: -12.5,
      interval95: [-31.0, 6.0] as [number, number],
      state: "inconclusive" as const,
      note: "Two scored players is too few to separate from chance.",
      eligible: 3,
      scored: 2,
    },
  ],
  rows: observations.map((row, index) =>
    index === 2 ? row : { ...row, outcome: row.forecast! - 20, error: -20 },
  ),
  details: [
    {
      label: "What this cannot tell you",
      value: "Two scored players cannot establish an advantage.",
    },
    {
      label: "Baselines shown",
      value: "Prior season, and the position median for the same window.",
    },
  ],
};

export const views = {
  unavailable: {
    schema_version: "track_record.view.v1",
    status: "unavailable",
    reason: "The archive is not reachable from this session.",
    snapshots: [],
    selected: null,
    production: stream("input_unavailable", {
      observations: [],
      counts: { eligible: 0, scored: 0, missing: 0 },
    }),
    market: stream("input_unavailable", {
      observations: [],
      counts: { eligible: 0, scored: 0, missing: 0 },
    }),
    save_capability: { enabled: false, reason: "The archive is not reachable.", expected: null },
  },
  not_configured: {
    schema_version: "track_record.view.v1",
    status: "not_configured",
    reason: "No archive root is configured for this session.",
    snapshots: [],
    selected: null,
    production: stream("not_registered", {
      observations: [],
      counts: { eligible: 0, scored: 0, missing: 0 },
    }),
    market: stream("not_registered", {
      observations: [],
      counts: { eligible: 0, scored: 0, missing: 0 },
    }),
    save_capability: { enabled: false, reason: "No archive root is configured.", expected: null },
  },
  empty: {
    schema_version: "track_record.view.v1",
    status: "available",
    reason: null,
    snapshots: [],
    selected: null,
    production: stream("not_registered", {
      observations: [],
      counts: { eligible: 0, scored: 0, missing: 0 },
    }),
    market: stream("not_registered", {
      observations: [],
      counts: { eligible: 0, scored: 0, missing: 0 },
    }),
    save_capability: { enabled: true, reason: null, expected: { ...SOURCE } },
  },
  enrolledPending: {
    schema_version: "track_record.view.v1",
    status: "available",
    reason: null,
    snapshots: [receipt()],
    selected: receipt(),
    production: stream("awaiting_horizon", {
      reason: "The 2026 regular season has not finished, so nothing can be scored yet.",
    }),
    market: stream("awaiting_capture", {
      reason: "No later market capture has been recorded for this window yet.",
      observations: marketObservations,
    }),
    save_capability: { enabled: true, reason: null, expected: { ...SOURCE } },
  },
  inputUnavailable: {
    schema_version: "track_record.view.v1",
    status: "available",
    reason: null,
    snapshots: [receipt()],
    selected: receipt(),
    production: stream("input_unavailable", {
      reason: "No frozen baseline was recorded for this reading, so it cannot be scored.",
      observations: [],
      counts: { eligible: 3, scored: 0, missing: 3 },
    }),
    market: stream("cutoff_ineligible", {
      reason: "This reading was saved after the declared cutoff for the market window.",
      observations: [],
      counts: { eligible: 0, scored: 0, missing: 0 },
    }),
    save_capability: { enabled: true, reason: null, expected: { ...SOURCE } },
  },
  graded: {
    schema_version: "track_record.view.v1",
    status: "available",
    reason: null,
    snapshots: [receipt()],
    selected: receipt(),
    production: stream("graded", {
      counts: { eligible: 3, scored: 2, missing: 1 },
      result: gradedResult,
    }),
    market: stream("insufficient_evidence", {
      reason: "One capture is not a movement.",
      counts: { eligible: 3, scored: 1, missing: 2 },
      observations: marketObservations,
    }),
    save_capability: { enabled: true, reason: null, expected: { ...SOURCE } },
  },
  twoSameDay: {
    schema_version: "track_record.view.v1",
    status: "available",
    reason: null,
    snapshots: [
      receipt(),
      receipt({ snapshot_id: "f".repeat(64), saved_at: "2026-09-08T14:02:00+00:00" }),
    ],
    selected: receipt(),
    production: stream("awaiting_horizon"),
    market: stream("awaiting_capture", { observations: marketObservations }),
    save_capability: { enabled: true, reason: null, expected: { ...SOURCE } },
  },
} as const;

export const captureResults = {
  saved: {
    snapshot_status: "saved",
    snapshot: receipt(),
    enrollment_status: "saved",
    reason: null,
  },
  alreadySaved: {
    snapshot_status: "already_saved",
    snapshot: receipt(),
    enrollment_status: "already_saved",
    reason: null,
  },
  partial: {
    snapshot_status: "saved",
    snapshot: receipt(),
    enrollment_status: "input_unavailable",
    reason: "The reading was archived, but no baseline is configured so it was not enrolled.",
  },
} as const;
