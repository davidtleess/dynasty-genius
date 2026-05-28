"""Subsystem 3 - whitelist & hard-block taxonomy contract tests (section 10.3)."""
from __future__ import annotations

from collections.abc import Mapping

from src.dynasty_genius.identity.college_prospect_identity import (
    CROSS_POSITION_THRESHOLD,
    POSITION_GROUP_HARD_BLOCKS,
    POSITION_GROUP_WHITELIST,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
    is_position_pair_hard_blocked,
    is_position_pair_whitelisted,
    normalize_name,
    surface_review_candidates,
)


def _row(
    name: str,
    position: str,
    position_group: str,
    school: str = "Ohio State",
    draft_class: int = 2027,
    sid: str = "incoming_001",
) -> NormalizedCollegeProspectRow:
    return NormalizedCollegeProspectRow.model_validate(
        {
            "raw_name": name,
            "normalized_name": normalize_name(name),
            "full_name": name,
            "position": position,
            "position_group": position_group,
            "draft_class": draft_class,
            "current_school": school,
            "prior_schools": [],
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
            "source": "manual_fixture",
            "source_record_id": sid,
            "source_snapshot_id": "fixture_2027_v1",
            "id_provenance": {
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
            },
            "notes": None,
        }
    )


def _entry(
    uuid: str,
    name: str,
    position: str,
    position_group: str,
    school: str = "Ohio State",
    draft_class: int = 2027,
) -> RegistryEntry:
    row = _row(
        name,
        position,
        position_group,
        school=school,
        draft_class=draft_class,
        sid=f"existing_{uuid}",
    )
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name=row.normalized_name,
            position_group=position_group,
            draft_class=draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status="confirmed",
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **row.model_dump(),
    )


def _hard_block_table() -> Mapping[str, frozenset[str]]:
    if callable(POSITION_GROUP_HARD_BLOCKS):
        return POSITION_GROUP_HARD_BLOCKS()
    return POSITION_GROUP_HARD_BLOCKS


def test_whitelist_pairs_match_spec():
    expected = frozenset(
        {frozenset({"WR", "TE"}), frozenset({"WR", "RB"}), frozenset({"FB", "RB"})}
    )
    assert POSITION_GROUP_WHITELIST == expected


def test_whitelist_is_direction_insensitive():
    assert is_position_pair_whitelisted("WR", "TE") is True
    assert is_position_pair_whitelisted("TE", "WR") is True
    assert is_position_pair_whitelisted("FB", "RB") is True
    assert is_position_pair_whitelisted("RB", "FB") is True


def test_qb_to_wr_hard_blocked_even_with_perfect_name_school_match():
    incoming = _row("Mike Williams", "QB", "QB", school="Clemson")
    existing = _entry("cpr_a", "Mike Williams", "WR", "WR", school="Clemson")
    candidates = surface_review_candidates(incoming, {existing.prospect_uuid: existing})
    assert candidates == [], "QB<->WR must hard-block regardless of name/school similarity"
    assert is_position_pair_hard_blocked("QB", "WR") is True
    assert "WR" in _hard_block_table()["QB"]


def test_ol_family_hard_blocked_against_anything():
    for ol_group in ["OL", "OT", "OG", "C"]:
        for skill in ["QB", "RB", "WR", "TE", "FB"]:
            assert is_position_pair_hard_blocked(ol_group, skill) is True
            assert is_position_pair_hard_blocked(skill, ol_group) is True


def test_special_teams_hard_blocked_against_anything():
    for special_teams in ["K", "P", "LS"]:
        for skill in ["QB", "RB", "WR", "TE", "FB", "OL"]:
            assert is_position_pair_hard_blocked(special_teams, skill) is True
            assert is_position_pair_hard_blocked(skill, special_teams) is True


def test_defense_to_offense_hard_blocked():
    defensive = ["DL", "DT", "DE", "EDGE", "OLB", "LB", "CB", "S", "DB"]
    offensive_skill = ["QB", "RB", "WR", "TE", "FB"]
    for defensive_group in defensive:
        for offensive_group in offensive_skill:
            assert is_position_pair_hard_blocked(defensive_group, offensive_group) is True
            assert is_position_pair_hard_blocked(offensive_group, defensive_group) is True


def test_whitelist_cross_group_surfaces_only_above_0_90():
    incoming = _row("Same Name", "TE", "TE", school="Same School")
    existing = _entry("cpr_a", "Same Name", "WR", "WR", school="Same School")
    candidates = surface_review_candidates(incoming, {existing.prospect_uuid: existing})
    assert candidates, "name+school identity should surface a cross-position TE<->WR candidate"
    top = candidates[0]
    assert top.match_score >= CROSS_POSITION_THRESHOLD
    assert "cross_position_group" in top.risk_flags
    assert "position_transition_allowed" in top.risk_flags


def test_whitelist_cross_group_below_0_90_is_suppressed():
    incoming = _row("Quintessential Name", "TE", "TE", school="Clemson")
    existing = _entry("cpr_a", "Different Wholly", "WR", "WR", school="Clemson")
    candidates = surface_review_candidates(incoming, {existing.prospect_uuid: existing})
    assert all(
        candidate.target_prospect_uuid != existing.prospect_uuid
        or candidate.match_score >= CROSS_POSITION_THRESHOLD
        for candidate in candidates
    )
