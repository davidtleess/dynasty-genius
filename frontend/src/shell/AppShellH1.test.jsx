// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "./AppShell";

const PRIMARY_LABELS = [
  "Daily What-Changed",
  "Roster Audit",
  "Trade Lab",
  "Roster Capacity",
  "League Pulse",
  "Model Trust",
  "Accuracy Tracker",
  "Rookie Board (Parked)",
  "Waiver Radar (Parked)",
  "Research Assistant (Parked)",
];

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

afterEach(() => vi.restoreAllMocks());

describe("AppShell H1 daily-login UX contract", () => {
  it("boots directly to Daily What-Changed on a fresh mount", async () => {
    installFetch();

    render(<AppShell />);

    expect(
      screen.getByRole("heading", { name: "Daily What-Changed", level: 1 }),
    ).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByRole("region", { name: /daily what-changed/i })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/what-changed");
  });

  it("orders primary rail active first and parked last with exact parked badges", () => {
    installFetch();

    render(<AppShell />);

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    expect(
      within(navigation)
        .getAllByRole("button")
        .map((button) => button.textContent.replace(/\s+/g, " ").trim()),
    ).toEqual(PRIMARY_LABELS);
    for (const label of ["Rookie Board", "Waiver Radar", "Research Assistant"]) {
      const item = within(navigation).getByRole("button", {
        name: new RegExp(label, "i"),
      });
      expect(within(item).getByText("(Parked)")).toBeTruthy();
    }
    expect(
      within(navigation).queryByRole("button", { name: /Project Tracker/i }),
    ).toBeNull();
  });

  it("renders parked educational cards with evidence paths and unpark conditions", () => {
    installFetch();

    render(<AppShell />);
    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });

    fireEvent.click(within(navigation).getByRole("button", { name: /Rookie Board/i }));
    expect(screen.getByRole("heading", { name: "Rookie Board — parked" })).toBeTruthy();
    expect(screen.getByText(/failed its pre-registered promotion gates/i)).toBeTruthy();
    expect(
      screen.getByText("docs/validation/engine_a_v2_cfbd_backtest_report.md"),
    ).toBeTruthy();
    expect(
      screen.getByText(/David-ratified spec for a React rookie surface/i),
    ).toBeTruthy();

    fireEvent.click(within(navigation).getByRole("button", { name: /Waiver Radar/i }));
    expect(screen.getByRole("heading", { name: "Waiver Radar — parked" })).toBeTruthy();
    expect(screen.getByText(/needs in-season usage signals/i)).toBeTruthy();
    expect(
      screen.getByText("docs/governance/01-north-star-architecture.md"),
    ).toBeTruthy();
    expect(screen.getByText(/In-season 2026 usage accrual/i)).toBeTruthy();

    fireEvent.click(
      within(navigation).getByRole("button", { name: /Research Assistant/i }),
    );
    expect(
      screen.getByRole("heading", { name: "Research Assistant — parked" }),
    ).toBeTruthy();
    expect(screen.getByText(/no active design yet/i)).toBeTruthy();
    expect(screen.getByText(/David-prioritized design cycle/i)).toBeTruthy();
  });

  it("keeps Project Tracker out of primary rail but reachable in Developer zone and Cmd-K", async () => {
    installFetch();

    render(<AppShell />);

    const primary = screen.getByRole("navigation", { name: "Primary surfaces" });
    expect(
      within(primary).queryByRole("button", { name: /Project Tracker/i }),
    ).toBeNull();

    const developer = screen.getByRole("navigation", { name: /Developer/i });
    fireEvent.click(within(developer).getByRole("button", { name: "Project Tracker" }));
    await waitFor(() => expect(screen.getByText("Horizon 1")).toBeTruthy());

    fireEvent.keyDown(document, { key: "k", metaKey: true });
    expect(screen.getByRole("option", { name: "Project Tracker" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "Rookie Board" })).toBeTruthy();
  });
});
