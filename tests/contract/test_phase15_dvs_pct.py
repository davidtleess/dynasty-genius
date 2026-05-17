"""Phase 15 dvs_pct batch - spec section 5.14."""
from __future__ import annotations

import pytest

from scripts.compute_dvs_pct_batch import compute_dvs_pct_batch
from src.dynasty_genius.models.player_value_object import PlayerValueObject


def _pvo(pos: str, dvs: float, grade: str = "ACTIVE_B") -> PlayerValueObject:
    return PlayerValueObject(
        player_id=f"test_{pos}_{dvs}",
        full_name="Test Player",
        position=pos,
        model_grade=grade,
        dynasty_value_score=dvs,
        signal_completeness=1.0,
    )


def test_dvs_pct_reference_population_active_b_only():
    """5.14: PRE_MODEL players are not in the reference population denominator."""
    pvos = [
        _pvo("WR", 90.0),
        _pvo("WR", 60.0),
        _pvo("WR", 30.0),
        _pvo("WR", 50.0, grade="PRE_MODEL"),
    ]
    compute_dvs_pct_batch(pvos)
    wr_pvos = [p for p in pvos if p.model_grade == "ACTIVE_B"]
    sorted_pvos = sorted(wr_pvos, key=lambda x: x.dynasty_value_score, reverse=True)
    assert sorted_pvos[0].dvs_pct == pytest.approx(100.0)
    assert sorted_pvos[1].dvs_pct == pytest.approx(50.0)
    assert sorted_pvos[2].dvs_pct == pytest.approx(0.0)
    pre_model = next(p for p in pvos if p.model_grade == "PRE_MODEL")
    assert pre_model.dvs_pct is None


def test_dvs_pct_timestamp_set():
    """dvs_pct_as_of is set after batch runs."""
    pvos = [_pvo("QB", 75.0), _pvo("QB", 50.0)]
    compute_dvs_pct_batch(pvos)
    for pvo in pvos:
        assert pvo.dvs_pct_as_of is not None
