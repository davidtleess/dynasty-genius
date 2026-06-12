// Model Trust Console — TrustTruthPanel (T6). The lede.
//
// Renders the fixed canonical G3 truth statement (a single constant, never free-typed;
// no global R2 claim — R2 is per-fold in T8's table), the universal non-dismissible
// decision_supported=false state, and the experimental state. overall_grade is
// DELIBERATELY NOT rendered here: the real grade vocabulary reads as a success tier
// (e.g. WR's ACTIVE_B_VALIDATED), which would contradict "edge unproven", so it is
// demoted to the provenance footer (T9, spec §10).
import type { TrustConsoleViewModel } from "./trustViewModel";

export const TRUST_TRUTH_COPY =
  "Consensus-competitive, edge unproven. Engine B is statistically tied with " +
  "DynastyProcess ECR expert consensus; per-fold NDCG-diff bootstrap CIs include zero.";

export function TrustTruthPanel({ vm }: { vm: TrustConsoleViewModel }) {
  return (
    <section className="dg-trust-truth" aria-label="Model trust truth">
      <p className="dg-trust-truth__statement">{TRUST_TRUTH_COPY}</p>
      {/* Universal, non-dismissible decision-support state (no dismiss control). */}
      <p className="dg-trust-truth__decision">decision_supported = false</p>
      {vm.experimental && (
        <p className="dg-trust-truth__experimental">Experimental — not validated</p>
      )}
    </section>
  );
}
