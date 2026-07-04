import type { z } from "zod";

import type { zTradeMarketReconciliation } from "../lib/api/zod.gen";
import { humanizeToken, RangeRow } from "./forcedCutRange";

type MarketReconciliation = z.infer<typeof zTradeMarketReconciliation>;

// Backend neutral divergence labels -> human display text. No verdict wording.
const SIGNAL_DISPLAY: Record<string, string> = {
  model_higher_than_market: "Model higher than market",
  model_lower_than_market: "Model lower than market",
  inside_band: "Inside band",
  unavailable: "Unavailable",
};

// Market Snapshot (amber lane). Renders raw FantasyCalc values, the market
// side difference, advisory realism warnings, and per-asset neutral
// divergence labels. Overlay-only; never a model input.
export function MarketLanePanel({
  reconciliation,
}: {
  reconciliation: MarketReconciliation;
}) {
  const penalty = reconciliation.david_forced_cut_penalty;

  return (
    <section
      className="dg-lane dg-lane--market"
      data-lane="market"
      data-testid="market-lane"
      data-visual-weight="equal"
    >
      <h3 className="dg-lane__title">Market snapshot (FantasyCalc)</h3>
      <dl className="dg-lane__metrics">
        <dt>Sent (raw)</dt>
        <dd>{reconciliation.market_sent_raw}</dd>
        <dt>Received (raw)</dt>
        <dd>{reconciliation.market_received_raw}</dd>
        <dt>Market side difference</dt>
        <dd>{reconciliation.market_delta_for_david}</dd>
      </dl>

      {/* FantasyCalc-native forced-cut capacity ranges. Scale-isolated from the
          model lane (never blended with xVAR); the old scalar penalty value is
          not displayed. Descriptive overlay only. */}
      {penalty === null || penalty === undefined ? (
        <p className="dg-forced-cut-none">No capacity penalty.</p>
      ) : penalty.market_penalty_status === "blocked" ? (
        <p className="dg-forced-cut-blocked">
          Roster rules conflict: transaction blocked.
        </p>
      ) : (
        <div className="dg-forced-cut-ranges">
          <RangeRow
            label="FantasyCalc capacity value-at-risk range"
            range={penalty.forced_cut_market_value_at_risk_range}
          />
          <RangeRow
            label="FantasyCalc recovery range"
            range={penalty.forced_cut_market_recovery_range}
          />
          {penalty.market_penalty_status === "uncertain_pool_unavailable" && (
            <p className="dg-forced-cut-caveat">
              Market replacement data stale — showing the widest possible range.
            </p>
          )}
          {penalty.caveats.length > 0 && (
            <ul className="dg-lane__caveats" aria-label="Capacity caveats">
              {penalty.caveats.map((caveat) => (
                <li key={caveat}>{humanizeToken(caveat)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <ul className="dg-lane__assets">
        {reconciliation.sent_assets.map((asset) => (
          <li key={asset.label}>
            {asset.label}
            {asset.divergence_context && (
              <span className="dg-lane__signal">
                {SIGNAL_DISPLAY[asset.divergence_context.signal_label] ??
                  asset.divergence_context.signal_label}
              </span>
            )}
          </li>
        ))}
      </ul>
      {reconciliation.realism_warnings.length > 0 && (
        <ul className="dg-lane__warnings">
          {reconciliation.realism_warnings.map((warning) => (
            <li key={warning.warning_type}>
              <span className="dg-lane__severity">{warning.severity}</span>{" "}
              {warning.message}
            </li>
          ))}
        </ul>
      )}
      {reconciliation.coverage_gaps.length > 0 && (
        <ul className="dg-lane__coverage" aria-label="Coverage gaps">
          {reconciliation.coverage_gaps.map((gap) => (
            <li key={gap}>{gap}</li>
          ))}
        </ul>
      )}
      {reconciliation.caveats.length > 0 && (
        <ul className="dg-lane__caveats">
          {reconciliation.caveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
      )}
      {reconciliation.source_timestamp && (
        <p className="dg-lane__timestamp">{reconciliation.source_timestamp}</p>
      )}
    </section>
  );
}
