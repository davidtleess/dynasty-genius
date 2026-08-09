# Manual-feed cadence GREEN fifth review — Codex v5

**Verdict:** NOT CLEAR — one remaining schema-validation class  
**Layer:** Layer 1 governed cadence-input integrity  
**Reviewed pins:** `ffe85416…`, `6ef0e894…`, `a09dac28…`, `bffd31cf…`

The prior single-snapshot, hermetic-absence, and behavioral report-instant repairs hold. Independent
focused tests pass 136 and Ruff is clean.

## X1 — Semantic fields and governed key identities remain unvalidated

`_validate_inputs()` still returns `INPUTS_OK` for:

```text
calendar.season = "not-an-int"
held.pff.nfl_receiving_summary.covered_seasons = "2025"
offer.pff.nfl_receiving_summary missing provenance
held.pff.nfl_typo = {...}
availability.nlf = {...}
```

These are fields/keys the engine consumes or depends on. A string `covered_seasons` is iterated
character-by-character by the engine; an unknown stream or misspelled availability window is
silently ignored; missing offer provenance fails only if incidental held data reaches evaluation;
and a nonnumeric season fails only on the contiguous-coverage path. This preserves the exact
source-dependent boundary defect the validator is meant to eliminate.

Required repair:

- require `calendar.season` to be an integer season;
- require `game_week_completions` to be a list before validating entries;
- for every held/offer record, require `covered_seasons` to be a list of integer seasons;
- require nonempty offer provenance in addition to observed time;
- reject unknown source/stream keys against the policy registry;
- reject unknown availability-window keys (the current engine supports NFL/FBS windows only);
- add acceptance counter-tests for a minimal valid artifact and retained season supersets.

Pin each malformed case behaviorally at `_validate_inputs()` and at least one at the full controller
surface to prove it fails closed and still preserves source isolation.

No source execution, scheduler, paid action, provider contact, commit, or push occurred.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result and is unrelated.
