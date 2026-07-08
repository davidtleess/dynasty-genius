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
import { formatCaptureTimestamp } from "../lib/copy";
import { useEndpointResource } from "../lib/useEndpointResource";
import { CaveatBlock } from "../ui/CaveatBlock";
import { ChartFrame } from "../ui/ChartFrame";
import { DailyTape as UiDailyTape } from "../ui/DailyTape";
import { DisclosureLine } from "../ui/DisclosureLine";
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

// Read-only Daily What-Changed surface, restarted on the governed primitive
// library (H2 reset Task 5). It reports the day-over-day market and model
// DELTAS — what changed since the prior snapshot — and issues no verdict.
// Market (price-discovery overlay) and model (output changes) stay in
// structurally isolated regions so a market price swing never reads as a model
// signal. The desk reads top-down: one dated masthead with the tape, then the
// change feed, with feed diagnostics and receipts in a subordinate right rail.
export function DailyWhatChanged() {
  const [state, setState] = useState<State>({ status: "loading" });

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
  return <ReadyView data={state.data} />;
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
    // biome-ignore lint/a11y/useAriaPropsSupportedByRole: aria-label supplies the hidden column label to assistive tech on this non-semantic delta-cell wrapper; the label is otherwise carried once by the column header
    <span
      className="dg-wc__delta-cell"
      aria-label={labelHidden ? label : undefined}
      title={text === NEUTRAL_DASH ? EXACT_ZERO_NOTE : undefined}
    >
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
  return (
    <li data-asset-row data-row-density="32px" className="dg-wc__player-row">
      {rank !== undefined && <span className="dg-wc__rank">{rank}</span>}
      <PlayerIdentity
        name={name}
        team={teamId ?? ""}
        position={position}
        {...headshotProps(sleeperId)}
        teamId={teamId ?? undefined}
        teamAccent={teamAccentFor(teamId)}
      />
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

function ReadyView({ data }: { data: WhatChangedResponse }) {
  const daily = data.daily_diff;
  const marketWindow = (daily.market.comparison_window ?? null) as {
    from_date?: string | null;
    to_date?: string | null;
  } | null;
  const moveCount =
    (daily.market.top_movers?.length ?? 0) +
    (daily.market.roster_deltas?.length ?? 0) +
    (daily.model.deltas?.length ?? 0);

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
  const quietDay = moveCount === 0;

  return (
    <section
      className={`dg-wc dg-motion-daily-open${isStale ? " dg-wc--stale" : ""}`}
      aria-label="Daily What-Changed"
    >
      <header className="dg-wc__desk-header">
        <div className="dg-wc__masthead">
          <h2 className="dg-wc__title">{deskDate(data.generated_at)}</h2>
          <ValueHero
            label="Moves on the tape"
            value={String(moveCount)}
            basis="market and model changes since the prior snapshot"
          />
        </div>
        {isStale && (
          <p className="dg-wc__stale-badge">
            Stale data caveat —{" "}
            {hours === null
              ? "the capture time could not be read"
              : `the capture is ${hours.toFixed(1)} hours old`}
            . The tape below reflects the last verified capture, not this morning.
          </p>
        )}
        <p className="dg-wc__disclaimer">
          A daily delta surface (what changed since the prior snapshot); no verdict, no
          nominated move.
        </p>
        <DisclosureLine />
      </header>
      <div className="dg-wc__layout">
        {/* Model movement FIRST (spec v3 §2, Gemini nudge finding): the model
            is the rational anchor; market-first would anchor the morning read
            on crowd noise before the model's evaluation. */}
        <div className="dg-wc__feed" data-stale={isStale ? "true" : undefined}>
          {quietDay && (
            <div className="dg-wc__quiet-day">
              <p className="dg-wc__quiet">
                No valuation deltas observed since the last capture (checked{" "}
                {deskDate(data.generated_at)}). The roster holds its baseline below.
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

// Subordinate right rail: the report's own operational context. Feed
// diagnostics (this surface's feeds, not whole-app system health — that axis
// stays in the shell) and provenance receipts, plus the honest pending slot
// where movement history will accrue.
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

  return (
    <aside className="dg-wc__rail" aria-label="Report context">
      <DailyTape />
      <section className="dg-wc__diagnostics" aria-label="Feed diagnostics">
        <h3 className="dg-wc__rail-title">Feed diagnostics</h3>
        <p className="dg-wc__rail-line">Feed status: {data.overall_status}</p>
        <p className="dg-wc__rail-line">Market feed: {market.status}</p>
        <p className="dg-wc__rail-line">Model feed: {model.status}</p>
        {market.market_source && (
          <p className="dg-wc__rail-line">Market source: {market.market_source}</p>
        )}
      </section>
      <section className="dg-wc__receipts" aria-label="Report receipts">
        <h3 className="dg-wc__rail-title">Receipts</h3>
        <p className="dg-wc__rail-line" title={data.generated_at}>
          Generated: {formatCaptureTimestamp(data.generated_at)}
        </p>
        {marketWindow?.from_date && marketWindow?.to_date && (
          <p className="dg-wc__rail-line">
            Captured {marketWindow.from_date} vs {marketWindow.to_date}
          </p>
        )}
        {modelWindow?.from_date && modelWindow?.to_date && (
          <p className="dg-wc__rail-line">
            Model window {modelWindow.from_date} vs {modelWindow.to_date}
          </p>
        )}
        {basisTitle && (
          <p className="dg-wc__rail-line" title={basisTitle}>
            {model.vintage_changed
              ? "Projection basis changed within this window"
              : "Projection basis consistent across this window"}
          </p>
        )}
      </section>
      <ChartFrame
        title="Movement history"
        summary="History accrues one verified capture per day; the line begins once enough days are on the books."
      >
        <SeriesSlot status="pending" label="Daily movement history" />
      </ChartFrame>
    </aside>
  );
}

function humanAssetKey(key: string): string {
  return key.startsWith("sleeper:") ? key.slice("sleeper:".length) : key;
}

function MarketRegion({ market }: { market: WhatChangedMarketSection }) {
  const topMovers = market.top_movers ?? [];
  const rosterDeltas = market.roster_deltas ?? [];
  // Voice: strip the raw backend key prefix from entered/exited ids — full
  // name resolution for these rows rides the identity slice (residual debt,
  // recorded in the Increment-1 delta doc).
  const entered = market.entered ?? [];
  const exited = market.exited ?? [];

  return (
    <section className="dg-wc__region" aria-label="Market price-discovery overlay">
      <h3 className="dg-wc__region-title">Market movement</h3>
      <p className="dg-wc__overlay-note">
        Price-discovery deltas — market overlay only, isolated from model output.
      </p>
      {market.aborted_reason && (
        <CaveatBlock
          tone="neutral"
          title="Market feed caveats"
          items={[market.aborted_reason]}
        />
      )}

      <h4 className="dg-wc__group">Your roster</h4>
      {rosterDeltas.length === 0 ? (
        <p className="dg-wc__quiet">
          Your roster's market values held steady — no movement on this tape.
        </p>
      ) : (
        <MarketRows rows={rosterDeltas} />
      )}

      <h4 className="dg-wc__group">Around the league</h4>
      {topMovers.length === 0 ? (
        <p className="dg-wc__quiet">
          No player movement on this tape — market values held steady overnight.
        </p>
      ) : (
        <MarketRows rows={topMovers} />
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
      {items.map((e, i) => (
        <li key={e.sleeper_id ?? i} className="dg-wc__universe-chip">
          <PlayerIdentity
            name={e.player_name ?? humanAssetKey(e.player_key)}
            team={e.team_id ?? ""}
            position={e.position ?? ""}
            {...headshotProps(e.sleeper_id)}
            teamId={e.team_id ?? undefined}
          />
        </li>
      ))}
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
            name={r.player_name ?? r.player_key}
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
  const caveats = [
    modelWindow?.status ?? null,
    model.feature_freshness?.aborted_reason ?? null,
    model.pvo_staleness?.aborted_reason ?? null,
  ].filter((item): item is string => item != null);

  return (
    <section className="dg-wc__region" aria-label="Model output changes">
      <h3 className="dg-wc__region-title">Model output changes</h3>
      {caveats.length > 0 && (
        <CaveatBlock tone="neutral" title="Model feed caveats" items={caveats} />
      )}
      {deltas.length === 0 ? (
        <p className="dg-wc__quiet">
          Projections held steady — no player movement on this tape.
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
          name={r.player_name ?? r.player_key}
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
          <DeltaCell label="Above replacement" value={r.xvar_delta} />
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
  return (
    <ul className="dg-wc__rows">
      {rows.map((r) => (
        <li
          key={r.sleeper_id}
          data-asset-row
          data-row-density="32px"
          className="dg-wc__player-row"
        >
          <PlayerIdentity
            name={r.player_name ?? r.sleeper_id}
            team={r.team_id ?? ""}
            position={r.position ?? ""}
            {...headshotProps(r.sleeper_id)}
            teamId={r.team_id ?? undefined}
          />
          <span data-lane="model" className="dg-wc__lane dg-wc__lane--flat">
            {NEUTRAL_DASH}
          </span>
          <span data-lane="market" className="dg-wc__lane dg-wc__lane--flat">
            {NEUTRAL_DASH}
          </span>
        </li>
      ))}
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
            Posture: {s.team_posture.david_posture}
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
            {type}: {count}
          </p>
        ))}
        <CaveatBlock
          tone="neutral"
          title="Divergence caveat"
          items={[
            "Divergence card counts are an unvalidated descriptive overlay (Gate-4 deferred); a tally of card types, not a proven edge.",
          ]}
        />
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

// Per-section shell: accessible-named region + status honesty stamp + the
// standard disclosure + caveats. The status label and value stay in separate
// nodes so a section's "Status: <value>" never collapses into one text node
// (which would let a section status collide with the top-level status).
function BaselineSection({
  label,
  sec,
  children,
}: {
  label: string;
  sec: WhatChangedStructuralSection;
  children: ReactNode;
}) {
  const caveats = [
    sec.staleness_caveat
      ? `${sec.staleness_caveat.basis} — ${
          sec.staleness_caveat.is_stale ? "stale" : "fresh"
        } (age ${sec.staleness_caveat.age_hours}h)`
      : null,
    sec.aborted_reason ?? null,
  ].filter((item): item is string => item != null);

  return (
    <section className="dg-wc__baseline-section" aria-label={label}>
      <h4 className="dg-wc__group">{label}</h4>
      <p className="dg-wc__baseline-meta">
        <span className="dg-wc__meta-label">Status:</span>{" "}
        <span className="dg-wc__meta-value">{sec.status}</span>
      </p>
      <DisclosureLine />
      {caveats.length > 0 && (
        <CaveatBlock tone="neutral" title="Context caveats" items={caveats} />
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
        <p className="dg-wc__baseline-line" title={`lineup_xvar=${v.lineup_xvar}`}>
          Starting lineup value: {v.lineup_xvar}
        </p>
      )}
      {v.starter_weighted_xvar != null && (
        <p
          className="dg-wc__baseline-line"
          title={`starter_weighted_xvar=${v.starter_weighted_xvar}`}
        >
          Weekly lineup strength: {v.starter_weighted_xvar}
        </p>
      )}
      {v.top_n_xvar != null && (
        <p className="dg-wc__baseline-line" title={`top_n_xvar=${v.top_n_xvar}`}>
          Top-asset core value: {v.top_n_xvar}
        </p>
      )}
      {v.total_xvar_capped != null && (
        <p
          className="dg-wc__baseline-line"
          title={`total_xvar_capped=${v.total_xvar_capped}`}
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
