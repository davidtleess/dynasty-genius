import type { z } from "zod";

import type {
  zTradeMarketReconciliation,
  zTradeRosterReconciliation,
} from "../lib/api/zod.gen";

type ModelReconciliation = z.infer<typeof zTradeRosterReconciliation>;
type MarketReconciliation = z.infer<typeof zTradeMarketReconciliation>;

const PLACEHOLDER = "—";

// The two lane deltas as TWO SEPARATE labelled facts — never merged,
// averaged, or subtracted into a single number. Per-asset backend signal
// labels are surfaced verbatim (neutral; descriptive, not a buy/sell rating).
export function DivergenceStrip({
  model,
  market,
}: {
  model: ModelReconciliation | null;
  market: MarketReconciliation | null;
}) {
  const modelDelta = model ? model.adjusted_fairness_delta : PLACEHOLDER;
  const marketDelta = market ? market.market_delta_for_david : PLACEHOLDER;
  const signals =
    market?.sent_assets
      .map((asset) => asset.divergence_context?.signal_label)
      .filter((label): label is NonNullable<typeof label> => label != null) ?? [];

  return (
    <section className="dg-divergence" data-testid="divergence-strip">
      <div className="dg-divergence__fact">
        <span className="dg-divergence__label">Model lane</span>
        <span className="dg-divergence__value">{modelDelta}</span>
      </div>
      <div className="dg-divergence__fact">
        <span className="dg-divergence__label">Market lane</span>
        <span className="dg-divergence__value">{marketDelta}</span>
      </div>
      {signals.length > 0 && (
        <ul className="dg-divergence__signals">
          {signals.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
