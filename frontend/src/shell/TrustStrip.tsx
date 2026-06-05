import { useEffect, useState } from "react";
import type { z } from "zod";

import { zTrustSurfaceResponse } from "../lib/api/zod.gen";
import "./TrustStrip.css";

// The validated shape IS the generated Zod schema's output (validated at the SDK
// boundary), so derive the type from it rather than the parallel generated TS type.
type TrustSurface = z.infer<typeof zTrustSurfaceResponse>;

type Position = "QB" | "RB" | "WR" | "TE";

type TrustState =
  | { status: "loading" }
  | { status: "ready"; data: TrustSurface }
  | { status: "unavailable" };

const UNVALIDATED_GRADES = new Set(["PRE_MODEL", "EXPERIMENTAL"]);

export function TrustStrip({ position }: { position: Position }) {
  const [state, setState] = useState<TrustState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`/api/trust-surface/${position}`);
        if (!response.ok) {
          if (!cancelled) setState({ status: "unavailable" });
          return;
        }
        // Validate at the SDK boundary with the generated Zod schema: a 200 whose
        // shape does not match the contract degrades, it never renders raw/unverified.
        const parsed = zTrustSurfaceResponse.safeParse(await response.json());
        if (!parsed.success) {
          if (!cancelled) setState({ status: "unavailable" });
          return;
        }
        if (!cancelled) setState({ status: "ready", data: parsed.data });
      } catch {
        if (!cancelled) setState({ status: "unavailable" });
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [position]);

  return (
    <div className="dg-trust" role="status" aria-label="Trust strip status">
      {state.status === "loading" && (
        <span className="dg-trust__loading">Loading trust...</span>
      )}
      {state.status === "unavailable" && (
        <span className="dg-trust__unavailable">Trust data unavailable</span>
      )}
      {state.status === "ready" && <TrustReady data={state.data} />}
    </div>
  );
}

function TrustReady({ data }: { data: TrustSurface }) {
  const unvalidated = data.experimental || UNVALIDATED_GRADES.has(data.overall_grade);
  const freshnessDates = Object.values(data.market_snapshot_dates ?? {});

  return (
    <div className="dg-trust__body">
      <span className="dg-trust__label">Model grade</span>
      <span className="dg-trust__grade">{data.overall_grade}</span>
      {unvalidated && <span className="dg-trust__badge">Unvalidated</span>}
      <span className="dg-trust__label">Source</span>
      <span className="dg-trust__source">
        {data.market_source_label ?? data.market_source}
      </span>
      {freshnessDates.map((date) => (
        <span key={date} className="dg-trust__freshness">
          {date}
        </span>
      ))}
      {data.model_reliability?.caveat && (
        <span className="dg-trust__caveat">{data.model_reliability.caveat}</span>
      )}
    </div>
  );
}
