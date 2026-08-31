import type { LeaguePulsePartnerRanking } from "../lib/api";
import { fieldLabel, postureClause, UNPLACED_POSTURE } from "../lib/copy";
import { FieldReceipt } from "../ui/Receipt";
import { TokenNotes } from "../ui/TokenNotes";
import "./PartnerRankings.css";

// ─────────────────────────────────────────────────────────────────────────────
// WHO TO CALL — the partner rankings, rewritten to answer the question a
// manager actually opens this page with.
//
// DG-119. Measured on the live product at 1440 the day this was written: 6,401
// pixels of page for eleven partners, each one a flat ~90px stack of
// label-over-value pairs with no card frame — "Roster 7", "Market-influenced",
// "Trade-fit score 2.091", "RB, WR", four naked decimals, two posture words, a
// row count, per-position decimals, and THE SAME CAVEAT SENTENCE ON ALL ELEVEN
// CARDS. Nothing on that page told David who to call or why.
//
// WHAT EACH NUMBER IS, read out of league_opportunity_map.py rather than out of
// a plausible reading of the field names. Every sentence below is entailed by
// one of these lines and by nothing else:
//
//   matched_positions          :170-175. A position joins this list ONLY where
//                              your positional z <= -0.75 AND theirs >= +0.75.
//                              That gate IS "thin on your side, deep on theirs"
//                              — the same thresholds `_position_label` uses to
//                              call a group deficit ("Thin") or surplus
//                              ("Deep") — so the sentence states the gate, not
//                              an interpretation of it. An EMPTY list is a
//                              measured negative: the loop ran over all four
//                              skill positions and none qualified.
//
//   complementarity_score      :177. max() of the matched positions' scores,
//                              default 0.0. So a 0.0 here always coincides with
//                              an empty matched_positions, and both say the
//                              same measured thing.
//
//   divergence_density_score   :184. clamp(len(divergence_rows) / 5). The rows
//                              are that roster's players whose market signal is
//                              MODEL_HIGH_MARKET_LOW or MODEL_LOW_MARKET_HIGH
//                              (:178-183). We print the COUNT, which is the
//                              fact; the clamped score is a receipt line. A
//                              ZERO IS LIST ABSENCE, NOT AGREEMENT: the rows
//                              come from `_rostered_market_rows` (:33-41), so a
//                              roster missing from the divergence artifact —
//                              stale, thin or gate-suppressed — reads zero
//                              exactly like a roster we priced and matched.
//
//   activity_recency_score     :185 — `activity_recency_score = 0.0`, A LITERAL.
//                              It is never computed from anything. There is no
//                              trade-activity input in this pipeline at all.
//                              THIS IS THE ZERO THAT IS NOT A MEASUREMENT, and
//                              the old card rendered it as "How recently
//                              they've traded — 0.00", which tells a manager
//                              these teams have not traded recently. Nobody
//                              measured that. The copy below says we do not
//                              track it, and PartnerRankingsReadable.test.jsx
//                              holds the graduation RED that fails the moment
//                              that line stops being a literal.
//
//   posture_alignment_score    :222-236. Returns 0.0 for TWO different reasons
//                              and the card must not conflate them: either side
//                              UNCLASSIFIED (a posture we could not place), or
//                              a placed pair that is simply not in the
//                              complementary table. The evidence carries both
//                              posture labels, so this component can tell which
//                              happened and says so — BY MIRRORING :223, the
//                              producer's own gate, and not by asking whether
//                              copy.ts happens to hold a word. The first cut
//                              asked the dictionary and got TRANSITIONAL wrong
//                              in both directions: a placed team rendered as
//                              "we don't have enough signal to say which way
//                              they're pointed", and a fully placed pairing's
//                              table-miss zero rendered as a missing posture.
//                              `_label_for` (team_posture.py:95-105) returns
//                              FIVE labels; UNCLASSIFIED is not one of them and
//                              is the only unplaced state there is.
//
//   partner_score              :189-195. The four parts, added. The list
//                              arrives sorted by it, descending (:219).
//
// THE CAVEAT MOVED; THE FACT DID NOT. `partner_score_market_influenced` is
// appended to EVERY ranking by the DTO itself (league_pulse_models.py:160-165),
// unconditionally — `map_partner_ranking` never passes a caveat list at all.
// It is therefore a property of how the score is BUILT, not of any one partner,
// and it belongs to the section. What is hoisted is only what is true of every
// card: `sharedCaveats` below takes the intersection, and anything a producer
// ever attaches to some partners and not others stays on the cards where it is
// true. Removing ten repetitions removes furniture. Removing the sentence would
// be the defect this whole program exists to prevent, so it is still here,
// above the cards it qualifies, said once.
// ─────────────────────────────────────────────────────────────────────────────

const SCORE_KEYS = [
  "complementarity_score",
  "divergence_density_score",
  "activity_recency_score",
  "posture_alignment_score",
] as const;

/**
 * `SKILL_POSITIONS` (league_opportunity_map.py:16) — the exact list the matching
 * loop sweeps. Sentences below claim a measured negative over it by name, so
 * `PartnerRankingsReadable.test.jsx` reads the producer and fails if it moves.
 */
const POSITIONS = ["QB", "RB", "WR", "TE"] as const;

export const PARTNER_RANKING_LEDE =
  "Everyone we could rank, in trade-fit order: how well their roster covers " +
  "your holes, how many of their players we and the market price differently, " +
  "and which way the two of you are pointed. Open a card for the parts behind " +
  "the order.";

/** English list: "RB", "RB and WR", "QB, RB and WR". */
function joinPositions(positions: readonly string[]): string {
  const last = positions[positions.length - 1];
  if (positions.length <= 1 || last === undefined) return positions.join("");
  return `${positions.slice(0, -1).join(", ")} and ${last}`;
}

function ordinal(n: number): string {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) return `${n}th`;
  const suffix = { 1: "st", 2: "nd", 3: "rd" }[n % 10] ?? "th";
  return `${n}${suffix}`;
}

/**
 * The score, said in words. `2.091` is not a fact a manager can use: it has no
 * range, no units and no scale on screen, and the four parts it sums do not
 * share one either (three are clamped 0-1, the fourth tops out at 0.25). What
 * IS a fact is the ORDER, which the producer itself computes (:219). So the
 * card leads with the rank and the raw score moves to the receipt.
 *
 * STANDARD COMPETITION RANKING, because ties are real: this league returned
 * 1.1 / 1.1, 1.05 / 1.05 and 1.0 / 1.0. Calling one of an identical pair "6th"
 * and the other "7th" would invent a difference the producer never emitted, so
 * equal scores share a rank and say they are tied.
 */
function rankWord(score: number, allScores: readonly number[]): string {
  const descending = [...allScores].sort((a, b) => b - a);
  const rank = descending.indexOf(score) + 1;
  const tied = allScores.filter((other) => other === score).length > 1;
  if (rank === 1) return tied ? "Tied for best fit" : "Best fit";
  return tied ? `Tied ${ordinal(rank)} best fit` : `${ordinal(rank)} best fit`;
}

/**
 * Which way the two rosters are pointed. Both postures placed → both are named.
 * Either one UNCLASSIFIED → the clause says the signal is missing for THAT
 * side, and never falls through to wording that implies we placed it.
 */
function postureSentence(perspective: string, counterparty: string): string {
  const you = postureClause(perspective);
  const them = postureClause(counterparty);
  if (you !== null && them !== null) return `You're ${you} and they're ${them}.`;
  if (you !== null)
    return `You're ${you}, and we don't have enough signal to say which way they're pointed.`;
  if (them !== null)
    return `They're ${them}, and we don't have enough signal to place your own roster.`;
  return "We don't have enough signal to place either roster.";
}

/**
 * The matched positions, said as the gate that produced them (:173).
 *
 * The empty case NAMES THE SWEEP. The loop runs over `SKILL_POSITIONS` and only
 * those (:16, :170), so "there's no position" would claim a wider check than the
 * producer performed — on the one surface whose whole premise is that it does
 * not do that. `PartnerRankingsReadable.test.jsx` locks this list to the
 * producer's tuple.
 */
function positionSentence(matched: readonly string[]): string {
  return matched.length > 0
    ? `They're deep at ${joinPositions(matched)} — exactly where you're thin.`
    : `There's no position among ${joinPositions(POSITIONS)} where you're thin and they're deep.`;
}

/**
 * The divergence row COUNT, which is the fact; the clamped score is not.
 *
 * A ZERO CLAIMS LIST MEMBERSHIP AND NOTHING MORE. `divergence_row_count` is
 * `len(divergence_rows)`, and those rows come out of `_rostered_market_rows`
 * (:33-41) filtered to two signals (:178-183) — so a roster with NO rows in the
 * market-divergence artifact at all, because it was stale, thin, or gate-
 * suppressed (universe_market_divergence.py:120-127 emits four such states),
 * yields the same zero as a roster that was priced against the market and
 * agreed everywhere. "None of their players show a price gap between us and the
 * market" asserts the second of those; only one of the two is entailed by the
 * count. So the sentence says which list they are absent from, and stops.
 */
function divergenceSentence(count: unknown): string | null {
  if (typeof count !== "number") return null;
  return count > 0
    ? `We and the market price ${count} of their players differently.`
    : "None of their players are on our price-gap list — the players we and the market price differently.";
}

/** One part of the score: what it counts, then the raw number as a receipt. */
function scorePartSentence(
  key: (typeof SCORE_KEYS)[number],
  value: number,
  ranking: LeaguePulsePartnerRanking,
  evidence: Record<string, unknown>,
): string {
  const matched = ranking.matched_positions ?? [];
  switch (key) {
    case "complementarity_score":
      return matched.length > 0
        ? `The best of the positions where you're thin and they're deep (${joinPositions(matched)}).`
        : `Nothing scored here: no position among ${joinPositions(POSITIONS)} has you thin and them deep.`;
    case "divergence_density_score": {
      // The part explains what it COUNTS. The headline sentence already states
      // the count itself, and repeating it word for word inside the receipt is
      // the stamped-furniture habit this ticket is retiring.
      const count = evidence.divergence_row_count;
      if (typeof count !== "number")
        return "Counts their players we and the market price differently.";
      return count > 0
        ? `Counts their players we and the market price differently — they have ${count}.`
        : "Counts their players we and the market price differently; none of theirs are on that list.";
    }
    case "activity_recency_score":
      // See the header note on :185. The sentence is guarded on the value so it
      // can never outlive the literal it describes: if a real signal ever
      // arrives the card falls back to naming what the part counts, and the
      // graduation RED in PartnerRankingsReadable.test.jsx fails in the same
      // commit so the wording is revisited rather than discovered wrong.
      return value === 0
        ? "We don't track trade activity, so this part scores nothing for anybody and moves no one up or down the list."
        : "How recently this team has traded.";
    case "posture_alignment_score": {
      if (value !== 0) return "Scores the two postures against each other.";
      // THE PRODUCER'S OWN GATE, not a dictionary lookup. `_posture_alignment_
      // score` returns 0.0 down two paths and this sentence tells them apart:
      // :223 `if "UNCLASSIFIED" in {perspective_posture, counterparty_posture}`
      // is the not-placed one, and :236's `.get(pair, 0.0)` is a fully placed
      // pair that is simply absent from the complementary table. Asking the copy
      // dictionary "do we have a word for this label?" instead answered the
      // wrong question and got TRANSITIONAL — a placed label — wrong in both
      // directions at once.
      const placed =
        String(evidence.perspective_posture) !== UNPLACED_POSTURE &&
        String(evidence.counterparty_posture) !== UNPLACED_POSTURE;
      return placed
        ? "Both postures were placed, so this pairing simply scores nothing."
        : "One of these teams does not have enough signal for a posture, so this part could not score.";
    }
  }
}

function PartnerCard({
  ranking,
  allScores,
  cardCaveats,
}: {
  ranking: LeaguePulsePartnerRanking;
  allScores: readonly number[];
  cardCaveats: readonly string[];
}) {
  const score = ranking.score_components as Record<string, number>;
  const evidence = ranking.evidence as Record<string, unknown>;
  const positionScores = (evidence.position_scores ?? {}) as Record<string, unknown>;
  const matched = ranking.matched_positions ?? [];

  const why = [
    postureSentence(
      String(evidence.perspective_posture),
      String(evidence.counterparty_posture),
    ),
    positionSentence(matched),
    divergenceSentence(evidence.divergence_row_count),
  ]
    .filter((sentence) => sentence !== null)
    .join(" ");

  const positionReceipt = POSITIONS.filter(
    (p) => typeof positionScores[p] === "number",
  ).map((p) => `${p} ${positionScores[p] as number}`);

  return (
    <article className="dg-partner-card">
      <div className="dg-partner-card__head">
        {/* DG-118: h3 under the section's h2 — nothing renders an h2 or h3
            between them, so the outline runs h1 → h2 → h3. */}
        <h3 className="dg-partner-card__name" data-user-text>
          {ranking.counterparty_team_name ?? "Unknown counterparty"}
        </h3>
        <p className="dg-partner-card__rank">
          {rankWord(ranking.partner_score, allScores)}
        </p>
      </div>

      <p className="dg-partner-card__why">{why}</p>

      {/* A caveat that is NOT true of every partner stays on the card it is true
          of, IN THE OPEN. The section above carries only the intersection, and a
          click is a softening: a caveat behind a disclosure is a caveat the
          reader can miss on the way to acting. */}
      <TokenNotes className="dg-partner-card__caveats" tokens={cardCaveats} />

      <details className="dg-partner-card__receipt">
        <summary className="dg-partner-card__receipt-summary">
          How this fit was scored
        </summary>
        <dl className="dg-partner-card__parts">
          {SCORE_KEYS.map((key) => {
            const value = score[key];
            if (typeof value !== "number") return null;
            return (
              <div key={key} className="dg-partner-card__part">
                <dt>{fieldLabel(key)}</dt>
                <dd>
                  <p className="dg-partner-card__part-copy">
                    {scorePartSentence(key, value, ranking, evidence)}
                  </p>
                  <p className="dg-partner-card__part-receipt" data-receipt>
                    <FieldReceipt field={key} value={value} />
                  </p>
                </dd>
              </div>
            );
          })}
        </dl>
        <ul className="dg-partner-card__sources" data-receipt>
          <li>
            <FieldReceipt
              field="partner_score"
              value={ranking.partner_score}
              withLabel
            />
          </li>
          <li>
            <FieldReceipt
              field="counterparty_roster_id"
              value={ranking.counterparty_roster_id}
              withLabel
            />
          </li>
          {/* No producer field to cite here: `position_scores` is already named
              by the label, and the values carry no machinery — QB/RB/WR/TE are
              words a manager reads as English. So this line is plain prose in
              the receipt layer, with nothing declared an address that is not
              one. */}
          {positionReceipt.length > 0 ? (
            <li>Per-position fit: {positionReceipt.join(", ")}</li>
          ) : null}
        </ul>
      </details>
    </article>
  );
}

/** Tokens present on EVERY ranking — the ones that belong to the section. */
function sharedCaveats(rankings: readonly LeaguePulsePartnerRanking[]): string[] {
  const first = rankings[0];
  if (first === undefined) return [];
  return (first.caveats ?? []).filter((token) =>
    rankings.every((ranking) => (ranking.caveats ?? []).includes(token)),
  );
}

export function PartnerRankings({
  rankings,
}: {
  rankings: LeaguePulsePartnerRanking[];
}) {
  const shared = sharedCaveats(rankings);
  const allScores = rankings.map((ranking) => ranking.partner_score);

  return (
    <section aria-label="Who to call" className="dg-partners">
      <h2 className="dg-partners__heading">Who to call</h2>
      <p className="dg-partners__lede">{PARTNER_RANKING_LEDE}</p>
      <TokenNotes className="dg-partners__caveats" tokens={shared} />
      {rankings.length === 0 ? (
        <p className="dg-partners__empty">No partner ranking context available.</p>
      ) : (
        <ol className="dg-partners__list">
          {rankings.map((ranking) => (
            <li key={ranking.counterparty_roster_id}>
              <PartnerCard
                ranking={ranking}
                allScores={allScores}
                cardCaveats={(ranking.caveats ?? []).filter(
                  (token) => !shared.includes(token),
                )}
              />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
