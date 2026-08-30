// @vitest-environment jsdom
//
// DG-110 — "hard to find things / clunky" (David's first-user verdict,
// dimension 4). A player's name is the product's most natural handle: every
// surface that prints one must open that player's card, and there must be one
// search that finds any tracked player from anywhere WITHOUT quietly editing
// the trade draft on the way. These are the decisive checks for that contract.

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { leaguePulseResponse } from "../league-pulse/fixtures";
import { AppShell } from "./AppShell";

const DRAFT_KEY = "dg.tradeLab.draft";

function catalogEntry(overrides = {}) {
  return {
    asset_id: "13269",
    caveats: [],
    decision_supported: false,
    kind: "player",
    label: "Chase",
    market_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: "13269",
      sleeper_id: "13269",
    },
    model_payload: {
      decision_supported: false,
      is_prospect: false,
      player_id: "13269",
      position: "QB",
      xvar: 10.31,
    },
    position: "QB",
    roster_owner_id: 1,
    roster_owner_name: "Dleess",
    ...overrides,
  };
}

function catalogResponse(results = [catalogEntry()]) {
  return {
    caveats: [],
    decision_supported: false,
    query: "cha",
    results,
    source_timestamp: "2026-08-29T13:00:46+00:00",
  };
}

function rosterAuditResponse() {
  return {
    status: "active",
    engine: "pvo_assembler_v1",
    reason: "ok",
    model_status_by_position: { QB: "PROVISIONAL" },
    caveats: [],
    dropped_player_count: 0,
    decision_supported: false,
    players: [
      {
        player_id: "roster-pid-1",
        sleeper_id: "11570",
        full_name: "Rasheen Ali",
        position: "RB",
        nfl_team: "BAL",
        age: 25,
        is_prospect: false,
        model_grade: "PRE_MODEL",
        model_status_applies: false,
        signal_completeness: 0.28,
        inputs_present: [],
        inputs_missing: [],
        counter_argument: { text: null, status: "experimental", caveats: [] },
        top_drivers: { items: [], caveats: [] },
        risk_flags: { items: [], caveats: [] },
        caveats: ["no_market_overlay"],
        decision_supported: false,
      },
      {
        player_id: "roster-pid-2",
        sleeper_id: "11565",
        full_name: "J.J. McCarthy",
        position: "QB",
        nfl_team: "MIN",
        age: 23,
        is_prospect: false,
        model_grade: "ACTIVE_B",
        model_status_applies: true,
        signal_completeness: 0.83,
        inputs_present: [],
        inputs_missing: [],
        counter_argument: { text: null, status: "experimental", caveats: [] },
        top_drivers: { items: [], caveats: [] },
        risk_flags: { items: [], caveats: [] },
        caveats: [],
        decision_supported: false,
      },
    ],
    qb_context_cards: [
      {
        player_id: "roster-pid-2",
        full_name: "J.J. McCarthy",
        identity_coverage: "NONE",
        context_role: "context_signal",
        epa_per_dropback: null,
        cpoe: null,
        dakota: null,
        dropback_count: null,
        pass_attempts: null,
        qb_context_annotations: [],
        qb_context_caveats: ["missing_qb_college_context"],
        source_qb_context_annotations: "cfbd_qb_context_annotations",
        decision_supported: false,
      },
    ],
  };
}

function rosterCapacityResponse() {
  return {
    artifact_status: "ok",
    status: "ok",
    capacity_health: {
      total_players: 27,
      total_capacity: 26,
      total_capacity_cuts_required: 1,
      active_slot_overflow: 1,
      by_slot_class: { active: 20, reserve: 4, taxi: 2 },
      reserve_unrestricted: true,
    },
    candidates: [
      {
        sleeper_player_id: "11570",
        full_name: "Rasheen Ali",
        position: "RB",
        cut_priority: 1,
        candidate_source: "capacity_ordered",
        raw_xvar: -27.83,
        dvs: 20.7,
        xvar_pct: 36.8,
        median_projection_2y: 3.255,
        value_field_status: {},
      },
    ],
    scenarios: [],
    unrostered_pool_range: {},
    excluded_counts: {},
    caveats: [],
    created_at: "2026-08-29T12:00:00+00:00",
    sleeper_snapshot_captured_at: "2026-08-29T11:00:00+00:00",
    decision_supported: false,
  };
}

function whatChangedResponse() {
  return {
    schema_version: "war_room_2_what_changed_v1",
    generated_at: "2026-08-29T12:00:00+00:00",
    decision_supported: false,
    overall_status: "ok",
    daily_diff: {
      decision_supported: false,
      overall_status: "ok",
      market: {
        status: "ok",
        decision_supported: false,
        market_source: "fantasycalc",
        comparison_window: { from_date: "2026-08-28", to_date: "2026-08-29" },
        roster_deltas: [
          {
            sleeper_id: "12508",
            player_key: "12508",
            player_name: "Jaxson Dart",
            position: "QB",
            value_delta: 306,
            value_delta_direction: "up",
            overall_rank_delta: -9,
            overall_rank_delta_direction: "up",
            position_rank_delta: -2,
            position_rank_delta_direction: "up",
          },
        ],
        top_movers: [],
        total_movers_count: 1,
        entered: [
          {
            sleeper_id: "player-3",
            player_key: "entered-3",
            player_name: "New Arrival",
          },
        ],
        exited: [
          { sleeper_id: "player-4", player_key: "exited-4", player_name: "Gone Guy" },
        ],
      },
      model: {
        status: "ok",
        decision_supported: false,
        comparison_window: { status: "insufficient_history" },
        deltas: [],
        vintage_changed: false,
        feature_freshness: null,
        pvo_staleness: null,
      },
    },
    structural_context: {
      status: "ok",
      decision_supported: false,
      current_not_delta: true,
      sections: {
        team_posture: {
          status: "ok",
          decision_supported: false,
          current_not_delta: true,
        },
        team_value: {
          status: "ok",
          decision_supported: false,
          current_not_delta: true,
        },
        league_opportunity: {
          status: "ok",
          decision_supported: false,
          current_not_delta: true,
        },
        drop_pressure: {
          status: "ok",
          decision_supported: false,
          current_not_delta: true,
        },
        sleeper_snapshot: {
          status: "ok",
          decision_supported: false,
          current_not_delta: true,
        },
      },
    },
  };
}

function playerDetailResponse() {
  return {
    caveats: [],
    decision_supported: false,
    degradation: null,
    divergence: null,
    evidence: null,
    frozen_prediction: null,
    identity: {
      age: 22,
      draft_class: 2025,
      name: "Player Card",
      nfl_draft_pick: 25,
      nfl_draft_round: 1,
      position: "QB",
      sleeper_id: "12508",
      team: "NYG",
    },
    market: null,
    model: null,
    model_status: "modeled",
    sleeper_id: "12508",
    source_timestamps: {},
  };
}

// AppShell fetches more endpoints than any one check cares about; anything not
// named here degrades honestly on 503 exactly as the product does.
function mockEndpoints(routes) {
  globalThis.fetch = vi.fn().mockImplementation((input) => {
    const url = typeof input === "string" ? input : String(input);
    const key = Object.keys(routes).find((route) => url.startsWith(route));
    const body = key === undefined ? { detail: "down" } : routes[key];
    const ok = key !== undefined;
    return Promise.resolve({
      ok,
      status: ok ? 200 : 503,
      json: async () => body,
    });
  });
}

function inspector() {
  return screen.getByRole("complementary", { name: "Player inspector" });
}

async function expectCardOpened(name) {
  await waitFor(() => {
    expect(inspector().dataset.state).toBe("open");
  });
  expect(within(inspector()).getByText(name)).toBeTruthy();
}

function goToSurface(label) {
  fireEvent.click(
    within(screen.getByRole("navigation", { name: "Primary surfaces" })).getByRole(
      "button",
      { name: label },
    ),
  );
}

beforeEach(() => {
  localStorage.clear();
  window.history.replaceState(null, "", "/");
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("DG-110 · a player is reachable from anywhere", () => {
  it("finds any tracked player from the shell without touching the trade draft", async () => {
    mockEndpoints({
      "/api/trade/assets": catalogResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);

    const search = screen.getByRole("searchbox", { name: /find a player/i });
    expect(search.getAttribute("placeholder")).toBeTruthy();

    fireEvent.change(search, { target: { value: "cha" } });
    fireEvent.click(await screen.findByRole("button", { name: "Chase" }));

    await expectCardOpened("Chase");
    // The retired defect: the only search that existed added its result to a
    // PERSISTED trade draft as a side effect. Inspecting must never do that.
    expect(localStorage.getItem(DRAFT_KEY)).toBeNull();
  });

  it("opens a player's card from his name on Roster Audit, and keeps the row detail", async () => {
    mockEndpoints({
      "/api/roster/audit": rosterAuditResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);
    goToSurface("Roster Audit");

    fireEvent.click(await screen.findByRole("button", { name: /^Open Rasheen Ali/ }));
    await expectCardOpened("Rasheen Ali");

    // The row's inline evidence is truth-bearing and survives the rewiring.
    // DG-109 turned the raw `no_market_overlay` key into the sentence it always
    // meant, so the receipt is asserted by its words now — reworded, not lost.
    fireEvent.click(screen.getByRole("button", { name: /expand rasheen ali/i }));
    expect(
      screen.getByText(/Market prices are deliberately left out of this read/i),
    ).toBeTruthy();
  });

  it("opens a player's card from a QB context card", async () => {
    mockEndpoints({
      "/api/roster/audit": rosterAuditResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);
    goToSurface("Roster Audit");

    const qb = await screen.findByRole("region", { name: /qb context cards/i });
    fireEvent.click(within(qb).getByRole("button", { name: /^Open J\.J\. McCarthy/ }));
    await expectCardOpened("J.J. McCarthy");
  });

  it("opens a player's card from a Roster Capacity cut candidate", async () => {
    mockEndpoints({
      "/api/roster/capacity": rosterCapacityResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);
    goToSurface("Roster Capacity");

    fireEvent.click(await screen.findByRole("button", { name: /^Open Rasheen Ali/ }));
    await expectCardOpened("Rasheen Ali");
  });

  it("opens a player's card from a League Pulse capacity pool", async () => {
    mockEndpoints({
      "/api/league/pulse": leaguePulseResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);
    goToSurface("League Pulse");

    fireEvent.click(await screen.findByRole("button", { name: /^Open Depth WR/ }));
    await expectCardOpened("Depth WR");
  });

  it("opens a player's card from the front page's entered and exited chips", async () => {
    mockEndpoints({
      "/api/league/what-changed": whatChangedResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);

    fireEvent.click(await screen.findByRole("button", { name: /^Open New Arrival/ }));
    await expectCardOpened("New Arrival");

    fireEvent.click(screen.getByRole("button", { name: /^Open Gone Guy/ }));
    await expectCardOpened("Gone Guy");
  });

  it("opens a player's card from the front page's largest-mover hero line", async () => {
    mockEndpoints({
      "/api/league/what-changed": whatChangedResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);

    const hero = (await screen.findByText("Your roster moved")).closest(
      ".dg-ui-value-hero",
    );
    // The basis keeps saying exactly what it said: how many moved, and by how
    // much the largest one moved. Only the name became a handle.
    expect(hero.textContent).toContain("1 of your players; largest Jaxson Dart +306");
    fireEvent.click(within(hero).getByRole("button", { name: /^Open Jaxson Dart/ }));
    await expectCardOpened("Jaxson Dart");
  });
});

describe("DG-110 · a player is reachable from the trade result lanes", () => {
  function tradeSide(sideValue) {
    return {
      assets: [],
      consolidation_factor: 1,
      side_value: sideValue,
      xvar_sum: sideValue,
    };
  }

  function modelReconciliation() {
    return {
      adjusted_david_received_value: 36,
      adjusted_fairness_delta: 2.1,
      adjusted_fairness_delta_range: [-1.4, 4.2],
      adjusted_favors: "david",
      adjusted_favors_status: "uncertain_range_crosses_parity",
      adjusted_received_value_range: [34.8, 40.4],
      adjusted_within_parity_band: true,
      base_evaluation: {
        caveats: [],
        decision_supported: false,
        fairness_delta: 2.1,
        favors: "david",
        favors_xvar_margin: 2.1,
        side_a: tradeSide(41.2),
        side_b: tradeSide(39.1),
        within_parity_band: true,
      },
      caveats: [],
      decision_supported: false,
      roster_penalty: {
        decision_supported: false,
        forced_cut_candidates: [
          { full_name: "Cut Candidate", sleeper_player_id: "11570", position: "RB" },
        ],
        forced_cut_recovery_range: [1.2, 2.3],
        forced_cut_value_at_risk_range: [0.8, 1.9],
        forced_cut_penalty_xvar: 3.1,
        penalty_caveats: [],
        penalty_status: "ok",
        pool_deficits: {},
        post_trade_overflow: 1,
        post_trade_total_players: 25,
      },
    };
  }

  function marketReconciliation() {
    return {
      adjusted_market_received: 7100,
      adjusted_market_sent: 8400,
      caveats: [],
      counterparty_forced_cut_penalty: null,
      counterparty_market_penalty_status: "not_requested",
      coverage_gaps: [],
      david_forced_cut_penalty: null,
      decision_supported: false,
      format_key: "dynasty_sf_ppr",
      market_delta_for_david: -1300,
      market_received_raw: 7100,
      market_sent_raw: 8400,
      market_source: "fantasycalc",
      realism_warnings: [],
      received_assets: [],
      sent_assets: [
        {
          asset_ref: {
            asset_kind: "player",
            decision_supported: false,
            player_id: "13269",
            sleeper_id: "13269",
          },
          caveats: [],
          coverage_gap: null,
          decision_supported: false,
          divergence_context: null,
          format_key: "dynasty_sf_ppr",
          label: "Chase",
          market_value: 8400,
          resolution: "player_sleeper_id",
          source: "fantasycalc",
          source_timestamp: "2026-08-29T13:00:46+00:00",
          trend_30d: null,
        },
      ],
      source_timestamp: "2026-08-29T13:00:46+00:00",
    };
  }

  it("opens a player's card from a market lane asset and a forced-cut candidate", async () => {
    mockEndpoints({
      "/api/trade/assets": catalogResponse(),
      "/api/trade/reconcile/market": marketReconciliation(),
      "/api/trade/reconcile": modelReconciliation(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);
    goToSurface("Trade Lab");

    fireEvent.change(
      screen.getByRole("searchbox", { name: "Search tradeable assets" }),
      { target: { value: "cha" } },
    );
    fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
    fireEvent.click(screen.getByRole("button", { name: "Run comparison" }));

    const marketLane = await screen.findByTestId("market-lane");
    fireEvent.click(within(marketLane).getByRole("button", { name: /^Open Chase/ }));
    await expectCardOpened("Chase");

    const modelLane = screen.getByTestId("model-lane");
    fireEvent.click(
      within(modelLane).getByRole("button", { name: /^Open Cut Candidate/ }),
    );
    await expectCardOpened("Cut Candidate");
  });
});

describe("DG-110 · the command palette indexes players", () => {
  it("has a visible trigger and a placeholder, and opens a player from a typed name", async () => {
    mockEndpoints({
      "/api/trade/assets": catalogResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);

    fireEvent.click(screen.getByRole("button", { name: /search .*⌘K|⌘K/i }));
    const palette = screen.getByRole("textbox", { name: "Command palette" });
    expect(palette.getAttribute("placeholder")).toBeTruthy();

    fireEvent.change(palette, { target: { value: "cha" } });
    const option = await screen.findByRole("option", { name: /Chase/ });
    fireEvent.click(option);
    await expectCardOpened("Chase");
  });
});

describe("DG-110 · the inspector never opens empty", () => {
  it("stays closed on first load and opens on the first selection", async () => {
    mockEndpoints({
      "/api/trade/assets": catalogResponse(),
      "/api/players/": playerDetailResponse(),
    });
    render(<AppShell />);

    expect(inspector().dataset.state).toBe("closed");

    fireEvent.change(screen.getByRole("searchbox", { name: /find a player/i }), {
      target: { value: "cha" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
    await expectCardOpened("Chase");
  });
});
