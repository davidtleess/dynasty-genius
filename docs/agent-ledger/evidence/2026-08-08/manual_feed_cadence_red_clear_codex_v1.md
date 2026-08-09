# Manual-feed cadence RED CLEAR — Codex v1

Date: 2026-08-08
Layer: 1
Reviewed path: `tests/contract/test_manual_feed_cadence_red.py`
Reviewed SHA-256: `c2869767fc49b24611c6d1401051e07ea3603c6d03558421233ec8dbda0b4bf5`
Verdict: **RED CLEAR**

## Independent verification

- Focused RED: true pytest exit 1; 35 failed, 0 passed, 0 skipped, zero collection errors. Every failure is attributable to the intentionally absent `src.dynasty_genius.sources.feed_cadence` module.
- Ruff: passed on the reviewed test.
- PFF inventory cross-check: the test-pinned fourteen NFL/NCAA league-report lanes exactly equal the fourteen lanes independently read from `app/data/pff_exports/pff_unique_payload_inventory.csv`.
- The expected key set independently pins all fourteen PFF lanes, the retained grade disposition and five PlayerProfiler streams; declared keys must equal it in both directions.
- `playerprofiler.player_season` correctly carries the union of game-week, season-final, combine and draft-cycle triggers.

## Cleared contract

The RED now pins independent cadence and coverage axes; observable and correctly assigned per-stream triggers; provider-observation provenance and no future evidence; complete-coverage and retention-superset behavior; David's all-ingestion authority; distinct NFL/FBS availability windows; complete PFF/PlayerProfiler family coverage; unknown/undetermined routes; and controller serialization, rollup and nonfailure semantics.

No GREEN, scheduler, capture, provider contact, commit or push was performed by Codex.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
