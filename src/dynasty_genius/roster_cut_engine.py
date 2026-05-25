"""Phase 21 — Roster Cut Engine.

Pure-function module: reads Sleeper snapshot + universe PVO,
returns a ranked RosterCutResult. No market data, no model artifacts touched.
"""
from __future__ import annotations

from pydantic import BaseModel

# ── Constants ──────────────────────────────────────────────────────────────────

CLIFF_AGES: dict[str, float] = {
    "RB": 27.0,
    "WR": 28.0,
    "TE": 28.0,
    "QB": 33.0,
}

_RESERVE_ALLOW_FLAGS: list[str] = [
    "reserve_allow_out",
    "reserve_allow_doubtful",
    "reserve_allow_sus",
    "reserve_allow_na",
    "reserve_allow_cov",
    "reserve_allow_dnr",
]

_STATUS_CANONICAL: dict[str, str] = {
    "out": "Out",
    "doubtful": "Doubtful",
    "suspended": "Suspended",
    "sus": "Suspended",
    "na": "NA",
    "covid-19": "COVID-19",
    "covid": "COVID-19",
    "cov": "COVID-19",
    "dnr": "DNR",
    "active": "Active",
    "questionable": "Questionable",
    "probable": "Probable",
}

_CANONICAL_TO_FLAG: dict[str, str] = {
    "Out": "reserve_allow_out",
    "Doubtful": "reserve_allow_doubtful",
    "Suspended": "reserve_allow_sus",
    "NA": "reserve_allow_na",
    "COVID-19": "reserve_allow_cov",
    "DNR": "reserve_allow_dnr",
}

_FORCED_REVIEW_STATUSES: frozenset[str] = frozenset({
    "ILLEGAL_RESERVE",
    "UNKNOWN_STATUS",
    "INVALID_SNAPSHOT",
})

_FORCED_REVIEW_RATIONALE: dict[str, str] = {
    "ILLEGAL_RESERVE": "reserve_slot_ineligible_must_comply",
    "UNKNOWN_STATUS": "reserve_eligibility_unknown_status_requires_review",
    "INVALID_SNAPSHOT": "reserve_slot_does_not_exist_in_league_settings",
}

_PROTECTED_SLOT_TYPES: frozenset[str] = frozenset({"IR", "TAXI"})

# ── Output models ──────────────────────────────────────────────────────────────


class RosterCutCandidate(BaseModel):
    sleeper_player_id: str
    full_name: str
    position: str
    age: float | None
    years_exp: int | None
    ir_compliance_status: str
    taxi_eligibility: str
    scoring_tier: str
    xvar_pct: float | None
    dvs: float | None
    cut_priority: int
    age_cliff_warning: bool
    cut_rationale: list[str]
    exempt: bool
    exempt_reason: str | None
    decision_supported: bool = False


class RosterCutResult(BaseModel):
    roster_id: int
    total_players: int
    active_slots: int
    total_capacity: int
    cuts_required: int
    reserve_unrestricted: bool
    cut_candidates: list[RosterCutCandidate]
    exempt_players: list[RosterCutCandidate]
    decision_supported: bool = False


# ── Pure helpers ───────────────────────────────────────────────────────────────


def _normalize_sleeper_status(raw: str | None) -> str:
    if raw is None:
        return "UNKNOWN_STATUS"
    return _STATUS_CANONICAL.get(raw.strip().lower(), "UNKNOWN_STATUS")


def _ir_compliance_status(
    sleeper_status: str | None,
    reserve_unrestricted: bool,
    reserve_slots: int,
    settings: dict,
) -> tuple[str, list[str]]:
    if reserve_slots == 0:
        return "INVALID_SNAPSHOT", ["reserve_slot_does_not_exist_in_league_settings"]
    if reserve_unrestricted:
        return "COMPLIANT", []
    canonical = _normalize_sleeper_status(sleeper_status)
    if canonical == "UNKNOWN_STATUS":
        return "UNKNOWN_STATUS", ["reserve_eligibility_unknown_status"]
    flag_key = _CANONICAL_TO_FLAG.get(canonical)
    if flag_key and int(settings.get(flag_key) or 0) == 1:
        return "COMPLIANT", []
    return "ILLEGAL_RESERVE", []


def _taxi_eligibility(years_exp: int, taxi_years: int, taxi_allow_vets: int) -> str:
    if taxi_allow_vets == 1 or years_exp <= taxi_years:
        return "ELIGIBLE"
    return "INELIGIBLE_VET"


def _taxi_deadline_status(season_type: str, week: int | None, taxi_deadline: int) -> str:
    if season_type in ("off", "pre") or week in (None, 0):
        return "NOT_REACHED"
    if week >= taxi_deadline:
        return "PASSED"
    if week >= taxi_deadline - 1:
        return "APPROACHING"
    return "NOT_REACHED"


def _age_cliff_warning(position: str, age: float | None) -> bool:
    if age is None:
        return False
    cliff = CLIFF_AGES.get(position)
    return cliff is not None and age >= cliff


def _scoring_tier(engine_path: str | None, xvar_pct: float | None, dvs: float | None) -> str:
    if engine_path == "PRE_MODEL":
        return "D"
    if xvar_pct is not None:
        return "A"
    if dvs is not None:
        return "B"
    return "C"


def _tier_sort_key(tier: str, xvar_pct: float | None, dvs: float | None) -> tuple[int, float]:
    tier_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    to = tier_order.get(tier, 3)
    if tier == "A":
        score = xvar_pct if xvar_pct is not None else float("inf")
    elif tier in ("B", "C"):
        score = dvs if dvs is not None else float("inf")
    else:
        score = float("inf")
    return (to, score)


# ── Main function ──────────────────────────────────────────────────────────────


def compute_roster_cut_candidates(
    universe_pvo: dict,
    sleeper_snapshot: dict,
    david_roster_id: int = 1,
) -> RosterCutResult:
    # Step 1: Parse settings and validate roster_positions
    league = sleeper_snapshot["league"]
    roster_positions: list[str] = league["roster_positions"]
    settings: dict = league["settings"]

    for pos in roster_positions:
        if pos in _PROTECTED_SLOT_TYPES:
            raise ValueError(f"roster_positions contains protected slot types: {pos!r}")

    active_slots = len(roster_positions)
    reserve_slots = int(settings.get("reserve_slots") or 0)
    taxi_slots = int(settings.get("taxi_slots") or 0)
    taxi_years = int(settings.get("taxi_years") or 0)
    taxi_allow_vets = int(settings.get("taxi_allow_vets") or 0)
    total_capacity = active_slots + reserve_slots + taxi_slots

    reserve_unrestricted = (
        reserve_slots > 0
        and all(int(settings.get(f) or 0) == 0 for f in _RESERVE_ALLOW_FLAGS)
    )

    # Step 2: Get roster data
    rosters = sleeper_snapshot["rosters"]
    roster = next(r for r in rosters if r["roster_id"] == david_roster_id)
    player_ids: list[str] = roster.get("players") or []
    taxi_ids: set[str] = set(roster.get("taxi") or [])
    reserve_ids: set[str] = set(roster.get("reserve") or [])
    total_players = len(player_ids)

    # over_limit: active-slot overflow (non-taxi, non-reserve players minus active slots)
    # This is the trigger for generating the cut list.
    # cuts_required: how many must actually be released (total vs total_capacity).
    non_reserve_count = total_players - len(reserve_ids) - len(taxi_ids)
    over_limit = non_reserve_count - active_slots
    cuts_required = max(0, total_players - total_capacity)

    # Step 3: Build PVO lookup
    pvo_lookup: dict[str, dict] = {
        p["sleeper_player_id"]: p for p in universe_pvo["players"]
    }

    # Step 4: Categorize all roster players
    exempt_players: list[RosterCutCandidate] = []
    forced_candidates: list[RosterCutCandidate] = []
    active_pool: list[dict] = []

    for pid in player_ids:
        entry = pvo_lookup.get(pid, {})
        pinfo = entry.get("player", {})
        val = entry.get("valuation", {})

        position = pinfo.get("position", "UNK")
        age: float | None = pinfo.get("age")
        years_exp: int = int(pinfo.get("years_exp") or 0)
        sleeper_status: str | None = pinfo.get("sleeper_status")
        xvar_pct: float | None = val.get("xvar_percentile_overall")
        dvs: float | None = val.get("dynasty_value_score")
        engine_path: str | None = val.get("engine_path", "PRE_MODEL")
        full_name: str = pinfo.get("full_name", pid)

        taxi_elig = _taxi_eligibility(years_exp, taxi_years, taxi_allow_vets)
        cliff = _age_cliff_warning(position, age)
        tier = _scoring_tier(engine_path, xvar_pct, dvs)

        if pid in taxi_ids:
            exempt_players.append(RosterCutCandidate(
                sleeper_player_id=pid,
                full_name=full_name,
                position=position,
                age=age,
                years_exp=years_exp,
                ir_compliance_status="NOT_ON_IR",
                taxi_eligibility=taxi_elig,
                scoring_tier=tier,
                xvar_pct=xvar_pct,
                dvs=dvs,
                cut_priority=-1,
                age_cliff_warning=cliff,
                cut_rationale=[],
                exempt=True,
                exempt_reason="taxi",
            ))
            continue

        if pid in reserve_ids:
            compliance_status, compliance_caveats = _ir_compliance_status(
                sleeper_status, reserve_unrestricted, reserve_slots, settings
            )
            if compliance_status in _FORCED_REVIEW_STATUSES:
                rationale_key = _FORCED_REVIEW_RATIONALE[compliance_status]
                cut_rationale = [rationale_key] + [
                    c for c in compliance_caveats if c != rationale_key
                ]
                if cliff:
                    cut_rationale.append("age_at_or_past_position_cliff")
                forced_candidates.append(RosterCutCandidate(
                    sleeper_player_id=pid,
                    full_name=full_name,
                    position=position,
                    age=age,
                    years_exp=years_exp,
                    ir_compliance_status=compliance_status,
                    taxi_eligibility=taxi_elig,
                    scoring_tier=tier,
                    xvar_pct=xvar_pct,
                    dvs=dvs,
                    cut_priority=0,
                    age_cliff_warning=cliff,
                    cut_rationale=cut_rationale,
                    exempt=False,
                    exempt_reason=None,
                ))
            else:
                rationale: list[str] = []
                if cliff:
                    rationale.append("age_at_or_past_position_cliff")
                exempt_players.append(RosterCutCandidate(
                    sleeper_player_id=pid,
                    full_name=full_name,
                    position=position,
                    age=age,
                    years_exp=years_exp,
                    ir_compliance_status=compliance_status,
                    taxi_eligibility=taxi_elig,
                    scoring_tier=tier,
                    xvar_pct=xvar_pct,
                    dvs=dvs,
                    cut_priority=-1,
                    age_cliff_warning=cliff,
                    cut_rationale=rationale,
                    exempt=True,
                    exempt_reason="ir_compliant",
                ))
            continue

        # Active player — add to scoring pool
        active_pool.append({
            "pid": pid,
            "full_name": full_name,
            "position": position,
            "age": age,
            "years_exp": years_exp,
            "taxi_elig": taxi_elig,
            "tier": tier,
            "xvar_pct": xvar_pct,
            "dvs": dvs,
            "cliff": cliff,
        })

    # Step 5: Early-return guard
    if over_limit <= 0 and not forced_candidates:
        return RosterCutResult(
            roster_id=david_roster_id,
            total_players=total_players,
            active_slots=active_slots,
            total_capacity=total_capacity,
            cuts_required=cuts_required,
            reserve_unrestricted=reserve_unrestricted,
            cut_candidates=[],
            exempt_players=exempt_players,
        )

    # Step 6: Score and rank active candidates (only when over_limit > 0)
    cut_candidates: list[RosterCutCandidate] = list(forced_candidates)

    if over_limit > 0:
        active_pool.sort(key=lambda c: _tier_sort_key(c["tier"], c["xvar_pct"], c["dvs"]))
        for rank, ac in enumerate(active_pool, start=1):
            rationale = []
            if ac["cliff"]:
                rationale.append("age_at_or_past_position_cliff")
            cut_candidates.append(RosterCutCandidate(
                sleeper_player_id=ac["pid"],
                full_name=ac["full_name"],
                position=ac["position"],
                age=ac["age"],
                years_exp=ac["years_exp"],
                ir_compliance_status="NOT_ON_IR",
                taxi_eligibility=ac["taxi_elig"],
                scoring_tier=ac["tier"],
                xvar_pct=ac["xvar_pct"],
                dvs=ac["dvs"],
                cut_priority=rank,
                age_cliff_warning=ac["cliff"],
                cut_rationale=rationale,
                exempt=False,
                exempt_reason=None,
            ))

    return RosterCutResult(
        roster_id=david_roster_id,
        total_players=total_players,
        active_slots=active_slots,
        total_capacity=total_capacity,
        cuts_required=cuts_required,
        reserve_unrestricted=reserve_unrestricted,
        cut_candidates=cut_candidates,
        exempt_players=exempt_players,
    )
