// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { TeamPostureTable } from "./TeamPostureTable";

function postureRows() {
  const base = leaguePulseResponse().team_postures[0];
  return [
    {
      ...base,
      roster_id: 9,
      team_name: "Roster Nine",
      posture_label: "ASCENDING",
      score: 0.812,
      caveats: ["phase18_heuristic_posture"],
      components: {
        starter_weighted_xvar_z: 1.1,
        age_window_score: 0.4,
        early_pick_balance_score: 0.2,
        development_stash_score: 0.1,
        ignored_component: 9.9,
      },
    },
  ];
}

describe("TeamPostureTable", () => {
  it("renders team posture rows with the exact component allowlist", () => {
    render(<TeamPostureTable postures={postureRows()} />);

    const section = screen.getByRole("region", { name: /team postures/i });
    expect(
      within(section).getByRole("heading", { name: /team postures/i }),
    ).toBeTruthy();

    const row = within(section).getByText("Roster Nine").closest("article");
    expect(row).toBeTruthy();
    const card = within(row);

    expect(card.getByText(/roster 9/i)).toBeTruthy();
    expect(card.getByText("ASCENDING")).toBeTruthy();
    expect(card.getByText(/0\.812/)).toBeTruthy();
    expect(card.getByText("phase18_heuristic_posture")).toBeTruthy();

    for (const component of [
      "starter_weighted_xvar_z",
      "age_window_score",
      "early_pick_balance_score",
      "development_stash_score",
    ]) {
      expect(card.getByText(component)).toBeTruthy();
    }

    expect(card.queryByText(/ignored_component/i)).toBeNull();
    expect(card.queryByText(/9\.9/)).toBeNull();
  });

  it("renders a section-level empty state", () => {
    render(<TeamPostureTable postures={[]} />);

    const section = screen.getByRole("region", { name: /team postures/i });
    expect(
      within(section).getByText(/no team posture context available/i),
    ).toBeTruthy();
  });
});
