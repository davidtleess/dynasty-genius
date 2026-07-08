// H2 I1 — typed URL surface state (vision spec §4: no react-router; one
// navigateSurface path shared by rail and command palette). I1 scope is
// `?surface=` ONLY — `&player=` hydration is I3-owned and non-I1 params are
// dropped on navigation so URL state never accretes silently.
import { useCallback, useEffect, useState } from "react";

export const SURFACE_SLUGS = {
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
  // Increment-0 evidence surface: URL-only (no rail button, no palette
  // command) — a developer capture target, not a David surface.
  "Asset Primitive Capture": "asset-primitive-capture",
} as const;

export type Surface = keyof typeof SURFACE_SLUGS;

const DEFAULT_SURFACE: Surface = "Daily What-Changed";

const SLUG_TO_SURFACE = new Map<string, Surface>(
  (Object.entries(SURFACE_SLUGS) as [Surface, string][]).map(([surface, slug]) => [
    slug,
    surface,
  ]),
);

export function slugForSurface(surface: Surface): string {
  return SURFACE_SLUGS[surface];
}

// Invalid or absent slugs fall back to the daily-login default (seed 1).
export function surfaceForSlug(slug: string | null): Surface {
  if (slug === null) {
    return DEFAULT_SURFACE;
  }
  return SLUG_TO_SURFACE.get(slug) ?? DEFAULT_SURFACE;
}

function readSurfaceFromLocation(): Surface {
  const params = new URLSearchParams(window.location.search);
  return surfaceForSlug(params.get("surface"));
}

export function useUrlSurfaceState(): {
  activeSurface: Surface;
  navigateSurface: (surface: Surface) => void;
} {
  const [activeSurface, setActiveSurface] = useState<Surface>(readSurfaceFromLocation);

  const navigateSurface = useCallback((surface: Surface) => {
    // The URL carries exactly the I1 contract: `?surface=<slug>` and nothing
    // else — stale non-I1 params (e.g. a pre-I3 `player=`) are dropped.
    window.history.pushState(null, "", `?surface=${slugForSurface(surface)}`);
    setActiveSurface(surface);
  }, []);

  useEffect(() => {
    function onPopState() {
      setActiveSurface(readSurfaceFromLocation());
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return { activeSurface, navigateSurface };
}
