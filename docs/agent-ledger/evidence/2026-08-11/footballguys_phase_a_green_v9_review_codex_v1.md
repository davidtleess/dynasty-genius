# Footballguys Phase A GREEN v9 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `b582b1d62a2eae199e5fb6b0ad519ae2126afd8e`  
**Verdict:** **NOT CLEAR — five findings**  
**Layer:** 1 (ingest/persistence)

## 1. Pin and scope audit

The commit reproduces the declared pins exactly:

- RED `tests/contract/test_footballguys_phase_a_red.py`:
  `54eccc7326cba73d2e6d662c16b239387344dfcd0a3b1e170bc38ebaecf79332`
- GREEN `src/dynasty_genius/sources/footballguys_intake.py`:
  `0f963e7371dc3b89e97de5f6b9f09e2c6d257f7c5c88155c87d8cf27cf134933`

The commit changes exactly the declared three files—RED, GREEN, and
`docs/agent-ledger/2026-08-11.md`—with `+518/-22`. Current working-tree RED/GREEN bytes are equal
to the committed pin. The scope-divergence audit is clear.

## 2. Reproduced gates

- Cold strict RED:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`
  → **371 passed, exit 0** in 22.53s.
- Full tracked suite with the standing cadence-RED exclusion:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q --ignore=tests/contract/test_governed_cadence_inputs_red.py`
  → **5,604 passed / 12 skipped / 9 xfailed, exit 0**.
- `.venv/bin/ruff check src app` → clean.
- Cold `python -W error -m py_compile` of the GREEN module → exit 0.

The published gates are accurate. The findings below are outside RED v9 and were reproduced in
isolated temporary roots with real SQLite files.

## 3. Findings

### 1. CRITICAL — semantic load-side type closure remains weaker than the writer and can open Phase C

The repaired writer validates adjudication identity fields, but `_adjudication_is_governed()`
(`footballguys_intake.py:391-410`) only requires truthiness for `adjudication_id`. A restored BLOB
identity therefore remains governable. Separately, the assertion-load guard at lines 2626-2641
uses equality membership (`active in (0, 1)`) rather than exact integer typing, so a restored REAL
`1.0` passes and is converted to active with `bool()`.

Two concrete probes:

1. Create two valid conflicting horizon assertions and a valid David adjudication, then restore
   `adjudication_id` as BLOB `b'blob-adjudication-id'`. The reducer returned `state=known`,
   `value=dynasty_startup`, and **`eligible_for_phase_c=True`**.
2. Rebuild `semantic_assertions` with the exact columns and valid `assertion_id` primary key but
   REAL `active=1.0`. Schema validation returned `wal`; the reducer returned `state=known`,
   `value=redraft`, and **`eligible_for_phase_c=True`**.

Required boundary: every writer scalar predicate must be mirrored exactly on load. In particular,
adjudication identity/key/effective-id must be nonempty TEXT, and assertion `active` must be an
exact SQLite integer 0/1—not an equality-compatible REAL. Invalid persisted rows must produce a
named fail-closed semantic state before adjudication/reducer projection.

### 2. HIGH — the event ordering key can lose its primary-key invariant and hide a failed intake

The new schema validator proves `event_id` uniqueness but `_SEMANTIC_IDENTITY` and
`_has_exact_unique_index()` (`footballguys_intake.py:1279-1302`) do not prove the load-bearing
`seq INTEGER PRIMARY KEY AUTOINCREMENT` contract. An exact-column event table with unique
`event_id` and a plain non-unique `seq INTEGER` is accepted.

Concrete probe:

1. Record a successful acquisition and a later failed intake at the same instant.
2. Rebuild `event_sequence` with all exact columns and `event_id TEXT UNIQUE`, but no primary key
   on `seq`.
3. Give the attempt the acquisition's same integer sequence in both its store claim and central
   event record.

Observed: schema initialization returned `wal`; all six `PRAGMA table_info(...).pk` flags were
zero; reconciliation returned `reconciled`; the refresh copy silently omitted
`newest attempted drop failed intake`. The restored order no longer proves which event was later.

Required boundary: validate the complete sequencing structure, not only event identity—at minimum
the exact integer primary key/autoincrement contract—and reject duplicate, nonpositive, or otherwise
non-monotonic central sequences on load before ordering. A duplicate sequence must render event
integrity failure, never equality that suppresses the overlay.

### 3. HIGH — exact-integer validation was added to acquisitions but omitted from attempts

At `footballguys_intake.py:2865-2875`, acquisition claims require an exact integer `event_seq`.
The sibling attempt branch at lines 2890-2899 checks IDs only. Python tuple equality then treats
REAL `2.0` as equal to central INTEGER `2`, and `_event_key()` later coerces it with `int()`.

Concrete probe: rebuild only the attempt relation so its signed `event_seq` is stored as REAL
`2.0`. Reconciliation returned `reconciled` and the read model treated the attempt as governed.

Required boundary: apply the same exact-int/non-bool sequence predicate to every attempt claim
before adding it to `claims`. Add a branch-symmetry mutant; an acquisition-only guard must fail.

### 4. HIGH — an invalid read clock still leaks a bare aware/naive comparison error

The central event validator calls `_canonical_instant(event_at, now=self.clock())` at lines
2927-2932 and catches only `FootballguysIntakeError`. When a restored driver/caller supplies an
offset-naive clock, `_canonical_instant` compares an aware persisted event with naive `now` and
Python raises bare `TypeError`.

Concrete probe: create a valid acquisition under the aware governed clock, reopen the same store
with an injected naive `datetime(2026, 8, 10, 12, 0, 0)`, and call `read_model()`. Observed:
`TypeError: can't compare offset-naive and offset-aware datetimes`.

Required boundary: validate/canonicalize the read clock once before comparison (or use the already
validated `read_model(now=...)` instant consistently), and convert invalid clock dependencies into
a named fail-closed state. Reader totality must not rely on a prior writer having validated a
different driver instance.

### 5. MEDIUM — H5's unchanged-state RED missed fresh-root mutation before validation

`write_semantic_adjudication()` initializes the semantic database at lines 2445-2447 before it
validates any record field. RED v9's H5 tests seeded a valid assertion first, so their
unchanged-state comparison could not detect this ordering.

Concrete probe: on a fresh root with no `semantics.db`, submit an adjudication with `key=[]`.
The writer returned the repaired named refusal `adjudication_key_invalid:[]`, but created
`semantics.db` and seven tables (`acquisitions`, `event_sequence`, four semantic tables, and
`sqlite_sequence`) first.

Required boundary: perform pure record-shape/type/vocabulary validation before initializing or
opening a durable store. Add a fresh-root physical-absence control for the main database and all
sidecars. This is also a RED-adequacy miss by this reviewing lane: the v9 unchanged-state oracle
was anchored after initialization and therefore passed code that mutates before refusing.

## 4. Disposition

**NOT CLEAR.** The commit scope and published gate censuses are accurate. Findings 1 and 2 are
load-bearing: one can promote malformed adjudication state into Phase-C eligibility; the other can
erase the newest failed-intake fact from the refresh copy. Keep `b582b1d` unpushed and do not run a
first capture against it.

No RED/GREEN/config/manifest/runtime/provider/scheduler changes were made by this review. Phase
B/C/D remain closed. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
