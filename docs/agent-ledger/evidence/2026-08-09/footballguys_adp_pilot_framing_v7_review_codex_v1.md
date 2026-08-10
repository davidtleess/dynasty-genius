# Footballguys `adp.csv` pilot framing v7 — Codex round-6 review

**Date:** 2026-08-09  
**Lane:** Codex, independent technical reviewer / prospective RED author  
**Framing reviewed:** `footballguys_adp_pilot_framing_claude_v7.md`  
**Framing SHA-256:** `e18685d22729ea65c13c19fec3e7b1383c1cf02b2ba73560a2864bcd1a2af8b0`  
**Generator reviewed:** `footballguys_identity_census_generator_v6.py`  
**Generator SHA-256:** `1e68600f22efb546f790bdd9d0feb0b8c0906dc73bce303d4853fc506a1b926c`  
**Minimized census reviewed:** `footballguys_adp_identity_census_claude_v7_minimized.json`  
**Minimized census SHA-256:** `00c423d86b2f84d90cc1ce842e1ea5b0be09bf886b1c31a55a6283199795648e`  
**Disposition:** **NOT CLEAR.** All four round-5 repairs work on the submitted execution path and
the census remains unchanged. One environment-controlled destination bypass and two bounded
post-fix sweep defects remain. Horizon and cohort gates remain failed; ingestion RED stays closed.

No provider contact, intake, durable raw store, model input, RED, commit, push, or new redundancy
comparison was performed by this lane. The generator was run only against pinned scratch inputs.

## Independent checks that passed

- All three submitted hashes, byte counts, and untracked-state claims match.
- Minimized regeneration is byte-identical: 11,918 bytes, SHA-256
  `00c423d86b2f84d90cc1ce842e1ea5b0be09bf886b1c31a55a6283199795648e`.
- Full regeneration is exact: 271,896 bytes, SHA-256
  `d1b64e69922410cf85c799b5365db7f1b72ae637071236c96fafce11296691aa`.
- File-wide and SF verdict ladders match. Every substantive minimized block is byte-equal to v5:
  both totals, guard evaluation, top-window counts, both ID commitments, and all 34 mappings.
- Current-process full writes to repo, home, and Downloads all refused with exit 1 and produced no
  file. `/private/tmp` succeeded.
- `Path.resolve()` precedes both containment checks; the submitted symlink-evasion logic is sound
  for existing symlinks.
- Full metadata now says `scratch-only; NOT commit-eligible; NOT committed`; minimized metadata
  remains commit-intended. The minimized expected-output pointer correctly names v7 §5 and generator
  version 6.
- The disagreement clause is deleted. The five Ruff findings remain cosmetic and non-blocking.

## Findings

### 1. `SCRATCH_ROOTS` trusts environment-controlled `TMPDIR` / `TEMP` / `TMP`

The positive allowlist is not actually fixed to system roots:

```python
Path(tempfile.gettempdir()).resolve()
```

Python's own `tempfile._candidate_tempdir_list()` tries `TMPDIR`, `TEMP`, and `TMP` first, then OS
locations, and even the current directory as a last resort. A writable durable directory supplied
through one of those variables therefore becomes allowlisted. Directly setting `TMPDIR` to the
repository made the generator's `SCRATCH_ROOTS` contain the repository; the explicit repo check
saved that one named location, but no equivalent check saves Downloads, Desktop, a synced drive, or
another writable durable root. The managed sandbox prevented Downloads from passing tempfile's
writability probe during this review; an ordinary user process can write there, so that sandbox
denial is not a generator control.

This recreates the exact bypass the allowlist was meant to close: for example, an unsandboxed run
with writable `TMPDIR=~/Downloads` can classify Downloads as scratch.

Required repair: derive allowed roots from fixed physical paths independent of environment (the
fixed resolved `/tmp` / `/private/tmp` root is sufficient for this pilot), or validate every
environment-derived candidate against a separately fixed physical-temp ancestry before including
it. Add a mutation control that sets `TMPDIR` to a writable durable non-repo directory and proves a
full write still refuses.

### 2. The framing still globally labels non-commit-eligible artifacts `COMMIT-INTENDED`

R5-3 fixed the generated full artifact's `status`, but the framing's sibling claims were not swept:

- the scope banner says **every artifact**—including censuses, framings, and superseded result—is
  `COMMIT-INTENDED`;
- §1.5 repeats that **every artifact is commit-intended**; and
- §5's heading says `the only commit-intended set` while its table includes the full scratch-only
  census target.

Those statements contradict the same document's `NOT commit-eligible` full status and its
`superseded ... NOT commit-intended` register. This is the fourth sibling-label miss in the thread,
not merely style: a reader following the top scope declaration can land the exact derivative the
conditional status exists to protect.

Required repair: state the set precisely. Only the v7 framing, generator, and minimized JSON are
repo-eligible/commit-intended. The full output is scratch-only and never commit-eligible; superseded
exhibits are retained locally but not commit-intended. Split §5 into the commit-intended subset and
the scratch-only expected-output target rather than placing both under one heading.

### 3. The generator header still points to framing v5, and one census count is wrong

The generated JSON's provenance pointer is fixed, but generator line 5 still says its outputs are
`cited in framing v5`; this generator version is shipped by v7. Framing §1.3 also says `all three
censuses` and then lists `v4 → v5 → v6 → v7`—four censuses.

These do not change execution, but they are direct provenance/count statements in the evidence
chain and should be corrected in the same post-fix sweep. The generator header should name v7 (or
the `CURRENT_FRAMING` constant), and `three` should become `four`.

## Ruling

**NOT CLEAR**, limited to findings 1–3. All four submitted round-5 repairs otherwise pass. Required
next revision is mechanical:

1. remove environment-controlled directories from the scratch allowlist and mutation-test `TMPDIR`;
2. correct every global commit-intended declaration and split the §5 register; and
3. repair the stale generator-header pointer and three/four count.

The decision state remains: **horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, no
comparison opened, nothing committed.** H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
