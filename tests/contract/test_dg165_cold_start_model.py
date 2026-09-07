"""Contract tests for the cold-start candidate (DG-165, available-players build 2026-09-06).

Task 5: the frozen never-record population from hash-verified raw REG captures (no fitting).
Task 6: the per-horizon hurdle candidate, baselines, paired evaluation and sidecar export.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def make_capture(root: Path, rows_by_season: dict[int, pd.DataFrame]) -> Path:
    """A tiny weekly_source_capture: raw/<season>.parquet files + manifest.json declaring their hashes."""
    cap = root / "capture"
    (cap / "raw").mkdir(parents=True)
    files = {}
    for season, df in rows_by_season.items():
        path = cap / "raw" / f"player_stats_{season}.parquet"
        df.to_parquet(path, index=False)
        files[f"raw/player_stats_{season}.parquet"] = {"sha256": _sha(path.read_bytes()), "rows": len(df), "season": season}
    (cap / "manifest.json").write_text(json.dumps({"ticket": "DG-165", "files": files}, sort_keys=True))
    return cap


def _weekly(rows):
    return pd.DataFrame(rows, columns=["player_id", "season", "week", "season_type", "position"])


@pytest.fixture
def capture(tmp_path):
    return make_capture(tmp_path, {
        2015: _weekly([("00-A", 2015, 3, "REG", "QB"),          # A: rookie-year record -> NOT eligible
                       ("00-W", 2015, 18, "REG", "WR"),         # W: week-18-only record -> NOT eligible under the full-REG rule
                       ("00-P", 2015, 1, "POST", "RB")]),       # P: only a POST row in the draft season -> eligible (REG absence)
        2016: _weekly([("00-B", 2016, 5, "REG", "RB"),          # B: first REG record the season after the draft -> eligible, appear_1 = 1
                       ("00-P", 2016, 2, "REG", "RB")]),
    })


def _cohort():
    return pd.DataFrame({"gsis_id": ["00-A", "00-B", "00-C", "00-W", "00-P", "00-OLD"], "draft_season": [2015, 2015, 2015, 2015, 2015, 2000],
                         "position": ["QB", "RB", "WR", "WR", "RB", "WR"], "pick": [1, 40, 90, 91, 60, 5], "round": [1, 2, 3, 3, 2, 1],
                         "age_at_draft": [22.0, 21.5, np.nan, 22.0, 23.0, 22.0], "team": ["X"] * 6,
                         "name": ["Ann", "Bob", "Cy", "Wes", "Pat", "Old"],
                         "label_basis": ["nflverse_gsis"] * 6, "position_current": ["QB", "RB", "WR", "WR", "RB", "WR"]})


def _players():
    return pd.DataFrame({"gsis_id": ["00-A", "00-B", "00-C", "00-W", "00-P"], "birth_date": ["1993-06-01", "1994-01-15", None, "1993-09-09", "1992-03-03"]})


def _artifact():
    return pd.DataFrame({"player_id": ["00-B", "00-P", "00-B", "00-C"], "season": [2016, 2016, 2017, 2018],
                         "points": [50.0, 20.0, 80.0, 10.0], "games": [8, 4, 12, 2], "appeared": [True, True, True, True]})


def test_verify_capture_refuses_altered_or_missing_files(capture):
    from src.dynasty_genius.rookie.cold_start_model import verify_capture
    verified = verify_capture(capture)
    assert set(verified) == {"raw/player_stats_2015.parquet", "raw/player_stats_2016.parquet"}
    path = capture / "raw" / "player_stats_2016.parquet"
    pd.read_parquet(path).iloc[:1].to_parquet(path, index=False)
    with pytest.raises(ValueError, match="sha256"):
        verify_capture(capture)
    path.unlink()
    with pytest.raises(ValueError, match="missing"):
        verify_capture(capture)


def test_never_record_population_applies_the_full_reg_rule(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
    )
    first = first_full_reg_season(capture)
    assert first["00-A"] == 2015 and first["00-W"] == 2015 and first["00-B"] == 2016 and first["00-P"] == 2016
    pop = never_record_population(cohort=_cohort(), first_reg=first, outcomes=_artifact(), players=_players(), last_complete_season=2025)
    assert sorted(pop["gsis_id"]) == ["00-B", "00-C", "00-P"]  # A and W excluded (REG record in the draft season); OLD outside 2001+
    by = pop.set_index("gsis_id")
    assert by.loc["00-B", "origin_year"] == 2016 and by.loc["00-B", "appear_1"] == 1.0 and by.loc["00-B", "points_1"] == 50.0
    assert by.loc["00-B", "label_source_1"] == "artifact" and by.loc["00-B", "appear_2"] == 1.0 and by.loc["00-B", "points_2"] == 80.0
    assert by.loc["00-C", "appear_1"] == 0.0 and by.loc["00-C", "label_source_1"] == "convention_zero"  # complete season, no artifact row
    assert by.loc["00-C", "appear_3"] == 1.0 and by.loc["00-C", "points_3"] == 10.0                     # 2018 = origin 2016 + 2
    assert by.loc["00-B", "age_at_origin"] == pytest.approx(22.63, abs=0.05)                            # 1994-01-15 to 2016-09-01
    assert pd.isna(by.loc["00-C", "age_at_origin"])                                                       # no birth date: NaN, never a default
    assert bool(by.loc["00-W", "window_absent_through_draft_season"]) if "00-W" in by.index else True
    assert by.loc["00-B", "log_pick"] == pytest.approx(np.log(40))


def test_labels_beyond_the_last_complete_season_are_unknown(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
    )
    # C has no REG record at all; re-dated to class 2024 his origin is 2025: h=1 = season 2025 (complete, no artifact row ->
    # convention zero), h=2 = 2026 (not complete -> unknown, never zero)
    cohort = _cohort().assign(draft_season=[2015, 2015, 2024, 2015, 2015, 2000])
    pop = never_record_population(cohort=cohort, first_reg=first_full_reg_season(capture), outcomes=_artifact(), players=_players(), last_complete_season=2025)
    c = pop.set_index("gsis_id").loc["00-C"]
    assert c["origin_year"] == 2025 and c["appear_1"] == 0.0 and c["label_source_1"] == "convention_zero"
    assert pd.isna(c["appear_2"]) and pd.isna(c["points_2"]) and c["label_source_2"] == "unknown"


def test_support_table_counts_training_and_test_rows_per_origin_and_horizon(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
        support_table,
    )
    cohort = pd.concat([_cohort(), pd.DataFrame({"gsis_id": ["00-Q"], "draft_season": [2013], "position": ["QB"], "pick": [10], "round": [1],
                                                  "age_at_draft": [22.0], "team": ["X"], "name": ["Quin"], "label_basis": ["nflverse_gsis"], "position_current": ["QB"]})])
    pop = never_record_population(cohort=cohort, first_reg=first_full_reg_season(capture), outcomes=_artifact(), players=_players(), last_complete_season=2025)
    sup = support_table(pop, origins=(2016,), horizons=(1, 2))
    row = sup.set_index(["origin", "horizon"])
    # at origin 2016, h=1: training rows need c + 1 < 2016 -> only Quin (2013); test rows = class 2015 with a complete 2016 label -> B, C, P
    assert row.loc[(2016, 1), "train_rows"] == 1 and row.loc[(2016, 1), "test_rows"] == 3
    assert row.loc[(2016, 2), "train_rows"] == 1 and row.loc[(2016, 2), "test_rows"] == 3
    assert row.loc[(2016, 1), "train_appearers"] == 0 and "QB" in json.loads(row.loc[(2016, 1), "train_rows_by_position"])


# ---------------------------------------------------------------- the frozen real population (root, 2026-09-06): asserted against the real files

REAL_CAPTURE = Path("runs/20260906T191723Z/weekly_source_capture")
REAL_ROOKIE = Path("runs/20260906T195904Z/dg165_rookie_capital")
REAL_ARTIFACT = Path("/Users/davidleess/dg-wt/DG-179/runs/20260906T194819Z/league_season_outcomes/outcomes.csv")


@pytest.mark.skipif(not (REAL_CAPTURE.exists() and REAL_ROOKIE.exists() and REAL_ARTIFACT.exists()), reason="frozen real files not present")
def test_frozen_real_population_counts_match_root():
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
        support_table,
        verify_capture,
    )
    assert len(verify_capture(REAL_CAPTURE)) == 27
    pop = never_record_population(cohort=pd.read_csv(REAL_ROOKIE / "cohort.csv"), first_reg=first_full_reg_season(REAL_CAPTURE),
                                  outcomes=pd.read_csv(REAL_ARTIFACT), players=pd.read_parquet(REAL_ROOKIE / "inputs" / "nflverse_players.parquet"),
                                  last_complete_season=2025)
    assert len(pop) == 424 and pop["draft_position"].value_counts().to_dict() == {"WR": 150, "QB": 118, "RB": 85, "TE": 71}
    sup = support_table(pop).set_index(["origin", "horizon"])
    assert [int(sup.loc[(2012, h), "train_rows"]) for h in range(1, 6)] == [199, 184, 164, 141, 119]
    test_rows = [int(sum(sup.loc[(T, h), "test_rows"] for T in range(2012, 2026))) for h in range(1, 6)]
    assert test_rows == [210, 199, 187, 179, 172]
    seven = pop.loc[pop["draft_season"] == 2025, "name"]
    assert {"Graham Mertz", "Kurtis Rourke", "Kyle McCord", "Will Howard", "Caleb Lohner", "Gavin Bartholomew", "Ricky White"} <= set(seven)
