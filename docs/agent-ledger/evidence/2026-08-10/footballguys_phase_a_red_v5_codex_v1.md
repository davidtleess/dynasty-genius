# Footballguys Phase A RED v5 — Codex v1

**Date:** 2026-08-10  
**Authority:** Claude accepted all seven findings from the adversarial review of `8a99bd9`
and explicitly requested Codex-authored RED v5.  
**Reviewed GREEN (unchanged):**
`src/dynasty_genius/sources/footballguys_intake.py` —
`aaecb2d8c5f80b8f9713199c2adf625d4011af072c988b9e109bf8a3dd216ec7`  
**RED v5:** `tests/contract/test_footballguys_phase_a_red.py` —
`9b3d5e87f62c3661d0a8dbc834ec49108dba01b6cb59c7e25e8a2d824c4faac6`  
**Size:** 2,479 lines / 96,688 bytes  
**Layer:** 1, intake/persistence

## Outcome

RED v5 binds the seven accepted real-boundary defects without touching GREEN.  The strict run
against the committed `8a99bd9` GREEN collects 249 cases and produces the intended RED:

```text
25 failed, 224 passed in 7.46s
process exit 1
```

The 224 passing cases are all 222 RED v4 contracts plus two v5 positive controls.  There are no
skip, xfail, or skipif markers.  Ruff, Python 3.14 compilation under `-W error`, and
`git diff --check` pass.

## New failing census

| Boundary | Failing cases | Production oracle |
|---|---:|---|
| C1 adjudication relation | 3 | public cross-key writer refusal; restored cross-key reducer fail-closed; intake cannot publish-without-receipt when the restored adjudication is invalid |
| C2 load-side semantic governance | 5 | restored attachment provenance, assertion claim, adjudication authority, adjudication provenance, and unsupported-claim readiness promotion |
| H3 closed semantic writer/read schema | 10 | assertion noop attachment equality (bytes/time), reused evidence metadata equality, three invalid retrieval instants, three non-integer versions, and restored mixed-version read safety |
| H4 store classification | 2 | non-SQLite primary ledger and non-SQLite counterpart with a valid sibling both render literal framing row 9 |
| H5 single newest attempt | 2 | failed→invalid and invalid→failed histories each render exactly one suffix from the final event |
| H6 global cross-store order | 1 | equal-instant receipt→observation-failure transition must show the later failure |
| H7 inactive-store read-only boundary | 2 | both retention directions preserve inactive legacy main/WAL byte fingerprints |
| **Total** | **25** | |

## Positive controls

1. Two evidence retrieval spellings of the same instant (`-04:00` and `Z`) share the canonical
   attachment identity and allow a new assertion with otherwise identical attachment facts.
2. At one fixed instant, observation-failure→receipt is the inverse cross-store transition: the
   later successful acquisition correctly suppresses the older failure suffix.

These controls prevent repairs that merely refuse all semantic writes or render every equal-time
transition as failed.

## Framing-to-test binding

- C1 validates the adjudication relation twice: at the public writer and independently over
  persisted/restored rows.  The downstream intake test binds the no-orphan lifecycle consequence.
- C2 corrupts persisted SQLite rows after valid public writes.  It therefore tests restore/load
  governance, not the already-green writer allowlists.
- H3 challenges both idempotency branches before `noop`, canonical acquisition-evidence time,
  exact integer typing (including Python/JSON boolean separation), and a restored wrong-type row.
- H4 writes actual non-SQLite bytes to governed store paths and enters through `read_model()`;
  it does not inject the pure evaluator's `ledger_unreadable` label.
- H5 creates one successful acquisition and two later durable attempts through `intake()`, in
  both orders, so the reducer must rank first and project one suffix.
- H6 crosses the receipts/observations databases at one fixed clock instant through public mode
  transitions; a per-database sequence cannot pass both directions.
- H7 fingerprints inactive main/WAL bytes around public intake in both active modes.  SHM is not
  part of the frozen fingerprint, preserving the already-framed permitted read-side residue.

## Checks

- `.venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`
  — **25 failed / 224 passed, exit 1** (the intended RED);
- `.venv/bin/ruff check tests/contract/test_footballguys_phase_a_red.py` — pass;
- `.venv/bin/python3.14 -W error -m py_compile tests/contract/test_footballguys_phase_a_red.py`
  — pass;
- `git diff --check -- tests/contract/test_footballguys_phase_a_red.py` — pass;
- forbidden skip/xfail marker search — zero;
- pre-RED-v5 pinned baseline: strict RED v4 **222/222, exit 0**; Ruff clean; full tracked suite
  **5,455 passed / 12 skipped / 9 xfailed**;
- GREEN SHA-256 rechecked after RED authorship and remains exactly `aaecb2d8...216ec7`.

## State and next gate

RED v5 is uncommitted.  Claude implements GREEN against this exact pin; RED and GREEN travel
together only on David's later landing word.  `8a99bd9` remains unpushed.  No first capture,
provider contact, scheduler, or Phase B/C/D work opens from RED authorship.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
