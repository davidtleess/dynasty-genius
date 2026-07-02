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
import sqlite3
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from pathlib import Path, PurePosixPath
from statistics import median_low
from typing import Any, Literal
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
        # Values the analyzer consumes at request time must be provably usable
        # at LOAD time — a malformed schedule or start date is config
        # corruption (503), never a request-time crash.
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", store.scheduled_time_local):
            raise _reject(
                f"schema invalid for store {store.store_id!r}: "
                f"scheduled_time_local {store.scheduled_time_local!r} is not HH:MM"
            )
        if _parse_date(store.capture_start_date) is None:
            raise _reject(
                f"schema invalid for store {store.store_id!r}: "
                f"capture_start_date {store.capture_start_date!r} is not an ISO date"
            )
        for companion in store.companion_tables:
            _validate_identifier(store.store_id, "companion table", companion.table)
            _validate_identifier(
                store.store_id, "companion date_column", companion.date_column
            )
            if _parse_date(companion.capture_start_date) is None:
                raise _reject(
                    f"schema invalid for store {store.store_id!r}: companion "
                    f"capture_start_date {companion.capture_start_date!r} is not "
                    "an ISO date"
                )
    return config


# --- T2: pure timeline/gap/density/staleness analyzer (spec §3, seeds 1-11,16,20-27)

# Class A is a CLOSED list (spec §3 R7): healthy-but-immature caveats that may
# coexist with ok. Any caveat not listed here — including future additions —
# degrades by default (fail-closed); extending Class A requires a
# cockpit-cleared spec amendment.
_CLASS_A_CAVEATS: frozenset[str] = frozenset(
    ("density_baseline_insufficient", "pre_capture_window")
)
_MISSING_RANGES_DISPLAY_CAP = 20
_MIN_DENSITY_BASELINE_DATES = 3


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _contiguous_ranges(missing: list[date]) -> list[list[date]]:
    ranges: list[list[date]] = []
    for day in missing:
        if ranges and (day - ranges[-1][-1]).days == 1:
            ranges[-1].append(day)
        else:
            ranges.append([day])
    return ranges


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def analyze_store_health(
    *,
    store_config: CadenceStoreConfig,
    date_row_counts: Mapping[str, Any],
    companion_date_sets: Mapping[str, set[str]],
    now: datetime,
    timezone: str,
    season_windows: SeasonWindows,
) -> StoreHealth:
    """Analyze one store's captured-date observations into StoreHealth (pure).

    ``date_row_counts`` values are plain row counts, or reader-metadata dicts
    ``{"row_count", "unexpected_settings_hashes", "caveats"}``. No disk here:
    the T3 reader produces these observations; this function owns their
    meaning. Facts (missing dates, gaps, staleness) are always reported;
    season-awareness modulates only the warn flag. Sub-floor "empty-shell"
    dates count as missing. The density baseline uses prior eligible dates
    only (never the date under evaluation, never future/invalid/sub-floor
    dates) so early empty shells cannot self-normalize the floor down.
    """

    # API misuse fails loud: a naive `now` would silently assume the system
    # zone and skew every deadline (robustness boundary — caller bug, not data).
    if now.tzinfo is None:
        raise ValueError("analyze_store_health requires a timezone-aware `now`")

    tz = ZoneInfo(timezone)
    now_local = now.astimezone(tz)
    today = now_local.date()

    hour, minute = (int(part) for part in store_config.scheduled_time_local.split(":"))
    deadline = datetime.combine(today, time(hour, minute), tzinfo=tz) + timedelta(
        hours=store_config.grace_hours
    )
    end_date = today if now_local >= deadline else today - timedelta(days=1)
    start_date = date.fromisoformat(store_config.capture_start_date)

    # Normalize observations; classify invalid / future keys out of the math.
    observed: dict[date, int] = {}
    external_caveats: list[str] = []
    has_invalid = False
    has_future = False
    has_unexpected_hash = False
    for key, value in date_row_counts.items():
        parsed = _parse_date(key)
        if parsed is None:
            has_invalid = True
            continue
        if isinstance(value, Mapping):
            row_count = int(value.get("row_count", 0))
            if value.get("unexpected_settings_hashes"):
                has_unexpected_hash = True
            external_caveats.extend(value.get("caveats", ()))
        else:
            row_count = int(value)
        if parsed > today:
            has_future = True
            continue
        # A zero-count observation means no canonical rows landed that day
        # (e.g. only wrong-settings-hash rows): the date is ABSENT, not an
        # empty shell — but its metadata flags above still surface.
        if row_count > 0:
            observed[parsed] = row_count

    last_capture = max(observed) if observed else None

    caveats: list[str] = []
    if end_date < start_date:
        caveats.append("pre_capture_window")
        expected_dates: list[date] = []
    else:
        expected_dates = [
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        ]

    present_raw = sorted(day for day in expected_dates if day in observed)

    # Density pass (ascending): evaluate each present date against the median
    # of PRIOR eligible dates only; sub-floor dates never join the baseline.
    eligible: list[date] = []
    sub_floor: list[date] = []
    for day in present_raw:
        if len(eligible) >= _MIN_DENSITY_BASELINE_DATES:
            baseline = median_low(observed[prior] for prior in eligible)
            if observed[day] < baseline * store_config.density_floor_pct / 100:
                sub_floor.append(day)
                continue
        eligible.append(day)
    baseline_median = (
        median_low(observed[day] for day in eligible)
        if len(eligible) >= _MIN_DENSITY_BASELINE_DATES
        else None
    )
    if expected_dates and baseline_median is None:
        caveats.append("density_baseline_insufficient")

    effective_present = set(present_raw) - set(sub_floor)
    missing = [day for day in expected_dates if day not in effective_present]
    ranges = _contiguous_ranges(missing)
    max_gap = max((len(r) for r in ranges), default=0)

    streak = 0
    cursor = end_date
    while cursor >= start_date and cursor in effective_present:
        streak += 1
        cursor -= timedelta(days=1)

    stale = bool(expected_dates) and end_date == today and today not in effective_present

    in_season = now_local.month in season_windows.in_season_months
    season_label = "in_season" if in_season else "off_season"
    warn_threshold = (
        store_config.warn_consecutive_missing.in_season
        if in_season
        else store_config.warn_consecutive_missing.off_season
    )

    if has_future:
        caveats.append("future_dates_detected")
    if has_invalid:
        caveats.append("invalid_dates_detected")
    if has_unexpected_hash:
        caveats.append("unexpected_settings_hash_detected")

    for companion in store_config.companion_tables:
        companion_start = max(date.fromisoformat(companion.capture_start_date), start_date)
        companion_dates = companion_date_sets.get(companion.table, set())
        if any(
            day >= companion_start and day.isoformat() not in companion_dates
            for day in present_raw
        ):
            caveats.append("companion_rows_missing")

    if len(ranges) > _MISSING_RANGES_DISPLAY_CAP:
        caveats.append("missing_ranges_truncated")
    caveats = _ordered_unique(caveats + list(external_caveats))

    has_class_b_caveat = any(c not in _CLASS_A_CAVEATS for c in caveats)
    status: StoreStatus = (
        "ok"
        if not missing and not stale and not sub_floor and not has_class_b_caveat
        else "degraded"
    )

    return StoreHealth(
        store_id=store_config.store_id,
        store_status=status,
        store_presence="present",
        timeline=StoreTimeline(
            capture_start_date=store_config.capture_start_date,
            first_date=min(present_raw).isoformat() if present_raw else None,
            last_date=max(present_raw).isoformat() if present_raw else None,
            expected_days=len(expected_dates),
            present_days=len(effective_present),
            missing_dates_count=len(missing),
            missing_ranges=[
                MissingRange(
                    from_date=r[0].isoformat(), to_date=r[-1].isoformat(), days=len(r)
                )
                for r in ranges[:_MISSING_RANGES_DISPLAY_CAP]
            ],
            missing_ranges_total=len(ranges),
            max_contiguous_gap_days=max_gap,
            consecutive_days_current=streak,
        ),
        staleness=StoreStaleness(
            last_capture_date=last_capture.isoformat() if last_capture else None,
            expected_by=deadline.isoformat(),
            stale=stale,
            grace_hours=store_config.grace_hours,
        ),
        density=StoreDensity(
            floor_pct=store_config.density_floor_pct,
            baseline_median_rows=int(baseline_median)
            if baseline_median is not None
            else None,
            baseline_window=store_config.density_baseline_window,
            sub_floor_dates=[day.isoformat() for day in sub_floor],
        ),
        flags=StoreFlags(
            warn_missing=max_gap >= warn_threshold and bool(missing),
            warn_basis=f"{season_label}>={warn_threshold} consecutive",
            window_risk=max_gap >= store_config.window_risk_contiguous_days,
            window_risk_basis=(
                f">={store_config.window_risk_contiguous_days} contiguous missing days"
            ),
        ),
        caveats=caveats,
        decision_supported=False,
    )


# --- T3: read-only SQLite reader + assembly (spec §3, seeds 12-13, 17-18, 21-22)


def _empty_observation_health(
    *,
    store_config: CadenceStoreConfig,
    now: datetime,
    timezone: str,
    season_windows: SeasonWindows,
    presence: StorePresence,
    caveat: str,
) -> StoreHealth:
    """Health for a store we could not read: honest window facts, one caveat.

    The timeline still reports what was EXPECTED (missing days, staleness) so
    an absent/corrupt store never looks quieter than a healthy one; the single
    Class-B caveat names the reason and forces ``degraded``.
    """

    health = analyze_store_health(
        store_config=store_config,
        date_row_counts={},
        companion_date_sets={},
        now=now,
        timezone=timezone,
        season_windows=season_windows,
    )
    return health.model_copy(
        update={
            "store_presence": presence,
            "store_status": "degraded",
            "caveats": [caveat],
        }
    )


def _read_capture_store(
    db_path: Path, store_config: CadenceStoreConfig
) -> tuple[dict[str, Any], dict[str, set[str]]]:
    """Read per-date observations + companion date sets (strictly read-only).

    Identifiers are loader-validated (R3); values are parameterized. When
    ``expected_settings_hash`` is set, only matching rows count as canonical —
    other hashes surface as per-date metadata so they can never mask a missing
    canonical day (seed 22).
    """

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        source_where = ""
        params: list[str] = []
        if store_config.source_filter is not None:
            source_where = " WHERE source = ?"
            params.append(store_config.source_filter)

        observations: dict[str, Any] = {}
        if store_config.expected_settings_hash is None:
            rows = connection.execute(
                f"SELECT {store_config.date_column}, COUNT(*) "  # noqa: S608 — identifiers loader-validated
                f"FROM {store_config.table}{source_where} "
                f"GROUP BY {store_config.date_column}",
                params,
            ).fetchall()
            for day, count in rows:
                observations[day] = count
        else:
            rows = connection.execute(
                f"SELECT {store_config.date_column}, settings_hash, COUNT(*) "  # noqa: S608
                f"FROM {store_config.table}{source_where} "
                f"GROUP BY {store_config.date_column}, settings_hash",
                params,
            ).fetchall()
            per_date: dict[Any, dict[str, int]] = {}
            for day, settings_hash, count in rows:
                per_date.setdefault(day, {})[settings_hash] = count
            for day, hash_counts in per_date.items():
                canonical = hash_counts.get(store_config.expected_settings_hash, 0)
                unexpected = sorted(
                    h
                    for h in hash_counts
                    if h != store_config.expected_settings_hash
                )
                if unexpected:
                    observations[day] = {
                        "row_count": canonical,
                        "unexpected_settings_hashes": unexpected,
                    }
                elif canonical > 0:
                    observations[day] = canonical

        companion_date_sets: dict[str, set[str]] = {}
        for companion in store_config.companion_tables:
            companion_rows = connection.execute(
                f"SELECT DISTINCT {companion.date_column} FROM {companion.table}"  # noqa: S608
            ).fetchall()
            companion_date_sets[companion.table] = {
                row[0] for row in companion_rows if isinstance(row[0], str)
            }
        return observations, companion_date_sets
    finally:
        connection.close()


def inspect_capture_store(
    *,
    store_config: CadenceStoreConfig,
    repo_root: Path,
    now: datetime,
    timezone: str,
    season_windows: SeasonWindows,
) -> StoreHealth:
    """Inspect one capture store on disk and analyze its health (read-only).

    An absent db file is a first-class ``store_absent`` state — the file is
    NEVER created by the health check (mode=ro open + presence check first).
    Any SQLite-level failure (0-byte file, missing table/column, non-database
    bytes) degrades as ``store_unreadable`` rather than raising to the client.
    """

    db_path = repo_root / store_config.db_path
    if not db_path.is_file():
        return _empty_observation_health(
            store_config=store_config,
            now=now,
            timezone=timezone,
            season_windows=season_windows,
            presence="absent",
            caveat="store_absent",
        )
    try:
        observations, companion_date_sets = _read_capture_store(db_path, store_config)
    except sqlite3.Error:
        return _empty_observation_health(
            store_config=store_config,
            now=now,
            timezone=timezone,
            season_windows=season_windows,
            presence="present",
            caveat="store_unreadable",
        )
    return analyze_store_health(
        store_config=store_config,
        date_row_counts=observations,
        companion_date_sets=companion_date_sets,
        now=now,
        timezone=timezone,
        season_windows=season_windows,
    )
