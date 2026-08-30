// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TradeLab } from "./TradeLab";

// DG-111 — trade_lab_fe_mitigation_v1 replacement copy. David's 2026-08-29
// ruling is the sign-off that released the byte lock; the replacement is
// recorded verbatim in the ticket. Every fact the lock protected survives:
// no win/lose verdict is computed, fit is not judged, the two pricings stay
// separate rather than blended, a stale or missing price says so in its own
// lane, and the call is the manager's. Only the register changed.
const MITIGATION_COPY =
  "We price both sides two ways — what the dynasty market is paying, and what our model says — and keep the two apart instead of blending them into one number. Where a price is stale or missing, that lane says so. We don't call the winner and we don't judge whether the deal fits your team: that part is yours.";

const STYLE_SOURCE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "TradeLab.css"),
  "utf-8",
);

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

function marketReconciliation() {
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

function installFetch() {
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
}

async function runComparison() {
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "cha" },
  });
  fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
  fireEvent.click(screen.getByRole("button", { name: /price this trade/i }));
}

function assertNodeAppearsBefore(first, second) {
  const order = first.compareDocumentPosition(second);
  expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
}

function ruleBody(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return STYLE_SOURCE.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, "m"))?.[1] ?? "";
}

describe("Trade Lab mitigation contract", () => {
  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders the exact mitigation copy on initial load before any lane pair exists", () => {
    render(<TradeLab />);

    const disclaimer = screen.getByText(MITIGATION_COPY);

    expect(disclaimer).toBeTruthy();
    expect(screen.queryByTestId("trade-lane-pair")).toBeNull();
    expect(disclaimer.closest("[hidden], [aria-hidden='true']")).toBeNull();
    expect(
      screen.queryByRole("button", { name: /expand|show|learn more/i }),
    ).toBeNull();
  });

  it("renders the equal-weight lane pair after the mitigation copy after a run", async () => {
    installFetch();

    render(<TradeLab />);
    const disclaimer = screen.getByText(MITIGATION_COPY);
    await runComparison();

    await waitFor(() => {
      expect(screen.getByTestId("trade-lane-pair")).toBeTruthy();
    });

    const lanePair = screen.getByTestId("trade-lane-pair");
    const modelLane = within(lanePair).getByTestId("model-lane");
    const marketLane = within(lanePair).getByTestId("market-lane");
    assertNodeAppearsBefore(disclaimer, lanePair);
    expect(modelLane.getAttribute("data-visual-weight")).toBe("equal");
    expect(marketLane.getAttribute("data-visual-weight")).toBe("equal");
    expect(modelLane.getAttribute("data-primary")).toBeNull();
    expect(marketLane.getAttribute("data-primary")).toBeNull();
    expect(lanePair.getAttribute("data-primary")).toBeNull();
  });

  it("keeps model and market lane containers free of lane-specific visual dominance CSS", () => {
    const bannedLaneContainerRules =
      /\b(border(?:-[a-z]+)?|background(?:-color)?|color|font-size|font-weight)\s*:/i;

    expect(ruleBody(".dg-lane--model")).not.toMatch(bannedLaneContainerRules);
    expect(ruleBody(".dg-lane--market")).not.toMatch(bannedLaneContainerRules);
  });

  it("keeps the mitigation copy readable at narrow viewport widths", () => {
    globalThis.innerWidth = 360;

    render(<TradeLab />);

    const disclaimer = screen.getByText(MITIGATION_COPY);
    expect(disclaimer.textContent).toBe(MITIGATION_COPY);
    expect(disclaimer.closest(".dg-trade-lab")).toBeTruthy();
    expect(disclaimer.closest("[hidden], [aria-hidden='true']")).toBeNull();
  });

  it("scans result surfaces for verdict leakage without false-failing on the disclaimer", async () => {
    installFetch();

    render(<TradeLab />);
    const disclaimer = screen.getByText(MITIGATION_COPY);
    await runComparison();

    await waitFor(() => {
      expect(screen.getByTestId("trade-lane-pair")).toBeTruthy();
      expect(screen.getByTestId("trade-verdict")).toBeTruthy();
    });

    // The point of this line: the note itself legitimately uses verdict
    // vocabulary ("we don't call the winner"), so the result-surface scan below
    // must be scoped to the RESULT surfaces and never false-fail on it.
    expect(disclaimer.textContent).toMatch(/\bwinner\b/i);
    const resultText = [
      screen.getByTestId("trade-lane-pair").textContent ?? "",
      screen.getByTestId("trade-verdict").textContent ?? "",
    ].join(" ");
    expect(resultText).not.toMatch(
      /\b(suitable|unsuitable|recommended|buy|sell|hold|winner|loser|favors)\b/i,
    );
    expect(resultText).not.toMatch(/\b(blended|combined|average[-\s]?delta)\b/i);
  });
});
