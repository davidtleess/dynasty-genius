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

    // DG-118: a `region`, not a `banner` — a page has one banner and the shell
    // owns it; this panel is a named landmark inside `main`.
    const banner = screen.getByRole("region", { name: /league pulse status/i });
    expect(within(banner).getByRole("heading", { name: "League Pulse" })).toBeTruthy();
    // DG-111: three stamps here — "EXPERIMENTAL — a read-only league snapshot.",
    // the "Diagnostic Workspace…" paragraph and "Descriptive only — not
    // decision-grade." — became one sentence. The two load-bearing facts stay:
    // it is a read-only snapshot, and we read rosters, not minds.
    expect(within(banner).queryByText(/not decision-grade/i)).toBeNull();
    expect(within(banner).getByText(/read-only snapshot/i)).toBeTruthy();
    expect(within(banner).getByText(/we don't read minds/i)).toBeTruthy();
    const capturedAt = within(banner).getByText("as of Jun 22, 2026, 2:00 PM EDT");
    expect(capturedAt).toBeTruthy();
    expect(capturedAt.getAttribute("title")).toBe("2026-06-22T18:00:00Z");
    // DG-109: the capture date the caveat carried survives verbatim; only the
    // token's vocabulary changed.
    expect(
      within(banner).getByText(
        "This league snapshot was built from data captured 2026-06-22.",
      ),
    ).toBeTruthy();
    expect(within(banner).getByText(/4 records could not be matched up/i)).toBeTruthy();
    expect(
      within(banner).queryByText("Descriptive only — not decision-grade."),
    ).toBeNull();
    expect(within(banner).queryByText(/decision_supported=false/i)).toBeNull();

    // The three artifact versions stay VERBATIM — they are the receipt, and a
    // receipt that renamed what it cites would stop being one. DG-109 only
    // labels them and declares the list as the receipt layer.
    for (const [label, version] of [
      ["Team posture data", "team_posture.v1"],
      ["Team value data", "team_value_matrix.v1"],
      ["League opportunity data", "league_opportunity.v2"],
    ]) {
      expect(within(banner).getByText(`${label}: ${version}`)).toBeTruthy();
    }
    expect(
      within(banner).getByText("Team posture data: team_posture.v1").closest("ul"),
    ).toHaveProperty("dataset.receipt");
  });

  it("does not render a withheld note when all dropped counts are zero", () => {
    render(<LeaguePulseHeader data={leaguePulseResponse()} />);

    expect(screen.queryByText(/records withheld/i)).toBeNull();
  });
});
