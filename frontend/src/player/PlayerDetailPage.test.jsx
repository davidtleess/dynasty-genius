// @vitest-environment jsdom

import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { PlayerDetailPage } from "./PlayerDetailPage";

function modeledDetail(overrides = {}) {
  return zPlayerDetailResponse.parse({
    caveats: ["decision_supported_false"],
    decision_supported: false,
    degradation: null,
    divergence: {
      delta: -0.237,
      status: "model_lower_than_market",
    },
    evidence: {
      caveats: {
        caveats: [],
        items: ["FantasyCalc snapshot is static", "Engine-A prospect context"],
      },
      counter_argument: {
        caveats: [],
        status: "available",
        text:
          "Premium valuation assumes continued high-level rushing or outlier passing efficiency " +
          "while the supporting cast and role remain stable across the first contract.",
      },
      risk_flags: {
        caveats: [],
        items: ["RB age cliff approaching", "projection variance elevated"],
      },
      top_drivers: {
        caveats: [],
        items: ["Round 1 draft capital", "age-adjusted production"],
      },
    },
    identity: {
      age: 22,
      draft_class: 2026,
      name: "Chase",
      nfl_draft_pick: 1,
      nfl_draft_round: 1,
      position: "QB",
      sleeper_id: "13269",
      team: "LVR",
    },
    market: {
      caveats: ["market_overlay_static_caveat"],
      market_rank_overall: 42,
      market_rank_position: 8,
      market_value: 4371,
      source: "fantasycalc",
      source_timestamp: "2026-05-24T17:19:52Z",
      status: "available",
    },
    model: {
      dynasty_value_score: 85.14,
      engine_path: "ENGINE_A",
      model_grade: "PROSPECT_D",
      model_version: "engine_a_v3",
      projection_1y: 6.1,
      projection_2y: 9.8,
      projection_3y: 12.4,
      xvar: 10.31,
      xvar_percentile_position: 0.91,
    },
    model_status: "modeled",
    sleeper_id: "13269",
    source_timestamps: {
      market: "2026-05-24T17:19:52Z",
      pvo: "2026-06-07T14:32:45Z",
    },
    ...overrides,
  });
}

function unmodeledDetail() {
  return modeledDetail({
    degradation: { message: "No active model score for this player category." },
    divergence: {
      delta: null,
      status: "unavailable",
    },
    evidence: null,
    market: {
      caveats: ["market_overlay_unavailable"],
      market_rank_overall: null,
      market_rank_position: null,
      market_value: null,
      source: null,
      source_timestamp: null,
      status: "unavailable",
    },
    model: null,
    model_status: "experimental",
  });
}

function partialDetail() {
  return modeledDetail({
    divergence: {
      delta: null,
      status: "inside_band",
    },
    evidence: {
      caveats: { caveats: [], items: [] },
      counter_argument: {
        caveats: ["counter_argument_unavailable"],
        status: "experimental",
        text: null,
      },
      risk_flags: { caveats: [], items: ["RB age cliff approaching"] },
      top_drivers: { caveats: [], items: [] },
    },
    market: {
      caveats: ["market_overlay_unavailable"],
      market_rank_overall: null,
      market_rank_position: null,
      market_value: null,
      source: null,
      source_timestamp: null,
      status: "unavailable",
    },
  });
}

function mockPlayerDetail(detail) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    json: vi.fn().mockResolvedValue(detail),
    ok: true,
    status: 200,
  });
}

function renderPage(sleeperId = "13269") {
  render(<PlayerDetailPage sleeperId={sleeperId} />);
}

describe("PlayerDetailPage full Decision-Evidence-Card", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches typed detail and renders separated model and market lanes with neutral divergence", async () => {
    mockPlayerDetail(modeledDetail());

    renderPage();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/players/13269");
    });

    const card = await screen.findByRole("article", {
      name: /player detail for chase/i,
    });
    expect(
      within(card).getByText("Descriptive only — not decision-grade."),
    ).toBeTruthy();
    expect(within(card).queryByRole("button", { name: /dismiss/i })).toBeNull();

    const modelLane = within(card).getByTestId("player-model-lane");
    const marketLane = within(card).getByTestId("player-market-lane");
    expect(modelLane.dataset.lane).toBe("model");
    expect(marketLane.dataset.lane).toBe("market");
    expect(modelLane.className).toContain("model");
    expect(marketLane.className).toContain("market");

    expect(within(modelLane).getByText("ENGINE_A")).toBeTruthy();
    expect(within(modelLane).getByText("PROSPECT_D")).toBeTruthy();
    expect(within(modelLane).getByText("85.14")).toBeTruthy();
    expect(within(modelLane).getByText("10.31")).toBeTruthy();
    expect(within(modelLane).getByText("91%")).toBeTruthy();
    expect(within(modelLane).getByText("6.1")).toBeTruthy();
    expect(within(modelLane).getByText("9.8")).toBeTruthy();
    expect(within(modelLane).getByText("12.4")).toBeTruthy();
    expect(within(modelLane).queryByText("4371")).toBeNull();

    expect(within(marketLane).getByText("FantasyCalc")).toBeTruthy();
    expect(within(marketLane).getByText("4371")).toBeTruthy();
    expect(within(marketLane).getByText("Overall 42")).toBeTruthy();
    expect(within(marketLane).getByText("Position 8")).toBeTruthy();
    expect(within(marketLane).getByText("2026-05-24T17:19:52Z")).toBeTruthy();
    expect(within(marketLane).getByText("market_overlay_static_caveat")).toBeTruthy();
    expect(within(marketLane).queryByText("85.14")).toBeNull();

    const divergence = within(card).getByTestId("player-divergence");
    expect(divergence.className).toContain("neutral");
    expect(divergence.className).not.toMatch(/model|market|blue|amber|green|red/i);
    expect(within(divergence).getByText("Model lower than market")).toBeTruthy();
    expect(within(divergence).queryByText("-0.237")).toBeNull();
  });

  it("renders the full evidence body without truncation or verdict language", async () => {
    const fullCounter =
      "Premium valuation assumes continued high-level rushing or outlier passing efficiency " +
      "while the supporting cast and role remain stable across the first contract.";
    mockPlayerDetail(modeledDetail());

    renderPage();

    const evidence = await screen.findByRole("region", { name: /evidence/i });
    expect(within(evidence).getByText(fullCounter)).toBeTruthy();
    expect(within(evidence).getByText("Round 1 draft capital")).toBeTruthy();
    expect(within(evidence).getByText("age-adjusted production")).toBeTruthy();
    expect(within(evidence).getByText("projection variance elevated")).toBeTruthy();
    expect(within(evidence).getByText("FantasyCalc snapshot is static")).toBeTruthy();

    const ageCliff = within(evidence).getByText("RB age cliff approaching");
    expect(ageCliff.className).toMatch(/age|cliff|amber/i);

    expect(
      within(evidence).queryByText(/Premium valuation assumes continued.*…/i),
    ).toBeNull();
    expect(
      screen.queryByText(/buy|sell|favors|recommended|recommendation/i),
    ).toBeNull();
    expect(document.body.textContent).not.toMatch(/\bwin\b|\bloss\b/i);
    expect(document.querySelector(".green, .red, .verdict")).toBeNull();
  });

  it("renders explicit Experimental degradation when the player has no active model score", async () => {
    mockPlayerDetail(unmodeledDetail());

    renderPage();

    const card = await screen.findByRole("article", {
      name: /player detail for chase/i,
    });
    expect(within(card).getByText("Experimental")).toBeTruthy();
    expect(within(card).getByText("No active model score")).toBeTruthy();
    expect(
      within(card).getByText("No active model score for this player category."),
    ).toBeTruthy();
    expect(within(card).getByTestId("player-model-lane")).toBeTruthy();
    expect(within(card).getByText("Model unavailable")).toBeTruthy();
    expect(within(card).getByTestId("player-market-lane")).toBeTruthy();
    expect(within(card).getByText("Market unavailable")).toBeTruthy();
    expect(within(card).getByText("Evidence unavailable")).toBeTruthy();
    expect(within(card).queryByText(/evidence incomplete/i)).toBeNull();
  });

  it("degrades missing evidence elements independently without fabricating text", async () => {
    mockPlayerDetail(partialDetail());

    renderPage();

    const evidence = await screen.findByRole("region", { name: /evidence/i });
    expect(within(evidence).getByText("No counter-argument available")).toBeTruthy();
    expect(within(evidence).getByText("Experimental")).toBeTruthy();
    expect(within(evidence).getByText("No top drivers available")).toBeTruthy();
    expect(within(evidence).getByText("No caveats available")).toBeTruthy();
    expect(within(evidence).getByText("RB age cliff approaching")).toBeTruthy();
    expect(within(evidence).queryByText(/Premium valuation/i)).toBeNull();
    expect(within(evidence).queryByText(/fabricated/i)).toBeNull();

    const marketLane = screen.getByTestId("player-market-lane");
    expect(within(marketLane).getByText("Market unavailable")).toBeTruthy();
    expect(screen.getByTestId("player-divergence").className).toContain("neutral");
    expect(
      within(screen.getByTestId("player-divergence")).getByText("Inside band"),
    ).toBeTruthy();
  });
});
