From Claude Code (implementing lane) — GREEN v19 READY FOR REVIEW

(a) EXACT RED REPRODUCTION BEFORE REPAIR — confirmed against your pins first:
- RED `ad6712a79a5c975b951423abfd2456680e6d4d8794e51344c810e4a4239ad046`, 6,306 lines /
  241,867 bytes — matches.
- GREEN pre-edit hash confirmed `cf3338e3918c169aa535a7c8cbf46c144abb6b93d1043e8be40d810be59754eb`
  BEFORE I touched it, as you asked.
- Strict census pre-repair: **563 collected = 46 failed + 517 passed, exit 1**. Exact match.

(b) REPAIRED GREEN:
- NEW GREEN `177257dd8f05efd0b1d514ef9e8479cbdfaed6ddf845b595e3caba9c533f8dec`
- strict `-W error`: **563/563 passed, exit 0** (exit code verified)
- ruff clean · strict `py_compile -W error` clean · `git diff --check` clean
- full suite: SUITE_PLACEHOLDER
- real-store byte-copy migration probe: **0 failures** (detail below)

WHAT I CHANGED, mapped to your four findings:
- C1 → `_validate_acquisition_current_schema` is now an UNCONDITIONAL POSTCONDITION at the end of
  `_migrate_acquisition_store`, on every branch. The version-keyed precheck at the old
  1645-1646 is deleted, so no migrating store can bypass it.
- H2 → new `_prevalidate_acquisition_store` / `_classify_acquisition_store`: receipts and
  observations now get the same read-only boundary semantics had. `initialize_database` calls it
  BEFORE `sqlite3.connect` and before the WAL pragma, so a refused store is byte-frozen and no
  `-wal` is materialised.
- H3 → classification is by EXACT DDL grammar via `_table_segments_match`, using new
  `_LEGACY_ACQUISITION_SEGMENTS` (v1/v2/v3) and `_LEGACY_ATTEMPT_SEGMENTS` (v1/v2); the
  unordered name-set test is gone. Marker-only is now exact row identity against
  `_MARKER_ROW = ("bootstrap-marker", "_bootstrap", "marker")`, replacing the NULL-blind
  `offering_id != '_bootstrap'` comparison.
- M4 → attempts rebuild reads `sqlite_sequence` before DROP and restores it after CREATE, so the
  high-water mark survives. I chose PRESERVATION over a series break, as flagged.

SELF-PROBE — ONE CHANGE BEYOND WHAT RED v19 BINDS, DISCLOSED:
`_classify_acquisition_store` originally early-returned when `acquisitions` was absent, so a
non-empty store carrying a surplus object but NO acquisitions table would have escaped the
read-only classifier and refused only at the post-migration validator — i.e. AFTER the
journal-mode write, reintroducing your H2 mutating-refusal defect in a state RED v19 does not
reach. I moved the closed object-inventory check ABOVE that early return. This is unbound by your
contract and is therefore exactly the kind of change you should attack: if you think the
inventory check belongs only on stores that already have acquisitions, say so and I will revert
it.

REAL-STORE PROBE — AND A FINDING WORTH YOUR ATTENTION:
`docs/agent-ledger/evidence/2026-08-11/footballguys_green_v19_real_store_probe.py` byte-copies the
LIVE stores into a disposable root; live files are read-only inputs and their hashes are
re-verified unchanged after the run (`ceac8dee…` before and after, both stores).
**David's live `app/data/footballguys/receipts.db` is a LEGACY v1 store** — its DDL is exactly
`_LEGACY_ACQUISITION_SEGMENTS[1]`. This migration family is not hypothetical; it is the shape of
his actual data. Probe result: migrates to the canonical postcondition, and a second open
re-validates. `observations.db` does not exist yet.

REVIEW TARGETS I'D ATTACK IF I WERE YOU:
a) `_index_signatures_governed(conn, "acquisitions")` is applied to LEGACY stores too. Legacy v1-v3
   declare the same PK/UNIQUE pair so the autoindexes should coincide — but I did not prove that
   holds for every legacy version, I inferred it from green tests.
b) The prevalidation gate is `elif store != "semantics" and path.exists() and size > 0`. Is there a
   reachable non-empty acquisition store whose classification I skip?
c) `sqlite_sequence` restore assumes the table exists post-CREATE because the new attempts table
   declares AUTOINCREMENT. If that assumption is false anywhere, the INSERT raises raw.
d) The rebuild still uses `",".join(sorted(columns))`; you cleared injection, but the column list
   now comes from a grammar-validated legacy shape — confirm that is strictly narrower.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D. Landing is David's word.
H2 QB rushing remains UNDER TEST with no result.
