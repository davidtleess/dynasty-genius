# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-12

## Active Phase

Phase 6 — Engine B v2 (MERGED — post-merge hardening in progress)

## Current Sprint Objective

Phase 6 core implementation merged to main (`762e50c`). Section 5 (Roster Auditor hardening) is the active work item — unblocked for Gemini.

- Stage 6.1 (v1.1 hygiene control): COMPLETE — artifact at `runs/v1_1_control/` — Ridge(alpha=100.0) fixed after Codex review (was RidgeCV); clean result: RMSE 3.397 / R² 0.609 / Spearman 0.767, 3/3 informational PASS
- Stage 6.2 (v2.0 stratified models): COMPLETE — QB/RB/WR promoted, TE not promoted
- Active branch: `phase6/engine-b-v2` — open PR, 4 Codex blocking issues resolved
- Design spec: `docs/superpowers/plans/2026-05-12-engine-b-v2-stratification.md`

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

1. **Roster Auditor hardening (Section 5)** — UNBLOCKED. Gemini to wire Engine B v2 predictions into roster auditor output, verify TE caveat propagates, confirm market overlay remains separated. Must run with `.venv/bin/python3.14` (artifacts pickled with 3.14; standard `.venv/bin/python` cannot unpickle).
2. **Untracked model run disposal** — David to decide on `runs/20260512T025445Z/` and `runs/20260512T032005Z/` (archive or delete)
3. **RB follow-on (Phase 6.1)** — evaluate `red_zone_touches` and `targets_per_game` as RB-specific features once stratified baseline is established
4. **TE diagnosis** — investigate alpha=1.0 overfitting; evaluate training sample quality before adding features
5. **Untracked model run disposal** — David to decide on `runs/20260512T025445Z/` and `runs/20260512T032005Z/` (archive or delete)

## QB Strategy (unchanged)

- CFBD Tier 3 via httpx — registered in contract, NOT promoted to model_input (backtest FAIL 0/3)
- Bifurcated aging curve: pocket passer cliff 33, dual-threat cliff 29 (display warnings only)
- `is_dual_threat = True` if rushing yards > 400/season in any T-2 to T
