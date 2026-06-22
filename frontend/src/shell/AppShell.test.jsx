// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { leaguePulseResponse } from "../league-pulse/fixtures";
import { AppShell } from "./AppShell";

const NAV_LABELS = [
  "Rookie Board",
  "Roster Audit",
  "Trade Lab",
  "Waiver Radar",
  "League Pulse",
  "Model Trust",
  "Research Assistant",
];

afterEach(() => vi.restoreAllMocks());

describe("AppShell", () => {
  it("renders the persistent shell regions and north-star navigation surfaces", () => {
    render(<AppShell />);

    expect(screen.getByRole("navigation", { name: "Primary surfaces" })).toBeTruthy();
    expect(screen.getByRole("banner", { name: "Trust strip" })).toBeTruthy();
    expect(
      screen.getByRole("complementary", { name: "Player inspector" }),
    ).toBeTruthy();

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    for (const label of NAV_LABELS) {
      expect(within(navigation).getByRole("button", { name: label })).toBeTruthy();
    }
    expect(
      within(navigation).queryByRole("button", { name: "Backtest Harness" }),
    ).toBeNull();
  });

  it("keeps navigation and trust strip mounted while switching placeholders", () => {
    render(<AppShell />);

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Trade Lab" }));

    expect(screen.getByRole("navigation", { name: "Primary surfaces" })).toBeTruthy();
    expect(screen.getByRole("banner", { name: "Trust strip" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Trade Lab", level: 1 })).toBeTruthy();
    expect(
      within(navigation).getByRole("button", { name: "Trade Lab" }),
    ).toHaveProperty("ariaCurrent", "page");
  });

  it("toggles the player inspector open and closed without unmounting the shell", () => {
    render(<AppShell />);

    const toggle = screen.getByRole("button", { name: "Toggle player inspector" });
    const inspector = screen.getByRole("complementary", { name: "Player inspector" });

    expect(inspector.dataset.state).toBe("open");

    fireEvent.click(toggle);
    expect(inspector.dataset.state).toBe("closed");
    expect(screen.getByRole("navigation", { name: "Primary surfaces" })).toBeTruthy();

    fireEvent.click(toggle);
    expect(inspector.dataset.state).toBe("open");
  });

  it("renders the Model Trust placeholder from the primary navigation", () => {
    render(<AppShell />);

    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Model Trust" }));

    const main = screen.getByRole("main");
    expect(
      within(main).getByRole("heading", { name: "Model Trust", level: 1 }),
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
    fireEvent.click(screen.getByRole("button", { name: "Roster Audit" }));
    await waitFor(() =>
      expect(screen.getByText(/experimental — not decision-grade/i)).toBeTruthy(),
    );
  });

  it("renders the Project Tracker surface when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        source: "resources/project_plan.json",
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

    render(<AppShell />);
    fireEvent.click(screen.getByRole("button", { name: "Project Tracker" }));

    await waitFor(() => expect(screen.getByText("Phase 1")).toBeTruthy());
  });

  it("renders the League Pulse surface when its nav item is selected", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => leaguePulseResponse(),
    });

    render(<AppShell />);
    fireEvent.click(screen.getByRole("button", { name: "League Pulse" }));

    await waitFor(() =>
      expect(screen.getByRole("region", { name: /league pulse/i })).toBeTruthy(),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/pulse");
  });
});
