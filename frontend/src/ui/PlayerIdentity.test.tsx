// @vitest-environment jsdom

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// DG-194 adds static imports; the existing cases keep their dynamic imports untouched.
import { headshotSrc, PlayerIdentity } from "./PlayerIdentity";

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

    rerender(
      <PlayerIdentity name="Neymar" team="" position="WR" imageStatus="missing" />,
    );
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

// DG-194 (David, 2026-09-08: "we need headshots for all players") — a headshot failure must belong
// to the IMAGE THAT FAILED, not to the component instance. React reuses an instance when a list
// re-renders with different data, so instance-scoped failure state hides a good photo for the next
// player who lands in that slot, and suppresses a retry from a different source for the same man.
describe("PlayerIdentity — a failed image must not poison the next one", () => {
  it("keeps showing a photo for the next player after the previous one failed in the same slot", () => {
    const { rerender } = render(
      <PlayerIdentity
        name="Joe Flacco"
        team="CIN"
        position="QB"
        imageStatus="available"
        imageSrc="/assets/headshots/19.jpg"
      />,
    );
    fireEvent.error(screen.getByAltText("Joe Flacco"));
    expect(screen.getByLabelText("Joe Flacco headshot unavailable")).toBeTruthy();

    // the same slot now shows a DIFFERENT player whose photo is fine
    rerender(
      <PlayerIdentity
        name="Ashton Jeanty"
        team="LV"
        position="RB"
        imageStatus="available"
        imageSrc="/assets/headshots/12527.jpg"
      />,
    );
    const img = screen.getByAltText("Ashton Jeanty") as HTMLImageElement;
    expect(img.tagName).toBe("IMG");
    expect(img.getAttribute("src")).toBe("/assets/headshots/12527.jpg");
    expect(screen.queryByLabelText("Ashton Jeanty headshot unavailable")).toBeNull();
  });

  it("tries again when the same player is given a different source", () => {
    const { rerender } = render(
      <PlayerIdentity
        name="Joe Flacco"
        team="CIN"
        position="QB"
        imageStatus="available"
        imageSrc="/assets/headshots/19.jpg"
      />,
    );
    fireEvent.error(screen.getByAltText("Joe Flacco"));
    expect(screen.getByLabelText("Joe Flacco headshot unavailable")).toBeTruthy();

    rerender(
      <PlayerIdentity
        name="Joe Flacco"
        team="CIN"
        position="QB"
        imageStatus="available"
        imageSrc="/assets/headshots/19-v2.jpg"
      />,
    );
    expect(
      (screen.getByAltText("Joe Flacco") as HTMLImageElement).getAttribute("src"),
    ).toBe("/assets/headshots/19-v2.jpg");
  });

  it("keeps the failed source suppressed while it is still the one being asked for", () => {
    const { rerender } = render(
      <PlayerIdentity
        name="Joe Flacco"
        team="CIN"
        position="QB"
        imageStatus="available"
        imageSrc="/assets/headshots/19.jpg"
      />,
    );
    fireEvent.error(screen.getByAltText("Joe Flacco"));
    rerender(
      <PlayerIdentity
        name="Joe Flacco"
        team="CIN"
        position="QB"
        imageStatus="available"
        imageSrc="/assets/headshots/19.jpg"
        positionRank="QB12"
      />,
    );
    expect(screen.queryByAltText("Joe Flacco")).toBeNull();
    expect(screen.getByLabelText("Joe Flacco headshot unavailable")).toBeTruthy();
  });

  it("treats a blank source as no source at all, rather than rendering an empty image", () => {
    render(
      <PlayerIdentity
        name="Tank Dell"
        team="HOU"
        position="WR"
        imageStatus="available"
        imageSrc="   "
      />,
    );
    expect(screen.queryByAltText("Tank Dell")).toBeNull();
    expect(screen.getByLabelText("Tank Dell headshot unavailable")).toBeTruthy();
  });

  it("loads lazily, decodes off the main thread and reserves a stable box", () => {
    render(
      <PlayerIdentity
        name="Joe Flacco"
        team="CIN"
        position="QB"
        imageStatus="available"
        imageSrc="/assets/headshots/19.jpg"
      />,
    );
    const img = screen.getByAltText("Joe Flacco");
    expect(img.getAttribute("loading")).toBe("lazy");
    expect(img.getAttribute("decoding")).toBe("async");
    // width and height are what keep a row from jumping as photos arrive
    expect(img.getAttribute("width")).toBe("32");
    expect(img.getAttribute("height")).toBe("32");
  });
});

describe("headshotSrc", () => {
  it("builds the one local URL the cache is served at", () => {
    expect(headshotSrc("12527")).toBe("/assets/headshots/12527.jpg");
  });
  it("returns nothing for an id that could not address a file", () => {
    for (const bad of ["", "   ", "../secrets", "a/b", "12 34"]) {
      expect(headshotSrc(bad)).toBeUndefined();
    }
  });
});
