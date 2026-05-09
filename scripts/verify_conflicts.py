import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dynasty_genius.identity import (
    CONFIDENCE_THRESHOLD,
    IdentityResolver,
    compute_name_confidence,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity


def flag_identity_conflicts(source_player: dict, candidate_player: dict) -> str:
    """Evaluate two player records for potential identity conflicts.

    Returns 'VERIFIED', 'CONFLICT', or 'PENDING'.
    Wrapper kept here so the verification script doesn't need to change its call sites.
    """
    name_score = compute_name_confidence(source_player["full_name"], candidate_player["full_name"])
    if name_score >= CONFIDENCE_THRESHOLD:
        src_year = source_player.get("birth_year")
        cand_year = candidate_player.get("birth_year")
        if src_year and cand_year and src_year != cand_year:
            return "CONFLICT"
        return "VERIFIED"
    if name_score >= 0.85:
        return "PENDING"
    return "CONFLICT"


def verify_conflicts() -> None:
    """Run assertion-based identity conflict checks for local/manual verification."""
    assert flag_identity_conflicts(
        {"full_name": "Josh Allen", "birth_year": 1996},
        {"full_name": "Joshua Allen", "birth_year": 1996},
    ) == "VERIFIED"

    assert flag_identity_conflicts(
        {"full_name": "Josh Allen", "birth_year": 1996},
        {"full_name": "Josh Allen", "birth_year": 1997},
    ) == "CONFLICT"

    assert flag_identity_conflicts(
        {"full_name": "Christopher Olave", "birth_year": 2000},
        {"full_name": "Chris Olave", "birth_year": 2000},
    ) == "VERIFIED"

    assert compute_name_confidence("Tony Richardson", "Anthony Richardson") < CONFIDENCE_THRESHOLD

    resolver = IdentityResolver(
        [
            PlayerIdentity(
                dg_id="cameron_thomas_te_2004",
                full_name="Cameron Thomas",
                position="TE",
                nfl_team="KC",
                jersey_number="88",
            )
        ]
    )
    team_resolved = resolver.resolve_by_name("Cam Thomas", "TE", team="KC")
    assert team_resolved is not None
    assert team_resolved.verification_status == "VERIFIED"
    assert team_resolved.verification_basis == "team"

    resolved = resolver.resolve_by_name("Cam Thomas", "TE", team="KC", jersey_number="88")
    assert resolved is not None
    assert resolved.verification_status == "VERIFIED"
    assert resolved.verification_basis == "team_jersey"

    weak_alias_resolver = IdentityResolver(
        [
            PlayerIdentity(
                dg_id="christian_mccaffrey_rb_1996",
                full_name="Christian McCaffrey",
                position="RB",
                nfl_team="SF",
                jersey_number="23",
            )
        ]
    )
    unresolved = weak_alias_resolver.resolve_by_name("C. McCaffrey", "RB", team="SF")
    assert unresolved is not None
    assert unresolved.verification_status == "CONFLICT"
    assert unresolved.verification_basis == "team_needs_jersey"

    print("identity conflict verification passed")


def test_conflicts():
    verify_conflicts()


if __name__ == "__main__":
    verify_conflicts()
