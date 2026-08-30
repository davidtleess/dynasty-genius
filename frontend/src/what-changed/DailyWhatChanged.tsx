import { useEffect, useState } from "react";
import { TEAM_COLORS } from "../generated/teamColors";
import type {
  WhatChangedEnteredExited,
  WhatChangedMarketDelta,
  WhatChangedMarketSection,
  WhatChangedModelDelta,
  WhatChangedModelSection,
  WhatChangedResponse,
  WhatChangedStructuralSection,
} from "../lib/api/types.gen";
import {
  zCaptureHealthResponse,
  zModelProvenanceResponse,
  zWhatChangedResponse,
} from "../lib/api/zod.gen";
import { describeToken, fieldLabel, formatCaptureTimestamp } from "../lib/copy";
import { useEndpointResource } from "../lib/useEndpointResource";
import {
  PlayerNameButton,
  PlayerSelectionProvider,
  type SelectPlayer,
  usePlayerSelection,
} from "../player/playerSelection";
import { MetricCell } from "../ui/MetricCell";
import { PlayerIdentity } from "../ui/PlayerIdentity";
import { ReceiptTrigger } from "../ui/ReceiptTrigger";
import { SeriesSlot } from "../ui/SeriesSlot";
import { type FeedHealth, feedHealth, freshnessLine } from "./feedHealth";
import {
  verdict as buildVerdict,
  type ComparisonWindow,
  cutPressure,
  endSentence,
  leagueMovers,
  movement,
  num,
  RECOMMENDATION_METHOD,
  type Recommendation,
  staleInputClause,
  staleInputs,
  whereYouStand,
  windowPhrase,
  worthALook,
} from "./morningRead";
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

// The sign encodes direction in TEXT: no arrow glyph is fabricated and no
// buy/sell word appears, so the delta reads correctly with color stripped out.
// (AMENDED by DG-115: this comment used to say "and no color" too. Since
// David's 2026-08-30 "Green up / red down" ruling the cell also carries a
// direction hue — see deltaDirection() below. What survives unchanged is the
// part that matters: the printed sign is always there, so the hue is a second
// channel and never the only one, and neither channel says whether the move is
// good for you.) Raw value (not rounded) — the backend owns precision. -0 keeps
// its sign rather than reading as +0.
function fmtSigned(value: number): string {
  if (Object.is(value, -0)) {
    return "-0";
  }
  return value >= 0 ? `+${value}` : `${value}`;
}

const NEUTRAL_DASH = "—";
const EXACT_ZERO_NOTE = "exact zero — shown as a neutral dash, not movement";

// An exact zero is NOT movement, so it must not wear a direction sign: it
// renders as the neutral dash. A negative zero keeps its honest -0 rather than
// being flattened to +0 — we print the sign we were handed.
function formatZeroDelta(value: number): string {
  if (value === 0 && !Object.is(value, -0)) {
    return NEUTRAL_DASH;
  }
  return fmtSigned(value);
}

/**
 * DG-115 direction color (David's 2026-08-30 panel: "Green up / red down").
 *
 * The hue is derived from the SAME function that prints the characters, so the
 * two can never tell different stories: whatever formatZeroDelta() renders as
 * the neutral dash gets no direction, and otherwise the hue simply follows the
 * printed sign. That is the whole claim — the color restates the sign the
 * reader can already see, and the sign is always printed, so color is never
 * the only channel.
 *
 * Two things it deliberately does NOT claim. (1) It says nothing about what a
 * negative zero MEANS. An earlier draft of this comment read it as "declined by
 * less than display precision"; the producer has no such concept — daily_diff.py
 * emits a raw `latest - prior` subtraction with no rounding step (see its
 * locked sign conventions at the top of the module), and value_delta is integer
 * arithmetic, so -0 is not something it sets out to produce. We print the sign
 * we were handed and color it to match; we do not narrate it. (2) A non-finite
 * delta gets NO direction. The text for one is already wrong ("NaN"), which is
 * a pre-existing hazard in an unvalidated field, but a hue that says "declined"
 * over characters that say no such thing would be this change's own fabrication.
 */
function deltaDirection(value: number): "up" | "down" | undefined {
  if (!Number.isFinite(value)) return undefined;
  if (formatZeroDelta(value) === NEUTRAL_DASH) return undefined;
  return value > 0 ? "up" : "down";
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
  const direction = deltaDirection(value);
  return (
    <span
      className="dg-wc__delta-cell"
      title={text === NEUTRAL_DASH ? EXACT_ZERO_NOTE : undefined}
      {...(direction !== undefined ? { "data-direction": direction } : {})}
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

/**
 * DG-113 — the morning read.
 *
 * Reading order is the order of David's three questions: am I ok (the header's
 * freshness line, then the verdict), what should I look at ("Worth a look"),
 * what moved (his roster, then the league), and last the standing context.
 *
 * The model region keeps its place BELOW the market one now. The old comment
 * here argued model-first so the morning would not be anchored on crowd noise;
 * that was written when the page was a two-lane delta surface with no verdict.
 * It has one now, the verdict is what anchors the morning, and on live payloads
 * the model region is a single honest sentence about why no comparison ran —
 * which is not the thing to open on.
 */
function ReadyView({ data }: { data: WhatChangedResponse }) {
  const daily = data.daily_diff;
  const marketWindow = (daily.market.comparison_window ??
    null) as ComparisonWindow | null;
  const sections = data.structural_context.sections;

  const hours = staleHours(data.generated_at);
  const isStale = hours === null || hours >= STALE_HOURS_THRESHOLD;

  const pressure = cutPressure(sections.drop_pressure);
  const moved = movement(
    daily.market,
    sections.sleeper_snapshot.status === "ok"
      ? (sections.sleeper_snapshot.david_roster_player_count ?? null)
      : null,
  );
  // The two sections the verdict and the cut card are BUILT from, each carrying
  // its own staleness clock — which is not the report's (see `staleInputs`).
  // `drop_pressure` produces the headline and the named cut; `sleeper_snapshot`
  // produces the "your 27 players" total that the deleted debug dump used to be
  // the only home for, and with the dump went the only place its notice
  // rendered.
  const inputStaleClause = staleInputClause(
    staleInputs([
      { label: "roster-limit check", section: sections.drop_pressure },
      { label: "roster read", section: sections.sleeper_snapshot },
    ]),
  );
  const verdict = buildVerdict({
    pressure,
    moved,
    // The header already carries the freshness sentence in full; the verdict
    // only needs the reader to know the numbers under it are not this
    // morning's. Saying it twice at full length is the stamp habit again.
    stalenessClause: isStale
      ? "Everything below is the last verified snapshot, not this morning's."
      : null,
    inputStaleClause,
  });
  const recommendations = worthALook({
    pressure,
    moved,
    window: marketWindow,
    inputStaleClause,
  });
  const standing = whereYouStand(data, pressure);

  const baselineRows = data.structural_context.baseline_roster_rows;
  const quietDay = moved.kind === "flat" || moved.kind === "none-priced";

  return (
    <section
      className={`dg-wc dg-motion-daily-open${isStale ? " dg-wc--stale" : ""}`}
      aria-label="Daily What-Changed"
    >
      <MorningHeader data={data} hours={hours} isStale={isStale} />

      <section
        className="dg-wc__verdict"
        data-testid="wc-verdict"
        data-tone={verdict.tone}
        aria-label="This morning's verdict"
      >
        <p className="dg-wc__verdict-headline">{verdict.headline}</p>
        {verdict.detail !== "" && (
          <p className="dg-wc__verdict-detail">
            {/* DG-110's rule survives the hero it was written for: the largest
                mover's NAME is still the handle onto his card, now inside the
                sentence rather than under a figure. */}
            {verdict.detailParts === null ? (
              verdict.detail
            ) : (
              <>
                {verdict.detailParts.lead}
                <PlayerNameButton
                  sleeperId={
                    moved.kind === "moved" ? moved.largest.sleeper_id : undefined
                  }
                  name={verdict.detailParts.name}
                  context={
                    moved.kind === "moved"
                      ? (moved.largest.position ?? undefined)
                      : undefined
                  }
                  className="dg-wc__verdict-open"
                />
                {verdict.detailParts.tail}
              </>
            )}
          </p>
        )}
      </section>

      <WorthALookBlock
        cards={recommendations.cards}
        missing={recommendations.missing}
      />

      <div className="dg-wc__feed" data-stale={isStale ? "true" : undefined}>
        <MarketRegion market={daily.market} />
        {quietDay && baselineRows && baselineRows.length > 0 && (
          <section className="dg-wc__region" aria-label="Your roster at rest">
            <h3 className="dg-wc__region-title">Your roster, as it stands</h3>
            <p className="dg-wc__overlay-note">
              Nothing of yours moved, so here is the roster the report was built
              against.
            </p>
            <BaselineRosterRows rows={baselineRows} />
          </section>
        )}
        <ModelRegion model={daily.model} />
        <WhereYouStandBlock
          standing={standing}
          postureSection={sections.team_posture}
          dropSection={sections.drop_pressure}
        />
      </div>
    </section>
  );
}

// ── the header band ──────────────────────────────────────────────────────────

/**
 * DG-113 — one freshness sentence with a dot, and the health sheet behind it.
 *
 * This is what is left of the right-hand rail. The "Partial Market Sync"
 * monospace tape, the FEED DIAGNOSTICS panel and the RECEIPTS panel are gone
 * from the page; every fact they carried is in the sheet below, which is shut
 * by default and expands IN FLOW — an accordion, so it can never overlap
 * content at any scroll position (the same structural choice ShellStatusDrawer
 * made and for the same reason).
 */
function MorningHeader({
  data,
  hours,
  isStale,
}: {
  data: WhatChangedResponse;
  hours: number | null;
  isStale: boolean;
}) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const capture = useEndpointResource({
    url: "/api/system/capture-health",
    schema: zCaptureHealthResponse,
  });
  const provenance = useEndpointResource({
    url: "/api/system/model-provenance",
    schema: zModelProvenanceResponse,
  });
  // Loading is NOT "unread": a sentence claiming we could not reach the feed
  // check, printed for the 200ms before it answers, would be a lie that
  // corrects itself. The feed clause simply waits.
  const feeds: FeedHealth =
    capture.status === "loading"
      ? { kind: "read", rows: [], behind: 0, allGaps: false, allRanToday: false }
      : feedHealth(capture.status === "ready" ? capture.data : null);
  const line = freshnessLine(
    freshnessSentence(data.generated_at, hours),
    isStale,
    capture.status === "loading" ? { kind: "unread" } : feeds,
  );
  const sentence =
    capture.status === "loading"
      ? freshnessSentence(data.generated_at, hours)
      : line.sentence;

  return (
    <header className="dg-wc__desk-header">
      <div className="dg-wc__masthead">
        <div>
          <p className="dg-wc__overline">Morning read</p>
          <h2 className="dg-wc__title">{deskDate(data.generated_at)}</h2>
        </div>
        <p
          className="dg-wc__freshness"
          data-testid="wc-freshness"
          data-status={capture.status === "loading" ? "unknown" : line.status}
          title={data.generated_at}
        >
          <span
            className="dg-wc__freshness-dot"
            data-freshness-dot
            data-status={capture.status === "loading" ? "unknown" : line.status}
            aria-hidden="true"
          />
          <span>{sentence}</span>{" "}
          <button
            type="button"
            className="dg-wc__details"
            data-testid="wc-health-sheet-toggle"
            aria-expanded={sheetOpen}
            onClick={() => setSheetOpen((open) => !open)}
          >
            {sheetOpen ? "Hide details" : "Details"}
          </button>
        </p>
      </div>
      {sheetOpen && (
        <HealthSheet
          data={data}
          feeds={feeds}
          // PANEL FIX: the header separates loading from unread precisely so a
          // sentence claiming we could not reach the feed check is never
          // printed for the 200ms before it answers — and then handed the
          // sheet a boolean that folded the two back together. The sheet gets
          // the same three states the header has.
          captureState={
            capture.status === "ready"
              ? "ready"
              : capture.status === "loading"
                ? "loading"
                : "unread"
          }
          provenanceState={
            provenance.status === "ready"
              ? "ready"
              : provenance.status === "loading"
                ? "loading"
                : "unread"
          }
          provenance={
            provenance.status === "ready"
              ? {
                  registryVersion: provenance.data.registry_version,
                  status: provenance.data.overall_status,
                }
              : null
          }
        />
      )}
    </header>
  );
}

/**
 * The health sheet: every feed as a plain row, then the report's own receipts.
 *
 * The receipt half keeps `data-receipt` — DG-109's declaration (renderRule.ts)
 * that this subtree is the "where this comes from" layer, the one place a raw
 * pipeline key is allowed, because a receipt that renamed the artifact it cites
 * would stop being a receipt. The feed rows above it do NOT carry that
 * exemption and are held to the dictionary like any other prose.
 */
function HealthSheet({
  data,
  feeds,
  captureState,
  provenanceState,
  provenance,
}: {
  data: WhatChangedResponse;
  feeds: FeedHealth;
  captureState: "ready" | "loading" | "unread";
  provenanceState: "ready" | "loading" | "unread";
  provenance: { registryVersion: number; status: string } | null;
}) {
  const market = data.daily_diff.market;
  const model = data.daily_diff.model;
  const modelWindow = model.comparison_window ?? null;
  const marketWindow = (market.comparison_window ?? null) as ComparisonWindow | null;
  const basisTitle = projectionBasisTitle(modelWindow);
  const rawReasons = producerReasons(data);

  return (
    <div className="dg-wc__sheet" data-testid="wc-health-sheet">
      <h3 className="dg-wc__sheet-title">The feeds behind these numbers</h3>
      {captureState === "unread" ? (
        <p className="dg-wc__sheet-line">
          The feed check didn't answer this morning, so we can't show you how the daily
          captures are doing.
        </p>
      ) : captureState === "loading" ? (
        <p className="dg-wc__sheet-line">Checking the daily feeds…</p>
      ) : (
        <ul className="dg-wc__feed-list">
          {feeds.kind === "read" &&
            feeds.rows.map((row) => (
              <li key={row.id} className="dg-wc__feed-row" data-feed-ok={row.ok}>
                <span className="dg-wc__feed-dot" aria-hidden="true" />
                <span className="dg-wc__feed-name">{row.name}</span>
                <span className="dg-wc__feed-detail">
                  {row.ran}
                  {row.note !== null ? ` ${row.note}` : ""}
                </span>
              </li>
            ))}
        </ul>
      )}
      {/* PANEL FIX: an endpoint that did not answer is not evidence that the
          model files are fine — the same standard the capture half is already
          held to. A sheet that says nothing here looks complete while a whole
          trust axis is quietly missing from it. */}
      {provenanceState === "unread" && (
        <p className="dg-wc__sheet-line">
          The model-file check didn't answer this morning, so we can't tell you whether
          our projections are being served from the files we expect.
        </p>
      )}
      {provenanceState === "loading" && (
        <p className="dg-wc__sheet-line">Checking the model files…</p>
      )}
      {provenance !== null && (
        // Three states, not two. `_overall_status` (system_model_provenance.py:62-75)
        // separates "flagged but still serving" from "not cleared to serve at
        // all", and collapsing those into one not-ok sentence would understate
        // the second and overstate the first. The registry version number is a
        // receipt, not prose, so it rides the title layer like every other one.
        <p
          className="dg-wc__sheet-line"
          title={`registry_version=${provenance.registryVersion}`}
        >
          {provenance.status === "ok"
            ? "Every model file our projections are served from is the one we expect."
            : provenance.status === "blocked"
              ? "A model file our projections need is not cleared to serve — the health panel in the shell names which."
              : "At least one model file is flagged as different from what we expect, though it is still being served — the health panel in the shell names which."}
        </p>
      )}
      <h3 className="dg-wc__sheet-title">Where this report comes from</h3>
      <p className="dg-wc__sheet-line" title={data.generated_at}>
        Built {formatCaptureTimestamp(data.generated_at)}.
      </p>
      {marketWindow?.from_date && marketWindow?.to_date && (
        <p className="dg-wc__sheet-line">
          Market prices compared {marketWindow.from_date} against {marketWindow.to_date}
          .
        </p>
      )}
      {/* A REQUIRED schema field (zod.gen.ts zWhatChangedMarketSection), so it
          is always available — and it used to hang off the capture-window
          conditional, which meant the sheet lost the source entirely on any
          morning the window carried no dates. */}
      {market.market_source && (
        <p className="dg-wc__sheet-line" data-receipt>
          Market source: {market.market_source}.
        </p>
      )}
      {modelWindow?.from_date && modelWindow?.to_date && (
        <p className="dg-wc__sheet-line">
          Model window {modelWindow.from_date} against {modelWindow.to_date}.
        </p>
      )}
      {basisTitle && (
        <p className="dg-wc__sheet-line" title={basisTitle}>
          {model.vintage_changed
            ? "Projection basis changed within this window."
            : "Projection basis consistent across this window."}
        </p>
      )}
      <p className="dg-wc__sheet-line" data-receipt data-testid="wc-provenance">
        Feed status: {data.overall_status} · market {market.status} · model{" "}
        {model.status}
        {rawReasons.length > 0
          ? ` · producer reasons, verbatim: ${rawReasons.join(", ")}`
          : ""}
      </p>
    </div>
  );
}

// ── "worth a look" ───────────────────────────────────────────────────────────

/**
 * David's ruling green-lights this block: "call a spade a spade, and I've given
 * it the green light."
 *
 * Two guards keep the spade honest. Every clause on a card is assembled in
 * `morningRead.ts` from a field on this page — nothing here is a judgement the
 * component made. And the METHOD line is always on screen: the rule that put a
 * card here, or left the block empty, is stated rather than left for the reader
 * to reverse-engineer. That line is not a caveat and does not soften anything;
 * it is the difference between a recommendation and an oracle.
 */
function WorthALookBlock({
  cards,
  missing,
}: {
  cards: Recommendation[];
  missing: string[];
}) {
  return (
    <section
      className="dg-wc__worth"
      data-testid="wc-worth-a-look"
      aria-label="Worth a look"
    >
      <h3 className="dg-wc__region-title">Worth a look</h3>
      {cards.length === 0 && missing.length === 0 && (
        <p className="dg-wc__quiet">Nothing worth acting on today.</p>
      )}
      {cards.map((card) => (
        <article
          key={card.id}
          className="dg-wc__rec"
          data-testid="wc-recommendation"
          data-rec-id={card.id}
        >
          <p className="dg-wc__rec-verdict">{card.headline}</p>
          {card.reasons.map((reason) => (
            <p key={reason} className="dg-wc__rec-reason">
              {reason}
            </p>
          ))}
          {card.action.kind === "surface" ? (
            // A real link, not a scripted handler: it survives a bare mount,
            // it middle-clicks, and the shell reads `?surface=` on boot
            // (useUrlSurfaceState) so it lands exactly where it says.
            <a className="dg-wc__rec-action" href={`?surface=${card.action.slug}`}>
              {card.action.label} →
            </a>
          ) : (
            <PlayerNameButton
              sleeperId={card.action.sleeperId}
              name={card.action.name}
              context={card.action.context}
              className="dg-wc__rec-action"
            >
              {`${card.action.label} →`}
            </PlayerNameButton>
          )}
        </article>
      ))}
      {missing.map((line) => (
        <p key={line} className="dg-wc__quiet" data-testid="wc-missing-input">
          {line}
        </p>
      ))}
      <p className="dg-wc__method">{RECOMMENDATION_METHOD}</p>
    </section>
  );
}

// ── where you stand ──────────────────────────────────────────────────────────

/**
 * The prose that replaces "Current roster context".
 *
 * The five section stamps that used to sit here are gone with the counts they
 * qualified. What survives is the rule underneath, and it is now stricter than
 * it was: a section's honesty notice renders beside THE CLAIM IT QUALIFIES. The
 * posture section's notice sits under the posture sentence; the drop-pressure
 * section's sits under the roster count, which is the only other thing this
 * block says. A notice for a section whose content is no longer on the page
 * would be qualifying nothing.
 */
function WhereYouStandBlock({
  standing,
  postureSection,
  dropSection,
}: {
  standing: ReturnType<typeof whereYouStand>;
  postureSection: WhatChangedResponse["structural_context"]["sections"]["team_posture"];
  dropSection: WhatChangedResponse["structural_context"]["sections"]["drop_pressure"];
}) {
  if (standing.posture === null && standing.roster === null) {
    return null;
  }
  const postureNotice = sectionNotice(postureSection);
  const dropNotice = sectionNotice(dropSection);
  return (
    <section
      className="dg-wc__region"
      data-testid="wc-where-you-stand"
      aria-label="Where you stand"
    >
      <h3 className="dg-wc__region-title">Where you stand</h3>
      {standing.teamName !== null && (
        <p className="dg-wc__stand-team" data-user-text>
          {standing.teamName}
        </p>
      )}
      {standing.posture !== null && (
        <p className="dg-wc__stand-line">{standing.posture}</p>
      )}
      {postureNotice && (
        <p
          className="dg-wc__baseline-meta"
          data-testid="wc-section-notice"
          title={postureSection.staleness_caveat?.basis ?? undefined}
        >
          {postureNotice}
        </p>
      )}
      {standing.roster !== null && (
        <p className="dg-wc__stand-line">{standing.roster}</p>
      )}
      {dropNotice && (
        <p
          className="dg-wc__baseline-meta"
          data-testid="wc-section-notice"
          title={dropSection.staleness_caveat?.basis ?? undefined}
        >
          {dropNotice}
        </p>
      )}
      <a className="dg-wc__rec-action" href="?surface=roster-audit">
        See the full roster →
      </a>
    </section>
  );
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
  // DG-113 adds the third, found rendering on the LIVE payload: two model runs
  // landed on 2026-08-30, so the producer refuses to emit a comparison rather
  // than fabricate one (daily_diff.py:255-271). That is the same species as the
  // two above — a refusal, not a fault — and the dictionary sentence for it
  // already says so in its own words ("we will not claim what moved
  // overnight"). Calling it "came back degraded", as the page did this morning,
  // is the cry-wolf pattern spending the word on a producer behaving correctly.
  "model_multi_vintage_ambiguous",
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
  /** Whether this lane actually has rows under the notice. */
  hasRows: boolean,
): string | null {
  if (reasons.length === 0) return null;
  // DG-113: the dictionary sentence is now its OWN sentence, not a clause
  // spliced between em-dashes with its full stop shaved off. Read on the live
  // payload the splice produced "…came back degraded — Two different model runs
  // landed on the same day, so we will not claim what moved overnight — so
  // treat the model numbers below as provisional": a capitalised sentence
  // wedged mid-clause, then a second "so", then an instruction. The dictionary
  // writes sentences; let them be sentences.
  const said = reasons.map((token) => endSentence(describeToken(token))).join(" ");
  const opening = reasons.every((token) => NOT_A_FAULT.has(token))
    ? `Heads up: we couldn't compare ${lane === "market" ? "market prices" : "our projections"} against an earlier day.`
    : `Heads up: ${lane === "market" ? "the market side" : "the model side"} came back degraded.`;
  // …and the closing instruction renders ONLY when there is something below to
  // apply it to. On today's payload the model lane has no rows at all, so
  // "treat the model numbers below as provisional" was pointing at nothing.
  if (!hasRows) {
    return `${opening} ${said}`;
  }
  const closing = reasons.every((token) => NOT_A_FAULT.has(token))
    ? `So nothing below is a change — it is just where things stand.`
    : `So treat ${lane === "market" ? "the prices" : "the model numbers"} below as provisional.`;
  return `${opening} ${said} ${closing}`;
}

function MarketRegion({ market }: { market: WhatChangedMarketSection }) {
  const rosterDeltas = market.roster_deltas ?? [];
  // DG-113 §2.5: his own players come OUT of the league list. Both lists are
  // slices of one `deltas_by_id` map, so an unfiltered league table repeats his
  // roster rows with identical numbers — Jaxson Dart was #1 of both.
  const league = leagueMovers(market);
  const when = windowPhrase(market.comparison_window as ComparisonWindow | null);

  // The market lane's trouble arrives on either axis, and only one of them is an
  // `aborted_reason` — see `laneNotice`. `status` is the closed set
  // {ok, unavailable, insufficient_history} (daily_diff.py:100-118, :150-165),
  // so anything but "ok" means the day-over-day comparison did not happen.
  const marketReasons = market.aborted_reason
    ? [market.aborted_reason]
    : market.status !== "ok"
      ? [market.status]
      : [];
  const notice = laneNotice("market", marketReasons, rosterDeltas.length > 0);
  // No comparison ran → an empty row list means "we did not look", never "we
  // looked and nothing moved". The empty-state copy has to stop making the
  // second claim, or the honesty sentence above is arguing with the page.
  const compared = marketReasons.length === 0;
  // PANEL FIX — THE BLOCKER. `market.entered ?? []` manufactured a zero the
  // producer declined to supply. BOTH of daily_diff's failure returns carry no
  // `entered`/`exited` keys at all — `missing_sleeper_snapshot`
  // (daily_diff.py:102-107) and `insufficient_history` (:112-117) return only
  // status/decision_supported/comparison_window/market_source — so on those
  // mornings the page said "we couldn't compare" at the top of this region and
  // "New to the priced pool: 0 · Dropped out: 0 / Nobody new carried a price
  // today" four inches below it. A producer that declines to answer, rendered
  // as a confident negative, is the phase-2A failure class exactly.
  //
  // The counts render only when the comparison ran AND both arrays are actually
  // present. A null array on an otherwise-ok lane is the same absence wearing a
  // different hat, so it takes the same branch.
  const pool =
    compared && market.entered != null && market.exited != null
      ? { entered: market.entered, exited: market.exited }
      : null;

  // The cards lead with the biggest MOVES; the tape carries every remaining
  // row, flat ones included, in the producer's own order. The rank numeral is
  // the row's position in `roster_deltas` — so the tape resumes at 4 instead of
  // restarting at 1 on the fourth-biggest mover, which is what it did before.
  const cardRows = rosterDeltas.filter((row) => row.value_delta !== 0).slice(0, 3);
  const onACard = new Set(cardRows);
  const tapeRows = rosterDeltas.filter((row) => !onACard.has(row));
  const tapeRanks = tapeRows.map((row) => rosterDeltas.indexOf(row) + 1);
  // The trend note explains BLANK sparklines. It is only true when a blank one
  // is on screen: once a player's series has points, `LaneSeriesSlot` draws a
  // real line and the note would be contradicting the picture beside it.
  const anyPendingSeries = [...rosterDeltas, ...league.rows].some(
    (row) =>
      usableSeriesPoints((row as { market_series?: unknown }).market_series) === null,
  );

  return (
    <>
      <section
        className="dg-wc__region"
        data-testid="wc-your-roster"
        aria-label="What moved on your roster"
      >
        <h3 className="dg-wc__region-title">What moved</h3>
        <p className="dg-wc__overlay-note">
          Market prices — what the dynasty market is paying, kept separate from our own
          projections.
        </p>
        {/* DG-111: was a "Market feed caveats" block printing the raw producer
            token. One sentence now; the token itself is preserved verbatim in
            the title attribute and in the health sheet, so nothing is lost. */}
        {notice && (
          <p
            className="dg-wc__overlay-note"
            data-testid="wc-market-degraded"
            title={marketReasons.join(", ")}
          >
            {notice}
          </p>
        )}

        {rosterDeltas.length === 0 ? (
          <p className="dg-wc__quiet">
            {/* PANEL FIX: "held steady" was the section contradicting the
                verdict two inches above it, and the section was the false half.
                An empty `roster_deltas` on a SUCCESSFUL comparison means the
                market priced none of his players on both dates
                (daily_diff.py:143-147) — a coverage fact, not a movement fact.
                `movement()` already refuses to call it movement; this string is
                the one place the old reading survived. */}
            {compared
              ? "The market didn't price any of your players on both of the last two days, so there is nothing of yours to compare."
              : "No day-over-day comparison for your roster on this tape."}
          </p>
        ) : (
          <>
            {/* DG-113 §2.4: the biggest moves get room to be read; the rest
                stay on the tape below. Both are the SAME rows in the same
                producer order, so the cards are a lead, never a second list.

                PANEL FIX: the cards are sliced off MOVERS, not off
                `roster_deltas`. That list keeps every roster player priced on
                both days EVEN IF FLAT (daily_diff.py:143-147); only `movers`
                filters `value_delta != 0`. Slicing the unfiltered list put
                players who did not move into three large cards under a heading
                reading "What moved", directly below a verdict saying "1 of them
                moved" — the same list/mover conflation SR-16 fixed on the hero
                this replaced. The tape then carries everything the cards did
                not, so no row is dropped and none is shown twice. */}
            <MoverCards rows={cardRows} when={when} />
            {tapeRows.length > 0 && <MarketRows rows={tapeRows} ranks={tapeRanks} />}
          </>
        )}

        {/* DG-111: this one line replaces the rail's "Movement history — Series
            pending" panel. Same fact, said once, next to the blank trend slots
            it explains — and ONLY when there is a blank slot on screen for it
            to explain, or it would contradict the first real sparkline drawn. */}
        {anyPendingSeries && (
          <p className="dg-wc__overlay-note" data-testid="wc-trend-note">
            Trend lines fill in as daily prices accrue — one capture a day — so they
            stay blank until enough days are on the books.
          </p>
        )}
      </section>

      <section
        className="dg-wc__region"
        data-testid="wc-around-the-league"
        aria-label="Around the league"
      >
        <h3 className="dg-wc__region-title">Around the league</h3>
        {league.rows.length === 0 ? (
          <p className="dg-wc__quiet">
            {compared
              ? league.excluded > 0
                ? "Every one of the day's biggest movers is already on your roster, above."
                : // `when`, not a hardcoded "overnight". The word is a claim
                  // about elapsed time and is only true when the two compared
                  // captures are adjacent days; `windowPhrase` is the one place
                  // that is decided, and this string was the last literal.
                  `No player movement on this tape — market values held steady ${when}.`
              : "No day-over-day comparison league-wide on this tape."}
          </p>
        ) : (
          <>
            <MarketRows rows={league.rows} ranks={league.ranks} />
            {/* SR-16: honest truncation — the league-wide total stays on the
                surface and never pretends to be about his roster, and a nullish
                total is never invented. DG-113 adds the second half of the
                honesty: rows removed by the roster filter are ACCOUNTED FOR
                rather than silently shrinking the count. */}
            <p className="dg-wc__overlay-note">
              {market.total_movers_count != null
                ? `Showing ${num(league.rows.length)} of ${num(market.total_movers_count)} movers league-wide`
                : `Showing ${num(league.rows.length)} movers`}
              {league.excluded > 0
                ? ` — ${num(league.excluded)} more ${league.excluded === 1 ? "is" : "are"} yours, and ${league.excluded === 1 ? "is" : "are"} up in what moved.`
                : "."}
            </p>
          </>
        )}

        {/* DG-113 §2.5: the two chip walls become one line you can open. Who
            entered and left the priced pool is real, and it is not what the
            morning is about. */}
        {pool === null ? (
          <p className="dg-wc__quiet">
            We couldn't compare the priced pool against an earlier day, so we can't tell
            you who joined it or dropped out of it.
          </p>
        ) : (
          <details className="dg-wc__pool">
            <summary className="dg-wc__pool-summary">
              New to the priced pool: {num(pool.entered.length)} · Dropped out:{" "}
              {num(pool.exited.length)}
            </summary>
            <h4 className="dg-wc__group">New to the pool</h4>
            <UniverseChipList
              items={pool.entered}
              emptyLabel="Nobody new carried a price today."
            />
            <h4 className="dg-wc__group">Dropped out</h4>
            <UniverseChipList
              items={pool.exited}
              emptyLabel="Nobody dropped out of the priced pool today."
            />
          </details>
        )}
      </section>
    </>
  );
}

/**
 * The day's three biggest moves, with room to be read.
 *
 * The delta keeps the same `DeltaCell` the tape rows use, so the printed sign
 * and the direction hue come off one function and cannot tell different
 * stories — the card is a bigger frame around the same governed cell, not a
 * second rendering of the same number with its own rules.
 */
function MoverCards({ rows, when }: { rows: WhatChangedMarketDelta[]; when: string }) {
  return (
    <ul className="dg-wc__cards" data-testid="wc-mover-cards">
      {rows.map((row, index) => {
        const name = row.player_name ?? humanAssetKey(row.player_key);
        return (
          <li key={row.sleeper_id ?? index} className="dg-wc__card">
            <PlayerNameButton
              sleeperId={row.sleeper_id}
              name={name}
              context={[row.position, row.team_id].filter(Boolean).join(" ")}
              className="dg-wc__player-open"
            >
              <PlayerIdentity
                name={name}
                team={row.team_id ?? ""}
                position={row.position ?? ""}
                {...headshotProps(row.sleeper_id)}
                teamId={row.team_id ?? undefined}
                teamAccent={teamAccentFor(row.team_id)}
              />
            </PlayerNameButton>
            <div className="dg-wc__card-figures">
              {row.current_value != null && (
                <span className="dg-wc__card-value">{num(row.current_value)}</span>
              )}
              <DeltaCell
                label={`Market price change ${when}`}
                value={row.value_delta}
                emphasis="row-focal"
                labelHidden
              />
            </div>
            <span className="dg-wc__lane" data-lane="market">
              <LaneSeriesSlot
                series={(row as { market_series?: unknown }).market_series}
                label={`${name} market series`}
              />
            </span>
          </li>
        );
      })}
    </ul>
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

/**
 * The tape.
 *
 * PANEL FIX — `ranks`. The numeral used to be `i + 1` over whatever slice the
 * caller handed in, which stopped being the row's rank the moment DG-113 put
 * three rows on cards above it and pulled his own players out of the league
 * list. The caller now says what each numeral means, because only the caller
 * knows: for the roster tape it is the position in `roster_deltas`, and for the
 * league it is the position in the producer's unfiltered `top_movers`. Both are
 * the number the row actually holds in the list it came from.
 */
function MarketRows({
  rows,
  ranks,
}: {
  rows: WhatChangedMarketDelta[];
  ranks?: number[];
}) {
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
            rank={ranks?.[i] ?? i + 1}
            sleeperId={r.sleeper_id}
            name={r.player_name ?? humanAssetKey(r.player_key)}
            position={r.position ?? ""}
            teamId={(r as { team_id?: string | null }).team_id}
            // PANEL FIX: `num()`, not `String()`. The mover cards directly above
            // print the same quantity through `num()`, so the screen carried
            // "5,204" on a card and "3873" on the row beneath it — one number,
            // two spellings, stacked with nothing in between.
            currentValue={
              (r as { current_value?: number | null }).current_value != null
                ? num((r as { current_value: number }).current_value)
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
  const notice = laneNotice("model", caveats, deltas.length > 0);
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
