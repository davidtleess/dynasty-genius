// @vitest-environment jsdom

// DG-043 — the two-lane furniture must render REAL labeled pairs.
//
// Defect 1 (axe definition-list, serious + the visible run-on line): the lanes
// put bare <span>s inside a <dl>, so a manager reads
// "FantasyCalc1224Overall 185Position 712026-07-22T13:00:00…" with no labels.
// The fix is one fix: every fact is a <div><dt>label</dt><dd>value</dd></div>
// group (the only children axe's definition-list rule permits), every number
// carries a plain-language label, raw ISO timestamps become readable dates,
// and raw caveat keys become plain sentences (David's 2026-08-29 prose ruling).
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ValuationTwoLane } from "./ValuationTwoLane";

const model = {
  dynasty_value_score: 85.14,
  engine_path: "ENGINE_A",
  model_grade: "PROSPECT_D",
  model_version: "engine_a_v3",
  projection_1y: 6.1,
  projection_2y: 9.8,
  projection_3y: 12.4,
  xvar: 10.31,
  xvar_percentile_position: 91.0,
};

const market = {
  caveats: [
    "market_overlay_static_caveat",
    "source_timestamp_is_fetch_time_not_publish_time",
  ],
  market_rank_overall: 42,
  market_rank_position: 8,
  market_value: 4371,
  source: "fantasycalc",
  source_timestamp: "2026-05-24T17:19:52Z",
  status: "available",
};

const divergence = { delta: -0.237, status: "model_lower_than_market" };

function renderLanes(overrides = {}) {
  render(
    <ValuationTwoLane
      model={model}
      market={market}
      divergence={divergence}
      {...overrides}
    />,
  );
}

// The exact structural contract behind axe's definition-list rule: a <dl> may
// directly contain only properly-ordered dt/dd groups (optionally wrapped in a
// <div>). Bare <span> children are the measured violation.
function expectValidDefinitionList(dl) {
  expect(dl.children.length).toBeGreaterThan(0);
  for (const group of dl.children) {
    expect(group.tagName).toBe("DIV");
    const parts = [...group.children].map((child) => child.tagName);
    expect(parts[0]).toBe("DT");
    expect(parts).toContain("DD");
    // dt(s) first, then dd(s) — never interleaved out of order.
    expect(parts.indexOf("DD")).toBeGreaterThan(parts.lastIndexOf("DT") - 1);
  }
}

describe("ValuationTwoLane labeled pairs (DG-043)", () => {
  it("renders the model lane as dt/dd pairs — every number labeled", () => {
    renderLanes();

    const lane = screen.getByTestId("player-model-lane");
    expectValidDefinitionList(lane.querySelector("dl"));

    const pairs = [
      ["Engine", "ENGINE_A"],
      ["Model grade", "PROSPECT_D"],
      ["Dynasty value", "85.14"],
      ["Value above replacement (xVAR)", "10.31"],
      ["Position percentile", "91%"],
      ["1-year projection", "6.1"],
      ["2-year projection", "9.8"],
      ["3-year projection", "12.4"],
    ];
    for (const [term, definition] of pairs) {
      const dt = within(lane).getByText(term);
      expect(dt.tagName).toBe("DT");
      const dd = within(dt.closest("div")).getByText(definition);
      expect(dd.tagName).toBe("DD");
    }
  });

  it("renders the market lane as labeled pairs with a readable date, not a raw ISO timestamp", () => {
    renderLanes();

    const lane = screen.getByTestId("player-market-lane");
    expectValidDefinitionList(lane.querySelector("dl"));

    const pairs = [
      ["Source", "FantasyCalc"],
      ["Market value", "4371"],
      ["Overall rank", "42"],
      ["Position rank", "8"],
      ["Prices captured", "May 24, 2026"],
    ];
    for (const [term, definition] of pairs) {
      const dt = within(lane).getByText(term);
      expect(dt.tagName).toBe("DT");
      const dd = within(dt.closest("div")).getByText(definition);
      expect(dd.tagName).toBe("DD");
    }

    expect(within(lane).queryByText("2026-05-24T17:19:52Z")).toBeNull();
  });

  it("speaks caveats as plain sentences, never raw pipeline keys", () => {
    renderLanes();

    const lane = screen.getByTestId("player-market-lane");
    expect(within(lane).queryByText("market_overlay_static_caveat")).toBeNull();
    expect(
      within(lane).queryByText("source_timestamp_is_fetch_time_not_publish_time"),
    ).toBeNull();
    expect(
      within(lane).getByText(
        "Market values come from a saved FantasyCalc snapshot, not a live feed.",
      ),
    ).toBeTruthy();
    expect(
      within(lane).getByText(
        "The capture date above is when we pulled these prices, not when the source published them.",
      ),
    ).toBeTruthy();
    // Caveat prose lives OUTSIDE the <dl> (it is a sentence, not a key/value
    // fact) so the definition list stays structurally valid.
    const dl = lane.querySelector("dl");
    expect(dl.textContent).not.toContain("snapshot, not a live feed");
  });

  it("humanizes an unknown caveat key instead of fabricating meaning for it", () => {
    renderLanes({
      market: { ...market, caveats: ["some_future_caveat_key"] },
    });

    const lane = screen.getByTestId("player-market-lane");
    expect(within(lane).queryByText("some_future_caveat_key")).toBeNull();
    expect(within(lane).getByText("Some future caveat key.")).toBeTruthy();
  });

  it("keeps honest degradation when the timestamp is absent", () => {
    renderLanes({
      market: { ...market, source_timestamp: null, caveats: [] },
    });

    const lane = screen.getByTestId("player-market-lane");
    const dt = within(lane).getByText("Prices captured");
    expect(within(dt.closest("div")).getByText("—")).toBeTruthy();
  });
});
