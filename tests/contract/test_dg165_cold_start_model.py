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


# ---------------------------------------------------------------- Task 6: candidate, baselines, paired evaluation, sidecar (root-frozen rules)

def _synthetic_population(seed=3, n_per_class=30, classes=range(2004, 2025)):
    """A never-record population whose appearance depends on pick and position, so the candidate has something to learn."""
    rng = np.random.default_rng(seed)
    rows = []
    for c in classes:
        for i in range(n_per_class):
            pos = ["QB", "RB", "WR", "TE"][i % 4]
            pick = int(rng.integers(1, 260))
            age = float(rng.normal(22.5, 0.8))
            row = {"gsis_id": f"{c}-{i}", "name": f"P{c}-{i}", "draft_season": c, "origin_year": c + 1, "draft_position": pos, "pick": pick,
                   "round": min(7, 1 + pick // 32), "log_pick": np.log(pick), "birth_date": None, "age_at_origin": age if i % 9 else np.nan,
                   "first_full_reg_season": None, "window_absent_through_draft_season": True}
            base = -0.5 - 0.6 * (np.log(pick) - 4.5) + (0.3 if pos == "WR" else 0.0)
            for h in range(1, 6):
                season = c + h
                if season > 2025:
                    row.update({f"appear_{h}": np.nan, f"points_{h}": np.nan, f"games_{h}": np.nan, f"label_source_{h}": "unknown"})
                    continue
                p = 1 / (1 + np.exp(-(base - 0.15 * (h - 1))))
                app = rng.random() < p
                pts = float(max(0.0, rng.normal(60 - 8 * (np.log(pick) - 4.5), 25))) if app else 0.0
                row.update({f"appear_{h}": float(app), f"points_{h}": pts, f"games_{h}": float(rng.integers(1, 17)) if app else 0.0,
                            f"label_source_{h}": "artifact" if app else "convention_zero"})
            rows.append(row)
    return pd.DataFrame(rows)


def test_fit_arms_uses_training_rows_only_and_gates_on_support():
    from src.dynasty_genius.rookie.cold_start_model import fit_arms, predict_arms
    pop = _synthetic_population()
    T, h = 2016, 1
    train = pop.loc[(pop["draft_season"] + h < T) & pop[f"appear_{h}"].notna()]
    fit = fit_arms(train, horizon=h, origin=T)
    assert fit["candidate"]["supported"] and fit["candidate"]["n_train"] == len(train) and fit["candidate"]["n_appearers"] == int(train["appear_1"].sum())
    # the age median is the TRAINING position median (fold-only), never a pooled or test statistic
    qb_median = float(train.loc[train["draft_position"] == "QB", "age_at_origin"].median())
    assert fit["candidate"]["age_median_by_position"]["QB"] == pytest.approx(qb_median)
    test = pop.loc[pop["draft_season"] == T - 1].copy()
    pred = predict_arms(fit, test)
    assert set(pred.columns) >= {"candidate_p_appear", "candidate_e_points", "candidate_e_points_given_appear", "candidate_e_games", "candidate_supported",
                                 "b1_p_appear", "b1_e_points", "b1_e_points_given_appear", "b1_supported", "b2_p_appear", "b2_e_points", "b2_supported"}
    assert pred["candidate_p_appear"].between(0, 1).all() and np.isfinite(pred["candidate_e_points"]).all()
    # unsupported: too few training rows -> no numbers at all
    tiny = fit_arms(train.head(30), horizon=h, origin=T)
    assert not tiny["candidate"]["supported"] and "60" in tiny["candidate"]["reason"]
    pt = predict_arms(tiny, test)
    assert pt["candidate_p_appear"].isna().all() and (~pt["candidate_supported"]).all()
    # one appearance class only -> unsupported, even with many rows
    one_class = train.assign(**{"appear_1": 0.0, "points_1": 0.0})
    assert not fit_arms(one_class, horizon=h, origin=T)["candidate"]["supported"]


def test_b1_reports_per_position_denominators_and_never_zero_fills():
    from src.dynasty_genius.rookie.cold_start_model import fit_arms, predict_arms
    pop = _synthetic_population()
    train = pop.loc[(pop["draft_season"] + 1 < 2016) & pop["appear_1"].notna()].copy()
    train = train.loc[~((train["draft_position"] == "TE") & (train["appear_1"] == 1.0))]  # TE: rows but zero appearers
    train = pd.concat([train.loc[train["draft_position"] != "QB"], train.loc[train["draft_position"] == "QB"].head(5)])  # QB: only 5 rows
    fit = fit_arms(train, horizon=1, origin=2016)
    cells = fit["b1"]["cells"]
    assert cells["TE"]["n"] >= 10 and cells["TE"]["appearers"] == 0 and cells["TE"]["supported"] and cells["TE"]["conditional_supported"] is False
    assert cells["TE"]["p_appear"] == 0.0 and cells["TE"]["e_points"] == 0.0 and cells["TE"]["e_points_given_appear"] is None
    assert cells["QB"]["n"] == 5 and cells["QB"]["supported"] is False and "10" in cells["QB"]["reason"]
    test = pd.DataFrame({"gsis_id": ["x", "y", "z"], "draft_position": ["TE", "QB", "WR"], "log_pick": [3.0, 3.0, 3.0], "round": [2, 2, 2],
                         "age_at_origin": [22.0, 22.0, 22.0]})
    pred = predict_arms(fit, test).set_index("gsis_id")
    assert pred.loc["x", "b1_p_appear"] == 0.0 and pd.isna(pred.loc["x", "b1_e_points_given_appear"]) and bool(pred.loc["x", "b1_supported"])
    assert pd.isna(pred.loc["y", "b1_p_appear"]) and not bool(pred.loc["y", "b1_supported"])  # unseen/under-supported position: no number
    assert bool(pred.loc["z", "b1_supported"]) and 0 < pred.loc["z", "b1_p_appear"] < 1
    # B2 carries no age: identical predictions when age changes
    a = predict_arms(fit, test.assign(age_at_origin=[22.0, 22.0, 22.0]))
    b = predict_arms(fit, test.assign(age_at_origin=[30.0, 30.0, 30.0]))
    assert np.allclose(a["b2_p_appear"].fillna(-1), b["b2_p_appear"].fillna(-1))
    assert not np.allclose(a["candidate_p_appear"].fillna(-1), b["candidate_p_appear"].fillna(-1))


def test_evaluate_uses_the_same_paired_rows_selects_per_horizon_and_is_deterministic():
    from src.dynasty_genius.rookie.cold_start_model import evaluate_candidate
    pop = _synthetic_population()
    ev = evaluate_candidate(pop, origins=range(2012, 2026), horizons=(1, 2), seed=11, draws=60)
    ev2 = evaluate_candidate(pop, origins=range(2012, 2026), horizons=(1, 2), seed=11, draws=60)
    assert json.dumps(ev["horizons"], sort_keys=True) == json.dumps(ev2["horizons"], sort_keys=True)
    h1 = ev["horizons"]["1"]
    assert h1["paired_rows"] > 0 and h1["paired_rows"] == h1["arms"]["candidate"]["n"] == h1["arms"]["b1"]["n"] == h1["arms"]["b2"]["n"]
    assert set(h1["arms"]["candidate"]) >= {"brier", "rmse_points", "mae_points", "bias_points", "n"}
    d = h1["paired_vs_b1"]
    assert set(d) >= {"brier_diff", "rmse_points_diff"} and set(d["brier_diff"]) >= {"point", "lo", "hi"}
    assert h1["selection"] in {"cold_start_candidate", "baseline_research_candidate"}
    rule = (d["brier_diff"]["hi"] < 0) and (d["rmse_points_diff"]["hi"] < 0)
    assert h1["selection"] == ("cold_start_candidate" if rule else "baseline_research_candidate")
    assert "retrospective" in ev["caveats"]["selection"] and "not conditioned on remaining on a current roster" in ev["caveats"]["population"]
    assert len(h1["by_origin"]) >= 5 and "QB" in h1["by_position"] and "reliability" in h1["calibration"]["candidate"]
    assert h1["support"]["excluded_rows_unsupported"] >= 0


def test_sidecar_exports_per_horizon_classes_seasons_and_refuses_unknown_players(tmp_path):
    from src.dynasty_genius.rookie.cold_start_model import export_sidecar
    seven = pd.DataFrame({"sleeper_id": ["1", "2"], "gsis_id": ["g1", "g2"], "name": ["A", "B"], "draft_position": ["QB", "WR"],
                          "route": ["never_appeared_drafted"] * 2, "draft_status": ["drafted_verified"] * 2, "draft_season": [2025, 2025],
                          "identity_status": ["verified_nfl_join"] * 2})
    binding = {"origin_year": 2026, "capture_manifest_sha256": "a" * 64, "artifact_sha256": "b" * 64, "cohort_sha256": "c" * 64, "coverage_run": "runs/x"}
    preds = pd.DataFrame({"gsis_id": ["g1", "g2"], **{f"candidate_p_appear_{h}": [0.3, 0.4] for h in range(1, 6)},
                          **{f"candidate_e_points_given_appear_{h}": [50.0, 60.0] for h in range(1, 6)},
                          **{f"candidate_e_points_{h}": [15.0, 24.0] for h in range(1, 6)}, **{f"candidate_e_games_{h}": [3.0, 4.0] for h in range(1, 6)},
                          **{f"candidate_e_games_given_appear_{h}": [10.0, 10.0] for h in range(1, 6)}, **{f"b1_e_games_given_appear_{h}": [10.0, 10.0] for h in range(1, 6)},
                          **{f"b1_p_appear_{h}": [0.2, 0.25] for h in range(1, 6)}, **{f"b1_e_points_given_appear_{h}": [40.0, np.nan] for h in range(1, 6)},
                          **{f"b1_e_points_{h}": [8.0, 10.0] for h in range(1, 6)}, **{f"b1_e_games_{h}": [2.0, 2.5] for h in range(1, 6)},
                          **{f"candidate_supported_{h}": [True, True] for h in range(1, 6)}, **{f"b1_supported_{h}": [True, True] for h in range(1, 6)}})
    selected = {1: "cold_start_candidate", 2: "baseline_research_candidate", 3: "baseline_research_candidate", 4: "unsupported", 5: "unsupported"}
    side = export_sidecar(seven, preds, selected_per_horizon=selected, origin_year=2026, binding=binding)
    by = side.set_index("gsis_id")
    assert by.loc["g1", "estimate_class_year1"] == "cold_start_candidate" and by.loc["g1", "p_appear_year1"] == 0.3 and by.loc["g1", "e_points_year1"] == 15.0
    assert by.loc["g1", "estimate_class_year2"] == "baseline_research_candidate" and by.loc["g1", "p_appear_year2"] == 0.2 and by.loc["g1", "e_points_year2"] == 8.0
    assert by.loc["g2", "estimate_class_year2"] == "unsupported" and pd.isna(by.loc["g2", "e_points_year2"])  # B1 conditional unsupported -> explicit unsupported, never a partial path
    assert by.loc["g1", "estimate_class_year4"] == "unsupported" and pd.isna(by.loc["g1", "p_appear_year4"]) and pd.isna(by.loc["g1", "e_points_year4"])
    assert [int(by.loc["g1", f"season_year{j}"]) for j in range(1, 6)] == [2026, 2027, 2028, 2029, 2030]
    with pytest.raises(ValueError, match="prediction"):
        export_sidecar(seven.assign(gsis_id=["g1", "g9"]), preds, selected_per_horizon=selected, origin_year=2026, binding=binding)


# ---------------------------------------------------------------- Task 6: unresolved list and the immutable run writer

def test_unresolved_from_ledger_names_a_reason_and_next_experiment_per_route():
    from src.dynasty_genius.rookie.cold_start_model import unresolved_from_ledger
    ledger = pd.DataFrame({"sleeper_id": ["1", "2", "3", "4", "5", "6", "7"], "name": ["Cand", "UDF", "Dorm", "DormN", "Join", "Conf", "Held"],
                           "gsis_id": ["g1", "g2", "g3", "g4", "g5", "g6", "g7"], "league_position": ["QB", "WR", "RB", "TE", "RB", "WR", "RB"],
                           "draft_status": ["drafted_verified", "no_draft_record_2_sources", "drafted_verified", "no_draft_record_3_sources",
                                            "drafted_verified", "draft_sources_conflict", "no_history_in_held_sources"],
                           "draft_position": ["QB", None, "FB", None, None, None, None],
                           "route": ["never_appeared_drafted", "never_appeared_no_draft_record", "dormant_drafted", "dormant_no_draft_record",
                                     "existing_forecast_join_failure", "draft_sources_conflict_unresolved", "no_held_source_history"],
                           "entry_season": [2025, 2026, 2019, 2020, 2016, 2024, 2026]})
    un = unresolved_from_ledger(ledger, candidate_ids={"g1"}).set_index("gsis_id")
    assert "g1" not in un.index and len(un) == 6
    assert un.loc["g3", "why"].startswith("draft position FB") and "skill" in un.loc["g3", "why"]
    assert "recovery sidecar" in un.loc["g5", "why"]
    for pid in ("g2", "g3", "g4", "g6", "g7"):
        assert un.loc[pid, "smallest_next_experiment"] and un.loc[pid, "status"] == "unresolved"
    assert un.loc["g5", "status"] == "recovered_existing_forecast"


def test_write_candidate_run_is_immutable_and_binds_inputs(tmp_path):
    from src.dynasty_genius.rookie.cold_start_model import (
        evaluate_candidate,
        export_sidecar,
        support_table,
        write_candidate_run,
    )
    pop = _synthetic_population()
    ev = evaluate_candidate(pop, origins=range(2012, 2026), horizons=(1,), seed=1, draws=20)
    frame = ev.pop("paired_rows_frame")
    binding = {"origin_year": 2026, "capture_manifest_sha256": "a" * 64, "artifact_sha256": "b" * 64, "cohort_sha256": "c" * 64, "coverage_run": "runs/x"}
    sidecar = export_sidecar(pd.DataFrame({"sleeper_id": ["s"], "gsis_id": ["2024-0"], "name": ["X"], "draft_position": ["QB"], "route": ["never_appeared_drafted"],
                                           "draft_status": ["drafted_verified"], "draft_season": [2025], "identity_status": ["verified_nfl_join"]}),
                             pd.DataFrame({"gsis_id": ["2024-0"], **{f"{a}_p_appear_{h}": [0.5] for a in ("candidate", "b1") for h in range(1, 6)},
                                           **{f"{a}_e_points_given_appear_{h}": [40.0] for a in ("candidate", "b1") for h in range(1, 6)},
                                           **{f"{a}_e_points_{h}": [20.0] for a in ("candidate", "b1") for h in range(1, 6)},
                                           **{f"{a}_e_games_given_appear_{h}": [8.0] for a in ("candidate", "b1") for h in range(1, 6)},
                                           **{f"{a}_e_games_{h}": [4.0] for a in ("candidate", "b1") for h in range(1, 6)},
                                           **{f"{a}_supported_{h}": [True] for a in ("candidate", "b1") for h in range(1, 6)}}),
                             selected_per_horizon={1: "cold_start_candidate"}, origin_year=2026, binding=binding)
    out = tmp_path / "runs" / "20990101T000000Z" / "dg165_cold_start_candidate"
    out.mkdir(parents=True)
    manifest = write_candidate_run(out, population=pop, support=support_table(pop, origins=(2016,), horizons=(1,)), evaluation=ev,
                                   paired_rows=frame, sidecar=sidecar, unresolved=pd.DataFrame({"gsis_id": []}),
                                   inputs={"capture": {"manifest_sha256": "a" * 64, "files": {"raw/x.parquet": "b" * 64}}}, git_sha="abc")
    for name, sha in manifest["outputs_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == sha
    assert {"population.csv", "support.csv", "evaluation.json", "paired_rows.csv", "cold_start_estimates.csv", "unresolved.csv", "REPORT.md"} <= set(manifest["outputs_sha256"])
    assert manifest["inputs"]["capture"]["manifest_sha256"] == "a" * 64 and manifest["selection_rule"] and manifest["caveats"]["population"]
    report = (out / "REPORT.md").read_text()
    assert "retrospective" in report and "not conditioned on remaining on a current roster" in report and "breakout" not in report.lower().replace("not a breakout", "")
    with pytest.raises(FileExistsError):
        write_candidate_run(out, population=pop, support=support_table(pop, origins=(2016,), horizons=(1,)), evaluation=ev, paired_rows=frame,
                            sidecar=sidecar, unresolved=pd.DataFrame({"gsis_id": []}), inputs={}, git_sha="abc")


# ---------------------------------------------------------------- root pre-fit review of the population builder (2026-09-06)

def test_population_requires_an_affirmative_resolved_identity(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
    )
    first = first_full_reg_season(capture)
    cohort = pd.concat([_cohort(), pd.DataFrame({"gsis_id": ["unresolved:2015:10"], "draft_season": [2015], "position": ["WR"], "pick": [10], "round": [1],
                                                  "age_at_draft": [22.0], "team": ["X"], "name": ["Ghost"], "label_basis": [None], "position_current": [None]})])
    pop = never_record_population(cohort=cohort, first_reg=first, outcomes=_artifact(), players=_players(), last_complete_season=2025)
    assert "unresolved:2015:10" not in set(pop["gsis_id"])
    with pytest.raises(ValueError, match="label_basis"):
        never_record_population(cohort=_cohort().drop(columns=["label_basis"]), first_reg=first, outcomes=_artifact(), players=_players(), last_complete_season=2025)
    bad_id = _cohort().assign(gsis_id=["00-A", "00-B", "C", "00-W", "00-P", "00-OLD"], label_basis=["nflverse_gsis"] * 6)
    with pytest.raises(ValueError, match="gsis"):
        never_record_population(cohort=bad_id, first_reg=first, outcomes=_artifact(), players=_players(), last_complete_season=2025)


def test_population_refuses_duplicate_cohort_identity_or_draft_keys(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
    )
    first = first_full_reg_season(capture)
    dup_id = pd.concat([_cohort(), _cohort().iloc[[2]]])
    with pytest.raises(ValueError, match="duplicate"):
        never_record_population(cohort=dup_id, first_reg=first, outcomes=_artifact(), players=_players(), last_complete_season=2025)
    dup_key = _cohort().copy()
    dup_key.loc[dup_key.gsis_id == "00-P", ["draft_season", "pick"]] = [2015, 90]  # same (season, pick) as C
    with pytest.raises(ValueError, match="duplicate"):
        never_record_population(cohort=dup_key, first_reg=first, outcomes=_artifact(), players=_players(), last_complete_season=2025)


def test_labels_parse_booleans_strictly_and_refuse_malformed_closed_rows(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
        support_table,
    )
    first = first_full_reg_season(capture)
    art = _artifact().astype({"appeared": object})
    art.loc[art.player_id == "00-B", "appeared"] = "False"          # a string 'False' is NOT truthy
    with pytest.raises(ValueError, match="appeared"):
        never_record_population(cohort=_cohort(), first_reg=first, outcomes=art, players=_players(), last_complete_season=2025)
    art = _artifact()
    art.loc[(art.player_id == "00-B") & (art.season == 2016), "points"] = np.nan   # closed season, present row, NaN points: malformed
    with pytest.raises(ValueError, match="points"):
        never_record_population(cohort=_cohort(), first_reg=first, outcomes=art, players=_players(), last_complete_season=2025)
    pop = never_record_population(cohort=_cohort(), first_reg=first, outcomes=_artifact(), players=_players(), last_complete_season=2025)
    sup = support_table(pop, origins=(2016,), horizons=(1,)).set_index(["origin", "horizon"])
    assert sup.loc[(2016, 1), "test_rows"] == 3  # B, C, P all jointly complete (appear, points, games) at 2016


def test_conflicting_birth_dates_refuse(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
    )
    players = pd.concat([_players(), pd.DataFrame({"gsis_id": ["00-B"], "birth_date": ["1990-01-01"]})])
    with pytest.raises(ValueError, match="birth"):
        never_record_population(cohort=_cohort(), first_reg=first_full_reg_season(capture), outcomes=_artifact(), players=players, last_complete_season=2025)


def test_capture_must_affirm_every_required_season(tmp_path):
    from src.dynasty_genius.rookie.cold_start_model import assert_capture_coverage
    cap = make_capture(tmp_path, {2015: _weekly([("00-A", 2015, 3, "REG", "QB")]), 2016: _weekly([("00-B", 2016, 5, "REG", "RB")])})
    assert assert_capture_coverage(cap, required_seasons=(2015, 2016)) == {"2015": "raw/player_stats_2015.parquet", "2016": "raw/player_stats_2016.parquet"}
    with pytest.raises(ValueError, match="2017"):
        assert_capture_coverage(cap, required_seasons=(2015, 2016, 2017))  # an omitted season can never read as 'no NFL record'
    m = json.loads((cap / "manifest.json").read_text())
    m["failures"] = [{"season": 2016, "error": "http 500"}]
    (cap / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="failure"):
        assert_capture_coverage(cap, required_seasons=(2015, 2016))


# ---------------------------------------------------------------- root model review (2026-09-06): feature blocks, RMSE units, frozen B1 floor

def test_feature_blocks_are_explicit_and_train_only():
    from src.dynasty_genius.rookie.cold_start_model import fit_arms
    pop = _synthetic_population()
    train = pop.loc[(pop["draft_season"] + 1 < 2016) & pop["appear_1"].notna()]
    fit = fit_arms(train, horizon=1, origin=2016)
    positions = list(fit["candidate"]["positions"])
    assert fit["candidate"]["feature_blocks"] == {"probability": ["log_pick", "round", "age_at_origin"] + [f"pos_{p}" for p in positions],
                                                  "conditional": ["log_pick"] + [f"pos_{p}" for p in positions]}
    assert fit["b2"]["feature_blocks"] == {"probability": ["log_pick", "round"] + [f"pos_{p}" for p in positions],
                                           "conditional": ["log_pick"] + [f"pos_{p}" for p in positions]}
    assert fit["candidate"]["ridge_points"].coef_.shape[0] == 1 + len(positions)   # no round in the conditional ridge
    assert fit["candidate"]["logit"].coef_.shape[1] == 3 + len(positions)
    assert fit["b1"]["min_conditional_appearers"] == 1 and fit["b1"]["min_position_rows"] == 10  # the frozen rule


def test_rmse_interval_is_in_rmse_units():
    from src.dynasty_genius.rookie.cold_start_model import paired_rmse_bootstrap
    rng = np.random.default_rng(0)
    actual = rng.normal(50, 20, 400)
    base_err = rng.normal(0, 10, 400)
    b1 = actual + base_err
    cand = actual + 2.0 * base_err          # candidate errors exactly twice the baseline's
    units = np.array([f"p{i}" for i in range(400)])
    d = paired_rmse_bootstrap(cand, b1, actual, units, seed=1, draws=300)
    rmse_c = np.sqrt(np.mean((cand - actual) ** 2))
    rmse_b = np.sqrt(np.mean((b1 - actual) ** 2))
    assert d["point"] == pytest.approx(rmse_c - rmse_b)
    assert d["lo"] <= d["point"] <= d["hi"] and (d["hi"] - d["lo"]) < 3 * (rmse_c - rmse_b)   # ~10 points wide, not ~300 (MSE units)
    assert abs(d["lo"]) < 40 and abs(d["hi"]) < 40


# ---------------------------------------------------------------- root exporter contract (2026-09-06): the seven-player sidecar refuses bad inputs

def _seven_ok():
    return pd.DataFrame({"sleeper_id": ["1"], "gsis_id": ["00-0040211"], "name": ["A"], "draft_position": ["QB"], "draft_season": [2025],
                         "route": ["never_appeared_drafted"], "draft_status": ["drafted_verified"], "identity_status": ["verified_nfl_join"]})


def _preds_ok(**over):
    d = {"gsis_id": ["00-0040211"]}
    for h in range(1, 6):
        d[f"candidate_p_appear_{h}"] = [0.3]
        d[f"candidate_e_points_given_appear_{h}"] = [50.0]
        d[f"candidate_e_points_{h}"] = [15.0]
        d[f"candidate_e_games_given_appear_{h}"] = [6.0]
        d[f"candidate_e_games_{h}"] = [1.8]
        d[f"candidate_supported_{h}"] = [True]
        d[f"b1_p_appear_{h}"] = [0.2]
        d[f"b1_e_points_given_appear_{h}"] = [40.0]
        d[f"b1_e_points_{h}"] = [8.0]
        d[f"b1_e_games_given_appear_{h}"] = [5.0]
        d[f"b1_e_games_{h}"] = [1.0]
        d[f"b1_supported_{h}"] = [True]
    d.update(over)
    return pd.DataFrame(d)


def _binding_ok():
    return {"origin_year": 2026, "capture_manifest_sha256": "a" * 64, "artifact_sha256": "b" * 64, "cohort_sha256": "c" * 64, "coverage_run": "runs/x"}


def test_sidecar_contract_refuses_each_invalid_input():
    from src.dynasty_genius.rookie.cold_start_model import export_sidecar
    sel = {h: "cold_start_candidate" for h in range(1, 6)}
    good = export_sidecar(_seven_ok(), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    assert len(good) == 1 and good["estimate_class_year1"].iloc[0] == "cold_start_candidate" and good["source_binding"].iloc[0]
    cases = {
        "finite": _preds_ok(candidate_e_points_3=[float("inf")]),
        "probab": _preds_ok(candidate_p_appear_2=[1.5]),
        "supported": _preds_ok(candidate_supported_4=[np.nan]),
        "games": _preds_ok(candidate_e_games_given_appear_1=[19.0]),
        "product": _preds_ok(candidate_e_points_1=[99.0]),  # != 0.3 * 50
    }
    for pattern, preds in cases.items():
        with pytest.raises(ValueError, match=pattern):
            export_sidecar(_seven_ok(), preds, selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    with pytest.raises(ValueError, match="duplicate"):
        export_sidecar(pd.concat([_seven_ok(), _seven_ok()]), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    with pytest.raises(ValueError, match="route"):
        export_sidecar(_seven_ok().assign(route="dormant_drafted"), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    with pytest.raises(ValueError, match="2025"):
        export_sidecar(_seven_ok().assign(draft_season=2024), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    with pytest.raises(ValueError, match="skill"):
        export_sidecar(_seven_ok().assign(draft_position="FB"), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    with pytest.raises(ValueError, match="identit"):
        export_sidecar(_seven_ok().assign(identity_status="sleeper_gsis_disagrees"), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    with pytest.raises(ValueError, match="binding"):
        export_sidecar(_seven_ok(), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding={"origin_year": 2026})
    with pytest.raises(ValueError, match="origin"):
        export_sidecar(_seven_ok(), _preds_ok(), selected_per_horizon=sel, origin_year=2027, binding=_binding_ok())
    unsupported = export_sidecar(_seven_ok(), _preds_ok(candidate_supported_5=[False]), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    assert unsupported["estimate_class_year5"].iloc[0] == "unsupported" and pd.isna(unsupported["p_appear_year5"].iloc[0])
    assert unsupported["estimate_class_year1"].iloc[0] == "cold_start_candidate"


def test_age_fallback_is_recorded_and_games_bound_is_declared():
    from src.dynasty_genius.rookie.cold_start_model import (
        GAMES_BOUND,
        fit_arms,
        predict_arms,
    )
    pop = _synthetic_population()
    train = pop.loc[(pop["draft_season"] + 1 < 2016) & pop["appear_1"].notna()].copy()
    train.loc[train["draft_position"] == "TE", "age_at_origin"] = np.nan  # no TE age at all -> overall training median for TE
    fit = fit_arms(train, horizon=1, origin=2016)
    fb = fit["candidate"]["age_fallback"]
    assert fb["position_median"] > 0 and fb["overall_median"] > 0 and fb["rule"].startswith("training position median")
    assert GAMES_BOUND == (1, 17)
    pred = predict_arms(fit, pop.loc[pop["draft_season"] == 2015])
    assert pred["candidate_e_games_given_appear"].between(1, 17).all()
    assert np.allclose(pred["candidate_e_games"], pred["candidate_p_appear"] * pred["candidate_e_games_given_appear"])


# ---------------------------------------------------------------- root code gate after acceptance (2026-09-06): remaining exporter and population guards

def test_exporter_remaining_cases_refuse():
    from src.dynasty_genius.rookie.cold_start_model import export_sidecar
    sel = {h: "cold_start_candidate" for h in range(1, 6)}
    # supported candidate with a NaN conditional points path: the conditional is REQUIRED, not optional
    with pytest.raises(ValueError, match="conditional"):
        export_sidecar(_seven_ok(), _preds_ok(candidate_e_points_given_appear_2=[np.nan]), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    # games -2 with p 0.5 and conditional games 4: e_games must be finite, within bounds and equal P x conditional
    with pytest.raises(ValueError, match="games"):
        export_sidecar(_seven_ok(), _preds_ok(candidate_p_appear_1=[0.5], candidate_e_games_given_appear_1=[4.0], candidate_e_games_1=[-2.0],
                                              candidate_e_points_given_appear_1=[30.0], candidate_e_points_1=[15.0]),
                       selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    # draft status must be affirmatively drafted_verified even when the route is the approved one
    with pytest.raises(ValueError, match="drafted_verified"):
        export_sidecar(_seven_ok().assign(draft_status="unknown_identity"), _preds_ok(), selected_per_horizon=sel, origin_year=2026, binding=_binding_ok())
    # origin must be exactly draft season + 1 = 2026 and the years 2026-2030; origin 2027 for a 2025 draftee refuses
    b = dict(_binding_ok(), origin_year=2027)
    with pytest.raises(ValueError, match="2026"):
        export_sidecar(_seven_ok(), _preds_ok(), selected_per_horizon=sel, origin_year=2027, binding=b)


def test_capture_dict_manifest_refuses_duplicate_seasons(tmp_path):
    from src.dynasty_genius.rookie.cold_start_model import assert_capture_coverage
    cap = make_capture(tmp_path, {2015: _weekly([("00-A", 2015, 3, "REG", "QB")]), 2016: _weekly([("00-B", 2016, 5, "REG", "RB")])})
    m = json.loads((cap / "manifest.json").read_text())
    m["files"]["raw/player_stats_2016_again.parquet"] = dict(m["files"]["raw/player_stats_2016.parquet"])  # second declaration for 2016
    (cap / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="2016"):
        assert_capture_coverage(cap, required_seasons=(2015, 2016))


def test_incoherent_present_outcome_rows_refuse(capture):
    from src.dynasty_genius.rookie.cold_start_model import (
        first_full_reg_season,
        never_record_population,
    )
    art = _artifact()
    art.loc[(art.player_id == "00-B") & (art.season == 2016), "appeared"] = False  # appeared False with 50 points / 8 games: incoherent
    with pytest.raises(ValueError, match="coheren"):
        never_record_population(cohort=_cohort(), first_reg=first_full_reg_season(capture), outcomes=art, players=_players(), last_complete_season=2025)


def test_report_states_the_explicit_status_partition_and_caveats():
    from src.dynasty_genius.rookie.cold_start_model import (
        CAVEATS,
        evaluate_candidate,
        render_candidate_report,
        support_table,
    )
    pop = _synthetic_population()
    ev = evaluate_candidate(pop, origins=range(2012, 2026), horizons=(1,), seed=1, draws=20)
    ev.pop("paired_rows_frame")
    side = pd.DataFrame({"gsis_id": ["a"], "estimate_class_year1": ["cold_start_candidate"], **{f"estimate_class_year{j}": ["unsupported"] for j in range(2, 6)}})
    unresolved = pd.DataFrame({"gsis_id": ["b", "c", "d"], "status": ["unresolved", "unresolved", "recovered_existing_forecast"]})
    text = render_candidate_report(ev, support_table(pop, origins=(2016,), horizons=(1,)), side, unresolved)
    assert "2 unresolved" in text and "1 recovered" in text and "3 players" not in text.replace("3 players remain", "")
    assert "research default PPR" in text and "not exact league scoring" in text
    assert "fixed fits and the realized origins" in text and "no season or model-fit uncertainty" in text
    assert "research default PPR" in CAVEATS["scoring"] and "fixed fits" in CAVEATS["bootstrap"]
