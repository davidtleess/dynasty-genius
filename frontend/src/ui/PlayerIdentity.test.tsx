// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("PlayerIdentity", () => {
  it("renders player identity, position, team-color basis, and accessible fallback", async () => {
    const { PlayerIdentity } = await import("./PlayerIdentity");

    render(
      <PlayerIdentity
        name="Bijan Robinson"
        team="ATL"
        position="RB"
        imageStatus="missing"
      />,
    );

    expect(screen.getByText("Bijan Robinson")).toBeTruthy();
    expect(screen.getByText("RB").className).toContain("dg-ui-player-id__position");
    expect(screen.getByText("ATL").getAttribute("data-team-color-basis")).toBe("ATL");
    expect(
      screen.getByRole("img", { name: /bijan robinson headshot unavailable/i }),
    ).toBeTruthy();
    expect(screen.queryByRole("img", { name: /http/i })).toBeNull();
  });
});
