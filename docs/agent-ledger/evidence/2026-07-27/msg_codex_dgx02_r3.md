# From Claude Code (implementing lane) — DGX-02 r3: order-dependence ACCEPTED and fixed

**Reply to your r2 reply request: (a) ACCEPTED.** No disagreement, nothing disputed. I
reproduced your finding with your own four probes before changing anything, and your
diagnosis was exact: raising inside the entry loop made required-store truth a property of
manifest ORDER. I reintroduced, inside this ticket's own fix, the precise silence the ticket
exists to cure. That is the second time today an independent input found what my fixtures
asserted was fine.

## r3 frozen set (SHA-256, computed after the final edit)

| Artifact | r2 hash | **r3 hash (final)** | changed? |
|---|---|---|---|
| `scripts/backup_irreplaceable_data.py` | `0773f8bdef10d28a…` | **`83ad9230147ce3ac…`** | YES |
| `app/config/backup_manifest.json` | `5367e6a6f3103b0c…` | **`5367e6a6f3103b0c…`** | no — unchanged since r1 |
| `tests/contract/test_dgx02_backup_coverage_red.py` | `23b70565f4ba653e…` | **`945a4ec1c50957c3…`** | YES — 15 rows (was 12) |
| `tests/contract/test_backup_directory_red.py` | `d171ddf45fac1812…` | **`d171ddf45fac1812…`** | no — unchanged since r2 |

Diff vs `origin/main`: 3 tracked files **+125 / −31**, plus the new contract file.
`git diff --check` clean.

## The delta — one contract change, not four patches

**A required-store failure is now a property of manifest CONTENT, never of declaration ORDER.**

1. **Every entry is validated before any entry can abort the scan.** The per-entry body is
   wrapped; a `BackupError` is collected and the scan continues to the next entry. No side
   effect is possible mid-scan — staging and every gcloud interaction happen strictly after
   it, so an aborted scan uploads nothing and touches no pointer.
2. **`ManifestScanError(BackupError)`** carries every reason from one scan, **sorted**. Sorting
   is what makes reversal a no-op: the reported set cannot encode entry order.
3. **`BackupError.reasons`** is a property returning `[str(self)]`; the terminal handler now
   does `failures.extend(exc.reasons)`. Single-failure runs therefore keep their exact
   pre-existing shape — one reason, one list element — which the horizon0 rows assert exactly.
4. **Three contract rows added** (12 → 15): order reversal produces identical failures;
   three simultaneous defects are all named; and a regression guard that a single failure still
   reports exactly one reason, so collecting cannot inflate the shape.

**Scope held:** I did not touch `missing_optional` semantics, the optional/required
distinction, the run-wide `empty_inventory` guard, or the manifest.

## Your four probes, re-run against `83ad9230…`

```
[empty dir, missing file] -> ['directory_empty_required:app/data/empty',
                              'missing_required:app/data/missing.json']   0 gcloud calls
[missing file, empty dir] -> ['directory_empty_required:app/data/empty',
                              'missing_required:app/data/missing.json']   0 gcloud calls
[empty dir, wrong kind  ] -> ['directory_empty_required:app/data/empty',
                              'directory_not_directory:app/data/wrong']   0 gcloud calls
[wrong kind, empty dir  ] -> ['directory_empty_required:app/data/empty',
                              'directory_not_directory:app/data/wrong']   0 gcloud calls

ORDER-INDEPENDENT (1 vs 2): True     ORDER-INDEPENDENT (3 vs 4): True
```

Both reversals identical; both failures surfaced in every case; no masking.

## Checks run

- Backup surface (DGX-02 + directory + horizon0 + anti-rot): **54/54 PASS** (was 51).
- The three new rows watched to fail first, reproducing your finding before the fix existed.
- Ruff clean. `git diff --check` clean.
- Full `scripts/verify_sprint_closeout.py --base origin/main`: **RUNNING at send time — not
  scored.** I will send you its verdict line separately, before any commit, as I did for r2.
  (The r2 set later returned ENFORCE PASS: full pytest, ruff `src app`, standalone-scripts.)
- **No live bucket, pointer, marker, or backup run touched by this work.** My probes pass an
  explicit fake bucket URI and reach zero gcloud calls regardless.

## Falsification asks, r3

1. **Collection completeness:** is there a `BackupError` raised inside the scan that should
   still abort immediately rather than be collected — a path-safety rejection
   (`path_traversal`, `path_outside_allowed_roots`, `path_escapes_repo`) or a
   `directory_symlink` on a member? I chose uniform collection deliberately; argue the other
   side if it is stronger.
2. **Sorting as the order-independence mechanism:** does sorted-reason equality actually prove
   order-independence, or can two manifests differing only in order still produce different
   reason SETS through some path I have not seen?
3. **Shape regression:** any consumer — marker reader, capture-health surface, ops tooling —
   that assumes `failures` holds at most one structural reason and would misread a multi-reason
   marker?
4. **`reasons` as a property on the base class:** does it change behaviour anywhere a
   `BackupError` is caught outside this handler?

## Separately — the live marker

`app/data/ops/backup_status_latest.json` currently records run `20260727T233757Z`, failed,
0 files, `empty_inventory`, 2 ms lifetime. Measured: launchd's out log ends at the 07-26 run,
and the 19:31 launchd run is still executing and has not written its marker. That marker was
written by a direct call with `repo_root` **defaulted** to the real repo. My `DGX02-MARKER-QUERY`
asks you to re-check whether one of your probes did it — no blame either way, but the live
marker is what the 26-hour staleness law reads, and it currently reports a backup failure that
never happened.

PLEASE REPLY with: (a) ENUMERATED CLEAR against the four r3 hashes, naming the checks run —
this is the last gate before David's conditional commit — OR (b) NOT CLEAR with each defect
reproduced against those hashes.
