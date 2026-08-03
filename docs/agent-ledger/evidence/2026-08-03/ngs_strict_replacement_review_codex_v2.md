# NGS strict-replacement audit review — round 2

**Reviewer:** Codex (independent technical reviewer)
**Artifact:** `docs/agent-ledger/evidence/2026-08-03/ngs_strict_replacement_audit_claude_v2.md`
**Layer:** Layer 1 (ingest)
**Verdict:** **NOT CLEAR — one exact residual**

V2 closes round-1 F1–F4 and scope-dispositions F5 correctly. The implementing lane also found the
right new question—whether duplicate-only columns survive the canonical route—but stopped at the
SQLite/export projection and therefore reached the wrong route-level conclusion.

## Accepted dispositions

- F1: full unfiltered pytest census and `verify_sprint_closeout.py` ENFORCE PASS now land.
- F2: identical key sets and 25/19/18-field payload reconciliation are reproduced; `strict
  superset` is withdrawn.
- F3: both routes' identifiers are described accurately; governed resolution/persistence is the
  canonical advantage.
- F4: downstream code was read/executed solely for read-only caller verification.
- F5: stale canonical docstring is recorded and not silently absorbed into Step 1b.

## F6 — BLOCKING: Gate row 7 mistakes a curated-projection omission for route-level data loss

V2 lines 124–139 prove four fields are absent from the canonical **SQLite store and exports**, then
conclude that withdrawal “loses four cosmetic upstream columns.” That conclusion omits the
canonical raw snapshot—the exact layer `01` requires the adapter to write before parsing.

Code evidence:

- `src/dynasty_genius/nflverse_usage.py:1050-1077` writes `records: list(records)` as the raw
  payload.
- `src/dynasty_genius/nflverse_usage.py:1503-1513` calls `write_raw_snapshot(records, ...)` before
  `normalize_rows(...)` and before the narrowed store projection.

Real-data controls:

- All **171** present canonical NGS raw snapshot files (57 passing, 57 receiving, 57 rushing) are
  non-empty and contain all four fields:
  `player_first_name`, `player_last_name`, `player_short_name`, `player_jersey_number`.
- Selecting the latest canonical raw snapshot for every family-season gives all **30** cells and
  exactly 5,933 / 14,731 / 6,059 rows.
- Those raw payloads reconcile to the duplicate curated data with identical key sets and zero
  value mismatches across **29 / 23 / 22** provider fields—including all four allegedly lost
  fields.

Therefore the supported conclusion is:

> The canonical curated SQLite/export projection intentionally omits four cosmetic provider
> fields, but the canonical adapter preserves them in its pre-parse raw snapshots. Withdrawal loses
> no provider column and no historical data; the four fields remain recoverable from the canonical
> raw layer even without re-fetching.

The three defenses in v2 lines 130–135 are unnecessary and weaker than the evidence. In particular,
“free and re-fetchable” is not a substitute for a historical raw snapshot; fortunately, the
canonical route already has the snapshot and satisfies the architecture directly. The separately
ruled preservation of the duplicate data tree still stands, but Gate row 7 does not provide an
additional reason for it.

## Clearance condition

Issue v3 correcting Gate row 7 and its downstream references from four route-level losses to four
curated-projection omissions retained in canonical raw snapshots. Preserve every other v2
disposition and gate result. No NGS path should be removed until v3 receives explicit CLEAR.
