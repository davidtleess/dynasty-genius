# League-scoped events GREEN CLEAR — Codex v1

**Date:** 2026-08-08 21:44 ET  
**Layer:** Layer 1 ingestion control  
**Verdict:** **CONTENT CLEAR**

## Cleared pins

- `src/dynasty_genius/sources/feed_cadence.py`
  `14f50a9db28093502783fc81cbb27e56a4e009ee1bc36780e0fd66b156f342b9`
- `src/dynasty_genius/sources/daily_control.py`
  `868b675885333170f4ab7f19334d7facffb4f5621e0119ffec48844d434e0ca5`
- `tests/contract/test_league_scoped_events_red.py`
  `4e55854a554b87c2f5c480bdd5c868fb3efebfc229fd6abfc9c7c304c4bcc7bc`
- `tests/contract/test_manual_feed_cadence_red.py`
  `ff2adf8f81e2ab508bef4c992e79c35fcdc04ba183d55a7eaf15b852f7f2592b`
- `tests/contract/test_layer1_daily_control_red.py`
  `4961677233cb3740bdf952580fef2bd701314ad47c66662cae937f62c6241074`

All five pins were independently recomputed and matched.

## Independent verification

- Focused three-file contract run: `179 passed`, true exit `0`.
- Ruff on the changed implementation and contract files: `All checks passed!`.
- `git diff --check`: clean.
- The declaration return and accumulator annotations now agree on the mixed declaration shape.
- The undeclared-stream contract covers an invented lane on a real source, the removed phantom, an
  unknown PlayerProfiler stream and an unknown source; all permission/retention fields remain false.
- Direct behavioral verification from the preceding review established that an observable
  draft/combine event survives a missing game-calendar block, while no actionable event preserves
  `undetermined`; real PFF lanes remain fully authorized and the removed phantom does not.
- The Head B grade regression requires its intended `ValueError` and grade-specific diagnostic.

## Scope and landing boundary

The five-file content is clear. This does not authorize a governed input artifact, B21 or CFBD
capture, scheduler work, paid access, provider contact, source execution, commit or push. Landing is
a separate action and must preserve the exact cleared pins.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
