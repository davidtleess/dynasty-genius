// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

function marketOverlay() {
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
    divergence_context: {
      caveats: [],
      decision_supported: false,
      percentile_delta: 0.32,
      sigma_threshold: 0.25,
      signal_label: "model_higher_than_market",
      source_signal_status: "gates_passed",
    },
    format_key: "dynasty_sf_ppr",
    label: "Chase",
    market_value: 8400,
    market_volatility: null,
    resolution: "player_sleeper_id",
    source: "fantasycalc",
    source_timestamp: "2026-05-24T17:19:44Z",
    trend_30d: null,
  };
}

function marketReconciliation(overrides = {}) {
  return {
    adjusted_market_received: 7100,
    adjusted_market_sent: 8400,
    caveats: ["fantasycalc_cache_warm"],
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
    sent_assets: [marketOverlay()],
    source_timestamp: "2026-05-24T17:19:44Z",
    ...overrides,
  };
}

function catalogResponse() {
  return {
    caveats: [],
    decision_supported: false,
    query: "cha",
    results: [
      {
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
      },
    ],
    source_timestamp: "2026-05-24T17:19:44Z",
  };
}

function okJson(body) {
  return Promise.resolve({
    json: () => Promise.resolve(body),
    ok: true,
    status: 200,
  });
}

function failedJson(status = 503) {
  return Promise.resolve({
    json: () => Promise.resolve({ detail: "unavailable" }),
    ok: false,
    status,
  });
}

function installFetch({
  model = okJson(modelReconciliation()),
  market = okJson(marketReconciliation()),
} = {}) {
  globalThis.fetch = vi.fn((url, init = {}) => {
    const href = String(url);
    if (href.startsWith("/api/trade/assets")) {
      return okJson(catalogResponse());
    }
    if (href.endsWith("/api/trade/reconcile/market") && init.method === "POST") {
      return market;
    }
    if (href.endsWith("/api/trade/reconcile") && init.method === "POST") {
      return model;
    }
    throw new Error(`unexpected fetch ${href}`);
  });
}

async function runComparison() {
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "cha" },
  });
  fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
  fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));
}

function banner() {
  return screen.getByText(/not decision-grade/i);
}

describe("TradeLab honest lane degradation", () => {
  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("always shows a non-dismissible decision_supported=false banner", async () => {
    installFetch();

    render(<TradeLab />);

    expect(banner()).toBeTruthy();
    expect(screen.queryByRole("button", { name: /dismiss|close/i })).toBeNull();

    await runComparison();

    await waitFor(() => {
      expect(screen.getByTestId("model-lane")).toBeTruthy();
      expect(screen.getByTestId("market-lane")).toBeTruthy();
    });
    expect(banner()).toBeTruthy();
    expect(screen.queryByRole("button", { name: /dismiss|close/i })).toBeNull();
  });

  it("renders both lanes unavailable when both endpoints return 503", async () => {
    installFetch({ model: failedJson(503), market: failedJson(503) });

    render(<TradeLab />);
    await runComparison();

    await waitFor(() => {
      expect(
        screen.getByRole("status", { name: /model lane unavailable/i }),
      ).toBeTruthy();
      expect(
        screen.getByRole("status", { name: /market lane unavailable/i }),
      ).toBeTruthy();
    });
    expect(screen.queryByText("41.2")).toBeNull();
    expect(screen.queryByText("8400")).toBeNull();
    expect(screen.queryByText("-1300")).toBeNull();
  });

  it("keeps model ready while market shows stale 200 caveats", async () => {
    installFetch({
      model: okJson(modelReconciliation()),
      market: okJson(
        marketReconciliation({
          caveats: ["source_timestamp_is_fetch_time_not_publish_time"],
        }),
      ),
    });

    render(<TradeLab />);
    await runComparison();

    await waitFor(() => {
      expect(screen.getByTestId("model-lane")).toBeTruthy();
      expect(screen.getByTestId("market-lane")).toBeTruthy();
    });

    expect(within(screen.getByTestId("model-lane")).getByText("41.2")).toBeTruthy();
    expect(
      within(screen.getByTestId("market-lane")).getByText(
        "source_timestamp_is_fetch_time_not_publish_time",
      ),
    ).toBeTruthy();
    expect(
      within(screen.getByTestId("market-lane")).getByText(/stale|source/i),
    ).toBeTruthy();
    expect(screen.getByText(/not decision-grade/i)).toBeTruthy();
    expect(screen.getByTestId("market-lane").textContent).not.toMatch(
      /verdict|win|loss/i,
    );
  });

  it("degrades only the model lane if model returns 503 while market returns 200", async () => {
    installFetch({
      model: failedJson(503),
      market: okJson(marketReconciliation()),
    });

    render(<TradeLab />);
    await runComparison();

    await waitFor(() => {
      expect(
        screen.getByRole("status", { name: /model lane unavailable/i }),
      ).toBeTruthy();
      expect(screen.getByTestId("market-lane")).toBeTruthy();
    });
    expect(within(screen.getByTestId("market-lane")).getByText("-1300")).toBeTruthy();
    expect(screen.getByTestId("market-lane").textContent).not.toMatch(
      /decision-grade/i,
    );
    expect(screen.getByText(/not decision-grade/i)).toBeTruthy();
  });

  it("treats a 200 response that fails Zod parsing as that lane unavailable", async () => {
    installFetch({
      model: okJson(modelReconciliation()),
      market: okJson({ caveats: ["shape_mismatch"] }),
    });

    render(<TradeLab />);
    await runComparison();

    await waitFor(() => {
      expect(screen.getByTestId("model-lane")).toBeTruthy();
      expect(
        screen.getByRole("status", { name: /market lane unavailable/i }),
      ).toBeTruthy();
    });
    expect(within(screen.getByTestId("model-lane")).getByText("41.2")).toBeTruthy();
    expect(screen.queryByText("-1300")).toBeNull();
  });
});
