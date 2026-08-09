# B21 schedules — GREEN (Claude, implementing lane)

Date: 2026-08-09
Layer: 1 (ingest) — presenting and primary; the layers 1–2 dependency check does not apply.
Built against CLEARed RED pin `38fceec11f9a4d623b53dee986fb59efe96fbf12429e18a2950190c9eca9cb86`
(`docs/agent-ledger/evidence/2026-08-09/b21_schedules_red_clear_codex_v1.md`).

**The RED was not touched.** Its hash still recomputes to `38fceec1…`, byte-identical to the pin you
CLEARed, including the stale "gameday unmeasured" sentence you told me not to edit.

## Changed files

| File | SHA-256 | Lines |
| :-- | :-- | --: |
| `src/dynasty_genius/sources/schedules_capture.py` (new) | `6da5666413ee08774aaafd049ba3129516d5fa1e40a2651d86e5e306c1da49ce` | 798 |
| `scripts/run_schedules_capture.py` (new) | `b1a051467ced866ef53ffb1f281f44957f296e876abcbaf01e77d888bfc42a04` | 94 |
| `app/config/backup_manifest.json` (one entry added) | `31839b15391b5547dac1d57671992cd19cadfb6207d922663269fb8439c0b486` | — |
| `tests/contract/test_b21_schedules_capture_red.py` | `38fceec1…` **UNCHANGED** | 1,062 |

*(The script hash reflects one post-smoke-run fix: the CLI printed `fetch_failed: fetch_failed: …`
because `CaptureError.__str__` already leads with the code. Cosmetic, operator-facing, fixed.)*

## Gates

- **Focused: 56 passed / 0 failed**, true exit 0.
- **Full suite: 5,014 passed / 15 failed / 12 skipped / 9 xfailed / 0 collection errors** (681s).
  **All 15 failures are in `tests/contract/test_governed_cadence_inputs_red.py`** — the other
  UNTRACKED withdrawn RED, targeting a module that does not exist. **Tracked-file failures: zero.**
  *(Measured correction: the 2026-08-08 handoff board's arithmetic implies 12 failures in that file.
  It collects **15**, and its mtime is 2026-08-08 16:20 — before that board was written and untouched
  by this session. The board's figure was wrong; I am reporting what I measured.)*
- **Ruff:** clean on both new files, and `ruff check src app` — the CI gate under `03` — is clean.
- **Clean-tree CI simulation:** `git archive HEAD` into an isolated tree, the four files overlaid,
  `test_b21_schedules_capture_red.py` + `test_backup_manifest_anti_rot_red.py` → **61 passed** with
  `app/data/` absent entirely.
- **Negative control on that simulation** (mandatory, per the local-green-≠-CI-green lesson): removing
  the new manifest entry inside the sim makes **P2 fail there**. The simulation is a real check, not
  a vacuous green.

## ⚠ LANDING-ORDER HAZARD — read this before any commit

**The manifest entry breaks the daily backup until the store exists AND holds at least one file.**

`scripts/backup_irreplaceable_data.py:226-228` raises `missing_required:<path>` when a required
entry's path is absent, and `:256-257` raises `directory_empty_required:<path>` when a required
directory expands to zero files. `app/data/sources/nflverse_schedules` **does not exist on this
machine right now**, and the backup LaunchAgent fires daily at 10:15.

So: **`app/config/backup_manifest.json` must not be committed before the first capture has populated
the store.** The whole change set lands together with the capture, or the disaster floor fails on its
next run. Both the capture and the commit are David-gated, so this resolves naturally in sequence —
but it is stated here because nothing mechanical enforces it, and a well-meant "commit the code now,
capture later" would break his backup.

*(This entry is required by P2 and by the standing manifest-coverage law. The store is genuinely
irreplaceable and unlike its two `app/data/sources/` siblings, which the manifest excludes as
rebuildable: this provider serves ONE mutable global asset, and 2026-08-06 measurement established
that nflverse rewrites published assets in place.)*

## The defect the RED caught in my GREEN

**E1[marker] failed on the first run, and it was a real bug, not a harness artifact.** My rollback
tracked files the attempt *created* and deleted them — but never restored files it *overwrote*. A
marker-boundary failure therefore left the already-rewritten `index.json` naming a vintage the
publication had abandoned: `vintage_count()` returned 2 where 1 was correct.

That is precisely the "second run half-succeeds over a good one" hazard E1 was widened to catch two
rounds ago, and three of the four boundaries passed while it was broken. Repaired with a `_Journal`
that records prior bytes for every touched path and restores by atomic replace — never in place,
because raw links share an inode with the content store and an in-place write would reach through the
link and corrupt a retained vintage.

## Design decisions a reviewer should challenge

1. **Content-addressed raw with hard links.** `raw/<check_id>.parquet` is a hard link to
   `content/<sha256>.parquet`. Every check keeps its own addressable path (S3), but identical bytes
   are stored once. Measured on a two-check no-change sequence: 3 files, **one payload on disk**
   (`du`: 4 KB total). Without this, a megabyte-scale asset checked daily duplicates itself forever,
   which is the same class as the open snapshot-retention question already on David's list.
2. **Validation order is deliberate and load-bearing**, per the RED: dtype/null → source times →
   scores → duplicates → identifier consistency. An unusable field is a more basic fact than a
   disagreement between two fields.
3. **`retrieved_at` defaults to `observed_at`** on direct `record_offering` (the import/replay path,
   where the observation instant *is* when the bytes were taken in hand). Every transport path takes
   it from the response and validates it.
4. **Stable codes:** `raw_bytes_required`, `raw_empty`, `raw_unparseable`, `schema_missing_column`,
   `required_field_type_invalid`, `source_time_invalid`, `score_type_invalid`, `duplicate_game_id`,
   `game_id_inconsistent`, `observed_at_invalid`, `retrieved_at_invalid`,
   `source_identity_unexpected`, `unsafe_identifier`, `fetch_failed`, plus
   `publish_failed:<boundary>` in the audit trail.
5. **The failed-attempt audit is written OUTSIDE the publication transaction** on purpose, so the
   evidence that we tried survives the rollback of what we tried to write.

## Self-probe beyond the contracts

Exercised by hand, off-network, in a scratch root: two-check no-change sequence (inode identity
confirmed, `last_checked_at` advanced, `last_changed_at` frozen, `partial_artifacts()` empty); the
CLI happy path (exit 0, marker written); the CLI transport-failure path over a **populated** store
(exit 1, prior marker byte-identical, `vintage_count()` 1, `failed_check_count()` 1); and
`--summary`, which is read-only and fetches nothing.

## NOT done — each a separate word

No live source call has been made. No scheduler installed, no plist touched, no consumer rewired
(`run_realized_outcome_scoring.py` still infers `"final"` from a populated score; this module
deliberately does not, and migrating it is the separately sequenced ticket). Nothing committed,
nothing pushed.

## Requested

Behavioural CLEAR on the four artifacts above. After that, the first live 2026 capture — **which
remains David's word, unchanged and escalated, and is not something this packet claims** — and then
the committed landing plus exact-SHA terminal CI, in that order for the manifest reason above.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
