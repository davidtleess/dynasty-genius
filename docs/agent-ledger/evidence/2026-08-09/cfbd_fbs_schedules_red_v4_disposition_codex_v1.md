# CFBD FBS schedules RED v4 — residual disposition

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Implementation lane: Codex  
Review answered: `cfbd_fbs_schedules_red_v3_review_codex_v2.md`

## Revised pin and RED gates

- `tests/contract/test_cfbd_fbs_schedules_capture_red.py`, 1,465 lines:
  `8eb194c5dddc78275dfe4f3aed728e8a6603083909be4a37063ebf63c86b1d97`
- Focused pytest: **171 failed / 1 disclosed pass**, true exit 1, zero setup or collection
  errors. The failures are the intended absent-module/CLI RED state.
- Ruff and Python compile: **clean**.
- Full-suite collection: **5,238 tests**, exit 0, zero collection errors.
- No provider request was made. GREEN remains closed pending independent review.

## Residual disposition

### R1 — accepted in full

The contradiction is removed. `seasonType=both` is the query selector for this route, while returned
games are scoped to `regular|postseason`. Both response values have positive controls. Literal
`both`, `allstar`, `spring_regular`, and `spring_postseason` response values now fail with the
specific `season_type_scope_mismatch` code. The 16-class retrieved-failure audit matrix uses that
same rule; an unknown string remains the distinct OpenAPI-level `enum_invalid` error.

### R2 — accepted in full

G2b builds two exact raw mutants that Python's default `json.loads` silently accepts by keeping the
last value: one duplicate `Game.id`, and one duplicate nested `GamePlayoff.competition`. Each last
value is valid, so no downstream field, enum, ID, or scope check can accidentally catch it. The
route must use duplicate-aware JSON parsing at every object depth and fail with the stable
`duplicate_json_member` code before canonical publication. Both mutants require exact-byte
quarantine, no raw/check/vintage/index/marker artifacts, and exactly one sanitized failed-audit
record carrying reason, raw SHA, and actual request count.

## Standing

This artifact requests independent CLEAR only. F1-F7 remain accepted from the prior review. No
GREEN, live paid request, canonical capture, manifest/catalog change, commit, push, scheduler,
cadence input, or consumer wiring has occurred.
