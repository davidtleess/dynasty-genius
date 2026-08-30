import type {
  LeaguePulseCapacityCandidatePool,
  LeaguePulseCard,
  LeaguePulseCardSectionCount,
  LeaguePulseMarketCard,
} from "../lib/api";
import { describeToken, fieldLabel, valueWord } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

// Opportunity Cards (No-Verdict T4b) — TWO visually separated lanes (hard
// scale-separation, allowlist-enforced): model-native cards carry NO market
// field; market-overlay cards live under a "descriptive signal, not a validated
// edge" banner. WITHIN each lane, cards group into transparent sort-key
// sub-sections, each disclosing a non-binding "Showing X of Y" completeness
// count. No composite score; sort_value renders in-line with its metric label
// (never a ranked badge). evidence_status renders neutral. The descriptive
// roster-capacity pool appears ONLY on UNROSTERED_MODEL_MARKET_DIVERGENCE cards,
// as a flat, unselected list — never a nominated cut.

const MODEL_EVIDENCE = [
  "position",
  "perspective_position_z",
  "counterparty_position_z",
  "perspective_surplus_label",
  "counterparty_surplus_label",
  "positional_z_differential",
] as const;
const MODEL_SCORE = ["fit_score", "feasibility_score"] as const;

const OVERLAY_EVIDENCE = [
  "signal",
  "evidence_status",
  "model_minus_market_delta",
  "market_percentile",
  "model_percentile",
  "asset_xvar",
  "lineup_role",
] as const;
const OVERLAY_SCORE = ["fit_score", "divergence_score", "feasibility_score"] as const;

const MARKET_LANE_BANNER = "Descriptive market signal, not a validated edge.";
const SORT_CAVEAT =
  "A larger value reflects a wider mathematical magnitude, not a prioritized transaction order.";
// Studio spec §6 voice guide, verbatim rewrite of a string seen on screen:
// "Tank DellWRValuation Unavailable - evaluate qualitatively" →
// "Tank Dell — no price available right now; judge this one yourself."
const UNVALUED_COPY = "No price available right now — judge this one yourself.";
const IR_BLOCKER_COPY = "IR-conflict non-dismissible blocker";

type AnyCard = LeaguePulseCard | LeaguePulseMarketCard;

// An evidence value is either an enum the dictionary speaks or a plain number.
// Absence renders NOTHING — the old `String(evidence[k])` printed the literal
// "null" for `lineup_role` on every non-taxi card.
const NUMERIC_EVIDENCE = new Set([
  "perspective_position_z",
  "counterparty_position_z",
  "positional_z_differential",
  "model_minus_market_delta",
  "market_percentile",
  "model_percentile",
  "asset_xvar",
]);

function evidenceValue(key: string, raw: unknown): string | null {
  if (raw === null || raw === undefined || raw === "") return null;
  if (key === "position") return String(raw);
  if (NUMERIC_EVIDENCE.has(key)) return String(raw);
  return valueWord(String(raw));
}

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <div className="dg-league-pulse__pair">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function groupBySortKey<T extends AnyCard>(cards: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>();
  for (const card of cards) {
    const existing = groups.get(card.sort_key);
    if (existing) {
      existing.push(card);
    } else {
      groups.set(card.sort_key, [card]);
    }
  }
  return [...groups.entries()];
}

function RosterCapacityPool({ pool }: { pool: LeaguePulseCapacityCandidatePool }) {
  const items = pool.items ?? [];
  const hasHardConflict = items.some(
    (item) => item.capacity_conflict_status === "hard_roster_rules_conflict",
  );
  const toneClass = hasHardConflict
    ? "dg-league-pulse__capacity--blocker"
    : "dg-league-pulse__capacity--neutral";

  return (
    <div
      data-testid="roster-capacity-candidates"
      className={`dg-league-pulse__capacity ${toneClass}`}
    >
      <p className="dg-league-pulse__capacity-label">Roster capacity candidates</p>
      {hasHardConflict ? (
        <p className="dg-league-pulse__capacity-blocker">{IR_BLOCKER_COPY}</p>
      ) : null}
      <ul className="dg-league-pulse__capacity-list">
        {items.map((item) => (
          <li key={item.sleeper_player_id} className="dg-league-pulse__capacity-row">
            <span className="dg-league-pulse__capacity-name" data-user-text>
              {item.full_name}
            </span>
            <span className="dg-league-pulse__capacity-position">{item.position}</span>
            {item.value_status === "unvalued" ? (
              <span className="dg-league-pulse__capacity-unvalued">
                {UNVALUED_COPY}
              </span>
            ) : (
              <span className="dg-league-pulse__capacity-xvar">
                {`Value over replacement: ${item.xvar_pct}th percentile`}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function OpportunityCard({
  card,
  evidenceKeys,
  scoreKeys,
}: {
  card: AnyCard;
  evidenceKeys: readonly string[];
  scoreKeys: readonly string[];
}) {
  const evidence = card.evidence as Record<string, unknown>;
  const score = card.score_components as Record<string, number>;
  const secondary = card.rationale_secondary ?? [];
  const pool = (card as LeaguePulseMarketCard).roster_capacity_candidates;
  const showsCapacity =
    card.card_type === "UNROSTERED_MODEL_MARKET_DIVERGENCE" && pool != null;

  return (
    <article className="dg-league-pulse__opportunity-card">
      <p className="dg-league-pulse__opportunity-category">
        {valueWord(card.sort_key)}
      </p>
      <h4 className="dg-league-pulse__opportunity-type">{valueWord(card.card_type)}</h4>
      <p className="dg-league-pulse__sort-metric">
        {`Sorted on ${fieldLabel(card.sort_key)}: ${card.sort_value.toFixed(2)}`}
      </p>
      <p className="dg-league-pulse__evidence-status dg-league-pulse__evidence-status--neutral">
        {`Evidence behind it: ${valueWord(card.evidence_status)}`}
      </p>
      <p className="dg-league-pulse__opportunity-rationale">
        {describeToken(card.rationale_primary)}
      </p>
      {secondary.length > 0 ? (
        <p className="dg-league-pulse__opportunity-secondary">
          Context: {secondary.map((token) => describeToken(token)).join(" ")}
        </p>
      ) : null}

      <dl className="dg-league-pulse__opportunity-evidence">
        {evidenceKeys
          .filter((k) => k in evidence)
          .map((k) => {
            const shown = evidenceValue(k, evidence[k]);
            return shown === null ? null : (
              <Pair key={k} label={fieldLabel(k)} value={shown} />
            );
          })}
      </dl>

      <dl className="dg-league-pulse__opportunity-components">
        {scoreKeys.map((k) => {
          const value = score[k];
          return typeof value === "number" ? (
            <Pair key={k} label={fieldLabel(k)} value={value.toFixed(2)} />
          ) : null;
        })}
      </dl>

      <TokenNotes
        className="dg-league-pulse__opportunity-caveats"
        tokens={card.caveats ?? []}
      />

      {showsCapacity ? <RosterCapacityPool pool={pool} /> : null}
    </article>
  );
}

function SortKeySection({
  cards,
  sectionCount,
  evidenceKeys,
  scoreKeys,
}: {
  cards: AnyCard[];
  sectionCount: LeaguePulseCardSectionCount | undefined;
  evidenceKeys: readonly string[];
  scoreKeys: readonly string[];
}) {
  const shown = sectionCount?.shown_count ?? cards.length;
  const total = sectionCount?.total_count ?? cards.length;

  return (
    <div className="dg-league-pulse__sort-section">
      <p className="dg-league-pulse__sort-section-count">
        {`Showing ${shown} of ${total} matches in this category`}
      </p>
      <p className="dg-league-pulse__sort-caveat">{SORT_CAVEAT}</p>
      {cards.map((card) => (
        <OpportunityCard
          key={card.card_id}
          card={card}
          evidenceKeys={evidenceKeys}
          scoreKeys={scoreKeys}
        />
      ))}
    </div>
  );
}

export function OpportunityCards({
  cardSectionCounts,
  modelNativeCards,
  marketOverlayCards,
}: {
  cardSectionCounts: LeaguePulseCardSectionCount[];
  modelNativeCards: LeaguePulseCard[];
  marketOverlayCards: LeaguePulseMarketCard[];
}) {
  const countBySortKey = new Map(
    (cardSectionCounts ?? []).map((count) => [count.sort_key, count]),
  );

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
          groupBySortKey(modelNativeCards).map(([sortKey, cards]) => (
            <SortKeySection
              key={sortKey}
              cards={cards}
              sectionCount={countBySortKey.get(sortKey)}
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
        <p className="dg-league-pulse__overlay-banner">{MARKET_LANE_BANNER}</p>
        {marketOverlayCards.length === 0 ? (
          <p className="dg-league-pulse__empty">
            No market overlay opportunity cards available.
          </p>
        ) : (
          groupBySortKey(marketOverlayCards).map(([sortKey, cards]) => (
            <SortKeySection
              key={sortKey}
              cards={cards}
              sectionCount={countBySortKey.get(sortKey)}
              evidenceKeys={OVERLAY_EVIDENCE}
              scoreKeys={OVERLAY_SCORE}
            />
          ))
        )}
      </section>
    </>
  );
}
