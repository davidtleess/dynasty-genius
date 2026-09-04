"""Fixture helper for DG-157: assemble one PVO row through the real assembler."""

from __future__ import annotations

from typing import Any

from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def assemble(*, position: str, projection: float) -> dict[str, Any]:
    """One Engine-B row at a chosen projection, with availability held at 1.0 so the test
    controls the input the score is built from."""
    identity = PlayerIdentity(
        dg_id="test",
        full_name="Test",
        position=position,
        is_prospect=False,
        verification_status="VERIFIED_NFL_DRAFT",
    )
    features = {
        "engine_b_score": {"predicted_avg_ppg_t1_t2": projection, "engine": "test_v2"},
        "games_t": 10,
        "feature_season": 2024,
        "availability_p": 1.0,
    }
    pvo = assemble_pvo(identity, features)
    return {
        "dynasty_value_score": pvo.dynasty_value_score,
        "xvar": pvo.xvar,
        "dvs_clamped": pvo.dvs_clamped,
        "xvar_ceiling_bound": pvo.xvar_ceiling_bound,
    }
