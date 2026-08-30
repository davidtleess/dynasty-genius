// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarketLanePanel } from "./MarketLanePanel";
import { ModelLanePanel } from "./ModelLanePanel";
import { TradeLab } from "./TradeLab";
import { TradeVerdict } from "./TradeVerdict";

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
    expect(within(lane).getByText(/what the forced cut could cost you/i)).toBeTruthy();
    expect(within(lane).getByText(/what you could get back off waivers/i)).toBeTruthy();
    expect(
      within(lane).getByText(/how far from even, once the cut is counted/i),
    ).toBeTruthy();
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
    // 8,400 is both the side total and this single asset's own price, so the
    // duplicate is expected — the assertion is that the grouped form renders.
    expect(within(lane).getAllByText("8,400").length).toBeGreaterThan(0);
    expect(within(lane).getByText("7,100")).toBeTruthy();
    expect(within(lane).getByText("-1,300")).toBeTruthy();
    expect(
      within(lane).getByText("We price him higher than the market does"),
    ).toBeTruthy();
    expect(within(lane).getByText(/advisory/i)).toBeTruthy();
    // DG-109 review fix: these two lines used to assert that the RAW keys
    // `fantasycalc_uncovered` and `fantasycalc_cache_warm` were on screen — the
    // branch's own test pinning the violation the branch exists to remove. The
    // FACT each one carries still has to be on screen, which is what is asserted
    // now. A coverage gap the dictionary can say, it says:
    expect(
      within(lane).getByText("FantasyCalc does not carry a price for this asset."),
    ).toBeTruthy();
    // ...and one it cannot is still never dropped — it goes to the labelled
    // receipt line rather than being humanized into prose nobody wrote.
    expect(within(lane).getByTestId("untranslated-tokens").textContent).toContain(
      "fantasycalc_cache_warm",
    );
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

describe("TradeVerdict", () => {
  it("prices both sides separately and never merges them into one number", () => {
    render(
      <TradeVerdict
        model={modelReconciliation({
          adjusted_david_received_value: 44.6,
          adjusted_within_parity_band: false,
        })}
        market={marketReconciliation({ market_delta_for_david: -1300 })}
      />,
    );

    const verdict = screen.getByTestId("trade-verdict");
    expect(verdict.textContent).toMatch(/by our model/i);
    expect(verdict.textContent).toMatch(/by market prices/i);
    // Each row's arithmetic is the difference of the two numbers printed beside
    // it — 44.6 - 41.2 on the model scale, 7,100 - 8,400 on the market's.
    expect(verdict.textContent).toContain("3.4");
    expect(verdict.textContent).toContain("1,300");
    expect(verdict.textContent).not.toMatch(/combined|blended|average/i);
    // The one number that would be a lie: a subtraction across the two scales.
    expect(verdict.textContent).not.toContain("-1297.9");
    expect(verdict.textContent).toMatch(/different scales/i);
  });

  it.each([
    ["model_higher_than_market", "We price him higher than the market does"],
    ["model_lower_than_market", "The market prices him higher than we do"],
  ])("says the %s signal in words, never as the backend key", (label, sentence) => {
    render(
      <TradeVerdict
        model={modelReconciliation()}
        market={marketReconciliation({
          sent_assets: [
            marketOverlay({ divergence_context: divergenceContext(label) }),
          ],
        })}
      />,
    );

    const verdict = screen.getByTestId("trade-verdict");
    expect(verdict.textContent).not.toContain(label);
    expect(verdict.textContent).toContain(sentence);
    expect(verdict.textContent).not.toMatch(/\bwin\b|\bloss\b|\bfair\b|\bmust\b/i);
  });

  it("lets the side totals disagree while each player's own price agrees", () => {
    render(
      <TradeVerdict
        model={modelReconciliation({
          adjusted_david_received_value: 2.85,
          adjusted_within_parity_band: false,
        })}
        market={marketReconciliation({
          market_delta_for_david: 2338,
          sent_assets: [
            marketOverlay({ divergence_context: divergenceContext("inside_band") }),
          ],
        })}
      />,
    );

    // The live case this came from: send Jaxson Dart, get Brock Bowers. The
    // market has the deal going one way and the model the other, while neither
    // player's own price is outside the band. Both statements are true, and the
    // copy has to let them stand together.
    const verdict = screen.getByTestId("trade-verdict");
    expect(verdict.textContent).toMatch(/the market and our model disagree here/i);
    expect(verdict.textContent).toMatch(
      /taken one player at a time, our prices and the market's agree/i,
    );
  });

  it("says a comparison is missing rather than implying the prices agree", () => {
    render(
      <TradeVerdict
        model={modelReconciliation()}
        market={marketReconciliation({
          sent_assets: [
            marketOverlay({ divergence_context: divergenceContext("unavailable") }),
          ],
        })}
      />,
    );

    const verdict = screen.getByTestId("trade-verdict");
    expect(verdict.textContent).not.toContain("unavailable");
    expect(verdict.textContent).toMatch(/no player-by-player comparison/i);
  });

  it("names the surviving price when one lane did not load", () => {
    const { rerender } = render(
      <TradeVerdict model={null} market={marketReconciliation()} />,
    );
    expect(screen.getByTestId("trade-verdict").textContent).toMatch(
      /our model's price for this trade did not load/i,
    );

    rerender(<TradeVerdict model={modelReconciliation()} market={null} />);
    const verdict = screen.getByTestId("trade-verdict");
    expect(verdict.textContent).toMatch(
      /the market's price for this trade did not load/i,
    );
    expect(verdict.textContent).not.toMatch(/NaN|undefined|null/);
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
    fireEvent.click(screen.getByRole("button", { name: /price this trade/i }));

    await waitFor(() => {
      expect(screen.getByTestId("model-lane")).toBeTruthy();
      expect(screen.getByTestId("market-lane")).toBeTruthy();
    });
    // Values appear in both the lane panel and the verdict block above it;
    // scope each assertion so the duplicate is intentional, not ambiguous.
    expect(within(screen.getByTestId("model-lane")).getByText("41.2")).toBeTruthy();
    expect(within(screen.getByTestId("market-lane")).getByText("-1,300")).toBeTruthy();
    expect(screen.getByTestId("trade-verdict")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/combined|blended|average/i);
    expect(document.body.textContent).not.toMatch(/favors/i);
  });
});
