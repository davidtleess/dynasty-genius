"""Grain-uniqueness and era probe for the six streams. Read-only."""

from __future__ import annotations

import json

import nflreadpy as nr
import polars as pl

SEASONS = [2023, 2024, 2025]


def dupes(frame: pl.DataFrame, keys: list[str]) -> dict:
    missing = [k for k in keys if k not in frame.columns]
    if missing:
        return {"keys": keys, "error": f"absent columns: {missing}"}
    g = frame.group_by(keys).len()
    dup = g.filter(pl.col("len") > 1)
    return {
        "keys": keys,
        "groups": g.height,
        "dup_groups": dup.height,
        "max_group": int(g["len"].max()) if g.height else 0,
        "null_in_key": {k: int(frame[k].is_null().sum()) for k in keys},
    }


out: dict = {}

# --- contracts -------------------------------------------------------------
c = nr.load_contracts()
out["contracts"] = {
    "rows": c.height,
    "candidates": [
        dupes(c, ["otc_id"]),
        dupes(c, ["otc_id", "year_signed"]),
        dupes(c, ["otc_id", "year_signed", "team", "value"]),
        dupes(c, ["otc_id", "year_signed", "team", "years", "value", "apy"]),
    ],
    "cols_col_dtype": str(c["cols"].dtype),
    "is_active_values": c["is_active"].value_counts().to_dicts(),
}

# --- depth charts: era split ----------------------------------------------
d = nr.load_depth_charts(seasons=SEASONS)
new_era = d.filter(pl.col("season").is_null())
old_era = d.filter(pl.col("season").is_not_null())
out["depth_charts"] = {
    "rows": d.height,
    "era_null_season_rows": new_era.height,
    "era_with_season_rows": old_era.height,
    "old_era_nonnull_cols": [c for c in old_era.columns if old_era[c].is_not_null().any()],
    "new_era_nonnull_cols": [c for c in new_era.columns if new_era[c].is_not_null().any()],
    "old_grain": dupes(old_era, ["season", "week", "club_code", "gsis_id", "depth_position"]),
    "new_grain_probe": dupes(new_era, ["gsis_id"]),
}

# --- ff_opportunity --------------------------------------------------------
o = nr.load_ff_opportunity(seasons=SEASONS)
out["ff_opportunity"] = {
    "rows": o.height,
    "grain": dupes(o, ["season", "week", "player_id"]),
    "null_player_id_rows": int(o["player_id"].is_null().sum()),
    "posteam_when_null": (
        o.filter(pl.col("player_id").is_null()).head(2).to_dicts()[:2] if o["player_id"].is_null().any() else None
    ),
}

# --- ff_rankings -----------------------------------------------------------
r = nr.load_ff_rankings()
out["ff_rankings"] = {
    "rows": r.height,
    "ecr_type_values": r["ecr_type"].value_counts().to_dicts(),
    "page_type_values": r["page_type"].value_counts().to_dicts(),
    "scrape_date_distinct": r["scrape_date"].unique().to_list()[:10],
    "grain": dupes(r, ["ecr_type", "page_type", "id"]),
}

# --- pfr_advstats: how many stat types -------------------------------------
pfr: dict = {}
for st in ("pass", "rush", "rec", "def"):
    try:
        f = nr.load_pfr_advstats(seasons=SEASONS, stat_type=st)
        pfr[st] = {
            "rows": f.height,
            "n_cols": f.width,
            "columns": list(f.columns),
            "grain": dupes(f, ["season", "week", "team", "pfr_player_id"]),
        }
    except Exception as exc:  # noqa: BLE001
        pfr[st] = {"error": f"{type(exc).__name__}: {exc}"}
out["pfr_advstats"] = pfr

# --- ftn charting ----------------------------------------------------------
f = nr.load_ftn_charting(seasons=SEASONS)
out["ftn_charting"] = {
    "rows": f.height,
    "grain": dupes(f, ["nflverse_game_id", "nflverse_play_id"]),
    "alt_grain": dupes(f, ["ftn_game_id", "ftn_play_id"]),
}

print(json.dumps(out, indent=2, default=str))
