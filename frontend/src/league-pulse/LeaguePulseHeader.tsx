import type { LeaguePulseResponse } from "../lib/api";
import { describeStatusToken, formatCaptureTimestamp } from "../lib/copy";

// Header band for the League Pulse surface.
//
// DG-111: three stamps stood here — "EXPERIMENTAL — a read-only league
// snapshot.", the "Diagnostic Workspace…" paragraph, and "Descriptive only —
// not decision-grade." They said the same thing three ways in the system's own
// vocabulary. One sentence replaces all three, and it keeps the two facts that
// were load-bearing: this is a read-only snapshot of the league, and reading a
// team's situation off its roster is not the same as knowing what its manager
// will do.
const LEAGUE_SNAPSHOT_COPY =
  "Your league at a glance — who's contending, who's rebuilding, and who to call. It's a read-only snapshot: we read each roster, we don't read minds.";

function withheldTotal(dropped: LeaguePulseResponse["dropped"]): number {
  return (
    (dropped.market_overlay_cards ?? 0) +
    (dropped.model_native_cards ?? 0) +
    (dropped.partner_rankings ?? 0) +
    (dropped.roster_capacity_candidate_pools ?? 0) +
    (dropped.team_postures ?? 0) +
    (dropped.team_values ?? 0)
  );
}

function schemaVersion(source: Record<string, unknown>): string {
  return String(source.schema_version ?? "");
}

export function LeaguePulseHeader({ data }: { data: LeaguePulseResponse }) {
  const withheld = withheldTotal(data.dropped);
  const artifactStateCaveat = (data.caveats ?? []).find((c) =>
    c.startsWith("league_pulse_artifact_state_"),
  );
  const sources = data.source_artifacts;

  return (
    // biome-ignore lint/a11y/noInteractiveElementToNoninteractiveRole: <header> is a banner landmark (not interactive); explicit role="banner"+aria-label names it for the contract test, and <div role="banner"> trips useSemanticElements instead (AppShell Trust-strip pattern).
    <header
      role="banner"
      aria-label="League Pulse status"
      className="dg-league-pulse__header"
    >
      <h2 className="dg-league-pulse__heading">League Pulse</h2>
      <p className="dg-league-pulse__diagnostic">{LEAGUE_SNAPSHOT_COPY}</p>
      <p className="dg-league-pulse__asof" title={data.captured_at}>
        as of {formatCaptureTimestamp(data.captured_at)}
      </p>
      {artifactStateCaveat ? (
        <p className="dg-league-pulse__caveat" title={artifactStateCaveat}>
          {describeStatusToken(artifactStateCaveat)}
        </p>
      ) : null}
      {withheld > 0 ? (
        <p className="dg-league-pulse__withheld">
          {withheld} records were dropped as unreadable and are not shown below.
        </p>
      ) : null}
      <ul className="dg-league-pulse__sources">
        <li>{schemaVersion(sources.team_posture)}</li>
        <li>{schemaVersion(sources.team_value_matrix)}</li>
        <li>{schemaVersion(sources.league_opportunity)}</li>
      </ul>
    </header>
  );
}
