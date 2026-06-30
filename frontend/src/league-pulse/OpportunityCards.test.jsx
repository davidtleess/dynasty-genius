// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { OpportunityCards } from "./OpportunityCards";

function renderCards(response = leaguePulseResponse()) {
  return render(
    <OpportunityCards
      cardSectionCounts={response.card_section_counts}
      marketOverlayCards={response.market_overlay_cards}
      modelNativeCards={response.model_native_cards}
    />,
  );
}

function articleFor(text) {
  const article = screen.getByText(text).closest("article");
  expect(article).toBeTruthy();
  return article;
}

function responseForRenderContract() {
  const base = leaguePulseResponse();
  const modelCard = {
    ...base.model_native_cards[0],
    card_id: "model-positional-z",
    evidence: {
      ...base.model_native_cards[0].evidence,
      ignored_model_evidence: "hide me",
      market_percentile: 99,
      model_minus_market_delta: 9.9,
    },
    score_components: {
      ...base.model_native_cards[0].score_components,
      divergence_score: 0.99,
      ignored_model_score: 0.11,
    },
    sort_key: "positional_z_differential_desc",
    sort_value: 1.6,
  };
  const marketCard = {
    ...base.market_overlay_cards[0],
    card_id: "market-delta",
    evidence: {
      ...base.market_overlay_cards[0].evidence,
      ignored_overlay_evidence: "hide me",
      model_minus_market_delta: 0.72,
    },
    score_components: {
      ...base.market_overlay_cards[0].score_components,
      ignored_overlay_score: 0.13,
    },
    sort_key: "absolute_model_market_delta_desc",
    sort_value: 0.72,
  };
  return leaguePulseResponse({
    card_section_counts: [
      {
        decision_supported: false,
        section_cap: 20,
        shown_count: 1,
        sort_key: "absolute_model_market_delta_desc",
        total_count: 7,
      },
      {
        decision_supported: false,
        section_cap: 20,
        shown_count: 1,
        sort_key: "positional_z_differential_desc",
        total_count: 3,
      },
    ],
    market_overlay_cards: [marketCard],
    model_native_cards: [modelCard],
  });
}

function capacityCandidate(overrides = {}) {
  return {
    capacity_conflict_status: "roster_capacity_pressure",
    caveats: [],
    decision_supported: false,
    dvs: -0.7,
    full_name: "Capacity Row",
    position: "WR",
    sleeper_player_id: "candidate-1",
    value_status: "valued",
    xvar_pct: 0.11,
    ...overrides,
  };
}

function capacityPool(items, overrides = {}) {
  return {
    caveats: [],
    decision_supported: false,
    items,
    narrowing_rule: "all_safe_candidates",
    pool_status: "available",
    selection_rule: "descriptive_candidate_pool_no_tool_selection",
    sort_key: "xvar_pct_ascending_then_full_name_then_sleeper_player_id",
    ...overrides,
  };
}

describe("OpportunityCards T4b render contract", () => {
  it("renders lane-separated sort-key sections with count headers and inline sort labels", () => {
    renderCards(responseForRenderContract());

    const modelLane = screen.getByRole("region", {
      name: /model-native opportunity cards/i,
    });
    const marketLane = screen.getByRole("region", {
      name: /market overlay opportunity cards/i,
    });

    expect(within(modelLane).getByText("Positional Imbalances")).toBeTruthy();
    expect(
      within(modelLane).getByText("Showing 1 of 3 matches in this category"),
    ).toBeTruthy();
    expect(
      within(modelLane).getByText(/Sort metric:\s*Positional z differential\s*1\.60/i),
    ).toBeTruthy();

    expect(within(marketLane).getByText("Market Divergences")).toBeTruthy();
    expect(
      within(marketLane).getByText("Showing 1 of 7 matches in this category"),
    ).toBeTruthy();
    expect(
      within(marketLane).getByText(
        /Sort metric:\s*Market divergence magnitude\s*0\.72/i,
      ),
    ).toBeTruthy();
    expect(
      screen.getAllByText(
        "A larger value reflects a wider mathematical magnitude, not a prioritized transaction order.",
      ).length,
    ).toBeGreaterThan(0);

    expect(screen.queryByText(/opportunity_score/i)).toBeNull();
    expect(document.querySelector(".dg-league-pulse__score-badge")).toBeNull();
    expect(within(modelLane).queryByText(/market_percentile/i)).toBeNull();
    expect(within(modelLane).queryByText(/model_minus_market_delta/i)).toBeNull();
    expect(within(modelLane).queryByText(/9\.9/)).toBeNull();
    expect(within(modelLane).queryByText(/hide me/i)).toBeNull();
    expect(within(marketLane).queryByText(/ignored_overlay_evidence/i)).toBeNull();
    expect(within(marketLane).queryByText(/ignored_overlay_score/i)).toBeNull();
  });

  it("renders evidence status as neutral slate copy without green red or warning classes", () => {
    renderCards(responseForRenderContract());

    const card = articleFor("ROSTER_SURPLUS_DEFICIT_MATCH");
    const status = within(card).getByText(/Evidence status:\s*Evidence complete/i);

    expect(status.className).toContain("dg-league-pulse__evidence-status");
    expect(status.className).toContain("dg-league-pulse__evidence-status--neutral");
    expect(status.className).not.toMatch(
      /green|red|warn|positive|negative|success|danger/i,
    );
  });

  it("renders roster capacity only for unrostered market divergence without a selected row", () => {
    const base = leaguePulseResponse();
    const noPressureCard = {
      ...base.market_overlay_cards[0],
      card_id: "market-no-pressure",
      evidence: {
        ...base.market_overlay_cards[0].evidence,
        model_minus_market_delta: 0.34,
      },
      rationale_primary: "no_capacity_pressure_context",
      roster_capacity_candidates: null,
      sort_value: 0.34,
    };
    const neutralCapacityCard = {
      ...base.market_overlay_cards[0],
      card_id: "market-neutral-capacity",
      evidence: {
        ...base.market_overlay_cards[0].evidence,
        model_minus_market_delta: 0.52,
      },
      rationale_primary: "neutral_capacity_context",
      roster_capacity_candidates: capacityPool([
        capacityCandidate({
          full_name: "Qualitative Eval WR",
          value_status: "unvalued",
          xvar_pct: null,
        }),
        capacityCandidate({
          full_name: "Capacity Bench WR",
          sleeper_player_id: "candidate-2",
        }),
      ]),
      sort_value: 0.52,
    };
    const blockerCapacityCard = {
      ...base.market_overlay_cards[0],
      card_id: "market-hard-conflict",
      evidence: {
        ...base.market_overlay_cards[0].evidence,
        model_minus_market_delta: 0.61,
      },
      rationale_primary: "hard_conflict_capacity_context",
      roster_capacity_candidates: capacityPool([
        capacityCandidate({
          capacity_conflict_status: "hard_roster_rules_conflict",
          full_name: "IR Lock WR",
          rule_conflict_label: "IR compliance violation",
          sleeper_player_id: "candidate-3",
        }),
      ]),
      sort_value: 0.61,
    };
    const taxiCard = {
      ...base.market_overlay_cards[0],
      card_id: "taxi-card",
      card_type: "TAXI_LONG_TERM_VALUE_PRESENT",
      rationale_primary: "taxi_long_term_context",
      roster_capacity_candidates: capacityPool([
        capacityCandidate({
          full_name: "Taxi Hidden WR",
          sleeper_player_id: "candidate-4",
        }),
      ]),
      sort_key: "taxi_long_term_value_desc",
      sort_value: 1.05,
    };

    renderCards(
      leaguePulseResponse({
        card_section_counts: [
          {
            decision_supported: false,
            section_cap: 20,
            shown_count: 3,
            sort_key: "absolute_model_market_delta_desc",
            total_count: 3,
          },
          {
            decision_supported: false,
            section_cap: 20,
            shown_count: 1,
            sort_key: "taxi_long_term_value_desc",
            total_count: 1,
          },
        ],
        market_overlay_cards: [
          noPressureCard,
          neutralCapacityCard,
          blockerCapacityCard,
          taxiCard,
        ],
        model_native_cards: [],
      }),
    );

    const noPressureArticle = articleFor("no_capacity_pressure_context");
    expect(within(noPressureArticle).queryByText(/Roster capacity/i)).toBeNull();

    const neutralArticle = articleFor("neutral_capacity_context");
    const neutralCapacity = within(neutralArticle).getByTestId(
      "roster-capacity-candidates",
    );
    expect(neutralCapacity.className).toContain("dg-league-pulse__capacity--neutral");
    expect(neutralCapacity.className).not.toContain(
      "dg-league-pulse__capacity--blocker",
    );
    expect(
      within(neutralCapacity).getByText(
        "Valuation Unavailable - evaluate qualitatively",
      ),
    ).toBeTruthy();
    expect(
      neutralCapacity.querySelector(".dg-league-pulse__capacity-row--selected"),
    ).toBeNull();
    for (const input of neutralCapacity.querySelectorAll(
      'input[type="checkbox"], input[type="radio"]',
    )) {
      expect(input.checked).toBe(false);
    }

    const blockerArticle = articleFor("hard_conflict_capacity_context");
    const blockerCapacity = within(blockerArticle).getByTestId(
      "roster-capacity-candidates",
    );
    expect(blockerCapacity.className).toContain("dg-league-pulse__capacity--blocker");
    expect(
      within(blockerCapacity).getByText("IR-conflict non-dismissible blocker"),
    ).toBeTruthy();

    const taxiArticle = articleFor("taxi_long_term_context");
    expect(within(taxiArticle).getByText("Taxi Squad")).toBeTruthy();
    expect(within(taxiArticle).queryByText("Taxi Hidden WR")).toBeNull();
  });
});
