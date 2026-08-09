# PFF grade columns are not a cadence stream — Codex ruling v1

**Date:** 2026-08-08 19:15 ET  
**Layer:** Layer 1 ingestion control  
**Disposition:** binding correction to the earlier split ruling

## Ruling

Remove `("pff", "grades")` from the cadence stream registry. Do not leave it unsplit and do not
replace it with `nfl_grades` / `ncaa_grades` streams.

The measured acquisition topology has fourteen PFF payload lanes: seven report families for each of
NFL and NCAA. There is no separately acquired grades payload. Grade fields are columns carried by
those fourteen real payload lanes. A separate grades cadence entry therefore creates a phantom
obligation; splitting it would create two phantom obligations. The refresh of grade columns occurs
when the real containing league/report lane is refreshed.

This corrects and supersedes Codex's 18:04 ET ruling to split `pff.grades`. That ruling inferred a
feed identity from a datatype and was wrong once the payload topology was measured.

## Shipped contract repair authorized

The same bounded repair may amend `tests/contract/test_manual_feed_cadence_red.py`. No additional
David authorization is required: this is a factual repair to the representation of the ingestion
surface, preserves his authorization to consume all data at its determined frequency, and does not
authorize a paid call, provider contact, capture, scheduler installation or model promotion.

Required contract changes:

1. The exact PFF cadence key set is the fourteen measured league/report lanes. No `grades`,
   `nfl_grades` or `ncaa_grades` cadence key may exist.
2. Remove the phantom key from `EXPECTED_STREAM_KEYS`, `REQUIRED_TRIGGERS`, production declarations
   and controller fixtures that merely need a real PFF record.
3. Preserve the refresh obligation on every real PFF lane; grade columns travel with those payloads.
4. Preserve raw retention and the existing column-level model-input prohibition. Removing a phantom
   stream must not weaken `PROHIBITED_COLUMNS` or the adapter/head contract tests.
5. Do not mark every field in a real PFF lane as model-use-forbidden. The restriction is column
   level; the current stream-level `is_grades` flag is advisory metadata attached to no real feed and
   should be removed rather than transferred wholesale.
6. Because the real catalog is private/gitignored, CI should use synthetic topology contracts. A
   private acceptance check may record only aggregate evidence that every measured grade-bearing
   field belongs to a real lane and that no standalone grade payload exists.

## FBS evidence correction

The held CFBD cache currently provides no dated FBS game calendar: the measured cache contains 217
files, 134 null payloads and 83 integer counts, with zero list-shaped/detailed schedules. Therefore
FBS cadence is currently `undetermined` and must remain isolated from NFL/B21 events.

It is not correct to call that state permanent. `scripts/build_w2b_cfbd.py` already calls the CFBD
`/games` endpoint and can preserve its unmodified response; the current helper reduces it to a
per-team game count and is not a governed calendar source. A future FBS calendar route remains
possible, but requires a separately reviewed capture design and the existing CFBD cost/key decision.
No paid call is authorized by this ruling.

## Effect on the league-scoped RED

The current RED pin `287dcc7c...` is superseded. P4 must encode the single outcome above. The other
previous review findings remain: stable machine-readable validation codes, total raw-declaration
scope checks, absent-vs-malformed separation, full-controller fail-closed isolation, exact-state
countertests and Ruff cleanliness.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
