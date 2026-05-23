# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-22

## Active Phase

Phase 12.5 — COMPLETE: Market-leakage guard + QB Backup caveat + pre-commit hooks (merged 2026-05-15; 530 tests)
Phase 13 — SPEC APPROVED: Identity Audit + Engine A Draft-Capital Bake-Off + TE Remodel Step 0
Phase 13.3 — COMPLETE: TE Model Change + Promotion (2026-05-16; 683 tests)
Phase 14 — COMPLETE: DVS Normalization + Bridge + VAR Activation (2026-05-16; 694 tests)
Phase 15 — IMPLEMENTATION COMPLETE: xVAR Cross-Positional Valuation + Bayesian Dead Window Blend + Trade Lab v0 (711 tests; 11 skipped)
Phase 15.1 — COMPLETE: 2026 Rookie Rank Refresh — prospect_cards enriched with Phase 15 xVAR + rank fields; rank movement report at docs/validation/phase15-2026-rookie-rank-refresh.md (2026-05-17; 730 tests)
Phase 15.2 — COMPLETE: Draft-status banner — refresh_draft_state.py fetches GET /draft/{id} in parallel with picks; draft_status, last_picked, total_picks, current_pick_no written to draft_state.js; color-coded strip on board (2026-05-17)
Phase 15.3 — COMPLETE: Available-now panel — top 3 non-taken xVAR-ranked picks above card list; tab-aware; TE caveat fires; board fully live-ready for 2026 rookie draft (2026-05-17)
Phase 15.4 — COMPLETE: Post-draft closeout — Sleeper draft complete, 36/36 picks written to `resources/draft_state.js`, Black pick #26 validated, roster audit rerun with Black present (2026-05-21)
Phase 16.1 — COMPLETE: Age blockers resolved — 6 verified DOBs ingested, all 80 2026 prospects now scored, DVS invariance held, full suite green (737 passed, 11 skipped; 2026-05-21)
Phase 16 — CLOSED FOR PHASE 17 ENTRY: Remaining signal-upgrade workstreams are validation/research gates and deferred; no production model change approved.
Phase 17 — IMPLEMENTATION COMPLETE THROUGH 17.5: Sleeper universe, full PVO batch, team matrix, market divergence, and league opportunity map artifacts complete (latest artifacts in `app/data/league_snapshots/` and `app/data/valuation/`)
Phase 18 — IMPLEMENTATION STARTED: 18.1 roster-audit rookie PVO reconciliation complete; 18.2 daily batch orchestration complete; 18.3 team posture classification complete; Gemini PM skill `dynasty-genius-pm` installed (2026-05-18)

## Current Sprint Objective

Phase 18 — 18.3 TEAM POSTURE CLASSIFICATION COMPLETE; READY FOR REVIEW / CHECKPOINT.
- Workstream 18.1 (Roster Audit Rookie Reconciliation) — COMPLETE: `/roster/audit` preserves Phase 17 full-universe Engine A PVO values for rostered current-draft rookies instead of degrading them to active-player `PRE_MODEL`; veterans remain on the existing audit path.
- Workstream 18.2 (Daily Batch Orchestration) — COMPLETE: `scripts/refresh_league_intelligence.py` runs the existing Phase 17.1 → 17.5 builders in order, supports `--dry-run`, and fails fast without adding new valuation logic.
- Workstream 18.3 (Team Posture Classification) — COMPLETE: `scripts/build_team_posture.py` builds `team_posture_latest.json` from internal team-matrix signals; opportunity partner rankings now consume posture and populate `posture_alignment_score` when the posture artifact is present.
- Latest live Woodbury rerun: 28 players, 5 QB context cards, `decision_supported=false`; current-draft rookies now surface Engine A values in `/roster/audit`: Fernando Mendoza (`DVS=85.14`, `xVAR=10.31`), Omar Cooper Jr. (`DVS=70.99`, `xVAR=1.79`), Chris Bell (`DVS=62.46`, `xVAR=-6.74`), Kaelon Black (`DVS=61.55`, `xVAR=13.4`).
- Phase 18.1 verification: roster audit/PVO focused suite passed (`35 passed`); full suite passed (`768 passed, 11 skipped`).
- Phase 18.2 verification: orchestration/Phase 17 focused suite passed (`23 passed`); dry-run CLI verified planned commands without external network or artifact writes.
- Phase 18.3 verification: posture/opportunity/refresh focused suite passed (`16 passed`); full suite passed (`777 passed, 11 skipped`). Latest posture coverage: 12/12 teams classified, `decision_supported_true_count=0`, `market_fields_absent=true`; Woodbury Riders currently labels `REBUILDING` under the v1 heuristic.

Phase 17 — 17.1 THROUGH 17.5 COMPLETE; REVIEWED / CHECKPOINTED.
- Workstream 17.0 (Planning) — COMPLETE: Merged research brief finalized with Section 19 Decision Memo.
- Workstream 17.1 (Universe Snapshot & Coverage) — COMPLETE: `scripts/build_sleeper_universe_snapshot.py` fetches Sleeper league, rosters, users, traded picks, latest draft, NFL state, and `/players/nfl`; writes `sleeper_universe_snapshot_latest.json` and `sleeper_universe_coverage_latest.json`.
- Workstream 17.2 (Full PVO Batch) — COMPLETE: `scripts/build_universe_pvo_batch.py` builds `universe_pvo_latest.json` from the 17.1 snapshot, `resources/prospect_cards.json`, Engine B inference scoring, and the governed ff_playerids crosswalk.
- Workstream 17.3 (Team Value Matrix) — COMPLETE: `scripts/build_team_value_matrix.py` builds `team_value_matrix_latest.json` from the 17.2 PVO artifact and 17.1 Sleeper snapshot.
- Workstream 17.4 (Market Divergence v2) — COMPLETE: `scripts/build_universe_market_divergence.py` builds `universe_market_divergence_latest.json` from the 17.2 full-universe PVO artifact plus FantasyCalc overlay data.
- Workstream 17.5 (League Opportunity Map) — COMPLETE: `scripts/build_league_opportunity_map.py` builds `league_opportunity_latest.json` and `league_opportunity_latest.md` from 17.3 team matrix plus 17.4 market divergence.
- Approved Defaults: Automated-only pick reconstruction with validation/caveat gates; Global Noise band 0.10 as diagnostic/provisional; FantasyCalc ppr=1/no TEP.
- Bench-weighting guardrail: no player-level value decay. Any depth weighting may apply only to team-strength aggregation after computing the best legal starting lineup from player xVAR/PVO values; actual manager lineup choices must not determine who is decayed.
- Latest 17.1 coverage: 12,189 Sleeper universe rows classified; 280/280 rostered players present; David roster 28/28 present; 1 unresolved Sleeper pseudo-player ID (`0`); PVO scoring not required in 17.1.
- Latest 17.2 coverage (`phase17-2-20260522T030627Z`): 12,189 rows; route counts `ENGINE_A=80`, `ENGINE_B=373`, `PRE_MODEL=9,605`, `INACTIVE=2,130`, `UNRESOLVED_IDENTITY=1`; no market overlay rows; `decision_supported_true_count=0`; all rostered skill players have explicit routes. `xvar_percentile_overall` remains null until cross-position percentile ranking is explicitly implemented.
- Latest 17.3 coverage (`phase17-3-20260522T110534Z`): all 12 teams emitted; future picks present but unvalued; taxi activation cost represented; guardrail embedded (`player_level_value_decay_allowed=false`, lineup selection from raw player xVAR, depth weighting only for non-starters after lineup selection).
- Latest 17.4 coverage (`phase17-4-20260522T115250Z`): 12,189 rows; 398 FantasyCalc market overlays; signals `MODEL_HIGH_MARKET_LOW=107`, `MODEL_LOW_MARKET_HIGH=56`, `INSIDE_BAND=107`, `UNAVAILABLE=11,918`, `UNRESOLVED_IDENTITY=1`; `decision_supported_true_count=0`; market data remains overlay-only; no imperative schema language; TE position-only suppression count is 0.
- Latest 17.5 coverage (`phase17-5-20260522T121830Z`): 20 opportunity cards capped for the run; card types `WAIVER_CANDIDATE=16`, `ROSTER_SURPLUS_DEFICIT_MATCH=3`, `DIVERGENCE_MODEL_HIGH=1`; 11 partner rankings; all cards evidence-backed; `decision_supported_true_count=0`; automated trade execution disabled; banned language absent.
- Current caveat: Automated pick reconstruction defers numeric values and publishes caveats for 2026 traded picks outside the future-pick reconstruction window after draft closeout.

Phase 15 — COMPLETE. Suite: 730 passed, 11 skipped, 0 failed. Board is live-ready.
- Workstream 15.1 (xVAR) — COMPLETE: xVAR, xvar_lambda, xvar_anchor, xvar_ceiling_bound, dvs_pct, dvs_pct_as_of, dvs_blend_weight_b fields in PVO; xVAR assembled in pvo_assembler for Engine A, Engine B, and blend paths.
- Workstream 15.2 (Bayesian Blend) — COMPLETE FOR V0: dvs_engine="blend" when both Engine A and B inputs present; w_B = n / (n + k_pos) shrinkage; Dead Window caveat appended. Blend-k defaults approved for Phase 15 V0 in `docs/validation/phase15-blend-k-validation.md`; residual-variance fitting remains a follow-up before changing k_pos.
- Task 2 COMPLETE: Trade Lab evaluator (`src/dynasty_genius/trade_lab/`) — xVAR-sum parity, sub-replacement exclusion, consolidation penalty, draft-pick valuation through Engine A.
- Task 3 COMPLETE: `POST /api/trade/evaluate` route added while preserving existing `/api/trade/analyze`.
- Task 4 COMPLETE: `dvs_pct` batch (`scripts/compute_dvs_pct_batch.py`) computes within-position percentiles against ACTIVE_B population only.
- Task 5 COMPLETE: xVAR/blend contract tests (`tests/contract/test_phase15_xvar.py`, `tests/contract/test_phase15_blend.py`) plus Trade Lab and dvs_pct contract tests.
- Task 6 COMPLETE: ledger/AGENT_SYNC cleanup.

Phase 14 DVS Normalization: COMPLETE. 694 tests.
- Task 14.1 COMPLETE: Constants injected and identity gate passed.
- Task 14.2 COMPLETE: DVS formula, Dead Window bridge, and provenance fields implemented.
- Task 14.3 COMPLETE: VAR batch calculation and calibration audit finished.
- Artifacts: `var_batch_20260516_190328.json`, `dvs_calibration_audit_20260516_190356.json`.


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
4. **TE divergence review period**: Phase 17.4 removed the position-only TE suppression. TE rows now route through normal gates with `te_review_period` metadata; do not convert TE divergence into decision-supported opportunity language until later validation confirms reliability.

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

## Phase 16 — CLOSED FOR PHASE 17 ENTRY

**Theme:** Engine A Rookie Signal Upgrade.

**Spec input:** `docs/strategies/Phase 16 Rookie Signal Upgrade Research - Merged.md` (FINAL — Compass spine, Dynasty Rookie supporting, Codex synthesis reviewed; updated 2026-05-17 with fold-consistency gate, RYPTPA-primary WR framing, RB age de-emphasis governance elevation).

**Phase 16.1 implementation:** COMPLETE (2026-05-21). Six PRE_MODEL age blockers now have verified DOBs and all 80 2026 prospects are scored. Validation note: `docs/validation/phase16-closeout-2026-05-21.md`; refreshed rank report: `docs/validation/phase15-2026-rookie-rank-refresh.md`.

**Sub-phase sequencing (David, 2026-05-17):**
- **Phase 16.1**: COMPLETE — age blockers only; no model semantics change.
- **Phase 16.2**: DEFERRED — validation harness / bake-off infrastructure (CFBD client wrapper, identity join pipeline, immutable snapshot tooling).
- **Phase 16.3**: DEFERRED — WR feature candidates; RYPTPA first, YPRR conditional on governed route data.
- **Phase 16.4**: DEFERRED — draft-capital transform bake-off. Promotion gate remains ≥3% aggregate MAE lift AND ≥3 of 4 LOOCV folds passing AND TE MAE not regressing >1%.
- **Phase 16.5**: DEFERRED — RB age de-emphasis governance decision before any RB feature bake-off.

**Key governance locks for all of Phase 16:**
- Market data overlay-only; xVAR display/decision only; no production model change without passing bake-off artifact.
- Every promotion requires fold-consistency (≥3 of 4 LOOCV folds) AND aggregate MAE gate.
- All six age-data blockers remain PRE_MODEL until Tier-1 source audit confirms each birth date.

**Prerequisites still pending:**
- **CLEARED — Post-draft closeout (2026-05-21):** `refresh_draft_state.py` confirmed `draft_status == "complete"` and `current_pick_no == total_picks == 36`; `resources/draft_state.js` refreshed; validation note written at `docs/validation/post-draft-closeout-2026-05-21.md`.
- Roster audit with Black on Sleeper roster: COMPLETE — `GET /api/roster/audit` returned HTTP 200 with Kaelon Black (`13414`) present; `decision_supported` remains false.
- **CLEARED — Age blockers (2026-05-21):** all six formerly PRE_MODEL 2026 rookies now have verified DOBs; `resources/prospect_cards.json` has 80 scored and 0 PRE_MODEL.

## Phase 17 — RESEARCH BRIEF READY

**Theme:** Sleeper Universe Valuation & League Opportunity Map.

**Spec input:** `docs/strategies/Phase 17 Sleeper Universe Valuation Research - Merged.md` (Codex merge of Phase 17 research reports with Claude/Gemini review feedback incorporated).

**Recommended gated sub-phases:**
- **17.1 Universe Snapshot & Coverage** — Sleeper player universe, league rosters, users, traded picks, draft state, source hashes, identity coverage, and top-300 unresolved gate.
- **17.2 Full PVO Batch** — full-universe PVO artifact with explicit engine routing (`ENGINE_A`, `ENGINE_B`, `BLEND_AB`, `PRE_MODEL`, `MARKET_ONLY`, `INACTIVE`, `UNRESOLVED_IDENTITY`, `CONTEXT_ONLY`).
- **17.3 Team Value Matrix** — starter-weighted xVAR, capped xVAR, positional surplus/deficit, taxi/IR handling, and future-pick ownership context with numeric pick values deferred.
- **17.4 Market Divergence v2** — FantasyCalc overlay only; percentile divergence; `signal_status` gates; stale TE hardcode cleanup with temporary `TE_REVIEW=true`; no NOISE_BAND tuning before mid-July.
- **17.5 League Opportunity Map** — neutral evidence cards and partner fit; `decision_supported=false` throughout Phase 17.

**Key governance locks for Phase 17:**
- Sleeper `player_id` is the Phase 17 universe key, but DG canonical identity remains the long-term mapping layer.
- Market data is overlay-only and never enters Engine A/B feature inputs.
- Future picks are reconstructed for ownership, but no numeric xVAR/DVS/market value is assigned in Phase 17.
- Opportunity language must stay neutral: no imperative buy/sell/target/fade labels.
- Divergence gates populate `signal_status`; they do not flip `decision_supported`.
- Top-300 identity gate: top-300 by FantasyCalc dynasty Superflex market value when available, falling back to DG xVAR when market data is unavailable.
- FantasyCalc parameter set **CONFIRMED**: `isDynasty=true&numQbs=2&numTeams=12&ppr=1`. Verified from `resources/david_league_context.json` (`te_premium: 0.0`). Sleeper league-settings check remains a Phase 17.1 validation dependency.

**Phase 17 Structural Defaults — David ruling (2026-05-21):**
- Bench/depth weighting: do not decay player value. Build best possible legal starting lineup first; apply any depth weighting only to non-starters in team-strength aggregation. Actual manager lineup choices must not drive decay. Coefficient can start at `0.5` only under that guardrail.
- Pick reconstruction: automated Sleeper delta only; trust but verify with validation/caveat gates. No manual override in v1.
- Divergence noise band: `0.10` global as diagnostic/provisional; revisit after first full-universe flag distribution.
- FantasyCalc params: confirmed `isDynasty=true&numQbs=2&numTeams=12&ppr=1`; no TEP.

---

## Phase 15 — COMPLETE

Phase 15 spec/plan: `docs/superpowers/plans/2026-05-16-phase15-trade-lab.md`.

**Architecture decisions locked:**
- xVAR formula: `(DVS - replacement_DVS) × Λ_pos` — WR-equivalent points above replacement.
- Engine A Λ applies when `dvs_engine in ("A", "blend")`. Engine B Λ only for `dvs_engine == "B"`.
- `XVAR_LAMBDA_ENGINE_B`: QB=1.386, RB=1.083, WR=1.000, TE=0.648 (P90-ratio derived).
- `XVAR_LAMBDA_ENGINE_A`: QB=1.315, RB=1.150, WR=1.000, TE=0.717.
- `ENGINE_B_REPLACEMENT_DVS`: QB=64.2, RB=46.4, WR=60.6, TE=95.6.
- `ENGINE_A_REPLACEMENT_DVS`: QB=77.3, RB=49.9, WR=69.2, TE=98.8.
- Bayesian blend: `w_B = n / (n + k_pos)`. `DVS_BLEND_K`: QB=6, RB=5, WR=5, TE=7. Fires only when both Engine A and B inputs present; produces `dvs_engine = "blend"`. Single-engine fallback produces `dvs_engine = "A"`.
- `TRADE_PARITY_BAND = 0.10` — governs trade math. `NOISE_BAND = 0.10` — governs veteran divergence flag suppression. **Never aliased.**
- `dvs_pct`: 0–100 within-position percentile vs Engine B active population. Populated by batch script.
- `decision_supported = False` on all surfaces, always.

**Workstream 15.1 — xVAR Cross-Positional Valuation (STRUCTURAL COMPLETE)**
- PVO fields added: `xvar`, `xvar_lambda`, `xvar_anchor`, `xvar_ceiling_bound`, `dvs_pct`, `dvs_pct_as_of`, `dvs_blend_weight_b`.
- xVAR assembled in pvo_assembler.py inside `if engine_b_resolved:` block.
- Known gap: `xvar_ceiling_bound` not yet populated for pure Engine A (prospect) paths — fix is Task 5.
- 3 passing contract tests in `tests/contract/test_phase15_valuation.py` (xvar_rank_preservation, xvar_scarcity_multiplier, bayesian_bridge_monotonicity).

**Workstream 15.2 — Bayesian Dead Window Blend (STRUCTURAL COMPLETE)**
- `dvs_engine = "blend"` when games_t < ENGINE_B_MIN_GAMES_T (8) and both Engine A and B inputs present.
- Dead Window caveat appended to blend output.
- blend-k defaults (QB=6, RB=5, WR=5, TE=7) in place but not yet validated against per-position residual variance.
- **Gate: `docs/validation/phase15-blend-k-validation.md` stub required — PENDING David review (Task 1).**

**Suite state (post-cleanup):** 690 passed, 11 skipped, 0 failed.
- Note: 4 fewer than Phase 14 peak (694) due to deletion of Gemini's broken `tests/test_trade_lab.py` artifact.
- 2 pre-existing nflreadpy collection errors excluded via `--ignore` (not regressions).

## Phase 14 — IN PLANNING

Phase 14 spec APPROVED by David: `docs/superpowers/specs/2026-05-16-phase14-dvs-normalization.md`.
Execution roadmap: `docs/strategies/Dynasty Genius Phase 14 Execution Roadmap.md`.

**Architecture decisions locked:**
- DVS normalization: Option C (Engine B P90 constants — QB 20.1, RB 15.7, WR 14.5, TE 9.4).
- Scale: 0–100 float, one decimal place. 0–1000 deferred to Phase 15.
- Bridge: Option B — explicit caveat, no Bayesian blending. `ENGINE_B_MIN_GAMES_T = 8`.
- VAR: within-position only in Phase 14. Cross-position is Phase 15.
- NOISE_BAND: veteran divergence flags stay dark until mid-July 2026.
- TE caveat: "TE market superiority gate deferred — projection-quality score only" (NOT experimental fallback).

**Subphase 14.1 — Constants and Identity Gate (COMPLETE)**
1. Added `ENGINE_B_P90_PPG`, `ENGINE_B_VAR_THRESHOLDS`, `ENGINE_B_MIN_GAMES_T` to `engine_b_contract.py`.
2. Ran 2024–2025 identity reconciliation report → `docs/validation/phase14-identity-reconciliation-2024-2025.md`. **Hard gate PASSED.**
3. Wrote 11 failing tests (spec sections 5.1–5.11).

**Subphase 14.2 — DVS Assembly and Bridge (COMPLETE)**
- Added `dvs_engine`, `dvs_p90_ref`, `dvs_clamped` to `PlayerValueObject`.
- Removed blocking comment at `pvo_assembler.py` line 316.
- Implemented Engine B DVS formula (clamped 0-100 float), Dead Window bridge (Year 1-3 vet fallback to Engine A), and TE G3-deferred caveat.
- All 11 contract tests (5.1-5.11) implemented and passing.
- Regression fixed: non-prospects with draft capital no longer promoted to PROSPECT_C model grade.

**Subphase 14.3 — VAR and Calibration Audit (COMPLETE)**
- Implemented `scripts/compute_var_batch.py`. Generated `app/data/backtest/phase14/var_batch_20260516_190328.json`.
- Implemented `scripts/audit_dvs_calibration.py`. Generated `app/data/backtest/phase14/dvs_calibration_audit_20260516_190356.json`.
- Replacement baselines established (QB25: 13.47, RB33: 8.59, WR53: 8.65, TE13: 9.76 PPG).
- Calibration audit confirms DVS magnitude validity (WR ECE: 0.046).

## Open Blockers

1. **NOISE_BAND calibration** — Locked at 0.10 until mid-July 2026. Do not tune the divergence band before then.
2. **TE divergence review period** — Phase 17.4 removed position-only suppression, but no exit criteria are defined yet; TE divergence must remain non-decision-supported.
3. **Phase 16.2-16.5 deferred gates** — Validation harness, WR/RB/QB feature candidates, draft-capital bake-off, and RB age de-emphasis remain explicitly deferred until David reopens them.

## Next Recommended Work

1. **Phase 18.4 cross-position xVAR percentile pass** — Populate `xvar_percentile_overall` in the universe PVO batch with a post-scoring ranking pass. This must remain derived from internal xVAR only; no market data enters valuation.
2. **Housekeeping: publish checkpoint** — Branch is well ahead of `origin/main`; decide whether to push and open a PR before starting more Phase 18 implementation.
