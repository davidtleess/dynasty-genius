"""The replacement bar David ruled: 'the next who is actually available' (2026-09-05).

At each position the bar is the best player NOBODY in his league owns, measured on the
SERVED rate so both sides of the subtraction are the same kind of number. The bar player's
conditional projection rides along because the retention cells are keyed on conditional
rates (CANONICAL.md). Held constant across horizons as a DECLARED scenario: today's waiver
inventory is not known years forward, and the contract says so on every term set.

Band-averaging over the top ``band`` available players is David's own suggestion (DG-171)
and is opt-in: the default of 1 is the ruling, unchanged.
"""
from __future__ import annotations

from typing import Iterable, Optional

from src.dynasty_genius.ranking.contract import ReplacementRef
from src.dynasty_genius.ranking.served_rows import ServedRow

POLICY_NAME = "best_available_served_rate"


def available_replacement(rows: Iterable[ServedRow], rostered_ids: set[str], snapshot_id: str,
                          band: int = 1, positions: Optional[Iterable[str]] = None) -> dict[str, ReplacementRef]:
    """One ReplacementRef per position from the players nobody in the league owns.

    A row can set the bar only if it carries a served rate that is an ESTIMATE (unclamped) and
    a conditional projection (so the margin key can be built). Engine A prospects have no
    projection and cannot be the bar; a clamped row's rate is a bound and cannot either.

    ``positions`` defaults to the positions present in ``rows``; the audit passes the four
    skill positions explicitly so a missing one is an error there, not a silent omission.
    """
    if band < 1:
        raise ValueError("band must be >= 1")
    rows = list(rows)
    rostered = {str(x) for x in rostered_ids}
    wanted = sorted({r.position for r in rows}) if positions is None else list(positions)
    out: dict[str, ReplacementRef] = {}
    for pos in wanted:
        pool = [r for r in rows if r.position == pos
                and str(r.sleeper_id) not in rostered and str(r.player_id) not in rostered
                and r.served_rate_ppg is not None and not r.dvs_clamped
                and r.projection_2y is not None and r.projection_2y > 0]
        if not pool:
            raise ValueError(f"no available player can set the {pos} replacement bar: "
                             "every scored, unclamped, projected player is rostered")
        top = sorted(pool, key=lambda r: r.served_rate_ppg, reverse=True)[:band]
        if len(top) < band:
            raise ValueError(f"{pos}: band={band} asked for but only {len(top)} available players qualify")
        rate = sum(r.served_rate_ppg for r in top) / len(top)
        cond = sum(r.projection_2y for r in top) / len(top)
        out[pos] = ReplacementRef(
            position=pos, policy=POLICY_NAME, rate_ppg=rate, conditional_rate_ppg=cond,
            snapshot_id=snapshot_id, horizon_assumption="held_constant_from_snapshot",
            band=band,
            player_id=top[0].player_id if band == 1 else None,
            player_name=top[0].full_name if band == 1 else None,
        )
    return out
