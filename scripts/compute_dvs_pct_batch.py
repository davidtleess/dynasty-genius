"""Compute within-position dvs_pct for active Player Value Objects.

Reference population: ACTIVE_B players with non-null dynasty_value_score.
Formula: (N - 1 - rank_desc) / (N - 1) * 100, where rank_desc is the AVERAGE
rank across equal scores so tied players share one percentile.
Mutates PVOs in-place by setting dvs_pct and dvs_pct_as_of.

NOTE ON THE FIELD NAME: this value reaches the artifact and the API as
``valuation.xvar_percentile_position`` (universe_pvo_batch.py:99), not as
``dvs_pct``. Searching the served payload for ``dvs_pct`` finds nothing and
looks like the field is unpopulated -- it is renamed on the way in.
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
        # AVERAGE RANK among equal scores. `enumerate` assigned a distinct rank
        # by sort position, so players the model scored identically received
        # different percentiles -- an ordering it has no basis for. Measured on
        # the live artifact 2026-08-31: 23 tie groups, 64 players, including the
        # 11 TEs the clamp pins at exactly 100.0 spread across 11 percentiles.
        # A tie is information; inventing an order discards it and asserts a
        # comparison the model cannot make.
        # With no ties this is arithmetically identical to enumerate(), so
        # untied populations are unchanged.
        i = 0
        while i < n:
            j = i
            while (
                j + 1 < n
                and sorted_pop[j + 1].dynasty_value_score
                == sorted_pop[i].dynasty_value_score
            ):
                j += 1
            mean_rank = (i + j) / 2.0
            pct = 100.0 if n == 1 else round(((n - 1 - mean_rank) / (n - 1)) * 100.0, 1)
            for tied in sorted_pop[i : j + 1]:
                tied.dvs_pct = pct
                tied.dvs_pct_as_of = now_utc
            i = j + 1


if __name__ == "__main__":
    print("compute_dvs_pct_batch: import and call compute_dvs_pct_batch(pvos) directly.")
