import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.routes import roster_audit_models as ram
from app.api.routes.roster_audit_models import (
    QBContextCard,
    RosterAuditResponse,
    validate_tokens,
)

REAL = Path("app/data/backtest/trust_surface/latest")


def test_trust_valid_from_published_artifact(monkeypatch):
    monkeypatch.setattr(ram, "TRUST_DIR", REAL)
    status, caveats = ram.load_model_status_by_position(["WR"])
    assert status["WR"] in {"VALIDATED", "PROVISIONAL", "EXPERIMENTAL"}


def test_trust_missing_is_failclosed(tmp_path, monkeypatch):
    monkeypatch.setattr(ram, "TRUST_DIR", tmp_path)
    status, caveats = ram.load_model_status_by_position(["QB"])
    assert status["QB"] == "EXPERIMENTAL" and "trust_status_unavailable" in caveats


def test_trust_malformed_is_failclosed(tmp_path, monkeypatch):
    (tmp_path / "backtest_result_RB.json").write_text("{ not json")
    monkeypatch.setattr(ram, "TRUST_DIR", tmp_path)
    status, caveats = ram.load_model_status_by_position(["RB"])
    assert status["RB"] == "EXPERIMENTAL" and "trust_status_unavailable" in caveats


def test_trust_stale_model_version_failclosed(tmp_path, monkeypatch):  # R2-4
    d = tmp_path / "t"
    shutil.copytree(REAL, d)
    m = json.loads((d / "manifest.json").read_text())
    pos = next(iter(m["positions"]))
    m["positions"][pos]["model_version"] = "engine_b_vSTALE"
    (d / "manifest.json").write_text(json.dumps(m))
    monkeypatch.setattr(ram, "TRUST_DIR", d)
    status, caveats = ram.load_model_status_by_position([pos])
    assert status[pos.upper()] == "EXPERIMENTAL" and "trust_status_stale" in caveats


def test_trust_missing_manifest_is_failclosed(tmp_path, monkeypatch):
    d = tmp_path / "t"
    shutil.copytree(REAL, d)
    (d / "manifest.json").unlink()
    monkeypatch.setattr(ram, "TRUST_DIR", d)
    status, caveats = ram.load_model_status_by_position(["WR"])
    assert status["WR"] == "EXPERIMENTAL" and "trust_status_unavailable" in caveats


def test_trust_out_of_domain_status_is_failclosed(tmp_path, monkeypatch):
    d = tmp_path / "t"
    shutil.copytree(REAL, d)
    result = json.loads((d / "backtest_result_WR.json").read_text())
    result["promotion_gate"]["model_status"] = "TOTALLY_BOGUS"
    (d / "backtest_result_WR.json").write_text(json.dumps(result))
    monkeypatch.setattr(ram, "TRUST_DIR", d)
    status, caveats = ram.load_model_status_by_position(["WR"])
    assert status["WR"] == "EXPERIMENTAL" and "trust_status_unavailable" in caveats


def test_decision_supported_locked():
    with pytest.raises(ValidationError):
        RosterAuditResponse(
            status="active",
            engine="e",
            reason="r",
            model_status_by_position={},
            decision_supported=True,
        )  # type: ignore[arg-type]


def test_qb_card_rejects_unknown_field():  # F2: no extra=allow
    with pytest.raises(ValidationError):
        QBContextCard(
            player_id="q",
            full_name="QB",
            identity_coverage="FULL",
            source_qb_context_annotations="x",
            market_value=99,
        )  # type: ignore[call-arg]


def test_validate_tokens_strips_unknown_and_banned():  # F1
    clean, caveats = validate_tokens(["past_cliff", "elite", "totally_unknown"])
    assert clean == ["past_cliff"] and "evidence_suppressed_banned_term" in caveats
