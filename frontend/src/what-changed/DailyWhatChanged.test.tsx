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
          // team_posture.py:98-102 emits the UPPERCASE enum. This fixture said
          // "Contender", which is not a value the producer can produce — and
          // because it is already plain English, `valueWord` passed it straight
          // through, so every spec built on it was exercising the dictionary's
          // BYPASS rather than the dictionary. DG-113 needs the real word.
          david_posture: "CONTENDER",
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

// DG-113: the receipts moved from an always-open right rail into the health
// sheet behind the header's "Details" control. Every spec that reads a receipt
// line now has to open it first — which is the point of the change, and worth
// one helper rather than a dozen repeated clicks.
async function openHealthSheet() {
  fireEvent.click(await screen.findByTestId("wc-health-sheet-toggle"));
  return screen.getByTestId("wc-health-sheet");
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
    // DG-113: the "What changed … since the last snapshot" subtitle is gone.
    // The verdict says what the morning is, which is what a subtitle under a
    // date was reaching for and could not do.
    expect(screen.queryByText(/since the last snapshot/i)).toBeNull();

    const sheet = await openHealthSheet();
    const generatedAt = within(sheet).getByText("Built Jul 1, 2026, 8:00 AM EDT.");
    expect(generatedAt.getAttribute("title")).toBe("2026-07-01T12:00:00+00:00");
    expect(
      within(sheet).getByText(/Market prices compared 2026-06-30 against 2026-07-01/i),
    ).toBeTruthy();

    // DG-113 §2.4/§2.5: one market region became two, because his roster and
    // the league are two different questions and used to be two headings
    // inside one box that repeated players between them.
    const mine = screen.getByTestId("wc-your-roster");
    const league = screen.getByTestId("wc-around-the-league");
    const model = screen.getByRole("region", { name: /model output changes/i });
    expect(within(league).getByText("Market Mover")).toBeTruthy();
    expect(within(mine).getByText("Delta Receiver")).toBeTruthy();
    expect(within(league).getByText("Entered Rookie")).toBeTruthy();
    expect(within(league).getByText("Exited Veteran")).toBeTruthy();
    expect(within(mine).queryByText("Model Delta")).toBeNull();
    expect(within(model).getByText("Model Delta")).toBeTruthy();
    expect(within(model).queryByText("Market Mover")).toBeNull();
    expect(within(mine).queryByText("Hidden Cut Candidate")).toBeNull();
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

  // DG-115 note: "neutrally" here means the LANGUAGE and the row, not the hue.
  // Since David's 2026-08-30 direction-color ruling a delta cell carries an
  // up/down hue (see the next test); what this one still pins is that the row
  // itself takes no verdict class, no arrow glyph is fabricated, and no
  // directive word reaches the screen.
  it("renders signed deltas neutrally without directive language or fabricated arrows", async () => {
    mockFetch(200, whatChangedResponse());

    const { container } = render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("-8")).toBeTruthy());
    const league = screen.getByTestId("wc-around-the-league");
    expect(within(league).getByText("+11")).toBeTruthy();
    expect(screen.getByText("-1.25")).toBeTruthy();
    expect(screen.getByText("+0.04")).toBeTruthy();
    expect(screen.getByText("-0.75")).toBeTruthy();
    // DG-113 AMENDS THIS LIST. The blanket ban on buy/sell/start/sit words was
    // the repealed no-recommendation law wearing a test's clothes; David's
    // 2026-08-30 ruling green-lights a named verdict, and "Worth a look" says
    // "start with Rasheen Ali" on a live payload. What is still banned is the
    // thing this spec was actually protecting — a delta ROW turning into a
    // directive, which is where a price movement would be silently retyped as
    // advice. So the ban is scoped to the rows.
    for (const row of container.querySelectorAll(".dg-wc__player-row")) {
      expect(row.textContent ?? "").not.toMatch(/\b(buy|sell|hold|start|sit)\b/i);
    }
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

  // DG-115: David ruled "Green up / red down" on 2026-08-30. The hue is set
  // from a data attribute derived from the SAME zero rule that prints the
  // characters, so the color and the sign can never tell different stories —
  // and the sign is always printed, so nothing here depends on seeing color.
  it("marks each delta with the direction it actually moved", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("-8")).toBeTruthy());

    const cellFor = (text: string) =>
      screen.getAllByText(text)[0]?.closest(".dg-wc__delta-cell");

    expect(cellFor("-8")?.getAttribute("data-direction")).toBe("down");
    expect(cellFor("+11")?.getAttribute("data-direction")).toBe("up");
    expect(cellFor("-1.25")?.getAttribute("data-direction")).toBe("down");
    expect(cellFor("+0.04")?.getAttribute("data-direction")).toBe("up");
    expect(cellFor("-0.75")?.getAttribute("data-direction")).toBe("down");
  });

  it("leaves an exact zero with no direction at all — nothing is not a movement", async () => {
    const body = whatChangedResponse({
      daily_diff: {
        model: {
          deltas: [
            {
              sleeper_id: "player-5",
              player_key: "player-5",
              player_name: "Model Delta",
              position: "QB",
              dynasty_value_score_delta: 0,
              dynasty_value_score_delta_direction: "flat",
              dvs_pct_delta: 0,
              xvar_delta: 0,
            },
          ],
        },
      },
    });
    mockFetch(200, body);

    const { container } = render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("Model Delta")).toBeTruthy());

    const zeroCells = [...container.querySelectorAll(".dg-wc__delta-cell")].filter(
      (cell) => cell.textContent?.includes("—"),
    );

    expect(zeroCells.length).toBeGreaterThanOrEqual(3);
    for (const cell of zeroCells) {
      expect(cell.getAttribute("data-direction")).toBeNull();
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
    expect((await screen.findByTestId("wc-market-degraded")).textContent).toMatch(
      /Market snapshot stale/,
    );
    expect(screen.getByTestId("wc-model-degraded").textContent).toMatch(
      /Feature source unverifiable/,
    );
    expect(screen.getByTestId("wc-model-degraded").textContent).toMatch(
      /Pvo seed stale/,
    );
    // DG-113: the producer tokens are still complete in the declared receipt
    // layer, inside the health sheet rather than an always-open rail — one
    // press down, complete when asked.
    //
    // DG-120: a status is a MESSAGE, so the sheet says it in English. The
    // reasons the dictionary has no sentence for still print their own bytes
    // (asserted below), which is why this sheet is still where an operator
    // reads what the producers actually said.
    await openHealthSheet();
    const raw = screen.getByTestId("wc-provenance").textContent;
    expect(raw).toMatch(/Feed status: Something needs attention/i);
    expect(raw).not.toMatch(/Feed status: degraded/i);
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
            // Both arrays PRESENT and empty — the producer looked and found
            // nobody. That is the only shape that licenses printing a zero;
            // the shape where the producer sends no keys at all is its own
            // test below ("never counts a pool the producer declined to send").
            entered: [],
            exited: [],
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
    // PANEL FIX: an empty `roster_deltas` on a comparison that RAN means the
    // market priced none of his players on both dates (daily_diff.py:143-147) —
    // a coverage fact. "Your roster's market values held steady" was the
    // section asserting the movement claim the verdict directly above it
    // refuses to make.
    // Said in the verdict AND in the section — they agree now, which is the
    // point, so this matches all of them rather than exactly one.
    expect(
      screen.getAllByText(
        /market didn't price any of your players on both of the last two days/i,
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByText(/Your roster's market values held steady/i)).toBeNull();
    // DG-113 §2.5: the two chip walls collapse to one line you can open, and
    // "No entered assets." — a raw-noun negative — becomes a sentence about
    // people. Absence is still said; it is just said in English.
    expect(screen.getByText(/New to the priced pool: 0 · Dropped out: 0/)).toBeTruthy();
    expect(screen.getByText(/Nobody new carried a price today/i)).toBeTruthy();
    expect(
      screen.getByText(/Nobody dropped out of the priced pool today/i),
    ).toBeTruthy();
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
    // ...but not lost either: the receipt sheet carries it. DG-120: as the
    // SENTENCE, not the token — `insufficient_history` is a status, and nothing
    // in the product is reachable by it, so there is no address to preserve.
    // The fact is the same one, and the raw token is still on the notice's own
    // title attribute for anyone who wants the producer's exact string.
    await openHealthSheet();
    expect(screen.getByTestId("wc-provenance").textContent).toContain(
      "Not enough days captured yet to compare one to the next.",
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
    const sheet = await openHealthSheet();
    expect(
      within(sheet).getByText(/model window 2026-06-30 against 2026-07-01/i),
    ).toBeTruthy();
    expect(screen.queryByText(/semantic-old/i)).toBeNull();
    expect(screen.queryByText(/semantic-new/i)).toBeNull();
    expect(
      within(sheet)
        .getByText(/Projection basis changed within this window/i)
        .getAttribute("title"),
    ).toContain("semantic-old → semantic-new");
  });

  // DG-113 REPLACES THIS SPEC WHOLESALE, and the replacement is narrower on
  // purpose.
  //
  // What it used to pin was "Current roster context": five accordion sections
  // printing "Team count: 12", "Partner ranking count: 2", "Card count: 3",
  // "Total capacity: 28", "David roster player count: 30" — and, worst,
  // "Starting lineup value: 31.4" directly above "Weekly lineup strength:
  // 42.75", two names for two quantities a manager cannot tell apart, which on
  // the live payload print the SAME NUMBER (97.39 and 97.39). Prose-ified debug
  // output is still debug output. The block is now "Where you stand" and says
  // two things in sentences; spec §2.6 leaves the roster-value figures to the
  // Roster surface, which can label them properly.
  //
  // The suppression half of the old spec is DELIBERATELY GONE, not lost. It
  // asserted that no cut candidate was ever named, on the reasoning that a
  // named list "reads as a drop directive". David's 2026-08-30 ruling settles
  // that the other way — "call a spade a spade, and I've given it the green
  // light" — so the named cut is now a REQUIREMENT, pinned in MorningRead.test
  // and morningRead.test. What survives here is the part the ruling did not
  // touch: unranked internal objects (divergence cards, partner rankings) still
  // never reach this surface, because nothing on this page is built from them.
  it("says where you stand in sentences, and leaves the internal object counts off the page", async () => {
    mockFetch(200, whatChangedResponse());

    render(<DailyWhatChanged />);

    const stand = await screen.findByTestId("wc-where-you-stand");
    expect(screen.queryByText(/current_not_delta=true/i)).toBeNull();
    expect(screen.queryByRole("region", { name: /structural current-state/i })).toBe(
      null,
    );

    // The posture, in the dictionary's word, with what produced it said out
    // loud — "Contending" reading as a plan somebody made is exactly the sort
    // of unearned meaning a bare enum acquires on the way to a screen.
    expect(stand.textContent).toMatch(/contending/i);
    expect(stand.textContent).toMatch(/formula over your roster/i);
    // The roster against its limit, once.
    expect(stand.textContent).toMatch(/30 players in 28 spots/i);

    // The staleness FACT survives, in words, beside the claim it qualifies:
    // DG-111 says how old and that it is stale, DG-109's dictionary says WHICH
    // pair of clocks the age was measured between, and the producer's own basis
    // token stays verbatim in the title attribute.
    const postureNotice = within(stand).getAllByTestId("wc-section-notice")[0];
    expect(postureNotice?.textContent).toMatch(/Team posture snapshot/i);
    expect(postureNotice?.textContent).toMatch(/1\.5 hours old/i);
    expect(postureNotice?.textContent).toMatch(/stale/i);
    expect(postureNotice?.getAttribute("title")).toContain("team_posture_snapshot");
    expect(within(stand).queryByText(/team_posture_snapshot/)).toBeNull();

    // THE DEBUG DUMP. Every one of these rendered on David's front page.
    const page = document.body.textContent ?? "";
    for (const debugLine of [
      "Starting lineup value",
      "Weekly lineup strength",
      "Top-asset core value",
      "Whole-roster value, capped",
      "Card count",
      "Partner ranking count",
      "David roster player count",
      "League roster count",
      "Team count",
      "Cuts required:",
      "Total players:",
      "Total capacity:",
    ]) {
      expect(page, `the debug dump must not come back: ${debugLine}`).not.toContain(
        debugLine,
      );
    }

    // Unranked internal objects still never surface: nothing on this page is
    // built from a divergence card or a partner ranking, so nothing about them
    // — names or counts — has any business being printed here.
    expect(screen.queryByText("Hidden Divergence Asset One")).toBeNull();
    expect(screen.queryByText("Hidden Divergence Asset Two")).toBeNull();
    expect(screen.queryByText("Hidden Depth Asset")).toBeNull();
    // The cut candidates in this fixture are ranked 97 and 98 — no rank-1
    // candidate — so the recommendation refuses to name one and says why.
    expect(screen.queryByText("Hidden Cut Candidate")).toBeNull();
    expect(screen.queryByText("Second Hidden Cut Candidate")).toBeNull();
    expect(screen.getByTestId("wc-worth-a-look").textContent).toMatch(
      /don't have a value-ranked list/i,
    );

    expect(screen.queryByText(/[▲▼⬆⬇]/u)).toBeNull();
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

  // DG-113 REPLACES THE TWO TAPE SPECS. The tape was a monospace strip reading
  // "Market Sync Active: 12 consecutive days tracked · Projection Update: July
  // 5, current" at the top of the right rail. Spec §2.1 retires it along with
  // the rail; the same two endpoints now feed ONE freshness sentence with a dot
  // and, behind it, a health sheet listing each feed as a plain row. The facts
  // are the same facts; the register is a sentence rather than a ticker.
  it("says how the feeds are doing in one sentence, with the detail one press down", async () => {
    // The dot carries BOTH freshness axes — how old this report is, and how the
    // feeds behind it are doing. This spec is about the second, so the first is
    // pinned to the fixture's own morning rather than left to drift with the
    // wall clock (which would make a 2026-07-01 fixture permanently stale).
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-01T13:00:00+00:00"));
    mockFetchByUrl({
      "/api/league/what-changed": { status: 200, body: whatChangedResponse() },
      "/api/system/capture-health": { status: 200, body: captureHealthResponse() },
      "/api/system/model-provenance": {
        status: 200,
        body: modelProvenanceResponse(),
      },
    });

    render(<DailyWhatChanged />);

    const freshness = await screen.findByTestId("wc-freshness");
    await waitFor(() =>
      expect(freshness.getAttribute("data-status")).not.toBe("unknown"),
    );
    // One healthy store in this fixture, and its `last_capture_date` equals the
    // payload's own `checked_at` day (2026-07-05), so today's capture really is
    // in and the sentence may say so.
    //
    // PANEL FIX: the green branch used to say "complete and up to date" off
    // `store_status` alone. `ok` means nothing missing, nothing stale, nothing
    // thin — and a store can be all three while today's capture simply has not
    // come due yet, so "up to date" was carrying more weight than the field can
    // bear. There are two branches now and this fixture takes the stronger one
    // BECAUSE the dates match, not because the status is ok.
    expect(freshness.textContent).toMatch(/our daily feed is in for today/i);
    expect(
      freshness.querySelector("[data-freshness-dot]")?.getAttribute("data-status"),
    ).toBe("ok");
    // The tape's own markup is gone from the page entirely.
    expect(document.querySelector(".dg-ui-tape")).toBeNull();

    const sheet = await openHealthSheet();
    expect(within(sheet).getByText(/Daily market prices/i)).toBeTruthy();
    expect(within(sheet).getByText(/Last ran Sunday, July 5/i)).toBeTruthy();
    // A healthy feed says when it ran and nothing else — no "Status: ok" stamp.
    expect(within(sheet).queryByText(/^Status:/)).toBeNull();
    expect(
      within(sheet).getByText(/Every model file our projections are served from/i),
    ).toBeTruthy();
    // The registry version is a receipt, not prose.
    expect(within(sheet).queryByText(/registry version 4/i)).toBeNull();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/system/capture-health",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/system/model-provenance",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("never claims the feeds are fine when it could not read them", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-01T13:00:00+00:00"));
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

    const freshness = await screen.findByTestId("wc-freshness");
    await waitFor(() =>
      expect(freshness.textContent).toMatch(/couldn't reach the feed check/i),
    );
    // THE FAILURE THIS SPEC EXISTS FOR: an endpoint that did not answer is not
    // evidence that the feeds are healthy, and "all our daily feeds are
    // complete and up to date" is the easiest false sentence on this page.
    expect(freshness.textContent).not.toMatch(/complete and up to date/i);
    expect(freshness.textContent).not.toMatch(/ran on time/i);
    // Both halves of the green branch, so neither can be reached from an
    // endpoint that never answered.
    expect(freshness.textContent).not.toMatch(/in for today/i);
    expect(freshness.textContent).not.toMatch(/landed everything/i);
    // The dot goes neutral rather than green — it has nothing to be green about.
    expect(
      freshness.querySelector("[data-freshness-dot]")?.getAttribute("data-status"),
    ).toBe("unknown");

    const sheet = await openHealthSheet();
    expect(
      within(sheet).getByText(/feed check didn't answer this morning/i),
    ).toBeTruthy();
    // Model provenance failed its own parse, so it says nothing at all rather
    // than reporting a status it never received.
    expect(within(sheet).queryByText(/model file/i)).toBeNull();
  });

  it("names which feed is behind and why, from the condition that actually degraded it", async () => {
    const health = captureHealthResponse();
    // A store that RAN today but is missing four days of history — the live
    // shape of market_divergence_history. The spec's example sentence for this
    // state ("ran a day behind") would be false three ways over.
    health.overall_status = "degraded";
    const store = health.stores[0] as NonNullable<(typeof health.stores)[0]>;
    health.stores = [
      {
        ...store,
        caveats: [],
        store_id: "market_divergence_history",
        store_status: "degraded",
        timeline: {
          ...store.timeline,
          expected_days: 53,
          present_days: 49,
          missing_dates_count: 4,
        },
      },
    ];
    mockFetchByUrl({
      "/api/league/what-changed": { status: 200, body: whatChangedResponse() },
      "/api/system/capture-health": { status: 200, body: health },
      "/api/system/model-provenance": {
        status: 200,
        body: modelProvenanceResponse(),
      },
    });

    render(<DailyWhatChanged />);

    const freshness = await screen.findByTestId("wc-freshness");
    await waitFor(() =>
      expect(freshness.textContent).toMatch(/gaps earlier in their history/i),
    );
    expect(freshness.textContent).not.toMatch(/behind|late|a day late/i);
    expect(
      freshness.querySelector("[data-freshness-dot]")?.getAttribute("data-status"),
    ).toBe("attention");

    const sheet = await openHealthSheet();
    expect(within(sheet).getByText(/Model-versus-market price gaps/i)).toBeTruthy();
    expect(
      within(sheet).getByText(/4 days of its 53-day history never landed/i),
    ).toBeTruthy();
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

  it("renders AssetRows with real identity assets and lane symmetry, market first", async () => {
    mockFetch(200, increment1Response());

    const { container } = render(<DailyWhatChanged />);

    await waitFor(() => expect(screen.getByText("Bijan Robinson")).toBeTruthy());
    const model = screen.getByRole("region", { name: /model output/i });
    const market = screen.getByTestId("wc-your-roster");
    // DG-113 REVERSES THIS. Model-first was argued as "the model is the
    // rational anchor; market-first would anchor the morning read on crowd
    // noise before the model's evaluation" — sound when this page was a
    // two-lane delta surface with nothing above it. It has a verdict above it
    // now, and the verdict is what anchors the morning. Meanwhile the model
    // region on a live payload is one honest sentence explaining why no
    // comparison ran, which is not the thing to open a morning on.
    //
    // The isolation the ordering was really protecting is untouched and is
    // asserted below: a market price never renders inside the model region and
    // vice versa.
    expect(
      market.compareDocumentPosition(model) & Node.DOCUMENT_POSITION_FOLLOWING,
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

    // DG-113 §2.4: the day's three biggest roster moves lead as CARDS, so a
    // one-mover payload puts Luther Burden on a card rather than a tape row.
    const card = within(market).getByText("Luther Burden").closest(".dg-wc__card");
    expect(card).toBeTruthy();
    expect(within(card as HTMLElement).getByText("+99")).toBeTruthy();
    // This row carries no `current_value`, so the card shows the change and no
    // level — it does not reach into the sparkline's last point to manufacture
    // one. A delta without its level is worse than a delta alone only if you
    // invent the level.
    expect(card?.querySelector(".dg-wc__card-value")).toBeNull();
    // A card carries the market lane and only the market lane. That is not the
    // lane-symmetry rule being dropped — a tape row shows an explicit dash
    // because model and market rows are INTERLEAVED there and the dash says
    // which lane is silent. All three cards sit inside the market region, whose
    // own subtitle says what they are, so there is no pairing to be silent
    // about and a dash would be furniture.
    expect(card?.querySelector("[data-lane='model']")).toBeNull();
    expect(card?.querySelector("[data-lane='market']")).toBeTruthy();
    expect(
      within(market).getByText(/kept separate from our own projections/i),
    ).toBeTruthy();
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

    // DG-113: quietDay is still derived from HIS roster's movers, and the copy
    // is still scoped to the roster so it stays true on days the league moved
    // and his did not. "No valuation deltas observed" is gone with the rest of
    // the lab register; the verdict says the same fact in a sentence.
    const verdict = await screen.findByTestId("wc-verdict");
    // roster_deltas is EMPTY with a comparison that ran, which is not "nothing
    // moved" — it is "none of his players carried a price on both days". The
    // two are different facts and the sentence says the one that is true.
    expect(verdict.textContent).toMatch(
      /didn't price any of your players on both of the last two days/i,
    );
    expect(verdict.textContent).not.toMatch(/held steady|nothing moved/i);
    expect(
      screen.getByText(/here is the roster the report was built against/i),
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

// SR-16 / DG-081 — the number David acts on is how many of HIS players moved,
// not a list-length sum (51) and not league-wide churn (456). Flat roster rows
// are present-in-both-snapshots rows, NOT movers — counting .length would print
// a near-constant 26 every morning (wallpaper).
//
// DG-113 keeps every one of those rules and moves them into the verdict
// sentence. The ValueHero that carried them ("Your roster moved · 26 · largest
// Tank Dell +139") was a figure with a caption where the morning needs a
// sentence, and a bare count never answered "am I ok" — 26 is a good morning or
// a bad one depending on facts the tile could not hold.
describe("DailyWhatChanged roster movement in the verdict", () => {
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

  it("counts his movers, names the largest, and keeps the league total honest", async () => {
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
    const verdict = await screen.findByTestId("wc-verdict");

    // 26 roster rows, all 26 moved, Tank Dell largest at +139. The COVERAGE
    // clause is the DG-113 addition: `roster_deltas` holds only the roster
    // players the market priced in both captures (26 here against a 30-player
    // roster in the fixture's sleeper snapshot), and a "your roster" total that
    // hid that would be rounding a subset up to the whole team.
    expect(verdict.textContent).toMatch(/priced 26 of your 30 players/i);
    expect(verdict.textContent).toMatch(/every one of them moved/i);
    expect(verdict.textContent).toMatch(/Tank Dell most of all, up 139/);
    // 25 league rows, none of them his (different sleeper ids), so nothing is
    // excluded and the count is the plain one.
    expect(screen.getByText(/Showing 25 of 456 movers league-wide\./)).toBeTruthy();
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
    const verdict = await screen.findByTestId("wc-verdict");

    // 26 priced, only 6 of them moved. The sentence must not report 26 movers.
    expect(verdict.textContent).toMatch(/priced 26 of your 30 players/i);
    expect(verdict.textContent).toMatch(/6 of them moved/);
    expect(verdict.textContent).not.toMatch(/26 of them moved/);
    expect(verdict.textContent).not.toMatch(/every one of them moved/i);
    expect(verdict.textContent).toMatch(/True Mover 6 most of all, up 60/);
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
    await screen.findByTestId("wc-verdict");

    expect(screen.getByText(/Showing 25 movers\./)).toBeTruthy();
    expect(screen.queryByText(/Showing 25 of/)).toBeNull();
  });

  // DG-113 §2.5 — THE DUPLICATE DAVID SAW. Both lists are slices of the same
  // `deltas_by_id` map (daily_diff.py:135-160), so a roster player who is also
  // a top mover lands in both with identical numbers. Filtering him out of the
  // league list is only half the job: the footer count has to account for where
  // those rows went, or a silently shrinking total is a second untruth.
  it("takes his own players out of the league list and says where they went", async () => {
    const shared = marketRow("Shared Mover", 300, 7);
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          market: {
            roster_deltas: [shared, marketRow("Roster Only", 20, 8)],
            top_movers: [
              shared,
              marketRow("League Only One", 250, 200),
              marketRow("League Only Two", 200, 201),
            ],
            total_movers_count: 457,
          },
          model: { deltas: [] },
        },
      }),
    );

    render(<DailyWhatChanged />);
    await screen.findByTestId("wc-verdict");

    const mine = screen.getByTestId("wc-your-roster");
    const league = screen.getByTestId("wc-around-the-league");
    expect(within(mine).getAllByText("Shared Mover").length).toBe(1);
    expect(within(league).queryByText("Shared Mover")).toBeNull();
    expect(within(league).getByText("League Only One")).toBeTruthy();
    expect(
      within(league).getByText(
        /Showing 2 of 457 movers league-wide — 1 more is yours, and is up in what moved\./,
      ),
    ).toBeTruthy();
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

  it("AppShell wires the feed to the player card: clicking a mover opens it", async () => {
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

    // DG-114: the press opens the CARD, not a preview of it. The card is the
    // producer's, so what it renders is the producer's answer for this player —
    // here /api/players/ is unmocked and degrades on 503 exactly as production
    // does. What this check owns is that the press routed THIS player's id into
    // the card, and that the card is what opened.
    const card = await screen.findByRole("dialog", { name: "Player card" });
    expect(card).toBeTruthy();
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/players/player-2");
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

    const market = await screen.findByTestId("wc-your-roster");
    // Prose on the surface: the reason is said in words, not as a raw key…
    const marketNote = within(market).getByTestId("wc-market-degraded");
    expect(marketNote.textContent).toMatch(/Market snapshot stale/);
    expect(marketNote.textContent).not.toContain("market_snapshot_stale");
    // …and the raw producer token is still reachable, verbatim, in the receipt,
    // which DG-113 moved one press down into the health sheet.
    await openHealthSheet();
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

    await waitFor(() => expect(screen.getByTestId("wc-your-roster")).toBeTruthy());
    const market = screen.getByTestId("wc-your-roster");

    // 1. The false claim is gone — both halves of it.
    expect(within(market).queryByText(/held steady/i)).toBeNull();
    expect(
      within(market).getByText(/No day-over-day comparison for your roster/i),
    ).toBeTruthy();
    expect(
      within(screen.getByTestId("wc-around-the-league")).getByText(
        /No day-over-day comparison league-wide/i,
      ),
    ).toBeTruthy();
    // …and the verdict does not fill the silence either.
    expect(screen.getByTestId("wc-verdict").textContent).toMatch(
      /couldn't compare your prices against an earlier day, so we can't say what moved/i,
    );

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

    // 3. The health sheet still records it — `producerReasons` reads the MARKET
    //    comparison window now, not only the model's. DG-120: as the sentence
    //    the dictionary holds for it, since a status is a message and not an
    //    address. The producer's exact token stays on the notice's title.
    const sheet = await openHealthSheet();
    expect(screen.getByTestId("wc-provenance").textContent).toContain(
      "Not enough days captured yet to compare one to the next.",
    );
    // 4. And the market source survives in the sheet even though the comparison
    //    window carried no dates.
    expect(sheet.textContent).toContain("fantasycalc_overlay");
  });

  // PANEL FIX. This test used to assert the section said "held steady" here.
  // It ran, and it found none of his players carrying a price on BOTH dates —
  // `roster_deltas` keeps only players present in both captures
  // (daily_diff.py:143-147). That is a coverage fact, not a movement fact, and
  // the verdict already said so; the section was two inches below it saying the
  // opposite. The two now agree, and the test pins the agreement rather than
  // the string.
  it("calls an empty priced set a coverage fact, in the verdict and in the section alike", async () => {
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

    await waitFor(() => expect(screen.getByTestId("wc-your-roster")).toBeTruthy());
    const market = screen.getByTestId("wc-your-roster");
    const coverage = /didn't price any of your players on both of the last two days/i;
    expect(within(market).getByText(coverage)).toBeTruthy();
    expect(screen.getByTestId("wc-verdict").textContent).toMatch(coverage);
    // Neither surface may retype "we have no prices to compare" as "the prices
    // did not change".
    expect(within(market).queryByText(/held steady/i)).toBeNull();
    expect(screen.getByTestId("wc-verdict").textContent).not.toMatch(
      /held steady|nothing moved/i,
    );
    expect(within(market).queryByTestId("wc-market-degraded")).toBeNull();
    // No rows on screen means no trend slots to explain, so the note that
    // explains blank ones does not render either.
    expect(within(market).queryByTestId("wc-trend-note")).toBeNull();
  });

  // DG-113, found rendering on the LIVE payload for 2026-08-30.
  it("treats two model runs on one day as a refusal, not a degradation, and points at nothing", async () => {
    mockFetch(
      200,
      whatChangedResponse({
        daily_diff: {
          model: {
            status: "model_multi_vintage_ambiguous",
            deltas: [],
            comparison_window: { status: "model_multi_vintage_ambiguous" },
            feature_freshness: null,
            pvo_staleness: null,
          },
        },
      }),
    );

    render(<DailyWhatChanged />);

    const notice = await screen.findByTestId("wc-model-degraded");
    // The producer refuses to emit a comparison rather than fabricate one
    // (daily_diff.py:255-271). That is a refusal, exactly like
    // insufficient_history — not a fault — and spending "degraded" on it is the
    // DG-047 cry-wolf pattern in new clothes.
    expect(notice.textContent).toMatch(/couldn't compare our projections/i);
    expect(notice.textContent).not.toMatch(/came back degraded/i);
    // The dictionary sentence renders whole, as its own sentence, rather than
    // spliced between em-dashes with its full stop shaved off.
    expect(notice.textContent).toContain(
      "Two different model runs landed on the same day, so we will not claim what moved overnight.",
    );
    // …and there is no closing instruction, because there are no model rows
    // below for one to apply to. "Treat the model numbers below as provisional"
    // was pointing at an empty region.
    expect(notice.textContent).not.toMatch(/below/i);
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

    await waitFor(() => expect(screen.getByTestId("wc-your-roster")).toBeTruthy());
    const notice = within(screen.getByTestId("wc-your-roster")).getByTestId(
      "wc-market-degraded",
    );
    expect(notice.textContent).toMatch(/came back degraded/i);
    expect(notice.textContent).toMatch(/could not read your Sleeper roster/i);
    expect(notice.getAttribute("title")).toBe("missing_sleeper_snapshot");
  });
});
