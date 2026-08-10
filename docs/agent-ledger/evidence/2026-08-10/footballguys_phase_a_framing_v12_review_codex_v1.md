# Phase A framing v12 — Codex round-12 review

Date: 2026-08-10 11:32 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v12.md`  
Submitted and reproduced SHA-256:
`2384dd9b8dfe63b61c9338346bccff1e5a07eb5b4df765fc4b534a0c69e760c7`  
Measured size: 655 lines / 53,837 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — five findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v12 in full and diffed v11 to v12. All five round-11 dispositions are present in the live
   contract, not only in the disposition table.
2. Recomputed the artifact SHA and size above.
3. Rehashed the two embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Rechecked the full state/precedence contract, retention choices, archive-object boundary, and
   the unchanged surface composition contract. Drawer-only detail, neutral freshness pill, no
   global-health inheritance, and “refresh recorded” copy remain aligned; no new interface finding.
5. Ran two harmless lock falsification probes under a temporary directory: the exact submitted
   lock-path replacement sequence and an inherited-descriptor/process-exit sequence. No repository
   or provider bytes were mutated.

## Findings

### 1. Critical — the required lock-replacement RED is outside the threat model and false under the specified algorithm

Section 6 lines 270–288 correctly states that `flock` binds an inode and that conforming writers
never replace the persistent lockfile. It then requires: hold lock A, replace/alias the pathname,
start B, and prove B cannot enter. Those statements cannot all stand. Path replacement is the
non-cooperating namespace mutation v12 explicitly excludes, and the post-open pathname check does
not prevent a stable replacement from becoming B's internally consistent lock identity.

I ran the exact sequence. A opened, locked, and passed its post-acquisition pathname/inode check.
The path was replaced once and then left stable. B opened the replacement, acquired an exclusive
lock on its different inode, and passed the same check. Observed result:

`{a_postcheck_passed: true, b_postcheck_passed: true, distinct_inodes: true, both_enter_lifecycle: true}`

This directly falsifies the required RED. The claim at lines 327–328 that out-of-model mutation is
“detected after the fact by verification failures” is also too strong: this stable replacement
causes no verification failure at either process, and the prior verify/unlink counterexample can
delete a replacement without a guaranteed detector.

Required closure: choose the declared threat model consistently. The smallest honest repair is to
retire the replacement/alias RED as out of model, retain the invariant that no conforming actor
mutates the lock entry, and replace it with an in-model overlapping-intake control that proves two
ordinary actors serialize on the persistent inode. Outside-model behavior must be stated as outside
all guarantees and only *potentially* detectable later. If replacement resistance is required, the
mechanism and threat model must instead change; the current postcheck cannot supply it.

### 2. High — the private `0700` namespace is load-bearing but never established or verified

The narrowed threat model depends entirely on the staging/lock root being a private directory owned
by the intake, yet v12 only asserts that property. It does not freeze how the root is created or
opened, reject a symlink root, verify through a bound descriptor that it is a directory owned by the
expected uid, or fail closed when its permissions are broader than `0700`. The later no-follow entry
checks do not repair a compromised root boundary.

Required closure: define the namespace bootstrap and load predicate—fixed path; no-follow directory
open; descriptor-bound `fstat`; directory type, owner, and exact accepted mode; refusal on symlink,
ownership mismatch, or broader permissions; and use of that verified dirfd for lock, stage, sweep,
and cleanup operations. RED needs at least a symlinked root, a world/group-writable root, and wrong
ownership. Until then, the condition used to exclude non-cooperating mutation is not executable.

### 3. High — “missing observation identity” both creates a valid-clock conflict and makes the record invalid

Lines 515–521 say a same-second observation with differing **or missing** archive identity enters
`same_instant_conflict`. That conflict uses the tied instant as the certain freshness clock. But
lines 522–527 say invalid provenance or absent bytes is `failed` and advances nothing, while §8
defines every `refresh_observation` as carrying archive hash, bytes, and declared provenance.
Missing identity therefore cannot simultaneously be a valid clock candidate and evidence of a
readiness conflict.

Required closure: validate observation identity before clock-candidate selection. A record missing
archive hash, byte count, or required provenance is an invalid attempt and must not enter the
same-instant equivalence cohort or advance freshness. Add controls for one valid plus one
missing-identity observation at the same second, two missing-identity observations, and both with
and without a prior valid clock; assert the invalid records never create or move the clock.

### 4. Medium — “kernel lock release on process death” is false when a descendant inherits the locked descriptor

Line 280 uses process death as the complete staleness rule. A forked child inherits the open file
description and can keep the `flock` alive after the original intake process closes its descriptor
or exits. My probe acquired the lock, forked a child that retained the descriptor, closed the
parent's copy, and confirmed a new acquisition remained blocked until the child exited. It then
became acquirable.

Required closure: state the real lifecycle—release occurs only after the last inherited reference
to the locked open file description closes—and freeze the process model. If intake must not fork
while holding the lock, say so and test it; if it may, require child-side closure. `O_CLOEXEC` is
useful for exec but does not by itself prevent fork inheritance. RED should cover parent exit/close
with a live inheriting child and prove the selected policy cannot strand the source in
`intake_busy` unexpectedly.

### 5. Medium — the sweep table is not a function for grammar-nonmatching symlinks, hard links, directories, or special files

Lines 380–390 give type dispositions—symlinks and multi-link regular entries are unlinked, while
directories/special entries are refused—and then say every grammar-nonmatching name is untouched.
A grammar-nonmatching symlink or multi-link regular entry matches two rows with different outcomes;
the text does not state whether name classification or type classification wins.

Required closure: make the evaluation ordered and total. The conservative contract is: first test
the frozen stage-name grammar; every nonmatching name is reported and untouched regardless of type;
only a matching name proceeds to the no-follow type table. Add nonmatching regular, symlink,
multi-link, directory, and special-entry controls in addition to the existing matching-name probes.

## Standing disposition

All five round-11 repair directions are present, and narrowing the cleanup threat model is the right
kind of remedy. The remaining defects are in its operational boundary: one required control demands
excluded and unenforceable behavior, the private-root assumption is not verified, observation
validation conflicts with clock selection, and two lifecycle functions remain underdefined. Plan
v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
