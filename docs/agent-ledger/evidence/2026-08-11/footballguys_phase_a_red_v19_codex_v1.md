# Footballguys Phase A RED v19 — migration closure

**Date:** 2026-08-11  
**Layer:** Layer 1 — ingest/persistence  
**Authority:** David: “work freely with claude until this is production grade”; implementing lane
accepted all four GREEN v18 findings and requested Codex RED v19.  
**RED:** `tests/contract/test_footballguys_phase_a_red.py`  
**SHA-256:** `ad6712a79a5c975b951423abfd2456680e6d4d8794e51344c810e4a4239ad046`  
**Size:** 6,306 lines / 241,867 bytes  
**Baseline GREEN:** `cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb`

## Prospective census

Strict command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q -W error --tb=no \
  tests/contract/test_footballguys_phase_a_red.py
```

Result: **563 collected = 46 failed + 517 passed, exit 1**.

- All 505 inherited v18 cases pass.
- V19 slice: **58 cases = 46 prospective failures + 12 positive migration anchors**.
- Ruff clean, strict Python 3.14 compile clean, diff check clean.
- No skip/skipif/xfail calls or decorators.

## Bound contracts

1. **Supported migration matrix:** exact acquisitions v1/v2/v3 × attempts v1/v2 × both active
   retention stores produces one canonical current store and passes the same full validation on
   immediate reopen. Twelve anchors are already green.
2. **Exact legacy grammars:** hidden CHECK and wrong physical order refuse for every acquisition
   version; hidden attempts CHECK refuses for both attempt versions and both stores.
3. **Closed legacy object inventory:** a surplus trigger or table refuses before rebuild for every
   acquisition version and both stores. Rebuild may not erase the evidence that should make the
   store ungoverned.
4. **Exact marker identity:** marker-only means exactly
   `(bootstrap-marker, _bootstrap, marker)`. A NULL-offering row, reserved offering with wrong row
   id, or correct reserved ids with wrong kind is populated/unreconcilable. SQL three-valued logic
   cannot establish emptiness.
5. **Non-mutating prevalidation:** malformed current receipts/observations in DELETE mode are
   fingerprinted before initialization; refusal must leave main/WAL bytes and WAL absence intact.
6. **Migration postcondition:** legacy acquisitions plus current attempts carrying a hidden CHECK
   must refuse before staging and before central allocation. The oracle asserts named domain error,
   zero events, zero objects, and no staging trace.
7. **Bidirectional transition:** current acquisitions plus exact legacy attempts must migrate; the
   already-current acquisition branch may not prematurely apply the final postcondition.
8. **AUTOINCREMENT state:** row-empty attempts with `sqlite_sequence=41` must retain 41 across v1
   or v2 migration; the next insert must receive 42.

## Adequacy notes

- The RED binds the transition states that passed v18's already-current fixtures.
- Every refusal family includes a broken implementation with a reproduced prospective failure.
- The positive migration matrix prevents “fixing” the defects by refusing all legacy stores.
- The sequence test reads the durable high-water row and then observes operational allocation;
  table grammar alone cannot pass it.
- Dynamic identifier injection is not alleged: exact supported column-name membership closes that
  narrow concern. The RED targets the false eligibility predicates around the rebuild.

## State

RED only. No GREEN authored by Codex; no commit, push, provider contact, capture, scheduler, or
Phase B/C/D. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
