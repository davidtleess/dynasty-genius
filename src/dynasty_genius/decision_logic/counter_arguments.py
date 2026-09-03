from typing import Optional

from src.dynasty_genius.models.player_value_object import PlayerValueObject


def generate_counter_argument(pvo: PlayerValueObject) -> Optional[str]:
    """Generate a mandatory steel-manned counter-argument for a player.

    Adheres to Product Constitution Rule 4: 'The Counter-Argument is Mandatory.'
    """
    return counter_argument_for(
        pvo.risk_flags, pvo.dynasty_value_score, pvo.position
    )


def counter_argument_for(
    risk_flags: Optional[list],
    dynasty_value_score: Optional[float],
    position: Optional[str],
) -> Optional[str]:
    """The counter-argument implied by these three fields, and nothing else.

    The same rule as ``generate_counter_argument``, reachable without a
    PlayerValueObject. The universe batch needs it because it restates
    ``risk_flags`` after assembly (DG-140): the counter-argument is a FUNCTION of
    the flags, so a restated flag with the assembly-time argument beside it leaves
    the card asserting a downside that no longer matches its own evidence — and on
    a row that gains ``age_past_position_cliff`` it would drop the mandatory
    counter-argument entirely, against Constitution Rule 4.
    """
    flags = risk_flags or []

    # Priority 1: Specific Risk Flags
    # The Constitution mandates steel-manning the downside path.
    if "age_past_position_cliff" in flags:
        return (
            "Liquidity Caveat: Production may remain useful, but trade liquidity "
            "often narrows as a player moves past the historical age cliff."
        )

    if "snap_share_below_40pct" in flags:
        return (
            "Usage Caveat: Sub-40% snap share at this stage of the season can "
            "signal limited coaching trust and a fragile path to weekly relevance."
        )

    # Priority 2: Top Assets (Internal Value > 80)
    # We use dynasty_value_score as the internal value measure.
    val = dynasty_value_score
    if val is not None and val > 80:
        pos = (position or "").upper()
        if pos == "QB":
            return "Premium valuation assumes continued high-level rushing or outlier passing efficiency; any dip in mobility or supporting cast could lead to a rapid value correction."
        if pos == "RB":
            return "RB value is notoriously fragile; current high ranking ignores the extreme year-over-year turnover at the position and the risk of a sudden volume reduction."
        if pos == "WR":
            return "High-end WR value can be capped by target competition or declining QB play, making this asset more dependent on situation than the market currently acknowledges."
        if pos == "TE":
            return "TE production is often TD-dependent; premium status is difficult to maintain if the team adds target-earning wideouts or changes offensive schemes."
        return "High valuation leaves little room for error; the market is currently pricing in a best-case scenario that may not be sustainable."

    return None
