# TW28 Identity Units A/B/D — Codex GREEN Review v2

**Disposition: CLEAR for the A/B/D implementation review.**

This CLEAR is intentionally before the repository-wide closeout tollgate. David's
ordered sequence is RED → GREEN → Codex enumerated CLEAR → full-suite tollgate →
separate A/B/D commit. Unit C remains a different thread and is not cleared here.

## Enumerated checks

1. **Split boundary — CLEAR.** The implementation changes only the Engine B identity
   producer, the frozen crosswalk's tracking rule, the frozen crosswalk itself, and
   the A/B/D contract. No Unit C route copy, player-detail component, API route,
   name matcher, row targeting, sentinel policy, or canonical-key bridge is present.

2. **Missing/corrupt crosswalk fail-closed behavior — CLEAR.** Missing files,
   invalid JSON, non-object roots, missing/non-list `entries`, non-object entries,
   non-string identifiers, undecodable UTF-8, and repeated keys inside any decoded
   JSON object produce stable named reasons instead of empty maps, codec prose, or
   JSON last-write-wins.

3. **Crosswalk collision semantics — CLEAR.** Exact parsed-object repeats are
   tolerated and counted. Conflicting GSIS mappings and conflicting Sleeper
   mappings abort before either index is partially written. JSON null and blank
   identifiers remain absent rather than becoming synthetic keys.

4. **Prediction totality — CLEAR.** An empty prediction collection and a prediction
   without a GSIS id abort. Exact repeated predictions are counted and collapsed;
   conflicting repeats abort. These cases are not mislabeled as identity orphans.

5. **Visible triage accounting — CLEAR.** Positive partial coverage emits raw
   prediction count, successful join count, orphan count, deterministic GSIS-sorted
   orphan facts, crosswalk duplicate count, and prediction duplicate count. Missing
   facts remain null; names and positions are not guessed.

6. **Policy boundary — CLEAR.** Zero successful joins aborts, closing the explicitly
   authorized empty-board path. Positive partial coverage remains publishable.
   No partial-coverage floor is selected or implied; David's open policy ruling is
   preserved.

7. **Real-payload positive control — CLEAR.** Independent execution against the
   frozen production dependency produced 7,952 GSIS mappings, 6,117 Sleeper
   mappings, zero crosswalk duplicates, 503 predictions, 501 joins, zero prediction
   duplicates, and exactly two sorted orphans:
   `00-0040058` Nick Kallerup (`sleeper_id_missing`) and `00-0040534`
   Ke'Shawn Williams (`sleeper_id_missing`).

8. **Reproducibility/trackability — CLEAR.** The production loader resolves
   `app/data/identity/_runs/ff_playerids_20260516.json`; its SHA-256 is
   `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.
   The exact payload is staged for tracking while sibling run artifacts remain
   ignored.

9. **Compatibility and preservation — CLEAR.** The scheduled-refresh contract
   preserves prior runtime artifacts on producer abort. The tuple/list-compatible
   container subclasses preserve existing caller and monkeypatch contracts. With
   conflicting Sleeper mappings rejected at parse time, removing the old
   `seen_sleepers` silent-drop guard does not open a second many-to-one join path.

10. **Independent verification — CLEAR.** Codex ran 43 focused-plus-sibling tests:
    43 passed. Ruff passed on the touched producer/test and on governed `src app`;
    `git diff --check` passed. The focused contract contains 21 cases, including the
    two decoder failures added after GREEN review v1.

11. **Residual disclosure, not absorbed into this CLEAR.** The pre-existing generic
    `_load_json` helper used for the Sleeper snapshot and prospect cards still uses
    ordinary `json.loads(path.read_text())`, so it does not share the crosswalk's new
    duplicate-key and named-decode protections. That is a separate input-hardening
    question, outside authorized Units A/B/D; no repair is inferred here.

## Remaining gates

- Run `scripts/verify_sprint_closeout.py` after this CLEAR and audit all ENFORCE,
  REPORT, and REMIND output.
- Commit only the A/B/D thread under David's existing commit word. Do not mix Unit C.
- A push remains separately unauthorized.

