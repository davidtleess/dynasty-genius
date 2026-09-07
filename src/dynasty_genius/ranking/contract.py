"""The shared value contract (DG-178).

Why the shape is this narrow. Production, availability, rookie qualification and career
retention arrive with different units (points a game vs season totals vs ratios), different
populations (players who played vs players who qualified vs draft classes) and different
clocks (a two-season window vs one season vs "ever"). Multiplying across those boundaries is
how a probability gets counted twice or a conditional mean gets served as an expectation.
So the contract admits only terms that are ALREADY unconditional — a season the player does
not contribute counts 0, because the replacement plays — and forces every producer to say
which event it integrated over and which replacement it subtracted.

The clock. ``h = 0`` is the NFL season that has not finished at ``forecast_date``; fantasy
seasons end in December, so that is ``forecast_date.year``. ``h = k`` is ``k`` seasons on.

The unit. Points per game above the position's replacement rate, at every position, so a
quarterback's term and a tight end's term are the same kind of number and the assembler can
compare them without a per-position rule. Position scarcity lives entirely in the
replacement each producer subtracted, which is why that subtraction is declared per term set.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

UNIT = "season_points_above_replacement"
QUANTITY_UNITS: dict[str, str] = {
    "season_points": "season_points_above_replacement",
    "ppg_rate": "ppg_above_replacement",
}
BASIS_VALUE_ABOVE_REPLACEMENT = "value_above_obtainable_replacement"
BASIS_MARGINAL_LINEUP_GAIN = "marginal_lineup_gain"

EstimateClass = Literal["served", "candidate", "fixture"]
Coverage = Literal["full", "partial", "none"]
# The only future-replacement scenario anyone has evidence for today. A second literal is
# added here together with the sensitivity evidence that justifies it, never silently.
HorizonAssumption = Literal[
    "held_constant_from_snapshot",              # one rate, the bar player's today, reused at every h
    "same_player_from_snapshot_per_season",     # the bar player chosen today; HIS own season-h forecast at each h
]


# ── The typed target: what kind of number a term is ──────────────────────────
# Comparability is decided on these fields and nothing else. A sentence describing an
# event does not make two quantities the same kind of thing; a mismatch on any field does.
Scope = Literal["REG", "ALL_GAMES"]
Scoring = Literal["PPR_nflverse_weekly", "served_all_games_ppr", "PPR_nflverse_default"]
Exposure = Literal["stat_row_games", "all_games", "none", "stat_record_weeks_in_window"]
Event = Literal[
    "appearance",                       # A_j: appears in season j (games_j >= 1); points/games 0 when absent
    "qualifying_season_min_games",      # >= MIN_GAMES_THRESHOLD games in a season (availability.py)
    "two_season_window_qualifying",     # the served P: a qualifying season in t+1 OR t+2
    "bar_rank_reg_total",               # rank <= QB37/RB45/WR71/TE21 by REG-season PPR total
    "retention_ratio_bar_rank",         # ev_0 x R(h) from the DG-164 cells (cohort keyed on the bar-rank event)
]
Clock = Literal["per_season", "two_season_window", "ever"]
Quantity = Literal["season_points", "ppg_rate"]


# The week window the season total is summed over. David's league plays its championship in
# NFL Week 17 (ruled 2026-09-06); before 2021 the regular season had 17 weeks and the same
# league calendar ended in Week 16. "all_reg_weeks" is the full regular season the first
# producer files used — a different target, refused by mismatch, never rescaled.
Window = Literal["all_reg_weeks", "championship_week17"]

WINDOW_DESCRIPTIONS: dict[str, str] = {
    "all_reg_weeks": "points over every NFL regular-season week (18 weeks, 17 games since 2021); not David's fantasy weeks",
    "championship_week17": ("points through the championship week (NFL Week 17) since 2021 and through Week 16 for "
                            "seasons before 2021, with equal weekly weighting; the same convention on every historical season"),
}
SCORING_CAVEATS: dict[str, str] = {
    "PPR_nflverse_weekly": "nflverse weekly PPR points; not David's exact league scoring",
    "PPR_nflverse_default": ("nflverse default PPR points, a research preset named explicitly; not David's exact league "
                             "scoring — saved PPR does not establish equivalence for all-unit fumble losses, recovery "
                             "touchdowns or individual special-teams forced-fumble and recovery bonuses, so no exact-match "
                             "claim is made and an exact-league mode would refuse this attribution"),
}
# The explicit name of a (scoring, window) research target, quoted on the surface and bound
# by every producer manifest; never inferred from a description.
TARGET_IDS: dict[tuple[str, str], str] = {
    ("PPR_nflverse_weekly", "all_reg_weeks"): "nflverse_weekly_ppr_all_reg_weeks_v0",
    ("PPR_nflverse_default", "championship_week17"): "nflverse_default_ppr_championship_window_v1",
}


class TargetSpec(BaseModel):
    """The typed description of what a term measures. Every field is a closed set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scope: Scope
    scoring: Scoring
    window: Window = "all_reg_weeks"
    exposure: Exposure
    event: Event
    clock: Clock
    quantity: Quantity
    # The information vintage: the last NFL season whose labels were available to the
    # producer. Typed as a season, not a calendar day — a September 1 and a September 6
    # pre-season forecast hold the same information; labels through 2024 and 2025 do not.
    labels_through: int = Field(..., ge=1999)

    def mismatches(self, other: "TargetSpec") -> tuple[str, ...]:
        return tuple(f for f in ("scope", "scoring", "window", "exposure", "event", "clock", "quantity", "labels_through")
                     if getattr(self, f) != getattr(other, f))

    @property
    def unit(self) -> str:
        return QUANTITY_UNITS[self.quantity]

    @property
    def window_description(self) -> str:
        return WINDOW_DESCRIPTIONS[self.window]

    @property
    def scoring_caveat(self) -> str:
        return SCORING_CAVEATS.get(self.scoring, "not David's exact league scoring")

    @property
    def target_id(self) -> str:
        return TARGET_IDS.get((self.scoring, self.window), f"{self.scoring}:{self.window}")


def annual_target(forecast_date: date, window: Window = "all_reg_weeks") -> TargetSpec:
    """The annual target contract agreed with lanes 24974 (DG-165) and 23481 (DG-177) on
    2026-09-06: regular season, nflverse weekly PPR, stat-row exposure, the appearance
    event with points and games exactly 0 when absent, one season per term, season points.
    C_ij = max(0, E[points_ij] - R_j x E[games_ij]) is the season-level start/bench policy
    value; the weekly-optimal value is an upper bound that is not computed."""
    scoring: Scoring = "PPR_nflverse_default" if window == "championship_week17" else "PPR_nflverse_weekly"
    # DG-179 counts exposure as unique stat_record weeks INSIDE the window; the first files counted stat-row games.
    exposure: Exposure = "stat_record_weeks_in_window" if window == "championship_week17" else "stat_row_games"
    return TargetSpec(scope="REG", scoring=scoring, window=window, exposure=exposure,
                      event="appearance", clock="per_season", quantity="season_points",
                      labels_through=forecast_date.year - 1)


def season_for_horizon(forecast_date: date, h: int) -> int:
    """The calendar NFL season horizon ``h`` refers to, for a forecast made on this date.

    Fantasy seasons end in December, so at any date in year Y the season that has not
    finished is Y itself: a September forecast points at the season about to kick off, a
    March forecast at the one that starts that autumn, a January forecast at the coming
    season because the previous fantasy season is over.
    """
    if h < 0:
        raise ValueError(f"horizon must be >= 0, got {h}")
    return forecast_date.year + h


class HorizonTerm(BaseModel):
    """One season's unconditional expected value above replacement, typed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    h: int = Field(..., ge=0)
    season: int
    ev_above_replacement: float
    conditioning_event: str = Field(..., min_length=1)
    spec: TargetSpec
    # The season-long replace/retain counterfactual, when the producer states it: the SIGNED
    # expected margin over the actual available reference in the same scoring window, and the
    # ex-ante action its sign chose. ev_above_replacement is the positive part of the margin.
    expected_margin: Optional[float] = None
    action: Optional[Literal["retain", "replace"]] = None

    @property
    def unit(self) -> str:
        return self.spec.unit

    @field_validator("ev_above_replacement")
    @classmethod
    def _non_negative(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError(f"ev_above_replacement must be finite, got {value!r}: NaN compares false "
                             "against every bound and would pass a range check silently")
        if value < 0:
            raise ValueError(
                "ev_above_replacement must be >= 0: an unconditional expectation above "
                "replacement counts a non-contributing season as 0 (the replacement plays). "
                f"A negative value ({value}) means a conditional mean had the bar subtracted "
                "without the probability being applied."
            )
        return value


class ProducerRef(BaseModel):
    """Who produced the terms, and whether the number is served, a candidate, or a fixture.

    ``evidence_verified`` is True only when the producer's files carry affirmative identity:
    the manifest names the scoring arm and the sha256 of the file it describes, the grading
    file names the arm it graded, and they agree. Absence is not agreement: an unverified
    producer's values are inspectable but never evidence-qualified (readiness "unverified").
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    estimate_class: EstimateClass
    evidence_verified: bool = False
    evidence_note: Optional[str] = None


class ReplacementRef(BaseModel):
    """Which replacement was subtracted, and the scenario assumed for future seasons."""

    model_config = ConfigDict(frozen=True)

    position: str
    policy: str = Field(..., min_length=1)
    rate_ppg: float
    snapshot_id: str = Field(..., min_length=1)
    horizon_assumption: HorizonAssumption
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    band: int = Field(1, ge=1)
    # What ``rate_ppg`` measures. The available-player policy takes the bar player's SERVED
    # rate (P x E) so both sides of the subtraction are the same kind of number.
    rate_quantity: str = "served_rate"
    # The bar player's CONDITIONAL rate, E[ppg | plays]. The retention cells are keyed on
    # projection_2y / bar_ppg with both sides conditional (CANONICAL.md), so the margin key
    # needs this and must not be built from the served rate.
    conditional_rate_ppg: Optional[float] = None
    # Whether the pool the bar was chosen from covers every player who could be "the next
    # actually available" at this position. A producer that forecasts only rookies cannot
    # supply the league's next available veteran; a bar from such a pool is stated as
    # incomplete and no comparable value is built on it.
    pool_complete: bool = True
    pool_note: Optional[str] = None
    # Round 3: what the bar IS. It is the best among players WITH a forecast; eligible
    # unrostered players nobody forecast (no stat row, no draft pick, no id mapping) could
    # still be the next actually available, so the census count travels with the reference
    # and the copy never calls him the verified best nobody owns.
    reference_scope: str = "best among players with a forecast"
    unforecast_eligible: Optional[int] = None      # None: no eligible census supplied
    unforecast_reasons: Optional[dict[str, int]] = None
    census_complete: Optional[bool] = None         # False when eligible players are unforecast
    reference_nfl_status: Optional[str] = None     # Sleeper roster status of the bar player, when captured
    # The fixed same-available-player scenario, kept explicitly this cycle (Codex, 2026-09-06 evening),
    # with its sensitivity LOGGED: the runner-up who would have been the bar, both per-season
    # series, and the season-1 gap that decided the identity.
    reference_series: Optional[list[float]] = None
    runner_up: Optional[dict] = None
    sensitivity_note: Optional[str] = None
    horizon_note: str = ("Scenario: the same player who is available today is assumed to be the reference in "
                         "every future season; this is not a claim about future waiver access.")


class ServedReference(BaseModel):
    """The served number, carried untouched so a research estimate can never impersonate it."""

    model_config = ConfigDict(frozen=True)

    dynasty_value_score: Optional[float] = None
    dvs_engine: Optional[str] = None
    captured_at: Optional[str] = None


class TermSet(BaseModel):
    """Everything one producer says about one player."""

    model_config = ConfigDict(frozen=True)

    player_id: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)
    forecast_date: date
    producer: ProducerRef
    # May be absent ONLY on a coverage="none" term set: a position with no bar cannot be
    # composed, and the row must still come back with its reason rather than vanish.
    replacement_ref: Optional[ReplacementRef] = None
    terms: list[HorizonTerm] = Field(default_factory=list)
    coverage: Coverage
    reason: Optional[str] = None
    full_name: Optional[str] = None
    sleeper_id: Optional[str] = None
    served: Optional[ServedReference] = None

    @model_validator(mode="after")
    def _consistent(self) -> "TermSet":
        horizons = [t.h for t in self.terms]
        if horizons != sorted(set(horizons)):
            raise ValueError(
                f"horizon list must be strictly increasing with no duplicates, got {horizons}"
            )
        for t in self.terms:
            expected = season_for_horizon(self.forecast_date, t.h)
            if t.season != expected:
                raise ValueError(
                    f"term h={t.h} says season {t.season} but the clock for a "
                    f"{self.forecast_date} forecast puts h={t.h} in {expected}"
                )
        if self.coverage in ("none", "partial") and not (self.reason or "").strip():
            raise ValueError(f"coverage={self.coverage!r} requires a reason")
        if self.coverage == "none" and self.terms:
            raise ValueError("coverage='none' cannot carry terms")
        if self.replacement_ref is None:
            if self.coverage != "none":
                raise ValueError("a term set with coverage other than 'none' must name the replacement it subtracted")
        elif self.replacement_ref.position.upper() != self.position.upper():
            raise ValueError(
                f"replacement subtracted is for {self.replacement_ref.position}, "
                f"the player is a {self.position}"
            )
        return self


class Posture(BaseModel):
    """Time preference, declared. Never inferred from the roster."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(..., min_length=1)
    discount: float = Field(..., gt=0.0, le=1.0)


class RankedValue(BaseModel):
    """One focal value per player, with everything needed to say where it came from."""

    model_config = ConfigDict(frozen=True)

    player_id: str
    position: str
    full_name: Optional[str] = None
    sleeper_id: Optional[str] = None
    value: Optional[float]
    basis: Literal["value_above_obtainable_replacement"] = BASIS_VALUE_ABOVE_REPLACEMENT
    unit: Optional[str] = None
    coverage: Coverage
    # Scientific comparability against the board's typed target, decided on typed fields:
    #   comparable    every summed term's spec equals the board's AND the producer's evidence is verified
    #   unverified    typed as the board's target, but the producer's evidence identity could not be verified
    #   research_only full numerical coverage, but at least one term is a different kind of number
    #   incomplete    partial numerical coverage
    #   none          no forecast at all
    #   unclassified  no board was declared, so nothing can be called comparable
    readiness: Literal["comparable", "unverified", "research_only", "incomplete", "none", "unclassified"] = "unclassified"
    comparability_note: Optional[str] = None
    reason: Optional[str] = None
    posture: Posture
    producer: ProducerRef
    replacement_ref: Optional[ReplacementRef]
    horizons_used: int
    forecast_date: date
    served: Optional[ServedReference] = None
    conditioning_events: tuple[str, ...] = ()
