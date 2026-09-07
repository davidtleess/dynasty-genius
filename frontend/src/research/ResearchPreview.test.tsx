// @vitest-environment jsdom
// Plan T4 interaction test: the in-page search over all league-owned players.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchPreview } from "./ResearchPreview";
import { comparisonPayload } from "./RosterComparison.fixtures";

function player(
  name: string,
  position: string,
  team: string,
  value: number | null,
  margins: number[],
) {
  return {
    player_id: name.toLowerCase().replace(/\s+/g, "-"),
    sleeper_id: name.length.toString(),
    name,
    position,
    team,
    age: 25,
    value,
    readiness: value == null ? "none" : "comparable",
    status_sentence:
      value == null
        ? "No forecast from the selected producers for this window; no reason stated."
        : "Research estimate.",
    raw_reason: null,
    producer: "vet",
    estimate_class: "candidate",
    evidence_verified: true,
    served_value: null,
    reference_player: "Kareem Hunt",
    reference_expected_points: 88.3,
    seasons: margins.map((m, i) => ({
      season: 2026 + i,
      expected_margin: m,
      action: m > 0 ? "retain" : "replace",
      advantage: Math.max(0, m),
      player_expected_points: 88.3 + m,
      reference_expected_points: 88.3,
    })),
    rostered_by: 5,
    on_davids_roster: false,
  };
}

const roster = [player("Fernando Mendoza", "QB", "LV", 229, [100, 129])];
const league = [
  ...roster,
  player("Braelon Allen", "RB", "NYJ", 0, [-53.6, -3.5]),
  player("Jayden Reed", "WR", "GB", 0, [-16, -23.2]),
  player("Ashton Jeanty", "RB", "LV", 181, [90, 91]),
  player("Deep Cut", "TE", "KC", 5, [2.5, 2.5]),
];
const view = {
  key: "h2",
  basis: {
    label: "Two-year impact (research preview)",
    horizons_summed: 2,
    seasons: [2026, 2027],
    estimand: "x",
    is_complete_dynasty_value: false,
    scoring_window: "w",
  },
  producers: [],
  support_sentence: "s",
  evidence_sentences: [],
  reference: {
    RB: {
      player: "Kareem Hunt",
      expected_points_by_season: [88.3, 46.2],
      pool_complete: true,
      note: null,
      nfl_attachment: {
        status: "unverified",
        basis: "no verified join",
        note: "no verified join",
      },
    },
  },
  readiness_counts: { comparable: 5, none: 0 },
  roster,
  league,
  top: [roster[0], league[3]],
};
const payload = {
  source: {
    kind: "local",
    run: "20260906T000000Z",
    pinned: true,
    forecast_date: "2026-09-06",
    artifact_captured_at: null,
    snapshot: null,
    note: "",
  },
  basis: view.basis,
  producers: [],
  reference: view.reference,
  readiness_counts: view.readiness_counts,
  roster,
  league,
  top: view.top,
  views: [view],
};

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => payload })),
  );
}

describe("ResearchPreview search", () => {
  it("finds a league-owned player outside the leaders, clears back to the default, and says when nothing matches", async () => {
    mockFetch();
    render(<ResearchPreview />);
    const input = await screen.findByLabelText("Find a league player");
    // default: roster and leaders, no search results, Deep Cut (outside the leaders) not shown
    expect(screen.queryByText("Deep Cut")).toBeNull();
    fireEvent.change(input, { target: { value: "deep" } });
    const results = await screen.findByRole("region", {
      name: "League players matching your search",
    });
    expect(within(results).getByText("Deep Cut")).toBeTruthy();
    expect(screen.getByText(/1 of 5 league-owned players match/)).toBeTruthy();
    // a zero-impact player is found too, with the honest margin label
    fireEvent.change(input, { target: { value: "reed" } });
    const results2 = await screen.findByRole("region", {
      name: "League players matching your search",
    });
    expect(within(results2).getByText("Jayden Reed")).toBeTruthy();
    expect(within(results2).getAllByText("below reference").length).toBeGreaterThan(0);
    // no match state
    fireEvent.change(input, { target: { value: "zzz" } });
    await waitFor(() =>
      expect(screen.getByText(/No league-owned player matches "zzz"/)).toBeTruthy(),
    );
    expect(
      screen.queryByRole("region", { name: "League players matching your search" }),
    ).toBeNull();
    // clear control resets to the default view
    fireEvent.click(screen.getByRole("button", { name: "Clear the player search" }));
    await waitFor(() => expect((input as HTMLInputElement).value).toBe(""));
    expect(screen.queryByText("Deep Cut")).toBeNull();
    expect(screen.getByText(/Searches the 5 league-owned players/)).toBeTruthy();
  });

  it("orders matches by impact and shows season-by-season expected points behind Why", async () => {
    mockFetch();
    render(<ResearchPreview />);
    const input = await screen.findByLabelText("Find a league player");
    fireEvent.change(input, { target: { value: "rb" } });
    const results = await screen.findByRole("region", {
      name: "League players matching your search",
    });
    const names = within(results)
      .getAllByText(/Ashton Jeanty|Braelon Allen/)
      .map((n) => n.textContent);
    expect(names).toEqual(["Ashton Jeanty", "Braelon Allen"]);
    const whys = within(results).getAllByRole("button", { name: "Why" });
    expect(whys.length).toBe(2);
    fireEvent.click(whys[1] as HTMLElement);
    expect(within(results).getByText(/2026: 34\.7 vs 88\.3 \(-54\)/)).toBeTruthy();
    expect(
      within(results).getByText(/NFL roster attachment is unverified/),
    ).toBeTruthy();
  });
});

describe("ResearchPreview search across horizons", () => {
  it("keeps an active query and its matches when the horizon toggles", async () => {
    const view5 = {
      ...view,
      key: "h5",
      basis: {
        ...view.basis,
        label: "Five-year impact (research preview)",
        horizons_summed: 5,
        seasons: [2026, 2027, 2028, 2029, 2030],
      },
    };
    const twoViews = { ...payload, views: [view, view5] };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, json: async () => twoViews })),
    );
    render(<ResearchPreview />);
    const input = await screen.findByLabelText("Find a league player");
    fireEvent.change(input, { target: { value: "braelon" } });
    await screen.findByRole("region", { name: "League players matching your search" });
    fireEvent.click(screen.getByRole("tab", { name: "5-year" }));
    await waitFor(() =>
      expect(screen.getByText("Five-year impact (research preview)")).toBeTruthy(),
    );
    expect((input as HTMLInputElement).value).toBe("braelon");
    const results = screen.getByRole("region", {
      name: "League players matching your search",
    });
    expect(within(results).getByText("Braelon Allen")).toBeTruthy();
    expect(
      screen.getByText(
        /1 of 5 league-owned players match; ordered by five-year impact/,
      ),
    ).toBeTruthy();
  });
});

describe("ResearchPreview search announcements", () => {
  it("announces the match count and the no-match state through one status region, not the table", async () => {
    mockFetch();
    render(<ResearchPreview />);
    const input = await screen.findByLabelText("Find a league player");
    const status = screen.getByRole("status");
    expect(status.textContent).toMatch(/Searches the 5 league-owned players/);
    fireEvent.change(input, { target: { value: "deep" } });
    await waitFor(() =>
      expect(status.textContent).toMatch(/1 of 5 league-owned players match/),
    );
    fireEvent.change(input, { target: { value: "zzz" } });
    await waitFor(() =>
      expect(status.textContent).toMatch(/No league-owned player matches "zzz"/),
    );
    expect(screen.getAllByRole("status")).toHaveLength(1);
    expect(
      document.querySelector("#dg-research-search-results")?.getAttribute("aria-live"),
    ).toBeNull();
  });
});

// Root's integrated-lifecycle finding (2026-09-07): when browser storage throws, the watchlist's
// in-memory fallback must survive switching between the research board and the available tab.
describe("ResearchPreview — available players tab lifecycle", () => {
  it("keeps a watched player across internal tab switches when storage cannot save", async () => {
    const availRow = {
      sleeper_id: "k",
      player_id: "00-9",
      name: "Kyle Allen",
      league_position: "QB",
      fantasy_positions: "QB",
      availability_class: "active",
      population: "default",
      nfl_team: "SF",
      nfl_status_raw: "ACT",
      join_basis: "sleeper_id",
      identity_conflict: null,
      readiness: "comparable",
      now_points: -0.035,
      future_points: 12,
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
        join_id: "00-9",
        seasons: [
          {
            season: 2026,
            e_points: -0.035,
            p_appear: 0.5,
            e_points_given_appear: -0.07,
            e_games: 1,
          },
        ],
      },
    };
    const available = {
      source: {
        kind: "local_research_catalog",
        catalog_run: "20260907T011150Z",
        report_run: "20260906T214512Z",
        pinned: true,
        census_run_id: "c",
      },
      freshness: {
        ownership_as_of: "2026-09-06T13:00:52+00:00",
        nfl_status_as_of: "Sun, 06 Sep 2026 11:28:11 GMT",
        caveat: "dated",
      },
      populations: {
        default: {
          total: 1,
          with_forecast: 1,
          without_forecast: 0,
          by_class: { active: 1 },
          by_position: {},
        },
      },
      populations_note: "note",
      disclosures: {},
      forecast_note: "note",
      forecast_years: [2026, 2027, 2028, 2029, 2030],
      future_years: [2027, 2028, 2029, 2030],
      notes: {
        ownership: "o",
        now: "n",
        future: "f",
        appearance: "a",
        sorting: "s",
        watchlist: "w",
      },
      rows: [availRow],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: true,
        json: async () => (String(url).includes("/available") ? available : payload),
      })),
    );
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    try {
      render(<ResearchPreview />);
      await screen.findByRole("tab", { name: "Available players" });
      fireEvent.click(screen.getByRole("tab", { name: "Available players" }));
      const t = await screen.findByRole("region", { name: "Available players" });
      fireEvent.click(within(t).getByRole("button", { name: "Watch Kyle Allen" }));
      await waitFor(() =>
        expect(
          within(t).getByRole("button", { name: "Unwatch Kyle Allen" }),
        ).toBeTruthy(),
      );
      expect(screen.getByText(/will last only for this page/)).toBeTruthy();
      fireEvent.click(screen.getByRole("tab", { name: "Research board" }));
      await screen.findByRole("region", {
        name: "League leaders on the research board",
      });
      fireEvent.click(screen.getByRole("tab", { name: "Available players" }));
      const t2 = await screen.findByRole("region", { name: "Available players" });
      expect(
        within(t2).getByRole("button", { name: "Unwatch Kyle Allen" }),
      ).toBeTruthy();
      expect(screen.getByText(/will last only for this page/)).toBeTruthy();
    } finally {
      setItem.mockRestore();
    }
  });
});

// DG-181: the third research tab. Direct entry by URL, entry from an available row (which chooses
// that player and leaves the roster choice to David), and choices that survive tab switches.
describe("ResearchPreview — compare players tab", () => {
  const flaccoAvail = {
    sleeper_id: "19",
    player_id: "00-0026158",
    name: "Joe Flacco",
    league_position: "QB",
    fantasy_positions: "QB",
    availability_class: "active",
    population: "default",
    nfl_team: "CIN",
    nfl_status_raw: "ACT",
    join_basis: "sleeper_id",
    identity_conflict: null,
    readiness: "comparable",
    now_points: 115.32497628242587,
    future_points: 179.44179369437418,
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
      join_id: "00-0026158",
      seasons: [
        {
          season: 2026,
          e_points: 115.32497628242587,
          p_appear: 0.84,
          e_points_given_appear: 137,
          e_games: 14,
        },
      ],
    },
  };
  const available = {
    source: {
      kind: "local_research_catalog",
      catalog_run: "20260907T013635Z",
      report_run: "20260906T214512Z",
      pinned: true,
      census_run_id: "c",
    },
    freshness: {
      ownership_as_of: "2026-09-06T13:00:52+00:00",
      nfl_status_as_of: "Sun, 06 Sep 2026 11:28:11 GMT",
      caveat: "dated",
    },
    populations: {
      default: {
        total: 1,
        with_forecast: 1,
        without_forecast: 0,
        by_class: { active: 1 },
      },
    },
    populations_note: "note",
    disclosures: {},
    forecast_note: "note",
    forecast_years: [2026, 2027, 2028, 2029, 2030],
    future_years: [2027, 2028, 2029, 2030],
    notes: {
      ownership: "o",
      now: "n",
      future: "f",
      appearance: "a",
      sorting: "s",
      watchlist: "w",
    },
    rows: [flaccoAvail],
  };
  function mockAll() {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: true,
        json: async () =>
          String(url).includes("/comparison")
            ? comparisonPayload
            : String(url).includes("/available")
              ? available
              : payload,
      })),
    );
  }
  afterEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("opens directly from ?tab=compare with nobody chosen", async () => {
    window.history.replaceState(null, "", "?surface=research-preview&tab=compare");
    mockAll();
    render(<ResearchPreview />);
    expect(
      await screen.findByRole("tab", { name: "Compare players", selected: true }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { level: 1, name: "Compare players" }),
    ).toBeTruthy();
    expect(await screen.findByLabelText("Available player")).toBeTruthy();
    expect(screen.getByLabelText("Your player")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /^Change / })).toBeNull();
  });

  it("opens from an available row with that player chosen and the roster choice left open, then keeps both choices across tabs", async () => {
    mockAll();
    render(<ResearchPreview />);
    fireEvent.click(await screen.findByRole("tab", { name: "Available players" }));
    const t = await screen.findByRole("region", { name: "Available players" });
    fireEvent.click(within(t).getByRole("button", { name: "Compare Joe Flacco" }));
    expect(
      await screen.findByRole("tab", { name: "Compare players", selected: true }),
    ).toBeTruthy();
    expect(
      await screen.findByRole("button", { name: "Change Available player" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Your player")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Change Your player" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Choose J.J. McCarthy" }));
    expect(screen.getByRole("status").textContent).toContain(
      "Joe Flacco's forecast is lower than J.J. McCarthy's",
    );
    fireEvent.click(screen.getByRole("tab", { name: "Research board" }));
    await screen.findByRole("region", { name: "League leaders on the research board" });
    fireEvent.click(screen.getByRole("tab", { name: "Compare players" }));
    expect(
      await screen.findByRole("button", { name: "Change Available player" }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Change Your player" })).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain(
      "Joe Flacco's forecast is lower than J.J. McCarthy's",
    );
  });
});
