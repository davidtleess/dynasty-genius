# Footballguys Phase A GREEN v18 — adversarial review

**Date:** 2026-08-11  
**Layer:** Layer 1 — ingest/persistence  
**Verdict:** **NOT CLEAR / BLOCKED** — 1 Critical, 2 High, 1 Medium  
**Reviewed GREEN:** `cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb`  
**Pinned RED:** `677b5fe9bbcda0a6734feff75c8fadd6ff8a03985219477254ccbdc9aca93de4`

## 1. Provenance and scope

The implementing lane established that this GREEN was written unsupervised by a re-adopted
background worker after its parent Claude Code session crashed during an upgrade. The worker is
now stopped and quarantined. Codex did not author the GREEN. That provenance raises the need for
independent inspection but does not itself decide correctness; the findings below are reproduced
against the settled bytes.

`HEAD` remained `87362f12f451eafa83aa52deadc6db7a806fc32a`. That commit contains only a
60-line ledger addition even though its subject claims GREEN completion. The RED and GREEN are
uncommitted. The working GREEN is `+98/-6` against the HEAD baseline
`11667534393fa600e6f707e5a1e24b5527723121c3583d005008c36bf366ac7d`; the RED is
`+424/-1` against HEAD. Other dirty-tree work was preserved and is outside this review.

The two reviewed pins and their mtimes remained unchanged before and after the review.

## 2. Reproduced gates

- Strict RED: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q -W error
  --tb=no tests/contract/test_footballguys_phase_a_red.py` → **505 passed, exit 0**.
- Tracked suite, excluding only the standing untracked cadence RED:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q --tb=no
  --ignore=tests/contract/test_governed_cadence_inputs_red.py` → **5,738 passed / 12 skipped /
  9 xfailed, exit 0**.
- `uvx ruff check` on RED and GREEN → clean.
- Python 3.14 strict compilation under `-W error` → clean.
- Diff check → clean.
- Disposable-root adversarial module: **6 failed / 0 passed**. Every failure below expresses a
  contract property not covered by RED v18; none modifies repository product code or runtime
  stores.

Contract-green therefore reproduces, but it is not sufficient.

## 3. Findings

### 1. CRITICAL — a legacy/current transition bypasses the full-store validator and can orphan the central event

`_validate_acquisition_current_schema()` validates both `acquisitions` and `attempts`, but it is
called only when `acquisitions` is already v4 (`footballguys_intake.py:1645-1646`). When
`acquisitions` is a marker-only v1 store and `attempts` is already current, the acquisition table
is rebuilt and the current attempts table is accepted by its unordered column set alone. There is
no unconditional validation of the canonical post-migration store.

Probe: exact legacy acquisitions + current attempts carrying
`CHECK(status = 'never')`, followed by a malformed intake. Observed:

- raw `sqlite3.IntegrityError`, not the named domain refusal;
- **1 central event committed**;
- 0 matching attempt rows;
- no pre-staging `store_schema_unmigratable:receipts` refusal.

This recreates the orphan-event failure the v18 repair was meant to close, on a migration state
instead of an already-current state. Validation must be a postcondition of every migration path,
not a conditional precheck of one version branch.

### 2. HIGH — malformed acquisition-store refusal is physically mutating in DELETE mode

Only `semantics` receives non-mutating read prevalidation before a write-capable SQLite connection
(`footballguys_intake.py:1886-1901`). Receipts and observations first execute
`PRAGMA journal_mode=WAL` (`1902-1906`) and only then validate their schema (`1923-1924`).

Probe: a current receipts store in DELETE mode with the hidden acquisition CHECK from RED v18.
Initialization returned the correct named schema refusal, but the 36,864-byte main database hash
changed from `85abad6a…` to `8b988de4…` before refusal. RED v18 fingerprints a database already in
WAL mode, so it tests the promise's shadow and misses this write.

Receipts and observations need the same read-only classification/validation boundary as semantics
before any journal-mode or migration write.

### 3. HIGH — legacy migration eligibility is neither exact-shape nor truly row-empty

Legacy acquisitions are classified by an unordered `PRAGMA table_info` name set
(`1634-1647`), and “row-empty” is implemented as
`WHERE offering_id != '_bootstrap'` (`1653-1656`). Three independent probes passed broken states:

1. a real legacy row with `offering_id = NULL` was not counted under SQL three-valued logic;
   `initialize_database("receipts")` succeeded and migrated the populated store;
2. a legacy table with the same names but hidden `CHECK(archive_bytes < 0)` was accepted and the
   rebuild silently removed the constraint;
3. the same legacy columns in a non-historical physical order were accepted and canonicalized.

The dynamic SQL at `1661-1677` is not itself injectable: reaching it requires an exact fixed
column-name set, so `sorted(columns)` can contain only governed identifiers. The defect is the
eligibility predicate around it. “Exact known shape” requires an exact legacy grammar and closed
object inventory, and marker-only requires the exact governed marker row—not one nullable
comparison.

### 4. MEDIUM — rebuilding an empty attempts table resets the AUTOINCREMENT high-water mark

The attempts guard proves `COUNT(*) == 0`, then drops and recreates the table (`1698-1710`). It
does not preserve `sqlite_sequence`. Probe: exact legacy attempts, insert sequence 41, delete the
row, verify `sqlite_sequence=41`, then migrate. The next insert received **1**, not 42.

The table is row-empty, but the durable AUTOINCREMENT state is not empty. Since the contract now
binds the AUTOINCREMENT grammar, migration must either preserve the high-water mark or explicitly
define a governed series break and prove no consumer treats local attempt sequence as persistent
order. Silent reuse is not equivalent to the declared schema behavior.

## 4. Rulings on the implementing lane's four questions

1. **Dynamic identifiers:** no injection path found; the exact fixed column-name set closes that
   narrow risk. The migration eligibility guard is nevertheless false for `NULL`/non-exact
   legacy states.
2. **Set versus order:** current v4 wrong-order tables are rejected by the DDL grammar; legacy
   wrong-order tables slip the unordered version classifier and are silently canonicalized.
3. **Attempts empty-only:** row emptiness is proven with `COUNT(*)`, but schema exactness and
   sequence state are not. A malformed empty attempts table can be dropped, and prior high-water
   state is erased.
4. **AUTOINCREMENT:** not preserved; 41 became 1.

## 5. Required next boundary

GREEN v18 is **not clear** and must not land or capture provider bytes. A prospective RED v19
should bind, at minimum:

- exact legacy grammars and object inventories for every supported acquisition/attempt version;
- exact marker-only row identity, including `NULL` and reserved-id mutants;
- non-mutating acquisition-store prevalidation before journal-mode writes;
- unconditional full current-store validation after every migration branch;
- the legacy-acquisitions/current-attempts hidden-CHECK orphan-event reproduction;
- attempts `sqlite_sequence` preservation, or a separately justified and tested series-break
  contract.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D is opened. H2 QB rushing
remains **UNDER TEST** with no result and is unrelated.
