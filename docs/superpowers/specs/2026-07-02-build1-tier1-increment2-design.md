# BUILD-1 Tier-1 Graduation — Increment 2: What-Changed + Trust Console — Design Spec

**Status:** THREE-WAY CLEAR (Codex spec CLEAR for RED v3, R2 withdrawn on re-probe; Gemini CLEAR) + **DAVID RATIFIED BOTH GRADUATIONS 2026-07-02**. Build authorized on branch `feature/build1-tier1-increment2`.
**Prior:** Increment 1 (PR #109) — ladder machinery + Roster Capacity graduated. This increment is **registry + tests ONLY**: prove the existing ladder carries more surfaces; no route/evaluator/adapter/schema change (Codex boundary 6). Closed component-id set unchanged.
**Plan:** `docs/superpowers/plans/2026-07-02-build1-tier1-increment2-plan.md`.

## 0. Scope

**Graduating (cap-2, Codex-concurred):**
1. **`daily_what_changed`** (Gemini #1 — the daily-login core). Route `/api/league/what-changed`; producer artifact `app/data/what_changed/what_changed_latest_report.json` (gitignored — runtime status only, R8); both live preconditions.
2. **`model_trust_console`** (Gemini #2 — the self-certification objection died with Increment 1). Route ids `/api/trust-surface/{position}` + `/api/trust-surface/{position}/model-card` (parameterized — must match the OpenAPI snapshot paths exactly, the tripwire's assertion basis); producer artifacts = the TRACKED trust truth set `app/data/backtest/trust_surface/latest/{backtest_result,model_card_source}_{QB,RB,WR,TE}.json` + `manifest.json` (Codex R1; tracked-but-still-runtime-status-only per R8 — presence is checked at request time, never as CI evidence); both live preconditions.

**Explicitly SEQUENCED, not rejected — Trade Lab (the soft-verdict trap, Gemini):** a Diagnostic Grade badge on the trade evaluator is the maximal badge-as-verdict surface. **Graduation precondition (binding for the future increment):** the Trade Lab FE must first ship the mitigation contract — model (xVAR) and market (FantasyCalc) lanes at equal visual weight + explicit copy that the panel computes no trade-outcome delta and evaluates no transaction suitability. Until that FE increment ships, Trade Lab stays Tier-0.
**HELD indefinitely — League Pulse (Gemini):** opponent-posture heuristics are narrative-driven; certifying them implies false mathematical certainty about opponent intent.

## 1. Registry entries (the GREEN deliverable)

Each entry's `ratified_date` is determined by **David's §4 ruling at spec CLEAR, before GREEN** — a ratified entry commits its stamp, a declined one commits `null` and honestly reports `awaiting_david_ratification` (R5). RED asserts both states via temp registries. Components use the CLOSED id set; the `expectation` free text carries surface-specific semantics; `optional` discloses non-applicability (never silent).

**daily_what_changed** — components:
- `audit_hygiene`: evidence `tests/contract/test_daily_what_changed_api.py`, `scripts/scan_league_opportunity_no_verdict.py` — fail-closed route contract + cordon enforcing.
- `deterministic_range_disclosure`: evidence `frontend/src/what-changed/DailyWhatChanged.test.tsx`, `tests/contract/test_daily_what_changed_diff_engine.py` — expectation: **signed neutral deltas, `-0` preserved (`Object.is`), comparison-window dates + `semantic_output_hash` vintages disclosed; a stale model side reports its window honestly, never a fabricated flat `0.00` delta (Gemini seed B); gap-dilated deltas are guarded by the `capture_health_ok` live precondition (Gemini seed A — a holed capture timeline degrades the badge before a misleading "1-day" delta can carry it)**.
- `mif_breaker`: evidence `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py`, `tests/unit/test_realized_outcome_scorer.py` — model-output deltas make input fidelity path-material; off-season `insufficient_data`.
- `no_directive_copy`: evidence `frontend/scripts/check-banned-language.mjs`.

**model_trust_console** — components:
- `audit_hygiene`: evidence `tests/contract/test_trust_surface_route.py`, `tests/contract/test_trust_publication_audit.py`.
- `deterministic_range_disclosure`: evidence `tests/contract/test_harness_trust_w3_modelcard.py`, `tests/contract/test_trust_surface_v2.py` — expectation: **uncertainty is disclosed-or-null, never fabricated (nullable R², BCa CIs with bounds shown); CIs are tied to the artifact run they came from — a run-mismatch between displayed CIs and the actively served model is guarded by the `model_provenance_ok` live precondition (Gemini seed C: stale-CI/run-mismatch degrades the badge)**.
- `mif_breaker`: evidence `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py`, `tests/unit/test_realized_outcome_scorer.py` — the console reports model trust; input fidelity is path-material; off-season `insufficient_data`.
- `no_directive_copy`: evidence `frontend/scripts/check-banned-language.mjs`, `frontend/src/trust/ProvenanceFooter.test.jsx`.

## 2. Tripwire RED rows (Codex-owned; per-surface HARDCODED semantics — boundary 5)
1. Registry loads and names exactly `[roster_capacity, daily_what_changed, model_trust_console]`; each new surface's `route_ids` ⊆ committed `frontend/openapi.json` paths (the Increment-1 assertion basis).
2. Every new evidence path exists; producer artifacts stay non-evidence + non-CI-checked (R8).
3. **What-Changed semantic tokens** (in its evidence files): `Object.is` / `-0` handling, `semantic_output_hash`, `player_name ?? player_key` identity, comparison-window assertions.
4. **Trust Console semantic tokens**: nullable-R²/`r2_oos`, BCa/`bca` CI assertions, provenance/run-identity assertions.
5. Both new entries `ratified_date: null` at RED time → live route reports `awaiting_david_ratification` for both (R5 proof) while roster_capacity stays `diagnostic_grade_active_limited`; after David's §4 stamps, both flip to `_limited` (mif dormant) — asserted via temp-registry route tests, real-registry smoke at ship.
6. No machinery diff: the tripwire fails if this increment touches evaluator/route/adapter modules (registry + tests only — file-scope guard via git-diff check in review, not a committed test).

## 3. Guardrails
Increment-1 guardrails hold unchanged (decision_supported false everywhere; badge vocabulary ban; no Tier-2 pathway; CI-safe temp fixtures). NEW: the What-Changed volatility-context recommendation (Gemini: serve historical volatility baselines beside deltas) is noted as a FUTURE surface enhancement, NOT a graduation gate — graduation certifies what the surface honestly does today.

## 4. David ratification points (two stamps)
Per the R5 gate, each surface graduates only on David's word. **RATIFIED: David stamped BOTH graduations 2026-07-02 (`daily_what_changed` + `model_trust_console`) after confirming three-way cockpit alignment** — GREEN commits both entries with `ratified_date: 2026-07-02`; the real-registry live smoke expects three `diagnostic_grade_active_limited` surfaces. **Committed end-state pinned (Codex R3):** whatever David rules at CLEAR is what GREEN commits — ratified entries carry their `ratified_date` stamp and the real-registry live smoke expects `diagnostic_grade_active_limited`; a declined entry commits `ratified_date: null` and the smoke expects `awaiting_david_ratification`. RED asserts BOTH states via temp registries regardless (state-independent gate).

## 5. Resolved (kickoff, 2026-07-02)
Gemini rank (WC #1, Trust #2, Trade Lab hold, League Pulse hold-indefinitely) + seeds A (gap-dilated delta → capture-health precondition), B (stale-model false-zero → insufficient/never-flat-0), C (stale-CI run-mismatch → provenance precondition) — all encoded §1/§2. Codex boundaries 1–6 (cap-2; per-surface hardcoded RED rows; existing component ids + optional-with-disclosure; mif only where path-material; registry+tests only) — all adopted. Claude updated from Trade-Lab-first to the Gemini set on soft-verdict grounds; Codex ACCEPTED explicitly.
