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
      // DG-109: which model scored him and what state the score is in are both
      // FACTS and both stay — said in words, not as ENGINE_A / PROSPECT_D.
      ["Scored by", "Rookie model — draft capital and age"],
      ["Model status", "Scored by the rookie model — accuracy grade D, its weakest"],
      ["Dynasty value", "85.14"],
      // DG-117: the card was the fourth place spelling this one quantity its
      // own way. The dictionary spells it now.
      ["Value over replacement", "10.31"],
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

  it("keeps an unmapped caveat on screen in the receipt layer, never dressed as prose", () => {
    renderLanes({
      market: { ...market, caveats: ["some_future_caveat_key"] },
    });

    const lane = screen.getByTestId("player-market-lane");
    // DG-109: the FACT is not dropped — it renders raw and labelled as raw, in
    // the receipt layer, so the crew adds a sentence for it. It is never
    // half-humanized into body copy that reads like a claim we wrote.
    const receipt = within(lane).getByTestId("untranslated-tokens");
    expect(receipt.textContent).toContain("some_future_caveat_key");
    expect(receipt.dataset.receipt).toBeDefined();
    expect(within(lane).queryByText("Some future caveat key.")).toBeNull();
  });

  it("keeps honest degradation when the timestamp is absent", () => {
    renderLanes({
      market: { ...market, source_timestamp: null, caveats: [] },
    });

    const lane = screen.getByTestId("player-market-lane");
    const dt = within(lane).getByText("Prices captured");
    expect(within(dt.closest("div")).getByText("—")).toBeTruthy();
  });

  // DG-043 panel fix 1 — te_review_period is a LIVE key: the producer appends it
  // to every TE (universe_market_divergence.py:291), 62 of the 398 players
  // carrying a market overlay today. It had no sentence, so it fell through the
  // humanizer and reached the screen as "Te review period." — a raw pipeline key
  // in all but spelling, which is what the prose ruling forbids.
  it("speaks the live te_review_period caveat as a real sentence", () => {
    renderLanes({
      market: { ...market, caveats: ["te_review_period"] },
    });

    const lane = screen.getByTestId("player-market-lane");
    expect(within(lane).queryByText("te_review_period")).toBeNull();
    expect(within(lane).queryByText("Te review period.")).toBeNull();
    expect(
      within(lane).getByText(
        "Tight end values are under review, so treat this one as a work in progress.",
      ),
    ).toBeTruthy();
  });

  // DG-043 panel fix 2 — the static-snapshot caveat used to hardcode
  // "FantasyCalc" while marketSourceLabel() already defended against a non-
  // FantasyCalc source. The two disagreed about whether the source is knowable,
  // so a second market source would have been NAMED WRONG inside a truth-bearing
  // caveat. The sentence is now built from the lane's own source.
  it("names the caveat's market source from the data, not a hardcoded provider", () => {
    renderLanes({
      market: {
        ...market,
        source: "keeptradecut",
        caveats: ["market_overlay_static_caveat"],
      },
    });

    const lane = screen.getByTestId("player-market-lane");
    expect(within(lane).queryByText(/FantasyCalc/)).toBeNull();
    expect(
      within(lane).getByText(
        "Market values come from a saved keeptradecut snapshot, not a live feed.",
      ),
    ).toBeTruthy();
  });

  it("drops the provider name entirely rather than inventing one when source is absent", () => {
    renderLanes({
      market: {
        ...market,
        source: null,
        caveats: ["market_overlay_static_caveat"],
      },
    });

    const lane = screen.getByTestId("player-market-lane");
    expect(
      within(lane).getByText(
        "Market values come from a saved snapshot, not a live feed.",
      ),
    ).toBeTruthy();
    expect(within(lane).queryByText(/saved — snapshot/)).toBeNull();
  });

  // DG-043 panel fix 3 — an ISO stamp with NO offset is parsed as LOCAL time by
  // Date.parse but was formatted back out in UTC, shifting the calendar day. At
  // any negative UTC offset an evening stamp rendered as TOMORROW — a date the
  // viewer has not reached. The legacy refresh path forwards source_timestamp
  // verbatim, so this input is reachable.
  it("shows the source's own calendar day for an offset-less timestamp", () => {
    renderLanes({
      market: {
        ...market,
        source_timestamp: "2026-08-29T21:00:00",
        caveats: [],
      },
    });

    const lane = screen.getByTestId("player-market-lane");
    const dt = within(lane).getByText("Prices captured");
    expect(within(dt.closest("div")).getByText("Aug 29, 2026")).toBeTruthy();
    expect(within(lane).queryByText("Aug 30, 2026")).toBeNull();
  });

  it("still honours an explicit offset rather than pinning it to UTC", () => {
    renderLanes({
      market: {
        ...market,
        source_timestamp: "2026-08-29T13:00:01.968686+00:00",
        caveats: [],
      },
    });

    const lane = screen.getByTestId("player-market-lane");
    const dt = within(lane).getByText("Prices captured");
    expect(within(dt.closest("div")).getByText("Aug 29, 2026")).toBeTruthy();
  });

  it("falls back to the raw string when the timestamp cannot be parsed", () => {
    renderLanes({
      market: { ...market, source_timestamp: "not-a-date", caveats: [] },
    });

    const lane = screen.getByTestId("player-market-lane");
    const dt = within(lane).getByText("Prices captured");
    expect(within(dt.closest("div")).getByText("not-a-date")).toBeTruthy();
  });
});
