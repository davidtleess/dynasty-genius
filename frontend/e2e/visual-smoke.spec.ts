// H2 reset Task 1 — browser evidence capture (reset spec §6 Task 1).
// CAPTURE-FIRST: this spec produces evidence artifacts (screenshots, a focus
// capture, an axe report). It is not a pass gate for visual quality — the
// artifacts ARE the deliverable, and failures they reveal feed the debt
// register (D3 semantics). No goldens, no toHaveScreenshot, no CI wiring.
// Route mocks only: no gitignored artifact is ever read.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

const ARTIFACT_DIR = "artifacts/visual";

const structuralSection = {
  status: "ok",
  decision_supported: false,
  current_not_delta: true,
};

const whatChanged = {
  schema_version: "war_room_2_what_changed_v1",
  generated_at: "2026-07-05T13:45:00Z",
  decision_supported: false,
  overall_status: "ok",
  daily_diff: {
    decision_supported: false,
    overall_status: "ok",
    market: {
      status: "ok",
      decision_supported: false,
      market_source: "keeptradecut",
      comparison_window: { from_date: "2026-07-04", to_date: "2026-07-05" },
      roster_deltas: [
        {
          sleeper_id: "player-1",
          player_key: "player-1",
          player_name: "Delta Receiver",
          position: "WR",
          team_id: "SEA",
          model_series: null,
          market_series: {
            basis: "fc_forward_capture_joinable.value",
            points: [
              { date: "2026-07-04", value: 100 },
              { date: "2026-07-05", value: 92 },
            ],
          },
          value_delta: -8,
          value_delta_direction: "down",
          overall_rank_delta: 14,
          overall_rank_delta_direction: "down",
          position_rank_delta: -2,
          position_rank_delta_direction: "up",
        },
      ],
      top_movers: [
        {
          sleeper_id: "player-2",
          player_key: "player-2",
          player_name: "Market Mover",
          position: "RB",
          team_id: "ATL",
          model_series: null,
          market_series: {
            basis: "fc_forward_capture_joinable.value",
            points: [
              { date: "2026-07-04", value: 100 },
              { date: "2026-07-05", value: 111 },
            ],
          },
          value_delta: 11,
          value_delta_direction: "up",
          overall_rank_delta: -9,
          overall_rank_delta_direction: "up",
          position_rank_delta: 3,
          position_rank_delta_direction: "down",
        },
      ],
      total_movers_count: 2,
      entered: [{ sleeper_id: "player-3", player_key: "Entered Rookie" }],
      exited: [{ sleeper_id: "player-4", player_key: "Exited Veteran" }],
    },
    model: {
      status: "ok",
      decision_supported: false,
      comparison_window: { from_date: "2026-07-04", to_date: "2026-07-05" },
      deltas: [
        {
          sleeper_id: "player-5",
          player_key: "player-5",
          player_name: "Model Delta",
          position: "QB",
          team_id: "BUF",
          model_series: {
            basis: "model_forward_capture_joinable.dynasty_value_score",
            points: [
              { date: "2026-07-04", value: 81.25 },
              { date: "2026-07-05", value: 80 },
            ],
          },
          market_series: null,
          dynasty_value_score_delta: -1.25,
          dynasty_value_score_delta_direction: "down",
          dvs_pct_delta: 0.04,
          xvar_delta: -0.75,
        },
      ],
      vintage_changed: false,
      feature_freshness: null,
      pvo_staleness: null,
    },
  },
  structural_context: {
    ...structuralSection,
    sections: {
      team_posture: structuralSection,
      team_value: structuralSection,
      league_opportunity: structuralSection,
      drop_pressure: structuralSection,
      sleeper_snapshot: structuralSection,
    },
  },
};

const captureHealth = {
  checked_at: "2026-07-05T09:00:00-04:00",
  config_version: 3,
  decision_supported: false,
  overall_status: "ok",
  stores: [
    {
      caveats: [],
      decision_supported: false,
      density: {
        baseline_median_rows: 7400,
        baseline_window: 7,
        floor_pct: 80,
        sub_floor_dates: [],
      },
      flags: {
        warn_basis: "ok",
        warn_missing: false,
        window_risk: false,
        window_risk_basis: "ok",
      },
      staleness: {
        expected_by: "2026-07-05T10:00:00-04:00",
        grace_hours: 24,
        last_capture_date: "2026-07-05",
        stale: false,
      },
      store_id: "fc_forward_capture",
      store_presence: "present",
      store_status: "ok",
      // Field names verified against zStoreTimeline in the generated client —
      // the harness's first catch was this fixture inventing its own names.
      timeline: {
        capture_start_date: "2026-06-24",
        consecutive_days_current: 12,
        expected_days: 12,
        first_date: "2026-06-24",
        last_date: "2026-07-05",
        max_contiguous_gap_days: 0,
        missing_dates_count: 0,
        missing_ranges: [],
        missing_ranges_total: 0,
        present_days: 12,
      },
    },
  ],
};

const modelProvenance = {
  artifacts: [
    {
      artifact_id: "engine_b_v2",
      decision_supported: false,
      expected_kind: "tracked_seed",
      load_verification_status: "verified",
      observed_status: "ok",
      path: "app/data/models/engine_b/latest.pkl",
      pointer_status: "referenced",
      promotion_status: "active",
      serving_allowed: true,
      severity: "info",
    },
  ],
  decision_supported: false,
  environment: "serving",
  overall_status: "ok",
  registry_version: 4,
};

const health = {
  checked_at: "2026-07-05T14:55:00+00:00",
  config_version: 1,
  decision_supported: false,
  disclaimer:
    "System health reflects pipeline completion, artifact freshness, and model provenance verification. It does not evaluate model accuracy or guarantee trade edge.",
  overall_status: "ok",
  reports: [],
  subsystems: [],
  worst_affected_tier: null,
};

// Verbatim from TrustStrip.test.jsx trustSurfaceResponse() — a known
// schema-valid shape (the harness's first run caught an invented fixture).
const trust = {
  divergence_validity: null,
  experimental: true,
  folds: [],
  git_sha: "56b3b84",
  market_snapshot_dates: { 2025: "2025-09-08" },
  market_source: "fc_native",
  market_source_label: "fantasycalc_native",
  model_artifact_hash: "abc123",
  model_card_available: true,
  model_reliability: {
    caveat: "QB magnitude predictions carry elevated uncertainty.",
    position: "QB",
    r2_oos_mean: null,
    spearman_rho_mean: 0.42,
  },
  model_status: "EXPERIMENTAL",
  model_version: "engine_b_v2",
  overall_grade: "EXPERIMENTAL",
  position: "QB",
  promotion_gate: {
    g1_rank_correlation_pass: false,
    g2_rmse_stability_pass: false,
    g3_market_superiority_pass: "deferred",
    g4_divergence_validity_pass: "deferred",
    gate_version: "1.0",
    model_status: "EXPERIMENTAL",
    overall_grade: "EXPERIMENTAL",
    promotion_justification: "evidence fixture",
  },
  retrain_mode: "refit_per_fold_fixed_alpha",
  ridge_alpha: 200,
  rmse_stability: {
    dm_hln_pvalue: null,
    dm_hln_statistic: null,
    dm_method: "harvey_leybourne_newbold_1997",
    dm_passes: null,
    rmse_cv: 0.1,
    rmse_max_deviation_pct: 0.2,
    rmse_mean: 3.1,
    rmse_per_fold: [3.2, 3.0, 3.1, 3.1],
  },
  run_date: "2026-06-04T22:57:17Z",
  run_id: "11111111-1111-4111-8111-111111111111",
  schema_version: "1.0.0",
};

test("daily open evidence bundle: desktop, mobile, focus capture, axe report", async ({
  page,
}) => {
  mkdirSync(ARTIFACT_DIR, { recursive: true });

  await page.route("**/api/league/what-changed", (route) =>
    route.fulfill({ json: whatChanged }),
  );
  await page.route("**/api/system/capture-health", (route) =>
    route.fulfill({ json: captureHealth }),
  );
  await page.route("**/api/system/model-provenance", (route) =>
    route.fulfill({ json: modelProvenance }),
  );
  await page.route("**/api/health", (route) => route.fulfill({ json: health }));
  await page.route("**/api/trust-surface/QB", (route) =>
    route.fulfill({ json: trust }),
  );

  // Desktop evidence.
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto("/?surface=what-changed");
  await page.getByText("Market Mover").waitFor();
  await page.screenshot({
    path: `${ARTIFACT_DIR}/daily-open-desktop.png`,
    fullPage: true,
  });

  // Increment 1: primitive-specific focus evidence. Focus must land on an
  // AssetRow receipt control, not merely the shell rail.
  const firstReceipt = page.getByRole("button", { name: /provenance for/i }).first();
  await expect(firstReceipt).toBeVisible({ timeout: 1500 });
  await firstReceipt.focus();
  await expect(firstReceipt).toBeFocused();
  await page.screenshot({
    path: `${ARTIFACT_DIR}/daily-open-primitive-focus-capture.png`,
  });

  // Axe accessibility smoke over the main region. Increment 1 hardens this
  // evidence surface: the report is still written, but violations fail RED.
  const axeResults = await new AxeBuilder({ page }).include("main").analyze();
  writeFileSync(
    `${ARTIFACT_DIR}/axe-report.json`,
    JSON.stringify(
      {
        captured_at: "run-time artifact",
        violation_count: axeResults.violations.length,
        violations: axeResults.violations,
      },
      null,
      2,
    ),
  );
  expect(axeResults.violations).toEqual([]);

  // Mobile evidence.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?surface=what-changed");
  await page.getByText("Market Mover").waitFor();
  await page.screenshot({
    path: `${ARTIFACT_DIR}/daily-open-mobile.png`,
    fullPage: true,
  });
});

test("asset primitive capture evidence bundle asserts axe zero", async ({ page }) => {
  mkdirSync(ARTIFACT_DIR, { recursive: true });

  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto("/?surface=asset-primitive-capture");
  await page.getByText("Asset primitive capture").waitFor();
  await page.screenshot({
    path: `${ARTIFACT_DIR}/asset-primitive-capture-desktop.png`,
    fullPage: true,
  });

  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.screenshot({
    path: `${ARTIFACT_DIR}/asset-primitive-capture-focus.png`,
  });

  const axeResults = await new AxeBuilder({ page }).include("main").analyze();
  writeFileSync(
    `${ARTIFACT_DIR}/asset-primitive-capture-axe-report.json`,
    JSON.stringify(
      {
        captured_at: "run-time artifact",
        violation_count: axeResults.violations.length,
        violations: axeResults.violations,
      },
      null,
      2,
    ),
  );
  expect(axeResults.violations).toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/?surface=asset-primitive-capture");
  await page.getByText("Asset primitive capture").waitFor();
  await page.screenshot({
    path: `${ARTIFACT_DIR}/asset-primitive-capture-mobile.png`,
    fullPage: true,
  });
});
