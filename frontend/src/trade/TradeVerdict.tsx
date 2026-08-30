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
//
// ── DG-116 PANEL FIXES: WHEN A LANE MAY NOT BE GIVEN A DIRECTION ─────────────
// The first cut of this block printed a flat "you give up more than you get
// back" from the two numbers beside it in three states where the producer
// publishes no such thing. Each one was reproduced against the running API
// before it was fixed, and each is now a `cannot` call rather than a direction:
//
//  1. `adjusted_favors_status == "uncertain_range_crosses_parity"`. That status
//     is set by `_favors_status` (reconciler.py:82-105) exactly when the two
//     ends of the capacity-aware received RANGE fall on opposite sides of
//     parity — the backend saying this could go either way once the forced cut
//     is counted. Live: send Jaxson Dart, get Brock Bowers returns
//     adjusted_received_value_range [30.68, 2.85] with that status, while the
//     point value is 2.85. Printing the low end as the answer manufactured a
//     direction the producer refused to state. (Worse, that same range is
//     inverted, so ModelLanePanel fails it closed to "Range unavailable" — the
//     one artifact that would have shown the uncertainty was blank.)
//
//  2. A player the model has no value for. `evaluator.py:90-98` appends
//     `"{id}: unscored (PRE_MODEL) — excluded from trade math"` and leaves him
//     OUT of the side total. Live: send Dart, get Malik Nabers → side_b
//     side_value 0.0 with that caveat. Rendering 0 as the value of the side he
//     is on, and then a direction on top of it, is the honesty law's own case:
//     an unscored player must still say it is unscored. xVAR can be negative
//     (the live forced cut is -27.83), so an unscored player cannot even be
//     bounded — the direction is genuinely unknown, not merely imprecise.
//
//  3. The same thing on the market side. `market_sent_raw`/`market_received_raw`
//     sum only `market_value is not None` (market_reconciler.py:598-602), so an
//     asset FantasyCalc does not price is silently absent from the total. The
//     lane already refuses to print a zero for him ("No price"); this block now
//     refuses to price the side without saying he is missing from it.
//
// The arithmetic David asked for is still stated in every one of these states.
// What is withheld is only the directional claim the producer does not make.
// ─────────────────────────────────────────────────────────────────────────────

/** Which way one lane's arithmetic points. `even` is a lane's own even-trade call. */
type Stance = "ahead" | "behind" | "even";

/**
 * What a lane is able to say. `direction` is a claim about which way the trade
 * goes; `cannot` is the honest alternative, carrying the producer's own reason
 * so the screen says WHY rather than going quiet.
 */
type LaneCall =
  | { kind: "direction"; stance: Stance }
  | { kind: "cannot"; reason: string };

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

/** "Rasheen Ali", "Rasheen Ali and Kyle Williams", "A, B and C". */
function listNames(names: string[]): string {
  if (names.length <= 1) {
    return names[0] ?? "";
  }
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
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

/**
 * The same two totals when the lane is NOT allowed a direction. The numbers
 * still get said — they are the arithmetic David asked for — but the sentence
 * says out loud that they cover only what this lane could price, so the reader
 * is never handed a total as if it were complete.
 */
function partialSentence(what: string, sent: string, received: string): string {
  return `Counting only ${what}, you give up ${sent} and get back ${received}.`;
}

function LaneRow({
  lane,
  heading,
  sentence,
  scale,
  notes,
}: {
  lane: "model" | "market";
  heading: string;
  sentence: string;
  scale: string;
  notes: string[];
}) {
  return (
    <div className="dg-verdict__row" data-lane={lane}>
      <p className="dg-verdict__heading">{heading}</p>
      <p className="dg-verdict__sentence">{sentence}</p>
      <p className="dg-verdict__scale">{scale}</p>
      {notes.map((note) => (
        <p className="dg-verdict__note" key={note}>
          {note}
        </p>
      ))}
    </div>
  );
}

/** `"11632: unscored (PRE_MODEL) — excluded from trade math"` → `"11632"`. */
const UNSCORED_CAVEAT = /^(\S+):\s*unscored\s*\(/;

/**
 * The ids the model dropped from its own totals, resolved to names off the
 * market lane's labels when that lane is there. An id is never printed: it is a
 * pipeline key, and a manager reading "11632" learns nothing.
 */
function unscoredNames(
  model: ModelReconciliation,
  market: MarketReconciliation | null,
): { named: string[]; unnamed: number } {
  const ids = model.base_evaluation.caveats
    .map((caveat) => UNSCORED_CAVEAT.exec(caveat)?.[1])
    .filter((id): id is string => id !== undefined);
  if (ids.length === 0) {
    return { named: [], unnamed: 0 };
  }
  const labelById = new Map<string, string>();
  for (const asset of [
    ...(market?.sent_assets ?? []),
    ...(market?.received_assets ?? []),
  ]) {
    const sleeperId = asset.asset_ref.sleeper_id;
    if (typeof sleeperId === "string") {
      labelById.set(sleeperId, asset.label);
    }
  }
  const named: string[] = [];
  let unnamed = 0;
  for (const id of ids) {
    const label = labelById.get(id);
    if (label === undefined) {
      unnamed += 1;
    } else {
      named.push(label);
    }
  }
  return { named, unnamed };
}

/** Assets FantasyCalc returned no price for — absent from the side totals. */
function unpricedLabels(market: MarketReconciliation): string[] {
  return [...market.sent_assets, ...market.received_assets]
    .filter((asset) => asset.market_value === null || asset.market_value === undefined)
    .map((asset) => asset.label);
}

/**
 * The per-player split. Four exhaustive states, each one a fact:
 *   * somebody's price disagrees      → name him and say which way, in words
 *   * every comparison came back and
 *     they all agree                  → say that
 *   * some came back and some did not → say the agreement covers only the ones
 *                                       we could compare, and NAME the rest
 *   * none came back                  → say THAT, rather than implying agreement
 *
 * The third state is the DG-116 panel's blocking finding, reproduced live: this
 * was `assets.some(inside_band)`, so one compared player spoke for every
 * uncompared one. `_classify_divergence` (market_reconciler.py:722-729, 759-765)
 * returns `unavailable` for a missing artifact row AND for every draft pick (no
 * sleeper_id), and 11,861 of the 12,201 rows in the live divergence artifact
 * carry it — so a mixed board is the ordinary board, not an edge case. Live:
 * send Jaxson Dart, get Malik Nabers → Dart `inside_band`, Nabers `unavailable`,
 * and the screen used to say our price for Nabers agreed with the market's.
 *
 * A trade with no assets in it renders nothing.
 */
function PlayerSplit({ assets }: { assets: MarketAsset[] }) {
  const directional = assets.filter(
    (asset) =>
      asset.divergence_context?.signal_label === "model_higher_than_market" ||
      asset.divergence_context?.signal_label === "model_lower_than_market",
  );
  const agreeing = assets.filter(
    (asset) => asset.divergence_context?.signal_label === "inside_band",
  );
  const uncompared = assets.filter(
    (asset) =>
      asset.divergence_context?.signal_label !== "model_higher_than_market" &&
      asset.divergence_context?.signal_label !== "model_lower_than_market" &&
      asset.divergence_context?.signal_label !== "inside_band",
  );
  const missing =
    uncompared.length === 0 ? null : (
      <p className="dg-verdict__split-none">
        {`We have no price of our own to compare against the market for ${listNames(
          uncompared.map((asset) => asset.label),
        )}.`}
      </p>
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
        {missing}
      </div>
    );
  }
  if (agreeing.length > 0) {
    return (
      <div className="dg-verdict__split">
        <p className="dg-verdict__split-none">
          {/* "Taken one player at a time" matters: the two SIDE TOTALS above can
              disagree while every individual price is inside the band, and the
              wording has to let both be true at once. The claim itself is the
              dictionary's own reading of `inside_band` — "Our price and the
              market's agree" — so the two can never say different things. When
              some assets were never compared, the claim is narrowed to the ones
              that were and the rest are named below it. */}
          {uncompared.length === 0
            ? "Taken one player at a time, our prices and the market's agree."
            : "Taken one player at a time, our prices and the market's agree on the ones we could compare."}
        </p>
        {missing}
      </div>
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

/**
 * The roster's post-trade cut list, stated as the STATE it is.
 *
 * This read "Making room for this trade means cutting Rasheen Ali." — a causal
 * claim the producer never makes. `forced_cut_candidates` is RC v1's cut set for
 * the roster AS IT WOULD STAND after the trade (reconciler.py:190-215); there is
 * no delta against today anywhere in it. Proven live: POST /api/trade/reconcile
 * with `{"david_assets": [], "received_assets": []}` — no trade at all — returns
 * post_trade_overflow 1 and the same cut, ['Rasheen Ali']. A 1-for-1 swap
 * returns it too. The cut is a squeeze the roster already has, and the sentence
 * blamed it on whatever trade happened to be on screen.
 */
function cutSentence(model: ModelReconciliation): string | null {
  const candidates = model.roster_penalty.forced_cut_candidates;
  if (candidates.length === 0) {
    return null;
  }
  const names = candidates
    .map((cut) => (typeof cut.full_name === "string" ? cut.full_name : null))
    .filter((name): name is string => name !== null);
  const who =
    names.length === candidates.length
      ? `is ${listNames(names)}`
      : `runs to ${candidates.length} player${candidates.length === 1 ? "" : "s"} — the model view below names them`;
  return `With this trade in place the roster is over the limit, and the model's cut list ${who}. That list is worked out from the roster as it would stand after the trade, so it does not tell you whether you were already short of room.`;
}

/** What the model lane is able to say, and the sentences that say it. */
function modelReading(
  model: ModelReconciliation,
  market: MarketReconciliation | null,
): { sentence: string; notes: string[]; call: LaneCall } {
  const sentValue = model.base_evaluation.side_a.side_value;
  const receivedValue = model.adjusted_david_received_value;
  const difference = receivedValue - sentValue;
  const notes: string[] = [];
  if (receivedValue !== model.base_evaluation.side_b.side_value) {
    notes.push(
      "What you get back here already has your forced cut's value taken out of it.",
    );
  }

  // (2) A player with no model value at all. He is not in either total, so
  // neither total is the value of its side and no direction can be read off it.
  const { named, unnamed } = unscoredNames(model, market);
  const excludedCount = named.length + unnamed;
  if (excludedCount > 0) {
    const who =
      named.length === excludedCount
        ? listNames(named)
        : `${excludedCount} of the players in this trade`;
    notes.push(
      `Our model has no value yet for ${who} — that is missing from these totals, not a zero in them.`,
    );
    return {
      sentence: partialSentence(
        "the players our model has a value for",
        modelNumber(sentValue),
        modelNumber(receivedValue),
      ),
      notes,
      call: {
        kind: "cannot",
        reason: `it has no value yet for ${who}, which is missing from its totals rather than counted as zero`,
      },
    };
  }

  const stance = stanceFor(difference, model.adjusted_within_parity_band);
  const sentence = arithmeticSentence(
    modelNumber(sentValue),
    modelNumber(receivedValue),
    modelNumber(Math.abs(difference)),
    stance,
  );

  // (1) The capacity-aware range straddles even. `adjusted_favors_status` is the
  // ONLY capacity-aware direction the backend publishes ("all capacity-aware
  // truth lives in adjusted_favors_status", reconciler.py:313-315), and this
  // value of it is a refusal to call the direction.
  if (model.adjusted_favors_status === "uncertain_range_crosses_parity") {
    const range = model.adjusted_received_value_range;
    const spread =
      range === null || range === undefined
        ? "the spread on that cut lands on both sides of even"
        : `their side is worth somewhere between ${modelNumber(
            Math.min(range[0], range[1]),
          )} and ${modelNumber(Math.max(range[0], range[1]))} to you — a spread that lands on both sides of even`;
    // The row has to carry the qualification too, or the numbers above read as
    // a call while the sentence below says there is none.
    notes.push(
      `Once the forced cut is counted, ${spread}. So this is arithmetic on the two totals, not a call on which way the trade goes.`,
    );
    return {
      sentence,
      notes,
      call: {
        kind: "cannot",
        reason: `once the forced cut is counted, ${spread}`,
      },
    };
  }

  return { sentence, notes, call: { kind: "direction", stance } };
}

/** What the market lane is able to say, and the sentences that say it. */
function marketReading(market: MarketReconciliation): {
  sentence: string;
  notes: string[];
  call: LaneCall;
} {
  const difference = market.market_delta_for_david;
  const notes: string[] = [];
  // adjusted_market_received subtracts the market price of the players this
  // trade forces you to cut (market_reconciler.py:613). Say so only when it
  // actually bit — a zero-cost cut must not be dressed up as a deduction.
  if (market.adjusted_market_received !== market.market_received_raw) {
    notes.push(
      "What you get back here already has your forced cut's market price taken out of it.",
    );
  }
  // The sent side has its own adjustment and it is NOT yours: when a roster
  // number is filled in, `adjusted_market_sent = market_sent_raw -
  // counterparty_penalty.penalty_market_value` (market_reconciler.py:628-632) —
  // "the value the counterparty receives after its own capacity cost" (:585).
  // Printed bare under "You give up", that is a different number for the same
  // side than the lane below prints, with nothing saying why.
  if (market.adjusted_market_sent !== market.market_sent_raw) {
    notes.push(
      "What you give up here is counted as what your side is worth to the other manager after their own forced cut, whose market price has been taken off it.",
    );
  }

  // (3) An asset FantasyCalc does not price is absent from the totals.
  const unpriced = unpricedLabels(market);
  if (unpriced.length > 0) {
    notes.push(
      `No market price came back for ${listNames(unpriced)} — that is missing from these totals, not a zero in them.`,
    );
    return {
      sentence: partialSentence(
        "what the market puts a price on",
        points(market.adjusted_market_sent),
        points(market.adjusted_market_received),
      ),
      notes,
      call: {
        kind: "cannot",
        reason: `no market price came back for ${listNames(unpriced)}, which is missing from its totals rather than counted as zero`,
      },
    };
  }

  const stance = stanceFor(difference, false);
  return {
    sentence: arithmeticSentence(
      points(market.adjusted_market_sent),
      points(market.adjusted_market_received),
      points(Math.abs(difference)),
      stance,
    ),
    notes,
    call: { kind: "direction", stance },
  };
}

/**
 * The read. It never weighs one lane against the other — that is the take/pass
 * call David declined to bless — and it only claims a DISAGREEMENT when both
 * lanes actually point opposite ways. A lane the producer will not let speak
 * says why instead of being quietly dropped.
 *
 * The "disagree" headline is withheld when either lane calls the trade even:
 * only the model publishes an even-trade band, so a 3-point market difference
 * against a model "even" call is a band artifact, not a finding.
 */
function readSentence(marketCall: LaneCall | null, modelCall: LaneCall | null): string {
  if (marketCall !== null && modelCall !== null) {
    if (marketCall.kind === "direction") {
      if (modelCall.kind === "direction") {
        const m = marketCall.stance;
        const d = modelCall.stance;
        if (m === d) {
          return `Both prices read this the same way — ${STANCE_CLAUSE[m]}.`;
        }
        if (m === "even" || d === "even") {
          return `By market prices ${STANCE_CLAUSE[m]}; by our model ${STANCE_CLAUSE[d]}.`;
        }
        return `The market and our model disagree here. By market prices ${STANCE_CLAUSE[m]}; by our model ${STANCE_CLAUSE[d]}.`;
      }
      return `By market prices ${STANCE_CLAUSE[marketCall.stance]}. Our model cannot say which way this one goes: ${modelCall.reason}.`;
    }
    if (modelCall.kind === "direction") {
      return `By our model ${STANCE_CLAUSE[modelCall.stance]}. The market pricing cannot say which way this one goes: ${marketCall.reason}.`;
    }
    return `Neither pricing can say which way this one goes. On the market side, ${marketCall.reason}. On our model's side, ${modelCall.reason}.`;
  }
  if (marketCall !== null) {
    return marketCall.kind === "direction"
      ? `Our model's price for this trade did not load, so the market's is the only one here — by market prices ${STANCE_CLAUSE[marketCall.stance]}.`
      : `Our model's price for this trade did not load, and the market's cannot say which way this one goes: ${marketCall.reason}.`;
  }
  if (modelCall !== null) {
    return modelCall.kind === "direction"
      ? `The market's price for this trade did not load, so our model's is the only one here — by our model ${STANCE_CLAUSE[modelCall.stance]}.`
      : `The market's price for this trade did not load, and our model cannot say which way this one goes: ${modelCall.reason}.`;
  }
  return "Neither price loaded, so there is nothing to compare yet.";
}

export function TradeVerdict({
  model,
  market,
}: {
  model: ModelReconciliation | null;
  market: MarketReconciliation | null;
}) {
  const marketRow = market === null ? null : marketReading(market);
  const modelRow = model === null ? null : modelReading(model, market);
  const read = readSentence(marketRow?.call ?? null, modelRow?.call ?? null);
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
            notes={marketRow.notes}
          />
        )}
        {modelRow !== null && (
          <LaneRow
            lane="model"
            heading="By our model"
            sentence={modelRow.sentence}
            scale="Value over a replacement-level player."
            notes={modelRow.notes}
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
