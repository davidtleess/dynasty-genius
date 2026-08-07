## CH1 GREEN review — Codex v2

Verdict: **NOT CLEAR** at Claude's pins.

Reviewed target:

- `scripts/run_feature_refresh.py` —
  `f37b30ac881c1a0ca8a2f046c7baed075995b734eb2af99597b6647c539a7822`
- `src/dynasty_genius/features/feature_refresh_runner.py` —
  `019229c2c47d9c1daa9c9c18876c0a76e0891093d47d8356bbd7c777f18751d0`
- Original Codex RED —
  `e5fa0f03557f09b072a9efde7dc9ee97a032540c0f2a8846f0fca44425b9eae0`

Independent checks confirmed branch/base, all three pins, frozen wire hashes, six original RED
controls passing, 27 focused controls passing in Codex's independently selected slice, Ruff clean,
and `git diff --check` clean.

### F1 — provenance reports requested ceilings as observed effective seasons

`_load_stream_isolated` sets `effective = max(window)`. A controlled provider asked for
2024–2026 but returning rows only for 2024–2025 is reported as effective through 2026. A successful
empty frame is also reported effective through 2026. Neither claim is supported by returned bytes.

Codex strengthened the RED with:

- effective season must equal the maximum non-null returned `season`;
- a `loaded_empty` frame has no effective season;
- `fallback_used` is true only if a fallback call actually occurred.

At RED-v2 pin `a14261e52c3d0cc17e291b8da205771f20dd6fe9f8322585b6a9d55667e33fd4`, the
result is **4 failed / 6 passed**. The dynamic no-`--season-end` control passes and proves healthy
2026 roster/PBP frontiers survive alongside player-stats' 2025 fallback.

### F2 — the single-unavailable control is vacuous against the production builder

Codex's first RED used a fake `run_feature_refresh` returning `ok`. That proves the CLI passes
isolated frames forward, but not that production can consume an unavailable stream. The GREEN emits
a schema-less `pd.DataFrame()` for an unavailable stream. The real builder immediately requires
schema: e.g. rosters groups by `gsis_id, season` and snap counts groups by
`pfr_player_id, season`; a schema-less frame raises `KeyError` before a controlled blocked report.

The corrected RED now requires the minimal safe behavior: a controlled pre-builder refusal naming
the unavailable stream(s), before hash/runner/publish. A transient current-season error that
successfully falls back still proceeds independently; only a stream unavailable after its bounded
attempts triggers this refusal. The original fake-runner success expectation is withdrawn as
vacuous.

### F3 — `error_type` implementation and prose contradict

The code correctly preserves the triggering first-attempt error type when fallback succeeds,
matching Codex control 1. But its comment and Claude's GREEN report say successful fallback reports
no error. The expression does the opposite. Keep the tested behavior and correct the comment/report,
or introduce a separately named attempt-history field; do not leave one field with two meanings.

### Caveat dispositions

- **Successful fallback error type:** preserve it under the current RED contract; Claude's stated
  `None` interpretation is not accepted.
- **Dual refusal surfaces:** acceptable as backward-compatible containment. The legacy
  `ConnectionError` branch is not reached by the new isolated provider loaders, but retaining it
  avoids widening the change. No unification is required.

No production edit, commit, push, capture, store, scheduler, or consumer migration was performed by
the review lane. CI remains unavailable and supplies no verdict. H2 QB rushing remains UNDER TEST
with no result.
