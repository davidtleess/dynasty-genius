import type { z } from "zod";

import type {
  zTradeMarketReconciliation,
  zTradeRosterReconciliation,
} from "../lib/api/zod.gen";
import { valueWord } from "../lib/copy";

type ModelReconciliation = z.infer<typeof zTradeRosterReconciliation>;
type MarketReconciliation = z.infer<typeof zTradeMarketReconciliation>;
type MarketAsset = MarketReconciliation["sent_assets"][number];

// ─────────────────────────────────────────────────────────────────────────────
// THE TRADE VERDICT — David's 2026-08-30 ruling, verbatim option label:
// **"Both prices, plainly."** State the arithmetic on BOTH pricings and name the
// disagreement. NO blended take/pass imperative: weighing market against model
// when they disagree is a judgement he explicitly declined to bless, so this
// component never produces one, and never merges the two into a single score.
//
// WHAT EACH NUMBER IS, read from the producers rather than from a plausible
// reading of the field names:
//
//   market  `market_delta_for_david = adjusted_market_received -
//           adjusted_market_sent` (market_reconciler.py:638). Positive means
//           more value coming back than going out. This component prints those
//           two operands and their difference, so the arithmetic on screen is
//           the backend's own identity, not a re-derivation.
//
//   model   `adjusted_fairness_delta = abs(side_a.side_value -
//           adjusted_received_value)` (reconciler.py:317) — an ABSOLUTE
//           magnitude that carries no direction at all. The direction lives in
//           `favors` / `adjusted_favors_status`, which this product deliberately
//           never renders (a typed verdict field). So the signed number here is
//           computed the only honest way: `adjusted_david_received_value -
//           base_evaluation.side_a.side_value`, i.e. the difference of the two
//           values printed beside it. Its magnitude is the backend's
//           `adjusted_fairness_delta` by construction.
//
// THE SCALE LAW (the reason a blended number would be a lie): the two lanes are
// on DIFFERENT SCALES. The market lane carries FantasyCalc's own points; the
// model lane counts value over a replacement-level player. The backend says so
// itself in the caveat `fantasycalc_raw_scale_not_xvar` — "These are
// FantasyCalc's own numbers on their own scale — not our value over
// replacement" (copy.ts). The copy below states that in the reader's path so a
// manager is never invited to subtract one lane from the other.
// ─────────────────────────────────────────────────────────────────────────────

/** Which way one lane's arithmetic points. `even` is a lane's own even-trade call. */
type Stance = "ahead" | "behind" | "even";

const STANCE_CLAUSE: Record<Stance, string> = {
  ahead: "you get back more than you give up",
  behind: "you give up more than you get back",
  even: "the two sides come out about even",
};

/** FantasyCalc points are whole numbers on a scale in the thousands. */
function points(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

/**
 * Model values carry two decimals. Rounding here is display only and is applied
 * to a difference computed from two already-rounded backend values, so it can
 * never print `39.620000000000005` for what the payload calls 39.62.
 */
function modelNumber(value: number): string {
  return String(Math.round(value * 100) / 100);
}

function stanceFor(difference: number, calledEven: boolean): Stance {
  if (calledEven || difference === 0) {
    return "even";
  }
  return difference > 0 ? "ahead" : "behind";
}

/** "You give up 8,400 and get back 7,100 — 1,300 more going out than coming back." */
function arithmeticSentence(
  sent: string,
  received: string,
  gap: string,
  stance: Stance,
): string {
  const tail =
    stance === "even"
      ? "close enough to call it even"
      : stance === "ahead"
        ? `${gap} more coming back than going out`
        : `${gap} more going out than coming back`;
  return `You give up ${sent} and get back ${received} — ${tail}.`;
}

function LaneRow({
  lane,
  heading,
  sentence,
  scale,
  note,
}: {
  lane: "model" | "market";
  heading: string;
  sentence: string;
  scale: string;
  note: string | null;
}) {
  return (
    <div className="dg-verdict__row" data-lane={lane}>
      <p className="dg-verdict__heading">{heading}</p>
      <p className="dg-verdict__sentence">{sentence}</p>
      <p className="dg-verdict__scale">{scale}</p>
      {note !== null && <p className="dg-verdict__note">{note}</p>}
    </div>
  );
}

/**
 * The per-player split. Three exhaustive states, each one a fact:
 *   * somebody's price disagrees   → name him and say which way, in words
 *   * every player's prices agree  → say that
 *   * no comparison came back      → say THAT, rather than implying agreement
 * A trade with no players in it (picks only) renders nothing — picks carry no
 * model-versus-market comparison, and silence is the honest rendering of that.
 */
function PlayerSplit({ assets }: { assets: MarketAsset[] }) {
  const directional = assets.filter(
    (asset) =>
      asset.divergence_context?.signal_label === "model_higher_than_market" ||
      asset.divergence_context?.signal_label === "model_lower_than_market",
  );
  if (directional.length > 0) {
    return (
      <div className="dg-verdict__split">
        <p className="dg-verdict__heading">
          Where we and the market disagree on a player
        </p>
        <ul className="dg-verdict__split-list">
          {directional.map((asset) => (
            <li key={asset.label}>
              <span className="dg-verdict__split-name" data-user-text="">
                {asset.label}
              </span>
              <span className="dg-verdict__split-word">
                {/* signal_label is a backend key; valueWord is the dictionary
                    that turns it into the sentence the market lane already
                    speaks. It used to reach the DOM raw from here. */}
                {valueWord(asset.divergence_context?.signal_label ?? "")}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (
    assets.some((asset) => asset.divergence_context?.signal_label === "inside_band")
  ) {
    return (
      <p className="dg-verdict__split-none">
        {/* "Taken one player at a time" matters: the two SIDE TOTALS above can
            disagree while every individual price is inside the band, and the
            wording has to let both be true at once. The claim itself is the
            dictionary's own reading of `inside_band` — "Our price and the
            market's agree" — so the two can never say different things. */}
        Taken one player at a time, our prices and the market's agree.
      </p>
    );
  }
  if (assets.length > 0) {
    return (
      <p className="dg-verdict__split-none">
        We have no player-by-player comparison against the market for this trade.
      </p>
    );
  }
  return null;
}

/** The names this trade would force off the roster, from the model's own cut list. */
function cutSentence(model: ModelReconciliation): string | null {
  const candidates = model.roster_penalty.forced_cut_candidates;
  if (candidates.length === 0) {
    return null;
  }
  const names = candidates
    .map((cut) => (typeof cut.full_name === "string" ? cut.full_name : null))
    .filter((name): name is string => name !== null);
  if (names.length === 0) {
    return `Making room for this trade means cutting ${candidates.length} player${
      candidates.length === 1 ? "" : "s"
    } — the model view below lists them.`;
  }
  return `Making room for this trade means cutting ${names.join(" and ")}.`;
}

export function TradeVerdict({
  model,
  market,
}: {
  model: ModelReconciliation | null;
  market: MarketReconciliation | null;
}) {
  // ── Market lane arithmetic (the backend's own operands and difference) ──
  let marketRow: { sentence: string; note: string | null } | null = null;
  let marketStance: Stance | null = null;
  if (market !== null) {
    const difference = market.market_delta_for_david;
    marketStance = stanceFor(difference, false);
    marketRow = {
      sentence: arithmeticSentence(
        points(market.adjusted_market_sent),
        points(market.adjusted_market_received),
        points(Math.abs(difference)),
        marketStance,
      ),
      // adjusted_market_received subtracts the market price of the players this
      // trade forces you to cut (market_reconciler.py:614). Say so only when it
      // actually bit — a zero-cost cut must not be dressed up as a deduction.
      note:
        market.adjusted_market_received !== market.market_received_raw
          ? "What you get back here already has the forced cut's market price taken out of it."
          : null,
    };
  }

  // ── Model lane arithmetic (signed the only honest way — see the header) ──
  let modelRow: { sentence: string; note: string | null } | null = null;
  let modelStance: Stance | null = null;
  if (model !== null) {
    const sentValue = model.base_evaluation.side_a.side_value;
    const receivedValue = model.adjusted_david_received_value;
    const difference = receivedValue - sentValue;
    modelStance = stanceFor(difference, model.adjusted_within_parity_band);
    modelRow = {
      sentence: arithmeticSentence(
        modelNumber(sentValue),
        modelNumber(receivedValue),
        modelNumber(Math.abs(difference)),
        modelStance,
      ),
      note:
        receivedValue !== model.base_evaluation.side_b.side_value
          ? "What you get back here already has the forced cut's value taken out of it."
          : null,
    };
  }

  // ── The read: agree, disagree, or only one price to go on ──
  let read: string;
  if (marketStance !== null && modelStance !== null) {
    read =
      marketStance === modelStance
        ? `Both prices read this the same way — ${STANCE_CLAUSE[marketStance]}.`
        : `The market and our model disagree here. By market prices ${STANCE_CLAUSE[marketStance]}; by our model ${STANCE_CLAUSE[modelStance]}.`;
  } else if (marketStance !== null) {
    read = `Our model's price for this trade did not load, so the market's is the only one here — by market prices ${STANCE_CLAUSE[marketStance]}.`;
  } else if (modelStance !== null) {
    read = `The market's price for this trade did not load, so our model's is the only one here — by our model ${STANCE_CLAUSE[modelStance]}.`;
  } else {
    read = "Neither price loaded, so there is nothing to compare yet.";
  }

  const cut = model === null ? null : cutSentence(model);

  return (
    <section
      className="dg-verdict"
      data-testid="trade-verdict"
      aria-label="Both prices"
    >
      <h3 className="dg-verdict__title">Both prices</h3>
      <div className="dg-verdict__rows">
        {marketRow !== null && (
          <LaneRow
            lane="market"
            heading="By market prices"
            sentence={marketRow.sentence}
            scale="FantasyCalc points."
            note={marketRow.note}
          />
        )}
        {modelRow !== null && (
          <LaneRow
            lane="model"
            heading="By our model"
            sentence={modelRow.sentence}
            scale="Value over a replacement-level player."
            note={modelRow.note}
          />
        )}
      </div>
      <p className="dg-verdict__read">{read}</p>
      {/* The scale law, in the reader's path and not in a footnote: two numbers
          on different scales must never be subtracted from one another. */}
      <p className="dg-verdict__scale-law">
        Those two numbers sit on different scales, so there is no subtracting one from
        the other: the market's are FantasyCalc points, ours count value over a
        replacement-level player.
      </p>
      {cut !== null && <p className="dg-verdict__cut">{cut}</p>}
      {market !== null && (
        <PlayerSplit assets={[...market.sent_assets, ...market.received_assets]} />
      )}
    </section>
  );
}
