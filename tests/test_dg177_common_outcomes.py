"""Consume the COMMON league-season outcome artifact (Codex / DG-179, schema
dg179_league_season_outcomes_v1) as this lane's label source.

The consumer mirrors the ACTUAL manifest keys, never provisional aliases; it binds the
CSV bytes to outputs["outcomes.csv"]; it requires the scoring preset, league_scoring_exact
false, the per-season windows (REG weeks 1-16 through 2020, 1-17 from 2021, weight 1.0),
the exposure definition and a known coverage_status; it derives an internal
validated-research attribute ONLY after those checks and keeps the qualification note;
it never converts "qualified research" into "complete individual data"; and it keeps
source-complete zeros distinct from unknown (seasons outside the artifact are censored).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.common_outcomes import (
    COVERAGE_FIXTURE,
    COVERAGE_QUALIFIED,
    EXPECTED_COLUMNS,
    SCHEMA_VERSION,
    SCORING_PRESET,
    CommonArtifactError,
    load_common_outcomes,
    validate_common_manifest,
)

DG179_MODULE = Path("/Users/davidleess/dg-wt/DG-179/src/dynasty_genius/eval/league_season_outcomes.py")


def _windows(years):
    out = {}
    for y in years:
        final = 18 if y >= 2021 else 17
        out[str(y)] = {"included_reg_weeks": list(range(1, final)), "excluded_final_reg_week": final,
                       "expected_full_reg_weeks": list(range(1, final + 1)), "weekly_weight": 1.0}
    return out


def _manifest(csv_bytes: bytes, years=(2019, 2020, 2021), coverage=COVERAGE_QUALIFIED, **over):
    m = {
        "schema_version": SCHEMA_VERSION,
        "scoring_preset": SCORING_PRESET,
        "league_scoring_exact": False,
        "saved_league_scoring_settings": {"rec": 1.0, "pass_td": 4.0},
        "saved_league_scoring_sha256": "1" * 64,
        "exact_league_scoring_gaps": {"fum_lost": "not established", "st_ff": "not established"},
        "scoring_rule": "Sum supplied fantasy_points_ppr; no component rescoring or generator-equivalence claim.",
        "window_rule": "Equal-weight REG stat records in weeks 1-16 through 2020 and weeks 1-17 from 2021",
        "season_windows": _windows(years),
        "exposure_definition": "unique stat_record weeks within the outcome window",
        "appearance_definition": "At least one stat record inside the identical points/games window.",
        "zero_definition": "Identified full-source player-season with no in-window stat record; never a fabricated unknown pair.",
        "last_complete_season": max(years),
        "coverage_status": coverage,
        "source_validation": {"input_rows": 10, "validated_requested_season_rows": 10, "out_of_scope_rows": 0,
                              "min_players_per_season": 500, "seasons": {str(y): {"reg_players": 600} for y in years}},
        "source_validation_limitations": "Statistical-source calendar and player-floor checks are not proof that no individual game or player record was omitted.",
        "source_identity": {"sha256": "2" * 64, "path": "identified_weekly.parquet"},
        "source_identity_sha256": "3" * 64,
        "scoring_identity": "4" * 64,
        "window_identity": "5" * 64,
        "target_identity": "6" * 64,
        "outcome_rows": 3,
        "outputs": {"outcomes.csv": {"sha256": hashlib.sha256(csv_bytes).hexdigest(), "bytes": len(csv_bytes)}},
    }
    m.update(over)
    return m


def _artifact(tmp_path, rows, **over):
    tmp_path.mkdir(parents=True, exist_ok=True)
    csv = pd.DataFrame(rows, columns=EXPECTED_COLUMNS).to_csv(index=False).encode()
    (tmp_path / "outcomes.csv").write_bytes(csv)
    m = _manifest(csv, **over)
    (tmp_path / "manifest.json").write_text(json.dumps(m, sort_keys=True, indent=2) + "\n")
    return tmp_path


ROWS = [("A", 2019, 150.5, 15, True), ("A", 2020, 0.0, 0, False), ("B", 2021, 90.0, 12, True)]


def test_constants_mirror_dg179():
    assert SCHEMA_VERSION == "dg179_league_season_outcomes_v1"
    assert SCORING_PRESET == "nflverse_default_ppr_championship_window_v1"
    assert COVERAGE_QUALIFIED == "qualified_research_game_complete_identified_rows"
    assert COVERAGE_FIXTURE == "calendar_checked_game_coverage_unverified"
    assert EXPECTED_COLUMNS == ["player_id", "season", "points", "games", "appeared"]


def test_manifest_checks_schema_preset_exactness_windows_exposure_and_coverage(tmp_path):
    good = _manifest(b"x")
    validate_common_manifest(good)
    for bad, needle in (
        ({"schema_version": "other"}, "schema_version"),
        ({"scoring_preset": "something_else"}, "scoring_preset"),
        ({"league_scoring_exact": True}, "league_scoring_exact"),
        ({"season_windows": {**_windows((2019, 2020, 2021)), "2020": {**_windows((2020,))["2020"], "included_reg_weeks": list(range(1, 18))}}}, "included_reg_weeks"),
        ({"season_windows": {**_windows((2019, 2020, 2021)), "2021": {**_windows((2021,))["2021"], "weekly_weight": 0.5}}}, "weekly_weight"),
        ({"exposure_definition": "games with a stat line anywhere"}, "exposure_definition"),
        ({"coverage_status": "complete_individual_data"}, "coverage_status"),
        ({"outputs": {}}, "outputs"),
        ({"source_validation_limitations": ""}, "limitations"),
    ):
        with pytest.raises(CommonArtifactError, match=needle):
            validate_common_manifest(_manifest(b"x", **bad))


def test_load_binds_bytes_and_derives_the_validated_research_attr_only_after_checks(tmp_path):
    d = _artifact(tmp_path, ROWS)
    out = load_common_outcomes(d)
    assert list(out.columns) == ["player_id", "season", "games", "points", "appeared"]
    assert out.attrs["scope"] == "REG_league_window" and out.attrs["window_id"] == "championship_week17"
    assert out.attrs["scoring"] == SCORING_PRESET and out.attrs["league_scoring_exact"] is False
    assert out.attrs["exact_league_scoring_gaps"]["fum_lost"]
    assert out.attrs["seasons_covered"] == [2019, 2020, 2021]
    sv = out.attrs["source_validation"]
    assert sv["validated"] is True                      # derived here, after schema + hash + coverage checks
    assert sv["coverage_status"] == COVERAGE_QUALIFIED
    assert sv["qualification_note"].startswith("Statistical-source calendar")
    assert sv["individual_stat_completeness_proven"] is False
    assert sv["facts"]["seasons"]["2019"]["reg_players"] == 600
    assert out.attrs["csv_sha256"] == hashlib.sha256((d / "outcomes.csv").read_bytes()).hexdigest()
    assert out.attrs["manifest_sha256"] == hashlib.sha256((d / "manifest.json").read_bytes()).hexdigest()
    assert out.attrs["target_identity"] == "6" * 64
    a20 = out.set_index(["player_id", "season"]).loc[("A", 2020)]
    assert a20["games"] == 0 and a20["points"] == 0.0 and bool(a20["appeared"]) is False   # source-complete zero


def test_a_hash_or_byte_length_mismatch_is_refused(tmp_path):
    d = _artifact(tmp_path, ROWS)
    m = json.loads((d / "manifest.json").read_text())
    m["outputs"]["outcomes.csv"]["sha256"] = "9" * 64
    (d / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(CommonArtifactError, match="sha256"):
        load_common_outcomes(d)


def test_a_fixture_grade_artifact_loads_but_is_marked_unqualified(tmp_path):
    d = _artifact(tmp_path, ROWS, coverage=COVERAGE_FIXTURE)
    out = load_common_outcomes(d)
    assert out.attrs["source_validation"]["validated"] is True
    assert out.attrs["source_validation"]["coverage_status"] == COVERAGE_FIXTURE
    assert out.attrs["source_validation"]["qualified_research"] is False
    with pytest.raises(CommonArtifactError, match="qualified"):
        load_common_outcomes(d, require_qualified=True)


def test_points_games_and_appearance_must_agree_within_a_row(tmp_path):
    with pytest.raises(CommonArtifactError, match="same mask"):
        load_common_outcomes(_artifact(tmp_path / "a", [("A", 2020, 12.0, 0, True)]))
    with pytest.raises(CommonArtifactError, match="same mask"):
        load_common_outcomes(_artifact(tmp_path / "b", [("A", 2020, 0.0, 3, False)]))


def test_a_season_outside_the_artifact_is_unknown_not_zero_in_annual_targets(tmp_path):
    from src.dynasty_genius.eval.annual_outcomes import annual_targets
    out = load_common_outcomes(_artifact(tmp_path, ROWS))
    training = pd.DataFrame({"player_id": ["A", "A"], "position": ["WR", "WR"], "feature_season": [2018, 2020]})
    t = annual_targets(training, out, horizons=(1, 2), last_complete_season=2021).set_index("feature_season")
    assert t.loc[2018, "games_year1"] == 15 and t.loc[2018, "games_year2"] == 0 and bool(t.loc[2018, "appeared_year2"]) is False
    assert np.isnan(t.loc[2020, "games_year2"]) and pd.isna(t.loc[2020, "appeared_year2"])   # 2022 not covered: unknown
    assert t.attrs["source_validation"]["coverage_status"] == COVERAGE_QUALIFIED


@pytest.mark.skipif(not DG179_MODULE.exists(), reason="DG-179 worktree not present")
def test_an_artifact_built_by_dg179s_own_builder_is_accepted(tmp_path):
    """Schema drift guard: build a fixture through DG-179's real builder (read-only import)."""
    spec = importlib.util.spec_from_file_location("dg179_league_season_outcomes", DG179_MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = []
    for season in (2019, 2020, 2021):
        final = 18 if season >= 2021 else 17
        for p in range(600):
            for w in range(1, final + 1):
                rows.append((f"p{p:04d}", season, w, "REG", float(w % 3)))
    weekly = pd.DataFrame(rows, columns=["player_id", "season", "week", "season_type", "fantasy_points_ppr"])
    annual, manifest = mod.build_league_season_outcomes(
        weekly, seasons=[2019, 2020, 2021], scoring_settings={"rec": 1.0},
        source_identity={"sha256": "a" * 64, "path": "fixture"}, min_players_per_season=500,
    )
    csv_bytes = annual.to_csv(index=False).encode()
    manifest["outputs"] = {"outcomes.csv": {"sha256": hashlib.sha256(csv_bytes).hexdigest(), "bytes": len(csv_bytes)}}
    (tmp_path / "outcomes.csv").write_bytes(csv_bytes)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n")
    out = load_common_outcomes(tmp_path)
    assert out.attrs["source_validation"]["coverage_status"] == COVERAGE_FIXTURE
    assert out.attrs["seasons_covered"] == [2019, 2020, 2021]
    assert out.attrs["target_identity"] == manifest["target_identity"]
    # the artifact's own zero definition: an identified player-season with no in-window record is 0, appeared False
    assert (out.loc[out.games == 0, "appeared"] == False).all()  # noqa: E712
