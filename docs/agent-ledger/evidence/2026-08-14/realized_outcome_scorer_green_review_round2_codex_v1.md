# TW0813-SCORER-1 — Green review round 2 (Codex v1)

**Verdict:** NOT CLEAR — two BLOCKER findings. This is semantic cycle green-review round 2;
the reinitialized structured run records it in its mechanically open `green-review` round 1.

**Pinned artifacts verified:**

- `scripts/run_realized_outcome_scoring.py` —
  `c5c2bae30e4402d4faf3f1ba737ff14befdf51e973fb9efaf287ad38f7ccce97`
- `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py` —
  `e0b9f23449c57de47a942b6b51ff3448badea7e423aeb99d5efec48a96689009`
- `tests/contract/test_realized_outcome_scorer_wiring_hardening.py` —
  `9256dfe04713738c523c8209c2a651f2b92248a7c954feb0e64b38391f6376da`
- `app/config/realized_outcome_frozen_predictions.json` —
  `77544b3b02850ceee1658806508af6e1af739fdf4cb0d756107195d6bb8bfce8`

## Findings

### R2-B1 — BLOCKER — schedule-shape validation still accepts missing/null `games`

**Criterion:** fail-closed external-data shape; the stated contract is dict root, list
`games`, dict rows.

`_schedule_shape_ok` at `scripts/run_realized_outcome_scoring.py:102-113` rewrites a missing
or null `games` value to `[]`. The hardening parameterization at
`tests/contract/test_realized_outcome_scorer_wiring_hardening.py:38-44` covers a non-dict
root, string `games`, and a null row, but not a missing `games` key or `games: null`.

Hermetic public-runner reproducer:
`/private/tmp/repro_scorer_g1_null_games.py`.

Observed for both `{season, week}` and `{season, week, games: null}`:

- returned `status=noop`, `noop_reason=week_not_finalized`;
- wrote a healthy noop terminal marker;
- was indistinguishable from the valid `{games: []}` offseason control.

Smallest remediation: require the `games` key and require its value to be a list; pin both
missing and null shapes to `failed/schedule_shape_invalid`, marker written, downstream loaders
not called. Preserve `games: []` as the healthy zero-game control.

Structured finding: `finding-green-review-1-6`.

### R2-B2 — BLOCKER — malformed prediction envelopes smooth to noop or escape markerless

**Criterion:** fail-closed production-loader envelope and terminal-marker completeness.

The new normalization at `scripts/run_realized_outcome_scoring.py:299-306` calls
`list(loaded_predictions.get("rows") or [])` and
`dict(loaded_predictions.get("coverage") or {})` without validating the mapping contract
`{rows: list[dict], coverage: dict}` or the row shapes.

Hermetic public-runner reproducer:
`/private/tmp/repro_scorer_prediction_envelope_shapes.py`.

Observed:

- missing `rows` -> healthy `noop/no_predictions_for_target` marker;
- `rows: null` -> healthy `noop/no_predictions_for_target` marker;
- `rows: "not-a-list"` -> healthy `noop/week_not_finalized` marker;
- `coverage: "bad"` -> raw `ValueError`, with no terminal marker.

Smallest remediation: preserve the explicitly pinned bare-list legacy adapter, but for a
mapping require present list `rows`, mapping `coverage`, and dict rows before the empty-list
noop. Every malformed envelope terminates failed with one named reason and a marker; add
missing/null/wrong-type rows, non-dict row, and wrong-type coverage contract rows.

Structured finding: `finding-green-review-1-7`.

## Checks completed

- Read the complete relevant product diff and hardening contracts; `git diff --check` clean.
- Recomputed all four hashes above; all matched.
- Focused bundle: 80 passed (hardening + original wiring RED + scorer unit + both revised
  legacy files).
- Related store/bridge/route/registration bundle: 52 passed.
- Full suite: 5,951 passed, 15 failed, 12 skipped, 9 xfailed. All 15 failures are confined
  to the standing untracked `tests/contract/test_governed_cadence_inputs_red.py` because
  `src.dynasty_genius.sources.cadence_inputs` does not exist; no new failure family appeared.
- `.venv/bin/ruff check` clean on all touched scorer files; strict Python compilation clean.
- Local-store-only probe: prediction envelope 501 eligible / 581 declared with
  `{capture_incomplete: 80}` exclusions; identity 501 mappings, timestamp
  `2026-05-16T03:28:22Z`, SHA `8ed4b675...`, duplicate count 0; week-1 util rows 0.
- Real pinned crosswalk independently contains exactly the three ambiguous PFR claims
  `CartKy01`, `HarrAl00`, `MillSt00`; the revised claim-set loader and hardening test exclude
  ambiguous attribution and preserve unambiguous attribution.
- G3 finite/range validation and G4 aware-datetime validation are correct at the pinned code;
  the core status-unverified floor delta is unchanged and its focused contract passes.
- Constitutional/scope checks: the scorer remains Layer 3 and reports only empirical
  model-performance facts; no market-value blend, UI claim, scheduler mutation, commit, push,
  provider contact, or live scoring run occurred. Layer-2 identity evidence was checked from
  the pinned local crosswalk only.

## RED adoption position

The 13 hardening rows at `9256dfe0...` are substantively sound and retained as an offered RED
extension, but the set is not complete enough for final adoption/CLEAR. Add the two R2-B1
schedule rows and the R2-B2 prediction-envelope family above; Codex will re-review the revised
pins. No live-provider verification is authorized or needed for these fixes.
