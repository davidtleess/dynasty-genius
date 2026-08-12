# Footballguys Phase A GREEN v20 adversarial review — NOT CLEAR

**Date:** 2026-08-12  
**Layer:** Layer 1 — governed ingest and persistence  
**GREEN reviewed:** `6fbac8af65c5f0c2eba92688a4ee7c600e0949b644262fc304a166076e2d14ca`  
**Frozen RED v20:** `88bcc54efbb069a77f2621808db11f1e57e609e3897ccd635c94bc4b609dc0f7`

## Gate reproduced from the implementing lane

- Strict RED v20: **575/575, exit 0**.
- Full suite: **5,808 passed / 15 failed / 12 skipped / 9 xfailed**, zero
  collection errors. All 15 failures are the standing untracked cadence RED.
- Ruff, strict compile, and diff check clean.
- Real-store byte-copy probe: zero failures; live stores unchanged.
- RED and GREEN hashes were verified before and after the gate.

The v20 repair itself is correct: attempts classification and populated-legacy
classification now occur before the acquisitions-absent return and before any
DELETE-to-WAL mutation. The positive legacy-partial-store anchors were load-bearing.

## Findings

### 1. Critical — acquisition rows are filtered before validation

`_store_rows()` executes:

```sql
SELECT * FROM acquisitions WHERE offering_id != '_bootstrap'
```

SQLite three-valued logic excludes `offering_id IS NULL`, and the predicate also
excludes any row impersonating the reserved offering id before row identity can be
checked. Live probes against both receipts and observations showed that a NULL
offering row and a bootstrap-marker impostor each rendered **`no_record`**. They are
persisted corrupt evidence and must enter reduction as an integrity failure.

This is the same filter-before-reduce species previously closed for semantic rows and
the same NULL-blind predicate species fixed in migration eligibility. The load path
must read every row, remove only the exact governed bootstrap marker, and validate all
others before any projection or sibling fallback.

### 2. High — `sqlite_sequence` is preserved but not governed

The implementation now preserves attempts AUTOINCREMENT high-water across legacy
migration, but accepts arbitrary `sqlite_sequence` state. Measured in both stores:

- TEXT and negative high-water values migrate successfully, then the next attempt is
  issued sequence 1;
- duplicate `attempts` rows and surplus `ghost` rows are accepted;
- a current table whose sequence is below `max(attempts.seq)` is accepted.

Thus “preserve high-water” can preserve invalid state or silently reset the durable
series. The non-mutating classifier must require exactly zero or one `attempts`
sequence row, no other names, an exact nonnegative INTEGER value, and—when attempts
rows exist—`seq >= max(attempts.seq)`. Invalid state refuses before WAL mutation.

### 3. High — unsupported future schema version is silently downgraded

A canonical current store with `PRAGMA user_version=999` passes prevalidation and is
rewritten to version 4 in both modes. An older binary must not silently claim ownership
of a future-version store. Values above the supported version must refuse during the
read-only boundary with the main/WAL fingerprint unchanged.

### 4. Medium — explicit read time is not validated before state branching

`read_model()` validates `self.clock()` but not its public `now` argument. On an empty
store, `None`, text, an integer, and a naive `datetime` all render the healthy-looking
`no_record` state because the code does not reach date arithmetic. With data, those
same values can fail deeper. Type/awareness validation must occur once at entry and
invalid values must render the literal row-9 unreadable state before any state branch.

## Disposition

GREEN v20 is **NOT CLEAR** for landing. RED v21 binds all four families. No commit,
push, capture, provider contact, scheduler, or Phase B/C/D is opened.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
