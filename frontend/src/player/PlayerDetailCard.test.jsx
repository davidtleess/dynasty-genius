// @vitest-environment jsdom

// DG-145 — David, 2026-09-03: "I think free agents should show 'FA' on the
// card", and, asked whether that meant no NFL team or nobody in his league:
// "1) nobody in the league owns." The API serves the fact (rostered by whom, a
// free agent, or unknown) dated by the league roster capture it came from; the
// card prints it in one line, and the word "FA" is minted once, in copy.ts.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LEAGUE_FREE_AGENT_LABEL } from "../lib/copy";
import { PlayerDetailCard } from "./PlayerDetailCard";

const AS_OF = "2026-09-03T13:00:45.589670+00:00";
const AS_OF_ON_SCREEN = "Sep 3, 2026, 9:00 AM EDT";

function detail(league_ownership, identityOverrides = {}) {
  return {
    caveats: ["decision_supported_false"],
    decision_supported: false,
    degradation: { message: "No active model score for this player category." },
    divergence: { delta: null, status: "unavailable" },
    evidence: null,
    frozen_prediction: {
      basis: "store_unavailable_or_ambiguous",
      coverage: {
        current_rostered_skill_in_frozen_prediction_cohort_count: 0,
        current_rostered_skill_not_in_frozen_prediction_cohort_count: 1,
        current_rostered_skill_player_count: 1,
      },
      decision_supported: false,
      frozen_capture_date: "2026-08-05",
      message: "Frozen prediction membership is currently unavailable.",
      season: 2026,
      status: "unavailable",
    },
    identity: {
      age: 27,
      draft_class: 2020,
      name: "Colby Parkinson",
      nfl_draft_pick: 133,
      nfl_draft_round: 4,
      position: "TE",
      sleeper_id: "6879",
      team: "LAR",
      ...identityOverrides,
    },
    league_ownership,
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
    sleeper_id: "6879",
    source_timestamps: { market: null, pvo: "2026-09-03T18:00:02Z" },
  };
}

function ownershipLine(league_ownership) {
  render(<PlayerDetailCard detail={detail(league_ownership)} />);
  return screen.getByTestId("league-ownership");
}

const OWNED_BY_DAVID = {
  as_of: AS_OF,
  owner_display_name: "Dleess",
  roster_id: 1,
  status: "rostered",
  team_name: "Woodbury Riders",
};

// DG-149 (David, 2026-09-04 07:35 ET): "a signal on every player NFL Team
// (including the FA tag if they don't have a team) and Team = team they are on
// in my league i.e. woodbury riders or if they are a FA they get the FA tag
// there too. they should be in different spots - no you can leave it by dleess"
describe("DG-149 two team signals on every player, in different spots", () => {
  it("prints FA in the NFL-team slot of the header for a player with no NFL team", () => {
    render(<PlayerDetailCard detail={detail(OWNED_BY_DAVID, { team: null })} />);
    const header = screen.getByText(/age 27/);
    expect(header.textContent).toBe("TE · FA · age 27");
  });

  it("prints the NFL team itself when he has one", () => {
    render(<PlayerDetailCard detail={detail(OWNED_BY_DAVID, { team: "LAR" })} />);
    expect(screen.getByText(/age 27/).textContent).toBe("TE · LAR · age 27");
  });

  it("names the league team he plays for, apart from the NFL team, and keeps the owner line", () => {
    render(<PlayerDetailCard detail={detail(OWNED_BY_DAVID, { team: null })} />);
    const league = screen.getByTestId("league-team");
    expect(league.textContent).toContain("League team");
    expect(
      within(league).getByText("Woodbury Riders").hasAttribute("data-user-text"),
    ).toBe(true);
    expect(screen.getByTestId("league-ownership").textContent).toContain(
      "Rostered by Dleess",
    );
    expect(league).not.toBe(screen.getByText(/age 27/));
  });

  it("prints FA as the league team of a player nobody in the league owns", () => {
    render(
      <PlayerDetailCard
        detail={detail({
          as_of: AS_OF,
          owner_display_name: null,
          roster_id: null,
          status: "free_agent",
          team_name: null,
        })}
      />,
    );
    const league = screen.getByTestId("league-team");
    expect(within(league).getByText("FA")).toBeTruthy();
  });

  it("falls back to the manager's handle, and says so, when he never named his team", () => {
    render(
      <PlayerDetailCard
        detail={detail({
          as_of: AS_OF,
          owner_display_name: "rzalika",
          roster_id: 5,
          status: "rostered",
          team_name: null,
        })}
      />,
    );
    const league = screen.getByTestId("league-team");
    expect(within(league).getByText("rzalika").hasAttribute("data-user-text")).toBe(
      true,
    );
    expect(league.textContent).toContain("no team name");
    expect(within(league).queryByText("FA")).toBeNull();
  });

  it("says the league team is unknown when the capture could not vouch for him", () => {
    render(
      <PlayerDetailCard
        detail={detail({
          as_of: null,
          owner_display_name: null,
          roster_id: null,
          status: "unknown",
          team_name: null,
        })}
      />,
    );
    const league = screen.getByTestId("league-team");
    expect(league.textContent).toContain("unknown");
    expect(within(league).queryByText("FA")).toBeNull();
  });
});

describe("DG-145 the card says who owns him in your league", () => {
  it("prints FA for a player nobody in the league owns, dated by the roster capture", () => {
    const line = ownershipLine({
      as_of: AS_OF,
      owner_display_name: null,
      roster_id: null,
      status: "free_agent",
    });
    expect(within(line).getByText("FA")).toBeTruthy();
    expect(line.textContent).toContain("nobody in your league owns him");
    expect(line.textContent).toContain(AS_OF_ON_SCREEN);
  });

  it("names the manager for a rostered player and never says FA", () => {
    const line = ownershipLine({
      as_of: AS_OF,
      owner_display_name: "Dleess",
      roster_id: 1,
      status: "rostered",
      team_name: "Woodbury Riders",
    });
    expect(line.textContent).toContain("Rostered by Dleess");
    expect(within(line).queryByText("FA")).toBeNull();
    expect(line.textContent).toContain(AS_OF_ON_SCREEN);
    // The handle is text the league wrote, not our vocabulary (DG-109).
    expect(within(line).getByText("Dleess").hasAttribute("data-user-text")).toBe(true);
  });

  it("says rostered without a name when the capture had the roster but not the manager", () => {
    const line = ownershipLine({
      as_of: AS_OF,
      owner_display_name: null,
      roster_id: 7,
      status: "rostered",
    });
    expect(line.textContent).toContain("Rostered in your league");
    expect(within(line).queryByText("FA")).toBeNull();
  });

  it("says the ownership is unknown, never FA, when the capture could not vouch for him", () => {
    const line = ownershipLine({
      as_of: null,
      owner_display_name: null,
      roster_id: null,
      status: "unknown",
    });
    expect(line.textContent).toContain(
      "Who owns him in your league is unknown right now",
    );
    expect(within(line).queryByText("FA")).toBeNull();
    expect(line.textContent).not.toContain("as of");
  });

  it("never prints FA without a capture time, even if the API called him a free agent", () => {
    // The route collapses an undated snapshot to "unknown" and a backend test
    // pins that; the card holds the same line at its own boundary, so the
    // contract's nullable as_of can never put an undated "FA" on screen.
    const line = ownershipLine({
      as_of: null,
      owner_display_name: null,
      roster_id: null,
      status: "free_agent",
    });
    expect(within(line).queryByText("FA")).toBeNull();
    expect(line.textContent).toContain(
      "Who owns him in your league is unknown right now",
    );
  });

  it("mints the word once, in the copy dictionary", () => {
    expect(LEAGUE_FREE_AGENT_LABEL).toBe("FA");
  });
});
