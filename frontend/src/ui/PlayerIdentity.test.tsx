// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
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

  it("renders a local cached headshot, team identity mark, and positional rank", async () => {
    const { PlayerIdentity } = await import("./PlayerIdentity");
    const Increment0PlayerIdentity = PlayerIdentity as any;

    const { container } = render(
      <Increment0PlayerIdentity
        name="Bijan Robinson"
        team="ATL"
        position="RB"
        imageStatus="available"
        imageSrc="/assets/headshots/1234.jpg"
        teamId="ATL"
        positionRank="RB1"
      />,
    );

    const image = screen.getByRole("img", { name: "Bijan Robinson" });
    expect(image.getAttribute("src")).toBe("/assets/headshots/1234.jpg");
    expect(image.getAttribute("src")).not.toContain("sleepercdn.com");
    expect(screen.getByText("RB1").className).toContain("dg-ui-player-id__pos-rank");
    const teamMark = container.querySelector("[data-team-id='ATL']");
    expect(teamMark).toBeTruthy();
    expect(teamMark?.className).toContain("dg-ui-player-id__team-mark");
  });

  it("swaps a broken cached image to the accessible fallback without a broken glyph", async () => {
    const { PlayerIdentity } = await import("./PlayerIdentity");
    const Increment0PlayerIdentity = PlayerIdentity as any;

    const { container } = render(
      <Increment0PlayerIdentity
        name="Jaxon Smith-Njigba"
        team="SEA"
        position="WR"
        imageStatus="available"
        imageSrc="/assets/headshots/9999.jpg"
        teamId="SEA"
      />,
    );

    fireEvent.error(screen.getByRole("img", { name: "Jaxon Smith-Njigba" }));

    expect(container.querySelector("img")).toBeNull();
    expect(
      screen.getByRole("img", { name: /jaxon smith-njigba headshot unavailable/i }),
    ).toBeTruthy();
  });

  it("uses a stable initials rule for non-ASCII, single-word, and long names", async () => {
    const { PlayerIdentity } = await import("./PlayerIdentity");

    const { rerender } = render(
      <PlayerIdentity name="Émile Zola" team="" position="WR" imageStatus="missing" />,
    );
    expect(screen.getByText("ÉZ").className).toContain(
      "dg-ui-player-id__headshot--fallback",
    );

    rerender(<PlayerIdentity name="Neymar" team="" position="WR" imageStatus="missing" />);
    expect(screen.getByText("NE").className).toContain(
      "dg-ui-player-id__headshot--fallback",
    );

    rerender(
      <PlayerIdentity
        name="Amon-Ra Julian Heru St. Brown"
        team=""
        position="WR"
        imageStatus="missing"
      />,
    );
    expect(screen.getByText("AH").className).toContain(
      "dg-ui-player-id__headshot--fallback",
    );
  });
});
