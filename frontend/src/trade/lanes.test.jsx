// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DivergenceStrip } from "./DivergenceStrip";
import { MarketLanePanel } from "./MarketLanePanel";
import { ModelLanePanel } from "./ModelLanePanel";
import { TradeLab } from "./TradeLab";

function tradeSide(sideValue) {
  return {
    assets: [],
    consolidation_factor: 1,
    side_value: sideValue,
    xvar_sum: sideValue,
  };
}

function modelReconciliation(overrides = {}) {
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
      forced_cut_candidates: [],
      forced_cut_recovery_range: [1.2, 2.3],
      forced_cut_value_at_risk_range: [0.8, 1.9],
      forced_cut_penalty_xvar: 3.1,
      penalty_caveats: [],
      penalty_status: "ok",
      pool_deficits: {},
      post_trade_overflow: 1,
      post_trade_total_players: 25,
    },
    ...overrides,
  };
}

function divergenceContext(signalLabel = "model_higher_than_market") {
  return {
    caveats: [],
    decision_supported: false,
    percentile_delta: 0.32,
    sigma_threshold: 0.25,
    signal_label: signalLabel,
    source_signal_status: "gates_passed",
  };
}

function marketOverlay(overrides = {}) {
  return {
    asset_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: "100",
      sleeper_id: "100",
    },
    caveats: [],
    coverage_gap: null,
    decision_supported: false,
    divergence_context: divergenceContext(),
    format_key: "dynasty_sf_ppr",
    label: "Chase",
    market_value: 8400,
    market_volatility: null,
    resolution: "player_sleeper_id",
    source: "fantasycalc",
    source_timestamp: "2026-05-24T17:19:44Z",
    trend_30d: null,
    ...overrides,
  };
}

function marketReconciliation(overrides = {}) {
  return {
    adjusted_market_received: 7100,
    adjusted_market_sent: 8400,
    caveats: ["fantasycalc_cache_warm"],
    counterparty_forced_cut_penalty: null,
    counterparty_market_penalty_status: "not_requested",
    coverage_gaps: ["fantasycalc_uncovered"],
    david_forced_cut_penalty: null,
    decision_supported: false,
    format_key: "dynasty_sf_ppr",
    market_delta_for_david: -1300,
    market_received_raw: 7100,
    market_sent_raw: 8400,
    market_source: "fantasycalc",
    realism_warnings: [
      {
        caveats: [],
        decision_supported: false,
        message: "Incoming package has lower market concentration.",
        metrics: { incoming_to_premium_ratio: 0.2 },
        severity: "advisory",
        warning_type: "package_dilution_warning",
      },
    ],
    received_assets: [],
    sent_assets: [marketOverlay()],
    source_timestamp: "2026-05-24T17:19:44Z",
    ...overrides,
  };
}

function mockCatalogEntry() {
  return {
    asset_id: "100",
    caveats: [],
    decision_supported: false,
    kind: "player",
    label: "Chase",
    market_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: "100",
      sleeper_id: "100",
    },
    model_payload: {
      decision_supported: false,
      is_prospect: false,
      player_id: "100",
      position: "WR",
      xvar: 22.5,
    },
    position: "WR",
    roster_owner_id: 1,
    roster_owner_name: "Woodbury Riders",
  };
}

function okJson(body) {
  return Promise.resolve({
    json: () => Promise.resolve(body),
    ok: true,
    status: 200,
  });
}

describe("Trade Lab lane panels", () => {
  it("renders model lane values and forced-cut ranges without backend favors fields", () => {
    render(<ModelLanePanel reconciliation={modelReconciliation()} />);

    const lane = screen.getByTestId("model-lane");
    const text = lane.textContent ?? "";
    expect(lane.getAttribute("data-lane")).toBe("model");
    expect(within(lane).getByText("41.2")).toBeTruthy();
    expect(within(lane).getByText("39.1")).toBeTruthy();
    expect(within(lane).getByText(/value-at-risk range/i)).toBeTruthy();
    expect(within(lane).getByText(/recovery range/i)).toBeTruthy();
    expect(within(lane).getByText(/adjusted fairness delta range/i)).toBeTruthy();
    for (const required of ["0.8", "1.9", "1.2", "2.3", "-1.4", "4.2"]) {
      expect(text).toContain(required);
    }
    expect(text).not.toContain("Forced-cut penalty3.1");
    expect(text).not.toMatch(/favors/i);
    expect(text).not.toContain("david");
  });

  it("renders market lane backend values and neutral per-asset divergence labels", () => {
    render(<MarketLanePanel reconciliation={marketReconciliation()} />);

    const lane = screen.getByTestId("market-lane");
    expect(lane.getAttribute("data-lane")).toBe("market");
    expect(within(lane).getByText("8400")).toBeTruthy();
    expect(within(lane).getByText("7100")).toBeTruthy();
    expect(within(lane).getByText("-1300")).toBeTruthy();
    expect(within(lane).getByText("Model higher than market")).toBeTruthy();
    expect(within(lane).getByText(/advisory/i)).toBeTruthy();
    expect(within(lane).getByText("fantasycalc_uncovered")).toBeTruthy();
    expect(within(lane).getByText("fantasycalc_cache_warm")).toBeTruthy();
    expect(lane.textContent).not.toMatch(/\bwin\b|\bloss\b|\bmust\b/i);
  });

  it("renders forced-cut candidate names in the model lane", () => {
    render(
      <ModelLanePanel
        reconciliation={modelReconciliation({
          roster_penalty: {
            decision_supported: false,
            forced_cut_candidates: [
              { decision_supported: false, full_name: "Bench WR", position: "WR" },
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
        })}
      />,
    );

    expect(within(screen.getByTestId("model-lane")).getByText("Bench WR")).toBeTruthy();
  });

  it("keeps model and market lanes in distinct physical containers", () => {
    render(
      <>
        <ModelLanePanel reconciliation={modelReconciliation()} />
        <MarketLanePanel reconciliation={marketReconciliation()} />
      </>,
    );

    const modelLane = screen.getByTestId("model-lane");
    const marketLane = screen.getByTestId("market-lane");
    expect(modelLane).not.toBe(marketLane);
    expect(modelLane.getAttribute("data-lane")).toBe("model");
    expect(marketLane.getAttribute("data-lane")).toBe("market");
  });
});

describe("DivergenceStrip", () => {
  it("shows model and market deltas as separate labelled facts without a blended number", () => {
    render(
      <DivergenceStrip
        model={modelReconciliation({ adjusted_fairness_delta: 2.1 })}
        market={marketReconciliation({ market_delta_for_david: -1300 })}
      />,
    );

    const strip = screen.getByTestId("divergence-strip");
    expect(within(strip).getByText(/model lane/i)).toBeTruthy();
    expect(within(strip).getByText("2.1")).toBeTruthy();
    expect(within(strip).getByText(/market lane/i)).toBeTruthy();
    expect(within(strip).getByText("-1300")).toBeTruthy();
    expect(strip.textContent).not.toMatch(/combined|blended|average|vs/i);
    expect(strip.textContent).not.toContain("-1297.9");
  });

  it.each([
    ["model_higher_than_market", "model_higher_than_market"],
    ["inside_band", "inside_band"],
    ["unavailable", "unavailable"],
  ])("surfaces backend signal label %s without client-side verdict wording", (label) => {
    render(
      <DivergenceStrip
        model={modelReconciliation()}
        market={marketReconciliation({
          sent_assets: [
            marketOverlay({ divergence_context: divergenceContext(label) }),
          ],
        })}
      />,
    );

    const strip = screen.getByTestId("divergence-strip");
    expect(strip.textContent).toContain(label);
    expect(strip.textContent).not.toMatch(/\bwin\b|\bloss\b|\bfair\b|\bmust\b/i);
  });

  it("degrades gracefully when lane data is missing", () => {
    render(<DivergenceStrip model={null} market={null} />);

    const strip = screen.getByTestId("divergence-strip");
    expect(strip.textContent).toMatch(/model lane/i);
    expect(strip.textContent).toMatch(/market lane/i);
    expect(strip.textContent).not.toMatch(/NaN|undefined|null/);
  });
});

describe("TradeLab two-lane response wiring", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("validates run responses and renders both lane panels without a blended number", async () => {
    globalThis.fetch = (url, init = {}) => {
      const href = String(url);
      if (href.startsWith("/api/trade/assets")) {
        return okJson({
          caveats: [],
          decision_supported: false,
          query: "cha",
          results: [mockCatalogEntry()],
          source_timestamp: "2026-05-24T17:19:44Z",
        });
      }
      if (href.endsWith("/api/trade/reconcile/market") && init.method === "POST") {
        return okJson(marketReconciliation());
      }
      if (href.endsWith("/api/trade/reconcile") && init.method === "POST") {
        return okJson(modelReconciliation());
      }
      throw new Error(`unexpected fetch ${href}`);
    };

    render(<TradeLab />);
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "cha" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    await waitFor(() => {
      expect(screen.getByTestId("model-lane")).toBeTruthy();
      expect(screen.getByTestId("market-lane")).toBeTruthy();
    });
    // Delta appears in both the market panel and the wired DivergenceStrip;
    // scope each assertion so the duplicate is intentional, not ambiguous.
    expect(within(screen.getByTestId("model-lane")).getByText("41.2")).toBeTruthy();
    expect(within(screen.getByTestId("market-lane")).getByText("-1300")).toBeTruthy();
    expect(screen.getByTestId("divergence-strip")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/combined|blended|average/i);
    expect(document.body.textContent).not.toMatch(/favors/i);
  });
});
