# Dynasty Genius Agent Sync

Doctrine version: 1.0.0
Last updated: 2026-05-16

## Active Phase

Phase 13.3 — COMPLETE: TE Model Change + Promotion (merged 2026-05-16; 677 tests)
Phase 13 — SPEC APPROVED: Identity Audit + Engine A Draft-Capital Bake-Off + TE Remodel Step 0

## Current Sprint Objective

Phase 13.3 TE Model Change: MERGED → main. 677 tests.
- Task 13.3.4 COMPLETE: TE regularization bake-off artifact at `app/data/backtest/phase13/te_regularization_bakeoff_20260516.json`.
- Task 13.3 TE MODEL CHANGE COMPLETE: TE promoted to `ACTIVE_B`.
    - `te_role_is_risk_profile` feature added (binary penalty for blocking specialists/role risk).
    - Ridge alpha increased to 100.0.
    - Retrained `te_v3.pkl` passed G1 (0.48 mean tau) and G2 (12.3% dev) walk-forward gates.
    - Manifest updated to point to `te_v3.pkl`.
    - TE removed from `ENGINE_B_EXPERIMENTAL_POSITIONS`.
    - Promotion decision note: `docs/validation/phase13-3-te-promotion-decision.md`.

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
    - Canonical DG player_ids assigned for all 116 TEs via `scripts/backfill_te_canonical_ids.py`; `pff_te_eligible_te_2018_2025_20260516_canonical.json` has 0 null player_ids.
- Task 13.3 PFF EXPORT REPORT: COMPLETE — `scripts/build_pff_te_export_report.py` + strict parser `src/dynasty_genius/adapters/pff_te_export.py`; redacted report at `app/data/identity/pff_te_export_schema_report_20260516.json`.
- Task 13.3.1 COMPLETE: TE Archetype Rubric Step 0 artifact generated at `app/data/identity/te_archetype_rubric_20260516.json`.
    - Sensitivity result: 14 players move from receiving_leaning to ambiguous when detached threshold changes from 0.40 to 0.45.
- Task 13.3.2 COMPLETE: TE Archetype Feature Bake-Off validation artifact at `app/data/backtest/phase13/te_archetype_bakeoff_20260516.json`.
    - Result: `role_risk_detector` is the only candidate that passes the conservative acceptance rule.
- Task 13.3.3 COMPLETE: TE role-risk controlled experiment artifact at `app/data/backtest/phase13/te_role_risk_experiment_20260516.json`.
    - Sensitivity alpha 100.0: `unified_penalty` passes all gates.

...

## Next Recommended Work

1. **Phase 14 Planning** — With TE promoted to ACTIVE_B, the next step is DVS (Dynasty Value Score) normalization and prospect-to-veteran bridging.
2. **NOISE_BAND calibration** — Deferred to mid-July 2026. Do not change `NOISE_BAND=0.10` before then.
3. **Start daily FC snapshot cron operationally** — `scripts/snapshot_fantasycalc.py` exists; schedule daily run outside source control.
