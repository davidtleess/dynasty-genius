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
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Literal
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
    # The producer ran and declared terminal failure. Distinct from `stale` (the
    # producer never ran) and from `corrupt_or_empty` (we cannot read what it wrote).
    # A fresh timestamp NEVER launders this away — see the status gate in
    # `evaluate_report_freshness`.
    "producer_failed",
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

    ``status_field`` is opt-in: only a producer that writes a terminal-state
    status on EVERY exit path may declare it. A producer that writes a fresh
    file on failure (the common case) is indistinguishable from success on
    mtime alone, so declaring ``status_field`` is what makes failure legible.
    ``success_status`` and ``failure_reason_field`` are meaningless without it
    and are rejected at load.
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
    status_field: str | None = None
    # A scalar for single-success producers; a list for producers with several
    # healthy terminal states (e.g. the realized-outcome scorer's ok AND noop).
    # Typed list[Any] deliberately: member-type/blank/duplicate rejection lives
    # in load-time validation with NAMED HealthConfigError reasons, not in an
    # anonymous pydantic union error.
    success_status: str | list[Any] | None = None
    failure_reason_field: str | None = None


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
        # Opt-in status parsing: the dependent fields are inert without
        # `status_field`, and an inert `success_status` reads as a guarantee the
        # evaluator never enforces. Fail closed rather than silently no-op.
        if artifact.status_field is None:
            for dependent in ("success_status", "failure_reason_field"):
                if getattr(artifact, dependent) is not None:
                    raise _reject(
                        f"schema invalid for artifact {artifact.artifact_id!r}: "
                        f"{dependent} requires status_field"
                    )
        else:
            if artifact.success_status is None:
                raise _reject(
                    f"schema invalid for artifact {artifact.artifact_id!r}: "
                    "status_field requires success_status"
                )
            # Value-bounds vacuum guards, same family as the min_size_bytes /
            # empty-identifier checks above (Codex NOT-CLEAR). A blank
            # `success_status` is the dangerous one: no producer ever writes the
            # empty string, so EVERY healthy run would report `producer_failed`
            # forever — a permanent false alarm that config alone could strand.
            # A blank `failure_reason_field` names no key and can only ever
            # resolve to `unreported`, silently discarding the producer's reason.
            for field_name in ("status_field", "failure_reason_field"):
                value = getattr(artifact, field_name)
                if value is not None and not value.strip():
                    raise _reject(
                        f"schema invalid for artifact {artifact.artifact_id!r}: "
                        f"empty {field_name}"
                    )
            success = artifact.success_status
            if isinstance(success, str):
                if not success.strip():
                    raise _reject(
                        f"schema invalid for artifact {artifact.artifact_id!r}: "
                        "empty success_status"
                    )
            elif isinstance(success, list):
                if not success:
                    raise _reject(
                        f"schema invalid for artifact {artifact.artifact_id!r}: "
                        "success_status list must be non-empty"
                    )
                seen: set[str] = set()
                for member in success:
                    if not isinstance(member, str):
                        raise _reject(
                            f"schema invalid for artifact {artifact.artifact_id!r}: "
                            "success_status list members must be strings"
                        )
                    if not member.strip():
                        raise _reject(
                            f"schema invalid for artifact {artifact.artifact_id!r}: "
                            "empty success_status list member"
                        )
                    if member in seen:
                        raise _reject(
                            f"schema invalid for artifact {artifact.artifact_id!r}: "
                            "duplicate success_status"
                        )
                    seen.add(member)
    return config


def _success_statuses(success_status: str | list[Any] | None) -> tuple[str, ...]:
    """Normalize the scalar-or-list config shape to a tuple for membership tests."""
    if success_status is None:
        return ()
    if isinstance(success_status, str):
        return (success_status,)
    return tuple(success_status)


# --- T2: pure freshness evaluator + tier rollup (spec §2–§3) --------------------

_DEGRADING_STATUSES: frozenset[str] = frozenset(
    ("stale", "corrupt_or_empty", "missing", "producer_failed")
)
_TIER_SEVERITY: dict[str, int] = {"core_substrate": 2, "daily_diagnostics": 1}


class ReportArtifactFact(_Strict):
    """Observed disk facts for one report artifact (produced by the T3 reader)."""

    exists: bool
    size_bytes: int | None
    mtime: datetime | None
    embedded_timestamp_value: str | None
    # Populated only for artifacts declaring `status_field`. `None` means the
    # producer reported no readable status — absent, or present but not a string.
    # Both fail closed at the status gate; neither may reach the freshness gate.
    status_value: str | None = None
    failure_reason: str | None = None


def _last_scheduled(artifact: ReportArtifactConfig, now_local: datetime) -> datetime:
    hour, minute = (int(p) for p in artifact.scheduled_time_local.split(":"))
    anchor = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if anchor > now_local:
        anchor -= timedelta(days=1)
    return anchor


def _freshness_window_start(
    artifact: ReportArtifactConfig, anchor: datetime
) -> datetime:
    # Daily: the artifact must postdate the latest scheduled run. Weekly: any
    # run within the trailing cadence period counts (no weekday anchor in
    # config by design — the period is the contract, not the weekday).
    if artifact.cadence == "weekly":
        return anchor - timedelta(days=6)
    return anchor


def evaluate_report_freshness(
    *,
    config: ReportFreshnessConfig,
    artifact_facts: dict[str, ReportArtifactFact],
    now: datetime,
) -> list[ReportHealth]:
    """Evaluate configured artifacts against observed facts (pure — no disk).

    Honesty rules (spec §2): dormancy is explicit config; a missing artifact
    degrades unless dormant; the size floor catches empty shells regardless of
    a fresh timestamp; a declared-but-malformed embedded timestamp degrades and
    NEVER silently falls back to mtime; past-schedule-within-grace reports
    ``freshness_overdue`` — never a flat healthy over yesterday's data.
    """

    if now.tzinfo is None:
        raise ValueError("evaluate_report_freshness requires a timezone-aware `now`")
    tz = ZoneInfo(config.timezone)
    now_local = now.astimezone(tz)

    reports: list[ReportHealth] = []
    for artifact in config.artifacts:
        fact = artifact_facts.get(artifact.artifact_id)
        status: str
        basis: str
        observed_at: str | None = None
        age_seconds: int | None = None
        disclosures: list[str] = []

        off_season = now_local.month not in artifact.season_windows.in_season_months
        # Dormancy is applied as a FLOOR after evaluation (see below), never as a
        # pre-emptive short-circuit: an EXISTING artifact's content must always be
        # read — a failed marker stays producer_failed and a fresh one stays fresh
        # even off-season. Only time-based degradation (missing/stale/overdue) is
        # what "the season is over" legitimately explains away.
        if fact is None or not fact.exists:
            status, basis = "missing", "artifact_absent"
        elif fact.size_bytes is not None and fact.size_bytes < artifact.min_size_bytes:
            status, basis = (
                "corrupt_or_empty",
                f"below_min_size:{fact.size_bytes}<{artifact.min_size_bytes}",
            )
        # ── status gate: strictly BEFORE the freshness gate ──────────────────
        # A producer that declared terminal failure is `producer_failed` no matter
        # how fresh its clock reads. Ordering is the whole contract: a failed run
        # rewrites its artifact, so a fresh timestamp is exactly what a failure
        # looks like on disk. Freshness may only speak for a producer that
        # reported success.
        elif artifact.status_field is not None and fact.status_value is None:
            # Absent, or present but not a string (e.g. `123`). Never coerced —
            # strict mode everywhere else, strict here.
            status, basis = (
                "corrupt_or_empty",
                f"malformed_status:{artifact.status_field}",
            )
        elif (
            artifact.status_field is not None
            and fact.status_value not in _success_statuses(artifact.success_status)
        ):
            status, basis = (
                "producer_failed",
                f"producer_failure:{fact.failure_reason or 'unreported'}",
            )
            if fact.embedded_timestamp_value is not None:
                observed_at = fact.embedded_timestamp_value
        else:
            timestamp: datetime | None = None
            if artifact.timestamp_field is not None:
                raw = fact.embedded_timestamp_value
                if raw is None:
                    timestamp = None
                else:
                    try:
                        timestamp = datetime.fromisoformat(raw)
                    except ValueError:
                        timestamp = None
                if timestamp is None:
                    status, basis = (
                        "corrupt_or_empty",
                        f"malformed_embedded_timestamp:{artifact.timestamp_field}",
                    )
                    reports.append(
                        _report(artifact, status, basis, None, None, disclosures)
                    )
                    continue
                timestamp_basis = "embedded_timestamp"
            else:
                timestamp = fact.mtime
                disclosures.append("timestamp_source:mtime_fallback")
                timestamp_basis = "mtime"
            if timestamp is None:
                status, basis = "corrupt_or_empty", "no_observable_timestamp"
            else:
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=tz)
                observed_at = timestamp.isoformat()
                age_seconds = int((now_local - timestamp).total_seconds())
                anchor = _last_scheduled(artifact, now_local)
                if timestamp > now_local:
                    # Clock-skew guard (Codex T2 defect; the capture-health
                    # future-dates lesson): a timestamp from the future is an
                    # anomaly, never "fresh" — negative age stays disclosed.
                    status, basis = (
                        "corrupt_or_empty",
                        f"future_timestamp:{timestamp_basis}",
                    )
                elif timestamp >= _freshness_window_start(artifact, anchor):
                    status, basis = "fresh", f"{timestamp_basis}_fresh"
                elif now_local <= anchor + timedelta(hours=artifact.grace_hours):
                    status, basis = "freshness_overdue", "within_grace"
                else:
                    status, basis = "stale", "past_grace"

        # Dormancy floor: off-season, dormant_ok explains ABSENCE only — the
        # artifact was never produced because nothing should run. An EXISTING
        # artifact evaluates fully: a failed/corrupt marker stays loud, a fresh
        # one reads fresh, and a STALE one reads stale — a producer that HAS
        # been writing and then goes silent is a missed fire, not dormancy
        # (Codex round-2 catch: hiding a missed weekly fire behind dormant_ok).
        if artifact.dormant_ok and off_season and status == "missing":
            status, basis = "dormant", "dormant_ok_offseason"
            observed_at = None
            age_seconds = None

        if artifact.tier == "auxiliary" and status in _DEGRADING_STATUSES:
            disclosures.append("auxiliary_info_only")
        reports.append(
            _report(artifact, status, basis, observed_at, age_seconds, disclosures)
        )
    return reports


def _report(
    artifact: ReportArtifactConfig,
    status: str,
    basis: str,
    observed_at: str | None,
    age_seconds: int | None,
    disclosures: list[str],
) -> ReportHealth:
    return ReportHealth(
        artifact_id=artifact.artifact_id,
        status=status,  # type: ignore[arg-type]
        tier=artifact.tier,
        basis=basis,
        artifact_path=artifact.path,
        producer=artifact.producer,
        observed_at=observed_at,
        age_seconds=age_seconds,
        disclosures=disclosures,
        decision_supported=False,
    )


def rollup_health_status(
    *, reports: list[ReportHealth]
) -> tuple[str, str | None]:
    """Aggregate report statuses to (overall_status, worst_affected_tier).

    Auxiliary-tier degradation is quiet info and NEVER degrades the root (the
    amber-blindness guard); ``freshness_overdue`` and ``dormant`` never degrade
    anything. There is no blocked state — the health light observes.
    """

    worst: str | None = None
    worst_rank = 0
    for report in reports:
        if report.status not in _DEGRADING_STATUSES:
            continue
        rank = _TIER_SEVERITY.get(report.tier, 0)
        if rank > worst_rank:
            worst_rank = rank
            worst = report.tier
    if worst is None:
        return "ok", None
    return "degraded", worst


# --- T3: report artifact-facts reader (read-only; spec §2) ----------------------


def read_report_artifact_facts(
    *, config: ReportFreshnessConfig, repo_root: Path
) -> dict[str, ReportArtifactFact]:
    """Observe disk facts for each configured artifact (strictly read-only).

    The embedded timestamp is extracted ONLY for artifacts that declare a
    ``timestamp_field`` — undeclared artifacts are never parsed (their content
    is not this layer's business). A declared-but-unparseable file yields
    ``embedded_timestamp_value=None``, which the evaluator fails closed as a
    malformed embedded timestamp (degrading the report, never the route).
    """

    facts: dict[str, ReportArtifactFact] = {}
    for artifact in config.artifacts:
        path = repo_root / artifact.path
        # Defense in depth: configs built without the loader (or a compromised
        # one) still cannot walk outside the repo root.
        try:
            if not path.resolve().is_relative_to(repo_root.resolve()):
                raise _reject(
                    f"invalid for artifact {artifact.artifact_id!r}: path "
                    f"{artifact.path!r} resolves outside the repo root"
                )
        except OSError as exc:
            raise _reject(
                f"invalid for artifact {artifact.artifact_id!r}: path "
                f"{artifact.path!r} cannot be resolved"
            ) from exc
        if not path.is_file():
            facts[artifact.artifact_id] = ReportArtifactFact(
                exists=False, size_bytes=None, mtime=None, embedded_timestamp_value=None
            )
            continue
        stat = path.stat()
        embedded: str | None = None
        status_value: str | None = None
        failure_reason: str | None = None
        # One read serves both gates. An unreadable payload leaves every derived
        # fact at its closed default, so the evaluator degrades rather than guesses.
        if artifact.timestamp_field is not None or artifact.status_field is not None:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                payload = None
            if isinstance(payload, dict):
                if artifact.timestamp_field is not None:
                    value = payload.get(artifact.timestamp_field)
                    embedded = value if isinstance(value, str) else None
                if artifact.status_field is not None:
                    raw_status = payload.get(artifact.status_field)
                    status_value = raw_status if isinstance(raw_status, str) else None
                    if artifact.failure_reason_field is not None:
                        raw_reason = payload.get(artifact.failure_reason_field)
                        failure_reason = (
                            raw_reason if isinstance(raw_reason, str) else None
                        )
        facts[artifact.artifact_id] = ReportArtifactFact(
            exists=True,
            size_bytes=stat.st_size,
            mtime=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            embedded_timestamp_value=embedded,
            status_value=status_value,
            failure_reason=failure_reason,
        )
    return facts
