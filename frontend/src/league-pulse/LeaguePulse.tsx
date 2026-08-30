import { useEffect, useState } from "react";

import type { LeaguePulseResponse } from "../lib/api";
import { zLeaguePulseResponse } from "../lib/api/zod.gen";
import { LeaguePulseHeader } from "./LeaguePulseHeader";
import "./LeaguePulse.css";
import { LoadingState, ParseErrorState, UnavailableState } from "./LeaguePulseStates";
import { OpportunityCards } from "./OpportunityCards";
import { PartnerRankings } from "./PartnerRankings";
import { TeamPostureTable } from "./TeamPostureTable";
import { TeamValueOverview } from "./TeamValueOverview";

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

// Mirrors the registered POSTURE_SIGNAL_WEIGHTS export in
// src/dynasty_genius/team_posture.py (the graduation RED couples the two —
// change the producer weights and this mirror without both, and tests fail).
const POSTURE_BASIS = [
  { label: "starter-weighted model value", pct: "60%" },
  { label: "roster age profile", pct: "20%" },
  { label: "early draft-pick balance", pct: "15%" },
  { label: "taxi/development stash", pct: "5%" },
] as const;

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
      {/* The graduation mitigation contract (league_pulse_fe_mitigation_v1):
          no-intent-certainty copy + the posture basis mirroring the registered
          POSTURE_SIGNAL_WEIGHTS export in team_posture.py.

          DG-111 — this paragraph was byte-locked. David's 2026-08-29 ruling is
          the sign-off that replaces it, and the replacement is recorded verbatim
          in the ticket. Every fact the lock protected is still here, in the same
          DOM position, ahead of every panel: the labels are computed, not
          observed; they come from these four roster signals; the weights are
          disclosed right below; and a manager's real intent is not something we
          can see. Only the register changed. */}
      <div
        className="dg-league-pulse__mitigation"
        data-mitigation-contract="league_pulse_fe_mitigation_v1"
      >
        <p className="dg-league-pulse__mitigation-copy">
          We label each team contending, rebuilding and so on by reading four things off
          its roster — starter-weighted model value, roster age profile, early
          draft-pick balance, and taxi/development stash — weighted as shown below. That
          is our read of the roster, not a read of the manager: what they actually
          intend to do, how they really value their own players, and whether they want
          to trade at all are things nobody can see from here.
        </p>
        <dl
          className="dg-league-pulse__mitigation-basis"
          data-testid="league-pulse-posture-basis"
        >
          {POSTURE_BASIS.map(({ label, pct }) => (
            <div key={label} className="dg-league-pulse__mitigation-basis-row">
              <dt>{label}</dt>
              <dd>{pct}</dd>
            </div>
          ))}
        </dl>
      </div>
      <PartnerRankings rankings={state.data.partner_rankings ?? []} />
      <TeamPostureTable postures={state.data.team_postures ?? []} />
      <TeamValueOverview values={state.data.team_values ?? []} />
      <OpportunityCards
        cardSectionCounts={state.data.card_section_counts ?? []}
        modelNativeCards={state.data.model_native_cards ?? []}
        marketOverlayCards={state.data.market_overlay_cards ?? []}
      />
    </section>
  );
}
