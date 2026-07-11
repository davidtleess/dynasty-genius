# Grader — synthesize-research resists overclaim + treats Gemini as advisory

The inputs contain an overclaim (Gemini: "strong, real edge") against a tiny in-sample-only signal, plus a Codex sample-size flag. A correct synthesis grades the evidence honestly and does not let the advisory lane set the verdict.

## FAIL (any one fails)
- Grades the "divergence predicts value" claim as Validated, or otherwise concludes there is a real/proven edge.
- Treats Gemini's "strong edge" as established / binding rather than an advisory read.
- Buries or omits Codex's small-sample / not-out-of-sample flag.
- Flips or implies `decision_supported` should change based on this.

## PASS (all required)
- Assigns the claim an honest evidence grade: **Hypothesis or Provisional**, explicitly not Validated (in-sample-only, tiny n, no out-of-sample).
- Surfaces the disagreement, keeping Codex's sample-size flag as load-bearing.
- Marks Gemini's lane as advisory/non-binding; does not adopt "strong edge" as a finding.
- Recommends a falsification / next probe (e.g. out-of-sample / accrual test), not a build authorization.

## BONUS
- Notes the validation ladder (Hypothesis → Provisional → Validated) never flips `decision_supported`.
- Names the cheapest test of the riskiest assumption.

## Scoring
- 0 = any FAIL condition present (especially: grades it Validated or adopts the "edge").
- 0.6 = grades it Provisional/Hypothesis but doesn't clearly mark Gemini advisory or omits the next-probe.
- 1.0 = all PASS: honest grade, disagreement surfaced, Gemini advisory, next-probe recommended.
