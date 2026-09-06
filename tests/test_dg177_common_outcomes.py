"""Part 2 of the Codex increment — consume the COMMON player-season outcome artifact.

Codex (DG-179) publishes one CSV + manifest per research window: player_id, season,
points, games, appeared, built from the full validated weekly source with REG weeks
1-16 through 2020 and 1-17 from 2021, equal week weights, scoring identified as
nflverse-default-PPR league-window research (not David's exact scoring). This module
reads it as the label source in place of this lane's own REG aggregation: it never
re-scores anything, never implies exact league equivalence, requires points, games
and appearance to come from the same artifact and mask, and keeps source-complete
absence (0 games) distinct from unknown (row absent, season not covered).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.dynasty_genius.eval.common_outcomes import (
    EXPECTED_COLUMNS,
    CommonArtifactError,
    load_common_outcomes,
    validate_common_manifest,
)


def _manifest(**over):
    m = {
        "artifact": "dg179_common_player_season",
        "scoring_identifier": "nflverse-default-PPR league-window research",
        "exact_league_scoring": False,
        "scope": {"season_type": "REG", "weeks": {"through_2020": [1, 16], "from_2021": [1, 17]}, "week_weights": "equal"},
        "columns": ["player_id", "season", "points", "games", "appeared"],
        "seasons_covered": [2018, 2019, 2020, 2021],
        "source_validated": True,
        "csv_sha256": "a" * 64,
    }
    m.update(over)
    return m


def _csv(tmp_path, rows):
    p = tmp_path / "common.csv"
    pd.DataFrame(rows, columns=EXPECTED_COLUMNS).to_csv(p, index=False)
    return p


def test_expected_columns_are_the_five_the_artifact_names():
    assert EXPECTED_COLUMNS == ["player_id", "season", "points", "games", "appeared"]


def test_manifest_must_name_the_window_the_scoring_and_the_validation():
    validate_common_manifest(_manifest())
    with pytest.raises(CommonArtifactError, match="scoring"):
        validate_common_manifest(_manifest(scoring_identifier=None))
    with pytest.raises(CommonArtifactError, match="exact"):
        validate_common_manifest(_manifest(exact_league_scoring=True))      # we never claim David's exact scoring
    with pytest.raises(CommonArtifactError, match="weeks"):
        validate_common_manifest(_manifest(scope={"season_type": "REG", "weeks": {"through_2020": [1, 17], "from_2021": [1, 17]}, "week_weights": "equal"}))
    with pytest.raises(CommonArtifactError, match="validated"):
        validate_common_manifest(_manifest(source_validated=False))


def test_load_binds_the_csv_bytes_to_the_manifest_and_returns_outcomes_with_attrs(tmp_path):
    import hashlib
    p = _csv(tmp_path, [("A", 2020, 150.5, 15, True), ("A", 2021, 0.0, 0, False), ("B", 2021, 90.0, 12, True)])
    m = _manifest(csv_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    out = load_common_outcomes(p, m)
    assert list(out.columns) == ["player_id", "season", "games", "points", "appeared"]
    assert out.attrs["scope"] == "REG_league_window"
    assert out.attrs["scoring"] == "nflverse-default-PPR league-window research"
    assert out.attrs["exact_league_scoring"] is False
    assert out.attrs["source_validation"]["validated"] is True
    assert out.attrs["seasons_covered"] == [2018, 2019, 2020, 2021]
    assert out.attrs["csv_sha256"] == m["csv_sha256"]
    a21 = out.set_index(["player_id", "season"]).loc[("A", 2021)]
    assert a21["games"] == 0 and a21["points"] == 0.0 and bool(a21["appeared"]) is False   # source-complete absence


def test_a_hash_mismatch_is_refused(tmp_path):
    p = _csv(tmp_path, [("A", 2020, 150.5, 15, True)])
    with pytest.raises(CommonArtifactError, match="sha256"):
        load_common_outcomes(p, _manifest(csv_sha256="b" * 64))


def test_points_games_and_appearance_must_agree_within_a_row(tmp_path):
    import hashlib
    p = _csv(tmp_path, [("A", 2020, 12.0, 0, True)])                # points with zero games
    with pytest.raises(CommonArtifactError, match="same mask"):
        load_common_outcomes(p, _manifest(csv_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    p = _csv(tmp_path, [("A", 2020, 0.0, 3, False)])                # games but not appeared
    with pytest.raises(CommonArtifactError, match="same mask"):
        load_common_outcomes(p, _manifest(csv_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))


def test_a_season_outside_coverage_is_unknown_not_zero_in_annual_targets(tmp_path):
    import hashlib

    from src.dynasty_genius.eval.annual_outcomes import annual_targets
    p = _csv(tmp_path, [("A", 2020, 150.5, 15, True), ("A", 2021, 0.0, 0, False)])
    m = _manifest(csv_sha256=hashlib.sha256(p.read_bytes()).hexdigest(), seasons_covered=[2020, 2021])
    out = load_common_outcomes(p, m)
    training = pd.DataFrame({"player_id": ["A", "A"], "position": ["WR", "WR"], "feature_season": [2019, 2020]})
    t = annual_targets(training, out, horizons=(1, 2), last_complete_season=2021).set_index("feature_season")
    assert t.loc[2019, "games_year1"] == 15 and t.loc[2019, "games_year2"] == 0 and bool(t.loc[2019, "appeared_year2"]) is False
    # feature 2020, year 2 = 2022: not in seasons_covered -> unknown (NaN), never 0, even though last_complete says 2021
    assert np.isnan(t.loc[2020, "games_year2"]) and pd.isna(t.loc[2020, "appeared_year2"])
    assert t.attrs["source_validation"]["validated"] is True and json.dumps(t.attrs["scoring"])
