// @vitest-environment jsdom

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  zTradeMarketReconciliation,
  zTradeRosterReconciliation,
} from "../lib/api/zod.gen";
import { MarketLanePanel } from "./MarketLanePanel";
import { ModelLanePanel } from "./ModelLanePanel";

function tradeSide(sideValue) {
  return {
    assets: [],
    consolidation_factor: 1,
    side_value: sideValue,
    xvar_sum: sideValue,
  };
}

function modelReconciliation(overrides = {}) {
  const base = {
    adjusted_david_received_value: 36,
    adjusted_fairness_delta: 2.1,
    adjusted_fairness_delta_range: [-4.25, 6.75],
    adjusted_favors: "david",
    adjusted_favors_status: "uncertain_range_crosses_parity",
    adjusted_received_value_range: [32.25, 43.25],
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
    reason: "within_parity_band",
    roster_penalty: {
      decision_supported: false,
      forced_cut_candidates: [],
      forced_cut_penalty_xvar: 19.5,
      forced_cut_recovery_range: [0, 19.5],
      forced_cut_value_at_risk_range: [0, 19.5],
      penalty_caveats: ["replacement_pool_stale"],
      penalty_status: "uncertain_pool_unavailable",
      pool_deficits: { WR: 2 },
      post_trade_overflow: 1,
      post_trade_total_players: 25,
    },
    status: "active",
  };
  return {
    ...base,
    ...overrides,
    roster_penalty: {
      ...base.roster_penalty,
      ...(overrides.roster_penalty ?? {}),
    },
  };
}

function marketPenalty(overrides = {}) {
  return {
    caveats: ["market_replacement_pool_stale"],
    decision_supported: false,
    forced_cut_candidates: [],
    forced_cut_market_recovery_range: [200, 500],
    forced_cut_market_value_at_risk_range: [700, 1000],
    market_penalty_status: "ok",
    penalty_market_value: 1200,
    post_trade_overflow: 1,
    roster_id: 1,
    unresolved_cut_count: 0,
    ...overrides,
  };
}

/** A priced (or unpriced) forced-cut overlay, as the market lane receives it. */
function marketCutOverlay(label, sleeperId, marketValue) {
  return {
    asset_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: label,
      sleeper_id: sleeperId,
    },
    caveats: [],
    coverage_gap: null,
    decision_supported: false,
    divergence_context: null,
    format_key: "dynasty_sf_ppr",
    label,
    market_value: marketValue,
    market_volatility: null,
    resolution: "player_sleeper_id",
    source: "fantasycalc",
    source_timestamp: null,
    trend_30d: null,
  };
}

function marketReconciliation(overrides = {}) {
  const base = {
    adjusted_market_received: 7100,
    adjusted_market_sent: 8400,
    caveats: [],
    counterparty_forced_cut_penalty: null,
    counterparty_market_penalty_status: "not_requested",
    coverage_gaps: [],
    david_forced_cut_penalty: marketPenalty(),
    decision_supported: false,
    format_key: "dynasty_sf_ppr",
    market_delta_for_david: -1300,
    market_received_raw: 7100,
    market_sent_raw: 8400,
    market_source: "fantasycalc",
    realism_warnings: [],
    received_assets: [],
    sent_assets: [],
    source_timestamp: "2026-05-24T17:19:44Z",
  };
  return { ...base, ...overrides };
}

function assertNoVerdictOrRawBackendTokens(text) {
  expect(text).not.toMatch(/favors/i);
  expect(text).not.toMatch(/\bdavid\b/i);
  expect(text).not.toMatch(/\bcounterparty\b/i);
  expect(text).not.toMatch(/uncertain_range_crosses_parity/i);
  expect(text).not.toMatch(/uncertain_pool_unavailable/i);
  expect(text).not.toMatch(/pool_deficits/i);
  expect(text).not.toMatch(/\bWR\b/);
}

describe("Trade Lab forced-cut range rendering", () => {
  it("renders model-lane backend-provided xVAR ranges without the old gross scalar", () => {
    const fixture = modelReconciliation();
    expect(zTradeRosterReconciliation.safeParse(fixture).success).toBe(true);

    render(<ModelLanePanel reconciliation={fixture} />);

    const lane = screen.getByTestId("model-lane");
    const text = lane.textContent ?? "";
    // DG-116 relabels these rows in plain language; the FACT each row carries
    // is unchanged, and the gross scalar is still never displayed.
    expect(within(lane).getByText(/what the forced cut could cost you/i)).toBeTruthy();
    expect(within(lane).getByText(/what you could get back off waivers/i)).toBeTruthy();
    expect(
      within(lane).getByText(/how far from even, once the cut is counted/i),
    ).toBeTruthy();
    for (const required of ["0", "19.5", "-4.25", "6.75"]) {
      expect(text).toContain(required);
    }
    expect(text).toMatch(/data stale/i);
    expect(text).not.toContain("Forced-cut penalty19.5");
    assertNoVerdictOrRawBackendTokens(text);
    expect(text).not.toMatch(/FantasyCalc|market|PVO/i);
  });

  it("hides ranges and surfaces a hard blocker when the model penalty is blocked", () => {
    render(
      <ModelLanePanel
        reconciliation={modelReconciliation({
          adjusted_fairness_delta_range: null,
          adjusted_received_value_range: null,
          roster_penalty: {
            forced_cut_penalty_xvar: 77.7,
            forced_cut_recovery_range: null,
            forced_cut_value_at_risk_range: null,
            penalty_caveats: ["manual_capacity_review_required"],
            penalty_status: "blocked",
            pool_deficits: { TE: 1 },
          },
        })}
      />,
    );

    const text = screen.getByTestId("model-lane").textContent ?? "";
    // WAS /transaction blocked/i. `penalty_status = "blocked"` is set when the
    // capacity audit did not return ok, or when a forced cut carries no model
    // value (reconciler.py:204-207, :261-284) — both mean "we could not compute
    // the cut's cost", neither means the league would reject the trade.
    expect(text).toMatch(/could not work out what the forced cut would cost/i);
    expect(text).toMatch(/manual capacity review required/i);
    expect(text).not.toContain("77.7");
    expect(text).not.toMatch(
      /what the forced cut could cost you|what you could get back off waivers/i,
    );
    expect(text).not.toMatch(/\bTE\b|pool deficits/i);
  });

  it("renders equal and zero-straddling model ranges neutrally", () => {
    render(
      <ModelLanePanel
        reconciliation={modelReconciliation({
          adjusted_fairness_delta_range: [-3, 3],
          roster_penalty: {
            forced_cut_penalty_xvar: 88.8,
            forced_cut_recovery_range: [12.5, 12.5],
            forced_cut_value_at_risk_range: [0, 0],
            penalty_caveats: [],
            penalty_status: "ok",
          },
        })}
      />,
    );

    const lane = screen.getByTestId("model-lane");
    const text = lane.textContent ?? "";
    expect(text).toContain("12.5");
    expect(text).toContain("-3");
    expect(text).toContain("3");
    expect(text).not.toContain("88.8");
    expect(text).not.toMatch(/positive|negative|green|red|advantage|disadvantage/i);
    expect(lane.querySelector(".dg-forced-cut-range--positive")).toBeNull();
    expect(lane.querySelector(".dg-forced-cut-range--negative")).toBeNull();
  });

  it("fails closed instead of rendering inverted model ranges", () => {
    render(
      <ModelLanePanel
        reconciliation={modelReconciliation({
          adjusted_fairness_delta_range: [555.55, -444.44],
          roster_penalty: {
            forced_cut_penalty_xvar: 99.9,
            forced_cut_recovery_range: [333.33, 222.22],
            forced_cut_value_at_risk_range: [987.65, 123.45],
            penalty_caveats: [],
            penalty_status: "ok",
          },
        })}
      />,
    );

    const text = screen.getByTestId("model-lane").textContent ?? "";
    expect(text).toMatch(/range unavailable/i);
    for (const hidden of [
      "987.65",
      "123.45",
      "333.33",
      "222.22",
      "555.55",
      "-444.44",
      "99.9",
    ]) {
      expect(text).not.toContain(hidden);
    }
  });

  it("renders market-lane FantasyCalc-native capacity ranges and null penalty states", () => {
    const fixture = marketReconciliation();
    expect(zTradeMarketReconciliation.safeParse(fixture).success).toBe(true);

    const { rerender } = render(<MarketLanePanel reconciliation={fixture} />);

    let lane = screen.getByTestId("market-lane");
    let text = lane.textContent ?? "";
    expect(within(lane).getByText(/what the forced cut could cost you/i)).toBeTruthy();
    expect(within(lane).getByText(/what you could get back off waivers/i)).toBeTruthy();
    for (const required of ["700", "1000", "200", "500"]) {
      expect(text).toContain(required);
    }
    expect(text).toContain(
      "Market replacement data is stale, so this range is the widest one possible.",
    );
    expect(text).not.toMatch(/xVAR|PVO|forced_cut_penalty_xvar|penalty_status/i);

    rerender(
      <MarketLanePanel
        reconciliation={marketReconciliation({ david_forced_cut_penalty: null })}
      />,
    );
    lane = screen.getByTestId("market-lane");
    text = lane.textContent ?? "";
    // A null penalty says the cost never came back — never that the roster has
    // room, which the field cannot support.
    expect(text).toMatch(/no forced-cut cost came back/i);
    expect(text).not.toMatch(
      /what the forced cut could cost you|what you could get back off waivers/i,
    );
  });

  it("renders a market stale-data caveat from uncertain status even without backend caveats", () => {
    render(
      <MarketLanePanel
        reconciliation={marketReconciliation({
          david_forced_cut_penalty: marketPenalty({
            caveats: [],
            forced_cut_market_recovery_range: [0, 1200],
            forced_cut_market_value_at_risk_range: [0, 1200],
            market_penalty_status: "uncertain_pool_unavailable",
          }),
        })}
      />,
    );

    const lane = screen.getByTestId("market-lane");
    const text = lane.textContent ?? "";
    expect(within(lane).getByText(/what the forced cut could cost you/i)).toBeTruthy();
    expect(within(lane).getByText(/what you could get back off waivers/i)).toBeTruthy();
    expect(text).toMatch(/market replacement data stale/i);
    expect(text).not.toMatch(/uncertain_pool_unavailable/i);
  });

  // ── DG-116 panel fixes on the market lane ──────────────────────────────────

  it("says the whole forced-cut cost is missing only when none of it was priced", () => {
    render(
      <MarketLanePanel
        reconciliation={marketReconciliation({
          david_forced_cut_penalty: marketPenalty({
            forced_cut_candidates: [],
            forced_cut_market_recovery_range: null,
            forced_cut_market_value_at_risk_range: null,
            market_penalty_status: "blocked",
            penalty_market_value: 0,
            unresolved_cut_count: 1,
          }),
        })}
      />,
    );

    const text = screen.getByTestId("market-lane").textContent ?? "";
    expect(text).toMatch(
      /could not put a market price on the forced cut, so that cost is left out/i,
    );
    expect(text).not.toMatch(/transaction blocked|roster rules/i);
  });

  it("says which part of a multi-cut cost is missing when only some cuts are priced", () => {
    // LIVE: send Jaxson Dart (12508), get Brock Bowers (11604) + Malik Nabers
    // (11632) → market_penalty_status "blocked" with unresolved_cut_count 1,
    // forced_cut_candidates [Rasheen Ali (no price), Kyle Williams (707)],
    // penalty_market_value 707, and received 14,170 → 13,463. The priced cut IS
    // in the numbers (market_reconciler.py:458-462 sums it regardless of the
    // block; :613 subtracts it unconditionally), so "that cost is left out of
    // the numbers here" was false on exactly this payload — while the label
    // above it read "Difference, after the forced cut" on the same screen.
    render(
      <MarketLanePanel
        reconciliation={marketReconciliation({
          adjusted_market_received: 13463,
          market_received_raw: 14170,
          market_delta_for_david: 8288,
          david_forced_cut_penalty: marketPenalty({
            forced_cut_candidates: [
              marketCutOverlay("Rasheen Ali", "11570", null),
              marketCutOverlay("Kyle Williams", "11565", 707),
            ],
            forced_cut_market_recovery_range: null,
            forced_cut_market_value_at_risk_range: null,
            market_penalty_status: "blocked",
            penalty_market_value: 707,
            unresolved_cut_count: 1,
          }),
        })}
      />,
    );

    const text = screen.getByTestId("market-lane").textContent ?? "";
    expect(text).toMatch(/could not put a market price on 1 of the 2 forced cuts/i);
    expect(text).toMatch(/the one we could price is already taken out of the numbers/i);
    expect(text).not.toMatch(/that cost is left out of the numbers here/i);
    // And the label that already flagged the adjustment is still there.
    expect(text).toMatch(/difference, after the forced cut/i);
  });

  it("never explains a capture date the same lane says did not come back", () => {
    // The live payload returns source_timestamp: null while the unconditional
    // base caveat `source_timestamp_is_fetch_time_not_publish_time` resolves to
    // "The capture date above is when we pulled these prices…". Both were on
    // screen together: one denying the date, the other explaining it.
    const { rerender } = render(
      <MarketLanePanel
        reconciliation={marketReconciliation({
          caveats: ["source_timestamp_is_fetch_time_not_publish_time"],
          source_timestamp: null,
        })}
      />,
    );

    let text = screen.getByTestId("market-lane").textContent ?? "";
    expect(text).toMatch(/no capture date came back with these prices/i);
    expect(text).not.toMatch(/the capture date above/i);
    // The FACT the caveat carries survives; only the dangling reference goes.
    expect(text).toMatch(/when we pulled the prices, not when FantasyCalc published/i);

    // With a real timestamp the caveat is unchanged and still points at it.
    rerender(
      <MarketLanePanel
        reconciliation={marketReconciliation({
          caveats: ["source_timestamp_is_fetch_time_not_publish_time"],
        })}
      />,
    );
    text = screen.getByTestId("market-lane").textContent ?? "";
    expect(text).toMatch(/prices pulled/i);
    expect(text).toMatch(/the capture date above/i);
  });

  it("says when the other manager's forced cut could not be priced", () => {
    // `_select_counterparty_penalty` returns "unavailable" for a known roster
    // with inadequate coverage (market_reconciler.py:585-590): the sent side is
    // left unadjusted and no penalty comes back. The run bar invites the manager
    // onto this path, so the decline has to be said out loud.
    render(
      <MarketLanePanel
        reconciliation={marketReconciliation({
          counterparty_market_penalty_status: "unavailable",
        })}
      />,
    );

    const text = screen.getByTestId("market-lane").textContent ?? "";
    expect(text).toMatch(/could not price what the other manager would have to cut/i);
    expect(text).not.toMatch(/unavailable/i);
  });
});
