// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { OpportunityCards } from "./OpportunityCards";

function cardsResponse() {
  const base = leaguePulseResponse();
  const modelCard = {
    ...base.model_native_cards[0],
    card_id: "model-roster-fit",
    card_type: "ROSTER_SURPLUS_DEFICIT_MATCH",
    caveats: ["counterparty_fit"],
    evidence: {
      position: "RB",
      perspective_position_z: -0.71,
      counterparty_position_z: 0.92,
      perspective_surplus_label: "deficit",
      counterparty_surplus_label: "surplus",
      market_percentile: 99,
      model_minus_market_delta: 9.9,
      ignored_model_evidence: "hide me",
    },
    opportunity_score: 0.612,
    rationale_primary: "opportunity_signal",
    rationale_secondary: ["counterparty_fit"],
    score_components: {
      fit_score: 0.8,
      feasibility_score: 0.6,
      divergence_score: 0.99,
      ignored_model_score: 0.11,
    },
  };
  const marketCard = {
    ...base.market_overlay_cards[0],
    card_id: "market-divergence",
    card_type: "DIVERGENCE_MODEL_HIGH",
    caveats: ["market_overlay_unvalidated_divergence"],
    evidence: {
      signal: "MODEL_HIGH_MARKET_LOW",
      signal_status: "active",
      model_minus_market_delta: 0.18,
      market_percentile: 42,
      model_percentile: 71,
      xvar: 1.4,
      raw_xvar: 1.6,
      lineup_role: "bench",
      asset_roster_id: 4,
      ignored_overlay_evidence: "hide me",
    },
    opportunity_score: 0.524,
    rationale_primary: "opportunity_signal",
    rationale_secondary: ["market_overlay_context_only"],
    recommended_drop: {
      sleeper_player_id: "drop-1",
      full_name: "Depth WR",
      position: "WR",
      cut_priority: 2,
      ir_compliance_status: "not_ir_eligible",
      cut_rationale: ["opportunity_signal"],
      decision_supported: false,
    },
    score_components: {
      fit_score: 0.4,
      divergence_score: 0.7,
      feasibility_score: 0.5,
      ignored_overlay_score: 0.13,
    },
  };
  return leaguePulseResponse({
    market_overlay_cards: [marketCard],
    model_native_cards: [modelCard],
  });
}

describe("OpportunityCards", () => {
  it("renders model-native cards separately with exact evidence and score allowlists", () => {
    render(
      <OpportunityCards
        marketOverlayCards={cardsResponse().market_overlay_cards}
        modelNativeCards={cardsResponse().model_native_cards}
      />,
    );

    const section = screen.getByRole("region", {
      name: /model-native opportunity cards/i,
    });
    expect(
      within(section).getByRole("heading", {
        name: /model-native opportunity cards/i,
      }),
    ).toBeTruthy();

    const card = within(section)
      .getByText("ROSTER_SURPLUS_DEFICIT_MATCH")
      .closest("article");
    expect(card).toBeTruthy();
    const row = within(card);

    expect(row.getByText(/opportunity_score/i)).toBeTruthy();
    expect(row.getByText(/0\.612/)).toBeTruthy();
    expect(row.getByText("opportunity_signal")).toBeTruthy();
    expect(row.getByText("counterparty_fit")).toBeTruthy();

    for (const evidenceField of [
      "position",
      "perspective_position_z",
      "counterparty_position_z",
      "perspective_surplus_label",
      "counterparty_surplus_label",
    ]) {
      expect(row.getByText(evidenceField)).toBeTruthy();
    }

    for (const scoreField of ["fit_score", "feasibility_score"]) {
      expect(row.getByText(scoreField)).toBeTruthy();
    }

    expect(row.queryByText(/market_percentile/i)).toBeNull();
    expect(row.queryByText(/model_minus_market_delta/i)).toBeNull();
    expect(row.queryByText(/ignored_model_evidence/i)).toBeNull();
    expect(row.queryByText(/ignored_model_score/i)).toBeNull();
    expect(row.queryByText(/divergence_score/i)).toBeNull();
    expect(row.queryByText(/9\.9/)).toBeNull();
    expect(row.queryByText(/hide me/i)).toBeNull();
  });

  it("renders market overlay cards separately with persistent caveat banner and recommended drops", () => {
    render(
      <OpportunityCards
        marketOverlayCards={cardsResponse().market_overlay_cards}
        modelNativeCards={cardsResponse().model_native_cards}
      />,
    );

    const section = screen.getByRole("region", {
      name: /market overlay opportunity cards/i,
    });
    expect(
      within(section).getByText(/descriptive market signal, not a validated edge/i),
    ).toBeTruthy();

    const card = within(section).getByText("DIVERGENCE_MODEL_HIGH").closest("article");
    expect(card).toBeTruthy();
    const row = within(card);

    expect(row.getByText(/opportunity_score/i)).toBeTruthy();
    expect(row.getByText(/0\.524/)).toBeTruthy();
    expect(row.getByText("market_overlay_unvalidated_divergence")).toBeTruthy();

    for (const evidenceField of [
      "signal",
      "signal_status",
      "model_minus_market_delta",
      "market_percentile",
      "model_percentile",
      "xvar",
      "raw_xvar",
      "lineup_role",
      "asset_roster_id",
    ]) {
      expect(row.getByText(evidenceField)).toBeTruthy();
    }

    for (const scoreField of ["fit_score", "divergence_score", "feasibility_score"]) {
      expect(row.getByText(scoreField)).toBeTruthy();
    }

    expect(row.getByText(/recommended_drop/i)).toBeTruthy();
    expect(row.getByText("Depth WR")).toBeTruthy();
    expect(row.getByText("WR")).toBeTruthy();
    expect(row.getByText(/cut_priority/i)).toBeTruthy();
    expect(row.getByText("2")).toBeTruthy();
    expect(row.getByText("not_ir_eligible")).toBeTruthy();
    expect(row.getAllByText("opportunity_signal").length).toBeGreaterThan(0);

    expect(row.queryByText(/ignored_overlay_evidence/i)).toBeNull();
    expect(row.queryByText(/ignored_overlay_score/i)).toBeNull();
    expect(row.queryByText(/hide me/i)).toBeNull();
  });

  it("renders lane-level empty states without collapsing either section", () => {
    render(<OpportunityCards marketOverlayCards={[]} modelNativeCards={[]} />);

    const modelSection = screen.getByRole("region", {
      name: /model-native opportunity cards/i,
    });
    const overlaySection = screen.getByRole("region", {
      name: /market overlay opportunity cards/i,
    });

    expect(
      within(modelSection).getByText(/no model-native opportunity cards available/i),
    ).toBeTruthy();
    expect(
      within(overlaySection).getByText(
        /no market overlay opportunity cards available/i,
      ),
    ).toBeTruthy();
    expect(
      within(overlaySection).getByText(
        /descriptive market signal, not a validated edge/i,
      ),
    ).toBeTruthy();
  });
});
