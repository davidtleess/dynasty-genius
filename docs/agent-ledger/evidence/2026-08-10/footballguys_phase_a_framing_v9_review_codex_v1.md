# Footballguys Phase A framing v9 — Codex round-9 review

Date: 2026-08-10

Reviewed artifact and reproduced identity:

- `footballguys_phase_a_intake_notice_framing_claude_v9.md` — SHA-256
  `301494a8ee8f8743c902fd527c1517e45e55164361eeaf943fc9871e89163fbf`, 489 lines,
  38,036 bytes.

## Verdict

**NOT CLEAR — five findings.** Unlike v8, the one-snapshot rule, exclusive staging creation,
descriptor lifetime, fresh-publication cleanup, full preimages, equal-instant reducer, and
two-stage overlay language are present in the live artifact. The two embedded preimages hash
directly from v9 to the declared 200-byte/478-byte outputs. The remaining blockers concern what the
new equal-instant reducer treats as equivalent and lifecycle branches that the rewritten store still
does not close.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. Plan v4 remains CLEAR. David's retention choice remains a separate hard gate.

## Checks run

- reproduced the submitted SHA-256 identity and line/byte counts;
- diff-read v9 against v8 and grep-verified every round-8 disposition in the final artifact;
- extracted the two fenced preimages directly from v9 and independently reproduced 200 bytes /
  `201d2484…` and 478 bytes / `0d6bf306…`, including trailing LF;
- independently reproduced N1–N4's full expected hashes;
- traced fresh-publication and canonical-reuse branches separately, including descriptor close,
  staging-name cleanup, receipt failure, and restart behavior;
- enumerated equal-second candidates with identical display facts but different content identity;
- crossed `clock_conflict` with AR selection, due/current state, failed/invalid overlays, later
  valid acquisitions, and more than two tied candidates;
- challenged the A/B/failure source-swap oracle with in-place source mutation during streaming.

## Findings

### 1. Critical — equal readiness/retention does not mean equal analysis content

The equal-instant rule declares candidates with identical readiness/retention facts harmlessly
collapsible. Consider two distinct byte-retained `ready` receipts at the same whole-second
`retrieved_at`, one for `content_vintage_id=X` and one for `content_vintage_id=Y`. Their stated
readiness and retention facts are identical, so v9 collapses them, but `latest_analysis_ready` can
now point to different football data depending on append/query order. The required mutant checks
only byte-identical state and copy, so this broken implementation passes while the Layer-1 output
changes.

Define equivalence over every state- and analysis-affecting fact, not just the two display labels.
At minimum, distinct candidates may collapse only when their role-defined analytical content,
readiness result, retention mode, and AR effect are equal. Different `content_vintage_id` values at
the maximal instant must conflict even when both rows say `ready`; wrapper-only archive differences
may collapse if their role vintage and every downstream effect are identical.

Required mutant: append two equal-second `ready` receipts with different `content_vintage_id`
values in both orders. Assert the effective clock **and** `latest_analysis_ready` identity/content,
not merely the rendered copy. It must yield the same named conflict in both orders and expose
neither content as analysis-ready through tie-breaking.

### 2. High — `clock_conflict` is not part of the table or the two-stage function

Section 7a creates a new `unverifiable` state, but §7's table still has no `clock_conflict` base row
even while claiming to enumerate the function. Stage 1 says it selects a unique base row, which it
cannot do for the exact condition that creates the conflict. The artifact also leaves these
reachable outcomes undefined:

- whether AR holds, advances, or becomes unavailable during the conflict;
- whether an older unambiguous clock is barred from silently winning;
- how newer failed/invalid attempts compose over the conflict;
- whether a strictly later valid candidate clears the old conflict;
- how three or more tied candidates render (the exact copy currently says “two drops”).

Add a conflict base row with status, pill, exact copy, AR behavior, and precedence. Make it an input
to stage-2 overlays and use copy that remains true for any cardinality, such as “multiple drops.”
Required controls cover two and three candidates, an older prior clock, a newer failed/invalid
attempt, and a later unique valid acquisition. A conflict must never fall back to an older candidate
or disappear because query order changed.

### 3. High — the canonical-reuse branch has no staging-descriptor terminal state

Stage 1 says the staging descriptor remains open until after the staged/published inode comparison.
That comparison exists only for a **newly published** object. When no-replace reports an existing
canonical path and the object verifies for reuse, the staged and canonical objects are necessarily
different inodes, and v9 never says when the held descriptor closes or when the redundant staging
name/inode is unlinked. A literal implementation leaks one full paid ZIP for every deduplicated
receipt.

Split the lifecycle explicitly:

- fresh publication: hold the staging descriptor through same-inode publication verification,
  then close;
- canonical reuse: verify byte equality through the two bound descriptors, close and unlink the
  redundant staging object, fsync its parent, then commit the receipt against the existing object.

Do not require inode equality on reuse. Required control: repeated same-content intake produces one
canonical object, zero staging files after return, and the correct number of receipts; inject a
receipt-commit failure on reuse and require the same no-leak result.

### 4. High — crash mutants name injection points but not their required durable states

V9 still lists crashes during staging, before publish, after publish before directory fsync, and on
reuse without defining the observable restart contract. Broken code can leave partial or complete
paid ZIPs under temporary names indefinitely and still “pass” a test that only confirms no receipt.
The text defines a reported recoverable orphan only for receipt-commit failure, not for the earlier
crash boundaries.

Freeze the post-crash matrix. For every injection point, name whether a staging file or canonical
orphan may exist, how it is discovered and reported on restart, whether it is safely removed or
reused, and prove that no receipt/freshness/AR state advances from file existence alone. Stale
staging bytes must remain under the selected retention/manifest boundary and must never be parsed as
a committed offering. A second clean intake should converge to one canonical object and one valid
receipt without manual pathname surgery.

### 5. Medium — staging creates a coherent C, not necessarily A, B, or failure

The repaired boundary correctly guarantees that every derived fact describes the staged bytes. It
does not guarantee that a source file mutated in place while being streamed produces exactly the
before image A, the after image B, or an error. The staging copy can be a byte-level hybrid C; if the
mutation affects an unselected member or otherwise leaves a valid ZIP, C can pass structural and
role validation. The current A/B/failure wording overclaims filesystem snapshot semantics and can
make a correct implementation fail its stated mutant.

State the guarantee precisely: whatever byte sequence C was staged becomes the sole authoritative
candidate, and all archive/role/schema/vintage facts must derive from C; invalid C fails. If true
A-or-B atomic source capture is required, add an actual source-snapshot mechanism and its own
controls. The present stage-first mechanism earns internal coherence, not atomic observation of a
concurrently mutable source.

## Non-blocking cleanup

Section 6 numbers both publish and canonical-exists handling as step 3 and then jumps to step 5.
Renumber this mechanically when repairing the branch lifecycle; it does not independently block the
framing.

## State

- Plan v4: **CLEAR**, unchanged.
- Phase A framing v9: five repairs required; no RED.
- Phase B waits for A's frozen bundle/evidence interface and independent oracle.
- Phase C/D remain closed.
- David's retention choice still gates Phase A RED regardless of the next review result.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
