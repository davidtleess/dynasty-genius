"""Phase 7 PVO schema contract tests.

Covers all 9 requirements from docs/superpowers/specs/2026-05-13-pvo-alignment-design.md:

1. Active-player PVO with Engine B score has projection_2y and engine_used = "engine_b"
2. projection_1y is never populated from Engine B
3. source_season maps from engine_b_score["feature_season"]
4. inputs_present/inputs_missing use ENGINE_B_FEATURES_BY_POSITION (no phantom features)
5. RosterAuditSignals.age_value_context receives the Engine B-backed context label
6. TE active-player PVO carries engine_b_experimental_v1_fallback caveat
7. market_overlay is None
8. decision_supported is False for active-player PVOs
9. No prohibited market feature appears in inputs_present

All tests use the batch path — engine_b_score supplied explicitly in features.
No Engine B artifacts required.
"""
from __future__ import annotations


from src.dynasty_genius.models.engine_b_contract import ENGINE_B_PROHIBITED_FEATURES
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


# ── Shared fixtures ───────────────────────────────────────────────────────────

def _rb_identity() -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test_rb_1998",
        full_name="Test RB",
        position="RB",
        nfl_team="KC",
        verification_status="VERIFIED",
    )


def _wr_identity() -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test_wr_1998",
        full_name="Test WR",
        position="WR",
        nfl_team="DET",
        verification_status="VERIFIED",
    )


def _te_identity() -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="test_te_1996",
        full_name="Test TE",
        position="TE",
        nfl_team="KC",
        verification_status="VERIFIED",
    )


def _rb_score(ppg: float = 15.5, feature_season: int = 2024) -> dict:
    return {
        "predicted_avg_ppg_t1_t2": ppg,
        "engine": "engine_b_v2_rb",
        "feature_season": feature_season,
        "position": "RB",
        "decision_supported": False,
        "experimental": False,
        "caveats": ["engine_b_not_decision_grade"],
    }


def _wr_score(ppg: float = 13.0) -> dict:
    return {
        "predicted_avg_ppg_t1_t2": ppg,
        "engine": "engine_b_v2_wr",
        "feature_season": 2024,
        "position": "WR",
        "decision_supported": False,
        "experimental": False,
        "caveats": ["engine_b_not_decision_grade"],
    }


def _te_score(ppg: float = 9.0) -> dict:
    return {
        "predicted_avg_ppg_t1_t2": ppg,
        "engine": "engine_b_v1",
        "feature_season": 2024,
        "position": "TE",
        "decision_supported": False,
        "experimental": True,
        "caveats": [
            "engine_b_not_decision_grade",
            "engine_b_does_not_beat_baseline_for_this_position",
        ],
    }


def _rb_features(engine_b_score: dict | None = None) -> dict:
    """RB base features (all 11 ENGINE_B_BASE_FEATURES present)."""
    f: dict = {
        "age": 25,
        "ppg_t": 15.0,
        "games_t": 16,
        "snap_share": 0.72,
        "aging_curve_value": 0.95,
        "ppg_t_minus_1": 14.5,
        "ppg_t_minus_2": 13.0,
        "snap_share_t_minus_1": 0.70,
        "ppg_t_minus_1_available": True,
        "ppg_t_minus_2_available": True,
        "snap_share_t_minus_1_available": True,
    }
    if engine_b_score is not None:
        f["engine_b_score"] = engine_b_score
    return f


def _te_features(engine_b_score: dict | None = None) -> dict:
    """TE features (base + receiver metrics)."""
    f: dict = {
        "age": 27,
        "ppg_t": 9.0,
        "games_t": 16,
        "snap_share": 0.60,
        "aging_curve_value": 0.90,
        "ppg_t_minus_1": 8.5,
        "ppg_t_minus_2": 8.0,
        "snap_share_t_minus_1": 0.58,
        "ppg_t_minus_1_available": True,
        "ppg_t_minus_2_available": True,
        "snap_share_t_minus_1_available": True,
        "weighted_opportunity": 0.20,
        "yprr": 1.5,
        "tprr": 0.12,
    }
    if engine_b_score is not None:
        f["engine_b_score"] = engine_b_score
    return f


# ── Requirement 1 ─────────────────────────────────────────────────────────────

def test_active_player_pvo_has_engine_b_projection_2y_and_engine_used():
    """Engine B predicted_avg_ppg_t1_t2 maps to projection_2y; engine_used = 'engine_b'."""
    score = _rb_score(ppg=15.5)
    pvo = assemble_pvo(_rb_identity(), _rb_features(engine_b_score=score))
    assert pvo.engine_used == "engine_b"
    assert pvo.projection_2y == 15.5


# ── Requirement 2 ─────────────────────────────────────────────────────────────

def test_engine_b_does_not_populate_projection_1y():
    """Engine B has no single-year model — projection_1y must remain None."""
    score = _rb_score()
    pvo = assemble_pvo(_rb_identity(), _rb_features(engine_b_score=score))
    assert pvo.projection_1y is None


# ── Requirement 3 ─────────────────────────────────────────────────────────────

def test_source_season_maps_from_engine_b_feature_season():
    """source_season carries the Engine B feature_season for provenance."""
    score = _rb_score(feature_season=2024)
    pvo = assemble_pvo(_rb_identity(), _rb_features(engine_b_score=score))
    assert pvo.source_season == 2024


# ── Requirement 4 ─────────────────────────────────────────────────────────────

def test_inputs_use_engine_b_contract_not_phantom_features():
    """Phantom features from the old _ENGINE_B_REQUIRED dict must not appear."""
    pvo = assemble_pvo(_rb_identity(), _rb_features())
    phantom = {"breakaway_run_pct", "run_blocking_grade", "target_share", "yards_per_route_run"}
    for feat in phantom:
        assert feat not in pvo.inputs_present, f"Phantom feature {feat!r} in inputs_present"
        assert feat not in pvo.inputs_missing, f"Phantom feature {feat!r} in inputs_missing"
    # Actual Engine B contract features ARE checked
    assert "snap_share" in pvo.inputs_present or "snap_share" in pvo.inputs_missing


# ── Requirement 5 ─────────────────────────────────────────────────────────────

def test_roster_audit_signals_age_value_context_from_engine_b():
    """When an Engine B score is threaded through, age_value_context reflects the projection."""
    score = _rb_score(ppg=15.5)
    pvo = assemble_pvo(_rb_identity(), _rb_features(engine_b_score=score))
    assert pvo.roster_audit is not None
    assert pvo.roster_audit.age_value_context is not None
    assert pvo.roster_audit.age_value_context != "no_engine_b_projection"


# ── Requirement 6 ─────────────────────────────────────────────────────────────

def test_te_active_player_pvo_carries_experimental_caveat_and_grade():
    """TE v1 fallback (experimental=True) propagates the experimental caveat."""
    score = _te_score()
    pvo = assemble_pvo(_te_identity(), _te_features(engine_b_score=score))
    assert "engine_b_experimental_v1_fallback" in pvo.caveats
    assert pvo.model_grade == "EXPERIMENTAL"


# ── Requirement 7 ─────────────────────────────────────────────────────────────

def test_market_overlay_is_none():
    """market_overlay must never be set in Phase 7 — reserved for Phase 9."""
    score = _rb_score()
    pvo = assemble_pvo(_rb_identity(), _rb_features(engine_b_score=score))
    assert pvo.market_overlay is None


# ── Requirement 8 ─────────────────────────────────────────────────────────────

def test_decision_supported_is_false_for_active_player_pvo():
    """Active-player PVOs must never claim decision-grade confidence."""
    score = _rb_score()
    pvo = assemble_pvo(_rb_identity(), _rb_features(engine_b_score=score))
    assert pvo.decision_supported is False


# ── Requirement 9 ─────────────────────────────────────────────────────────────

def test_no_prohibited_market_feature_in_inputs_present():
    """KTC, ADP, FantasyCalc, and other market features must never appear in signal lists."""
    score = _rb_score()
    pvo = assemble_pvo(_rb_identity(), _rb_features(engine_b_score=score))
    leaked = set(pvo.inputs_present) & ENGINE_B_PROHIBITED_FEATURES
    assert not leaked, f"Prohibited market features in inputs_present: {leaked}"
