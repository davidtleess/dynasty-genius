# Manual-feed cadence GREEN sixth review — Codex v6

**Verdict:** NOT CLEAR — two behavioral omissions  
**Layer:** Layer 1 cadence/coverage truthfulness  
**Reviewed pins:** `ffe85416…`, `6ef0e894…`, `65f17e97…`, `3372cf4d…`

The malformed semantic/key cases, valid counter-cases, immutable snapshot and controller
fail-closed path now hold. Focused tests pass 147; Ruff and diff-check pass. Two direct
counterexamples remain.

## Y1 — Evidence records may omit coverage and then report `adequate`

The prior ruling required every non-null held/offer record to carry `covered_seasons` as a list of
integer seasons. The implementation validates the field only **if present**. This artifact validates
as `ok`:

```json
{
  "calendar": {"season": 2026, "week1_kickoff": "...aware...", "final_game": "...aware..."},
  "held": {"pff": {"nfl_receiving_summary": {"ingested_at": "...aware..."}}},
  "offer": {"pff": {"nfl_receiving_summary": {
    "observed_at": "...aware...", "provenance": "vendor_export_manifest"
  }}}
}
```

The engine converts both missing fields to empty sets and reports coverage `adequate`. Missing
coverage evidence has become positive reassurance.

Required repair: every non-null held and offer record must require `covered_seasons`; validate it as
a list of integer seasons. Add missing-held and missing-offer cases plus a controller-surface
counter-test proving coverage can never become adequate from absent coverage evidence.

## Y2 — Missing game-week facts report `current` during the season

The repaired `_game_week_completions()` says that absent declared completions must not invent an
event and dependent streams should be undetermined. But `evaluate_stream()` falls through to
`_in_active_window()` and returns `current` whenever now is between kickoff and final.

Direct reproduction at 2026-09-20 with held PFF data, an offer, and no
`game_week_completions`:

```text
cadence=current, coverage=adequate, trigger=None
```

That is the same false reassurance as the removed timer approximation: the engine lacks the event
facts needed to know whether a week completed.

Required repair: for policies depending on `game_week_complete`, missing governed completion or
availability evidence must produce cadence `undetermined`, never `current`. Add preseason,
in-season-missing-evidence, before-first-completion, and after-declared-completion counter-tests so
`not_due`, `undetermined`, `current`, and `due` remain behaviorally distinct.

No source execution, scheduler, paid action, provider contact, commit, or push occurred.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
