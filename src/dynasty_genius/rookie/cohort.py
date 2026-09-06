"""The draft-capital cohort: one row per drafted QB/RB/WR/TE, from nflverse draft picks,
with every prospect's NFL identity resolved or explicitly marked unresolved.

Why nflverse and not ``prospects_with_outcomes_v3.csv``: that table starts at the 2015
class and carries no 2026 class. nflverse draft picks run 1980-2026 with ``gsis_id`` and age
at draft populated for 95% of skill-position picks since 1999, which gives twenty-plus
complete classes at h=5 and the eighty 2026 rookies on David's board.

THE ID GAP, and what it does and does not prove. 108 skill-position picks (1999-2025) carry
no ``gsis_id``, and PFR's career ``games`` field is NaN for all but one of them. NaN is a
missing record, not a measured zero (round-1 review, item 2): the previous build turned it
into "never played", which is an inference the field cannot support. Resolution now runs
through independent sources, in order, each step keyed tightly enough that a hit is an
identity and not a namesake:

    1. nflverse players table by (draft_year, draft_pick)
    2. nflverse players table by normalised name AND draft/rookie season in {c, c+1}
    3. nflverse 1999-2025 seasonal rosters by (entry_year, draft_number)
    4. nflverse rosters by normalised name AND entry/rookie year in {c, c+1}
    5. otherwise UNRESOLVED

Measured 2026-09-06: 64 of the 108 resolve (4 / 55 / 4 / 1), one of whom has stat rows;
44 have no NFL identity in any source. A resolved identity with no weekly stat row scored
zero fantasy points — a measured fact — and labels 0. An unresolved prospect is KEPT with
``label_basis = "unresolved"`` and NaN labels: counted, never dropped, never asserted to
have failed. ``unresolved_as_zero`` in the labels is the explicit sensitivity arm.

Undrafted players are NOT in this cohort; there is no undrafted-prospect population table
in the product, and their coverage is reported separately, never invented.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd

__all__ = [
    "SKILL_POSITIONS",
    "draft_cohort_from_picks",
    "load_draft_picks",
    "load_players",
    "load_rosters",
    "resolve_missing_ids",
]

SKILL_POSITIONS: tuple[str, ...] = ("QB", "RB", "WR", "TE")

COHORT_COLUMNS: tuple[str, ...] = (
    "gsis_id", "draft_season", "position", "pick", "round", "age_at_draft", "team", "name",
    "label_basis",
)

BASIS_GSIS = "nflverse_gsis"
BASIS_UNRESOLVED = "unresolved"


def load_draft_picks() -> pd.DataFrame:
    """Network read of the nflverse draft-pick table (immutable upstream, memory-cached)."""
    import nflreadpy as nfl  # imported lazily so tests never need the network client

    return nfl.load_draft_picks().to_pandas()


def load_players() -> pd.DataFrame:
    import nflreadpy as nfl

    return nfl.load_players().to_pandas()


def load_rosters(seasons: Iterable[int]) -> pd.DataFrame:
    import nflreadpy as nfl

    return nfl.load_rosters(sorted(set(int(s) for s in seasons))).to_pandas()


def _norm(name) -> str:
    return re.sub(r"[^a-z]", "", str(name).lower())


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def resolve_missing_ids(
    picks: pd.DataFrame,
    *,
    players: pd.DataFrame,
    rosters: pd.DataFrame,
) -> pd.DataFrame:
    """For pick rows without a gsis_id, return ``gsis_id`` and ``label_basis`` per row.

    ``picks`` rows need ``season, pick, pfr_player_name``. ``players`` needs ``gsis_id,
    display_name, draft_year, draft_pick, rookie_season``; ``rosters`` needs ``gsis_id,
    full_name, entry_year, rookie_year, draft_number``. A step counts as a hit only when it
    identifies exactly one gsis_id.
    """
    pl = players.copy()
    pl["_n"] = pl["display_name"].map(_norm)
    pl["_dy"] = _num(pl["draft_year"]) if "draft_year" in pl else np.nan
    pl["_dp"] = _num(pl["draft_pick"]) if "draft_pick" in pl else np.nan
    pl["_rs"] = _num(pl["rookie_season"]) if "rookie_season" in pl else np.nan
    ro = rosters.copy()
    ro["_n"] = ro["full_name"].map(_norm)
    ro["_ey"] = _num(ro["entry_year"]) if "entry_year" in ro else np.nan
    ro["_ry"] = _num(ro["rookie_year"]) if "rookie_year" in ro else np.nan
    ro["_dn"] = _num(ro["draft_number"]) if "draft_number" in ro else np.nan

    out = []
    for idx, row in picks.iterrows():
        c, k, n = int(row["season"]), int(row["pick"]), _norm(row["pfr_player_name"])
        gsis, basis = None, BASIS_UNRESOLVED
        hit = pl.loc[(pl["_dy"] == c) & (pl["_dp"] == k), "gsis_id"].dropna().unique()
        if len(hit) == 1:
            gsis, basis = hit[0], "players:draft_year+pick"
        else:
            hit = pl.loc[(pl["_n"] == n) & ((pl["_dy"] == c) | pl["_rs"].isin([c, c + 1])), "gsis_id"].dropna().unique()
            if len(hit) == 1:
                gsis, basis = hit[0], "players:name+year"
            else:
                hit = ro.loc[(ro["_ey"] == c) & (ro["_dn"] == k), "gsis_id"].dropna().unique()
                if len(hit) == 1:
                    gsis, basis = hit[0], "rosters:entry_year+draft_number"
                else:
                    hit = ro.loc[(ro["_n"] == n) & (ro["_ey"].isin([c, c + 1]) | ro["_ry"].isin([c, c + 1])), "gsis_id"].dropna().unique()
                    if len(hit) == 1:
                        gsis, basis = hit[0], "rosters:name+year"
        out.append({"index": idx, "gsis_id": gsis, "label_basis": basis})
    return pd.DataFrame(out).set_index("index")


def draft_cohort_from_picks(
    picks: pd.DataFrame,
    *,
    seasons: Iterable[int],
    positions: Iterable[str] = SKILL_POSITIONS,
    players: pd.DataFrame | None = None,
    rosters: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Reduce a draft-pick table to the cohort frame and a coverage report.

    Every skill-position pick in ``seasons`` is a row. Rows with a gsis_id carry
    ``label_basis = "nflverse_gsis"``; rows without one are resolved through ``players``
    and ``rosters`` when given, else marked unresolved. Unresolved rows get a synthetic
    ``gsis_id`` (``unresolved:<season>:<pick>``) so they stay addressable and countable.
    """
    seasons = sorted(set(int(s) for s in seasons))
    positions = tuple(positions)
    frame = picks.loc[picks["season"].isin(seasons) & picks["position"].isin(positions)].copy()
    skill_rows = int(len(frame))

    has_id = frame["gsis_id"].notna() & (frame["gsis_id"].astype(str).str.strip() != "")
    gsis = pd.Series(
        [str(v).strip() if ok else None for v, ok in zip(frame["gsis_id"], has_id)],
        index=frame.index, dtype=object,
    )
    basis = pd.Series(np.where(has_id, BASIS_GSIS, BASIS_UNRESOLVED), index=frame.index, dtype=object)
    resolution_counts: dict[str, int] = {}
    missing = frame.loc[~has_id]
    if len(missing) and players is not None and rosters is not None:
        resolved = resolve_missing_ids(missing, players=players, rosters=rosters)
        for idx, r in resolved.iterrows():
            basis.loc[idx] = r["label_basis"]
            if pd.notna(r["gsis_id"]):
                gsis.loc[idx] = str(r["gsis_id"])
        resolution_counts = resolved["label_basis"].value_counts().to_dict()
    elif len(missing):
        resolution_counts = {BASIS_UNRESOLVED: int(len(missing))}
    synthetic = "unresolved:" + frame["season"].astype(int).astype(str) + ":" + frame["pick"].astype(int).astype(str)
    gsis = pd.Series([g if pd.notna(g) else s for g, s in zip(gsis, synthetic)], index=frame.index, dtype=object)

    cohort = pd.DataFrame(
        {
            "gsis_id": gsis.to_numpy(),
            "draft_season": frame["season"].astype(int).to_numpy(),
            "position": frame["position"].astype(str).to_numpy(),
            "pick": frame["pick"].astype(int).to_numpy(),
            "round": frame["round"].astype(int).to_numpy(),
            "age_at_draft": pd.to_numeric(frame["age"], errors="coerce").to_numpy(),
            "team": frame["team"].astype(str).to_numpy() if "team" in frame else "",
            "name": frame["pfr_player_name"].astype(str).to_numpy() if "pfr_player_name" in frame else "",
            "label_basis": basis.to_numpy(),
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
        "with_gsis_id": int(has_id.sum()),
        "without_gsis_id": int((~has_id).sum()),
        "resolution_of_missing_ids": {str(k): int(v) for k, v in resolution_counts.items()},
        "unresolved_kept_with_nan_labels": int((cohort["label_basis"] == BASIS_UNRESOLVED).sum()),
        "duplicate_gsis_dropped": duplicates,
        "missing_age": int(cohort["age_at_draft"].isna().sum()),
        "rows": int(len(cohort)),
    }
    return cohort[list(COHORT_COLUMNS)], report
