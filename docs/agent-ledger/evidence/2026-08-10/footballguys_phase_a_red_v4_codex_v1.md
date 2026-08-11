# Footballguys Phase A RED v4 — Codex authorship record

**Date:** 2026-08-10  
**File:** `tests/contract/test_footballguys_phase_a_red.py`  
**SHA-256:** `45d7e6f4cd865d55ed024c1829dbd0c0f9f1b6ab77cfa3b1554a94493ce7966e`  
**Size:** 2,038 lines / 81,487 bytes  
**Supersedes:** RED v3 `3b5383380c2bdbe0d9f0d85da10704bed721f7033f0a0f2a67b8c6331eeaa565`  
**Baseline GREEN:** committed pin `8bf15189372ba29f83a62b09af3ece2e77813547` / module
`c5d87c6283ce8a9513362e1d98cd7dc7f72e79d42678122525ac2f24e45fc4aa`  

## Authority and scope

Claude accepted all nine findings from the adversarial review of `8bf1518`, zero contested, and
requested Codex-authored RED v4 before the next GREEN repair. This artifact changes the executable
contract only. It does not implement GREEN, migrate a real store, write provider bytes, contact a
provider, install a scheduler, open Phase B/C/D, commit, or push.

## RED v4 additions

1. **Legacy-store migration and fail-closed ordering**

   - Recreates the exact acquisition schema left on this machine by the first landed GREEN.
   - Requires a versioned migration that adds `source`/`role_records`, creates `attempts`, commits a
     receipt, preserves one canonical object, and converges after a fresh composition root.
   - Requires an unmigratable schema to refuse with a named error before staging or publication.

2. **Governed semantic evidence and adjudication**

   - Pins a content-addressed `semantic_evidence_objects(evidence_sha256, evidence_blob)` table
     inside the already ignored and manifest-covered `semantics.db`.
   - Requires durable evidence bytes, rehash on use, a provider-authentic provenance allowlist,
     horizon-claim allowlist, append-only evidence identity, and conflict on identity reuse with
     different bytes.
   - Requires durable `semantic_adjudications` plus
     `write_semantic_adjudication(record)` using explicit authority/provenance/parents/effective
     assertion.
   - Corrupting the retained evidence BLOB must yield `active_evidence_unverifiable`, never a known
     horizon.

3. **Derived readiness in both directions**

   - A receipt retained before evidence must become analysis-ready on a fresh load after effective
     provider-authentic evidence arrives, without changing receipt identity.
   - A formerly ready receipt must lose AR eligibility (but keep its acquisition identity and
     freshness clock) when retained evidence later fails its digest.

4. **Durable attempt ordering**

   - Four black-box sequences bind failure-before-success and success-before-failure at both
     distinct and equal instants.
   - Equal instants are resolved by the shared durable sequence: only a failure recorded after the
     successful acquisition gets the `newest attempted drop failed intake` suffix.

5. **Literal special-state composition**

   - Production-path fixture: older ready receipt, newer corrupt receipt, then newer failed intake.
   - Requires the integrity state to hold the older clock and AR identity, disclose the dated
     `analysis uses` clause, and append the newer-failure suffix.

6. **Named identity-sidecar columns**

   - Refuses `id,foo,bar` and `id,name,team`.
   - Accepts both pinned identity shapes: `id,name,pos` and the real product's
     `id,first,last,pos`.

7. **Published mode and provenance**

   - Requires canonical objects at `0444` while retaining downstream rehash as the authoritative
     integrity boundary.
   - Refuses the superseded original RED pin in the production module header.

8. **Strict warning gate repaired**

   - Replaces all four `with sqlite3.connect(...)` fixtures with `contextlib.closing(...)`.
   - The exact `-W error` command now exits only for the intended RED assertions; there is no
     teardown `ResourceWarning`/`ExceptionGroup`.

## Failing census against `8bf1518`

Command:

` .venv/bin/python3.14 -m pytest -q --tb=no -W error tests/contract/test_footballguys_phase_a_red.py `

Result: **222 collected = 17 failed + 205 passed**, process exit **1**.

Failure mapping:

- stale production pin: 1;
- wrong sidecar columns: 2;
- semantic evidence/adjudication/provenance/claims/identity/rehash: 6;
- legacy migration and pre-staging refusal: 2;
- late-evidence promotion and evidence-loss demotion: 2;
- success-then-failure ordering (distinct and equal instants): 2;
- held-AR plus stage-2 special composition: 1;
- canonical `0444`: 1.

The two failure-before-success attempt-order cases and both accepted sidecar aliases pass, serving
as positive/negative controls around the new predicates.

## Quality and anti-shadow checks

- `py_compile` — pass;
- Ruff on the RED file — pass;
- `git diff --check` on the RED file — pass;
- no `skip`, `skipif`, or `xfail` — zero occurrences;
- all six independent known-answer hashes remain present exactly once;
- the four SQLite connection leaks are closed; strict warnings no longer create a second failure
  channel;
- failures execute real archive parsing, actual SQLite schemas/BLOB corruption, fresh composition
  roots, real object modes, and production read-model composition—not injected result labels.

## Gate

RED v4 and its future GREEN repair must travel in one reviewed act. `8bf1518` remains unpushed and
must not run a first capture. No provider contact, scheduler, or Phase B/C/D work opens. H2 QB
rushing remains **UNDER TEST** with no result and is unrelated.
