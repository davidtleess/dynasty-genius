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


def starter_lines(cohort: pd.DataFrame, outcomes: pd.DataFrame, *, slots: dict, multiplier: float = 1.0,
                  deep_slots: dict | None = None) -> pd.DataFrame:
    """The N-th highest realized window points among the season's cohort rows of a position,
    N = round(slots × multiplier). A cell with fewer rows than N has line 0 and is disclosed.
    `deep_slots` (DG-165's deep-roster relevance counts, not a starting cutoff) gives a second,
    separately named line."""
    c = cohort[cohort["position"].isin(slots)].copy()
    c["points"], _ = _window_points(c, outcomes, "feature_season")
    rows = []
    for (pos, season), g in c.groupby(["position", "feature_season"]):
        n = max(1, int(round(slots[pos] * multiplier)))
        pts = np.sort(g["points"].to_numpy())[::-1]
        short = len(pts) < n
        deep = np.nan
        if deep_slots is not None and pos in deep_slots:
            dn = int(deep_slots[pos])
            deep = 0.0 if len(pts) < dn else float(pts[dn - 1])
        rows.append({"position": pos, "season": int(season), "slots": n, "rows_in_cell": int(len(pts)),
                     "line_points": 0.0 if short else float(pts[n - 1]), "short_cell": bool(short), "deep_line_points": deep})
    return pd.DataFrame(rows, columns=["position", "season", "slots", "rows_in_cell", "line_points", "short_cell", "deep_line_points"])


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


# ── closed outcomes with label sources ───────────────────────────────────────────────────────

def attach_outcomes(cands: pd.DataFrame, outcomes: pd.DataFrame, lines: pd.DataFrame, *, horizons=(1, 2, 3),
                    last_complete_season: int = 2025, absolute_line: float = 100.0) -> pd.DataFrame:
    """One row per (player_id, origin, horizon) with the realized DG-179 window points of the target
    season and the contributor flags. Target seasons after the last complete season are dropped and
    counted (`.attrs["censored_dropped"]`), never zero. A target season without a starter line refuses."""
    frames = []
    censored = 0
    for j in horizons:
        r = cands[["player_id", "origin", "position"]].copy()
        r["horizon"] = int(j)
        r["target_season"] = r["origin"] + int(j)
        open_rows = r["target_season"] > last_complete_season
        censored += int(open_rows.sum())
        r = r[~open_rows]
        if not len(r):
            continue
        pts, label = _window_points(r, outcomes, "target_season")
        r["realized_points"], r["label_source"] = pts, label
        o = outcomes[["player_id", "season", "games", "appeared"]].drop_duplicates(["player_id", "season"])
        m = r.merge(o, left_on=["player_id", "target_season"], right_on=["player_id", "season"], how="left")
        r["realized_games"] = pd.to_numeric(m["games"], errors="coerce").fillna(0).astype(int).to_numpy()
        r["appeared"] = m["appeared"].map(lambda v: bool(v) if not pd.isna(v) else False).to_numpy()
        frames.append(r)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["player_id", "origin", "position", "horizon", "target_season"])
    if len(out):
        keyed = lines.drop_duplicates(["position", "season"]).rename(columns={"season": "target_season", "line_points": "later_line",
                                                                              "deep_line_points": "later_deep_line"})
        out = out.merge(keyed[["position", "target_season", "later_line", "later_deep_line"]], on=["position", "target_season"], how="left")
        if out["later_line"].isna().any():
            missing = out.loc[out["later_line"].isna(), ["position", "target_season"]].drop_duplicates()
            raise StashSelectionError(f"no starter line for {missing.to_dict('records')}; a missing line is not zero")
        out["contributor"] = out["realized_points"] >= out["later_line"]
        out["contributor_abs"] = out["realized_points"] >= float(absolute_line)
        out["contributor_deep"] = (out["realized_points"] >= out["later_deep_line"]).where(out["later_deep_line"].notna(), other=pd.NA)
    out.attrs["censored_dropped"] = censored
    return out.reset_index(drop=True)


def cumulative_contributor(rows: pd.DataFrame, horizons=(1, 2, 3)) -> pd.DataFrame:
    """Per (player_id, origin): contributor in any of the horizons, defined only when every horizon is closed."""
    out = []
    for (pid, origin), g in rows.groupby(["player_id", "origin"]):
        closed = set(int(h) for h in g["horizon"]) >= set(int(h) for h in horizons)
        out.append({"player_id": pid, "origin": int(origin), "closed": bool(closed),
                    "any_contributor_1_3": bool(g["contributor"].astype(bool).any()) if closed else pd.NA})
    return pd.DataFrame(out, columns=["player_id", "origin", "closed", "any_contributor_1_3"])
