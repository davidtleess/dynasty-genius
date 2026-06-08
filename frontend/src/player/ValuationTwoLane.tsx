// Surface-3 T8 — two physically separate valuation lanes + uniform-neutral
// divergence. Model (blue) and market (amber) are never blended; the divergence
// element is uniform-neutral slate — direction is conveyed by LABEL TEXT only,
// never by directional brand colour, and the numeric delta is not rendered.
import type { z } from "zod";

import type { zPlayerDetailResponse } from "../lib/api/zod.gen";

type PlayerDetail = z.infer<typeof zPlayerDetailResponse>;
type ModelLane = PlayerDetail["model"];
type MarketLane = PlayerDetail["market"];
type Divergence = PlayerDetail["divergence"];

const DIVERGENCE_LABELS: Record<string, string> = {
  model_higher_than_market: "Model higher than market",
  model_lower_than_market: "Model lower than market",
  inside_band: "Inside band",
};

function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

function marketSourceLabel(source: string | null | undefined): string {
  return source === "fantasycalc" ? "FantasyCalc" : (source ?? "—");
}

export function ValuationTwoLane({
  model,
  market,
  divergence,
}: {
  model: ModelLane;
  market: MarketLane;
  divergence: Divergence;
}) {
  const divergenceLabel =
    DIVERGENCE_LABELS[divergence.status] ?? "Divergence unavailable";

  return (
    <div className="dg-two-lane">
      <div
        data-testid="player-model-lane"
        data-lane="model"
        className="dg-two-lane__lane dg-two-lane__lane--model"
      >
        {model ? (
          <dl className="dg-two-lane__facts">
            <span>{model.engine_path}</span>
            <span>{model.model_grade}</span>
            <span>{model.dynasty_value_score}</span>
            <span>{model.xvar}</span>
            <span>{percent(model.xvar_percentile_position)}</span>
            <span>{model.projection_1y ?? "—"}</span>
            <span>{model.projection_2y ?? "—"}</span>
            <span>{model.projection_3y ?? "—"}</span>
          </dl>
        ) : (
          <p className="dg-two-lane__degraded">Model unavailable</p>
        )}
      </div>

      <div
        data-testid="player-market-lane"
        data-lane="market"
        className="dg-two-lane__lane dg-two-lane__lane--market"
      >
        {market?.status === "available" ? (
          <dl className="dg-two-lane__facts">
            <span>{marketSourceLabel(market.source)}</span>
            <span>{market.market_value}</span>
            <span>Overall {market.market_rank_overall}</span>
            <span>Position {market.market_rank_position}</span>
            <span>{market.source_timestamp}</span>
            {market.caveats.map((caveat) => (
              <span key={caveat}>{caveat}</span>
            ))}
          </dl>
        ) : (
          <p className="dg-two-lane__degraded">Market unavailable</p>
        )}
      </div>

      <div
        data-testid="player-divergence"
        className="dg-two-lane__divergence dg-two-lane__divergence--neutral"
      >
        <span>{divergenceLabel}</span>
      </div>
    </div>
  );
}
