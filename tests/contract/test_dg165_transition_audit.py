"""Contract tests for the rookie -> veteran transition audit (DG-165, build released 2026-09-06).

Fixtures are two tiny synthetic frozen runs with the same shapes as
runs/20260906T195904Z/dg165_rookie_capital and DG-177's dg177_basic_horizons.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

TARGET = "0" * 64
CSV_SHA = "1" * 64
MAN_SHA = "2" * 64
PRESET = "nflverse_default_ppr_championship_window_v1"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha(data)


def make_rookie_run(root: Path, *, oot: pd.DataFrame | None = None, cohort: pd.DataFrame | None = None,
                    target: str = TARGET) -> Path:
    run = root / "rookie"
    run.mkdir(parents=True)
    if cohort is None:
        cohort = pd.DataFrame({
            # 4 drafted skill players in class 2015 + one unresolved identity
            "gsis_id": ["00-A", "00-B", "00-C", "00-D", "unresolved:2015:250"],
            "draft_season": [2015, 2015, 2015, 2015, 2015],
            "position": ["QB", "RB", "WR", "TE", "WR"],
            "pick": [1, 40, 90, 150, 250],
            "round": [1, 2, 3, 5, 7],
            "age_at_draft": [22.0, 21.5, 22.3, 23.0, np.nan],
            "team": ["X"] * 5,
            "name": ["Ann", "Bob", "Cy", "Dee", "Eve"],
            # real label_basis values are the SOURCE that resolved the identity; only "unresolved" is unknown
            "label_basis": ["nflverse_gsis", "players:name+year", "nflverse_gsis", "rosters:entry_year+draft_number", "unresolved"],
            "position_current": ["QB", "RB", "WR", "TE", None],
        })
    if oot is None:
        oot = pd.DataFrame({
            "gsis_id": ["00-A", "00-B", "00-C", "00-D"],
            "draft_season": [2015] * 4, "position": ["QB", "RB", "WR", "TE"],
            "pick": [1, 40, 90, 150], "round": [1, 2, 3, 5], "age_at_draft": [22.0, 21.5, 22.3, 23.0],
            "team": ["X"] * 4, "name": ["Ann", "Bob", "Cy", "Dee"],
            "label_basis": ["nflverse_gsis", "players:name+year", "nflverse_gsis", "rosters:entry_year+draft_number"],
            "position_current": ["QB", "RB", "WR", "TE"],
            "forecast_year": [2015] * 4,
            # season-1 labels: Dee never appeared in the window
            "appear_1": [1.0, 1.0, 1.0, 0.0], "points_1": [200.0, 100.0, 50.0, 0.0], "games_1": [16.0, 12.0, 8.0, 0.0],
            # season-2 labels (target for k=1)
            "appear_2": [1.0, 1.0, 1.0, 0.0], "points_2": [250.0, 90.0, 40.0, 0.0], "games_2": [17.0, 10.0, 6.0, 0.0],
            "appear_3": [1.0, 1.0, np.nan, 0.0], "points_3": [240.0, 80.0, np.nan, 0.0], "games_3": [16.0, 9.0, np.nan, 0.0],
            "p_appear_year2": [0.95, 0.85, 0.70, 0.40], "e_points_year2": [230.0, 100.0, 60.0, 20.0],
            "e_points_year2_given_appear": [242.1, 117.6, 85.7, 50.0], "e_games_year2": [15.0, 11.0, 8.0, 4.0],
            "p_appear_year3": [0.93, 0.80, 0.65, 0.35], "e_points_year3": [225.0, 95.0, 55.0, 18.0],
            "e_points_year3_given_appear": [241.9, 118.8, 84.6, 51.4], "e_games_year3": [14.0, 10.0, 7.0, 3.0],
        })
    hashes = {}
    hashes["cohort.csv"] = _write(run / "cohort.csv", cohort.to_csv(index=False).encode())
    hashes["out_of_time_predictions.csv"] = _write(run / "out_of_time_predictions.csv", oot.to_csv(index=False).encode())
    picks = pd.DataFrame({
        # raw draft table covers 1980-2026; the modelling cohort starts at 2001, so a 1998 WR is a
        # drafted skill player OUTSIDE cohort coverage, not "drafted at another position"
        "season": [2015, 2015, 2015, 2015, 2015, 2014, 1998],
        "round": [1, 2, 3, 5, 7, 4, 3], "pick": [1, 40, 90, 150, 250, 120, 70],
        "gsis_id": ["00-A", "00-B", "00-C", "00-D", None, "00-LB", "00-OLD"],
        "position": ["QB", "RB", "WR", "TE", "WR", "LB", "WR"],
        "pfr_player_name": ["Ann", "Bob", "Cy", "Dee", "Eve", "Lou", "Old"],
    })
    (run / "inputs").mkdir()
    picks.to_parquet(run / "inputs" / "nflverse_draft_picks.parquet", index=False)
    picks_sha = _sha((run / "inputs" / "nflverse_draft_picks.parquet").read_bytes())
    manifest = {
        "model_version": "dg165_rookie_capital_v3_chain", "git_sha": "deadbeef",
        "scoring_arm_id": "dg165_rookie_capital_v3_chain:inner_menu:trend",
        "forecast_date": {"forecast_year": 2026, "labels_through": 2025, "last_completed_season": 2025},
        "outcomes": {"target_identity": target, "csv_sha256": CSV_SHA, "manifest_sha256": MAN_SHA, "scoring_preset": PRESET},
        "inputs": {"nflverse_draft_picks": {"path": "inputs/nflverse_draft_picks.parquet", "sha256": picks_sha, "rows": len(picks)}},
        "outputs_sha256": hashes,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return run


def make_veteran_run(root: Path, *, hist: pd.DataFrame | None = None, cohort: pd.DataFrame | None = None,
                     target: str = TARGET) -> Path:
    run = root / "veteran"
    run.mkdir(parents=True)
    if hist is None:
        # horizon-1 rows at feature season 2015 (= rookie season of class 2015) for A, B, C;
        # D has no row (never appeared); an undrafted player U and a drafted linebacker LB also have rows.
        hist = pd.DataFrame({
            "horizon": [1, 1, 1, 1, 1, 1, 1],
            "player_id": ["00-B", "00-A", "00-C", "00-U", "00-LB", "00-A", "00-B"],
            "position": ["RB", "QB", "WR", "WR", "RB", "QB", "RB"],
            "feature_season": [2015, 2015, 2015, 2015, 2015, 2016, 2016],
            "forecast_season": [2016, 2016, 2016, 2016, 2016, 2017, 2017],
            "policy_p_appear_year1": [0.90, 0.97, 0.75, 0.5, 0.5, 0.96, 0.88],
            "policy_e_points_year1_given_appear": [111.1, 247.4, 66.7, 40.0, 40.0, 250.0, 100.0],
            "policy_e_games_year1_given_appear": [12.0, 16.0, 9.0, 8.0, 8.0, 15.0, 11.0],
            "policy_e_points_year1": [100.0, 240.0, 50.0, 20.0, 20.0, 240.0, 88.0],
            "policy_e_games_year1": [10.8, 15.5, 6.75, 4.0, 4.0, 14.4, 9.7],
            "appeared_year1": [1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0],
            "games_year1": [10.0, 17.0, 6.0, 5.0, 0.0, 16.0, 9.0],
            "points_year1": [90.0, 250.0, 40.0, 30.0, 0.0, 240.0, 80.0],
        })
    if cohort is None:
        cohort = pd.DataFrame({
            "player_id": ["00-A", "00-B", "00-C", "00-U", "00-LB", "00-A", "00-B"],
            "feature_season": [2015, 2015, 2015, 2015, 2015, 2016, 2016],
            "position": ["QB", "RB", "WR", "WR", "RB", "QB", "RB"],
            "identity_status": ["resolved"] * 7,
            "games_t": [16.0, 12.0, 3.0, 4.0, 1.0, 17.0, 10.0],
            "seasons_played": [1, 1, 1, 1, 1, 2, 2],
        })
    hashes = {}
    hashes["historical_predictions.csv"] = _write(run / "historical_predictions.csv", hist.to_csv(index=False).encode())
    gz = gzip.compress(cohort.to_csv(index=False).encode(), mtime=0)
    hashes["basic_cohort.csv.gz"] = _write(run / "basic_cohort.csv.gz", gz)
    manifest = {
        "producer": "DG-177 veteran annual forecast candidate (report-only)", "candidate_arm": "basic_cohort_3col_plus_lags",
        "git_head": "cafebabe", "last_complete_season": 2025,
        "label_source": {"kind": "common_outcome_artifact", "target_identity": target, "csv_sha256": CSV_SHA,
                         "manifest_sha256": MAN_SHA, "scoring_preset": PRESET},
        "forecast_cutoff": {"rule": "features observed through the feature season; a year-j label trains only when "
                                    "feature_season + j <= last complete season"},
        "outputs_sha256": hashes,
    }
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return run


@pytest.fixture
def runs(tmp_path):
    return make_rookie_run(tmp_path), make_veteran_run(tmp_path)


# ---------------------------------------------------------------- Task 1: verified loaders, same target

def test_rookie_loader_verifies_every_declared_byte(runs):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run
    rookie_dir, _ = runs
    loaded = load_rookie_run(rookie_dir)
    assert set(loaded.verified) >= {"cohort.csv", "out_of_time_predictions.csv", "inputs/nflverse_draft_picks.parquet"}
    assert len(loaded.cohort) == 5 and len(loaded.out_of_time) == 4 and len(loaded.draft_picks) == 7


def test_rookie_loader_refuses_altered_bytes(runs):
    from src.dynasty_genius.rookie.transition_audit import load_rookie_run
    rookie_dir, _ = runs
    path = rookie_dir / "out_of_time_predictions.csv"
    path.write_text(path.read_text().replace("250.0", "251.0", 1))
    with pytest.raises(ValueError, match="sha256"):
        load_rookie_run(rookie_dir)


def test_veteran_loader_refuses_missing_declaration(runs):
    from src.dynasty_genius.rookie.transition_audit import load_veteran_run
    _, vet_dir = runs
    m = json.loads((vet_dir / "manifest.json").read_text())
    del m["outputs_sha256"]["basic_cohort.csv.gz"]
    (vet_dir / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(ValueError, match="basic_cohort.csv.gz"):
        load_veteran_run(vet_dir)


def test_same_target_is_asserted_not_assumed(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        load_veteran_run,
        verify_same_target,
    )
    r = load_rookie_run(make_rookie_run(tmp_path))
    v = load_veteran_run(make_veteran_run(tmp_path, target="f" * 64))
    with pytest.raises(ValueError, match="target_identity"):
        verify_same_target(r, v)
    v2 = load_veteran_run(make_veteran_run(tmp_path / "again"))
    block = verify_same_target(r, v2)
    assert block["status"] == "same_target" and block["target_identity"] == TARGET


# ---------------------------------------------------------------- Task 2: draft status

def test_draft_status_distinguishes_drafted_no_record_and_unknown(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        classify_draft_status,
        load_rookie_run,
    )
    rookie_dir, _ = runs
    r = load_rookie_run(rookie_dir)
    ids = pd.Series(["00-A", "00-B", "00-LB", "00-OLD", "00-U", "00-Z", "unresolved:2015:250"])
    status = pd.Series(["resolved", "resolved", "resolved", "resolved", "resolved", "unresolved_in_source", "resolved"])
    out = classify_draft_status(ids, status, r)
    # A resolved by nflverse_gsis and B by players:name+year are BOTH drafted skill players; the 1998 WR is a
    # drafted skill player outside cohort coverage (raw draft position classified positively); absence from the
    # draft table is "no draft record", never positive undrafted evidence.
    assert out.tolist() == ["drafted_skill", "drafted_skill", "drafted_other_position", "drafted_skill_outside_cohort",
                            "no_draft_record", "unknown_identity", "drafted_skill_unresolved"]


# ---------------------------------------------------------------- Task 3: the join

def _rebuild_veteran(tmp_path, **kwargs):
    import shutil
    shutil.rmtree(tmp_path / "veteran", ignore_errors=True)
    return make_veteran_run(tmp_path, **kwargs)


def test_join_is_by_key_not_row_order_and_records_both_origins(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir, vet_dir = runs
    j = join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)
    by_id = j.set_index("player_id")
    # the veteran fixture lists B before A; the join must pair by id, so A's veteran forecast is 240 not 100
    assert by_id.loc["00-A", "veteran_e_points"] == 240.0 and by_id.loc["00-A", "rookie_e_points"] == 230.0
    assert sorted(j["player_id"]) == ["00-A", "00-B", "00-C"]  # D has no veteran row; U and LB are not drafted skill
    row = by_id.loc["00-A"]
    assert row["experience"] == 1 and row["target_season"] == 2016
    assert row["rookie_forecast_year"] == 2015 and row["rookie_information_through_season"] == 2014
    assert row["veteran_feature_season"] == 2015 and row["veteran_information_through_season"] == 2015
    assert row["information_gap_seasons"] == 1
    assert row["points"] == 250.0 and row["appeared"] == 1.0 and row["games"] == 17.0
    assert row["err_rookie"] == pytest.approx(-20.0) and row["err_veteran"] == pytest.approx(-10.0)
    assert bool(row["veteran_closer"]) is True
    assert row["draft_position"] == "QB" and row["veteran_position"] == "QB"
    c = by_id.loc["00-C"]
    assert bool(c["thin_history"]) is True and c["veteran_games_t"] == 3.0


def test_join_refuses_label_disagreement_even_within_relative_tolerance(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    hist = pd.read_csv(make_veteran_run(tmp_path) / "historical_predictions.csv")
    hist.loc[hist.player_id == "00-A", "points_year1"] = 250.002  # np.isclose(atol=1e-6) would PASS this via rtol
    vet_dir = _rebuild_veteran(tmp_path, hist=hist)
    with pytest.raises(ValueError, match="label"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_join_refuses_duplicate_keys(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    hist = pd.read_csv(make_veteran_run(tmp_path) / "historical_predictions.csv")
    hist = pd.concat([hist, hist.iloc[[1]]], ignore_index=True)  # A twice at 2015
    vet_dir = _rebuild_veteran(tmp_path, hist=hist)
    with pytest.raises(ValueError, match="unique"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_join_asserts_the_veterans_own_forecast_season(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    hist = pd.read_csv(make_veteran_run(tmp_path) / "historical_predictions.csv")
    hist.loc[(hist.player_id == "00-A") & (hist.feature_season == 2015), "forecast_season"] = 2017  # labels untouched
    vet_dir = _rebuild_veteran(tmp_path, hist=hist)
    with pytest.raises(ValueError, match="forecast_season"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_rookie_rows_not_at_draft_time_refuse_instead_of_silent_filter(tmp_path):
    import shutil

    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        rookie_draft_time_frame,
    )
    rookie_dir = make_rookie_run(tmp_path)
    oot = pd.read_csv(rookie_dir / "out_of_time_predictions.csv")
    extra = oot.iloc[[0]].copy()
    extra["forecast_year"] = 2016
    shutil.rmtree(rookie_dir)
    rookie_dir = make_rookie_run(tmp_path, oot=pd.concat([oot, extra], ignore_index=True))
    with pytest.raises(ValueError, match="forecast_year"):
        rookie_draft_time_frame(load_rookie_run(rookie_dir), experience=1)


def test_rookie_history_keys_must_agree_with_the_cohort(tmp_path):
    import shutil

    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        rookie_draft_time_frame,
    )
    rookie_dir = make_rookie_run(tmp_path)
    oot = pd.read_csv(rookie_dir / "out_of_time_predictions.csv")
    oot.loc[oot.gsis_id == "00-B", "pick"] = 41  # cohort says 40
    shutil.rmtree(rookie_dir)
    rookie_dir = make_rookie_run(tmp_path, oot=oot)
    with pytest.raises(ValueError, match="cohort"):
        rookie_draft_time_frame(load_rookie_run(rookie_dir), experience=1)


def test_join_refuses_a_prediction_without_its_cohort_row(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    cohort = pd.read_csv(make_veteran_run(tmp_path) / "basic_cohort.csv.gz")
    cohort = cohort[~((cohort.player_id == "00-C") & (cohort.feature_season == 2015))]  # C predicted but no feature row
    vet_dir = _rebuild_veteran(tmp_path, cohort=cohort)
    with pytest.raises(ValueError, match="basic cohort"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_join_experience_two_uses_the_next_feature_season(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir, vet_dir = runs
    j = join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=2)
    assert sorted(j["player_id"]) == ["00-A", "00-B"]  # C's season-3 label is unknown (NaN) -> not a joined row
    a = j.set_index("player_id").loc["00-A"]
    assert a["veteran_feature_season"] == 2016 and a["target_season"] == 2017 and a["rookie_e_points"] == 225.0


# ---------------------------------------------------------------- Task 4: ledgers

def test_coverage_ledger_keeps_every_cohort_player_in_the_denominator(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        coverage_ledger,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir, vet_dir = runs
    led = coverage_ledger(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)
    assert len(led) == 5  # every cohort row, unresolved included
    cat = led.set_index("player_id")["category"]
    assert cat["00-A"] == "paired" and cat["00-B"] == "paired" and cat["00-C"] == "paired"
    assert cat["00-D"] == "no_veteran_row_no_window_appearance"  # missed his rookie season: counted, not dropped, not forecast
    assert cat["unresolved:2015:250"] == "identity_unresolved"
    assert led["category"].value_counts().sum() == 5


def test_coverage_ledger_marks_unknown_labels_and_appearance_without_veteran_row(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        coverage_ledger,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    hist = pd.read_csv(make_veteran_run(tmp_path) / "historical_predictions.csv")
    hist = hist[hist.player_id != "00-C"]  # C appeared in his rookie season but the veteran side has no row (role abstain)
    vet_dir = _rebuild_veteran(tmp_path, hist=hist, cohort=pd.read_csv(vet_dir_cohort(tmp_path)))
    led = coverage_ledger(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=2)
    cat = led.set_index("player_id")["category"]
    assert cat["00-C"] == "label_unknown"  # season-3 label is NaN at k=2: unknown, never zero
    led1 = coverage_ledger(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)
    assert led1.set_index("player_id")["category"]["00-C"] == "no_veteran_row_despite_window_appearance"


def vet_dir_cohort(tmp_path):
    return tmp_path / "veteran" / "basic_cohort.csv.gz"


def test_veteran_population_ledger_separates_drafted_no_record_unknown(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
        veteran_population_ledger,
    )
    rookie_dir, vet_dir = runs
    r, v = load_rookie_run(rookie_dir), load_veteran_run(vet_dir)
    j = join_transition(r, v, experience=1)
    pop = veteran_population_ledger(r, v, j, experience=1)
    row = pop.set_index(["veteran_feature_season", "draft_status"])["rows"]
    assert row[(2015, "drafted_skill_paired")] == 3
    assert row[(2015, "drafted_other_position")] == 1  # the linebacker
    assert row[(2015, "no_draft_record")] == 1  # 00-U: absent from the draft table = unknown draft status
    assert (2015, "undrafted") not in row.index


# ---------------------------------------------------------------- Task 5: metrics and bootstrap

def _toy_joined(errors_rookie, errors_veteran, players=None, experience=None):
    n = len(errors_rookie)
    pts = np.full(n, 100.0)
    d = pd.DataFrame({
        "player_id": players or [f"p{i}" for i in range(n)], "draft_season": [2015] * n, "draft_position": ["WR"] * n,
        "experience": experience or [1] * n, "thin_history": [False] * n,
        "appeared": [1.0] * n, "points": pts,
        "rookie_e_points": pts + np.asarray(errors_rookie, dtype=float),
        "veteran_e_points": pts + np.asarray(errors_veteran, dtype=float),
        "rookie_p_appear": [0.8] * n, "veteran_p_appear": [0.9] * n,
    })
    for side in ("rookie", "veteran"):
        d[f"err_{side}"] = d[f"{side}_e_points"] - d["points"]
        d[f"abs_err_{side}"] = d[f"err_{side}"].abs()
        d[f"sq_err_{side}"] = d[f"err_{side}"] ** 2
    d["veteran_closer"] = d["abs_err_veteran"] < d["abs_err_rookie"]
    return d


def test_bias_is_reported_apart_from_accuracy():
    from src.dynasty_genius.rookie.transition_audit import paired_metrics
    m = paired_metrics(_toy_joined([10, 10, 10, 10], [10, -10, 10, -10]))
    assert m["rookie"]["bias"] == pytest.approx(10.0) and m["rookie"]["rmse"] == pytest.approx(10.0)
    assert m["veteran"]["bias"] == pytest.approx(0.0) and m["veteran"]["rmse"] == pytest.approx(10.0)
    assert m["paired"]["mean_sq_err_diff"] == pytest.approx(0.0)
    assert m["n"] == 4 and m["rookie"]["brier_appear"] == pytest.approx((1 - 0.8) ** 2)
    assert m["rookie"]["mae"] == pytest.approx(10.0) and m["paired"]["share_veteran_closer"] == pytest.approx(0.0)


def test_fold_summary_keeps_each_draft_class_as_a_temporal_fold():
    from src.dynasty_genius.rookie.transition_audit import fold_sign_summary
    d = _toy_joined([10, 10, 10, 10], [5, 5, 20, 20])
    d["draft_season"] = [2014, 2014, 2015, 2015]
    f = fold_sign_summary(d)
    assert f["classes_total"] == 2 and f["classes_veteran_better"] == 1
    assert f["by_draft_class"]["2014"]["n"] == 2 and f["by_draft_class"]["2014"]["mean_sq_err_diff"] < 0
    assert f["by_draft_class"]["2015"]["mean_sq_err_diff"] > 0


def test_bootstrap_is_deterministic_and_resamples_players_as_units():
    from src.dynasty_genius.rookie.transition_audit import paired_bootstrap
    # each player has one row at k=1 with signed diff +x and one at k=2 with -x: resampling PLAYERS gives exactly 0
    # on every draw; resampling rows would not.
    players = ["a", "b", "c", "d", "a", "b", "c", "d"]
    d = _toy_joined([0] * 8, [3, 5, 7, 9, -3, -5, -7, -9], players=players, experience=[1, 1, 1, 1, 2, 2, 2, 2])
    d["signed_diff"] = d["err_veteran"]
    one = paired_bootstrap(d, seed=7, draws=50, statistic_columns={"signed": "signed_diff"})
    two = paired_bootstrap(d, seed=7, draws=50, statistic_columns={"signed": "signed_diff"})
    assert one == two
    assert one["signed"]["lo"] == pytest.approx(0.0) and one["signed"]["hi"] == pytest.approx(0.0)
    assert one["unit"] == "player_id" and one["draws"] == 50 and one["level"] == 0.90 and one["n_units"] == 4
    default = paired_bootstrap(d, seed=7, draws=50)
    assert set(default) >= {"mean_sq_err_diff", "mean_abs_err_diff", "brier_diff", "conditional_on", "folds"}
    assert default["mean_sq_err_diff"]["lo"] <= default["mean_sq_err_diff"]["point"] <= default["mean_sq_err_diff"]["hi"]


# ---------------------------------------------------------------- Task 6: writer, report, CLI

def test_write_audit_hashes_every_output_records_input_manifests_and_refuses_a_second_call(runs, tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        load_veteran_run,
        run_audit,
        write_audit,
    )
    rookie_dir, vet_dir = runs
    r, v = load_rookie_run(rookie_dir), load_veteran_run(vet_dir)
    result = run_audit(r, v, experiences=(1, 2), seed=3, draws=20)
    out = tmp_path / "runs" / "20990101T000000Z" / "dg165_transition_audit"
    out.mkdir(parents=True)
    manifest = write_audit(out, result, rookie=r, veteran=v, seed=3, draws=20, experiences=(1, 2), git_sha="abc")
    for name, sha in manifest["outputs_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == sha
    assert {"joined_rows.csv", "coverage_ledger.csv", "veteran_population_ledger.csv", "metrics.json", "REPORT.md"} <= set(manifest["outputs_sha256"])
    assert manifest["inputs"]["rookie"]["verified"]["out_of_time_predictions.csv"] == r.verified["out_of_time_predictions.csv"]
    assert manifest["inputs"]["rookie"]["manifest_sha256"] == hashlib.sha256((rookie_dir / "manifest.json").read_bytes()).hexdigest()
    assert manifest["inputs"]["veteran"]["manifest_sha256"] == hashlib.sha256((vet_dir / "manifest.json").read_bytes()).hexdigest()
    assert manifest["binding"]["status"] == "same_target"
    metrics = json.loads((out / "metrics.json").read_text())
    assert metrics["experiences"]["1"]["overall"]["n"] == 3
    assert metrics["experiences"]["1"]["coverage_counts"]["no_veteran_row_no_window_appearance"] == 1
    assert metrics["experiences"]["1"]["raw_source_population_excluded"] is None  # fixture manifest declares no raw population
    caveats = metrics["definitions"]["caveats"]
    assert "policy menu" in json.dumps(caveats) and "player-sampling" in json.dumps(caveats) and "role" in json.dumps(caveats)
    report = (out / "REPORT.md").read_text()
    assert "n = 3" in report and "no_veteran_row_no_window_appearance" in report and "not" in report.lower()
    with pytest.raises(FileExistsError):
        write_audit(out, result, rookie=r, veteran=v, seed=3, draws=20, experiences=(1, 2), git_sha="abc")


def test_report_numbers_come_from_metrics_not_prose(runs, tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        load_veteran_run,
        render_report,
        run_audit,
    )
    rookie_dir, vet_dir = runs
    r, v = load_rookie_run(rookie_dir), load_veteran_run(vet_dir)
    result = run_audit(r, v, experiences=(1,), seed=3, draws=20)
    text = render_report(result["metrics"], result["coverage"], result["population"], result["binding"])
    rmse = result["metrics"]["experiences"]["1"]["overall"]["veteran"]["rmse"]
    assert f"{rmse:.1f}" in text


def test_cli_end_to_end(runs, tmp_path):
    import os
    import subprocess
    import sys
    rookie_dir, vet_dir = runs
    repo = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/dg165/audit_rookie_transition.py", "--rookie-run", str(rookie_dir), "--veteran-run", str(vet_dir),
         "--experience", "1", "--seed", "1", "--draws", "10", "--runs-root", str(tmp_path / "runs")],
        capture_output=True, text=True, cwd=repo, env={**os.environ, "PYTHONPATH": "."},
    )
    assert proc.returncode == 0, proc.stderr
    run_dir = Path(proc.stdout.strip().splitlines()[-1])
    assert (run_dir / "manifest.json").exists() and run_dir.name == "dg165_transition_audit"


# ---------------------------------------------------------------- root probe 2026-09-06: required measurements must be finite

def test_join_refuses_a_missing_games_t_instead_of_labelling_not_thin(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    cohort = pd.read_csv(make_veteran_run(tmp_path) / "basic_cohort.csv.gz")
    cohort.loc[(cohort.player_id == "00-C") & (cohort.feature_season == 2015), "games_t"] = np.nan  # feature row exists, measurement missing
    vet_dir = _rebuild_veteran(tmp_path, cohort=cohort)
    with pytest.raises(ValueError, match="games_t"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_join_refuses_a_non_finite_prediction_before_metrics(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    hist = pd.read_csv(make_veteran_run(tmp_path) / "historical_predictions.csv")
    hist.loc[(hist.player_id == "00-A") & (hist.feature_season == 2015), "policy_e_points_year1"] = np.nan
    vet_dir = _rebuild_veteran(tmp_path, hist=hist)
    with pytest.raises(ValueError, match="finite"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_join_refuses_a_probability_outside_the_unit_interval(tmp_path):
    import shutil

    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    oot = pd.read_csv(rookie_dir / "out_of_time_predictions.csv")
    oot.loc[oot.gsis_id == "00-B", "p_appear_year2"] = 1.2
    shutil.rmtree(rookie_dir)
    rookie_dir = make_rookie_run(tmp_path, oot=oot)
    with pytest.raises(ValueError, match="probabilit"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(make_veteran_run(tmp_path)), experience=1)


def test_negative_fantasy_points_remain_valid_labels_and_forecasts(tmp_path):
    import shutil

    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
        paired_metrics,
    )
    rookie_dir = make_rookie_run(tmp_path)
    oot = pd.read_csv(rookie_dir / "out_of_time_predictions.csv")
    oot.loc[oot.gsis_id == "00-C", ["points_2", "e_points_year2"]] = [-3.0, -1.5]
    shutil.rmtree(rookie_dir)
    rookie_dir = make_rookie_run(tmp_path, oot=oot)
    hist = pd.read_csv(make_veteran_run(tmp_path) / "historical_predictions.csv")
    hist.loc[(hist.player_id == "00-C") & (hist.feature_season == 2015), "points_year1"] = -3.0
    vet_dir = _rebuild_veteran(tmp_path, hist=hist)
    j = join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)
    assert j.set_index("player_id").loc["00-C", "points"] == -3.0
    assert paired_metrics(j)["n"] == 3


# ---------------------------------------------------------------- root review 2026-09-06 (2): integrality, ledger unknowns, duplicate experiences

def test_non_integral_year_is_refused_not_truncated(tmp_path):
    from src.dynasty_genius.rookie.transition_audit import (
        join_transition,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    hist = pd.read_csv(make_veteran_run(tmp_path) / "historical_predictions.csv")
    hist["forecast_season"] = hist["forecast_season"].astype(float)
    hist.loc[(hist.player_id == "00-A") & (hist.feature_season == 2015), "forecast_season"] = 2016.25  # astype(int) would say 2016
    vet_dir = _rebuild_veteran(tmp_path, hist=hist)
    with pytest.raises(ValueError, match="integral"):
        join_transition(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)


def test_non_integral_rookie_key_is_refused(tmp_path):
    import shutil

    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        rookie_draft_time_frame,
    )
    rookie_dir = make_rookie_run(tmp_path)
    oot = pd.read_csv(rookie_dir / "out_of_time_predictions.csv")
    oot["pick"] = oot["pick"].astype(float)
    oot.loc[oot.gsis_id == "00-B", "pick"] = 40.5
    shutil.rmtree(rookie_dir)
    rookie_dir = make_rookie_run(tmp_path, oot=oot)
    with pytest.raises(ValueError, match="integral"):
        rookie_draft_time_frame(load_rookie_run(rookie_dir), experience=1)


def test_ledger_partial_label_is_unknown_and_missing_forecast_row_is_its_own_category(tmp_path):
    import shutil

    from src.dynasty_genius.rookie.transition_audit import (
        coverage_ledger,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    oot = pd.read_csv(rookie_dir / "out_of_time_predictions.csv")
    oot.loc[oot.gsis_id == "00-A", "appear_2"] = np.nan          # points remain: the label is UNKNOWN, not "no forecast"
    oot = oot[oot.gsis_id != "00-C"]                              # C (appeared, unpaired) has no draft-time forecast row at all
    shutil.rmtree(rookie_dir)
    rookie_dir = make_rookie_run(tmp_path, oot=oot)
    vet_dir = make_veteran_run(tmp_path)
    led = coverage_ledger(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experience=1)
    cat = led.set_index("player_id")["category"]
    assert len(led) == 5
    assert cat["00-A"] == "label_unknown"
    assert cat["00-C"] == "rookie_forecast_missing"                # never "no window appearance" from a NaN flag
    assert cat["00-D"] == "no_veteran_row_no_window_appearance"    # D's appearance flag is a measured 0


def test_ledger_unknown_appearance_without_veteran_row_is_not_called_no_appearance(tmp_path):
    import shutil

    from src.dynasty_genius.rookie.transition_audit import (
        coverage_ledger,
        load_rookie_run,
        load_veteran_run,
    )
    rookie_dir = make_rookie_run(tmp_path)
    oot = pd.read_csv(rookie_dir / "out_of_time_predictions.csv")
    oot.loc[oot.gsis_id == "00-D", "appear_1"] = np.nan          # D: no veteran row AND unknown rookie-season appearance
    shutil.rmtree(rookie_dir)
    rookie_dir = make_rookie_run(tmp_path, oot=oot)
    led = coverage_ledger(load_rookie_run(rookie_dir), load_veteran_run(make_veteran_run(tmp_path)), experience=1)
    assert led.set_index("player_id")["category"]["00-D"] == "no_veteran_row_appearance_unknown"


def test_run_audit_rejects_duplicate_or_empty_experiences_and_bad_draws(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        load_veteran_run,
        run_audit,
    )
    rookie_dir, vet_dir = runs
    r, v = load_rookie_run(rookie_dir), load_veteran_run(vet_dir)
    with pytest.raises(ValueError, match="experience"):
        run_audit(r, v, experiences=(1, 1), seed=1, draws=5)
    with pytest.raises(ValueError, match="experience"):
        run_audit(r, v, experiences=(), seed=1, draws=5)
    with pytest.raises(ValueError, match="draws"):
        run_audit(r, v, experiences=(1,), seed=1, draws=0)


def test_cli_rejects_duplicate_experiences(runs, tmp_path):
    import os
    import subprocess
    import sys
    rookie_dir, vet_dir = runs
    repo = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/dg165/audit_rookie_transition.py", "--rookie-run", str(rookie_dir), "--veteran-run", str(vet_dir),
         "--experience", "1", "1", "--seed", "1", "--draws", "5", "--runs-root", str(tmp_path / "runs")],
        capture_output=True, text=True, cwd=repo, env={**os.environ, "PYTHONPATH": "."},
    )
    assert proc.returncode != 0 and "experience" in (proc.stderr + proc.stdout).lower()
    assert not (tmp_path / "runs").exists()


def test_metrics_carry_the_separate_samples_caveat(runs):
    from src.dynasty_genius.rookie.transition_audit import (
        load_rookie_run,
        load_veteran_run,
        run_audit,
    )
    rookie_dir, vet_dir = runs
    res = run_audit(load_rookie_run(rookie_dir), load_veteran_run(vet_dir), experiences=(1, 2), seed=1, draws=5)
    text = res["metrics"]["definitions"]["caveats"]["experience_comparison"]
    assert "separate" in text and "within" in text
