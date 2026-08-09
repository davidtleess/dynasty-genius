# League-scoped events GREEN review — Codex v1

**Date:** 2026-08-08 21:06 ET  
**Layer:** Layer 1 ingestion control  
**Verdict:** **NOT CLEAR**

## Reviewed pins

- `src/dynasty_genius/sources/feed_cadence.py`
  `ae2a4dcfc893b552bf7f63e51fee1508c5dc2660cc8641fefa6b7f63a9409ce2`
- `src/dynasty_genius/sources/daily_control.py`
  `868b675885333170f4ab7f19334d7facffb4f5621e0119ffec48844d434e0ca5`
- `tests/contract/test_league_scoped_events_red.py`
  `94f7edf275360c5e568ee93a505042b09cdd6d16804ae84520eea1788f7d1fe8`
- `tests/contract/test_manual_feed_cadence_red.py`
  `4aab001c8acec1d955b2e935facd83c88cb0a80123bf9ad64dd47f9255cf5c66`
- `tests/contract/test_layer1_daily_control_red.py`
  `4961677233cb3740bdf952580fef2bd701314ad47c66662cae937f62c6241074`

All five pins were independently recomputed and matched. The three touched contract files passed
`170/170`; Ruff on the five reviewed paths and `git diff --check` were clean.

## Findings

### F1 — missing game facts erase a valid independent PlayerProfiler event

`playerprofiler.player_season` responds to four clocks: game-week completion, season final,
combine completion and draft completion. `evaluate_stream()` currently returns `undetermined`
immediately when its NFL competition block is absent, before `_last_event()` can inspect the
top-level combine/draft facts.

Direct reproduction used an empty competition registry, a declared combine completion on
2026-03-05, held data ingested on 2026-03-01, a valid offer observed on 2026-03-06 and an evaluation
instant on 2026-03-06. Actual result:

```json
{"cadence":"undetermined","coverage":"adequate","trigger":null}
```

The independently observable `combine_complete` event is newer than the held vintage, so the
correct result is `due` with trigger `combine_complete`. Missing game-calendar evidence must make
only the game-driven part uncomputable; it must not suppress another declared trigger.

Required contract: with no NFL block, a newer combine/draft event makes `player_season` due; with
no actionable global event, the same missing NFL block remains `undetermined`.

### F2 — phantom stream removal is incomplete at the disposition boundary

The registry correctly removes `pff.grades`, but the public `stream_disposition()` surface still
returns this for that nonexistent stream:

```text
StreamDisposition(source='pff', stream='grades', model_use_forbidden=False,
                  retained_raw=True, ingestion_authorized=True,
                  creates_refresh_obligation=False, consumer_authorized=False)
```

That says ingestion and raw retention are authorized for an identity the same module says names no
feed. The disposition boundary must refuse an undeclared stream (preferably a stable
`policy_missing` `CadenceError`) or otherwise represent it as nonexistent; it must not authorize a
phantom. Add a regression against `pff.grades` and an arbitrary unknown key.

### F3 — `_declarations()` still publishes a false type contract

`_declarations()` and its local `out` are annotated as lists of three-tuples, while the collection
intentionally contains both three- and four-tuples. This exact correction was required in the
20:52 fixture-migration ruling and remains undone. Define a truthful declaration alias/union and use
it at both annotations.

### F4 — the grade enforcement regression accepts unrelated failures

`test_s7c_the_grades_PROHIBITION_is_COLUMN_level_and_survives_the_phantom_removal` uses
`pytest.raises(Exception)`. The enforcing function's contract is a `ValueError` naming a prohibited
subjective PFF grade column. The broad assertion would pass on an unrelated `TypeError`,
`AttributeError` or other regression. Require `ValueError` and the grade-leakage diagnostic.

## Ruling

**NOT CLEAR.** Repair F1-F4, add the two behavioral counter-cases for F1, and return fresh pins plus
focused/full gates. No governed input artifact, B21/CFBD capture, scheduler, paid call, provider
contact, commit or push is authorized by this review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
