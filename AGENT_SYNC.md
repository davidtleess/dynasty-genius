# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-16

## Active Phase

Phase 12.5 — COMPLETE: Market-leakage guard + QB Backup caveat + pre-commit hooks (merged 2026-05-15; 530 tests)
Phase 13 — IN PROGRESS: Identity Audit + Engine A Draft-Capital Bake-Off + TE Remodel Step 0
Phase 13.3 — COMPLETE: TE Model Change + Promotion (2026-05-16; 683 tests)

## Current Sprint Objective

Phase 12.5 Hygiene & UI: MERGED → main. 530 tests.
- Task 2A COMPLETE: Market-leakage guard `validate_training_csv.py` + pre-commit hook.
- Task 2B COMPLETE: QB backup-profile caveat logic in `pvo_assembler.py`.
- Task 2C COMPLETE: CI green and branch merged.

Phase 13 implementation handoff:
- Spec APPROVED by David: `docs/superpowers/specs/2026-05-15-phase13-final-spec.md`.
- Task 13.1.0 COMPLETE: Identity Contract (`docs/identity/identity_contract.md`).
- Task 13.1.1 COMPLETE: Identity Coverage Matrix audit runner (`src/dynasty_genius/audit/identity_coverage_matrix.py`).
- Task 13.1.2 COMPLETE: Review Queue + Override Registry validation (`identity_review_queue.py`, `identity_override_registry.py`).
- Task 13.1.3 COMPLETE: Identity materialization gate blocks unresolved PFF/college rows (`identity_materialization_gate.py`).
- Task 13.1 coverage-review gap CLOSED: immutable Identity Snapshot generator (`identity_snapshot_generator.py`) plus schema-compatible coverage timestamp alias.
- Task 13.2.0 COMPLETE: Draft-Capital Candidate Manifest (`src/dynasty_genius/eval/draft_capital_manifest.py`).
- Task 13.2.1 COMPLETE: Draft-Class LOOCV Harness (`src/dynasty_genius/eval/draft_class_loocv.py`).
- Task 13.2.2 COMPLETE: Draft-Capital Bake-Off evaluator (`src/dynasty_genius/eval/draft_capital_bakeoff.py`).
- Task 13.2.3 COMPLETE: Draft-Capital Promotion Decision recorded as VALIDATION_ONLY / NO PRODUCTION CHANGE (`docs/validation/phase13-draft-capital-promotion-decision.md`).
- Task 13.3.0 COMPLETE_WITH_BLOCKERS: PFF Feasibility Memo (`docs/validation/phase13-pff-feasibility-memo.md`).
    - Export Checklist READY: `docs/validation/phase13-pff-csv-export-checklist.md`.
    - TE Identity Coverage Run Plan READY: `docs/superpowers/plans/2026-05-15-phase13-te-identity-run-plan.md`.
    - Real CSV schema/sample LOCKED from David's local v10+ PFF Premium Stats `receiving_summary` exports; raw CSVs stay private/untracked.
- Task 13.3 TE SOURCE-ID COVERAGE GATE: PASSED — run_id te_2018_2025_20260516; 116/116 resolved (0.0% loss rate); 0 duplicate conflicts; artifacts promoted to app/data/identity/.
    - Source-ID coverage is complete for gsis_id + sleeper_id + pff_id; all 116 rows resolved via ff_playerids_crosswalk.
    - Initial identity snapshot intentionally empty (no DG canonical player_ids assigned in ff_playerids). Canonical backfill now complete in `identity_snapshot_te_2018_2025_20260516_canonical.json`.
    - Canonical DG player_ids assigned for all 116 TEs via `scripts/backfill_te_canonical_ids.py`; `pff_te_eligible_te_2018_2025_20260516_canonical.json` has 0 null player_ids.
- Task 13.3 PFF EXPORT REPORT: COMPLETE — `scripts/build_pff_te_export_report.py` + strict parser `src/dynasty_genius/adapters/pff_te_export.py`; redacted report at `app/data/identity/pff_te_export_schema_report_20260516.json`.
    - v10+ local manifest is ignored under `app/data/pff_exports/`; raw PFF CSVs and absolute local paths are not committed.
    - Report covers 110/116 drafted TEs after adding David's local `receiving_summary (18).csv` as the 2017 final-season export; missing 6 = 2018 (1), 2020 (2), 2021 (1), 2022 (1), 2023 (1).
    - David's local `receiving_summary (19).csv` was inspected and is a duplicate of an already represented export, so it adds no new 2020 coverage.
    - Remaining missing rows are treated as likely PFF collegiate coverage gaps (often FCS/small-school). They are excluded from archetype labeling; no imputation, fuzzy fill, or model materialization.
    - All files use snap-alignment fallback (`inline_snaps`, `slot_snaps`, `wide_snaps`), not route-alignment fields; grade columns are detected and stripped from parser output.
- Task 13.3.1 COMPLETE: TE Archetype Rubric Step 0 artifact generated at `app/data/identity/te_archetype_rubric_20260516.json`.
    - Artifact accounts for all 116 drafted TEs: 110 with PFF alignment coverage, 6 excluded as PFF coverage gaps.
    - Labeling result: 105 labeled, 5 low_volume, 6 excluded; archetypes among all rows: 69 receiving_leaning, 22 ambiguous, 14 blocking_leaning, 11 null.
    - Sensitivity result: 14 players move from receiving_leaning to ambiguous when detached threshold changes from 0.40 to 0.45.
    - Labels are snap-alignment based (`snaps_fallback`), not route-alignment. PFF remains context_signal only.
    - No raw PFF IDs, names, local paths, PFF grades, Engine A/B feature changes, model training, TE promotion, DVS, or market data.
- Task 13.3.1 DIAGNOSTIC VALIDATION COMPLETE: aggregate residual lens at `app/data/identity/te_archetype_validation_20260516.json`.
    - Joined the committed archetype artifact to the existing TE backtest prediction log: 337 labeled prediction rows, 60 unique drafted TEs.
    - Receiving vs blocking signal: realized PPG mean +3.6453, residual mean +1.5922, positive residual rate +0.3662 for receiving_leaning over blocking_leaning.
    - Output is aggregate-only and redacted; no player-level rows, source-native IDs, PFF IDs, local paths, PFF grades, model feature changes, TE promotion, DVS, or market data.
    - Interpretation: useful evidence that TE archetype labels explain outcome/residual patterns; not proof of incremental model lift until a later explicit feature bake-off.
- Task 13.3 HUMAN CALIBRATION NOTE COMPLETE: `docs/validation/phase13-te-human-archetype-review.md`.
    - David labeled clear receiving specialists, blocking specialists, and complete TEs.
    - Key implication: split snap-alignment archetype from fantasy-role archetype before any model feature bake-off.
- Task 13.3.2 COMPLETE: TE Archetype Feature Bake-Off validation artifact at `app/data/backtest/phase13/te_archetype_bakeoff_20260516.json`.
    - Tested snap-alignment, two-axis fantasy-role taxonomy, complete-TE detector, and role-risk detector candidates.
    - Result: `role_risk_detector` is the only candidate that passes the conservative acceptance rule (mean RMSE/MAE improvement and RMSE improvement in 4/4 folds). Full fantasy-role one-hot improves mean error but only 2/4 RMSE folds.
    - Validation-only: no Engine A/B production feature changes, promoted artifacts, TE promotion, market data, PFF grades, raw PFF rows, source-native IDs, local paths, or player-level committed rows.
- Task 13.3.3 DECISION APPROVED: `docs/validation/phase13-3-3-te-role-risk-decision.md`.
    - Advance only the `role_risk_detector` family to a controlled TE-only model-change experiment.
    - Not production adoption: no Engine B production contract change, promoted artifact, TE promotion, PVO scoring change, market data, PFF grades, or raw/player-level PFF output.
- Task 13.3.3 PLAN READY: `docs/superpowers/plans/2026-05-16-phase13-3-3-te-role-risk-experiment.md`.
    - Plan runs a controlled experiment with RMSE/MAE plus Spearman/Kendall deltas and explicit no-promotion gates.
    - Gemini review incorporated: sparse-duo vs unified-penalty candidates, negative coefficient gate, per-fold rank floor, alpha sensitivity at 100.0, and all-zero candidate drift test.
    - Claude review incorporated: four-fold unit tests, portable scipy rank calls, visible rank threshold, eligible-manifest/baseline-feature/alpha provenance, rank-gate failure test, and expanded PFF grade redaction terms.
    - Output remains aggregate-only and validation-only.
- Task 13.3.3 COMPLETE: TE role-risk controlled experiment artifact at `app/data/backtest/phase13/te_role_risk_experiment_20260516.json`.
    - Tested `sparse_duo` and `unified_penalty` candidates with fold-level RMSE/MAE plus Spearman/Kendall deltas, negative coefficient gate, and alpha sensitivity.
    - Primary alpha 1.0 result: both candidates improve RMSE/MAE in 4/4 folds and have negative coefficients, but both fail the rank-degradation gate; no production model-change spec is approved from this artifact.
    - Sensitivity alpha 100.0: `unified_penalty` passes all gates, suggesting stronger TE regularization is worth a separate research/spec decision.
    - Validation-only: no production Engine B contract changes, model artifact promotion, TE promotion, PVO scoring change, market data, PFF grades, raw PFF rows, source-native IDs, local paths, or player-level committed rows.
- Task 13.3.4 DECISION APPROVED: `docs/validation/phase13-3-4-te-regularization-decision.md`.
    - Continue with a validation-only TE regularization bake-off before any role-risk production model-change spec.
    - Approved alpha grid: 1.0, 10.0, 50.0, 100.0, 250.0, 500.0.
    - Candidate scope: baseline TE features only, baseline + unified penalty, optional baseline + sparse role-risk duo.
    - No production Engine B contract changes, model artifact promotion, TE promotion, PVO scoring change, market data, PFF grades, raw PFF rows, source-native IDs, local paths, or player-level committed rows.
- Task 13.3.4 COMPLETE: TE regularization bake-off artifact at `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json`.
    - Tested alpha grid (1.0–500.0) across baseline_only, unified_penalty, sparse_duo candidates.
    - unified_penalty at alpha=100.0 passes all gates: 4/4 RMSE folds, mean RMSE delta −0.0404, rank gate clear, coefficient −0.199.
    - Validation-only: no production model change, no TE promotion, no market data, no PFF grades.
- Task 13.3 MODEL-CHANGE SPEC WRITTEN: `docs/superpowers/specs/2026-05-16-phase13-3-te-model-change.md` (David approved 2026-05-16).
    - Authorizes: alpha 1.0 → 100.0, add `te_role_is_risk_profile` binary feature, retrain TE as te_v3.pkl.
    - IMPLEMENTATION COMPLETE: corrected walk-forward gate passed and TE is promoted to `ACTIVE_B`.
    - SPEC SEQUENCING CORRECTED: validate first with updated CSV + `WalkForwardDriver.FIXED_ALPHA["TE"] = 100.0`; only retrain deployment pkl and update manifest after harness gate pass.
    - Harness artifact: `app/data/backtest/runs/eba2c2e4-9742-44ed-945a-8b46a0cb670f/backtest_result_TE.json` — `overall_grade: ACTIVE_B`, G1/G2 pass, G3 deferred.
    - Deployment artifact: local ignored run `app/data/models/engine_b/runs/20260516T164503Z/te_v3.pkl`; local `v2_manifest.json` TE pointer updated.
    - `te_role_is_risk_profile` coefficients are negative in all four walk-forward folds; deployment coefficient is `-0.4721918577`.
    - `ENGINE_B_EXPERIMENTAL_POSITIONS = frozenset()`; TE fallback remains experimental only when no TE v2/v3 bundle is loaded.
    - Verification: focused model-change suite green; full suite green (`683 passed, 11 skipped`).
- 13.1 Identity Audit is the first hard gate.
- 13.2 Engine A Draft-Capital Bake-Off may research candidates, but promotion waits on locked historical identity coverage.
- 13.3 TE Remodel is Step 0 only and is gated by 13.1 TE cohort coverage.
- TE remains EXPERIMENTAL; DVS remains out of scope; market-derived data remains overlay-only.
Research inputs:
- `docs/strategies/Phase13-round2-research.md`
- `docs/strategies/Phase13-Round2-Dynasty Genius Framework Review.md`
- `docs/strategies/phase13-agent-merge-gemini.md`
- `docs/strategies/phase13-agent-merge-claude.md`
- `docs/strategies/phase13-agent-merge-codex.md`

Phase 10/11 Backtest Harness: COMPLETE.
Phase 9.5 Prospect Identity Join: MERGED → main (PR #26, merge commit 845de98). 384 tests. Back-fill complete.
Spec at `docs/superpowers/specs/2026-05-14-phase9-5-prospect-identity-join.md`.

Phase 10/11 Backtest Harness: COMPLETE. Spec APPROVED (David, 2026-05-14). 479 tests.
- Task 10.0 COMPLETE: BacktestResult Pydantic schema + 17 contract tests.
- Task 10.1 COMPLETE: MarketSnapshotStore (SQLite) + 6 unit tests. fc_snapshots.db gitignored.
- Task 10.2 COMPLETE: daily FantasyCalc snapshot script + 5 unit tests.
- Task 10.3 COMPLETE: WalkForwardDriver feature fold builder with temporal isolation + 7 unit tests.
- Task 10.4 COMPLETE: statistical metric functions (Kendall τ-b, Spearman ρ, NDCG, Precision@k, Wilson CI, HLN-DM) + 17 unit tests.
- Task 10.5 COMPLETE: WalkForwardDriver.run() — 4-fold loop, Ridge refit at fixed alpha, BCa CIs, BacktestResult returned; market fields all None + 15 contract tests.
- Task 10.6 COMPLETE: BacktestResult artifact persistence contract tests.
- Task 10.7 COMPLETE: market comparison integration (join snapshots, populate NDCG) + 6 unit tests.
- Task 10.8 COMPLETE: gate evaluator (evaluate_promotion_gates, ACTIVE_B_VALIDATED logic, G3 deferred state) + 6 unit tests.
- Task 10.9 COMPLETE: Trust Surface route (GET /trust-surface/{position}, overall_grade at top level) + scripts/run_backtest.py CLI (--position, --all, --model, --market-store) + 5 contract tests + 2 CLI unit tests.
- Task 10.10 COMPLETE: community CSV ingest script + 4 unit tests.
- PR #27 MERGED → main `91c91d1`: https://github.com/davidtleess/dynasty-genius/pull/27
- Next: generate operational backtest artifacts, then start Phase 12 planning/spec.
Spec at `docs/superpowers/specs/2026-05-14-phase10-11-backtest-harness.md`.

Research brief at `docs/strategies/Phase 10-11 Backtest Harness Research - Merged.md`.

Phase 8 COMPLETE (8.1 + 8.2 + 8.3): decision surfaces wired read-only over PVO. 339 tests.
Phase 9 COMPLETE (9.0 + 9.1 + 9.2 + 9.3): market overlay divergence engine + surface wiring. 376 tests.

- Phase 9.0 (Adapter Foundation): Fix fantasycalc_adapter.py URL params, rewrite field capture, MarketSource abstraction, 3-stage cache, test fixture.
- Phase 9.1 (Divergence Engine): compute_divergence(), percentile-rank formula, position-specific flags and caveats.
- Phase 9.2 (PVO Integration): wire into pvo_assembler and all three surfaces; contract tests.
- Phase 9.3 (Seasonal Signals + VAR): VAR from model scores, rookie_peak_value_window, market_recency_swing.

Phase 7 PVO alignment complete. Engine B v2 is fully wired into the Player Value Object pipeline.

- Stage 6.1 (v1.1 hygiene control): COMPLETE — artifact at `runs/v1_1_control/`
- Stage 6.2 (v2.0 stratified models): COMPLETE — QB/RB/WR promoted, TE not promoted
- Section 5 (Roster Auditor Hardening): COMPLETE — TE caveat propagation, governance-safe `age_value_context` overlay, market isolation; 309 tests
- Phase 7 PVO alignment: COMPLETE — Engine B scoring path, roster audit threading, `age_value_context` in `RosterAuditSignals`, `source_season` in PVO, 9 new contract tests; 318 tests total
- Production artifacts: `qb_v2.pkl`, `rb_v2.pkl`, `wr_v2.pkl` promoted; `engine_b_v1.pkl` fallback for TE

## Merged PRs (complete history)

- PR #13 (`hygiene/pydantic-compat`): MERGED → main `16e3567`.
- PR #14 (`hygiene/pydantic-v2-upgrade`): MERGED → main `f54ba11`.
- PR #15 (`hygiene/nflreadpy-migration`): MERGED → main `fa995624`.
- PR #17 (`engine-a/v2-enrichment-pipeline`): MERGED → main. QB CFBD adapter, ID map (95.2%), TDD tests, backtest gate (FAIL 0/3).
- PR #18 (`infra/adapter-test-gates`): MERGED. 4 adapter gates (RAS, manual export, FantasyCalc, leakage).
- PR #19 (`stage4/qb-professional-context`): MERGED. EPA/CPOE/DAKOTA context layer, QB identity bridge, qb_context_cards.
- PR #20 (`feature/qb-context-annotations`): MERGED. Display-only bust flags, mobility signal, P2S caveats.
- PR #21 (`docs/phase5-engine-b-plan`): MERGED. Phase 5 planning doc.
- PR #22 (`phase5/engine-b-contracts`): CLOSED, superseded by PR #23.
- PR #23 (`engine-b/service-integration`): MERGED → main `55f1351`. Engine B v1 dataset, training, service/API integration, roster auditor wiring, and governance decision record.
- PR #24 (`phase6/engine-b-v2`): MERGED → main `762e50c`. Engine B v2 position-stratified models (QB/RB/WR promoted, TE experimental), v2 manifest routing, per-position feature contracts, Stage 6.1 control, 4 Codex blockers resolved.
- PR #25 (`feature/phase9-market-overlay`): MERGED → main `c04d9bf`. FC adapter (numQbs=2 fix, 3-stage cache, banned-field sanitization), divergence engine (percentile-rank, 5 flags, position caveats), VAR computation, surface wiring (Roster Audit, Rookie Board, Trade Lab), 14 contract tests + 25 unit tests; 376 tests total.
- PR #27 (`feature/phase10-11-backtest-harness`): MERGED → main `91c91d1`. Walk-forward backtest harness, statistical metrics, market snapshot store/archive ingest, market NDCG comparison, promotion gates, Trust Surface route, and run_backtest CLI; 479 tests total.

## Open PRs / Branches

- Older open hygiene/governance PRs: PR #2, PR #3, PR #9 — do not close without David's instruction

## Engine B v1 Final State

- **Artifact**: `app/data/models/engine_b/runs/20260512T032635Z/engine_b_v1.pkl`
- **Features**: 19 (removed `target_share_nfl`, `air_yards_share` — r=0.95–0.98 collinear with WOPR)
- **Alpha**: 100.0 (stronger regularisation for collinear feature set)
- **Holdout**: 2022–2023 seasons (752 rows, 30% — more conservative than Q5 spec of 20%)
- **Gate**: PASS 3/3 — RMSE 3.346, R² 0.621, Spearman 0.775
- **TE**: `ENGINE_B_EXPERIMENTAL_POSITIONS = {"TE"}` — does not beat baseline, caveat enforced
- **Suite**: 261 passed, 11 skipped, 0 failed

## Engine B v2 Final State (Phase 6)

- **Run**: `app/data/models/engine_b/runs/20260513T012309Z/`
- **Manifest**: `app/data/models/engine_b/v2_manifest.json`
- **QB**: PROMOTED — `qb_v2.pkl` — RMSE 4.508, R² 0.439, Spearman 0.695, alpha=1000.0
- **RB**: PROMOTED — `rb_v2.pkl` — RMSE 3.582, R² 0.591, Spearman 0.783, alpha=500.0
- **WR**: PROMOTED — `wr_v2.pkl` — RMSE 2.887, R² 0.683, Spearman 0.809, alpha=200.0
- **TE**: NOT PROMOTED — `te_v2.pkl` fails gate (0/3) — alpha=1.0 — `ENGINE_B_EXPERIMENTAL_POSITIONS = {"TE"}` retained
- **v1.1 control**: `runs/v1_1_control/` — validation artifact only, not promoted
- **Suite**: 293 passed, 11 skipped, 0 failed

## Open Blockers

1. **TE model** — fails gate at both v1 and v2. alpha=1.0 suggests overfitting. Fundamental signal problem; defer to Phase 6 follow-on.
2. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds.
3. **Local Python mismatch** — use `.venv/bin/python3.14` for nflreadpy work.

## Codex PR #24 Blocking Issues — RESOLVED

1. **Issue 1 (v2_manifest.json tracked)** — FIXED: `git rm --cached`; `v2_manifest.json` added to `.gitignore`
2. **Issue 2 (TE fallback broken)** — FIXED: `_load_v1_bundle()` now searches for dirs containing `engine_b_v1.pkl`
3. **Issue 3 (missing-required check absent)** — FIXED: `validate_position_feature_contract()` now checks for missing required features; `_BASE_FEATURES` → `ENGINE_B_BASE_FEATURES` (public); 2 new tests added
4. **Issue 4 (v1.1 used RidgeCV not Ridge)** — FIXED: `train_v1_1_control()` now uses `Ridge(alpha=100.0)`; Stage 6.1 re-run; clean result logged above

## Phase 12 Spec

Spec APPROVED (David, 2026-05-15). Committed at `docs/superpowers/specs/2026-05-15-phase12-operational-artifacts.md`.
Research brief at `docs/strategies/Phase 12 Research Brief - Merged.md`.

- Task 12.0: Operational first run — `run_backtest.py --all` (QB/RB/WR; `ACTIVE_POSITIONS` excludes TE) + `run_backtest.py --position TE` separately; verify `backtest_result_{QB,RB,WR}.json` and `backtest_result_TE.json` exist before proceeding
- Task 12.1: ModelCard + CalibrationReport schemas + 7 contract tests ✓ COMPLETE
- Task 12.2: ECE + subgroup metric functions + 5 tests ✓ COMPLETE
- Task 12.3: Per-fold prediction log (CSV artifact) + 5 tests ✓ COMPLETE
- Task 12.4: Market-comparison ledger (JSON artifact) + 5 tests ✓ COMPLETE
- Task 12.5: Model card generation script + 6 tests ✓ COMPLETE
- Task 12.6: Trust Surface v2 — new `GET /trust-surface/{position}/model-card` endpoint + 8 tests ✓ COMPLETE
- Task 12.7: Divergence ledger v0 + build script + 5 tests ✓ COMPLETE
- Task 12.8: ARTIFACTS.md + AGENT_SYNC.md update + ledger entry (no tests) ✓ COMPLETE

**Governance**: `dynasty_value_score` stays `None`; TE remains EXPERIMENTAL; no production model artifact is retrained or replaced (harness in-fold Ridge refits are expected evaluation behavior); all artifacts immutable once written. Act 2 (DVS) is conditional — requires Act 1 artifact review and David's explicit spec approval.

Phase 12 implementation COMPLETE (Codex/Claude, 2026-05-15): operational-artifact pipeline, model-card schemas and generator, Trust Surface v2 model-card route, passive divergence ledger, and artifact index are in place. Latest verification reported by Task 12.7: 521 passed, 11 skipped. Artifact index: `docs/ARTIFACTS.md`.

Task 12.0 COMPLETE (Codex, 2026-05-15): first operational artifacts generated.
- QB: `app/data/backtest/runs/401e7e86-e34a-43d7-a72e-82f18466ab7a/backtest_result_QB.json` — ACTIVE_B
- RB: `app/data/backtest/runs/5fc06017-67cd-486d-80e2-90fd029d4314/backtest_result_RB.json` — ACTIVE_B
- WR: `app/data/backtest/runs/b3a338a3-ec42-4af8-a046-2ca0672e9390/backtest_result_WR.json` — ACTIVE_B
- TE: `app/data/backtest/runs/db90b0cf-04c8-44e2-9c80-b63da685342f/backtest_result_TE.json` — EXPERIMENTAL
- Market source: `unavailable` for all positions (expected; no archive store passed).
- TE precondition fix: `WalkForwardDriver.FIXED_ALPHA["TE"] = 1.0` added with regression test; no TE promotion logic changed.

## Next Recommended Work

1. **Phase 14 Planning** — DVS normalization and prospect-to-veteran bridge can be planned now that QB/RB/WR/TE are all `ACTIVE_B`.
2. **PFF parser follow-up** — if alternate route-alignment exports become available, add them to the ignored local manifest and regenerate the redacted report; raw export stays private/untracked.
3. **NOISE_BAND calibration** — Deferred to mid-July 2026. Do not change `NOISE_BAND=0.10` before then.
4. **Start daily FC snapshot cron operationally** — `scripts/snapshot_fantasycalc.py` exists; schedule daily run outside source control. Native snapshots needed for G4 by ~Q4 2026.
