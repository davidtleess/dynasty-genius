# QB-1 Execution GREEN Review — Codex v1

**Cycle:** TW14-QB1-1  
**Verdict:** **NOT CLEAR**  
**Review boundary received:** `execution.py` `5e95cb58…` · `status.py` `5592b472…` ·
`__init__.py` `987b8ca5…` · D1 fetch script `d781bddc…` · four §9.1 files 4/4 pinned.

No study execution occurred. H2 QB rushing remains **UNDER TEST** with no result.

## Positive disposition — legacy r12 collision

QBGREEN-F1 is **ACCEPTED**. The three old rows pinned the retired H5 stub and collided by
construction with the frozen execution RED. I amended only those three parameter cases to pass a
valid H5 payload for `H5`, `h5 `, and ` H5`, and to require the H5-only
`market_noninferior` vocabulary plus `decision_supported=False`. Revised whole-file SHA-256:
`db351f8c321bd83179a8bab17beffc435709265e23909aff64468ecae981790d`.
The full reinforcement file is **344/344 passing**.

## Findings

### G1 — BLOCKER — the real 7/7 D1 envelope is unusable by the shipped D1 gate

`admit_fetch_manifest` emits `metadata.completeness="complete"`; the existing
`load_validation_sources` contract requires exactly `"ok"`. The live local receipt hashes and
parses all seven datasets, then the next registered boundary rejects every one:

`source_unavailable: weekly: completeness 'complete'; ... pbp: completeness 'complete'`.

This is an end-to-end integration failure hidden by testing only the new admission helper in
isolation. The source-state output must pass `load_validation_sources` unchanged, and the RED must
pin the composition.

### G2 — BLOCKER — D1 admission ignores the receipt's registration pin

The completion receipt carries `registration_pin`, but `admit_fetch_manifest` never reads it. A
receipt changed to sixty-four zeroes still admits all seven datasets. That breaks the binding
pre-registration protocol and the Codex RED contract's stated registration-pin admission law.
Refuse a missing/wrong receipt pin before any frame parse, with a named registration failure.

### G3 — BLOCKER — the terminal runner can publish invalid evidence and can emit silence

`run_qb1_study` writes any mapping returned by `execute` without assembling or validating it. A
callback returning `{"run_status":"ok","decision_supported":true}` is atomically published as
success. Conversely, a plain `ValueError` escapes and produces no terminal artifact. Both violate
D5: recursive No-Verdict enforcement and **every invocation emits an artifact, including
failures**. Validate/assemble success before publication and convert ordinary execution failures
to a named, metric-free failed report; do not catch process-control exceptions.

### G4 — BLOCKER — no reviewed end-to-end composition exists

The only `run_qb1_study` production symbol is a generic callback wrapper; there is no non-test
caller and no study runner script. `scripts/` contains only `run_qb1_d1_fetch.py`. David's new word
authorizes execution **after Codex CLEAR**, while Claude disclosed that
`scripts/run_qb1_study.py` is being authored now; at this verdict it does not exist. A material
composition artifact created after the handed-off pins cannot execute first and be reviewed from
its receipt. It must enter the GREEN review boundary, with its pin and hermetic composition RED,
before the trigger can clear.

### G5 — BLOCKER — F33 misses the registered `validation_*` consumer wall

The frozen F33 contract explicitly scans imports, `validation_*` adapter call sites, and study-root
reads repo-wide under `src/dynasty_genius/**` and `app/**`. The implementation scans only three
string markers and none is `validation_`. A synthetic served-app module importing and calling
`load_validation_weekly_stats` passes `enforce_consumer_boundary` cleanly. The three broad
path-substring allowlist entries also create permanent blind spots inside entire files. Pin the
exact registered symbol/path/import wall and make exceptions occurrence-specific, not whole-file
escape hatches.

### G6 — BLOCKER — H5 status labels impossible or contradictory evidence

The H5 boundary lacks the model lane's total-evidence validation. It accepts >4 folds, p-values
outside `[0,1]`, reversed CI bounds, and a pooled delta whose sign contradicts the zero-excluding
CI. Concrete examples all receive substantive H5 labels: `folds=5`, `adjusted_p_ni=-1`,
`p_ni=2`, `ci95=[0.20,0.10]`, and positive δ with an entirely negative CI. Most seriously, the
last case can emit `model_superior` even though registered δ is positive. These must refuse named
before the ordered status function.

### G7 — WARN — two exact-count validators admit impossible cardinality

`require_case_panel` checks only the set of ids, so all seven ids plus a duplicate eighth row pass
the “exactly seven” gate. `validate_join_coverage(101,100,...)` admits coverage `1.01`. Pin exact
case-row uniqueness and `0 <= joined <= evaluable` with named refusals.

## Evidence

- Exact four source pins reproduced.
- Frozen execution/program/inference bundle: **30 + 129 + 52 = 211 passed**.
- Revised legacy reinforcement file: **344 passed**; the three r12 rows now pass.
- Adversarial reproducer:
  `qb1_green_adversarial_probe_codex_v1.py`, SHA-256
  `de97c5ff09f4483c00b49349e08118d3a3009739703af80ab1b60344dcd9a3b7` — **13/13
  reproductions pass** against the defective behavior above.
- Real local D1 read-only probe: 7/7 parsed with reported rows
  `199868/21377/25035/33195/12472/12927/532376`, then all seven rejected for
  `completeness='complete'`.
- Four durable H5 files independently hash to the exact registered §9.1 values.
- `rg` finds no non-test caller of `run_qb1_study`; `scripts/run_qb1_study.py` is absent at
  verdict time.
- Touched r12 and probe Ruff clean; touched diff-check clean. A full-suite rerun is not used to
  smooth the six open BLOCKERs.

## Required next boundary

Claude owns the smallest GREEN corrections plus the completed composition script and focused
contracts. Re-review occurs before execution. David's execution trigger remains valid but held:
**no review CLEAR, no run**. No provider call, refetch, registration change, result artifact,
commit, or push is authorized by this review.
