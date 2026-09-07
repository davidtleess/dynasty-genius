"""DG-178 — grading the ASSEMBLED value on withheld seasons.

The contract sums C_ij = max(0, E[points] - R x E[games]). Adapter tests prove the arithmetic;
they say nothing about whether the number ranks players well. This module grades C_ij from a
producer's historical per-player predictions against the realised contribution under the
same policy, with a STATED historical bar proxy: "actually available" cannot be rebuilt for
past seasons (no historical league rosters), so R is the per-league-week expected points of
the player at a declared rank by PREDICTED expected points — ex ante, attainable — and the
rank's sensitivity is part of the report.
"""
from __future__ import annotations

import pytest


def _rows():
    # one position, one season: predicted (e_points, e_games) and realised (points, games)
    return [
        {"player_id": "a", "position": "WR", "season": 2023, "e_points": 250.0, "e_games": 16.0, "points": 240.0, "games": 17.0},
        {"player_id": "b", "position": "WR", "season": 2023, "e_points": 180.0, "e_games": 15.0, "points": 120.0, "games": 12.0},
        {"player_id": "c", "position": "WR", "season": 2023, "e_points": 120.0, "e_games": 14.0, "points": 200.0, "games": 16.0},
        {"player_id": "d", "position": "WR", "season": 2023, "e_points": 90.0, "e_games": 12.0, "points": 40.0, "games": 6.0},
        {"player_id": "e", "position": "WR", "season": 2023, "e_points": 60.0, "e_games": 10.0, "points": 0.0, "games": 0.0},
    ]


def test_the_historical_reference_is_the_rank_n_player_by_the_baseline_arms_predicted_points() -> None:
    from src.dynasty_genius.ranking.grading import historical_reference

    base = [dict(r, e_points={"a": 200.0, "b": 190.0, "c": 150.0, "d": 60.0, "e": 30.0}[r["player_id"]]) for r in _rows()]
    ref = historical_reference(base, position="WR", season=2023, rank=3)
    assert ref.player_id == "c" and ref.expected_points == 150.0 and ref.realised_points == 200.0
    assert ref.basis == "rank_by_baseline_arm_predicted_points"


def test_a_rank_beyond_the_population_is_refused_not_clamped() -> None:
    from src.dynasty_genius.ranking.grading import historical_reference

    with pytest.raises(ValueError, match="rank"):
        historical_reference(_rows(), position="WR", season=2023, rank=9)


def test_predicted_and_realised_contributions_follow_the_same_ex_ante_action() -> None:
    """Predicted advantage = max(0, e_points - reference expected). Realised advantage of the
    action: retained (predicted > 0) realises points - reference realised, which may be
    negative; replaced realises 0."""
    from src.dynasty_genius.ranking.grading import contributions

    ref = {"player_id": "c", "e_points": 120.0, "points": 200.0}
    by = {o.player_id: o for o in contributions(_rows(), reference=ref)}
    assert by["a"].predicted == pytest.approx(130.0) and by["a"].realised == pytest.approx(40.0)
    assert by["b"].predicted == pytest.approx(60.0) and by["b"].realised == pytest.approx(-80.0)
    assert by["c"].predicted == 0.0 and by["c"].started is False and by["c"].realised == 0.0
    assert by["e"].predicted == 0.0 and by["e"].realised == 0.0 and by["e"].realised_if_started == pytest.approx(-200.0)


def test_grading_reports_rank_agreement_error_and_decision_value_against_a_baseline() -> None:
    from src.dynasty_genius.ranking.grading import contributions, grade

    ref = {"player_id": "c", "e_points": 120.0, "points": 200.0}
    cand = contributions(_rows(), reference=ref)
    base_rows = [dict(r, e_points=120.0) for r in _rows()]   # predicts everyone AT the reference: replaces all
    base = contributions(base_rows, reference=ref)
    g = grade(cand, base)
    assert set(g) >= {"n", "n_started", "spearman_pred_vs_realised", "rmse", "decision_value_sum",
                      "baseline_decision_value_sum", "top_k_overlap", "k", "decision_value_diff"}
    assert g["n"] == 5 and g["baseline_decision_value_sum"] == 0.0
    assert -1.0 <= g["spearman_pred_vs_realised"] <= 1.0


def test_grading_is_by_position_and_season_never_pooled_across_positions_silently() -> None:
    from src.dynasty_genius.ranking.grading import grade_by_cell

    rows = _rows() + [dict(r, position="TE", player_id=r["player_id"] + "_te") for r in _rows()]
    cells = grade_by_cell(rows, rows, rank_by_position={"WR": 3, "TE": 3})
    assert set(cells) == {("WR", 2023), ("TE", 2023)}
    assert cells[("WR", 2023)]["reference"]["player_id"] == "c"


def test_veteran_history_rows_map_one_horizon_onto_the_common_shape(tmp_path) -> None:
    from src.dynasty_genius.ranking.grading import veteran_history_rows

    p = tmp_path / "hist.csv"
    p.write_text(
        "horizon,arm,player_id,position,feature_season,forecast_season,p_appear_year1,e_points_year1,e_games_year1,"
        "baseline_e_points_year1,baseline_e_games_year1,appeared_year1,games_year1,points_year1,"
        "p_appear_year2,e_points_year2,e_games_year2,baseline_e_points_year2,baseline_e_games_year2,appeared_year2,games_year2,points_year2,"
        "policy_e_points_year1,policy_e_games_year1,policy_e_points_year2,policy_e_games_year2\n"
        "1,cand,00-1,WR,2022,2023,0.9,180.0,14.4,150.0,13.0,True,17,240.0,,,,,,,,,180.0,14.4,,\n"
        "1,other,00-1,WR,2022,2023,0.9,100.0,10.0,150.0,13.0,True,17,240.0,,,,,,,,,100.0,10.0,,\n"
        "2,cand,00-1,WR,2022,2024,,,,,,,,,0.8,144.0,12.0,120.0,11.0,True,16,200.0,,,144.0,12.0\n"
    )
    got = veteran_history_rows(p, arm="cand", horizon=1)
    cand, base = got.candidate, got.baseline
    assert got.unavailable == 0 and got.mode == "policy"
    assert len(cand) == 1 and cand[0]["season"] == 2023 and cand[0]["e_points"] == 180.0 and cand[0]["points"] == 240.0
    assert base[0]["e_points"] == 150.0 and base[0]["points"] == 240.0 and base[0]["player_id"] == "00-1"
    cand2 = veteran_history_rows(p, arm="cand", horizon=2).candidate
    assert cand2[0]["season"] == 2024 and cand2[0]["e_games"] == 12.0 and cand2[0]["games"] == 16.0
    assert cand[0]["producer"] == "veteran"


def test_rookie_history_rows_map_season_j_onto_the_common_shape_and_skip_unlabelled(tmp_path) -> None:
    from src.dynasty_genius.ranking.grading import rookie_history_rows

    p = tmp_path / "oot.csv"
    p.write_text(
        "gsis_id,draft_season,position,pick,forecast_year,points_1,games_1,points_2,games_2,"
        "e_points_year1,e_games_year1,baseline_e_points_year1,baseline_e_games_year1,"
        "e_points_year2,e_games_year2,baseline_e_points_year2,baseline_e_games_year2\n"
        "00-9,2024,RB,3,2024,150.0,16.0,,,120.0,14.0,80.0,12.0,130.0,14.5,85.0,12.5\n"
        "00-8,2023,RB,40,2023,20.0,5.0,60.0,9.0,40.0,8.0,30.0,7.0,50.0,9.0,35.0,8.0\n"
    )
    got = rookie_history_rows(p, season_j=1)
    cand = got.candidate
    assert {r["player_id"] for r in cand} == {"00-9", "00-8"}
    assert next(r for r in cand if r["player_id"] == "00-9")["season"] == 2024
    got2 = rookie_history_rows(p, season_j=2)
    cand2, base2 = got2.candidate, got2.baseline
    assert [r["player_id"] for r in cand2] == ["00-8"] and cand2[0]["season"] == 2024 and cand2[0]["points"] == 60.0
    assert base2[0]["e_points"] == 35.0 and cand[0]["producer"] == "rookie"


def test_a_rookie_history_graded_on_a_different_arm_than_the_scoring_file_is_detected() -> None:
    """Run 144444Z: manifest.trend_experiment.decision = 'auto_trend' (the 2026 scores use the
    trend arm) while evaluation.json says trend: false (the plain arm was graded). The
    grading that was quoted described an arm that is not on the board."""
    from src.dynasty_genius.ranking.grading import rookie_arm_consistency

    ok, note = rookie_arm_consistency({"trend_experiment": {"decision": "auto_trend"}}, {"trend": False})
    assert ok is False and "plain" in note and "trend" in note
    ok2, _ = rookie_arm_consistency({"trend_experiment": {"decision": "auto_trend"}}, {"trend": True})
    assert ok2 is True
    ok3, _ = rookie_arm_consistency({"trend_experiment": {"decision": "plain"}}, {"trend": False})
    assert ok3 is True
    # A manifest with no experiment block scores the plain model; an evaluation that says
    # trend graded something else.
    ok4, _ = rookie_arm_consistency({}, {"trend": True})
    assert ok4 is False


# ── Round 2, item 2: keep losses, one ex-ante reference for both arms ─────────────────────
def test_a_started_player_who_lost_to_the_reference_keeps_his_loss_in_the_error() -> None:
    """Predicted +10 and realised -10 is an error of 20, not 10. Zero is only the outcome of
    the REPLACE action taken before the season, never a clip on a loss."""
    from src.dynasty_genius.ranking.grading import contributions, grade

    rows = [{"player_id": "a", "position": "WR", "season": 2023, "e_points": 110.0, "points": 90.0},
            {"player_id": "b", "position": "WR", "season": 2023, "e_points": 90.0, "points": 130.0},
            {"player_id": "c", "position": "WR", "season": 2023, "e_points": 130.0, "points": 100.0},
            {"player_id": "ref", "position": "WR", "season": 2023, "e_points": 100.0, "points": 100.0}]
    ref = {"player_id": "ref", "points": 100.0}  # identity + outcome; this arm's own forecast of him is 100
    out = {c.player_id: c for c in contributions(rows, reference=ref)}
    assert out["a"].predicted == pytest.approx(10.0) and out["a"].started is True
    assert out["a"].realised == pytest.approx(-10.0)
    assert out["b"].predicted == 0.0 and out["b"].started is False and out["b"].realised == 0.0
    assert out["b"].realised_if_started == pytest.approx(30.0)
    assert out["ref"].predicted == 0.0 and out["ref"].realised == 0.0  # self = 0
    g = grade(list(out.values()), list(out.values()))
    # errors: a: 10 - (-10) = 20; b: 0 (replaced); c: 30 - 0 = 30; ref: 0 -> rmse = sqrt((400+0+900+0)/4)
    assert g["rmse"] == pytest.approx(((400.0 + 0.0 + 900.0 + 0.0) / 4) ** 0.5)


def test_the_reference_is_chosen_ex_ante_by_one_rule_and_shared_by_both_arms() -> None:
    """The historical reference is a stated PROXY: the rank-N player by the training-only
    baseline arm's predicted points — available before the outcome and independent of the
    candidate — and the same reference is applied to both arms."""
    from src.dynasty_genius.ranking.grading import grade_by_cell

    cand = [{"player_id": p, "position": "WR", "season": 2023, "e_points": e, "points": r}
            for p, e, r in (("a", 250.0, 240.0), ("b", 180.0, 120.0), ("c", 120.0, 200.0), ("d", 90.0, 40.0))]
    base = [dict(r, e_points={"a": 200.0, "b": 190.0, "c": 150.0, "d": 60.0}[r["player_id"]]) for r in cand]
    cells = grade_by_cell(cand, base, rank_by_position={"WR": 3})
    cell = cells[("WR", 2023)]
    assert cell["reference"]["player_id"] == "c"           # rank 3 by BASELINE e_points (200, 190, 150, 60)
    assert cell["reference"]["basis"] == "rank_by_baseline_arm_predicted_points"
    assert cell["reference"]["expected_points"] == pytest.approx(150.0)
    assert cell["reference"]["realised_points"] == pytest.approx(200.0)


def test_grading_reports_bootstrap_uncertainty_on_the_candidate_minus_baseline_difference() -> None:
    from src.dynasty_genius.ranking.grading import contributions, grade

    rows = [{"player_id": str(i), "position": "RB", "season": 2023, "e_points": 100.0 + i, "points": 95.0 + 1.5 * i}
            for i in range(30)]
    base = [dict(r, e_points=100.0) for r in rows]
    rows.append({"player_id": "ref", "position": "RB", "season": 2023, "e_points": 100.0, "points": 100.0})
    base.append({"player_id": "ref", "position": "RB", "season": 2023, "e_points": 100.0, "points": 100.0})
    ref = {"player_id": "ref", "points": 100.0}
    g = grade(contributions(rows, reference=ref), contributions(base, reference=ref), n_boot=200, seed=1)
    assert "decision_value_diff_ci90" in g and len(g["decision_value_diff_ci90"]) == 2
    assert "bias_among_started" in g and "bias_ci90" in g


# ── Round 2: the two-season SUM from one forecast origin ──────────────────────────────
def _origin_rows():
    # one origin (feature season 2022), one position: year-1 and year-2 forecasts + outcomes per player
    return [
        {"player_id": "a", "position": "WR", "origin": 2022, "e_points_1": 250.0, "points_1": 240.0, "e_points_2": 220.0, "points_2": 100.0},
        {"player_id": "b", "position": "WR", "origin": 2022, "e_points_1": 180.0, "points_1": 120.0, "e_points_2": 170.0, "points_2": 190.0},
        {"player_id": "c", "position": "WR", "origin": 2022, "e_points_1": 120.0, "points_1": 200.0, "e_points_2": 110.0, "points_2": 90.0},
        {"player_id": "d", "position": "WR", "origin": 2022, "e_points_1": 90.0, "points_1": 40.0, "e_points_2": 130.0, "points_2": 150.0},
    ]


def test_the_two_season_sum_is_graded_against_one_reference_chosen_at_the_origin() -> None:
    """Reference PLAYER = rank-N by the BASELINE arm's year-1 predicted points at the origin;
    each arm subtracts its OWN forecast of him in each season (round 3), and his realised
    points serve both seasons. Per player: predicted V = sum over seasons of max(0, margin_s);
    realised = sum over seasons of the chosen action's outcome."""
    from src.dynasty_genius.ranking.grading import grade_two_season_by_origin

    cand = _origin_rows()
    base = [dict(r, e_points_1={"a": 200.0, "b": 190.0, "c": 150.0, "d": 60.0}[r["player_id"]],
                 e_points_2={"a": 150.0, "b": 140.0, "c": 100.0, "d": 50.0}[r["player_id"]]) for r in cand]
    cells = grade_two_season_by_origin(cand, base, rank_by_position={"WR": 3})
    cell = cells[("WR", 2022)]
    ref = cell["reference"]
    assert ref["player_id"] == "c" and ref["expected_points"] == [150.0, 100.0] and ref["realised_points"] == [200.0, 90.0]
    assert ref["expected_points_by_arm"] == {"candidate": [120.0, 110.0], "baseline": [150.0, 100.0]}
    # player a under the candidate: margins vs the candidate's own c (120, 110): +130, +110 -> retain both;
    # realised (240-200) + (100-90) = 50
    by = {p["player_id"]: p for p in cell["players"]}
    assert by["a"]["predicted"] == pytest.approx(240.0) and by["a"]["realised"] == pytest.approx(50.0)
    assert by["a"]["baseline_predicted"] == pytest.approx((200.0 - 150.0) + (150.0 - 100.0))
    # player d: margins -30 (replace) and +20 (retain): predicted 20; realised 0 + (150 - 90) = 60
    assert by["d"]["predicted"] == pytest.approx(20.0) and by["d"]["realised"] == pytest.approx(60.0)
    assert by["c"]["predicted"] == 0.0 and by["c"]["baseline_predicted"] == 0.0  # the reference vs himself
    assert cell["n"] == 4 and "rmse" in cell and "decision_value_diff" in cell


def test_two_season_folds_are_reported_separately_with_counts_not_pooled_into_a_superiority_claim() -> None:
    from src.dynasty_genius.ranking.grading import grade_two_season_by_origin

    cand = _origin_rows() + [dict(r, origin=2023) for r in _origin_rows()]
    base = [dict(r, e_points_1=r["e_points_1"] - 30.0, e_points_2=r["e_points_2"] - 30.0) for r in cand]
    cells = grade_two_season_by_origin(cand, base, rank_by_position={"WR": 3}, n_boot=50)
    assert set(cells) == {("WR", 2022), ("WR", 2023)}
    for cell in cells.values():
        assert cell["n"] == 4 and cell["decision_value_diff_ci90"] is not None


def test_arm_consistency_accepts_policy_plus_arm_id_lists_and_checks_a_declared_evaluation_hash() -> None:
    """Lane 24974's round-2 shape: manifest.model_policy = 'inner_menu', manifest.scoring_arm_id =
    '<model>:inner_menu:trend', manifest.pairing.status; evaluation.policy_id = 'inner_menu',
    evaluation.arm_ids = [...]. Consistent when the policies match AND the scoring arm id is
    among the evaluation's arm ids. A declared evaluation sha256 must match the bytes read."""
    from src.dynasty_genius.ranking.grading import rookie_arm_consistency

    man = {"model_policy": "inner_menu", "scoring_arm_id": "m:inner_menu:trend",
           "outputs_sha256": {"evaluation.json": "abc"}}
    ev = {"policy_id": "inner_menu", "arm_ids": ["m:inner_menu:trend", "m:plain"]}
    ok, why = rookie_arm_consistency(man, ev)
    assert ok is True
    ok2, why2 = rookie_arm_consistency(man, {"policy_id": "inner_menu", "arm_ids": ["m:plain"]})
    assert ok2 is False and "arm" in why2
    ok3, _ = rookie_arm_consistency(man, {"policy_id": "outer_winner", "arm_ids": ["m:inner_menu:trend"]})
    assert ok3 is False
    # declared evaluation hash checked when the caller passes the bytes' sha
    ok4, why4 = rookie_arm_consistency(man, ev, evaluation_sha256="zzz")
    assert ok4 is False and "sha256" in why4
    ok5, _ = rookie_arm_consistency(man, ev, evaluation_sha256="abc")
    assert ok5 is True


def test_veteran_history_without_an_arm_column_is_read_whole_and_reaches_five_horizons(tmp_path) -> None:
    """Lane 23481's basic-horizon history has no arm column (one policy per file) and years
    1-5 on the same row for one origin. The reader takes every row when no arm column exists,
    prefers policy_* columns, and the origin builder pairs k seasons from one row."""
    from src.dynasty_genius.ranking.grading import (
        multi_season_rows_from_single_file,
        veteran_history_rows,
    )

    p = tmp_path / "hist.csv"
    cols = ["horizon", "player_id", "position", "feature_season", "forecast_season"]
    for j in (1, 2, 3):
        cols += [f"policy_e_points_year{j}", f"policy_e_games_year{j}", f"baseline_e_points_year{j}", f"baseline_e_games_year{j}",
                 f"points_year{j}", f"games_year{j}"]
    row1 = ["1", "00-1", "WR", "2011", "2012", "100", "14", "90", "13", "110", "15", "120", "14", "95", "13", "80", "12", "130", "14", "100", "13", "150", "16"]
    row3 = ["3", "00-1", "WR", "2011", "2014", "100", "14", "90", "13", "110", "15", "120", "14", "95", "13", "80", "12", "130", "14", "100", "13", "150", "16"]
    p.write_text(",".join(cols) + "\n" + ",".join(row1) + "\n" + ",".join(row3) + "\n")
    got = veteran_history_rows(p, arm="anything", horizon=3)
    cand, base = got.candidate, got.baseline
    assert len(cand) == 1 and cand[0]["season"] == 2014 and cand[0]["e_points"] == 130.0 and base[0]["e_points"] == 100.0
    got3 = multi_season_rows_from_single_file(p, seasons=3, id_col="player_id", origin_col="feature_season", origin_offset=1,
                                              pred_prefix="policy_e_points_year", base_prefix="baseline_e_points_year",
                                              label_prefix="points_year", producer="veteran", horizon_col="horizon", horizon_value=3)
    c3, b3 = got3.candidate, got3.baseline
    # the origin is the FIRST FORECAST season (feature season + 1), never the feature season
    assert c3[0]["origin"] == 2012 and c3[0]["target_seasons"] == [2012, 2013, 2014]
    assert c3[0]["e_points_3"] == 130.0 and c3[0]["points_2"] == 80.0 and b3[0]["e_points_2"] == 95.0


def test_the_multi_season_sum_generalises_the_two_season_sum() -> None:
    from src.dynasty_genius.ranking.grading import grade_multi_season_by_origin

    cand = [dict(r, e_points_3=r["e_points_2"] - 10.0, points_3=r["points_2"] - 20.0) for r in _origin_rows()]
    base = [dict(r, e_points_1=r["e_points_1"] - 30.0, e_points_2=r["e_points_2"] - 30.0, e_points_3=r["e_points_3"] - 30.0) for r in cand]
    cells3 = grade_multi_season_by_origin(cand, base, seasons=3, rank_by_position={"WR": 3})
    cells2 = grade_multi_season_by_origin(cand, base, seasons=2, rank_by_position={"WR": 3})
    assert set(cells3) == {("WR", 2022)} and cells3[("WR", 2022)]["seasons"] == 3
    assert len(cells3[("WR", 2022)]["reference"]["expected_points"]) == 3
    assert cells2[("WR", 2022)]["n"] == 4


def test_veteran_multi_season_rows_join_horizon_rows_on_player_and_origin(tmp_path) -> None:
    """The basic-horizon history carries each season's forecast on its own horizon row; the
    k-season origin rows join h = 1..k on (player_id, feature_season)."""
    from src.dynasty_genius.ranking.grading import veteran_multi_season_rows

    p = tmp_path / "hist.csv"
    head = ["horizon", "player_id", "position", "feature_season", "forecast_season",
            "policy_e_points_year1", "baseline_e_points_year1", "points_year1",
            "policy_e_points_year2", "baseline_e_points_year2", "points_year2",
            "policy_e_points_year3", "baseline_e_points_year3", "points_year3"]
    rows = [["1", "a", "WR", "2020", "2021", "100", "90", "110", "", "", "", "", "", ""],
            ["2", "a", "WR", "2020", "2022", "", "", "", "120", "95", "80", "", "", ""],
            ["3", "a", "WR", "2020", "2023", "", "", "", "", "", "", "130", "100", "150"],
            ["1", "b", "WR", "2020", "2021", "50", "45", "40", "", "", "", "", "", ""]]
    p.write_text(",".join(head) + "\n" + "\n".join(",".join(r) for r in rows) + "\n")
    got = veteran_multi_season_rows(p, seasons=3)
    c3, b3 = got.candidate, got.baseline
    assert [r["player_id"] for r in c3] == ["a"]
    assert c3[0]["origin"] == 2021 and c3[0]["target_seasons"] == [2021, 2022, 2023]  # first forecast season, not 2020
    assert c3[0]["e_points_2"] == 120.0 and c3[0]["points_3"] == 150.0 and b3[0]["e_points_3"] == 100.0
    c2 = veteran_multi_season_rows(p, seasons=2).candidate
    assert [r["player_id"] for r in c2] == ["a"]  # b has no season-2 row
