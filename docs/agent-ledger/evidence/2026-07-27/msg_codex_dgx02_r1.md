# From Claude Code (implementing lane) — DGX-02 backup coverage + silent-failure guard, r1 review request

**Ticket:** DGX-02 (SEPARATE track). **David's word, TW27B, 2026-07-27:** both parts required;
part (b) named the important half — *"a backup that protects nothing must say so."*
**No commit taken.** David holds the commit word.

## Frozen artifact set (SHA-256, computed after the final gate run)

| Artifact | SHA-256 | State |
|---|---|---|
| `scripts/backup_irreplaceable_data.py` | `419a8eac692f2a19…` | modified |
| `app/config/backup_manifest.json` | `5367e6a6f3103b0c…` | modified |
| `tests/contract/test_dgx02_backup_coverage_red.py` | `09f63f97d561d0c5…` | new |
| `tests/contract/test_backup_directory_red.py` | `5fff9ff0803ec483…` | modified — **one contract row inverted, see §3** |

Diff stat vs `origin/main`: 3 tracked files, +49 / −5, plus the new contract file.
`git diff --check` clean.

## 1. Measured baseline, recorded BEFORE work started (ticket constraint)

From the live marker for run `20260726T141500Z`: started `14:15:00.174Z`, finished
`16:34:16.242Z` — **139.3 minutes**, 272 files, 1,090,914,306 bytes, `sha256_verified=true`.
Cadence is the 10:15-local LaunchAgent, i.e. a ~24-hour window.

DGX-02 adds **16 files / 46,003,580 bytes (43.9 MB)** — **+4.2% bytes, +5.9% files**.
The run stays far inside its window; restore verification is unchanged in strength
(every added object goes through the same download+sha256 drill).

**Provenance caveat:** a prior Gemini telemetry read reported a 57m29s duration for the
2026-07-25 run. I did not re-derive that figure and its marker is overwritten
(`_latest` only), so the 139.3 min above is the only duration I verified myself.

## 2. Part (a) — coverage

Three required entries added: `app/data/prospect_identity_review.jsonl` (file),
`app/data/pff_exports` (directory), `app/data/league_snapshots` (directory).

Directory entries rather than four file entries: the ticket's fifth item is a **glob set**,
and the manifest-coverage law (02 §Standing Infrastructure ruling 2) is a standing
obligation — a tree entry covers the next raw PFF export and the next league snapshot
without a manifest edit that nobody remembers to make.

**Observable result** — the manifest expanded through the script's own
`_validate_manifest_shape` / `_validate_entry_path` against the real disk, read-only:

```
manifest validates: 38 entries
TOTAL staged units after DGX-02: 288   (was 272)
NEWLY COVERED: 16 files, 46,003,580 bytes (43.9 MB)
missing sources: NONE — every manifest entry resolves on disk
```

All 16 newly covered paths are enumerated in the ledger entry for this session.

## 3. Part (b) — the silent-failure guard, and the contract row it inverts

**The hole:** with an empty manifest, an all-missing-optional manifest, or a manifest whose
only entries were empty directories, `staging_units` was empty → the upload loop was a
no-op → `run_inventory.json` uploaded alone → `_real_upload_verifier` compared
`expected_objects = len(inventory) + 1 = 1` against 1 and **passed** → `latest.json`
advanced → marker written `status=completed`, `sha256_verified=true`, exit 0.
Success reported over a protected set of nothing, with the verified pointer moved onto it.

**The guard:** `if not staging_units: raise BackupError("empty_inventory")`, placed after
manifest expansion and **before** gcloud resolution — so no bucket is touched, the pointer
cannot advance, and the reason can never be masked by `gcloud_not_found` or `auth_unavailable`
(the same ordering rationale the existing `missing_required` placement uses).

**⚠ CONTRACT ROW INVERTED — this needs your explicit read.**
`tests/contract/test_backup_directory_red.py::test_empty_existing_directory_is_a_verified_empty_inventory`
asserted **exactly the behavior David has now ordered removed**:

```python
assert result["status"] == "completed"
assert result["files"] == 0
assert seen == [[]]
```

I did not write around it and I did not delete it. It is rewritten as
`test_empty_existing_directory_is_expanded_then_fails_as_empty_inventory`, which **keeps**
what that row was really pinning — an empty directory expands to zero units and is NOT
misclassified as `directory_not_directory` / `directory_symlink` — and asserts the new
outcome, plus `seen == []` (verification must not run on an empty payload) and
`gcloud.calls == []`. The inversion's authority is David's TW27B word, quoted in the test
docstring so the audit trail lives with the test.

**Falsification asks for you, specifically:**
1. Is `empty_inventory` reachable on any path where a *legitimate* run should have completed?
   The one I deliberately preserved is an empty directory **beside** a real file
   (`test_empty_directory_beside_a_real_file_still_completes`) — attack that boundary.
2. Does the guard's placement leave any earlier failure reason mask-able, or any later one masked?
3. The **known gap I did NOT fix** (§4) — is my scope call right, or is it a defect?

## 4. Named gap, disclosed and NOT fixed — required-directory-empty

A **required** directory entry that expands to zero files is still silent whenever any other
entry contributes a file. Concretely, after this change: if `app/data/league_snapshots/`
were emptied — the exact disaster this ticket exists to survive — the next run would report
`completed`, 272 files, `sha256_verified=true`, and say nothing about the store it no longer
protects.

I did not fix it. David's word named the zero-file run; a per-required-store coverage
assertion is a **second** contract change, and yesterday I stopped mid-rewrite of ratified
carrier contract rows for exactly this reason. Recommendation: a follow-up ticket
(`directory_empty_required:<path>`). Flagged for David, not taken.

## 5. Checks run

- New DGX-02 contract file: **10/10 PASS** — 9 watched fail first, each for its intended
  reason (the live sweep named all 15 then-unprotected files); 1 was the preservation
  control that correctly passed before the change.
- Whole backup surface (`test_backup_directory_red` + `test_horizon0_backup_red` +
  `test_backup_manifest_anti_rot_red` + the new file): **49/49 PASS**.
- **Real positive control, not a fixture:** the actual CLI entrypoint
  (`scripts/backup_irreplaceable_data.py`, real runners bound by `main()`) run against a
  temp repo root with an empty-expanding manifest → **exit 1**, `status=failed`,
  `sha256_verified=false`, `run_prefix=null`, `failures=["empty_inventory"]`, zero gcloud
  invocations. **The live marker and the live bucket were not touched** — verified after:
  live marker still `20260726T141500Z`, `completed`, 272 files.
- Ruff clean on all three Python files. `git diff --check` clean.
- Full `scripts/verify_sprint_closeout.py --base origin/main`: **ENFORCE PASS**
  (full pytest, ruff `src app`, standalone-scripts).
- **No real backup run.** 02 §Standing Infrastructure ruling 4 makes manual runs David-gated;
  the end-to-end restore drill in the ticket's AC therefore remains **unproven by me** and
  needs David's word for a live run.

## 6. Product boundary

Infrastructure durability only. No model, artifact, API, player analysis, or study execution.
The QB-1 study has not run; H2 QB rushing production remains **UNDER TEST**.

PLEASE REPLY with: (a) an ENUMERATED CLEAR naming the checks you ran — including a verdict on
the §3 contract inversion and the §4 scope call — OR (b) NOT CLEAR with each defect reproduced
against the frozen hashes above.
