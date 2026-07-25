"""QB-1 validation study package (spec v8, SHA 8fa244c1…, byte-frozen).

Research-only: reports and artifacts, no product surface, no model promotion,
no served-API change. Consumer boundary (F33): ONLY code inside this package
may read ``validation_study``-role data; Engine A/B and served surfaces are
walled off.

GREEN discipline: a seam is exported here ONLY when its real behavior exists —
unimplemented spec rows deliberately stay absent so their RED rows stay red.
Slice 1 (2026-07-16): registration hash gate, output-path guard, No-Verdict
scan, dataset/manifest shape guards.
Slice 2 (2026-07-17): reviewer-contract signature reconciliation (F14/F15/F24),
the seven-dataset source gate (F1, v9), identity-overlap and as-of guards (F17/F19),
report output validation (F26), the model-lane status decision (F30 — the H5
lane refuses with a named reason until its behavioral RED lands), and the
draft-join closure (F34); D1 ``validation_*`` ingestion + the
``nflreadpy_qb_validation`` registry entry land in the adapter/registry.
Slice 3 (2026-07-18): the D2 Sleeper-scored PPG label table
(F11 ``validate_label_table``, F21 ``validate_scoring_edges``,
F28 ``validate_attrition_classes``) — settings-derived Decimal scoring with
the hash assertion, the pinned qualifying-game predicate, and the exhaustive
outcome-class law.
Slice D3-a (2026-07-23): the expanding-fold construction and train-safe
preparation guards in ``folds.py`` (F4 ``run_expanding_folds``,
F12 ``validate_age_features``, F20 ``validate_degenerate_inputs``,
F22 ``fit_train_only_imputer``, F27 ``validate_hypothesis_partition``) — the
leakage-proof layer that runs before any estimator (F5) or scoring (F6).
Slice D3-b (2026-07-23): the single-fold, single-ridge-lane estimator in
``ridge_lane.py`` (F5 ``fit_ridge_lane``) — the H1-H4 train-fitted
imputer→scaler→RidgeCV(LOO/GCV) pipeline, per-lane, train-only, no test-fold
leakage; naive-carryforward and comparison scoring remain D3-c.
Slice D3-c (2026-07-24): the per-fold comparison-scoring layer in
``comparisons.py`` (``build_naive_lane`` helper, F6 ``score_comparisons``,
F8 ``build_primary_comparisons``, + the drivable ``validate_contrast_set``
guard) — exact-key common-pool paired deltas with player-keyed
``paired_evidence``, contrast-lane-aware secondaries, and the two-level fold
topology. Per-fold ONLY: pooling/bootstrap/permutation/BH-FDR remain D3-d;
H5 materialization/join remain D4; H2 rushing production remains UNDER TEST.
"""
from __future__ import annotations

from src.dynasty_genius.eval.qb_validation.comparisons import (
    build_naive_lane,
    build_primary_comparisons,
    score_comparisons,
    validate_contrast_set,
)
from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
from src.dynasty_genius.eval.qb_validation.folds import (
    fit_train_only_imputer,
    run_expanding_folds,
    validate_age_features,
    validate_degenerate_inputs,
    validate_hypothesis_partition,
)
from src.dynasty_genius.eval.qb_validation.guards import (
    OUTPUT_ROOT,
    scan_banned_language,
    validate_as_of_dates,
    validate_dataset_shape,
    validate_manifest_columns,
    validate_output_path,
    validate_report_output,
)
from src.dynasty_genius.eval.qb_validation.identity import (
    normalize_name,
    resolve_draft_join,
    validate_identity_overlap,
)
from src.dynasty_genius.eval.qb_validation.inference import (
    bca_interval,
    benjamini_hochberg,
    build_cluster_universe,
    cluster_bootstrap_distribution,
    cluster_permutation_p,
    pool_paired_deltas,
    run_primary_inference,
    shifted_null_ni_p,
)
from src.dynasty_genius.eval.qb_validation.qb_ppg_labels import (
    ATTRITION_CLASSES,
    OUTCOME_CLASSES,
    SCORING_COMPONENTS,
    build_label_table,
    score_stat_line,
    settings_hash,
    validate_attrition_classes,
    validate_label_table,
    validate_scoring_edges,
)
from src.dynasty_genius.eval.qb_validation.registration import (
    build_registration,
    reject_registration_drift,
    require_registration_hash,
)
from src.dynasty_genius.eval.qb_validation.ridge_lane import (
    fit_ridge_lane,
)
from src.dynasty_genius.eval.qb_validation.sources import (
    VALIDATION_DATASETS,
    load_validation_sources,
)
from src.dynasty_genius.eval.qb_validation.status import (
    evaluate_power_and_status,
)
from src.dynasty_genius.eval.qb_validation.study_matrix import (
    build_study_matrix,
)

__all__ = [
    "QBValidationFailure",
    "OUTPUT_ROOT",
    "VALIDATION_DATASETS",
    "ATTRITION_CLASSES",
    "OUTCOME_CLASSES",
    "SCORING_COMPONENTS",
    "build_label_table",
    "build_study_matrix",
    "run_expanding_folds",
    "validate_age_features",
    "validate_degenerate_inputs",
    "fit_train_only_imputer",
    "validate_hypothesis_partition",
    "fit_ridge_lane",
    "build_naive_lane",
    "score_comparisons",
    "build_primary_comparisons",
    "validate_contrast_set",
    "score_stat_line",
    "settings_hash",
    "validate_label_table",
    "validate_scoring_edges",
    "validate_attrition_classes",
    "build_registration",
    "require_registration_hash",
    "reject_registration_drift",
    "load_validation_sources",
    "normalize_name",
    "resolve_draft_join",
    "validate_identity_overlap",
    "validate_as_of_dates",
    "validate_output_path",
    "scan_banned_language",
    "validate_dataset_shape",
    "validate_manifest_columns",
    "validate_report_output",
    "evaluate_power_and_status",
    # D3-d — the inference increment (pooling, cluster bootstrap BCa,
    # shifted-null NI, cluster permutation, BH-FDR). Emits no support_status.
    "pool_paired_deltas",
    "build_cluster_universe",
    "cluster_bootstrap_distribution",
    "bca_interval",
    "cluster_permutation_p",
    "shifted_null_ni_p",
    "benjamini_hochberg",
    "run_primary_inference",
]
