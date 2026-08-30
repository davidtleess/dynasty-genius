// Shared copy helpers. Single source of truth for status-token translation and
// capture-timestamp formatting.
//
// Translation contract: a caveat must never soften into permission. Unmapped
// tokens are HUMANIZED — underscores to spaces, sentence case — and still fire
// a console.warn so the crew adds a real sentence (DG-111: a raw pipeline key
// is not English and never belongs in body copy). The humanizer only
// REFORMATS: it never adds meaning the token did not carry, and every call
// site keeps the verbatim token reachable (a title attribute or the receipt
// sheet) so precision is preserved, not destroyed. Suffixes, dates, and
// position codes are preserved verbatim in the mapped shapes.

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
  return humanizeToken(token);
}

// Reformat-only fallback: `market_snapshot_stale` -> "Market snapshot stale".
// Adds no meaning; a token that is already a sentence fragment survives as one.
// Exported so a surface can humanize a producer string it renders directly.
export function humanizeToken(token: string): string {
  const words = token.replaceAll("_", " ").trim();
  if (words === "") {
    return token;
  }
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
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

// DG-111 — what replaced the stamp.
//
// "Descriptive only — not decision-grade." used to render on every region of
// every surface (seven times on the front page alone). David repealed that
// register on 2026-08-29: "I don't care to persist the governance of language
// and caveats and lack of overall recommendation from the back end into the
// front end. I'd rather use layman's terms and call a spade a spade."
//
// The API field `decision_supported=false` is UNCHANGED and the honest reading
// of it survives — but as ONE sentence, in plain words, on the two surfaces
// where it actually changes how you read a number: the player card (whose
// projection came from this model) and the Model Trust console (whose subject
// IS this model's standing). One constant so the two can never drift.
export const MODEL_STANDING_SENTENCE =
  "Our model is a sharp second opinion, not a proven market-beater — weigh it accordingly.";
