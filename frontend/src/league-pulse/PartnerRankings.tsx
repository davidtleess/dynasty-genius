import { Fragment } from "react";

import type { LeaguePulsePartnerRanking } from "../lib/api";

// Partner Rankings — the "who-to-target" context. Presented as MARKET-INFLUENCED
// context, NOT a validated ranking (the partner score is partly market-derived;
// the divergence is descriptive, not a proven edge). Strict per-field allowlists
// keep nested evidence/score noise off the surface.

const SCORE_KEYS = [
  "complementarity_score",
  "divergence_density_score",
  "activity_recency_score",
  "posture_alignment_score",
] as const;

const EVIDENCE_KEYS = [
  "perspective_posture",
  "counterparty_posture",
  "divergence_row_count",
] as const;

const POSITIONS = ["QB", "RB", "WR", "TE"] as const;

function PartnerCard({ ranking }: { ranking: LeaguePulsePartnerRanking }) {
  const score = ranking.score_components as Record<string, number>;
  const evidence = ranking.evidence as Record<string, unknown>;
  const positionScores = (evidence.position_scores ?? {}) as Record<string, unknown>;
  const matched = (ranking.matched_positions ?? []).join(", ");

  return (
    <article className="dg-league-pulse__partner-card">
      <h4 className="dg-league-pulse__partner-name">
        {ranking.counterparty_team_name ?? "Unknown counterparty"}
      </h4>
      <p className="dg-league-pulse__partner-roster">
        Roster {ranking.counterparty_roster_id}
      </p>
      <p className="dg-league-pulse__partner-badge">Market-influenced</p>
      <dl className="dg-league-pulse__partner-fit">
        <dt>partner_score</dt>
        <dd>{ranking.partner_score.toFixed(3)}</dd>
      </dl>
      <p className="dg-league-pulse__partner-positions">{matched}</p>

      <dl className="dg-league-pulse__partner-scores">
        {SCORE_KEYS.map((k) => {
          const value = score[k];
          return typeof value === "number" ? (
            <Fragment key={k}>
              <dt>{k}</dt>
              <dd>{value.toFixed(2)}</dd>
            </Fragment>
          ) : null;
        })}
      </dl>

      <dl className="dg-league-pulse__partner-evidence">
        {EVIDENCE_KEYS.filter((k) => k in evidence).map((k) => (
          <Fragment key={k}>
            <dt>{k}</dt>
            <dd>{String(evidence[k])}</dd>
          </Fragment>
        ))}
      </dl>

      <ul className="dg-league-pulse__partner-position-scores">
        {POSITIONS.filter((p) => typeof positionScores[p] === "number").map((p) => (
          <li key={p}>
            {p} {(positionScores[p] as number).toFixed(2)}
          </li>
        ))}
      </ul>

      <ul className="dg-league-pulse__partner-caveats">
        {(ranking.caveats ?? []).map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </article>
  );
}

export function PartnerRankings({
  rankings,
}: {
  rankings: LeaguePulsePartnerRanking[];
}) {
  return (
    <section aria-label="Partner Rankings" className="dg-league-pulse__partners">
      <h3 className="dg-league-pulse__section-heading">Partner Rankings</h3>
      <p className="dg-league-pulse__section-note">
        Market-influenced context — not a validated ranking. The partner score is partly
        market-derived. Two-lane evidence is shown for context.
      </p>
      {rankings.length === 0 ? (
        <p className="dg-league-pulse__empty">No partner ranking context available.</p>
      ) : (
        rankings.map((ranking) => (
          <PartnerCard key={ranking.counterparty_roster_id} ranking={ranking} />
        ))
      )}
    </section>
  );
}
