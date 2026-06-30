import type { LeaguePulseResponse } from "../lib/api";

// Honesty band for the League Pulse surface. Anchors the whole surface as
// artifact-state, EXPERIMENTAL, and NOT decision-grade — neutral copy only.

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
      <p className="dg-league-pulse__experimental">
        EXPERIMENTAL — not decision-grade. This is a read-only league snapshot, not a
        recommendation.
      </p>
      <p className="dg-league-pulse__asof">as of {data.captured_at}</p>
      {artifactStateCaveat ? (
        <p className="dg-league-pulse__caveat">{artifactStateCaveat}</p>
      ) : null}
      {withheld > 0 ? (
        <p className="dg-league-pulse__withheld">{withheld} records withheld</p>
      ) : null}
      <p className="dg-league-pulse__grade">decision_supported=false</p>
      <ul className="dg-league-pulse__sources">
        <li>{schemaVersion(sources.team_posture)}</li>
        <li>{schemaVersion(sources.team_value_matrix)}</li>
        <li>{schemaVersion(sources.league_opportunity)}</li>
      </ul>
    </header>
  );
}
