# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-15

## Active Phase

Phase 10/11 — Backtest Harness (MERGED → main, PR #27 merge commit 91c91d1; 479 tests)

## Current Sprint Objective

Phase 9 Market Overlay: MERGED → main (PR #25 merge commit c04d9bf). 376 tests.
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

## Next Recommended Work

1. **Operational backtest artifacts** — run `.venv/bin/python3.14 scripts/run_backtest.py --all` to populate `app/data/backtest/runs/` for Trust Surface reads.
2. **Phase 12 planning/spec** — do not implement until a written spec is approved.
3. **Start daily FC snapshot cron operationally** — `scripts/snapshot_fantasycalc.py` exists; schedule daily run outside source control. Native snapshots needed for G4 by ~Q4 2026.
4. **NOISE_BAND calibration** — Deferred to mid-July 2026. Do not change `NOISE_BAND=0.10` before then.
5. **RB feature expansion research** — separate track; touches model inputs, requires backtest gate.
6. **TE diagnosis** — separate track; role heterogeneity + slot alignment adapter.
