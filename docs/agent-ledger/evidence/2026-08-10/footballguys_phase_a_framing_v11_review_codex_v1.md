# Phase A framing v11 — Codex round-11 review

Date: 2026-08-10 11:24 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v11.md`  
Submitted and reproduced SHA-256:
`56a807dd47c94a257bc16cf8acd11eabd78e2b19dc530852df1692cdf4c632d3`  
Measured size: 600 lines / 48,933 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — five findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v11 in full and diffed v10 to v11. All five round-10 dispositions are present in the live
   sections, not only in the disposition table.
2. Recomputed the artifact SHA and size above.
3. Rehashed the two embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Checked the state table and precedence text for the 10-day/31-day conflict split, older-AR
   disclosure, failed/invalid overlays, pill independence, and later-unique clearing. The round-10
   readiness/freshness correction is integrated consistently.
5. Checked the unchanged surface contract against `PRODUCT.md`, `DESIGN.md`, `DailyTape.tsx`, and
   `ShellStatusDrawer.tsx`: detail remains drawer-only, the pill is a neutral freshness count,
   Footballguys does not inherit into global health, and copy says refresh **recorded**, not
   downloaded. No new interface finding.
6. Ran three harmless filesystem falsification probes under a temporary directory:
   lock-path replacement, verify-then-unlink replacement, and a resolving orphan sweep. Each
   counterexample below was reproduced; no repository or provider bytes were used.

## Findings

### 1. Critical — R10-4 is still a check-then-unlink race; a pathname cannot become “the bound entry” by prose

At lines 289–297 the contract verifies the staging pathname against the held descriptor and then
unlinks the pathname. Those are two syscalls with a mutation window between them. The lifecycle
lock serializes cooperating intakes, but the required mutant itself permits a concurrent rename;
the contract therefore cannot use the lock to declare that mutation impossible.

Reproduced counterexample:

1. Open the staging inode and confirm `lstat(path).(dev, ino) == fstat(fd).(dev, ino)`.
2. Rename that verified entry aside.
3. Rename a sentinel into the staging pathname.
4. Call `unlink(staging_path)`.

Observed: the pre-unlink identity check passed, the sentinel's only directory entry was deleted,
and the verified inode survived under the displaced name. That directly falsifies v11's required
outcome that a replacement remains untouched and the verified inode does not leak. Section 6.5's
fresh-failure removal/quarantine has the same unnamed cleanup-identity problem.

Required closure: either narrow the threat model explicitly to lock-respecting writers and delete
the impossible concurrent-rename claim, or specify an implementable cleanup mechanism whose final
destructive operation cannot target a post-verification replacement. Do not call a pathname entry
“bound” unless the kernel operation is actually bound to that identity. RED needs the replacement
at the last possible boundary, after the final identity check and before deletion, for both reuse
and fresh-failure cleanup; the sentinel and verified inode dispositions must be asserted.

### 2. High — the new `flock` is not bound to a stable lock identity, so two intakes can both hold “the” exclusive lock

Lines 252–258 say only “an exclusive `flock` on a per-source lockfile.” `flock` locks an inode, not
a pathname. The contract does not freeze the lock directory, creation/open flags, symlink/hard-link
rules, file type/link count, replacement policy, or directory-entry identity.

Reproduced counterexample: process A opened the lock path and acquired `LOCK_EX`; the path was
renamed, a new file was created at the original path, and process B acquired `LOCK_EX` on that new
inode. The probe reported distinct inodes `12912622656` and `12912622657` with both exclusive locks
held. Both processes could now sweep and mutate the same source lifecycle.

Required closure: define a stable, private lock namespace and descriptor-bound lockfile contract
(no-follow open, regular-file/integrity checks, no replacement/unlink lifecycle, and an explicit
threat boundary), or use another mechanism that provides one stable serialization identity. RED
must hold lock A, replace/alias the lock pathname, start B, and prove B cannot enter the sweep or
staging lifecycle.

### 3. High — “safely removed” leaves the crash sweep able to follow a planted entry outside the staging boundary

Lines 338–339 define when the sweep runs but not what it may enumerate or how it deletes. “Reported
and safely removed” is not an executable predicate. A broken but text-conforming implementation can
resolve each orphan path and unlink the resolved target.

Reproduced counterexample: a staging entry was a symlink to a sentinel; a resolving sweep using
`entry.resolve().unlink()` deleted the sentinel target. The lifecycle lock does not help because the
entry can be crash residue or pre-planted before the lock is acquired.

Required closure: freeze the staging root and filename grammar, enumerate non-recursively through a
bound directory, inspect entries no-follow, never resolve or recurse, and state the behavior for
regular files, symlinks, hard links, directories, and special files. RED needs at least a symlink to
a sentinel, a multi-link regular file, and a directory/special entry; no outside target may be
opened, parsed, mutated, or deleted.

### 4. Medium — lock contention has two incompatible APIs and no reachable-state disposition

Line 256 says the second intake “waits **or** returns `intake_busy`.” That leaves RED and GREEN free
to choose different behavior. If `intake_busy` is recorded as the newest attempt, it is absent from
the claimed-total state function at lines 489–575; if it is not an attempt, that invariant is not
stated. An implementation could therefore surface it as a failed attempt and append failure copy,
or block indefinitely, while still pointing to this framing.

Required closure: choose a deterministic policy (or an explicit caller-selected policy with both
branches specified), including timeout/cancellation semantics. Freeze whether `intake_busy` is a
non-attempt control result; it should not mutate the attempt ledger, clock, AR, pill, or drawer copy
unless a deliberate table row says otherwise. The concurrency RED must assert the exact return and
the complete unchanged state.

### 5. Medium — equal-instant equivalence is undefined for two metadata-only observations

Lines 446–452 require `content_vintage_id` to decide equal-instant equivalence. Option 3 at lines
584–587 defines `refresh_observation` with archive hash+bytes and provenance, but no role records or
`content_vintage_id`. The existing acquisition-vs-observation mutant conflicts on retention mode,
so it does not answer observation-vs-observation. Two observations at the same second can therefore
either collapse or enter `same_instant_conflict` depending on an implementation's treatment of the
missing analytical identity, violating the claim that the table is a function.

Required closure: define the observation equivalence key explicitly. A conservative candidate is
to collapse only identical observation archive identity/provenance and make differing or missing
identity conflict; another defensible rule is possible, but it must be closed here. Add same-second
observation pairs with equal and unequal archive hashes in both append orders, asserting freshness,
readiness, copy, and AR.

## Standing disposition

The round-10 freshness/readiness correction, older-AR copy, and fresh/reuse crash split all stand.
The blockers are confined to the newly introduced serialization/cleanup boundary and one remaining
total-function gap. The governing state remains: no RED before a fresh CLEAR **and** David's §8
retention word; Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered
hypothesis **UNDER TEST** with no result and is unrelated.
