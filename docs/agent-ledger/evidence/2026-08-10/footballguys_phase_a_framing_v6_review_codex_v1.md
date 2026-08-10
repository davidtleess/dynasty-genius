# Footballguys Phase A framing v6 — Codex round-6 review

Date: 2026-08-10

Reviewed artifact and reproduced identity:

- `footballguys_phase_a_intake_notice_framing_claude_v6.md` — SHA-256
  `c8ca684054507abe17a134ba2c026ec904984d9c8cdb0f6048794afb1ecbb645`, 310 lines,
  23,494 bytes.

## Verdict

**NOT CLEAR — six findings.** All five round-5 dispositions are accepted in direction. V6 is
materially closer to a self-contained RED input: the complete-archive acceptance control, selected-
member safety scope, numeric resource ceilings, coexistence states, semantic reducer, restored local
calendar rule, and per-edge hash table are the correct repairs. No previous plan or pilot finding is
reopened.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. Plan v4 remains CLEAR. David's retention choice remains a separate hard gate.

## Checks run

- reproduced the submitted SHA-256 identity and line/byte counts;
- diff-read v6 against v5 and traced every round-5 disposition into the live self-contained text;
- rechecked all archive ceilings against the complete paid-ZIP measurements; the known input fits
  every inclusive boundary;
- traced every use of `receipt_id`, `archive_object_sha256`, role hashes, and
  `content_vintage_id` across §§5–6a;
- crossed archive-object identity with role-defined vintage identity using a same-roles/different-
  wrapper counterexample;
- exhaustively intersected the state-table predicates and found overlapping rows with different
  exact copy;
- independently evaluated the spring-DST control: 2026-02-07 12:00 EST to 2026-03-09 12:00 EDT is
  30 New York calendar dates but 719 elapsed hours (29d23h);
- looked for the claimed independent known-answer bytes/hash and found no vector or bound artifact;
- challenged the semantic reducer with retained, missing, and hash-failed contradictory evidence.

## Findings

### 1. High — the old “receipt hash” instruction survived beside the repaired rule

Section 6 still says every downstream load reverifies bytes “against the receipt hash.” Section 6a
then says the opposite: rehash the ZIP against `archive_object_sha256`, **never** `receipt_id`.
Because `receipt_id` is the offering-signature hash, both instructions cannot be implemented.

This is the sibling-field repair class already named in the pilot cycle: the dedicated table was
fixed while the earlier live instruction asserting the same boundary was not swept. Replace the
§6 wording with `archive_object_sha256` and reserve “receipt hash” entirely; the receipt *carries*
the object hash but is not itself the hash target.

One mutant is enough: an implementation follows §6 literally and compares ZIP bytes to
`receipt_id`; the independent valid-archive load must catch it.

### 2. High — one archive object per content vintage contradicts the two identities

Section 6a says there is “one immutable content-addressed object per content vintage.” But
`content_vintage_id` intentionally hashes only the two selected role records, while
`archive_object_sha256` hashes the intact ZIP. Two provider ZIPs can carry byte-identical `adp` and
`identity_sidecar` members while differing in an unselected app binary, ZIP metadata, or other
unselected bytes. They then have:

- the same `content_vintage_id`;
- different `archive_object_sha256` values;
- two distinct intact archives that must both remain attributable to their offerings.

Freeze the actual cardinality: canonical archive objects are keyed one-per-distinct
`archive_object_sha256`; zero or more offering receipts may reference each archive object; multiple
archive objects may map to the same role-defined `content_vintage_id`. Never key the raw object path
by `content_vintage_id`.

Required mutant: two ZIPs with identical selected roles and one differing unselected byte are forced
onto one canonical object or treated as corruption. Both should be preserved as distinct archive
objects while the unchanged role vintage is reported honestly.

### 3. High — the state table has overlapping predicates and conflicting exact copy

Row 4 allows `review_required` with AR “older or none.” Row 8 is the subset with an older AR. The
same state therefore matches both rows, but row 4 omits “analysis uses the <date> drop” while row 8
includes it. The table is not a function.

Row 13 repeats the defect for a due review-required acquisition: AR is “older or none,” but its copy
never discloses an older analysis-ready drop. Row 15 then inherits “clock row's copy,” so the
ambiguity propagates into invalid-newest-attempt states.

Make the predicates disjoint:

- current + review-required + AR none;
- current + review-required + older AR, with dated analysis copy;
- due + review-required + AR none;
- due + review-required + older AR, with dated analysis copy.

Then define row 15 as composition over one uniquely selected base row. Required mutant: first-match
evaluation against the current row order must not silently select the less-informative copy.

### 4. High — the spring-DST control's expected result is backwards

V6 correctly states that New York **calendar dates**, not elapsed hours, govern. It then requires
“29 days 23 hours across a DST change (still not due — calendar dates govern).” Across the spring
transition, 30 local calendar days can be exactly 29d23h elapsed. For example:

- 2026-02-07 12:00 EST → 2026-03-09 12:00 EDT;
- local-date difference = 30;
- elapsed time = 719 hours = 29d23h;
- the v6 rule therefore says **due**, not “still not due.”

Replace the control with paired oracles: 30 New York calendar dates across spring-forward is due
even when only 29d23h elapsed; fewer than 30 local dates is not due regardless of elapsed duration.
Add the fall-back complement, where 30 calendar dates may exceed 30 elapsed days but remains due for
the same calendar reason.

### 5. Medium — the durable-ID known-answer vector is asserted but does not exist

Section 6a says serialization “is frozen with an independent known-answer vector,” but v6 supplies
no canonical byte sequence, expected SHA-256, or hash-bound fixture path. It also says only
“fixed separators” and “one canonical UTC form” without naming the separator bytes or timestamp
grammar. JSON arrays, line-delimited fields, and pipe-delimited fields can all satisfy that prose
and yield different durable IDs.

Before CLEAR, embed or hash-bind an actual independent fixture containing:

- exact typed input fields and role order;
- the normalized UTC timestamp string;
- exact canonical UTF-8 bytes;
- expected `content_vintage_id` bytes/hash;
- expected offering-signature bytes and `receipt_id` hash.

The oracle must construct those bytes independently and never import the production serializer.
Include negative vectors for role swap, integer/string byte-count confusion, delimiter collision,
and equivalent offset spellings.

### 6. High — dropping unavailable assertions can still erase a live contradiction

The reducer covers “unresolved conflict among retained assertions.” Consider a retained redraft
assertion followed by a contradictory startup assertion whose record remains but whose attachment
is later missing, unretained, or hash-failed. Filtering to retained assertions drops the challenge;
the older redraft assertion can again become the effective state. The following attachment rule is
ambiguous about whether one unavailable challenger globally blocks the key or merely cannot support
its own claim.

Define the reducer over **all active assertion records**, not only currently usable attachments. Any
active record with absent/hash-failed evidence makes the key unverifiable/`unknown`; evidence loss
never restores an older claim. A record may leave the reducer only through the explicit,
provenance-bound adjudication/supersession mechanism, not by losing its attachment.

Required mutants: delete or corrupt the newer conflicting attachment and observe the old horizon
reappear; mark the challenger `unretained` and exclude it; or garbage-collect evidence before its
supersession parents are resolved. All must keep Phase C closed.

## State

- Plan v4: **CLEAR**, unchanged.
- Phase A framing v6: six repairs required; no RED.
- Phase B waits for A's frozen bundle/evidence interface and independent oracle.
- Phase C/D remain closed.
- David's retention choice still gates Phase A RED regardless of the next review result.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
