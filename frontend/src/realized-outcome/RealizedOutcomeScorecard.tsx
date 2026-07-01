import { useEffect, useState } from "react";

import type { RealizedOutcomeScorecardResponse } from "../lib/api/types.gen";
import { zRealizedOutcomeScorecardResponse } from "../lib/api/zod.gen";
import "./RealizedOutcomeScorecard.css";

type State =
  | { status: "loading" }
  | { status: "ready"; data: RealizedOutcomeScorecardResponse }
  | { status: "unavailable" }
  | { status: "parse-error" };

// Read-only Realized-Outcome scaffolding surface. It scores a FROZEN model's
// predictions vs realized NFL outcomes — a DIAGNOSTIC accuracy/fidelity audit, never
// a player verdict. No scorecard artifact exists yet (off-season no-op), so the
// primary state is an honest, educational "not yet accruing" placeholder. Even once a
// scorecard is produced, rich metric rendering (rank tables / MIF / cohorts) waits for
// a real artifact to verify against in ~Sept 2026 — this surface only scaffolds the
// contract + empty/active states. decision_supported stays false; market is excluded.
export function RealizedOutcomeScorecard() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const res = await fetch("/api/realized-outcome/scorecard");
        if (!res.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        const data = zRealizedOutcomeScorecardResponse.parse(
          await res.json(),
        ) as RealizedOutcomeScorecardResponse;
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
    return <p className="dg-ro__notice">Loading diagnostic scorecard…</p>;
  }
  if (state.status === "unavailable") {
    return <p className="dg-ro__notice">Diagnostic Scorecard unavailable.</p>;
  }
  if (state.status === "parse-error") {
    return <p className="dg-ro__notice">Could not read Diagnostic Scorecard.</p>;
  }
  return <ReadyView data={state.data} />;
}

function ReadyView({ data }: { data: RealizedOutcomeScorecardResponse }) {
  const inactive = data.status === "inactive";
  const maturity =
    data.maturity_pct === null || data.maturity_pct === undefined
      ? "unset"
      : data.maturity_pct;

  return (
    <section className="dg-ro" aria-label="Diagnostic Scorecard">
      <p className="dg-ro__eyebrow">Accuracy Tracker</p>
      <h2 className="dg-ro__title">Diagnostic Scorecard</h2>

      {inactive ? (
        <div className="dg-ro__state">
          <p className="dg-ro__lead">
            Realized-outcome loop inactive — 2026 data accrues from September.
          </p>
          {data.status_reason && (
            <p className="dg-ro__meta">Reason: {data.status_reason}</p>
          )}
          <p className="dg-ro__note">
            Once the season is underway, this surface will track how the frozen model's
            predictions hold up against actual NFL production: within-position rank
            accuracy per position cohort, plus a fidelity audit of the model's inputs.
            It stays descriptive until it accrues enough to settle.
          </p>
        </div>
      ) : (
        <div className="dg-ro__state">
          <p className="dg-ro__lead">Scorecard scaffold active.</p>
          <p className="dg-ro__note">
            Rich metric rendering waits for real artifact validation (~Sept 2026); this
            surface currently confirms the contract without a metrics table.
          </p>
        </div>
      )}

      <p className="dg-ro__meta">settlement_status: {data.settlement_status}</p>
      <p className="dg-ro__meta">maturity_pct: {maturity}</p>
      <p className="dg-ro__meta">decision_supported=false</p>

      <p className="dg-ro__note">
        Model Input Fidelity is an input/fidelity audit — it checks whether realized NFL
        usage matches the model's input assumptions. It is a diagnostic on the inputs,
        not a player verdict.
      </p>
    </section>
  );
}
