# Evidence copy correction — 2026-09-06, after the bounded research-preview review (Codex)

No forecast, evaluation or score in this run is changed; no existing file in this directory is modified.

**What is corrected.** `policy_comparison.json` → `evidence_status["inner_menu"]`, and the sentence rendered
from it in `REPORT.md` ("Declared policy: inner_menu — independent of the policy choice: …"), OVERSTATE the
evidence. The policy selects only inside each training window, but the policy MENU (plain / class-year trend /
trend + first-round-QB indicator) was refined after these historical years had been inspected in earlier runs.
The outer evaluation is therefore:

> **retrospective historical evaluation with forecast cutoffs enforced** — not untouched independent confirmation.

**Exact replacement language** (now the template wording in `evaluate.py` for every later run):

- policy arm: "retrospective historical evaluation with forecast cutoffs enforced; the policy selects, if at all,
  only inside each training window, but the policy menu itself was refined after inspecting these historical
  years, so this is not untouched independent confirmation"
- exploratory arm: "exploratory comparison against the declared policy on the same retrospective evaluation;
  never used to reassign the canonical evidence"

The same overstated wording appears in the superseded runs `153743Z` and `154033Z`; this note covers them.

**Unchanged and still disclosed:** the first-round-quarterback under-prediction (CALIBRATION.md, REPORT.md);
no blanket adjustment is applied anywhere.
