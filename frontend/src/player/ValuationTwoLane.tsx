// Surface-3 T8 — two physically separate valuation lanes + uniform-neutral
// divergence. Model (blue) and market (amber) are never blended; the divergence
// element is uniform-neutral slate — direction is conveyed by LABEL TEXT only,
// never by directional brand colour, and the numeric delta is not rendered.
//
// DG-043: every fact is a real labeled pair — <div><dt>label</dt><dd>value</dd></div>
// groups are the only children the <dl> carries (axe definition-list), and per
// David's 2026-08-29 prose ruling the labels speak plain fantasy language:
// no raw pipeline keys, no raw ISO timestamps on screen.
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

// Raw caveat keys never reach the screen (prose ruling). Known keys get the
// sentence a smart friend would say; an unknown key degrades to its own words
// (underscores to spaces) — reformatted, never given fabricated meaning.
const CAVEAT_SENTENCES: Record<string, string> = {
  market_overlay_static_caveat:
    "Market values come from a saved FantasyCalc snapshot, not a live feed.",
  source_timestamp_is_fetch_time_not_publish_time:
    "The capture date above is when we pulled these prices, not when the source published them.",
};

function caveatSentence(caveat: string): string {
  const known = CAVEAT_SENTENCES[caveat];
  if (known !== undefined) {
    return known;
  }
  const words = caveat.replaceAll("_", " ").trim();
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}.`;
}

// The artifact emits percentiles on a 0-100 scale (compute_dvs_pct_batch rounds
// to one decimal; the sibling xvar_percentile_overall is 0-100 too), so render
// as-is. Multiplying by 100 here was a latent unit bug that never fired while
// the field was NULL on every row (pre-DG-086).
function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value)}%`;
}

function marketSourceLabel(source: string | null | undefined): string {
  return source === "fantasycalc" ? "FantasyCalc" : (source ?? "—");
}

// Readable capture date ("Jul 22, 2026"). UTC so the shown day never shifts
// with the viewer's clock; an unparseable timestamp falls back to the raw
// string (honest, never fabricated) and an absent one renders the em dash.
const CAPTURE_DATE_FORMAT = new Intl.DateTimeFormat("en-US", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

function captureDate(timestamp: string | null | undefined): string {
  if (timestamp === null || timestamp === undefined) {
    return "—";
  }
  const parsed = Date.parse(timestamp);
  return Number.isNaN(parsed) ? timestamp : CAPTURE_DATE_FORMAT.format(parsed);
}

function Fact({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="dg-two-lane__fact">
      <dt>{label}</dt>
      <dd>{value ?? "—"}</dd>
    </div>
  );
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
            <Fact label="Engine" value={model.engine_path} />
            <Fact label="Model grade" value={model.model_grade} />
            <Fact label="Dynasty value" value={model.dynasty_value_score} />
            <Fact label="Value above replacement (xVAR)" value={model.xvar} />
            <Fact
              label="Position percentile"
              value={percent(model.xvar_percentile_position)}
            />
            <Fact label="1-year projection" value={model.projection_1y} />
            <Fact label="2-year projection" value={model.projection_2y} />
            <Fact label="3-year projection" value={model.projection_3y} />
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
          <>
            <dl className="dg-two-lane__facts">
              <Fact label="Source" value={marketSourceLabel(market.source)} />
              <Fact label="Market value" value={market.market_value} />
              <Fact label="Overall rank" value={market.market_rank_overall} />
              <Fact label="Position rank" value={market.market_rank_position} />
              <Fact
                label="Prices captured"
                value={captureDate(market.source_timestamp)}
              />
            </dl>
            {market.caveats.map((caveat) => (
              <p key={caveat} className="dg-two-lane__note">
                {caveatSentence(caveat)}
              </p>
            ))}
          </>
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
