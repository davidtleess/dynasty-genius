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
import { basisWord, fieldLabel, sourcedCaveat, valueWord } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

type PlayerDetail = z.infer<typeof zPlayerDetailResponse>;
type ModelLane = PlayerDetail["model"];
type MarketLane = PlayerDetail["market"];
type Divergence = PlayerDetail["divergence"];

// Rendered when a value the backend owns is simply absent — never a zero, never
// a guess.
const UNKNOWN = "—";

// The artifact emits percentiles on a 0-100 scale (compute_dvs_pct_batch rounds
// to one decimal; the sibling xvar_percentile_overall is 0-100 too), so render
// as-is. Multiplying by 100 here was a latent unit bug that never fired while
// the field was NULL on every row (pre-DG-086).
function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? UNKNOWN : `${Math.round(value)}%`;
}

function marketSourceLabel(source: string | null | undefined): string {
  return source === "fantasycalc" ? "FantasyCalc" : (source ?? UNKNOWN);
}

// The caveat sentences name the source, so an absent source must reach them as
// an empty string rather than as the em dash the FACT rows use.
function sourceForSentence(source: string | null | undefined): string {
  const label = marketSourceLabel(source);
  return label === UNKNOWN ? "" : label;
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

// Per ECMAScript, an ISO date-time carrying NO timezone designator is parsed as
// the viewer's LOCAL time. Formatting that instant back out in UTC then shifts
// the calendar day — west of Greenwich an evening stamp renders as tomorrow, a
// date the viewer has not reached. The legacy refresh path forwards
// `source_timestamp` verbatim (scripts/run_market_divergence_refresh.py:293), so
// an offset-less stamp is reachable. Pin those to UTC: the day shown is then
// always the calendar day the source itself wrote.
const OFFSETLESS_ISO = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/;

function captureDate(timestamp: string | null | undefined): string {
  if (timestamp === null || timestamp === undefined) {
    return UNKNOWN;
  }
  const trimmed = timestamp.trim();
  const pinned = OFFSETLESS_ISO.test(trimmed)
    ? `${trimmed.replace(" ", "T")}Z`
    : timestamp;
  const parsed = Date.parse(pinned);
  return Number.isNaN(parsed) ? timestamp : CAPTURE_DATE_FORMAT.format(parsed);
}

// An enum the backend may simply not have. Absent stays the em dash the numeric
// facts use — never a fabricated word, never the string "null".
function enumFact(value: string | null | undefined): string {
  return value === null || value === undefined ? UNKNOWN : valueWord(value);
}

function Fact({
  label,
  value,
  basis,
}: {
  label: string;
  value: string | number | null;
  /** DG-128: the score's basis (A / B / blend) for the stylesheet; "" = none. */
  basis?: string;
}) {
  return (
    <div className="dg-two-lane__fact" data-basis={basis}>
      <dt>{label}</dt>
      <dd>{value ?? UNKNOWN}</dd>
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
  // "unavailable" is the players route's own fallback when no divergence block
  // exists (app/api/routes/players.py:295) — say that, rather than a bare word
  // that could read as a verdict on the player.
  const divergenceLabel =
    divergence.status === "unavailable"
      ? "We have no price comparison for him right now."
      : valueWord(divergence.status);

  return (
    <div className="dg-two-lane">
      <div
        data-testid="player-model-lane"
        data-lane="model"
        className="dg-two-lane__lane dg-two-lane__lane--model"
      >
        {model ? (
          <dl className="dg-two-lane__facts">
            {/* Which model scored him and what state that score is in are both
                FACTS, not machinery — they stay, said in words. */}
            {/* DG-128 (2026-09-01): "Scored by" names what PRODUCED the score —
                its basis — and falls back to the lane for a row from before the
                marker existed. The basis also rides `data-basis` as a marker;
                nothing styles on it — David ruled 2026-09-01 that the number is
                not greyed by its basis. DG-144 (2026-09-03): the range fact
                that sat under the value is gone — "one number per player";
                the API still carries the band and this card does not read it. */}
            <Fact
              label="Scored by"
              value={basisWord(model.dvs_engine) ?? enumFact(model.engine_path)}
            />
            <Fact label="Model status" value={enumFact(model.model_grade)} />
            <Fact
              label="Dynasty value"
              value={model.dynasty_value_score}
              basis={model.dvs_engine ?? ""}
            />
            {/* DG-117: was "Value above replacement (xVAR)" — a fourth name for
                the quantity the roster surfaces and League Pulse already spell
                differently. The dictionary spells it once now. */}
            <Fact label={fieldLabel("xvar")} value={model.xvar} />
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
            <TokenNotes
              className="dg-two-lane__notes"
              notes={market.caveats.map((caveat) =>
                sourcedCaveat(caveat, sourceForSentence(market.source)),
              )}
            />
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
