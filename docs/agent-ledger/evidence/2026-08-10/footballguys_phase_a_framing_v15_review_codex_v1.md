# Phase A framing v15 — Codex round-15 review

Date: 2026-08-10 11:49 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v15.md`  
Submitted and reproduced SHA-256:
`8d3be7a4206f7fae63666836747aa55acb233c5b0ff0fd3b64ffeb80e8a08c70`  
Measured size: 775 lines / 64,227 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — four findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v15 in full and diffed v14 to v15. All five round-14 disposition blocks are present in the
   live sections.
2. Recomputed the artifact SHA and size above.
3. Re-ran the forbidden-phrase sweep. The two retired formulations remain absent from live
   instructions.
4. Rehashed the two embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
5. Cross-checked the conditional-store rule against the retained state table and its explicit
   receipts→observations / observations→receipts coexistence contract.
6. Inspected the actual backup mechanism and manifest schema. A `kind="sqlite"` manifest entry
   names the main database; `backup_irreplaceable_data.py` uses SQLite's online backup API to make
   one coherent staged database. It does not copy live `-wal`/`-shm` files as independent payloads.
7. Rechecked the surface contract against the product register and `ShellStatusDrawer.tsx`.
   Placement and pill semantics remain aligned, but the option-3 “no data retained” copy is not
   truthful under the standing crash-residue contract (finding 2).

## Findings

### 1. Critical — option 3 store nonexistence contradicts the standing retention-mode coexistence state

Lines 379–387 say that under option 3, `objects/` and `receipts.db` **DO NOT EXIST**. Lines 684–687
render option-3 observations with an older retained receipt, and lines 751–755 explicitly make
“receipts then observations, or the reverse, across a David retention change” a first-class state.

Those cannot all be true. If David first selects option 1/2 and later selects option 3, older raw
objects and receipts must remain available, covered, and readable for the preserved
`latest_analysis_ready` state. Deleting them would be destructive and falsify the older-AR copy;
refusing their existence would make the accepted coexistence rows unreachable.

Required closure: distinguish **write mode** from **historical store presence**. In an option-3-only
history, no object/receipt store is created. A transition from 1/2 to 3 stops new raw publishes and
receipts but preserves existing objects and receipts read-only under their existing coverage;
transitioning back resumes writes only after the selected coverage still passes. Add both
transition directions with older AR, asserting no deletion, no new option-3 receipt/object, stable
AR identity, and truthful copy.

### 2. High — option 3 can display “no data retained” while a crash-resident paid ZIP remains on disk

The state table says option-3 observations render “metadata only — no data retained.” But the
single-snapshot lifecycle stages the intact archive under every mode, and the post-crash matrix
explicitly permits a partial or complete staging file to survive until the next intake sweep. If
the process crashes after staging under option 3, raw provider bytes can remain for days while the
surface continues to assert that no data is retained.

Calling the file transient or excluding it from the backup manifest does not make the on-disk bytes
absent. This is an honesty defect, not merely a cleanup caveat.

Required closure: give option 3 a storage mechanism whose crash state earns the copy—for example,
create and immediately unlink an option-3 staging entry while holding its descriptor so process
death reclaims it, with no canonical publish path—or weaken the copy to the exact durable fact
(`no archive committed` / `raw archive not retained as a committed object`). Add crash injection
during and after option-3 staging, then assert both directory contents and rendered copy.

### 3. High — “database plus sidecars” does not match the governed SQLite backup mechanism

Lines 381–394 model each SQLite store as its main DB plus `-wal`/`-shm` sidecars and require
coverage for the set. The actual backup manifest uses one `kind="sqlite"` entry for the main
database, and the backup runner opens the live database read-only and calls
`sqlite3.Connection.backup()` to produce one transactionally coherent snapshot. It does not back
up WAL/SHM files independently—and doing so as ordinary files can produce an inconsistent restore.
The artifact also never freezes journal mode, so a rollback-journal implementation may create
`-journal` rather than the named sidecars.

Required closure: distinguish Git ignore coverage from backup coverage. Ignore every possible
runtime SQLite companion narrowly. For offsite protection, pin one main-DB manifest entry with
`kind="sqlite"` per logical database and require the existing SQLite backup path; do not require
ephemeral sidecars as separate backup payloads. Freeze the journal mode or explicitly support both
WAL and rollback artifacts. RED must restore the staged SQLite backup and verify committed rows
from a live-WAL source; a file-copy mutant and a sidecar-required-on-clean-shutdown mutant must fail.

### 4. Medium — the claim that every runtime location is pinned is still false

The object root and database names are now concrete, but the load-bearing lockfile remains only “a
fixed name” beneath `intake/`; no filename is supplied. `semantics.db` and `observations.db` use
“+ sidecars” rather than a closed sidecar/journal-mode set. That leaves the exact paths required by
the ignore controls, lifecycle-lock identity test, manifest/exception register, and cleanup tests
to implementation choice.

Required closure: name the lock path (for example, `intake/lifecycle.lock`) and staging directory
exactly. After resolving finding 3, enumerate the runtime SQLite files that may exist under the
chosen journal contract and separately state which are ignored versus which logical main database
is backed up. The “every runtime location” test must compare the frozen set against both the ignore
rule and the conditional retention mode.

## Standing disposition

All five round-14 repairs are present, including the ignore-first ordering, concrete object/database
locations, coverage-before-write, a real spawn abstraction boundary, and actual-tree bootstrap.
The blockers are confined to the newly explicit conditional storage model: it erases an already-
accepted coexistence state, overstates option-3 cleanup, and misstates SQLite backup/sidecar
semantics. Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8
retention word; Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered
hypothesis **UNDER TEST** with no result and is unrelated.
