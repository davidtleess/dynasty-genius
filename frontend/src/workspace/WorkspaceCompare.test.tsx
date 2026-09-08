// @vitest-environment jsdom
// DG-187 — Compare: an available player against the man holding a roster spot.
//
// Identities and forecast totals below are the real ones from the accepted run (Flacco, Prentice,
// Rourke, Mendoza, Jeanty, McCarthy, Dell, Ali). Rank intervals for the AVAILABLE players are
// marked synthetic — the accepted run's published rank pairs I hold are for David's roster — and
// every roster rank pair here is the real one.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import type { MarketRankPlayer, MarketRanksAvailable, RankInterval } from "../lib/api";
import { auditRenderedCopy, formatRawCopyFindings } from "../lib/renderRule";
import type {
  ComparisonPayload,
  ComparisonPlayer,
} from "../research/comparisonHelpers";
import type { WorkspaceCompareProps, WorkspacePlayer } from "./types";
import { WorkspaceCompare } from "./WorkspaceCompare";

const YEARS = [2026, 2027, 2028, 2029, 2030];
const span = (start: number, end = start): RankInterval => ({ start, end, total: 388 });

function rank(over: Partial<MarketRankPlayer>): MarketRankPlayer {
  return {
    sleeper_id: "x",
    name: "X",
    position: "QB",
    team: null,
    on_roster: false,
    taxi_or_reserve: null,
    league_ownership: "available",
    model_value: 1,
    market_value: 1,
    our_rank: span(1),
    market_rank: span(1),
    model_rank_all: span(1),
    market_rank_published: 1,
    comparison: { direction: "same", gap_min: 0, gap_max: 0 },
    missing_reason: null,
    model_zero_tie: false,
    seasons: [],
    reference_player: null,
    ...over,
  };
}

function forecast(over: Partial<ComparisonPlayer>): ComparisonPlayer {
  return {
    sleeper_id: "x",
    name: "X",
    position: "QB",
    team: null,
    population: "default",
    status: "active",
    now_points: 0,
    future_points: 0,
    seasons: YEARS.map((season) => ({ season, points: 0, estimate_class: null })),
    starting_estimate: false,
    missing_reason: null,
    evidence_note: "Accepted forecast.",
    ...over,
  };
}

function player(over: Partial<WorkspacePlayer> & { id: string }): WorkspacePlayer {
  return {
    name: "X",
    position: "QB",
    team: null,
    ownership: "available",
    rank: null,
    forecast: null,
    watched: false,
    watchedAt: null,
    ...over,
  };
}

const flacco = player({
  id: "19",
  name: "Joe Flacco",
  position: "QB",
  team: "CIN",
  ownership: "available",
  // synthetic rank pair: an available-side pair is not in the numbers I hold from the accepted run
  rank: rank({
    sleeper_id: "19",
    name: "Joe Flacco",
    team: "CIN",
    our_rank: span(120),
    market_rank: span(157),
    comparison: { direction: "higher", gap_min: 37, gap_max: 37 },
  }),
  forecast: forecast({
    sleeper_id: "19",
    name: "Joe Flacco",
    team: "CIN",
    now_points: 115.32497628242587,
    future_points: 179.44179369437418,
    evidence_note: "Accepted veteran annual forecast.",
  }),
});

const prentice = player({
  id: "8025",
  name: "Adam Prentice",
  position: "RB",
  team: "DEN",
  ownership: "available",
  rank: rank({
    sleeper_id: "8025",
    name: "Adam Prentice",
    position: "RB",
    team: "DEN",
    our_rank: span(300),
    market_rank: null,
    market_value: null,
    market_rank_published: null,
    comparison: { direction: "unavailable", gap_min: null, gap_max: null },
    missing_reason: "the market snapshot carries no price for him",
  }),
  forecast: forecast({
    sleeper_id: "8025",
    name: "Adam Prentice",
    position: "RB",
    team: "DEN",
    now_points: 10.197681979436744,
    future_points: 8.545248489434728,
  }),
});

const rourke = player({
  id: "12477",
  name: "Kurtis Rourke",
  position: "QB",
  team: "SF",
  ownership: "available",
  rank: rank({
    sleeper_id: "12477",
    name: "Kurtis Rourke",
    team: "SF",
    our_rank: span(230, 388),
  }),
  forecast: forecast({
    sleeper_id: "12477",
    name: "Kurtis Rourke",
    team: "SF",
    now_points: -0.2117124292497116,
    future_points: 38.578925122738816,
    starting_estimate: true,
    seasons: [
      {
        season: 2026,
        points: -0.2117124292497116,
        estimate_class: "cold_start_candidate",
      },
      {
        season: 2027,
        points: 10.991481481481483,
        estimate_class: "baseline_research_candidate",
      },
      {
        season: 2028,
        points: 11.166796116504855,
        estimate_class: "baseline_research_candidate",
      },
      {
        season: 2029,
        points: 9.695247524752476,
        estimate_class: "baseline_research_candidate",
      },
      { season: 2030, points: 6.7254, estimate_class: "baseline_research_candidate" },
    ],
    evidence_note: "Starting estimate, not an accepted forecast.",
  }),
});

const mccarthy = player({
  id: "11565",
  name: "J.J. McCarthy",
  position: "QB",
  team: "MIN",
  ownership: "roster",
  rank: rank({
    sleeper_id: "11565",
    name: "J.J. McCarthy",
    team: "MIN",
    on_roster: true,
    league_ownership: "roster",
    our_rank: span(83),
    market_rank: span(193, 194),
    comparison: { direction: "higher", gap_min: 110, gap_max: 111 },
  }),
  forecast: forecast({
    sleeper_id: "11565",
    name: "J.J. McCarthy",
    team: "MIN",
    status: "rostered",
    now_points: 156.5816995883777,
    future_points: 832.2660448226352,
  }),
});

const jeanty = player({
  id: "12527",
  name: "Ashton Jeanty",
  position: "RB",
  team: "LV",
  ownership: "roster",
  rank: rank({
    sleeper_id: "12527",
    name: "Ashton Jeanty",
    position: "RB",
    team: "LV",
    on_roster: true,
    league_ownership: "roster",
    our_rank: span(31),
    market_rank: span(19),
    comparison: { direction: "lower", gap_min: -12, gap_max: -12 },
  }),
  forecast: forecast({
    sleeper_id: "12527",
    name: "Ashton Jeanty",
    position: "RB",
    team: "LV",
    status: "rostered",
    now_points: 300.1,
    future_points: 1200.5,
  }),
});

const ali = player({
  id: "11570",
  name: "Rasheen Ali",
  position: "RB",
  team: "BAL",
  ownership: "roster",
  rank: rank({
    sleeper_id: "11570",
    name: "Rasheen Ali",
    position: "RB",
    team: "BAL",
    on_roster: true,
    league_ownership: "roster",
    our_rank: null,
    market_rank: null,
    market_value: null,
    market_rank_published: null,
    comparison: { direction: "unavailable", gap_min: null, gap_max: null },
    missing_reason: "the market snapshot carries no price for him",
  }),
  forecast: null,
});

const elsewhere = player({
  id: "9999",
  name: "Someone Elsewhere",
  position: "WR",
  team: "KC",
  ownership: "league",
});

const players = [mccarthy, flacco, jeanty, rourke, ali, prentice, elsewhere];

const data = {
  status: "available",
  source: {
    forecast_date: "2026-09-07",
    market_as_of: "2026-09-06T13:00:02.542329+00:00",
    ownership_as_of: "2026-09-06T13:00:52.635970+00:00",
    report_run: "20260906T214512Z",
    report_sha256: "19e032a4",
    market_sha256: "05bce6dd",
    league_sha256: "ece82e24",
  },
  basis: {
    years: YEARS,
    season_weights: [0.2, 0.2, 0.2, 0.2, 0.2],
    summary:
      "Five equally weighted seasons above the best available player at his position.",
    market_proxy_note:
      "FantasyCalc stands for the broader market, not for one league mate.",
    scoring_note: "Research scoring through the championship window.",
  },
  coverage: {
    model_players: 825,
    market_players: 399,
    market_picks: 24,
    common_players: 388,
    total_players: 836,
    roster_players: 27,
    roster_common_players: 26,
  },
  rows: [],
} as unknown as MarketRanksAvailable;

const comparison: ComparisonPayload = {
  source: {
    report_run: "20260906T214512Z",
    catalog_run: "20260907T013635Z",
    report_sha256: "19e032a4",
    ownership_as_of: "2026-09-06T13:00:52.635970+00:00",
    nfl_status_as_of: "Sun, 06 Sep 2026 11:28:11 GMT",
  },
  forecast_years: YEARS,
  future_years: [2027, 2028, 2029, 2030],
  scoring_note: "Research scoring through the championship window.",
  available: [flacco, prentice, rourke].map((p) => p.forecast as ComparisonPlayer),
  roster: [mccarthy, jeanty].map((p) => p.forecast as ComparisonPlayer),
};

type Selection = WorkspaceCompareProps["selection"];

function Harness({ initial }: { initial: Selection }) {
  const [selection, setSelection] = useState<Selection>(initial);
  return (
    <WorkspaceCompare
      players={players}
      data={data}
      comparison={comparison}
      selection={selection}
      onSelect={setSelection}
    />
  );
}

const NOTHING: Selection = { availableId: null, rosterId: null };
const availableSelect = () =>
  screen.getByLabelText("Available player") as HTMLSelectElement;
const rosterSelect = () => screen.getByLabelText("Your player") as HTMLSelectElement;
const optionLabels = (select: HTMLSelectElement) =>
  Array.from(select.options).map((option) => option.textContent);
const sideFor = (name: string) =>
  screen.getByRole("group", { name: `Compare: ${name}` });

describe("WorkspaceCompare — choosing", () => {
  it("chooses nobody for you and says what the screen is for", () => {
    render(<Harness initial={NOTHING} />);
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(availableSelect().value).toBe("");
    expect(rosterSelect().value).toBe("");
    expect(screen.queryByRole("group", { name: /^Compare: / })).toBeNull();
    expect(
      screen.getByText(/Pick an available player and one of your own/),
    ).toBeTruthy();
  });

  it("offers each side its own pool, alphabetically, and nobody else's players", () => {
    render(<Harness initial={NOTHING} />);
    expect(optionLabels(availableSelect())).toEqual([
      "Choose an available player",
      "Adam Prentice · RB DEN",
      "Joe Flacco · QB CIN",
      "Kurtis Rourke · QB SF",
    ]);
    expect(optionLabels(rosterSelect())).toEqual([
      "Choose one of your players",
      "Ashton Jeanty · RB LV",
      "J.J. McCarthy · QB MIN",
      "Rasheen Ali · RB BAL",
    ]);
    // a player owned elsewhere in the league belongs to neither pool
    expect(optionLabels(availableSelect()).join(" ")).not.toContain(
      "Someone Elsewhere",
    );
    expect(optionLabels(rosterSelect()).join(" ")).not.toContain("Someone Elsewhere");
  });

  it("reports a pick without touching the other side", () => {
    const onSelect = vi.fn();
    render(
      <WorkspaceCompare
        players={players}
        data={data}
        comparison={comparison}
        selection={NOTHING}
        onSelect={onSelect}
      />,
    );
    fireEvent.change(availableSelect(), { target: { value: "19" } });
    expect(onSelect).toHaveBeenCalledWith({ availableId: "19", rosterId: null });
    fireEvent.change(rosterSelect(), { target: { value: "11565" } });
    expect(onSelect).toHaveBeenLastCalledWith({ availableId: null, rosterId: "11565" });
  });

  it("clears a side back to nobody chosen", () => {
    render(<Harness initial={{ availableId: "19", rosterId: "11565" }} />);
    expect(sideFor("Joe Flacco")).toBeTruthy();
    fireEvent.change(availableSelect(), { target: { value: "" } });
    expect(screen.queryByRole("group", { name: "Compare: Joe Flacco" })).toBeNull();
  });
});

describe("WorkspaceCompare — the two readings", () => {
  it("shows each side's rank pair and the rank disagreement from the same cohort", () => {
    render(<Harness initial={{ availableId: "19", rosterId: "11565" }} />);
    const mine = sideFor("J.J. McCarthy");
    expect(within(mine).getByText("Our rank")).toBeTruthy();
    expect(within(mine).getByText("#83")).toBeTruthy();
    expect(within(mine).getByText("Market rank")).toBeTruthy();
    expect(within(mine).getByText("#193–194")).toBeTruthy();
    expect(
      within(mine).getByText("We rank him at least 110 places higher"),
    ).toBeTruthy();
    const theirs = sideFor("Joe Flacco");
    expect(within(theirs).getByText("#120")).toBeTruthy();
    expect(within(theirs).getByText("We rank him 37 places higher")).toBeTruthy();
  });

  it("labels the forecasts as season totals for the named windows, never as a per-game rate", () => {
    const { container } = render(
      <Harness initial={{ availableId: "19", rosterId: "11565" }} />,
    );
    const theirs = sideFor("Joe Flacco");
    expect(within(theirs).getByText("2026 total")).toBeTruthy();
    expect(within(theirs).getByText("115.3")).toBeTruthy();
    expect(within(theirs).getByText("2027–2030 total")).toBeTruthy();
    expect(within(theirs).getByText("179.4")).toBeTruthy();
    expect((container.textContent ?? "").toLowerCase()).not.toContain("ppg");
    expect((container.textContent ?? "").toLowerCase()).not.toContain("per game");
  });

  it("keeps this season and the future in separate verdicts, spoken only within a position", () => {
    render(<Harness initial={{ availableId: "19", rosterId: "11565" }} />);
    const now = screen.getByRole("group", { name: "Help this season" });
    const future = screen.getByRole("group", { name: "Future potential" });
    expect(
      within(now).getByText(
        "For 2026, Joe Flacco's forecast is lower than J.J. McCarthy's by 41.3 points (115.3 vs 156.6).",
      ),
    ).toBeTruthy();
    expect(
      within(future).getByText(
        "For 2027–2030, Joe Flacco's forecast is lower than J.J. McCarthy's by 652.8 points (179.4 vs 832.3).",
      ),
    ).toBeTruthy();
  });

  it("refuses a forecast comparison across positions and says why", () => {
    render(<Harness initial={{ availableId: "19", rosterId: "12527" }} />);
    const now = screen.getByRole("group", { name: "Help this season" });
    expect(
      within(now).getByText(
        "Different positions (QB vs RB): raw point totals alone do not settle this roster choice.",
      ),
    ).toBeTruthy();
    expect(within(now).queryByText(/places (higher|lower)/)).toBeNull();
    // both totals are still shown side by side, just left uncompared
    expect(within(sideFor("Ashton Jeanty")).getByText("300.1")).toBeTruthy();
    expect(within(sideFor("Joe Flacco")).getByText("115.3")).toBeTruthy();
  });

  it("names the estimate behind a starting-estimate season instead of dressing it as a forecast", () => {
    render(<Harness initial={{ availableId: "12477", rosterId: "11565" }} />);
    const theirs = sideFor("Kurtis Rourke");
    expect(within(theirs).getByText(/draft-based starting estimate/)).toBeTruthy();
    expect(within(theirs).getByText("-0.2")).toBeTruthy();
    expect(
      within(theirs).getByText("Starting estimate, not an accepted forecast."),
    ).toBeTruthy();
  });
});

describe("WorkspaceCompare — what is missing", () => {
  it("says a rank is absent with the source's reason, and never as a zero", () => {
    render(<Harness initial={{ availableId: "8025", rosterId: "11565" }} />);
    const theirs = sideFor("Adam Prentice");
    expect(within(theirs).getByText("—")).toBeTruthy();
    expect(within(theirs).getByText("No comparable rank pair")).toBeTruthy();
    expect(
      within(theirs).getByText(/the market snapshot carries no price for him/),
    ).toBeTruthy();
    expect(within(theirs).queryByText("#0")).toBeNull();
  });

  it("says plainly when a chosen player has no forecast at all", () => {
    render(<Harness initial={{ availableId: "19", rosterId: "11570" }} />);
    expect(sideFor("Rasheen Ali")).toBeTruthy();
    const now = screen.getByRole("group", { name: "Help this season" });
    expect(
      within(now).getByText(
        "We have no forecast for Rasheen Ali, so these two cannot be compared on points.",
      ),
    ).toBeTruthy();
  });

  it("says so when a chosen player is not in the pool this screen can offer", () => {
    render(<Harness initial={{ availableId: "9999", rosterId: null }} />);
    expect(
      screen.getByText(
        "That player is not available to compare here: this screen pairs an available player with one of yours.",
      ),
    ).toBeTruthy();
    expect(screen.queryByRole("group", { name: /^Compare: / })).toBeNull();
  });
});

describe("WorkspaceCompare — reading it", () => {
  it("keeps every identity and number in step when a selection changes", () => {
    render(<Harness initial={{ availableId: "19", rosterId: "11565" }} />);
    expect(within(sideFor("J.J. McCarthy")).getByText("#83")).toBeTruthy();
    fireEvent.change(rosterSelect(), { target: { value: "12527" } });
    expect(screen.queryByRole("group", { name: "Compare: J.J. McCarthy" })).toBeNull();
    expect(screen.queryByText("#83")).toBeNull();
    expect(within(sideFor("Ashton Jeanty")).getByText("#31")).toBeTruthy();
    expect(
      within(sideFor("Ashton Jeanty")).getByText("We rank him 12 places lower"),
    ).toBeTruthy();
  });

  it("names the cohort both ranks are drawn from, so a rank is never read against the wrong total", () => {
    render(<Harness initial={{ availableId: "19", rosterId: "11565" }} />);
    expect(
      screen.getByText(
        "Both ranks are out of the 388 players our forecast and the market both cover.",
      ),
    ).toBeTruthy();
  });

  it("says the standing caveat once and gives no instruction", () => {
    const { container } = render(
      <Harness initial={{ availableId: "19", rosterId: "11565" }} />,
    );
    expect(
      screen.getAllByText(
        "Projected production; your lineup and roster needs still matter.",
      ),
    ).toHaveLength(1);
    const text = (container.textContent ?? "").toLowerCase();
    for (const forbidden of ["drop him", "trade him", "start him", "you should"]) {
      expect(text).not.toContain(forbidden);
    }
  });

  it("is operable from the keyboard through labelled native controls", () => {
    render(<Harness initial={NOTHING} />);
    for (const select of [availableSelect(), rosterSelect()]) {
      expect(select.tagName).toBe("SELECT");
      expect(select.hasAttribute("disabled")).toBe(false);
      expect(select.getAttribute("aria-hidden")).toBeNull();
    }
  });

  it("puts no raw pipeline key or shouted token on screen", () => {
    const { container } = render(
      <Harness initial={{ availableId: "12477", rosterId: "11565" }} />,
    );
    const findings = auditRenderedCopy(container);
    expect(findings, formatRawCopyFindings(findings)).toEqual([]);
  });
});
