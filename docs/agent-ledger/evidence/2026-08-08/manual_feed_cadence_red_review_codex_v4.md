# Manual-feed cadence RED coverage re-review — Codex v4

Date: 2026-08-08
Layer: 1
Reviewed pin: `4ad6e20d9c76dd43449b28692ab8a42eb953f1dd1176f9a1976be90be15125bc`
Verdict: **NOT CLEAR — one finding**

The future-evidence guard, trigger ontology, corrected evidence language and prior mechanisms hold. One coverage defect remains:

## C1 — the “total” required-trigger map is self-certified against an incomplete declaration set

`REQUIRED_TRIGGERS` covers only three PFF keys: NFL receiving summary, NCAA receiving summary and a cross-cutting grades key. Held evidence contains seven PFF report families across fourteen league/report lanes: passing summary, passing pressure, passing depth, receiving summary, receiving depth, receiving scheme and rushing summary for NFL/NCAA. A GREEN may simply omit the other held families from `streams_for()`; `mapped <= declared` and the `unmapped` calculation then pass because both sides inherit the same omission.

Pin the expected source/stream keys in the test from the measured Layer 1 inventory, independent of module declarations, and require equality for PlayerProfiler/PFF. Then map every expected lane/family to its required triggers. A family-level representation is acceptable if it explicitly preserves the NFL/FBS availability distinction; silent omission is not.

Also repair the live PlayerProfiler mapping: `player_season` currently requires only `season_final`, but the measured file contains proprietary in-season cumulative metrics and rookie/prospect derivatives. Its acquisition triggers must include the relevant union—game-week completion plus season-final, combine and draft-cycle events—or it must be split into separately named datapoint families. Otherwise the RED permits the exact under-refresh David asked us to prevent.

This is the acceptance edge created by David's all-ingestion authorization: every measured, routed Layer 1 family must appear before cadence can be called complete.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
