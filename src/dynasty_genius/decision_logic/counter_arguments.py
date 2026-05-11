from typing import Optional

from src.dynasty_genius.models.player_value_object import PlayerValueObject


def generate_counter_argument(pvo: PlayerValueObject) -> Optional[str]:
    """Generate a mandatory steel-manned counter-argument for a player.

    Adheres to Product Constitution Rule 4: 'The Counter-Argument is Mandatory.'
    """
    flags = pvo.risk_flags or []

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
    val = pvo.dynasty_value_score
    if val is not None and val > 80:
        pos = (pvo.position or "").upper()
        if pos == "QB":
            return "Elite valuation assumes continued high-level rushing or outlier passing efficiency; any dip in mobility or supporting cast could lead to a rapid value correction."
        if pos == "RB":
            return "RB value is notoriously fragile; current high ranking ignores the extreme year-over-year turnover at the position and the risk of a sudden volume reduction."
        if pos == "WR":
            return "High-end WR value can be capped by target competition or declining QB play, making this asset more dependent on situation than the market currently acknowledges."
        if pos == "TE":
            return "TE production is often TD-dependent; elite status is difficult to maintain if the team adds target-earning wideouts or changes offensive schemes."
        return "High valuation leaves little room for error; the market is currently pricing in a best-case scenario that may not be sustainable."

    return None
