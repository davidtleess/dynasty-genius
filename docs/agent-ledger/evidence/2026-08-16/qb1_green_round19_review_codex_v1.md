# QB-1 green-review Round 19 — Codex v1

Date: 2026-08-16 (America/New_York)  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Round: 19, revision 120  
Verdict: **CLEAR / READY_FOR_GATE**

## Review result

No blocking correctness, safety, scope, or evidence finding remains at the
submitted pins. Round 19 implements the authorized metric-free
failure-origin observability seam without widening the failed terminal
artifact, disclosing raw failure content, or changing successful publication.

This verdict releases exactly the one fresh registered rerun already granted
by the revision-120 authorization. It does not itself execute the runner,
publish a result, commit, push, or rule on any registered comparison.

## Scope and final pins

The full review diff is confined to the three authorized files:

- `src/dynasty_genius/eval/qb_validation/execution.py` —
  `3fd4144c75544e0941a913ec93c1e6d428de409742e591afd7bbe32f209ba2ab`
- `scripts/run_qb1_study.py` —
  `898e50429fc4930ee813ce63a79126b9c2413891aba4ff2a5e3edc5edddbe790`
- `tests/contract/test_qb1_green_correction_contracts.py` —
  `26c1766c4d279ad8ce6cdb8031900116719e97a102276e58cd4b775ad7d0f938`

The submitted churn is 407 lines: execution `+67/-2`, CLI `+23/-22`, and
contracts `+293/-0`. The existing failed registered artifact remains unchanged
at `80d060195858da20dfa3b56a35bb6db929e60a46b1e7f53bc15500da8b9c4e62`.
No registered runner or composition was invoked during review.

## Correctness and boundary review

- The optional observer is keyword-only and defaults to `None`; the existing
  observer-less callable surface remains compatible.
- Both named-failure catches write the exact six-key metric-free terminal
  envelope before invoking the observer. Their only phase values are
  `execute` and `publication_gate`.
- The diagnostic is a closed mapping of `phase` plus ordered `sites`; every
  site contains only repository-relative `path`, code-object `function`, and
  positive integer `line`. Absolute, traversal, `.venv`, and out-of-repository
  frames are omitted.
- Neither `failure.detail`, rejected payload values, exception messages,
  source expressions, arguments, locals, comparison values, nor a
  content-derived digest enters the observer payload, stdout, terminal report,
  or a sidecar.
- The ordinary-`Exception` path remains `execution_error` with no diagnostic.
  `KeyboardInterrupt`/`SystemExit` semantics remain process-control semantics;
  an observer-raised `SystemExit` propagates only after the terminal envelope
  has been atomically written.
- The CLI persists the diagnostic only in failed stdout as `failure_origin`.
  Successful stdout retains exactly the established four keys. The observer
  is not threaded into report assembly, validation, or artifact writing.
- Observer absence, non-callability, mutation, re-entrancy, and ordinary
  observer exceptions cannot suppress or corrupt the already-written artifact.

## Independent verification

- Focused correction contract:
  `.venv/bin/python3.14 -m pytest -q tests/contract/test_qb1_green_correction_contracts.py`
  — **166 passed**.
- Five-file QB-1 regression bundle (execution, correction, reinforcement,
  inference, program) — **721 passed**.
- Scoped Ruff, strict `py_compile`, and `git diff --check` — **clean**.
- Claude adversarial probe
  `qb1_r19_observer_adversarial_probe_claude_v1.py`
  (`d40f7d9b4d8f50ece520fb5d7cd6d3e008a39b4ff93ada54a5afa3189c00eef0`)
  — **5/5 passed**.
- Independent Codex probe
  `qb1_round19_observability_review_probe_codex_v1.py`
  (`d804b47cbbd28590d8ab2e8ab9befcc790bbcb00e9a184abedbe374454933069`)
  — **5/5 passed**: artifact-before-observer ordering, publication-gate
  phase/non-disclosure, generic-exception silence, external-frame omission,
  and process-control propagation after publication.
- Claude's submitted full-suite census is **6,168 passed / 15 standing
  untracked cadence RED failures / 12 skipped**; the 15 failures are disclosed
  as the pre-existing `test_governed_cadence_inputs_red.py` set, with no
  tracked regression.

## Real-surface and governance disposition

The required real-surface proof for this implementation is the CLI-level
synthetic exercise of both catch phases, not a registered composition. Both
paths passed, including sentinel non-disclosure and the exact unchanged
success surface. The frozen registration, input machinery, and current failed
artifact were not mutated.

Layer served: Layer 3 publication/failure observability. The Layer-1/2
dependency check remained pinned and untouched; nothing in this round grants
authority to change ingestion, identity, curation, registered values, or the
study design.

H2 QB rushing remains **UNDER TEST with no result**. Any completed registered
readout must go untouched to David for his separate ruling.
