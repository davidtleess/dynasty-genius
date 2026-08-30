// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { leaguePulseResponse } from "../league-pulse/fixtures";
import { AppShell } from "./AppShell";

function healthResponse() {
  return {
    checked_at: "2026-07-03T14:55:00+00:00",
    config_version: 1,
    decision_supported: false,
    disclaimer: "System health reflects pipeline status.",
    overall_status: "ok",
    reports: [],
    subsystems: [],
    worst_affected_tier: null,
  };
}

function trustResponse() {
  return {
    position: "QB",
    decision_supported: false,
    source: "model_card",
    as_of: "2026-07-05T12:00:00Z",
    model_status: "available",
    reliability: null,
    metrics: [],
    caveats: [],
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
    if (href === "/api/trust-surface/QB") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => trustResponse(),
      });
    }
    if (href === "/api/league/pulse") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => leaguePulseResponse(),
      });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

describe("AppShell H2 I1 URL surface state", () => {
  it("boots from a valid ?surface= slug and preserves aria-current in the rail", () => {
    installFetch();
    window.history.replaceState(null, "", "/?surface=trade-lab");

    render(<AppShell />);

    // DG-114 groups Trade Lab under the Trades destination. The SLUG is
    // untouched — that is the point of the check — so a bookmark saved before
    // the grouping still lands on the trade builder, with Trades lit in the rail
    // and the builder's own view chip current inside it.
    expect(screen.getByRole("heading", { name: "Trades", level: 1 })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Trades" })).toHaveProperty(
      "ariaCurrent",
      "page",
    );
    const views = screen.getByRole("navigation", { name: "Trades views" });
    expect(within(views).getByRole("button", { name: "Build a trade" })).toHaveProperty(
      "ariaCurrent",
      "page",
    );
  });

  it("falls back to Daily What-Changed on invalid ?surface= slugs", () => {
    installFetch();
    window.history.replaceState(null, "", "/?surface=unknown");

    render(<AppShell />);

    expect(screen.getByRole("heading", { name: "Today", level: 1 })).toBeTruthy();
  });

  it("updates the URL from rail navigation without adding player state", async () => {
    installFetch();
    window.history.replaceState(null, "", "/?surface=what-changed&player=123");

    render(<AppShell />);
    const navigation = screen.getByRole("navigation", { name: "Primary surfaces" });
    fireEvent.click(within(navigation).getByRole("button", { name: "League" }));

    await waitFor(() =>
      expect(screen.getByRole("region", { name: "League Pulse" })).toBeTruthy(),
    );
    expect(window.location.search).toBe("?surface=league-pulse");
    expect(window.location.search).not.toContain("player=");
  });

  it("uses the same URL navigation path from Cmd-K commands", async () => {
    installFetch();
    window.history.replaceState(null, "", "/?surface=what-changed");

    render(<AppShell />);

    fireEvent.keyDown(document, { key: "k", metaKey: true });
    const search = screen.getByRole("textbox", { name: "Command palette" });
    fireEvent.change(search, { target: { value: "league" } });
    fireEvent.keyDown(search, { key: "Enter" });

    await waitFor(() =>
      expect(screen.getByRole("region", { name: "League Pulse" })).toBeTruthy(),
    );
    expect(window.location.search).toBe("?surface=league-pulse");
    expect(screen.getByRole("button", { name: "League" })).toHaveProperty(
      "ariaCurrent",
      "page",
    );
  });
});
