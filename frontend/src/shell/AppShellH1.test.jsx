// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "./AppShell";

// DG-114 amends this contract on David's authority (2026-08-30 panel, verbatim
// option label: "Remove from nav entirely"). H1 §1b put the parked surfaces LAST
// in the rail with a "(Parked)" badge, on the argument that hiding them would
// hide an honest gap. David has now ruled the other way: roadmap is not product,
// so they leave the navigation and stay reachable at their URL — where the
// honest gap is still stated in full, by the same parked card, which the third
// check below still mounts and reads. The fact survives; the rail entry does not.
const PRIMARY_LABELS = ["Today", "Roster", "Trades", "League", "Track record"];

function healthResponse() {
  return {
    checked_at: "2026-07-03T14:55:00+00:00",
    config_version: 1,
    decision_supported: false,
    disclaimer:
      "System health reflects pipeline completion, artifact freshness, and model provenance verification. It does not evaluate model accuracy or guarantee trade edge.",
    overall_status: "ok",
    reports: [],
    subsystems: [
      {
        basis: "adapter_status:ok",
        decision_supported: false,
        status: "ok",
        subsystem_id: "model_provenance",
        tier: "core_substrate",
      },
      {
        basis: "adapter_status:ok",
        decision_supported: false,
        status: "ok",
        subsystem_id: "capture_health",
        tier: "core_substrate",
      },
      {
        basis: "adapter_status:ok",
        decision_supported: false,
        status: "ok",
        subsystem_id: "tier_readiness",
        tier: "daily_diagnostics",
      },
    ],
    worst_affected_tier: null,
  };
}

function whatChangedResponse() {
  const structural = {
    status: "ok",
    decision_supported: false,
    current_not_delta: true,
  };
  return {
    schema_version: "war_room_2_what_changed_v1",
    generated_at: "2026-07-05T13:45:00Z",
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
          from_date: "2026-07-04",
          to_date: "2026-07-05",
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
      ...structural,
      sections: {
        team_posture: structural,
        team_value: structural,
        league_opportunity: structural,
        drop_pressure: structural,
        sleeper_snapshot: structural,
      },
    },
  };
}

function projectTrackerResponse() {
  return {
    source: "resources/project_plan.json",
    schema_version: "project_plan.v1",
    updated_at: "2026-07-05",
    parser_version: "v1",
    status: "ok",
    warnings: [],
    phases: [
      {
        id: "h1",
        title: "Horizon 1",
        status: "in_progress",
        summary: null,
        tasks: [],
      },
    ],
  };
}

function installFetch() {
  globalThis.fetch = vi.fn((url) => {
    const href = String(url);
    if (href === "/api/health") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => healthResponse(),
      });
    }
    if (href === "/api/league/what-changed") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => whatChangedResponse(),
      });
    }
    if (href === "/api/internal/project-plan") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => projectTrackerResponse(),
      });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

describe("AppShell H1 daily-login UX contract", () => {
  it("boots directly to the morning read on a fresh mount", async () => {
    installFetch();

    render(<AppShell />);

    // Same surface, same first screen; the destination is called Today now.
    expect(screen.getByRole("heading", { name: "Today", level: 1 })).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByRole("region", { name: /daily what-changed/i })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/what-changed");
  });

  it("leads the rail with the morning read and carries no parked entry at all", () => {
    installFetch();

    render(<AppShell />);

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    expect(
      within(navigation)
        .getAllByRole("button")
        .map((button) => button.textContent.replace(/\s+/g, " ").trim()),
    ).toEqual(PRIMARY_LABELS);
    for (const label of ["Rookie Board", "Waiver Radar", "Research Assistant"]) {
      expect(
        within(navigation).queryByRole("button", { name: new RegExp(label, "i") }),
      ).toBeNull();
    }
    expect(within(navigation).queryByText("(Parked)")).toBeNull();
    expect(
      within(navigation).queryByRole("button", { name: /Project Tracker/i }),
    ).toBeNull();
  });

  it("renders parked educational cards with evidence paths and unpark conditions", () => {
    installFetch();

    // Out of the rail, still at its URL, still saying exactly why it is parked.
    window.history.replaceState(null, "", "/?surface=rookie-board");
    const first = render(<AppShell />);
    expect(screen.getByRole("heading", { name: "Rookie Board — parked" })).toBeTruthy();
    expect(screen.getByText(/failed its pre-registered promotion gates/i)).toBeTruthy();
    expect(
      screen.getByText("docs/validation/engine_a_v2_cfbd_backtest_report.md"),
    ).toBeTruthy();
    expect(
      screen.getByText(/David-ratified spec for a React rookie surface/i),
    ).toBeTruthy();
    first.unmount();

    window.history.replaceState(null, "", "/?surface=waiver-radar");
    const second = render(<AppShell />);
    expect(screen.getByRole("heading", { name: "Waiver Radar — parked" })).toBeTruthy();
    expect(screen.getByText(/needs in-season usage signals/i)).toBeTruthy();
    expect(screen.getByText("PRODUCT.md")).toBeTruthy();
    expect(screen.getByText(/In-season 2026 usage accrual/i)).toBeTruthy();
    second.unmount();

    window.history.replaceState(null, "", "/?surface=research-assistant");
    render(<AppShell />);
    expect(
      screen.getByRole("heading", { name: "Research Assistant — parked" }),
    ).toBeTruthy();
    expect(screen.getByText(/no active design yet/i)).toBeTruthy();
    expect(screen.getByText(/David-prioritized design cycle/i)).toBeTruthy();
  });

  it("keeps Project Tracker out of every navigation affordance and reachable at its URL", async () => {
    installFetch();

    // The Developer zone in the rail is gone with the parked entries: the crew
    // reaches its own tracker the way the spec says (§4.1), by URL.
    window.history.replaceState(null, "", "/?surface=project-tracker");
    render(<AppShell />);
    await waitFor(() => expect(screen.getByText("Horizon 1")).toBeTruthy());

    const primary = screen.getByRole("navigation", { name: "Primary surfaces" });
    expect(
      within(primary).queryByRole("button", { name: /Project Tracker/i }),
    ).toBeNull();
    expect(screen.queryByRole("navigation", { name: /Developer/i })).toBeNull();

    fireEvent.keyDown(document, { key: "k", metaKey: true });
    expect(screen.queryByRole("option", { name: "Project Tracker" })).toBeNull();
    expect(screen.queryByRole("option", { name: "Rookie Board" })).toBeNull();
  });
});
