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
    ScenarioRequest,
    ScenarioResult,
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


def _value_at_risk(
    player_value: float | None, pool: PoolRange | None
) -> tuple[float, float] | None:
    """Single-player value-at-risk range, pinned orientation, unclamped.

    `[player − pool_max, player − pool_min]`: low = best-case recovery (the cut
    is replaced by the best available), high = worst-case. Negative means the
    replacement is better than the player (the cut is a net upgrade). None when
    the pool has no usable range or the player carries no value.
    """
    if pool is None or pool.low is None or pool.high is None or player_value is None:
        return None
    return (player_value - pool.high, player_value - pool.low)


def _resolve_cut_set(
    request: ScenarioRequest,
    candidates: list[CapacityCandidate],
    cut_result: Any,
    roster_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Turn a request into a concrete cut set, caveating what it cannot honor."""
    candidate_ids = {c.sleeper_player_id for c in candidates}
    caveats: list[str] = []

    if request.proposed_cuts is not None:
        exempt_ids = {e.sleeper_player_id for e in cut_result.exempt_players}
        cut_set: list[str] = []
        for pid in request.proposed_cuts:
            if pid in candidate_ids:
                cut_set.append(pid)
            elif pid in exempt_ids:
                caveats.append(f"proposed_cut_exempt_skipped:{pid}")
            elif pid in roster_ids:
                caveats.append(f"proposed_cut_not_a_capacity_candidate_skipped:{pid}")
            else:
                caveats.append(f"proposed_cut_off_roster_skipped:{pid}")
        return cut_set, caveats

    requested = (
        request.clear_n if request.clear_n is not None else cut_result.cuts_required
    )
    ordered_ids = [c.sleeper_player_id for c in candidates]
    take = requested
    if requested > len(ordered_ids):
        caveats.append(
            f"clear_n_exceeds_available_candidates:requested_{requested}"
            f"_available_{len(ordered_ids)}"
        )
        take = len(ordered_ids)
    take = max(0, take)
    return ordered_ids[:take], caveats


def _build_scenario(
    request: ScenarioRequest,
    candidates: list[CapacityCandidate],
    cut_result: Any,
    pool_range: dict[str, PoolRange],
    roster_ids: set[str],
) -> ScenarioResult:
    candidate_by_id = {c.sleeper_player_id: c for c in candidates}
    cut_set, caveats = _resolve_cut_set(request, candidates, cut_result, roster_ids)
    cut_lookup = set(cut_set)

    # Group the cut set per position with its raw value.
    cut_values_by_position: dict[str, list[float]] = {}
    for pid in cut_set:
        candidate = candidate_by_id.get(pid)
        if candidate is None:
            continue
        if candidate.raw_xvar is None:
            caveats.append(f"cut_player_value_unavailable:{pid}")
            continue
        cut_values_by_position.setdefault(candidate.position, []).append(
            candidate.raw_xvar
        )

    # Depletion-aware cumulative: per position, best case recovers the top-N of
    # the retained pool, worst case the bottom-N of it. Slices cap at what
    # exists, so deficit spots (no replacement) recover nothing. Summed across
    # positions; unclamped, orientation cannot invert.
    low_total = 0.0
    high_total = 0.0
    pool_deficits: dict[str, int] = {}
    for position, cut_values in cut_values_by_position.items():
        n_p = len(cut_values)
        cut_sum = sum(cut_values)
        pool = pool_range.get(position)

        # Unavailable pool (stale / unverifiable / coverage failure): recovery is
        # genuinely UNKNOWN, so widen to the full uncertainty band [0, cut_sum]
        # and caveat — never a precise (cut_sum, cut_sum) that would read as a
        # verified zero-recovery calc. Distinct from a deficit (valid-but-
        # exhausted) and from a barren-but-valid `ok` pool (real zero recovery).
        if pool is None or pool.status != "ok":
            low_total += 0.0
            high_total += cut_sum
            caveats.append(
                f"{position}_waiver_range_unavailable_recovery_unverifiable"
            )
            continue

        retained = list(pool.top_k_values)
        upper_recovery = sum(sorted(retained, reverse=True)[:n_p])
        lower_recovery = sum(sorted(retained)[:n_p])
        low_total += cut_sum - upper_recovery
        high_total += cut_sum - lower_recovery

        pool_size = pool.pool_size if pool.pool_size is not None else 0
        if n_p > pool_size:
            deficit = n_p - pool_size
            pool_deficits[position] = deficit
            caveats.append(
                f"{position}_unrostered_pool_insufficient_to_replace_cuts"
                f"_deficit_of_{deficit}"
            )

    # The next capacity-ordered candidate not in the cut set — the cost of going
    # one deeper in the EXISTING forced order. No identifier; nominates no one.
    marginal_next_candidate_cost: tuple[float, float] | None = None
    for candidate in candidates:
        if candidate.sleeper_player_id in cut_lookup:
            continue
        if candidate.candidate_source != "capacity_ordered":
            continue
        marginal_next_candidate_cost = _value_at_risk(
            candidate.raw_xvar, pool_range.get(candidate.position)
        )
        break

    # Descriptive depth after the cuts: active = cut-eligible candidates that
    # remain, bench = exempt (taxi/IR) rows. Purely informational.
    per_position_depth_impact: dict[str, dict[str, int]] = {}
    for position in cut_values_by_position:
        active_after = sum(
            1
            for c in candidates
            if c.position == position and c.sleeper_player_id not in cut_lookup
        )
        bench_after = sum(
            1
            for e in cut_result.exempt_players
            if e.position == position and e.sleeper_player_id not in cut_lookup
        )
        per_position_depth_impact[position] = {
            "active_after": active_after,
            "bench_after": bench_after,
        }

    return ScenarioResult(
        cut_set=cut_set,
        cumulative_value_at_risk=(low_total, high_total),
        marginal_next_candidate_cost=marginal_next_candidate_cost,
        per_position_depth_impact=per_position_depth_impact,
        pool_deficits=pool_deficits,
        caveats=caveats,
    )


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

        # Scenario rollup: None -> a single default clear of the required cuts.
        roster_ids = set(player_ids) | reserve_ids | taxi_ids
        scenario_inputs = (
            scenarios
            if scenarios is not None
            else [{"clear_n": cut_result.cuts_required}]
        )
        scenario_results = [
            _build_scenario(
                ScenarioRequest.model_validate(scenario_input),
                candidates,
                cut_result,
                unrostered_pool_range,
                roster_ids,
            )
            for scenario_input in scenario_inputs
        ]
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
        scenarios=scenario_results,
        unrostered_pool_range=unrostered_pool_range,
        excluded_counts=excluded_counts,
        caveats=[],
    )
