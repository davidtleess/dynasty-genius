// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
    adjusted_favors: "david",
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
      forced_cut_penalty_xvar: 3.1,
      penalty_caveats: [],
      post_trade_overflow: 1,
      post_trade_total_players: 25,
    },
    ...overrides,
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
    sent_assets: [],
    source_timestamp: "2026-05-24T17:19:44Z",
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

function assertNoFavorsVerdictText(text) {
  expect(text).not.toMatch(/favors/i);
  expect(text).not.toMatch(/\bdavid\b/i);
  expect(text).not.toMatch(/\bcounterparty\b/i);
}

describe("Trade Lab favors non-render guard", () => {
  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("keeps backend favors fields out of ModelLanePanel DOM text", () => {
    render(<ModelLanePanel reconciliation={modelReconciliation()} />);

    assertNoFavorsVerdictText(screen.getByTestId("model-lane").textContent ?? "");
  });

  it("keeps backend favors fields out of rendered TradeLab result surfaces", async () => {
    globalThis.fetch = vi.fn((url, init = {}) => {
      const href = String(url);
      if (href.startsWith("/api/trade/assets")) {
        return okJson(catalogResponse());
      }
      if (href.endsWith("/api/trade/reconcile/market") && init.method === "POST") {
        return okJson(marketReconciliation());
      }
      if (href.endsWith("/api/trade/reconcile") && init.method === "POST") {
        return okJson(modelReconciliation());
      }
      throw new Error(`unexpected fetch ${href}`);
    });

    render(<TradeLab />);
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "cha" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
    fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

    await waitFor(() => {
      expect(screen.getByTestId("model-lane")).toBeTruthy();
      expect(screen.getByTestId("market-lane")).toBeTruthy();
      expect(screen.getByTestId("divergence-strip")).toBeTruthy();
    });

    assertNoFavorsVerdictText(screen.getByTestId("model-lane").textContent ?? "");
    assertNoFavorsVerdictText(screen.getByTestId("divergence-strip").textContent ?? "");
    expect(within(screen.getByTestId("model-lane")).getByText("41.2")).toBeTruthy();
  });
});
