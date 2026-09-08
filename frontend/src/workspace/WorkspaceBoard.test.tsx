// @vitest-environment jsdom
// DG-188 — the workspace board: a dense row per player whose every number is a RANK over the one cohort both
// sides cover. The imported design put "Our value" and "Market" side by side as numbers; those are five-year
// points above replacement and a FantasyCalc price, which are not comparable, so the dense row carries the
// comparable reading and the panel carries the values with their units.
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { MarketRankPlayer, MarketRanksAvailable } from "../lib/api";
import type { ComparisonPlayer } from "../research/comparisonHelpers";
import type { WorkspaceBoardProps, WorkspacePlayer } from "./types";
import { WorkspaceBoard } from "./WorkspaceBoard";

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
    our_rank: interval(10),
    market_rank: interval(40),
    model_rank_all: interval(12, 12, 825),
    market_rank_published: 41,
    comparison: { direction: "higher", gap_min: 30, gap_max: 30 },
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

const boardProps = {
  data,
  nowLabel: "2026",
  futureLabel: "2027–2030",
  onWatch: () => {},
  onCompare: () => {},
};

function renderBoard(rows: WorkspacePlayer[], over: Partial<WorkspaceBoardProps> = {}) {
  return render(<WorkspaceBoard rows={rows} {...boardProps} {...over} />);
}

// The row control's accessible name opens with the player's own name; the panel's actions read "Watch <name>" and
// "Compare <name>", so anchoring at the start keeps this helper pointed at the row even while a panel is open.
function rowButton(name: string) {
  return screen.getByRole("button", { name: new RegExp(`^${name},`) });
}

// --- the dense row -------------------------------------------------------------------------------

it("labels the two columns as ranks and carries each label exactly once", () => {
  const { container } = renderBoard([player()]);
  const header = container.querySelector(".dg-workspace-board__head");
  expect(header).toBeTruthy();
  expect(header?.textContent).toContain("Ours");
  expect(header?.textContent).toContain("Market");
  expect(header?.textContent).toMatch(/gap \(places\)/i);
  // the label lives in the header once, never repeated on every row
  expect(screen.getAllByText("Ours")).toHaveLength(1);
  expect(screen.getAllByText("Market")).toHaveLength(1);
});

it("shows both ranks and the guaranteed gap, and never a market price on the dense row", () => {
  renderBoard([player()]);
  const row = rowButton("Alpha Adams");
  expect(within(row).getByText("#10")).toBeTruthy();
  expect(within(row).getByText("#40")).toBeTruthy();
  expect(row.textContent).not.toContain("5000"); // the FantasyCalc price is not a comparable reading
  expect(row.textContent).not.toContain("300"); // nor is our points total
  expect(row.getAttribute("aria-label")).toMatch(/30 places higher/);
});

it("renders the rows in the order given and never re-sorts them", () => {
  renderBoard([
    player({
      id: "3",
      name: "Charlie Cross",
      rank: rankRow({ sleeper_id: "3", our_rank: interval(300) }),
    }),
    player({ id: "1", name: "Alpha Adams" }),
    player({
      id: "2",
      name: "Bravo Bell",
      rank: rankRow({ sleeper_id: "2", our_rank: interval(2) }),
    }),
  ]);
  const names = screen
    .getAllByRole("button", { name: /Cross|Adams|Bell/ })
    .map((b) => b.textContent ?? "");
  expect(names[0]).toContain("Charlie Cross");
  expect(names[1]).toContain("Alpha Adams");
  expect(names[2]).toContain("Bravo Bell");
});

it("shows a tied rank as its shared interval rather than inventing an order", () => {
  renderBoard([
    player({ rank: rankRow({ our_rank: interval(230, 388), model_zero_tie: true }) }),
  ]);
  expect(within(rowButton("Alpha Adams")).getByText("#230–388")).toBeTruthy();
});

it("names a missing market price as missing rather than showing a zero", () => {
  renderBoard([
    player({
      rank: rankRow({
        market_value: null,
        market_rank: null,
        market_rank_published: null,
        comparison: { direction: "unavailable", gap_min: null, gap_max: null },
      }),
    }),
  ]);
  const row = rowButton("Alpha Adams");
  expect(within(row).getByText(/no price/i)).toBeTruthy();
  expect(row.textContent).not.toMatch(/\b0\b/);
});

// --- expansion -----------------------------------------------------------------------------------

it("expands a row into the panel and marks the control expanded", () => {
  renderBoard([player()]);
  const row = rowButton("Alpha Adams");
  expect(row.getAttribute("aria-expanded")).toBe("false");
  expect(screen.queryByRole("region", { name: /Alpha Adams/ })).toBeNull();
  fireEvent.click(row);
  expect(row.getAttribute("aria-expanded")).toBe("true");
  const panel = screen.getByRole("region", { name: /Alpha Adams/ });
  expect(row.getAttribute("aria-controls")).toBe(panel.id);
});

it("keeps exactly one row open, including when different players are expanded rapidly", () => {
  renderBoard([
    player(),
    player({
      id: "2",
      name: "Bravo Bell",
      rank: rankRow({ sleeper_id: "2" }),
      forecast: forecastRow({ sleeper_id: "2", name: "Bravo Bell" }),
    }),
    player({
      id: "3",
      name: "Charlie Cross",
      rank: rankRow({ sleeper_id: "3" }),
      forecast: forecastRow({ sleeper_id: "3", name: "Charlie Cross" }),
    }),
  ]);
  fireEvent.click(rowButton("Alpha Adams"));
  fireEvent.click(rowButton("Bravo Bell"));
  fireEvent.click(rowButton("Charlie Cross"));
  expect(screen.getAllByRole("region", { name: /versus the market/ })).toHaveLength(1);
  expect(screen.getByRole("region", { name: /Charlie Cross/ })).toBeTruthy();
  expect(rowButton("Alpha Adams").getAttribute("aria-expanded")).toBe("false");
  expect(rowButton("Bravo Bell").getAttribute("aria-expanded")).toBe("false");
});

it("closes the open row when it is activated again", () => {
  renderBoard([player()]);
  fireEvent.click(rowButton("Alpha Adams"));
  fireEvent.click(rowButton("Alpha Adams"));
  expect(screen.queryByRole("region", { name: /Alpha Adams/ })).toBeNull();
});

it("puts no interactive control inside the row control", () => {
  renderBoard([player()]);
  const row = rowButton("Alpha Adams");
  fireEvent.click(row);
  for (const role of ["button", "link", "checkbox", "textbox"] as const) {
    expect(within(row).queryAllByRole(role)).toHaveLength(0);
  }
  // the panel is a sibling of the control, never nested inside it
  expect(row.contains(screen.getByRole("region", { name: /Alpha Adams/ }))).toBe(false);
});

// --- rows the sources could not fully cover -------------------------------------------------------

it("still renders, expands and watches a player with no rank and no forecast", () => {
  const onWatch = vi.fn();
  const stranger = player({
    id: "9",
    name: "India Ivey",
    rank: null,
    forecast: null,
    ownership: "unknown",
  });
  renderBoard([stranger], { onWatch });
  const row = rowButton("India Ivey");
  expect(row).toBeTruthy();
  fireEvent.click(row);
  expect(screen.getByRole("region", { name: /India Ivey/ })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Watch India Ivey" }));
  expect(onWatch).toHaveBeenCalledWith(stranger);
});

it("falls back to initials rather than painting a broken headshot", () => {
  renderBoard([player()]);
  const image = screen.getByAltText("Alpha Adams");
  expect(image.getAttribute("src")).toBe("/assets/headshots/1.jpg");
  fireEvent.error(image);
  expect(screen.getByLabelText("Alpha Adams headshot unavailable")).toBeTruthy();
  expect(screen.queryByAltText("Alpha Adams")).toBeNull();
});

it("renders a designed empty state rather than a bare table with no rows", () => {
  renderBoard([]);
  expect(screen.getByText(/no players match/i)).toBeTruthy();
});

// --- root's DG-186 review: a bound must not be printed as a measurement ------------------------------

it("marks a gap derived from overlapping tie ranges as a bound, not an exact number", () => {
  renderBoard([
    player({
      rank: rankRow({
        comparison: { direction: "higher", gap_min: 110, gap_max: 111 },
      }),
    }),
  ]);
  const row = rowButton("Alpha Adams");
  expect(within(row).getByText("≥+110")).toBeTruthy();
  expect(row.getAttribute("aria-label")).toMatch(/at least 110 places higher/);
});

it("prints a bare number only when both ranks are exact", () => {
  renderBoard([player()]); // gap_min === gap_max === 30
  expect(within(rowButton("Alpha Adams")).getByText("+30")).toBeTruthy();
});

it("bounds a lower verdict downward", () => {
  renderBoard([
    player({
      rank: rankRow({ comparison: { direction: "lower", gap_min: -70, gap_max: -68 } }),
    }),
  ]);
  expect(within(rowButton("Alpha Adams")).getByText("≤−68")).toBeTruthy();
});

it.each([
  {
    order: "now" as const,
    now: 0.004,
    future: 12,
    estimate: true,
    expected: "2026: 0.004 points · starting estimate",
    ranked: false,
  },
  {
    order: "future" as const,
    now: 12,
    future: 0.2,
    estimate: false,
    expected: "2027–2030: 0.2 points",
    ranked: true,
  },
  {
    order: "now" as const,
    now: 0,
    future: 0,
    estimate: false,
    expected: "2026: 0.0 points",
    ranked: true,
  },
  {
    order: "future" as const,
    now: 12,
    future: null,
    estimate: false,
    expected: "2027–2030: no forecast",
    ranked: false,
  },
])("announces the visible forecast sort key and estimate caveat: $expected", ({
  order,
  now,
  future,
  estimate,
  expected,
  ranked,
}) => {
  renderBoard(
    [
      player({
        rank: ranked ? rankRow() : null,
        forecast: forecastRow({
          now_points: now,
          future_points: future,
          starting_estimate: estimate,
        }),
      }),
    ],
    { order },
  );
  const row = rowButton("Alpha Adams");
  expect(within(row).getByText(expected)).toBeTruthy();
  expect(row.getAttribute("aria-label")).toContain(expected);
});
