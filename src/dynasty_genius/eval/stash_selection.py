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


DEFINITIONS_VERSION = "stash_selection_definitions_v2"
REQUIRED_DEFINITION_KEYS = ("version", "frozen_before_first_result", "origins", "contribution_bars", "cohort_primary",
                            "cohort_exploratory", "primary_test", "immediate_help_test", "budgets", "uncertainty", "label_ledger",
                            "claims_not_made")


def load_definitions(path: Path) -> dict:
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    if d.get("version") != DEFINITIONS_VERSION or d.get("frozen_before_first_result") is not True:
        raise StashSelectionError(f"definitions must be the frozen v2 file ({DEFINITIONS_VERSION}); got {d.get('version')!r}")
    missing = [k for k in REQUIRED_DEFINITION_KEYS if k not in d]
    if missing:
        raise StashSelectionError(f"definitions file lacks {missing}")
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


# ── paired orderings from the frozen history ─────────────────────────────────────────────────

ORDERING_COLUMNS = ("rank_current", "rank_current_total", "rank_current_ppg", "rank_draft", "rank_future",
                    "rank_future_appear", "rank_future_candidate", "rank_null")
CELL = ["origin", "position", "horizon"]


def attach_forecasts(rows: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Join the frozen producer's out-of-fold forecasts for (player, origin, horizon). A candidate-horizon
    row without a history row is a chronology or source error and refuses; it is never a zero."""
    parts = []
    for j, g in rows.groupby("horizon"):
        j = int(j)
        cols = {f"policy_e_points_year{j}": "future_points", f"policy_p_appear_year{j}": "future_appear",
                f"candidate_e_points_year{j}": "future_candidate", f"baseline_e_points_year{j}": "null_reference"}
        h = history[history["horizon"] == j][["player_id", "feature_season", *cols]].rename(columns=cols)
        h = h.rename(columns={"feature_season": "origin"}).drop_duplicates(["player_id", "origin"])
        m = g.merge(h, on=["player_id", "origin"], how="left", indicator=True)
        missing = m[m["_merge"] != "both"]
        if len(missing):
            raise StashSelectionError(f"{len(missing)} candidate rows have no frozen history row at horizon {j} "
                                      f"(e.g. {missing[['player_id', 'origin']].head(3).to_dict('records')})")
        parts.append(m.drop(columns=["_merge"]))
    return pd.concat(parts, ignore_index=True) if parts else rows.copy()


def _rank_desc(frame: pd.DataFrame, col: str) -> pd.Series:
    """Average rank within a cell, higher value first."""
    return frame.groupby(CELL)[col].rank(method="average", ascending=False)


def orderings(rows: pd.DataFrame) -> pd.DataFrame:
    """Average ranks inside each (origin, position, horizon) cell for every declared ordering. Draft
    capital ranks the overall pick ascending; undrafted and not-yet-visible picks share one last rank."""
    r = rows.copy()
    r["rank_current"] = _rank_desc(r, "origin_points")
    r["rank_current_total"] = _rank_desc(r, "total_points_t")
    r["rank_current_ppg"] = _rank_desc(r, "ppg_t")
    pick = pd.to_numeric(r["draft_pick"], errors="coerce").where(r["draft_visible"].astype(bool))
    r["_draft_key"] = (-pick).fillna(-np.inf)                 # ascending pick == descending negative pick; unknown last
    r["rank_draft"] = _rank_desc(r, "_draft_key")
    r = r.drop(columns=["_draft_key"])
    r["rank_future"] = _rank_desc(r, "future_points")
    r["rank_future_appear"] = _rank_desc(r, "future_appear")
    r["rank_future_candidate"] = _rank_desc(r, "future_candidate")
    r["rank_null"] = _rank_desc(r, "null_reference")
    return r


# ── rank discrimination and selection at a fixed budget ──────────────────────────────────────

def _avg_rank(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(method="average").to_numpy()


def _spearman(rank_col: np.ndarray, points: np.ndarray) -> float:
    """Spearman between the ordering (lower rank = preferred) and realized points, signed so that a
    positive value means the preferred players earned more. NaN when either side is constant."""
    a, b = _avg_rank(-np.asarray(rank_col, dtype=float)), _avg_rank(np.asarray(points, dtype=float))
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _auc(rank_col: np.ndarray, flag: np.ndarray) -> float:
    """P(preferred score of a positive > negative) + half credit for ties; NaN with a single class."""
    score = -np.asarray(rank_col, dtype=float)
    pos, neg = score[flag.astype(bool)], score[~flag.astype(bool)]
    if not len(pos) or not len(neg):
        return float("nan")
    wins = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(wins / (len(pos) * len(neg)))


def spearman_by_cell(rows: pd.DataFrame, rank_col: str) -> pd.DataFrame:
    out = []
    for key, g in rows.groupby(CELL):
        r = g[rank_col].to_numpy(dtype=float)
        val = _spearman(r, g["realized_points"].to_numpy()) if len(g) >= 3 else float("nan")
        out.append({**dict(zip(CELL, key)), "ordering": rank_col, "n": int(len(g)), "value": val,
                    "all_tied": bool(len(np.unique(r)) == 1)})
    return pd.DataFrame(out, columns=[*CELL, "ordering", "n", "value", "all_tied"])


def auc_by_cell(rows: pd.DataFrame, rank_col: str, flag_col: str = "contributor") -> pd.DataFrame:
    out = []
    for key, g in rows.groupby(CELL):
        flag = g[flag_col].astype(bool).to_numpy()
        out.append({**dict(zip(CELL, key)), "ordering": rank_col, "n": int(len(g)), "n_positive": int(flag.sum()),
                    "value": _auc(g[rank_col].to_numpy(dtype=float), flag)})
    return pd.DataFrame(out, columns=[*CELL, "ordering", "n", "n_positive", "value"])


def select_at_budget(rows: pd.DataFrame, rank_col: str, budget: int, flag_col: str = "contributor") -> pd.DataFrame:
    """Pick the `budget` best-ranked candidates in each cell. A tie straddling the boundary is
    disclosed and credited fractionally (slots left ÷ tied rows); it is never broken by an arbitrary order."""
    out = []
    for key, g in rows.groupby(CELL):
        g = g.sort_values(rank_col)
        r = g[rank_col].to_numpy(dtype=float)
        flag = g[flag_col].astype(bool).to_numpy().astype(float)
        pts = g["realized_points"].to_numpy(dtype=float)
        bust = (~g["appeared"].astype(bool)).to_numpy().astype(float)
        n = len(g)
        k = min(int(budget), n)
        weight = np.zeros(n)
        if k:
            cutoff = r[k - 1]
            better = r < cutoff
            tied = r == cutoff
            slots_left = k - int(better.sum())
            weight[better] = 1.0
            if tied.sum() > slots_left:
                weight[tied] = slots_left / tied.sum()
                boundary, fractional = int(tied.sum()), True
            else:
                weight[tied] = 1.0
                boundary, fractional = 0, False
        else:
            boundary, fractional = 0, False
        hits = float((weight * flag).sum())
        out.append({**dict(zip(CELL, key)), "ordering": rank_col, "budget": int(budget), "n": int(n), "picks": int(k),
                    "hits": hits, "points_captured": float((weight * pts).sum()), "misses": float(flag.sum() - hits),
                    "busts": float((weight * bust).sum()), "boundary_ties": boundary, "fractional_credit_applied": fractional})
    return pd.DataFrame(out, columns=[*CELL, "ordering", "budget", "n", "picks", "hits", "points_captured", "misses", "busts",
                                      "boundary_ties", "fractional_credit_applied"])


def _pooled(cells: pd.DataFrame) -> dict:
    d = cells.dropna(subset=["value"])
    n = int(d["n"].sum())
    return {"n": n, "cells": int(len(d)), "cells_undefined": int(len(cells) - len(d)),
            "value": float((d["value"] * d["n"]).sum() / n) if n else float("nan")}


def compare_orderings(rows: pd.DataFrame, ordering_cols, budgets=(2, 4, 8), flag_col: str = "contributor") -> dict:
    pooled: dict = {}
    season_frames = []
    for col in ordering_cols:
        sp, auc = spearman_by_cell(rows, col), auc_by_cell(rows, col, flag_col)
        sel = {str(b): select_at_budget(rows, col, b, flag_col) for b in budgets}
        pooled[col] = {"spearman": _pooled(sp), "auc": _pooled(auc),
                       "selection": {b: {"cells": int(len(s)), "picks": int(s["picks"].sum()), "hits": float(s["hits"].sum()),
                                         "points_captured": float(s["points_captured"].sum()), "misses": float(s["misses"].sum()),
                                         "busts": float(s["busts"].sum()), "boundary_ties": int(s["boundary_ties"].sum()),
                                         "cells_with_fractional_credit": int(s["fractional_credit_applied"].sum())}
                                     for b, s in sel.items()}}
        f = sp.rename(columns={"value": "spearman"}).merge(auc[[*CELL, "n_positive", "value"]].rename(columns={"value": "auc"}), on=CELL)
        for b, s in sel.items():
            f = f.merge(s[[*CELL, "picks", "hits", "points_captured", "misses", "busts", "boundary_ties"]].rename(
                columns={c: f"{c}_b{b}" for c in ("picks", "hits", "points_captured", "misses", "busts", "boundary_ties")}), on=CELL)
        season_frames.append(f)
    by_season = pd.concat(season_frames, ignore_index=True) if season_frames else pd.DataFrame(columns=CELL)
    return {"pooled": pooled, "by_season": by_season}


# ── v2: contribution bars from the full positional panel, and the drafted early-career cohort ─

EXCL_NO_DRAFT = "no_verified_draft_class"
EXCL_DRAFT_YEAR = "draft_year_outside_1_3"
EXCL_PRIOR = "prior_contribution"
EXCL_IDENTITY = "unresolved_identity"


def contribution_bars(cohort: pd.DataFrame, outcomes: pd.DataFrame, *, bars: dict) -> pd.DataFrame:
    """The N-th highest DG-179 window points among ALL cohort rows of a position in a season (the full
    positional outcome panel), never among selected candidates. Short panels have bar 0 and are disclosed."""
    c = cohort[cohort["position"].isin(bars)].copy()
    c["points"], _ = _window_points(c, outcomes, "feature_season")
    rows = []
    for (pos, season), g in c.groupby(["position", "feature_season"]):
        n = int(bars[pos])
        pts = np.sort(g["points"].to_numpy())[::-1]
        short = len(pts) < n
        rows.append({"position": pos, "season": int(season), "bar_count": n, "rows_in_panel": int(len(pts)),
                     "bar_points": 0.0 if short else float(pts[n - 1]), "short_panel": bool(short)})
    return pd.DataFrame(rows, columns=["position", "season", "bar_count", "rows_in_panel", "bar_points", "short_panel"])


def contributor_flags(outcome_rows: pd.DataFrame, bars: pd.DataFrame, *, position: str) -> pd.Series:
    """appeared AND points >= bar of that season; a zero bar never creates a contributor from an absent record."""
    b = bars[bars["position"] == position].set_index("season")["bar_points"]
    bar = outcome_rows["season"].map(b)
    appeared = outcome_rows["appeared"].map(lambda v: bool(v) if not pd.isna(v) else False)
    return (appeared & (pd.to_numeric(outcome_rows["points"], errors="coerce") >= bar) & bar.notna()).astype(bool)


def primary_cohort_ledger(cohort: pd.DataFrame, outcomes: pd.DataFrame, draft: pd.DataFrame, *, definitions: dict, bars: dict,
                          origin: int) -> pd.DataFrame:
    """Every cohort row of the origin season with an exclusion reason ('' = primary candidate): a verified draft
    class c <= origin with 1 <= origin - c + 1 <= 3, and no season in c..origin in which the player appeared
    AND scored at or above the primary bar (absent DG-179 row = convention zero; unresolved identity excluded)."""
    lo, hi = definitions["origins"]["feature_seasons"]
    if not (lo <= int(origin) <= hi):
        raise StashSelectionError(f"origin {origin} is outside the frozen range {lo}-{hi}")
    c = cohort[(pd.to_numeric(cohort["feature_season"], errors="coerce") == int(origin)) & cohort["position"].isin(bars)].copy()
    c["origin"] = int(origin)
    c["origin_points"], c["origin_label_source"] = _window_points(c, outcomes, "feature_season")
    d = draft.dropna(subset=["gsis_id"]).copy() if len(draft) else pd.DataFrame(columns=["gsis_id", "season", "round", "pick"])
    d = d.sort_values(["gsis_id", "season"]).drop_duplicates("gsis_id", keep="first")
    d = d.rename(columns={"gsis_id": "player_id", "season": "draft_season", "round": "draft_round", "pick": "draft_pick"})
    c = c.merge(d[["player_id", "draft_season", "draft_round", "draft_pick"]], on="player_id", how="left")
    visible = c["draft_season"].notna() & (c["draft_season"] <= c["origin"])
    c["draft_visible"] = visible
    for col in ("draft_season", "draft_round", "draft_pick"):
        c[col] = c[col].where(visible)
    c["nfl_years_since_draft"] = (c["origin"] - c["draft_season"] + 1).where(visible)
    c["observed_history_seasons"] = pd.to_numeric(c["seasons_played"], errors="coerce") if "seasons_played" in c else np.nan
    panel_bars = contribution_bars(cohort, outcomes, bars=bars)
    o = outcomes[["player_id", "season", "points", "games", "appeared"]].drop_duplicates(["player_id", "season"])
    verdicts: list[tuple[str, int, int]] = []          # (exclusion_reason, prior_seasons_checked, prior_no_record_seasons)
    for _, r in c.iterrows():
        if "identity_status" in c and not pd.isna(r.get("identity_status")) and r["identity_status"] != "resolved":
            verdicts.append((EXCL_IDENTITY, 0, 0))
        elif not bool(r["draft_visible"]):
            verdicts.append((EXCL_NO_DRAFT, 0, 0))
        elif not (1 <= int(r["nfl_years_since_draft"]) <= 3):
            verdicts.append((EXCL_DRAFT_YEAR, 0, 0))
        else:
            seasons = list(range(int(r["draft_season"]), int(origin) + 1))
            hist = pd.DataFrame({"player_id": r["player_id"], "season": seasons}).merge(o, on=["player_id", "season"], how="left")
            absent = hist["points"].isna()
            hist["points"] = hist["points"].fillna(0.0)                 # resolved absent row = explicit convention zero
            hist["appeared"] = hist["appeared"].where(~absent, False)
            flags = contributor_flags(hist, panel_bars, position=r["position"])
            verdicts.append((EXCL_PRIOR if bool(flags.any()) else "", len(seasons), int(absent.sum())))
    c["exclusion_reason"] = [v[0] for v in verdicts]
    c["prior_seasons_checked"] = [v[1] for v in verdicts]
    c["prior_no_record_seasons"] = [v[2] for v in verdicts]
    cols = ["player_id", "origin", "position", "origin_points", "origin_label_source", "total_points_t", "ppg_t", "games_t", "age",
            "observed_history_seasons", "draft_visible", "draft_season", "draft_round", "draft_pick", "nfl_years_since_draft",
            "exclusion_reason", "prior_seasons_checked", "prior_no_record_seasons"]
    return c[[k for k in cols if k in c]].sort_values(["position", "player_id"]).reset_index(drop=True)


def primary_candidates(cohort, outcomes, draft, *, definitions: dict, bars: dict, origin: int) -> pd.DataFrame:
    ledger = primary_cohort_ledger(cohort, outcomes, draft, definitions=definitions, bars=bars, origin=origin)
    return ledger[ledger["exclusion_reason"] == ""].reset_index(drop=True)
