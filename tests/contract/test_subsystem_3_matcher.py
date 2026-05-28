"""Subsystem 3 - matcher contract tests (section 10.2)."""
from __future__ import annotations

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    LOW_CONFIDENCE_LOWER,
    LOW_CONFIDENCE_UPPER,
    MATCHER_ALGORITHM_VERSION,
    MIN_CANDIDATE_SCORE,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
    normalize_name,
    score_candidate,
    surface_review_candidates,
)


def _row(
    name: str,
    position: str = "WR",
    position_group: str = "WR",
    draft_class: int = 2027,
    school: str = "Ohio State",
    prior: list[str] | None = None,
    source_record_id: str = "fixture_2027_001",
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
            "prior_schools": prior or [],
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
            "source": "manual_fixture",
            "source_record_id": source_record_id,
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


def _registry_entry(
    uuid: str,
    name: str,
    position: str = "WR",
    position_group: str = "WR",
    draft_class: int = 2027,
    school: str = "Ohio State",
    status: str = "confirmed",
    prior: list[str] | None = None,
    source_record_id: str = "fixture_2027_existing",
) -> RegistryEntry:
    row = _row(
        name=name,
        position=position,
        position_group=position_group,
        draft_class=draft_class,
        school=school,
        prior=prior,
        source_record_id=source_record_id,
    )
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,  # type: ignore[arg-type]
        match_key=compute_match_key(
            normalized_name=row.normalized_name,
            position_group=row.position_group,
            draft_class=row.draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status=status,  # type: ignore[arg-type]
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **row.model_dump(),
    )


def test_normalize_name_matches_existing_sleeper_side_resolver_exactly():
    """Spec section 5.1: identical to prospect_identity_resolver.normalize_name."""
    from src.dynasty_genius.adapters.prospect_identity_resolver import (
        normalize_name as legacy_normalize,
    )

    samples = [
        "Arch Manning",
        "Marvin Harrison Jr.",
        "A.J. Brown",
        "  Spaces   Galore  ",
        "Hyphen-Name O'Reilly",
    ]
    for sample in samples:
        assert normalize_name(sample) == legacy_normalize(sample)


def test_blend_is_075_jw_plus_025_token_set_not_max():
    incoming = _row("Mike Williams Jr", school="Tulane")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Williams Mike",
        school="Tulane",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.score_breakdown["name_base"] == pytest.approx(
        0.75 * candidate.score_breakdown["jw_score"]
        + 0.25 * candidate.score_breakdown["token_set_score"]
    )
    assert candidate.score_breakdown["name_base"] < max(
        candidate.score_breakdown["jw_score"],
        candidate.score_breakdown["token_set_score"],
    )


def test_position_group_bonus_adds_0_10_and_school_bonus_adds_0_05_and_total_clamps_to_1():
    incoming = _row("Identical Name", school="Same School")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Identical Name",
        school="Same School",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.score_breakdown["position_bonus"] == pytest.approx(0.10)
    assert candidate.score_breakdown["school_bonus"] == pytest.approx(0.05)
    assert 0.0 <= candidate.match_score <= 1.0
    assert candidate.match_score == pytest.approx(1.0)


def test_draft_class_mismatch_is_hard_zero():
    incoming = _row("Same Name", draft_class=2027, school="Same School")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Same Name",
        draft_class=2026,
        school="Same School",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.match_score == 0.0
    assert "class_boundary_blocked" in candidate.risk_flags


def test_top_3_above_0_80_only():
    incoming = _row("Target Name", school="Texas")
    registry = {
        "cpr_a": _registry_entry("cpr_a", "Target Name", school="Texas"),
        "cpr_b": _registry_entry("cpr_b", "Target Naam", school="Texas"),
        "cpr_c": _registry_entry("cpr_c", "Targat Naym", school="Texas"),
        "cpr_d": _registry_entry("cpr_d", "Different Person", school="Texas"),
        "cpr_e": _registry_entry("cpr_e", "Yet Another", school="Texas"),
    }
    candidates = surface_review_candidates(incoming, registry)
    assert len(candidates) == 3
    assert all(candidate.match_score >= MIN_CANDIDATE_SCORE for candidate in candidates)
    assert (
        candidates[0].match_score
        >= candidates[1].match_score
        >= candidates[2].match_score
    )


def test_low_confidence_band_emits_flag_in_0_80_to_0_88():
    incoming = _row("Borderline Name", school="Texas")
    registry = {
        "cpr_a": _registry_entry("cpr_a", "Bdrline Person", school="Bama"),
    }
    candidates = surface_review_candidates(incoming, registry)
    assert candidates, "expected one borderline candidate"
    top = candidates[0]
    assert LOW_CONFIDENCE_LOWER <= top.match_score < LOW_CONFIDENCE_UPPER
    assert "low_confidence" in top.risk_flags


def test_ambiguous_near_tie_when_top_two_within_0_05():
    incoming = _row("Common Name", school="Texas")
    registry = {
        "cpr_a": _registry_entry("cpr_a", "Common Name", school="Texas"),
        "cpr_b": _registry_entry("cpr_b", "Comman Name", school="Texas"),
    }
    candidates = surface_review_candidates(incoming, registry)
    assert len(candidates) >= 2
    margin = candidates[0].match_score - candidates[1].match_score
    assert margin <= 0.05
    assert "ambiguous_near_tie" in candidates[0].risk_flags
    assert "common_name" in candidates[0].risk_flags


def test_raw_match_features_captured_at_match_time():
    incoming = _row("Pinned Name", school="Pinned School")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Pinned Name",
        school="Pinned School",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.raw_match_features["prospect_name"] == "Pinned Name"
    assert candidate.raw_match_features["school"] == "Pinned School"
    assert candidate.raw_match_features["draft_class"] == 2027


def test_matcher_algorithm_version_pinned_on_every_candidate():
    incoming = _row("Some Name")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Some Name",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.matcher_algorithm_version == MATCHER_ALGORITHM_VERSION


def test_class_agnostic_2026_and_2028_behave_identically():
    incoming_2026 = _row("Class Test", draft_class=2026)
    incoming_2028 = _row("Class Test", draft_class=2028)
    existing_2026 = _registry_entry("cpr_a", "Class Test", draft_class=2026)
    existing_2028 = _registry_entry("cpr_b", "Class Test", draft_class=2028)
    score_2026 = score_candidate(incoming_2026, existing_2026)
    score_2028 = score_candidate(incoming_2028, existing_2028)
    assert score_2026.match_score == score_2028.match_score
