import { useEffect, useState } from "react";

import type {
  WhatChangedMarketDelta,
  WhatChangedMarketSection,
  WhatChangedModelDelta,
  WhatChangedModelSection,
  WhatChangedResponse,
} from "../lib/api/types.gen";
import { zWhatChangedResponse } from "../lib/api/zod.gen";
import "./DailyWhatChanged.css";

type State =
  | { status: "loading" }
  | { status: "ready"; data: WhatChangedResponse }
  | { status: "unavailable" }
  | { status: "parse-error" };

// Read-only Daily What-Changed surface (Slice 1: daily_diff only). It reports the
// day-over-day market and model DELTAS — what changed since the prior snapshot — and
// issues no verdict. Market (price-discovery overlay) and model (output changes) are
// kept in structurally isolated regions so a market price swing never reads as a
// model signal. structural_context is deferred (it duplicates League Pulse / Roster
// Audit) and is never rendered here.
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
      <p className="dg-wc__disclaimer">
        Descriptive only — decision_supported=false. A daily delta surface (what changed
        since the prior snapshot); no verdict, no nominated move.
      </p>
      <p className="dg-wc__status">Status: {data.overall_status}</p>
      <p className="dg-wc__generated">Generated: {data.generated_at}</p>
      {comparisonWindow?.from_date && comparisonWindow?.to_date && (
        <p className="dg-wc__window">
          Captured {comparisonWindow.from_date} vs {comparisonWindow.to_date}
        </p>
      )}
      <MarketRegion market={daily.market} />
      <ModelRegion model={daily.model} />
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
          <tr key={r.sleeper_id ?? i} className="dg-wc__row">
            <td>{r.player_name ?? r.player_key}</td>
            <td>{r.position}</td>
            <td className="dg-wc__delta">{fmtSigned(r.value_delta)}</td>
          </tr>
        ))}
      </tbody>
    </table>
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
          <tr key={r.sleeper_id ?? i} className="dg-wc__row">
            <td>{r.player_name ?? r.player_key}</td>
            <td>{r.position}</td>
            <td className="dg-wc__delta">{fmtSigned(r.dynasty_value_score_delta)}</td>
            <td className="dg-wc__delta">{fmtSigned(r.dvs_pct_delta)}</td>
            <td className="dg-wc__delta">{fmtSigned(r.xvar_delta)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
