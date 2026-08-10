# Footballguys Phase A framing v10 — Codex round-10 review

Date: 2026-08-10

Reviewed artifact and reproduced identity:

- `footballguys_phase_a_intake_notice_framing_claude_v10.md` — SHA-256
  `54f414160a71056589d08523498b7196cb56afc7d22415fac21f226955135d38`, 556 lines,
  44,232 bytes.

## Verdict

**NOT CLEAR — five findings.** All five round-9 repairs are present. The equal-instant equivalence
now includes analytical content, `clock_conflict` has a row and precedence, reuse has a terminal
state, crash points have durable outcomes, and the staging guarantee is correctly limited to
internal coherence. The two embedded preimages still reproduce exactly from v10.

Finding 1 corrects my own prior remedy: I accepted “clock conflict → refresh time unverifiable” in
round 9 without testing it against the orthogonal freshness/readiness contract. Equal validated
instants make the **time** certain; it is the content/readiness that conflicts.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. Plan v4 remains CLEAR. David's retention choice remains a separate hard gate.

## Checks run

- reproduced the submitted SHA-256 identity and line/byte counts;
- diff-read v10 against v9 and traced every round-9 disposition into the live sections;
- extracted the fenced preimages directly from v10 and reproduced 200 bytes / `201d2484…` and
  478 bytes / `0d6bf306…`, including trailing LF;
- replayed different-vintage, wrapper-only, two-candidate, three-candidate, append-order, prior-AR,
  later-valid, failed-overlay, and invalid-overlay cases through the equal-instant reducer;
- crossed the conflict state with 10-day-current and 31-day-due freshness;
- traced staging sweep, reuse cleanup, fresh receipt failure, reuse receipt failure, and concurrent
  intake namespace operations;
- challenged the close/unlink sequence with a staging-entry replacement after descriptor-bound
  verification.

## Findings

### 1. Critical — equal-instant content disagreement is not refresh-time ambiguity

Every candidate that creates row 16 has the same validated maximal `retrieved_at`. The acquisition
time is therefore known exactly and the 30-day freshness calculation is deterministic. What is
ambiguous is which content/readiness fact should govern analysis. V10 instead sets freshness status
to `unverifiable`, increments the freshness-only pill by one, and tells David “refresh time
ambiguous.” That violates the contract's explicit separation of acquisition freshness, intake
readiness, and `latest_analysis_ready`.

The consequences go both ways:

- a 10-day-old same-instant conflict is known `current`, but v10 produces an extra freshness pill;
- a 31-day-old same-instant conflict is known `due`, but v10 suppresses “monthly refresh due.”

Model this as a **readiness/content conflict layered over the shared freshness instant**, not a
clock conflict. Freshness remains `current` or `due`; the pill follows that axis only; Phase C stays
closed; AR holds per the accepted rule. Exact copy should state the known age/due fact and the
separate disagreement, for example “Last Footballguys refresh recorded N days ago · multiple drops
at that time disagree — data review required.”

Required controls: non-equivalent tied candidates at 10 and 31 days, each with both append orders.
Assert freshness status, pill, readiness conflict, AR, Phase-C closure, and copy independently.

### 2. High — the conflict row hides the older analysis-ready drop it explicitly preserves

Row 16 says AR holds at the last unambiguous value, but its exact copy never says which older drop
analysis continues to use. This repeats the hidden-second-axis defect already repaired for
review-required and metadata-only states. If no prior AR exists, the omission is harmless; if an
older AR exists, David is told only about the disagreement and cannot see that analysis remains on
older data.

Split or compose the conflict/readiness state by AR none versus older AR. The latter must append
`analysis uses the <date> drop`, under both current and due freshness and under failed/invalid
attempt overlays. Required mutant: older ready R, then two non-equivalent equal-instant candidates;
AR must remain R and the exact copy must disclose R's date.

### 3. High — the startup sweep can delete another live intake's staging file

The crash matrix instructs every next intake to sweep and remove staging-directory entries, but no
writer lock, lease, or active-run distinction exists. Two manual intakes can overlap: A creates and
writes its exclusive staging file; B starts, treats A's live file as a crash orphan, and unlinks it.
Unix may preserve A's open inode, but A loses its publication name and the supposedly safe recovery
mechanism has destroyed a live run.

Acquire a per-source exclusive lifecycle lock **before** sweeping and hold it through staging,
publication/reuse cleanup, receipt commit, and terminal cleanup. Define stale-lock recovery without
trusting PID reuse or age alone. Alternatively bind every staging entry to a durable active-run
lease with equivalent guarantees.

Required control: two overlapping intakes plus one crash. The second process may wait or return a
named busy result, but it must never sweep the live first process; the surviving/next run must
converge to the same one-object/receipt contract.

### 4. High — reuse cleanup returns to pathname identity after descriptor verification

The reuse branch verifies bytes through two bound descriptors, then says the staging descriptor is
closed and the staging name/inode unlinked. It does not bind the directory entry being unlinked to
the verified staged inode. A concurrent rename can move that inode away and place a different file
at the old staging name; cleanup then deletes the replacement and leaks the verified staged inode
under its new name. This is the validation-to-cleanup version of the pathname race already barred
for reads.

While the staging descriptor is still open, verify the staging directory entry no-follow against
the descriptor's device/inode, unlink that bound entry under the lifecycle lock, fsync the parent,
then close. If the entry no longer names that inode, refuse cleanup without deleting the replacement
and report the displaced staging inode/name state.

Required mutant: replace the staging directory entry after byte equality but before unlink. A
sentinel replacement must remain byte-identical, no receipt may commit, and no verified staging
inode may be silently leaked.

### 5. Medium — receipt-commit failure conflates fresh and reuse residues

The post-crash table says receipt-commit failure “either branch” leaves a verified canonical object
with no referencing receipt. That is true for a newly published object. It is generally false on
reuse: the canonical object may already have one or many prior receipts, the redundant stage has
already been removed, and the failed transaction creates no new filesystem residue. Calling the
healthy shared object an orphan can trigger incorrect reporting or cleanup.

Split the row:

- fresh commit failure → newly published, unreferenced canonical orphan;
- reuse commit failure → no new object or staging residue; existing reference set remains exactly
  unchanged (or a pre-existing orphan remains an orphan if that was the starting condition).

Required control: start with one canonical object and one receipt, attempt a second offering through
reuse, fail its receipt transaction, and assert one object, one original receipt, zero staging
files, and no newly reported canonical orphan.

## State

- Plan v4: **CLEAR**, unchanged.
- Phase A framing v10: five repairs required; no RED.
- Phase B waits for A's frozen bundle/evidence interface and independent oracle.
- Phase C/D remain closed.
- David's retention choice still gates Phase A RED regardless of the next review result.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
