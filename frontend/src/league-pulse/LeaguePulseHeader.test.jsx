// @vitest-environment jsdom
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { leaguePulseResponse } from "./fixtures";
import { LeaguePulseHeader } from "./LeaguePulseHeader";

function headerResponse() {
  return leaguePulseResponse({
    dropped: {
      market_overlay_cards: 2,
      model_native_cards: 1,
      partner_rankings: 0,
      roster_capacity_candidate_pools: 1,
      team_postures: 0,
      team_values: 0,
      decision_supported: false,
    },
  });
}

describe("LeaguePulseHeader", () => {
  it("renders artifact-state honesty, source versions, withheld counts, and non-grade status", () => {
    render(<LeaguePulseHeader data={headerResponse()} />);

    const banner = screen.getByRole("banner", { name: /league pulse status/i });
    expect(within(banner).getByRole("heading", { name: "League Pulse" })).toBeTruthy();
    expect(within(banner).getByText(/experimental/i)).toBeTruthy();
    expect(within(banner).getByText(/not decision-grade/i)).toBeTruthy();
    expect(within(banner).getByText(/as of 2026-06-22T18:00:00Z/i)).toBeTruthy();
    expect(
      within(banner).getByText("league_pulse_artifact_state_2026-06-22"),
    ).toBeTruthy();
    expect(within(banner).getByText(/4 records withheld/i)).toBeTruthy();
    expect(within(banner).getByText(/decision_supported=false/i)).toBeTruthy();

    for (const version of [
      "team_posture.v1",
      "team_value_matrix.v1",
      "league_opportunity.v2",
    ]) {
      expect(within(banner).getByText(version)).toBeTruthy();
    }
  });

  it("does not render a withheld note when all dropped counts are zero", () => {
    render(<LeaguePulseHeader data={leaguePulseResponse()} />);

    expect(screen.queryByText(/records withheld/i)).toBeNull();
  });
});
