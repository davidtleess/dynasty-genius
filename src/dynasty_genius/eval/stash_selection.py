"""DG-177 stash-selection evaluation: can the frozen future-production ordering find later contributors
among low-production developmental candidates? Frozen inputs only; definitions frozen before any result."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


class StashSelectionError(ValueError):
    """A definitions, source or chronology condition under which the evaluator refuses."""


DEFINITIONS_VERSION = "stash_selection_definitions_v1"
REQUIRED_DEFINITION_KEYS = ("version", "frozen_before_first_result", "origins", "low_production", "developmental",
                            "outcome", "orderings", "metrics", "claims_not_made")


def load_definitions(path: Path) -> dict:
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    missing = [k for k in REQUIRED_DEFINITION_KEYS if k not in d]
    if missing:
        raise StashSelectionError(f"definitions file lacks {missing}")
    if d.get("version") != DEFINITIONS_VERSION or d.get("frozen_before_first_result") is not True:
        raise StashSelectionError("definitions must be the frozen v1 file")
    d["_file"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return d


# ── starter lines and candidates (origin-available evidence only) ────────────────────────────

OFFENSIVE_POSITIONS = ("QB", "RB", "WR", "TE")
LABEL_ARTIFACT = "artifact_row"
LABEL_NO_RECORD = "no_record_zero"


def _window_points(frame: pd.DataFrame, outcomes: pd.DataFrame, season_col: str) -> tuple[pd.Series, pd.Series]:
    """Realized DG-179 window points for (player_id, season_col) with the label source; an
    identified player-season with no artifact row is zero under the artifact's own convention."""
    o = outcomes[["player_id", "season", "points", "games", "appeared"]].drop_duplicates(["player_id", "season"])
    m = frame[["player_id", season_col]].merge(o, left_on=["player_id", season_col], right_on=["player_id", "season"], how="left")
    present = m["points"].notna()
    points = pd.to_numeric(m["points"], errors="coerce").fillna(0.0).to_numpy()
    label = np.where(present, LABEL_ARTIFACT, LABEL_NO_RECORD)
    return pd.Series(points, index=frame.index), pd.Series(label, index=frame.index)


def starter_lines(cohort: pd.DataFrame, outcomes: pd.DataFrame, *, slots: dict, multiplier: float = 1.0) -> pd.DataFrame:
    """The N-th highest realized window points among the season's cohort rows of a position,
    N = round(slots × multiplier). A cell with fewer rows than N has line 0 and is disclosed."""
    c = cohort[cohort["position"].isin(slots)].copy()
    c["points"], _ = _window_points(c, outcomes, "feature_season")
    rows = []
    for (pos, season), g in c.groupby(["position", "feature_season"]):
        n = max(1, int(round(slots[pos] * multiplier)))
        pts = np.sort(g["points"].to_numpy())[::-1]
        short = len(pts) < n
        rows.append({"position": pos, "season": int(season), "slots": n, "rows_in_cell": int(len(pts)),
                     "line_points": 0.0 if short else float(pts[n - 1]), "short_cell": bool(short)})
    return pd.DataFrame(rows, columns=["position", "season", "slots", "rows_in_cell", "line_points", "short_cell"])


def candidates(cohort: pd.DataFrame, outcomes: pd.DataFrame, draft: pd.DataFrame, *, definitions: dict, slots: dict | None = None,
               slot_multiplier: float = 1.0, max_observed_history_seasons: int | None = 3) -> pd.DataFrame:
    """One row per (player_id, origin) that is low-production at the origin (DG-179 window points below
    the starter line) and inside the observed-history stratum. Only evidence dated at or before the
    origin is read: origin production, observed seasons, and draft facts with draft season <= origin."""
    lo, hi = definitions["origins"]["feature_seasons"]
    slots = slots or definitions["low_production"]["starter_slots"]
    c = cohort.copy()
    c["feature_season"] = pd.to_numeric(c["feature_season"], errors="coerce")
    outside = c[(c["feature_season"] < lo) | (c["feature_season"] > hi)]
    if len(outside):
        raise StashSelectionError(f"{len(outside)} cohort rows carry an origin outside the frozen range {lo}-{hi}")
    c = c[c["position"].isin(OFFENSIVE_POSITIONS) & c["position"].isin(slots)].copy()
    c["origin"] = c["feature_season"].astype(int)
    c["origin_points"], c["origin_label_source"] = _window_points(c, outcomes, "feature_season")
    lines = starter_lines(c, outcomes, slots=slots, multiplier=slot_multiplier)
    c = c.merge(lines[["position", "season", "line_points", "short_cell"]].rename(columns={"season": "origin", "line_points": "origin_line",
                                                                                          "short_cell": "origin_short_cell"}),
                on=["position", "origin"], how="left")
    c["observed_history_seasons"] = pd.to_numeric(c["seasons_played"], errors="coerce")
    d = draft.dropna(subset=["gsis_id"]).copy() if len(draft) else pd.DataFrame(columns=["gsis_id", "season", "round", "pick"])
    d = d.sort_values(["gsis_id", "season"]).drop_duplicates("gsis_id", keep="first")
    d = d.rename(columns={"gsis_id": "player_id", "season": "draft_season", "round": "draft_round", "pick": "draft_pick"})
    c = c.merge(d[["player_id", "draft_season", "draft_round", "draft_pick"]], on="player_id", how="left")
    visible = c["draft_season"].notna() & (c["draft_season"] <= c["origin"])
    c["draft_visible"] = visible
    for col in ("draft_season", "draft_round", "draft_pick"):
        c[col] = c[col].where(visible)
    c["nfl_years_since_draft"] = (c["origin"] - c["draft_season"] + 1).where(visible)
    low = c["origin_points"] < c["origin_line"]
    stratum = (c["observed_history_seasons"] <= max_observed_history_seasons) if max_observed_history_seasons is not None else True
    keep = c[low & stratum & c["observed_history_seasons"].notna()]
    cols = ["player_id", "origin", "position", "origin_points", "origin_label_source", "origin_line", "origin_short_cell",
            "total_points_t", "ppg_t", "games_t", "age", "observed_history_seasons", "draft_visible", "draft_season", "draft_round",
            "draft_pick", "nfl_years_since_draft"]
    return keep[cols].sort_values(["origin", "position", "player_id"]).reset_index(drop=True)
