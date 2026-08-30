// H2 I1 — typed URL surface state (vision spec §4: no react-router; one
// navigateSurface path shared by rail and command palette). I1 scope is
// `?surface=` ONLY — `&player=` hydration is I3-owned and non-I1 params are
// dropped on navigation so URL state never accretes silently.
import { useCallback, useEffect, useState } from "react";

export const SURFACE_SLUGS = {
  "Daily What-Changed": "what-changed",
  "Roster Audit": "roster-audit",
  "Trade Lab": "trade-lab",
  // DG-114: partner rankings move off League Pulse and become the second view
  // of Trades (spec §4.1). A NEW slug — every slug that existed before this
  // ticket still resolves to the surface it always did.
  "Trade Partners": "trade-partners",
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
  navigateSurface: (surface: Surface, options?: { replace?: boolean }) => void;
} {
  const [activeSurface, setActiveSurface] = useState<Surface>(readSurfaceFromLocation);

  // DG-114: `replace` exists for exactly one caller — a navigation made while
  // the player card's own history entry is on top of the stack. Pushing there
  // would strand that entry behind the new surface, so Back would walk through
  // a card that is no longer open. Replacing consumes it instead. Ordinary rail
  // navigation still pushes, so Back still walks surfaces.
  const navigateSurface = useCallback(
    (surface: Surface, options?: { replace?: boolean }) => {
      // The URL carries exactly the I1 contract: `?surface=<slug>` and nothing
      // else — stale non-I1 params (e.g. a pre-I3 `player=`) are dropped.
      const url = `?surface=${slugForSurface(surface)}`;
      if (options?.replace === true) {
        window.history.replaceState(null, "", url);
      } else {
        window.history.pushState(null, "", url);
      }
      setActiveSurface(surface);
    },
    [],
  );

  useEffect(() => {
    function onPopState() {
      setActiveSurface(readSurfaceFromLocation());
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return { activeSurface, navigateSurface };
}
