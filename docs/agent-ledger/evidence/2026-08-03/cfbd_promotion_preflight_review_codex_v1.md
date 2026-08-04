# CFBD DATA promotion preflight review — Codex v1

**Date:** 2026-08-03
**Lane:** independent reviewer
**Scope:** the two post-implementation preflight fixes only: `.gitignore` and
`app/config/backup_manifest.json`
**Verdict:** **NOT CLEAR — one exact manifest-disposition residual**

## Evidence checked

- Read `docs/governance/02-agent-operating-loop.md` §Manifest coverage law and §Silence is not
  success directly.
- Read the literal two-file diff.
- Read `scripts/backup_irreplaceable_data.py` manifest parsing and missing/empty-directory behavior.
- Verified both representative history artifacts are ignored by the new rule:
  `git check-ignore -v` resolves both to `.gitignore:55`.
- Ran the backup contract slice:
  `26 passed` across `test_backup_manifest_anti_rot_red.py`, `test_backup_directory_red.py`, and
  `test_dgx02_backup_coverage_red.py`.

## B1 — `.gitignore`: CLEAR

Ignoring `app/data/training/cfbd_promotion_history/` is correct. The preimage is a byte-identical
copy of the deliberately ignored active training CSV; without the directory rule, a later
`git add -A` could stage the preimage and receipts. The rule covers the actual nested preimage and
receipt topology produced by `default_promotion_spec`.

## B2 — backup-manifest coverage: path correct, `optional` disposition NOT CLEAR

The directory belongs in the backup manifest, but `optional` does not protect the post-promotion
store against disappearance:

- `_validate_manifest_shape` forces every entry in the `optional` section to `required == false`.
- A missing optional path appends `missing_optional:*` but does not abort the run.
- The backup may still finish `status == completed`, set `sha256_verified == true`, and advance
  `latest.json`; the contract suite explicitly preserves this optional-directory behavior.
- An empty optional directory is likewise tolerated.

After the authorized promotion, this directory contains the only durable pre-promotion bytes.
Treating its later absence or emptying as optional would allow the disaster floor to remain green
after losing the artifact it was added to protect.

## Required correction

Move this exact entry into the manifest's `required` section and set `required: true`:

```json
{
  "path": "app/data/training/cfbd_promotion_history",
  "required": true,
  "kind": "directory"
}
```

David authorized **commit and immediate execution**. The short committed-but-not-yet-executed
interval should therefore fail closed. Once execution succeeds, the directory is present and
non-empty; if execution fails to create it, or it is later deleted or emptied, the backup must fail
with a named reason. A clean checkout is not the governing backup-ready state: the same manifest
already requires the deliberately gitignored active
`app/data/training/prospects_with_outcomes_v3.csv`.

No conditional “required after first promotion” mechanism is needed for this pinned one-time move.
The immediate run is the state transition. Making the entry required now is both simpler and safer.

## Boundary

This review does not authorize or execute the promotion, commit, push, refresh, bakeoff, retrain,
or model/feature promotion. QB rushing remains a registered hypothesis **UNDER TEST** with no
result; this data movement supplies no evidence about it.
