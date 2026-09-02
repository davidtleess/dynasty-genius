"""DG-128 (2026-09-01): the batch hands each veteran his draft capital before assembly.

Three things must be true for a gated player's blank to fill; this file pins the first —
that pick, round and draft-season age REACH the assembler. The other two (the blend's B
component pays the hurdle; the assembler reads `age_at_nfl_entry`) are pinned in
test_phase15_blend.py and test_dg128_engine_a_reads_draft_age.py.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.dynasty_genius.draft_capital import (
    DraftCapitalError,
    build_snapshot,
    write_snapshot,
)
from src.dynasty_genius.models.dvs_band import ENGINE_A_SIGMA_RUN, ENGINE_B_SIGMA_RUN

_WILSON = "00-0037740"  # drafted: 2022 R1 P10, age 22
_UNDRAFTED = "00-0099999"  # no draft row


def _producer():
    return importlib.import_module("scripts.build_universe_pvo_batch")


def _snapshot(tmp_path: Path) -> Path:
    path = tmp_path / "resources" / "draft_capital" / "nflverse_draft_picks.json"
    write_snapshot(
        build_snapshot(
            [{"gsis_id": _WILSON, "season": 2022, "round": 1, "pick": 10, "age": 22, "position": "WR"}],
            seasons=(2000, 2026),
            pulled_at="2026-09-01T00:00:00+00:00",
            source="test",
        ),
        path,
    )
    return path


def _configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, snapshot: Path | None) -> tuple[Any, list[dict]]:
    """Route the producer's inputs to fixtures and capture every assemble_pvo call."""
    producer = _producer()
    entries = {
        gsis: {"gsis_id": gsis, "sleeper_id": sleeper, "name": name, "position": "WR"}
        for gsis, sleeper, name in ((_WILSON, "8146", "Garrett Wilson"), (_UNDRAFTED, "9999", "Nobody Drafted"))
    }
    feature_rows = {
        _WILSON: {"player_id": _WILSON, "position": "WR", "age": 26.0, "games_t": 7.0},
        _UNDRAFTED: {"player_id": _UNDRAFTED, "position": "WR", "age": 24.0, "games_t": 5.0},
    }
    predictions = [{"player_id": gsis, "position": "WR", "prediction": 10.0} for gsis in entries]
    source = SimpleNamespace(
        path=tmp_path / "features.csv",
        metadata=lambda: {
            "feature_csv_path": "features.csv",
            "feature_source_kind": "test",
            "feature_csv_sha256": "test-feature-sha",
        },
    )
    monkeypatch.setattr(producer, "ROOT", tmp_path)
    monkeypatch.setattr(producer, "FF_PLAYERIDS_PATH", tmp_path / "crosswalk.json")
    monkeypatch.setattr(producer, "_load_ff_playerids", lambda path=None: (entries, {}))
    monkeypatch.setattr(producer, "resolve_feature_source", lambda **_kwargs: source)
    monkeypatch.setattr(producer, "_load_engine_b_feature_rows", lambda _path: feature_rows)
    monkeypatch.setattr(producer, "score_inference_partition", lambda **_kwargs: predictions)
    monkeypatch.setattr(producer, "PlayerIdentity", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(producer, "compute_dvs_pct_batch", lambda _objects: None)
    # The served-run pin check reads real model pointers; a test that wants it stubs it
    # back in.
    monkeypatch.setattr(
        producer, "assert_band_sigma_runs_match_served_models", lambda: None
    )
    monkeypatch.setattr(
        producer,
        "DRAFT_CAPITAL_PATH",
        snapshot if snapshot is not None else tmp_path / "absent" / "nflverse_draft_picks.json",
    )

    calls: list[dict] = []

    def fake_assemble(identity, **kwargs):
        calls.append({"identity": identity, **kwargs})
        payload = {"gsis_id": identity.dg_id, "position": "WR", "dynasty_value_score": 50.0}
        return SimpleNamespace(model_dump=lambda: payload)

    monkeypatch.setattr(producer, "assemble_pvo", fake_assemble)
    return producer, calls


def _call_for(calls: list[dict], gsis: str) -> dict:
    return next(call for call in calls if call["identity"].dg_id == gsis)


def test_a_drafted_veteran_reaches_the_assembler_with_his_draft_capital(monkeypatch, tmp_path) -> None:
    producer, calls = _configure(monkeypatch, tmp_path, snapshot=_snapshot(tmp_path))
    producer._active_pvos_from_engine_b()

    features = _call_for(calls, _WILSON)["features"]
    assert (features["pick"], features["round"], features["age_at_nfl_entry"]) == (10.0, 1.0, 22.0)
    # His CURRENT age is untouched — the two ages live under two keys.
    assert features["age"] == 26.0


def test_an_undrafted_veteran_gets_no_draft_capital_keys(monkeypatch, tmp_path) -> None:
    producer, calls = _configure(monkeypatch, tmp_path, snapshot=_snapshot(tmp_path))
    producer._active_pvos_from_engine_b()

    features = _call_for(calls, _UNDRAFTED)["features"]
    assert not {"pick", "round", "age_at_nfl_entry"} & set(features)
    assert features["age"] == 24.0


def test_every_pvo_records_the_snapshot_it_was_built_from(monkeypatch, tmp_path) -> None:
    snapshot = _snapshot(tmp_path)
    producer, calls = _configure(monkeypatch, tmp_path, snapshot=snapshot)
    producer._active_pvos_from_engine_b()

    for call in calls:
        versions = call["source_versions"]
        assert versions["draft_capital"] == "resources/draft_capital/nflverse_draft_picks.json"
        assert len(versions["draft_capital_sha256"]) == 64


def test_the_coverage_report_counts_who_was_handed_draft_capital(monkeypatch, tmp_path) -> None:
    producer, _calls = _configure(monkeypatch, tmp_path, snapshot=_snapshot(tmp_path))
    batch = producer._active_pvos_from_engine_b()

    accounting = batch.join_accounting["draft_capital"]
    assert accounting["matched_count"] == 1
    assert accounting["unmatched_count"] == 1
    assert accounting["age_missing_count"] == 0
    assert accounting["indexed_players"] == 1


def test_a_missing_snapshot_aborts_the_refresh_with_a_bare_token(monkeypatch, tmp_path) -> None:
    producer, _calls = _configure(monkeypatch, tmp_path, snapshot=None)
    with pytest.raises(DraftCapitalError, match=r"^draft_capital_snapshot_missing$"):
        producer._active_pvos_from_engine_b()


def test_every_pvo_records_the_runs_its_band_widths_came_from(monkeypatch, tmp_path) -> None:
    # The band's half-widths are pinned to two model runs. A retrain that moves a
    # manifest must move the pin; carrying the pin on every PVO makes a stale pin
    # visible in the artifact rather than silent in a module constant.
    producer, calls = _configure(monkeypatch, tmp_path, snapshot=_snapshot(tmp_path))
    producer._active_pvos_from_engine_b()

    for call in calls:
        versions = call["source_versions"]
        assert versions["dvs_band_sigma_run_b"] == ENGINE_B_SIGMA_RUN
        assert versions["dvs_band_sigma_run_a"] == ENGINE_A_SIGMA_RUN


def test_the_refresh_refuses_to_band_against_runs_the_served_models_did_not_come_from(
    monkeypatch, tmp_path
) -> None:
    # The pin recorded on each PVO is only honest if it was checked against what the
    # tree actually serves. The refresh must ask before it scores, and stop if told no.
    producer, calls = _configure(monkeypatch, tmp_path, snapshot=_snapshot(tmp_path))

    def refuse() -> None:
        raise ValueError("dvs_band_sigma_run_stale:RB:20260915T090000Z")

    monkeypatch.setattr(producer, "assert_band_sigma_runs_match_served_models", refuse)
    with pytest.raises(ValueError, match=r"^dvs_band_sigma_run_stale:RB:"):
        producer._active_pvos_from_engine_b()
    assert calls == []
