# Phase A framing v17 — Codex round-17 review

Date: 2026-08-10 12:00 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v17.md`  
Submitted and reproduced SHA-256:
`bd46868256a569328a1c70f627233c543c36b7b3eb357e71813920a59f9c827f`  
Measured size: 862 lines / 71,311 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — three findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v17 in full and diffed v16 to v17. All four round-16 repair blocks and claimed mutants are
   present.
2. Recomputed the artifact SHA and size above.
3. Rehashed the embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Traced both retention modes linearly through §6 rather than treating headings as control flow.
   The new B branch appears before—and therefore does not replace—the linked common staging step.
5. Traced every option-3 success, validation-refusal, process-crash, system-crash, and SQLite
   transaction-failure exit to descriptor, directory-entry, database, clock, and rendered-copy
   state.
6. Rechecked WAL establishment against the governed SQLite online-backup mechanism. The new
   before-schema/write establishment and reopen-refusal rules close round-16 finding 4.
7. Rechecked rows 11/11b/12/12b and overlay composition against the product register and existing
   in-flow status drawer. The referent-qualified copy closes round-16 finding 3.
8. Re-ran the forbidden wording sweep. The unqualified live “no data retained” formulation is
   gone; remaining hits are disposition history.

## Findings

### 1. Critical — the supposedly common prefix still performs Branch A's linked staging before Branch B

The disposition says §6 is a mode-neutral common prefix of steps 0–2 followed by two terminal
branches. The live order is different:

- lines 440–464 define Branch B and its own create/unlink/fsync/stream lifecycle;
- lines 477–481 then define common step 1, which creates another linked staging entry, streams the
  provider archive into it, and fsyncs it;
- Branch A does not begin until lines 496–497.

Step 1 cannot be common: linked create-and-stream is Branch A behavior, while option 3 requires
unlink-and-directory-fsync before the first byte. Reading the numbered flow top-to-bottom either
runs B before the alleged common prefix or makes option 3 run two creates and two source streams,
one of them linked. The surviving step-0 concurrency control at lines 359–362 also still requires
unqualified one-object/one-receipt convergence, despite the later statement that this invariant is
A-only.

This is the same additive-editing class v17 says it fixed, one structural level lower. A RED that
only asserts B1's internal syscall order can pass while production first executes the linked common
step.

Required closure: make only lock/namespace/coverage selection common. Put staging acquisition in
the mode branch:

- A1: create linked staging entry, stream/hash/fsync;
- B1: create, unlink, directory-fsync, then stream/hash anonymously;
- call one shared descriptor-bound validation/fact routine after either A1 or B1;
- continue to the already-separated terminal commits.

Scope every concurrency and convergence oracle by mode. Add a full call-trace oracle asserting
exactly one staging create and one source stream per intake; the mutant that runs A1 before B1 must
fail.

### 2. High — Branch B closes the descriptor only on the success path

B3 closes the anonymous descriptor after B2 validation and before B4 commit. Nothing requires
closure when B2 refuses because of a malformed archive, resource cap, missing role, CRC/hash
failure, schema failure, source read error, or any other exception. A long-lived process can
therefore retain the unlinked paid archive inode indefinitely after a rejected intake even though
no observation exists and the lifecycle lock may be released.

The current “still-open descriptor at observation commit” mutant exercises only the successful
path. Code that closes immediately before B4 but leaks on every validation exception passes it.

Required closure: descriptor cleanup is an unconditional `finally`-class invariant for every B
exit after creation, including B1/fsync refusal and all B2 failures. Keep B3's close-before-visible
ordering for success. RED each failure family while keeping the process alive, then assert the raw
descriptor/inode is gone, no observation committed, and clock/AR/copy are unchanged. Mutating away
the failure cleanup must fail.

### 3. Medium — the option-3 crash matrix confuses logical non-commit with an empty filesystem

Lines 456–460 say a B2/B3 crash leaves “nothing durable” and an observation-commit failure leaves
“nothing on disk.” In an option-3-only history, `observations.db` itself is durable. In a 1/2→3
history, older objects and receipts are deliberately preserved. A failed WAL-mode transaction can
also create or change SQLite main/WAL/SHM files without committing the observation. None of those
physical facts advances freshness, but they make “nothing on disk” false.

The safety property is narrower and stronger: no named/raw provider archive survives, no
observation row commits, and clock/AR/copy do not advance. Physical SQLite residue must be handled
by SQLite recovery and the governed backup path, not denied by the matrix.

Required closure: specify permitted residue per object class—raw archive, staging entry,
observation database/WAL/SHM, and pre-existing historical stores. Inject a real SQLite failure and
assert logical state after reopen plus raw-archive absence. A mock transaction whose only oracle is
directory emptiness must fail.

## Standing disposition

The round-16 copy and WAL findings are closed. The option-3 durability ordering is also correct
inside B1. The blocker is now control-flow integration: the linked staging step remains outside
Branch A, so v17 still does not define one executable path per mode. The two failure-state findings
ensure the eventual RED measures descriptor and database semantics rather than success-path prose.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
