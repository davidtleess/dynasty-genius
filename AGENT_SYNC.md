# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-12

## Active Phase

Phase 6 — Engine B v2 (implementation in progress)

## Current Sprint Objective

Phase 6 implementation complete. PR open on `phase6/engine-b-v2` pending Codex review and merge.

- Stage 6.1 (v1.1 hygiene control): COMPLETE — validation artifact at `runs/v1_1_control/`
- Stage 6.2 (v2.0 stratified models): COMPLETE — QB/RB/WR promoted, TE not promoted
- Active branch: `phase6/engine-b-v2` — open PR, awaiting Codex review
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

## Open PRs / Branches

- `phase6/engine-b-v2`: Phase 6 Engine B v2 — open PR, pending Codex review
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
- **Suite**: 291 passed, 11 skipped, 0 failed

## Open Blockers

1. **TE model** — fails gate at both v1 and v2. alpha=1.0 suggests overfitting. Fundamental signal problem; defer to Phase 6 follow-on.
2. **PP below 80% gate** — target_share 69.6%, breakout_age WR/TE 72.8%. Path B holds.
3. **Local Python mismatch** — use `.venv/bin/python3.14` for nflreadpy work.

## Next Recommended Work

1. **Merge `phase6/engine-b-v2` PR** after Codex review
2. **Roster Auditor hardening (Section 5)** — Gemini to verify v2 predictions surface correctly, TE caveat propagates, market overlay remains separated (post-merge)
3. **Untracked model run disposal** — David to decide on `runs/20260512T025445Z/` and `runs/20260512T032005Z/` (archive or delete)
4. **RB follow-on (Phase 6.1)** — evaluate `red_zone_touches` and `targets_per_game` as RB-specific features once stratified baseline is established
5. **TE diagnosis** — investigate alpha=1.0 overfitting; evaluate training sample quality before adding features

## QB Strategy (unchanged)

- CFBD Tier 3 via httpx — registered in contract, NOT promoted to model_input (backtest FAIL 0/3)
- Bifurcated aging curve: pocket passer cliff 33, dual-threat cliff 29 (display warnings only)
- `is_dual_threat = True` if rushing yards > 400/season in any T-2 to T
