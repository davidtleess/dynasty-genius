# Footballguys Phase A GREEN v16 adversarial review — NOT CLEAR

**Reviewed pin:** `1e5492b9bb540a45be4fe451000d9d72af0a3130`  
**Date:** 2026-08-11  
**Layer:** Layer 1 — ingest/persistence  
**Verdict:** **NOT CLEAR — 2 HIGH, 1 MEDIUM**

## 1. Post-commit divergence audit

The commit has exactly the declared three-file scope:

| File | Delta | SHA-256 at the pin |
|---|---:|---|
| `docs/agent-ledger/2026-08-11.md` | +56/-0 | record-only |
| `src/dynasty_genius/sources/footballguys_intake.py` | +134/-0 | `63c31c1870b674ec0212fc301a2f995d909051b54c8ecac5430adf457ea4e1bb` |
| `tests/contract/test_footballguys_phase_a_red.py` | +226/-1 | `0c4199a888240850496283e90ea4d3b2b308fc6a4d5a60d20e31142c7b688e6d` |

Parent: `7b490f337bd66044836f481bd019f99eaf7a52e6`.

Ambient HEAD advanced after the landing, but `git diff 1e5492b..HEAD` is empty for both
reviewed code paths. The working-tree blobs reproduce the pin hashes exactly.

## 2. Contract-conformance checks

- Strict RED command:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`
  → **446 passed, exit 0**.
- Full tracked suite, with only the standing untracked cadence RED excluded:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q --tb=no tests --ignore=tests/contract/test_governed_cadence_inputs_red.py`
  → **5,679 passed / 12 skipped / 9 xfailed, exit 0**.
- `.venv/bin/ruff check src app` → clean.
- Strict `py_compile` over RED and GREEN → exit 0.
- One deliberately over-strengthened whole-suite run with `-W error` exited during collection on
  20 pre-existing scikit-learn artifact-version warnings. It is not the published full-suite gate;
  it is recorded rather than misreported as a product regression.

## 3. Falsification matrix

| Input class | Probe/result |
|---|---|
| Valid nominal | Canonical v16 marker and index controls pass. |
| Boundary / legacy | Inherited `i12` exact v1 legacy marker remains accepted and writes governed semantic evidence. |
| Missing / malformed | All seven v16 marker negatives now refuse with the named error. |
| Duplicate / surplus | All four surplus-autoindex v16 controls now refuse. |
| Wrong physical signature | A table-level `UNIQUE(assertion_id)` substituted for the required primary key is accepted; finding 2. |
| Hidden table constraint | Four non-event semantic tables accept load-bearing `CHECK` constraints; finding 1. |
| Table suffix / alternate physical shape | `STRICT` and `WITHOUT ROWID` marker tables are accepted; finding 3. |
| Null/wrong runtime scalar | Inherited writer/load scalar controls remain green; no new divergence found in this review. |
| Empty collection | Existing bare-ledger and empty-store controls remain green; no new divergence found. |
| Cross-component | Semantic assertion/attachment/object/adjudication consequences were exercised through the real writer, not only schema inspection. |
| Numeric edge | Existing signed-64 semantic-version controls remain green; the new assertion `CHECK(version > 100)` defeats a legal version and exposes the unvalidated DDL. |
| Synthetic/override | All new mutations used disposable roots with the production composition root and real SQLite stores. |

## 4. Findings

### 1. HIGH — four governed semantic tables still have open DDL grammars

`_validate_semantics_schema` checks only an unordered column-name set and index predicates for
`semantic_assertions`, `semantic_attachments`, `semantic_evidence_objects`, and
`semantic_adjudications` (`footballguys_intake.py:1643-1664`). Only `event_sequence` receives a
closed table grammar (`:1665-1694`); the marker gets its separate parser later.

Fresh stores were rebuilt with canonical columns and indexes plus one load-bearing `CHECK`:

```text
semantic_assertions CHECK(version > 100)
  initialization: ACCEPTED
  first writer: sqlite3.IntegrityError

semantic_attachments CHECK(evidence_bytes < 0)
  initialization: ACCEPTED
  first writer: sqlite3.IntegrityError

semantic_evidence_objects CHECK(length(evidence_blob) < 0)
  initialization: ACCEPTED
  writer result: {'status': 'written'}
  effective state: unknown / active_evidence_unverifiable

semantic_adjudications CHECK(authority = 'nobody')
  initialization: ACCEPTED
  first adjudication: sqlite3.IntegrityError
```

The evidence-object branch is especially important: `INSERT OR IGNORE` turns the hidden schema
constraint into a false `written` acknowledgement while the required bytes do not exist. This is
the event-table whole-grammar defect from rounds 13–14 surviving in four sibling tables.

**Required next RED:** exact complete table grammar for all four tables, with one operational
constraint mutant per writer branch. Each must refuse during non-mutating prevalidation, preserving
main/WAL bytes and all application rows. The evidence-object control must assert that broken code's
false `written` response fails the oracle.

### 2. HIGH — “exact index signatures” discard origin, collation, and ordering

At `footballguys_intake.py:1463-1476`, `PRAGMA index_list` exposes `origin` but the implementation
binds it to `_origin` and discards it. `PRAGMA index_info` retains only column identity/order; it
does not close collation or descending-key state available through `index_xinfo`.

Two fresh mutations passed initialization:

```text
assertion_id TEXT UNIQUE                -> origin='u' accepted instead of required origin='pk'
assertion_id TEXT PRIMARY KEY COLLATE NOCASE
  index_xinfo collation='NOCASE'        -> accepted
  'Case-ID' then 'case-id'              -> assertion_identity_conflict
```

The second store changes case-sensitive identity semantics while satisfying the alleged exact
signature. This is not a cosmetic DDL difference: two application-distinct IDs collapse.

**Required next RED:** signature equality must bind, per index and in stable key order, uniqueness,
origin (`pk` vs `u`), partial/expression status, key/non-key membership, direction, collation, and
exact column sequence. Include PK→table-UNIQUE substitution and `COLLATE NOCASE` mutants. A test
that checks only count+column names must fail.

### 3. MEDIUM — marker grammar ignores every token after the closing parenthesis

`_parsed_table_segments` locates the matching close parenthesis, parses only the interior, and
returns immediately (`footballguys_intake.py:1403-1431`). It never validates the remaining DDL.
Both of these were accepted:

```text
CREATE TABLE acquisitions (...) STRICT
CREATE TABLE acquisitions (...) WITHOUT ROWID
```

The landing note says exactly two marker shapes are governed: canonical and exact legacy v1.
The implementation accepts at least four physical shapes and changes SQLite type/rowid semantics.

**Required next RED:** reject every non-comment, non-whitespace table-option token after the
matching close parenthesis. Include `STRICT` and `WITHOUT ROWID` negatives for canonical and legacy
grammars, plus the two exact positives. The parser must consume the whole DDL, not only find a valid
interior substring.

## 5. Constitutional and architectural alignment

- Market data remains outside Engine A/B; no model or comparison path changed.
- The source adapter stays fail-closed in the covered RED cases, but findings 1–3 show the schema
  contract is not yet fail-closed over restored/altered SQLite state.
- No provider contact, capture, scheduler, surface, or downstream phase was opened.
- QB rushing H2 remains **UNDER TEST** with no result and is unrelated.

## 6. Disposition

Commit `1e5492b` remains **NOT CLEAR** and unpushed. No first Footballguys capture should run
against this pin. On implementing-lane acceptance, Codex should author RED v17 binding all three
families; RED and repaired GREEN travel together only on David's word.
