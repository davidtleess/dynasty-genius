"""DEBT-6 Slice 1c — whole-app health models and fail-closed freshness config.

T1: strict Pydantic models (the exact-copy disclaimer is a ``Literal`` type so
no runtime path can weaken it; status enums lock ``ok|degraded`` — the health
light OBSERVES, it never gates) and the fail-closed report-freshness config
loader. The pure freshness evaluator (T2), subsystem adapters + route (T3),
and the real config + OpenAPI (T4) are later tasks.

Spec: docs/superpowers/specs/2026-07-02-debt6-health-rollup-slice1c-design.md
Plan: docs/superpowers/plans/2026-07-02-debt6-health-rollup-slice1c-plan.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, ValidationError

DISCLAIMER = (
    "System health reflects pipeline completion, artifact freshness, and model "
    "provenance verification. It does not evaluate model accuracy or guarantee "
    "trade edge."
)

HealthOverallStatus = Literal["ok", "degraded"]
HealthTier = Literal["core_substrate", "daily_diagnostics", "auxiliary"]
ReportCadence = Literal["daily", "weekly"]
ReportFreshnessStatus = Literal[
    "fresh",
    "freshness_overdue",
    "stale",
    "corrupt_or_empty",
    "dormant",
    "missing",
]
SubsystemStatus = Literal["ok", "degraded", "unavailable"]

_SCHEDULED_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class _Strict(BaseModel):
    """Reject unknown fields AND type coercion (the standing precedent)."""

    model_config = ConfigDict(extra="forbid", strict=True)


# --- report-freshness config (checked-in expectations) --------------------------


class SeasonWindows(_Strict):
    in_season_months: list[int]


class ReportArtifactConfig(_Strict):
    """One producer report artifact whose freshness the rollup observes.

    ``tier`` drives aggregation (auxiliary staleness never degrades the root —
    the amber-blindness guard); ``dormant_ok`` + ``season_windows`` make
    dormancy explicit config, never inference; ``timestamp_field`` names an
    embedded top-level timestamp (absent → disclosed mtime fallback).
    """

    artifact_id: str
    path: str
    producer: str
    cadence: ReportCadence
    scheduled_time_local: str
    grace_hours: int
    tier: HealthTier
    min_size_bytes: int
    timestamp_field: str | None
    dormant_ok: bool
    season_windows: SeasonWindows


class ReportFreshnessConfig(_Strict):
    config_version: int
    timezone: str
    artifacts: list[ReportArtifactConfig]


# --- response models --------------------------------------------------------------


class SubsystemHealth(_Strict):
    subsystem_id: str
    status: SubsystemStatus
    basis: str
    tier: HealthTier
    decision_supported: Literal[False]


class ReportHealth(_Strict):
    artifact_id: str
    status: ReportFreshnessStatus
    tier: HealthTier
    basis: str
    artifact_path: str
    producer: str
    observed_at: str | None
    age_seconds: int | None
    disclosures: list[str]
    decision_supported: Literal[False]


class SystemHealthResponse(_Strict):
    overall_status: HealthOverallStatus
    worst_affected_tier: HealthTier | None
    checked_at: str
    config_version: int
    subsystems: list[SubsystemHealth]
    reports: list[ReportHealth]
    # Exact-copy mandatory disclaimer (Gemini): a Literal type means no code
    # path can serve a weakened version and still validate.
    disclaimer: Literal[
        "System health reflects pipeline completion, artifact freshness, and model "
        "provenance verification. It does not evaluate model accuracy or guarantee "
        "trade edge."
    ]
    decision_supported: Literal[False]


class SystemHealthErrorResponse(_Strict):
    error: str
    message: str
    decision_supported: Literal[False]


# --- loader (fail-closed) -----------------------------------------------------------


class HealthConfigError(Exception):
    """Raised when the checked-in report-freshness config cannot serve as truth.

    The route (T3) maps this family to a sanitized 503: a health endpoint whose
    own expectations are broken must not report health.
    """


def _reject(reason: str) -> HealthConfigError:
    return HealthConfigError(f"report freshness config {reason}")


def _validate_repo_relative(artifact_id: str, field_name: str, value: str) -> None:
    # Repo-relative POSIX only: backslashes, absolute paths, drive prefixes,
    # and `..` segments are confinement violations (the R3-style guard).
    if "\\" in value:
        raise _reject(
            f"invalid for artifact {artifact_id!r}: {field_name} {value!r} must "
            "be a POSIX relative path"
        )
    parts = PurePosixPath(value).parts
    if PurePosixPath(value).is_absolute() or (parts and parts[0].endswith(":")):
        raise _reject(
            f"invalid for artifact {artifact_id!r}: {field_name} {value!r} must "
            "be relative"
        )
    if ".." in parts:
        raise _reject(
            f"invalid for artifact {artifact_id!r}: {field_name} {value!r} must "
            "not escape the repo root"
        )


def load_report_freshness(*, config_path: Path) -> ReportFreshnessConfig:
    """Load and validate the checked-in report-freshness config.

    Fail-closed: absent, malformed, schema-invalid (unknown cadence/tier,
    wrong types under strict mode), empty, duplicate-id, unsafe-path, bad
    schedule format, or unknown-timezone configs raise
    :class:`HealthConfigError`. The path is injectable so tests never touch
    the real ``app/config``.
    """

    if not config_path.exists():
        raise _reject(f"missing at {config_path}")

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _reject(f"malformed JSON at {config_path}: {exc}") from exc

    try:
        config = ReportFreshnessConfig.model_validate(raw)
    except ValidationError as exc:
        raise _reject(f"schema invalid at {config_path}: {exc}") from exc

    try:
        ZoneInfo(config.timezone)
    except Exception as exc:
        raise _reject(
            f"schema invalid at {config_path}: unknown timezone {config.timezone!r}"
        ) from exc

    if not config.artifacts:
        raise _reject(f"declares an empty artifacts list at {config_path}")

    seen_ids: set[str] = set()
    for artifact in config.artifacts:
        if artifact.artifact_id in seen_ids:
            raise _reject(f"has duplicate artifact_id {artifact.artifact_id!r}")
        seen_ids.add(artifact.artifact_id)
        # Value-bounds vacuum guards (Codex T1 hold): empty identifiers pass
        # lexical confinement; a zero/negative size floor disables the
        # empty-shell check; invalid season months could suppress staleness
        # through dormancy. All fail closed at load.
        if not artifact.artifact_id.strip():
            raise _reject("schema invalid: empty artifact_id")
        if not artifact.path.strip() or not artifact.producer.strip():
            raise _reject(
                f"schema invalid for artifact {artifact.artifact_id!r}: empty "
                "path or producer"
            )
        if artifact.min_size_bytes <= 0:
            raise _reject(
                f"schema invalid for artifact {artifact.artifact_id!r}: "
                "min_size_bytes must be positive"
            )
        if artifact.grace_hours < 0:
            raise _reject(
                f"schema invalid for artifact {artifact.artifact_id!r}: "
                "grace_hours must be >= 0"
            )
        months = artifact.season_windows.in_season_months
        if not months or any(m < 1 or m > 12 for m in months):
            raise _reject(
                f"schema invalid for artifact {artifact.artifact_id!r}: "
                "season months must be non-empty and each within 1..12"
            )
        _validate_repo_relative(artifact.artifact_id, "path", artifact.path)
        _validate_repo_relative(artifact.artifact_id, "producer", artifact.producer)
        if not _SCHEDULED_TIME_RE.fullmatch(artifact.scheduled_time_local):
            raise _reject(
                f"schema invalid for artifact {artifact.artifact_id!r}: "
                f"scheduled_time_local {artifact.scheduled_time_local!r} is not HH:MM"
            )
    return config
