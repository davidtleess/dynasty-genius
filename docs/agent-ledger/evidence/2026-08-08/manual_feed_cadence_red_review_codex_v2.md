# Manual-feed cadence RED re-review — Codex v2

Date: 2026-08-08
Layer: 1
Reviewed pin: `b12478076305ba47a3a3215767c8359b9cee2b8fe30e1f29918e8d9778c34521`
Verdict: **NOT CLEAR**

Independent gates reproduced: 24 failed, 0 passed, 0 skipped, zero collection errors; true pytest exit 1. `.venv/bin/ruff check` passed.

The rewrite repairs the original F1–F8 mechanisms, but seven residual contract holes remain.

1. **David's all-ingestion authorization supersedes S7c.** David ruled “just to be clear i authorize all consumption within the scheduled and determined frequency”, then clarified “not just manual - all injestion”. For every cadence policy that is actually determined, ingestion is authorized. Grades remain prohibited as model inputs and retained raw, but S7c must not assert `consumer_authorized=False` or no refresh obligation. Pin ingestion authorization true and let the reviewed PFF event cadence govern acquisition. This does not buy paid access, invent a route/cadence, contact a provider, or promote grades into models.

2. **`current` is never behaviorally exercised.** It appears only in the vocabulary. A GREEN that never returns `current` passes all 24 tests. Add the complete transition: before an event `not_due`; after an unsatisfied availability event `due`; after a durable ingest satisfying that event `current`; after the next event `due` again.

3. **Undetermined cadence is unrepresentable.** S5c says RotoViz/Campus2Canton are “unknown on both axes”, but asserts only coverage and age because the cadence vocabulary has no honest value. David authorized ingestion only within a determined frequency; these routes do not yet have one. Add a cadence value such as `undetermined` (distinct from coverage `unknown`) and assert it. Do not report `not_due`, which would claim a cadence judgment was made.

4. **PFF NFL and FBS availability windows are still not distinguished.** S7 tests one NFL family after Wednesday and one quiet NCAA history case. It never pins NFL noon-next-day versus FBS 08:00-next-day, nor a just-before-window counter-case. `game_week_complete` alone permits GREEN to mark both due immediately after kickoff. Inject completed-game and availability times; assert each family flips only when its relevant reviewed window passes. No universal weekday.

5. **Duplicate policy rejection is still not structural.** Iterating `streams_for()` and adding returned keys to `seen` proves only that this public output is unique; GREEN can deduplicate duplicate declarations before returning it. Test the raw policy declarations or require the policy constructor/validator to reject duplicate `(source, stream)` keys.

6. **Controller aggregation counter-cases are incomplete.** S8b covers the no-stream-due/worst-coverage case only. Add: one due stream makes source cadence due; inadequate/unknown coverage remains visible without becoming an automatic-job failure; every declared stream is serialized; and no source rollup substitutes for the per-stream truth.

7. **Coverage adequacy must allow retained supersets.** S4c pins equality only. Layer 1 may legitimately retain extra historical seasons. Add a counter-case where held seasons are a strict superset of the observed offered set and remain adequate; adequacy requires offered coverage to be contained in held coverage, not exact equality.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
