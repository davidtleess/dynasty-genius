"""Round-3 grading corrections (Codex pinned review of bfe67907, 2026-09-06):

1. one origin on both producers: the veteran history's origin is its FIRST FORECAST season
   (feature_season + 1), the rookie history's is forecast_year; a joint cell may only combine
   rows whose target seasons are identical;
2. the selected-policy evaluation reads policy_* columns only — a row without them is
   unavailable, never a fold manufactured from the raw arm columns;
3. each arm subtracts ITS OWN forecast of the shared reference player, so the reference
   scores zero under both arms and a candidate can never predict value against himself.
"""
from __future__ import annotations

import csv

import pytest

from src.dynasty_genius.ranking.grading import (
    contributions,
    grade_by_cell,
    grade_multi_season_by_origin,
    historical_reference,
    rookie_two_season_rows,
    veteran_history_rows,
    veteran_multi_season_rows,
    veteran_two_season_rows,
)


def _row(pid, e, pts, *, pos="WR", season=2023, producer=None):
    return {"player_id": pid, "position": pos, "season": season, "e_points": e, "points": pts, "producer": producer}


def _by_id(cs):
    return {c.player_id: c for c in cs}


# ── 3. each arm subtracts its own forecast of the reference ──────────────────────────────
def test_the_reference_player_predicts_zero_under_both_arms_and_others_use_each_arms_own_reference_forecast() -> None:
    base = [_row("A", 100.0, 110.0), _row("R", 50.0, 60.0), _row("B", 40.0, 20.0)]
    cand = [_row("A", 120.0, 110.0), _row("R", 70.0, 60.0), _row("B", 75.0, 20.0)]
    ref = historical_reference(base, position="WR", season=2023, rank=2)
    assert ref.player_id == "R"
    cc, bc = _by_id(contributions(cand, reference=ref)), _by_id(contributions(base, reference=ref))
    # self = 0 under BOTH arms
    assert cc["R"].predicted == 0.0 and bc["R"].predicted == 0.0
    assert cc["R"].started is False and cc["R"].realised == 0.0
    # candidate margin uses the candidate's forecast of R (70), not the baseline's (50)
    assert cc["A"].predicted == pytest.approx(50.0)
    assert bc["A"].predicted == pytest.approx(50.0)
    # B: retained by the candidate (75 > 70) and LOST to the reference: 20 - 60 = -40, kept
    assert cc["B"].started is True and cc["B"].realised == pytest.approx(-40.0)
    assert bc["B"].started is False and bc["B"].realised == 0.0


def test_an_arm_that_carries_no_row_for_the_reference_player_is_refused() -> None:
    base = [_row("A", 100.0, 110.0), _row("R", 50.0, 60.0)]
    ref = historical_reference(base, position="WR", season=2023, rank=2)
    with pytest.raises(ValueError, match="reference"):
        contributions([_row("A", 120.0, 110.0)], reference=ref)


def test_grade_by_cell_applies_the_own_forecast_rule_so_the_live_formula_and_the_grade_agree() -> None:
    base = [_row(p, e, y) for p, e, y in (("A", 100, 110), ("R", 50, 60), ("B", 40, 20))]
    cand = [_row(p, e, y) for p, e, y in (("A", 120, 110), ("R", 70, 60), ("B", 75, 20))]
    cell = grade_by_cell(cand, base, rank_by_position={"WR": 2}, top_k={"WR": 2})[("WR", 2023)]
    assert cell["reference"]["player_id"] == "R"
    assert cell["reference"]["expected_points_by_arm"] == {"candidate": 70.0, "baseline": 50.0}
    assert cell["n_started"] == 2  # A and B under the candidate; R never
    assert cell["interval_meaning"].startswith("90% bootstrap over players, conditional on this observed cohort")


def test_the_multi_season_sum_subtracts_each_arms_own_reference_forecast_per_season() -> None:
    def orow(pid, e1, e2, y1, y2, producer="veteran"):
        return {"player_id": pid, "position": "RB", "origin": 2023, "target_seasons": [2023, 2024], "producer": producer,
                "e_points_1": e1, "e_points_2": e2, "points_1": y1, "points_2": y2}
    base = [orow("A", 100, 90, 120, 80), orow("R", 50, 40, 55, 45), orow("B", 30, 30, 10, 10)]
    cand = [orow("A", 130, 100, 120, 80), orow("R", 80, 60, 55, 45), orow("B", 85, 20, 10, 10)]
    cell = grade_multi_season_by_origin(cand, base, seasons=2, rank_by_position={"RB": 2})[("RB", 2023)]
    players = {p["player_id"]: p for p in cell["players"]}
    assert players["R"]["predicted"] == 0.0 and players["R"]["actions"] == ["replace", "replace"]
    assert players["A"]["predicted"] == pytest.approx((130 - 80) + (100 - 60))
    assert players["A"]["baseline_predicted"] == pytest.approx((100 - 50) + (90 - 40))
    # B retained in season 1 only (85 > 80): realised 10 - 55 = -45, kept; season 2 replaced
    assert players["B"]["actions"] == ["retain", "replace"] and players["B"]["realised"] == pytest.approx(-45.0)
    assert cell["reference"]["expected_points_by_arm"]["candidate"] == [80.0, 60.0]
    assert cell["target_seasons"] == [2023, 2024]


# ── 1. one origin on both producers ─────────────────────────────────────────────────────
def _write_veteran_history(path, rows, *, with_policy=True, with_arm=True):
    cols = ["horizon", "player_id", "position", "feature_season", "forecast_season"]
    if with_arm:
        cols.insert(1, "arm")
    for j in (1, 2):
        cols += [f"e_points_year{j}", f"e_games_year{j}", f"baseline_e_points_year{j}", f"baseline_e_games_year{j}",
                 f"points_year{j}", f"games_year{j}"]
        if with_policy:
            cols += [f"policy_e_points_year{j}", f"policy_e_games_year{j}"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def _vrow(pid, h, feature, e, b, y, *, policy=None, arm="cand"):
    j = h
    r = {"horizon": h, "arm": arm, "player_id": pid, "position": "WR", "feature_season": feature,
         "forecast_season": feature + h, f"e_points_year{j}": e, f"e_games_year{j}": 10, f"baseline_e_points_year{j}": b,
         f"baseline_e_games_year{j}": 10, f"points_year{j}": y, f"games_year{j}": 10}
    if policy is not None:
        r[f"policy_e_points_year{j}"] = policy
        r[f"policy_e_games_year{j}"] = 10
    return r


def _write_rookie_history(path, rows):
    cols = ["gsis_id", "position", "forecast_year", "e_points_year1", "e_games_year1", "baseline_e_points_year1",
            "baseline_e_games_year1", "points_1", "games_1", "e_points_year2", "e_games_year2", "baseline_e_points_year2",
            "baseline_e_games_year2", "points_2", "games_2"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def test_veteran_origin_is_the_first_forecast_season_so_2022_features_pair_with_the_2023_rookie_origin(tmp_path) -> None:
    vp = tmp_path / "vet.csv"
    _write_veteran_history(vp, [_vrow("V", 1, 2022, 90, 80, 95, policy=91), _vrow("V", 2, 2022, 85, 70, 80, policy=86)])
    rp = tmp_path / "rook.csv"
    _write_rookie_history(rp, [{"gsis_id": "K", "position": "WR", "forecast_year": 2023,
                                "e_points_year1": 60, "e_games_year1": 10, "baseline_e_points_year1": 50, "baseline_e_games_year1": 10,
                                "points_1": 70, "games_1": 10, "e_points_year2": 65, "e_games_year2": 10,
                                "baseline_e_points_year2": 55, "baseline_e_games_year2": 10, "points_2": 75, "games_2": 10}])
    vet = veteran_two_season_rows(vp, arm="cand")
    rook = rookie_two_season_rows(rp)
    assert vet.candidate[0]["origin"] == 2023 and vet.candidate[0]["target_seasons"] == [2023, 2024]
    assert rook.candidate[0]["origin"] == 2023 and rook.candidate[0]["target_seasons"] == [2023, 2024]
    joint = grade_multi_season_by_origin(vet.candidate + rook.candidate, vet.baseline + rook.baseline, seasons=2,
                                         rank_by_position={"WR": 1})
    assert list(joint) == [("WR", 2023)]
    assert {p["producer"] for p in joint[("WR", 2023)]["players"]} == {"veteran", "rookie"}


def test_a_cell_mixing_rows_with_different_target_seasons_is_refused_not_summed() -> None:
    a = {"player_id": "A", "position": "WR", "origin": 2023, "target_seasons": [2023, 2024], "producer": "veteran",
         "e_points_1": 10, "e_points_2": 10, "points_1": 10, "points_2": 10}
    b = {**a, "player_id": "B", "target_seasons": [2022, 2023], "producer": "rookie"}
    with pytest.raises(ValueError, match="target seasons"):
        grade_multi_season_by_origin([a, b], [a, b], seasons=2, rank_by_position={"WR": 1})


def test_the_k_season_join_uses_the_first_forecast_season_as_origin(tmp_path) -> None:
    vp = tmp_path / "vet.csv"
    _write_veteran_history(vp, [_vrow("V", 1, 2020, 90, 80, 95, policy=91), _vrow("V", 2, 2020, 85, 70, 80, policy=86)])
    got = veteran_multi_season_rows(vp, seasons=2, arm="cand")
    assert got.candidate[0]["origin"] == 2021 and got.candidate[0]["target_seasons"] == [2021, 2022]
    assert got.candidate[0]["e_points_1"] == 91.0  # policy column, not the raw arm's 90


# ── 2. policy columns only ──────────────────────────────────────────────────────────────
def test_a_row_without_policy_output_is_unavailable_in_policy_mode_and_only_legacy_mode_reads_the_raw_arm(tmp_path) -> None:
    vp = tmp_path / "vet.csv"
    _write_veteran_history(vp, [_vrow("V", 1, 2021, 90, 80, 95, policy=91),
                                _vrow("W", 1, 2021, 70, 60, 65),                    # policy empty: zero evaluated folds
                                _vrow("V", 2, 2021, 85, 70, 80),                    # year 2 never graded by the policy
                                _vrow("W", 2, 2021, 60, 50, 55)])
    got = veteran_history_rows(vp, arm="cand", horizon=1)
    assert [r["player_id"] for r in got.candidate] == ["V"] and got.unavailable == 1
    assert got.candidate[0]["e_points"] == 91.0
    y2 = veteran_history_rows(vp, arm="cand", horizon=2)
    assert y2.candidate == [] and y2.unavailable == 2  # no fold manufactured from the raw columns
    legacy = veteran_history_rows(vp, arm="cand", horizon=2, mode="legacy_arm")
    assert sorted(r["player_id"] for r in legacy.candidate) == ["V", "W"] and legacy.mode == "legacy_arm"
    assert legacy.candidate[0]["e_points"] in (85.0, 60.0)
    # the k-season join, same rule: an origin whose year 2 has no policy output does not count
    assert veteran_multi_season_rows(vp, seasons=2, arm="cand").candidate == []
    assert len(veteran_multi_season_rows(vp, seasons=2, arm="cand", mode="legacy_arm").candidate) == 2


def test_legacy_mode_requires_an_arm_column_because_the_raw_columns_belong_to_a_named_arm(tmp_path) -> None:
    vp = tmp_path / "vet.csv"
    _write_veteran_history(vp, [_vrow("V", 1, 2021, 90, 80, 95, policy=91)], with_arm=False)
    with pytest.raises(ValueError, match="arm column"):
        veteran_history_rows(vp, arm="cand", horizon=1, mode="legacy_arm")
    assert veteran_history_rows(vp, arm=None, horizon=1).candidate[0]["e_points"] == 91.0
