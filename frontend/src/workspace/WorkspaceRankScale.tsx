// DG-196 — the shared us-vs-market rank scale, adapted from the imported Directions design.
//
// The artifact (RankScale.dc.html plus scaleFor() in the main HTML) draws one player on one
// 388-long axis. It is a drawing, and a component has to be stricter than a drawing in five ways,
// each of which the artifact gets wrong because it never had to be general:
//
//   1. the population is a prop, not the constant 388 welded into pos(), the ticks and the captions;
//   2. BOTH sides can be tied — the artifact reads mktE only to size the zoom window and would draw
//      a market tie at its start, silently reporting a span as a point;
//   3. a one-player population is legal, and (1-1)/(1-1) is NaN;
//   4. a malformed interval is refused, never clipped into the axis, because a coordinate invented
//      to keep the picture drawable is the failure path returning the success signal;
//   5. a magnified axis always carries labels — the artifact's tick loop starts at
//      ceil(lo/step)*step and emits nothing at all for a window like #1..#8.
//
// Everything else is the artifact's: the shared best-to-worst axis, ours above in blue, the market
// below in amber, the neutral hull between them, the ticks, the exact numeric labels, the caption
// that declares the population, and the zoomed local inset with its stated extent.
import type { CSSProperties } from "react";

import { rankText } from "../market-ranks/MarketRanks";
import "./WorkspaceRankScale.css";

export type RankSpan = { start: number; end: number; total: number };
export type WorkspaceRankScaleProps = {
  ourRank: RankSpan | null;
  marketRank: RankSpan | null;
  playerName: string;
};

/** A rank has to be a whole place inside its own population. NaN and Infinity fail Number.isInteger. */
function isDrawable(span: RankSpan | null): boolean {
  if (span === null) return true; // absent is not malformed; it is handled as missing
  const { start, end, total } = span;
  if (![start, end, total].every((value) => Number.isInteger(value))) return false;
  return total >= 1 && start >= 1 && start <= end && end <= total;
}

/**
 * Map a rank onto 0-100 within the window [low, high]. Rank `low` sits at the left edge, `high` at
 * the right. A window holding ONE place has exactly one position, and it is the middle: the
 * alternative, 0/0, is the NaN the artifact emits for a one-player population.
 *
 * This is the only place a rank becomes a coordinate. It used to be two functions, one of which
 * handled the degenerate window and one of which did not, which is how the one-player axis drew at
 * the far left instead of its single place.
 */
function place(rank: number, low: number, high: number): number {
  return high === low ? 50 : ((rank - low) / (high - low)) * 100;
}

const percent = (value: number): string => `${Number(value.toFixed(4))}%`;

/**
 * A label's position and its own width, handed to the CSS so it can clamp inside the axis.
 *
 * The artifact anchors by coordinate alone: translateX(-50%) between 7% and 93%, and flush at the
 * edges. That is blind to how wide the text is, so on a 260px column "Market #40-49" centred at 10%
 * still escapes the container. The width is knowable here — these are monospace digits — so the
 * component states the box and the stylesheet clamps the position against it.
 */
function labelBox(at: number, characters: number): CSSProperties {
  return {
    "--dg-rank-scale-at": percent(at),
    "--dg-rank-scale-box": `${characters}ch`,
  } as CSSProperties;
}

/** Endpoints plus quarters, as ranks. Deduped, so a tiny population does not repeat a tick. */
function tickRanks(total: number): number[] {
  if (total === 1) return [1];
  const marks = [0, 0.25, 0.5, 0.75, 1].map((fraction) =>
    Math.round(1 + (total - 1) * fraction),
  );
  return [...new Set(marks)].sort((left, right) => left - right);
}

/**
 * Ranks to label inside a magnified window. The window ends are always present — an axis that
 * magnifies without saying what it magnified is worse than no inset at all.
 */
function zoomTickRanks(low: number, high: number): number[] {
  // End labels plus one interior reading leave space for full rank labels even in a narrow
  // inspector. The old step grid put #133 and #140 on top of one another at 260px.
  return [...new Set([low, Math.round((low + high) / 2), high])];
}

type Direction = "higher" | "lower" | "same" | "overlap";

/** The project's existing rank-gap arithmetic, so this scale and the dense row never disagree. */
function directionOf(
  ours: RankSpan,
  market: RankSpan,
): { direction: Direction; text: string } {
  const gapMin = market.start - ours.end;
  const gapMax = market.end - ours.start;
  const exact = ours.start === ours.end && market.start === market.end;
  if (exact && ours.start === market.start) {
    return { direction: "same", text: "We and the market place him at the same rank." };
  }
  if (gapMin > 0 || gapMax < 0) {
    const direction: Direction = gapMin > 0 ? "higher" : "lower";
    const places = gapMin > 0 ? gapMin : Math.abs(gapMax);
    const bound = gapMin === gapMax ? "" : "at least ";
    return {
      direction,
      text: `We rank him ${bound}${places} ${places === 1 ? "place" : "places"} ${direction}.`,
    };
  }
  return {
    direction: "overlap",
    text: "The two readings overlap, so neither is clearly ahead.",
  };
}

function Marks({
  span,
  side,
  low,
  high,
}: {
  span: RankSpan;
  side: "ours" | "market";
  low: number;
  high: number;
}) {
  const at = (rank: number) => place(rank, low, high);
  const tied = span.start !== span.end;
  // A tie is drawn as the whole span it really is. Its minimum VISIBLE width lives in the CSS, never
  // in this number: DG-188 shipped a 0.5 meant as 0.5% that was a 50% floor, and every exact rank
  // filled half the axis while a genuine 159-wide tie looked identical to one player.
  if (tied) {
    return (
      <div
        className="dg-rank-scale__band"
        data-side={side}
        style={{
          left: percent(at(span.start)),
          width: percent(at(span.end) - at(span.start)),
        }}
      />
    );
  }
  return (
    <div
      className="dg-rank-scale__mark"
      data-side={side}
      style={{ left: percent(at(span.start)) }}
    />
  );
}

function Plot({
  ours,
  market,
  low,
  high,
  ticks,
  zoom,
}: {
  ours: RankSpan;
  market: RankSpan;
  low: number;
  high: number;
  ticks: number[];
  zoom: boolean;
}) {
  const at = (rank: number) => place(rank, low, high);
  const hullStart = at(Math.min(ours.start, market.start));
  const hullEnd = at(Math.max(ours.end, market.end));
  const ourAnchor = (at(ours.start) + at(ours.end)) / 2; // anchors TEXT only; the span stays whole
  const marketAnchor = (at(market.start) + at(market.end)) / 2;
  const tag = (side: "ours" | "market", label: string, at: number) => {
    const word = side === "ours" ? "Ours" : "Market";
    return (
      <span
        className="dg-rank-scale__tag"
        data-side={side}
        style={labelBox(at, word.length + label.length + 2)}
      >
        <span className="dg-rank-scale__side">{word}</span>
        {label}
      </span>
    );
  };
  return (
    <div
      className={`dg-rank-scale__plot${zoom ? " dg-rank-scale__plot--zoom" : ""}`}
      aria-hidden="true"
    >
      {!zoom && (
        <div className="dg-rank-scale__lane" data-side="ours">
          {tag("ours", rankText(ours), ourAnchor)}
        </div>
      )}
      <div className="dg-rank-scale__axis">
        <div className="dg-rank-scale__rail" />
        <div
          className="dg-rank-scale__hull"
          style={{ left: percent(hullStart), width: percent(hullEnd - hullStart) }}
        />
        <div className="dg-rank-scale__row" data-side="ours">
          <Marks span={ours} side="ours" low={low} high={high} />
        </div>
        <div className="dg-rank-scale__row" data-side="market">
          <Marks span={market} side="market" low={low} high={high} />
        </div>
      </div>
      {!zoom && (
        <div className="dg-rank-scale__lane" data-side="market">
          {tag("market", rankText(market), marketAnchor)}
        </div>
      )}
      <div
        className={`dg-rank-scale__ticks${zoom ? " dg-rank-scale__ticks--zoom" : ""}`}
      >
        {ticks.map((rank) => {
          const label = `#${rank}`;
          return (
            <span
              key={rank}
              className="dg-rank-scale__tick"
              style={labelBox(at(rank), label.length)}
            >
              {label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

export function WorkspaceRankScale({
  ourRank,
  marketRank,
  playerName,
}: WorkspaceRankScaleProps) {
  const who = <span data-user-text>{playerName}</span>;

  // A refusal draws nothing. Clipping a bad interval to keep the picture would put a coordinate on
  // screen that no rank produced.
  if (!isDrawable(ourRank) || !isDrawable(marketRank)) {
    return (
      <figure className="dg-rank-scale dg-rank-scale--refused">
        <figcaption className="dg-rank-scale__caption">
          {who}. A rank interval here is not a whole place inside its own population, so
          there is no comparable scale to draw.
        </figcaption>
      </figure>
    );
  }
  if (ourRank !== null && marketRank !== null && ourRank.total !== marketRank.total) {
    return (
      <figure className="dg-rank-scale dg-rank-scale--refused">
        <figcaption className="dg-rank-scale__caption">
          {who}. Our rank counts a population of {ourRank.total} and the market's counts{" "}
          {marketRank.total}. Those are two different fields, not one scale, so there is
          no comparable scale to draw.
        </figcaption>
      </figure>
    );
  }

  // A side with no rank is missing, not zero. No axis is drawn, because half an axis invites the
  // reader to place the absent side somewhere, and the only honest place is nowhere.
  // The nesting is what narrows the types: the falsity of "both are null" tells TypeScript nothing
  // about either one, so each side is tested on its own.
  if (ourRank === null) {
    if (marketRank === null) {
      return (
        <figure className="dg-rank-scale dg-rank-scale--partial">
          <figcaption className="dg-rank-scale__caption">
            {who} carries no rank from us and no market rank, so there is no scale to
            draw.
          </figcaption>
        </figure>
      );
    }
    return (
      <figure className="dg-rank-scale dg-rank-scale--partial">
        <figcaption className="dg-rank-scale__caption">
          {who}. The market ranks him {rankText(marketRank)} of {marketRank.total}. He
          carries no rank from us, so there is nothing to set beside it. Missing, not
          zero.
        </figcaption>
      </figure>
    );
  }
  if (marketRank === null) {
    return (
      <figure className="dg-rank-scale dg-rank-scale--partial">
        <figcaption className="dg-rank-scale__caption">
          {who}. We rank him {rankText(ourRank)} of {ourRank.total}. He carries no
          market rank, so there is nothing to set beside ours. Missing, not zero.
        </figcaption>
      </figure>
    );
  }

  const total = ourRank.total;
  const { text: directionText } = directionOf(ourRank, marketRank);
  const tied = ourRank.start !== ourRank.end || marketRank.start !== marketRank.end;

  // The local window. pad = ceil(total / 20) reproduces the artifact's +/-20 on a 388 axis without
  // inheriting the constant. The inset appears only when it genuinely magnifies.
  const pad = Math.max(1, Math.ceil(total / 20));
  const windowLow = Math.max(1, Math.min(ourRank.start, marketRank.start) - pad);
  const windowHigh = Math.min(total, Math.max(ourRank.end, marketRank.end) + pad);
  // The artifact shows the inset when the window is under 340 of 387, i.e. 88% of the axis. Kept as
  // a ratio rather than the constant: an inset re-plotting almost the whole population is a second
  // copy of the first axis, not a magnification.
  const zoomed =
    total > 1 && windowHigh > windowLow && windowHigh - windowLow < (total - 1) * 0.88;

  return (
    <figure className="dg-rank-scale">
      <Plot
        ours={ourRank}
        market={marketRank}
        low={1}
        high={total}
        ticks={tickRanks(total)}
        zoom={false}
      />
      <figcaption className="dg-rank-scale__caption">
        {who}. We rank him {rankText(ourRank)}, the market {rankText(marketRank)}, on
        one shared {total}-player scale where lower is better. {directionText}
        {tied
          ? " A tie is a rank tie: several players hold those places, and it is drawn as the span it really is. It is not a confidence interval."
          : ""}
      </figcaption>
      {zoomed && (
        <div className="dg-rank-scale__zoom">
          <p className="dg-rank-scale__zoom-head">
            <span className="dg-rank-scale__zoom-title">Same two marks, closer in</span>
            <span className="dg-rank-scale__zoom-extent">
              {`Zoomed: #${windowLow}–#${windowHigh} of ${total}`}
            </span>
          </p>
          <Plot
            ours={ourRank}
            market={marketRank}
            low={windowLow}
            high={windowHigh}
            ticks={zoomTickRanks(windowLow, windowHigh)}
            zoom
          />
        </div>
      )}
    </figure>
  );
}
