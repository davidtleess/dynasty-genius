import type { z } from "zod";

import type { zTradeMarketReconciliation } from "../lib/api/zod.gen";
import {
  describeToken,
  formatCaptureTimestamp,
  sourcedCaveat,
  valueWord,
} from "../lib/copy";
import { PlayerNameButton } from "../player/playerSelection";
import { TokenNotes } from "../ui/TokenNotes";
import { RangeRow } from "./forcedCutRange";

type MarketReconciliation = z.infer<typeof zTradeMarketReconciliation>;
type MarketAsset = MarketReconciliation["sent_assets"][number];

// This lane is FantasyCalc-native end to end (its scale line says so), and the
// two sourced caveats name the source inside their own sentence.
const SOURCE_LABEL = "FantasyCalc";

/** FantasyCalc points are whole numbers in the thousands; group them. */
function points(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

/** A difference reads better carrying its own sign. */
function signedPoints(value: number): string {
  return value > 0 ? `+${points(value)}` : points(value);
}

// One side's assets. Both sides are priced by the backend and both carry
// per-asset divergence context (trade_market.py:287-294 enriches sent_assets
// AND received_assets), but only the sent side was ever rendered — so half of
// every trade's per-asset detail never reached the screen.
function AssetSide({ title, assets }: { title: string; assets: MarketAsset[] }) {
  if (assets.length === 0) {
    return null;
  }
  return (
    <div className="dg-lane__side">
      <p className="dg-lane__side-title">{title}</p>
      <ul className="dg-lane__assets">
        {assets.map((asset) => (
          <li key={`${title}-${asset.label}`} className="dg-lane__asset">
            <span className="dg-lane__asset-name">
              {/* DG-110: a priced player in the result opens his card. Picks
                  have no card and stay plain text. */}
              <PlayerNameButton
                sleeperId={
                  asset.asset_ref.asset_kind === "player"
                    ? asset.asset_ref.sleeper_id
                    : null
                }
                name={asset.label}
              />
            </span>
            <span className="dg-lane__asset-value">
              {/* An asset FantasyCalc does not price says so; it never shows a
                  zero or a dash standing in for a number we do not have. */}
              {asset.market_value === null || asset.market_value === undefined
                ? "No price"
                : points(asset.market_value)}
            </span>
            {asset.divergence_context && (
              <span className="dg-lane__signal">
                {valueWord(asset.divergence_context.signal_label)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

// The market's side of the pricing (the amber lane). Renders raw FantasyCalc
// values, the market side difference, advisory realism warnings, and per-asset
// neutral divergence labels. Overlay-only; never a model input.
export function MarketLanePanel({
  reconciliation,
}: {
  reconciliation: MarketReconciliation;
}) {
  const penalty = reconciliation.david_forced_cut_penalty;
  // `market_delta_for_david` is the ADJUSTED pair's difference
  // (market_reconciler.py:638), while the two rows above it are the raw side
  // totals. When a forced cut has been priced in, 6,002 − 5,194 no longer
  // reproduces the printed difference, so the label has to say why rather than
  // leaving a reader to conclude we cannot subtract.
  const differenceIsNetOfCut =
    reconciliation.adjusted_market_received !== reconciliation.market_received_raw ||
    reconciliation.adjusted_market_sent !== reconciliation.market_sent_raw;

  // The one caveat whose sentence refers to a capture date. With no date to
  // refer to, its fact is carried by the freshness line above instead of
  // dangling here — the fact survives, the broken reference does not.
  const shownCaveats = reconciliation.caveats.filter(
    (caveat) =>
      Boolean(reconciliation.source_timestamp) ||
      caveat !== "source_timestamp_is_fetch_time_not_publish_time",
  );

  return (
    <section
      className="dg-lane dg-lane--market"
      data-lane="market"
      data-testid="market-lane"
      data-visual-weight="equal"
    >
      {/* DG-118: sibling of the verdict heading — see TradeVerdict.tsx. */}
      <h2 className="dg-lane__title">The market</h2>
      <p className="dg-lane__scale">FantasyCalc points</p>
      <dl className="dg-lane__metrics">
        <dt>You send</dt>
        <dd>{points(reconciliation.market_sent_raw)}</dd>
        <dt>You get</dt>
        <dd>{points(reconciliation.market_received_raw)}</dd>
        <dt>
          {differenceIsNetOfCut ? "Difference, after the forced cut" : "Difference"}
        </dt>
        <dd>{signedPoints(reconciliation.market_delta_for_david)}</dd>
      </dl>
      {/* The bare ISO string used to float at the BOTTOM of the lane, unlabelled
          and only when it existed — while the sourced caveat down there says
          "the capture date above", which pointed at nothing above it and, on a
          null timestamp, at nothing at all. Freshness belongs beside the prices
          it qualifies, and it renders either way now: a missing pull time is
          itself a freshness fact, and the measured live payload returns
          `source_timestamp: null`.

          DG-116 panel fix: relocating the line fixed WHERE the caveat points,
          not WHETHER it is true. On the live null-timestamp payload the lane
          said there was no capture date and four lines later explained what
          "the capture date above" means. So on a null timestamp that one caveat
          is carried HERE instead, with its fact intact and nothing to dangle
          from; `hiddenCaveats` below is what keeps it from being said twice. */}
      <p className="dg-lane__timestamp">
        {reconciliation.source_timestamp
          ? `Prices pulled ${formatCaptureTimestamp(reconciliation.source_timestamp)}`
          : `No capture date came back with these prices, so we cannot say how fresh they are — and when one does come back it is when we pulled the prices, not when ${SOURCE_LABEL} published them.`}
      </p>

      {/* FantasyCalc-native forced-cut capacity ranges. Scale-isolated from the
          model lane (never blended with our own value over replacement); the old
          scalar penalty value is not displayed. Descriptive overlay only. */}
      {penalty === null || penalty === undefined ? (
        // The field is absent, which is all this says. It is NOT a claim that
        // the roster has room — the route always attaches a penalty object, so
        // absence here means the cost never came back, not that it is zero.
        <p className="dg-forced-cut-none">
          No forced-cut cost came back with this trade.
        </p>
      ) : penalty.market_penalty_status === "blocked" ? (
        // WAS: "Roster rules conflict: transaction blocked." — an assertion that
        // the league would reject the trade. The producer sets this status on
        // exactly one condition: `unresolved_cut_count > 0`, i.e. "an unresolved
        // cut leaves the net incomplete — block, never fabricate"
        // (market_reconciler.py:534-537). That is a missing PRICE, not a rules
        // conflict, and the live payload proves it: the status arrives beside
        // the caveat "Rasheen Ali (11570): no FantasyCalc value".
        //
        // DG-116 panel fix: the replacement was singular and said the cost was
        // "left out of the numbers here", which is false on a multi-cut set
        // where only SOME cuts are unpriced. `penalty_market_value` sums the
        // priced overlays regardless of the block (market_reconciler.py:458-462)
        // and `adjusted_market_received` subtracts it unconditionally (:613), so
        // the priced part IS in the numbers — and the label eight lines above
        // then reads "Difference, after the forced cut" on the same screen.
        // Reproduced live: send Jaxson Dart, get Brock Bowers + Malik Nabers →
        // status "blocked", unresolved_cut_count 1 of 2 cuts,
        // penalty_market_value 707, received 14,170 → 13,463.
        <p className="dg-forced-cut-blocked">
          {penalty.penalty_market_value > 0
            ? `We could not put a market price on ${penalty.unresolved_cut_count} of the ${penalty.forced_cut_candidates.length} forced cuts, so that part of the cost is missing here. The ${penalty.forced_cut_candidates.length - penalty.unresolved_cut_count === 1 ? "one" : "ones"} we could price ${penalty.forced_cut_candidates.length - penalty.unresolved_cut_count === 1 ? "is" : "are"} already taken out of the numbers above.`
            : `We could not put a market price on the forced ${penalty.unresolved_cut_count === 1 ? "cut" : "cuts"}, so that cost is left out of the numbers here.`}
        </p>
      ) : (
        <div className="dg-forced-cut-ranges">
          <RangeRow
            label="What the forced cut could cost you"
            range={penalty.forced_cut_market_value_at_risk_range}
          />
          <RangeRow
            label="What you could get back off waivers"
            range={penalty.forced_cut_market_recovery_range}
          />
          {penalty.market_penalty_status === "uncertain_pool_unavailable" && (
            <p className="dg-forced-cut-caveat">
              Market replacement data stale — showing the widest possible range.
            </p>
          )}
          {penalty.caveats.length > 0 && (
            <ul className="dg-lane__caveats" aria-label="Capacity notes">
              {penalty.caveats.map((caveat) => (
                <li key={caveat}>{describeToken(caveat)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {/* The run bar invites a manager to fill in the other roster number so we
          will also price what that manager has to cut. The backend can decline
          — `"unavailable"` is "known roster, inadequate coverage"
          (market_reconciler.py:585-590) — and nothing on this surface said so,
          so the promise was made and the decline was silent. */}
      {reconciliation.counterparty_market_penalty_status === "unavailable" && (
        <p className="dg-forced-cut-blocked">
          We could not price what the other manager would have to cut, so their side of
          the squeeze is not in these numbers.
        </p>
      )}
      <div className="dg-lane__sides">
        <AssetSide title="What you send" assets={reconciliation.sent_assets} />
        <AssetSide title="What you get" assets={reconciliation.received_assets} />
      </div>
      {reconciliation.realism_warnings.length > 0 && (
        <ul className="dg-lane__warnings" aria-label="Things worth a second look">
          {reconciliation.realism_warnings.map((warning) => (
            <li key={warning.warning_type}>
              <span className="dg-lane__severity">{valueWord(warning.severity)}</span>{" "}
              {warning.message}
            </li>
          ))}
        </ul>
      )}
      {/* DG-109 review fix: the penalty caveats above were converted and these
          two were not — same component, and `reconciliation.caveats` was in the
          same `dg-lane__caveats` class thirty lines down. Trade Lab is an active
          nav surface, so the raw keys (`fantasycalc_uncovered`,
          `market_overlay_display_only`, `decision_supported_false`) were on
          David's screen with a drafted trade. */}
      {reconciliation.coverage_gaps.length > 0 && (
        <TokenNotes
          className="dg-lane__coverage"
          ariaLabel="Coverage gaps"
          tokens={reconciliation.coverage_gaps}
        />
      )}
      {/* Through `sourcedCaveat`, not the plain lookup: two of the base market
          caveats need this lane's own source named INSIDE the sentence, so a
          future non-FantasyCalc source is named correctly rather than
          mislabelled inside a truth-bearing caveat. */}
      {shownCaveats.length > 0 && (
        <TokenNotes
          className="dg-lane__caveats"
          notes={shownCaveats.map((caveat) => sourcedCaveat(caveat, SOURCE_LABEL))}
        />
      )}
    </section>
  );
}
