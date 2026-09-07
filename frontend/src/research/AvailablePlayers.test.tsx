// @vitest-environment jsdom
// Plan T4 interaction tests: the Available players tab (root's frontend review 2026-09-07 folded in).
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AvailablePlayers } from "./AvailablePlayers";
import { WATCHLIST_KEY } from "./availableHelpers";

function row(over: Record<string, unknown>) {
  return {
    sleeper_id: "1",
    player_id: "00-1",
    name: "Some Guy",
    league_position: "WR",
    fantasy_positions: "WR",
    availability_class: "active",
    population: "default",
    nfl_team: "KC",
    nfl_status_raw: "ACT",
    join_basis: "sleeper_id",
    identity_conflict: null,
    readiness: "comparable",
    now_points: 100,
    future_points: 300,
    future_years: [2027, 2028, 2029, 2030],
    future_reason: null,
    missing_reason: null,
    impact: { h2: 0, h5: 0 },
    recovered: false,
    forecast_path: {
      status: "complete",
      years_present: [2026, 2027, 2028, 2029, 2030],
    },
    forecast: {
      producer: "vet",
      source_csv: "x",
      source_csv_sha256: "a",
      join_basis: "report_gsis",
      join_id: "00-1",
      seasons: [2026, 2027, 2028, 2029, 2030].map((s, i) => ({
        season: s,
        e_points: 100 - i * 10,
        p_appear: 0.8,
        e_points_given_appear: 120,
        e_games: 11,
      })),
    },
    ...over,
  };
}
const rows = [
  row({ sleeper_id: "a", name: "Alpha Wide", now_points: 120.5, future_points: 380 }),
  row({
    sleeper_id: "b",
    name: "Beta Back",
    league_position: "RB",
    nfl_team: "MIN",
    availability_class: "practice_squad",
    nfl_status_raw: "DEV",
    now_points: 10,
    future_points: 190,
  }),
  row({
    sleeper_id: "c",
    name: "Charlie End",
    league_position: "TE",
    availability_class: "injured_reserve",
    nfl_status_raw: "RES",
    now_points: -1.5,
    future_points: 4,
  }),
  row({
    sleeper_id: "d",
    name: "Delta Wide",
    nfl_team: "GB",
    now_points: null,
    future_points: null,
    forecast: null,
    readiness: null,
    impact: { h2: null, h5: null },
    forecast_path: { status: "none", years_present: [] },
    missing_reason: "no forecast from the selected producers; no reason stated",
  }),
  row({ sleeper_id: "e", name: "Echo Wide", now_points: 120.5, future_points: 200 }),
  row({
    sleeper_id: "f",
    name: "Foxtrot Cut",
    league_position: "QB",
    availability_class: "cut",
    population: "cut",
    nfl_status_raw: "CUT",
    now_points: 50,
    future_points: 100,
  }),
  row({
    sleeper_id: "g",
    name: "Golf Back",
    league_position: "RB",
    now_points: 30,
    future_points: 150,
    impact: { h2: null, h5: null },
    recovered: true,
    readiness: null,
  }),
];
const payload = {
  source: {
    kind: "local_research_catalog",
    catalog_run: "20260906T230000Z",
    report_run: "20260906T214512Z",
    pinned: true,
    census_run_id: "20260906T202057Z",
  },
  freshness: {
    ownership_as_of: "2026-09-06T13:00:52+00:00",
    nfl_status_as_of: "Sun, 06 Sep 2026 11:28:11 GMT",
    caveat:
      "Ownership is as of the league snapshot captured 2026-09-06T13:00:52+00:00; NFL roster status is as of the roster capture dated Sun, 06 Sep 2026 11:28:11 GMT. Both may have changed since; nothing here is live.",
  },
  populations: {
    default: {
      total: 6,
      with_forecast: 5,
      without_forecast: 1,
      with_now: 5,
      with_future_total: 5,
      incomplete_path: 0,
      by_class: { active: 3, practice_squad: 1, injured_reserve: 1 },
      by_position: {},
    },
    cut: {
      total: 1,
      with_forecast: 1,
      without_forecast: 0,
      with_now: 1,
      with_future_total: 1,
      incomplete_path: 0,
      by_class: { cut: 1 },
      by_position: {},
    },
  },
  populations_note: "default = …",
  disclosures: {
    uncovered_sleeper_ids: 3373,
    unmatched_nfl_records: 141,
    contested_nfl_records: 1,
    archive_unforecast_by_position: { QB: 368 },
    note: "counts only",
  },
  forecast_note: "values are the producers' own expected season points",
  forecast_years: [2026, 2027, 2028, 2029, 2030],
  future_years: [2027, 2028, 2029, 2030],
  notes: {
    ownership: "Ownership filters availability only.",
    now: "Now = 2026; not weekly start advice.",
    future: "Future = 2027–2030 summed.",
    appearance: "P(appears) is not P(becomes useful).",
    sorting: "Sorting states its basis.",
    watchlist: "Your own shortlist.",
  },
  rows,
};

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});
function mockFetch(body: unknown = payload) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => body })),
  );
}
const names = (region: HTMLElement) =>
  within(region)
    .getAllByTestId("avail-name")
    .map((n) => n.querySelector(".dg-ui-player-id__name")?.textContent);
const table = () => screen.getByRole("region", { name: "Available players" });

describe("AvailablePlayers", () => {
  it("shows the default verified pool sorted by 2026 points with the basis stated, ties named, and rows without a value apart with their reason", async () => {
    mockFetch();
    render(<AvailablePlayers />);
    const t = await screen.findByRole("region", { name: "Available players" });
    expect(names(t)).toEqual([
      "Alpha Wide",
      "Echo Wide",
      "Golf Back",
      "Beta Back",
      "Charlie End",
    ]);
    expect(
      screen.getByText(/sorted by 2026 projected points \(championship window\)/i),
    ).toBeTruthy();
    expect(within(t).getAllByText(/tied with/).length).toBe(2);
    expect(
      screen.getByText(/5 of 6 in the default pool shown with a forecast; 1 without/),
    ).toBeTruthy();
    const missing = screen.getByRole("region", { name: "No value for this ordering" });
    expect(within(missing).getByText("Delta Wide")).toBeTruthy();
    expect(
      within(missing).getByText(
        /no forecast from the selected producers; no reason stated/,
      ),
    ).toBeTruthy();
    expect(screen.queryByText("Foxtrot Cut")).toBeNull(); // cut is not in the default pool
    expect(
      screen.getByText(
        /Ownership as of 2026-09-06T13:00:52\+00:00; NFL status as of Sun, 06 Sep 2026 11:28:11 GMT/,
      ),
    ).toBeTruthy();
    expect(within(t).getByText("-1.5")).toBeTruthy(); // a negative forecast stays a value
  });

  it("filters by search, position and NFL status, switches the sort basis to future with ties named on that basis only, and states no-match and clear", async () => {
    mockFetch();
    render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    fireEvent.click(screen.getByRole("checkbox", { name: "cut" }));
    await waitFor(() => expect(screen.getByText("Foxtrot Cut")).toBeTruthy());
    fireEvent.click(screen.getByRole("checkbox", { name: "cut" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "RB" }));
    await waitFor(() => expect(names(table())).toEqual(["Golf Back", "Beta Back"]));
    fireEvent.click(screen.getByRole("checkbox", { name: "RB" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Sort by" }), {
      target: { value: "future" },
    });
    await waitFor(() =>
      expect(
        screen.getByText(/sorted by projected points 2027–2030 summed/i),
      ).toBeTruthy(),
    );
    expect(names(table())).toEqual([
      "Alpha Wide",
      "Echo Wide",
      "Beta Back",
      "Golf Back",
      "Charlie End",
    ]);
    expect(within(table()).queryAllByText(/tied with/).length).toBe(0);
    const search = screen.getByLabelText("Find an available player");
    fireEvent.change(search, { target: { value: "zzz" } });
    await waitFor(() =>
      expect(screen.getByText(/No available player matches "zzz"/)).toBeTruthy(),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Clear the available-player search" }),
    );
    await waitFor(() => expect((search as HTMLInputElement).value).toBe(""));
  });

  it("keeps forecast coverage and sort-value coverage distinct: a recovered forecast ranks by points but sits apart under impact with its reason", async () => {
    mockFetch();
    render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    fireEvent.change(screen.getByRole("combobox", { name: "Sort by" }), {
      target: { value: "impact5" },
    });
    await waitFor(() =>
      expect(
        screen.getByText(/sorted by five-year impact above the reference/i),
      ).toBeTruthy(),
    );
    expect(names(table())).toEqual([
      "Alpha Wide",
      "Beta Back",
      "Charlie End",
      "Echo Wide",
    ]);
    expect(
      screen.getByText(
        /5 of 6 in the default pool shown with a forecast; 1 without\. 2 listed apart with no value for this ordering/,
      ),
    ).toBeTruthy();
    const missing = screen.getByRole("region", { name: "No value for this ordering" });
    expect(within(missing).getByText("Golf Back")).toBeTruthy();
    expect(
      within(missing).getByText(
        /recovered forecast: not among the accepted board rows, so it has no impact number/,
      ),
    ).toBeTruthy();
    // the missing-forecast filter is about forecasts, not about the sort value
    fireEvent.click(screen.getByRole("checkbox", { name: "Missing forecast only" }));
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: "Available players" })).toBeNull(),
    );
    expect(
      within(
        screen.getByRole("region", { name: "No value for this ordering" }),
      ).queryByText("Golf Back"),
    ).toBeNull();
    expect(screen.getByText("Delta Wide")).toBeTruthy();
  });

  it("treats an emptied NFL-status selection as an explicit no-match, not a silent default", async () => {
    mockFetch();
    render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    for (const s of ["active", "practice squad", "injured reserve"])
      fireEvent.click(screen.getByRole("checkbox", { name: s }));
    await waitFor(() =>
      expect(
        screen.getByText(
          /No NFL status is selected; tick at least one status to list players/,
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByRole("region", { name: "Available players" })).toBeNull();
  });

  it("watches by stable id with identity metadata, keeps a watched player who left the pool or the census, explains ignored controls, and persists", async () => {
    window.localStorage.setItem(
      WATCHLIST_KEY,
      JSON.stringify({ version: 1, ids: ["f", "zz"] }),
    );
    mockFetch();
    render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    fireEvent.click(screen.getByRole("checkbox", { name: "Watched only" }));
    await waitFor(() => expect(screen.getByText("Foxtrot Cut")).toBeTruthy());
    expect(screen.getByText(/watched · left the default pool \(cut\)/)).toBeTruthy();
    expect(screen.getByText("Sleeper id zz")).toBeTruthy();
    expect(
      screen.getByText(/watched · not in the current census; identity unresolved/),
    ).toBeTruthy();
    expect(
      (screen.getByRole("checkbox", { name: "cut" }) as HTMLInputElement).disabled,
    ).toBe(true);
    expect(
      (
        screen.getByRole("checkbox", {
          name: "Missing forecast only",
        }) as HTMLInputElement
      ).disabled,
    ).toBe(true);
    expect(
      screen.getByText(
        /NFL status and missing-forecast filters are ignored while Watched only is on/,
      ),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("checkbox", { name: "Watched only" }));
    const t = await screen.findByRole("region", { name: "Available players" });
    fireEvent.click(within(t).getByRole("button", { name: "Watch Alpha Wide" }));
    await waitFor(() => {
      const saved = JSON.parse(window.localStorage.getItem(WATCHLIST_KEY) ?? "{}");
      expect(saved.version).toBe(2);
      expect(Object.keys(saved.entries)).toEqual(["a", "f", "zz"]);
      expect(saved.entries.a.name).toBe("Alpha Wide");
      expect(saved.entries.a.position).toBe("WR");
    });
    fireEvent.click(within(t).getByRole("button", { name: "Unwatch Alpha Wide" }));
    await waitFor(() =>
      expect(
        Object.keys(
          JSON.parse(window.localStorage.getItem(WATCHLIST_KEY) ?? "{}").entries,
        ),
      ).toEqual(["f", "zz"]),
    );
  });

  it("reports unreadable saved data instead of failing, and a partly readable list with what was kept", async () => {
    window.localStorage.setItem(WATCHLIST_KEY, "{not json");
    mockFetch();
    const { unmount } = render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    expect(screen.getByText(/saved watchlist could not be read/)).toBeTruthy();
    unmount();
    window.localStorage.setItem(
      WATCHLIST_KEY,
      JSON.stringify({ version: 1, ids: ["a", null, ""] }),
    );
    render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    expect(
      screen.getByText(
        /had 2 unreadable entries, which were ignored; the 1 readable one was kept/,
      ),
    ).toBeTruthy();
  });

  it("opens a Why disclosure with the season path, appearance probability and identity, and explains a missing row", async () => {
    mockFetch();
    render(<AvailablePlayers />);
    const t = await screen.findByRole("region", { name: "Available players" });
    fireEvent.click(
      within(t).getAllByRole("button", { name: "Why" })[0] as HTMLElement,
    );
    expect(within(t).getByText(/2026: 100\.0 pts, P\(appears\) 0\.80/)).toBeTruthy();
    expect(within(t).getByText(/P\(appears\) is not P\(becomes useful\)/)).toBeTruthy();
    expect(within(t).getByText(/identity join report_gsis 00-1/)).toBeTruthy();
  });

  it("never prints a nonzero value as zero: tiny negatives and positives keep their sign, exact zero reads 0.0", async () => {
    mockFetch({
      ...payload,
      rows: [
        row({
          sleeper_id: "k",
          name: "Kilo Passer",
          league_position: "QB",
          now_points: -0.035094,
          future_points: -0.07185,
        }),
        row({
          sleeper_id: "z",
          name: "Zulu Back",
          league_position: "RB",
          now_points: 0,
          future_points: 0.007147,
        }),
      ],
    });
    render(<AvailablePlayers />);
    const t = await screen.findByRole("region", { name: "Available players" });
    expect(within(t).getByText("-0.04")).toBeTruthy();
    expect(within(t).getByText("-0.07")).toBeTruthy();
    expect(within(t).getAllByText("0.0").length).toBeGreaterThan(0);
    expect(within(t).getByText("0.01")).toBeTruthy();
    expect(within(t).queryByText("-0.0")).toBeNull();
  });
});

describe("AvailablePlayers — starting estimates (root-accepted cold-start sidecar, new-only)", () => {
  it("labels a starting estimate visibly, names the per-year class in Why with the producer's evidence, and counts it apart", async () => {
    const classes = {
      "2026": "cold_start_candidate",
      "2027": "baseline_research_candidate",
      "2028": "baseline_research_candidate",
      "2029": "baseline_research_candidate",
      "2030": "baseline_research_candidate",
    };
    const path = [
      { season: 2026, e: -0.2117124292, p: 0.18 },
      { season: 2027, e: 10.99, p: 0.3 },
      { season: 2028, e: 9.5, p: 0.28 },
      { season: 2029, e: 8.0, p: 0.25 },
      { season: 2030, e: 6.7, p: 0.2 },
    ];
    const starting = row({
      sleeper_id: "r",
      name: "Kurtis Rourke",
      league_position: "QB",
      nfl_team: "SF",
      now_points: -0.2117124292,
      future_points: 36.0,
      impact: { h2: null, h5: null },
      readiness: null,
      starting_estimate: true,
      estimate_classes: classes,
      forecast: {
        producer:
          "DG-165 cold-start research candidate (starting estimate):dg165_cold_start_candidate_v1",
        source_csv: "x",
        source_csv_sha256: "a",
        join_basis: "cold_start_census_nfl_gsis",
        join_id: "00-0040589",
        seasons: path.map((x) => ({
          season: x.season,
          e_points: x.e,
          p_appear: x.p,
          e_points_given_appear: x.e / x.p,
          e_games: 1,
        })),
      },
    });
    mockFetch({
      ...payload,
      rows: [...rows, starting],
      populations: {
        ...payload.populations,
        default: {
          ...payload.populations.default,
          total: 7,
          with_forecast: 6,
          starting_estimates: 1,
        },
      },
      starting_estimates: {
        count: 1,
        rows: [{ sleeper_id: "r", gsis: "00-0040589", classes }],
        source: {
          run_dir: "runs/20260907T011503Z/dg165_cold_start_candidate",
          manifest_sha256: "d".repeat(64),
          estimates_sha256: "9".repeat(64),
          schema_version: "dg165_cold_start_candidate_v1",
        },
        evidence: {
          selected_per_horizon: {
            "1": "cold_start_candidate",
            "2": "baseline_research_candidate",
            "3": "baseline_research_candidate",
            "4": "baseline_research_candidate",
            "5": "baseline_research_candidate",
          },
          horizons: {
            "1": {
              b1: { n: 210, rmse_points: 28.19, brier: 0.2474 },
              candidate: { n: 210, rmse_points: 24.5, brier: 0.2293 },
            },
            "2": {
              b1: { n: 199, rmse_points: 35.1, brier: 0.2267 },
              candidate: { n: 199, rmse_points: 36.3, brier: 0.2202 },
            },
          },
          caveats: {
            population:
              "a draft-population prior; not conditioned on remaining on a current roster",
          },
          meaning: "retrospective policy selection; not independent confirmation",
        },
      },
      notes: {
        ...payload.notes,
        starting_estimate:
          "A starting estimate is a research candidate; not a breakout probability, no impact number.",
      },
    });
    render(<AvailablePlayers />);
    const t = await screen.findByRole("region", { name: "Available players" });
    expect(names(t)).toEqual([
      "Alpha Wide",
      "Echo Wide",
      "Golf Back",
      "Beta Back",
      "Kurtis Rourke",
      "Charlie End",
    ]);
    expect(
      screen.getByText(
        /6 of 7 in the default pool shown with a forecast \(1 of them a starting estimate\); 1 without/,
      ),
    ).toBeTruthy();
    expect(within(t).getByText(/active · starting estimate/)).toBeTruthy();
    expect(within(t).getByText("-0.2")).toBeTruthy(); // negative, never clamped or zeroed
    const rourke = within(t).getByText("Kurtis Rourke").closest("tr") as HTMLElement;
    fireEvent.click(within(rourke).getByRole("button", { name: "Why" }));
    expect(
      within(t).getByText(
        /2026: -0\.2 pts, P\(appears\) 0\.18 \(cold-start candidate\)/,
      ),
    ).toBeTruthy();
    expect(
      within(t).getByText(
        /2027: 11\.0 pts, P\(appears\) 0\.30 \(historical baseline\)/,
      ),
    ).toBeTruthy();
    expect(
      within(t).getByText(
        /Starting estimate: year 1 from the draft-capital candidate, which beat the position baseline on 210 paired historical rows \(RMSE 24\.5 vs 28\.2; Brier 0\.229 vs 0\.247\)/,
      ),
    ).toBeTruthy();
    expect(
      within(t).getByText(/not conditioned on remaining on a current roster/),
    ).toBeTruthy();
    expect(
      within(t).getByText(
        /Retrospective policy selection; not independent confirmation/,
      ),
    ).toBeTruthy();
    // under impact ordering it sits apart with the honest reason: no impact number is fabricated
    fireEvent.change(screen.getByRole("combobox", { name: "Sort by" }), {
      target: { value: "impact5" },
    });
    await waitFor(() =>
      expect(
        within(
          screen.getByRole("region", { name: "No value for this ordering" }),
        ).getByText("Kurtis Rourke"),
      ).toBeTruthy(),
    );
    expect(
      screen.getByText(
        /starting estimate: no impact number is fabricated for a research candidate/,
      ),
    ).toBeTruthy();
  });
});

describe("AvailablePlayers — watched-only keeps an owned player whose status lies outside the unowned classes", () => {
  it("lists a watched row that became owned under a special status with the dated changed-status wording, never a forecast or 'available'", async () => {
    const ekeler = row({
      sleeper_id: "4663",
      name: "Austin Ekeler",
      league_position: "RB",
      nfl_team: null,
      availability_class: "no_verified_join_to_2026_roster",
      population: "owned",
      owned_now: true,
      roster_id: 3,
      now_points: null,
      future_points: null,
      forecast: null,
      readiness: null,
      impact: { h2: null, h5: null },
      missing_reason: "owned in your league; forecasts are shown on the research board",
      forecast_path: { status: "not_carried", years_present: [] },
    });
    window.localStorage.setItem(
      WATCHLIST_KEY,
      JSON.stringify({
        version: 2,
        entries: {
          "4663": {
            name: "Austin Ekeler",
            position: "RB",
            team: "WAS",
            watched_at: "2026-09-01T12:00:00Z",
          },
        },
      }),
    );
    mockFetch({ ...payload, rows: [...rows, ekeler] });
    render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    expect(screen.queryByText("Austin Ekeler")).toBeNull(); // owned rows are never in the available view
    fireEvent.click(screen.getByRole("checkbox", { name: "Watched only" }));
    await waitFor(() => expect(screen.getByText("Austin Ekeler")).toBeTruthy());
    expect(
      screen.getByText(
        /no verified join to 2026 roster · owned in your league · watched · now owned in your league/,
      ),
    ).toBeTruthy();
    expect(screen.getByText(/1 watched player shown/)).toBeTruthy();
    expect(screen.queryByText(/watched · available/)).toBeNull();
    const missing = screen.getByRole("region", { name: "No value for this ordering" });
    expect(
      within(missing).getByText(
        /owned in your league; forecasts are shown on the research board/,
      ),
    ).toBeTruthy();
    // search and position still narrow the shortlist
    fireEvent.click(screen.getByRole("checkbox", { name: "QB" }));
    await waitFor(() => expect(screen.queryByText("Austin Ekeler")).toBeNull());
    expect(screen.getByText(/0 watched players shown/)).toBeTruthy();
  });
});

describe("AvailablePlayers — a Why explanation is readable on a phone without sideways panning", () => {
  it("anchors the table's horizontal scroll to the left when a detail opens and renders the prose in a viewport-bound block", async () => {
    const scrollTo = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      value: scrollTo,
      configurable: true,
      writable: true,
    });
    mockFetch();
    render(<AvailablePlayers />);
    const t = await screen.findByRole("region", { name: "Available players" });
    const rowEl = within(t).getByText("Alpha Wide").closest("tr") as HTMLElement;
    fireEvent.click(within(rowEl).getByRole("button", { name: "Why" }));
    const detail = within(t)
      .getByText(/2026: 100\.0 pts/)
      .closest(".dg-research__detail") as HTMLElement;
    const prose = detail.querySelector(".dg-avail__prose") as HTMLElement;
    expect(prose).toBeTruthy();
    expect(
      prose.contains(within(t).getByText(/P\(appears\) is not P\(becomes useful\)/)),
    ).toBe(true);
    // the scroll container that wraps the table was told to go back to its left edge
    expect(scrollTo).toHaveBeenCalledWith({ left: 0 });
    const scroller = t.closest(".dg-table-scroll") ?? t;
    expect(scroller.classList.contains("dg-table-scroll")).toBe(true);
  });
});

// DG-181: a "Compare" action beside Watch / Why hands the row to the research page, which opens
// the comparison with that available player chosen and the roster choice left to David.
describe("AvailablePlayers — Compare action", () => {
  it("offers Compare on value rows and no-value rows only when a handler is given, and hands back the row", async () => {
    mockFetch();
    const onCompare = vi.fn();
    render(<AvailablePlayers onCompare={onCompare} />);
    const t = await screen.findByRole("region", { name: "Available players" });
    fireEvent.click(within(t).getByRole("button", { name: "Compare Alpha Wide" }));
    expect(onCompare).toHaveBeenCalledTimes(1);
    expect(onCompare.mock.calls[0]?.[0]).toMatchObject({
      sleeper_id: "a",
      name: "Alpha Wide",
    });
    const missing = screen.getByRole("region", { name: "No value for this ordering" });
    fireEvent.click(
      within(missing).getByRole("button", { name: "Compare Delta Wide" }),
    );
    expect(onCompare.mock.calls[1]?.[0]).toMatchObject({ sleeper_id: "d" });
    expect(within(t).getByText("Watch / Compare / Why")).toBeTruthy();
  });

  it("renders no Compare control without a handler", async () => {
    mockFetch();
    render(<AvailablePlayers />);
    await screen.findByRole("region", { name: "Available players" });
    expect(screen.queryByRole("button", { name: /^Compare / })).toBeNull();
    expect(screen.getAllByText("Watch / Why").length).toBeGreaterThan(0);
  });
});
