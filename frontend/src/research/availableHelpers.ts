// Pure helpers for the Available players tab (plan T4, 2026-09-06; root's frontend review 2026-09-07).
// No React, no fetch. Ownership and NFL status filter AVAILABILITY only; they never change a
// forecast. Sorting states its basis; exact ties are named on THAT basis; rows without a value
// for the selected ordering form their own tail with the specific reason; the watchlist is
// David's local shortlist keyed by stable Sleeper id with minimal identity metadata so a watched
// id that leaves the census stays visible as unresolved instead of vanishing.

export type SeasonForecast = {
  season: number;
  e_points: number;
  p_appear: number | null;
  e_points_given_appear: number | null;
  e_games: number | null;
};
export type AvailableRow = {
  sleeper_id: string;
  player_id: string | null;
  name: string;
  league_position: string;
  fantasy_positions: string;
  availability_class: string;
  population: string; // default | cut | retired | unknown | owned | unresolved (watched, not in the census)
  nfl_team: string | null;
  nfl_status_raw: string | null;
  now_points: number | null;
  future_points: number | null;
  future_years: number[];
  future_reason: string | null;
  missing_reason: string | null;
  impact: { h2: number | null; h5: number | null };
  forecast: { producer: string; seasons: SeasonForecast[] } | null;
  owned_now?: boolean;
  recovered?: boolean;
  forecast_path?: { status: string; years_present: number[] };
  /** root-accepted cold-start research candidate (new-only); per-year class by season */
  starting_estimate?: boolean;
  estimate_classes?: Record<string, string>;
};

export const DEFAULT_STATUSES = [
  "active",
  "practice_squad",
  "injured_reserve",
] as const;
export const ALL_STATUSES = [...DEFAULT_STATUSES, "cut", "retired", "unknown"] as const;
export const POSITIONS = ["QB", "RB", "WR", "TE"] as const;

export type Filters = {
  query?: string;
  positions?: string[];
  /** undefined = the default pool; an explicitly empty list matches nothing. */
  statuses?: string[];
  watchedOnly?: boolean;
  missingOnly?: boolean;
  watched?: Set<string>;
};

// A row has a forecast when the producer's season path is present or a current-year value is.
export function hasForecast(r: AvailableRow): boolean {
  return r.forecast !== null || r.now_points !== null;
}

export function filterAvailable(rows: AvailableRow[], f: Filters): AvailableRow[] {
  const q = (f.query ?? "").trim().toLowerCase();
  const statuses = new Set(f.statuses === undefined ? DEFAULT_STATUSES : f.statuses);
  const positions = f.positions && f.positions.length > 0 ? new Set(f.positions) : null;
  return rows.filter((r) => {
    if (!statuses.has(r.availability_class)) return false;
    if (positions && !positions.has(r.league_position)) return false;
    if (f.watchedOnly && !(f.watched?.has(r.sleeper_id) ?? false)) return false;
    if (f.missingOnly && hasForecast(r)) return false;
    if (q) {
      const hit =
        r.name.toLowerCase().includes(q) ||
        (r.nfl_team ?? "").toLowerCase().includes(q) ||
        r.league_position.toLowerCase().includes(q);
      if (!hit) return false;
    }
    return true;
  });
}

export type SortBasis = "now" | "future" | "impact2" | "impact5" | "name";
export const BASIS_LABELS: Record<SortBasis, string> = {
  now: "2026 projected points (championship window)",
  future: "projected points 2027–2030 summed",
  impact2: "two-year impact above the reference",
  impact5: "five-year impact above the reference",
  name: "name",
};
export type RankedRow = {
  row: AvailableRow;
  value: number | null;
  tied_with: string[];
};
export type MissingRow = { row: AvailableRow; reason: string };
export type Sorted = {
  basis: SortBasis;
  basis_label: string;
  ranked: RankedRow[];
  /** Rows with no value for THIS ordering, each with the specific reason; never treated as zero. */
  missing: MissingRow[];
};

export function keyFor(r: AvailableRow, basis: SortBasis): number | null {
  switch (basis) {
    case "now":
      return r.now_points;
    case "future":
      return r.future_points;
    case "impact2":
      return r.impact.h2;
    case "impact5":
      return r.impact.h5;
    default:
      return null;
  }
}

const NO_FORECAST = "no forecast from the selected producers; no reason stated";
const RECOVERED_NO_IMPACT =
  "recovered forecast: not among the accepted board rows, so it has no impact number";

// Why a row has no value for the selected ordering — the producer's or the catalog's own words.
export function missingReasonFor(r: AvailableRow, basis: SortBasis): string {
  if (!hasForecast(r)) return r.missing_reason ?? NO_FORECAST;
  switch (basis) {
    case "future":
      return r.future_reason ?? r.missing_reason ?? "future total undefined";
    case "impact2":
    case "impact5":
      if (r.starting_estimate)
        return "starting estimate: no impact number is fabricated for a research candidate";
      return r.recovered
        ? RECOVERED_NO_IMPACT
        : "no impact number on the accepted board";
    default:
      return r.missing_reason ?? "no value in the producer's path for this year";
  }
}

const byName = (a: AvailableRow, b: AvailableRow) =>
  a.name < b.name
    ? -1
    : a.name > b.name
      ? 1
      : a.sleeper_id < b.sleeper_id
        ? -1
        : a.sleeper_id > b.sleeper_id
          ? 1
          : 0;

// Exact ties in the basis are broken by name then id and every member of a tie names the others.
export function sortAvailable(rows: AvailableRow[], basis: SortBasis): Sorted {
  if (basis === "name") {
    const all = [...rows].sort(byName);
    return {
      basis,
      basis_label: BASIS_LABELS.name,
      ranked: all
        .filter(hasForecast)
        .map((row) => ({ row, value: null, tied_with: [] })),
      missing: all
        .filter((r) => !hasForecast(r))
        .map((row) => ({ row, reason: missingReasonFor(row, basis) })),
    };
  }
  const withValue: { row: AvailableRow; value: number }[] = [];
  const missing: MissingRow[] = [];
  for (const r of rows) {
    const v = keyFor(r, basis);
    if (v === null || Number.isNaN(v))
      missing.push({ row: r, reason: missingReasonFor(r, basis) });
    else withValue.push({ row: r, value: v });
  }
  withValue.sort((a, b) =>
    b.value !== a.value ? b.value - a.value : byName(a.row, b.row),
  );
  const groups = new Map<number, string[]>();
  for (const x of withValue)
    groups.set(x.value, [...(groups.get(x.value) ?? []), x.row.sleeper_id]);
  const ranked = withValue.map((x) => ({
    row: x.row,
    value: x.value,
    tied_with: (groups.get(x.value) ?? []).filter((id) => id !== x.row.sleeper_id),
  }));
  return {
    basis,
    basis_label: BASIS_LABELS[basis],
    ranked,
    missing: missing.sort((a, b) => byName(a.row, b.row)),
  };
}

// ── display: a nonzero value never prints as zero ───────────────────────────────────────────
// The board's formatter rounds to one decimal; here a −0.035 must not read "-0.0" beside a true
// 0.0. Ordinary values keep one decimal; under 0.1 the precision grows until the sign shows.
export function formatAvailablePoints(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  if (v === 0) return "0.0";
  if (Math.abs(v) >= 0.1) return v.toFixed(1);
  for (const d of [2, 3, 4]) {
    const s = v.toFixed(d);
    if (Number(s) !== 0) return s;
  }
  return v > 0 ? "+<0.0001" : "-<0.0001";
}

// ── watchlist: David's local shortlist by stable Sleeper id ────────────────────────────────
export const WATCHLIST_KEY = "dg178.watchlist";
export type WatchEntry = {
  name: string | null;
  position: string | null;
  team: string | null;
  watched_at: string | null;
};
export type Watchlist = Map<string, WatchEntry>;
type StorageLike = {
  getItem: (k: string) => string | null;
  setItem: (k: string, v: string) => void;
};
const EMPTY_ENTRY: WatchEntry = {
  name: null,
  position: null,
  team: null,
  watched_at: null,
};

const validId = (x: unknown): x is string =>
  typeof x === "string" && x.trim() !== "" && x === x.trim();
const strOrNull = (x: unknown): string | null | undefined =>
  x === null || x === undefined ? null : typeof x === "string" ? x : undefined;

function entryFrom(raw: unknown): WatchEntry | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const o = raw as Record<string, unknown>;
  const name = strOrNull(o.name);
  const position = strOrNull(o.position);
  const team = strOrNull(o.team);
  const watched_at = strOrNull(o.watched_at);
  if (
    name === undefined ||
    position === undefined ||
    team === undefined ||
    watched_at === undefined
  )
    return null;
  return { name, position, team, watched_at };
}

function repairNotice(kept: number, dropped: number): string | null {
  if (dropped === 0) return null;
  if (kept === 0)
    return `The saved watchlist had ${dropped} unreadable ${dropped === 1 ? "entry" : "entries"} and no readable one; watch players again to rebuild it.`;
  return `The saved watchlist had ${dropped} unreadable ${dropped === 1 ? "entry, which was" : "entries, which were"} ignored; the ${kept} readable ${kept === 1 ? "one was" : "ones were"} kept.`;
}

export function loadWatchlist(storage: StorageLike): {
  entries: Watchlist;
  notice: string | null;
} {
  let raw: string | null;
  try {
    raw = storage.getItem(WATCHLIST_KEY);
  } catch {
    return {
      entries: new Map(),
      notice:
        "Watchlist storage is unavailable in this browser; the shortlist will not persist.",
    };
  }
  if (raw == null) return { entries: new Map(), notice: null };
  let parsed: { version?: number; ids?: unknown; entries?: unknown };
  try {
    parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") throw new Error("shape");
  } catch {
    return {
      entries: new Map(),
      notice:
        "The saved watchlist could not be read and was ignored; watch players again to rebuild it.",
    };
  }
  const entries: Watchlist = new Map();
  let dropped = 0;
  if (parsed.version === 1 && Array.isArray(parsed.ids)) {
    for (const id of parsed.ids) {
      if (validId(id)) entries.set(id, { ...EMPTY_ENTRY });
      else dropped += 1;
    }
  } else if (
    parsed.version === 2 &&
    parsed.entries &&
    typeof parsed.entries === "object" &&
    !Array.isArray(parsed.entries)
  ) {
    for (const [id, raw] of Object.entries(parsed.entries as Record<string, unknown>)) {
      const entry = validId(id) ? entryFrom(raw) : null;
      if (entry) entries.set(id, entry);
      else dropped += 1;
    }
  } else {
    return {
      entries: new Map(),
      notice:
        "The saved watchlist could not be read and was ignored; watch players again to rebuild it.",
    };
  }
  return {
    entries: new Map([...entries].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))),
    notice: repairNotice(entries.size, dropped),
  };
}

export function saveWatchlist(storage: StorageLike, entries: Watchlist): boolean {
  try {
    const sorted = Object.fromEntries(
      [...entries]
        .filter(([id]) => validId(id))
        .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)),
    );
    storage.setItem(WATCHLIST_KEY, JSON.stringify({ version: 2, entries: sorted }));
    return true;
  } catch {
    return false;
  }
}

// A watched player stays on the list; his availability is said plainly when it changed, and a
// watched id the current census does not carry is unresolved, never silently lost.
export function watchStatus(row: AvailableRow | undefined, watched: boolean): string {
  if (!watched) return "";
  if (!row || row.population === "unresolved")
    return "watched · not in the current census; identity unresolved";
  if (row.owned_now) return "watched · now owned in your league";
  if (row.population !== "default")
    return `watched · left the default pool (${row.availability_class.replace(/_/g, " ")})`;
  return "watched · available";
}

// A placeholder row for a watched id the catalog does not carry, built from the stored metadata.
export function unresolvedRow(id: string, entry: WatchEntry): AvailableRow {
  return {
    sleeper_id: id,
    player_id: null,
    name: entry.name ?? `Sleeper id ${id}`,
    league_position: entry.position ?? "?",
    fantasy_positions: "",
    availability_class: "unknown",
    population: "unresolved",
    nfl_team: entry.team,
    nfl_status_raw: null,
    now_points: null,
    future_points: null,
    future_years: [],
    future_reason: null,
    missing_reason: `not in the current census${entry.watched_at ? ` (watched ${entry.watched_at.slice(0, 10)})` : ""}; identity unresolved, no forecast shown`,
    impact: { h2: null, h5: null },
    forecast: null,
  };
}
