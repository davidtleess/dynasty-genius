"""DG-128 (2026-09-02): the batch pins the band's sigma runs on every PVO, and refuses to
band against runs the served models did not come from.

The band's half-widths are module constants derived from two model runs. Carrying the pin on
every PVO makes a stale pin visible in the artifact rather than silent in a constant; asking
the tree before scoring makes a moved manifest a halt, not a quiet lie.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.dynasty_genius.models.dvs_band import ENGINE_A_SIGMA_RUN, ENGINE_B_SIGMA_RUN

_WILSON = "00-0037740"
_ALLEN = "00-0039823"


def _producer():
    return importlib.import_module("scripts.build_universe_pvo_batch")


def _configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Any, list[dict]]:
    """Route the producer's inputs to fixtures and capture every assemble_pvo call."""
    producer = _producer()
    entries = {
        gsis: {"gsis_id": gsis, "sleeper_id": sleeper, "name": name, "position": "WR"}
        for gsis, sleeper, name in ((_WILSON, "8146", "Garrett Wilson"), (_ALLEN, "11584", "Braelon Allen"))
    }
    feature_rows = {
        _WILSON: {"player_id": _WILSON, "position": "WR", "age": 26.0, "games_t": 7.0},
        _ALLEN: {"player_id": _ALLEN, "position": "WR", "age": 22.0, "games_t": 4.0},
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
    monkeypatch.setattr(producer, "assert_band_sigma_runs_match_served_models", lambda: None)

    calls: list[dict] = []

    def fake_assemble(identity, **kwargs):
        calls.append({"identity": identity, **kwargs})
        payload = {"gsis_id": identity.dg_id, "position": "WR", "dynasty_value_score": 50.0}
        return SimpleNamespace(model_dump=lambda: payload)

    monkeypatch.setattr(producer, "assemble_pvo", fake_assemble)
    return producer, calls


def test_every_pvo_records_the_runs_its_band_widths_came_from(monkeypatch, tmp_path) -> None:
    producer, calls = _configure(monkeypatch, tmp_path)
    producer._active_pvos_from_engine_b()

    assert len(calls) == 2
    for call in calls:
        versions = call["source_versions"]
        assert versions["dvs_band_sigma_run_b"] == ENGINE_B_SIGMA_RUN
        assert versions["dvs_band_sigma_run_a"] == ENGINE_A_SIGMA_RUN



def test_the_refresh_refuses_to_band_against_runs_the_served_models_did_not_come_from(
    monkeypatch, tmp_path
) -> None:
    # The pin recorded on each PVO is only honest if it was checked against what the
    # tree actually serves. The refresh must ask before it scores, and stop if told no.
    producer, calls = _configure(monkeypatch, tmp_path)

    def refuse() -> None:
        raise ValueError("dvs_band_sigma_run_stale:RB:20260915T090000Z")

    monkeypatch.setattr(producer, "assert_band_sigma_runs_match_served_models", refuse)
    with pytest.raises(ValueError, match=r"^dvs_band_sigma_run_stale:RB:"):
        producer._active_pvos_from_engine_b()
    assert calls == []
