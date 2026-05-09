import re
from pathlib import Path

from src.dynasty_genius.identity import (
    CONFIDENCE_THRESHOLD,
    IdentityResolver,
    assign_collision_suffixes,
    compute_name_confidence,
    generate_dg_id,
)
from src.dynasty_genius.models.league_context import LeagueContext
from src.dynasty_genius.models.player_identity import PlayerIdentity


ROOT = Path(__file__).resolve().parents[1]


def _model_fields(model):
    if hasattr(model, "model_fields"):
        return model.model_fields
    return model.__fields__


def test_dg_id_normalizes_suffixes_and_common_given_name_aliases():
    assert generate_dg_id("Josh Allen Jr.", "QB", 1996) == "joshua_allen_qb_1996"
    assert generate_dg_id("Joshua Allen", "QB", 1996) == "joshua_allen_qb_1996"
    assert generate_dg_id("Mike Williams III", "WR", 1994) == "michael_williams_wr_1994"


def test_collision_suffixes_are_deterministic_and_human_readable():
    base_ids = [
        "michael_williams_wr_1994",
        "michael_williams_wr_1994",
        "joshua_allen_qb_1996",
        "michael_williams_wr_1994",
    ]

    assert assign_collision_suffixes(base_ids) == [
        "michael_williams_wr_1994",
        "michael_williams_wr_1994_2",
        "joshua_allen_qb_1996",
        "michael_williams_wr_1994_3",
    ]


def test_canonical_identity_models_exclude_market_overlay_fields():
    assert "ktc_id" not in _model_fields(PlayerIdentity)
    assert "preferred_market_source" not in _model_fields(LeagueContext)


def test_identity_layer_has_no_market_join_anchors():
    banned = re.compile(
        r"\b(ktc|keeptradecut|adp|fantasypros|dynastynerds|market_value|market_rank)\b",
        re.IGNORECASE,
    )
    identity_files = [
        ROOT / "src/dynasty_genius/identity.py",
        ROOT / "src/dynasty_genius/models/player_identity.py",
        ROOT / "resources/sql/create_player_identity.sql",
    ]

    offenders = []
    for path in identity_files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if banned.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")

    assert offenders == []

    pipeline_text = (ROOT / "src/dynasty_genius/pipelines/identity.py").read_text(
        encoding="utf-8"
    )
    assert "MARKET_DERIVED_COLUMNS" in pipeline_text
    assert re.search(r"\.select\([^)]*(ktc|adp|market)", pipeline_text, re.IGNORECASE) is None
    assert re.search(r"\.join\([^)]*(ktc|adp|market)", pipeline_text, re.IGNORECASE) is None


def test_fuzzy_name_confidence_routes_uncertain_aliases_to_conflict():
    assert CONFIDENCE_THRESHOLD == 0.95
    assert compute_name_confidence("Amon Ra St Brown", "Amon-Ra St. Brown") == 1.0
    assert compute_name_confidence("Luther Burden", "Luther Burden III") == 1.0
    assert compute_name_confidence("Tony Richardson", "Anthony Richardson") < CONFIDENCE_THRESHOLD
    assert compute_name_confidence("C. McCaffrey", "Christian McCaffrey") < CONFIDENCE_THRESHOLD


def test_identity_resolver_exact_ids_and_name_conflicts():
    identities = [
        PlayerIdentity(
            dg_id="anthony_richardson_qb_2002",
            full_name="Anthony Richardson",
            position="QB",
            nfl_team="IND",
            jersey_number="5",
            sleeper_id="sleeper_ar",
            pff_id="pff_ar",
        ),
        PlayerIdentity(
            dg_id="christian_mccaffrey_rb_1996",
            full_name="Christian McCaffrey",
            position="RB",
            nfl_team="SF",
            jersey_number="23",
            sleeper_id="sleeper_cmc",
            pff_id="pff_cmc",
        ),
    ]
    resolver = IdentityResolver(identities)

    assert resolver.resolve_sleeper_id("sleeper_ar") == "anthony_richardson_qb_2002"
    assert resolver.resolve_pff_id("pff_cmc") == "christian_mccaffrey_rb_1996"

    result = resolver.resolve_by_name("Tony Richardson", "QB")
    assert result is not None
    assert result.candidate_dg_id == "anthony_richardson_qb_2002"
    assert result.verification_status == "CONFLICT"

    result = resolver.resolve_by_name("Tony Richardson", "QB", team="IND", jersey_number="5")
    assert result is not None
    assert result.candidate_dg_id == "anthony_richardson_qb_2002"
    assert result.verification_status == "VERIFIED"
    assert result.verification_basis == "team_jersey"

    result = resolver.resolve_by_name("C. McCaffrey", "RB", team="SF")
    assert result is not None
    assert result.candidate_dg_id == "christian_mccaffrey_rb_1996"
    assert result.verification_status == "CONFLICT"
    assert result.verification_basis == "team_needs_jersey"


def test_team_plus_jersey_verifies_cam_cameron_conflict():
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

    result = resolver.resolve_by_name("Cam Thomas", "TE", team="KC", jersey_number="88")
    assert result is not None
    assert result.candidate_dg_id == "cameron_thomas_te_2004"
    assert result.verification_status == "VERIFIED"
    assert result.verification_basis == "team_jersey"
