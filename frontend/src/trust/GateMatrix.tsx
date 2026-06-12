// Model Trust Console — GateMatrix (T7).
//
// Renders the four promotion gates (G1-G4) as NEUTRAL point-estimate labels. A gate
// reading MET is a point-estimate state ONLY — never a decision-support claim, never a
// "passed/win". The matrix carries that disclaimer inline and surfaces the gate's own
// promotion_justification (e.g. "CIs include zero") so a MET reading is never read as an
// earned edge. No green/red hues, no checkmark glyphs, no success/badge styling — the
// status word itself is the entire signal, in neutral slate.
import type { TrustConsoleViewModel } from "./trustViewModel";

const GATE_ROWS = [
  { key: "g1_rank_correlation_pass", label: "G1 Rank correlation" },
  { key: "g2_rmse_stability_pass", label: "G2 RMSE stability" },
  { key: "g3_market_superiority_pass", label: "G3 Market superiority" },
  { key: "g4_divergence_validity_pass", label: "G4 Divergence validity" },
] as const;

// Point-estimate gate state -> neutral label. bool gates yield MET/UNMET; the
// market/divergence gates can additionally be deferred or (G4) insufficient-data.
function gateStatus(value: boolean | string): string {
  if (value === true) return "MET";
  if (value === false) return "UNMET";
  if (value === "deferred") return "DEFERRED";
  if (value === "insufficient_data") return "INSUFFICIENT DATA";
  return "UNKNOWN";
}

export function GateMatrix({ gates }: { gates: TrustConsoleViewModel["gates"] }) {
  return (
    <section className="dg-trust-gates" aria-label="Validation gates">
      <ul className="dg-trust-gates__list">
        {GATE_ROWS.map((row) => (
          <li key={row.key} className="dg-trust-gates__row">
            {row.label}: {gateStatus(gates[row.key])}
          </li>
        ))}
      </ul>
      {/* MET is a point-estimate gate state, NOT decision support — non-dismissible. */}
      <p className="dg-trust-gates__disclaimer">
        MET = point-estimate gate state, not decision support
      </p>
      <p className="dg-trust-gates__justification">{gates.promotion_justification}</p>
    </section>
  );
}
