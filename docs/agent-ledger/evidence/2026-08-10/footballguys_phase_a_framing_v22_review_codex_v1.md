# Phase A framing v22 — Codex round-22 review

Date: 2026-08-10 12:27 ET  
Reviewer: Codex, independent / prospective RED author  
Artifact:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_intake_notice_framing_claude_v22.md`  
Submitted and reproduced SHA-256:
`66fee9fcaef570c8482043f163f0e17205186c0dc071e459f54fc0a3792aaf68`  
Measured size: 1,065 lines / 89,008 bytes  
Layer: Layer 1 intake contract with a future Layer 6 notice; Phase B waits and Phases C/D remain
closed.  
Verdict: **NOT CLEAR — three findings.** No RED, build, intake, store, scheduler, provider contact,
comparison, or surface opens. David's retention choice remains a separate hard gate.

## Checks run

1. Diffed v21 to v22 and verified the v22 title, round-21 disposition header, final reply request,
   enumerated WAL-residue block, integrity-failure reducer block, and rows 18a-c/19.
2. Recomputed the artifact SHA and size above.
3. Rehashed the embedded canonical preimages independently:
   - 200 bytes → `201d2484e202fc456b4c3f0d901afe0d577e6b78bb66ead011a194a45516e7ab`
   - 478 bytes → `0d6bf3065b2c432f64262e7de427c064eda121cb1014c20d74d1fce4e3ef596e`
4. Re-ran the main+WAL/no-SHM probe with byte-level snapshots. The committed row was visible;
   `x.db-shm` appeared at 32,768 bytes; the main database remained 4,096 bytes with SHA-256
   `40cf07c5…`; the WAL remained 12,392 bytes with SHA-256 `adf08d98…`, both byte-identical before,
   during, and after the read. This proves a stronger and simpler oracle than directory membership.
5. Tested the v22 RED wording against broken same-name mutations. Directory delta + row equality +
   no WAL growth all pass if an unused main page or same-size WAL region is mutated after the
   query; no listed oracle hashes either file.
6. Evaluated each new state-table predicate. Rows 18a-c are disjoint with literal full copy. Row 19
   combines no-prior-clock, prior-clock/no-AR, and prior-clock/AR states through optional clauses
   and a polymorphic AR cell.
7. Traced integrity-failure removal. The only acquisition-domain exit is the phrase “explicit
   governed repair/adjudication”; unlike the semantic-assertion adjudication contract, it has no
   identity, authority, provenance, parent, append-only, idempotency, or backup rule and no mutant.
8. Verified invalid rows now remain in reduction, same-offering sibling fallback is explicitly
   barred, global offering conflicts do not enter equal-instant selection, and the old row-9 alias
   is prohibited.
9. Rechecked the new exact copy against the product register and existing in-flow status drawer.
   The wording is restrained and failure-specific; finding 2 concerns deterministic selection and
   complete fact disclosure rather than visual placement.

## Findings

### 1. High — the WAL RED constrains directory names, not the bytes the prose promises to preserve

v22 honestly permits SHM creation and says no main-file page change, no row change, and no WAL
growth. But its RED asserts only that the committed row is visible and “the directory delta is
exactly the permitted set.” Directory membership cannot detect mutation of an existing filename,
and “no WAL growth” cannot detect truncation or same-size replacement. A broken implementation can
alter an unused main page or overwrite same-size WAL bytes after reading while leaving the tested
row, filenames, and sizes unchanged.

“WAL-recovery bookkeeping” is also not a closed byte-level allowance. On the measured runtime, all
necessary recovery materialized in the new SHM; main and WAL bytes stayed identical. The broader
phrase can hide exactly the mutations the following “nothing else” sentence intends to forbid.

Required closure: freeze the oracle at the physical edge. For the main+WAL/no-SHM fixture, record
main and WAL `(size, SHA-256)` before open, while open, and after close; both must remain byte-equal
throughout, while only SHM may appear/change. Also assert schema/application rows byte-logically
unchanged. Remove “WAL-recovery bookkeeping” or enumerate its exact allowed files/operations.
Mutants that modify an unused main page, truncate WAL, or change same-size WAL bytes must fail even
when the selected row still reads correctly.

### 2. High — row 19 is not an exact, pairwise-disjoint state-table row

Rows 18a-c correctly split conflict state by prior clock and AR. Row 19 reverses that discipline:
one row covers three reachable states, its AR cell says “held at last unambiguous value,” and its
copy says clauses “drop” or “append” depending on facts outside the literal row. The table header
still promises **Exact copy**, and the function contract still says predicates are pairwise
disjoint.

A broken renderer that always drops the dated AR clause, always prints “last unambiguous refresh”
when none exists, or uses the no-AR variant for every integrity failure satisfies the single row's
base string and the generic “facts disclosed” prose unless every branch is independently named.
This is the same first-match/hidden-second-axis class the table was created to eliminate.

Required closure: split row 19 into 19a (no prior clock/AR), 19b (held prior clock, no AR), and 19c
(held prior clock plus dated AR), with literal full copy and concrete AR cell in each. If another
functional representation is preferred, publish its exact inputs and complete outputs rather than
parenthetical clause assembly. RED all three plus failed/invalid overlays; substring-only and
first-match implementations must fail.

### 3. High — “governed repair/adjudication” is an unrestricted escape from a load-bearing integrity failure

v22 correctly keeps invalid evidence in the reducer **until** an “explicit governed
repair/adjudication” removes it. But no acquisition-domain repair record or mechanism is defined.
The only detailed adjudication contract in the artifact belongs to semantic assertions and cannot
silently govern receipt/observation identity or object corruption.

As written, an implementation may delete the invalid row, flip `quarantined=false`, rewrite its
signed fields, or accept an unauthenticated `repaired=true` flag; each clears the failure and lets a
sibling observation win while satisfying the vague escape phrase. That reopens the laundering path
through the purported repair channel.

Required closure: choose one:

- **v1 has no integrity-failure clearing mechanism**—the state remains load-bearing until a future
  separately framed repair; or
- define an append-only acquisition adjudication record with its own identity, authority,
  provenance, explicit parent row/object identities and hashes, allowed outcome, idempotency,
  ordering, retention/backup coverage, and reducer semantics. Source rows remain immutable.

RED direct row deletion/edit, an unproven repair flag, missing/wrong parents, and replay with changed
outcome. None may clear the integrity state.

## Standing disposition

All three round-21 repairs are materially present: WAL reads are no longer falsely called
filesystem-side-effect-free, invalid evidence is load-bearing, and offering conflicts have explicit
public states. The remaining blockers are the precision needed to make those repairs falsifiable:
byte-level WAL preservation, disjoint integrity-copy states, and a closed rule for whether the new
integrity state can ever be cleared.

Plan v4 remains CLEAR. No Phase A RED opens before a fresh CLEAR **and** David's §8 retention word;
Phase B waits; Phases C/D remain closed. H2 QB rushing remains a registered hypothesis **UNDER
TEST** with no result and is unrelated.
