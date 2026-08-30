// @vitest-environment jsdom
//
// DG-116 — Trade Lab: the surface David ruled, driven end to end through
// <TradeLab /> so the assertions are about what a manager actually sees.
//
// David's 2026-08-30 design panel, verbatim option label: **"Both prices,
// plainly"** — state the arithmetic on BOTH pricings and name the disagreement,
// with NO blended take/pass imperative (weighing the two when they disagree is
// a call he explicitly declined to bless).
//
// THE HONESTY LAW THIS FILE GUARDS: the two pricings are on DIFFERENT SCALES.
// The model lane counts value over a replacement-level player; the market lane
// carries FantasyCalc's own points. The backend says so itself in the caveat
// `fantasycalc_raw_scale_not_xvar` (market_reconciler.py:21-27). So the copy
// must SAY the scales differ rather than inviting a subtraction across them,
// and the verdict may never print a single merged number.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TradeLab } from "./TradeLab";

const STYLE_SOURCE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "TradeLab.css"),
  "utf-8",
);

function ruleBody(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return STYLE_SOURCE.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, "m"))?.[1] ?? "";
}

function tradeSide(sideValue) {
  return {
    assets: [],
    consolidation_factor: 1,
    side_value: sideValue,
    xvar_sum: sideValue,
  };
}

// The DISAGREEING case, which is the one David's ruling is really about: the
// market has him giving up more than he gets, our model has him getting back
// more than he gives. Numbers chosen so each row's on-screen arithmetic is
// self-consistent (44.6 - 41.2 = 3.4; 7100 - 8400 = -1300).
function modelReconciliation(overrides = {}) {
  return {
    adjusted_david_received_value: 44.6,
    adjusted_fairness_delta: 3.4,
    adjusted_fairness_delta_range: [1.2, 5.6],
    adjusted_favors: "david",
    adjusted_favors_status: "david",
    adjusted_received_value_range: [42.4, 46.8],
    adjusted_within_parity_band: false,
    base_evaluation: {
      caveats: [],
      decision_supported: false,
      fairness_delta: 3.4,
      favors: "david",
      favors_xvar_margin: 3.4,
      side_a: tradeSide(41.2),
      side_b: tradeSide(44.6),
      within_parity_band: false,
    },
    caveats: [],
    decision_supported: false,
    roster_penalty: {
      decision_supported: false,
      forced_cut_candidates: [],
      forced_cut_recovery_range: [1.2, 2.3],
      forced_cut_value_at_risk_range: [0.8, 1.9],
      forced_cut_penalty_xvar: 0,
      penalty_caveats: [],
      penalty_status: "ok",
      pool_deficits: {},
      post_trade_overflow: 0,
      post_trade_total_players: 25,
    },
    ...overrides,
  };
}

function marketOverlay(label, sleeperId, signalLabel) {
  return {
    asset_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: sleeperId,
      sleeper_id: sleeperId,
    },
    caveats: [],
    coverage_gap: null,
    decision_supported: false,
    divergence_context: {
      caveats: [],
      decision_supported: false,
      percentile_delta: 0.32,
      sigma_threshold: 0.25,
      signal_label: signalLabel,
      source_signal_status: null,
    },
    format_key: "dynasty_sf_ppr",
    label,
    market_value: 8400,
    market_volatility: null,
    resolution: "player_sleeper_id",
    source: "fantasycalc",
    source_timestamp: null,
    trend_30d: null,
  };
}

function marketReconciliation(overrides = {}) {
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
    received_assets: [marketOverlay("Jaxson Dart", "200", "model_lower_than_market")],
    sent_assets: [marketOverlay("Ja'Marr Chase", "100", "model_higher_than_market")],
    source_timestamp: null,
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
        label: "Ja'Marr Chase",
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
    source_timestamp: null,
  };
}

function okJson(body) {
  return Promise.resolve({
    json: () => Promise.resolve(body),
    ok: true,
    status: 200,
  });
}

function installFetch({
  model = modelReconciliation(),
  market = marketReconciliation(),
} = {}) {
  globalThis.fetch = vi.fn((url, init = {}) => {
    const href = String(url);
    if (href.startsWith("/api/trade/assets")) {
      return okJson(catalogResponse());
    }
    if (href.endsWith("/api/trade/reconcile/market") && init.method === "POST") {
      return okJson(market);
    }
    if (href.endsWith("/api/trade/reconcile") && init.method === "POST") {
      return okJson(model);
    }
    throw new Error(`unexpected fetch ${href}`);
  });
}

function priceButton() {
  return screen.getByRole("button", { name: /price this trade/i });
}

async function priceATrade() {
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "cha" } });
  fireEvent.click(await screen.findByRole("button", { name: "Ja'Marr Chase" }));
  fireEvent.click(priceButton());
  await waitFor(() => expect(screen.getByTestId("trade-verdict")).toBeTruthy());
  return screen.getByTestId("trade-verdict");
}

describe("Trade Lab — both prices, plainly", () => {
  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("states the arithmetic on BOTH pricings in plain sentences", async () => {
    installFetch();
    render(<TradeLab />);

    const verdict = await priceATrade();
    const text = verdict.textContent ?? "";

    expect(text).toMatch(/by market prices/i);
    expect(text).toMatch(/by our model/i);
    // Market row: the two side totals and their difference, all three visible.
    expect(text).toContain("8,400");
    expect(text).toContain("7,100");
    expect(text).toContain("1,300");
    // Model row: same three facts on the model's own scale.
    expect(text).toContain("41.2");
    expect(text).toContain("44.6");
    expect(text).toContain("3.4");
  });

  it("names the disagreement when the two pricings point opposite ways", async () => {
    installFetch();
    render(<TradeLab />);

    const text = (await priceATrade()).textContent ?? "";

    expect(text).toMatch(/disagree/i);
    expect(text).toMatch(/giv(e|ing) up more than you get/i);
    expect(text).toMatch(/get(ting)? back more than you give/i);
  });

  it("says the two pricings are on different scales instead of inviting a subtraction", async () => {
    installFetch();
    render(<TradeLab />);

    const text = (await priceATrade()).textContent ?? "";

    expect(text).toMatch(/different scales/i);
    expect(text).toMatch(/FantasyCalc/);
    expect(text).toMatch(/value over a replacement-level player/i);
    // The one number that must never exist: a merged score across the scales.
    expect(text).not.toMatch(/\b(blended|combined|net difference|overall score)\b/i);
  });

  it("issues no take/pass imperative — David declined to bless the weighting", async () => {
    installFetch();
    render(<TradeLab />);

    const text = (await priceATrade()).textContent ?? "";

    expect(text).not.toMatch(
      /\b(take (this|it|the deal)|pass (on|up)|accept|reject|do it|walk away|pull the trigger)\b/i,
    );
    expect(text).not.toMatch(/\b(good|bad|great|terrible) (deal|trade)\b/i);
  });

  it("speaks the per-player disagreement in words, never the backend signal key", async () => {
    installFetch();
    render(<TradeLab />);

    const text = (await priceATrade()).textContent ?? "";

    expect(text).not.toMatch(/model_higher_than_market|model_lower_than_market/);
    expect(text).toContain("We price him higher than the market does");
    expect(text).toContain("The market prices him higher than we do");
    expect(text).toContain("Ja'Marr Chase");
    expect(text).toContain("Jaxson Dart");
  });

  it("lists the assets on BOTH sides of the market lane, not the sent side only", async () => {
    installFetch();
    render(<TradeLab />);
    await priceATrade();

    const marketLane = screen.getByTestId("market-lane");
    expect(within(marketLane).getByText(/Ja'Marr Chase/)).toBeTruthy();
    expect(within(marketLane).getByText(/Jaxson Dart/)).toBeTruthy();
  });

  it("tells a manager what to do on an empty board instead of showing blank space", () => {
    installFetch();
    render(<TradeLab />);

    const empty = screen.getByRole("region", { name: /build a trade/i });
    expect(empty.textContent).toMatch(/search/i);
    expect(empty.textContent.length).toBeGreaterThan(120);
  });

  it("gives every control a visible label", () => {
    installFetch();
    render(<TradeLab />);

    // The player box was an unlabelled white rectangle: an aria-label only a
    // screen reader could hear, and no placeholder.
    const box = screen.getByRole("searchbox");
    expect(box.labels?.length ?? 0).toBeGreaterThan(0);
    expect(box.getAttribute("placeholder")).toBeTruthy();

    const roster = screen.getByRole("spinbutton");
    expect(roster.labels?.length ?? 0).toBeGreaterThan(0);
  });

  it("styles the native controls instead of leaving browser chrome on the dark canvas", () => {
    const input = ruleBody(".dg-trade-lab input");
    const button = ruleBody(".dg-trade-lab button");

    for (const body of [input, button]) {
      expect(body).toMatch(/appearance:\s*none/);
      expect(body).toMatch(/background:\s*var\(--dg-/);
      expect(body).toMatch(/color:\s*var\(--dg-/);
      expect(body).toMatch(/border:\s*1px solid var\(--dg-/);
    }
    expect(ruleBody(".dg-trade-lab :focus-visible")).toMatch(
      /outline:\s*2px solid var\(--dg-focus\)/,
    );
  });
});
