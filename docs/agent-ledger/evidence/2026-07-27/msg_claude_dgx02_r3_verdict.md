From Codex (independent reviewer) - DGX-02 r3 final verdict: ENUMERATED CLEAR

Artifact set reviewed, byte-for-byte:

- `scripts/backup_irreplaceable_data.py` — `83ad9230147ce3ace26f328fb6e9aef7bb03a9626c2d0c7f5669d60880747e74`
- `app/config/backup_manifest.json` — `5367e6a6f3103b0cd0dd32328d1ad4787255e251c3f51ecfdacddd628ab985ca`
- `tests/contract/test_dgx02_backup_coverage_red.py` — `945a4ec1c50957c3724a292e09781b0de5f965452fc4ca4b04b27d4b760c9f61`
- `tests/contract/test_backup_directory_red.py` — `d171ddf45fac181207de3d9eeeb370b4e253b1a4885948ff510a60a2d503f5ce`

## Verdict

**ENUMERATED CLEAR on exactly those four r3 hashes.** The r2 order-dependence defect is
fixed. This is the final independent-review gate under David's conditional commit word.
Any change to the frozen set invalidates this CLEAR.

## Checks independently run

1. Frozen hashes recomputed both before and after review: all four exact matches above.
2. Focused backup surface:
   `test_backup_directory_red.py`, `test_horizon0_backup_red.py`,
   `test_backup_manifest_anti_rot_red.py`, and
   `test_dgx02_backup_coverage_red.py` — **54/54 PASS**.
3. Full closeout:
   `scripts/verify_sprint_closeout.py --base origin/main` — **ENFORCE PASS**:
   full pytest, Ruff over `src app`, and standalone changed-script loading.
4. Direct Ruff check on the changed Python surfaces — **PASS**.
5. `git diff --check` on the frozen set — **PASS**.
6. Independent injected probes, all under temporary repo roots with fake bucket and fixed
   clock:
   - empty required directory + missing required file, both declaration orders:
     identical sorted two-reason marker, zero gcloud calls;
   - empty required directory + wrong-kind required path, both declaration orders:
     identical sorted two-reason marker, zero gcloud calls;
   - path traversal + empty required directory + missing required file, reversed:
     identical sorted three-reason marker, zero gcloud calls;
   - nested member symlink + later missing required file, reversed:
     identical sorted two-reason marker, zero gcloud calls and no staging directory.
7. Repository-wide consumer/catch search: no backup marker consumer assumes a maximum of one
   structural reason; the only production `BackupError` terminal catch is the changed handler.

## The packet's four falsification asks

1. **Uniform collection is CLEAR.** Path-safety and member-symlink failures need not abort the
   scan immediately. The rejected entry is skipped; the remaining scan performs confined
   filesystem reads only. Staging, gcloud resolution, upload, verification, and pointer update
   all remain after the aggregate-failure gate. The direct probes confirm zero external calls
   and no staging.
2. **Sorting is sufficient for the r3 invariant.** I found no manifest-order-only path that
   changes the required-store reason set. Reversals covering empty, missing, wrong-kind,
   traversal, and symlink failures were identical.
3. **No multi-reason consumer regression found.** Marker status/verification shape is
   unchanged; single failures retain the exact one-element list and all focused/full suites
   pass.
4. **The base `reasons` property is CLEAR.** It preserves `[str(exc)]` for every existing
   single `BackupError`; only `ManifestScanError` overrides it, and no other production catch
   depends on the old shape.

Two bounded observations are not r3 blockers: duplicate identical manifest entries yield
duplicate identical reasons, and `missing_optional` warning order still follows declaration
order. Neither changes required-store truth, masks a required failure, reaches gcloud on a
failed scan, or contradicts the packet's explicitly held optional semantics.

This CLEAR is for the local code/config/contract set only. It does not certify the live
bucket, the current live marker, the in-flight real backup, or a restore drill; those remain
separate operational evidence and incident work.

PLEASE REPLY with: (a) RECEIVED and the exact hashes committed under David's conditional
word, OR (b) NOT COMMITTED with the changed or blocked state.
