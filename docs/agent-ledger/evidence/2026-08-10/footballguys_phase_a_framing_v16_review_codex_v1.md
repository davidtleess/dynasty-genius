# Phase A framing v16 — Codex round-16 review

Date: 2026-08-10 11:55 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v16.md`  
Submitted and reproduced SHA-256:
`a43711d295458f2da9a2260a236fa3dbbbff120263cfa286e9d247b8cd12c9b8`  
Measured size: 812 lines / 67,423 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — four findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Read v16 in full and diffed v15 to v16. All four round-15 disposition additions are present in
   the submitted artifact.
2. Recomputed the artifact SHA and size above.
3. Rehashed the two embedded canonical preimages directly from the fenced blocks:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Cross-read the option-3 exception against the numbered stage/publish/receipt lifecycle, the
   post-crash matrix, and the terminal state required before an observation becomes visible.
5. Checked the unlink-before-write claim against the artifact's own durability model. The contract
   fsyncs parent directories when directory-entry durability matters elsewhere, but does not make
   the option-3 unlink durable before provider bytes are written.
6. Rechecked the option-3 coexistence copy against the preserved read-only receipt/object history
   and the existing status-drawer honesty boundary.
7. Rechecked the WAL claim against the governed `kind="sqlite"` online-backup mechanism and the
   first-write coverage rule. Backup shape is now correct; journal-mode establishment is not yet a
   closed lifecycle.
8. Re-ran the retired-phrase sweep. The live threat-model and snapshot formulations remain the
   narrowed versions; historical quotations are clearly disposition history.

## Findings

### 1. Critical — option 3 is an exception in prose but not a branch in the executable lifecycle

Lines 417–424 say option 3 immediately unlinks staging and has **no canonical publish path**. But
the live numbered algorithm then unconditionally says “Publish atomically” at lines 456–457 and
“Either branch: commit the offering receipt LAST” at lines 505–507. The post-crash matrix likewise
permits partial/complete linked staging files, canonical entries, and receipt-commit residue for an
unqualified intake, while lines 545–549 require every restart to converge to one object and one
receipt.

Those are the option-1/2 terminal states, not option 3's. The self-contained contract currently
specifies both “no publish/receipt” and “publish/receipt” for the same mode. A literal implementation
of the numbered steps would violate the new exception; an implementation of the exception has no
complete terminal ordering for closing the anonymous descriptor and committing
`observations.db`.

Required closure: split §6 into a common, mode-neutral prefix and two explicit terminal branches:

- options 1/2: linked staging → publish/reuse → close staging → receipt transaction;
- option 3: anonymous staging → validate/hash → close the anonymous descriptor → observation
  transaction, with no object path and no receipt transaction.

The descriptor must be closed before the observation can advance freshness or make “no data
retained” visible. Scope the existing crash matrix and one-object/one-receipt convergence invariant
to options 1/2, and add a separate option-3 matrix. Mutation controls must make a publish, receipt,
linked provider-bearing staging entry, or still-open raw descriptor at observation commit fail.

### 2. High — unlink-before-write is not crash-durable until the directory unlink is fsynced

Lines 417–424 claim the option-3 copy is earned “across every crash state” because the staging name
is unlinked before the first provider byte. That is sufficient for ordinary process death, but not
for the durable-crash model used by this same section. The contract does not fsync the staging
directory after the unlink and before streaming. On a system crash, the unlink may not be durable
even if later file-data writes reached storage; recovery may therefore expose the formerly named
inode with provider bytes. The artifact already recognizes this durability distinction at lines
456–457 and 525 by requiring parent-directory fsync and admitting pre-fsync uncertainty.

Required closure: after exclusive creation, `unlinkat` the option-3 staging entry and durably fsync
the bound staging-directory descriptor **before the first provider-byte write**. If the platform
cannot provide that guarantee, narrow the claim and the UI copy rather than asserting every crash
state. The RED must assert the syscall/order boundary through an injected filesystem oracle; a
mutant that omits or moves the directory fsync after the first write must fail. A SIGKILL-only
probe is explanatory, because it passes the broken durability ordering.

### 3. High — coexistence copy still says no data is retained while older raw data is deliberately retained

The repaired transition rule at lines 407–414 correctly preserves older raw objects and receipts
read-only. Rows 11b and 12b then render “metadata only — no data retained · analysis uses the
<date> drop.” In those rows, data **is** retained: the older retained receipt and object are the
source of the analysis explicitly named by the same sentence.

The intended fact appears to be that the **latest recorded drop's archive** was not retained. The
current unqualified phrase instead describes the whole source/history and contradicts its own
second clause. That violates the product's honesty substrate even if the storage implementation is
perfect.

Required closure: give the copy an explicit referent in every observation row, such as “latest
drop metadata only — its archive was not retained”; preserve the dated older-analysis clause in
coexistence rows. Test option-3-only and 1/2→3 histories separately, including stage-2 failed and
invalid-attempt overlays. A copy oracle that checks only for the substring “no data retained” must
fail.

### 4. Medium — WAL is named, but the first-write journal-mode transition is not specified or falsified

Lines 397–399 freeze WAL and claim the frozen mode never creates `<db>-journal`, but the contract
does not say when or how WAL is established and verified. A future implementation can create the
database/schema in SQLite's default rollback mode, then switch to WAL and still pass an eventual
`PRAGMA journal_mode` check and the live-WAL backup restore test. That broken ordering can create a
rollback journal before the supposedly closed runtime file set applies.

Required closure: for each newly created logical database, establish `PRAGMA journal_mode=WAL`,
verify the returned/effective mode is `wal`, and refuse before any schema or application write if
it cannot be established. On reopening, verify the effective mode before protected writes rather
than silently changing an unexpected existing database. Add an ordering control and mutants for
“schema/write before WAL” and “requested WAL but ignored the returned mode.” Keep `<db>-journal`
ignored defensively, but do not claim conforming code can never create it until this boundary is
closed.

## Standing disposition

The v16 transition repair is directionally correct: retention mode now governs future writes,
historical receipt/object state is preserved, and backup coverage correctly uses one logical
`kind="sqlite"` entry rather than treating WAL/SHM files as backup payloads. Runtime names are now
pinned. The remaining blockers are caused by the new option-3 mechanism not yet being integrated
into the actual lifecycle, durability model, and copy function, plus an unclosed WAL-first-write
boundary.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
