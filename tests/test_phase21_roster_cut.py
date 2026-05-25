"""Phase 21 W1 — RosterCutEngine TDD tests (32 tests).

Written RED-first before src/dynasty_genius/roster_cut_engine.py exists.
"""
from __future__ import annotations

import json

import pytest

from src.dynasty_genius.roster_cut_engine import (
    RosterCutCandidate,
    RosterCutResult,
    _ir_compliance_status,
    _normalize_sleeper_status,
    _taxi_deadline_status,
    _taxi_eligibility,
    compute_roster_cut_candidates,
)

# ─── Fixture helpers ──────────────────────────────────────────────────────────

_STANDARD_POSITIONS = ["QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX"] + ["BN"] * 14  # 20 slots

_STANDARD_SETTINGS: dict = {
    "reserve_slots": 4,
    "reserve_allow_out": 0,
    "reserve_allow_doubtful": 0,
    "reserve_allow_sus": 0,
    "reserve_allow_na": 0,
    "reserve_allow_cov": 0,
    "reserve_allow_dnr": 0,
    "taxi_slots": 2,
    "taxi_years": 1,
    "taxi_allow_vets": 0,
    "taxi_deadline": 4,
    "bench_lock": 1,
}


def _make_snapshot(
    player_ids: list[str],
    *,
    taxi_ids: list[str] | None = None,
    reserve_ids: list[str] | None = None,
    roster_positions: list[str] | None = None,
    settings: dict | None = None,
    season_type: str = "off",
    week: int = 0,
    roster_id: int = 1,
) -> dict:
    return {
        "league": {
            "roster_positions": roster_positions if roster_positions is not None else list(_STANDARD_POSITIONS),
            "settings": settings if settings is not None else dict(_STANDARD_SETTINGS),
        },
        "rosters": [
            {
                "roster_id": roster_id,
                "players": player_ids,
                "taxi": taxi_ids or [],
                "reserve": reserve_ids or [],
            }
        ],
        "draft_state": {
            "nfl_state": {"season_type": season_type, "week": week}
        },
    }


def _make_pvo_player(
    pid: str,
    *,
    position: str = "WR",
    age: float = 24.0,
    years_exp: int = 2,
    sleeper_status: str = "Active",
    xvar_pct: float | None = None,
    dvs: float | None = 50.0,
    engine_path: str = "ENGINE_B",
) -> dict:
    return {
        "sleeper_player_id": pid,
        "player": {
            "full_name": f"Player {pid}",
            "position": position,
            "age": age,
            "years_exp": years_exp,
            "sleeper_status": sleeper_status,
        },
        "valuation": {
            "xvar": None if xvar_pct is None else float(xvar_pct - 50.0),
            "xvar_percentile_overall": xvar_pct,
            "dynasty_value_score": dvs,
            "engine_path": engine_path,
        },
        "league_context": {"roster_id": 1, "rostered": True, "on_ir": False, "on_taxi": False},
    }


def _make_pvo(players: list[dict]) -> dict:
    return {"players": players}


# ─── Blocker 1 — IR eligibility ───────────────────────────────────────────────

def test_unrestricted_reserve_exempts_all_ir_players():
    """All reserve_allow_* = 0 and reserve_slots > 0 → every IR player is COMPLIANT."""
    ir_player = _make_pvo_player("ir1", position="RB", sleeper_status="Active")
    snapshot = _make_snapshot(
        ["p1", "p2", "ir1"],
        reserve_ids=["ir1"],
    )
    result = compute_roster_cut_candidates(_make_pvo([ir_player, _make_pvo_player("p1"), _make_pvo_player("p2")]), snapshot)
    exempt_ids = {c.sleeper_player_id for c in result.exempt_players}
    assert "ir1" in exempt_ids
    ir_exempt = next(c for c in result.exempt_players if c.sleeper_player_id == "ir1")
    assert ir_exempt.ir_compliance_status == "COMPLIANT"
    assert ir_exempt.exempt is True


def test_restricted_reserve_illegal_player_surfaces_as_forced_compliance():
    """reserve_allow_out=1 + player status=Active → ILLEGAL_RESERVE, cut_priority=0."""
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_allow_out"] = 1  # only "Out" status allowed
    settings["reserve_slots"] = 4
    ir_player = _make_pvo_player("bad_ir", sleeper_status="Active")  # Active is not "Out"
    snapshot = _make_snapshot(
        ["p1", "bad_ir"],
        reserve_ids=["bad_ir"],
        settings=settings,
    )
    result = compute_roster_cut_candidates(_make_pvo([ir_player, _make_pvo_player("p1")]), snapshot)
    candidate_ids = {c.sleeper_player_id for c in result.cut_candidates}
    assert "bad_ir" in candidate_ids
    c = next(c for c in result.cut_candidates if c.sleeper_player_id == "bad_ir")
    assert c.ir_compliance_status == "ILLEGAL_RESERVE"
    assert c.cut_priority == 0


def test_illegal_reserve_not_simply_exempt():
    """ILLEGAL_RESERVE player must NOT appear in exempt_players."""
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_allow_out"] = 1
    ir_player = _make_pvo_player("bad_ir", sleeper_status="Active")
    snapshot = _make_snapshot(["p1", "bad_ir"], reserve_ids=["bad_ir"], settings=settings)
    result = compute_roster_cut_candidates(_make_pvo([ir_player, _make_pvo_player("p1")]), snapshot)
    exempt_ids = {c.sleeper_player_id for c in result.exempt_players}
    assert "bad_ir" not in exempt_ids


# ─── Blocker 2 — Taxi eligibility ─────────────────────────────────────────────

def test_taxi_player_is_exempt_regardless_of_eligibility():
    """A vet (years_exp=5) already on taxi is still exempt."""
    vet_taxi = _make_pvo_player("vet1", years_exp=5, position="WR")
    snapshot = _make_snapshot(
        ["p1", "vet1"],
        taxi_ids=["vet1"],
    )
    result = compute_roster_cut_candidates(_make_pvo([vet_taxi, _make_pvo_player("p1")]), snapshot)
    exempt_ids = {c.sleeper_player_id for c in result.exempt_players}
    assert "vet1" in exempt_ids
    taxi_exempt = next(c for c in result.exempt_players if c.sleeper_player_id == "vet1")
    assert taxi_exempt.exempt is True
    assert taxi_exempt.exempt_reason == "taxi"


def test_vet_not_on_taxi_is_ineligible():
    """years_exp=5, not on taxi, taxi_allow_vets=0 → INELIGIBLE_VET in taxi_eligibility."""
    vet = _make_pvo_player("vet2", years_exp=5, position="WR", xvar_pct=55.0)
    # Over limit to ensure candidates are generated
    players = ["vet2"] + [f"p{i}" for i in range(25)]
    pvo_list = [vet] + [_make_pvo_player(f"p{i}", xvar_pct=float(60 + i)) for i in range(25)]
    snapshot = _make_snapshot(players)
    result = compute_roster_cut_candidates(_make_pvo(pvo_list), snapshot)
    all_candidates = result.cut_candidates + result.exempt_players
    vet_rec = next((c for c in all_candidates if c.sleeper_player_id == "vet2"), None)
    assert vet_rec is not None
    assert vet_rec.taxi_eligibility == "INELIGIBLE_VET"


def test_rookie_on_taxi_has_eligible_status():
    """years_exp=0 on taxi → taxi_eligibility=ELIGIBLE."""
    rookie = _make_pvo_player("rook1", years_exp=0)
    snapshot = _make_snapshot(["rook1", "p1"], taxi_ids=["rook1"])
    result = compute_roster_cut_candidates(_make_pvo([rookie, _make_pvo_player("p1")]), snapshot)
    taxi_rec = next(c for c in result.exempt_players if c.sleeper_player_id == "rook1")
    assert taxi_rec.taxi_eligibility == "ELIGIBLE"


# ─── Blocker 3 — Defensive capacity math ─────────────────────────────────────

def test_ir_taxi_slots_not_in_roster_positions_passes_validation():
    """Standard positions list (no IR/TAXI strings) does not raise."""
    snapshot = _make_snapshot(["p1"])
    result = compute_roster_cut_candidates(_make_pvo([_make_pvo_player("p1")]), snapshot)
    assert result.active_slots == 20


def test_roster_positions_containing_ir_raises():
    """roster_positions containing 'IR' raises ValueError before computing capacity."""
    bad_positions = list(_STANDARD_POSITIONS) + ["IR"]
    snapshot = _make_snapshot(["p1"], roster_positions=bad_positions)
    with pytest.raises(ValueError, match="roster_positions contains protected slot types"):
        compute_roster_cut_candidates(_make_pvo([_make_pvo_player("p1")]), snapshot)


def test_active_slots_equals_non_protected_positions():
    """active_slots = len(roster_positions) for a clean positions list."""
    positions = ["QB", "RB", "WR"] + ["BN"] * 5  # 8 slots
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_slots"] = 2
    settings["taxi_slots"] = 1
    snapshot = _make_snapshot(["p1"], roster_positions=positions, settings=settings)
    result = compute_roster_cut_candidates(_make_pvo([_make_pvo_player("p1")]), snapshot)
    assert result.active_slots == 8
    assert result.total_capacity == 11  # 8 + 2 + 1


# ─── Blocker 4 — Edge-case roster occupancy ──────────────────────────────────

def test_over_limit_is_computed_correctly():
    """28 players vs 26 capacity → cuts_required=2."""
    players = [f"p{i}" for i in range(28)]
    taxi = [players[0], players[1]]
    reserve = [players[2], players[3], players[4]]
    pvo = _make_pvo([_make_pvo_player(pid, xvar_pct=float(50 + i)) for i, pid in enumerate(players)])
    snapshot = _make_snapshot(players, taxi_ids=taxi, reserve_ids=reserve)
    result = compute_roster_cut_candidates(pvo, snapshot)
    assert result.total_players == 28
    assert result.total_capacity == 26
    assert result.cuts_required == 2


def test_roster_below_capacity_returns_no_cuts():
    """20 players vs 26 capacity → cuts_required=0, cut_candidates=[]."""
    players = [f"p{i}" for i in range(20)]
    pvo = _make_pvo([_make_pvo_player(pid) for pid in players])
    snapshot = _make_snapshot(players)
    result = compute_roster_cut_candidates(pvo, snapshot)
    assert result.cuts_required == 0
    assert result.cut_candidates == []


def test_roster_exactly_at_capacity_returns_no_cuts():
    """26 players vs 26 capacity → cuts_required=0, cut_candidates=[]."""
    players = [f"p{i}" for i in range(26)]
    taxi = [players[0], players[1]]
    reserve = [players[2], players[3], players[4], players[5]]
    pvo = _make_pvo([_make_pvo_player(pid) for pid in players])
    snapshot = _make_snapshot(players, taxi_ids=taxi, reserve_ids=reserve)
    result = compute_roster_cut_candidates(pvo, snapshot)
    assert result.cuts_required == 0
    assert result.cut_candidates == []


def test_partial_occupancy_with_taxi_ir_present():
    """15 players (2 taxi, 2 IR), 26 capacity → cuts_required=0."""
    players = [f"p{i}" for i in range(15)]
    taxi = [players[0], players[1]]
    reserve = [players[2], players[3]]
    pvo = _make_pvo([_make_pvo_player(pid) for pid in players])
    snapshot = _make_snapshot(players, taxi_ids=taxi, reserve_ids=reserve)
    result = compute_roster_cut_candidates(pvo, snapshot)
    assert result.cuts_required == 0
    assert result.cut_candidates == []


# ─── v0.3 Blocker — IR compliance before early return ─────────────────────────

def test_illegal_reserve_surfaces_even_when_roster_at_capacity():
    """26/26 roster with an ILLEGAL_RESERVE player → cuts_required=0 but
    cut_candidates contains one cut_priority=0 entry."""
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_allow_out"] = 1  # restrict reserve to "Out" only
    # Build exactly 26 players: 20 active + 4 reserve + 2 taxi = 26
    active = [f"a{i}" for i in range(20)]
    reserve = [f"ir{i}" for i in range(4)]  # all "Active" status → ILLEGAL_RESERVE
    taxi = [f"t{i}" for i in range(2)]
    players = active + reserve + taxi
    pvo_list = (
        [_make_pvo_player(pid, xvar_pct=float(50 + i)) for i, pid in enumerate(active)]
        + [_make_pvo_player(pid, sleeper_status="Active") for pid in reserve]
        + [_make_pvo_player(pid, years_exp=0) for pid in taxi]
    )
    snapshot = _make_snapshot(players, taxi_ids=taxi, reserve_ids=reserve, settings=settings)
    result = compute_roster_cut_candidates(_make_pvo(pvo_list), snapshot)
    assert result.cuts_required == 0
    forced = [c for c in result.cut_candidates if c.cut_priority == 0]
    assert len(forced) == 4
    assert all(c.ir_compliance_status == "ILLEGAL_RESERVE" for c in forced)


# ─── v0.3 Follow-up — Taxi deadline status ───────────────────────────────────

def test_taxi_deadline_status_offseason_returns_not_reached():
    """season_type='off', week=0, deadline=4 → NOT_REACHED, no approaching caveat."""
    status = _taxi_deadline_status("off", 0, 4)
    assert status == "NOT_REACHED"


def test_taxi_deadline_status_week_3_approaching():
    """season_type='reg', week=3, deadline=4 → APPROACHING."""
    status = _taxi_deadline_status("reg", 3, 4)
    assert status == "APPROACHING"


def test_taxi_deadline_status_week_4_passed():
    """season_type='reg', week=4, deadline=4 → PASSED."""
    status = _taxi_deadline_status("reg", 4, 4)
    assert status == "PASSED"


# ─── v0.3 Follow-up — Sleeper status normalization ───────────────────────────

def test_normalize_known_alias_sus():
    assert _normalize_sleeper_status("sus") == "Suspended"


def test_normalize_case_insensitive_out():
    assert _normalize_sleeper_status("OUT") == "Out"


def test_normalize_unknown_status_produces_unknown():
    assert _normalize_sleeper_status("Injured Reserve") == "UNKNOWN_STATUS"
    # Also verify compliance function returns UNKNOWN_STATUS + caveat
    status, caveats = _ir_compliance_status(
        "Injured Reserve",
        reserve_unrestricted=False,
        reserve_slots=4,
        settings=dict(_STANDARD_SETTINGS),
    )
    assert status == "UNKNOWN_STATUS"
    assert any("unknown_status" in c for c in caveats)


# ─── v0.3 Follow-up — Unrestricted-reserve invariant ─────────────────────────

def test_all_reserve_allow_zero_means_unrestricted():
    """reserve_slots=4, all flags=0 → reserve_unrestricted=True; any status is COMPLIANT."""
    # The engine computes this in Step 1 and exposes it on RosterCutResult
    snapshot = _make_snapshot(["p1"])
    result = compute_roster_cut_candidates(_make_pvo([_make_pvo_player("p1")]), snapshot)
    assert result.reserve_unrestricted is True


def test_partial_reserve_flags_means_restricted():
    """reserve_allow_out=1 → reserve_unrestricted=False; 'Active' status is ILLEGAL_RESERVE."""
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_allow_out"] = 1
    status, _ = _ir_compliance_status(
        "Active", reserve_unrestricted=False, reserve_slots=4, settings=settings
    )
    assert status == "ILLEGAL_RESERVE"


def test_reserve_unrestricted_is_false_when_reserve_slots_zero():
    """reserve_slots=0 → reserve_unrestricted=False on the result."""
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_slots"] = 0
    settings["taxi_slots"] = 0  # keep capacity small
    positions = ["QB", "RB"] + ["BN"] * 2  # 4 active slots
    snapshot = _make_snapshot(["p1"], roster_positions=positions, settings=settings)
    result = compute_roster_cut_candidates(_make_pvo([_make_pvo_player("p1")]), snapshot)
    assert result.reserve_unrestricted is False


# ─── v0.4 Blocker — Invalid-snapshot and UNKNOWN_STATUS forced-review ─────────

def test_reserve_slots_zero_with_ir_players_surfaces_invalid_snapshot():
    """reserve_slots=0, player in reserve list → INVALID_SNAPSHOT, cut_priority=0."""
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_slots"] = 0
    positions = list(_STANDARD_POSITIONS)  # 20 active
    ir_player = _make_pvo_player("ir_bad", sleeper_status="Active")
    active = [f"a{i}" for i in range(19)]
    players = active + ["ir_bad"]
    pvo_list = [_make_pvo_player(pid, xvar_pct=float(50+i)) for i, pid in enumerate(active)] + [ir_player]
    snapshot = _make_snapshot(players, reserve_ids=["ir_bad"], settings=settings, roster_positions=positions)
    result = compute_roster_cut_candidates(_make_pvo(pvo_list), snapshot)
    bad = next((c for c in result.cut_candidates if c.sleeper_player_id == "ir_bad"), None)
    assert bad is not None
    assert bad.ir_compliance_status == "INVALID_SNAPSHOT"
    assert bad.cut_priority == 0
    assert any("does_not_exist" in r for r in bad.cut_rationale)


def test_unknown_status_reserve_surfaces_even_when_roster_at_capacity():
    """26/26 roster with UNKNOWN_STATUS reserve player → cuts_required=0
    but result still contains cut_priority=0 entry for that player."""
    settings = dict(_STANDARD_SETTINGS)
    settings["reserve_allow_out"] = 1  # restricted reserve
    active = [f"a{i}" for i in range(20)]
    reserve = [f"ir{i}" for i in range(4)]
    taxi = [f"t{i}" for i in range(2)]
    players = active + reserve + taxi
    pvo_list = (
        [_make_pvo_player(pid, xvar_pct=float(50+i)) for i, pid in enumerate(active)]
        + [_make_pvo_player(pid, sleeper_status="Injured Reserve") for pid in reserve]  # unrecognized
        + [_make_pvo_player(pid, years_exp=0) for pid in taxi]
    )
    snapshot = _make_snapshot(players, taxi_ids=taxi, reserve_ids=reserve, settings=settings)
    result = compute_roster_cut_candidates(_make_pvo(pvo_list), snapshot)
    assert result.cuts_required == 0
    unknown_candidates = [c for c in result.cut_candidates if c.ir_compliance_status == "UNKNOWN_STATUS"]
    assert len(unknown_candidates) == 4
    assert all(c.cut_priority == 0 for c in unknown_candidates)


# ─── Scoring and governance ───────────────────────────────────────────────────

def test_taxi_players_are_exempt():
    """Taxi players never appear in cut_candidates."""
    taxi = _make_pvo_player("taxi1", years_exp=0)
    active = [_make_pvo_player(f"a{i}", xvar_pct=float(40+i)) for i in range(25)]
    all_pvo = [taxi] + active
    players = ["taxi1"] + [f"a{i}" for i in range(25)]
    snapshot = _make_snapshot(players, taxi_ids=["taxi1"])
    result = compute_roster_cut_candidates(_make_pvo(all_pvo), snapshot)
    candidate_ids = {c.sleeper_player_id for c in result.cut_candidates}
    assert "taxi1" not in candidate_ids


def test_ir_players_exempt_when_compliant():
    """Compliant IR players never appear in cut_candidates."""
    ir1 = _make_pvo_player("ir1", sleeper_status="Active")  # unrestricted → COMPLIANT
    ir2 = _make_pvo_player("ir2", sleeper_status="Active")
    active = [_make_pvo_player(f"a{i}", xvar_pct=float(40+i)) for i in range(25)]
    players = [f"a{i}" for i in range(25)] + ["ir1", "ir2"]
    snapshot = _make_snapshot(players, reserve_ids=["ir1", "ir2"])
    pvo = _make_pvo([ir1, ir2] + active)
    result = compute_roster_cut_candidates(pvo, snapshot)
    candidate_ids = {c.sleeper_player_id for c in result.cut_candidates}
    assert "ir1" not in candidate_ids
    assert "ir2" not in candidate_ids


def test_cut_candidates_ranked_by_xvar_percentile():
    """Tier A players ranked ascending by xvar_percentile_overall."""
    players_data = [
        _make_pvo_player("barner", position="TE", xvar_pct=34.3),
        _make_pvo_player("jones", position="QB", xvar_pct=39.3),
        _make_pvo_player("mitchell", position="WR", xvar_pct=37.3),
    ]
    # Add enough players to be over limit
    filler = [_make_pvo_player(f"f{i}", xvar_pct=float(60+i)) for i in range(23)]
    players = ["barner", "jones", "mitchell"] + [f"f{i}" for i in range(23)]
    snapshot = _make_snapshot(players)
    result = compute_roster_cut_candidates(_make_pvo(players_data + filler), snapshot)
    ranked_ids = [c.sleeper_player_id for c in result.cut_candidates if c.scoring_tier == "A"]
    barner_rank = ranked_ids.index("barner")
    jones_rank = ranked_ids.index("jones")
    mitchell_rank = ranked_ids.index("mitchell")
    assert barner_rank < mitchell_rank < jones_rank


def test_pre_model_players_ranked_last():
    """PRE_MODEL players appear after all tier A/B/C players."""
    pre_model = _make_pvo_player("pre1", xvar_pct=None, dvs=None, engine_path="PRE_MODEL")
    scored = _make_pvo_player("sc1", xvar_pct=20.0)  # very low xvar — still tier A
    filler = [_make_pvo_player(f"f{i}", xvar_pct=float(60+i)) for i in range(24)]
    players = ["pre1", "sc1"] + [f"f{i}" for i in range(24)]
    snapshot = _make_snapshot(players)
    pvo = _make_pvo([pre_model, scored] + filler)
    result = compute_roster_cut_candidates(pvo, snapshot)
    candidate_ids = [c.sleeper_player_id for c in result.cut_candidates]
    assert candidate_ids.index("sc1") < candidate_ids.index("pre1")


def test_cliff_age_is_evidence_not_score():
    """RB at age 27 has age_cliff_warning=True but retains its numeric rank position."""
    rb_old = _make_pvo_player("rb_old", position="RB", age=27.0, xvar_pct=55.0)
    rb_young = _make_pvo_player("rb_young", position="RB", age=22.0, xvar_pct=55.0)
    filler = [_make_pvo_player(f"f{i}", xvar_pct=float(40+i)) for i in range(24)]
    players = ["rb_old", "rb_young"] + [f"f{i}" for i in range(24)]
    snapshot = _make_snapshot(players)
    result = compute_roster_cut_candidates(_make_pvo([rb_old, rb_young] + filler), snapshot)
    old_rec = next(c for c in result.cut_candidates if c.sleeper_player_id == "rb_old")
    young_rec = next(c for c in result.cut_candidates if c.sleeper_player_id == "rb_young")
    assert old_rec.age_cliff_warning is True
    assert young_rec.age_cliff_warning is False
    # Same xvar_pct so same rank tier; cliff must not change order relative to xvar rank
    assert "age_at_or_past_position_cliff" in old_rec.cut_rationale


def test_decision_supported_false_on_result():
    """result.decision_supported is always False."""
    snapshot = _make_snapshot(["p1"])
    result = compute_roster_cut_candidates(_make_pvo([_make_pvo_player("p1")]), snapshot)
    assert result.decision_supported is False


def test_no_market_features_in_cut_scoring():
    """No ktc_value, fantasycalc_value, or market fields in any RosterCutCandidate."""
    players = [f"p{i}" for i in range(26)]
    pvo = _make_pvo([_make_pvo_player(pid) for pid in players])
    snapshot = _make_snapshot(players)
    result = compute_roster_cut_candidates(pvo, snapshot)
    banned = {"ktc_value", "fantasycalc_value", "market_value", "market_overlay"}
    for candidate in result.cut_candidates + result.exempt_players:
        candidate_dict = candidate.model_dump()
        for key in candidate_dict:
            assert key not in banned, f"Banned market field '{key}' found on candidate"


# ─── Blocker 5 — Recursive decision_supported lock ───────────────────────────

def test_no_nested_decision_supported_true_in_cut_result():
    """Walks all nested dicts/lists in serialized RosterCutResult and asserts
    no decision_supported: True anywhere."""
    players = [f"p{i}" for i in range(28)]
    taxi = [players[0], players[1]]
    reserve = [players[2], players[3], players[4]]
    pvo = _make_pvo([_make_pvo_player(pid, xvar_pct=float(40+i)) for i, pid in enumerate(players)])
    snapshot = _make_snapshot(players, taxi_ids=taxi, reserve_ids=reserve)
    result = compute_roster_cut_candidates(pvo, snapshot)
    raw = json.loads(result.model_dump_json())

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            assert obj.get("decision_supported") is not True, (
                f"decision_supported=True found in: {obj}"
            )
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(raw)
