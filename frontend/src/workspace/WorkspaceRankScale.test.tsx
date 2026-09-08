// @vitest-environment jsdom
// DG-196 — the shared us-vs-market rank scale, adapted from the imported Directions design.
//
// The imported artifact draws ONE player on ONE 388-long axis. Everything asserted here is about the
// five ways a component has to be stricter than a drawing: the population is a prop, both sides can be
// tied, a one-player population is legal, a malformed interval is refused rather than clipped, and a
// magnified axis always carries labels.
//
// Geometry is read off the rendered DOM. Percentages below are hand-derived from the stated ranks
// ((r - 1) / (total - 1) * 100), never recomputed with the component's own helper.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { auditRenderedCopy, formatRawCopyFindings } from "../lib/renderRule";
import { WorkspaceRankScale } from "./WorkspaceRankScale";

type Span = { start: number; end: number; total: number };
const span = (start: number, end = start, total = 388): Span => ({ start, end, total });

function draw(props: {
  ourRank?: Span | null;
  marketRank?: Span | null;
  playerName?: string;
}) {
  const { container } = render(
    <WorkspaceRankScale
      ourRank={props.ourRank ?? null}
      marketRank={props.marketRank ?? null}
      playerName={props.playerName ?? "Alpha Adams"}
    />,
  );
  return container;
}

const rail = (root: Element) => root.querySelector(".dg-rank-scale__rail");
const caption = (root: Element) =>
  root.querySelector(".dg-rank-scale__caption")?.textContent ?? "";
const mark = (root: Element, side: string) =>
  root.querySelector(
    `.dg-rank-scale__plot:not(.dg-rank-scale__plot--zoom) .dg-rank-scale__mark[data-side="${side}"]`,
  );
const band = (root: Element, side: string) =>
  root.querySelector(
    `.dg-rank-scale__plot:not(.dg-rank-scale__plot--zoom) .dg-rank-scale__band[data-side="${side}"]`,
  );
const ticks = (root: Element) =>
  [
    ...root.querySelectorAll(
      ".dg-rank-scale__ticks:not(.dg-rank-scale__ticks--zoom) .dg-rank-scale__tick",
    ),
  ].map((node) => node.textContent);
const pct = (node: Element | null | undefined, property: "left" | "width") => {
  const raw = (node as HTMLElement | null)?.style.getPropertyValue(property) ?? "";
  return raw === "" ? null : Number.parseFloat(raw);
};

// --- the axis itself ---------------------------------------------------------------------------

describe("the shared axis", () => {
  it("places rank 1 at the left edge and the last rank at the right edge", () => {
    const root = draw({ ourRank: span(1, 1, 5), marketRank: span(5, 5, 5) });
    expect(pct(mark(root, "ours"), "left")).toBeCloseTo(0, 6);
    expect(pct(mark(root, "market"), "left")).toBeCloseTo(100, 6);
  });

  it("reads its population from the props rather than a built-in 388", () => {
    const root = draw({ ourRank: span(3, 3, 5), marketRank: span(5, 5, 5) });
    // rank 3 of 5 is the middle of the axis; on a welded 388 axis it would sit at 0.5%
    expect(pct(mark(root, "ours"), "left")).toBeCloseTo(50, 6);
    expect(caption(root)).toContain("5-player");
    expect(caption(root)).not.toContain("388");
  });

  it("labels the axis with ticks that start at 1 and end at the population", () => {
    const root = draw({ ourRank: span(2, 2, 5), marketRank: span(4, 4, 5) });
    const labels = ticks(root);
    expect(labels[0]).toBe("#1");
    expect(labels[labels.length - 1]).toBe("#5");
  });

  it("says lower is better so the direction of the axis is never inferred from the picture", () => {
    const root = draw({ ourRank: span(2, 2, 5), marketRank: span(4, 4, 5) });
    expect(caption(root).toLowerCase()).toMatch(/lower is better|best on the left/);
  });
});

// --- ties on BOTH sides, which the sample artifact does not do ---------------------------------

describe("ties", () => {
  it("draws our tie as the span it really is", () => {
    const root = draw({ ourRank: span(3, 5, 5), marketRank: span(1, 1, 5) });
    const ours = band(root, "ours");
    expect(ours).not.toBeNull();
    expect(pct(ours, "left")).toBeCloseTo(50, 6); // rank 3 of 5
    expect(pct(ours, "width")).toBeCloseTo(50, 6); // through rank 5
  });

  it("draws a MARKET tie as a span too, which the imported artifact never did", () => {
    const root = draw({ ourRank: span(1, 1, 5), marketRank: span(3, 5, 5) });
    const market = band(root, "market");
    expect(market).not.toBeNull();
    expect(pct(market, "left")).toBeCloseTo(50, 6);
    expect(pct(market, "width")).toBeCloseTo(50, 6);
  });

  it("draws both spans when both sides are tied", () => {
    const root = draw({ ourRank: span(1, 2, 5), marketRank: span(4, 5, 5) });
    expect(band(root, "ours")).not.toBeNull();
    expect(band(root, "market")).not.toBeNull();
  });

  it("never replaces a tie with its midpoint", () => {
    const root = draw({ ourRank: span(3, 5, 5), marketRank: span(1, 1, 5) });
    // a midpoint substitution would draw a single ours mark at rank 4, i.e. 75%
    expect(mark(root, "ours")).toBeNull();
    expect(screen.getAllByText(/#3–5/).length).toBeGreaterThan(0);
  });

  it("says a tie is a rank tie and not a confidence interval", () => {
    const root = draw({ ourRank: span(3, 5, 5), marketRank: span(1, 1, 5) });
    expect(caption(root).toLowerCase()).toContain("confidence interval");
  });

  it("keeps a singleton narrow instead of floor-filling the axis", () => {
    // DG-188 regression: a 0.5 meant as a 0.5% minimum was a 50% floor, so every exact rank
    // filled half the axis and a genuine 159-wide tie looked identical to one player.
    const root = draw({ ourRank: span(40, 40), marketRank: span(41, 41) });
    expect(band(root, "ours")).toBeNull();
    expect(pct(mark(root, "ours"), "width")).toBeNull(); // width belongs to CSS, not the number

    const wide = draw({ ourRank: span(40, 42), marketRank: span(41, 41) });
    expect(pct(band(wide, "ours"), "width")).toBeLessThan(5); // 2/387 of the axis, not 50
    expect(pct(band(wide, "ours"), "width")).toBeGreaterThan(0);
  });
});

// --- what the caption claims -------------------------------------------------------------------

describe("the direction it reports", () => {
  it("reports how many places higher we rank him when the intervals are clear of each other", () => {
    const root = draw({ ourRank: span(3, 3), marketRank: span(10, 10) });
    expect(caption(root)).toContain("7 places higher");
  });

  it("reports lower when the market ranks him better than we do", () => {
    const root = draw({ ourRank: span(20, 20), marketRank: span(5, 5) });
    expect(caption(root)).toContain("lower");
  });

  it("says the ranks are the same only when both sides are a single equal rank", () => {
    const root = draw({ ourRank: span(9, 9), marketRank: span(9, 9) });
    expect(caption(root).toLowerCase()).toContain("same");
  });

  it("claims no preference when the two intervals overlap", () => {
    const root = draw({ ourRank: span(4, 9), marketRank: span(7, 12) });
    const text = caption(root).toLowerCase();
    expect(text).toContain("overlap");
    expect(text).not.toMatch(/places (higher|lower)/);
  });

  it("says at least when a tie makes the distance a bound rather than a number", () => {
    const root = draw({ ourRank: span(3, 5), marketRank: span(20, 20) });
    expect(caption(root)).toContain("at least");
  });
});

// --- a missing side is missing, not zero --------------------------------------------------------

describe("a missing side", () => {
  it("draws no axis and no zero marker when the market has no rank", () => {
    const root = draw({ ourRank: span(3, 5), marketRank: null });
    expect(rail(root)).toBeNull();
    expect(mark(root, "market")).toBeNull();
    expect(band(root, "market")).toBeNull();
  });

  it("keeps our rank readable and names the absence as missing rather than zero", () => {
    const root = draw({ ourRank: span(3, 5), marketRank: null });
    expect(screen.getAllByText(/#3–5/).length).toBeGreaterThan(0);
    expect(root.textContent?.toLowerCase()).toContain("missing, not zero");
  });

  it("keeps the market rank readable when we have no rank for him", () => {
    const root = draw({ ourRank: null, marketRank: span(12, 12) });
    expect(rail(root)).toBeNull();
    expect(screen.getAllByText(/#12/).length).toBeGreaterThan(0);
    expect(root.textContent?.toLowerCase()).toContain("missing, not zero");
  });

  it("says so plainly when neither side has a rank", () => {
    const root = draw({ ourRank: null, marketRank: null });
    expect(rail(root)).toBeNull();
    expect(root.textContent?.toLowerCase()).toContain("no rank");
  });
});

// --- refusals: an invented coordinate is worse than no picture ----------------------------------

describe("refusals", () => {
  it("refuses two different populations rather than drawing them on one axis", () => {
    const root = draw({ ourRank: span(3, 3, 388), marketRank: span(3, 3, 825) });
    expect(rail(root)).toBeNull();
    expect(root.textContent?.toLowerCase()).toContain("no comparable scale");
  });

  it.each([
    ["a rank below 1", { start: 0, end: 3, total: 388 }],
    ["a rank past the population", { start: 3, end: 400, total: 388 }],
    ["an inverted interval", { start: 5, end: 3, total: 388 }],
    ["a non-integer rank", { start: 2.5, end: 3, total: 388 }],
    ["a non-finite rank", { start: Number.NaN, end: 3, total: 388 }],
    ["an infinite population", { start: 1, end: 3, total: Number.POSITIVE_INFINITY }],
    ["an empty population", { start: 1, end: 1, total: 0 }],
  ])("refuses %s rather than clipping it into the axis", (_label, bad) => {
    const root = draw({ ourRank: bad as Span, marketRank: span(9, 9) });
    expect(rail(root)).toBeNull();
    expect(root.textContent?.toLowerCase()).toContain("no comparable scale");
  });

  it("never emits a NaN coordinate", () => {
    const root = draw({ ourRank: span(3, 3, 388), marketRank: span(3, 3, 825) });
    expect(root.innerHTML).not.toContain("NaN");
  });
});

// --- the degenerate population ------------------------------------------------------------------

describe("a one-player population", () => {
  it("draws the single position without dividing by zero", () => {
    const root = draw({ ourRank: span(1, 1, 1), marketRank: span(1, 1, 1) });
    expect(rail(root)).not.toBeNull();
    expect(root.innerHTML).not.toContain("NaN");
    expect(pct(mark(root, "ours"), "left")).toBeCloseTo(50, 6);
  });

  it("carries exactly one tick, so the degenerate axis describes itself", () => {
    const root = draw({ ourRank: span(1, 1, 1), marketRank: span(1, 1, 1) });
    expect(ticks(root)).toEqual(["#1"]);
  });
});

// --- the zoomed inset ----------------------------------------------------------------------------

describe("the zoomed inset", () => {
  it("declares the rank extent it is actually showing", () => {
    const root = draw({ ourRank: span(3, 5), marketRank: span(12, 12) });
    // pad = ceil(388 / 20) = 20, so the window is #1 to #32
    expect(root.textContent).toContain("#1");
    expect(root.textContent).toContain("#32");
    expect(root.textContent).toContain("of 388");
  });

  it("always labels both ends of the magnified window", () => {
    // the imported loop started at ceil(wLo/step)*step and could emit no ticks at all
    const root = draw({ ourRank: span(3, 5), marketRank: span(12, 12) });
    const zoomTicks = [
      ...root.querySelectorAll(".dg-rank-scale__ticks--zoom .dg-rank-scale__tick"),
    ].map((node) => node.textContent);
    expect(zoomTicks.length).toBeGreaterThan(1);
    expect(zoomTicks[0]).toBe("#1");
    expect(zoomTicks[zoomTicks.length - 1]).toBe("#32");
  });

  it("is left out when the two marks already span the whole axis", () => {
    const root = draw({ ourRank: span(1, 1), marketRank: span(388, 388) });
    expect(root.querySelector(".dg-rank-scale__zoom")).toBeNull();
  });

  it("is left out for a one-player population, which cannot be magnified", () => {
    const root = draw({ ourRank: span(1, 1, 1), marketRank: span(1, 1, 1) });
    expect(root.querySelector(".dg-rank-scale__zoom")).toBeNull();
  });

  it("re-plots the same intervals rather than re-deriving them", () => {
    const root = draw({ ourRank: span(3, 5), marketRank: span(12, 12) });
    const zoomBand = root.querySelector(
      '.dg-rank-scale__plot--zoom .dg-rank-scale__band[data-side="ours"]',
    );
    // window #1..#32 spans 31 ranks; ours starts at #3 -> 2/31, and is 2/31 wide through #5
    expect(pct(zoomBand, "left")).toBeCloseTo((2 / 31) * 100, 4);
    expect(pct(zoomBand, "width")).toBeCloseTo((2 / 31) * 100, 4);
  });
});

// --- the reading survives without colour or geometry ----------------------------------------------

describe("accessible text", () => {
  it("states the player, both ranks, the population and the direction in words", () => {
    const root = draw({
      ourRank: span(3, 5),
      marketRank: span(20, 20),
      playerName: "Alpha Adams",
    });
    const text = caption(root);
    expect(text).toContain("Alpha Adams");
    expect(text).toContain("#3–5");
    expect(text).toContain("#20");
    expect(text).toContain("388-player");
    expect(text).toContain("higher");
  });

  it("hides the pure geometry from assistive technology", () => {
    const root = draw({ ourRank: span(3, 5), marketRank: span(20, 20) });
    const plot = root.querySelector(".dg-rank-scale__plot");
    expect(plot?.getAttribute("aria-hidden")).toBe("true");
  });

  it("renders no raw or unformatted copy", () => {
    const root = draw({ ourRank: span(3, 5), marketRank: span(20, 20) });
    const findings = auditRenderedCopy(root);
    expect(findings, formatRawCopyFindings(findings)).toHaveLength(0);
  });
});

// --- root's rendering review, 2026-09-08 ----------------------------------------------------------

describe("both readings stay visible", () => {
  it("gives each side its own lane so an exact agreement does not hide our mark", () => {
    // ours and the market on the identical rank: without separate lanes the later mark in the DOM
    // draws straight over the earlier one, and agreement — the whole point of the picture — vanishes
    const root = draw({ ourRank: span(40, 40), marketRank: span(40, 40) });
    const ourLane = root.querySelector('.dg-rank-scale__row[data-side="ours"]');
    const marketLane = root.querySelector('.dg-rank-scale__row[data-side="market"]');
    expect(ourLane).not.toBeNull();
    expect(marketLane).not.toBeNull();
    expect(ourLane).not.toBe(marketLane);
    expect(ourLane?.contains(mark(root, "ours"))).toBe(true);
    expect(marketLane?.contains(mark(root, "market"))).toBe(true);
  });

  it("separates overlapping ties into their own lanes too", () => {
    const root = draw({ ourRank: span(40, 45), marketRank: span(42, 47) });
    const ourLane = root.querySelector('.dg-rank-scale__row[data-side="ours"]');
    const marketLane = root.querySelector('.dg-rank-scale__row[data-side="market"]');
    expect(ourLane?.contains(band(root, "ours"))).toBe(true);
    expect(marketLane?.contains(band(root, "market"))).toBe(true);
  });
});

describe("labels are bounded by their own width", () => {
  it("states each label's box so the stylesheet can clamp it inside the axis", () => {
    const root = draw({ ourRank: span(40, 49), marketRank: span(4, 4) });
    const tags = [...root.querySelectorAll(".dg-rank-scale__tag")] as HTMLElement[];
    expect(tags).toHaveLength(2);
    for (const tag of tags) {
      expect(tag.style.getPropertyValue("--dg-rank-scale-at")).toMatch(/%$/);
      expect(tag.style.getPropertyValue("--dg-rank-scale-box")).toMatch(/ch$/);
    }
  });

  it("gives a longer label a wider box", () => {
    const root = draw({ ourRank: span(40, 49), marketRank: span(4, 4) });
    const boxOf = (side: string) => {
      const tag = root.querySelector(
        `.dg-rank-scale__tag[data-side="${side}"]`,
      ) as HTMLElement;
      return Number.parseFloat(tag.style.getPropertyValue("--dg-rank-scale-box"));
    };
    // "Ours #40–49" is longer than "Market #4" by enough that a fixed box would misplace one of them
    expect(boxOf("ours")).toBeGreaterThan(boxOf("market"));
  });

  it("bounds the tick labels the same way", () => {
    const root = draw({ ourRank: span(3, 3), marketRank: span(300, 300) });
    const tick = root.querySelector(".dg-rank-scale__tick") as HTMLElement;
    expect(tick.style.getPropertyValue("--dg-rank-scale-box")).toMatch(/ch$/);
  });
});

describe("the zoom stays legible and stays worth drawing", () => {
  it("drops an interior tick that would collide with a window end", () => {
    // window #69 to #115: the step-10 grid puts #70 one place from the left end and #110 five from
    // the right, either of which prints on top of the end label on a narrow column
    const root = draw({ ourRank: span(89, 89), marketRank: span(95, 95) });
    const zoomTicks = [
      ...root.querySelectorAll(".dg-rank-scale__ticks--zoom .dg-rank-scale__tick"),
    ].map((node) => node.textContent);
    expect(zoomTicks[0]).toBe("#69");
    expect(zoomTicks[zoomTicks.length - 1]).toBe("#115");
    expect(zoomTicks).not.toContain("#70");
    expect(zoomTicks).not.toContain("#110");
    expect(zoomTicks.length).toBeGreaterThan(2);
  });

  it("is left out when the window would re-plot almost the whole population", () => {
    // #10 to #360 of 388 is 90% of the axis: a second copy of the first picture, not a magnification
    const root = draw({ ourRank: span(30, 30), marketRank: span(340, 340) });
    expect(root.querySelector(".dg-rank-scale__zoom")).toBeNull();
  });

  it("is still drawn when the window genuinely magnifies", () => {
    const root = draw({ ourRank: span(30, 30), marketRank: span(60, 60) });
    expect(root.querySelector(".dg-rank-scale__zoom")).not.toBeNull();
  });
});
