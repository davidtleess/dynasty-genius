"""DG-179's shared league-season outcome artifact (schema dg179_league_season_outcomes_v1), read
by DG-178 exactly as Codex implemented it (2026-09-06 evening): one global artifact shared by
both producers, its CSV bytes and manifest hashed and compared, its coverage status read as a
RESEARCH qualification (admitted game ids match the source and the unattributed-row quarantine
is disclosed) — never converted into 'complete individual data'."""
from __future__ import annotations

import hashlib
import json

import pytest

from src.dynasty_genius.ranking.outcome_artifact import OutcomeArtifact

CSV = ("player_id,season,points,games,appeared\n"
       "00-0000001,2024,210.5,16,True\n"
       "00-0000001,2025,0.0,0,False\n"
       "00-0000002,2025,-1.2,3,True\n")


def _windows(years):
    out = {}
    for y in years:
        final = 18 if y >= 2021 else 17
        out[str(y)] = {"included_reg_weeks": list(range(1, final)), "excluded_final_reg_week": final,
                       "expected_full_reg_weeks": list(range(1, final + 1)), "weekly_weight": 1.0}
    return out


def _manifest(csv_bytes, *, coverage="qualified_research_game_complete_identified_rows", years=(2020, 2024, 2025), **over):
    m = {
        "schema_version": "dg179_league_season_outcomes_v1",
        "scoring_preset": "nflverse_default_ppr_championship_window_v1",
        "league_scoring_exact": False,
        "saved_league_scoring_settings": {"rec": 1.0, "pass_td": 4.0},
        "saved_league_scoring_sha256": "5" * 64,
        "exact_league_scoring_gaps": {"fumble_lost_all_units": "not attributed", "st_ff": "not attributed"},
        "scoring_rule": "Sum supplied fantasy_points_ppr; no component rescoring or generator-equivalence claim.",
        "window_rule": "Equal-weight REG stat records in weeks 1-16 through 2020 and weeks 1-17 from 2021",
        "season_windows": _windows(years),
        "exposure_definition": "unique stat_record weeks within the outcome window",
        "appearance_definition": "At least one stat record inside the identical points/games window.",
        "zero_definition": "Identified full-source player-season with no in-window stat record; never a fabricated unknown pair.",
        "last_complete_season": max(years),
        "coverage_status": coverage,
        "source_validation": {"input_rows": 10, "seasons": {str(y): {"reg_rows": 5} for y in years}},
        "source_validation_limitations": "Statistical-source calendar and player-floor checks are not proof that no individual game or player record was omitted.",
        "source_identity": {"sha256": "6" * 64, "source_preparation": {"path": "prep", "sha256": "7" * 64}},
        "source_identity_sha256": "8" * 64,
        "scoring_identity": "a" * 64, "window_identity": "b" * 64, "target_identity": "c" * 64,
        "outcome_rows": 3,
        "outputs": {"outcomes.csv": {"sha256": hashlib.sha256(csv_bytes).hexdigest(), "bytes": len(csv_bytes)}},
    }
    m.update(over)
    return m


def _write(tmp_path, csv_text=CSV, **over):
    b = csv_text.encode()
    (tmp_path / "outcomes.csv").write_bytes(b)
    (tmp_path / "manifest.json").write_text(json.dumps(_manifest(b, **over)))
    return tmp_path / "manifest.json", tmp_path / "outcomes.csv"


def test_a_verified_artifact_binds_its_bytes_identity_window_and_research_qualification(tmp_path) -> None:
    man, csv = _write(tmp_path)
    art = OutcomeArtifact.load(man, csv)
    assert art.csv_sha256 == hashlib.sha256(CSV.encode()).hexdigest() and len(art.manifest_sha256) == 64
    assert art.target_identity == "c" * 64 and art.scoring_identity == "a" * 64 and art.window_identity == "b" * 64
    assert art.rows == 3 and art.admitted_seasons == [2020, 2024, 2025] and art.last_complete_season == 2025
    assert art.research_qualified is True
    assert art.qualification_note.startswith("research qualification: admitted game ids match the source")
    assert "not proof of perfect individual stats" in art.qualification_note
    assert art.league_scoring_exact is False and "fumble_lost_all_units" in art.exact_league_scoring_gaps
    spec = art.target_spec()
    assert (spec.window, spec.scoring, spec.exposure, spec.labels_through) == (
        "championship_week17", "PPR_nflverse_default", "stat_record_weeks_in_window", 2025)
    assert spec.target_id == "nflverse_default_ppr_championship_window_v1"
    # negatives and zeros are values; a season outside the admitted years is UNKNOWN, not zero
    assert art.outcome("00-0000002", 2025) == {"points": -1.2, "games": 3, "appeared": True}
    assert art.outcome("00-0000001", 2025) == {"points": 0.0, "games": 0, "appeared": False}
    assert art.outcome("00-0000001", 2019) is None and art.outcome("nobody", 2025) is None


def test_a_calendar_checked_but_unverified_artifact_is_not_research_qualified(tmp_path) -> None:
    man, csv = _write(tmp_path, coverage="calendar_checked_game_coverage_unverified")
    art = OutcomeArtifact.load(man, csv)
    assert art.research_qualified is False and "calendar_checked_game_coverage_unverified" in art.qualification_note
    (tmp_path / "x").mkdir()
    man2, csv2 = _write(tmp_path / "x", coverage="complete_individual_data")
    art2 = OutcomeArtifact.load(man2, csv2)
    assert art2.research_qualified is False and "unknown coverage status" in art2.qualification_note


def test_hash_schema_exactness_and_window_rule_are_each_refused_when_they_fail(tmp_path) -> None:
    man, csv = _write(tmp_path)
    csv.write_bytes(CSV.replace("210.5", "211.5").encode())
    with pytest.raises(ValueError, match="sha256"):
        OutcomeArtifact.load(man, csv)
    d = tmp_path / "s"
    d.mkdir()
    man, csv = _write(d, schema_version="dg179_league_season_outcomes_v2")
    with pytest.raises(ValueError, match="schema"):
        OutcomeArtifact.load(man, csv)
    d = tmp_path / "e"
    d.mkdir()
    man, csv = _write(d, league_scoring_exact=True)
    with pytest.raises(ValueError, match="exact"):
        OutcomeArtifact.load(man, csv)
    d = tmp_path / "w"
    d.mkdir()
    bad = _windows((2020, 2024, 2025))
    bad["2020"]["included_reg_weeks"] = list(range(1, 18))  # week 17 admitted before 2021: not the rule
    man, csv = _write(d, season_windows=bad)
    with pytest.raises(ValueError, match="window"):
        OutcomeArtifact.load(man, csv)
    d = tmp_path / "c"
    d.mkdir()
    man, csv = _write(d, csv_text="player_id,season,points\n00-1,2025,1.0\n")
    with pytest.raises(ValueError, match="columns"):
        OutcomeArtifact.load(man, csv)


def test_a_producer_bound_to_the_artifact_must_match_its_identity_exactly(tmp_path) -> None:
    from src.dynasty_genius.ranking.outcome_artifact import producer_binding_matches

    man, csv = _write(tmp_path)
    art = OutcomeArtifact.load(man, csv)
    good = {"target_identity": "c" * 64, "outcomes_csv_sha256": art.csv_sha256, "manifest_sha256": art.manifest_sha256,
            "scoring_preset": "nflverse_default_ppr_championship_window_v1", "coverage_status": art.coverage_status,
            "last_complete_season": 2025}
    assert producer_binding_matches(good, art) == []
    assert producer_binding_matches(dict(good, target_identity="d" * 64), art) == ["target_identity"]
    assert "outcomes_csv_sha256" in producer_binding_matches(dict(good, outcomes_csv_sha256="0" * 64), art)
    assert producer_binding_matches(None, art) == ["no outcome binding"]


def test_two_producer_bindings_agree_on_the_core_identity_even_when_one_states_extra_identity_fields() -> None:
    """Lane 23481's companion carries exactly the core vocabulary; lane 24974's adds
    scoring_identity / window_identity. Both bind the same artifact: agreement is decided
    on the core fields, a differing core field is a disagreement, and a missing core field
    is a disagreement too (never treated as agreement)."""
    from src.dynasty_genius.ranking.outcome_artifact import bindings_disagree

    core = {"target_identity": "c" * 64, "outcomes_csv_sha256": "1" * 64, "manifest_sha256": "2" * 64,
            "scoring_preset": "nflverse_default_ppr_championship_window_v1",
            "coverage_status": "qualified_research_game_complete_identified_rows", "last_complete_season": 2025}
    extra = dict(core, scoring_identity="a" * 64, window_identity="b" * 64, artifact=None)
    assert bindings_disagree(core, extra) == []
    assert bindings_disagree(core, dict(extra, outcomes_csv_sha256="9" * 64)) == ["outcomes_csv_sha256"]
    assert "manifest_sha256" in bindings_disagree(core, {k: v for k, v in extra.items() if k != "manifest_sha256"})
    assert bindings_disagree(None, core) == ["no outcome binding"]
