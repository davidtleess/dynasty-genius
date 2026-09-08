// @vitest-environment jsdom
// DG-188 — the expanded player panel: David's four ideas kept recognizably separate, each carrying its own unit.
//
// The imported design's panel ends with "Our score is published in the market's own units so the two are
// subtractable. Rank is the supporting reading, not the price." That is false for this product — our number is
// five-year points above replacement and the market's is a FantasyCalc price — so these tests pin the opposite,
// and pin that the sample's position ranks and lineup-slot label never appear, because no such data exists.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { MarketRankPlayer, MarketRanksAvailable } from "../lib/api";
import type { ComparisonPlayer } from "../research/comparisonHelpers";
import type { WorkspacePlayer } from "./types";
import { WorkspacePlayerPanel } from "./WorkspacePlayerPanel";

afterEach(cleanup);

const interval = (start: number, end = start, total = 388) => ({ start, end, total });

function rankRow(over: Partial<MarketRankPlayer> = {}): MarketRankPlayer {
  return {
    sleeper_id: "1",
    name: "Alpha Adams",
    position: "QB",
    team: "KC",
    on_roster: false,
    league_ownership: "Available",
    taxi_or_reserve: null,
    model_value: 300.4,
    market_value: 5000,
    our_rank: interval(83),
    market_rank: interval(193, 194),
    model_rank_all: interval(83, 83, 825),
    market_rank_published: 193,
    comparison: { direction: "higher", gap_min: 110, gap_max: 111 },
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
    position: "QB",
    team: "KC",
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
    position: "QB",
    team: "KC",
    ownership: "available",
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
    summary: "Our number adds the five seasons 2026–2030 with equal weight.",
    market_proxy_note:
      "FantasyCalc's dynasty value at your league's settings — a proxy for the wider market.",
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
  futureLabel: "2027–2030",
  onWatch: () => {},
  onCompare: () => {},
};

function renderPanel(over: Partial<typeof props> & { player?: WorkspacePlayer } = {}) {
  const { player: subject = player(), ...rest } = over;
  return render(<WorkspacePlayerPanel player={subject} {...props} {...rest} />);
}

// --- the answer first ----------------------------------------------------------------------------

it("leads with the paired ranks and says the two cover the same players", () => {
  renderPanel();
  const answer = screen.getByRole("region", { name: /Alpha Adams/ });
  expect(within(answer).getByText("#83")).toBeTruthy();
  expect(within(answer).getByText("#193–194")).toBeTruthy();
  expect(answer.textContent).toMatch(/same 388 players/);
  expect(answer.textContent).toMatch(/We rank him at least 110 places higher/);
});

it("states that the two numbers are not in the same units and a rank gap is not a price", () => {
  renderPanel();
  const text = screen.getByRole("region", { name: /Alpha Adams/ }).textContent ?? "";
  expect(text).toMatch(/different units/i);
  expect(text).toMatch(/not a (trade )?price/i);
  expect(text).not.toMatch(/subtractable/i); // the imported sample's false claim
});

it("reads a shared zero tie as an overlap and explains the shared interval", () => {
  renderPanel({
    player: player({
      rank: rankRow({
        model_value: 0,
        model_zero_tie: true,
        our_rank: interval(230, 388),
        market_rank: interval(300),
        comparison: { direction: "overlap", gap_min: -88, gap_max: 70 },
      }),
    }),
  });
  const text = screen.getByRole("region", { name: /Alpha Adams/ }).textContent ?? "";
  expect(text).toMatch(/overlap/i);
  expect(text).toMatch(/#230–388/);
  expect(text).toMatch(/tied|share/i);
  expect(text).not.toMatch(/places higher|places lower/);
});

it("quotes only the guaranteed magnitude when the two intervals are disjoint", () => {
  renderPanel();
  expect(screen.getByRole("region", { name: /Alpha Adams/ }).textContent).toMatch(
    /at least 110 places higher/,
  );
});

it("names a missing market price as missing rather than zero", () => {
  renderPanel({
    player: player({
      rank: rankRow({
        market_value: null,
        market_rank: null,
        market_rank_published: null,
        comparison: { direction: "unavailable", gap_min: null, gap_max: null },
      }),
    }),
  });
  const text = screen.getByRole("region", { name: /Alpha Adams/ }).textContent ?? "";
  expect(text).toMatch(/no price carried/i);
  expect(text).toMatch(/missing, not zero/i);
});

// --- the four ideas, each with its own unit --------------------------------------------------------

it("keeps the four ideas recognizable and labels each number with its own unit", () => {
  renderPanel();
  const ideas = screen.getByRole("list", { name: /four/i });
  const items = within(ideas).getAllByRole("listitem");
  expect(items).toHaveLength(4);
  const idea = (position: number) => items[position] as HTMLElement;
  const [football, dynasty, market, situation] = [idea(0), idea(1), idea(2), idea(3)];

  expect(football.textContent).toMatch(/Football forecast/);
  expect(football.textContent).toMatch(/240\.7/); // the total, at the board's own precision
  expect(football.textContent).toMatch(/total points/i);
  expect(football.textContent).toMatch(/2026/);
  expect(football.textContent).not.toMatch(/\bppg\b/i); // the number is a season total, never a rate

  expect(dynasty.textContent).toMatch(/Dynasty valuation/);
  expect(dynasty.textContent).toMatch(/300/); // model_value
  expect(dynasty.textContent).toMatch(/five-year points above replacement/i);

  expect(market.textContent).toMatch(/Market valuation/);
  expect(market.textContent).toMatch(/5,?000/); // market_value
  expect(market.textContent).toMatch(/FantasyCalc Market Value/);

  expect(situation.textContent).toMatch(/Your situation/);
  expect(situation.textContent).toMatch(/Available/);
});

it("says only what the sources carry about the roster spot and never a lineup role", () => {
  renderPanel({
    player: player({
      ownership: "roster",
      rank: rankRow({
        on_roster: true,
        league_ownership: "Your roster",
        taxi_or_reserve: true,
      }),
    }),
  });
  const situation = within(screen.getByRole("list", { name: /four/i })).getAllByRole(
    "listitem",
  )[3] as HTMLElement;
  expect(situation.textContent).toMatch(/Your roster/);
  expect(situation.textContent).toMatch(/taxi|injured reserve/i);
  expect(situation.textContent).not.toMatch(
    /starter|start him|flex|lineup|bench slot/i,
  );
});

it("shows neither a position rank nor a completeness or age-cliff claim, because no such data exists", () => {
  renderPanel();
  const text = screen.getByRole("region", { name: /Alpha Adams/ }).textContent ?? "";
  expect(text).not.toMatch(/QB\d|RB\d|WR\d|TE\d/);
  expect(text).not.toMatch(/age cliff|completeness|confidence/i);
});

// --- this season versus later, and the limits ------------------------------------------------------

it("separates the current season from the future years and calls both totals", () => {
  renderPanel();
  const horizon = screen.getByRole("group", { name: /this season/i });
  expect(horizon.textContent).toMatch(/2026/);
  expect(horizon.textContent).toMatch(/240\.7/);
  expect(horizon.textContent).toMatch(/2027–2030/);
  expect(horizon.textContent).toMatch(/810\.2/);
  expect(horizon.textContent).toMatch(/summed|total/i);
});

it("builds the limits from the payload rather than from a sample", () => {
  renderPanel({
    player: player({
      rank: rankRow({
        model_zero_tie: true,
        model_value: 0,
        our_rank: interval(230, 388),
      }),
      forecast: forecastRow({
        starting_estimate: true,
        missing_reason: "2030 forecast missing: future total undefined, not zero",
        evidence_note: "Starting estimate, not an accepted forecast.",
      }),
    }),
  });
  const limits = screen.getByRole("list", { name: /limits/i });
  const text = limits.textContent ?? "";
  expect(text).toMatch(/2030 forecast missing/);
  expect(text).toMatch(/Starting estimate/);
  expect(text).toMatch(/at or below replacement/i);
  expect(text).toMatch(/does not distinguish/i);
  expect(text).not.toMatch(/tied at exactly zero/i);
});

it("puts the dated sources behind a disclosure built from the payload", () => {
  renderPanel();
  const details = screen.getByRole("group", { name: /how these numbers were made/i });
  fireEvent.click(within(details).getByText(/how these numbers were made/i));
  const text = details.textContent ?? "";
  expect(text).toMatch(/equal weight/); // basis.summary
  expect(text).toMatch(/proxy for the wider market/); // basis.market_proxy_note
  expect(text).toMatch(/not your league's exact scoring/); // basis.scoring_note
  expect(text).toMatch(/Sep 6, 2026/); // the dates, humanised
  expect(text).not.toMatch(/[0-9a-f]{16}/); // no hashes in the reading surface
});

// --- the actions ------------------------------------------------------------------------------------

it("offers watch as a labelled native button and reports the player back", () => {
  const onWatch = vi.fn();
  const subject = player();
  renderPanel({ player: subject, onWatch });
  const watch = screen.getByRole("button", { name: "Watch Alpha Adams" });
  expect(watch.tagName).toBe("BUTTON");
  fireEvent.click(watch);
  expect(onWatch).toHaveBeenCalledWith(subject);
});

it("offers unwatch when he is already on the watchlist", () => {
  renderPanel({ player: player({ watched: true }) });
  expect(screen.getByRole("button", { name: "Unwatch Alpha Adams" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Watch Alpha Adams" })).toBeNull();
});

it("offers compare for an available player and reports him back", () => {
  const onCompare = vi.fn();
  const subject = player();
  renderPanel({ player: subject, onCompare });
  fireEvent.click(screen.getByRole("button", { name: "Compare Alpha Adams" }));
  expect(onCompare).toHaveBeenCalledWith(subject);
});

it("offers compare for a player on the roster without calling him available", () => {
  renderPanel({
    player: player({
      ownership: "roster",
      rank: rankRow({ on_roster: true, league_ownership: "Your roster" }),
    }),
  });
  expect(screen.getByRole("button", { name: "Compare Alpha Adams" })).toBeTruthy();
  const actions = screen.getByRole("group", { name: /actions/i });
  expect(actions.textContent).not.toMatch(/available/i);
});

it("offers no compare for a player another team owns", () => {
  renderPanel({
    player: player({
      ownership: "league",
      rank: rankRow({ league_ownership: "Rostered by another team" }),
    }),
  });
  expect(screen.queryByRole("button", { name: /^Compare/ })).toBeNull();
  expect(screen.getByRole("button", { name: "Watch Alpha Adams" })).toBeTruthy();
});

it("still offers compare when the points are missing but the identity is usable", () => {
  renderPanel({
    player: player({
      forecast: forecastRow({
        now_points: null,
        future_points: null,
        missing_reason: "unpriced",
      }),
    }),
  });
  expect(screen.getByRole("button", { name: "Compare Alpha Adams" })).toBeTruthy();
});

it("still watches a player the sources could not cover at all", () => {
  const onWatch = vi.fn();
  const stranger = player({
    id: "9",
    name: "India Ivey",
    rank: null,
    forecast: null,
    ownership: "unknown",
  });
  renderPanel({ player: stranger, onWatch });
  expect(screen.getByRole("region", { name: /India Ivey/ }).textContent).toMatch(
    /no comparable ranking/i,
  );
  fireEvent.click(screen.getByRole("button", { name: "Watch India Ivey" }));
  expect(onWatch).toHaveBeenCalledWith(stranger);
  expect(screen.queryByRole("button", { name: /^Compare/ })).toBeNull();
});

// --- root's DG-186 review, 2026-09-07: the axis must not flatter a lone player into a wide tie ------

it("draws each rank interval at its true share of the axis, never padded to a visible minimum", () => {
  const { container } = renderPanel({
    player: player({
      rank: rankRow({ our_rank: interval(83), market_rank: interval(230, 388) }),
    }),
  });
  const marks = [
    ...container.querySelectorAll(".dg-workspace-panel__mark"),
  ] as HTMLElement[];
  expect(marks).toHaveLength(2);
  expect(marks[0]?.style.width).toBe("0.258%"); // one player of 388
  expect(marks[0]?.style.left).toContain("21.134%");
  expect(marks[1]?.style.width).toBe("40.979%"); // the 159-wide zero tie, ~159x wider on screen
  expect(marks[1]?.style.left).toContain("59.021%");
  for (const mark of marks) expect(mark.style.width).not.toBe("50.000%");
});

it("captions the axis so a mark's position and width can be read at all", () => {
  renderPanel();
  const text = screen.getByRole("region", { name: /Alpha Adams/ }).textContent ?? "";
  expect(text).toMatch(/Best rank at the left/);
  expect(text).toMatch(/#1 through #388/);
  expect(text).toMatch(/lower number is better/i);
  expect(text).toMatch(/minimum visible width/i);
  expect(text).toMatch(/printed ranks/i);
});

it("keeps a player we forecast but the market does not price on our own board", () => {
  renderPanel({
    player: player({
      rank: rankRow({
        market_value: null,
        market_rank: null,
        market_rank_published: null,
        comparison: { direction: "unavailable", gap_min: null, gap_max: null },
      }),
    }),
  });
  const text = screen.getByRole("region", { name: /Alpha Adams/ }).textContent ?? "";
  expect(text).toMatch(/Primary paired ranks cover the 388/);
  expect(text).toMatch(/Our own board ranks 825/);
});

it("never prints a small positive total as a zero", () => {
  renderPanel({
    player: player({
      rank: rankRow({ model_value: 0 }),
      forecast: forecastRow({ now_points: 0.2, future_points: 0 }),
    }),
  });
  const ideas = within(screen.getByRole("list", { name: /four/i })).getAllByRole(
    "listitem",
  );
  expect((ideas[0] as HTMLElement).textContent).toMatch(/0\.2/); // a real, tiny forecast
  expect((ideas[1] as HTMLElement).textContent).toMatch(/0\.0/); // a real, exact zero
});
