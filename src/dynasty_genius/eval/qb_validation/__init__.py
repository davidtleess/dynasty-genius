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
the six-dataset source gate (F1), identity-overlap and as-of guards (F17/F19),
report output validation (F26), the model-lane status decision (F30 — the H5
lane refuses with a named reason until its behavioral RED lands), and the
draft-join closure (F34); D1 ``validation_*`` ingestion + the
``nflreadpy_qb_validation`` registry entry land in the adapter/registry.
Slice 3 (2026-07-18): the D2 Sleeper-scored PPG label table
(F11 ``validate_label_table``, F21 ``validate_scoring_edges``,
F28 ``validate_attrition_classes``) — settings-derived Decimal scoring with
the hash assertion, the pinned qualifying-game predicate, and the exhaustive
outcome-class law.
"""
from __future__ import annotations

from src.dynasty_genius.eval.qb_validation.errors import QBValidationFailure
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

__all__ = [
    "QBValidationFailure",
    "OUTPUT_ROOT",
    "VALIDATION_DATASETS",
    "ATTRITION_CLASSES",
    "OUTCOME_CLASSES",
    "SCORING_COMPONENTS",
    "build_label_table",
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
