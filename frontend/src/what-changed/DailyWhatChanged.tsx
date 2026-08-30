import { type ReactNode, useEffect, useState } from "react";
import { TEAM_COLORS } from "../generated/teamColors";
import type {
  WhatChangedEnteredExited,
  WhatChangedMarketDelta,
  WhatChangedMarketSection,
  WhatChangedModelDelta,
  WhatChangedModelSection,
  WhatChangedResponse,
  WhatChangedStructuralContext,
  WhatChangedStructuralSection,
} from "../lib/api/types.gen";
import {
  zCaptureHealthResponse,
  zModelProvenanceResponse,
  zWhatChangedResponse,
} from "../lib/api/zod.gen";
import {
  describeToken,
  fieldLabel,
  formatCaptureTimestamp,
  receiptDetail,
  valueWord,
} from "../lib/copy";
import { useEndpointResource } from "../lib/useEndpointResource";
import {
  PlayerNameButton,
  PlayerSelectionProvider,
  type SelectPlayer,
  usePlayerSelection,
} from "../player/playerSelection";
import { DailyTape as UiDailyTape } from "../ui/DailyTape";
import { MetricCell } from "../ui/MetricCell";
import { PlayerIdentity } from "../ui/PlayerIdentity";
import { ReceiptTrigger } from "../ui/ReceiptTrigger";
import { SeriesSlot } from "../ui/SeriesSlot";
import { ValueHero } from "../ui/ValueHero";
import { projectionBasisTitle } from "./projectionBasis";
import "./DailyWhatChanged.css";

type State =
  | { status: "loading" }
  | { status: "ready"; data: WhatChangedResponse }
  | { status: "unavailable" }
  | { status: "parse-error" };

// DG-089 (found by David, first real user session): "this player moved — let
// me click him" did nothing. Rows open the shell's shared player-selection
// plumbing when the surface is given a handler. Context rather than prop
// threading: AssetRow sits several layers beneath the surface prop, and every
// player row on the feed should behave identically. With no handler (bare
// mounts, tests), rows stay non-interactive — no phantom buttons.
//
// DG-110 promoted that context out of this file: it is now the whole
// product's one selection sink (player/playerSelection). The surface prop
// still works for a bare mount and simply overrides what the shell provides.

// The Daily What-Changed surface: the day-over-day market and model deltas.
// Market and model stay in structurally isolated regions so a market price
// swing never reads as a model signal. The desk reads top-down: one dated
// masthead with the tape, then the change feed.
//
// DG-111 (David, 2026-08-29): the stamped honesty furniture is retired. Seven
// "Descriptive only — not decision-grade." lines, six "Status:" stamps, the
// stacked caveat blocks and the FEED DIAGNOSTICS / RECEIPTS / Movement-history
// rail are gone. Every FACT they carried survives — as one plain sentence
// where it applies, with the producer's verbatim token kept reachable in the
// "Where this comes from" sheet at the bottom of the rail.
export function DailyWhatChanged({
  onSelectPlayer,
}: {
  onSelectPlayer?: SelectPlayer | undefined;
} = {}) {
  const [state, setState] = useState<State>({ status: "loading" });
  // The shell's sink when it is mounted inside one; the explicit prop still
  // wins so a bare mount can be driven directly.
  const inheritedSelectPlayer = usePlayerSelection();

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const res = await fetch("/api/league/what-changed");
        if (!res.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        const data = zWhatChangedResponse.parse(
          await res.json(),
        ) as WhatChangedResponse;
        if (active) setState({ status: "ready", data });
      } catch {
        if (active) setState({ status: "parse-error" });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") {
    return <p className="dg-wc__notice">Loading daily changes…</p>;
  }
  if (state.status === "unavailable") {
    return <p className="dg-wc__notice">Daily What-Changed unavailable.</p>;
  }
  if (state.status === "parse-error") {
    return <p className="dg-wc__notice">Could not read daily What-Changed.</p>;
  }
  return (
    <PlayerSelectionProvider value={onSelectPlayer ?? inheritedSelectPlayer}>
      <ReadyView data={state.data} />
    </PlayerSelectionProvider>
  );
}

// Signed and neutral: the sign encodes direction, so there is no arrow, color,
// or buy/sell word to smuggle in a verdict. Raw value (not rounded) — the
// backend owns precision. -0 keeps its sign rather than reading as +0.
function fmtSigned(value: number): string {
  if (Object.is(value, -0)) {
    return "-0";
  }
  return value >= 0 ? `+${value}` : `${value}`;
}

const NEUTRAL_DASH = "—";
const EXACT_ZERO_NOTE = "exact zero — shown as a neutral dash, not movement";

// An exact zero is NOT movement, so it must not wear a direction sign: it
// renders as the neutral dash. A negative zero means "declined by less than
// display precision" and keeps its honest -0.
function formatZeroDelta(value: number): string {
  if (value === 0 && !Object.is(value, -0)) {
    return NEUTRAL_DASH;
  }
  return fmtSigned(value);
}

function DeltaCell({
  label,
  value,
  emphasis,
  labelHidden,
}: {
  label: string;
  value: number;
  emphasis?: "row-focal" | undefined;
  /** Worklist #3: the column header carries the label once; per-row labels
   *  move to the accessibility layer (52 repeats ≈ 100 wasted words). */
  labelHidden?: boolean | undefined;
}) {
  const text = formatZeroDelta(value);
  return (
    <span
      className="dg-wc__delta-cell"
      title={text === NEUTRAL_DASH ? EXACT_ZERO_NOTE : undefined}
    >
      {/* When the column header carries the visible label, the per-row label
          moves to a screen-reader-only element so assistive tech still names
          the cell — a genuine hidden label, not an aria prop on a generic span. */}
      {labelHidden ? <span className="dg-wc__sr-only">{label}</span> : null}
      <MetricCell label={labelHidden ? "" : label} value={text} emphasis={emphasis} />
    </span>
  );
}

// ── Increment 1: the AssetRow tape (rethink v3 §5 / Increment-1 spec v3) ─────
// Lenient client-side series read: anything that is not a 2+-point dated
// series renders the pending slot — a malformed producer row degrades to
// honesty, never to a fabricated line (fail-safe, spec seed 6).
function usableSeriesPoints(
  series: unknown,
): { capturedAt: string; value: number }[] | null {
  if (series === null || typeof series !== "object") return null;
  const points = (series as { points?: unknown }).points;
  if (!Array.isArray(points) || points.length < 2) return null;
  const mapped: { capturedAt: string; value: number }[] = [];
  for (const point of points) {
    if (
      point === null ||
      typeof point !== "object" ||
      typeof (point as { date?: unknown }).date !== "string" ||
      typeof (point as { value?: unknown }).value !== "number"
    ) {
      return null;
    }
    mapped.push({
      capturedAt: (point as { date: string }).date,
      value: (point as { value: number }).value,
    });
  }
  return mapped;
}

function teamAccentFor(teamId: string | null | undefined): string | undefined {
  if (!teamId) return undefined;
  return TEAM_COLORS[teamId]?.primary;
}

// Fail-safe headshot contract (discipline-reset finding #3): only claim an
// image when a sleeper id actually exists. A null/blank id degrades to the
// PlayerIdentity headshot→initials fallback chain — it must never build a
// literal `/assets/headshots/undefined.jpg` request. One source of truth for
// every row type (asset rows, universe chips, baseline rows) so the divergence
// cannot reappear on one surface.
function headshotProps(sleeperId: string | null | undefined): {
  imageStatus: "available" | "missing";
  imageSrc: string | undefined;
} {
  // Trim before the truthiness check (Codex boundary finding): a whitespace-only
  // id is as blank as null and must degrade to the fallback — never build a
  // `/assets/headshots/   .jpg` request. The URL uses the trimmed id.
  const id = sleeperId?.trim();
  return id
    ? { imageStatus: "available", imageSrc: `/assets/headshots/${id}.jpg` }
    : { imageStatus: "missing", imageSrc: undefined };
}

function lastSeriesDate(series: unknown): string | null {
  const points = usableSeriesPoints(series);
  return points === null ? null : (points[points.length - 1]?.capturedAt ?? null);
}

function seriesBasis(series: unknown): string | null {
  if (series === null || typeof series !== "object") return null;
  const basis = (series as { basis?: unknown }).basis;
  return typeof basis === "string" && basis.trim() !== "" ? basis : null;
}

function LaneSeriesSlot({ series, label }: { series: unknown; label: string }) {
  const points = usableSeriesPoints(series);
  return points === null ? (
    <SeriesSlot status="pending" label={label} />
  ) : (
    <SeriesSlot status="ready" label={label} points={points} />
  );
}

// One player's line on the tape: identity (real cached headshot, DB-driven
// team mark), the row-focal signed delta in its OWN lane, the other lane an
// explicit neutral dash (lane symmetry: silence is shown, never implied), and
// the PIT series ending at the Hard Right Edge.
function AssetRow({
  sleeperId,
  name,
  position,
  teamId,
  lane,
  children,
  seriesLabel,
  series,
  rank,
  currentValue,
}: {
  sleeperId: string | null | undefined;
  name: string;
  position: string;
  teamId: string | null | undefined;
  lane: "model" | "market";
  children: React.ReactNode;
  seriesLabel: string;
  series: unknown;
  rank?: number | undefined;
  currentValue?: string | undefined;
}) {
  const otherLane = lane === "model" ? "market" : "model";
  // The trim-before-truthiness rule and the no-phantom-button rule both live
  // in PlayerNameButton now (DG-110); a blank id still degrades to the plain,
  // non-interactive identity.
  return (
    <li data-asset-row data-row-density="32px" className="dg-wc__player-row">
      {rank !== undefined && <span className="dg-wc__rank">{rank}</span>}
      <PlayerNameButton
        sleeperId={sleeperId}
        name={name}
        context={[position, teamId].filter(Boolean).join(" ")}
        className="dg-wc__player-open"
      >
        <PlayerIdentity
          name={name}
          team={teamId ?? ""}
          position={position}
          {...headshotProps(sleeperId)}
          teamId={teamId ?? undefined}
          teamAccent={teamAccentFor(teamId)}
        />
      </PlayerNameButton>
      <span data-lane={lane} className="dg-wc__lane">
        {currentValue !== undefined && (
          <span
            className="dg-wc__current-value"
            title="current value (level, not movement)"
          >
            {currentValue}
          </span>
        )}
        {children}
        <LaneSeriesSlot series={series} label={seriesLabel} />
        <ReceiptTrigger
          label={name}
          capturedAt={lastSeriesDate(series) ?? "capture date unavailable"}
          source={seriesBasis(series) ?? `${lane} lane — series pending`}
        />
      </span>
      <span
        data-lane={otherLane}
        className="dg-wc__lane dg-wc__lane--flat"
        title={`no ${otherLane} movement on this row's tape`}
      >
        {NEUTRAL_DASH}
      </span>
    </li>
  );
}

const DESK_DATE = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  weekday: "long",
  month: "long",
  day: "numeric",
});

// The masthead title is the day itself — the daily-login moment. The shell h1
// already names the surface; repeating it here would double the heading.
function deskDate(iso: string): string {
  const parsed = Date.parse(iso);
  return Number.isNaN(parsed) ? "Today's report" : DESK_DATE.format(new Date(parsed));
}

// Staleness basis (spec v3 key-state 3): the report judges its OWN data truth
// via generated_at; ≥26h (the 02 backup-law interval + grace) or unparseable
// → stale. System-level capture health stays the shell's separate trust axis.
const STALE_HOURS_THRESHOLD = 26;

function staleHours(generatedAt: string): number | null {
  const parsed = Date.parse(generatedAt);
  if (Number.isNaN(parsed)) return null;
  return (Date.now() - parsed) / 3_600_000;
}

// DG-111 — the freshness fact, in one sentence, every morning.
//
// This REPLACES the "Stale data caveat — the capture is 27.5 hours old. The
// tape below reflects the last verified capture, not this morning." badge. The
// three facts it carried are all still here and are the only reason this line
// exists: (1) the data is old, (2) by exactly this much, (3) what you are
// looking at is the last verified snapshot rather than today's. The
// unreadable-timestamp branch stays loud rather than falling silent — an
// unparseable capture time is the one case where saying nothing would be a lie
// of omission.
function freshnessSentence(generatedAt: string, hours: number | null): string {
  if (hours === null) {
    return (
      "We couldn't read when this data was captured, so treat everything below as " +
      "the last verified snapshot, not today's."
    );
  }
  if (hours >= STALE_HOURS_THRESHOLD) {
    return (
      `This morning's capture didn't land — everything below is ${hours.toFixed(1)} ` +
      "hours old, the last verified snapshot, not today's."
    );
  }
  // Deliberately "as of", not "current" or "fresh": the report can be up to 26
  // hours old and still sit under the stale threshold, so this line states the
  // capture time and lets the reader judge it. It never claims freshness the
  // timestamp does not support.
  return `These numbers are as of ${formatCaptureTimestamp(generatedAt)}.`;
}

function ReadyView({ data }: { data: WhatChangedResponse }) {
  const daily = data.daily_diff;
  const marketWindow = (daily.market.comparison_window ?? null) as {
    from_date?: string | null;
    to_date?: string | null;
  } | null;
  // SR-16: the hero is the number David acts on — how many of HIS players
  // moved. roster_deltas is NOT a mover list (it holds every roster player
  // present in both snapshots, flat ones included), so filter on value_delta;
  // counting .length would print a near-constant roster size every morning.
  const rosterMovers = (daily.market.roster_deltas ?? []).filter(
    (row) => row.value_delta !== 0,
  );
  const largestMover = rosterMovers.reduce<(typeof rosterMovers)[number] | null>(
    (best, row) =>
      best === null || Math.abs(row.value_delta) > Math.abs(best.value_delta)
        ? row
        : best,
    null,
  );
  // DG-110: the basis says exactly what it always said — how many of his
  // players moved, and which one moved most, by how much. The largest mover's
  // NAME is now the handle onto his card; the sentence is unchanged.
  const largestMoverName = largestMover
    ? (largestMover.player_name ?? largestMover.player_key)
    : null;
  const heroBasis =
    largestMover && largestMoverName !== null ? (
      <>
        {`${rosterMovers.length} of your players; largest `}
        <PlayerNameButton
          sleeperId={largestMover.sleeper_id}
          name={largestMoverName}
          context={largestMover.position ?? undefined}
          className="dg-wc__hero-open"
        />
        {` ${largestMover.value_delta > 0 ? "+" : ""}${largestMover.value_delta}`}
      </>
    ) : (
      "no movement on your roster since the prior snapshot"
    );

  const hours = staleHours(data.generated_at);
  const isStale = hours === null || hours >= STALE_HOURS_THRESHOLD;

  const baselineRows = (
    data.structural_context as {
      baseline_roster_rows?:
        | {
            sleeper_id: string;
            player_name?: string | null;
            position?: string | null;
            team_id?: string | null;
          }[]
        | null;
    }
  ).baseline_roster_rows;
  const quietDay = rosterMovers.length === 0;

  return (
    <section
      className={`dg-wc dg-motion-daily-open${isStale ? " dg-wc--stale" : ""}`}
      aria-label="Daily What-Changed"
    >
      <header className="dg-wc__desk-header">
        <div className="dg-wc__masthead">
          <h2 className="dg-wc__title">{deskDate(data.generated_at)}</h2>
          <ValueHero
            label="Your roster moved"
            value={String(rosterMovers.length)}
            basis={heroBasis}
          />
        </div>
        <p className="dg-wc__disclaimer">
          What changed on your roster and around the league since the last snapshot.
        </p>
        <p
          className={isStale ? "dg-wc__stale-badge" : "dg-wc__freshness"}
          data-testid="wc-freshness"
          title={data.generated_at}
        >
          {freshnessSentence(data.generated_at, hours)}
        </p>
      </header>
      <div className="dg-wc__layout">
        {/* Model movement FIRST (spec v3 §2, Gemini nudge finding): the model
            is the rational anchor; market-first would anchor the morning read
            on crowd noise before the model's evaluation. */}
        <div className="dg-wc__feed" data-stale={isStale ? "true" : undefined}>
          {quietDay && (
            <div className="dg-wc__quiet-day">
              <p className="dg-wc__quiet">
                No valuation deltas observed on your roster since the last capture
                (checked {deskDate(data.generated_at)}). The roster holds its baseline
                below.
              </p>
              {baselineRows && baselineRows.length > 0 && (
                <BaselineRosterRows rows={baselineRows} />
              )}
            </div>
          )}
          <ModelRegion model={daily.model} />
          <MarketRegion market={daily.market} />
          <StructuralBaseline ctx={data.structural_context} />
        </div>
        <ContextRail data={data} marketWindow={marketWindow} />
      </div>
    </section>
  );
}

// DG-111 — the rail's furniture becomes one receipt sheet.
//
// It used to be three stacked panels: FEED DIAGNOSTICS (four status lines),
// RECEIPTS (four provenance lines) and a "Movement history — Series pending"
// chart frame with its own disclosure stamp. All of that was true and none of
// it was what David needed at 7am. The content is intact and complete, one
// press down, in a sheet that is shut by default. This is the only place on
// the surface where machine vocabulary is allowed — including every producer
// reason verbatim, so humanizing a token upstairs never destroys it.
function ContextRail({
  data,
  marketWindow,
}: {
  data: WhatChangedResponse;
  marketWindow: { from_date?: string | null; to_date?: string | null } | null;
}) {
  const market = data.daily_diff.market;
  const model = data.daily_diff.model;
  const modelWindow = model.comparison_window ?? null;
  const basisTitle = projectionBasisTitle(modelWindow);
  const rawReasons = producerReasons(data);

  return (
    <aside className="dg-wc__rail" aria-label="Report context">
      <DailyTape />
      {/* DG-111: the rail's "Feed diagnostics" and "Receipts" panels are one
          sheet now, shut by default. Nothing in them was deleted — the surface
          upstairs says every one of these facts in English, and this is where
          the exact tokens stay.

          `data-receipt` is DG-109's declaration (renderRule.ts:48) that this
          subtree is the "where this comes from" layer, which is the one place
          the render rule permits a raw pipeline key: a receipt that renamed the
          artifact it cites would stop being a receipt. Without the attribute
          this sheet would be the only raw copy on the front page. */}
      <details className="dg-wc__receipts" data-receipt data-testid="wc-provenance">
        <summary className="dg-wc__rail-title">Where this comes from</summary>
        <p className="dg-wc__rail-line" title={data.generated_at}>
          Report built {formatCaptureTimestamp(data.generated_at)}.
        </p>
        {marketWindow?.from_date && marketWindow?.to_date && (
          <p className="dg-wc__rail-line">
            Market prices captured {marketWindow.from_date} vs {marketWindow.to_date}.
          </p>
        )}
        {/* The price feed every market number on this page came from. It is a
            REQUIRED schema field (zod.gen.ts zWhatChangedMarketSection), so it
            is always available — and it used to hang off the capture-window
            conditional, which meant the sheet lost the source entirely on any
            morning the window carried no dates. The sheet has to be complete
            when asked, so it stands on its own line. */}
        {market.market_source && (
          <p className="dg-wc__rail-line">Market source: {market.market_source}.</p>
        )}
        {modelWindow?.from_date && modelWindow?.to_date && (
          <p className="dg-wc__rail-line">
            Model window {modelWindow.from_date} vs {modelWindow.to_date}.
          </p>
        )}
        {basisTitle && (
          <p className="dg-wc__rail-line" title={basisTitle}>
            {model.vintage_changed
              ? "Projection basis changed within this window"
              : "Projection basis consistent across this window"}
          </p>
        )}
        <p className="dg-wc__rail-line">
          Feed status: {data.overall_status} · market {market.status} · model{" "}
          {model.status}
        </p>
        {rawReasons.length > 0 && (
          <p className="dg-wc__rail-line" data-testid="wc-raw-reasons">
            Producer reasons, verbatim: {rawReasons.join(", ")}
          </p>
        )}
      </details>
    </aside>
  );
}

// A dictionary sentence already ends in a full stop; a humanized fallback does
// not. Both have to sit in front of the age clause without running into it.
function endSentence(text: string): string {
  return /[.!?]$/.test(text) ? text : `${text}.`;
}

// Every producer reason on the report, verbatim and de-duplicated. The surface
// above says these in English; this is the copy that keeps the exact token, so
// a humanized sentence is a translation and never a deletion.
//
// PANEL FIX: the market lane's `comparison_window.status` was missing from this
// list while the model lane's was present. That is the axis daily_diff.py:111-117
// uses to report `insufficient_history` — a state that carries NO
// `aborted_reason` — so the one place the report recorded it verbatim did not
// record it at all. Both lanes are read the same way now.
function producerReasons(data: WhatChangedResponse): string[] {
  const market = data.daily_diff.market;
  const model = data.daily_diff.model;
  const sections = data.structural_context.sections as unknown as Record<
    string,
    WhatChangedStructuralSection
  >;
  return [
    ...new Set(
      [
        market.aborted_reason ?? null,
        market.comparison_window?.status ?? null,
        model.comparison_window?.status ?? null,
        model.feature_freshness?.aborted_reason ?? null,
        model.pvo_staleness?.aborted_reason ?? null,
        ...Object.values(sections).map((sec) => sec?.aborted_reason ?? null),
        ...Object.values(sections).map((sec) => sec?.staleness_caveat?.basis ?? null),
      ].filter((item): item is string => item != null && item !== ""),
    ),
  ];
}

function humanAssetKey(key: string): string {
  return key.startsWith("sleeper:") ? key.slice("sleeper:".length) : key;
}

// A comparison that never ran is not a comparison that came back bad, and the
// front page must not call the first one a degradation. `insufficient_history`
// means this install does not have two capture dates yet — a young history, not
// a fault — and `baseline_holding` means today's run is the same vintage as
// yesterday's, so there is nothing to compare. Calling either "degraded" is the
// DG-047 cry-wolf pattern in new clothes: it spends the word on a normal
// morning and leaves nothing to say on a bad one.
const NOT_A_FAULT: ReadonlySet<string> = new Set([
  "insufficient_history",
  "baseline_holding",
]);

/**
 * The one honesty sentence for a lane (market or model), or null when the lane
 * is clean.
 *
 * PANEL FIX — THE BLOCKER. The market lane reports trouble on TWO axes and only
 * one of them is an `aborted_reason`: daily_diff.py:111-117 returns
 * `status: "insufficient_history"` with no `aborted_reason` at all when fewer
 * than two FantasyCalc capture dates exist. The old gate here read
 * `market.aborted_reason &&`, so on that morning the region fell silent and its
 * empty-state copy — "market values held steady overnight" — stood as an
 * affirmative claim about a comparison that was never made. Before DG-111 the
 * rail said `Market feed: insufficient_history` in always-visible text; moving
 * that line into a receipt sheet that is shut by default is what turned a
 * cluttered truth into a clean falsehood.
 *
 * Both lanes now go through here, so they cannot drift apart again.
 */
function laneNotice(
  lane: "market" | "model",
  reasons: readonly string[],
): string | null {
  if (reasons.length === 0) return null;
  // A dictionary sentence ends in a full stop; here it is a CLAUSE inside a
  // longer sentence, so the stop comes off. Nothing else about the string is
  // touched — the words the dictionary chose are the words that render.
  const said = reasons
    .map((token) => describeToken(token).replace(/\.$/, ""))
    .join("; ");
  const numbers = lane === "market" ? "the prices below" : "the model numbers below";
  if (reasons.every((token) => NOT_A_FAULT.has(token))) {
    const subject = lane === "market" ? "market prices" : "our projections";
    return `Heads up: we couldn't compare ${subject} against an earlier day — ${said} — so nothing below is a change, it's just where things stand.`;
  }
  const side = lane === "market" ? "the market side" : "the model side";
  return `Heads up: ${side} came back degraded — ${said} — so treat ${numbers} as provisional.`;
}

function MarketRegion({ market }: { market: WhatChangedMarketSection }) {
  const topMovers = market.top_movers ?? [];
  const rosterDeltas = market.roster_deltas ?? [];
  // Voice: strip the raw backend key prefix from entered/exited ids — full
  // name resolution for these rows rides the identity slice (residual debt,
  // recorded in the Increment-1 delta doc).
  const entered = market.entered ?? [];
  const exited = market.exited ?? [];

  // The market lane's trouble arrives on either axis, and only one of them is an
  // `aborted_reason` — see `laneNotice`. `status` is the closed set
  // {ok, unavailable, insufficient_history} (daily_diff.py:100-118, :150-165),
  // so anything but "ok" means the day-over-day comparison did not happen.
  const marketReasons = market.aborted_reason
    ? [market.aborted_reason]
    : market.status !== "ok"
      ? [market.status]
      : [];
  const notice = laneNotice("market", marketReasons);
  // No comparison ran → an empty row list means "we did not look", never "we
  // looked and nothing moved". The empty-state copy has to stop making the
  // second claim, or the honesty sentence above is arguing with the page.
  const compared = marketReasons.length === 0;
  // The trend note explains BLANK sparklines. It is only true when a blank one
  // is on screen: once a player's series has points, `LaneSeriesSlot` draws a
  // real line and the note would be contradicting the picture beside it.
  const anyPendingSeries = [...rosterDeltas, ...topMovers].some(
    (row) =>
      usableSeriesPoints((row as { market_series?: unknown }).market_series) === null,
  );

  return (
    <section className="dg-wc__region" aria-label="Market price-discovery overlay">
      <h3 className="dg-wc__region-title">Market movement</h3>
      <p className="dg-wc__overlay-note">
        Market prices — what the dynasty market is paying, kept separate from our own
        projections.
      </p>
      {/* DG-111: was a "Market feed caveats" block printing the raw producer
          token. One sentence now; the token itself is preserved verbatim in the
          title attribute and in the receipt sheet, so nothing is lost. */}
      {notice && (
        <p
          className="dg-wc__overlay-note"
          data-testid="wc-market-degraded"
          title={marketReasons.join(", ")}
        >
          {notice}
        </p>
      )}

      <h4 className="dg-wc__group">Your roster</h4>
      {rosterDeltas.length === 0 ? (
        <p className="dg-wc__quiet">
          {compared
            ? "Your roster's market values held steady — no movement on this tape."
            : "No day-over-day comparison for your roster on this tape."}
        </p>
      ) : (
        <MarketRows rows={rosterDeltas} />
      )}

      <h4 className="dg-wc__group">Around the league</h4>
      {topMovers.length === 0 ? (
        <p className="dg-wc__quiet">
          {compared
            ? "No player movement on this tape — market values held steady overnight."
            : "No day-over-day comparison league-wide on this tape."}
        </p>
      ) : (
        <>
          <MarketRows rows={topMovers} />
          {/* SR-16: honest truncation — the league-wide total stays on the
              surface but never pretends to be about his roster, and a nullish
              total is never invented. */}
          <p className="dg-wc__overlay-note">
            {market.total_movers_count != null
              ? `Showing ${topMovers.length} of ${market.total_movers_count} market movers league-wide`
              : `Showing ${topMovers.length} market movers`}
          </p>
        </>
      )}

      {/* DG-111: this one line replaces the rail's "Movement history — Series
          pending. History accrues one verified capture per day; the line begins
          once enough days are on the books." panel. Same fact, said once, next
          to the blank trend slots it explains — and, per the review panel, ONLY
          when there is a blank slot on screen for it to explain. The panel it
          replaced was true because the slot it wrapped was pending by
          construction; an unconditional copy of it would contradict the first
          real sparkline the page draws. */}
      {anyPendingSeries && (
        <p className="dg-wc__overlay-note" data-testid="wc-trend-note">
          Trend lines fill in as daily prices accrue — one capture a day — so they stay
          blank until enough days are on the books.
        </p>
      )}

      <h4 className="dg-wc__group">Entered</h4>
      <UniverseChipList items={entered} emptyLabel="No entered assets." />

      <h4 className="dg-wc__group">Exited</h4>
      <UniverseChipList items={exited} emptyLabel="No exited assets." />
    </section>
  );
}

// Entered/exited universe chips: these rows are exactly where identity is most
// likely partial (a just-appeared/just-departed asset), so they ride the same
// fail-safe headshot contract as every other row — a missing sleeper id draws
// the initials fallback, never a broken `undefined.jpg` face-hole.
function UniverseChipList({
  items,
  emptyLabel,
}: {
  items: WhatChangedEnteredExited[];
  emptyLabel: string;
}) {
  if (items.length === 0) {
    return <p className="dg-wc__quiet">{emptyLabel}</p>;
  }
  return (
    <ul className="dg-wc__list">
      {items.map((e, i) => {
        // DG-110: a name that just entered or left the pool is exactly the
        // one you want to look up; the chip opens his card like every other
        // player row. No sleeper id, no button — same rule as the rows.
        const name = e.player_name ?? humanAssetKey(e.player_key);
        return (
          <li key={e.sleeper_id ?? i} className="dg-wc__universe-chip">
            <PlayerNameButton
              sleeperId={e.sleeper_id}
              name={name}
              context={[e.position, e.team_id].filter(Boolean).join(" ")}
              className="dg-wc__player-open"
            >
              <PlayerIdentity
                name={name}
                team={e.team_id ?? ""}
                position={e.position ?? ""}
                {...headshotProps(e.sleeper_id)}
                teamId={e.team_id ?? undefined}
              />
            </PlayerNameButton>
          </li>
        );
      })}
    </ul>
  );
}

// Feed rows are identity-first (benchmark parity: data feels human): the
// player, the signed delta, and an honest pending slot where that player's
// series will land once enough daily captures accrue. No table semantics —
// each row is one player's line on the tape.
const ROW_CAP = 10;

function MarketRows({ rows }: { rows: WhatChangedMarketDelta[] }) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? rows : rows.slice(0, ROW_CAP);
  return (
    <>
      <div className="dg-wc__col-header" aria-hidden="true">
        <span>Player</span>
        <span>Value · Δ · 30-day</span>
      </div>
      <ul className="dg-wc__rows">
        {visible.map((r, i) => (
          <AssetRow
            key={r.sleeper_id ?? i}
            rank={i + 1}
            sleeperId={r.sleeper_id}
            name={r.player_name ?? humanAssetKey(r.player_key)}
            position={r.position ?? ""}
            teamId={(r as { team_id?: string | null }).team_id}
            currentValue={
              (r as { current_value?: number | null }).current_value != null
                ? String((r as { current_value?: number | null }).current_value)
                : undefined
            }
            lane="market"
            seriesLabel={`${r.player_name ?? r.player_key} market series`}
            series={(r as { market_series?: unknown }).market_series}
          >
            <DeltaCell
              label="Market value change"
              value={r.value_delta}
              emphasis="row-focal"
              labelHidden
            />
          </AssetRow>
        ))}
      </ul>
      {rows.length > ROW_CAP && (
        <button
          type="button"
          className="dg-wc__expand"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show top 10" : `Show all ${rows.length}`}
        </button>
      )}
    </>
  );
}

// H2 I2a daily tape: substrate facts ONLY — never movement or trend claims.
// Each endpoint degrades independently to an honest unavailable line.
function DailyTape() {
  const capture = useEndpointResource({
    url: "/api/system/capture-health",
    schema: zCaptureHealthResponse,
  });
  const provenance = useEndpointResource({
    url: "/api/system/model-provenance",
    schema: zModelProvenanceResponse,
  });

  // The tape appears only once both substrate endpoints have settled — a
  // half-loaded tape would juxtapose facts with placeholders. Ready facts and
  // honest unavailable lines are the only two voices it has.
  if (capture.status === "loading" || provenance.status === "loading") {
    return null;
  }

  const firstStore = capture.status === "ready" ? capture.data.stores[0] : undefined;

  // The surface maps endpoint truth onto the voice-guide tape primitive:
  // manager prose on screen, raw values in the title layer (prose principle).
  return (
    <UiDailyTape
      capture={
        capture.status === "ready" && firstStore
          ? {
              consecutiveDays: firstStore.timeline.consecutive_days_current,
              lastCaptureAt: firstStore.staleness.last_capture_date ?? "",
              status: capture.data.overall_status === "ok" ? "ok" : "degraded",
            }
          : { consecutiveDays: 0, lastCaptureAt: "", status: "unavailable" }
      }
      provenance={
        provenance.status === "ready"
          ? {
              registryVersion: provenance.data.registry_version,
              modelVintage: provenance.data.overall_status,
              status: provenance.data.overall_status === "ok" ? "ok" : "degraded",
            }
          : { registryVersion: 0, modelVintage: "unavailable", status: "unavailable" }
      }
    />
  );
}

function ModelRegion({ model }: { model: WhatChangedModelSection }) {
  const deltas = model.deltas ?? [];
  const modelWindow = model.comparison_window ?? null;
  // These three are raw producer enums. They run through the copy dictionary on
  // the way to the screen — on a quiet day all three are absent, which is
  // exactly why the fixture-pinned test never caught them here.
  const caveats = [
    modelWindow?.status ?? null,
    model.feature_freshness?.aborted_reason ?? null,
    model.pvo_staleness?.aborted_reason ?? null,
  ].filter((item): item is string => item != null);
  const notice = laneNotice("model", caveats);
  // `comparison_window.status` is set ONLY on the two paths where the producer
  // refuses to compare — `insufficient_history` (fewer than two capture dates)
  // and `model_multi_vintage_ambiguous` (two model runs on one day). The success
  // path carries dates and vintages and no status at all (daily_diff.py:237-282).
  // So a status here means the empty delta list is "we did not compare", never
  // "we compared and nothing moved".
  const compared = modelWindow?.status == null;

  return (
    <section className="dg-wc__region" aria-label="Model output changes">
      <h3 className="dg-wc__region-title">Model output changes</h3>
      {/* DG-111: one sentence in place of the stacked caveat block; the raw
          tokens ride the title attribute and the receipt sheet. */}
      {notice && (
        <p
          className="dg-wc__overlay-note"
          data-testid="wc-model-degraded"
          title={caveats.join(", ")}
        >
          {notice}
        </p>
      )}
      {deltas.length === 0 ? (
        <p className="dg-wc__quiet">
          {compared
            ? "Projections held steady — no player movement on this tape."
            : "No day-over-day comparison of our projections on this tape."}
        </p>
      ) : (
        <ModelRows rows={deltas} />
      )}
    </section>
  );
}

function ModelRows({ rows }: { rows: WhatChangedModelDelta[] }) {
  return (
    <ul className="dg-wc__rows">
      {rows.map((r, i) => (
        <AssetRow
          key={r.sleeper_id ?? i}
          rank={i + 1}
          sleeperId={r.sleeper_id}
          name={r.player_name ?? humanAssetKey(r.player_key)}
          position={r.position ?? ""}
          teamId={(r as { team_id?: string | null }).team_id}
          currentValue={
            (r as { current_value?: number | null }).current_value != null
              ? String((r as { current_value?: number | null }).current_value)
              : undefined
          }
          lane="model"
          seriesLabel={`${r.player_name ?? r.player_key} model series`}
          series={(r as { model_series?: unknown }).model_series}
        >
          <DeltaCell
            label="Model value change"
            value={r.dynasty_value_score_delta}
            emphasis="row-focal"
            labelHidden
          />
          <DeltaCell label="Percentile" value={r.dvs_pct_delta} />
          {/* DG-117: was "Above replacement" — a fifth spelling of the one
              quantity. `xvar_delta` is the change in it, and the column sits
              under a "change" header, so the label is the quantity's name. */}
          <DeltaCell label={fieldLabel("xvar")} value={r.xvar_delta} />
        </AssetRow>
      ))}
    </ul>
  );
}

// Quiet-day baseline (spec v3 key-state 1): David's roster locked flat —
// rendered ONLY when the producer supplies baseline_roster_rows; both lanes
// are honest dashes (0 delta by definition), series pending.
function BaselineRosterRows({
  rows,
}: {
  rows: {
    sleeper_id: string;
    player_name?: string | null;
    position?: string | null;
    team_id?: string | null;
  }[];
}) {
  // DG-089: quiet-day mornings show ONLY these rows — David's founding gesture
  // ("this is my player, let me click him") must work here too, same context
  // gate, same trim rule as AssetRow.
  return (
    <ul className="dg-wc__rows">
      {rows.map((r) => {
        const name = r.player_name ?? r.sleeper_id;
        return (
          <li
            key={r.sleeper_id}
            data-asset-row
            data-row-density="32px"
            className="dg-wc__player-row"
          >
            <PlayerNameButton
              sleeperId={r.sleeper_id}
              name={name}
              context={[r.position, r.team_id].filter(Boolean).join(" ")}
              className="dg-wc__player-open"
            >
              <PlayerIdentity
                name={name}
                team={r.team_id ?? ""}
                position={r.position ?? ""}
                {...headshotProps(r.sleeper_id)}
                teamId={r.team_id ?? undefined}
              />
            </PlayerNameButton>
            <span data-lane="model" className="dg-wc__lane dg-wc__lane--flat">
              {NEUTRAL_DASH}
            </span>
            <span data-lane="market" className="dg-wc__lane dg-wc__lane--flat">
              {NEUTRAL_DASH}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

// Structural current-state context (Slice 2 semantics, Task 5 voice). It is
// deliberately SUBORDINATE to the deltas above — a where-things-stand-now
// anchor, not a change surface — and renders section SUMMARIES/COUNTS only.
// The producer artifact carries named, priority-ranked drop candidates and
// named divergence cards; those are DELIBERATELY not rendered here — a static
// named/ranked cut list reads as a drop directive and duplicates the
// interactive Roster Capacity sandbox. That deferral is enforced by RED
// suppression assertions.
function StructuralBaseline({ ctx }: { ctx: WhatChangedStructuralContext }) {
  const s = ctx.sections;
  return (
    <section className="dg-wc__baseline" aria-label="Structural current-state baseline">
      <h3 className="dg-wc__region-title">Current roster context</h3>
      <p className="dg-wc__overlay-note">
        Where the roster stands right now — the backdrop for today's movement, not the
        movement itself.
      </p>

      <BaselineSection label="Team Posture" sec={s.team_posture}>
        {s.team_posture.david_posture != null && (
          <p className="dg-wc__baseline-line">
            Where you stand: {valueWord(s.team_posture.david_posture)}
          </p>
        )}
        {s.team_posture.team_count != null && (
          <p className="dg-wc__baseline-line">
            Team count: {s.team_posture.team_count}
          </p>
        )}
      </BaselineSection>

      <BaselineSection label="Team Value" sec={s.team_value}>
        <TeamValueLines sec={s.team_value} />
      </BaselineSection>

      <BaselineSection label="League Opportunity" sec={s.league_opportunity}>
        <p className="dg-wc__baseline-line">
          Partner ranking count:{" "}
          {s.league_opportunity.top_partner_rankings?.length ?? 0}
        </p>
        <p className="dg-wc__baseline-line">
          Card count: {s.league_opportunity.top_cards?.length ?? 0}
        </p>
        {cardTypeCounts(s.league_opportunity.top_cards).map(([type, count]) => (
          <p className="dg-wc__baseline-line" key={type}>
            {valueWord(type)}: {count}
          </p>
        ))}
        {/* DG-111: was a titled "Divergence caveat" block. Same fact, said the
            way you would say it out loud. It is a caution, not permission. */}
        <p className="dg-wc__baseline-line">
          These are counts of divergence cards, not a proven edge — we have not
          validated that they predict anything.
        </p>
      </BaselineSection>

      <BaselineSection label="Drop Pressure" sec={s.drop_pressure}>
        {s.drop_pressure.summary?.cuts_required != null && (
          <p className="dg-wc__baseline-line">
            Cuts required: {s.drop_pressure.summary.cuts_required}
          </p>
        )}
        {s.drop_pressure.summary?.total_players != null && (
          <p className="dg-wc__baseline-line">
            Total players: {s.drop_pressure.summary.total_players}
          </p>
        )}
        {s.drop_pressure.summary?.total_capacity != null && (
          <p className="dg-wc__baseline-line">
            Total capacity: {s.drop_pressure.summary.total_capacity}
          </p>
        )}
      </BaselineSection>

      <BaselineSection label="Sleeper Snapshot" sec={s.sleeper_snapshot}>
        {s.sleeper_snapshot.david_roster_player_count != null && (
          <p className="dg-wc__baseline-line">
            David roster player count: {s.sleeper_snapshot.david_roster_player_count}
          </p>
        )}
        {s.sleeper_snapshot.league_roster_count != null && (
          <p className="dg-wc__baseline-line">
            League roster count: {s.sleeper_snapshot.league_roster_count}
          </p>
        )}
      </BaselineSection>
    </section>
  );
}

// DG-111 — per-section honesty, in a sentence, only when there is something to
// say.
//
// Each of these five sections used to carry the same three-part stamp: a
// "Status: ok" line, a disclosure line, and a "Context caveats" block printing
// `captured_at_vs_report_generated_at — fresh (age 0h)`. Five identical
// paragraphs of nothing, every morning.
//
// What survives is the rule underneath: a section that is NOT clean must say so
// in words. A healthy section renders silence — silence here means "ok" and
// only "ok", because any other status produces a sentence. The producer's own
// tokens stay verbatim in the title attribute and in the receipt sheet.
function sectionNotice(sec: WhatChangedStructuralSection): string | null {
  const parts: string[] = [];
  const stale = sec.staleness_caveat;
  if (stale?.is_stale) {
    parts.push(
      `this one is ${stale.age_hours} hours old and flagged stale, so it is the last verified read rather than a fresh one`,
    );
  }
  if (sec.aborted_reason) {
    parts.push(
      `part of it did not come through — ${describeToken(sec.aborted_reason)}`,
    );
  } else if (sec.status !== "ok" && parts.length === 0) {
    parts.push(`this section came back ${describeToken(sec.status)}`);
  }
  if (parts.length === 0) {
    return null;
  }
  const lead = `Heads up: ${parts.join("; ")}.`;
  // DG-109's dictionary answers "measured against what?" — `basis` names WHICH
  // pair of clocks the age was taken between. An age without its basis is half a
  // fact, so the stale branch keeps both: how old, and against what.
  return stale?.is_stale ? `${lead} ${endSentence(describeToken(stale.basis))}` : lead;
}

function BaselineSection({
  label,
  sec,
  children,
}: {
  label: string;
  sec: WhatChangedStructuralSection;
  children: ReactNode;
}) {
  const notice = sectionNotice(sec);
  const rawTokens = [sec.staleness_caveat?.basis ?? null, sec.aborted_reason ?? null]
    .filter((item): item is string => item != null)
    .join(", ");

  return (
    <section className="dg-wc__baseline-section" aria-label={label}>
      <h4 className="dg-wc__group">{label}</h4>
      {/* One notice, not three. It carries every fact the retired trio carried —
          the section's status when it is not ok, WHY it is short when the
          producer aborted, and how stale it is measured against which clock —
          and the verbatim producer tokens ride the title attribute and the
          receipt sheet. A clean section says nothing, because silence here means
          "ok" and only "ok": any other status produces a sentence. */}
      {notice && (
        <p
          className="dg-wc__baseline-meta"
          data-testid="wc-section-notice"
          title={rawTokens || undefined}
        >
          {notice}
        </p>
      )}
      {children}
    </section>
  );
}

// Team value in manager language; the raw producer field names live one layer
// down in the title attributes (voice-guide prose principle).
function TeamValueLines({ sec }: { sec: WhatChangedStructuralSection }) {
  const v = sec.david_value_summary;
  if (!v) {
    return <p className="dg-wc__quiet">No team value summary.</p>;
  }
  return (
    <>
      {v.lineup_xvar != null && (
        <p
          className="dg-wc__baseline-line"
          title={receiptDetail("lineup_xvar", v.lineup_xvar)}
        >
          Starting lineup value: {v.lineup_xvar}
        </p>
      )}
      {v.starter_weighted_xvar != null && (
        <p
          className="dg-wc__baseline-line"
          title={receiptDetail("starter_weighted_xvar", v.starter_weighted_xvar)}
        >
          Weekly lineup strength: {v.starter_weighted_xvar}
        </p>
      )}
      {v.top_n_xvar != null && (
        <p
          className="dg-wc__baseline-line"
          title={receiptDetail("top_n_xvar", v.top_n_xvar)}
        >
          Top-asset core value: {v.top_n_xvar}
        </p>
      )}
      {v.total_xvar_capped != null && (
        <p
          className="dg-wc__baseline-line"
          title={receiptDetail("total_xvar_capped", v.total_xvar_capped)}
        >
          Whole-roster value, capped: {v.total_xvar_capped}
        </p>
      )}
    </>
  );
}

// Count cards by type, preserving first-seen order for stable rendering.
function cardTypeCounts(
  cards: WhatChangedStructuralSection["top_cards"],
): Array<[string, number]> {
  const counts = new Map<string, number>();
  for (const card of cards ?? []) {
    const type = card.card_type ?? "UNKNOWN";
    counts.set(type, (counts.get(type) ?? 0) + 1);
  }
  return [...counts.entries()];
}
