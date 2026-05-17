"""Compute within-position dvs_pct for active Player Value Objects.

Reference population: ACTIVE_B players with non-null dynasty_value_score.
Formula: (N - 1 - rank_desc) / (N - 1) * 100.
Mutates PVOs in-place by setting dvs_pct and dvs_pct_as_of.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from src.dynasty_genius.models.player_value_object import PlayerValueObject


def compute_dvs_pct_batch(pvos: List[PlayerValueObject]) -> None:
    """Set dvs_pct and dvs_pct_as_of on each ACTIVE_B PVO in-place."""
    now_utc = datetime.now(timezone.utc).isoformat()
    positions = {pvo.position.upper() for pvo in pvos}

    for pos in positions:
        active_b = [
            pvo
            for pvo in pvos
            if pvo.position.upper() == pos
            and pvo.model_grade == "ACTIVE_B"
            and pvo.dynasty_value_score is not None
        ]
        n = len(active_b)
        if n == 0:
            continue

        sorted_pop = sorted(active_b, key=lambda pvo: pvo.dynasty_value_score, reverse=True)
        for rank_0, pvo in enumerate(sorted_pop):
            pvo.dvs_pct = 100.0 if n == 1 else round(((n - 1 - rank_0) / (n - 1)) * 100.0, 1)
            pvo.dvs_pct_as_of = now_utc


if __name__ == "__main__":
    print("compute_dvs_pct_batch: import and call compute_dvs_pct_batch(pvos) directly.")
