// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  CaptureHealthResponse,
  ModelProvenanceResponse,
  WhatChangedResponse,
} from "../lib/api/types.gen";
import { zWhatChangedResponse } from "../lib/api/zod.gen";
import { AppShell } from "../shell/AppShell";
import { DailyWhatChanged } from "./DailyWhatChanged";

type ResponseOverrides = Partial<
  Omit<WhatChangedResponse, "daily_diff" | "structural_context">
> & {
  daily_diff?: Omit<Partial<WhatChangedResponse["daily_diff"]>, "market" | "model"> & {
    market?: Partial<WhatChangedResponse["daily_diff"]["market"]>;
    model?: Partial<WhatChangedResponse["daily_diff"]["model"]>;
  };
};

type StructuralSection =
  WhatChangedResponse["structural_context"]["sections"]["team_posture"];

function structuralSection(overrides: Partial<StructuralSection> = {}) {
  return {
    status: "ok",
    decision_supported: false,
    current_not_delta: true,
    ...overrides,
  };
}

function whatChangedResponse(overrides: ResponseOverrides = {}): WhatChangedResponse {
  const base = {
    schema_version: "war_room_2_what_changed_v1",
    generated_at: "2026-07-01T12:00:00+00:00",
    decision_supported: false,
    overall_status: "ok",
    daily_diff: {
      decision_supported: false,
      overall_status: "ok",
      market: {
        status: "ok",
        decision_supported: false,
        market_source: "keeptradecut",
        comparison_window: {
          from_date: "2026-06-30",
          to_date: "2026-07-01",
        },
        roster_deltas: [
          {
            sleeper_id: "player-1",
            player_key: "player-1",
            player_name: "Delta Receiver",
            position: "WR",
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
        comparison_window: {
          from_date: "2026-06-30",
          to_date: "2026-07-01",
          from_vintage: {
            semantic_output_hash: "semantic-old",
            provenance_hash: "provenance-old",
          },
          to_vintage: {
            semantic_output_hash: "semantic-new",
            provenance_hash: "provenance-new",
          },
        },
        deltas: [
          {
            sleeper_id: "player-5",
            player_key: "player-5",
            player_name: "Model Delta",
            position: "QB",
            dynasty_value_score_delta: -1.25,
            dynasty_value_score_delta_direction: "down",
            dvs_pct_delta: 0.04,
            xvar_delta: -0.75,
          },
        ],
        vintage_changed: true,
        feature_freshness: {
          decision_supported: false,
          feature_source_kind: "runtime",
          feature_csv_path: "app/data/features/latest.csv",
          feature_csv_sha256: "feature-sha",
          source_as_of: "2026-07-01",
        },
        pvo_staleness: {
          decision_supported: false,
          pvo_source_kind: "seed",
          pvo_path: "app/data/pvo/latest.csv",
          pvo_sha256: "pvo-sha",
          coverage_path: "app/data/pvo/coverage.json",
          coverage_sha256: "coverage-sha",
          source_as_of: "2026-06-29",
          seed_staleness: {
            decision_supported: false,
            promotion_review_threshold_crossed: true,
            count_model_supported_players_drifted_gt_5pct: 7,
            count_players_drifted_gt_5pct: 11,
            coverage_count_deltas: { QB: -1 },
            mean_abs_value_delta: 0.08,
            p95_abs_value_delta: 0.22,
            review_triggers: ["model_supported_players_gt_5pct"],
            seed_age_days: 2,
            seed_as_of: "2026-06-29",
          },
        },
      },
    },
    structural_context: {
      status: "ok",
      decision_supported: false,
      current_not_delta: true,
      sections: {
        team_posture: structuralSection({
          david_roster_id: 1,
          david_team_name: "David",
          david_posture: "Contender",
          team_count: 12,
          staleness_caveat: {
            basis: "team_posture_snapshot",
            report_generated_at: "2026-07-01T12:00:00+00:00",
            age_hours: 1.5,
            is_stale: true,
          },
        }),
        team_value: structuralSection({
          david_value_summary: {
            roster_id: 1,
            team_name: "David",
            posture_label: "Contender",
            lineup_xvar: 31.4,
            starter_weighted_xvar: 42.75,
            top_n_xvar: 88.2,
            total_xvar_capped: 104.6,
          },
        }),
        league_opportunity: structuralSection({
          status: "degraded",
          aborted_reason: "league_opportunity_partial_source",
          top_partner_rankings: [
            {
              counterparty_roster_id: 7,
              counterparty_team_name: "Partner One",
              partner_score: 0.82,
              matched_positions: ["WR", "RB"],
            },
            {
              counterparty_roster_id: 8,
              counterparty_team_name: "Partner Two",
              partner_score: 0.64,
              matched_positions: ["TE"],
            },
          ],
          top_cards: [
            {
              card_id: "card-1",
              card_type: "DIVERGENCE_MODEL_HIGH",
              asset_name: "Hidden Divergence Asset One",
            },
            {
              card_id: "card-2",
              card_type: "DIVERGENCE_MODEL_HIGH",
              asset_name: "Hidden Divergence Asset Two",
            },
            {
              card_id: "card-3",
              card_type: "DEPTH_CONTEXT",
              asset_name: "Hidden Depth Asset",
            },
          ],
        }),
        drop_pressure: {
          ...structuralSection({
            summary: {
              roster_id: 1,
              total_players: 30,
              total_capacity: 28,
              cuts_required: 2,
            },
          }),
          top_candidates: [
            {
              sleeper_player_id: "hidden-current-context",
              player_name: "Hidden Cut Candidate",
              position: "WR",
              cut_priority: 97,
            },
            {
              sleeper_player_id: "hidden-current-context-2",
              player_name: "Second Hidden Cut Candidate",
              position: "RB",
              cut_priority: 98,
            },
          ],
        },
        sleeper_snapshot: structuralSection({
          david_roster_player_count: 30,
          league_roster_count: 12,
        }),
      },
    },
  };

  return zWhatChangedResponse.parse({
    ...base,
    ...overrides,
    daily_diff: {
      ...base.daily_diff,
      ...overrides.daily_diff,
      market: {
        ...base.daily_diff.market,
        ...overrides.daily_diff?.market,
      },
      model: {
        ...base.daily_diff.model,
        ...overrides.daily_diff?.model,
      },
    },
  }) as WhatChangedResponse;
}

function mockFetch(status: number, body: unknown) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status === 200,
    status,
    json: async () => body,
  });
}

function captureHealthResponse(
  overrides: Partial<CaptureHealthResponse> = {},
): CaptureHealthResponse {
  return {
    backup: {
      decision_supported: false,
      marker: {
        bytes: 1,
        failures: [],
        files: 1,
        finished_at: "2026-07-05T14:54:02+00:00",
        run_id: "20260705T141500Z",
        sha256_verified: true,
        started_at: "2026-07-05T14:15:00+00:00",
        status: "completed",
      },
      marker_present: true,
      reasons: [],
      status: "ok",
      threshold_hours: 26,
    },
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
        // schedule_drift became a required store field with DG-083 (config v3);
        // this fixture predated it and silently fell to the degraded parse path.
        schedule_drift: {
          basis: "chain_report",
          chain_step: "run_fc_forward_capture",
          drift_minutes: 0,
          exceeds_grace: false,
          recorded_start: "2026-07-05T09:00:02-04:00",
          target_local: "09:00",
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
    ...overrides,
  };
}

function modelProvenanceResponse(
  overrides: Partial<ModelProvenanceResponse> = {},
): ModelProvenanceResponse {
  return {
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
    ...overrides,
  };
}

function mockFetchByUrl(responses: Record<string, { status: number; body: unknown }>) {
  globalThis.fetch = vi.fn().mockImplementation((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const response = responses[url];
    if (!response) {
      return Promise.reject(new Error(`unmocked fetch ${url}`));
    }
    return Promise.resolve({
      ok: response.status >= 200 && response.status < 300,
      status: response.status,
      json: async () => response.body,
    });
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function increment1Response(overrides: Record<string, unknown> = {}) {
  const body = JSON.parse(JSON.stringify(whatChangedResponse())) as any;
  body.generated_at = "2026-07-06T14:00:00+00:00";
  body.daily_diff.market.roster_deltas = [
    {
      sleeper_id: "12519",
      player_key: "sleeper:12519",
      player_name: "Luther Burden",
      position: "WR",
      team_id: "CHI",
      value_delta: 99,
      value_delta_direction: "rose",
      overall_rank_delta: -2,
      overall_rank_delta_direction: "improved",
      position_rank_delta: 0,
      position_rank_delta_direction: "unchanged",
      model_series: null,
      market_series: {
        basis: "fc_forward_capture_joinable.value",
        points: [
          { date: "2026-07-05", value: 4110 },
          { date: "2026-07-06", value: 4209 },
        ],
      },
    },
  ];
  body.daily_diff.market.top_movers = [];
  body.daily_diff.market.entered = [];
  body.daily_diff.market.exited = [];
  body.daily_diff.model.deltas = [
    {
      sleeper_id: "9509",
      player_key: "sleeper:9509",
      player_name: "Bijan Robinson",
      position: "RB",
      team_id: "ATL",
      dynasty_value_score_delta: 2.5,
      dynasty_value_score_delta_direction: "rose",
      dvs_pct_delta: 0.02,
      xvar_delta: 0.7,
      market_series: null,
      model_series: {
        basis: "model_forward_capture_joinable.dynasty_value_score",
        points: [
          { date: "2026-07-05", value: 96 },
          { date: "2026-07-06", value: 98.5 },
        ],
      },
    },
  ];
  body.structural_context.baseline_roster_rows = [
    {
      sleeper_id: "13269",
      player_key: "sleeper:13269",
      player_name: "Tetairoa McMillan",
      position: "WR",
      team_id: null,
      image_status: "missing",
      model_lane_value: 0,
      market_lane_value: 0,
      model_series: null,
      market_series: null,
    },
  ];
  return { ...body, ...overrides };
}

describe("DailyWhatChanged", () => {
  it("renders a daily delta surface with isolated market and model regions", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(screen.getByRole("region", { name: /daily what-changed/i })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/what-changed");
    expect(
      screen.getByRole("heading", { level: 2, name: /Wednesday, July 1/i }),
    ).toBeTruthy();
    // DG-111: was seven stamped "Descriptive only — not decision-grade." lines
    // and a "delta surface" subtitle. Now: zero stamps, one plain subtitle, and
    // the provenance the rail used to shout is one press down — same facts,
    // same timestamps, same comparison window.
    expect(screen.queryAllByText("Descriptive only — not decision-grade.")).toEqual([]);
    expect(screen.queryByText(/decision_supported=false/i)).toBeNull();
    expect(screen.getByText(/since the last snapshot/i)).toBeTruthy();
    const generatedAt = screen.getByText("Report built Jul 1, 2026, 8:00 AM EDT.");
    expect(generatedAt).toBeTruthy();
    expect(generatedAt.getAttribute("title")).toBe("2026-07-01T12:00:00+00:00");
    expect(
      screen.getByText(/Market prices captured 2026-06-30 vs 2026-07-01/i),
    ).toBeTruthy();

    const market = screen.getByRole("region", {
      name: /market price-discovery overlay/i,
    });
    const model = screen.getByRole("region", { name: /model output changes/i });
    expect(within(market).getByText("Market Mover")).toBeTruthy();
    expect(within(market).getByText("Delta Receiver")).toBeTruthy();
    expect(within(market).getByText("Entered Rookie")).toBeTruthy();
    expect(within(market).getByText("Exited Veteran")).toBeTruthy();
    expect(within(market).queryByText("Model Delta")).toBeNull();
    expect(within(model).getByText("Model Delta")).toBeTruthy();
    expect(within(model).queryByText("Market Mover")).toBeNull();
    expect(within(market).queryByText("Hidden Cut Candidate")).toBeNull();
    expect(within(model).queryByText("Hidden Cut Candidate")).toBeNull();
  });

  it("degrades a whitespace-only sleeper id to the initials fallback, never a broken headshot request", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: {
            roster_deltas: [
              {
                sleeper_id: "   ",
                player_key: "blank-id",
                player_name: "Blank Id Row",
                position: "WR",
                value_delta: 3,
                value_delta_direction: "up",
                overall_rank_delta: -1,
                overall_rank_delta_direction: "up",
                position_rank_delta: 0,
                position_rank_delta_direction: "flat",
              },
            ],
            top_movers: [],
            entered: [],
            exited: [],
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    // The blank-id row renders its initials fallback, not a headshot…
    expect(
      await screen.findByLabelText("Blank Id Row headshot unavailable"),
    ).toBeTruthy();
    expect(screen.queryByRole("img", { name: "Blank Id Row" })).toBeNull();
    // …and no image on the page was built from a blank id (no src carries a space).
    for (const img of Array.from(document.querySelectorAll("img"))) {
      expect(img.getAttribute("src") ?? "").not.toContain(" ");
    }
  });

  it("renders signed deltas neutrally without directive language or fabricated arrows", async () => {
    mockFetch(200, whatChangedResponse());

    const { container } = render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("-8")).toBeTruthy());
    const market = screen.getByRole("region", {
      name: /market price-discovery overlay/i,
    });
    expect(within(market).getByText("+11")).toBeTruthy();
    expect(screen.getByText("-1.25")).toBeTruthy();
    expect(screen.getByText("+0.04")).toBeTruthy();
    expect(screen.getByText("-0.75")).toBeTruthy();
    expect(screen.queryByText(/\b(buy|sell|hold|start|sit)\b/i)).toBeNull();
    expect(screen.queryByText(/optimizer|recommender|trend optimizer/i)).toBeNull();
    expect(screen.queryByText(/transaction recommender/i)).toBeNull();
    expect(screen.queryByText(/[▲▼⬆⬇]/u)).toBeNull();

    for (const row of container.querySelectorAll(".dg-wc__player-row")) {
      expect(row.className).not.toMatch(
        /buy|sell|positive|negative|success|danger|green|red/,
      );
      expect(row.getAttribute("aria-selected")).toBeNull();
    }
  });

  it("keeps degraded 200 responses in view and surfaces freshness caveats", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        overall_status: "degraded",
        daily_diff: {
          overall_status: "degraded",
          market: { status: "degraded", aborted_reason: "market_snapshot_stale" },
          model: {
            status: "degraded",
            feature_freshness: {
              decision_supported: false,
              feature_source_status: "not_ready",
              aborted_reason: "feature_source_unverifiable",
            },
            pvo_staleness: {
              decision_supported: false,
              pvo_source_status: "not_ready",
              aborted_reason: "pvo_seed_stale",
            },
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    // DG-111: the degradation is still stated — in prose on the surface, and
    // with the producer's own token preserved verbatim in the receipt sheet.
    // A degraded morning stays loud; it just speaks English first.
    await waitFor(() =>
      expect(screen.getByText(/Feed status: degraded/i)).toBeTruthy(),
    );
    expect(screen.getByTestId("wc-market-degraded").textContent).toMatch(
      /Market snapshot stale/,
    );
    expect(screen.getByTestId("wc-model-degraded").textContent).toMatch(
      /Feature source unverifiable/,
    );
    expect(screen.getByTestId("wc-model-degraded").textContent).toMatch(
      /Pvo seed stale/,
    );
    const raw = screen.getByTestId("wc-raw-reasons").textContent;
    for (const token of [
      "market_snapshot_stale",
      "feature_source_unverifiable",
      "pvo_seed_stale",
    ]) {
      expect(raw).toContain(token);
    }
    expect(screen.queryAllByText("Descriptive only — not decision-grade.")).toEqual([]);
    expect(screen.queryByText(/decision_supported=false/i)).toBeNull();
  });

  it("renders honest empty and quiet states without manufacturing signal", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: {
            top_movers: [],
            roster_deltas: null,
            entered: [],
            exited: null,
            total_movers_count: 0,
          },
          model: {
            deltas: [],
            vintage_changed: false,
            comparison_window: { status: "insufficient_history" },
            feature_freshness: null,
            pvo_staleness: null,
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(screen.getByText(/market values held steady overnight/i)).toBeTruthy(),
    );
    expect(screen.getByText(/Your roster's market values held steady/i)).toBeTruthy();
    expect(screen.getByText(/no entered assets/i)).toBeTruthy();
    expect(screen.getByText(/no exited assets/i)).toBeTruthy();
    // DG-111 REVIEW-PANEL FIX. `comparison_window.status` is set ONLY where the
    // producer refused to compare (daily_diff.py:237-241), so an empty delta
    // list here means "we did not look", and the surface must not say
    // "Projections held steady" — that is an affirmative claim about a
    // comparison that never happened.
    expect(screen.queryByText(/Projections held steady/i)).toBeNull();
    expect(
      screen.getByText(/No day-over-day comparison of our projections/i),
    ).toBeTruthy();
    // ...and a young capture history is NOT a degradation. Calling it one is the
    // DG-047 cry-wolf pattern: it spends the word on a normal morning.
    const modelNotice = screen.getByTestId("wc-model-degraded").textContent;
    expect(modelNotice).toMatch(
      /couldn't compare our projections against an earlier day/i,
    );
    expect(modelNotice).not.toMatch(/came back degraded/i);
    // DG-109 review fix: this line used to assert that the RAW key
    // `insufficient_history` was on David's screen — one of the 359 green tests
    // pinning the exact violation the ticket exists to remove, and positive
    // proof that ModelRegion's caveat branch rendered unconverted. Meanwhile the
    // dictionary entry for it was added by this branch and no render path
    // consulted it. Same fact, same branch, said in words now.
    expect(modelNotice).toMatch(
      /Not enough days captured yet to compare one to the next/,
    );
    // Not in body copy anywhere on the surface...
    expect(modelNotice).not.toMatch(/insufficient_history/);
    expect(
      within(screen.getByRole("region", { name: "Model output changes" })).queryByText(
        /insufficient_history/i,
      ),
    ).toBeNull();
    // ...but not lost either: the verbatim token is in the receipt sheet, which
    // is the one layer the render rule permits a raw pipeline key.
    expect(screen.getByTestId("wc-raw-reasons").textContent).toContain(
      "insufficient_history",
    );
    expect(screen.queryByText(/top mover unavailable/i)).toBeNull();
    expect(screen.queryByText(/0\.00/i)).toBeNull();
  });

  it("handles sparse real-shape rows and model windows without hiding identity or vintage dates", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: {
            top_movers: null,
            roster_deltas: null,
            entered: [
              { sleeper_id: "entered-only-1", player_key: "Entered Only One" },
              { sleeper_id: "entered-only-2", player_key: "Entered Only Two" },
            ],
            exited: [{ sleeper_id: "exited-only-1", player_key: "Exited Only One" }],
          },
          model: {
            comparison_window: {
              from_date: "2026-06-30",
              to_date: "2026-07-01",
              from_vintage: {
                semantic_output_hash: "semantic-old",
                provenance_hash: "provenance-old",
              },
              to_vintage: {
                semantic_output_hash: "semantic-new",
                provenance_hash: "provenance-new",
              },
            },
            deltas: [
              {
                sleeper_id: "model-null-name",
                player_key: "model-key-fallback",
                player_name: null,
                position: null,
                dynasty_value_score_delta: -0,
                dynasty_value_score_delta_direction: "flat",
                dvs_pct_delta: 0.01,
                xvar_delta: -2,
              },
              {
                sleeper_id: "model-named",
                player_key: "model-named",
                player_name: "Second Model Delta",
                position: "TE",
                dynasty_value_score_delta: 2,
                dynasty_value_score_delta_direction: "up",
                dvs_pct_delta: -0.02,
                xvar_delta: 0,
              },
            ],
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("Entered Only One")).toBeTruthy());
    expect(screen.getByText("Entered Only Two")).toBeTruthy();
    expect(screen.getByText("Exited Only One")).toBeTruthy();
    expect(screen.getByText("model-key-fallback")).toBeTruthy();
    expect(screen.getByText("Second Model Delta")).toBeTruthy();
    expect(screen.getByText("-0")).toBeTruthy();
    expect(screen.getByText(/model window 2026-06-30 vs 2026-07-01/i)).toBeTruthy();
    expect(screen.queryByText(/semantic-old/i)).toBeNull();
    expect(screen.queryByText(/semantic-new/i)).toBeNull();
    expect(
      screen
        .getByText(/Projection basis changed within this window/i)
        .getAttribute("title"),
    ).toContain("semantic-old → semantic-new");
  });

  it("renders structural current-state baseline summaries without named candidate or card lists", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /structural current-state baseline/i }),
      ).toBeTruthy(),
    );
    expect(screen.getByText(/backdrop for today's movement/i)).toBeTruthy();
    expect(screen.queryByText(/current_not_delta=true/i)).toBeNull();

    const baseline = screen.getByRole("region", {
      name: /structural current-state baseline/i,
    });
    for (const label of [
      "Team Posture",
      "Team Value",
      "League Opportunity",
      "Drop Pressure",
      "Sleeper Snapshot",
    ]) {
      // DG-111: the "Status: ok" stamp and the disclosure line are retired from
      // every section. A clean section says nothing at all; only a section with
      // something wrong speaks, and it speaks in a sentence.
      const section = within(baseline).getByRole("region", { name: label });
      expect(within(section).queryByText(/^Status:/)).toBeNull();
      expect(
        within(section).queryByText("Descriptive only — not decision-grade."),
      ).toBeNull();
    }

    const posture = within(baseline).getByRole("region", { name: "Team Posture" });
    expect(within(posture).getByText(/contender/i)).toBeTruthy();
    expect(within(posture).getByText(/team count: 12/i)).toBeTruthy();
    // The staleness FACT survives, in words. DG-111 says how old and that it is
    // stale; DG-109's dictionary says WHICH pair of clocks the age was measured
    // between — both facts in one notice — and the producer's own basis token is
    // kept verbatim in the title attribute (and in the receipt sheet).
    const postureNotice = within(posture).getByTestId("wc-section-notice");
    expect(postureNotice.textContent).toMatch(/Team posture snapshot/i);
    expect(postureNotice.textContent).toMatch(/1\.5 hours old/i);
    expect(postureNotice.textContent).toMatch(/stale/i);
    expect(postureNotice.getAttribute("title")).toContain("team_posture_snapshot");
    // No raw producer token reaches the visible sentence (DG-109's render rule).
    expect(within(posture).queryByText(/team_posture_snapshot/)).toBeNull();
    // A clean section stays silent — that is the "one caveat, only where it
    // changes something" rule, mechanically enforced.
    expect(
      within(
        within(baseline).getByRole("region", { name: "Sleeper Snapshot" }),
      ).queryByTestId("wc-section-notice"),
    ).toBeNull();

    const teamValue = within(baseline).getByRole("region", { name: "Team Value" });
    expect(within(teamValue).getByText(/Starting lineup value: 31.4/i)).toBeTruthy();
    expect(within(teamValue).getByText(/Weekly lineup strength: 42.75/i)).toBeTruthy();
    expect(within(teamValue).getByText(/Top-asset core value: 88.2/i)).toBeTruthy();
    expect(
      within(teamValue).getByText(/Whole-roster value, capped: 104.6/i),
    ).toBeTruthy();

    const opportunity = within(baseline).getByRole("region", {
      name: "League Opportunity",
    });
    expect(within(opportunity).getByText(/partner ranking count: 2/i)).toBeTruthy();
    expect(within(opportunity).getByText(/card count: 3/i)).toBeTruthy();
    // DG-109: the opportunity counts printed their own shouted enums. The counts
    // are unchanged; only the words are.
    expect(
      within(opportunity).getByText(/We value him more than the market does: 2/i),
    ).toBeTruthy();
    expect(within(opportunity).getByText(/Depth context: 1/i)).toBeTruthy();
    // DG-111: the section's own trouble is one notice, and the raw token stays
    // on the element rather than in the sentence.
    expect(within(opportunity).getByTestId("wc-section-notice").textContent).toMatch(
      /League opportunity partial source/i,
    );
    expect(
      within(opportunity).getByTestId("wc-section-notice").getAttribute("title"),
    ).toContain("league_opportunity_partial_source");

    const dropPressure = within(baseline).getByRole("region", {
      name: "Drop Pressure",
    });
    expect(within(dropPressure).getByText(/cuts required: 2/i)).toBeTruthy();
    expect(within(dropPressure).getByText(/total players: 30/i)).toBeTruthy();
    expect(within(dropPressure).getByText(/total capacity: 28/i)).toBeTruthy();

    const sleeper = within(baseline).getByRole("region", { name: "Sleeper Snapshot" });
    expect(within(sleeper).getByText(/david roster player count: 30/i)).toBeTruthy();
    expect(within(sleeper).getByText(/league roster count: 12/i)).toBeTruthy();

    expect(screen.queryByText("Hidden Cut Candidate")).toBeNull();
    expect(screen.queryByText("Second Hidden Cut Candidate")).toBeNull();
    expect(screen.queryByText("97")).toBeNull();
    expect(screen.queryByText("98")).toBeNull();
    expect(screen.queryByText("Hidden Divergence Asset One")).toBeNull();
    expect(screen.queryByText("Hidden Divergence Asset Two")).toBeNull();
    expect(screen.queryByText("Hidden Depth Asset")).toBeNull();
    expect(
      screen.queryByText(/recommended|target|drop list|opportunity ranking/i),
    ).toBeNull();
    expect(screen.queryByText(/\b(best|should|buy|sell|start|sit)\b/i)).toBeNull();
    expect(screen.queryByText(/[▲▼⬆⬇]/u)).toBeNull();

    for (const section of within(baseline).getAllByRole("region")) {
      expect(section.className).not.toMatch(/red|green|success|danger/);
    }
  });

  it("renders unavailable for non-OK responses and parse-error for invalid 200 bodies", async () => {
    mockFetch(503, {
      detail: {
        error: "what_changed_report_unavailable",
        message: "report file missing",
      },
    });
    const { unmount } = render(<DailyWhatChanged />);
    await waitFor(() =>
      expect(screen.getByText(/daily what-changed unavailable/i)).toBeTruthy(),
    );
    unmount();

    mockFetch(200, { bogus: true });
    render(<DailyWhatChanged />);
    await waitFor(() =>
      expect(screen.getByText(/could not read daily what-changed/i)).toBeTruthy(),
    );
  });

  it("renders the I2a daily tape from capture-health and model-provenance substrate facts", async () => {
    mockFetchByUrl({
      "/api/league/what-changed": { status: 200, body: whatChangedResponse() },
      "/api/system/capture-health": { status: 200, body: captureHealthResponse() },
      "/api/system/model-provenance": {
        status: 200,
        body: modelProvenanceResponse(),
      },
    });

    render(<DailyWhatChanged />);

    const tape = await screen.findByRole("region", { name: /daily tape/i });
    expect(
      within(tape).getByText(/market sync active: 12 consecutive days tracked/i),
    ).toBeTruthy();
    expect(within(tape).getByText(/projection update: july 5, current/i)).toBeTruthy();
    // DG-111: the third "Status: Synced / Status: Degraded" stamp is retired.
    // A clean tape says nothing; a degraded one says what it means.
    expect(within(tape).queryByText(/status: synced/i)).toBeNull();
    expect(
      within(tape).queryByText(
        /capture streak|last capture|model vintage|registry version/i,
      ),
    ).toBeNull();
    expect(
      within(tape)
        .getByText(/market sync active/i)
        .getAttribute("title"),
    ).toContain("Days captured in a row — 12 (from consecutive_days)");
    expect(
      within(tape)
        .getByText(/projection update/i)
        .getAttribute("title"),
    ).toContain("Model registry version — 4 (from registry_version)");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/system/capture-health",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/system/model-provenance",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("degrades the daily tape honestly when substrate endpoints are unavailable", async () => {
    mockFetchByUrl({
      "/api/league/what-changed": { status: 200, body: whatChangedResponse() },
      "/api/system/capture-health": {
        status: 503,
        body: { detail: { message: "capture health unavailable" } },
      },
      "/api/system/model-provenance": {
        status: 200,
        body: { invalid: true },
      },
    });

    render(<DailyWhatChanged />);

    const tape = await screen.findByRole("region", { name: /daily tape/i });
    expect(
      within(tape).getByText(/partial market sync: some inputs are being verified/i),
    ).toBeTruthy();
    expect(
      within(tape).getByText(/projections active using the latest verified data/i),
    ).toBeTruthy();
    // DG-111: the third "Status: Synced / Status: Degraded" stamp is retired.
    // A clean tape says nothing; a degraded one says what it means.
    expect(within(tape).queryByText(/status: degraded/i)).toBeNull();
    expect(within(tape).getByText(/some of this data is behind/i)).toBeTruthy();
    expect(
      within(tape).queryByText(
        /capture health|model provenance|capture streak|model vintage|registry version/i,
      ),
    ).toBeNull();
  });

  it("reserves honest empty chart slots without rendering I2b sparkline paths", async () => {
    mockFetchByUrl({
      "/api/league/what-changed": { status: 200, body: whatChangedResponse() },
      "/api/system/capture-health": { status: 200, body: captureHealthResponse() },
      "/api/system/model-provenance": {
        status: 200,
        body: modelProvenanceResponse(),
      },
    });

    const { container } = render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(screen.getAllByText("Market Mover").length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText(/series pending/i).length).toBeGreaterThanOrEqual(3);
    expect(
      container.querySelectorAll(
        ".dg-ui-series__line, .dg-ui-series__gap, .dg-ui-series__edge",
      ),
    ).toHaveLength(0);
    expect(screen.queryByLabelText(/sparkline|trend/i)).toBeNull();
  });

  it("renders Increment-1 model-first AssetRows with real identity assets and lane symmetry", async () => {
    mockFetch(200, increment1Response());

    const { container } = render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("Bijan Robinson")).toBeTruthy());
    const model = screen.getByRole("region", { name: /model output/i });
    const market = screen.getByRole("region", { name: /market price/i });
    expect(
      model.compareDocumentPosition(market) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    const modelRow = within(model)
      .getByText("Bijan Robinson")
      .closest("[data-asset-row]");
    expect(modelRow).toBeTruthy();
    expect(modelRow?.getAttribute("data-row-density")).toBe("32px");
    expect(
      within(modelRow as HTMLElement)
        .getByRole("img", { name: "Bijan Robinson" })
        .getAttribute("src"),
    ).toBe("/assets/headshots/9509.jpg");
    expect(
      (
        within(modelRow as HTMLElement).getByText("ATL").parentElement ?? modelRow
      )?.querySelector("[data-team-id='ATL']"),
    ).toBeTruthy();
    expect(within(modelRow as HTMLElement).getByText("+2.5")).toBeTruthy();
    expect(within(modelRow as HTMLElement).getByText("—")).toBeTruthy();
    expect(
      within(modelRow as HTMLElement).getByRole("img", {
        name: /model series.*hard right edge/i,
      }),
    ).toBeTruthy();

    const marketRow = within(market)
      .getByText("Luther Burden")
      .closest("[data-asset-row]");
    expect(marketRow).toBeTruthy();
    expect(within(marketRow as HTMLElement).getByText("—")).toBeTruthy();
    expect(
      container.querySelector("[data-lane='market'] [data-lane='model']"),
    ).toBeNull();
  });

  // DG-111: the badge said "Stale data caveat — the capture is 27.5 hours old."
  // The word "caveat" is gone; the age, the staleness and the desaturated rows
  // are not.
  it("renders stale generated_at as a non-urgent header sentence and desaturates rows", async () => {
    const body = increment1Response();
    body.generated_at = new Date(Date.now() - 27.5 * 60 * 60 * 1000).toISOString();
    mockFetch(200, body);

    const { container } = render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(screen.getByTestId("wc-freshness").textContent).toMatch(/didn't land/i),
    );
    expect(screen.getByText(/2[67](\.\d)? hours/i)).toBeTruthy();
    expect(container.querySelector(".dg-wc--stale")).toBeTruthy();
    expect(
      container.querySelector("[data-stale='true'] [data-asset-row]"),
    ).toBeTruthy();
  });

  it("renders quiet-day baseline roster rows only when the producer supplies them", async () => {
    const body = increment1Response();
    body.daily_diff.market.roster_deltas = [];
    body.daily_diff.market.top_movers = [];
    body.daily_diff.model.deltas = [];
    mockFetch(200, body);

    render(<DailyWhatChanged />);

    await waitFor(() =>
      // Copy amended with SR-16: quietDay is derived from HIS roster's movers,
      // so the sentence scopes itself to the roster to stay true on days the
      // league moved but his roster held.
      expect(
        screen.getByText(
          /No valuation deltas observed on your roster since the last capture/i,
        ),
      ),
    );
    expect(
      screen.getByText("no movement on your roster since the prior snapshot"),
    ).toBeTruthy();
    expect(screen.getByText("Tetairoa McMillan")).toBeTruthy();
    const row = screen.getByText("Tetairoa McMillan").closest("[data-asset-row]");
    expect(row).toBeTruthy();
    expect(within(row as HTMLElement).getAllByText("—").length).toBeGreaterThanOrEqual(
      2,
    );
  });

  it("falls back to pending series and neutral team ring on malformed Increment-1 row data", async () => {
    const body = increment1Response();
    body.daily_diff.model.deltas[0].team_id = null;
    body.daily_diff.model.deltas[0].model_series = {
      basis: "model_forward_capture_joinable.dynasty_value_score",
      points: [{ date: "2026-07-06", value: 98.5 }],
    };
    mockFetch(200, body);

    render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("Bijan Robinson")).toBeTruthy());
    const row = screen.getByText("Bijan Robinson").closest("[data-asset-row]");
    expect(row).toBeTruthy();
    expect((row as HTMLElement).querySelector("[data-team-id]")).toBeNull();
    expect(within(row as HTMLElement).getByText(/series pending/i)).toBeTruthy();
  });
});

// SR-16 / DG-081 — the hero is the number David acts on: how many of HIS
// players moved, not a list-length sum (51) and not league-wide churn (456).
// Flat roster rows are present-in-both-snapshots rows, NOT movers — counting
// .length would print a near-constant 26 every morning (wallpaper).
describe("DailyWhatChanged roster-mover hero", () => {
  function marketRow(name: string, delta: number, idx: number) {
    return {
      sleeper_id: `hero-${idx}`,
      player_key: `hero-${idx}`,
      player_name: name,
      position: "WR",
      value_delta: delta,
      value_delta_direction: delta > 0 ? "up" : delta < 0 ? "down" : "flat",
      overall_rank_delta: 0,
      overall_rank_delta_direction: "flat",
      position_rank_delta: 0,
      position_rank_delta_direction: "flat",
    };
  }

  function heroElement(): HTMLElement {
    return screen
      .getByText("Your roster moved")
      .closest(".dg-ui-value-hero") as HTMLElement;
  }

  it("derives the hero from his roster's movers with the largest name in the basis, and keeps the league total honest", async () => {
    const rosterDeltas = [
      marketRow("Tank Dell", 139, 0),
      marketRow("Fernando Mendoza", -84, 1),
      ...Array.from({ length: 24 }, (_, i) =>
        marketRow(`Roster Mover ${i + 1}`, i + 1, i + 2),
      ),
    ];
    const topMovers = Array.from({ length: 25 }, (_, i) =>
      marketRow(`League Mover ${i + 1}`, 50 - i, 100 + i),
    );
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: {
            roster_deltas: rosterDeltas,
            top_movers: topMovers,
            total_movers_count: 456,
          },
          model: { deltas: [] },
        },
      }),
    );

    render(<DailyWhatChanged />);
    await waitFor(() => expect(screen.getByText("Your roster moved")).toBeTruthy());

    const hero = heroElement();
    expect(within(hero).getByText("26")).toBeTruthy();
    expect(within(hero).getByText(/largest Tank Dell \+139/)).toBeTruthy();
    expect(
      screen.getByText("Showing 25 of 456 market movers league-wide"),
    ).toBeTruthy();
  });

  it("counts only rows that actually moved — flat roster rows never inflate the hero", async () => {
    const rosterDeltas = [
      ...Array.from({ length: 20 }, (_, i) => marketRow(`Flat Holder ${i + 1}`, 0, i)),
      ...Array.from({ length: 6 }, (_, i) =>
        marketRow(`True Mover ${i + 1}`, (i + 1) * 10, 20 + i),
      ),
    ];
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: {
            roster_deltas: rosterDeltas,
            top_movers: [],
            total_movers_count: 456,
          },
          model: { deltas: [] },
        },
      }),
    );

    render(<DailyWhatChanged />);
    await waitFor(() => expect(screen.getByText("Your roster moved")).toBeTruthy());

    const hero = heroElement();
    expect(within(hero).getByText("6")).toBeTruthy();
    expect(within(hero).queryByText("26")).toBeNull();
    expect(within(hero).getByText(/largest True Mover 6 \+60/)).toBeTruthy();
  });

  it("never renders a league-wide total the payload does not carry", async () => {
    const topMovers = Array.from({ length: 25 }, (_, i) =>
      marketRow(`League Mover ${i + 1}`, 50 - i, 100 + i),
    );
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: { top_movers: topMovers, total_movers_count: null },
        },
      }),
    );

    render(<DailyWhatChanged />);
    await waitFor(() => expect(screen.getByText("Your roster moved")).toBeTruthy());

    expect(screen.getByText("Showing 25 market movers")).toBeTruthy();
    expect(screen.queryByText(/Showing 25 of/)).toBeNull();
  });
});

// DG-089: David's first real session found the product's most natural gesture —
// "this player moved, let me click him" — did nothing. Rows open the shared
// player-selection plumbing when the surface is given a handler, and stay
// non-interactive when it is not (a bare render must not grow phantom buttons).
describe("DG-089 player selection from the change feed", () => {
  it("mover rows expose an open-player button that reports the sleeper id", async () => {
    mockFetch(200, whatChangedResponse());
    const onSelectPlayer = vi.fn();

    render(<DailyWhatChanged onSelectPlayer={onSelectPlayer} />);

    const button = await screen.findByRole("button", { name: /^Open Market Mover/ });
    fireEvent.click(button);
    expect(onSelectPlayer).toHaveBeenCalledWith("player-2", "Market Mover");

    // DG-110 gave the same player a SECOND handle — the hero line names the
    // largest mover, and that name opens the same card — so this row assertion
    // now says which of the two handles it is exercising.
    const receiverHandles = screen.getAllByRole("button", {
      name: /^Open Delta Receiver/,
    });
    const row = receiverHandles.find((handle) =>
      handle.className.includes("dg-wc__player-open"),
    );
    expect(row).toBeTruthy();
    fireEvent.click(row as HTMLElement);
    expect(onSelectPlayer).toHaveBeenCalledWith("player-1", "Delta Receiver");
  });

  it("quiet-day baseline roster rows are clickable too — the founding gesture's most common morning", async () => {
    const body = JSON.parse(JSON.stringify(whatChangedResponse())) as {
      daily_diff: { market: { roster_deltas: unknown[] } };
      structural_context: { baseline_roster_rows?: unknown };
    };
    // Baseline rows render only on a quiet day (no roster movers).
    body.daily_diff.market.roster_deltas = [];
    body.structural_context.baseline_roster_rows = [
      {
        sleeper_id: "player-9",
        player_name: "Quiet Roster Guy",
        position: "TE",
        team_id: "KC",
        market_lane_value: 0,
        model_lane_value: 0,
      },
    ];
    mockFetch(200, body);
    const onSelectPlayer = vi.fn();

    render(<DailyWhatChanged onSelectPlayer={onSelectPlayer} />);

    fireEvent.click(
      await screen.findByRole("button", { name: /^Open Quiet Roster Guy/ }),
    );
    expect(onSelectPlayer).toHaveBeenCalledWith("player-9", "Quiet Roster Guy");
  });

  it("rows stay non-interactive when no selection handler is provided", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    await screen.findByRole("region", { name: /daily what-changed/i });
    expect(screen.queryByRole("button", { name: /open market mover/i })).toBeNull();
  });

  it("AppShell wires the feed to the inspector: clicking a mover opens it", async () => {
    // Default-503 variant of mockFetchByUrl: AppShell fetches more endpoints
    // than this test cares about; each degrades honestly on 503.
    const responses: Record<string, { status: number; body: unknown }> = {
      "/api/league/what-changed": { status: 200, body: whatChangedResponse() },
    };
    globalThis.fetch = vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      const response = responses[url] ?? { status: 503, body: { detail: "down" } };
      return Promise.resolve({
        ok: response.status >= 200 && response.status < 300,
        status: response.status,
        json: async () => response.body,
      });
    });

    render(<AppShell />);

    const button = await screen.findByRole("button", { name: /^Open Market Mover/ });
    fireEvent.click(button);

    const inspector = await screen.findByRole("complementary", {
      name: "Player inspector",
    });
    await waitFor(() => {
      expect(within(inspector).getByText("Market Mover")).toBeTruthy();
    });
  });
});

// ── DG-111 — the furniture is retired; the facts speak in prose ──────────────
// David, 2026-08-29: "I really don't care for the caveats and the hard wording
// governance… I'd rather use layman's terms and call a spade a spade."
// The honesty law that survives his ruling: stale must still SAY it is stale.
// These tests exist so a future edit cannot quietly delete the fact along with
// the stamp that used to carry it.
describe("DG-111 the stale morning still says it is stale, in prose", () => {
  it("says the capture is old in one plain sentence, with the real age, and no stamp", async () => {
    const body = increment1Response();
    body.generated_at = new Date(Date.now() - 27.5 * 60 * 60 * 1000).toISOString();
    mockFetch(200, body);

    render(<DailyWhatChanged />);

    const stale = await screen.findByTestId("wc-freshness");
    // The FACT: it is old, by this many hours, and what you see is the last
    // verified snapshot rather than today's.
    expect(stale.textContent).toMatch(/2[67](\.\d)? hours old/i);
    expect(stale.textContent).toMatch(/last verified snapshot/i);
    expect(stale.textContent).toMatch(/not today/i);
    // The FURNITURE: gone.
    expect(stale.textContent).not.toMatch(/caveat/i);
    expect(screen.queryByText("Descriptive only — not decision-grade.")).toBeNull();
  });

  it("says so even when the capture time is unreadable — never silence", async () => {
    const body = increment1Response();
    body.generated_at = "not-a-timestamp";
    mockFetch(200, body);

    render(<DailyWhatChanged />);

    const stale = await screen.findByTestId("wc-freshness");
    expect(stale.textContent).toMatch(/couldn't read/i);
    expect(stale.textContent).toMatch(/last verified snapshot/i);
  });

  it("names a degraded feed in prose and keeps the raw reason in the receipt sheet", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        overall_status: "degraded",
        daily_diff: {
          overall_status: "degraded",
          market: { status: "degraded", aborted_reason: "market_snapshot_stale" },
          model: {
            status: "degraded",
            pvo_staleness: {
              decision_supported: false,
              pvo_source_status: "not_ready",
              aborted_reason: "pvo_seed_stale",
            },
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    const market = await screen.findByRole("region", {
      name: /market price-discovery overlay/i,
    });
    // Prose on the surface: the reason is said in words, not as a raw key…
    const marketNote = within(market).getByTestId("wc-market-degraded");
    expect(marketNote.textContent).toMatch(/Market snapshot stale/);
    expect(marketNote.textContent).not.toContain("market_snapshot_stale");
    // …and the raw producer token is still reachable, verbatim, in the receipt.
    const receipts = screen.getByTestId("wc-provenance");
    expect(receipts.textContent).toContain("market_snapshot_stale");
    expect(receipts.textContent).toContain("pvo_seed_stale");
  });

  it("a healthy morning carries no caveat furniture at all", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(screen.getByRole("region", { name: /daily what-changed/i })).toBeTruthy(),
    );
    expect(screen.queryAllByText("Descriptive only — not decision-grade.")).toEqual([]);
    expect(screen.queryByRole("note", { name: /caveats/i })).toBeNull();
    expect(screen.queryByText(/^Status:/)).toBeNull();
    expect(screen.queryByText(/Feed diagnostics/i)).toBeNull();
  });
});

// ── DG-111 REVIEW PANEL — the blocker, and the state no fixture ever drove ────
//
// `_build_market_section` (src/dynasty_genius/what_changed/daily_diff.py:111-117)
// returns `status: "insufficient_history"` with NO `aborted_reason`, no
// `roster_deltas` and no `top_movers` when fewer than two FantasyCalc capture
// dates exist. The market region's heads-up used to be gated on
// `market.aborted_reason` alone, so on that morning the surface fell silent and
// its empty-state copy — "market values held steady overnight" — stood as an
// affirmative claim about a comparison that was never made. Before DG-111 the
// rail printed `Market feed: insufficient_history` in always-visible text;
// moving that into a receipt sheet shut by default turned a cluttered truth into
// a clean falsehood. That is the honesty law's one BLOCKING shape: a
// truth-bearing behavior deleted instead of reworded.
describe("DG-111 a comparison that never ran never reads as 'nothing moved'", () => {
  it("speaks when the market lane has too little history, and drops the held-steady claim", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        overall_status: "degraded",
        daily_diff: {
          overall_status: "degraded",
          market: {
            status: "insufficient_history",
            market_source: "fantasycalc_overlay",
            comparison_window: { status: "insufficient_history" },
            roster_deltas: null,
            top_movers: null,
            entered: null,
            exited: null,
            total_movers_count: null,
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /market price-discovery/i }),
      ).toBeTruthy(),
    );
    const market = screen.getByRole("region", { name: /market price-discovery/i });

    // 1. The false claim is gone — both halves of it.
    expect(within(market).queryByText(/held steady/i)).toBeNull();
    expect(
      within(market).getByText(/No day-over-day comparison for your roster/i),
    ).toBeTruthy();
    expect(
      within(market).getByText(/No day-over-day comparison league-wide/i),
    ).toBeTruthy();

    // 2. The fact is VISIBLE, not hidden behind a shut receipt sheet.
    const notice = within(market).getByTestId("wc-market-degraded");
    expect(notice.textContent).toMatch(
      /couldn't compare market prices against an earlier day/i,
    );
    expect(notice.textContent).toMatch(/Not enough days captured yet/i);
    // A young capture history is not a fault, and must not be called one.
    expect(notice.textContent).not.toMatch(/came back degraded/i);
    // The producer's own token rides the element, never the sentence.
    expect(notice.getAttribute("title")).toBe("insufficient_history");
    expect(within(market).queryByText(/insufficient_history/)).toBeNull();

    // 3. The receipt sheet still records it verbatim — `producerReasons` reads
    //    the MARKET comparison window now, not only the model's.
    expect(screen.getByTestId("wc-raw-reasons").textContent).toContain(
      "insufficient_history",
    );
    // 4. And the market source survives in the sheet even though the comparison
    //    window carried no dates.
    expect(screen.getByTestId("wc-provenance").textContent).toContain(
      "fantasycalc_overlay",
    );
  });

  it("keeps saying 'held steady' when the comparison genuinely ran and nothing moved", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: {
            status: "ok",
            roster_deltas: [],
            top_movers: [],
            total_movers_count: 0,
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /market price-discovery/i }),
      ).toBeTruthy(),
    );
    const market = screen.getByRole("region", { name: /market price-discovery/i });
    expect(
      within(market).getByText(/held steady — no movement on this tape/i),
    ).toBeTruthy();
    expect(within(market).queryByTestId("wc-market-degraded")).toBeNull();
    // No rows on screen means no trend slots to explain, so the note that
    // explains blank ones does not render either.
    expect(within(market).queryByTestId("wc-trend-note")).toBeNull();
  });

  it("still calls a real market abort a degradation, and says why", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        overall_status: "degraded",
        daily_diff: {
          overall_status: "degraded",
          market: {
            status: "unavailable",
            aborted_reason: "missing_sleeper_snapshot",
            market_source: "fantasycalc_overlay",
            roster_deltas: null,
            top_movers: null,
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /market price-discovery/i }),
      ).toBeTruthy(),
    );
    const notice = within(
      screen.getByRole("region", { name: /market price-discovery/i }),
    ).getByTestId("wc-market-degraded");
    expect(notice.textContent).toMatch(/came back degraded/i);
    expect(notice.textContent).toMatch(/could not read your Sleeper roster/i);
    expect(notice.getAttribute("title")).toBe("missing_sleeper_snapshot");
  });
});
