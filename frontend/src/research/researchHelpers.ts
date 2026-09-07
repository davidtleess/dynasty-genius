// Pure helpers for the research preview (plan T4, 2026-09-06). No React, no fetch: the
// search runs over the league rows the API already serves, and the margin wording never
// turns a rounded value into a direction.

export type SearchableRow = {
  player_id: string;
  name: string;
  position: string;
  team: string | null;
  value: number | null;
};

// Matches name, team or position, case-insensitively. An empty query returns nothing so the
// default view (roster, then leaders) stands. Order is deterministic: value descending
// (absent values last), then name, then player id.
export function filterLeague<T extends SearchableRow>(rows: T[], query: string): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const hit = (r: T) =>
    r.name.toLowerCase().includes(q) ||
    (r.team ?? "").toLowerCase().includes(q) ||
    r.position.toLowerCase() === q ||
    r.position.toLowerCase().includes(q);
  return rows.filter(hit).sort((a, b) => {
    const av = a.value ?? Number.NEGATIVE_INFINITY;
    const bv = b.value ?? Number.NEGATIVE_INFINITY;
    if (bv !== av) return bv - av;
    if (a.name !== b.name) return a.name < b.name ? -1 : 1;
    return a.player_id < b.player_id ? -1 : a.player_id > b.player_id ? 1 : 0;
  });
}

// An exact tie is "equal to reference"; a difference under a thousandth of a point is named
// as within that threshold; any other signed difference keeps its direction.
export function marginLabel(margin: number | null | undefined): string {
  if (margin == null || Number.isNaN(margin)) return "";
  if (margin === 0) return "equal to reference";
  if (Math.abs(margin) < 0.001) return "within 0.001 of reference";
  return margin > 0 ? "above reference" : "below reference";
}

// Enough decimals that the rendered value is never a signed zero: one decimal from 0.1, two
// from 0.01, three from 0.001, and "±<0.001" below that; a signed integer from 1 point.
export function formatMargin(margin: number | null | undefined): string {
  if (margin == null || Number.isNaN(margin)) return "—";
  if (margin === 0) return "0";
  const abs = Math.abs(margin);
  const sign = margin > 0 ? "+" : "-";
  if (abs >= 1) return `${sign}${Math.round(abs)}`;
  if (abs >= 0.1) return `${sign}${abs.toFixed(1)}`;
  if (abs >= 0.01) return `${sign}${abs.toFixed(2)}`;
  if (abs >= 0.001) return `${sign}${abs.toFixed(3)}`;
  return `${sign}<0.001`;
}

export function formatPoints(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toFixed(1);
}
