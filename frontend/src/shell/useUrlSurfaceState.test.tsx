// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  SURFACE_SLUGS,
  slugForSurface,
  surfaceForSlug,
  useUrlSurfaceState,
} from "./useUrlSurfaceState";

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("useUrlSurfaceState", () => {
  it("exposes the H2 I1 typed surface slug map", () => {
    expect(SURFACE_SLUGS).toMatchObject({
      "Daily What-Changed": "what-changed",
      "Roster Audit": "roster-audit",
      "Trade Lab": "trade-lab",
      "Roster Capacity": "roster-capacity",
      "League Pulse": "league-pulse",
      "Model Trust": "model-trust",
      "Accuracy Tracker": "accuracy-tracker",
      "Rookie Board": "rookie-board",
      "Waiver Radar": "waiver-radar",
      "Research Assistant": "research-assistant",
      "Project Tracker": "project-tracker",
    });
    expect(surfaceForSlug("trade-lab")).toBe("Trade Lab");
    expect(slugForSurface("League Pulse")).toBe("league-pulse");
    expect(surfaceForSlug("unknown")).toBe("Daily What-Changed");
  });

  it("initializes from ?surface= and falls back on invalid slugs without player-param support", () => {
    window.history.replaceState(null, "", "/?surface=trade-lab&player=123");

    const { result } = renderHook(() => useUrlSurfaceState());

    expect(result.current.activeSurface).toBe("Trade Lab");
    expect(result.current).not.toHaveProperty("player");

    window.history.replaceState(null, "", "/?surface=not-real");
    const invalid = renderHook(() => useUrlSurfaceState());
    expect(invalid.result.current.activeSurface).toBe("Daily What-Changed");
  });

  it("updates URL state through one navigateSurface function and drops non-I1 params", () => {
    window.history.replaceState(null, "", "/?surface=trade-lab&player=123");

    const { result } = renderHook(() => useUrlSurfaceState());

    act(() => result.current.navigateSurface("Roster Audit"));

    expect(result.current.activeSurface).toBe("Roster Audit");
    expect(window.location.search).toBe("?surface=roster-audit");
  });

  it("reacts to browser popstate", () => {
    window.history.replaceState(null, "", "/?surface=what-changed");

    const { result } = renderHook(() => useUrlSurfaceState());
    act(() => result.current.navigateSurface("Trade Lab"));
    expect(result.current.activeSurface).toBe("Trade Lab");

    act(() => {
      window.history.pushState(null, "", "/?surface=league-pulse");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    expect(result.current.activeSurface).toBe("League Pulse");
  });
});
