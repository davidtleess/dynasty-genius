// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { PartnerRankings } from "./PartnerRankings";

function partnerRankingResponse() {
  const base = leaguePulseResponse();
  const ranking = {
    ...base.partner_rankings[0],
    counterparty_roster_id: 8,
    counterparty_team_name: "Market Context FC",
    caveats: ["partner_score_market_influenced"],
    evidence: {
      perspective_posture: "CONTENDER",
      counterparty_posture: "REBUILDING",
      divergence_row_count: 4,
      ignored_nested_key: "must not render",
      position_scores: {
        QB: 0.12,
        RB: 0.81,
        WR: 0.34,
        TE: 0.25,
        DL: 0.99,
      },
    },
    market_influenced: true,
    matched_positions: ["RB", "WR"],
    partner_score: 0.742,
    score_components: {
      complementarity_score: 0.8,
      divergence_density_score: 0.5,
      activity_recency_score: 0.2,
      posture_alignment_score: 0.6,
      ignored_score_component: 0.99,
    },
  };
  return leaguePulseResponse({ partner_rankings: [ranking] });
}

describe("PartnerRankings", () => {
  it("renders partner rankings as market-influenced context with the allowlisted score and evidence fields", () => {
    render(<PartnerRankings rankings={partnerRankingResponse().partner_rankings} />);

    const section = screen.getByRole("region", {
      name: /partner rankings/i,
    });

    expect(
      within(section).getByRole("heading", { name: /partner rankings/i }),
    ).toBeTruthy();
    expect(within(section).getByText(/market-influenced context/i)).toBeTruthy();
    expect(within(section).getByText(/not a validated ranking/i)).toBeTruthy();

    const card = within(section).getByText("Market Context FC").closest("article");
    expect(card).toBeTruthy();
    const row = within(card);

    expect(row.getByText(/roster 8/i)).toBeTruthy();
    // Exact match: must be an explicit partner_score label, not the caveat token.
    expect(row.getByText("partner_score")).toBeTruthy();
    expect(row.getByText(/0\.742/)).toBeTruthy();
    expect(row.getByText(/RB, WR/)).toBeTruthy();
    expect(row.getByText(/market-influenced/i)).toBeTruthy();
    expect(row.getByText("partner_score_market_influenced")).toBeTruthy();

    for (const component of [
      "complementarity_score",
      "divergence_density_score",
      "activity_recency_score",
      "posture_alignment_score",
    ]) {
      expect(row.getByText(component)).toBeTruthy();
    }

    expect(row.getByText(/perspective_posture/i)).toBeTruthy();
    expect(row.getByText(/CONTENDER/)).toBeTruthy();
    expect(row.getByText(/counterparty_posture/i)).toBeTruthy();
    expect(row.getByText(/REBUILDING/)).toBeTruthy();
    expect(row.getByText(/divergence_row_count/i)).toBeTruthy();
    expect(row.getByText("4")).toBeTruthy();

    for (const [position, value] of [
      ["QB", "0.12"],
      ["RB", "0.81"],
      ["WR", "0.34"],
      ["TE", "0.25"],
    ]) {
      expect(row.getByText(new RegExp(`${position}\\s+${value}`))).toBeTruthy();
    }

    expect(row.queryByText(/ignored_score_component/i)).toBeNull();
    expect(row.queryByText(/ignored_nested_key/i)).toBeNull();
    expect(row.queryByText(/must not render/i)).toBeNull();
    expect(row.queryByText(/DL\s+0\.99/)).toBeNull();
  });

  it("renders a section-level empty state without hiding the surface", () => {
    render(<PartnerRankings rankings={[]} />);

    const section = screen.getByRole("region", {
      name: /partner rankings/i,
    });
    expect(
      within(section).getByText(/no partner ranking context available/i),
    ).toBeTruthy();
  });
});
