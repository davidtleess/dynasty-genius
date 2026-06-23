// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { TeamValueOverview } from "./TeamValueOverview";

function valueRows() {
  const base = leaguePulseResponse().team_values[0];
  return [
    {
      ...base,
      roster_id: 9,
      team_name: "Roster Nine",
      age_profile: {
        value_weighted_age: 25.4,
        median_age: 25,
        pct_value_over_28: 0.22,
        ignored_age_key: 99,
      },
      future_picks: {
        owned_count: 7,
        outgoing_count: 1,
        pick_value_status: "unvalued",
        ignored_pick_key: "hide me",
      },
      positional_summary: {
        QB: { z_score: 0.4, surplus_label: "balanced", ignored: "hide me" },
        RB: { z_score: -0.3, surplus_label: "deficit" },
        WR: { z_score: 0.8, surplus_label: "surplus" },
        TE: { z_score: 0.1, surplus_label: "balanced" },
        DL: { z_score: 9.9, surplus_label: "ignore" },
      },
      value_views: {
        starter_weighted_xvar: 8.4,
        lineup_xvar: 7.9,
        depth_credit_xvar: 1.2,
        total_xvar_capped: 9.1,
        top_n_xvar: 8.6,
        ignored_value_view: 99,
        decision_supported: false,
      },
      players: [{ full_name: "Hidden Player" }],
    },
  ];
}

describe("TeamValueOverview", () => {
  it("renders team value context with exact allowlists and no raw player list", () => {
    render(<TeamValueOverview values={valueRows()} />);

    const section = screen.getByRole("region", { name: /team value overview/i });
    expect(
      within(section).getByRole("heading", { name: /team value overview/i }),
    ).toBeTruthy();

    const row = within(section).getByText("Roster Nine").closest("article");
    expect(row).toBeTruthy();
    const card = within(row);

    expect(card.getByText(/roster 9/i)).toBeTruthy();

    for (const valueView of [
      "starter_weighted_xvar",
      "lineup_xvar",
      "depth_credit_xvar",
      "total_xvar_capped",
      "top_n_xvar",
    ]) {
      expect(card.getByText(valueView)).toBeTruthy();
    }

    for (const ageField of ["value_weighted_age", "median_age", "pct_value_over_28"]) {
      expect(card.getByText(ageField)).toBeTruthy();
    }

    for (const pickField of ["owned_count", "outgoing_count", "pick_value_status"]) {
      expect(card.getByText(pickField)).toBeTruthy();
    }

    for (const position of ["QB", "RB", "WR", "TE"]) {
      expect(card.getByText(new RegExp(`${position}\\s+z_score`, "i"))).toBeTruthy();
    }
    expect(card.getByText(/QB\s+z_score\s+0\.40\s+balanced/i)).toBeTruthy();
    expect(card.getByText(/RB\s+z_score\s+-0\.30\s+deficit/i)).toBeTruthy();

    expect(card.queryByText(/ignored_value_view/i)).toBeNull();
    expect(card.queryByText(/ignored_age_key/i)).toBeNull();
    expect(card.queryByText(/ignored_pick_key/i)).toBeNull();
    expect(card.queryByText(/hide me/i)).toBeNull();
    expect(card.queryByText(/DL\s+z_score/i)).toBeNull();
    expect(card.queryByText(/Hidden Player/i)).toBeNull();
  });

  it("renders a section-level empty state", () => {
    render(<TeamValueOverview values={[]} />);

    const section = screen.getByRole("region", { name: /team value overview/i });
    expect(within(section).getByText(/no team value context available/i)).toBeTruthy();
  });
});
