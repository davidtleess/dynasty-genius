"""DG-178 round 2, item 7 — the research preview route reads a LOCAL run report, read-only.

It serves the candidate board from `runs/<id>/dg178_audit/report.json` in this checkout,
never from the live valuation artifact, and says so in the payload. Reasons come back as
fantasy-language sentences with the raw reason kept beside them.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


def _report():
    return {
        "run": "20260906T000000Z", "forecast_date": "2026-09-06",
        "board_target": {"scope": "REG", "scoring": "PPR_nflverse_weekly", "exposure": "stat_row_games",
                         "event": "appearance", "clock": "per_season", "quantity": "season_points", "labels_through": 2025},
        "inputs": {"artifact": {"captured_at": "2026-09-06T13:00:53+00:00", "sha256": "a" * 64},
                   "snapshot": {"id": "league-20260906T130052Z"}},
        "comparable_board": {
            "n_comparable": 1, "horizons_summed": 2,
            "readiness": {"comparable": 1, "unverified": 1, "research_only": 0, "incomplete": 0, "none": 1},
            "annual_producers": [
                {"model_version": "vet_v1", "csv": "x.csv", "seasons": 2, "evidence": {"verified": False, "reason": "unverified: manifest declares no sha256 for the scoring CSV (outputs_sha256)"}},
                {"model_version": "rookie_v3", "csv": "y.csv", "seasons": 6, "evidence": {"verified": True, "reason": "verified"}},
                {"model_version": "union_replacement", "seasons": 2, "positions_without_a_bar": [],
                 "replacement": {"QB": [{"player_name": "Spencer Rattler", "rate_ppg": 106.6, "pool_complete": True, "pool_note": None},
                                        {"player_name": "Spencer Rattler", "rate_ppg": 91.2, "pool_complete": True, "pool_note": None}]}},
            ],
            "davids_roster": [
                {"player_id": "m", "sleeper_id": "13269", "name": "Fernando Mendoza", "position": "QB", "team": "LV", "age": 22,
                 "value": 280.3, "readiness": "comparable", "reason": None, "producer": "rookie_v3", "estimate_class": "candidate",
                 "evidence_verified": True, "served_dvs": 70.73, "reference_player": "Spencer Rattler",
                 "reference_expected_points": 106.6, "on_davids_roster": True, "rostered_by": 1,
                 "seasons": [{"season": 2026, "expected_margin": 107.9, "action": "retain", "advantage": 107.9},
                             {"season": 2027, "expected_margin": 172.4, "action": "retain", "advantage": 172.4}]},
                {"player_id": "d", "sleeper_id": "12508", "name": "Jaxson Dart", "position": "QB", "team": "NYG", "age": 23,
                 "value": 261.4, "readiness": "unverified", "reason": "unverified: the producer's evidence identity could not be verified (unverified: manifest declares no sha256 for the scoring CSV (outputs_sha256))",
                 "producer": "vet_v1", "estimate_class": "candidate", "evidence_verified": False, "served_dvs": 76.4,
                 "reference_player": "Spencer Rattler", "reference_expected_points": 106.6, "on_davids_roster": True, "rostered_by": 1,
                 "seasons": [{"season": 2026, "expected_margin": 102.1, "action": "retain", "advantage": 102.1},
                             {"season": 2027, "expected_margin": 96.2, "action": "retain", "advantage": 96.2}]},
                {"player_id": "t", "sleeper_id": "9484", "name": "Tank Dell", "position": "WR", "team": "HOU", "age": 26,
                 "value": None, "readiness": "none", "reason": "not forecast by any annual producer (vet_v1, rookie_v3); a veteran without a 2025 feature row or an undrafted rookie",
                 "producer": "annual_target", "estimate_class": "candidate", "evidence_verified": False, "served_dvs": None,
                 "reference_player": None, "reference_expected_points": None, "on_davids_roster": True, "rostered_by": 1, "seasons": []},
            ],
            "league_rostered": [], "top": [], "all_inspectable": [],
        },
    }


@pytest.fixture
def client(tmp_path, monkeypatch):
    run = tmp_path / "runs" / "20260906T000000Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(_report()))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    return TestClient(app)


def test_the_route_serves_the_latest_local_run_and_names_its_source(client) -> None:
    r = client.get("/api/research/preview")
    assert r.status_code == 200
    body = r.json()
    assert body["source"]["kind"] == "local_research_run"
    assert body["source"]["run"] == "20260906T000000Z"
    assert body["basis"]["horizons_summed"] == 2
    assert "two-year" in body["basis"]["label"].lower()
    assert body["basis"]["is_complete_dynasty_value"] is False


def test_reasons_become_fantasy_sentences_with_the_raw_reason_kept(client) -> None:
    body = client.get("/api/research/preview").json()
    by = {p["name"]: p for p in body["roster"]}
    assert by["Tank Dell"]["value"] is None
    # the superseded "no 2025 stat line" claim is gone: a missing veteran is a missing forecast, reason stated or not
    assert "2025" not in by["Tank Dell"]["status_sentence"] and "raw_reason" in by["Tank Dell"]
    assert by["Tank Dell"]["status_sentence"].startswith("No forecast from the selected producers for this window")
    assert "not a zero" in by["Tank Dell"]["status_sentence"]
    assert "inspection only" in by["Jaxson Dart"]["status_sentence"].lower() and by["Jaxson Dart"]["evidence_verified"] is False
    assert "hash" not in by["Jaxson Dart"]["status_sentence"].split(":")[0]  # jargon stays out of the lead clause
    assert by["Fernando Mendoza"]["value"] == 280.3 and by["Fernando Mendoza"]["seasons"][0]["action"] == "retain"


def test_the_replacement_reference_is_named_per_position(client) -> None:
    body = client.get("/api/research/preview").json()
    assert body["reference"]["QB"]["player"] == "Spencer Rattler"
    assert body["reference"]["QB"]["expected_points_by_season"] == [106.6, 91.2]


def test_a_missing_run_is_a_404_not_an_empty_board(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "nowhere"))
    from app.main import app

    r = TestClient(app).get("/api/research/preview")
    assert r.status_code == 404
    assert "no research run" in r.json()["detail"]  # the route's own refusal, not a missing route


def test_a_longer_horizon_view_is_served_beside_the_two_year_one_with_its_evidence(tmp_path, monkeypatch) -> None:
    rep = _report()
    rep["horizon_board"] = {
        "n_comparable": 1, "horizons_summed": 5,
        "readiness": {"comparable": 1, "unverified": 0, "research_only": 0, "incomplete": 0, "none": 1},
        "annual_producers": [
            {"model_version": "vet_basic", "csv": "b.csv", "seasons": 5, "evidence": {"verified": True, "reason": "verified"},
             "evidence_notes": {"QB|season1": "beats the training-only baseline on unconditional points (out-of-time RMSE 70.8 vs 75.6); graded on 14 folds",
                                "QB|season5": "beats the training-only baseline on unconditional points (out-of-time RMSE 81.4 vs 86.6); graded on ONE fold"}},
            {"model_version": "union_replacement", "seasons": 5, "positions_without_a_bar": [],
             "replacement": {"QB": [{"player_name": "Joe Flacco", "rate_ppg": 121.0, "pool_complete": True, "pool_note": None}] * 5}},
        ],
        "davids_roster": [dict(rep["comparable_board"]["davids_roster"][0], value=731.0,
                               seasons=[{"season": 2026 + h, "expected_margin": 100.0, "action": "retain", "advantage": 100.0} for h in range(5)])],
        "league_rostered": [], "top": [], "all_inspectable": [],
    }
    rep["comparable_views"] = {"h2": "comparable_board", "h5": "horizon_board"}
    run = tmp_path / "runs" / "20260906T000001Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(rep))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    body = TestClient(app).get("/api/research/preview").json()
    assert [v["key"] for v in body["views"]] == ["h2", "h5"]
    five = next(v for v in body["views"] if v["key"] == "h5")
    assert five["basis"]["horizons_summed"] == 5 and "five-year" in five["basis"]["label"].lower()
    assert five["roster"][0]["value"] == 731.0 and len(five["roster"][0]["seasons"]) == 5
    assert any("graded once" in s for s in five["evidence_sentences"])
    assert five["reference"]["QB"]["player"] == "Joe Flacco"


def _round3_report():
    """A report with both views, the producers' evaluation status, the eligible census on the
    reference, and a player (Dell) absent from the two-year view but on the five-year one."""
    rep = _report()
    two = rep["comparable_board"]
    two["annual_producers"][0]["evidence"] = {"verified": True, "reason": "verified: scoring, history and evaluation bytes match",
                                             "meaning": "source check: file identity, not scientific validation",
                                             "bound_files": {"scoring": "x.csv", "history": "historical_predictions.csv", "evaluation": "results.json"}}
    two["annual_producers"][0]["evaluation_status"] = {
        "source": "x.evaluation_status.json", "meaning": {"supported": "closed history sufficient to evaluate; not validation"},
        "seasons": {"1": {"summary": "evaluated on 3 folds; beats its training-only baseline within the 90% interval at 2 of 4 positions",
                          "positions": {"QB": {"folds": 3, "improvement": "inconclusive: the 90% interval includes zero"},
                                        "RB": {"folds": 3, "improvement": "within the reported 90% interval"}}},
                    "2": {"summary": "not evaluated: zero historical folds at every position",
                          "positions": {"QB": {"folds": 0, "improvement": "not graded: zero evaluated policy folds"}}}}}
    two["annual_producers"][2]["replacement"]["QB"][0].update({
        "reference_scope": "best among players with a forecast", "unforecast_eligible": 368,
        "unforecast_reasons": {"no_gsis_mapping": 149}, "census_complete": False,
        "pool_note": "best among players with a forecast; 368 eligible unrostered QB have no forecast and may change the reference",
        "horizon_note": "Scenario: the same player who is available today is assumed in every future season; not a claim about future waiver access."})
    two["annual_producers"].append({"model_version": "assembled_grading", "assembled_grading": {
        "run": "20260906T163059Z", "reference_rule": "each arm subtracts its own forecast of the reference",
        "interval_meaning": "90% bootstrap over players, conditional on this observed cohort and its reference",
        "seasons": {"1": {"joint": {"status": "graded", "n": 1695, "by_position": {
            "QB": {"folds": 3, "n": 100, "decision_value": 12354.0, "baseline_decision_value": 11054.0,
                   "folds_interval_above_zero": 2, "folds_interval_below_zero": 0, "folds_interval_spanning_zero": 1}}},
                          "veteran": {"status": "graded", "n": 1459, "by_position": {
            "QB": {"folds": 3, "n": 90, "decision_value": 10915.0, "baseline_decision_value": 11054.0,
                   "folds_interval_above_zero": 0, "folds_interval_below_zero": 1, "folds_interval_spanning_zero": 2}}}},
                    "2": {"joint": {"status": "not graded: the selected policy scored no fold at this season", "n": 0, "by_position": {}}}},
        "sums": {"2": {"joint": {"status": "not graded: no origin has the selected policy's forecast for every season", "origins": [], "n": 0,
                                 "cells_interval_above_zero": 0, "cells_interval_below_zero": 0, "cells_interval_spanning_zero": 0}}}}})
    rep["horizon_board"] = {
        "n_comparable": 2, "horizons_summed": 5,
        "readiness": {"comparable": 2, "unverified": 0, "research_only": 0, "incomplete": 0, "none": 0},
        "annual_producers": [
            {"model_version": "vet_basic", "csv": "b.csv", "seasons": 5, "evidence": {"verified": True, "reason": "verified"},
             "evaluation_status": {"source": "b.evaluation_status.json", "seasons": {
                 str(j): {"summary": f"evaluated on {f} folds; beats its training-only baseline within the 90% interval at 4 of 4 positions", "positions": {}}
                 for j, f in ((1, 14), (2, 12), (3, 9), (4, 5))} | {
                 "5": {"summary": "evaluated on 1 fold; beats its training-only baseline within the 90% interval at 2 of 4 positions; a single fold is not support", "positions": {}}}}},
            {"model_version": "union_replacement", "seasons": 5, "positions_without_a_bar": [],
             "replacement": {"QB": [{"player_name": "Joe Flacco", "rate_ppg": 121.0, "pool_complete": True, "pool_note": None}] * 5}},
        ],
        "davids_roster": [dict(two["davids_roster"][0], value=731.0,
                               seasons=[{"season": 2026 + h, "expected_margin": 100.0, "action": "retain", "advantage": 100.0} for h in range(5)]),
                          dict(two["davids_roster"][2], value=0.0, readiness="comparable", reason=None, producer="vet_basic",
                               seasons=[{"season": 2026 + h, "expected_margin": -80.0, "action": "replace", "advantage": 0.0} for h in range(5)])],
        "league_rostered": [], "top": [], "all_inspectable": [],
    }
    rep["comparable_views"] = {"h2": "comparable_board", "h5": "horizon_board"}
    return rep


@pytest.fixture
def round3_client(tmp_path, monkeypatch):
    run = tmp_path / "runs" / "20260906T000002Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(_round3_report()))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    return TestClient(app)


def test_file_identity_and_historical_evaluation_are_separate_facts_per_producer(round3_client) -> None:
    two = round3_client.get("/api/research/preview").json()["views"][0]
    vet = next(p for p in two["producers"] if p["name"] == "vet_v1")
    assert vet["label"] == "veteran forecast"
    assert vet["identity"]["verified"] is True and "not scientific validation" in vet["identity"]["meaning"]
    assert vet["identity"]["bound_files"]["history"] == "historical_predictions.csv"
    ev = vet["historical_evaluation"]["by_season"]
    assert ev["1"]["status"] == "evaluated" and ev["1"]["positions"]["QB"]["improvement"].startswith("inconclusive")
    assert ev["2"]["status"] == "not_evaluated"
    # the adjacent plain statement, on the view itself
    assert two["support_sentence"] == ("The veteran forecast: season 1 has some historical support; season 2 is experimental "
                                       "and has not been evaluated. The rookie forecast carries no per-season historical "
                                       "evaluation on this file.")


def test_the_reference_states_its_scope_and_the_unforecast_eligible_count(round3_client) -> None:
    two = round3_client.get("/api/research/preview").json()["views"][0]
    qb = two["reference"]["QB"]
    assert qb["scope"] == "best among players with a forecast" and qb["unforecast_eligible"] == 368
    assert qb["census_complete"] is False and "may change the reference" in qb["note"]
    assert "not a claim about future waiver access" in qb["horizon_note"]


def test_a_missing_reason_describes_this_views_coverage_and_points_at_the_view_that_has_him(round3_client) -> None:
    body = round3_client.get("/api/research/preview").json()
    two, five = body["views"]
    dell2 = next(p for p in two["roster"] if p["name"] == "Tank Dell")
    assert dell2["other_view"] == {"view": "h5", "label": "5-year", "seasons_word": "five", "value": 0.0}
    assert "five-year view does carry him" in dell2["status_sentence"] and "no producer has" not in dell2["status_sentence"]
    assert "2025" not in dell2["status_sentence"]  # never claims a missing veteran lacks a 2025 line
    dell5 = next(p for p in five["roster"] if p["name"] == "Tank Dell")
    assert dell5["readiness"] == "comparable" and dell5["other_view"] is None


def test_the_served_score_is_labelled_as_a_different_scale_and_the_estimate_is_not_advice(round3_client) -> None:
    two = round3_client.get("/api/research/preview").json()["views"][0]
    m = next(p for p in two["roster"] if p["name"] == "Fernando Mendoza")
    assert m["served_value"] == 70.73 and m["served_value_label"].startswith("Existing app score (0-100")
    assert m["status_sentence"].endswith("not drop or trade advice.")
    assert "not a recommendation to drop, trade or start" in two["basis"]["advice_note"]


def test_the_assembled_grading_reaches_the_view_with_the_two_season_sum_stated_as_ungradeable(round3_client) -> None:
    two = round3_client.get("/api/research/preview").json()["views"][0]
    assert two["assembled_grading"]["run"] == "20260906T163059Z"
    joined = " ".join(two["assembled_grading_sentences"])
    assert "Season 1, both forecasts together" in joined and "QB above baseline in total over 3 folds (2 clearly above, 0 clearly below, 1 indistinguishable)" in joined
    assert "the veteran forecast alone" in joined and "QB below baseline in total over 3 folds" in joined
    assert "Season 2: the assembled value could not be graded" in joined
    assert "2-season sum from one origin cannot be graded" in joined
    assert "conditional on this observed cohort" in joined


def test_a_view_says_when_its_reference_differs_from_the_other_views_reference(round3_client) -> None:
    two, five = round3_client.get("/api/research/preview").json()["views"]
    assert "QB Spencer Rattler here vs Joe Flacco on the 5-year view" in two["cross_view_note"]
    assert "owe the swing to the reference" in two["cross_view_note"]
    assert "QB Joe Flacco here vs Spencer Rattler on the 2-year view" in five["cross_view_note"]


def test_a_model_comparison_is_served_in_the_details_never_as_a_horizon_view(tmp_path, monkeypatch) -> None:
    rep = _round3_report()
    # the legacy annual model becomes a comparison; the horizon views share one term set
    rep["model_comparison_board"] = dict(rep["comparable_board"], label="Two-year impact from the legacy veteran model")
    rep["model_comparisons"] = {"legacy_annual_2y": "model_comparison_board"}
    rep["composition_consistency"] = {"players_checked": 800, "violations": 0, "rule": "prefix sum"}
    run = tmp_path / "runs" / "20260906T000003Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(rep))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    body = TestClient(app).get("/api/research/preview").json()
    assert [v["key"] for v in body["views"]] == ["h2", "h5"]
    assert body["composition"]["consistency"]["violations"] == 0 and "prefix sum" in body["composition"]["rule"]
    cmp = body["model_comparisons"][0]
    assert cmp["key"] == "legacy_annual_2y" and cmp["kind"] == "model_comparison"
    assert cmp["label"].startswith("Two-year impact from the legacy veteran model")
    assert cmp["roster"][0]["name"] == "Fernando Mendoza" and cmp["roster"][0]["value"] == 280.3


def test_a_wr_eligible_player_the_veteran_model_excludes_gets_the_true_reason_and_no_number(tmp_path, monkeypatch) -> None:
    rep = _round3_report()
    rep["comparable_board"]["league_rostered"] = [
        {"player_id": "h", "sleeper_id": "12530", "name": "Travis Hunter", "position": "WR", "team": "JAX", "age": 23,
         "value": None, "readiness": "none",
         "reason": "not forecast by any annual producer (vet_v1, rookie_v3); the producer's stated reason: "
                   "veteran_basic: position_outside_modelled_set (source position CB)",
         "fantasy_positions": ["DB", "WR"], "placement_source": "sleeper_fantasy_positions", "nfl_status": "Active",
         "producer": "annual_target", "estimate_class": "candidate", "evidence_verified": False, "served_dvs": None,
         "reference_player": None, "reference_expected_points": None, "on_davids_roster": False, "rostered_by": 5, "seasons": []}]
    run = tmp_path / "runs" / "20260906T000004Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(rep))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    two = TestClient(app).get("/api/research/preview").json()["views"][0]
    hunter = next(p for p in two["league"] if p["name"] == "Travis Hunter")
    assert hunter["value"] is None and hunter["readiness"] == "none"
    assert hunter["status_sentence"] == ("Sleeper allows WR (DB|WR), but the veteran model currently excludes his two-position "
                                         "history (its source position is CB); no forecast yet.")
    assert "2025" not in hunter["status_sentence"] and "draftee" not in hunter["status_sentence"]
    assert hunter["fantasy_positions"] == ["DB", "WR"] and hunter["nfl_status"] == "Active"


def test_the_scoring_window_sentence_follows_the_boards_typed_window(tmp_path, monkeypatch) -> None:
    rep = _round3_report()
    rep["board_target"] = dict(rep["board_target"], window="championship_week17", scoring="PPR_nflverse_default")
    run = tmp_path / "runs" / "20260906T000005Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(rep))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    two = TestClient(app).get("/api/research/preview").json()["views"][0]
    s = two["basis"]["scoring_window"]
    assert s.startswith("Forecasts are points through the championship week (NFL Week 17) since 2021")
    assert "Week 16" in s and "equal weekly weighting" in s and "not David's exact league scoring" in s
    assert "no exact-match claim" in s and "not yet a forecast of David's fantasy weeks" not in s
    assert "research preset nflverse_default_ppr_championship_window_v1" in s
    # the full-season default still carries the old limitation
    old = _round3_report()
    run2 = tmp_path / "runs" / "20260906T000006Z" / "dg178_audit"
    run2.mkdir(parents=True)
    (run2 / "report.json").write_text(json.dumps(old))
    s2 = TestClient(app).get("/api/research/preview").json()["views"][0]["basis"]["scoring_window"]
    assert "not yet a forecast of David's fantasy weeks" in s2 and "championship in NFL Week 17" in s2


def test_the_served_run_can_be_pinned_so_a_new_candidate_run_does_not_replace_the_comparator(tmp_path, monkeypatch) -> None:
    """Codex: keep the accepted preview running until a new candidate is validated. The route
    serves the newest run by default; DG178_PREVIEW_RUN pins the default to the comparator, and
    ?run= still opens any run for QA."""
    older, newer = _report(), _report()
    newer["comparable_board"]["davids_roster"][0]["value"] = 999.0
    for rid, rep in (("20260906T000010Z", older), ("20260906T000011Z", newer)):
        run = tmp_path / "runs" / rid / "dg178_audit"
        run.mkdir(parents=True)
        (run / "report.json").write_text(json.dumps(rep))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    c = TestClient(app)
    assert c.get("/api/research/preview").json()["source"]["run"] == "20260906T000011Z"
    monkeypatch.setenv("DG178_PREVIEW_RUN", "20260906T000010Z")
    body = c.get("/api/research/preview").json()
    assert body["source"]["run"] == "20260906T000010Z" and body["source"]["pinned"] is True
    cand = c.get("/api/research/preview", params={"run": "20260906T000011Z"}).json()
    assert cand["source"]["run"] == "20260906T000011Z" and cand["roster"][0]["value"] == 999.0
    assert c.get("/api/research/preview", params={"run": "nope"}).status_code == 404


def test_the_shared_outcome_artifacts_qualification_reaches_the_page_as_research_not_complete_data(tmp_path, monkeypatch) -> None:
    rep = _round3_report()
    rep["board_target"] = dict(rep["board_target"], window="championship_week17", scoring="PPR_nflverse_default",
                               exposure="stat_record_weeks_in_window")
    rep["outcome_artifact"] = {"schema_version": "dg179_league_season_outcomes_v1",
                               "scoring_preset": "nflverse_default_ppr_championship_window_v1",
                               "target_identity": "c" * 64, "scoring_identity": "a" * 64, "window_identity": "b" * 64,
                               "source_identity_sha256": "8" * 64, "outcomes_csv_sha256": "1" * 64, "manifest_sha256": "2" * 64,
                               "coverage_status": "qualified_research_game_complete_identified_rows", "research_qualified": True,
                               "qualification_note": "research qualification: ...", "last_complete_season": 2025,
                               "admitted_seasons": [2001, 2025], "league_scoring_exact": False,
                               "exact_league_scoring_gaps": {"fumble_lost_all_units": "not attributed"},
                               "source_validation_limitations": "calendar checks are not proof no record was omitted"}
    run = tmp_path / "runs" / "20260906T000007Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(rep))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    basis = TestClient(app).get("/api/research/preview").json()["views"][0]["basis"]
    art = basis["outcome_artifact"]
    assert art["research_qualified"] is True and art["coverage_status"] == "qualified_research_game_complete_identified_rows"
    assert "not proof that every individual stat is perfect" in art["qualification_sentence"]
    assert "not David's exact league scoring" in art["qualification_sentence"]
    assert "complete individual data" not in json.dumps(art)
    assert art["exact_scoring_gaps"] == ["fumble_lost_all_units: not attributed"]
    assert art["identity"]["target_identity"] == "c" * 64
    # without an artifact the field is absent-by-value, never invented
    assert TestClient(app).get("/api/research/preview", params={"run": "20260906T000007Z"}).json()["views"][0]["basis"]["outcome_artifact"] is not None


# ── Plan T3 (2026-09-06 player comparison): zero / missing / equal / near-zero, per-season detail, coverage, attachment ──
def _t3_report():
    rep = _round3_report()
    two = rep["comparable_board"]
    ref = two["annual_producers"][2]["replacement"]
    ref["RB"] = [{"player_name": "Kareem Hunt", "player_id": "00-0033923", "rate_ppg": 88.2770971070361, "pool_complete": True, "pool_note": None},
                 {"player_name": "Kareem Hunt", "player_id": "00-0033923", "rate_ppg": 46.1704555773408, "pool_complete": True, "pool_note": None}]
    ref["WR"] = [{"player_name": "Marvin Mims", "player_id": "00-0039100", "rate_ppg": 105.583, "pool_complete": True, "pool_note": None},
                 {"player_name": "Marvin Mims", "player_id": "00-0039100", "rate_ppg": 90.0, "pool_complete": True, "pool_note": None}]
    two["league_rostered"] = [
        {"player_id": "ba", "sleeper_id": "11565", "name": "Braelon Allen", "position": "RB", "team": "NYJ", "age": 22,
         "value": 0.0, "readiness": "comparable", "reason": None, "producer": "vet_v1", "estimate_class": "candidate",
         "evidence_verified": True, "served_dvs": 40.1, "reference_player": "Kareem Hunt", "reference_expected_points": 88.2770971070361,
         "on_davids_roster": False, "rostered_by": 5,
         "seasons": [{"season": 2026, "expected_margin": -53.61265642415228, "action": "replace", "advantage": 0.0},
                     {"season": 2027, "expected_margin": -3.499953259581865, "action": "replace", "advantage": 0.0}]},
        {"player_id": "tie", "sleeper_id": "2", "name": "Exact Tie", "position": "WR", "team": "KC", "age": 25,
         "value": 0.0, "readiness": "comparable", "reason": None, "producer": "vet_v1", "estimate_class": "candidate",
         "evidence_verified": True, "served_dvs": None, "reference_player": "Marvin Mims", "reference_expected_points": 105.583,
         "on_davids_roster": False, "rostered_by": 6,
         "seasons": [{"season": 2026, "expected_margin": 0.0, "action": "replace", "advantage": 0.0},
                     {"season": 2027, "expected_margin": 0.0, "action": "replace", "advantage": 0.0}]},
        {"player_id": "near", "sleeper_id": "3", "name": "Near Zero", "position": "WR", "team": "KC", "age": 25,
         "value": 0.3, "readiness": "comparable", "reason": None, "producer": "vet_v1", "estimate_class": "candidate",
         "evidence_verified": True, "served_dvs": None, "reference_player": "Marvin Mims", "reference_expected_points": 105.583,
         "on_davids_roster": False, "rostered_by": 6,
         "seasons": [{"season": 2026, "expected_margin": 0.3, "action": "retain", "advantage": 0.3},
                     {"season": 2027, "expected_margin": -0.2, "action": "replace", "advantage": 0.0}]},
        {"player_id": "miss", "sleeper_id": "4", "name": "Missing Vet", "position": "WR", "team": "KC", "age": 29,
         "value": None, "readiness": "none",
         "reason": "not forecast by any annual producer (vet_v1, rookie_v3); no producer stated a reason for this player (typically no 2025 stat line for the veteran forecast and not a 2026 draftee)",
         "producer": "annual_target", "estimate_class": "candidate", "evidence_verified": False, "served_dvs": None,
         "reference_player": None, "reference_expected_points": None, "on_davids_roster": False, "rostered_by": 7, "seasons": []},
    ]
    rep["current_census"] = {
        "run_id": "20260906T202057Z", "census_csv_sha256": "c" * 64, "report_sha256": "d" * 64, "season": 2026,
        "identity_checks": {"census_csv_sha256": True, "nflverse_roster_sha256": True, "sleeper_eligibility_sha256": True,
                            "league_snapshot_sha256": True, "season": True, "unique_sleeper_ids": True},
        "coverage": {"league_owned": {"total": 274, "in_census": 274, "absent_from_census": 0, "by_class": {"active": 256, "injured_reserve": 12, "practice_squad": 2, "exempt": 1, "no_verified_join_to_2026_roster": 3},
                                      "with_forecast": 274, "without_forecast": 0},
                     "unverified_unowned": {"by_position": {"TE": {"with_forecast": 1, "without_forecast": 2}},
                                            "note": "census members with no verified NFL join (contested or unknown identity); not counted as listed, shown separately"},
                     "listed_unowned": {"by_position": {"QB": {"active": {"with_forecast": 34, "without_forecast": 9},
                                                                "practice_squad": {"with_forecast": 8, "without_forecast": 4}}}},
                     "unmatched_nfl_records": {"count": 141, "note": "NFL skill rows no Sleeper row claims; kept separate, never added to a denominator"},
                     "uncovered_sleeper_ids": 3373, "contested_nfl_records": 1,
                     "denominator_note": "members = listed-or-owned, NOT active NFL"},
        "reference_attachment": {"QB": {"status": "active", "basis": "sleeper_id", "nfl_team": "CIN", "note": "verified join to the captured 2026 roster (ACT)"},
                                 "RB": {"status": "unverified", "basis": "no verified join",
                                        "note": "no verified join to the captured 2026 roster (Sleeper flags Active/- are not membership); absence from the NFL is not proven; Sleeper lists Active with no team"}},
    }
    rep["unforecast_eligible_census"] = {"QB": {"count": 368, "reasons": {"no_gsis_mapping": 149}}}
    return rep


@pytest.fixture
def t3_client(tmp_path, monkeypatch):
    run = tmp_path / "runs" / "20260906T000020Z" / "dg178_audit"
    run.mkdir(parents=True)
    (run / "report.json").write_text(json.dumps(_t3_report()))
    monkeypatch.setenv("DG178_RUNS_ROOT", str(tmp_path / "runs"))
    from app.main import app

    return TestClient(app)


def test_zero_missing_equal_and_near_zero_read_differently_and_are_tied_to_the_rows_seasons(t3_client) -> None:
    two = t3_client.get("/api/research/preview").json()["views"][0]
    by = {p["name"]: p for p in two["league"]}
    z = by["Braelon Allen"]["status_sentence"]
    assert z.startswith("Zero impact on this board: an actual forecast that does not exceed the next available RB")
    assert "2026: 34.7 vs 88.3" in z and "2027: 42.7 vs 46.2" in z
    assert "not missing data" in z and "not zero points" in z and "not zero trade value" in z
    assert by["Exact Tie"]["status_sentence"].startswith("Equal to the reference in both seasons shown")
    n = by["Near Zero"]["status_sentence"]
    assert "+0.3" in n and "-0.2" in n and "0 above" not in n and "0 below" not in n
    m = by["Missing Vet"]["status_sentence"]
    assert "2025" not in m and m.startswith("No forecast from the selected producers for this window")
    assert "no reason stated" in m
    assert by["Braelon Allen"]["value"] == 0.0 and by["Missing Vet"]["value"] is None


def test_each_season_carries_player_and_reference_expected_points_derived_at_full_precision(t3_client) -> None:
    two = t3_client.get("/api/research/preview").json()["views"][0]
    ba = next(p for p in two["league"] if p["name"] == "Braelon Allen")
    s0, s1 = ba["seasons"]
    assert s0["reference_expected_points"] == 88.2770971070361
    assert abs(s0["player_expected_points"] - (88.2770971070361 - 53.61265642415228)) < 1e-12
    assert abs(s1["player_expected_points"] - (46.1704555773408 - 3.499953259581865)) < 1e-12
    miss = next(p for p in two["league"] if p["name"] == "Missing Vet")
    assert miss["seasons"] == []
    # a season whose reference is absent stays absent, never derived from a rounded display value
    m = next(p for p in two["roster"] if p["name"] == "Fernando Mendoza")
    assert all("player_expected_points" in s for s in m["seasons"])


def test_coverage_is_three_separate_populations_and_the_reference_attachment_comes_from_the_census(t3_client) -> None:
    two = t3_client.get("/api/research/preview").json()["views"][0]
    cov = two["coverage"]
    assert cov["league_owned"]["total"] == 274 and cov["league_owned"]["with_forecast"] == 274
    assert cov["listed_unowned"]["by_position"]["QB"]["active"] == {"with_forecast": 34, "without_forecast": 9}
    assert cov["unmatched_nfl_records"]["count"] == 141
    assert cov["archive"]["QB"] == 368 and "inactive" in cov["archive_note"].lower()
    assert cov["census_run_id"] == "20260906T202057Z" and cov["identity_checks"]["census_csv_sha256"] is True
    sent = cov["sentences"]
    assert sent[0].startswith("Your league owns 274 players; all 274 are in the dated census")
    assert any(s.startswith("QB: of the unowned players with a verified join to the 2026 NFL roster capture") and "9 active" in s for s in sent)
    assert any(s.startswith("TE: 3 unowned census member(s) have NO verified NFL join") and "1 with a research estimate, 2 without" in s for s in sent)
    assert not any("listed on a 2026 NFL roster" in s for s in sent)  # nothing unverified is called listed
    assert any(s.startswith("1 NFL record is contested by more than one Sleeper id and is attributed to nobody") for s in sent)
    rb = two["reference"]["RB"]
    assert rb["player"] == "Kareem Hunt" and rb["nfl_attachment"]["status"] == "unverified"
    assert "absence from the NFL is not proven" in rb["nfl_attachment"]["note"]
    assert rb["sleeper_status"] == rb.get("nfl_status")  # Sleeper's flag is named as Sleeper's, not as NFL status
    assert two["reference"]["QB"]["nfl_attachment"]["status"] == "active"
