# From Claude Code (implementing lane) — DGX-02 r2 addendum: the §4 fold-in

**Supersedes r1.** Your r1 ENUMERATED CLEAR is recorded and is **not** the commit gate.
David (TW27G) overruled the r1 scope judgment and folded §4 in now:
*"a required directory that expands to zero files must fail loudly, not ride along
silently while other entries contribute files."* Commit is conditional on **your CLEAR
against the final set below**. No push — that is a separate David word.

## Final frozen set (SHA-256, computed after the last edit)

| Artifact | r1 hash | **r2 hash (final)** | changed? |
|---|---|---|---|
| `scripts/backup_irreplaceable_data.py` | `419a8eac692f2a19…` | **`0773f8bdef10d28a…`** | YES |
| `app/config/backup_manifest.json` | `5367e6a6f3103b0c…` | **`5367e6a6f3103b0c…`** | no — byte-identical |
| `tests/contract/test_dgx02_backup_coverage_red.py` | `09f63f97d561d0c5…` | **`23b70565f4ba653e…`** | YES |
| `tests/contract/test_backup_directory_red.py` | `5fff9ff0803ec483…` | **`d171ddf45fac1812…`** | YES |

Diff vs `origin/main`: 3 tracked files **+62 / −5**, plus the new contract file
(**12 rows**, was 10). `git diff --check` clean.

## Exact r1 → r2 delta — four changes, nothing else

**1. New guard in `backup_irreplaceable_data.py` (the fold-in).** Inside the directory
branch, `units_before = len(staging_units)` is captured before expansion; after it:

```python
if entry["required"] and len(staging_units) == units_before:
    raise BackupError(f"directory_empty_required:{entry['path']}")
```

Raised **during expansion**, so it precedes gcloud resolution exactly as `empty_inventory`
and `missing_required` do. `required: false` still means tolerated.

**2. Failure precedence changed — re-check this.** For a manifest whose only entry is a
**required** empty directory, the reason is now `directory_empty_required:<path>`, not
`empty_inventory`. The run-wide guard still fires for: an empty manifest, all-optional-missing,
and optional-empty-directories. Both remain reachable; I contract both.

**3. Two rows you cleared in r1 changed.** Named explicitly because artifact drift under
review is exactly the r1 #5 defect you caught yesterday:
- `test_dgx02_backup_coverage_red.py::test_empty_directory_beside_a_real_file_still_completes`
  (mine, r1) asserted a **required** empty directory beside a real file still completes —
  the precise case David just ordered to fail. **Replaced** by
  `test_a_run_that_protects_every_declared_store_completes` (a genuinely complete run,
  2 files) and its honest half kept as
  `test_optional_directory_expanding_to_zero_files_is_tolerated`.
- `test_backup_directory_red.py`'s inverted row — renamed to
  `test_empty_existing_required_directory_fails_as_an_unprotected_store` and now expects the
  per-store reason. Both David words are quoted in its docstring.

**4. Three rows added to the DGX-02 contract file** (10 → 12):
`test_required_directory_expanding_to_zero_files_fails_loudly` (the disaster case:
`league_snapshots` emptied while other entries still contribute — RED watched to fail,
it returned `completed` before the change),
`test_optional_directory_expanding_to_zero_files_is_tolerated`, and the replacement
complete-run row. The three run-wide `empty_inventory` rows were re-pointed at an
**optional** empty directory so they isolate the run-wide guard from the per-store one.

## Checks run on the final set

- Backup surface (4 files: DGX-02 + directory + horizon0 + anti-rot): **51/51 PASS**.
- The new guard's RED watched to fail first, for its intended reason.
- Ruff clean on all three Python files. `git diff --check` clean.
- Real-CLI control on the **failure** path (never reaches the network — the guard precedes
  gcloud): `league_snapshots` emptied with other stores populated → **exit 1**,
  `failures: ["directory_empty_required:app/data/league_snapshots"]`, 0 files, no pointer.
  Restore one file → `completed`, 3 files.
- Full `scripts/verify_sprint_closeout.py --base origin/main`: **result pending at the time
  of writing** — it exceeded a 600s wall while your suites ran concurrently and is still
  executing. **I will send you the verdict line before any commit; do not treat this row as
  passed.** The r1 run of the same gate was ENFORCE PASS, but that was a different artifact set.

## Disclosure — my r1 evidence base is partly contaminated, and it is my fault

One "real CLI positive control" behind the r1 packet **hit the production bucket**. I passed
`--repo-root`, `--manifest` and `--staging` but **not `--bucket`**, so it defaulted to
`DEFAULT_BUCKET_URI`, authenticated, uploaded 3 fixture files, passed the restore drill on
them, and **advanced the real `latest.json`** to a synthetic run (`20260727T125127Z`).

Established read-only afterwards: no payload lost, append-only held, all prior run prefixes
intact, yesterday's real run `20260726T141500Z` still 273 objects, live status marker untouched.
The only damage is the pointer naming a 3-file synthetic run. Reported to David; **I have not
touched the bucket since** and will not — deletes are forbidden and re-advancing the pointer is
his call. Today's 10:15 scheduled run should supersede it with a genuine verified prefix.

**What this means for your review:** the r1 packet's success-path control is not trustworthy
evidence. The failure-path controls never reach the network by construction (the guard precedes
gcloud resolution) and stand. Re-derive anything you need rather than taking my run reports.

**Falsification asks, r2:**
1. Attack the precedence: is there an input where `directory_empty_required` masks a reason that
   should have surfaced first (`missing_required`, `directory_symlink`, `directory_not_directory`),
   or where it fires on a legitimately complete run?
2. `units_before` counts units, not members — is there a shape where a directory contributes a
   unit that is not its own member, or where a nested symlink/rejection makes the count lie?
3. Optional-directory tolerance: right call, or does an empty optional store also deserve a
   named failure?
4. Anything in change 3 where I updated a test instead of fixing code.

PLEASE REPLY with: (a) ENUMERATED CLEAR against the four r2 hashes above, naming the checks run —
this is the last gate before David's conditional commit — OR (b) NOT CLEAR with each defect
reproduced against those hashes.
