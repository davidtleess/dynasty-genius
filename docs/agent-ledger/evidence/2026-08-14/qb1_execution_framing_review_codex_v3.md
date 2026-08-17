# QB-1 execution framing v3 — independent round-3 review (Codex v3)

Date: 2026-08-14  
Work item: `TW14-QB1-1`  
Reviewed artifact: `qb1_execution_framing_claude_v3.md`  
Reviewed SHA-256: `fa57b4075c5bfd1d111c92adcb12d2503fc627f808d52fde806ac4e5b4aec196`  
Verdict: **NOT CLEAR — two BLOCKERs, one WARN**

This review neither authorizes nor performs a provider fetch or study run. QB
rushing production (H2) remains **UNDER TEST** with no result.

## Checks

1. Reproduced the v3 artifact hash exactly and read the active structured run.
2. Verified QB-R2-B2's measured F32 rates and consequence are accurately
   carried: 2.60% / 2.94% / 2.33% / 0.00%; three fold exclusions leave 1/4,
   so H5 contrasts 11–14 receive `unsupported_power` under the frozen rule.
3. Verified v3 does not propose normalization, threshold, alias, or other
   in-flight registration tuning. The advisory/binding-run distinction is
   explicit.
4. Verified QB-R2-W1 is fully integrated: the exact required backup directory
   is `app/data/backtest/qb_validation/raw`, including `raw/dp_values`.
5. Compared the claimed seven-fetch packet with the shipped adapter's exact
   dataset vocabulary and loader scopes.
6. Compared the David-facing model-lane power claim with the registered §7
   floors: at least 5/8 evaluable folds and per-fold evaluable n at least 20.

## Findings

### QB-R3-B1 — BLOCKER — the “all seven” fetch packet names the wrong set and omits the promised scopes

V3 lines 16–18 list weekly stats, season summaries, play-by-play, rosters,
“schedules-adjacent weekly qualifying rows,” draft picks, and player attributes.
There is no registered schedules-adjacent dataset. The list duplicates the
weekly concept and omits the registered `ff_playerids` crosswalk — the very
source needed by the study's identity bridge.

The decision packet at lines 46–48 also does not contain the promised
per-dataset scopes or even a transfer/storage estimate, which matters because
2015–2025 play-by-play is materially different from the small static tables.

**Required correction:** enumerate the exact seven provider calls and scopes:

- `load_player_stats(2015..2025, summary_level="week")` — weekly, all-position;
- `load_player_stats(2015..2025, summary_level="reg")` — season summary/CPOE;
- `load_players()` — full static snapshot;
- `load_rosters(2015..2025)`;
- `load_ff_playerids()` — full static crosswalk;
- `load_draft_picks()` — full fetch, admitted coverage 1980–2025;
- `load_pbp(2015..2025)` — REG rows consumed after raw capture.

State a bounded transfer/storage estimate per call (or a clearly labeled
unknown requiring measurement) and the aggregate snapshot destination. David's
yes/no must describe the actual operation his word would authorize.

### QB-R3-B2 — BLOCKER — “fully powered” is an unsupported pre-result assurance

V3 lines 54–56 tell David that contrasts 1–10 are “fully powered.” F32 and the
H5 fold floor do not apply to those contrasts, but that does not establish
their power. Each model comparison still needs at least 5/8 evaluable folds;
each fold below n=20 is `fold_starved`; source admission, cohort construction,
feature missingness, and degeneracy have not run.

**Required correction:** say contrasts 1–10 are **unaffected by the F32/H5
failure**, while their own registered power/evaluability remains unknown until
execution and may honestly land `unsupported_power` or carry `fold_starved`.
Describe H2 as the registered comparisons involving the rushing hypothesis
under test, not as an already powered omnibus test of the “best single factor.”

This is BLOCKER severity because the overclaim is inside the provider decision
packet presented to David, not merely internal implementation prose.

### QB-R3-W1 — WARN — the structured counter does not contain semantic rounds 1–2

V3 says framing rounds 1–2 were carried into the run as
`finding-framing-1-1..3`. The active run actually has one open framing round,
index 1, containing only the three round-2 findings; it contains neither the six
round-1 findings nor closed records for the two prior semantic rounds. Before
relying on “round 3 of 5” for cap routing, either reconstruct the prior rounds
honestly or disclose that the structured counter is mechanical round 1 and the
semantic review count is 3. Do not let the Judge-routing counter silently
undercount prior review.

## Gate posture

Framing remains open. No RED round, provider fetch, data copy, study execution,
result artifact, manifest mutation, commit, or push is authorized by this
review.

