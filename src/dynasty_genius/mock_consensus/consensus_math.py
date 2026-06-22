"""Canonical consensus math for Subsystem 1 (pure, threshold-free).

Per spec v4 U1, this module owns ONLY the shared consensus *math*: it returns
RAW dispersion statistics and counts. It applies **no threshold**, emits **no**
``disagreement_flag``, holds **no abstention policy**, and performs **no I/O**.
The ``IQR > 6`` dispersion flag/block and all abstention gating are *consumer*
policy (S1 aggregation in T4; S4 keeps its own ``dispersion_threshold``).

IQR is LOCKED to ``statistics.quantiles(picks, n=4)`` with the default
``'exclusive'`` method for S4 parity (see
``src/dynasty_genius/eval/backtest_mock_draft.py:486-491``); ``len < 2`` yields
``iqr = 0.0``. MAD is the raw, unscaled median-absolute-deviation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median as _median
from statistics import quantiles as _quantiles


@dataclass(frozen=True)
class ConsensusObservation:
    """One analyst's mock-draft projection for a prospect (pure input row)."""

    pick_no: int | None
    projected_round: int | None
    source_id: str
    analyst: str
    published_date: str


@dataclass(frozen=True)
class ConsensusStats:
    """Raw consensus statistics. Threshold-free (U1): no ``disagreement_flag``."""

    median: float
    min: int
    max: int
    iqr: float
    mad: float
    n_sources: int
    n_unique_analysts: int
    staleness_days: int


def compute_consensus_stats(
    observations: list[ConsensusObservation],
    *,
    as_of: str,
) -> ConsensusStats:
    """Compute raw consensus statistics over observation pick numbers.

    Pure: no I/O, no policy, no threshold. Fails loud on empty input.
    """
    if not observations:
        raise ValueError("observations must not be empty")

    picks = [obs.pick_no for obs in observations]
    median_val = float(_median(picks))
    min_val = min(picks)
    max_val = max(picks)

    if len(picks) >= 2:
        q1, _q2, q3 = _quantiles(picks, n=4)
        iqr_val = float(q3 - q1)
    else:
        iqr_val = 0.0

    mad_val = float(_median([abs(pick - median_val) for pick in picks]))

    n_sources = len({obs.source_id for obs in observations})
    n_unique_analysts = len({obs.analyst for obs in observations})

    as_of_date = date.fromisoformat(as_of)
    staleness_days = max(
        (as_of_date - date.fromisoformat(obs.published_date)).days
        for obs in observations
    )

    return ConsensusStats(
        median=median_val,
        min=min_val,
        max=max_val,
        iqr=iqr_val,
        mad=mad_val,
        n_sources=n_sources,
        n_unique_analysts=n_unique_analysts,
        staleness_days=staleness_days,
    )
