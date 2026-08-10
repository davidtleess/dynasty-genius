# Phase A framing v21 — Codex round-21 review

Date: 2026-08-10 12:22 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v21.md`  
Submitted and reproduced SHA-256:
`ae0cabcfe3fc13a99c7e855d523c2999da8b78de084ca1c9a96ca6950360c5a4`  
Measured size: 1,020 lines / 84,547 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — three findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Diffed v20 to v21 and verified the corrected v21 title, the disclosed stale-v20-header account,
   the restored round-19 disposition block, the round-20 disposition block, and the final v21
   reply request. The three claimed round-20 repair blocks are live.
2. Recomputed the artifact SHA and size above.
3. Rehashed the embedded canonical preimages independently:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Reproduced SQLite WAL behavior on the pinned local SQLite/Python runtime. Starting from an
   existing WAL database copied with `x.db` + `x.db-wal` but no `x.db-shm`, opening
   `file:…/x.db?mode=ro` and reading the committed row changed the directory from
   `[x.db, x.db-wal]` to `[x.db, x.db-shm, x.db-wal]`. `mode=ro` prevented logical writes but did
   not make the lookup filesystem-non-creating.
5. Ran the obvious negative control, `mode=ro&immutable=1`, against the same main+WAL shape. It
   created no SHM, but reported `journal_mode=delete` and failed with `no such table: t`; it did
   not see the committed WAL state. Therefore “just add immutable” is not an admissible repair.
6. Traced the main-file tri-state against orphan `-wal`/`-shm`, row identity mismatch, object
   mismatch, and a valid sibling observation. The live rule says quarantine/no coalescence/no AR
   advance, but does not close freshness, status, pill, copy, or fallback candidacy.
7. Traced the new persisted `offering_identity_conflict` through the reachable-state table. The
   reducer now names `unverifiable` and holds prior clock/AR, but no row specifies its exact copy,
   pill, prior-AR disclosure, or overlay behavior; row 9 is specifically “ledger unreadable.”
8. Verified the prior early reuse commit remains deleted, both row types now receive signature
   recomputation in the prose contract, and the valid identical-signature receipt-precedence case
   remains coherent.
9. Rechecked the notice surface against the product register and existing in-flow status drawer.
   Placement remains sound; finding 3 is the remaining user-visible total-function defect.

## Findings

### 1. High — `mode=ro` is not a non-creating WAL lookup, and the tri-state omits orphan sidecars

v21's existing-store branch equates a SQLite `mode=ro` URI with a read-only, non-creating lookup.
The live probe above falsifies that filesystem claim: when committed state lives in `x.db-wal` and
`x.db-shm` is absent, the read-only connection creates `x.db-shm` in order to read the WAL. This is
not merely theoretical crash residue; it is a normal recoverable WAL shape. Conversely,
`immutable=1` avoided the sidecar but silently ignored the committed WAL state in the control.

The main-file-only tri-state also leaves `main absent + orphan -wal/-shm present` undefined. Calling
that “absent/empty” would ignore corrupt or incomplete restored state; calling it existing cannot
open the missing main database. The current REDs begin with all three files absent and therefore
pass both broken classifications.

Required closure: distinguish **logical-row read-only** from **filesystem side-effect-free**. Pick
and evidence one implementable contract:

- permit SQLite's SHM creation/mutation only for an already-existing, governed, covered database;
  enumerate its allowed physical residue while proving no schema/application row changes; or
- use another evidenced snapshot/read mechanism that sees committed WAL rows without mutating the
  source directory.

Do not use `immutable=1` unless a control proves uncheckpointed committed WAL rows remain visible.
Classify main-absent plus any sidecar-present state as malformed/unverifiable, never empty. RED the
exact main+WAL/no-SHM shape, assert the committed row is seen, assert the permitted directory delta,
and retain the all-files-absent non-creation controls.

### 2. High — quarantining an invalid receipt is not a closed reducer outcome

v21 now recomputes every row's identity and says a mismatch “quarantines the row.” Its cross-store
fixture asserts only “no coalescence, no AR advance.” A broken reducer can satisfy both by dropping
the invalid receipt and allowing the valid sibling observation to become the clock, render
`current`, and say “its archive was not retained.” The same fallback is available when receipt
metadata validates but its canonical object fails descriptor-bound verification.

That contradicts the standing read-path rule that corrupt Footballguys state degrades the stream
to `unverifiable`; invalid evidence must not disappear and make a weaker surviving record look
healthy. It also risks the false copy that no archive was retained when a receipt proves an archive
was meant to be retained but its identity or bytes are now untrustworthy.

Required closure: carry any identity-invalid or object-invalid persisted row into the effective
reducer as a named integrity failure. It must make the stream `unverifiable`, hold the last
unambiguous clock and AR, and bar every same-offering sibling from clock/AR/copy fallback until an
explicit governed repair/adjudication removes the failure. Extend the cross-store fixture to assert
status, clock identity, pill, full copy, and Phase-C closure—not only no coalescence/no AR advance.
Mutants that filter the quarantined row before reduction or let the observation win must fail.

### 3. High — `offering_identity_conflict` creates a reachable state absent from the total state table

The new global-conflict rule says the stream is `unverifiable`, holds AR and the last unambiguous
clock, and excludes the conflicting group from clock selection. That is a new reachable public
state, but §7 still has no row for it. Row 9 is specifically an unreadable ledger with copy
`Footballguys refresh record unreadable`; using that copy for two valid-but-conflicting signatures
would misstate the failure and hide the held clock/analysis facts.

The table therefore is no longer the promised total function. It does not define:

- conflict with no prior unambiguous clock or AR;
- conflict with a held prior clock and no AR;
- conflict with held prior clock and older AR, including the analysis date;
- how a newer failed/invalid attempt composes over the conflict;
- the exact pill/copy result for each case.

Required closure: add disjoint conflict base rows (or an equally closed functional projection) with
exact copy, pill, clock/AR identity, and stage-2 overlay behavior. The copy must name an acquisition
identity conflict rather than unreadability and disclose any retained older analysis date. RED every
axis and both query orders; an implementation that aliases the state to row 9 or picks a healthy
clock row must fail.

## Standing disposition

The v20 header defect is disclosed and repaired, and all three round-20 repairs are materially
present. The remaining issues are consequences of making those repairs executable: SQLite's WAL
read path has physical side effects, quarantined evidence needs a non-filtering reducer outcome,
and the new global conflict needs a complete public-state projection.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
