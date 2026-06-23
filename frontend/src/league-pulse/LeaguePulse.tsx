import { useEffect, useState } from "react";

import type { LeaguePulseResponse } from "../lib/api";
import { zLeaguePulseResponse } from "../lib/api/zod.gen";
import { LeaguePulseHeader } from "./LeaguePulseHeader";
import "./LeaguePulse.css";
import { LoadingState, ParseErrorState, UnavailableState } from "./LeaguePulseStates";
import { PartnerRankings } from "./PartnerRankings";

// Read-only League Pulse surface over the frozen Inc1 GET /api/league/pulse contract.
// State machine: loading -> ready / unavailable / parse-error. The backend is always
// artifact-state, so status="degraded" is the normal READY case (header renders the
// as-of banner), NOT a failure. Any non-OK (incl. 503/422) -> unavailable; a JSON or
// Zod-contract failure -> parse-error. Never blank.
type State =
  | { status: "loading" }
  | { status: "ready"; data: LeaguePulseResponse }
  | { status: "unavailable" }
  | { status: "parse-error" };

export function LeaguePulse() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const res = await fetch("/api/league/pulse");
        if (!res.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        const data = zLeaguePulseResponse.parse(
          await res.json(),
        ) as LeaguePulseResponse;
        if (active) setState({ status: "ready", data });
      } catch {
        if (active) setState({ status: "parse-error" });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") return <LoadingState />;
  if (state.status === "unavailable") return <UnavailableState />;
  if (state.status === "parse-error") return <ParseErrorState />;

  // READY (incl. degraded artifact-state). Section components are wired in T2–T5.
  return (
    <section
      className="dg-league-pulse"
      aria-label="League Pulse"
      data-testid="league-pulse-ready"
      data-status={state.data.status}
    >
      <LeaguePulseHeader data={state.data} />
      <PartnerRankings rankings={state.data.partner_rankings ?? []} />
      {/* Postures + Values (T4), Opportunity Cards (T5) */}
    </section>
  );
}
