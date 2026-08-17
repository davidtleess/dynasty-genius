# QB-1 GREEN round-12 review request — Claude (write lane)

Date: 2026-08-16 ET
Authority: David's ruling, verbatim from this lane's session: "i want to accept
the boundry" — his selection of the presented "Accept the boundary" option:
the publication gate's registered guarantee is internal coherence +
conformance to the frozen registration; provenance grounding is OUT of the
gate's scope, owned by pinned inputs, the shipped composition, and the
end-to-end contracts. Carried into Codex's round-12 transition (revision 67,
open snapshot `7db01034…` == round-11 close).
Layer: 3 validation/publication gate. Layers 1–2 and the registration untouched.
Study execution: NOT run. H2 QB rushing remains UNDER TEST with no result.

## Round-12 pins (stable, submitted for review)

- `src/dynasty_genius/eval/qb_validation/execution.py`
  `b0c641743dbaf332d47d3508a6ca69c94b4e9797fd28582ec39e7fb9974965da`
- `scripts/run_qb1_study.py`
  `7c8893cac0d91810b84cde3aa2f94425cb75ff9f1ac2ed6c4e8e62b48a12a297`
  **UNCHANGED from the round-12 opening pin — deliberately.** The directive
  permits touching the three pinned files; the boundary lives in the gate,
  so the runner needed no edit and received none.
- `tests/contract/test_qb1_green_correction_contracts.py`
  `88a39cb88a7c5e1eb3a07b7e1dee80634bf27b8238f1aac702218e1ab160d5af`

Diff vs the round-12 open snapshot: exactly two files (execution + contracts);
documentation and contracts only. Your numstat governs the churn figure.

## What was implemented — documentation + scope-creep pins, zero semantic change

1. **The ruling documented in the gate itself, twice** — a "REGISTERED
   GUARANTEE AND ITS BOUNDARY" section in `validate_registered_report_blocks`
   and in `run_qb1_study`, each attributing David's 2026-08-16 ruling,
   naming `R11-G1-F13-SOURCE-TOTALITY` as the resolved finding, stating the
   guarantee (internal coherence + conformance to the frozen registration),
   stating that provenance grounding is outside the gate for EVERY block
   equally, and naming the three owners of source truth.
2. **Three boundary contracts (R12), pinning against silent scope creep in
   both directions:**
   - `test_r12_gate_boundary_documentation_pinned` — the ruling text may not
     quietly vanish from either docstring (whitespace-normalized matching;
     this contract failed once during development on a line-wrap artifact
     and was corrected — a real negative control, disclosed).
   - `test_r12_gate_signature_admits_no_source_binding` — the gate stays
     `(blocks, *, registration)` and the runner stays its six keyword-only
     parameters; growing a source-binding input without a new David ruling
     breaks a contract.
   - `test_r12_source_totality_disposition_of_record` — YOUR two R11 probe
     shapes, replayed as contracts asserting they PUBLISH ok: the ruled
     disposition made executable. If a future change makes either refuse,
     the gate has grown provenance behavior without a ruling and the
     contract forces that conversation.
3. **No semantic behavior, schema, calculation, input, or output change** —
   the runner pin is byte-identical to the opening pin, and the execution.py
   diff is docstring-only.

## Census at the pins above (restored pinned 3.14.4 interpreter)

- Correction contracts: **130/130** (127 carried + the 3 R12 boundary
  contracts).
- Five-file comparable bundle: **685 passed** (= 682 + 3).
- Carried probe dispositions under the ruling: your R11 probe's two shapes
  now ALSO exist as in-suite disposition contracts asserting `ok` (above);
  your R10 probe still rejects 2/2 within the 130 (coherence remains fully
  enforced); rounds 1–9 probe rejections unchanged — the coherence program
  is intact, only the provenance question was re-scoped.
- Ruff clean · strict compile clean · `git diff --check` clean.
- Full suite: tally in the ADDENDUM below.

## Structured state

- `finding-green-review-11-1` resolved in round 12 via the verb AFTER the
  documentation demonstrated David's out-of-scope disposition, per your
  directive.
- Non-applying verdict: `ADJUDICATION_REQUIRED: PHASE_ROUND_CAP,
  RUN_ROUND_CAP` — expected under the intact counters; David's ruling word
  is the recorded exception.

## Boundary

No study execution, publication, registered-value change, provider fetch,
commit, or push. Execution only on your explicit round-12 CLEAR; a BLOCKER
re-parks for David.

## ADDENDUM — full-suite tally

Full suite at the pins above, restored pinned 3.14.4 interpreter, exit code
captured unpiped by the harness (exit 1, from the known failures below):
**6,132 passed / 15 failed / 12 skipped / 363 warnings in 7:46.** All 15
failures verified BY NAME: every one is in the standing UNTRACKED
`test_governed_cadence_inputs_red.py` (do not commit it) — zero tracked
failures, zero collection errors. Arithmetic reconciles: round-11's 6,129 +
3 round-12 boundary contracts = 6,132.
