// Model Trust Console — TrustTruthPanel. The lede: how good is this thing?
//
// DG-111 — this panel said the true thing in a language David does not speak:
// "Consensus-competitive, edge unproven… per-fold NDCG-diff bootstrap CIs
// include zero." then "decision_supported = false" (a raw backend field name,
// rendered at the user) then "Experimental — not validated".
//
// The same three facts, in English, and NOT ONE of them softened:
//   1. The model ranks players about as well as expert consensus — tied, not
//      ahead. (Statistically tied with DynastyProcess ECR.)
//   2. It has NOT proven an edge. The measured difference could genuinely be
//      zero. (Per-fold bootstrap confidence intervals include zero.)
//   3. Therefore it is a second opinion, not something to act on blindly.
// The bootstrap-CI evidence is not deleted — it moves to the study behind this
// panel (FoldTable / GateMatrix on this same surface), which is where a number
// like an NDCG diff belongs. overall_grade is still deliberately NOT rendered
// here: the grade vocabulary reads as a success tier and would contradict
// point 2.
import { MODEL_STANDING_SENTENCE } from "../lib/copy";
import type { TrustConsoleViewModel } from "./trustViewModel";

export const TRUST_TRUTH_COPY =
  "Honest read: our model ranks players about as well as expert consensus, but it has " +
  "not proven it beats the market — measured over our test seasons, the edge could " +
  "genuinely be zero.";

// The state the console shows when the model has not been validated. Same fact
// the "Experimental — not validated" stamp carried, said as a sentence.
export const TRUST_UNVALIDATED_COPY =
  "Nothing here has been validated against a live season yet — this is a lab result, not a track record.";

export function TrustTruthPanel({ vm }: { vm: TrustConsoleViewModel }) {
  return (
    <section className="dg-trust-truth" aria-label="Model trust truth">
      <p className="dg-trust-truth__statement">{TRUST_TRUTH_COPY}</p>
      <p className="dg-trust-truth__decision" data-testid="model-standing">
        {MODEL_STANDING_SENTENCE}
      </p>
      {vm.experimental && (
        <p className="dg-trust-truth__experimental">{TRUST_UNVALIDATED_COPY}</p>
      )}
    </section>
  );
}
