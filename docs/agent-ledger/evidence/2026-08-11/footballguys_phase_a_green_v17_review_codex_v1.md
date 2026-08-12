# Footballguys Phase A GREEN v17 adversarial review — NOT CLEAR

**Reviewed pin:** `82405fd4814654504172feb0ad8a8c002a34d699`  
**Date:** 2026-08-11  
**Layer:** Layer 1 — ingest/persistence  
**Verdict:** **NOT CLEAR — 1 CRITICAL, 1 MEDIUM**

## 1. Post-commit divergence audit

The commit has exactly the declared three-file scope:

| File | Delta | SHA-256 at the pin |
|---|---:|---|
| `docs/agent-ledger/2026-08-11.md` | +64/-0 | record-only |
| `src/dynasty_genius/sources/footballguys_intake.py` | reviewed code delta | `11667534393fa600e6f707e5a1e24b5527723121c3583d005008c36bf366ac7d` |
| `tests/contract/test_footballguys_phase_a_red.py` | reviewed contract delta | `00299c99798dbfd1c6bb582704b7b143fd3e70ae8bf6e45babf5d0d182ce4689` |

Overall commit delta: **589 insertions / 6 deletions**. Parent:
`996e18570697a4c56a266a119d0359da6290a38f`.

The working-tree RED and GREEN blobs reproduce the committed hashes exactly. Ambient unrelated
working-tree files were not changed by this review.

## 2. Contract-conformance checks

- Strict RED command:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`
  → **472 passed, exit 0**.
- Full tracked suite, excluding only the standing untracked cadence RED:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q --tb=no tests --ignore=tests/contract/test_governed_cadence_inputs_red.py`
  → **5,705 passed / 12 skipped / 9 xfailed, exit 0**.
- `uvx ruff check src app tests/contract/test_footballguys_phase_a_red.py` → clean.
- Strict Python 3.14 compile over RED and GREEN → exit 0.
- `git diff --check` → clean for the reviewed delta; the shared tree contains disclosed unrelated
  user/peer work which was preserved.

## 3. Falsification matrix

| Input class | Probe/result |
|---|---|
| Valid nominal | All 472 pinned RED v17 contracts pass. |
| Hidden receipt constraint | Canonical v4 acquisition columns plus `CHECK(archive_bytes < 0)` pass initialization, then produce a false-success intake; finding 1. |
| Hidden attempt constraint | Canonical v3 attempt columns plus `CHECK(status='never')` pass initialization, then leak raw SQLite failure after central-event commit; finding 1. |
| Missing durable row | False-success probe has one retained object and one central acquisition event but zero receipt rows. |
| Extra table option | Canonical `event_sequence` followed by `STRICT` passes initialization; finding 2. |
| Cross-store ordering | Both broken write branches were exercised through the real central event allocator and active receipts store. |
| Malformed provider input | A non-ZIP archive drove the real failed-attempt path, exposing the hidden attempt constraint rather than a synthetic direct insert. |
| Empty collection | Receipt-row count was asserted independently from the returned intake status; zero was not treated as success. |
| Duplicate/surplus identity | Static review confirms active acquisition-store validation closes only column-name sets, not PK/UNIQUE/index/object inventory; required RED below makes the operational identity constraints explicit. |
| Passes-broken-code defense | Each disposable probe asserts the externally required state, not merely that a parser helper was called or a column set matched. |

## 4. Findings

### 1. CRITICAL — active receipt/observation schemas are names-only, enabling false success and orphan events

`_migrate_acquisition_store` accepts the current acquisition schema solely by the unordered set of
column names (`footballguys_intake.py:1567-1593`) and does the same for attempts (`:1602-1620`).
It does not close table grammar, PK/UNIQUE/index semantics, triggers/views/surplus objects, or
load-bearing constraints for either `receipts.db` or `observations.db`.

Two production-boundary probes demonstrate different corrupt outcomes:

1. Rebuild `receipts.acquisitions` with the exact v4 columns and canonical PK/UNIQUE, adding only
   `CHECK(archive_bytes < 0)`. Initialization accepts it. A valid archive intake then returns:

   ```text
   status=review_required
   raw_retained=True
   receipt_id=<nonempty>
   attempt_recorded=True
   canonical object count=1
   central acquisition-event count=1
   durable non-bootstrap receipt-row count=0
   ```

   The cause is the unvalidated schema combined with `INSERT OR IGNORE` at lines 2495-2522: the
   CHECK violation is silently ignored, the code never verifies a row was inserted, and the
   caller reports success. This violates the framing's receipt-last invariant in its strongest
   form: retained paid bytes and a success-shaped response exist without the receipt that is meant
   to make that state representable.

2. Rebuild `receipts.attempts` with the exact v3 columns and add only
   `CHECK(status='never')`. Initialization accepts it. A malformed archive takes the real failure
   path, `_record_attempt` first commits one central attempt event, and the attempts insert then
   raises raw `sqlite3.IntegrityError`. The result is **one orphan central event**, no named
   domain refusal, and no completed attempt record.

The code change in v17 correctly closed four semantic tables, but the same storage contract never
reached the two active acquisition-store tables. Because both retention modes share this migrator,
the defect affects receipts and observations.

**Required next RED:** bind both active-store tables and both retention modes to exact known schema
lineages. For `acquisitions` and `attempts`, validate complete DDL grammar, exact physical
PK/UNIQUE/index signatures via `index_xinfo`, and the store object inventory (including triggers,
views, and surplus indexes) before staging or central-event allocation. Include:

- canonical current positives and exact governed legacy-migration positives;
- hidden CHECK and trigger mutants on each table;
- missing/substituted PK/UNIQUE and surplus-index mutants;
- the valid-archive false-success probe above, asserting zero object, zero central event, zero
  receipt row, and a named pre-staging refusal;
- the malformed-archive attempt probe above, asserting zero central event and no raw SQLite error;
- the same controls for the observations mode; and
- a terminal invariant that no success-shaped result may be returned unless exactly one matching
  durable acquisition row exists. A test that checks only column names or only initialization
  must fail.

### 2. MEDIUM — the event-table parser still ignores whole-DDL suffixes

The v17 shared `_parsed_table_segments` helper now rejects non-comment suffix tokens at lines
1418-1421. `event_sequence`, however, remains on the older separate
`_event_table_grammar_is_governed` parser (`:1291-1365`), which stops at the matching close
parenthesis and returns after comparing the six interior segments.

A real SQLite table with the exact canonical event columns and indexes followed by `STRICT`
passes `initialize_database("semantics")`. That contradicts the standing closed-whole-DDL rule and
is the same sibling-fix pattern caught repeatedly in framing: the new predicate exists, but one
governed sibling never calls it.

**Required next RED:** a canonical `event_sequence` positive plus a canonical-body-`STRICT`
negative that must refuse `store_schema_unmigratable:semantics` during non-mutating prevalidation.
The oracle must exercise `initialize_database`, not merely a helper. Consolidating event parsing
onto the shared whole-DDL parser is the simplest repair, but the RED binds behavior rather than
that mechanism.

## 5. Constitutional and architectural alignment

- This review is Layer 1 only; no market data entered Engine A/B and no comparison opened.
- Horizon and cohort gates remain failed; Phase B/C/D remain closed.
- No provider contact, first capture, scheduler, runtime-store mutation, commit, or push occurred.
- QB rushing H2 remains **UNDER TEST** with no result and is unrelated.

## 6. Disposition

Commit `82405fd` remains **NOT CLEAR** and unpushed. No first Footballguys capture should run
against this pin. On implementing-lane acceptance, Codex should author RED v18 binding findings
1-2; the RED and repaired GREEN travel together only on David's word.
