import { Fragment } from "react";

import type {
  LeaguePulseCard,
  LeaguePulseMarketCard,
  LeaguePulseRecommendedDrop,
} from "../lib/api";

// Opportunity Cards — TWO visually separated lanes (Q3=B). Model-native cards
// carry NO market field (allowlist-enforced). Market-overlay cards live under a
// persistent "descriptive market signal, not a validated edge" banner; each
// surfaces its unvalidated-divergence caveat. Strict per-lane allowlists.

const MODEL_EVIDENCE = [
  "position",
  "perspective_position_z",
  "counterparty_position_z",
  "perspective_surplus_label",
  "counterparty_surplus_label",
] as const;
const MODEL_SCORE = ["fit_score", "feasibility_score"] as const;

const OVERLAY_EVIDENCE = [
  "signal",
  "signal_status",
  "model_minus_market_delta",
  "market_percentile",
  "model_percentile",
  "xvar",
  "raw_xvar",
  "lineup_role",
  "asset_roster_id",
] as const;
const OVERLAY_SCORE = ["fit_score", "divergence_score", "feasibility_score"] as const;

const RECOMMENDED_DROP_BANNER = "Descriptive market signal, not a validated edge.";

type AnyCard = LeaguePulseCard | LeaguePulseMarketCard;

function RecommendedDrop({ drop }: { drop: LeaguePulseRecommendedDrop }) {
  return (
    <div className="dg-league-pulse__recommended-drop">
      <p className="dg-league-pulse__rd-label">recommended_drop</p>
      <p className="dg-league-pulse__rd-name">{drop.full_name}</p>
      <p className="dg-league-pulse__rd-position">{drop.position}</p>
      <dl>
        <dt>cut_priority</dt>
        <dd>{drop.cut_priority}</dd>
      </dl>
      <p className="dg-league-pulse__rd-ir">{drop.ir_compliance_status}</p>
      <ul>
        {(drop.cut_rationale ?? []).map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </div>
  );
}

function OpportunityCard({
  card,
  evidenceKeys,
  scoreKeys,
  recommendedDrop,
}: {
  card: AnyCard;
  evidenceKeys: readonly string[];
  scoreKeys: readonly string[];
  recommendedDrop?: LeaguePulseRecommendedDrop | null;
}) {
  const evidence = card.evidence as Record<string, unknown>;
  const score = card.score_components as Record<string, number>;
  const secondary = card.rationale_secondary ?? [];

  return (
    <article className="dg-league-pulse__opportunity-card">
      <h4 className="dg-league-pulse__opportunity-type">{card.card_type}</h4>
      <dl className="dg-league-pulse__opportunity-score">
        <dt>opportunity_score</dt>
        <dd>{card.opportunity_score.toFixed(3)}</dd>
      </dl>
      <p className="dg-league-pulse__opportunity-rationale">{card.rationale_primary}</p>
      {secondary.length > 0 ? (
        <p className="dg-league-pulse__opportunity-secondary">
          Context: {secondary.join(", ")}
        </p>
      ) : null}

      <dl className="dg-league-pulse__opportunity-evidence">
        {evidenceKeys
          .filter((k) => k in evidence)
          .map((k) => (
            <Fragment key={k}>
              <dt>{k}</dt>
              <dd>{String(evidence[k])}</dd>
            </Fragment>
          ))}
      </dl>

      <dl className="dg-league-pulse__opportunity-components">
        {scoreKeys.map((k) => {
          const value = score[k];
          return typeof value === "number" ? (
            <Fragment key={k}>
              <dt>{k}</dt>
              <dd>{value.toFixed(2)}</dd>
            </Fragment>
          ) : null;
        })}
      </dl>

      <ul className="dg-league-pulse__opportunity-caveats">
        {(card.caveats ?? []).map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>

      {recommendedDrop ? <RecommendedDrop drop={recommendedDrop} /> : null}
    </article>
  );
}

export function OpportunityCards({
  modelNativeCards,
  marketOverlayCards,
}: {
  modelNativeCards: LeaguePulseCard[];
  marketOverlayCards: LeaguePulseMarketCard[];
}) {
  return (
    <>
      <section
        aria-label="Model-native opportunity cards"
        className="dg-league-pulse__model-cards"
      >
        <h3 className="dg-league-pulse__section-heading">
          Model-native opportunity cards
        </h3>
        {modelNativeCards.length === 0 ? (
          <p className="dg-league-pulse__empty">
            No model-native opportunity cards available.
          </p>
        ) : (
          modelNativeCards.map((card) => (
            <OpportunityCard
              key={card.card_id}
              card={card}
              evidenceKeys={MODEL_EVIDENCE}
              scoreKeys={MODEL_SCORE}
            />
          ))
        )}
      </section>

      <section
        aria-label="Market overlay opportunity cards"
        className="dg-league-pulse__market-cards"
      >
        <h3 className="dg-league-pulse__section-heading">
          Market overlay opportunity cards
        </h3>
        <p className="dg-league-pulse__overlay-banner">{RECOMMENDED_DROP_BANNER}</p>
        {marketOverlayCards.length === 0 ? (
          <p className="dg-league-pulse__empty">
            No market overlay opportunity cards available.
          </p>
        ) : (
          marketOverlayCards.map((card) => (
            <OpportunityCard
              key={card.card_id}
              card={card}
              evidenceKeys={OVERLAY_EVIDENCE}
              scoreKeys={OVERLAY_SCORE}
              recommendedDrop={card.recommended_drop ?? null}
            />
          ))
        )}
      </section>
    </>
  );
}
