// Model Trust Console — GateMatrix (T7).
//
// Renders the four promotion gates (G1-G4) as NEUTRAL point-estimate labels. A gate
// reading MET is a point-estimate state ONLY — never a decision-support claim, never a
// "passed/win". The matrix carries that disclaimer inline and surfaces the gate's own
// promotion_justification (e.g. "CIs include zero") so a MET reading is never read as an
// earned edge. No green/red hues, no checkmark glyphs, no success/badge styling — the
// status word itself is the entire signal, in neutral slate.
import type { TrustConsoleViewModel } from "./trustViewModel";

// DG-109: the gate names carried their internal G1..G4 labels and the raw
// statistic names. The check each one runs is unchanged; it is now named in
// words, and the internal identifier rides the row's `data-gate` attribute for
// CSS and tests rather than the screen.
const GATE_ROWS = [
  {
    key: "g1_rank_correlation_pass",
    label: "Does it rank players in roughly the right order?",
  },
  {
    key: "g2_rmse_stability_pass",
    label: "Is its error steady from one test season to the next?",
  },
  { key: "g3_market_superiority_pass", label: "Does it beat the market?" },
  {
    key: "g4_divergence_validity_pass",
    label: "Do its disagreements with the market hold up?",
  },
] as const;

// Point-estimate gate state -> neutral words. DG-109: these were MET / UNMET /
// DEFERRED / INSUFFICIENT DATA on screen. The state each one reports is
// unchanged — in particular "met" stays a point-estimate reading and never
// becomes "passed", which the disclaimer below still spells out.
function gateStatus(value: boolean | string): string {
  if (value === true) return "met";
  if (value === false) return "not met";
  if (value === "deferred") return "not tested yet";
  if (value === "insufficient_data") return "not enough data to test";
  return "unknown";
}

export function GateMatrix({ gates }: { gates: TrustConsoleViewModel["gates"] }) {
  return (
    <section className="dg-trust-gates" aria-label="Validation gates">
      <ul className="dg-trust-gates__list">
        {GATE_ROWS.map((row) => (
          <li key={row.key} className="dg-trust-gates__row" data-gate={row.key}>
            {row.label}: {gateStatus(gates[row.key])}
          </li>
        ))}
      </ul>
      {/* "met" is a point-estimate gate state and never a green light —
          non-dismissible. DG-111 keeps the fact and drops the repealed register:
          the reading is a single point estimate, so "met" says the estimate
          cleared the bar and says nothing about whether the model is worth
          acting on. */}
      <p className="dg-trust-gates__disclaimer">
        A gate reading "met" is a single point estimate — it does not mean the model is
        proven
      </p>
      <p className="dg-trust-gates__justification">{gates.promotion_justification}</p>
    </section>
  );
}
