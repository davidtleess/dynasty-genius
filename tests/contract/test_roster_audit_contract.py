import json
import shutil
from pathlib import Path

from app.api.routes import roster_audit_models as ram

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
