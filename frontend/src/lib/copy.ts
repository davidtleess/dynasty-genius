// H1 shared copy helpers (spec 2026-07-05 §1c). Single source of truth for
// status-token translation and capture-timestamp formatting.
//
// Translation contract: mathematically descriptive, never permissive — a
// caveat must never soften into permission. Unmapped tokens render RAW with a
// console.warn (fail-safe: never crash, never invent copy). Suffixes, dates,
// and position codes are preserved verbatim so precision is never lost.

const EXACT_TOKENS: Record<string, string> = {
  insufficient_history: "Not enough capture history for a comparison window",
  current_not_delta: "Current-state baseline, not today's delta",
  freshness_unverifiable:
    "Freshness unverifiable — the input's capture time could not be confirmed",
  density_baseline_insufficient:
    "Waiver-pool valuation coverage is below the reporting floor; replacement-cost ranges cannot be verified",
  pre_capture_window: "Before the capture window began",
  waiver_range_unavailable: "Waiver range unavailable",
};

// Position-prefixed real shape, e.g. WR_waiver_range_unavailable_recovery_unverifiable
// → "WR waiver range unavailable (recovery_unverifiable)".
const POSITION_WAIVER_PATTERN = /^([A-Z]{2,3})_waiver_range_unavailable_(.+)$/;

export function describeStatusToken(token: string): string {
  const exact = EXACT_TOKENS[token];
  if (exact !== undefined) {
    return exact;
  }
  if (token.startsWith("waiver_range_unavailable:")) {
    return `Waiver range unavailable (${token.slice("waiver_range_unavailable:".length).trim()})`;
  }
  if (token.startsWith("capacity_audit_blocked:")) {
    return `Capacity audit blocked (${token.slice("capacity_audit_blocked:".length).trim()})`;
  }
  if (token.startsWith("league_pulse_artifact_state_")) {
    return `League Pulse artifact state (${token.slice("league_pulse_artifact_state_".length).trim()})`;
  }
  const positionMatch = POSITION_WAIVER_PATTERN.exec(token);
  if (positionMatch) {
    return `${positionMatch[1]} waiver range unavailable (${positionMatch[2]})`;
  }
  console.warn("Unmapped status token", token);
  return token;
}

// Deterministic regardless of host locale/timezone (CI-stable): fixed en-US +
// America/New_York. The exact ISO string belongs in a title attribute at the
// call site; null/undefined → "—"; unparseable input renders unchanged.
const CAPTURE_TIME_FORMAT = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZoneName: "short",
});

export function formatCaptureTimestamp(iso: string | null | undefined): string {
  if (iso === null || iso === undefined) {
    return "—";
  }
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return iso;
  }
  return CAPTURE_TIME_FORMAT.format(new Date(parsed));
}

// The standard non-decision-grade disclosure line (spec §1c, exact string
// LOCKED). The API field decision_supported=false is unchanged — the UI just
// stops quoting the field name at the user.
export const DISCLOSURE_LINE = "Descriptive only — not decision-grade.";
