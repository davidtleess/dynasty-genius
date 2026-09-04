// DG-149: the word "FA" has one home, and both team spots read it from there.
import { describe, expect, it } from "vitest";

import { FREE_AGENT_LABEL, LEAGUE_FREE_AGENT_LABEL, nflTeamLabel } from "./copy";

describe("DG-149 the NFL-team label", () => {
  it("prints the team when he has one and FA when he has none, Active or not", () => {
    expect(nflTeamLabel("KC")).toBe("KC");
    expect(nflTeamLabel(null)).toBe("FA");
    expect(nflTeamLabel(undefined)).toBe("FA");
    expect(nflTeamLabel("")).toBe("FA");
  });

  it("is the same word as the league free-agent label, minted once", () => {
    expect(FREE_AGENT_LABEL).toBe("FA");
    expect(LEAGUE_FREE_AGENT_LABEL).toBe(FREE_AGENT_LABEL);
  });
});
