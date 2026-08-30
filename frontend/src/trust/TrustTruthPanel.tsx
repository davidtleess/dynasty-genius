// Model Trust Console — TrustTruthPanel (T6). The lede.
//
// Renders the fixed canonical G3 truth statement (a single constant, never free-typed;
// no global R2 claim — R2 is per-fold in T8's table), the universal non-dismissible
// decision_supported=false state, and the experimental state. overall_grade is
// DELIBERATELY NOT rendered here: the real grade vocabulary reads as a success tier
// (e.g. WR's ACTIVE_B_VALIDATED), which would contradict "edge unproven", so it is
// demoted to the provenance footer (T9, spec §10).
import { DISCLOSURE_LINE } from "../lib/copy";
import type { TrustConsoleViewModel } from "./trustViewModel";

// DG-109: this is the lede — the one sentence about the model David actually
// reads — and it carried `NDCG`, a ranking-quality statistic, as a shouted
// acronym. NOTHING in the claim changed: still consensus-competitive, still edge
// unproven, still statistically tied with the same benchmark, and the per-fold
// intervals still include zero. Only the statistic's name is said in words. The
// string stays a single constant, never free-typed at a call site.
export const TRUST_TRUTH_COPY =
  "Consensus-competitive, edge unproven. Engine B is statistically tied with " +
  "DynastyProcess expert consensus rankings; season by season, the range around " +
  "its ranking-quality edge still includes zero.";

export function TrustTruthPanel({ vm }: { vm: TrustConsoleViewModel }) {
  return (
    <section className="dg-trust-truth" aria-label="Model trust truth">
      <p className="dg-trust-truth__statement">{TRUST_TRUTH_COPY}</p>
      {/* Universal, non-dismissible decision-support state (no dismiss control).
          DG-109: the API field `decision_supported=false` is unchanged and the
          state is still stated at the same strength — the UI just stops quoting
          the field name at the user, which is what copy.ts:679-682 says this
          shared constant is for. It was still being quoted verbatim here. */}
      <p className="dg-trust-truth__decision">{DISCLOSURE_LINE}</p>
      {vm.experimental && (
        <p className="dg-trust-truth__experimental">Experimental — not validated</p>
      )}
    </section>
  );
}
