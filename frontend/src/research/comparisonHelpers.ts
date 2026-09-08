// DG-181 — pure helpers for the roster-spot comparison (plan RosterComparison.plan.md, 2026-09-07).
// No React, no fetch. The API owns every total; the only arithmetic here is the signed difference
// between two values that are both shown, and it is only spoken for two players at the SAME
// position. Across positions both forecasts are shown and no winner is named. Nothing here turns
// a points difference into a lineup gain, dynasty value, a breakout probability or an add/drop call.
import { formatAvailablePoints } from "./availableHelpers";

export type ComparisonSeason = {
  season: number;
  points: number | null;
  estimate_class: string | null;
};
export type ComparisonPlayer = {
  sleeper_id: string;
  name: string;
  position: string;
  team: string | null;
  population: string;
  status: string;
  now_points: number | null;
  future_points: number | null;
  seasons: ComparisonSeason[];
  starting_estimate: boolean;
  missing_reason: string | null;
  evidence_note: string;
  /** Roster rows only: true when the saved roster keeps him on taxi or IR (report list); a label,
   *  not lineup eligibility. Absent or null when the source list is absent; available rows null. */
  taxi_or_reserve?: boolean | null;
};
export type ComparisonSource = {
  report_run: string;
  catalog_run: string;
  catalog_content_sha256?: string | undefined;
  report_sha256: string;
  ownership_as_of: string | null;
  nfl_status_as_of: string | null;
};
export type ComparisonPayload = {
  source: ComparisonSource;
  forecast_years: number[];
  future_years: number[];
  scoring_note: string;
  available: ComparisonPlayer[];
  roster: ComparisonPlayer[];
};

export type PeriodKey = "now_points" | "future_points";
export type Period = { key: PeriodKey; label: string };

// One short line beside the numbers; the scoring and evidence specifics live in the disclosure.
export const CAVEAT =
  "Projected production; your lineup and roster needs still matter.";

// The current season is the first forecast year; the future span is the first to last future year.
export function periodsFor(p: { forecast_years: number[]; future_years: number[] }): {
  now: Period;
  future: Period;
} {
  const first = p.future_years[0];
  const last = p.future_years[p.future_years.length - 1];
  return {
    now: { key: "now_points", label: String(p.forecast_years[0] ?? "") },
    future: {
      key: "future_points",
      label:
        first === undefined ? "" : last === first ? String(first) : `${first}–${last}`,
    },
  };
}

// A value takes part in arithmetic only when it is a finite number; NaN, Infinity and strings
// are treated as missing rather than becoming a zero or a sentence.
export function finitePoints(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function findPlayer(
  list: ComparisonPlayer[],
  id: string | null,
): ComparisonPlayer | null {
  if (id === null) return null;
  return list.find((p) => p.sleeper_id === id) ?? null;
}

const byName = (a: ComparisonPlayer, b: ComparisonPlayer) =>
  a.name < b.name
    ? -1
    : a.name > b.name
      ? 1
      : a.sleeper_id < b.sleeper_id
        ? -1
        : a.sleeper_id > b.sleeper_id
          ? 1
          : 0;

// Name, team or position, case-insensitively; alphabetical so the list never ranks anyone.
export function searchPlayers(
  list: ComparisonPlayer[],
  query: string,
  opts: { limit?: number; allWhenEmpty?: boolean } = {},
): { matches: ComparisonPlayer[]; total: number } {
  const limit = opts.limit ?? 12;
  const q = query.trim().toLowerCase();
  if (!q && !opts.allWhenEmpty) return { matches: [], total: 0 };
  const hits = (
    q
      ? list.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            (p.team ?? "").toLowerCase().includes(q) ||
            p.position.toLowerCase().includes(q),
        )
      : [...list]
  ).sort(byName);
  return { matches: hits.slice(0, limit), total: hits.length };
}

// Sign plus the same never-prints-as-zero precision the catalog uses for values.
export function formatSignedPoints(diff: number): string {
  if (diff === 0) return "0.0";
  const body = formatAvailablePoints(Math.abs(diff));
  return `${diff > 0 ? "+" : "-"}${body.replace(/^[+-]/, "")}`;
}

export type Verdict =
  | { kind: "cross_position"; sentence: string }
  | { kind: "missing"; sentence: string }
  | {
      kind: "same_position";
      diff: number;
      direction: "higher" | "lower" | "tie";
      sentence: string;
    };

export function compareForecasts(
  a: ComparisonPlayer,
  b: ComparisonPlayer,
  period: Period,
): Verdict {
  if (a.position !== b.position) {
    return {
      kind: "cross_position",
      sentence: `Different positions (${a.position} vs ${b.position}): raw point totals alone do not settle this roster choice.`,
    };
  }
  const av = finitePoints(a[period.key]);
  const bv = finitePoints(b[period.key]);
  if (av === null || bv === null) {
    const who = [av === null ? a.name : null, bv === null ? b.name : null]
      .filter((n): n is string => n !== null)
      .join(" or ");
    return {
      kind: "missing",
      sentence: `No ${period.label} forecast for ${who}, so no comparison for that period.`,
    };
  }
  const shown = `(${formatAvailablePoints(av)} vs ${formatAvailablePoints(bv)})`;
  const diff = av - bv;
  // Two finite values can still overflow when subtracted; that is a refusal, never a winner or a zero.
  if (!Number.isFinite(diff)) {
    return {
      kind: "missing",
      sentence: `The ${period.label} forecasts for ${a.name} and ${b.name} cannot be compared: their difference is not a finite number.`,
    };
  }
  if (diff === 0) {
    return {
      kind: "same_position",
      diff,
      direction: "tie",
      sentence: `For ${period.label}, the two forecasts are an exact tie ${shown}.`,
    };
  }
  const direction = diff > 0 ? "higher" : "lower";
  const tail = Math.abs(diff) < 1 ? ", a difference under one point." : ".";
  return {
    kind: "same_position",
    diff,
    direction,
    // Prose carries the magnitude; the sign is already in the word. The signed delta belongs in
    // a numeric column, not a sentence that would read "lower by -41.3".
    sentence: `For ${period.label}, ${a.name}'s forecast is ${direction} than ${b.name}'s by ${formatAvailablePoints(Math.abs(diff))} points ${shown}${tail}`,
  };
}

// Dates are humanized here only; the API serves them as captured. An unparseable string is
// shown as it came rather than invented.
export function humanizeDate(s: string | null | undefined): string {
  if (s == null || s === "") return "—";
  const trimmed = s.replace(/(\.\d{3})\d+/, "$1");
  const t = Date.parse(trimmed);
  if (Number.isNaN(t)) return s;
  const text = new Date(t).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
  return `${text} UTC`;
}

const STATUS_WORDS: Record<string, string> = {
  active: "active",
  practice_squad: "practice squad",
  injured_reserve: "injured reserve",
  cut: "cut",
  retired: "retired",
  unknown: "unknown identity",
};
const ROSTER_PLAIN = new Set(["", "rostered", "owned"]);

export function statusWord(p: ComparisonPlayer, side: "available" | "roster"): string {
  const word = STATUS_WORDS[p.status] ?? p.status.replace(/_/g, " ");
  const parts: string[] = [];
  if (side === "available") {
    parts.push(word);
    if (p.population !== "default")
      parts.push("outside the default available pool; pickup eligibility not asserted");
  } else {
    parts.push("on your roster");
    if (!ROSTER_PLAIN.has(p.status)) parts.push(word);
  }
  if (p.starting_estimate) parts.push("starting estimate");
  return parts.join(" · ");
}

// The sidecar's class names, said the way a manager reads them: where a starting estimate's
// year came from, not the producer's vocabulary.
const CLASS_WORDS: Record<string, string> = {
  cold_start_candidate: "draft-based starting estimate",
  baseline_research_candidate: "historical position average",
  unsupported: "not estimated by the producer",
};

export function classWord(c: string | null | undefined): string | null {
  if (c == null || c === "") return null;
  return CLASS_WORDS[c] ?? c.replace(/_/g, " ");
}
