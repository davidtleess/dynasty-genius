// @vitest-environment jsdom
// DG-198 — the roster board grouped by position (direction B).
//
// The design source carried three numbers this product cannot honestly print: a position-rank chip,
// a QB1/QB2 starter slot, and a "starts two" lineup rule. None of them exist in our payload, so none
// of them is rendered, and the tests below pin their absence as deliberately as they pin what is
// shown. What IS shown is a rank from us, a rank from the market over the same cohort, the gap in
// places, and the two season totals in their own units.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { MarketRankPlayer, MarketRanksAvailable } from "../lib/api";
import { auditRenderedCopy, formatRawCopyFindings } from "../lib/renderRule";
import type { ComparisonPlayer } from "../research/comparisonHelpers";
import type { WorkspacePlayer } from "./types";
import {
  WorkspaceRosterGroups,
  type WorkspaceRosterGroupsProps,
} from "./WorkspaceRosterGroups";

afterEach(cleanup);

const interval = (start: number, end = start, total = 388) => ({ start, end, total });

function rankRow(over: Partial<MarketRankPlayer> = {}): MarketRankPlayer {
  return {
    sleeper_id: "1",
    name: "Alpha Adams",
    position: "QB",
    team: "KC",
    on_roster: true,
    league_ownership: "Your roster",
    taxi_or_reserve: false,
    model_value: 300.4,
    market_value: 5000,
    our_rank: interval(10),
    market_rank: interval(40),
    model_rank_all: interval(12, 12, 825),
    market_rank_published: 41,
    comparison: { direction: "higher", gap_min: 30, gap_max: 30 },
    missing_reason: null,
    model_zero_tie: false,
    seasons: [],
    reference_player: null,
    ...over,
  };
}

function forecastRow(over: Partial<ComparisonPlayer> = {}): ComparisonPlayer {
  return {
    sleeper_id: "1",
    name: "Alpha Adams",
    position: "QB",
    team: "KC",
    population: "owned",
    status: "active",
    now_points: 100,
    future_points: 400,
    seasons: [],
    starting_estimate: false,
    missing_reason: null,
    evidence_note: "Accepted forecast",
    ...over,
  };
}

function player(over: Partial<WorkspacePlayer> = {}): WorkspacePlayer {
  const id = over.id ?? "1";
  const name = over.name ?? `Player ${id}`;
  const position = over.position ?? "QB";
  return {
    id,
    name,
    position,
    team: "KC",
    ownership: "roster",
    rank: rankRow({ sleeper_id: id, name, position }),
    forecast: forecastRow({ sleeper_id: id, name, position }),
    watched: false,
    watchedAt: null,
    ...over,
  };
}

const data: MarketRanksAvailable = {
  status: "available",
  source: {
    report_run: "run",
    report_sha256: "hash",
    market_sha256: "market",
    league_sha256: "league",
    forecast_date: "2026-09-06",
    market_as_of: "2026-09-06T13:00:00Z",
    ownership_as_of: "2026-09-06T13:01:00Z",
  },
  basis: {
    years: [2026, 2027],
    season_weights: [1, 1],
    summary: "Two seasons above replacement",
    market_proxy_note: "FantasyCalc is the broad market.",
    scoring_note:
      "12-team Superflex, full PPR, no TE premium; championship through Week 17.",
  },
  coverage: {
    model_players: 3,
    market_players: 3,
    market_picks: 0,
    common_players: 3,
    total_players: 3,
    roster_players: 1,
    roster_common_players: 1,
  },
  rows: [],
};

function renderGroups(over: Partial<WorkspaceRosterGroupsProps> = {}) {
  // The spies are returned as themselves rather than read back off the props, so their call
  // records stay typed and a test cannot accidentally assert against an overridden handler.
  const onSelect = vi.fn<(p: WorkspacePlayer) => void>();
  const onWatch = vi.fn<(p: WorkspacePlayer) => void>();
  const onFindAlternatives = vi.fn<(position: string) => void>();
  const props: WorkspaceRosterGroupsProps = {
    rows: [player()],
    data,
    nowLabel: "2026",
    futureLabel: "2027–2030",
    order: "ours",
    selectedId: null,
    onSelect,
    onWatch,
    onFindAlternatives,
    ...over,
  };
  return {
    ...render(<WorkspaceRosterGroups {...props} />),
    onSelect,
    onWatch,
    onFindAlternatives,
  };
}

/** Every row is a native button; this is how the tests read the board without guessing at markup. */
function rowLabels(): string[] {
  return screen
    .queryAllByRole("button")
    .filter((b) => b.classList.contains("dg-roster-groups__row"))
    .map((b) => b.getAttribute("aria-label") ?? "");
}

describe("WorkspaceRosterGroups — nobody disappears", () => {
  it("renders every player exactly once, including an unexpected position", () => {
    const rows = [
      player({ id: "qb", name: "Quinn Quarter", position: "QB" }),
      player({ id: "rb", name: "Rhea Rush", position: "RB" }),
      player({ id: "wr", name: "Wes Wide", position: "WR" }),
      player({ id: "te", name: "Tess Tight", position: "TE" }),
      player({ id: "k", name: "Kip Kicker", position: "K" }),
      player({ id: "dst", name: "Dana Def", position: "DEF" }),
    ];
    renderGroups({ rows });
    const labels = rowLabels();
    expect(labels).toHaveLength(rows.length);
    for (const row of rows) {
      expect(labels.filter((l) => l.startsWith(row.name))).toHaveLength(1);
    }
  });

  it("orders the known positions first and keeps any other position after them", () => {
    const rows = [
      player({ id: "k", name: "Kip Kicker", position: "K" }),
      player({ id: "te", name: "Tess Tight", position: "TE" }),
      player({ id: "qb", name: "Quinn Quarter", position: "QB" }),
      player({ id: "wr", name: "Wes Wide", position: "WR" }),
      player({ id: "rb", name: "Rhea Rush", position: "RB" }),
    ];
    const { container } = renderGroups({ rows });
    const labels = Array.from(
      container.querySelectorAll(".dg-roster-groups__group-label"),
      (n) => n.textContent,
    );
    expect(labels).toEqual([
      "Quarterbacks",
      "Running backs",
      "Wide receivers",
      "Tight ends",
      "K",
    ]);
  });

  it("renders an empty roster without inventing a statistic", () => {
    const { container } = renderGroups({ rows: [] });
    expect(rowLabels()).toHaveLength(0);
    expect(container.textContent).toContain("No players");
    expect(container.textContent).not.toContain("0.0");
  });
});

describe("WorkspaceRosterGroups — order inside a group", () => {
  it("follows the asked order and keeps players it cannot order below, with a visible label", () => {
    const rows = [
      player({
        id: "c",
        name: "Carl Third",
        rank: rankRow({ our_rank: interval(30) }),
      }),
      player({ id: "a", name: "Ann First", rank: rankRow({ our_rank: interval(10) }) }),
      player({ id: "n", name: "Ned NoRank", rank: rankRow({ our_rank: null }) }),
      player({
        id: "b",
        name: "Bea Second",
        rank: rankRow({ our_rank: interval(20) }),
      }),
    ];
    const { container } = renderGroups({ rows, order: "ours" });
    expect(rowLabels().map((l) => l.split(",")[0])).toEqual([
      "Ann First",
      "Bea Second",
      "Carl Third",
      "Ned NoRank",
    ]);
    expect(container.textContent).toContain("Not ranked in this order");
  });

  it("keeps tied players in a stable order rather than inventing a midpoint", () => {
    const tie = interval(230, 388);
    const rows = [
      player({ id: "z", name: "Zoe Tie", rank: rankRow({ our_rank: tie }) }),
      player({ id: "a", name: "Abe Tie", rank: rankRow({ our_rank: tie }) }),
    ];
    const { container } = renderGroups({ rows, order: "ours" });
    expect(rowLabels().map((l) => l.split(",")[0])).toEqual(["Abe Tie", "Zoe Tie"]);
    expect(container.textContent).toContain("#230–388");
    expect(container.textContent).not.toContain("#309");
  });
});

describe("WorkspaceRosterGroups — a group total is only as good as its coverage", () => {
  const withPoints = (id: string, now: number | null, future: number | null) =>
    player({
      id,
      name: `Player ${id}`,
      forecast: forecastRow({ sleeper_id: id, now_points: now, future_points: future }),
    });

  it("prints a season total when every player in the group carries that season", () => {
    const { container } = renderGroups({
      rows: [withPoints("a", 100, 400), withPoints("b", 50.5, 200)],
    });
    expect(container.textContent).toContain("150.5");
    expect(container.textContent).toContain("600.0");
    expect(container.textContent).not.toContain("of 2 players");
  });

  it("prints a subtotal and its coverage rather than a false full total", () => {
    const { container } = renderGroups({
      rows: [withPoints("a", 100, 400), withPoints("b", null, null)],
    });
    expect(container.textContent).toContain("100.0");
    expect(container.textContent).toContain("1 of 2 players");
  });

  it("prints no total at all when no player in the group carries the season", () => {
    const { container } = renderGroups({
      rows: [withPoints("a", null, null), withPoints("b", null, null)],
    });
    const summary = container.querySelector(".dg-roster-groups__group-summary");
    expect(summary?.textContent ?? "").not.toContain("0.0");
    expect(summary?.textContent ?? "").toContain("2");
  });

  it("shows a real zero as zero and a missing number as neither zero nor blank", () => {
    const { container } = renderGroups({
      rows: [withPoints("zero", 0, 0), withPoints("none", null, null)],
    });
    const cells = Array.from(
      container.querySelectorAll(".dg-roster-groups__now"),
      (n) => n.textContent,
    );
    expect(cells).toContain("0.0");
    expect(cells).toContain("—");
  });

  it("states the rank span of a group only from ranks it actually has", () => {
    const { container } = renderGroups({
      rows: [
        player({ id: "a", rank: rankRow({ our_rank: interval(4) }) }),
        player({ id: "b", rank: rankRow({ our_rank: interval(19) }) }),
        player({ id: "c", rank: rankRow({ our_rank: null }) }),
      ],
    });
    const summary = container.querySelector(".dg-roster-groups__group-summary");
    expect(summary?.textContent).toContain("#4–19");
  });
});

describe("WorkspaceRosterGroups — the actions carry the right player", () => {
  it("selects the row that was pressed", () => {
    const rows = [
      player({ id: "a", name: "Ann First" }),
      player({ id: "b", name: "Bea Second" }),
    ];
    const { onSelect } = renderGroups({ rows, order: "name" });
    fireEvent.click(screen.getByRole("button", { name: /^Bea Second/ }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0]?.id).toBe("b");
  });

  it("marks the selected row pressed and leaves the others unpressed", () => {
    const rows = [
      player({ id: "a", name: "Ann First" }),
      player({ id: "b", name: "Bea Second" }),
    ];
    renderGroups({ rows, selectedId: "b" });
    expect(
      screen.getByRole("button", { name: /^Bea Second/ }).getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      screen.getByRole("button", { name: /^Ann First/ }).getAttribute("aria-pressed"),
    ).toBe("false");
  });

  it("watches a player without selecting his row", () => {
    const rows = [player({ id: "a", name: "Ann First" })];
    const { onSelect, onWatch } = renderGroups({ rows });
    fireEvent.click(screen.getByRole("button", { name: /Watch Ann First/ }));
    expect(onWatch).toHaveBeenCalledTimes(1);
    expect(onWatch.mock.calls[0]?.[0]?.id).toBe("a");
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("never nests one button inside another", () => {
    const { container } = renderGroups({ rows: [player()] });
    for (const button of Array.from(container.querySelectorAll("button"))) {
      expect(button.querySelector("button")).toBeNull();
    }
  });
});

describe("WorkspaceRosterGroups — collapsing a group", () => {
  it("collapses and reopens through a native button with honest state", () => {
    renderGroups({ rows: [player({ id: "a", name: "Ann First" })] });
    const toggle = screen
      .getAllByRole("button")
      .filter((b) =>
        b.classList.contains("dg-roster-groups__group-toggle"),
      )[0] as HTMLButtonElement;
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(rowLabels()).toHaveLength(1);

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(rowLabels()).toHaveLength(0);

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(rowLabels()).toHaveLength(1);
  });

  it("shows every group when it cannot ask the viewport, rather than hiding players", () => {
    // jsdom has no matchMedia. The fallback must reveal players, never conceal them.
    expect(window.matchMedia).toBeUndefined();
    renderGroups({
      rows: [
        player({ id: "qb", name: "Quinn Quarter", position: "QB" }),
        player({ id: "rb", name: "Rhea Rush", position: "RB" }),
      ],
    });
    expect(rowLabels()).toHaveLength(2);
  });
});

describe("WorkspaceRosterGroups — the quarterback depth section", () => {
  const qbs = [
    player({ id: "a", name: "Ann First", position: "QB" }),
    player({ id: "b", name: "Bea Second", position: "QB" }),
  ];

  it("is absent unless the parent asks for it", () => {
    const { container } = renderGroups({ rows: qbs });
    expect(container.textContent).not.toContain("Quarterback depth");
  });

  it("shows the owned quarterbacks and offers to browse available ones", () => {
    const { onFindAlternatives } = renderGroups({ rows: qbs, showDepth: true });
    expect(screen.getByText("Quarterback depth")).toBeTruthy();
    fireEvent.click(
      screen.getByRole("button", { name: /Browse available quarterbacks/ }),
    );
    expect(onFindAlternatives).toHaveBeenCalledWith("QB");
  });

  it("names no starter slot, role or lineup requirement", () => {
    const { container } = renderGroups({ rows: qbs, showDepth: true });
    const text = container.textContent ?? "";
    for (const invented of [
      "QB1",
      "QB2",
      "Starter",
      "starts two",
      "Best pickup",
      "Bench",
    ]) {
      expect(text).not.toContain(invented);
    }
  });

  it("quotes the league format only when the source states it", () => {
    const stated = renderGroups({ rows: qbs, showDepth: true });
    expect(stated.container.textContent).toContain("Superflex");
    cleanup();

    const quiet = renderGroups({
      rows: qbs,
      showDepth: true,
      data: { ...data, basis: { ...data.basis, scoring_note: "Full PPR" } },
    });
    expect(quiet.container.textContent).not.toContain("Superflex");
  });
});

describe("WorkspaceRosterGroups — the copy rule", () => {
  it("puts no raw pipeline key or shouted token on screen", () => {
    const { container } = renderGroups({
      rows: [
        player({ id: "a", name: "Ann First", position: "QB" }),
        player({ id: "b", name: "Rhea Rush", position: "RB" }),
        player({ id: "c", name: "Ned NoRank", rank: rankRow({ our_rank: null }) }),
      ],
      showDepth: true,
    });
    const findings = auditRenderedCopy(container);
    expect(findings, formatRawCopyFindings(findings)).toEqual([]);
  });

  it("states both column units once, not on every row", () => {
    const { container } = renderGroups({ rows: [player(), player({ id: "2" })] });
    const head = container.querySelector(".dg-roster-groups__head");
    expect(head?.textContent).toContain("2026");
    expect(head?.textContent).toContain("2027–2030");
    const rows = container.querySelectorAll(".dg-roster-groups__row");
    for (const row of Array.from(rows)) {
      expect(row.textContent).not.toContain("2027–2030");
    }
  });
});

describe("WorkspaceRosterGroups — root review, 2026-09-08", () => {
  it("shows every owned quarterback in the depth section, including one this order cannot rank", () => {
    const rows = [
      player({ id: "a", name: "Ann First", position: "QB" }),
      player({
        id: "n",
        name: "Ned NoRank",
        position: "QB",
        rank: rankRow({ our_rank: null }),
      }),
    ];
    const { container } = renderGroups({ rows, showDepth: true, order: "ours" });
    const cards = Array.from(
      container.querySelectorAll(".dg-roster-groups__depth-card"),
      (c) => c.getAttribute("aria-label") ?? "",
    );
    expect(cards).toHaveLength(2);
    expect(cards.filter((l) => l.startsWith("Ned NoRank"))).toHaveLength(1);
  });

  it("takes the top of a group's span from the widest tie, not from where that tie starts", () => {
    const { container } = renderGroups({
      rows: [
        player({ id: "a", rank: rankRow({ our_rank: interval(4) }) }),
        player({ id: "b", rank: rankRow({ our_rank: interval(230, 388) }) }),
      ],
    });
    expect(
      container.querySelector(".dg-roster-groups__group-summary")?.textContent,
    ).toContain("#4–388");
  });

  it("carries both seasons in the row's accessible name, because a phone hides those columns", () => {
    renderGroups({ rows: [player({ id: "a", name: "Ann First" })] });
    const label =
      screen.getByRole("button", { name: /^Ann First/ }).getAttribute("aria-label") ??
      "";
    expect(label).toContain("2026: 100.0 points");
    expect(label).toContain("2027–2030: 400.0 points");
  });

  it("names the two ranks inside the row, where no column header is on screen", () => {
    const { container } = renderGroups({ rows: [player()] });
    const row = container.querySelector(".dg-roster-groups__row");
    expect(
      Array.from(
        row?.querySelectorAll(".dg-roster-groups__reading-label") ?? [],
        (n) => n.textContent,
      ),
    ).toEqual(["Ours", "Market", "Gap"]);
  });

  it("names every reading on a depth card, which sits under no column header at all", () => {
    const { container } = renderGroups({
      rows: [player({ id: "a", name: "Ann First", position: "QB" })],
      showDepth: true,
    });
    const card = container.querySelector(".dg-roster-groups__depth-card");
    expect(
      Array.from(
        card?.querySelectorAll(".dg-roster-groups__reading-label") ?? [],
        (n) => n.textContent,
      ),
    ).toEqual(["Ours", "Market", "2026 pts"]);
  });

  it("does not claim the forecast reproduces this league's own scoring", () => {
    const { container } = renderGroups();
    const basis =
      container.querySelector(".dg-roster-groups__basis")?.textContent ?? "";
    expect(basis).toContain("research PPR scoring");
    expect(basis).not.toContain("this league's scoring");
    // the methodology is the source's own sentence, not my paraphrase of it
    expect(basis).toContain(data.basis.scoring_note);
  });

  it("labels the season numbers as points, so a total cannot read as a price", () => {
    const { container } = renderGroups({
      rows: [
        player({
          id: "a",
          forecast: forecastRow({
            sleeper_id: "a",
            now_points: 100,
            future_points: 400,
          }),
        }),
      ],
    });
    const head = container.querySelector(".dg-roster-groups__head")?.textContent ?? "";
    expect(head).toContain("2026 pts");
    expect(head).toContain("2027–2030 pts");
    const summary =
      container.querySelector(".dg-roster-groups__group-summary")?.textContent ?? "";
    expect(summary).toContain("2026 100.0 pts");
    expect(summary).toContain("2027–2030 400.0 pts");
  });
});
