# Footballguys Phase A RED v16 — exact index inventory and marker grammar

**Authored:** 2026-08-11 20:45 EDT  
**Layer:** Layer 1 — governed source intake  
**Status:** RED authored; GREEN unchanged; nothing committed or pushed by this act

## Pins

- RED: `tests/contract/test_footballguys_phase_a_red.py`
  - SHA-256: `0c4199a888240850496283e90ea4d3b2b308fc6a4d5a60d20e31142c7b688e6d`
  - size: 5,052 lines / 196,973 bytes
- Unmodified GREEN: `src/dynasty_genius/sources/footballguys_intake.py`
  - SHA-256: `7dc64bf502b2a260ea3c4c050ad93b6fd5bf45c50f67720114dadfffdf0d4103`

## Binding controls

### H1 — exact index signatures

The RED requires the index set to equal the governed signatures, including
SQLite-created autoindexes. It adds one surplus table-level `UNIQUE` constraint
to each of the four semantic tables whose grammar is not independently closed:

1. `semantic_assertions`: surplus `UNIQUE(claim)`;
2. `semantic_attachments`: surplus `UNIQUE(provenance)`;
3. `semantic_evidence_objects`: surplus `UNIQUE(evidence_blob)`;
4. `semantic_adjudications`: surplus `UNIQUE(authority)`.

Each creates a SQLite autoindex with an allowed-looking `sqlite_autoindex_*`
name. Each must refuse `store_schema_unmigratable:semantics`. The pre-existing
v14/v15 controls already close `event_sequence` grammar and reject its surplus
unique/non-unique indexes. H2 below closes the marker table.

### H2 — exact `acquisitions` marker grammar

The only accepted marker schema is the ordered grammar:

`row_id TEXT PRIMARY KEY, offering_id TEXT UNIQUE, kind TEXT`

The negative matrix covers:

1. missing `kind`;
2. an extra column;
3. wrong column order;
4. missing `row_id` primary key;
5. missing `offering_id` uniqueness;
6. surplus `UNIQUE(kind)` / autoindex;
7. a `NOT NULL` suffix on `kind`.

Every negative must refuse in non-mutating initialization with the exact named
error. The canonical marker schema is a positive control.

## Non-vacuity

- Both families seed a real semantic assertion before schema mutation.
- H1 rebuilds the target table and copies any governed rows before testing.
- H2 inserts a real marker row into every schema variant.
- Every negative compares the main/WAL size and SHA-256 fingerprint before and
  after refusal.
- Every case, including positives, compares all application-table rows before
  and after initialization.
- No skip, xfail, or skipif occurs in the RED artifact.

## Strict failing census

Command, run twice:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Both runs produced the same result and process status:

```text
446 collected = 11 failed + 435 passed
exit 1
```

Failure partition:

- H1: 4 failures — the four surplus SQLite autoindexes listed above.
- H2: 7 failures — every malformed marker grammar listed above.
- Both new canonical controls pass.

## Static checks

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m py_compile tests/contract/test_footballguys_phase_a_red.py` — exit 0.
- `.venv/bin/ruff check tests/contract/test_footballguys_phase_a_red.py` — clean.
- `git diff --check` — clean.

## Scope

This act authors RED v16 only. It does not modify GREEN, commit, push, capture
provider data, contact a provider, install a scheduler, or open Phase B/C/D.
QB rushing H2 remains **UNDER TEST** with no result and is unrelated.
