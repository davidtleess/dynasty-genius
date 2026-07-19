"""QB-1 GREEN reinforcement rows — slice-2 review blind spots, pinned forever.

Each R-row encodes one defect class from the Codex slice-2 review (ledger
2026-07-17 23:18, B1-B6/H1) so the repaired behavior can never silently
regress. Hermetic: injected loaders, tmp snapshot dirs, no network, no
gitignored artifact assertions.
"""

from __future__ import annotations

import decimal
from collections import abc as cabc
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction

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


# ============================================================================
# Slice 3 (D2 label table) reinforcement — R22-R27, pinned from the GREEN
# self-probe (65 probes, ledger 2026-07-18). One row class per defect class;
# the predicate-column KeyError the self-probe caught pre-routing is pinned
# in R22/R24 (attempts/sacks_suffered/carries are validated predicate inputs,
# not scoring components).
# ============================================================================

_D2_SETTINGS = {
    "pass_yd": 0.04, "pass_td": 4.0, "pass_int": -2.0, "pass_2pt": 2.0,
    "rush_yd": 0.1, "rush_td": 6.0, "rush_2pt": 2.0,
    "rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0, "rec_2pt": 2.0,
    "fum_lost": -2.0,
}


def _d2_hash(settings=None):
    return qbv.settings_hash(_D2_SETTINGS if settings is None else settings)


def _wk(player="00-0000001", season=2024, week=1, st="REG", **stats):
    base = {
        "player_id": player, "season": season, "week": week, "season_type": st,
        "attempts": 0, "carries": 0, "sacks_suffered": 0,
        "passing_yards": 0, "passing_tds": 0, "passing_interceptions": 0,
        "rushing_yards": 0, "rushing_tds": 0,
        "receptions": 0, "receiving_yards": 0, "receiving_tds": 0,
        "sack_fumbles_lost": 0, "rushing_fumbles_lost": 0,
        "receiving_fumbles_lost": 0,
        "passing_2pt_conversions": 0, "rushing_2pt_conversions": 0,
        "receiving_2pt_conversions": 0,
    }
    base.update(stats)
    return base


_D2_LABEL = {
    "player_id": "00-1", "season": 2024, "outcome_class": "evaluable",
    "qualifying_games": 10, "points_total": 200.0, "ppg": 20.0,
}

_D2_GOLDEN = [
    {"stats": {"passing_yards": 300, "passing_tds": 2,
               "passing_interceptions": 1}, "expected_points": 18.0},
    {"stats": {"receptions": 3, "receiving_yards": 25, "receiving_tds": 1},
     "expected_points": 11.5},
    {"stats": {"sack_fumbles_lost": 1, "rushing_fumbles_lost": 1,
               "receiving_fumbles_lost": 1}, "expected_points": -6.0},
    {"stats": {"passing_2pt_conversions": 1, "rushing_2pt_conversions": 1,
               "receiving_2pt_conversions": 1}, "expected_points": 6.0},
]

_D2_CLASSIFIED = [
    {"player_id": "00-1", "season": 2024, "outcome_class": "evaluable",
     "qualifying_games": 8, "ppg": 15.0},
    {"player_id": "00-2", "season": 2024, "outcome_class": "no_target_season"},
    {"player_id": "00-3", "season": 2024, "outcome_class": "rookie_no_priors"},
]
_D2_ATTRITION = {"no_target_season": 1, "rookie_no_priors": 1}


# --- R22: hand-computed build + the pinned qualifying predicate -------------
def test_r22_hand_computed_ppg_over_qualifying_games_only():
    rows = [
        _wk(week=1, attempts=30, passing_yards=300, passing_tds=2,
            passing_interceptions=1),                      # 12 + 8 - 2 = 18
        _wk(week=2, carries=5, rushing_yards=50, rushing_tds=1),  # 5 + 6 = 11
        _wk(week=3),                     # non-qualifying: excluded BOTH sides
    ]
    out = qbv.build_label_table(rows, _D2_SETTINGS,
                                expected_settings_hash=_d2_hash())
    (label,) = out["labels"]
    assert label["qualifying_games"] == 2
    assert label["points_total"] == 29.0
    assert label["ppg"] == 14.5
    assert label["outcome_class"] == "evaluable"
    assert out["settings_hash"] == _d2_hash()
    assert out["season_type"] == "REG"
    assert out["unscored_settings_keys"] == []


@pytest.mark.parametrize(
    "stats,expected_games",
    [
        ({"sacks_suffered": 1}, 1),          # attempts=0, sacks=1 qualifies
        ({"carries": 1}, 1),                 # carries alone qualifies
        ({"attempts": 1}, 1),                # attempts alone qualifies
    ],
)
def test_r22_qualifying_predicate_boundaries(stats, expected_games):
    out = qbv.build_label_table([_wk(week=1, **stats)], _D2_SETTINGS,
                                expected_settings_hash=_d2_hash())
    assert out["labels"][0]["qualifying_games"] == expected_games


def test_r22_zero_qualifying_player_season_is_rostered_not_labeled():
    out = qbv.build_label_table([_wk(week=1)], _D2_SETTINGS,
                                expected_settings_hash=_d2_hash())
    assert out["labels"] == []
    assert out["zero_qualifying_player_seasons"] == [
        {"player_id": "00-0000001", "season": 2024}
    ]


def test_r22_negative_yardage_is_legal_and_unclamped():
    out = qbv.build_label_table(
        [_wk(week=1, carries=3, rushing_yards=-7)], _D2_SETTINGS,
        expected_settings_hash=_d2_hash())
    assert out["labels"][0]["points_total"] == pytest.approx(-0.7)


def test_r22_pandas_records_with_numpy_scalars_build_exactly():
    frame = pd.DataFrame([
        _wk(week=1, attempts=30, passing_yards=300.0, passing_tds=2,
            passing_interceptions=1),
        _wk(week=2, attempts=25, passing_yards=210.0),
    ])
    out = qbv.build_label_table(frame.to_dict("records"), _D2_SETTINGS,
                                expected_settings_hash=_d2_hash())
    assert out["labels"][0]["qualifying_games"] == 2
    assert out["labels"][0]["points_total"] == 26.4


def test_r22_empty_weekly_input_is_a_lawful_empty_table():
    out = qbv.build_label_table([], _D2_SETTINGS,
                                expected_settings_hash=_d2_hash())
    assert out["labels"] == []
    assert out["zero_qualifying_player_seasons"] == []


# --- R23: the settings law (hash, coverage, snapshot validity, disclosure) --
def test_r23_settings_hash_mismatch_fails_the_run():
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1)], _D2_SETTINGS,
                              expected_settings_hash="beef")
    assert err.value.reason == "settings_hash_mismatch"


@pytest.mark.parametrize("bad_pin", [None, "", 42, float("nan")])
def test_r23_malformed_expected_hash_refuses(bad_pin):
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1)], _D2_SETTINGS,
                              expected_settings_hash=bad_pin)
    assert err.value.reason == "settings_hash_mismatch"


def test_r23_absent_pinned_scoring_key_refuses_never_defaults():
    partial = {k: v for k, v in _D2_SETTINGS.items() if k != "rec"}
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1)], partial,
                              expected_settings_hash=_d2_hash(partial))
    assert err.value.reason == "scoring_setting_missing"
    assert "rec" in err.value.detail


@pytest.mark.parametrize("bad_value", ["four", True, np.bool_(False),
                                       float("inf"), None])
def test_r23_invalid_scoring_value_refuses(bad_value):
    bad = dict(_D2_SETTINGS, pass_td=bad_value)
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1)], bad,
                              expected_settings_hash=_d2_hash(bad))
    assert err.value.reason == "settings_snapshot_invalid"


def test_r23_unserializable_snapshot_refuses_at_hash():
    with pytest.raises(F) as err:
        qbv.settings_hash({"pass_yd": {1, 2}})
    assert err.value.reason == "settings_snapshot_invalid"


def test_r23_non_mapping_settings_refuses():
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1)], [1, 2],
                              expected_settings_hash="x")
    assert err.value.reason == "settings_snapshot_invalid"


def test_r23_team_only_extras_disclosed_zero_extras_silent():
    # Expectation lawfully flipped TWICE (both ledgered): round-1 B1 removed
    # unclassified disclosure; round-2 B1 narrowed disclosure to the exact
    # team-only allowlist (points/yards-allowed brackets). Zero stays inert.
    extra = dict(_D2_SETTINGS, pts_allow_0=10.0, yds_allow_550p=-3.0,
                 bonus_pass_yd_300=0.0)
    out = qbv.build_label_table([_wk(week=1, attempts=1)], extra,
                                expected_settings_hash=_d2_hash(extra))
    assert out["unscored_settings_keys"] == ["pts_allow_0", "yds_allow_550p"]


# --- R24: weekly-row fail-closed classes (incl. the predicate columns) ------
@pytest.mark.parametrize("dropped", ["receptions", "attempts", "carries",
                                     "sacks_suffered", "season_type"])
def test_r24_absent_pinned_column_refuses(dropped):
    row = _wk(week=1, attempts=1)
    del row[dropped]
    with pytest.raises(F) as err:
        qbv.build_label_table([row], _D2_SETTINGS,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "label_row_invalid"
    assert dropped in err.value.detail


@pytest.mark.parametrize(
    "column,bad",
    [
        ("attempts", None), ("attempts", float("nan")), ("attempts", pd.NA),
        ("attempts", np.bool_(True)), ("attempts", np.float32(1.5)),
        ("attempts", Fraction(3, 2)), ("receptions", -2),
        ("passing_yards", float("inf")), ("carries", True),
    ],
)
def test_r24_invalid_stat_values_refuse_named_never_raw(column, bad):
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, **{column: bad})], _D2_SETTINGS,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "stat_value_invalid"
    assert column in err.value.detail


def test_r24_integral_numpy_scalars_are_legal_stats():
    out = qbv.build_label_table(
        [_wk(week=1, attempts=np.int64(30), passing_yards=np.float64(250.0))],
        _D2_SETTINGS, expected_settings_hash=_d2_hash())
    assert out["labels"][0]["points_total"] == 10.0


@pytest.mark.parametrize(
    "identity",
    [
        {"player": None}, {"player": np.nan}, {"player": "  "},
        {"season": 0}, {"season": 10000}, {"season": 2024.5},
        {"season": None}, {"week": None}, {"week": -1},
    ],
)
def test_r24_unusable_identity_refuses(identity):
    kwargs = {"week": 1, "attempts": 1}
    kwargs.update(identity)
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(**kwargs)], _D2_SETTINGS,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "label_row_invalid"


def test_r24_postseason_row_refuses_named():
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=19, st="POST", attempts=20)],
                              _D2_SETTINGS, expected_settings_hash=_d2_hash())
    assert err.value.reason == "non_regular_season_row"


def test_r24_duplicate_weekly_row_refuses_double_counting():
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=1, attempts=1), _wk(week=1, attempts=2)], _D2_SETTINGS,
            expected_settings_hash=_d2_hash())
    assert err.value.reason == "duplicate_weekly_row"


@pytest.mark.parametrize("bad_rows", ["rows", {"a": 1}, [["not"]], [None], 42])
def test_r24_wrong_shaped_weekly_input_refuses(bad_rows):
    with pytest.raises(F) as err:
        qbv.build_label_table(bad_rows, _D2_SETTINGS,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "label_row_invalid"


def test_r24_pandas_nan_cell_refuses_named():
    frame = pd.DataFrame([_wk(week=1, attempts=30), _wk(week=2, attempts=None)])
    with pytest.raises(F) as err:
        qbv.build_label_table(frame.to_dict("records"), _D2_SETTINGS,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "stat_value_invalid"


# --- R25: the F11 label-table law -------------------------------------------
def test_r25_valid_label_table_passes():
    assert qbv.validate_label_table([_D2_LABEL]) == [_D2_LABEL]


def test_r25_duplicate_player_season_refuses():
    with pytest.raises(F) as err:
        qbv.validate_label_table([_D2_LABEL, dict(_D2_LABEL)])
    assert err.value.reason == "duplicate_player_season"


@pytest.mark.parametrize("bad_ppg", [float("nan"), float("inf"), True,
                                     np.bool_(False), "high", None])
def test_r25_invalid_ppg_refuses_non_finite_ppg(bad_ppg):
    with pytest.raises(F) as err:
        qbv.validate_label_table([dict(_D2_LABEL, ppg=bad_ppg)])
    assert err.value.reason == "non_finite_ppg"


def test_r25_absent_ppg_refuses():
    row = {k: v for k, v in _D2_LABEL.items() if k != "ppg"}
    with pytest.raises(F) as err:
        qbv.validate_label_table([row])
    assert err.value.reason == "non_finite_ppg"


@pytest.mark.parametrize("bad_games", [0, -1, None, 2.5, np.bool_(True)])
def test_r25_missing_or_invalid_games_refuses(bad_games):
    with pytest.raises(F) as err:
        qbv.validate_label_table([dict(_D2_LABEL, qualifying_games=bad_games)])
    assert err.value.reason == "missing_games"


def test_r25_attrition_classified_row_refuses_inside_the_label_table():
    with pytest.raises(F) as err:
        qbv.validate_label_table(
            [dict(_D2_LABEL, outcome_class="no_target_season")])
    assert err.value.reason == "label_row_invalid"


def test_r25_non_finite_points_total_refuses():
    with pytest.raises(F) as err:
        qbv.validate_label_table([dict(_D2_LABEL, points_total=float("nan"))])
    assert err.value.reason == "non_finite_ppg"


# --- R26: the F21 golden-row law ---------------------------------------------
def test_r26_golden_edge_set_matches_exactly():
    qbv.validate_scoring_edges(_D2_GOLDEN, _D2_SETTINGS,
                               expected_hash=_d2_hash())


def test_r26_hash_mismatch_fails_the_run():
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(_D2_GOLDEN, _D2_SETTINGS,
                                   expected_hash="feed")
    assert err.value.reason == "settings_hash_mismatch"


def test_r26_one_wrong_expectation_refuses_exactly():
    off = _D2_GOLDEN[:-1] + [dict(_D2_GOLDEN[-1], expected_points=6.1)]
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(off, _D2_SETTINGS, expected_hash=_d2_hash())
    assert err.value.reason == "golden_scoring_mismatch"


def test_r26_under_covering_golden_set_refuses():
    no_receiving = [_D2_GOLDEN[0], _D2_GOLDEN[2], _D2_GOLDEN[3]]
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(no_receiving, _D2_SETTINGS,
                                   expected_hash=_d2_hash())
    assert err.value.reason == "golden_coverage_missing"
    assert "receptions" in err.value.detail


def test_r26_empty_golden_set_refuses():
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges([], _D2_SETTINGS, expected_hash=_d2_hash())
    assert err.value.reason == "golden_row_invalid"


def test_r26_unknown_stat_key_refuses_never_scores_zero():
    typo = _D2_GOLDEN + [{"stats": {"recieving_yards": 10},
                          "expected_points": 1.0}]
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(typo, _D2_SETTINGS, expected_hash=_d2_hash())
    assert err.value.reason == "unknown_stat_column"


def test_r26_sparse_stat_line_scores_exactly():
    assert qbv.score_stat_line(
        {"passing_yards": 300, "passing_tds": 2, "passing_interceptions": 1},
        _D2_SETTINGS,
    ) == Decimal("18")


def test_r26_pass_int_term_is_settings_derived_not_hardcoded():
    # The same stat line under a pass_int=-1 snapshot scores differently:
    # the -2 lives in David's league snapshot, never in code.
    alt = dict(_D2_SETTINGS, pass_int=-1.0)
    assert qbv.score_stat_line(
        {"passing_interceptions": 2}, alt) == Decimal("-2")
    assert qbv.score_stat_line(
        {"passing_interceptions": 2}, _D2_SETTINGS) == Decimal("-4")


# --- R27: the F28 attrition law ----------------------------------------------
def test_r27_exhaustive_classified_table_passes():
    qbv.validate_attrition_classes(_D2_CLASSIFIED, _D2_ATTRITION)


@pytest.mark.parametrize(
    "bad_row",
    [{"outcome_class": "dropped"}, {"player_id": "00-4", "season": 2024}],
)
def test_r27_unknown_or_absent_class_refuses(bad_row):
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(_D2_CLASSIFIED + [bad_row],
                                       _D2_ATTRITION)
    assert err.value.reason == "attrition_class_unknown"


@pytest.mark.parametrize(
    "attrition",
    [
        {"no_target_season": 2, "rookie_no_priors": 1},   # count mismatch
        {"no_target_season": 1},                          # omitted class
        {"no_target_season": 1, "rookie_no_priors": 1, "other": 0},
        {"no_target_season": True, "rookie_no_priors": 1},  # bool count
        [1],                                              # not a mapping
    ],
)
def test_r27_dishonest_attrition_table_refuses(attrition):
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(_D2_CLASSIFIED, attrition)
    assert err.value.reason == "attrition_count_mismatch"


def test_r27_attrition_row_carrying_zero_ppg_refuses_imputed_number():
    rows = _D2_CLASSIFIED + [{"player_id": "00-5", "season": 2024,
                              "outcome_class": "no_target_season", "ppg": 0.0}]
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            rows, {"no_target_season": 2, "rookie_no_priors": 1})
    assert err.value.reason == "attrition_row_carries_metrics"


def test_r27_attrition_row_with_qualifying_games_is_a_class_conflict():
    rows = _D2_CLASSIFIED + [{"player_id": "00-6", "season": 2024,
                              "outcome_class": "no_target_season",
                              "qualifying_games": 3}]
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            rows, {"no_target_season": 2, "rookie_no_priors": 1})
    assert err.value.reason == "outcome_class_conflict"


# --- R28 (round-1 B1): active QB-applicable extras fail closed --------------
@pytest.mark.parametrize(
    "key,value",
    [("bonus_pass_yd_300", 3.0), ("pass_fd", 0.5), ("bonus_rec_te", 0.5)],
)
def test_r28_unclassified_active_scoring_rule_refuses_the_build(key, value):
    # ("weird", "abc") moved to R34 under round-2 H1: an UNPARSEABLE value
    # refuses as a malformed snapshot BEFORE vocabulary classification.
    extra = dict(_D2_SETTINGS, **{key: value})
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=1, attempts=30, passing_yards=300)], extra,
            expected_settings_hash=_d2_hash(extra))
    assert err.value.reason == "scoring_setting_unsupported"
    assert key in err.value.detail


def test_r28_codex_probe_bonus_key_never_understates_ppg():
    # The exact round-1 probe: bonus_pass_yd_300=3.0 + a 300-yard week must
    # refuse, never emit points_total=12.0 as "Sleeper-scored".
    extra = dict(_D2_SETTINGS, bonus_pass_yd_300=3.0)
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=1, attempts=30, passing_yards=300)], extra,
            expected_settings_hash=_d2_hash(extra))
    assert err.value.reason == "scoring_setting_unsupported"


def test_r28_score_stat_line_inherits_the_unsupported_law():
    extra = dict(_D2_SETTINGS, bonus_pass_yd_300=3.0)
    with pytest.raises(F) as err:
        qbv.score_stat_line({"passing_yards": 300}, extra)
    assert err.value.reason == "scoring_setting_unsupported"


@pytest.mark.parametrize("key,value", [("pts_allow_0", 10.0),
                                       ("pts_allow", 1.0),
                                       ("yds_allow_550p", -3.0)])
def test_r28_team_only_actives_disclose_and_build(key, value):
    # Param set lawfully narrowed by round-2 B1 (ledgered): the former
    # fgm/def_td/idp_tkl/int/sack disclose-controls now refuse — R33 pins
    # them on the refusal side.
    extra = dict(_D2_SETTINGS, **{key: value})
    out = qbv.build_label_table([_wk(week=1, attempts=1)], extra,
                                expected_settings_hash=_d2_hash(extra))
    assert out["unscored_settings_keys"] == [key]


# --- R33 (round-2 B1): player-scoring rules are never "non-QB by vibes" -----
def test_r33_live_snapshot_mirror_refuses_never_understates():
    # Hermetic mirror of David's LIVE league snapshot's active extra rules
    # (st_td/st_ff/st_fum_rec/fum_rec_td — Codex round-2 evidence): Sleeper
    # defines these as individual-player scoring, so a 12-point "labeled"
    # week under them is understated. The build must refuse, not disclose.
    live_mirror = dict(_D2_SETTINGS, st_td=6.0, st_ff=1.0, st_fum_rec=1.0,
                       fum_rec_td=6.0)
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=1, attempts=30, passing_yards=300)], live_mirror,
            expected_settings_hash=_d2_hash(live_mirror))
    assert err.value.reason == "scoring_setting_unsupported"
    for key in ("st_td", "st_ff", "st_fum_rec", "fum_rec_td"):
        assert key in err.value.detail


@pytest.mark.parametrize(
    "key,value",
    [("st_td", 6.0), ("st_ff", 1.0), ("st_fum_rec", 1.0), ("fum_rec_td", 6.0),
     ("idp_tkl", 1.0), ("def_td", 6.0), ("fgm", 3.0), ("int", 2.0),
     ("sack", 1.0), ("blk_kick", 2.0)],
)
def test_r33_individual_player_scoring_rules_refuse(key, value):
    extra = dict(_D2_SETTINGS, **{key: value})
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, attempts=1)], extra,
                              expected_settings_hash=_d2_hash(extra))
    assert err.value.reason == "scoring_setting_unsupported"


# --- R34 (round-2 H1): unparseable extras + collision keys fail closed ------
@pytest.mark.parametrize(
    "key,value",
    [("def_td", None), ("st_td", "not-a-number"), ("fgm", "bad"),
     ("idp_tkl", None), ("pts_allow_0", "garbage"),
     ("pts_allow_0", float("nan")), ("weird", "abc")],
)
def test_r34_unparseable_extra_values_refuse_before_classification(key, value):
    # Even an ALLOWLISTED key with an unparseable value is a malformed
    # snapshot — refused named, never disclosed and never silent.
    extra = dict(_D2_SETTINGS, **{key: value})
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, attempts=1)], extra,
                              expected_settings_hash=_d2_hash(extra))
    assert err.value.reason == "settings_snapshot_invalid"


@pytest.mark.parametrize(
    "key",
    ["fg_qb_bonus", "fgarbage", "st_unknown_qb_event", "idp_unknown",
     "pts_allow_x", "yds_allowance"],
)
def test_r34_family_lookalike_keys_refuse_exact_vocabulary_only(key):
    extra = dict(_D2_SETTINGS, **{key: 1.0})
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, attempts=1)], extra,
                              expected_settings_hash=_d2_hash(extra))
    assert err.value.reason == "scoring_setting_unsupported"


# --- R29 (round-1 B2): edge coverage is earned by nonzero stats -------------
def test_r29_all_zero_golden_set_is_vacuous_and_refuses():
    zero_row = {"stats": {c: 0 for c in (
        "passing_interceptions", "passing_2pt_conversions",
        "rushing_2pt_conversions", "receptions", "receiving_yards",
        "receiving_tds", "receiving_2pt_conversions", "sack_fumbles_lost",
        "rushing_fumbles_lost", "receiving_fumbles_lost")},
        "expected_points": 0.0}
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges([zero_row], _D2_SETTINGS,
                                   expected_hash=_d2_hash())
    assert err.value.reason == "golden_coverage_missing"


def test_r29_zero_valued_edge_key_does_not_count_as_covered():
    # Receiving keys present but zero across the set -> receiving uncovered.
    padded = [dict(_D2_GOLDEN[0]), _D2_GOLDEN[2], _D2_GOLDEN[3]]
    padded[0] = {"stats": dict(_D2_GOLDEN[0]["stats"], receptions=0,
                               receiving_yards=0, receiving_tds=0),
                 "expected_points": 18.0}
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(padded, _D2_SETTINGS,
                                   expected_hash=_d2_hash())
    assert err.value.reason == "golden_coverage_missing"
    assert "receptions" in err.value.detail


def test_r29_nonzero_covering_golden_set_still_passes():
    qbv.validate_scoring_edges(_D2_GOLDEN, _D2_SETTINGS,
                               expected_hash=_d2_hash())


# --- R30 (round-1 H1): both directions of the F28 class invariant -----------
@pytest.mark.parametrize("bad_games", [-1, True, "garbage", 2.5,
                                       np.bool_(False)])
def test_r30_present_malformed_games_on_attrition_row_refuses(bad_games):
    rows = _D2_CLASSIFIED + [{"player_id": "00-7", "season": 2024,
                              "outcome_class": "no_target_season",
                              "qualifying_games": bad_games}]
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            rows, {"no_target_season": 2, "rookie_no_priors": 1})
    assert err.value.reason == "label_row_invalid"


def test_r30_explicit_zero_games_on_attrition_row_is_lawful():
    rows = _D2_CLASSIFIED + [{"player_id": "00-7", "season": 2024,
                              "outcome_class": "no_target_season",
                              "qualifying_games": 0}]
    qbv.validate_attrition_classes(
        rows, {"no_target_season": 2, "rookie_no_priors": 1})


@pytest.mark.parametrize(
    "games_field",
    [{}, {"qualifying_games": 0}],
    ids=["absent_games", "zero_games"],
)
def test_r30_evaluable_without_qualifying_games_is_a_class_conflict(games_field):
    row = {"player_id": "00-8", "season": 2024, "outcome_class": "evaluable"}
    row.update(games_field)
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(_D2_CLASSIFIED + [row], _D2_ATTRITION)
    assert err.value.reason == "outcome_class_conflict"


def test_r30_evaluable_with_malformed_games_refuses_as_corruption():
    row = {"player_id": "00-8", "season": 2024, "outcome_class": "evaluable",
           "qualifying_games": "garbage"}
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(_D2_CLASSIFIED + [row], _D2_ATTRITION)
    assert err.value.reason == "label_row_invalid"


def test_r30_duplicate_attrition_player_season_refuses_even_with_matching_count():
    dup = {"player_id": "00-2", "season": 2024,
           "outcome_class": "no_target_season"}
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            _D2_CLASSIFIED + [dup],
            {"no_target_season": 2, "rookie_no_priors": 1})
    assert err.value.reason == "duplicate_player_season"


def test_r30_classified_row_without_identity_refuses():
    row = {"outcome_class": "no_target_season"}
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(_D2_CLASSIFIED + [row], _D2_ATTRITION)
    assert err.value.reason == "label_row_invalid"


# --- R31 (round-1 H2): weeks are 1-indexed -----------------------------------
def test_r31_week_zero_refuses_never_counts_as_a_game():
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=0, attempts=20)], _D2_SETTINGS,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "label_row_invalid"


def test_r31_week_one_and_late_weeks_remain_legal():
    out = qbv.build_label_table(
        [_wk(week=1, attempts=20), _wk(week=22, attempts=20)], _D2_SETTINGS,
        expected_settings_hash=_d2_hash())
    assert out["labels"][0]["qualifying_games"] == 2


# --- R32 (round-1 H3): the fingerprint rejects non-JSON tokens ---------------
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_r32_non_json_numeric_on_any_key_refuses_at_hash(bad):
    with pytest.raises(F) as err:
        qbv.settings_hash(dict(_D2_SETTINGS, unused=bad))
    assert err.value.reason == "settings_snapshot_invalid"


# --- R35 (round-3 B1): one freeze — hash and multipliers are the same state -
class _FlippingSettings(cabc.Mapping):
    """A LEGAL Mapping whose pass_td flips 4.0 -> 40.0 after its first read.

    Codex's round-3 probe class: without a single freeze boundary, the
    fingerprint sees 4.0 and the scorer sees 40.0.
    """

    def __init__(self):
        self._base = dict(_D2_SETTINGS)
        self._pass_td_reads = 0

    def __iter__(self):
        return iter(self._base)

    def __len__(self):
        return len(self._base)

    def __getitem__(self, key):
        if key == "pass_td":
            self._pass_td_reads += 1
            return 4.0 if self._pass_td_reads == 1 else 40.0
        return self._base[key]


def test_r35_mutating_mapping_cannot_decouple_hash_from_multipliers():
    out = qbv.build_label_table(
        [_wk(week=1, attempts=1, passing_tds=1)], _FlippingSettings(),
        expected_settings_hash=_d2_hash())
    # The returned hash fingerprints pass_td=4.0 (== the plain _D2_SETTINGS
    # hash) AND the label was scored under that same frozen state — never
    # the post-mutation 40.0.
    assert out["settings_hash"] == _d2_hash()
    assert out["labels"][0]["points_total"] == 4.0


def test_r35_scoring_edges_hash_and_scores_share_one_frozen_state():
    golden = [dict(_D2_GOLDEN[0], stats=dict(_D2_GOLDEN[0]["stats"],
                                             passing_tds=1))]
    # 300 yds (12) + ONE TD at the FROZEN pass_td=4.0 (4) − 1 INT (2) = 14;
    # the post-mutation 40.0 would score 50 and refuse.
    golden[0]["expected_points"] = 14.0
    qbv.validate_scoring_edges(
        golden + _D2_GOLDEN[1:], _FlippingSettings(), expected_hash=_d2_hash())


# --- R36 (round-3 H1): non-string keys never classify, on EVERY boundary ----
class _SpoofKey:
    """Hashable non-string key str-impersonating an allowlisted key."""

    def __str__(self):
        return "pts_allow_0"

    def __hash__(self):
        return hash("spoof")

    def __eq__(self, other):
        return isinstance(other, _SpoofKey)


@pytest.mark.parametrize("bad_key", [_SpoofKey(), True, 1, ("pts_allow_0",)],
                         ids=["spoof_str", "bool", "int", "tuple"])
def test_r36_non_string_settings_keys_refuse_on_every_boundary(bad_key):
    spoofed = dict(_D2_SETTINGS)
    spoofed[bad_key] = 6.0
    with pytest.raises(F) as err:
        qbv.settings_hash(spoofed)
    assert err.value.reason == "settings_snapshot_invalid"
    with pytest.raises(F) as err:
        qbv.score_stat_line({"passing_tds": 1}, spoofed)
    assert err.value.reason == "settings_snapshot_invalid"
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, attempts=1)], spoofed,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "settings_snapshot_invalid"


def test_r36_codex_probe_spoofed_score_stat_line_refuses():
    # The exact round-3 exported-helper probe: previously returned 4.0.
    spoofed = dict(_D2_SETTINGS)
    spoofed[_SpoofKey()] = 6.0
    with pytest.raises(F) as err:
        qbv.score_stat_line({"passing_tds": 1}, spoofed)
    assert err.value.reason == "settings_snapshot_invalid"
    assert "SpoofKey" in err.value.detail


# --- R37 (round-4 B1): frozen VALUE semantics — hash bytes are what scores --
class _SplitFloat(float):
    """JSON-encodes as its numeric 4.0; str()-converts as '40.0'.

    Codex's round-4 probe class: a shallow reference copy hashes the JSON
    side and scores the str side.
    """

    def __new__(cls):
        return super().__new__(cls, 4.0)

    def __str__(self):
        return "40.0"


def test_r37_scalar_subclass_scores_exactly_what_the_hash_fingerprints():
    split = dict(_D2_SETTINGS, pass_td=_SplitFloat())
    out = qbv.build_label_table(
        [_wk(week=1, attempts=1, passing_tds=1)], split,
        expected_settings_hash=_d2_hash())
    # The canonical bytes say pass_td=4.0; the label must be scored at 4.0
    # under that very fingerprint — never 40.0.
    assert out["settings_hash"] == _d2_hash()
    assert out["labels"][0]["points_total"] == 4.0


def test_r37_scoring_edges_reject_the_split_semantics_expectation():
    split = dict(_D2_SETTINGS, pass_td=_SplitFloat())
    plain_semantics = [{"stats": {"passing_tds": 1}, "expected_points": 4.0}]
    # Under the frozen canonical state the plain-4 expectation passes...
    qbv.validate_scoring_edges(plain_semantics + _D2_GOLDEN, split,
                               expected_hash=_d2_hash())
    # ...and the 40-side expectation (Codex's accepted-46 schedule class)
    # now refuses as a mismatch.
    split2 = dict(_D2_SETTINGS, pass_td=_SplitFloat())
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(
            [{"stats": {"passing_tds": 1}, "expected_points": 40.0}]
            + _D2_GOLDEN,
            split2, expected_hash=_d2_hash())
    assert err.value.reason == "golden_scoring_mismatch"


def test_r37_score_stat_line_uses_decoded_canonical_multipliers():
    split = dict(_D2_SETTINGS, pass_td=_SplitFloat())
    assert qbv.score_stat_line({"passing_tds": 1}, split) == Decimal("4")


# --- R38 (round-4 H1): hostile key __repr__ never escapes the named refusal -
class _HostileReprKey:
    def __repr__(self):
        raise RuntimeError("repr exploded")

    def __hash__(self):
        return 7

    def __eq__(self, other):
        return isinstance(other, _HostileReprKey)


def test_r38_hostile_key_repr_refuses_named_on_every_boundary():
    hostile = dict(_D2_SETTINGS)
    hostile[_HostileReprKey()] = 1.0
    for attempt in (
        lambda: qbv.settings_hash(hostile),
        lambda: qbv.score_stat_line({"passing_tds": 1}, hostile),
        lambda: qbv.build_label_table([_wk(week=1, attempts=1)], hostile,
                                      expected_settings_hash=_d2_hash()),
    ):
        with pytest.raises(F) as err:
            attempt()
        assert err.value.reason == "settings_snapshot_invalid"
        assert "HostileReprKey" in err.value.detail


# --- R39 (round-5 B1): the registered pin is an exact plain string ----------
class _OverriddenNePin(str):
    """A str subclass whose __ne__ answers False for a mismatched pin.

    Round-5 defensive-QA schedule: the hash gate must compare trusted
    primitive semantics only, so this pin class is rejected by type before
    any comparison runs.
    """

    def __ne__(self, other):
        return False

    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash(str(self))


def test_r39_pin_subclass_is_rejected_on_both_hash_gated_boundaries():
    bad_pin = _OverriddenNePin("definitely-not-the-registered-hash")
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, attempts=1)], _D2_SETTINGS,
                              expected_settings_hash=bad_pin)
    assert err.value.reason == "settings_hash_mismatch"
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(_D2_GOLDEN, _D2_SETTINGS,
                                   expected_hash=bad_pin)
    assert err.value.reason == "settings_hash_mismatch"


def test_r39_even_a_correct_text_pin_subclass_is_rejected_by_type():
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, attempts=1)], _D2_SETTINGS,
                              expected_settings_hash=_OverriddenNePin(_d2_hash()))
    assert err.value.reason == "settings_hash_mismatch"


@pytest.mark.parametrize(
    "malformed_pin",
    ["beef", "g" * 64, "A" * 64, "0" * 63, "0" * 65],
)
def test_r39_non_sha256_shaped_pins_refuse(malformed_pin):
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(week=1, attempts=1)], _D2_SETTINGS,
                              expected_settings_hash=malformed_pin)
    assert err.value.reason == "settings_hash_mismatch"


def test_r39_exact_correct_pin_still_passes():
    out = qbv.build_label_table([_wk(week=1, attempts=1)], _D2_SETTINGS,
                                expected_settings_hash=_d2_hash())
    assert out["settings_hash"] == _d2_hash()


# --- R40 (round-5 H1): str-subclass keys are rejected before sorting --------
class _RaisingLtKey(str):
    """A str-subclass key whose __lt__ raises; sort_keys must never run it."""

    def __lt__(self, other):
        raise RuntimeError("comparison raised")


def test_r40_str_subclass_key_refuses_named_on_every_boundary():
    keyed = {(_RaisingLtKey("pass_td") if k == "pass_td" else k): v
             for k, v in _D2_SETTINGS.items()}
    for attempt in (
        lambda: qbv.settings_hash(keyed),
        lambda: qbv.score_stat_line({"passing_tds": 1}, keyed),
        lambda: qbv.build_label_table([_wk(week=1, attempts=1)], keyed,
                                      expected_settings_hash=_d2_hash()),
        lambda: qbv.validate_scoring_edges(_D2_GOLDEN, keyed,
                                           expected_hash=_d2_hash()),
    ):
        with pytest.raises(F) as err:
            attempt()
        assert err.value.reason == "settings_snapshot_invalid"
        assert "RaisingLtKey" in err.value.detail


# --- R41 (round-5 H2 ruling): diagnostics stay total on raising __repr__ ----
class _RaisingReprValue:
    """Malformed row/stat CONTENT whose __repr__ raises — in-contract per the
    round-5 ruling; the named refusal must still be produced."""

    def __repr__(self):
        raise RuntimeError("repr raised")


def test_r41_raising_repr_stat_value_refuses_named_on_score():
    with pytest.raises(F) as err:
        qbv.score_stat_line({"passing_tds": _RaisingReprValue()}, _D2_SETTINGS)
    assert err.value.reason == "stat_value_invalid"
    assert "unrepresentable" in err.value.detail


def test_r41_raising_repr_stat_value_refuses_named_on_build():
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=1, attempts=_RaisingReprValue())], _D2_SETTINGS,
            expected_settings_hash=_d2_hash())
    assert err.value.reason == "stat_value_invalid"
    assert "unrepresentable" in err.value.detail


def test_r41_raising_repr_unknown_stat_key_refuses_named():
    class _RaisingReprKey:
        def __repr__(self):
            raise RuntimeError("repr raised")

        def __hash__(self):
            return 11

        def __eq__(self, other):
            return False

    with pytest.raises(F) as err:
        qbv.score_stat_line({_RaisingReprKey(): 1}, _D2_SETTINGS)
    assert err.value.reason == "unknown_stat_column"
    assert "unrepresentable" in err.value.detail


def test_r41_raising_repr_golden_expected_points_refuses_named():
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(
            [{"stats": {"receptions": 1},
              "expected_points": _RaisingReprValue()}] + _D2_GOLDEN,
            _D2_SETTINGS, expected_hash=_d2_hash())
    assert err.value.reason == "golden_row_invalid"
    assert "unrepresentable" in err.value.detail


def test_r41_raising_repr_label_fields_refuse_named():
    with pytest.raises(F) as err:
        qbv.validate_label_table([dict(_D2_LABEL, ppg=_RaisingReprValue())])
    assert err.value.reason == "non_finite_ppg"
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            _D2_CLASSIFIED + [{"player_id": "00-9", "season": 2024,
                               "outcome_class": "no_target_season",
                               "qualifying_games": _RaisingReprValue()}],
            {"no_target_season": 2, "rookie_no_priors": 1})
    assert err.value.reason == "label_row_invalid"


# --- R42 (round-6 B1): categorical gates compare trusted plain text ---------
class _OverriddenNeText(str):
    """A str subclass whose __ne__ answers False against any comparison —
    categorical gates must reject it at the text boundary, by type."""

    def __ne__(self, other):
        return False

    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash(str(self))


def test_r42_subclass_season_type_refuses_reg_only_law():
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=1, attempts=20, st=_OverriddenNeText("POST"))],
            _D2_SETTINGS, expected_settings_hash=_d2_hash())
    assert err.value.reason == "non_regular_season_row"


def test_r42_subclass_outcome_class_refuses_in_label_table():
    row = dict(_D2_LABEL, outcome_class=_OverriddenNeText("not_evaluable"))
    with pytest.raises(F) as err:
        qbv.validate_label_table([row])
    assert err.value.reason == "label_row_invalid"


def test_r42_subclass_outcome_class_refuses_in_attrition_table():
    row = {"player_id": "00-9", "season": 2024,
           "outcome_class": _OverriddenNeText("no_target_season")}
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            _D2_CLASSIFIED + [row],
            {"no_target_season": 2, "rookie_no_priors": 1})
    assert err.value.reason == "attrition_class_unknown"


def test_r42_exact_plain_categories_still_pass():
    out = qbv.build_label_table([_wk(week=1, attempts=1, st="REG")],
                                _D2_SETTINGS, expected_settings_hash=_d2_hash())
    assert out["labels"][0]["outcome_class"] == "evaluable"


# --- R43 (round-6 B2): integer gates run on exact plain ints ----------------
class _ComparisonOverriddenInt(int):
    """An int subclass whose ordering dunders answer False — range gates
    must never execute them."""

    def __lt__(self, other):
        return False

    def __ge__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __eq__(self, other):
        return True

    def __hash__(self):
        return hash(int(self))


class _RaisingLtInt(int):
    def __lt__(self, other):
        raise RuntimeError("comparison raised")


def test_r43_zero_week_subclass_refuses_the_week_law():
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=_ComparisonOverriddenInt(0), attempts=20)],
            _D2_SETTINGS, expected_settings_hash=_d2_hash())
    assert err.value.reason == "label_row_invalid"


def test_r43_negative_games_subclass_refuses_in_label_table():
    row = dict(_D2_LABEL, qualifying_games=_ComparisonOverriddenInt(-1))
    with pytest.raises(F) as err:
        qbv.validate_label_table([row])
    assert err.value.reason == "missing_games"


def test_r43_negative_games_subclass_refuses_in_attrition_table():
    row = {"player_id": "00-9", "season": 2024,
           "outcome_class": "no_target_season",
           "qualifying_games": _ComparisonOverriddenInt(-1)}
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            _D2_CLASSIFIED + [row],
            {"no_target_season": 2, "rookie_no_priors": 1})
    assert err.value.reason == "label_row_invalid"


def test_r43_raising_comparison_int_stat_normalizes_to_plain_semantics():
    # The underlying value (3 attempts) is legal; post-normalization the
    # subclass's raising __lt__ is never executed — the build succeeds on
    # the trusted plain conversion instead of surfacing a raw error (the
    # pre-repair behavior Codex's round-6 probe reproduced).
    out = qbv.build_label_table(
        [_wk(week=1, attempts=_RaisingLtInt(3))], _D2_SETTINGS,
        expected_settings_hash=_d2_hash())
    assert out["labels"][0]["qualifying_games"] == 1


def test_r43_plain_int_boundaries_still_pass():
    out = qbv.build_label_table([_wk(week=1, attempts=1)], _D2_SETTINGS,
                                expected_settings_hash=_d2_hash())
    assert out["labels"][0]["qualifying_games"] == 1


# --- R44 (round-6 H1): player-id text boundary rejects subclasses -----------
class _RaisingStripId(str):
    def strip(self):
        raise RuntimeError("strip raised")


def test_r44_subclass_player_id_refuses_named_on_all_three_callers():
    bad_id = _RaisingStripId("00-0000001")
    with pytest.raises(F) as err:
        qbv.build_label_table([_wk(player=bad_id, week=1, attempts=1)],
                              _D2_SETTINGS, expected_settings_hash=_d2_hash())
    assert err.value.reason == "label_row_invalid"
    with pytest.raises(F) as err:
        qbv.validate_label_table([dict(_D2_LABEL, player_id=bad_id)])
    assert err.value.reason == "label_row_invalid"
    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            [{"player_id": bad_id, "season": 2024,
              "outcome_class": "no_target_season"}],
            {"no_target_season": 1, "rookie_no_priors": 0})
    assert err.value.reason == "label_row_invalid"


# --- R45 (round-6 H2): refusal-message construction is total ----------------
class _RaisingNameMeta(type):
    @property
    def __name__(cls):
        raise RuntimeError("name raised")


class _FullyOpaqueValue(metaclass=_RaisingNameMeta):
    def __repr__(self):
        raise RuntimeError("repr raised")


def test_r45_value_with_raising_repr_and_type_name_still_refuses_named():
    with pytest.raises(F) as err:
        qbv.score_stat_line({"passing_tds": _FullyOpaqueValue()}, _D2_SETTINGS)
    assert err.value.reason == "stat_value_invalid"
    assert "unrepresentable" in err.value.detail


def test_r45_settings_key_with_raising_type_name_refuses_named():
    class _OpaqueKey(metaclass=_RaisingNameMeta):
        def __repr__(self):
            raise RuntimeError("repr raised")

        def __hash__(self):
            return 13

        def __eq__(self, other):
            return False

    keyed = dict(_D2_SETTINGS)
    keyed[_OpaqueKey()] = 1.0
    with pytest.raises(F) as err:
        qbv.settings_hash(keyed)
    assert err.value.reason == "settings_snapshot_invalid"


def test_r45_attrition_declared_class_key_renders_safely():
    class _RaisingReprClassKey:
        def __repr__(self):
            raise RuntimeError("repr raised")

        def __hash__(self):
            return 17

        def __eq__(self, other):
            return False

    with pytest.raises(F) as err:
        qbv.validate_attrition_classes(
            _D2_CLASSIFIED,
            {"no_target_season": 1, "rookie_no_priors": 1,
             _RaisingReprClassKey(): 0})
    assert err.value.reason == "attrition_count_mismatch"
    assert "unrepresentable" in err.value.detail


# --- R46 (round-6 H3): system failures propagate, never relabeled -----------
class _MemoryErrorInt:
    def __int__(self):
        raise MemoryError("simulated resource exhaustion")


class _MemoryErrorStr:
    def __str__(self):
        raise MemoryError("simulated resource exhaustion")

    def __repr__(self):
        return "_MemoryErrorStr()"


def test_r46_memory_error_from_count_conversion_propagates():
    with pytest.raises(MemoryError):
        qbv.build_label_table(
            [_wk(week=1, attempts=_MemoryErrorInt())], _D2_SETTINGS,
            expected_settings_hash=_d2_hash())


def test_r46_memory_error_from_decimal_conversion_propagates():
    with pytest.raises(MemoryError):
        qbv.score_stat_line({"passing_yards": _MemoryErrorStr()}, _D2_SETTINGS)


def test_r46_ordinary_conversion_failures_still_refuse_named():
    with pytest.raises(F) as err:
        qbv.build_label_table(
            [_wk(week=1, attempts="not-a-count")], _D2_SETTINGS,
            expected_settings_hash=_d2_hash())
    assert err.value.reason == "stat_value_invalid"


# --- R47 (round-7 H1): preservation holds through BOTH _safe_repr stages ----
@pytest.mark.parametrize("system_exc", [MemoryError, RecursionError,
                                        SystemError])
def test_r47_system_exception_in_type_name_stage_propagates(system_exc):
    class _StageTwoMeta(type):
        @property
        def __name__(cls):
            raise system_exc("simulated system failure")

    class _StageTwoValue(metaclass=_StageTwoMeta):
        def __repr__(self):
            raise RuntimeError("repr raised")  # ordinary -> stage two runs

    with pytest.raises(system_exc):
        qbv.score_stat_line({"passing_tds": _StageTwoValue()}, _D2_SETTINGS)


# --- R48 (round-7 H2): nested container subclasses refuse named at freeze ---
class _RaisingItemsDict(dict):
    def items(self):
        raise RuntimeError("items raised")

    def keys(self):
        raise RuntimeError("keys raised")


class _RaisingIterList(list):
    def __iter__(self):
        raise RuntimeError("iteration raised")


@pytest.mark.parametrize(
    "nested",
    [_RaisingItemsDict({"a": 1}), _RaisingIterList([1, 2])],
    ids=["mapping_subclass", "sequence_subclass"],
)
def test_r48_raising_nested_container_value_refuses_named(nested):
    keyed = dict(_D2_SETTINGS, extra_container=nested)
    with pytest.raises(F) as err:
        qbv.settings_hash(keyed)
    assert err.value.reason == "settings_snapshot_invalid"
    with pytest.raises(F) as err:
        qbv.score_stat_line({"passing_tds": 1}, keyed)
    assert err.value.reason == "settings_snapshot_invalid"


def test_r48_memory_error_from_nested_container_propagates():
    class _MemoryErrorIterList(list):
        def __iter__(self):
            raise MemoryError("simulated resource exhaustion")

    keyed = dict(_D2_SETTINGS, extra_container=_MemoryErrorIterList([1]))
    with pytest.raises(MemoryError):
        qbv.settings_hash(keyed)


# --- R49 (round-7 H3): the validator returns only normalized primitives ----
def test_r49_returned_rows_carry_exact_plain_scalars():
    subclass_row = dict(_D2_LABEL,
                        qualifying_games=_ComparisonOverriddenInt(10))
    (returned,) = qbv.validate_label_table([subclass_row])
    assert type(returned["qualifying_games"]) is int
    assert returned["qualifying_games"] == 10
    assert type(returned["player_id"]) is str
    assert type(returned["season"]) is int
    assert type(returned["ppg"]) is float
    # Trusted semantics on the validated result: this comparison must run
    # plain-int ordering, not the subclass's overridden method.
    assert returned["qualifying_games"] >= 1


def test_r49_fields_outside_the_projection_do_not_survive():
    row = dict(_D2_LABEL, stray_field="anything")
    (returned,) = qbv.validate_label_table([row])
    assert "stray_field" not in returned
    assert set(returned) == {"player_id", "season", "outcome_class",
                             "qualifying_games", "ppg", "points_total"}


def test_r49_plain_projection_round_trips_the_canonical_fixture():
    assert qbv.validate_label_table([_D2_LABEL]) == [_D2_LABEL]


# --- R50 (round-8 B1): the projected primitive is validated, not only the ---
# --- pre-projection Decimal ------------------------------------------------
def test_r50_finite_decimal_beyond_float_range_refuses_on_ppg():
    row = dict(_D2_LABEL, ppg=Decimal("1e10000"))
    with pytest.raises(F) as err:
        qbv.validate_label_table([row])
    assert err.value.reason == "non_finite_ppg"


def test_r50_finite_decimal_beyond_float_range_refuses_on_points_total():
    row = dict(_D2_LABEL, points_total=Decimal("1e10000"))
    with pytest.raises(F) as err:
        qbv.validate_label_table([row])
    assert err.value.reason == "non_finite_ppg"


def test_r50_string_magnitude_beyond_float_range_refuses_too():
    row = dict(_D2_LABEL, ppg="1e10000")
    with pytest.raises(F) as err:
        qbv.validate_label_table([row])
    assert err.value.reason == "non_finite_ppg"


def test_r50_build_aggregate_beyond_float_range_refuses_named():
    huge = _wk(week=1, attempts=1, passing_yards=Decimal("1e10000"))
    with pytest.raises(F) as err:
        qbv.build_label_table([huge], _D2_SETTINGS,
                              expected_settings_hash=_d2_hash())
    assert err.value.reason == "non_finite_ppg"


def test_r50_normal_magnitudes_still_project_finitely():
    (returned,) = qbv.validate_label_table([_D2_LABEL])
    assert returned["ppg"] == 20.0 and returned["points_total"] == 200.0


# --- R51 (round-9 B1): scoring is independent of ambient Decimal context ----
def test_r51_score_stat_line_ignores_ambient_precision():
    line = {"passing_yards": 267}  # 267 x 0.04 = 10.68 exactly
    with decimal.localcontext(decimal.Context(prec=2)):
        assert qbv.score_stat_line(line, _D2_SETTINGS) == Decimal("10.68")
    assert qbv.score_stat_line(line, _D2_SETTINGS) == Decimal("10.68")


def test_r51_build_ignores_ambient_precision_and_keeps_the_hash():
    rows = [_wk(week=1, attempts=10, passing_yards=267)]
    with decimal.localcontext(decimal.Context(prec=2)):
        out = qbv.build_label_table(rows, _D2_SETTINGS,
                                    expected_settings_hash=_d2_hash())
    assert out["labels"][0]["ppg"] == 10.68
    assert out["labels"][0]["points_total"] == 10.68
    assert out["settings_hash"] == _d2_hash()


def test_r51_multi_week_aggregation_ignores_ambient_precision():
    rows = [_wk(week=1, attempts=10, passing_yards=267),
            _wk(week=2, attempts=10, passing_yards=133)]  # 10.68 + 5.32 = 16
    with decimal.localcontext(decimal.Context(prec=2)):
        out = qbv.build_label_table(rows, _D2_SETTINGS,
                                    expected_settings_hash=_d2_hash())
    assert out["labels"][0]["points_total"] == 16.0
    assert out["labels"][0]["ppg"] == 8.0


# --- R52 (round-9 B2): arithmetic failures refuse named under BOTH trap ----
# --- configurations ----------------------------------------------------------
_EXTREME_FINITE = Decimal("9e999999")


@pytest.mark.parametrize(
    "ambient",
    [decimal.Context(), decimal.Context(traps={t: False for t in
                                               decimal.Context().traps})],
    ids=["default_traps", "all_traps_disabled"],
)
def test_r52_extreme_finite_operand_refuses_named_on_score(ambient):
    with decimal.localcontext(ambient):
        with pytest.raises(F) as err:
            qbv.score_stat_line({"passing_yards": _EXTREME_FINITE},
                                _D2_SETTINGS)
    assert err.value.reason == "stat_value_invalid"


@pytest.mark.parametrize(
    "ambient",
    [decimal.Context(), decimal.Context(traps={t: False for t in
                                               decimal.Context().traps})],
    ids=["default_traps", "all_traps_disabled"],
)
def test_r52_extreme_finite_operand_refuses_named_on_build(ambient):
    with decimal.localcontext(ambient):
        with pytest.raises(F) as err:
            qbv.build_label_table(
                [_wk(week=1, attempts=1, passing_yards=_EXTREME_FINITE)],
                _D2_SETTINGS, expected_settings_hash=_d2_hash())
    assert err.value.reason == "stat_value_invalid"


def test_r52_extreme_finite_operand_refuses_named_on_edges():
    golden = [{"stats": {"passing_yards": _EXTREME_FINITE},
               "expected_points": 0.0}] + _D2_GOLDEN
    with pytest.raises(F) as err:
        qbv.validate_scoring_edges(golden, _D2_SETTINGS,
                                   expected_hash=_d2_hash())
    assert err.value.reason == "stat_value_invalid"


# --- R53 (round-10 B1): the qualifying predicate is arithmetic-free ---------
_CONSTRAINED_AMBIENT = decimal.Context(prec=2, Emin=-1, Emax=0)


def test_r53_ordinary_counts_build_under_constrained_ambient_exponents():
    # Codex's round-10 schedule: attempts=10 under Emax=0 ambient raised raw
    # decimal.Overflow from the predicate's ambient addition. The
    # comparison-only predicate must build identically to the default
    # context.
    rows = [_wk(week=1, attempts=10, passing_yards=267)]
    with decimal.localcontext(_CONSTRAINED_AMBIENT):
        out = qbv.build_label_table(rows, _D2_SETTINGS,
                                    expected_settings_hash=_d2_hash())
    assert out["labels"][0]["qualifying_games"] == 1
    assert out["labels"][0]["ppg"] == 10.68


@pytest.mark.parametrize(
    "stats,expected_games",
    [({"sacks_suffered": 1}, 1), ({"carries": 1}, 1), ({"attempts": 1}, 1),
     ({}, 0)],
    ids=["sacks_only", "carries_only", "attempts_only", "all_zero"],
)
def test_r53_predicate_boundaries_hold_under_constrained_ambient(
    stats, expected_games
):
    with decimal.localcontext(_CONSTRAINED_AMBIENT):
        out = qbv.build_label_table([_wk(week=1, **stats)], _D2_SETTINGS,
                                    expected_settings_hash=_d2_hash())
    if expected_games:
        assert out["labels"][0]["qualifying_games"] == expected_games
    else:
        assert out["labels"] == []
        assert out["zero_qualifying_player_seasons"] == [
            {"player_id": "00-0000001", "season": 2024}]
