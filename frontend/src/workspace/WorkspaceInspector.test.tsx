// @vitest-environment jsdom
// DG-199 — the Roster-first inspector (design B, approved by David 2026-09-08).
//
// These tests pin the things the imported artifact gets wrong or cannot know. B's panel shows a
// position-rank chip, a lineup role and illustrative "why" drivers with push badges; none of those exist
// in this product's data, so they are pinned absent. B also welds "of 388 paired" into the markup; the
// population is read from the payload instead. Layout is not asserted here at all — no CSS strings — the
// browser measures layout and root owns the real-surface pass.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { MarketRankPlayer, MarketRanksAvailable } from "../lib/api";
import type { ComparisonPlayer } from "../research/comparisonHelpers";
import type { WorkspacePlayer } from "./types";
import { WorkspaceInspector } from "./WorkspaceInspector";

afterEach(cleanup);

const interval = (start: number, end = start, total = 388) => ({ start, end, total });

function rankRow(over: Partial<MarketRankPlayer> = {}): MarketRankPlayer {
  return {
    sleeper_id: "1",
    name: "Alpha Adams",
    position: "WR",
    team: "BAL",
    on_roster: true,
    league_ownership: "Your roster",
    taxi_or_reserve: null,
    model_value: 300.4,
    market_value: 1233,
    our_rank: interval(230, 388),
    market_rank: interval(204),
    model_rank_all: interval(222, 222, 825),
    market_rank_published: 204,
    comparison: { direction: "lower", gap_min: -184, gap_max: -26 },
    missing_reason: null,
    model_zero_tie: false,
    seasons: [{ season: 2026, advantage: 120.5 }],
    reference_player: "Joe Flacco",
    ...over,
  };
}

function forecastRow(over: Partial<ComparisonPlayer> = {}): ComparisonPlayer {
  return {
    sleeper_id: "1",
    name: "Alpha Adams",
    position: "WR",
    team: "BAL",
    population: "default",
    status: "active",
    now_points: 240.7,
    future_points: 810.2,
    seasons: [],
    starting_estimate: false,
    missing_reason: null,
    evidence_note: "Accepted research forecast from the veteran annual forecast.",
    ...over,
  };
}

function player(over: Partial<WorkspacePlayer> = {}): WorkspacePlayer {
  return {
    id: "1",
    name: "Alpha Adams",
    position: "WR",
    team: "BAL",
    ownership: "roster",
    rank: rankRow(),
    forecast: forecastRow(),
    watched: false,
    watchedAt: null,
    ...over,
  };
}

const data: MarketRanksAvailable = {
  status: "available",
  source: {
    forecast_date: "2026-09-06",
    league_sha256: "e".repeat(64),
    market_as_of: "2026-09-06T13:00:02.542329+00:00",
    market_sha256: "b".repeat(64),
    ownership_as_of: "2026-09-06T13:00:52.635970+00:00",
    report_run: "20260906T214512Z",
    report_sha256: "a".repeat(64),
  },
  basis: {
    years: [2026, 2027, 2028, 2029, 2030],
    season_weights: [1, 1, 1, 1, 1],
    summary: "Our number adds the five seasons 2026-2030 with equal weight.",
    market_proxy_note:
      "FantasyCalc's dynasty value at your league's settings - a proxy for the wider market.",
    scoring_note: "This is not your league's exact scoring.",
  },
  coverage: {
    common_players: 388,
    market_picks: 24,
    market_players: 399,
    model_players: 825,
    roster_common_players: 26,
    roster_players: 27,
    total_players: 836,
  },
  rows: [],
};

const props = {
  data,
  nowLabel: "2026",
  futureLabel: "2027-2030",
  onWatch: () => {},
  onCompare: () => {},
  onAlternatives: () => {},
};

/** Every query scopes here. Once "Full detail" is open the reused panel contributes a second Watch and a
 *  second Compare, which is exactly why the contract asks for scoped queries. */
const actions = (name = "Alpha Adams") =>
  screen.getByRole("group", { name: `Inspector actions for ${name}` });
/** Ownership is repeated by the reused panel once "Full detail" exists in the DOM, so ownership
 *  assertions address the inspector's own identity header. */
const identity = (name = "Alpha Adams") =>
  screen.getByRole("group", { name: `${name} identity` });
/** The reused panel prints the same gap sentence, so the inspector's own copy is addressed here. */
const comparison = (name = "Alpha Adams") =>
  screen.getByRole("group", { name: `Rank comparison for ${name}` });

it("shows both rank intervals as real spans on the payload's own population", () => {
  render(<WorkspaceInspector {...props} player={player()} />);
  const ours = screen.getByRole("group", { name: "Our rank" });
  const market = screen.getByRole("group", { name: "Market rank" });
  // A tie is the span it really is. A midpoint (#309) would be a rank no player holds.
  expect(within(ours).getByText("#230–388")).toBeTruthy();
  expect(within(ours).queryAllByText("#309").length).toBe(0);
  expect(within(market).getByText("#204")).toBeTruthy();
  // The population is read, never welded in as the artifact's literal 388.
  expect(
    within(comparison()).getAllByText(/388 paired players/).length,
  ).toBeGreaterThan(0);
});

it("states the gap with the project's own arithmetic, not a recomputed one", () => {
  render(<WorkspaceInspector {...props} player={player()} />);
  // comparisonText over {direction:"lower", gap_min:-184, gap_max:-26}.
  // Scoped: the reused panel prints this same sentence, so an unscoped match would still pass if the
  // inspector stopped using the project's own arithmetic.
  expect(
    within(comparison()).getByText("We rank him at least 26 places lower"),
  ).toBeTruthy();
});

it("keeps this season and the future apart, each labelled with its own window", () => {
  render(<WorkspaceInspector {...props} player={player()} />);
  const now = screen.getByRole("group", { name: "This season 2026" });
  const future = screen.getByRole("group", { name: "Future 2027-2030" });
  expect(within(now).getByText("240.7")).toBeTruthy();
  expect(within(future).getByText("810.2")).toBeTruthy();
});

it("labels the market price in its own units and never as points", () => {
  render(<WorkspaceInspector {...props} player={player()} />);
  const value = screen.getByRole("group", { name: "FantasyCalc Market Value" });
  expect(within(value).getByText("1,233")).toBeTruthy();
  expect(within(value).getByText("market units")).toBeTruthy();
  expect(within(value).queryByText("points")).toBeNull();
  const explanation = screen.getByText(/^Season readings are projected/);
  expect(explanation.textContent).toMatch(/projected total points/);
  expect(explanation.textContent).toMatch(
    /Our rank uses five-year points above replacement/,
  );
  expect(explanation.textContent).toMatch(/market price in separate units/);
});

it("prints missing as missing, never as zero", () => {
  render(
    <WorkspaceInspector
      {...props}
      player={player({
        forecast: forecastRow({
          now_points: null,
          future_points: null,
          missing_reason: "No accepted forecast in this report.",
        }),
        rank: rankRow({ market_value: null }),
      })}
    />,
  );
  expect(
    within(screen.getByRole("group", { name: "This season 2026" })).getByText(
      "No forecast",
    ),
  ).toBeTruthy();
  expect(
    within(screen.getByRole("group", { name: "FantasyCalc Market Value" })).getByText(
      "No price",
    ),
  ).toBeTruthy();
  expect(screen.queryAllByText("0.0").length).toBe(0);
  expect(
    screen.getAllByText("No accepted forecast in this report.").length,
  ).toBeGreaterThan(0);
});

it("prints an exact zero as 0.0, distinct from missing", () => {
  render(
    <WorkspaceInspector
      {...props}
      player={player({ forecast: forecastRow({ now_points: 0 }) })}
    />,
  );
  const now = screen.getByRole("group", { name: "This season 2026" });
  expect(within(now).getByText("0.0")).toBeTruthy();
  expect(within(now).queryAllByText("No forecast").length).toBe(0);
});

it("says so explicitly when the season total is a starting estimate", () => {
  const { rerender } = render(
    <WorkspaceInspector
      {...props}
      player={player({ forecast: forecastRow({ starting_estimate: true }) })}
    />,
  );
  expect(screen.getAllByText(/starting estimate/i).length).toBeGreaterThan(0);
  rerender(<WorkspaceInspector {...props} player={player()} />);
  expect(screen.queryAllByText(/starting estimate/i).length).toBe(0);
});

it("reports ownership from the real field and labels taxi or reserve without inferring a lineup", () => {
  render(
    <WorkspaceInspector
      {...props}
      player={player({ forecast: forecastRow({ taxi_or_reserve: true }) })}
    />,
  );
  expect(within(identity()).getByText("Your roster")).toBeTruthy();
  expect(screen.getAllByText(/taxi or reserve/i).length).toBeGreaterThan(0);
  expect(screen.queryAllByText(/starter/i).length).toBe(0);
  expect(screen.queryAllByText(/QB1|WR1|RB1|flex/i).length).toBe(0);
});

it("carries the three actions for an owned player and calls back with him", () => {
  const onWatch = vi.fn();
  const onCompare = vi.fn();
  const onAlternatives = vi.fn();
  const subject = player();
  render(
    <WorkspaceInspector
      {...props}
      player={subject}
      onWatch={onWatch}
      onCompare={onCompare}
      onAlternatives={onAlternatives}
    />,
  );
  const group = actions();
  fireEvent.click(within(group).getByRole("button", { name: /^Watch Alpha Adams$/ }));
  fireEvent.click(within(group).getByRole("button", { name: /^Compare Alpha Adams/ }));
  fireEvent.click(
    within(group).getByRole("button", { name: /Find an alternative at WR/ }),
  );
  expect(onWatch).toHaveBeenCalledWith(subject);
  expect(onCompare).toHaveBeenCalledWith(subject);
  expect(onAlternatives).toHaveBeenCalledWith(subject);
});

it("offers an alternative only for a player you own, and compare only where he can sit", () => {
  const { rerender } = render(
    <WorkspaceInspector {...props} player={player({ ownership: "available" })} />,
  );
  expect(
    within(actions()).queryByRole("button", { name: /Find an alternative/ }),
  ).toBeNull();
  expect(within(actions()).getByRole("button", { name: /^Compare/ })).toBeTruthy();

  rerender(
    <WorkspaceInspector
      {...props}
      player={player({
        ownership: "league",
        // A served handle the fallback map cannot invent, so this assertion fails the moment the
        // component stops reading the real ownership field.
        rank: rankRow({ on_roster: false, league_ownership: "Rostered by Dseidman" }),
      })}
    />,
  );
  expect(within(actions()).queryByRole("button", { name: /^Compare/ })).toBeNull();
  expect(
    within(actions()).queryByRole("button", { name: /Find an alternative/ }),
  ).toBeNull();
  expect(within(identity()).getByText("Rostered by Dseidman")).toBeTruthy();
});

it("keeps its own actions unambiguous once the full-detail panel is open", () => {
  render(<WorkspaceInspector {...props} player={player()} />);
  fireEvent.click(screen.getByText("Full detail"));
  // The reused panel brings a second Watch and a second Compare to the page.
  expect(screen.getAllByRole("button", { name: /^Watch Alpha Adams$/ }).length).toBe(2);
  // Scoped to the inspector's own group there is still exactly one of each.
  const group = actions();
  expect(
    within(group).getAllByRole("button", { name: /^Watch Alpha Adams$/ }).length,
  ).toBe(1);
  expect(
    within(group).getAllByRole("button", { name: /^Compare Alpha Adams/ }).length,
  ).toBe(1);
});

it("keeps the detailed basis inside the one expansion, and invents no drivers anywhere", () => {
  render(<WorkspaceInspector {...props} player={player()} />);
  // The compact view carries interpretation, not the basis wall: the forecast note is not repeated
  // beside the comparison, it lives in "Full detail".
  fireEvent.click(screen.getByText("Full detail"));
  expect(
    screen.getAllByText("Accepted research forecast from the veteran annual forecast.")
      .length,
  ).toBe(1);
  expect(
    screen.getAllByText(/does not include player-specific reasons/i).length,
  ).toBeGreaterThan(0);
  // The artifact's illustrative factor block must not appear.
  expect(screen.queryAllByText(/ILLUSTRATIVE FACTORS/i).length).toBe(0);
  expect(screen.queryAllByText(/pushes (up|down)/i).length).toBe(0);
});

it("still identifies a player who carries no rank at all, without inventing one", () => {
  render(
    <WorkspaceInspector
      {...props}
      player={player({ rank: null, ownership: "roster" })}
    />,
  );
  expect(screen.getAllByText("Alpha Adams").length).toBeGreaterThan(0);
  expect(
    within(comparison()).getAllByText(/no comparable rank pair/i).length,
  ).toBeGreaterThan(0);
  expect(screen.queryAllByText(/#\d/).length).toBe(0);
  expect(within(identity()).getByText("Your roster")).toBeTruthy();
});

it("names our own board rank against its own population, never as a position rank", () => {
  render(<WorkspaceInspector {...props} player={player()} />);
  expect(
    within(comparison()).getAllByText(/#222 of 825 on our own board/).length,
  ).toBeGreaterThan(0);
  expect(screen.queryAllByText(/WR\s*#?\d+\b/).length).toBe(0);
});

it("does not claim a pair when only one side carries a rank", () => {
  render(
    <WorkspaceInspector
      {...props}
      player={player({
        rank: rankRow({
          market_rank: null,
          comparison: { direction: "unavailable", gap_min: null, gap_max: null },
        }),
      })}
    />,
  );
  const block = comparison();
  expect(within(block).queryAllByText(/Both ranks are places/).length).toBe(0);
  expect(within(block).getAllByText(/No comparable rank pair/).length).toBeGreaterThan(
    0,
  );
});
