From Codex (RED-authoring lane) — Phase A RED v4 authored; strict census 17F/205P

(a) RED v4 is ready:

`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `45d7e6f4cd865d55ed024c1829dbd0c0f9f1b6ab77cfa3b1554a94493ce7966e`
2,038 lines / 81,487 bytes; supersedes RED v3 `3b538338…`.

STRICT CENSUS against committed GREEN `8bf1518` / `c5d87c62…`:
`.venv/bin/python3.14 -m pytest -q --tb=no -W error tests/contract/test_footballguys_phase_a_red.py`
→ **222 collected = 17 failed + 205 passed**, process exit **1**. The four connection leaks are
fixed with `contextlib.closing`; no teardown ResourceWarning/ExceptionGroup remains. py_compile
pass · Ruff clean · diff hygiene clean · zero skip/xfail/skipif · all six independent hash vectors
remain exactly once.

NEW BOUNDARIES:
1. Exact pre-v3 acquisition schema must migrate/version before publication; one receipt/one object
and fresh-root convergence. Unmigratable schema refuses by name before staging.
2. `semantics.db` is the already ignored + manifest-covered content-addressed evidence store:
`semantic_evidence_objects(evidence_sha256,evidence_blob)` retains the bytes. Rehash on every use;
provider-authentic provenance and horizon-claim allowlists; reused evidence id + changed bytes =
conflict; corrupt blob closes the gate.
3. Durable `semantic_adjudications` plus `write_semantic_adjudication(record)` with id, key,
authority, provenance, explicit parents, effective assertion.
4. Readiness is derived both ways: later valid evidence promotes the unchanged retained receipt;
later evidence hash failure demotes AR while receipt identity/freshness remain unchanged.
5. Attempt ordering is black-box tested in four sequences: failure→success and success→failure,
at distinct and equal instants. Equal instant is resolved by shared durable sequence; only failure
after success gets the suffix.
6. Production special-state path: older ready receipt + newer corrupt receipt + newest failed
attempt must hold old clock/AR, disclose its date, and append stage-2 failure suffix.
7. Sidecar refuses `id,foo,bar` and `id,name,team`; accepts `id,name,pos` and the REAL product shape
`id,first,last,pos`.
8. Published object is `0444`, rehash still authoritative. Production docstring may not cite the
superseded `1130f2bc` pin.

Failure map: stale pin 1 · wrong sidecar 2 · semantics 6 · migrations 2 · readiness 2 · attempt
ordering 2 · special composition 1 · object mode 1 = 17. The two failure-before-success cases and
both accepted sidecar aliases are positive controls.

Durable authorship record:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_red_v4_codex_v1.md`
SHA-256 `189ddf7f51496c50f39e15db274757eda79c5d6ecfe25288b9a38951c7fa6b5c`.

RED v4 + GREEN repair travel together only on David's next landing word. `8bf1518` stays unpushed;
no first capture/provider/scheduler/Phase B/C/D. H2 QB rushing remains UNDER TEST with no result.

PLEASE REPLY with your reproduced pin/census before GREEN, then repair against this exact file.
