"""Roster Capacity Scenario Simulator — core capacity/candidate pass.

Pure function. Delegates capacity ranking to the existing roster cut engine,
then re-joins raw value fields from the universe PVO and reshapes into a
descriptive `CapacityAuditResult`. No market data, no model artifacts, no
normative verdicts.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from src.dynasty_genius.roster_capacity.models import (
    CapacityAuditResult,
    CapacityCandidate,
    CapacityHealth,
    PoolRange,
)
from src.dynasty_genius.roster_cut_engine import compute_roster_cut_candidates

# Unrostered-pool builder constants (recorded in the producer report, spec §12).
# Deliberately wide / fail-closed, never tightening or fabricating a range.
_POOL_TOP_K = 8  # display top-K that low/high are min/max over
_POOL_MIN_POOL = 4  # a same-position pool thinner than this is unusable
_POOL_FRESHNESS_DAYS = 30  # snapshots older than this fail closed
_POOL_VALUATION_COVERAGE_FLOOR = 0.5  # >=50% of the pool must carry usable values

# Errors that signal corrupt/malformed DATA (right top-level type, wrong
# content). These yield a blocked result so a producer can record the failure.
# Wrong top-level argument TYPES are screened before the try and raise as API
# misuse; therefore any error raised INSIDE the try is data-content corruption.
# This includes TypeError (e.g. a non-dict row indexed as a dict) and ValueError
# (e.g. a protected slot type in roster_positions, or int() on a bad setting).
_DATA_CORRUPTION_ERRORS = (
    KeyError,
    IndexError,
    StopIteration,
    AttributeError,
    TypeError,
    ValueError,
)


def _finite(value: object) -> float | None:
    """Return a finite float, else None. Guards inf/nan and non-numerics."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    return None


def _build_candidate(
    engine_candidate: Any,
    pvo_lookup: dict[str, dict],
    excluded_counts: dict[str, int],
) -> CapacityCandidate:
    pid = engine_candidate.sleeper_player_id
    entry = pvo_lookup.get(pid)

    candidate_source = (
        "forced_review" if engine_candidate.cut_priority == 0 else "capacity_ordered"
    )

    if entry is None:
        excluded_counts["missing_pvo_join"] = (
            excluded_counts.get("missing_pvo_join", 0) + 1
        )
        return CapacityCandidate(
            sleeper_player_id=pid,
            full_name=engine_candidate.full_name,
            position=engine_candidate.position,
            cut_priority=engine_candidate.cut_priority,
            candidate_source=candidate_source,
            raw_xvar=None,
            dvs=None,
            xvar_pct=None,
            median_projection_2y=None,
            value_field_status={
                "xvar": "unavailable",
                "dvs": "unavailable",
                "projection_2y": "unavailable",
                "position": "unknown_position",
                "model": "pre_model",
            },
        )

    valuation = entry.get("valuation") or {}
    player_info = entry.get("player") or {}

    raw_xvar_in = valuation.get("xvar")
    dvs_in = valuation.get("dynasty_value_score")
    projection_in = entry.get("projection_2y")
    xvar_pct_in = valuation.get("xvar_percentile_overall")
    position_in = player_info.get("position")
    engine_path = valuation.get("engine_path")

    raw_xvar = _finite(raw_xvar_in)
    dvs = _finite(dvs_in)
    projection = _finite(projection_in)
    xvar_pct = _finite(xvar_pct_in)

    # Count fields that were PRESENT but non-finite (corrupt numerics), distinct
    # from genuinely absent ones. Only the three numeric value fields are tracked.
    for raw_value, clean_value in (
        (raw_xvar_in, raw_xvar),
        (dvs_in, dvs),
        (projection_in, projection),
    ):
        if raw_value is not None and clean_value is None:
            excluded_counts["non_finite_value_field"] = (
                excluded_counts.get("non_finite_value_field", 0) + 1
            )

    value_field_status = {
        "xvar": "ok" if raw_xvar is not None else "unavailable",
        "dvs": "ok" if dvs is not None else "unavailable",
        "projection_2y": "ok" if projection is not None else "unavailable",
        "position": "ok" if position_in else "unknown_position",
        "model": "ok" if engine_path and engine_path != "PRE_MODEL" else "pre_model",
    }

    return CapacityCandidate(
        sleeper_player_id=pid,
        full_name=engine_candidate.full_name,
        position=engine_candidate.position,
        cut_priority=engine_candidate.cut_priority,
        candidate_source=candidate_source,
        raw_xvar=raw_xvar,
        dvs=dvs,
        xvar_pct=xvar_pct,
        median_projection_2y=projection,
        value_field_status=value_field_status,
    )


def _pool_global_unavailable_reason(snapshot: dict) -> str | None:
    """Snapshot-wide reasons the whole waiver pool cannot be trusted.

    Returns a caveat string, or None when the snapshot is fresh and complete.
    An absent freshness/coverage signal is treated as usable (the tests build
    minimal snapshots without these keys).
    """
    # Absent captured_at: usable (minimal fixtures omit it). But a captured_at
    # that is PRESENT yet uninterpretable as a datetime — an unparseable string
    # OR a wrong type — means we cannot verify freshness, so fail closed rather
    # than silently treat a corrupt freshness signal as fresh.
    captured_at = snapshot.get("captured_at")
    if captured_at is not None:
        captured: datetime | None = None
        if isinstance(captured_at, str):
            try:
                captured = datetime.fromisoformat(captured_at)
            except ValueError:
                captured = None
        if captured is None:
            return "snapshot_freshness_unverifiable"
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - captured > timedelta(days=_POOL_FRESHNESS_DAYS):
            return f"snapshot_stale_beyond_{_POOL_FRESHNESS_DAYS}d"

    coverage = snapshot.get("coverage") or {}
    if coverage.get("rostered_players_missing_from_snapshot"):
        return "incomplete_roster_coverage"
    return None


def _max_scenario_n(scenarios: list[dict] | None) -> int:
    """Largest player count any requested scenario could draw from the pool.

    The pool keeps top-max(K, this) values so it never under-serves T3.
    """
    largest = 0
    for scenario in scenarios or []:
        if not isinstance(scenario, dict):
            continue
        if "clear_n" in scenario:
            try:
                largest = max(largest, int(scenario["clear_n"]))
            except (TypeError, ValueError):
                continue
        elif "proposed_cuts" in scenario:
            largest = max(largest, len(scenario.get("proposed_cuts") or []))
    return largest


def _pool_for_position(
    position: str,
    pool_size: int,
    values: list[float],
    retention: int,
    global_caveat: str | None,
) -> PoolRange:
    if global_caveat is not None:
        return PoolRange(
            status="waiver_range_unavailable",
            low=None,
            high=None,
            top_k_values=[],
            pool_size=pool_size,
            caveats=[global_caveat],
        )
    if pool_size < _POOL_MIN_POOL:
        return PoolRange(
            status="waiver_range_unavailable",
            low=None,
            high=None,
            top_k_values=[],
            pool_size=pool_size,
            caveats=[f"thin_unrostered_pool_below_min_{_POOL_MIN_POOL}"],
        )
    coverage_ratio = (len(values) / pool_size) if pool_size else 0.0
    if coverage_ratio < _POOL_VALUATION_COVERAGE_FLOOR:
        return PoolRange(
            status="waiver_range_unavailable",
            low=None,
            high=None,
            top_k_values=[],
            pool_size=pool_size,
            caveats=["valuation_coverage_below_floor"],
        )

    ordered = sorted(values, reverse=True)
    # top_k_values retains out to the largest scenario (for T3 depletion);
    # low/high are the min/max of the narrower DISPLAY top-K only.
    top_k_values = ordered[:retention]
    display = ordered[:_POOL_TOP_K]
    caveats: list[str] = []
    if display and all(value == 0.0 for value in display):
        caveats.append(f"{position.lower()}_unrostered_pool_depleted_all_zero_value")
    return PoolRange(
        status="ok",
        low=min(display),
        high=max(display),
        top_k_values=top_k_values,
        pool_size=pool_size,
        caveats=caveats,
    )


def _build_unrostered_pool_range(
    sleeper_snapshot: dict,
    pvo_lookup: dict[str, dict],
    scenarios: list[dict] | None,
    excluded_counts: dict[str, int],
) -> dict[str, PoolRange]:
    """Per-position replacement range over players on no roster.

    Rostered set = the union players ∪ starters ∪ taxi ∪ reserve across EVERY
    team (matches sleeper_universe._build_roster_context); unrostered = the
    snapshot player universe minus that set, grouped by position and valued via
    the PVO index. Wide, fail-closed, never fabricated.
    """
    rostered: set[str] = set()
    for roster in sleeper_snapshot.get("rosters") or []:
        for field in ("players", "starters", "taxi", "reserve"):
            for pid in roster.get(field) or []:
                if pid:
                    rostered.add(str(pid))

    # Group every snapshot position; an unrostered member is a snapshot player
    # whose id is not in the rostered union. Positions with zero unrostered
    # members still get a (fail-closed) entry so consumers find the key.
    positions: set[str] = set()
    unrostered_by_position: dict[str, list[str]] = {}
    for row in sleeper_snapshot.get("players") or []:
        if not isinstance(row, dict):
            continue
        position = (row.get("player") or {}).get("position")
        if not position:
            continue
        positions.add(position)
        pid = row.get("sleeper_player_id")
        if pid is None or str(pid) in rostered:
            continue
        unrostered_by_position.setdefault(position, []).append(str(pid))

    global_caveat = _pool_global_unavailable_reason(sleeper_snapshot)
    retention = max(_POOL_TOP_K, _max_scenario_n(scenarios))

    pool_range: dict[str, PoolRange] = {}
    for position in sorted(positions):
        members = unrostered_by_position.get(position, [])
        values: list[float] = []
        for pid in members:
            entry = pvo_lookup.get(pid)
            value = (
                _finite((entry.get("valuation") or {}).get("xvar"))
                if isinstance(entry, dict)
                else None
            )
            if value is None:
                excluded_counts["unrostered_pool_value_unavailable"] = (
                    excluded_counts.get("unrostered_pool_value_unavailable", 0) + 1
                )
            else:
                values.append(value)
        pool_range[position] = _pool_for_position(
            position, len(members), values, retention, global_caveat
        )
    return pool_range


def simulate_capacity_scenarios(
    universe_pvo: dict,
    sleeper_snapshot: dict,
    david_roster_id: int = 1,
    *,
    scenarios: list[dict] | None = None,
) -> CapacityAuditResult:
    """Descriptive capacity audit for David's roster.

    Raises TypeError on API misuse (non-dict arguments). Returns a blocked
    result on corrupt DATA. Otherwise returns an ``ok`` result with capacity
    health and a per-candidate value-at-risk view.
    """
    # API misuse (wrong argument TYPE) raises — it is a caller bug, not data.
    if not isinstance(universe_pvo, dict):
        raise TypeError(
            f"universe_pvo must be a dict, got {type(universe_pvo).__name__}"
        )
    if not isinstance(sleeper_snapshot, dict):
        raise TypeError(
            f"sleeper_snapshot must be a dict, got {type(sleeper_snapshot).__name__}"
        )

    try:
        # The PVO holds one valuation row per player; sleeper_player_id is the
        # join key. A duplicate key invalidates the join (we cannot pick a
        # canonical row), so fail closed rather than silently last-win.
        players = universe_pvo.get("players")
        if isinstance(players, list):
            seen: set[str] = set()
            duplicate_ids: list[str] = []
            for row in players:
                pid = row.get("sleeper_player_id") if isinstance(row, dict) else None
                if pid is None:
                    continue
                if pid in seen:
                    if pid not in duplicate_ids:
                        duplicate_ids.append(pid)
                else:
                    seen.add(pid)
            if duplicate_ids:
                return CapacityAuditResult(
                    status="blocked",
                    capacity_health=None,
                    candidates=[],
                    excluded_counts={},
                    caveats=[
                        "duplicate sleeper_player_id in universe_pvo: "
                        + ", ".join(duplicate_ids)
                    ],
                )

        cut_result = compute_roster_cut_candidates(
            universe_pvo, sleeper_snapshot, david_roster_id
        )

        # Active-slot overflow is recomputed from the snapshot: the cut engine
        # does not expose the non-reserve count it derives internally.
        rosters = sleeper_snapshot["rosters"]
        roster = next(r for r in rosters if r["roster_id"] == david_roster_id)
        player_ids: list[str] = roster.get("players") or []
        reserve_ids = set(roster.get("reserve") or [])
        taxi_ids = set(roster.get("taxi") or [])
        non_reserve_count = len(player_ids) - len(reserve_ids) - len(taxi_ids)
        active_slot_overflow = max(0, non_reserve_count - cut_result.active_slots)

        settings = sleeper_snapshot["league"]["settings"]
        reserve_slots = int(settings.get("reserve_slots") or 0)
        taxi_slots = int(settings.get("taxi_slots") or 0)

        pvo_lookup: dict[str, dict] = {
            p["sleeper_player_id"]: p for p in universe_pvo["players"]
        }

        excluded_counts: dict[str, int] = {}
        candidates = [
            _build_candidate(c, pvo_lookup, excluded_counts)
            for c in cut_result.cut_candidates
        ]

        capacity_health = CapacityHealth(
            total_players=cut_result.total_players,
            total_capacity=cut_result.total_capacity,
            total_capacity_cuts_required=cut_result.cuts_required,
            active_slot_overflow=active_slot_overflow,
            by_slot_class={
                "active": cut_result.active_slots,
                "reserve": reserve_slots,
                "taxi": taxi_slots,
            },
            reserve_unrestricted=cut_result.reserve_unrestricted,
        )

        unrostered_pool_range = _build_unrostered_pool_range(
            sleeper_snapshot, pvo_lookup, scenarios, excluded_counts
        )
    except _DATA_CORRUPTION_ERRORS as exc:
        return CapacityAuditResult(
            status="blocked",
            capacity_health=None,
            candidates=[],
            excluded_counts={},
            caveats=[f"capacity_audit_blocked: {type(exc).__name__}: {exc}"],
        )

    return CapacityAuditResult(
        status="ok",
        capacity_health=capacity_health,
        candidates=candidates,
        unrostered_pool_range=unrostered_pool_range,
        excluded_counts=excluded_counts,
        caveats=[],
    )
