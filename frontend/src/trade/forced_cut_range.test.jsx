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
    expect(within(lane).getByText(/value-at-risk range/i)).toBeTruthy();
    expect(within(lane).getByText(/recovery range/i)).toBeTruthy();
    expect(within(lane).getByText(/adjusted fairness delta range/i)).toBeTruthy();
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
    expect(text).toMatch(/transaction blocked/i);
    expect(text).toMatch(/manual capacity review required/i);
    expect(text).not.toContain("77.7");
    expect(text).not.toMatch(/value-at-risk range|recovery range/i);
    expect(text).not.toMatch(/blocked\b.*blocked\b/i);
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
    expect(
      within(lane).getByText(/fantasycalc capacity value-at-risk range/i),
    ).toBeTruthy();
    expect(within(lane).getByText(/fantasycalc recovery range/i)).toBeTruthy();
    for (const required of ["700", "1000", "200", "500"]) {
      expect(text).toContain(required);
    }
    expect(text).toContain("market replacement pool stale");
    expect(text).not.toMatch(/xVAR|PVO|forced_cut_penalty_xvar|penalty_status/i);

    rerender(
      <MarketLanePanel
        reconciliation={marketReconciliation({ david_forced_cut_penalty: null })}
      />,
    );
    lane = screen.getByTestId("market-lane");
    text = lane.textContent ?? "";
    expect(text).toMatch(/no capacity penalty/i);
    expect(text).not.toMatch(/value-at-risk range|recovery range/i);
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
    expect(
      within(lane).getByText(/fantasycalc capacity value-at-risk range/i),
    ).toBeTruthy();
    expect(within(lane).getByText(/fantasycalc recovery range/i)).toBeTruthy();
    expect(text).toMatch(/market replacement data stale/i);
    expect(text).not.toMatch(/uncertain_pool_unavailable/i);
  });
});
