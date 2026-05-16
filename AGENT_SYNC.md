# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-15

## Active Phase

Phase 12.5 — COMPLETE: Market-leakage guard + QB Backup caveat + pre-commit hooks (merged 2026-05-15; 530 tests)
Phase 13 — SPEC APPROVED: Identity Audit + Engine A Draft-Capital Bake-Off + TE Remodel Step 0

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
    - BLOCKER: Actual real CSV schema/sample still needed.
- Task 13.3.1 BLOCKED: TE Archetype Rubric waits for real PFF CSV sample/schema and passing 2018-2025 drafted TE identity coverage artifact.
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

1. **Acquire/lock PFF collegiate TE CSV sample schema** — synthetic/redacted fixture ready in checklist; raw export stays private/untracked.
2. **Run 2018-2025 drafted TE identity coverage artifact** — must pass >=98% resolved before Task 13.3.1.
3. **Resolve TE identity CLI gaps before execution** — wire existing snapshot generator, add composite/prospect registry flags, failure report, and PFF eligibility manifest.
4. **Task 13.3.1 TE Archetype Rubric** — blocked until both PFF sample/schema and identity gate are done.
5. **NOISE_BAND calibration** — Deferred to mid-July 2026. Do not change `NOISE_BAND=0.10` before then.
6. **Start daily FC snapshot cron operationally** — `scripts/snapshot_fantasycalc.py` exists; schedule daily run outside source control. Native snapshots needed for G4 by ~Q4 2026.
