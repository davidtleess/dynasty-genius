"""RED — clamp truth must survive the whole chain: scorer → assembler → batch.

Codex round-2 finding: the round-1 contracts exercised `EngineAScorer.score`
alone, so nothing pinned the assembler, the V3 head, the blend path, or the
batch serializer against a producer-to-surface regression.

Blend semantics per Codex's ruling (round 2): `dvs_clamped` states what happened
to THIS score. Both blend components enter already clamped to [0,100] and the
weights sum to 1, so the blend arithmetic can never truncate — the blend is
therefore NOT clamped, even when a component was. `xvar_ceiling_bound` derives
from the same flag (`pvo_assembler:500`) and must stay truthful with it.
"""
from __future__ import annotations

from typing import Any

import pytest

from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import ENGINE_B_MIN_GAMES_T, assemble_pvo
from src.dynasty_genius.scoring import engine_a as engine_a_module
from src.dynasty_genius.universe_pvo_batch import build_universe_pvo_batch


class _StubModel:
    def __init__(self, ppg: float) -> None:
        self._ppg = ppg

    def predict(self, _x: Any) -> list[float]:
        return [self._ppg]


def test_v3_head_reports_clamp_truth_measured_before_rounding(monkeypatch):
    """The second Engine A head must obey the same pre-round rule."""
    scorer = engine_a_module.EngineAV3Scorer()
    monkeypatch.setattr(scorer, "_load", lambda: True)
    p90 = engine_a_module.DVS_SCALE_ANCHOR_PPG["TE"]  # DG-159: one denominator, not the position P90
    monkeypatch.setattr(
        scorer, "_models", {"TE": _StubModel(p90 * 0.9999589)}, raising=False
    )
    # The v3 head refuses unless every contracted feature is present and non-None.
    contract = engine_a_module.HEAD_A_V3_FEATURE_CONTRACTS["TE"]
    features = {feat: 1.0 for feat in contract}

    result = scorer.score(position="TE", features=features)

    assert result["dynasty_value_score"] == 100.0
    assert result["dvs_clamped"] is False


def test_v3_head_reports_not_clamped_at_exactly_one_hundred(monkeypatch):
    """Boundary: raw exactly 100.0 truncates nothing."""
    scorer = engine_a_module.EngineAV3Scorer()
    monkeypatch.setattr(scorer, "_load", lambda: True)
    p90 = engine_a_module.DVS_SCALE_ANCHOR_PPG["TE"]  # DG-159: one denominator, not the position P90
    monkeypatch.setattr(scorer, "_models", {"TE": _StubModel(p90)}, raising=False)
    contract = engine_a_module.HEAD_A_V3_FEATURE_CONTRACTS["TE"]

    result = scorer.score(position="TE", features={f: 1.0 for f in contract})

    assert result["dynasty_value_score"] == 100.0
    assert result["dvs_clamped"] is False


def test_v3_head_reports_clamped_above_one_hundred(monkeypatch):
    """A hardcoded False in the v3 producer must fail here."""
    scorer = engine_a_module.EngineAV3Scorer()
    monkeypatch.setattr(scorer, "_load", lambda: True)
    p90 = engine_a_module.DVS_SCALE_ANCHOR_PPG["TE"]  # DG-159: one denominator, not the position P90
    monkeypatch.setattr(scorer, "_models", {"TE": _StubModel(p90 * 1.25)}, raising=False)
    contract = engine_a_module.HEAD_A_V3_FEATURE_CONTRACTS["TE"]

    result = scorer.score(position="TE", features={f: 1.0 for f in contract})

    assert result["dynasty_value_score"] == 100.0
    assert result["dvs_clamped"] is True


def _stub_engine_a(monkeypatch, *, score: float, clamped: bool) -> None:
    """Pin Engine A's output so the assembler's consumption of clamp TRUTH is
    tested, not its ability to re-infer from a rounded score."""
    result = {
        "dynasty_value_score": score,
        "dvs_clamped": clamped,
        "engine_used": "engine_a_test",
        "model_version": "test",
        "model_grade": "PROSPECT_A",
        "caveats": [],
    }
    monkeypatch.setattr(
        "src.dynasty_genius.pvo_assembler.score_prospect", lambda *a, **k: dict(result)
    )
    monkeypatch.setattr(
        "src.dynasty_genius.pvo_assembler.score_prospect_v3", lambda *a, **k: None
    )


@pytest.mark.parametrize("clamped", [False, True])
def test_assembler_uses_engine_a_clamp_truth_not_the_rounded_score(monkeypatch, clamped):
    """Both directions of the original defect, pinned end-to-end.

    `False` is the defect Codex found in round 1: Engine A ships 100.0 having
    truncated nothing, so the assembler must NOT re-derive `clamped` from the
    rounded score. `True` is Codex finding F5 (round 4): a consumer hardcoded
    to `False` would silently DISCARD genuine truncation, and the whole clamp
    bundle stayed green under exactly that mutation. Both directions are
    required — either alone leaves half the seam unguarded.
    """
    _stub_engine_a(monkeypatch, score=100.0, clamped=clamped)

    pvo = assemble_pvo(
        _engine_b_identity(),
        {"pick": 5.0, "round": 1.0, "age": 22.0},
        is_prospect=True,
    )

    assert pvo.dynasty_value_score == 100.0
    assert pvo.dvs_clamped is clamped
    assert pvo.xvar_ceiling_bound is clamped


@pytest.mark.parametrize("clamped", [False, True])
def test_engine_a_clamp_truth_survives_into_the_batch_serializer(monkeypatch, clamped):
    """scorer → assembler → batch with controlled truth, end to end, both ways.

    The `True` case is the F5 positive control carried to the serialized row: a
    genuinely truncated Engine A score must still read as truncated on the
    surface, not merely inside the PVO.
    """
    _stub_engine_a(monkeypatch, score=100.0, clamped=clamped)
    pvo = assemble_pvo(
        _engine_b_identity(),
        {"pick": 5.0, "round": 1.0, "age": 22.0},
        is_prospect=True,
    )

    snapshot = {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-1",
        "captured_at": "2026-08-18T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": "909",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Ceiling Back", "position": "RB", "team": "SF"},
                "league_context": {"rostered": True, "roster_id": 1},
            }
        ],
        "lineage": {"sleeper_players_hash": "sha256:test"},
    }
    batch = build_universe_pvo_batch(
        snapshot,
        prospect_pvos=[{**pvo.model_dump(), "sleeper_id": "909"}],
        active_pvos=[],
        captured_at="2026-08-18T00:00:01+00:00",
    )

    valuation = batch["players"][0]["valuation"]
    assert valuation["dynasty_value_score"] == 100.0
    assert valuation["dvs_clamped"] is clamped


@pytest.mark.parametrize("clamped", [False, True])
def test_dead_window_fallback_uses_engine_a_clamp_truth(monkeypatch, clamped):
    """games_t == 0 takes the Engine-A-only fallback branch, which had the same
    defective inference as the primary path — and, per F5, the same capacity to
    discard a true one. This seam is a separate line of code from the primary
    consumer, so it carries its own positive control rather than inheriting one.
    """
    _stub_engine_a(monkeypatch, score=100.0, clamped=clamped)
    features = _engine_b_features(30.0, games_t=0)
    features.update({"pick": 5.0, "round": 1.0, "age": 22.0})

    pvo = assemble_pvo(_engine_b_identity(), features)

    assert pvo.dvs_engine == "A", "dead-window fallback not exercised"
    assert pvo.dvs_clamped is clamped
    assert pvo.xvar_ceiling_bound is clamped


def _engine_b_identity() -> PlayerIdentity:
    return PlayerIdentity(
        dg_id="ceiling_rb_1999",
        full_name="Ceiling Back",
        position="RB",
        nfl_team="SF",
        verification_status="VERIFIED",
    )


def _engine_b_features(projected_ppg: float, games_t: int = 16) -> dict[str, Any]:
    """Drive the assembler through its supported `engine_b_score` injection seam
    (pvo_assembler:277) so the clamp logic is exercised without Engine B model
    artifacts. RB P90 is 15.7, so a projection of 30.0 gives raw DVS 191.1."""
    return {
        "age": 25,
        "games_t": games_t,
        "engine_b_score": {
            "engine": "engine_b_test",
            "predicted_avg_ppg_t1_t2": projected_ppg,
            "feature_season": 2025,
            "caveats": [],
        },
    }


def test_assembler_discloses_clamp_for_a_genuinely_truncated_engine_b_score():
    """A raw DVS above the ceiling must reach the PVO as clamped, with xVAR bound."""
    pvo = assemble_pvo(_engine_b_identity(), _engine_b_features(30.0))

    assert pvo.dynasty_value_score == 100.0
    assert pvo.dvs_clamped is True
    assert pvo.xvar_ceiling_bound is True


def test_assembler_reports_not_clamped_for_an_ordinary_engine_b_score():
    """Control: an unremarkable score must not acquire a ceiling claim."""
    pvo = assemble_pvo(_engine_b_identity(), _engine_b_features(10.0))

    assert pvo.dynasty_value_score is not None
    assert pvo.dynasty_value_score < 100.0
    assert pvo.dvs_clamped is False
    assert pvo.xvar_ceiling_bound is False


def test_blend_score_is_not_clamped_even_when_a_component_was():
    """Blend arithmetic cannot truncate; the shipped blend must not claim it did.

    The blend needs BOTH components, so Engine A inputs (pick/round/age) are
    supplied alongside the injected Engine B projection, and `games_t` is placed
    inside the blend window. The blend path is asserted, never skipped — an
    earlier version of this test guarded the assertions behind
    `if dvs_engine == "blend"` and a mutation probe proved it vacuous.
    """
    features = _engine_b_features(30.0, games_t=ENGINE_B_MIN_GAMES_T - 1)
    features.update({"pick": 5.0, "round": 1.0, "age": 22.0})

    pvo = assemble_pvo(_engine_b_identity(), features)

    assert pvo.dvs_engine == "blend", "blend path not exercised — test would be vacuous"
    assert pvo.dynasty_value_score is not None
    assert pvo.dvs_clamped is False
    assert pvo.xvar_ceiling_bound is False


def test_clamp_truth_survives_the_batch_serializer():
    """End of chain: what the assembler decided is what the surface ships."""
    clamped_pvo = {
        "sleeper_id": "202",
        "player_id": "00-0000202",
        "full_name": "Ceiling Back",
        "position": "RB",
        "model_grade": "ACTIVE_B",
        "dynasty_value_score": 100.0,
        "dvs_clamped": True,
        "dvs_p90_ref": 15.7,
        "dvs_engine": "B",
        "decision_supported": False,
        "market_overlay": None,
    }
    snapshot = {
        "schema_version": "sleeper_universe_snapshot.v1",
        "league_id": "league-1",
        "captured_at": "2026-08-18T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": "202",
                "cohort": "FANTASY_RELEVANT",
                "identity_status": "sleeper_resolved",
                "player": {"full_name": "Ceiling Back", "position": "RB", "team": "SF"},
                "league_context": {"rostered": True, "roster_id": 2},
            }
        ],
        "lineage": {"sleeper_players_hash": "sha256:test"},
    }

    batch = build_universe_pvo_batch(
        snapshot,
        prospect_pvos=[],
        active_pvos=[clamped_pvo],
        captured_at="2026-08-18T00:00:01+00:00",
    )
    valuation = batch["players"][0]["valuation"]

    assert valuation["dvs_clamped"] is True
    assert valuation["dvs_p90_ref"] == 15.7
    assert valuation["dynasty_value_score"] == 100.0
