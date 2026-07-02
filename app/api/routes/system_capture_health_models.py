"""DEBT-6 Slice 1b — capture-health cadence config models and loader.

T1 scope: Pydantic v2 schema (all ``extra="forbid"`` so verdict-fields like
``gate_4_ready`` fail closed) and the fail-closed cadence-config loader.
The timeline/gap/density/staleness analyzer (T2), the read-only SQLite reader
(T3), and route wiring/OpenAPI (T4) belong to later tasks.

Freshness never blocks: status enums are ``ok | degraded`` only — a missed
capture is a caveat lane, never an integrity gate (spec §0 standing split).

Spec: docs/superpowers/specs/2026-07-02-debt6-capture-health-slice1b-design.md
Plan: docs/superpowers/plans/2026-07-02-debt6-capture-health-slice1b-plan.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ValidationError

StoreStatus = Literal["ok", "degraded"]
OverallStatus = Literal["ok", "degraded"]
StorePresence = Literal["present", "absent"]

# SQLite identifiers cannot be parameterized, so config-supplied table/column
# names are confined to a strict identifier alphabet (Codex R3).
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _Strict(BaseModel):
    """Base model: reject unknown fields AND type coercion.

    ``extra="forbid"`` keeps verdict-language out; ``strict=True`` keeps a
    checked-in cadence contract from silently normalizing wrong shapes
    (``grace_hours: "3"`` / ``true`` must fail, not coerce — Codex T1 hold).
    """

    model_config = ConfigDict(extra="forbid", strict=True)


# --- cadence config (checked-in expectations) ---------------------------------


class CompanionTableConfig(_Strict):
    """A companion table whose per-date presence is checked alongside raw rows.

    ``capture_start_date`` is the companion's OWN go-live: raw dates before it
    are never companion gaps (the real prediction-snapshot table started four
    days after the raw store — Codex R1, seed 21).
    """

    table: str
    date_column: str
    capture_start_date: str


class WarnConsecutiveMissing(_Strict):
    in_season: int
    off_season: int


class SeasonWindows(_Strict):
    in_season_months: list[int]


class CadenceStoreConfig(_Strict):
    store_id: str
    db_path: str
    table: str
    date_column: str
    source_filter: str | None = None
    expected_settings_hash: str | None = None
    capture_start_date: str
    expected_cadence: Literal["daily"]
    scheduled_time_local: str
    grace_hours: int
    density_floor_pct: int
    density_baseline_window: int
    warn_consecutive_missing: WarnConsecutiveMissing
    window_risk_contiguous_days: int
    companion_tables: list[CompanionTableConfig] = Field(default_factory=list)


class CaptureCadenceConfig(_Strict):
    config_version: int
    timezone: str
    season_windows: SeasonWindows
    stores: list[CadenceStoreConfig]


# --- response models -----------------------------------------------------------


class MissingRange(_Strict):
    """One contiguous missing-date range; display list is capped, totals never."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")
    days: int


class StoreTimeline(_Strict):
    capture_start_date: str
    first_date: str | None
    last_date: str | None
    expected_days: int
    present_days: int
    missing_dates_count: int
    missing_ranges: list[MissingRange]
    missing_ranges_total: int
    max_contiguous_gap_days: int
    consecutive_days_current: int


class StoreStaleness(_Strict):
    last_capture_date: str | None
    expected_by: str
    stale: bool
    grace_hours: int


class StoreDensity(_Strict):
    floor_pct: int
    baseline_median_rows: int | None
    baseline_window: int
    sub_floor_dates: list[str]


class StoreFlags(_Strict):
    warn_missing: bool
    warn_basis: str
    window_risk: bool
    window_risk_basis: str


class StoreHealth(_Strict):
    store_id: str
    store_status: StoreStatus
    store_presence: StorePresence
    timeline: StoreTimeline
    staleness: StoreStaleness
    density: StoreDensity
    flags: StoreFlags
    caveats: list[str]
    decision_supported: Literal[False]


class CaptureHealthResponse(_Strict):
    overall_status: OverallStatus
    config_version: int
    checked_at: str
    stores: list[StoreHealth]
    decision_supported: Literal[False]


class CaptureHealthErrorResponse(_Strict):
    error: str
    message: str
    decision_supported: Literal[False]


# --- loader (fail-closed) -------------------------------------------------------


class CaptureHealthConfigError(Exception):
    """Raised when the checked-in cadence config cannot serve as truth.

    The route (T4) maps this whole family to a sanitized 503: a health endpoint
    whose own expectations are broken must not pretend health (spec §2).
    """


def _reject(reason: str) -> CaptureHealthConfigError:
    return CaptureHealthConfigError(f"capture cadence config {reason}")


def _validate_db_path(store_id: str, db_path: str) -> None:
    # A repo-relative POSIX path has no business containing backslashes; that
    # also closes the C:\... Windows-absolute form PurePosixPath cannot see.
    if "\\" in db_path:
        raise _reject(
            f"invalid for store {store_id!r}: db_path must be a POSIX relative path"
        )
    parts = PurePosixPath(db_path).parts
    if PurePosixPath(db_path).is_absolute() or (parts and parts[0].endswith(":")):
        raise _reject(f"invalid for store {store_id!r}: db_path must be relative")
    if ".." in parts:
        raise _reject(
            f"invalid for store {store_id!r}: db_path must not escape the repo root"
        )


def _validate_identifier(store_id: str, field_name: str, value: str) -> None:
    if not _IDENTIFIER_RE.match(value):
        raise _reject(
            f"invalid for store {store_id!r}: {field_name} {value!r} is not a "
            "safe SQL identifier"
        )


def load_capture_cadence(*, config_path: Path) -> CaptureCadenceConfig:
    """Load and validate the checked-in capture cadence config.

    Fail-closed: absent, malformed, schema-invalid, empty, duplicate-id, or
    unsafe path/identifier configs raise :class:`CaptureHealthConfigError`
    rather than returning partial expectations. The path is injectable so
    tests never touch the real ``app/config``.
    """

    if not config_path.exists():
        raise _reject(f"missing at {config_path}")

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _reject(f"malformed JSON at {config_path}: {exc}") from exc

    try:
        config = CaptureCadenceConfig.model_validate(raw)
    except ValidationError as exc:
        raise _reject(f"schema invalid at {config_path}: {exc}") from exc

    try:
        ZoneInfo(config.timezone)
    except Exception as exc:
        raise _reject(
            f"schema invalid at {config_path}: unknown timezone {config.timezone!r}"
        ) from exc

    if not config.stores:
        raise _reject(f"declares an empty stores list at {config_path}")

    seen_ids: set[str] = set()
    for store in config.stores:
        if store.store_id in seen_ids:
            raise _reject(f"has duplicate store_id {store.store_id!r}")
        seen_ids.add(store.store_id)
        _validate_db_path(store.store_id, store.db_path)
        _validate_identifier(store.store_id, "table", store.table)
        _validate_identifier(store.store_id, "date_column", store.date_column)
        for companion in store.companion_tables:
            _validate_identifier(store.store_id, "companion table", companion.table)
            _validate_identifier(
                store.store_id, "companion date_column", companion.date_column
            )
    return config
