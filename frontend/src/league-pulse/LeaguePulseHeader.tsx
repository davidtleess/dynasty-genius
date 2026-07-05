import type { LeaguePulseResponse } from "../lib/api";
import { describeStatusToken, formatCaptureTimestamp } from "../lib/copy";

// Honesty band for the League Pulse surface. Anchors the whole surface as
// artifact-state, EXPERIMENTAL, and NOT decision-grade — neutral copy only.
//
// No-Verdict diagnostic-workspace copy: states the descriptive-only guarantee in
// the system's own vocabulary, free of any banned verdict token, so the enforcing
// cordon stays clean. Cockpit-converged at T4c (Gemini framing + Codex validation).
const DIAGNOSTIC_WORKSPACE_COPY =
  "Diagnostic Workspace: Surfaces raw model outputs and market variance. Valuation data is descriptive only, does not nominate players or direct trades, and requires manual qualitative evaluation.";

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
      {/* The not-decision-grade phrase lives ONLY in the standard disclosure
          line below — singular queries on it must stay unambiguous. */}
      <p className="dg-league-pulse__experimental">
        EXPERIMENTAL — a read-only league snapshot.
      </p>
      <p className="dg-league-pulse__diagnostic">{DIAGNOSTIC_WORKSPACE_COPY}</p>
      <p className="dg-league-pulse__asof" title={data.captured_at}>
        as of {formatCaptureTimestamp(data.captured_at)}
      </p>
      {artifactStateCaveat ? (
        <p className="dg-league-pulse__caveat">
          {describeStatusToken(artifactStateCaveat)}
        </p>
      ) : null}
      {withheld > 0 ? (
        <p className="dg-league-pulse__withheld">{withheld} records withheld</p>
      ) : null}
      <p className="dg-league-pulse__grade">Descriptive only — not decision-grade.</p>
      <ul className="dg-league-pulse__sources">
        <li>{schemaVersion(sources.team_posture)}</li>
        <li>{schemaVersion(sources.team_value_matrix)}</li>
        <li>{schemaVersion(sources.league_opportunity)}</li>
      </ul>
    </header>
  );
}
