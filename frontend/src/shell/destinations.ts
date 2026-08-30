// DG-114 — the five destinations (DG091-STUDIO-SPEC.md §4.1).
//
// The rail used to be a list of eleven SURFACES, which is the shape of the
// backend's report catalogue rather than the shape of a manager's morning. This
// module is the one place that maps the surfaces onto the five places a person
// actually goes: Today, Roster, Trades, League, Track record.
//
// IT IS A GROUPING, NOT A ROUTER REWRITE. `?surface=<slug>` still addresses the
// same surfaces it addressed yesterday — a bookmark David saved before this
// ticket lands on the same content after it. What changed is that several
// surfaces now share one rail item, and the ones inside a destination are
// reached by a view switcher instead of by two separate links that looked like
// two separate products.
//
// A surface that belongs to NO destination (the three parked cards, the crew's
// Project Tracker, the asset-primitive capture target) is still reachable at its
// URL and appears in no navigation affordance at all — David's 2026-08-30 panel,
// verbatim option label: "Remove from nav entirely". Roadmap is not product.
import type { Surface } from "./useUrlSurfaceState";

export type DestinationView = {
  surface: Surface;
  /** The view switcher's label. Absent for a destination with one view. */
  label: string;
};

export type Destination = {
  /** The rail label. */
  label: string;
  /** Views in switcher order; the first is where the rail item lands you. */
  views: readonly DestinationView[];
};

export const DESTINATIONS: readonly Destination[] = [
  {
    label: "Today",
    views: [{ surface: "Daily What-Changed", label: "Today" }],
  },
  {
    // Spec §4.1: one roster place. The cut list is a different ORDER of the
    // same roster, not a second product, so it is a view here rather than its
    // own rail item. "Cut list" is the spec's own label, and the surface it
    // opens says in its own words what the order actually is — legality
    // problems first, then scored players lowest-first, then the ones we cannot
    // score — which is NOT a straight most-expendable-first sort, and the chip
    // does not claim it is. (The two views still read two different producers —
    // /api/roster/audit and /api/roster/capacity — and each keeps its own
    // freshness and its own empty states. Merging them into literally one
    // table is a data-surface job, and this ticket does not claim it.)
    label: "Roster",
    views: [
      { surface: "Roster Audit", label: "All players" },
      { surface: "Roster Capacity", label: "Cut list" },
    ],
  },
  {
    label: "Trades",
    views: [
      { surface: "Trade Lab", label: "Build a trade" },
      { surface: "Trade Partners", label: "Trade partners" },
    ],
  },
  {
    label: "League",
    views: [{ surface: "League Pulse", label: "League" }],
  },
  {
    label: "Track record",
    views: [
      { surface: "Model Trust", label: "Model trust" },
      { surface: "Accuracy Tracker", label: "Accuracy tracker" },
    ],
  },
] as const;

/** The destination a surface lives in, or null when it is URL-only. */
export function destinationForSurface(surface: Surface): Destination | null {
  return (
    DESTINATIONS.find((destination) =>
      destination.views.some((view) => view.surface === surface),
    ) ?? null
  );
}
