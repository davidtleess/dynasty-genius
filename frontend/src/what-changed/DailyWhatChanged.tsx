import { type ReactNode, useEffect, useState } from "react";

import type {
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

function DeltaCell({ label, value }: { label: string; value: number }) {
  const text = formatZeroDelta(value);
  return (
    <span
      className="dg-wc__delta-cell"
      title={text === NEUTRAL_DASH ? EXACT_ZERO_NOTE : undefined}
    >
      <MetricCell label={label} value={text} />
    </span>
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

  return (
    <section className="dg-wc dg-motion-daily-open" aria-label="Daily What-Changed">
      <header className="dg-wc__desk-header">
        <div className="dg-wc__masthead">
          <h2 className="dg-wc__title">{deskDate(data.generated_at)}</h2>
          <ValueHero
            label="Moves on the tape"
            value={String(moveCount)}
            basis="market and model changes since the prior snapshot"
          />
        </div>
        <DailyTape />
        <p className="dg-wc__disclaimer">
          A daily delta surface (what changed since the prior snapshot); no verdict, no
          nominated move.
        </p>
        <DisclosureLine />
      </header>
      <div className="dg-wc__layout">
        <div className="dg-wc__feed">
          <MarketRegion market={daily.market} />
          <ModelRegion model={daily.model} />
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

function MarketRegion({ market }: { market: WhatChangedMarketSection }) {
  const topMovers = market.top_movers ?? [];
  const rosterDeltas = market.roster_deltas ?? [];
  const entered = market.entered ?? [];
  const exited = market.exited ?? [];

  return (
    <section className="dg-wc__region" aria-label="Market price-discovery overlay">
      <h3 className="dg-wc__region-title">Market price-discovery overlay</h3>
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

      <h4 className="dg-wc__group">Top movers</h4>
      {topMovers.length === 0 ? (
        <p className="dg-wc__quiet">
          No player movement on this tape — market values held steady overnight.
        </p>
      ) : (
        <MarketRows rows={topMovers} />
      )}

      <h4 className="dg-wc__group">Roster market deltas</h4>
      {rosterDeltas.length === 0 ? (
        <p className="dg-wc__quiet">
          Your roster's market values held steady — no movement on this tape.
        </p>
      ) : (
        <MarketRows rows={rosterDeltas} />
      )}

      <h4 className="dg-wc__group">Entered</h4>
      {entered.length === 0 ? (
        <p className="dg-wc__quiet">No entered assets.</p>
      ) : (
        <ul className="dg-wc__list">
          {entered.map((e, i) => (
            <li key={e.sleeper_id ?? i}>{e.player_key}</li>
          ))}
        </ul>
      )}

      <h4 className="dg-wc__group">Exited</h4>
      {exited.length === 0 ? (
        <p className="dg-wc__quiet">No exited assets.</p>
      ) : (
        <ul className="dg-wc__list">
          {exited.map((e, i) => (
            <li key={e.sleeper_id ?? i}>{e.player_key}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

// Feed rows are identity-first (benchmark parity: data feels human): the
// player, the signed delta, and an honest pending slot where that player's
// series will land once enough daily captures accrue. No table semantics —
// each row is one player's line on the tape.
function MarketRows({ rows }: { rows: WhatChangedMarketDelta[] }) {
  return (
    <ul className="dg-wc__rows">
      {rows.map((r, i) => (
        <li key={r.sleeper_id ?? i} className="dg-wc__player-row">
          <PlayerIdentity
            name={r.player_name ?? r.player_key}
            team=""
            position={r.position ?? ""}
            imageStatus="missing"
          />
          <DeltaCell label="Market value" value={r.value_delta} />
          <SeriesSlot
            status="pending"
            label={`${r.player_name ?? r.player_key} market value history`}
          />
        </li>
      ))}
    </ul>
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
        <li key={r.sleeper_id ?? i} className="dg-wc__player-row">
          <PlayerIdentity
            name={r.player_name ?? r.player_key}
            team=""
            position={r.position ?? ""}
            imageStatus="missing"
          />
          <DeltaCell label="Model value" value={r.dynasty_value_score_delta} />
          <DeltaCell label="Percentile" value={r.dvs_pct_delta} />
          <DeltaCell label="Above replacement" value={r.xvar_delta} />
          <SeriesSlot
            status="pending"
            label={`${r.player_name ?? r.player_key} model value history`}
          />
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
