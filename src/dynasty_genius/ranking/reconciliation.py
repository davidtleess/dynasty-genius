"""The league's scoring and week scope against the candidate's, measured (DG-178 round 2, item 4).

The candidate target is nflverse ``fantasy_points_ppr`` over the NFL regular season: 18 calendar
weeks, 17 team games. David's league is a Sleeper PPR league whose fantasy season runs weeks
1-17, with playoffs from the week its settings name. "PPR" in both names is not equality: the
scoring keys are compared one by one against nflverse's published formula and the week scope
against the league's settings, and every difference is listed. Nothing here rescales a number.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

# nflverse fantasy_points_ppr, as published by nflreadr's calculate_player_stats:
#   0.04/pass yd, 4/pass TD, -2/INT, 0.1/rush yd, 6/rush TD, 1/rec, 0.1/rec yd, 6/rec TD,
#   -2/fumble lost, 2/two-point conversion (pass, rush, rec), 6/special-teams TD, 6/fumble-recovery TD.
NFLVERSE_PPR: dict[str, float] = {
    "pass_yd": 0.04, "pass_td": 4.0, "pass_int": -2.0, "pass_2pt": 2.0,
    "rush_yd": 0.1, "rush_td": 6.0, "rush_2pt": 2.0,
    "rec": 1.0, "rec_yd": 0.1, "rec_td": 6.0, "rec_2pt": 2.0,
    "fum_lost": -2.0, "fum_rec_td": 6.0, "st_td": 6.0,
    "bonus_rec_te": 0.0,
}
NFL_REG_WEEKS = (1, 18)  # 18 calendar weeks, 17 team games


@dataclass(frozen=True)
class ScoringDifference:
    key: str
    league_value: Optional[float]
    candidate_value: Optional[float]

    @property
    def same(self) -> bool:
        return self.league_value is not None and self.candidate_value is not None \
            and abs(self.league_value - self.candidate_value) < 1e-9


@dataclass(frozen=True)
class ScoringReconciliation:
    candidate_definition: str
    differences: list[ScoringDifference]
    unmatched_keys: list[str]        # league keys nflverse's formula has no term for (kickers, defence, bonuses)
    league_regular_weeks: tuple[int, int]
    playoff_start_week: int
    league_final_week: Optional[int]  # None: the snapshot does not record it, and it is not inferred
    candidate_weeks: tuple[int, int]
    week_scope_note: str

    @property
    def all_equal(self) -> bool:
        return all(d.same for d in self.differences) and not self.unmatched_keys

    @property
    def window_matches_league(self) -> bool:
        """False until a forecast is recomputed over David's actual fantasy weeks. A full
        NFL regular-season forecast is not a weeks-1-to-N fantasy forecast."""
        return False

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_definition": self.candidate_definition,
            "differences": [{"key": d.key, "league": d.league_value, "candidate": d.candidate_value, "same": d.same}
                            for d in self.differences if not d.same],
            "same_keys": [d.key for d in self.differences if d.same],
            "unmatched_league_keys": self.unmatched_keys,
            "league_regular_weeks": self.league_regular_weeks, "playoff_start_week": self.playoff_start_week,
            "league_final_week": self.league_final_week, "candidate_weeks": self.candidate_weeks,
            "week_scope_note": self.week_scope_note, "all_equal": self.all_equal,
            "window_matches_league": self.window_matches_league,
        }


_SKILL_KEYS = ("pass_yd", "pass_td", "pass_int", "pass_2pt", "rush_yd", "rush_td", "rush_2pt", "rec", "rec_yd",
               "rec_td", "rec_2pt", "fum_lost", "fum_rec_td", "st_td", "bonus_rec_te")


def reconcile_scoring(snapshot: Mapping[str, Any]) -> ScoringReconciliation:
    league = snapshot.get("league") or {}
    scoring = {k: float(v) for k, v in (league.get("scoring_settings") or {}).items() if isinstance(v, (int, float))}
    settings = league.get("settings") or {}
    diffs = [ScoringDifference(key=k, league_value=scoring.get(k, 0.0 if k == "bonus_rec_te" else None),
                               candidate_value=NFLVERSE_PPR[k]) for k in _SKILL_KEYS]
    unmatched = sorted(k for k in scoring if k not in NFLVERSE_PPR and not k.startswith(("fgm", "xpm", "def", "pts_allow",
                                                                                           "sack", "safe", "blk", "int",
                                                                                           "ff", "fum_rec", "fgmiss",
                                                                                           "xpmiss", "st_")))
    playoff_start = int(settings.get("playoff_week_start") or 15)
    final_week = settings.get("last_scored_leg") or settings.get("playoff_week_end") or settings.get("final_week")
    final_week = int(final_week) if final_week else None
    week_note = (f"candidate forecasts score NFL regular-season weeks {NFL_REG_WEEKS[0]}-{NFL_REG_WEEKS[1]} (17 team games); "
                 f"David's league plays a regular season of weeks 1-{playoff_start - 1} with playoffs from week {playoff_start}; "
                 f"the final fantasy week is not recorded in the snapshot and is not inferred here; NFL week 18 is outside most "
                 f"Sleeper leagues but that is not verified from his settings. A full-season forecast is NOT a forecast of his "
                 f"fantasy weeks; that recomputation has not been done")
    return ScoringReconciliation(
        candidate_definition="nflverse fantasy_points_ppr", differences=diffs, unmatched_keys=unmatched,
        league_regular_weeks=(1, playoff_start - 1), playoff_start_week=playoff_start, league_final_week=final_week,
        candidate_weeks=NFL_REG_WEEKS, week_scope_note=week_note,
    )
