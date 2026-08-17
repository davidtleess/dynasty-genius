# QB-1 exclusion-row diagnostic continuation — Codex v1

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Transition: revision 124 BLOCKED → revision 125 ACTIVE `verifying`  
State repair: `TW16-QB1-EXCLUSION-ROW-DIAGNOSTIC-CONTINUATION-CODEX-V1`

## Failed receipt recorded

The Round-19 CLEAR-authorized registered rerun fired exactly once and failed
closed. Codex independently reproduced:

- terminal artifact SHA-256
  `0c0cd6308a14dc44a177335ddafc2876f65e2010d3ae1748e8e912e197540956`,
  296 bytes, exact six-key failed envelope;
- stdout receipt SHA-256
  `ceb2fba7a8c18b9b48380de5037e0e8b00c09f80681bc297a23e02700109bb7f`,
  981 bytes, exact five-key failed CLI summary;
- terminal report SHA-256
  `0f05fadd02f4a5489edbc73b4b5504318e667a6f13eb08af7596091e4679584d`;
- `run_status=failed`, `failure_reason=report_schema_invalid`,
  `decision_supported=false`, and no registered result;
- `failure_origin.phase=execute` with exactly five closed site records. The
  terminal meaningful pair is
  `validate_registered_report_blocks` at `execution.py:1298` followed by
  `_refuse` at `execution.py:965`;
- zero remaining registered runner processes, no second fire, and the grant
  consumed.

The failed `real-surface-qa` check was recorded durably. The accumulated
fail-closed threshold correctly moved the run to revision 124
`blocked/BLOCKED` before the guarded continuation reopened it.

## Registration read before staging

The measured clause requires each `excluded_folds` entry to be a mapping with
a non-negative integer `test_season` and a non-empty `reasons` sequence whose
members are in the closed four-word fold-flag vocabulary. The receipt proves
that at least one real composed entry violates that conjunction, but it does
not reveal the comparison, season, failed conjunct, or reason word.

Static source inspection narrows the producer space without identifying the
real row: `pool_paired_deltas` constructs the mapping and season fields and
copies `_fold_reasons(fold)`; the comparison producer can emit the literal
reason words `empty_common_pool`, `fold_starved`, and `degenerate_input`, while
the current publication vocabulary contains `fold_starved`,
`join_coverage_low`, `join_reconciliation_failed`, and `degenerate_input`.
This is a candidate producer/gate mismatch, not a measured root-cause claim;
the real offending projection remains required before classification.

Because the rejected payload was not durable, that projection cannot be read
from the failed process. A new registered runner is not authorized. David's
standing continuation words — “ok lets continue until we get throught h5”,
then “go” — support one diagnostic-only replay under the closed boundary below.

## Staged diagnostic boundary

Exactly one invocation of the unchanged frozen-input composition may occur,
outside the registered runner. It must be intercepted at the already-measured
`compose_study` defense-in-depth call to
`validate_registered_report_blocks` and abort before that validator returns.
The full candidate payload must never be serialized, printed, or inspected.

The only allowed durable projection is:

- registered comparison ID and lane;
- `excluded_folds` container type and structural length;
- per-entry index and sorted key names;
- registered `test_season` literal plus type/predicate result;
- `reasons` container type and structural length;
- exact reason words, closed-vocabulary membership, and named failed
  conjuncts;
- aggregate structural counts over those fields.

Forbidden from reading or persistence: pooled or paired deltas, correlations,
confidence intervals, p-values, adjusted p-values, support statuses,
predictions, labels, player identities, common-pool sizes, case-panel values,
sensitivity values, raw payload content outside the projection, failure detail,
or exception text.

There is no runner, terminal write, receipt mutation, provider fetch, input
mutation, product-code/test write, repair, implementation round, registered
rerun, commit, or push. Before/after hashes of the pinned code, registered
inputs, terminal artifact, and stdout receipt are mandatory. If the safe
projection cannot be obtained under these constraints, the named disposition
is `diagnostic_projection_unavailable`; the boundary must not widen.

Results return to Codex for a registration read. No vocabulary change or
producer repair is authorized until Codex classifies the measured mismatch as
implementation or amendment and opens a separately revision-guarded round.

## Transition proof

`qb1_exclusion_row_diagnostic_continuation_open_codex_v1.mjs` passed syntax
validation and its guarded dry run at revision 124. The sole `--apply`
invocation persisted revision 125, phase `verifying`, terminal state null,
with no implementation round, registered runner, or registered rerun open.

H2 QB rushing remains **UNDER TEST with no result**.
