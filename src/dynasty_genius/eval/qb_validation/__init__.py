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
"""
from __future__ import annotations

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
]
