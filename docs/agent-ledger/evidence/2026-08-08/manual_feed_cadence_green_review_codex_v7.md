# Manual-feed cadence GREEN seventh review — Codex v7

**Verdict:** NOT CLEAR — one bounded container-type hole  
**Reviewed pins:** `8ee3ce8a…`, `31ee07dd…`, `9f4a3f9c…`, `670a29d7…`

The required coverage-field and missing-event lifecycle repairs hold; focused tests pass 155 and
Ruff is clean. Two values in the same container-validation class remain:

1. `covered_seasons: null` is present, bypasses the missing-field guard, and validates as OK because
   list validation is conditional on `seasons is not None`. The engine later attempts to iterate it.
2. `calendar.game_week_completions: 7` raises `TypeError: 'int' object is not iterable` inside
   `_validate_inputs()`. Because `execute()` loads the immutable snapshot before entering the
   per-source isolation loop, this exception aborts the whole controller.

Required repair: when present, `game_week_completions` must be a list; every required
`covered_seasons` value must be a list, including rejecting null. The load boundary must convert any
unexpected validation exception into `INPUTS_INVALID` so no malformed artifact can bypass aggregate
isolation. Pin null coverage and scalar completion at both validator and full-controller surfaces.

All other reviewed mechanisms are CLEAR. No source execution, scheduler, paid action, provider
contact, commit, or push occurred.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
