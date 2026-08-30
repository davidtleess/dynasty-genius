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

    // DG-109: the allowlists are unchanged — the same five value views, three
    // age fields and three pick fields render, now under labels in words.
    for (const valueView of [
      "Starter-weighted value",
      "Starting lineup value",
      "Credit for depth",
      "Whole roster, capped",
      "Top-asset core",
    ]) {
      expect(card.getByText(valueView)).toBeTruthy();
    }

    for (const ageField of [
      "Age, weighted by value",
      "Median age",
      "Share of value on players over 28",
    ]) {
      expect(card.getByText(ageField)).toBeTruthy();
    }

    for (const pickField of [
      "Picks owned",
      "Picks traded away",
      "How picks are priced",
    ]) {
      expect(card.getByText(pickField)).toBeTruthy();
    }
    // `pick_value_status: "unvalued"` — the enum speaks rather than showing.
    expect(card.getByText("No price")).toBeTruthy();

    for (const position of ["QB", "RB", "WR", "TE"]) {
      expect(
        card.getByText(new RegExp(`${position}:.*vs\\. the league average`, "i")),
      ).toBeTruthy();
    }
    expect(
      card.getByText(/QB:\s+0\.40\s+vs\. the league average — even/i),
    ).toBeTruthy();
    expect(
      card.getByText(/RB:\s+-0\.30\s+vs\. the league average — thin/i),
    ).toBeTruthy();

    // No raw pipeline key survives on this card.
    expect(card.queryByText(/z_score/i)).toBeNull();
    expect(card.queryByText(/starter_weighted_xvar/i)).toBeNull();

    expect(card.queryByText(/ignored_value_view/i)).toBeNull();
    expect(card.queryByText(/ignored_age_key/i)).toBeNull();
    expect(card.queryByText(/ignored_pick_key/i)).toBeNull();
    expect(card.queryByText(/hide me/i)).toBeNull();
    expect(card.queryByText(/DL:/i)).toBeNull();
    expect(card.queryByText(/Hidden Player/i)).toBeNull();
  });

  it("renders a section-level empty state", () => {
    render(<TeamValueOverview values={[]} />);

    const section = screen.getByRole("region", { name: /team value overview/i });
    expect(within(section).getByText(/no team value context available/i)).toBeTruthy();
  });
});
