# Backup coverage expansion — adversarial change-surface review

**Date:** 2026-07-25
**Mode:** read-only analysis; no backup run, manifest/runner/test mutation, commit, push, wire, or delivery-tool action
**Inputs:** shipped source and contracts, live local status marker (read-only), current protected/unprotected files, and `/tmp/gemini_backup_coverage.md`

## Bottom line

This is safe as a small, staged expansion only if the plan uses capabilities the runner already has:

1. four exact `kind: "file"` declarations; and
2. either:
   - one existing `kind: "directory"` declaration for `app/data/league_snapshots` (honestly broad: all present and future regular files in that directory, including the two tracked `*_latest.json` aliases), or
   - exact declarations for the ten timestamped files that exist today (honestly incomplete for the next generated run).

The manifest/runner do **not** support glob or pattern entries today. A family-selective `*_phase17-*.json` implementation is a schema-and-runner feature, not a manifest-only edit, and should be a separate change after the immediate exact-file coverage is safe.

The highest risk is not payload corruption. It is making a newly absent/unsupported path required, causing every daily run to fail before upload, while backup-health surfacing remains unwired. The previous verified remote run stays intact and `latest.json` does not advance, but all new daily protection stops until somebody reads the failed marker/LaunchAgent state.

I recommend two steps rather than one ambitious change:

- **Step A:** harden and prove the existing file/directory path with RED-first fixtures, then add the four exact files and the deliberately broad snapshot directory if David accepts that scope.
- **Step B (only if family-selective semantics are required):** separately design and ratify first-class pattern support, including required zero-match failure, per-member path safety, overlap rejection, and generation-pair behavior.

## 1. Change surface

### A. Primary production/config surface

| Path | Why it is in scope | Expected treatment |
|---|---|---|
| `app/config/backup_manifest.json` | The declaration source. It currently uses `backup_manifest.v2`, with `required`, `optional`, `exclude_paths`, and reasoned `exclusions`. | Must change for any coverage expansion. Exact file/directory additions do not inherently require a schema bump. A glob/pattern kind does. |
| `scripts/backup_irreplaceable_data.py` | Contains the only schema validator, path resolver, directory expander, stable copier, staging inventory, uploader, restore verifier, latest-pointer gate, and status-marker writer. There is no separate JSON-schema file. | No production edit is necessary for four exact files plus an existing directory kind. Any glob support changes `_ENTRY_KINDS`, `_validate_manifest_shape`, expansion semantics, zero-match behavior, path/symlink checks for every match, overlap detection, and likely the accepted schema version. |
| `ops/launchd/com.davidleess.dynasty-backup-irreplaceable.plist` | Runs the script daily at 10:15 local. | Regression surface, but should **not** change for a manifest expansion. Any proposal to alter schedule here is scope expansion. |
| `.gitignore` | Establishes why these artifacts are outside git. The four files are already ignored; the timestamped snapshots are ignored by `app/data/league_snapshots/*_phase[0-9]*.json`. | No change is needed. |

The four file producers/consumers are concurrency context, not default edit targets:

- `src/dynasty_genius/adapters/prospect_identity_resolver.py` appends one JSON line at a time to `app/data/prospect_identity_review.jsonl`.
- `scripts/build_college_features.py` reads `phase16_wr_manifest.json` and writes `phase16_wr_manual_review.csv`.
- `scripts/build_sleeper_universe_snapshot.py` invokes the snapshot writer.
- `src/dynasty_genius/sleeper_universe.py:343-367` writes timestamped snapshot, `snapshot_latest`, timestamped coverage, and `coverage_latest` sequentially with direct `write_text` calls.

The minimal backup expansion should not edit those producers. Their write shapes must, however, appear in the RED fixtures.

### B. Schema, status, inventory, and remote contracts

There are no standalone schema files. These contracts live inline in the runner:

- `backup_manifest.v1|v2`: `scripts/backup_irreplaceable_data.py:39,67-119`
- entry kinds (`sqlite`, `file`, `directory` only): `:44`
- `backup_run_inventory.v1`: `:246-255`
- `backup_latest_pointer.v1`: `:289-309`
- `backup_status.v1`: `:322-345`
- full remote list/size/download/hash verification: `:405-440`

For exact files/directory:

- status **shape does not change**;
- `files` and `bytes` change dynamically;
- inventory gains one row per resolved file;
- the remote run gains one object per unique inventory row;
- `latest.json` shape remains unchanged and still advances only after verification.

Measured on the current filesystem:

- four exact files: 4 files / 1,201,388 bytes;
- ten timestamped snapshot/coverage files: 10 / 37,259,301 bytes;
- whole `app/data/league_snapshots` directory: 12 / 44,745,860 bytes (the ten timestamped files plus two tracked latest aliases);
- four exact files + whole directory: 16 / 45,947,248 bytes.

Against the current marker (260 / 986,794,481), a same-instant whole-directory run would nominally be 276 / 1,032,741,729. These are **observations, not assertions to hard-code**: sources can change before a run.

### C. Contract tests

Direct owning tests:

1. `tests/contract/test_horizon0_backup_red.py`
   - manifest shape/type/path safety;
   - required absence and optional behavior;
   - stable non-DB copy;
   - exact remote keys;
   - restore-hash rejection and latest-pointer ordering;
   - marker behavior.
2. `tests/contract/test_backup_directory_red.py`
   - recursive regular-file expansion;
   - member path preservation;
   - symlink rejection;
   - missing/not-a-directory failure;
   - the important current rule that an **empty existing required directory is a successful zero-unit inventory**.
3. `tests/contract/test_backup_manifest_anti_rot_red.py`
   - committed-manifest coverage and reasoned exclusions;
   - currently scans only present `app/data/**/*.db` plus model-registry references;
   - does **not** mechanically cover the four new ignored file classes or the snapshot families.

Tests that read the real manifest and belong in the regression run, but do not pin its total count/bytes and should not need expectation edits:

- `tests/contract/test_market_divergence_ops_scheduler.py:106-116`
- `tests/contract/test_league_snapshot_capture_red.py:209-212`
- `tests/contract/test_h2_increment0_asset_pipeline_red.py:45-56`

No test found pins the current production totals `260` or `986,794,481`. Existing count/byte assertions are fixture-derived or zero-inventory checks.

### D. Standing contracts

- `docs/governance/02-agent-operating-loop.md` — standing offsite-backup law: no deletes, manifest coverage law, silence-is-not-success, manual runs David-gated, full restore drill required.
- `docs/superpowers/specs/2026-07-04-h0-0a-offsite-backup-design.md:12-27` — concrete paths, **no wildcards**; explicitly enumerated directories are allowed and inventoried.
- `docs/superpowers/specs/2026-07-06-02-amendment-offsite-backup-standing-workflow.md` — source amendment for the standing law and layered anti-rot boundary.

An exact-file/directory addition conforms to those contracts. First-class wildcard support changes the ratified “no wildcards” contract and therefore is not merely implementation detail.

### E. Counts, alarms, and user-visible health

- `files` and `bytes` are informational marker fields computed from the staged inventory.
- The remote verifier uses the current inventory dynamically (`len(inventory)+1`, per-object bytes, then per-object restored SHA-256); it has no fixed production count or byte ceiling.
- No production code currently consumes `app/data/ops/backup_status_latest.json`.
- `GET /api/system/capture-health` currently covers capture-store cadence only; backup health remains a named pending follow-up.
- The LaunchAgent exit code, stdout/stderr logs, and local marker expose a failure, but there is no automated user-facing staleness/failure alarm.

Thus, larger totals do not directly trip an assertion or alarm. Conversely, a run broken by the change can remain operationally unnoticed unless somebody checks the marker/job.

### F. Recent anti-rot directory-scope commit

Commit `a66e21c` changed only `tests/contract/test_backup_manifest_anti_rot_red.py`. Its helper grants recursive scope to **exclusions** that look directory-shaped (trailing slash or extensionless final segment), while file exclusions remain exact.

Adding `app/data/league_snapshots` as a required `kind: "directory"` does **not** interact with that exclusion logic: it is a covered entry, not an exclusion, and is outside the existing excluded subtrees.

Two caveats matter:

1. `_covered_manifest_paths` still records literal declaration paths only. It does not treat a covered directory as covering descendants. If anti-rot is extended to scan the new snapshot files, inclusion matching needs its own explicit file-vs-directory semantics; reusing exact-string matching would falsely call every member uncovered.
2. Production `exclude_paths` validation checks only exact equality with an entry path. It does not filter directory members by reasoned `exclusions`. A narrow `app/data/league_snapshots` directory is unaffected, but a broad parent such as `app/data` would accidentally absorb staging/assets/other excluded data. Do not use a broad parent as a shortcut.

A literal glob path also receives no help from the recent anti-rot change.

## 2. Failure modes, ranked by damage

### 1. CRITICAL — the expansion stops the entire daily backup, and nobody notices promptly

**Trigger:** a required exact file is absent/unreadable, a literal wildcard is declared as a required file, a directory path is absent/not a directory, or a new matched member is a symlink.

**Reproduced source behavior:** all entries are resolved before authentication/upload (`scripts/backup_irreplaceable_data.py:186-218`). Required absence raises `missing_required:*`; no payload object is uploaded. The marker becomes failed and `latest.json` does not advance. No application health route reads that marker.

**Damage:** the last verified remote run remains safe, but every subsequent currently-working backup is blocked. This is the failure to design against first.

**Control:** required-source preflight on the actual host immediately before rollout; RED showing no remote call/pointer advance on failure; explicit post-rollout marker/remote-pointer acceptance under David’s manual-run gate.

### 2. HIGH — the declaration looks required but is silently normalized to optional

The validator checks that `required` is a Boolean, but it does not enforce section/flag consistency:

```python
"required": bool(entry["required"]) and section == "required"
```

Therefore:

- an entry in `required` with `"required": false` becomes optional;
- every entry in `optional` is treated optional even if it says `"required": true`.

An absent optional path adds `missing_optional:*` to `failures` but the run can still finish `status=completed`, `sha256_verified=true`, and advance the pointer. With no marker consumer, this can present as a green backup while the new irreplaceable target is missing.

**Control:** RED rejecting section/flag disagreement before any copy, or a single-source schema with no duplicated requiredness. Do not rely on review to spot the mismatch.

### 3. HIGH — directory declaration succeeds while the intended snapshot family is absent or generation-paired incompletely

The runner supports directories, not family requirements. It deliberately accepts an empty existing required directory as a verified zero-unit inventory (`test_backup_directory_red.py:199-214`).

The snapshot producer writes four files sequentially: timestamped snapshot, latest snapshot, timestamped coverage, latest coverage. Directory members are enumerated once before staging. A run that begins between those writes can enumerate the new snapshot but not its coverage sibling, then complete successfully. A file created after enumeration is invisible to that run. Stable-copy/hash checks protect each **enumerated** member; they do not prove the directory’s intended generation set was complete.

The current directory always exists in a fresh checkout because its two `*_latest.json` files are tracked. Thus “required directory exists” cannot prove the ten ignored history files are present.

**Control:** state explicitly whether broad directory coverage is sufficient. If generation pairing/no-zero-family is required, it needs a pattern/generation contract, not merely `kind: "directory"`.

### 4. HIGH — overlapping declarations duplicate one destination and make the real verifier fail after upload

There is no duplicate resolved-path check. A directory plus an exact member produces duplicate inventory rows and uploads the same remote key twice. The real remote listing deduplicates by key, while `expected_objects = len(inventory)+1`; verification then fails and the pointer stays put.

This cannot silently corrupt the old backup, but it can turn an additive manifest edit into a full failed run after spending staging/upload time.

**Control:** RED that duplicate declarations and directory/file overlaps fail before authentication/upload with a named reason.

### 5. MEDIUM-HIGH — a fake/partial test proves declaration, not protection

Current anti-rot does not scan these classes. A test that only asserts the manifest contains `app/data/league_snapshots` or a literal path proves syntax, not:

- member resolution;
- inventory inclusion;
- exact remote object keys;
- remote restore;
- hash equality;
- pointer ordering.

The generic test seam can also inject `upload_verifier=lambda: True`, which is appropriate for unit isolation but is not end-to-end evidence.

**Control:** require fixture-level resolved-member assertions and a real-verifier fake bucket, followed by a David-authorized live acceptance check of the new remote objects.

### 6. MEDIUM — broad directory scope protects more than intended and grows without a family boundary

`kind: "directory"` recursively includes every regular file and rejects any nested symlink. Today `app/data/league_snapshots` is narrow (12 files), so this is tractable. Tomorrow any unrelated large/transient file or symlink under that directory changes backup behavior automatically.

This is the minimum code-free way to cover future snapshot runs, but it must be described as **whole-directory protection**, not as support for two globs.

Storage retention is outside this review and remains David’s decision.

### 7. MEDIUM — stable-copy behavior can fail a run on active writes; it is unlikely to upload a torn enumerated file

For non-SQLite files the runner fingerprints source, copies it, fingerprints again, retries once if changed, then fails `unstable_file:*`. This applies to the append-only JSONL and every directory member.

- An append during copy normally changes the before/after fingerprint and triggers retry/failure.
- An append after the second fingerprint yields a valid point-in-time prefix, not a torn staged copy.
- The producer has no cross-process backup lock, so sustained appends can exhaust the two attempts and block the whole run.
- Direct `write_text` snapshot updates can likewise produce bounded instability.

This risk is real but lower than directory-enumeration omission. The existing stable-copy gate is materially protective.

### 8. MEDIUM-LOW — added bytes extend a backup already taking about an hour

The current marker spans `14:15:00Z` to `15:14:31Z` for 986,794,481 bytes/260 files. Whole-directory coverage adds about 45.95 MB/16 files today. There is no coded duration/byte alarm, but every payload is uploaded and then downloaded for full verification, so wall time and transfer scale in both directions.

No fixed threshold will trip; the operational risk is a longer vulnerability window and greater overlap probability with writers/jobs.

### 9. LOW but worth recording — remote inventory content itself is not restored/hash-verified

The verifier requires one extra `run_inventory.json` object by object count, but downloads/hashes only payload files. Payload protection is still genuinely verified. Acceptance evidence should separately read the remote inventory and confirm the new paths/hashes, rather than assuming the inventory upload is correct because payload verification passed.

## 3. RED-first verification shape

The eventual plan should not ask David to approve based on a green manifest diff. It should require this sequence.

### Phase 1 — prove today’s boundary red

1. **Glob rejection RED**
   - `kind: "glob"` is rejected as malformed before any remote call.
   - `kind: "file"` with `*` is treated as a literal absent path: required fails the whole run; optional can complete with `missing_optional`.
   - This prevents a reviewer from mistaking wildcard-looking JSON for coverage.
2. **Requiredness-consistency RED**
   - required-section/false and optional-section/true must fail schema validation, not be normalized.
3. **Overlap RED**
   - exact duplicate and directory-plus-member overlap must fail before auth/upload.
4. **Snapshot-directory RED**
   - a fixture containing multiple timestamped snapshot/coverage pairs plus latest aliases resolves to the exact expected paths once each;
   - a file added before enumeration is included;
   - a file added after enumeration demonstrates the current omission boundary;
   - symlink and disappearing-member cases fail named and do not advance the pointer.
5. **Generation-shape RED, if requirements demand it**
   - latest-only, snapshot-without-coverage, coverage-without-snapshot, or zero timestamped matches must fail.
   - If the chosen manifest shape cannot express this, the plan must say so and not claim the guarantee.

### Phase 2 — prove the fix offline, end to end

Using temp sources and a fake object store that serves real bytes:

1. Stage every legacy fixture and every new target.
2. Assert each new source appears exactly once in `backup_run_inventory.v1` with contemporaneous bytes/SHA-256.
3. Assert each uploads to `runs/<run_id>/<repo-relative-path>` (no recursive-layout ambiguity).
4. Assert remote list count and bytes equal the unique inventory.
5. Download **every** new object and compare bytes/SHA-256.
6. Read remote `run_inventory.json` and confirm it contains the same new paths/hashes.
7. Assert marker `files`/`bytes` equal the staged inventory dynamically; do not pin today’s live totals.
8. Assert `latest.json` advances only after all verification.
9. Inject one missing/corrupt new remote object: marker failed, `sha256_verified=false`, prior latest pointer unchanged.
10. Inject one absent required new source: zero payload uploads and prior latest unchanged.
11. Re-run the pre-existing contract suite to prove legacy files, no-delete behavior, and pointer/marker contracts remain intact.

This is what proves an entry is **covered**, rather than merely declared:

`source resolved → stable staged bytes → inventory row → exact remote key → remote list parity → restored SHA-256 match → verified marker → pointer advance`

### Phase 3 — actual-host acceptance (David-gated)

Committed tests cannot depend on gitignored local artifacts, so CI cannot prove the actual ignored bytes are offsite. After code/config review and only with David’s authorization:

1. Read-only preflight immediately before the run:
   - all four exact files exist/readable;
   - capture the current intended snapshot member list, bytes, and hashes;
   - confirm no resolved overlaps and no symlinks.
2. Run the normal backup/restore drill.
3. Require:
   - `status=completed`, `sha256_verified=true`, no missing-optional warning for protected items;
   - remote latest points to that run;
   - remote inventory explicitly contains all four exact paths and every intended snapshot member;
   - remote list count/bytes reconcile to inventory;
   - downloaded copies of **all newly protected objects** hash-match the run inventory;
   - at least one pre-existing SQLite and one pre-existing non-DB object also restore/hash correctly, proving the old protection path still works.
4. Record actual duration and totals as evidence, not permanent thresholds.

Anything less proves configuration intent, not offsite protection.

## 4. Globs and growth — plain ruling

### What is supported today

- Exact files: **yes**
- SQLite files: **yes**
- Recursive whole directories: **yes**
- Glob/pattern entries: **no**
- Include/exclude patterns within a directory: **no**
- Required minimum match count: **no**
- Snapshot/coverage generation pairing: **no**

`_ENTRY_KINDS` accepts only `sqlite`, `file`, and `directory`. A wildcard inside a file path is not expanded. A required literal wildcard breaks the run; an optional one can coexist with a completed marker.

### Minimum honest options

1. **Fastest durable, code-free option:** four required exact files plus required whole-directory `app/data/league_snapshots`.
   - Covers current and future regular files automatically.
   - Also covers two tracked latest aliases and any unrelated future file in that directory.
   - Does not enforce that a timestamped family exists or that snapshot/coverage pairs are complete.
   - Must be described as whole-directory coverage.
2. **Narrowest manifest-only option:** exact-enumerate the ten current timestamped files.
   - Precisely covers today’s bytes.
   - The next run is unprotected until another manifest change, so it does not satisfy automatic growth coverage.
3. **True family-selective option:** add a first-class pattern/generation schema and runner behavior.
   - This is the only honest way to claim two glob families with required zero-match and pairing semantics.
   - It is the riskiest option and should be isolated from the four immediate exact-file additions.

Do not encode `*` in a current `file` entry and call it coverage. Do not use a broad `app/data` directory to simulate globbing; production member expansion does not apply the reasoned exclusions and would absorb unrelated/excluded paths.

## Recommendation to Tower

The change is somewhat riskier than “add six manifest rows,” chiefly because patterns do not exist, directory success can conceal missing family members, and backup-health failure is not automatically surfaced. It is still worth doing.

Put a **small safe plan** in front of David:

- immediate four exact files;
- a deliberate yes/no ruling on whole `app/data/league_snapshots` coverage versus family-selective semantics;
- REDs for requiredness mismatch, overlap, real member resolution, corruption/missing-object pointer hold, and legacy regression;
- David-gated live proof of the actual new remote objects.

Do not combine first-class glob implementation, retention policy, writer refactoring, or backup-health UI wiring into the immediate protection step.
