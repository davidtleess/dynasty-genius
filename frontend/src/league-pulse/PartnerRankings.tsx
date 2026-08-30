import type { LeaguePulsePartnerRanking } from "../lib/api";
import { fieldLabel, valueWord } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

// Partner Rankings — the "who-to-target" context. Presented as MARKET-INFLUENCED
// context, NOT a validated ranking (the partner score is partly market-derived;
// the divergence is descriptive, not a proven edge). Strict per-field allowlists
// keep nested evidence/score noise off the surface.
//
// DG-109: every score name, evidence key and posture value goes through the copy
// dictionary. `partner_score` is still shown as its own labelled pair, distinct
// from the `partner_score_market_influenced` caveat — the two must never collapse
// into one another.

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

// The two posture fields hold enum labels; the row count is a number.
function evidenceValue(key: string, raw: unknown): string {
  return key === "divergence_row_count" ? String(raw) : valueWord(String(raw));
}

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <div className="dg-league-pulse__pair">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function PartnerCard({ ranking }: { ranking: LeaguePulsePartnerRanking }) {
  const score = ranking.score_components as Record<string, number>;
  const evidence = ranking.evidence as Record<string, unknown>;
  const positionScores = (evidence.position_scores ?? {}) as Record<string, unknown>;
  const matched = (ranking.matched_positions ?? []).join(", ");

  return (
    <article className="dg-league-pulse__partner-card">
      <h4 className="dg-league-pulse__partner-name" data-user-text>
        {ranking.counterparty_team_name ?? "Unknown counterparty"}
      </h4>
      <p className="dg-league-pulse__partner-roster">
        Roster {ranking.counterparty_roster_id}
      </p>
      <p className="dg-league-pulse__partner-badge">Market-influenced</p>
      <dl className="dg-league-pulse__partner-fit">
        <Pair
          label={fieldLabel("partner_score")}
          value={ranking.partner_score.toFixed(3)}
        />
      </dl>
      <p className="dg-league-pulse__partner-positions">{matched}</p>

      <dl className="dg-league-pulse__partner-scores">
        {SCORE_KEYS.map((k) => {
          const value = score[k];
          return typeof value === "number" ? (
            <Pair key={k} label={fieldLabel(k)} value={value.toFixed(2)} />
          ) : null;
        })}
      </dl>

      <dl className="dg-league-pulse__partner-evidence">
        {EVIDENCE_KEYS.filter((k) => k in evidence).map((k) => (
          <Pair key={k} label={fieldLabel(k)} value={evidenceValue(k, evidence[k])} />
        ))}
      </dl>

      <ul className="dg-league-pulse__partner-position-scores">
        {POSITIONS.filter((p) => typeof positionScores[p] === "number").map((p) => (
          <li key={p}>
            {p} {(positionScores[p] as number).toFixed(2)}
          </li>
        ))}
      </ul>

      <TokenNotes
        className="dg-league-pulse__partner-caveats"
        tokens={ranking.caveats ?? []}
      />
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
