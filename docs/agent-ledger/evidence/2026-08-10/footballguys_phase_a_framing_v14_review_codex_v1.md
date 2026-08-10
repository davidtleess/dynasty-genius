# Phase A framing v14 — Codex round-14 review

Date: 2026-08-10 11:44 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v14.md`  
Submitted and reproduced SHA-256:
`60a681dabe9fd8490e89ff0d810618e2d25db0b0a56298c533ccfe4a0084cfa2`  
Measured size: 725 lines / 59,872 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — five findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v14 in full and diffed v13 to v14. All four round-13 disposition blocks are present in the
   live sections.
2. Recomputed the artifact SHA and size above.
3. Ran the promised negative sweeps. The unconditional process-death formulation is absent. The
   phrase “detected after the fact” occurs only in quoted disposition/retirement history, not as a
   live instruction. The two stale-sibling repairs therefore pass.
4. Rehashed the two embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
5. Checked the new namespace against the real repository. The repo root, `app/`, and `app/data/`
   are all owned by `davidleess:staff` and mode `0755`. No Footballguys runtime path exists yet.
6. Ran `git check-ignore -v` against representative staging, lock, object, and receipt paths under
   `app/data/footballguys/`. It returned no match for any path: all are currently commit-eligible.
   The repository's existing `.gitignore` comment explicitly requires a deliberate per-source rule
   rather than a blanket future-vendor ignore.
7. Rechecked the surface contract against the product register and `ShellStatusDrawer.tsx`:
   drawer-only detail, neutral freshness pill, no global-health inheritance, and “refresh recorded”
   copy remain aligned. No new interface finding.

## Findings

### 1. High — the newly pinned paid-data namespace is not gitignored

V14 names `app/data/footballguys/intake/` and stages the intact paid ZIP there. That path is under
the Git working tree, and the current ignore file has no Footballguys rule. Independent
`git check-ignore -v` probes for a staging ZIP, lockfile, candidate object, and receipt database all
returned no match. A crash-resident raw ZIP is therefore visible to `git add -A` and can be committed
before any content-store or manifest control has a chance to help.

Mode `0700` is not a Git boundary: Git runs as the same uid. This repository deliberately removed a
blanket future-vendor ignore and records that each new source must receive an explicit, considered
rule (`.gitignore` lines 127–135).

Required closure: require a narrow Footballguys runtime ignore rule to land before the first
namespace or staging write, covering every raw/staging/object path and SQLite sidecar that the
selected retention mode can create without pre-ignoring unrelated future data. RED needs positive
`git check-ignore` controls for staging/provider bytes and every durable runtime file, plus a
negative control proving commit-intended evidence/config paths remain trackable.

### 2. High — only lock/staging is named; the canonical object and receipt store remain floating paths

The new path contract names the lockfile and `staging/` beneath
`app/data/footballguys/intake/`. Section 6 still publishes to an unnamed “canonical content path”
and commits to an unnamed SQLite ledger. Neither the object root nor the receipt database filename
is present anywhere in the self-contained artifact.

That prevents RED from asserting three load-bearing properties: staging and publication are on the
same filesystem, the content-addressed pathname is derived canonically from the full archive hash,
and all private durable files fall under the intended ignore/backup boundary. An implementation can
choose arbitrary locations while still citing this framing.

Required closure: pin conditional runtime locations for the retained-object root, receipt SQLite
database, and SQLite `-wal`/`-shm` companions (or explicitly state that these do not exist under
option 3). Freeze the hash-to-path grammar and assert same-device staging/publication before the
no-replace operation. Add a cross-device mutant and exact-location controls.

### 3. High — v14 claims receipt-manifest coverage that §6 does not contain

Lines 344–346 say “the receipts/observation ledgers keep their own §6/§8 coverage.” Section 8 does
require manifest coverage before the first observation-ledger write. Section 6 contains no
corresponding manifest-or-exception rule for the receipt SQLite database, and no rule says the raw
object manifest entry or David-scoped exception must predate the first canonical publish.

This is a false live pointer and a regression from the earlier explicit boundary: manifest entry or
named exception before the first protected write. A transactionally sound receipt database is
still non-regenerable operational provenance, and option 1's raw object store is irreplaceable paid
history.

Required closure: restore the ordering rule in the self-contained artifact for every conditional
durable store: raw objects, receipt DB including sidecars, semantic assertion/evidence storage, and
the observation ledger. The selected manifest entry or David-granted exception must already exist
before namespace code can perform its first protected publish/transaction. Add a mutant that writes
each store one step before its coverage exists.

### 4. High — the “executable guard” remains an assertion without a closed enforcement surface or independent oracle

Lines 325–331 say the lock object's scope asserts that no `fork`, `posix_spawn`, or `subprocess`
call occurs and that mutating/removing the guard must fail. Python/POSIX provides no ambient
lock-scope hook that automatically observes every spawning route. The artifact does not say which
functions are wrapped, how thread-global patching is avoided, how `multiprocessing`/process pools
or native calls are treated, or what independent test operation must be rejected. A mutant suite
can exercise one wrapper while broken production code uses another route and leaks the descriptor.

Required closure: choose a real enforcement boundary. One viable contract is a single injected
process-spawn abstraction used by all in-scope production dependencies, with direct spawning APIs
barred by a static/import boundary and a RED that calls the production abstraction while locked;
removing the lock-state check must allow the call and fail the oracle. Another is a registered
child-side close mechanism plus explicit tests. Keep `O_CLOEXEC`, but do not call the scope guard
executable until the interception point and its independent fail/pass behavior are frozen.

### 5. Medium — first-run bootstrap is not closed against the real parent modes or concurrent creators

The actual repo root, `app/`, and `app/data/` are mode `0755`, while v14 says every component is
opened and “the intake components” must be exactly `0700` without enumerating which components that
phrase covers. A literal implementation may reject the real tree or chmod a shared tracked parent;
an intended implementation likely checks only the newly private nodes, but that is not the written
predicate.

Bootstrap also happens before the lifecycle lock exists. Two ordinary first-ever intakes can both
observe a missing component and race at `mkdirat`; the contract does not state that `EEXIST` means
reopen-no-follow-and-verify rather than failure or replacement.

Required closure: enumerate the predicate per component: trusted existing repo/`app`/`app/data`
parents are opened no-follow and owner/type checked without chmod; the exact private nodes requiring
`0700` are named. Use the actual 0755 tree as the positive control. Add two simultaneous missing-
root creators and require safe `EEXIST` convergence to one verified namespace before ordinary lock
contention begins.

## Standing disposition

The four round-13 repairs are present, and both forbidden-phrase sweeps pass. The remaining defects
were exposed by choosing a concrete repository path: private paid bytes are presently commit-
eligible, durable paths/coverage remain incomplete, the spawn guard lacks an enforceable boundary,
and first-run bootstrap has no real-tree/concurrency oracle. Plan v4 remains CLEAR. No Phase A RED
opens before a fresh CLEAR **and** David's §8 retention word; Phase B waits; Phases C/D remain
closed. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is
unrelated.
