// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { leaguePulseResponse } from "../league-pulse/fixtures";
import { AppShell } from "./AppShell";

// DG-114: five destinations, not eleven surface links. The surfaces themselves
// are unchanged and still addressed by the same `?surface=` slugs — what moved
// is how you get to them. `goTo` presses the rail item, then the view chip when
// the destination holds more than one surface.
const NAV_LABELS = ["Today", "Roster", "Trades", "League", "Track record"];

function goTo(destination, view) {
  const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
  fireEvent.click(within(navigation).getByRole("button", { name: destination }));
  if (view !== undefined) {
    const views = screen.getByRole("navigation", { name: `${destination} views` });
    fireEvent.click(within(views).getByRole("button", { name: view }));
  }
}

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

describe("AppShell", () => {
  it("renders the persistent shell regions and north-star navigation surfaces", () => {
    render(<AppShell />);

    expect(screen.getByRole("navigation", { name: "Primary surfaces" })).toBeTruthy();
    expect(screen.getByRole("banner", { name: "Trust strip" })).toBeTruthy();
    // DG-114: the third column is gone. The player card opens as a drawer over
    // the surface on press, so there is no standing panel to sit empty.
    expect(
      screen.queryByRole("complementary", { name: "Player inspector" }),
    ).toBeNull();

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    expect(
      within(navigation)
        .getAllByRole("button")
        .map((button) => button.textContent.replace(/\s+/g, " ").trim()),
    ).toEqual(NAV_LABELS);
    expect(
      within(navigation).queryByRole("button", { name: "Project Tracker" }),
    ).toBeNull();
    expect(
      within(navigation).queryByRole("button", { name: "Backtest Harness" }),
    ).toBeNull();
  });

  it("keeps navigation and trust strip mounted while switching placeholders", () => {
    render(<AppShell />);

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    goTo("Trades");

    expect(screen.getByRole("navigation", { name: "Primary surfaces" })).toBeTruthy();
    expect(screen.getByRole("banner", { name: "Trust strip" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Trades", level: 1 })).toBeTruthy();
    expect(within(navigation).getByRole("button", { name: "Trades" })).toHaveProperty(
      "ariaCurrent",
      "page",
    );
  });

  it("opens no player panel until a player is picked", () => {
    render(<AppShell />);

    // DG-110 kept an empty inspector off the first load; DG-114 removes the
    // panel itself. Nothing player-shaped is on screen until a name is pressed.
    expect(screen.queryByRole("dialog", { name: "Player card" })).toBeNull();
    expect(screen.queryByText(/no player picked yet/i)).toBeNull();
    expect(screen.getByRole("navigation", { name: "Primary surfaces" })).toBeTruthy();
  });

  it("renders the Model Trust placeholder from the primary navigation", () => {
    render(<AppShell />);

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    goTo("Track record", "Model trust");

    const main = screen.getByRole("main");
    expect(
      within(main).getByRole("heading", { name: "Track record", level: 1 }),
    ).toBeTruthy();
    for (const position of ["QB", "RB", "WR", "TE"]) {
      expect(within(main).getByRole("button", { name: position })).toBeTruthy();
    }
    expect(
      within(navigation).queryByRole("button", { name: "Backtest Harness" }),
    ).toBeNull();
  });

  it("renders the Roster Audit surface when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "active",
        engine: "e",
        reason: "r",
        model_status_by_position: {},
        caveats: [],
        players: [],
        qb_context_cards: [],
        dropped_player_count: 0,
        decision_supported: false,
      }),
    });
    render(<AppShell />);
    goTo("Roster", "All players");
    // DG-111: the roster surface no longer stamps a disclaimer; the surface is
    // recognised by its own controls instead.
    await waitFor(() =>
      expect(screen.getByRole("region", { name: /roster audit status/i })).toBeTruthy(),
    );
    expect(screen.queryByText(/experimental — not decision-grade/i)).toBeNull();
  });

  it("renders the Project Tracker surface when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        source: "resources/project_plan.json",
        schema_version: "project_plan.v1",
        updated_at: "2026-07-05",
        status: "ok",
        phases: [
          {
            id: "p1",
            title: "Phase 1",
            status: "in_progress",
            summary: null,
            tasks: [],
          },
        ],
        warnings: [],
        parser_version: "v1",
      }),
    });

    // DG-114: the crew's tracker left the navigation entirely (David, verbatim:
    // "Remove from nav entirely"). It is reached at its URL and nowhere else.
    window.history.replaceState(null, "", "/?surface=project-tracker");
    render(<AppShell />);

    await waitFor(() => expect(screen.getByText("Phase 1")).toBeTruthy());
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/internal/project-plan");
  });

  it("renders the League Pulse surface when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => leaguePulseResponse(),
    });

    render(<AppShell />);
    goTo("League");

    await waitFor(() =>
      expect(screen.getByRole("region", { name: "League Pulse" })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/pulse");
  });

  it("renders the Roster Capacity sandbox when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        artifact_status: "ok",
        status: "ok",
        capacity_health: {
          total_players: 29,
          total_capacity: 28,
          total_capacity_cuts_required: 1,
          active_slot_overflow: 2,
          by_slot_class: { active: 22, reserve: 4, taxi: 3 },
          reserve_unrestricted: false,
        },
        candidates: [],
        scenarios: [],
        unrostered_pool_range: {},
        excluded_counts: {},
        caveats: [],
        created_at: "2026-06-30T12:00:00+00:00",
        sleeper_snapshot_captured_at: "2026-06-30T11:00:00+00:00",
        decision_supported: false,
      }),
    });

    render(<AppShell />);
    goTo("Roster", "Cut list");

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /roster capacity sandbox/i }),
      ).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/roster/capacity");
  });

  it("renders the Daily What-Changed surface when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        schema_version: "war_room_2_what_changed_v1",
        generated_at: "2026-07-01T12:00:00+00:00",
        decision_supported: false,
        overall_status: "ok",
        daily_diff: {
          decision_supported: false,
          overall_status: "ok",
          market: {
            status: "ok",
            decision_supported: false,
            market_source: "keeptradecut",
            comparison_window: {
              from_date: "2026-06-30",
              to_date: "2026-07-01",
            },
            roster_deltas: [],
            top_movers: [],
            total_movers_count: 0,
            entered: [],
            exited: [],
          },
          model: {
            status: "ok",
            decision_supported: false,
            comparison_window: { status: "insufficient_history" },
            deltas: [],
            vintage_changed: false,
            feature_freshness: null,
            pvo_staleness: null,
          },
        },
        structural_context: {
          status: "ok",
          decision_supported: false,
          current_not_delta: true,
          sections: {
            team_posture: {
              status: "ok",
              decision_supported: false,
              current_not_delta: true,
            },
            team_value: {
              status: "ok",
              decision_supported: false,
              current_not_delta: true,
            },
            league_opportunity: {
              status: "ok",
              decision_supported: false,
              current_not_delta: true,
            },
            drop_pressure: {
              status: "ok",
              decision_supported: false,
              current_not_delta: true,
            },
            sleeper_snapshot: {
              status: "ok",
              decision_supported: false,
              current_not_delta: true,
            },
          },
        },
      }),
    });

    render(<AppShell />);
    goTo("Today");

    await waitFor(() =>
      expect(screen.getByRole("region", { name: /daily what-changed/i })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/what-changed");
  });

  it("renders the Accuracy Tracker diagnostic scorecard when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "inactive",
        status_reason: "awaiting_first_finalized_week",
        as_of_week: null,
        settlement_status: "unsettled",
        maturity_pct: null,
        cohort_metrics: {},
        tracking_rows: [],
        excluded_counts: {},
        coverage: {
          declared_count: null,
          eligible_count: null,
          resolved_count: null,
          outcome_present_count: null,
          graded_count: null,
          rank_eligible_count: null,
          identity_excluded_counts: {},
          prediction_excluded_counts: {},
        },
        decision_supported: false,
      }),
    });

    render(<AppShell />);
    goTo("Track record", "Accuracy tracker");

    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: /diagnostic scorecard/i }),
      ).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/realized-outcome/scorecard");
  });
});
