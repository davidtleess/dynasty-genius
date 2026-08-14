From Claude (implementing lane) — TW0813-SCORER-1: R2-B1/R2-B2 fixed + pinned; green-review re-review requested (semantic round 3) [w#scorer-wire-1]

Both round-2 findings ACCEPTED and fixed; both resolved in the run (finding-green-review-1-6..7).

R2-B1 FIXED: _schedule_shape_ok now requires a PRESENT list `games` — a missing key or games:null is a malformed envelope failing schedule_shape_invalid with the terminal marker and zero downstream loader calls; a present `games: []` remains the healthy off-season control. Your two escaping shapes are pinned (the G1 parameterization now covers five shapes).

R2-B2 FIXED: the envelope boundary is fail-closed with one named reason — a mapping envelope must carry a present list `rows` AND a mapping `coverage`, every row must be a mapping, and a loader returning anything that is neither mapping nor list fails prediction_envelope_invalid with marker (your raw-ValueError coverage:string case included). The bare-list legacy adapter is preserved exactly (empty list still noops no_predictions_for_target — pinned as a positive control alongside the six malformed-envelope pins).

Revised pins:
- scripts/run_realized_outcome_scoring.py — SHA-256 42f5b736afe77076abef0834bb36d0254067288fde05e41cb10f203f1e773677
- tests/contract/test_realized_outcome_scorer_wiring_hardening.py — SHA-256 cb719113c4675323697ef4655867646349825aa46115d1eda347a21defb78b7e (22 rows: prior 13 + 2 schedule shapes + 6 envelope shapes + 1 legacy control)
- core unchanged e0b9f234… · declaration unchanged 77544b3b…

Census (rerunnable): hardening + RED + unit + both legacy files 89/89 · Ruff + strict compile clean · FULL suite 5,960 passed / 15 failed — solely the standing cadence RED; delta = exactly the 9 new rows; zero new failures.

PLEASE REPLY with: (a) green-review CLEAR with enumerated checks + your final adoption/re-pin of the 22 hardening rows as RED owner — which sends the cycle to its gate-path commit (push stays David's keystroke, already worded, not requested here), OR (b) further findings with reproducers.
