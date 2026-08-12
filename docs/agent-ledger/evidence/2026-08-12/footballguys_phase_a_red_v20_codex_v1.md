# Footballguys Phase A RED v20 — acquisition refusal must be physically non-mutating

**Date:** 2026-08-12  
**Layer:** Layer 1 — governed ingest and persistence  
**Authority:** David: “work freely with claude until this is production grade.”  
**Scope:** RED authorship only. No commit, push, capture, provider contact, scheduler, or Phase B/C/D.

## Stable pins

- RED: `tests/contract/test_footballguys_phase_a_red.py`
  - SHA-256: `88bcc54efbb069a77f2621808db11f1e57e609e3897ccd635c94bc4b609dc0f7`
  - 6,424 lines / 247,107 bytes
- Baseline GREEN: `src/dynasty_genius/sources/footballguys_intake.py`
  - SHA-256: `177257dd8f05efd0b1d514ef9e8479cbdfaed6ddf845b595e3caba9c533f8dec`

## Finding bound

GREEN v19's new read-only acquisition-store classifier still has two exits that can
refuse only after the store has been changed from DELETE to WAL:

1. An attempts-only store returns early when `acquisitions` is absent, before the
   existing `attempts` table is validated. A malformed current attempts table is
   refused later, after the main database has changed.
2. An exact legacy acquisitions marker plus an exact but populated legacy attempts
   table passes prevalidation. Migration later refuses the populated table, again
   after the main database has changed.

These are one contract family: every refusal-class fact that is knowable from a
read-only acquisition store must be classified before any journal-mode or migration
write.

## RED v20 controls

- Malformed attempts-only DELETE-mode store, for receipts and observations:
  named schema refusal, main/WAL byte fingerprint unchanged, no WAL created.
- Canonical current attempts-only store, for both modes: positive migration and
  repeat-open anchor. This prevents a refuse-all repair.
- Empty exact legacy attempts-only v1/v2, for both modes: positive migration,
  repeat-open, and AUTOINCREMENT high-water preservation. This prevents a repair
  that refuses every legacy partial store while satisfying the mutation negatives.
- Populated exact legacy attempts v1 and v2, for both modes: named unreconcilable
  refusal, main/WAL byte fingerprint unchanged, no WAL created.

## Measured census against baseline GREEN

Exact strict command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q tests/contract/test_footballguys_phase_a_red.py --tb=no
```

Initial result before the positive-only amendment: **571 collected = 6 failed +
565 passed, exit 1**.

- Initial focused v20 slice: **6 failed + 2 passed**.
- All 563 inherited v19 contracts pass.
- Each failure is the byte-level fingerprint assertion after the implementation has
  already produced the expected named refusal.
- Receipts and observations fail symmetrically.

The final RED pin adds four positive-only legacy-partial-store anchors. They were
measured against baseline GREEN before its mtime changed: focused v20 became **6
failed + 6 passed**, with the same six failure identities. Therefore the final
pre-GREEN census is **575 collected = 6 failed + 569 passed** by two directly
measured non-overlapping components (the inherited/initial full run plus four new
passing anchors). A concurrent GREEN edit began 26 seconds after the RED amendment,
so a later full run was correctly treated as a post-repair run, not mislabeled as a
baseline census.

## Hygiene

- `.venv/bin/ruff check tests/contract/test_footballguys_phase_a_red.py`: clean.
- Strict Python 3.14 compile under `-W error`: clean.
- Skip/xfail/skipif grep: zero.
- No GREEN or runtime store was changed by Codex.

## Required GREEN outcome

The classifier must validate any existing attempts table before an acquisitions-absent
return, and must determine whether a legacy attempts table is populated during the
non-mutating prevalidation boundary. Canonical and empty exact legacy attempts-only
stores remain migratable, with legacy sequence state preserved. Refused stores remain
byte-identical and acquire no WAL.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
