# Footballguys `adp.csv` pilot framing v8 — Codex round-7 review

Date: 2026-08-10  
Layer: Layer 1 ingest framing, with a Layer 2 identity dependency  
Reviewer: Codex, independent review / RED-authoring lane  
Verdict: **NOT CLEAR — one destination-enforcement finding**

This verdict does not open RED, build, comparison, intake, storage, or provider contact. Horizon and
cohort gates remain failed; ingestion RED remains closed.

## Submitted artifacts verified

- framing v8: `a165bc7bd43282da7656eb01be006e7ba202fad40e30c3ea2e4464e3cffd51f0`
- generator v7: `9a7f72485d631805fae8869408dd74ad62914c6a9e624d66d81271884e4ee4bd`
- minimized census v8: `0222c764a7835305cd5b7c9b559651584c985a2b11592bc095ead6ad4e1f225b`,
  11,918 bytes
- all three are untracked; the framing's exact three-file commit-intended boundary is internally
  consistent, and the full output is separated as scratch-only / never commit-eligible.

## Passing checks

1. Regenerated minimized output is byte-identical to the submitted artifact: `0222c764...`, 11,918
   bytes.
2. Regenerated full output under `/private/tmp` while `TMPDIR` pointed at the repository is
   byte-identical to the registered target: `9666169bea8a457248382e627d4f5cc8df130289d98c4ecab48bc3617558a108`,
   271,958 bytes.
3. The same hostile `TMPDIR` did not widen the allowlist: a repository target and a home-directory
   target were both refused, with no output file produced. The effective fixed root set was exactly
   `('/private/tmp',)` after macOS path resolution.
4. The full output has 608 rows, 608 distinct source ids, one uniform 15-field schema, and the
   truthful scratch-only status. The minimized output points to framing v8 §5 and generator
   `fbg-identity-census/7`, contains no per-mapping rank fields, and is structurally identical to
   the submitted JSON.
5. The seven substantive blocks named in the framing are byte-equal between v7 and v8: both totals,
   guard evaluation, top-window counts, both ID commitments, and all 34 wrong-human mappings.
6. Ruff still reports the disclosed five cosmetic findings; this remains non-blocking and outside
   the governed `ruff check src app` scope.

## Round-7 finding

### R7-1 — High: a pre-existing hard link defeats the scratch-only destination guard

The guard validates only the pathname after `Path.resolve()` and then overwrites that path with
`Path.write_text()` (`footballguys_identity_census_generator_v7.py` lines 229–245). Resolution
closes symlink and `..` spellings, but it cannot reveal another hard-link name for the same inode.

Safe positive reproduction, using a harmless sentinel and **not** the provider-derived output:

- created one sentinel file in the repo and a hard-link name for it under `/private/tmp`;
- `stat` showed the same inode (`12912604503`) for both names;
- the scratch pathname resolved to `/private/tmp/codex_fbg_v8_hardlink_probe_sentinel.txt`;
- `Path.samefile()` proved it was the repo file;
- the current repo-containment predicate returned false and the scratch allowlist predicate returned
  true.

Therefore a `--full` run targeting that pre-existing scratch alias would pass both checks and
`write_text()` would replace the contents of the durable repo inode as well. That contradicts the
framing's claim that the writer refuses the repository and every other durable root. The probe files
were deleted after inspection; no provider-derived data was written through the alias.

Required repair: do not overwrite an existing output path. Create the output atomically and
exclusively (for example, an exclusive-create file descriptor after validating the resolved parent),
then write through that descriptor. Do not use a separate `exists()` check followed by
`write_text()`, which leaves the same check/write race.

Required closeout controls:

1. pre-existing hard-link alias in `/private/tmp` to a durable sentinel → **REFUSED**, durable
   sentinel byte-identical;
2. pre-existing ordinary file in `/private/tmp` → **REFUSED**, byte-identical;
3. new pathname under `/private/tmp` → **ALLOWED**, registered full hash reproduced;
4. hostile `TMPDIR` T1–T3 and the existing D1–D7/pin controls remain green.

## Standing disposition

**NOT CLEAR on v8.** This is one bounded enforcement defect; it does not disturb any identity
measurement or reopen the comparison. Horizon FAILED, cohort floor FAILED, ingestion RED CLOSED,
comparison not opened, nothing committed.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
