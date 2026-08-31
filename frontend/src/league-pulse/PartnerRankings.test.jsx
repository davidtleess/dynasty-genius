// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { PartnerRankings } from "./PartnerRankings";

// THE ALLOWLIST TESTS. DG-119 rebuilt this panel's presentation — card frames,
// a rank word instead of a bare 2.091, one caveat for the section instead of
// eleven stamps — and the readability of that rebuild is covered in
// PartnerRankingsReadable.test.jsx. What is covered HERE is the part that did
// not change and must not: the strict per-field allowlists that keep nested
// evidence and stray score components off the surface, and the fact that every
// value the panel does show is said in words rather than in producer tokens.

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
      activity_recency_score: 0.0,
      posture_alignment_score: 0.25,
      ignored_score_component: 0.99,
    },
  };
  return leaguePulseResponse({ partner_rankings: [ranking] });
}

describe("PartnerRankings", () => {
  it("renders the allowlisted score, evidence and position fields and nothing else", () => {
    render(<PartnerRankings rankings={partnerRankingResponse().partner_rankings} />);

    const section = screen.getByRole("region", { name: /who to call/i });
    expect(within(section).getByRole("heading", { name: /who to call/i })).toBeTruthy();
    expect(
      within(section).getByText(
        /partly market-derived, so it is context rather than a proven edge/i,
      ),
    ).toBeTruthy();

    const card = within(section).getByText("Market Context FC").closest("article");
    expect(card).toBeTruthy();
    const row = within(card);

    // The four allowlisted components, each still named by the dictionary.
    for (const component of [
      "How well the rosters fit",
      "How often we disagree on price",
      // NOT "How recently they've traded" — the part is the literal 0.0 on
      // league_opportunity_map.py:185, so a term naming a measured recency is
      // the same false frame the value was retired for.
      "Trade activity",
      "Whether you're pointed opposite ways",
    ]) {
      expect(row.getByText(component)).toBeTruthy();
    }

    // Both postures and the divergence count still reach the reader — as the
    // sentence that says who to call and why, rather than as labelled pairs.
    expect(
      row.getByText(
        /You're contending and they're rebuilding\. They're deep at RB and WR — exactly where you're thin\. We and the market price 4 of their players differently\./,
      ),
    ).toBeTruthy();

    // The raw producer vocabulary never reaches a reader outside the receipt.
    expect(row.queryByText(/CONTENDER/)).toBeNull();
    expect(row.queryByText(/perspective_posture/i)).toBeNull();
    expect(row.queryByText("partner_score_market_influenced")).toBeNull();

    // Allowlists: a stray score component, a nested evidence key and a position
    // outside QB/RB/WR/TE are all dropped.
    expect(row.queryByText(/ignored_score_component/i)).toBeNull();
    expect(row.queryByText(/ignored_nested_key/i)).toBeNull();
    expect(row.queryByText(/must not render/i)).toBeNull();
    expect(row.queryByText(/DL 0\.99/)).toBeNull();
    expect(row.getByText(/QB 0\.12, RB 0\.81, WR 0\.34, TE 0\.25/)).toBeTruthy();
  });

  it("renders a section-level empty state without hiding the surface", () => {
    render(<PartnerRankings rankings={[]} />);

    const section = screen.getByRole("region", { name: /who to call/i });
    expect(
      within(section).getByText(/no partner ranking context available/i),
    ).toBeTruthy();
  });

  it("says nothing about a caveat when the producer emitted none", () => {
    // Absence renders nothing (spec §6 rule 6). An empty caveat list produces
    // no element at all — not an "everything checks out" line, which would be a
    // claim the producer never made.
    const base = partnerRankingResponse().partner_rankings[0];
    render(<PartnerRankings rankings={[{ ...base, caveats: [] }]} />);

    expect(screen.queryByText(/market-derived/i)).toBeNull();
  });

  it("keeps a caveat that is true of only one partner on that partner's card", () => {
    const base = partnerRankingResponse().partner_rankings[0];
    render(
      <PartnerRankings
        rankings={[
          { ...base, counterparty_roster_id: 8, counterparty_team_name: "Both" },
          {
            ...base,
            counterparty_roster_id: 9,
            counterparty_team_name: "Only This One",
            caveats: ["partner_score_market_influenced", "posture_unclassified"],
          },
        ]}
      />,
    );

    // The shared token is hoisted once; the one-off stays where it is true.
    expect(
      screen.getAllByText(/partly market-derived, so it is context/i),
    ).toHaveLength(1);
    const unique = screen.getByText(/does not have enough signal for a posture\./i);
    expect(unique.closest("article")).toBe(
      screen.getByText("Only This One").closest("article"),
    );
  });
});
