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
    frozen_prediction: {
      basis: "model_supported_prediction_captured",
      coverage: {
        current_rostered_skill_in_frozen_prediction_cohort_count: 221,
        current_rostered_skill_not_in_frozen_prediction_cohort_count: 53,
        current_rostered_skill_player_count: 274,
      },
      decision_supported: false,
      frozen_capture_date: "2026-08-05",
      message: "A model prediction was frozen for 2026 outcome evaluation.",
      season: 2026,
      status: "included",
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
      xvar_percentile_position: 91.0,
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
    // DG-111: the card's opening stamp is retired. The model's standing is now
    // said once, in plain words, at the FOOT of the card — after the numbers it
    // qualifies, not shouted before them.
    expect(
      within(card).queryByText("Descriptive only — not decision-grade."),
    ).toBeNull();
    expect(within(card).getByTestId("model-standing")).toBeTruthy();
    expect(within(card).queryByRole("button", { name: /dismiss/i })).toBeNull();

    const modelLane = within(card).getByTestId("player-model-lane");
    const marketLane = within(card).getByTestId("player-market-lane");
    expect(modelLane.dataset.lane).toBe("model");
    expect(marketLane.dataset.lane).toBe("market");
    expect(modelLane.className).toContain("model");
    expect(marketLane.className).toContain("market");

    // DG-109: both model facts survive — in words, not as ENGINE_A / PROSPECT_D.
    expect(
      within(modelLane).getByText("Rookie model — draft capital and age"),
    ).toBeTruthy();
    expect(
      within(modelLane).getByText(
        "Scored by the rookie model — accuracy grade D, its weakest",
      ),
    ).toBeTruthy();
    expect(within(modelLane).queryByText("ENGINE_A")).toBeNull();
    expect(within(modelLane).getByText("85.14")).toBeTruthy();
    expect(within(modelLane).getByText("10.31")).toBeTruthy();
    expect(within(modelLane).getByText("91%")).toBeTruthy();
    expect(within(modelLane).getByText("6.1")).toBeTruthy();
    expect(within(modelLane).getByText("9.8")).toBeTruthy();
    expect(within(modelLane).getByText("12.4")).toBeTruthy();
    expect(within(modelLane).queryByText("4371")).toBeNull();

    expect(within(marketLane).getByText("FantasyCalc")).toBeTruthy();
    expect(within(marketLane).getByText("4371")).toBeTruthy();
    // DG-043: ranks, dates, and caveats speak plain language as labeled pairs —
    // no raw pipeline keys, no raw ISO timestamps (2026-08-29 prose ruling).
    expect(within(marketLane).getByText("Overall rank")).toBeTruthy();
    expect(within(marketLane).getByText("42")).toBeTruthy();
    expect(within(marketLane).getByText("Position rank")).toBeTruthy();
    expect(within(marketLane).getByText("8")).toBeTruthy();
    expect(within(marketLane).getByText("May 24, 2026")).toBeTruthy();
    expect(within(marketLane).queryByText("2026-05-24T17:19:52Z")).toBeNull();
    expect(within(marketLane).queryByText("market_overlay_static_caveat")).toBeNull();
    expect(
      within(marketLane).getByText(
        "Market values come from a saved FantasyCalc snapshot, not a live feed.",
      ),
    ).toBeTruthy();
    expect(within(marketLane).queryByText("85.14")).toBeNull();

    const divergence = within(card).getByTestId("player-divergence");
    expect(divergence.className).toContain("neutral");
    expect(divergence.className).not.toMatch(/model|market|blue|amber|green|red/i);
    expect(
      within(divergence).getByText("The market prices him higher than we do"),
    ).toBeTruthy();
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

  // DG-111: the "Experimental" badge over the bare phrase "No active model
  // score" is retired. The FACT is unchanged and is now a sentence — see the
  // "DG-111 the unscored player still says so, in prose" block below for the
  // full wording contract. The producer's own reason still renders verbatim.
  it("states the unscored player's degradation in prose, keeping the producer's reason", async () => {
    mockPlayerDetail(unmodeledDetail());

    renderPage();

    const card = await screen.findByRole("article", {
      name: /player detail for chase/i,
    });
    expect(within(card).queryByText("Experimental")).toBeNull();
    expect(within(card).getByTestId("player-unscored").textContent).toMatch(
      /Not scored yet/i,
    );
    expect(
      within(card).getByText("No active model score for this player category."),
    ).toBeTruthy();
    expect(within(card).getByTestId("player-model-lane")).toBeTruthy();
    expect(within(card).getByText("Model unavailable")).toBeTruthy();
    expect(within(card).getByTestId("player-market-lane")).toBeTruthy();
    expect(within(card).getByText("Market unavailable")).toBeTruthy();
    // DG-109: absence renders NOTHING. A null evidence block asserted nothing
    // about the player, so the section disappears rather than announcing an
    // empty region. The model/market lanes still say they are unavailable —
    // those ARE facts about data we expected and do not have.
    expect(within(card).queryByRole("region", { name: /evidence/i })).toBeNull();
    expect(within(card).queryByText("Evidence unavailable")).toBeNull();
    expect(within(card).queryByText(/evidence incomplete/i)).toBeNull();
  });

  it("keeps current model status separate from frozen evaluation membership", async () => {
    mockPlayerDetail(
      modeledDetail({
        frozen_prediction: {
          basis: "non_model_route_at_freeze",
          coverage: {
            current_rostered_skill_in_frozen_prediction_cohort_count: 221,
            current_rostered_skill_not_in_frozen_prediction_cohort_count: 53,
            current_rostered_skill_player_count: 274,
          },
          decision_supported: false,
          frozen_capture_date: "2026-08-05",
          message: "No model prediction was frozen for 2026 outcome evaluation.",
          season: 2026,
          status: "not_in_frozen_prediction_cohort",
        },
      }),
    );

    renderPage();

    const card = await screen.findByRole("article", {
      name: /player detail for chase/i,
    });
    expect(within(card).getByTestId("player-model-lane")).toBeTruthy();
    expect(within(card).getByText("Not in 2026 model snapshot")).toBeTruthy();
    expect(
      within(card).getByText(
        "No model prediction was frozen for 2026 outcome evaluation.",
      ),
    ).toBeTruthy();
    expect(
      within(card).getByText(
        "221 of 274 current rostered skill players were included.",
      ),
    ).toBeTruthy();
    // The card's full section is THE "<season> model evaluation" landmark —
    // exactly one on the page (the inspector's compact preview must not mint
    // a duplicate; axe landmark-unique, measured 2026-08-25).
    expect(
      within(card).getByRole("region", { name: "2026 model evaluation" }),
    ).toBeTruthy();
  });

  it("can show a frozen prediction for a player who is unmodeled now", async () => {
    mockPlayerDetail(unmodeledDetail());

    renderPage();

    const card = await screen.findByRole("article", {
      name: /player detail for chase/i,
    });
    expect(within(card).getByTestId("player-unscored")).toBeTruthy();
    expect(within(card).getByText("Included in 2026 model snapshot")).toBeTruthy();
  });

  // DG-111: absence renders nothing. The four "No X available" rows and the
  // "Experimental" badge said nothing about the PLAYER — only about our tables.
  // What is present still renders in full, and nothing is fabricated.
  it("renders only the evidence that exists, without fabricating text or stamping absences", async () => {
    mockPlayerDetail(partialDetail());

    renderPage();

    const evidence = await screen.findByRole("region", { name: /evidence/i });
    // DG-109, David's prose ruling: absence is not content. An unavailable
    // counter-argument, an empty driver list and an empty caveat list each
    // asserted NOTHING about this player, so none of them renders a row.
    expect(within(evidence).queryByText("No counter-argument available")).toBeNull();
    expect(within(evidence).queryByText("No top drivers available")).toBeNull();
    expect(within(evidence).queryByText("No caveats available")).toBeNull();
    expect(within(evidence).queryByText("No risk flags available")).toBeNull();
    // DG-111: the "Experimental" badge that used to fill this section is gone too.
    expect(within(evidence).queryByText("Experimental")).toBeNull();
    // What IS present still speaks, and keeps its constitutional amber.
    expect(within(evidence).getByText("RB age cliff approaching")).toBeTruthy();
    expect(within(evidence).queryByText(/Premium valuation/i)).toBeNull();
    expect(within(evidence).queryByText(/fabricated/i)).toBeNull();

    const marketLane = screen.getByTestId("player-market-lane");
    expect(within(marketLane).getByText("Market unavailable")).toBeTruthy();
    expect(screen.getByTestId("player-divergence").className).toContain("neutral");
    expect(
      within(screen.getByTestId("player-divergence")).getByText(
        "Our price and the market's agree",
      ),
    ).toBeTruthy();
  });
});

// ── DG-111 — the unscored player still says he is unscored, in prose ─────────
// The stamps ("Descriptive only — not decision-grade.", the "Experimental"
// badge, "Decision support only") are retired by David's 2026-08-29 ruling.
// The FACT underneath one of them — this player has no model score — is not.
describe("DG-111 the unscored player still says so, in prose", () => {
  it("says 'not scored yet' in a sentence and keeps the backend's own reason", async () => {
    mockPlayerDetail(unmodeledDetail());

    renderPage();

    const card = await screen.findByRole("article", { name: /player detail for/i });
    const unscored = within(card).getByTestId("player-unscored");
    expect(unscored.textContent).toMatch(/Not scored yet/i);
    expect(unscored.textContent).toMatch(/Chase/);
    expect(unscored.textContent).toMatch(/projection stays blank/i);
    // The producer's own explanation survives verbatim — never swallowed.
    expect(unscored.textContent).toContain(
      "No active model score for this player category.",
    );
    // The furniture is gone.
    expect(within(card).queryByText("Experimental")).toBeNull();
    expect(
      within(card).queryByText("Descriptive only — not decision-grade."),
    ).toBeNull();
  });

  it("says nothing about absent evidence rather than stamping four empty rows", async () => {
    mockPlayerDetail(partialDetail());

    renderPage();

    const evidence = await screen.findByRole("region", { name: /evidence/i });
    expect(within(evidence).queryByText("No counter-argument available")).toBeNull();
    expect(within(evidence).queryByText("No top drivers available")).toBeNull();
    expect(within(evidence).queryByText("No caveats available")).toBeNull();
    expect(within(evidence).queryByText("Experimental")).toBeNull();
    // What IS there still shows.
    expect(within(evidence).getByText("RB age cliff approaching")).toBeTruthy();
  });

  it("never lets an all-empty evidence block read as a clean bill of health", async () => {
    mockPlayerDetail(
      modeledDetail({
        evidence: {
          caveats: { caveats: [], items: [] },
          counter_argument: { caveats: [], status: "experimental", text: null },
          risk_flags: { caveats: [], items: [] },
          top_drivers: { caveats: [], items: [] },
        },
      }),
    );

    renderPage();

    const evidence = await screen.findByRole("region", { name: /evidence/i });
    expect(evidence.textContent).toMatch(/don't have/i);
    expect(evidence.textContent).not.toMatch(/no risk flags/i);
  });

  it("states the model's standing once, in plain words, at the bottom of the card", async () => {
    mockPlayerDetail(modeledDetail());

    renderPage();

    const card = await screen.findByRole("article", { name: /player detail for/i });
    const standing = within(card).getAllByTestId("model-standing");
    expect(standing).toHaveLength(1);
    expect(standing[0].textContent).toMatch(/second opinion/i);
    expect(standing[0].textContent).not.toMatch(/decision-grade/i);
  });
});
