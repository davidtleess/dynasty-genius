// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlayerDetailPage } from "../player/PlayerDetailPage";
import { PlayerSelectionProvider } from "../player/playerSelection";
import { RosterAudit } from "../roster/RosterAudit";
import { comparisonText, RankPlayerView } from "./MarketRanks";
import {
  MarketRanksContext,
  MarketRanksProvider,
  type RankState,
} from "./MarketRanksContext";

const rank = (start: number, end = start) => ({ start, end, total: 3 });
const row = {
  sleeper_id: "one",
  name: "First Player",
  position: "QB",
  team: "MIN",
  on_roster: true,
  league_ownership: "Your roster",
  taxi_or_reserve: false,
  model_value: 20,
  market_value: 500,
  our_rank: rank(1),
  market_rank: rank(3),
  model_rank_all: rank(1),
  market_rank_published: 4,
  comparison: { direction: "higher" as const, gap_min: 2, gap_max: 2 },
  missing_reason: null,
  model_zero_tie: false,
  seasons: [{ season: 2026, advantage: 20 }],
  reference_player: "Reference Player",
};
const data = {
  status: "available" as const,
  source: {
    report_run: "test",
    report_sha256: "test",
    market_sha256: "test",
    league_sha256: "test",
    forecast_date: "2026-09-06",
    market_as_of: "2026-09-06T13:00:00Z",
    ownership_as_of: "2026-09-06T13:00:00Z",
  },
  basis: {
    years: [2026, 2027, 2028, 2029, 2030],
    season_weights: [1, 1, 1, 1, 1],
    summary: "Five equally weighted seasons above replacement.",
    market_proxy_note:
      "FantasyCalc represents the broader market, not a specific manager.",
    scoring_note: "Research PPR scoring.",
  },
  coverage: {
    model_players: 3,
    market_players: 3,
    market_picks: 1,
    common_players: 3,
    total_players: 3,
    roster_players: 2,
    roster_common_players: 1,
  },
  rows: [
    row,
    {
      ...row,
      sleeper_id: "two",
      name: "Missing Player",
      position: "WR",
      our_rank: null,
      market_rank: null,
      market_value: null,
      market_rank_published: null,
      comparison: { direction: "unavailable" as const, gap_min: null, gap_max: null },
      missing_reason: "No saved market price.",
    },
  ],
};
function wrap(node: React.ReactNode, state: RankState = { status: "available", data }) {
  return (
    <MarketRanksContext.Provider value={state}>{node}</MarketRanksContext.Provider>
  );
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("core comparable ranks", () => {
  it("states signed exact, tied, overlapping and unavailable differences honestly", () => {
    expect(comparisonText(row.comparison)).toBe("We rank him 2 places higher");
    expect(comparisonText({ direction: "lower", gap_min: -40, gap_max: -10 })).toBe(
      "We rank him at least 10 places lower",
    );
    expect(comparisonText({ direction: "overlap", gap_min: -5, gap_max: 9 })).toContain(
      "Tied ranks overlap",
    );
  });
  it("roster searches, filters and opens the saved stable identity without the old audit", () => {
    const select = vi.fn();
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(
      wrap(
        <PlayerSelectionProvider value={select}>
          <RosterAudit />
        </PlayerSelectionProvider>,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Open First Player, QB MIN" }));
    expect(select).toHaveBeenCalledWith("one", "First Player");
    fireEvent.change(screen.getByRole("searchbox", { name: "Search your roster" }), {
      target: { value: "missing" },
    });
    expect(screen.queryByText("First Player")).toBeNull();
    expect(screen.getByText("Missing Player")).toBeTruthy();
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Position" }), {
      target: { value: "QB" },
    });
    expect(screen.queryByText("Missing Player")).toBeNull();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("changes player identity and ranks together with no old score fetch", () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    const view = render(wrap(<PlayerDetailPage sleeperId="one" />));
    expect(screen.getByText("We rank him 2 places higher")).toBeTruthy();
    view.rerender(wrap(<PlayerDetailPage sleeperId="two" />));
    expect(screen.queryByText("First Player")).toBeNull();
    expect(screen.getByText("Missing Player")).toBeTruthy();
    expect(screen.queryByText("We rank him 2 places higher")).toBeNull();
    expect(fetcher).not.toHaveBeenCalled();
    view.rerender(wrap(<PlayerDetailPage sleeperId="unknown" />));
    expect(screen.getByText(/No comparable ranking for this player/)).toBeTruthy();
  });
  it("discloses structural zeros without inventing a strict rank", () => {
    render(
      wrap(
        <RankPlayerView
          player={{
            ...row,
            model_zero_tie: true,
            our_rank: rank(2, 3),
            model_value: 0,
            comparison: { direction: "overlap", gap_min: 0, gap_max: 1 },
          }}
          data={data}
        />,
      ),
    );
    expect(screen.getByText("#2–3")).toBeTruthy();
    expect(screen.getByText(/does not distinguish/)).toBeTruthy();
  });
  it("configured loading and error never fall back to old scores", () => {
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    const view = render(wrap(<RosterAudit />, { status: "loading" }));
    expect(screen.getByRole("status").textContent).toContain("Loading");
    view.rerender(wrap(<RosterAudit />, { status: "error" }));
    expect(screen.getByRole("alert").textContent).toContain("unavailable");
    expect(f).not.toHaveBeenCalled();
  });
  it("provider rejects malformed enabled data and preserves explicit unconfigured", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "available", rows: [] }),
      }),
    );
    const view = render(
      <MarketRanksProvider>
        <RosterAudit />
      </MarketRanksProvider>,
    );
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    view.unmount();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (url) => ({
        ok: true,
        json: async () =>
          url === "/api/research/market-ranks" ? { status: "not_configured" } : {},
      })),
    );
    render(
      <MarketRanksProvider>
        <RosterAudit />
      </MarketRanksProvider>,
    );
    await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/roster/audit"));
  });
});
