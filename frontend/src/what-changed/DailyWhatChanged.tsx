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
import { DailyTape as UiDailyTape } from "../ui/DailyTape";
import "./DailyWhatChanged.css";

type State =
  | { status: "loading" }
  | { status: "ready"; data: WhatChangedResponse }
  | { status: "unavailable" }
  | { status: "parse-error" };

// Read-only Daily What-Changed surface. It reports the day-over-day market and model
// DELTAS — what changed since the prior snapshot — and issues no verdict. Market
// (price-discovery overlay) and model (output changes) are kept in structurally
// isolated regions so a market price swing never reads as a model signal. Slice 2
// appends a SUBORDINATE structural current-state baseline (summaries/counts only) to
// ground the deltas ("compared to what?") without duplicating League Pulse / Roster
// Audit or nominating any target (see StructuralBaseline).
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

// Signed and neutral: the sign encodes direction, so there is no arrow, color, or
// buy/sell word to smuggle in a verdict. Raw value (not rounded) — the backend owns
// precision. -0 keeps its sign rather than reading as +0.
function fmtSigned(value: number): string {
  if (Object.is(value, -0)) {
    return "-0";
  }
  return value >= 0 ? `+${value}` : `${value}`;
}

function ReadyView({ data }: { data: WhatChangedResponse }) {
  const daily = data.daily_diff;
  const comparisonWindow = (data.daily_diff.market.comparison_window ?? null) as {
    from_date?: string | null;
    to_date?: string | null;
  } | null;

  return (
    <section className="dg-wc" aria-label="Daily What-Changed">
      <h2 className="dg-wc__title">Daily Change Log</h2>
      <DailyTape />
      <p className="dg-wc__disclaimer">Descriptive only — not decision-grade.</p>
      <p className="dg-wc__disclaimer">
        A daily delta surface (what changed since the prior snapshot); no verdict, no
        nominated move.
      </p>
      <p className="dg-wc__status">Status: {data.overall_status}</p>
      <p className="dg-wc__generated" title={data.generated_at}>
        Generated: {formatCaptureTimestamp(data.generated_at)}
      </p>
      {comparisonWindow?.from_date && comparisonWindow?.to_date && (
        <p className="dg-wc__window">
          Captured {comparisonWindow.from_date} vs {comparisonWindow.to_date}
        </p>
      )}
      <MarketRegion market={daily.market} />
      <ModelRegion model={daily.model} />
      <StructuralBaseline ctx={data.structural_context} />
    </section>
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
        <p className="dg-wc__caveat">{market.aborted_reason}</p>
      )}

      <h4 className="dg-wc__group">Top movers</h4>
      {topMovers.length === 0 ? (
        <p className="dg-wc__empty">No market top movers.</p>
      ) : (
        <MarketDeltaTable rows={topMovers} />
      )}

      <h4 className="dg-wc__group">Roster market deltas</h4>
      {rosterDeltas.length === 0 ? (
        <p className="dg-wc__empty">No roster market deltas.</p>
      ) : (
        <MarketDeltaTable rows={rosterDeltas} />
      )}

      <h4 className="dg-wc__group">Entered</h4>
      {entered.length === 0 ? (
        <p className="dg-wc__empty">No entered assets.</p>
      ) : (
        <ul className="dg-wc__list">
          {entered.map((e, i) => (
            <li key={e.sleeper_id ?? i}>{e.player_key}</li>
          ))}
        </ul>
      )}

      <h4 className="dg-wc__group">Exited</h4>
      {exited.length === 0 ? (
        <p className="dg-wc__empty">No exited assets.</p>
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

function MarketDeltaTable({ rows }: { rows: WhatChangedMarketDelta[] }) {
  return (
    <table className="dg-wc__table">
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.sleeper_id ?? i} className="dg-wc__row dg-wc__mover-row">
            <td>{r.player_name ?? r.player_key}</td>
            <td>{r.position}</td>
            <td className="dg-wc__delta dg-wc__value">{fmtSigned(r.value_delta)}</td>
            {/* I2a: the sparkline cell is reserved but HONEST-EMPTY — no path
                renders until the I2b PIT-series contract delivers real data. */}
            <td className="dg-wc__series-slot">series pending</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// H2 I2a daily tape: substrate facts ONLY (capture streak / last capture /
// model vintage / registry version) — never movement or trend claims. Each
// endpoint degrades independently to an honest unavailable line.
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
  const quiet = deltas.length === 0;

  return (
    <section className="dg-wc__region" aria-label="Model output changes">
      <h3 className="dg-wc__region-title">Model output changes</h3>
      {modelWindow?.status && <p className="dg-wc__caveat">{modelWindow.status}</p>}
      {modelWindow?.from_date && modelWindow?.to_date && (
        <p className="dg-wc__window">
          Model window {modelWindow.from_date} vs {modelWindow.to_date}
        </p>
      )}
      {modelWindow?.from_vintage?.semantic_output_hash &&
        modelWindow?.to_vintage?.semantic_output_hash && (
          <p className="dg-wc__vintage">
            Vintage {modelWindow.from_vintage.semantic_output_hash} →{" "}
            {modelWindow.to_vintage.semantic_output_hash}
          </p>
        )}
      {model.feature_freshness?.aborted_reason && (
        <p className="dg-wc__caveat">{model.feature_freshness.aborted_reason}</p>
      )}
      {model.pvo_staleness?.aborted_reason && (
        <p className="dg-wc__caveat">{model.pvo_staleness.aborted_reason}</p>
      )}
      {quiet ? (
        <p className="dg-wc__empty">Model no change.</p>
      ) : (
        <ModelDeltaTable rows={deltas} />
      )}
    </section>
  );
}

function ModelDeltaTable({ rows }: { rows: WhatChangedModelDelta[] }) {
  return (
    <table className="dg-wc__table">
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.sleeper_id ?? i} className="dg-wc__row dg-wc__mover-row">
            <td>{r.player_name ?? r.player_key}</td>
            <td>{r.position}</td>
            <td className="dg-wc__delta dg-wc__value">
              {fmtSigned(r.dynasty_value_score_delta)}
            </td>
            <td className="dg-wc__delta dg-wc__value">{fmtSigned(r.dvs_pct_delta)}</td>
            <td className="dg-wc__delta dg-wc__value">{fmtSigned(r.xvar_delta)}</td>
            <td className="dg-wc__series-slot">series pending</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Structural current-state baseline (Slice 2). Deliberately SUBORDINATE to the
// deltas above — it is CURRENT-STATE context (current_not_delta=true), not a
// day-over-day change, and exists only to make the deltas legible ("compared to
// what?"). Per the No-Verdict Line + the three-way-ruled v1 scope, it renders
// section SUMMARIES/COUNTS only. The producer artifact carries named, cut_priority-
// ranked drop candidates and named divergence cards; those are DELIBERATELY not
// rendered here — a static named/ranked cut list reads as a drop directive and
// duplicates the interactive Roster Capacity sandbox. That deferral is the whole
// point of this slice, so it is enforced by the RED's suppression assertions.
function StructuralBaseline({ ctx }: { ctx: WhatChangedStructuralContext }) {
  const s = ctx.sections;
  return (
    <section className="dg-wc__baseline" aria-label="Structural current-state baseline">
      <h3 className="dg-wc__region-title">Current-state baseline, not today's delta</h3>
      <p className="dg-wc__overlay-note">
        current_not_delta=true — absolute snapshot values that ground the deltas above;
        not day-over-day changes.
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
        <p className="dg-wc__caveat">
          Divergence card counts are an unvalidated descriptive overlay (Gate-4
          deferred); a tally of card types, not a proven edge.
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

// Per-section shell: accessible-named region + status/decision_supported honesty
// stamp + staleness caveat + aborted reason. The status label and value are kept
// in separate nodes so the section's "Status: <value>" never collapses into one
// text node (which would let a section status collide with the top-level status).
function BaselineSection({
  label,
  sec,
  children,
}: {
  label: string;
  sec: WhatChangedStructuralSection;
  children: ReactNode;
}) {
  return (
    <section className="dg-wc__baseline-section" aria-label={label}>
      <h4 className="dg-wc__group">{label}</h4>
      <p className="dg-wc__baseline-meta">
        <span className="dg-wc__meta-label">Status:</span>{" "}
        <span className="dg-wc__meta-value">{sec.status}</span>
      </p>
      <p className="dg-wc__baseline-meta">Descriptive only — not decision-grade.</p>
      {sec.staleness_caveat && (
        <p className="dg-wc__caveat">
          {sec.staleness_caveat.basis} —{" "}
          {sec.staleness_caveat.is_stale ? "stale" : "fresh"} (age{" "}
          {sec.staleness_caveat.age_hours}h)
        </p>
      )}
      {sec.aborted_reason && <p className="dg-wc__caveat">{sec.aborted_reason}</p>}
      {children}
    </section>
  );
}

function TeamValueLines({ sec }: { sec: WhatChangedStructuralSection }) {
  const v = sec.david_value_summary;
  if (!v) {
    return <p className="dg-wc__empty">No team value summary.</p>;
  }
  return (
    <>
      {v.lineup_xvar != null && (
        <p className="dg-wc__baseline-line">Lineup xvar: {v.lineup_xvar}</p>
      )}
      {v.starter_weighted_xvar != null && (
        <p className="dg-wc__baseline-line">
          Starter weighted xvar: {v.starter_weighted_xvar}
        </p>
      )}
      {v.top_n_xvar != null && (
        <p className="dg-wc__baseline-line">Top n xvar: {v.top_n_xvar}</p>
      )}
      {v.total_xvar_capped != null && (
        <p className="dg-wc__baseline-line">Total xvar capped: {v.total_xvar_capped}</p>
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
