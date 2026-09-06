"""The draft-capital cohort: one row per drafted QB/RB/WR/TE, from nflverse draft picks.

Why nflverse and not ``prospects_with_outcomes_v3.csv``: that table starts at the 2015
class and carries no 2026 class, so a five-season horizon has six complete classes to learn
from and nothing to score. nflverse draft picks run 1980-2026 with ``gsis_id`` and age at
draft populated for 95% of skill-position picks since 1999 (measured 2026-09-06), which
gives twenty-plus complete classes at h=5 and the eighty 2026 rookies on David's board.

THE ID GAP IS NOT RANDOM. Measured 2026-09-06 on the 1999-2025 skill picks: 108 rows have
no ``gsis_id``, and 107 of them have ZERO career games in PFR. A gsis id is assigned when a
player reaches an NFL roster system; the ones who never did never got one. Dropping the
id-less rows therefore deletes washouts — the survivorship landmine of the feasibility
gate, in a third costume — and it bit hardest in 1999-2004, where the kept rows showed a
0.5% washout rate against 6-10% later. So:

* no id AND zero career games → KEPT under a synthetic id ``nogsis:<season>:<pick>``. He has
  no panel rows, so every observable horizon labels 0, which is the truth.
* no id AND career games > 0 → cannot be joined to any outcome, dropped, and COUNTED
  (one row in the 1999-2025 sample).

Undrafted players are NOT in this cohort. There is no undrafted-prospect population table
anywhere in the product; their coverage is reported separately, never invented.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

__all__ = ["SKILL_POSITIONS", "draft_cohort_from_picks", "load_draft_picks"]

SKILL_POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE")

COHORT_COLUMNS: tuple[str, ...] = (
    "gsis_id", "draft_season", "position", "pick", "round", "age_at_draft", "team", "name",
    "id_status",
)

ID_STATUS_GSIS = "gsis"
ID_STATUS_NO_GSIS_NEVER_PLAYED = "no_gsis_never_played"


def load_draft_picks() -> pd.DataFrame:
    """Network read of the nflverse draft-pick table (immutable upstream, memory-cached)."""
    import nflreadpy as nfl  # imported lazily so tests never need the network client

    return nfl.load_draft_picks().to_pandas()


def draft_cohort_from_picks(
    picks: pd.DataFrame,
    *,
    seasons: Iterable[int],
    positions: Iterable[str] = SKILL_POSITIONS,
) -> tuple[pd.DataFrame, dict[str, int | list[int]]]:
    """Reduce a draft-pick table to the cohort frame and a coverage report.

    ``picks`` needs ``season, round, pick, position, gsis_id, age`` and PFR's career
    ``games`` (used only to decide whether an id-less pick is a washout or unlabelable).
    Missing age is kept (a feature, imputed at fit time) and counted.
    """
    seasons = sorted(set(int(s) for s in seasons))
    positions = tuple(positions)
    frame = picks.loc[picks["season"].isin(seasons) & picks["position"].isin(positions)].copy()
    skill_rows = int(len(frame))

    has_id = frame["gsis_id"].notna() & (frame["gsis_id"].astype(str).str.strip() != "")
    career_games = pd.to_numeric(frame["games"], errors="coerce").fillna(0) if "games" in frame else pd.Series(0, index=frame.index)
    never_played = career_games <= 0
    keep_as_washout = ~has_id & never_played
    drop_unlabelable = ~has_id & ~never_played

    frame = frame.loc[has_id | keep_as_washout]
    synthetic = "nogsis:" + frame["season"].astype(int).astype(str) + ":" + frame["pick"].astype(int).astype(str)
    gsis = np.where(has_id.loc[frame.index], frame["gsis_id"].astype(str).str.strip(), synthetic)
    status = np.where(has_id.loc[frame.index], ID_STATUS_GSIS, ID_STATUS_NO_GSIS_NEVER_PLAYED)

    cohort = pd.DataFrame(
        {
            "gsis_id": gsis,
            "draft_season": frame["season"].astype(int).to_numpy(),
            "position": frame["position"].astype(str).to_numpy(),
            "pick": frame["pick"].astype(int).to_numpy(),
            "round": frame["round"].astype(int).to_numpy(),
            "age_at_draft": pd.to_numeric(frame["age"], errors="coerce").to_numpy(),
            "team": frame["team"].astype(str).to_numpy() if "team" in frame else "",
            "name": frame["pfr_player_name"].astype(str).to_numpy() if "pfr_player_name" in frame else "",
            "id_status": status,
        }
    )
    duplicates = int(cohort["gsis_id"].duplicated().sum())
    cohort = (
        cohort.sort_values(["draft_season", "pick"])
        .drop_duplicates("gsis_id", keep="first")
        .reset_index(drop=True)
    )
    report = {
        "seasons": seasons,
        "skill_rows": skill_rows,
        "no_gsis_kept_as_washout": int(keep_as_washout.sum()),
        "no_gsis_played_dropped_unlabelable": int(drop_unlabelable.sum()),
        "duplicate_gsis_dropped": duplicates,
        "missing_age": int(cohort["age_at_draft"].isna().sum()),
        "rows": int(len(cohort)),
    }
    return cohort[list(COHORT_COLUMNS)], report
