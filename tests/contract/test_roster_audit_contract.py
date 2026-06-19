import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.routes import roster_audit_models as ram
from app.api.routes.roster_audit_models import (
    QBContextCard,
    RosterAuditResponse,
    RosterDependencyError,
    assemble_response,
    map_player,
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


def _raw(**o):
    base = {"player_id": "p", "full_name": "WR", "position": "WR",
        "engine_used": "engine_b", "model_grade": "ACTIVE_B",
        "counter_argument": "solid floor", "top_drivers": ["target_share"],
        "risk_flags": ["snap_share_below_40pct"], "caveats": ["no_market_overlay"],
        "roster_audit": {"signal": "at_cliff", "signal_drivers": ["age_at_position_cliff"],
                         "decision_supported": True},  # F3 nested-true probe
        "market_overlay": {"market_value": 123}, "market_value": 99, "future_x": "leak"}
    base.update(o)
    return base


def test_excludes_market_and_future():  # AC-1
    p = map_player(_raw()).model_dump()
    for f in ("market_overlay", "market_value", "future_x"):
        assert f not in p
    assert "leak" not in str(p) and "123" not in str(p)


def test_nested_decision_supported_coerced_false():  # F3
    p = map_player(_raw())
    assert p.roster_audit.decision_supported is False


def test_token_only_caveats_enforced():  # AC-5
    p = map_player(_raw(caveats=["no_market_overlay", "elite", "mystery_token"]))
    assert "elite" not in p.caveats and "mystery_token" not in p.caveats


def test_scalar_token_fields_validated():  # R3-1: AC-5 scalar (signal/age_value_context/liquidity_risk)
    p = map_player(_raw(roster_audit={"signal": "elite", "age_value_context": "must sell",
                                      "liquidity_risk": "unknown"}))
    assert p.roster_audit.signal is None
    assert p.roster_audit.age_value_context is None
    assert p.roster_audit.liquidity_risk is None
    assert "evidence_suppressed_banned_term" in p.roster_audit.caveats


def test_engine_a_not_applicable():  # AC-6 / F6
    for eng in ("engine_a", None):
        assert map_player(_raw(engine_used=eng, model_grade="PROSPECT_C")).model_status_applies is False
    assert map_player(_raw(engine_used="engine_b")).model_status_applies is True


def _audit(players, qb=None):
    return {"status": "active", "engine": "pvo_assembler_v1", "reason": "ok",
        "caveats": ["no_market_overlay"], "players": players, "qb_context_cards": qb or []}


def test_isolated_corrupt_dropped():  # AC-4
    r = assemble_response(_audit([_raw(player_id="g"), {"oops": 1}]))
    assert r.dropped_player_count == 1 and "player_row_dropped_corrupt" in r.caveats
    assert len(r.players) == 1 and r.status == "degraded"


def test_all_invalid_systemic_503():
    with pytest.raises(RosterDependencyError):
        assemble_response(_audit([{"x": 1}, {"y": 2}]))


def test_qb_card_tokens_validated():  # AC-5 (QB path)
    qb = [{"player_id": "q", "full_name": "QB", "identity_coverage": "FULL",
           "source_qb_context_annotations": "cfbd_qb_context_annotations",
           "qb_context_annotations": ["elite", "low_td_int_ratio_bust_context"]}]
    r = assemble_response(_audit([_raw()], qb=qb))
    assert "elite" not in r.qb_context_cards[0].qb_context_annotations
    assert "low_td_int_ratio_bust_context" in r.qb_context_cards[0].qb_context_annotations


def test_qb_card_unsafe_source_dropped_degraded():  # R2-2 + R2-5
    qb = [{"player_id": "q", "full_name": "QB", "identity_coverage": "FULL",
           "source_qb_context_annotations": "totally_unknown_source"}]
    r = assemble_response(_audit([_raw()], qb=qb))
    assert r.qb_context_cards == [] and r.dropped_player_count == 1
    assert "qb_context_card_dropped_corrupt" in r.caveats and r.status == "degraded"
