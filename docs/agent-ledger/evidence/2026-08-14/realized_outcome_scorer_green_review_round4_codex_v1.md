# Realized-outcome scorer wiring — green review round 4 (Codex v1)

Date: 2026-08-14
Work item: `TW0813-SCORER-1`
Role: adversarial reviewer / RED owner
Verdict: **CLEAR**

## Exact change verified

- Revised hardening file: `tests/contract/test_realized_outcome_scorer_wiring_hardening.py`
- SHA-256: `1feeeafdf1a5746295fbdcc46cee065f36e7650b80f14b05554d0117d4ad2ebf`
- Product pins remain unchanged:
  - script: `42f5b736afe77076abef0834bb36d0254067288fde05e41cb10f203f1e773677`
  - scorer core: `e0b9f23449c57de47a942b6b51ff3448badea7e423aeb99d5efec48a96689009`

The only semantic-round-4 edits are the three R3-B1 contract rows requested by the RED owner:

1. `games: ()` is a malformed schedule and fails named with a terminal marker.
2. `rows: ()` is a malformed prediction envelope and fails named with a terminal marker.
3. A well-formed empty mapping envelope (`rows: [], coverage: {}`) noops as `no_predictions_for_target`.

## Falsification and checks

- The schedule list-guard-deletion mutant now fails on the new tuple row: **1 failed, 5 passed**.
- The prediction tuple-acceptance mutant now fails on the new tuple row: **1 failed, 6 passed**.
- Hardening file: **25/25 passed**, **25 collected**.
- Full focused bundle: **92/92 passed**.
- Ruff: clean.
- Diff check: clean.

## RED adoption and verdict

I adopt and re-pin the 25-row hardening set at SHA-256
`1feeeafdf1a5746295fbdcc46cee065f36e7650b80f14b05554d0117d4ad2ebf` as the final RED
hardening contract for this cycle. All review findings are resolved. The scorer cycle is CLEAR to
proceed to its authorized gate-path commit. Push remains David's keystroke, and the first live
finalized-week scoring run remains David-gated.
