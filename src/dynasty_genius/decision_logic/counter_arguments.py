from typing import Optional

from src.dynasty_genius.models.engine_b_contract import (
    DVS_SCALE_ANCHOR_PPG,
    ENGINE_B_P90_PPG,
)
from src.dynasty_genius.models.player_value_object import PlayerValueObject

# DG-158 — "top asset" is a share of the scale, not a number of points on it.
#
# This gate read `val > 80` on a 0-100 scale, which meant "the top fifth". The
# 80 was only ever correct because every position's ceiling was 100. Replace the
# per-position denominators with a single anchor and the ceilings stop being 100:
# measured on the served artifact, clearing 80 would then require a player to
# score 102.4 today at running back, 110.9 at receiver and 171.0 at tight end,
# and scores clamp at 100 — so the MANDATORY counter-argument (Constitution
# Rule 4) becomes unreachable at three of four positions on each engine, and 41
# players lose it with no risk flag to catch them. Silently: nobody edits this
# file, the arithmetic just stops reaching it.
#
# So the threshold is now derived. `SCALE_ANCHOR_PPG` is the denominator each
# position's score is expressed against; while it equals the position's own P90
# the ceiling is 100 and the threshold is 80, exactly as today. When the anchor
# moves, the threshold moves with it and the rule keeps meaning "the top fifth".
TOP_ASSET_SCALE_SHARE = 0.80

# The denominator the displayed score is divided by. DG-159 made it a single anchor
# for every position, so the ceilings are no longer 100: QB 100, RB 78.1, WR 72.1,
# TE 46.8. This reads the same constant the score divides by, so the two cannot
# drift apart.
#
# It must NOT be aliased back to ENGINE_B_P90_PPG. That was its value while the two
# were the same thing, and `position_ceiling` would then be P90/P90*100 — identically
# 100 whatever anyone does to either, so the threshold silently returns to a hard 80
# that three of four positions can never reach, and 41 players lose the MANDATORY
# counter-argument with every test in this file still green.
SCALE_ANCHOR_PPG = DVS_SCALE_ANCHOR_PPG


def position_ceiling(position: str) -> float:
    """The highest displayed score this position can reach, on today's scale.

    ``score = ppg / anchor * 100`` and the best player is at his position's P90,
    so the ceiling is ``P90 / anchor * 100`` — 100 while the anchor is the
    position's own P90, and less once a single anchor serves every position.
    """
    pos = (position or "").upper()
    return ENGINE_B_P90_PPG[pos] / SCALE_ANCHOR_PPG[pos] * 100.0


def top_asset_threshold(position: str) -> float:
    """The score above which a player is a top asset, in today's units.

    A KeyError for an unknown position is deliberate: guessing a threshold for a
    position nobody has scaled is how a silent default gets in.
    """
    return TOP_ASSET_SCALE_SHARE * position_ceiling(position)


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

    # Priority 2: Top Assets — the top fifth of this position's scale.
    # DG-158: was a literal `> 80`, which silently stopped firing when the scale
    # moved beneath it. `top_asset_threshold` is 80.0 while the ceiling is 100.
    val = dynasty_value_score
    if val is not None and val > top_asset_threshold(position):
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
