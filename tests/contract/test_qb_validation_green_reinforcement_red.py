"""QB-1 GREEN reinforcement rows — slice-2 review blind spots, pinned forever.

Each R-row encodes one defect class from the Codex slice-2 review (ledger
2026-07-17 23:18, B1-B6/H1) so the repaired behavior can never silently
regress. Hermetic: injected loaders, tmp snapshot dirs, no network, no
gitignored artifact assertions.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

import src.dynasty_genius.eval.qb_validation as qbv
from src.dynasty_genius.adapters import nflreadpy_qb_adapter as adapter
from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

F = qbv.QBValidationFailure


def _frame(columns, rows=2, overrides=None):
    data = {c: [1] * rows for c in columns}
    if overrides:
        data.update(overrides)
    return pd.DataFrame(data)


def _ok_state(tmp_path, dataset="weekly"):
    # The snapshot must EXIST on disk (round-2 B1): write a real file.
    snapshot = tmp_path / f"{dataset}.parquet"
    snapshot.write_bytes(b"snapshot")
    return {
        "status": "ok",
        "frame": _frame(("a",)),
        "metadata": {
            "dataset": dataset,
            "raw_snapshot_path": str(snapshot),
            "source_timestamp": "2026-07-17T00:00:00+00:00",
            "parser_version": adapter.VALIDATION_PARSER_VERSION,
            "completeness": "ok",
        },
    }


def _ok_pool(tmp_path):
    return {name: _ok_state(tmp_path, name) for name in qbv.VALIDATION_DATASETS}


# --- R1 (B1): the pinned column contract carries the study -----------------
def test_r1_pins_carry_names_scoring_discriminators_and_parsed_fields():
    pins = adapter.VALIDATION_DATASET_COLUMNS
    assert "pfr_player_name" in pins["draft_picks"]
    assert "display_name" in pins["players"]
    weekly = set(pins["weekly"])
    assert {"season_type", "passing_yards", "passing_tds", "passing_interceptions",
            "rushing_yards", "rushing_tds", "receptions", "receiving_yards",
            "receiving_tds", "sack_fumbles_lost", "rushing_fumbles_lost",
            "receiving_fumbles_lost", "passing_2pt_conversions",
            "rushing_2pt_conversions", "receiving_2pt_conversions"} <= weekly
    assert "interceptions" not in weekly and "fumbles_lost" not in weekly
    assert "season_type" in pins["pbp"]
    entry = SOURCE_REGISTRY["nflreadpy_qb_validation"]
    flattened = {c for cols in pins.values() for c in cols}
    assert flattened <= set(entry.allowed_fields)
    assert "offense_team" in entry.allowed_fields  # the parsed rename is registered


def test_r1_draft_join_reads_the_production_name_columns():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "DRAFTED" and out["matched_by"] == "name_season"


# --- R2 (B2): mandatory snapshots + registered temporal scopes -------------
def test_r2_snapshot_is_written_even_when_no_dir_is_supplied(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "_DEFAULT_SNAPSHOT_ROOT", tmp_path / "raw")
    frame = _frame(adapter.VALIDATION_DATASET_COLUMNS["players"])
    out = adapter.load_validation_players(loader=lambda: frame)
    assert out["metadata"]["raw_snapshot_path"] is not None
    assert list((tmp_path / "raw").glob("players-*.parquet"))


@pytest.mark.parametrize("seasons", [[2014], [2026], [2020, 1999], [], ["not-a-year"]])
def test_r2_out_of_scope_seasons_refuse_before_any_fetch(seasons):
    calls = []
    with pytest.raises(adapter.ValidationIngestError, match="season_out_of_scope"):
        adapter.load_validation_weekly_stats(
            seasons, loader=lambda: calls.append(1), snapshot_dir="/nonexistent"
        )
    assert calls == []  # the loader was never invoked


def test_r2_weekly_parse_drops_postseason_and_records_the_drop(tmp_path):
    frame = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["weekly"],
        rows=4,
        overrides={"season": [2024] * 4, "season_type": ["REG", "POST", "REG", "POST"]},
    )
    out = adapter.load_validation_weekly_stats(
        [2024], loader=lambda: frame, snapshot_dir=tmp_path
    )
    assert set(out["frame"]["season_type"]) == {"REG"}
    assert out["metadata"]["rows_dropped_at_parse"] == 2


def test_r2_draft_rows_outside_pinned_coverage_are_dropped(tmp_path):
    frame = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["draft_picks"],
        rows=4,
        overrides={"season": [1979, 1980, 2025, 2026]},
    )
    out = adapter.load_validation_draft_picks(loader=lambda: frame, snapshot_dir=tmp_path)
    assert sorted(out["frame"]["season"]) == [1980, 2025]
    assert out["metadata"]["rows_dropped_at_parse"] == 2


def test_r2_pbp_parse_filters_reg_then_renames(tmp_path):
    frame = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["pbp"],
        rows=2,
        overrides={"season": [2024, 2024], "season_type": ["REG", "POST"]},
    )
    out = adapter.load_validation_pbp([2024], loader=lambda: frame, snapshot_dir=tmp_path)
    assert "offense_team" in out["frame"].columns
    assert "posteam" not in out["frame"].columns
    assert len(out["frame"]) == 1


# --- R3 (B3): the source gate proves usable, provenance-bearing inputs -----
def test_r3_status_string_alone_is_not_admission():
    pool = {name: {"status": "ok"} for name in qbv.VALIDATION_DATASETS}
    with pytest.raises(F, match="source_unavailable"):
        qbv.load_validation_sources(pool)


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ({"frame": None}, "no parsed frame"),
        ({"frame": _frame(("a",), rows=0)}, "empty parsed frame"),
        ({"frame": object()}, "not a dataframe"),
        ({"metadata": None}, "provenance"),
        ({"metadata": {"raw_snapshot_path": None, "source_timestamp": "t",
                       "parser_version": "v", "completeness": "ok"}}, "snapshot absent"),
    ],
)
def test_r3_each_admission_defect_is_named(mutation, expected, tmp_path):
    pool = _ok_pool(tmp_path)
    pool["pbp"] = {**_ok_state(tmp_path, "pbp"), **mutation}
    with pytest.raises(F, match="source_unavailable") as exc:
        qbv.load_validation_sources(pool)
    assert expected in str(exc.value)


def test_r3_bad_completeness_is_named(tmp_path):
    pool = _ok_pool(tmp_path)
    state = _ok_state(tmp_path, "pbp")
    state["metadata"] = {**state["metadata"], "completeness": "partial"}
    pool["pbp"] = state
    with pytest.raises(F, match="source_unavailable.*completeness"):
        qbv.load_validation_sources(pool)


def test_r3_non_mapping_state_is_named_not_raw_attributeerror(tmp_path):
    pool = _ok_pool(tmp_path)
    pool["weekly"] = "ok"
    with pytest.raises(F, match="source_unavailable.*not a mapping"):
        qbv.load_validation_sources(pool)


# --- R8 (round-2 B1): usable means dataframe-shaped with a REAL snapshot ----
@pytest.mark.parametrize(
    "fake_frame", [[{"not": "a frame"}], "not-a-frame", ("a", "b")]
)
def test_r8_length_bearing_non_frames_are_refused(fake_frame, tmp_path):
    pool = _ok_pool(tmp_path)
    state = _ok_state(tmp_path, "weekly")
    state["frame"] = fake_frame
    pool["weekly"] = state
    with pytest.raises(F, match="source_unavailable.*not a dataframe"):
        qbv.load_validation_sources(pool)


def test_r8_nonexistent_snapshot_path_is_refused(tmp_path):
    pool = _ok_pool(tmp_path)
    state = _ok_state(tmp_path, "draft_picks")
    state["metadata"] = {
        **state["metadata"],
        "raw_snapshot_path": str(tmp_path / "does-not-exist.parquet"),
    }
    pool["draft_picks"] = state
    with pytest.raises(F, match="source_unavailable.*snapshot absent"):
        qbv.load_validation_sources(pool)


def test_r8_control_fully_usable_pool_admits(tmp_path):
    assert set(qbv.load_validation_sources(_ok_pool(tmp_path))) == set(
        qbv.VALIDATION_DATASETS
    )


# --- R4 (B4): registered policy is not a payload knob ----------------------
def test_r4_fold_floor_override_refused_and_floor_is_pinned():
    with pytest.raises(F, match="registration_override_refused"):
        qbv.evaluate_power_and_status({"folds": 1, "fold_floor": 1})
    assert (
        qbv.evaluate_power_and_status({"folds": 4})["support_status"]
        == "unsupported_power"
    )


@pytest.mark.parametrize("delta", [float("inf"), float("-inf"), float("nan")])
def test_r4_non_finite_evidence_is_refused_never_supported(delta):
    with pytest.raises(F, match="non_finite_evidence"):
        qbv.evaluate_power_and_status(
            {"folds": 8, "ci_excludes_zero": True, "direction": "registered",
             "pooled_delta": delta, "passes_fdr": True}
        )


@pytest.mark.parametrize("folds", ["8", 8.5, -1, True, None])
def test_r4_malformed_folds_are_named(folds):
    with pytest.raises(F, match="status_payload_malformed|status_payload_incomplete"):
        qbv.evaluate_power_and_status({"folds": folds})


# --- R5 (B5): gsis joins honor the cross-check closure ---------------------
STUDY_GSIS = {"gsis_id": "00-1", "display_name": "Chad Example",
              "birth_date": "2000-09-01", "college_name": "Ohio State"}


def test_r5_gsis_join_with_failed_checks_triages_not_drafts():
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 29, "college": "Alabama"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])  # age delta 8 + college conflict
    assert out["resolution"] == "TRIAGE" and out["reason"] == "cross_check_conflict"
    row_age_only = {**row, "college": "Ohio State"}
    assert qbv.resolve_draft_join(STUDY_GSIS, [row_age_only])["resolution"] == "TRIAGE"


def test_r5_gsis_join_with_uncomputable_checks_stays_drafted_degraded():
    study = {"gsis_id": "00-1", "display_name": "Chad Example"}  # no DOB/college
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": None}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["age_check"]["computable"] is False
    assert out["college_check"]["result"] == "missing"


# --- R6 (B6): recursive decision_supported on every nested model -----------
def test_r6_list_element_model_missing_the_flag_refuses():
    with pytest.raises(F, match="decision_supported_missing_on_model"):
        qbv.validate_report_output(
            {"decision_supported": False, "comparisons": [{"pooled_delta": -0.2}]}
        )
    with pytest.raises(F, match="decision_supported_missing_on_model"):
        qbv.validate_report_output(
            {"decision_supported": False,
             "folds": [{"decision_supported": False,
                        "nested": [{"deep_model": 1}]}]}
        )


def test_r6_plain_sub_mappings_are_not_models():
    report = {
        "decision_supported": False,
        "comparisons": [
            {"decision_supported": False, "ci95": {"lower": -0.1, "upper": 0.2}}
        ],
    }
    assert qbv.validate_report_output(report) is report


# --- R7 (H1): malformed externals stay inside the named vocabulary ---------
def test_r7_unparseable_draft_season_triages():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example",
           "season": "not-a-year", "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "missing_draft_row_season"


def test_r7_datetime_inputs_normalize_instead_of_typeerror():
    qbv.validate_as_of_dates(
        model_feature_date=datetime(2024, 12, 30, 23, 59),
        model_cutoff=date(2024, 12, 31),
        market_date="2025-09-07",
        market_cutoff=datetime(2025, 9, 8, 12, 0),
    )
    with pytest.raises(F, match="as_of_date_unparseable"):
        qbv.validate_as_of_dates(
            model_feature_date=object(), model_cutoff=date(2024, 12, 31),
            market_date="2025-09-07", market_cutoff="2025-09-08",
        )


# --- R9 (round-2 B2): bounded folds, strictly-boolean evidence -------------
def test_r9_impossible_fold_count_is_refused():
    with pytest.raises(F, match="status_payload_malformed.*exceeds"):
        qbv.evaluate_power_and_status(
            {"folds": 9, "ci_excludes_zero": True, "direction": "registered",
             "pooled_delta": 0.10, "passes_fdr": True}
        )


@pytest.mark.parametrize("flag", ["ci_excludes_zero", "passes_fdr"])
@pytest.mark.parametrize("value", ["false", "true", 1, 0.0])
def test_r9_truthy_non_bool_conjuncts_are_refused(flag, value):
    payload = {"folds": 8, "ci_excludes_zero": True, "direction": "registered",
               "pooled_delta": 0.10, "passes_fdr": True}
    payload[flag] = value
    with pytest.raises(F, match="status_payload_malformed.*must be a bool"):
        qbv.evaluate_power_and_status(payload)


def test_r9_control_real_bools_still_support():
    out = qbv.evaluate_power_and_status(
        {"folds": 8, "ci_excludes_zero": True, "direction": "registered",
         "pooled_delta": 0.10, "passes_fdr": True}
    )
    assert out["support_status"] == "supported"


# --- R10 (round-2 B3): DRAFTED records carry their capital -----------------
def test_r10_gsis_drafted_carries_normalized_capital():
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["is_udfa"] == 0
    assert out["draft_round"] == 2 and out["draft_overall"] == 40


def test_r10_null_gsis_fallback_carries_capital_and_stable_row_id():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example", "season": 2022,
           "round": 6, "pick": 199, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["draft_round"] == 6 and out["draft_overall"] == 199
    assert out["draft_row_id"] == "draft:2022:r6:p199"


def test_r10_unreadable_capital_on_a_matched_row_triages_never_imputes():
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": None, "pick": "forty", "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "drafted_but_unjoinable"


# --- R11 (round-2 H1): temporal keys are exact, requested = fetched --------
@pytest.mark.parametrize("seasons", [[2024.9], [2024.0], ["2024"]])
def test_r11_non_int_season_requests_refuse_never_truncate(seasons):
    with pytest.raises(adapter.ValidationIngestError, match="season_out_of_scope"):
        adapter.load_validation_weekly_stats(
            seasons, loader=lambda: None, snapshot_dir="/nonexistent"
        )


def test_r11_fetched_rows_outside_the_request_fail_closed(tmp_path):
    frame = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["weekly"],
        overrides={"season": [2024, 2026], "season_type": ["REG", "REG"]},
    )
    with pytest.raises(adapter.ValidationIngestError, match="season_out_of_scope"):
        adapter.load_validation_weekly_stats(
            [2024], loader=lambda: frame, snapshot_dir=tmp_path
        )


# --- R12 (round-3 B1): closed lane vocabulary — nothing falls open ----------
@pytest.mark.parametrize("lane", ["H5", "h5 ", " H5"])
def test_r12_h5_spellings_refuse_named_never_model_support(lane):
    with pytest.raises(F, match="h5_status_not_implemented"):
        qbv.evaluate_power_and_status(
            {"lane": lane, "folds": 8, "ci_excludes_zero": True,
             "direction": "registered", "pooled_delta": 0.10, "passes_fdr": True}
        )


@pytest.mark.parametrize("lane", ["market", "Model2", 5, ["model"]])
def test_r12_unknown_lanes_refuse_named(lane):
    with pytest.raises(F, match="status_payload_malformed.*unknown lane"):
        qbv.evaluate_power_and_status(
            {"lane": lane, "folds": 8, "ci_excludes_zero": True,
             "direction": "registered", "pooled_delta": 0.10, "passes_fdr": True}
        )


@pytest.mark.parametrize("payload_lane", [{}, {"lane": "model"}, {"lane": "MODEL"}])
def test_r12_control_model_lane_explicit_or_omitted_still_works(payload_lane):
    payload = {"folds": 8, "ci_excludes_zero": True, "direction": "registered",
               "pooled_delta": 0.10, "passes_fdr": True, **payload_lane}
    assert qbv.evaluate_power_and_status(payload)["support_status"] == "supported"


# --- R13 (round-3 B2): draft capital is 1-indexed; no guessed ceiling -------
@pytest.mark.parametrize("rnd,pick", [(0, 0), (-1, -5), (0, 40), (2, 0)])
def test_r13_non_positive_capital_triages_never_materializes(rnd, pick):
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": rnd, "pick": pick, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "drafted_but_unjoinable"
    assert "draft_round" not in out or out.get("draft_round") is None


def test_r13_control_historical_12_round_draft_is_legal():
    # The registered 1980-2025 coverage includes 12-round drafts: no ceiling.
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 1987,
           "round": 12, "pick": 336, "age": 21, "college": "Ohio State"}
    study = {"gsis_id": "00-1", "display_name": "Chad Example"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["draft_round"] == 12 and out["draft_overall"] == 336


# --- R14 (round-3 H1): datetime-like DOBs normalize into the age closure ----
@pytest.mark.parametrize(
    "dob", [datetime(2000, 9, 1, 14, 30), pd.Timestamp("2000-09-01T14:30:00")]
)
def test_r14_datetime_and_timestamp_dobs_compute_the_age_audit(dob):
    study = {"gsis_id": "00-1", "display_name": "Chad Example", "birth_date": dob,
             "college_name": "Ohio State"}
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["age_check"]["computable"] is True
    assert out["age_check"]["pass"] is True


# --- R16 (round-4 B1): fractional numerics never truncate, in ANY type ------
@pytest.mark.parametrize(
    "bad_round",
    [np.float32(1.5), np.float64(1.5), Decimal("1.5"), 1.5, np.nan],
)
def test_r16_fractional_capital_in_any_numeric_type_triages(bad_round):
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": bad_round, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "drafted_but_unjoinable"


@pytest.mark.parametrize(
    "good_round,expected", [(np.float32(2.0), 2), (np.int64(2), 2), (Decimal("2"), 2)]
)
def test_r16_control_integral_numerics_of_any_type_are_capital(good_round, expected):
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": good_round, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["draft_round"] == expected


def test_r16_fractional_fallback_season_triages_not_truncates():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example",
           "season": np.float32(2022.5), "round": 2, "pick": 40, "age": 21,
           "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "missing_draft_row_season"


# --- R18 (round-5 B1): boolean scalars are categorical, never capital -------
@pytest.mark.parametrize("field", ["round", "pick"])
@pytest.mark.parametrize("truthy", [np.bool_(True), np.bool_(False), True, False])
def test_r18_boolean_capital_of_any_representation_triages(field, truthy):
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    row[field] = truthy
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "drafted_but_unjoinable"


def test_r18_boolean_fallback_season_triages_without_raising():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example",
           "season": np.bool_(False), "round": 2, "pick": 40, "age": 21,
           "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])  # no raw ValueError from date(0,…)
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "missing_draft_row_season"


def test_r18_boolean_age_degrades_to_uncomputable():
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": np.bool_(True), "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "DRAFTED"  # primary key holds; check degraded
    assert out["age_check"]["computable"] is False


@pytest.mark.parametrize("good", [np.int64(1), 1, np.uint64(2)])
def test_r18_control_integral_scalars_remain_valid_capital(good):
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": good, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["draft_round"] == int(good)


# --- R19 (round-6 B1): missing-like names are no key, never shared identity -
_NULL_NAMES = [np.nan, pd.NaT, pd.NA, None]


@pytest.mark.parametrize("null_name", _NULL_NAMES)
def test_r19_both_sides_missing_names_triage_not_match(null_name):
    study = {"gsis_id": None, "display_name": null_name,
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": null_name, "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "missing_identity_keys"


@pytest.mark.parametrize("null_name", _NULL_NAMES)
def test_r19_study_only_missing_name_triages_never_udfa(null_name):
    study = {"gsis_id": None, "display_name": null_name,
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": "00-9", "pfr_player_name": "Someone Else", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "X"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "missing_identity_keys"


@pytest.mark.parametrize("null_name", _NULL_NAMES)
def test_r19_draft_only_missing_name_never_candidates(null_name):
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    null_row = {"gsis_id": None, "pfr_player_name": null_name, "season": 2022,
                "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [null_row])
    assert out["resolution"] == "UDFA"  # the null cell never matches by name


def test_r19_control_real_names_still_join_and_na_never_raises():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    assert qbv.resolve_draft_join(study, [row])["resolution"] == "DRAFTED"
    # pd.NA in the primary key slot with the fixture fallback key present:
    # no ambiguous-bool raise, the usable key wins.
    mixed = {**row, "pfr_player_name": pd.NA, "name": "Chad Example"}
    assert qbv.resolve_draft_join(study, [mixed])["resolution"] == "DRAFTED"


# --- R21 (round-7 B1): missing-like GSIS never raises, leaks, or matches ----
_NULL_KEYS = [np.nan, pd.NaT, pd.NA, None, "", "  "]


def _named_row(**overrides):
    row = {"gsis_id": None, "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    row.update(overrides)
    return row


@pytest.mark.parametrize("null_key", _NULL_KEYS)
def test_r21_study_null_gsis_falls_to_name_fallback_no_raise(null_key):
    study = {"gsis_id": null_key, "player_id": "p1", "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    out = qbv.resolve_draft_join(study, [_named_row()])
    assert out["resolution"] == "DRAFTED" and out["matched_by"] == "name_season"
    assert out["study_player_id"] == "p1"  # never a leaked NaN/NaT sentinel


@pytest.mark.parametrize("null_key", _NULL_KEYS)
def test_r21_null_draft_row_before_a_real_exact_match_is_skipped(null_key):
    study = {"gsis_id": "00-1", "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    rows = [_named_row(gsis_id=null_key, pfr_player_name="Someone Else"),
            _named_row(gsis_id="00-1")]
    out = qbv.resolve_draft_join(study, rows)
    assert out["resolution"] == "DRAFTED" and out["matched_by"] == "gsis"


@pytest.mark.parametrize("null_key", [np.nan, pd.NaT, pd.NA])
def test_r21_both_sides_null_gsis_use_the_name_key_no_raise(null_key):
    study = {"gsis_id": null_key, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    out = qbv.resolve_draft_join(study, [_named_row(gsis_id=null_key)])
    assert out["resolution"] == "DRAFTED" and out["matched_by"] == "name_season"


def test_r21_composite_row_id_survives_a_nan_draft_gsis():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    out = qbv.resolve_draft_join(study, [_named_row(gsis_id=np.nan)])
    assert out["draft_row_id"] == "draft:2022:r2:p40"  # composite, not NaN


# --- R20 (round-6 H1): date-unrepresentable seasons stay in the closure -----
@pytest.mark.parametrize(
    "bad_season", [0, -1, 10000, np.int64(0), np.uint64(10000)]
)
def test_r20_invalid_integral_season_on_gsis_degrades_no_raise(bad_season):
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example",
           "season": bad_season, "round": 2, "pick": 40, "age": 21,
           "college": "Ohio State"}
    out = qbv.resolve_draft_join(STUDY_GSIS, [row])
    assert out["resolution"] == "DRAFTED"  # primary key holds
    assert out["age_check"]["computable"] is False


@pytest.mark.parametrize("bad_season", [0, -1, 10000, np.int64(0)])
def test_r20_invalid_integral_season_on_fallback_triages_no_raise(bad_season):
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": "2000-09-01", "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example",
           "season": bad_season, "round": 2, "pick": 40, "age": 21,
           "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "missing_draft_row_season"


# --- R17 (round-4 H1): pandas NaT DOB degrades, never aborts ----------------
def test_r17_nat_dob_on_gsis_join_degrades_to_uncomputable():
    study = {"gsis_id": "00-1", "display_name": "Chad Example",
             "birth_date": pd.NaT, "college_name": "Ohio State"}
    row = {"gsis_id": "00-1", "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "DRAFTED"
    assert out["age_check"]["computable"] is False


def test_r17_nat_dob_on_fallback_triages_never_raises():
    study = {"gsis_id": None, "display_name": "Chad Example",
             "birth_date": pd.NaT, "college_name": "Ohio State"}
    row = {"gsis_id": None, "pfr_player_name": "Chad Example", "season": 2022,
           "round": 2, "pick": 40, "age": 21, "college": "Ohio State"}
    out = qbv.resolve_draft_join(study, [row])
    assert out["resolution"] == "TRIAGE"
    assert out["reason"] == "drafted_but_unjoinable"


# --- R15 (round-3 H2): non-finite fetched seasons refuse named --------------
def test_r15_infinite_fetched_seasons_refuse_named_not_raw_pandas(tmp_path):
    weekly = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["weekly"],
        overrides={"season": [float("inf")] * 2, "season_type": ["REG", "REG"]},
    )
    with pytest.raises(adapter.ValidationIngestError, match="non-finite"):
        adapter.load_validation_weekly_stats(
            [2024], loader=lambda: weekly, snapshot_dir=tmp_path
        )
    draft = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["draft_picks"],
        overrides={"season": [float("-inf"), 2020]},
    )
    with pytest.raises(adapter.ValidationIngestError, match="non-finite"):
        adapter.load_validation_draft_picks(loader=lambda: draft, snapshot_dir=tmp_path)


def test_r11_fractional_or_unparseable_fetched_seasons_fail_closed(tmp_path):
    fractional = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["draft_picks"],
        overrides={"season": [2024.5, 2020]},
    )
    with pytest.raises(adapter.ValidationIngestError, match="non-integral"):
        adapter.load_validation_draft_picks(
            loader=lambda: fractional, snapshot_dir=tmp_path
        )
    garbage = _frame(
        adapter.VALIDATION_DATASET_COLUMNS["pbp"],
        overrides={"season": ["soon", "2024"], "season_type": ["REG", "REG"]},
    )
    with pytest.raises(adapter.ValidationIngestError, match="unparseable"):
        adapter.load_validation_pbp([2024], loader=lambda: garbage, snapshot_dir=tmp_path)
