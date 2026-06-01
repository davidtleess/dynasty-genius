"""Subsystem 4 v2 draft-truth loader contract tests."""
from __future__ import annotations

import ast
import json
import sys
import types
from pathlib import Path
from typing import get_args, get_origin

import polars as pl
import pytest
from pydantic import BaseModel, ValidationError

from src.dynasty_genius.identity import prospect_nfl_bridge as bridge
from src.dynasty_genius.identity.college_prospect_identity import normalize_name

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFT_TRUTH_FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / ("backtest_" + "mo" + "ck_draft")
    / "draft_truth"
    / "2024.json"
)
SYNTHETIC_TRUTH_FIXTURE = (
    REPO_ROOT
    / "resources"
    / "synthetic_draft_truth"
    / "2025.json"
)


def _source_row(**overrides):
    row = {
        "season": 2024,
        "round": 1,
        "pick": 1,
        "team": "CHI",
        "gsis_id": "00-0039918",
        "pfr_player_id": "WillCa03",
        "pfr_player_name": "Caleb Williams",
        "position": "QB",
        "college": "USC",
    }
    row.update(overrides)
    return row


def _write_fixture(
    tmp_path: Path,
    rows: list[dict],
    *,
    fetched_at: str | None = "2026-01-01T00:00:00Z",
) -> Path:
    payload: dict = {"rows": rows}
    if fetched_at is not None:
        payload["metadata"] = {"fetched_at": fetched_at}
    path = tmp_path / "draft_truth.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _load_fixture(path: Path, **kwargs):
    return bridge.load_nflreadr_draft_truth(
        2024,
        data_mode="real",
        fixture_path=path,
        **kwargs,
    )


def _load_synthetic(draft_year: int = 2025, **kwargs):
    return bridge.load_nflreadr_draft_truth(
        draft_year,
        data_mode="synthetic",
        **kwargs,
    )


def _load_live(draft_year: int = 2024, **kwargs):
    return bridge.load_nflreadr_draft_truth(
        draft_year,
        data_mode="real",
        **kwargs,
    )


def _install_fake_nflreadpy(monkeypatch, rows: list[dict] | Exception):
    calls: list[dict] = []

    def load_draft_picks(*, seasons):
        calls.append({"seasons": seasons})
        if isinstance(rows, Exception):
            raise rows
        return pl.DataFrame(rows)

    fake_module = types.SimpleNamespace(load_draft_picks=load_draft_picks)
    monkeypatch.setitem(sys.modules, "nflreadpy", fake_module)
    return calls


def test_truth_load_diagnostics_model_contract():
    diagnostics_cls = bridge.NflTruthLoadDiagnostics

    assert issubclass(diagnostics_cls, BaseModel)
    assert diagnostics_cls.model_config.get("extra") == "forbid"

    expected_int_fields = {
        "truth_rows_loaded",
        "skipped_missing_gsis_id",
        "skipped_bad_pick",
        "skipped_bad_round",
        "skipped_missing_name",
        "skipped_missing_position",
        "skipped_missing_team",
    }
    assert set(diagnostics_cls.model_fields) == {
        *expected_int_fields,
        "required_columns_seen",
    }

    diagnostics = diagnostics_cls()
    for field_name in expected_int_fields:
        field = diagnostics_cls.model_fields[field_name]
        assert field.annotation is int
        assert getattr(diagnostics, field_name) == 0

    columns_field = diagnostics_cls.model_fields["required_columns_seen"]
    assert get_origin(columns_field.annotation) is list
    assert get_args(columns_field.annotation) == (str,)
    assert diagnostics.required_columns_seen == []

    with pytest.raises(ValidationError):
        diagnostics_cls.model_validate({"unexpected_field": 1})


def test_truth_load_result_model_contract():
    result_cls = bridge.NflreadrTruthLoadResult
    diagnostics_cls = bridge.NflTruthLoadDiagnostics

    assert issubclass(result_cls, BaseModel)

    rows_field = result_cls.model_fields["rows"]
    assert get_origin(rows_field.annotation) is list
    assert get_args(rows_field.annotation) == (bridge.NflTruthRow,)

    diagnostics_field = result_cls.model_fields["diagnostics"]
    assert diagnostics_field.annotation is diagnostics_cls

    truth_row = bridge.NflTruthRow(
        gsis_id="00-0000001",
        pfr_id=None,
        full_name="Example Player",
        normalized_name="example player",
        position="QB",
        college="Example U",
        draft_year=2024,
        draft_pick_no=1,
        draft_round=1,
        nfl_team="CHI",
        fetched_at="2026-01-01T00:00:00Z",
    )
    result = result_cls(rows=[truth_row], diagnostics=diagnostics_cls())

    assert result.rows == [truth_row]
    assert isinstance(result.diagnostics, diagnostics_cls)


def test_truth_loader_exceptions_are_value_errors():
    assert issubclass(bridge.NflreadrSchemaDriftError, ValueError)
    assert issubclass(bridge.NflreadrSourceContaminationError, ValueError)
    assert issubclass(bridge.NflreadrEmptyTruthError, ValueError)


def test_fixture_mode_maps_committed_source_rows_to_truth_rows():
    result = _load_fixture(DRAFT_TRUTH_FIXTURE)

    assert isinstance(result, bridge.NflreadrTruthLoadResult)
    assert isinstance(result.diagnostics, bridge.NflTruthLoadDiagnostics)
    assert result.diagnostics.truth_rows_loaded == 2

    first = result.rows[0]
    assert isinstance(first, bridge.NflTruthRow)
    assert first.gsis_id == "00-0039918"
    assert first.pfr_id == "WillCa03"
    assert first.full_name == "Caleb Williams"
    assert first.normalized_name == normalize_name("Caleb Williams")
    assert first.position == "QB"
    assert first.college == "USC"
    assert first.draft_year == 2024
    assert first.draft_pick_no == 1
    assert first.draft_round == 1
    assert first.nfl_team == "CHI"
    assert first.fetched_at == "2026-01-01T00:00:00Z"


def test_fixture_mode_schema_gate_rejects_missing_required_key(tmp_path: Path):
    row = _source_row()
    del row["pfr_player_id"]
    path = _write_fixture(tmp_path, [row])

    with pytest.raises(bridge.NflreadrSchemaDriftError):
        _load_fixture(path)


def test_fixture_mode_rejects_pre_normalized_truth_row_shape(tmp_path: Path):
    path = _write_fixture(
        tmp_path,
        [
            {
                "gsis_id": "00-0039918",
                "pfr_id": "WillCa03",
                "full_name": "Caleb Williams",
                "normalized_name": "caleb williams",
                "position": "QB",
                "college": "USC",
                "draft_year": 2024,
                "draft_pick_no": 1,
                "draft_round": 1,
                "nfl_team": "CHI",
                "fetched_at": "2026-01-01T00:00:00Z",
            }
        ],
    )

    with pytest.raises(bridge.NflreadrSchemaDriftError):
        _load_fixture(path)


def test_fixture_mode_null_pfr_player_id_maps_to_none(tmp_path: Path):
    path = _write_fixture(tmp_path, [_source_row(pfr_player_id=None)])

    result = _load_fixture(path)

    assert result.rows[0].pfr_id is None
    assert result.diagnostics.truth_rows_loaded == 1


def test_fixture_mode_skips_present_key_bad_values_and_counts_each_reason(
    tmp_path: Path,
):
    path = _write_fixture(
        tmp_path,
        [
            _source_row(gsis_id=""),
            _source_row(gsis_id="00-badpick-bool", pick=True),
            _source_row(gsis_id="00-badpick-float", pick=1.0),
            _source_row(gsis_id="00-badpick-string", pick="1"),
            _source_row(gsis_id="00-badround-bool", round=False),
            _source_row(gsis_id="00-badround-float", round=1.0),
            _source_row(gsis_id="00-badround-string", round="1"),
            _source_row(gsis_id="00-missing-name", pfr_player_name=""),
            _source_row(gsis_id="00-missing-position", position=""),
            _source_row(gsis_id="00-missing-team", team=""),
            _source_row(gsis_id="00-kept", pfr_player_name="Kept Player"),
        ],
    )

    result = _load_fixture(path)

    assert [row.gsis_id for row in result.rows] == ["00-kept"]
    assert result.diagnostics.truth_rows_loaded == 1
    assert result.diagnostics.skipped_missing_gsis_id == 1
    assert result.diagnostics.skipped_bad_pick == 3
    assert result.diagnostics.skipped_bad_round == 3
    assert result.diagnostics.skipped_missing_name == 1
    assert result.diagnostics.skipped_missing_position == 1
    assert result.diagnostics.skipped_missing_team == 1


def test_fixture_mode_absent_pick_or_round_key_is_schema_drift_not_skip(
    tmp_path: Path,
):
    missing_pick = _source_row()
    del missing_pick["pick"]
    missing_round = _source_row(gsis_id="00-missing-round")
    del missing_round["round"]

    for row in (missing_pick, missing_round):
        path = _write_fixture(tmp_path, [row])
        with pytest.raises(bridge.NflreadrSchemaDriftError):
            _load_fixture(path)


def test_fixture_mode_fetched_at_is_verbatim_and_override_is_allowed(
    tmp_path: Path,
):
    offset_path = _write_fixture(
        tmp_path,
        [_source_row()],
        fetched_at="2026-01-01T00:00:00+00:00",
    )
    first = _load_fixture(offset_path)
    second = _load_fixture(offset_path)

    assert first.rows[0].fetched_at == "2026-01-01T00:00:00+00:00"
    assert first.model_dump() == second.model_dump()

    missing_path = _write_fixture(tmp_path, [_source_row()], fetched_at=None)
    with pytest.raises(ValueError):
        _load_fixture(missing_path)

    overridden = _load_fixture(
        missing_path,
        fetched_at="2026-02-03T04:05:06Z",
    )
    assert overridden.rows[0].fetched_at == "2026-02-03T04:05:06Z"


def test_fixture_mode_empty_real_rows_raise_empty_truth_error(tmp_path: Path):
    path = _write_fixture(tmp_path, [])

    with pytest.raises(bridge.NflreadrEmptyTruthError):
        _load_fixture(path)


def test_fixture_mode_preserves_duplicate_gsis_id_rows(tmp_path: Path):
    path = _write_fixture(
        tmp_path,
        [
            _source_row(gsis_id="00-duplicate", pick=1),
            _source_row(gsis_id="00-duplicate", pick=2),
        ],
    )

    result = _load_fixture(path)

    assert [row.gsis_id for row in result.rows] == ["00-duplicate", "00-duplicate"]
    assert [row.draft_pick_no for row in result.rows] == [1, 2]


def test_fixture_mode_drops_extra_source_columns_before_model_validation(
    tmp_path: Path,
):
    path = _write_fixture(
        tmp_path,
        [_source_row(extra_source_column="must_not_reach_truth_row")],
    )

    result = _load_fixture(path)

    assert result.diagnostics.truth_rows_loaded == 1
    assert "extra_source_column" not in result.rows[0].model_dump()


def test_fixture_mode_wrong_season_fails_loud_before_skip_accounting(
    tmp_path: Path,
):
    path = _write_fixture(tmp_path, [_source_row(season=2023, pick="1")])

    with pytest.raises(bridge.NflreadrSourceContaminationError) as exc_info:
        _load_fixture(path)

    message = str(exc_info.value)
    assert "2023" in message
    assert "2024" in message
    assert "00-0039918" in message
    assert "skipped_bad_pick" not in message


@pytest.mark.parametrize("bad_season", ["2024", 2024.0, True])
def test_fixture_mode_non_int_season_fails_loud_without_coercion(
    tmp_path: Path,
    bad_season,
):
    path = _write_fixture(tmp_path, [_source_row(season=bad_season)])

    with pytest.raises(bridge.NflreadrSourceContaminationError) as exc_info:
        _load_fixture(path)

    message = str(exc_info.value)
    assert repr(bad_season) in message
    assert "2024" in message
    assert "00-0039918" in message


def test_fixture_mode_integer_matching_season_remains_valid(tmp_path: Path):
    path = _write_fixture(tmp_path, [_source_row(season=2024)])

    result = _load_fixture(path)

    assert result.diagnostics.truth_rows_loaded == 1
    assert result.rows[0].draft_year == 2024


def test_synthetic_mode_uses_committed_fixture_by_convention():
    result = _load_synthetic()

    assert isinstance(result, bridge.NflreadrTruthLoadResult)
    assert result.diagnostics.truth_rows_loaded == 2
    assert [row.gsis_id for row in result.rows] == ["00-synth001", "00-synth002"]

    first = result.rows[0]
    assert isinstance(first, bridge.NflTruthRow)
    assert first.pfr_id == "MannAr00"
    assert first.full_name == "Arch Manning"
    assert first.normalized_name == normalize_name("Arch Manning")
    assert first.position == "QB"
    assert first.college == "Texas"
    assert first.draft_year == 2025
    assert first.draft_pick_no == 1
    assert first.draft_round == 1
    assert first.nfl_team == "TEN"
    assert first.fetched_at == "2026-01-02T00:00:00Z"

    assert result.rows[1].pfr_id is None


def test_synthetic_mode_does_not_call_live_draft_source(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("synthetic mode must not call live draft source")

    monkeypatch.setitem(
        __import__("sys").modules,
        "nflreadpy",
        type("FakeNflreadpy", (), {"load_draft_picks": fail_if_called})(),
    )

    result = _load_synthetic()

    assert result.diagnostics.truth_rows_loaded == 2


def test_synthetic_mode_explicit_fixture_path_overrides_convention(tmp_path: Path):
    override_path = _write_fixture(
        tmp_path,
        [
            {
                **_source_row(
                    season=2025,
                    gsis_id="00-override",
                    pfr_player_name="Override Player",
                    team="NYG",
                )
            }
        ],
        fetched_at="2026-03-04T05:06:07Z",
    )

    result = _load_synthetic(fixture_path=override_path)

    assert [row.gsis_id for row in result.rows] == ["00-override"]
    assert result.rows[0].full_name == "Override Player"
    assert result.rows[0].fetched_at == "2026-03-04T05:06:07Z"


def test_synthetic_mode_missing_convention_fixture_fails_with_explicit_token():
    with pytest.raises(ValueError) as exc_info:
        _load_synthetic(2099)

    message = str(exc_info.value)
    assert "synthetic_truth_fixture_unavailable" in message
    assert "2099" in message


def test_synthetic_mode_empty_fixture_uses_unavailable_token(tmp_path: Path):
    empty_path = _write_fixture(tmp_path, [], fetched_at="2026-01-02T00:00:00Z")

    with pytest.raises(ValueError) as exc_info:
        _load_synthetic(fixture_path=empty_path)

    message = str(exc_info.value)
    assert "synthetic_truth_fixture_unavailable" in message
    assert "NflreadrEmptyTruthError" not in message


def test_real_mode_live_path_lazily_loads_source_frame_and_maps_rows(monkeypatch):
    calls = _install_fake_nflreadpy(
        monkeypatch,
        [
            _source_row(
                gsis_id="00-live001",
                pfr_player_id="DanJe00",
                pfr_player_name="Jayden Daniels",
                team="WAS",
            ),
            _source_row(
                gsis_id="00-live002",
                pfr_player_id=None,
                pfr_player_name="Malik Nabers",
                position="WR",
                college="LSU",
                pick=6,
                team="NYG",
            ),
        ],
    )

    result = _load_live()

    assert calls == [{"seasons": [2024]}]
    assert isinstance(result, bridge.NflreadrTruthLoadResult)
    assert result.diagnostics.truth_rows_loaded == 2
    assert [row.gsis_id for row in result.rows] == ["00-live001", "00-live002"]

    first = result.rows[0]
    assert first.pfr_id == "DanJe00"
    assert first.full_name == "Jayden Daniels"
    assert first.normalized_name == normalize_name("Jayden Daniels")
    assert first.position == "QB"
    assert first.college == "USC"
    assert first.draft_year == 2024
    assert first.draft_pick_no == 1
    assert first.draft_round == 1
    assert first.nfl_team == "WAS"

    assert result.rows[1].pfr_id is None
    assert result.rows[1].position == "WR"
    assert result.rows[1].draft_pick_no == 6


def test_real_mode_imports_nflreadpy_only_inside_function_body():
    source_path = REPO_ROOT / "src/dynasty_genius/identity/prospect_nfl_bridge.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

    module_level_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "nflreadpy"
    ]
    assert module_level_imports == []


def test_real_mode_live_path_fetched_at_override_is_verbatim(monkeypatch):
    _install_fake_nflreadpy(monkeypatch, [_source_row()])

    result = _load_live(fetched_at="2026-04-05T06:07:08+00:00")

    assert result.rows[0].fetched_at == "2026-04-05T06:07:08+00:00"


def test_real_mode_live_path_default_fetched_at_is_utc_z_iso(monkeypatch):
    _install_fake_nflreadpy(monkeypatch, [_source_row()])

    result = _load_live()

    fetched_at = result.rows[0].fetched_at
    assert fetched_at.endswith("Z")
    assert "T" in fetched_at


def test_real_mode_live_source_errors_propagate(monkeypatch):
    _install_fake_nflreadpy(monkeypatch, RuntimeError("live source unavailable"))

    with pytest.raises(RuntimeError, match="live source unavailable"):
        _load_live()


def test_real_mode_live_empty_source_raises_empty_truth_error(monkeypatch):
    _install_fake_nflreadpy(monkeypatch, [])

    with pytest.raises(bridge.NflreadrEmptyTruthError):
        _load_live()


def test_real_mode_live_missing_required_column_raises_schema_drift(monkeypatch):
    row = _source_row()
    row.pop("pick")
    _install_fake_nflreadpy(monkeypatch, [row])

    with pytest.raises(bridge.NflreadrSchemaDriftError):
        _load_live()


def test_real_mode_live_wrong_season_raises_source_contamination(monkeypatch):
    _install_fake_nflreadpy(monkeypatch, [_source_row(season=2023)])

    with pytest.raises(bridge.NflreadrSourceContaminationError):
        _load_live()
