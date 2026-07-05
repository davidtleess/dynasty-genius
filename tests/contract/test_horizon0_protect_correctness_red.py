"""Horizon 0 protect/correctness RED contracts.

These tests cover 0b/0c from the 2026-07-04 remediation board. They use temp
fixtures and dependency injection only; no committed test may depend on local
gitignored ``app/data`` artifacts.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import pytest

import app.api.routes.players as players_route
import app.services.engine_b_service as engine_b_service
import src.dynasty_genius.pvo_assembler as pvo_assembler
from src.dynasty_genius.models.engine_b_contract import ENGINE_B_FEATURES_BY_POSITION
from src.dynasty_genius.models.player_identity import PlayerIdentity


def _clear_loader_cache(loader) -> None:
    cache_clear = getattr(loader, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


def test_player_detail_pvo_loader_reflects_rewritten_runtime_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Volatile player-detail PVO artifacts must not remain stale in-process."""
    pvo_path = tmp_path / "universe_pvo_runtime.json"
    pvo_path.write_text(json.dumps({"captured_at": "first", "players": []}))

    monkeypatch.setattr(
        players_route,
        "resolve_pvo_source",
        lambda **_kwargs: SimpleNamespace(pvo_path=pvo_path),
    )
    _clear_loader_cache(players_route._load_player_detail_artifacts)

    assert players_route._load_player_detail_artifacts()["captured_at"] == "first"

    pvo_path.write_text(json.dumps({"captured_at": "second", "players": []}))

    assert players_route._load_player_detail_artifacts()["captured_at"] == "second"


def test_player_detail_market_loader_reflects_rewritten_divergence_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Volatile market divergence artifacts must not remain stale in-process."""
    divergence_path = tmp_path / "universe_market_divergence_latest.json"
    divergence_path.write_text(json.dumps({"captured_at": "first", "players": []}))

    monkeypatch.setattr(players_route, "MARKET_DIVERGENCE_PATH", divergence_path)
    _clear_loader_cache(players_route._load_market_divergence_artifact)

    assert players_route._load_market_divergence_artifact()["captured_at"] == "first"

    divergence_path.write_text(json.dumps({"captured_at": "second", "players": []}))

    assert players_route._load_market_divergence_artifact()["captured_at"] == "second"


def _rb_identity() -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="fixture_rb_001",
        full_name="Fixture RB",
        position="RB",
        nfl_team="DAL",
        verification_status="VERIFIED",
    )


def _rb_engine_b_features() -> dict[str, object]:
    features: dict[str, object] = {
        feature: 1.0 for feature in ENGINE_B_FEATURES_BY_POSITION["RB"]
    }
    features.update(
        {
            "age": 24.0,
            "feature_season": 2025,
            "games_t": 12.0,
            "ppg_t": 13.4,
            "ppg_t_minus_1_available": True,
            "ppg_t_minus_2_available": True,
            "snap_share": 0.62,
            "snap_share_t_minus_1_available": True,
        }
    )
    return features


def test_pvo_assembler_logs_engine_b_single_player_failure_with_context(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Single-player Engine B failures must be observable and caveated."""

    def raise_scoring_failure(_payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("fixture scoring failure")

    monkeypatch.setattr(
        pvo_assembler,
        "predict_player_season_b",
        raise_scoring_failure,
    )
    caplog.set_level(logging.ERROR, logger=pvo_assembler.__name__)

    pvo = pvo_assembler.assemble_pvo(_rb_identity(), _rb_engine_b_features())

    assert "engine_b_single_player_scoring_failed" in pvo.caveats
    records = [
        record
        for record in caplog.records
        if record.levelno >= logging.ERROR
        and "Engine B single-player scoring failed" in record.getMessage()
    ]
    assert records, "Expected an Engine B scoring failure log record"
    record = records[0]
    assert record.exc_info is not None
    assert getattr(record, "player_id", None) == "fixture_rb_001"
    assert getattr(record, "player_name", None) == "Fixture RB"
    assert getattr(record, "position", None) == "RB"
    assert getattr(record, "feature_season", None) == 2025


def test_engine_b_service_contract_violation_logs_without_stdout(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Engine B service failures should use structured logging, not print."""
    caplog.set_level(logging.ERROR, logger=engine_b_service.__name__)

    result = engine_b_service._validate_bundle(
        {"features": ["age", "ktc_value"]},
        "fixture_engine_b.pkl",
    )

    captured = capsys.readouterr()
    assert result is False
    assert captured.out == ""
    assert captured.err == ""
    records = [
        record
        for record in caplog.records
        if record.levelno >= logging.ERROR
        and "Engine B contract violation" in record.getMessage()
    ]
    assert records, "Expected a structured Engine B contract violation log"
    assert getattr(records[0], "source", None) == "fixture_engine_b.pkl"
