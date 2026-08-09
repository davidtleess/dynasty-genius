# Manual-feed cadence RED final re-review — Codex v3

Date: 2026-08-08
Layer: 1
Reviewed pin: `18293ae325126117c1809fc20e71a6fb19c0beb2066770b0439530f63466c3b0`
Verdict: **NOT CLEAR**

Independent gates reproduced: 31 failed, 0 passed, 0 skipped, zero collection errors; true pytest exit 1. `.venv/bin/ruff check` passed.

The lifecycle, all-ingestion authority, coverage supersets, duplicate construction, undetermined cadence and controller rollups are now pinned correctly. Three final findings remain.

1. **S7d uses future evidence.** One `off` observation is timestamped `2026-09-15T13:00-04:00`. It is passed to the NFL-before evaluation at 09:00 that same day and both FBS evaluations on September 13. The test therefore lets an evaluator use evidence that did not exist yet. Use no offer before availability, or separate observations whose `observed_at <= now`, and add a direct guard that future-dated offer observations raise `CadenceError`.

2. **The policy-to-trigger mapping remains underconstrained.** S6 proves only that each stream has one or more allowed triggers; it does not prove the right stream has the right triggers. GREEN could assign `operator_drop` to every stream and pass. Pin a total expected mapping (partitioned by declared stream keys, not a count) or exact required trigger subsets for every declared manual family. The ontology must also carry the aligned completed-history triggers that are currently absent: schema change, methodology change and bounded pre-analysis hash comparison. Otherwise those agreed source changes can never create an obligation.

3. **Two evidence claims need scope correction.** “No 2026 gamelog, grade, or snap count can exist” must say no **in-scope 2026 regular-season** game event has occurred; preseason exists. The “1,423 column-instances have no nflverse counterpart” figure is lexical schema overlap and cannot be used as proof that all 1,423 are substantively unique—the debate already retired that inference. Grades are independently unique, so keep the conclusion and remove or qualify the number.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
