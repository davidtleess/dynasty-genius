# Footballguys Phase A GREEN review — commit `c183c11` — Codex v1

Date: 2026-08-10  
Reviewer: Codex, independent review lane  
Layer: 1 — intake/persistence  
Verdict: **NOT CLEAR — 2 Critical / 2 High**

## Pin and divergence audit

- Commit: `c183c11553bd7d22514862cf11f9b2dca01cfe65`
- Parent: `53ae83451ad7480686299ebc65eb05610a5a5eb0`
- Exact diff: the declared three modified files and `+538/-58`.
- RED SHA-256 reproduced:
  `ac9d903aab5e52130b951665af626bc8ef0f57346372fb1b2ddace836843cd22`.
- GREEN SHA-256 reproduced:
  `657873570fb35beaecf5cc44ee7bf18a7e6917c9b4cd94028874ec21e329b607`.
- Current RED/GREEN bytes remain identical to the committed pin.

## Declared gates independently reproduced

- Strict Python 3.14 RED v7 with `PYTHONDONTWRITEBYTECODE=1 -W error`:
  **318 passed, exit 0**.
- Full tracked suite, excluding only the standing untracked cadence RED:
  **5,551 passed / 12 skipped / 9 xfailed, exit 0**.
- Ruff and cold `py_compile -W error`: clean.

## Findings

### C1 — Critical — the semantics/event migration still promotes unbound central history

The correction only rejects populated legacy acquisition/attempt tables
(`footballguys_intake.py:1302-1342`). The old central `event_sequence(seq)` migration still adds
nullable identity columns in place (`1391-1397`) without checking whether rows exist and without
rebuilding the `event_id UNIQUE` constraint that new stores receive at `1377-1381`.

The load validator then converts central rows to a dictionary (`2715-2721`), checks only event
types equal to `acquisition`/`attempt` (`2727-2729`), and treats everything else—including NULL
legacy rows—as irrelevant. Duplicate ids in the migrated non-unique table are also collapsed by
the dictionary before validation. If the central query itself fails and there are no store claims,
the validator explicitly returns success (`2722-2723`).

Live probes:

1. Replace a governed empty central ledger with the exact historical `event_sequence(seq)` table
   containing one row. The next intake migrated the row to `(seq=1, NULL, NULL, NULL, NULL, NULL)`,
   accepted it, appended a new acquisition event at seq 2, and rendered healthy `current`.
2. On that migrated table, copy the valid seq-2 event id and tuple onto seq 1. The database now
   had two central rows with the same event id; the reducer still rendered healthy `current`
   because the dictionary kept only one.
3. With no acquisitions, replace `semantics.db` with non-SQLite bytes. `read_model()` rendered
   `no_record`, not unreadable/integrity failure, because `return not claims` converts central
   unreadability into success.

This violates the accepted “no fabricated history / orphans remain visible” rule at the central
store itself. Required repair: populated bare central ledgers refuse as unreconcilable before
mutation; migrated/current schema validation includes keys/uniqueness, not just column names; every
central row has a closed non-null identity/type; duplicates and unreadable central state fail
closed even when there are zero store claims.

### C2 — Critical — unreadable inactive acquisition state is detected but ignored before publish

`_store_rows()` records an unreadable store and returns an empty list on a query error
(`footballguys_intake.py:1455-1474`). `_prepare_stores()` clears that flag, calls reconciliation,
and tests only its boolean result (`1951-1953`). Reconciliation can therefore return true when an
inactive `acquisitions` relation is unreadable but has no matching central events. Later
`_same_offering_row()` again treats the empty result as “no counterpart” and publication proceeds.

Live probe: install an inactive WAL database with an `acquisitions(row_id)` table and an otherwise
current empty `attempts` table, then perform a valid full-offsite intake. The intake returned
`review_required`, published the paid ZIP, and committed the receipt. A subsequent read correctly
rendered row 9 unreadable. The system knew the counterpart was unreadable before staging but did
not make that knowledge load-bearing until after the write.

Required repair: reconciliation returns a typed unreadable result or checks `_unreadable_stores`
before success; intake refuses by name before staging/publication for either counterpart relation.
A “read later becomes row 9” test is not sufficient—the pre-write residue oracle must remain zero.

### H3 — High — the allegedly total semantic writer still leaks raw `TypeError`

At `footballguys_intake.py:2201-2206`, provenance and claim are tested for frozenset membership
before their type is established. RED v7's wrong-type rows use BLOB/bytes values
(`test_footballguys_phase_a_red.py:2963-2975`), which are hashable and therefore reach the named
refusals. Unhashable values exercise different code.

Live probes set `assertion.claim=[]` and `attachment.provenance=[]`. Both calls raised bare
`TypeError("cannot use 'list' as a set element")`, contradicting the total-schema/no-bare-exception
contract. Required RED uses at least one unhashable container per allowlisted field and asserts the
domain refusal plus unchanged semantic state.

### H4 — High — physical-file mode selection has a check/use race

`_read_uri()` checks `path-wal.exists()` and returns a URI (`footballguys_intake.py:1444-1453`);
the SQLite open occurs later at `1459-1461` and at the other read sites. `read_model()` does not
hold the lifecycle lock, so a conforming intake writer can create/commit WAL between those two
operations. The reader then opens the already-selected immutable URI and recreates the exact stale
read RED v7 was meant to close. The inverse race can select plain read-only after WAL disappears,
reintroducing forbidden WAL materialization.

Deterministic production-path probe: on the second immutable open of an inactive current store,
inject a committed `DROP TABLE attempts` after `_read_uri()` returns but before the real
`sqlite3.connect()`. WAL was 8,272 bytes, yet `read_model()` rendered healthy `current`; the
immutable connection missed the committed drop. This uses the production selector/open sequence,
not a mocked classifier.

Required repair: make file-set observation and database open one stable protocol—e.g. serialize
readers with the lifecycle lock or open/revalidate/retry against descriptor-bound sidecar state.
RED must inject WAL appearance and disappearance at the selector/open boundary, assert the
committed state/copy, and retain the existing physical-residue rules.

## Disposition

`c183c11` is **NOT CLEAR** and remains unpushed. No first capture may run against this pin. Await
implementer acceptance/contest before RED v8 authorship. No provider contact, scheduler, capture,
runtime-store mutation, push, or Phase B/C/D work was performed. H2 QB rushing remains **UNDER
TEST** with no result and is unrelated.
