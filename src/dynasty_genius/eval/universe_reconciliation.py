"""Round 2, item 6 — reconcile the eligible fantasy universe with the forecast cohort.

For every row of the ranking lane's eligible universe: a forecast when the basic cohort
holds a row for the inference season (a whole missed season after an active one IS a
row, with zero games), otherwise one precise reason. Nothing here invents a feature
row and nothing is written as zero.

Statuses:
  forecast                          in the inference cohort
  identity_conflict                 the universe's gsis id and the id map's disagree
  no_gsis_mapping                   no gsis id on the row and none in the id map
  no_nfl_history                    gsis known, never a weekly stat line in the source
  left_cohort_two_absent_seasons    history exists but the last appearance is two or more
                                    seasons before the inference season
  position_outside_modelled_set     a cohort row exists but its stat-line position is not one
                                    the forecast models (e.g. a two-way player listed DB)
  not_in_cohort_other               history and mapping exist but no cohort row (reported)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REASONS = (
    "forecast", "identity_conflict", "no_gsis_mapping", "no_nfl_history",
    "left_cohort_two_absent_seasons", "position_outside_modelled_set", "not_in_cohort_other",
)


def _clean_id(value) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    s = str(value).strip()
    return s or None


def reconcile_universe(
    universe: pd.DataFrame,
    idmap: pd.DataFrame,
    cohort_inference: pd.DataFrame,
    history: pd.DataFrame,
    *,
    inference_season: int,
    cohort_positions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """``cohort_positions`` (player_id, feature_season, position) is the UNFILTERED cohort's
    position map, so a player dropped by the modelled-position filter gets that reason."""
    positions_by_gsis: dict[str, str] = {}
    if cohort_positions is not None:
        cp = cohort_positions[cohort_positions["feature_season"].astype(int) == int(inference_season)]
        positions_by_gsis = {str(p): str(x) for p, x in zip(cp["player_id"], cp["position"])}
    idmap = idmap.copy()
    idmap["sleeper_key"] = pd.to_numeric(idmap["sleeper_id"], errors="coerce")
    idmap = idmap[idmap["sleeper_key"].notna() & idmap["gsis_id"].notna()]
    map_by_sleeper = {int(k): str(g) for k, g in zip(idmap["sleeper_key"], idmap["gsis_id"])}
    cohort = cohort_inference[cohort_inference["feature_season"].astype(int) == int(inference_season)]
    games_by_gsis = {str(p): int(g) for p, g in zip(cohort["player_id"], cohort["games_t"])}
    last_seen = {str(p): int(s) for p, s in zip(history["player_id"], history["last_season_seen"])}

    rows = []
    for rec in universe.to_dict("records"):
        sleeper = _clean_id(rec.get("sleeper_id"))
        key = int(float(sleeper)) if sleeper is not None and sleeper.replace(".", "", 1).isdigit() else None
        g_universe = _clean_id(rec.get("gsis_id"))
        g_map = map_by_sleeper.get(key) if key is not None else None
        gsis = g_universe or g_map
        status: str
        if g_universe and g_map and g_universe != g_map:
            status = "identity_conflict"
        elif gsis is None:
            status = "no_gsis_mapping"
        elif gsis in games_by_gsis:
            status = "forecast"
        elif gsis not in last_seen:
            status = "no_nfl_history"
        elif last_seen[gsis] <= int(inference_season) - 2:
            status = "left_cohort_two_absent_seasons"
        elif gsis in positions_by_gsis:
            status = "position_outside_modelled_set"
        else:
            status = "not_in_cohort_other"
        rows.append({
            "sleeper_id": sleeper, "name": rec.get("name"), "position": rec.get("position"),
            "rostered": rec.get("rostered"), "gsis_id_universe": g_universe, "gsis_id_idmap": g_map,
            "gsis_id": gsis if status != "identity_conflict" else None,
            "status": status,
            "last_season_seen": last_seen.get(gsis) if gsis else None,
            "cohort_position": positions_by_gsis.get(gsis) if gsis else None,
            f"games_{inference_season}": games_by_gsis.get(gsis) if gsis else None,
        })
    return pd.DataFrame(rows)
