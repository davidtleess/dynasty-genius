// @vitest-environment jsdom

import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { WhatChangedResponse } from "../lib/api/types.gen";
import { zWhatChangedResponse } from "../lib/api/zod.gen";
import { DailyWhatChanged } from "./DailyWhatChanged";

type ResponseOverrides = Partial<
  Omit<WhatChangedResponse, "daily_diff" | "structural_context">
> & {
  daily_diff?: Omit<Partial<WhatChangedResponse["daily_diff"]>, "market" | "model"> & {
    market?: Partial<WhatChangedResponse["daily_diff"]["market"]>;
    model?: Partial<WhatChangedResponse["daily_diff"]["model"]>;
  };
};

function structuralSection() {
  return {
    status: "ok",
    decision_supported: false,
    current_not_delta: true,
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
        team_posture: structuralSection(),
        team_value: structuralSection(),
        league_opportunity: structuralSection(),
        drop_pressure: {
          ...structuralSection(),
          top_candidates: [
            {
              sleeper_player_id: "hidden-current-context",
              player_name: "Deferred Structural Player",
              position: "WR",
              cut_priority: 1,
            },
          ],
        },
        sleeper_snapshot: structuralSection(),
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

afterEach(() => vi.restoreAllMocks());

describe("DailyWhatChanged", () => {
  it("renders a daily delta surface with isolated market and model regions", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    await waitFor(() =>
      expect(screen.getByRole("region", { name: /daily what-changed/i })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/what-changed");
    expect(screen.getByRole("heading", { name: /daily change log/i })).toBeTruthy();
    expect(screen.getByText(/decision_supported=false/i)).toBeTruthy();
    expect(screen.getByText(/delta surface/i)).toBeTruthy();
    expect(screen.getByText(/generated: 2026-07-01T12:00:00\+00:00/i)).toBeTruthy();
    expect(screen.getByText(/captured 2026-06-30 vs 2026-07-01/i)).toBeTruthy();

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
    expect(screen.queryByText("Deferred Structural Player")).toBeNull();
    expect(screen.queryByText(/team posture|team value|drop pressure/i)).toBeNull();
  });

  it("renders signed deltas neutrally without directive language or fabricated arrows", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("-8")).toBeTruthy());
    expect(screen.getByText("+11")).toBeTruthy();
    expect(screen.getByText("-1.25")).toBeTruthy();
    expect(screen.getByText("+0.04")).toBeTruthy();
    expect(screen.getByText("-0.75")).toBeTruthy();
    expect(screen.queryByText(/buy|sell|hold|start|sit/i)).toBeNull();
    expect(screen.queryByText(/optimizer|recommender|trend optimizer/i)).toBeNull();
    expect(screen.queryByText(/transaction recommender/i)).toBeNull();
    expect(screen.queryByText(/[▲▼⬆⬇]/u)).toBeNull();

    for (const row of screen.getAllByRole("row")) {
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

    await waitFor(() => expect(screen.getByText(/status: degraded/i)).toBeTruthy());
    expect(screen.getByText(/market_snapshot_stale/i)).toBeTruthy();
    expect(screen.getByText(/feature_source_unverifiable/i)).toBeTruthy();
    expect(screen.getByText(/pvo_seed_stale/i)).toBeTruthy();
    expect(screen.getByText(/decision_supported=false/i)).toBeTruthy();
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

    await waitFor(() => expect(screen.getByText(/no market top movers/i)).toBeTruthy());
    expect(screen.getByText(/no roster market deltas/i)).toBeTruthy();
    expect(screen.getByText(/no entered assets/i)).toBeTruthy();
    expect(screen.getByText(/no exited assets/i)).toBeTruthy();
    expect(screen.getByText(/model no change/i)).toBeTruthy();
    expect(screen.getByText(/insufficient_history/i)).toBeTruthy();
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
    expect(screen.getByText(/semantic-old/i)).toBeTruthy();
    expect(screen.getByText(/semantic-new/i)).toBeTruthy();
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
});
