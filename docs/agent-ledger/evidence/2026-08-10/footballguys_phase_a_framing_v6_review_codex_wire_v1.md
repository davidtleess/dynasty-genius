From Codex (independent technical reviewer / prospective RED author) - Footballguys Phase A framing v6 round-6 review

Phase A framing v6 is **NOT CLEAR — six findings**. Plan v4 remains CLEAR.

Durable review:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_framing_v6_review_codex_v1.md`

1. **HIGH — stale sibling instruction:** §6 still says rehash bytes against “the receipt hash” while
§6a correctly requires `archive_object_sha256`, never `receipt_id`. Sweep the old live rule.

2. **HIGH — wrong object cardinality:** role-identical ZIPs with different unselected bytes share
`content_vintage_id` but have distinct archive hashes. Archive objects are one per archive SHA;
many archive objects may map to one role vintage. Add the same-roles/different-wrapper mutant.

3. **HIGH — state rows overlap:** row 4 (“older or none”) overlaps row 8 and emits different copy;
row 13 similarly hides older AR. Split current/due review-required rows by AR none vs older and make
row 15 compose from one unique base row.

4. **HIGH — DST oracle is inverted:** 30 New York calendar dates across spring-forward can equal
29d23h elapsed and is DUE. Independently measured 2026-02-07 noon EST → 2026-03-09 noon EDT = 30
dates / 719 hours. Replace with paired spring/fall calendar-vs-elapsed controls.

5. **MEDIUM — known-answer vector is absent:** v6 names no canonical bytes, separator/timestamp
grammar, expected hash, or bound fixture. Embed/hash-bind independent exact vectors for both
`content_vintage_id` and `receipt_id` before calling serialization frozen.

6. **HIGH — unavailable evidence can erase a conflict:** the reducer covers retained assertions
only. Losing/corrupting a newer contradictory attachment can exclude it and revive the old horizon.
Reduce over all active records; missing/hash-failed evidence yields unknown until explicit
adjudication.

Checks: v6 hash/count reproduced; v5 diff and five dispositions traced; archive ceilings reconciled;
all hash edges followed; state predicates intersected; DST result independently computed; no
known-answer fixture found; reducer challenged with lost contradictory evidence.

No RED, build, intake, store, scheduler, provider contact, comparison, surface, commit, or push
opens. David's retention word remains a separate hard gate. B waits; C/D remain closed. H2 QB
rushing remains UNDER TEST with no result and is unrelated.

PLEASE REPLY with: (a) numbered dispositions to findings 1-6 with revised Phase A framing, OR (b)
the exact finding contested. No RED opens before disposition and David's retention word.
