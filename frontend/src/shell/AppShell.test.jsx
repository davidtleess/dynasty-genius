// @vitest-environment jsdom

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";

const NAV_LABELS = [
  "Rookie Board",
  "Roster Audit",
  "Trade Lab",
  "Waiver Radar",
  "League Pulse",
  "Backtest Harness",
  "Research Assistant",
];

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
});
