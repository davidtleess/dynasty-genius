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


DEFINITIONS_VERSION = "stash_selection_definitions_v3"
REQUIRED_DEFINITION_KEYS = ("version", "frozen_before_first_result", "origins", "contribution_bars", "cohort_primary",
                            "cohort_exploratory", "primary_test", "immediate_help_test", "budgets", "uncertainty", "label_ledger",
                            "claims_not_made")


def load_definitions(path: Path) -> dict:
    raw = Path(path).read_bytes()
    d = json.loads(raw)
    if d.get("version") != DEFINITIONS_VERSION or d.get("frozen_before_first_result") is not True:
        raise StashSelectionError(f"definitions must be the frozen v3 file ({DEFINITIONS_VERSION}); got {d.get('version')!r}")
    missing = [k for k in REQUIRED_DEFINITION_KEYS if k not in d]
    if missing:
        raise StashSelectionError(f"definitions file lacks {missing}")
    d["_file"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return d


# ── starter lines and candidates (origin-available evidence only) ────────────────────────────

OFFENSIVE_POSITIONS = ("QB", "RB", "WR", "TE")
LABEL_ARTIFACT = "artifact_row"
LABEL_NO_RECORD = "no_record_zero"


_TRUE = {"true", "1", "1.0", "yes"}
_FALSE = {"false", "0", "0.0", "no"}


def parse_bool(value) -> bool:
    """Strict: booleans, 0/1, and the strings true/false (case-insensitive). 'False' is False; anything else refuses."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)) and not (isinstance(value, float) and np.isnan(value)):
        if float(value) in (0.0, 1.0):
            return bool(float(value))
        raise StashSelectionError(f"invalid boolean value {value!r}")
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise StashSelectionError(f"invalid boolean value {value!r}")


def validated_outcomes(outcomes: pd.DataFrame) -> pd.DataFrame:
    """The DG-179 outcome rows as the evaluator reads them: unique (player_id, season), finite points, a
    strict boolean `appeared`. A present row with an invalid value refuses; absence means a missing key."""
    o = outcomes[["player_id", "season", "points", "games", "appeared"]].copy()
    if o.duplicated(["player_id", "season"]).any():
        n = int(o.duplicated(["player_id", "season"]).sum())
        raise StashSelectionError(f"{n} duplicate outcome rows on (player_id, season); a conflict is never resolved by picking one")
    pts = pd.to_numeric(o["points"], errors="coerce")
    if not np.isfinite(pts.to_numpy(dtype=float)).all():
        raise StashSelectionError("an outcome row carries non-finite points; an invalid value is not a missing key")
    o["points"] = pts.astype(float)
    o["season"] = pd.to_numeric(o["season"], errors="coerce")
    if not np.isfinite(o["season"].to_numpy(dtype=float)).all() or (o["season"] != np.floor(o["season"])).any():
        raise StashSelectionError("an outcome row carries a non-integral season")
    o["season"] = o["season"].astype(int)
    try:
        o["appeared"] = o["appeared"].map(parse_bool)
    except StashSelectionError as err:
        raise StashSelectionError(f"invalid appeared flag in the outcomes: {err}") from err
    return o


def _window_points(frame: pd.DataFrame, outcomes: pd.DataFrame, season_col: str) -> tuple[pd.Series, pd.Series]:
    """Realized DG-179 window points for (player_id, season_col) with the label source; an identified
    player-season with no artifact row (a missing KEY) is zero under the artifact's own convention."""
    o = validated_outcomes(outcomes)
    m = frame[["player_id", season_col]].merge(o, left_on=["player_id", season_col], right_on=["player_id", "season"], how="left",
                                               indicator=True)
    present = (m["_merge"] == "both").to_numpy()
    points = np.where(present, m["points"].to_numpy(dtype=float), 0.0)
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
            deep = np.nan if len(pts) < dn else float(pts[dn - 1])
        rows.append({"position": pos, "season": int(season), "slots": n, "rows_in_cell": int(len(pts)),
                     "line_points": np.nan if short else float(pts[n - 1]), "short_cell": bool(short), "deep_line_points": deep})
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
    c = c.merge(validated_draft(draft), on="player_id", how="left")
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
        o = validated_outcomes(outcomes)[["player_id", "season", "games", "appeared"]]
        m = r.merge(o, left_on=["player_id", "target_season"], right_on=["player_id", "season"], how="left")
        r["realized_games"] = pd.to_numeric(m["games"], errors="coerce").fillna(0).astype(int).to_numpy()
        r["appeared"] = m["appeared"].map(lambda v: False if pd.isna(v) else parse_bool(v)).to_numpy()
        frames.append(r)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["player_id", "origin", "position", "horizon", "target_season"])
    if len(out):
        keyed = lines.drop_duplicates(["position", "season"]).rename(columns={"season": "target_season", "line_points": "later_line",
                                                                              "deep_line_points": "later_deep_line"})
        out = out.merge(keyed[["position", "target_season", "later_line", "later_deep_line"]], on=["position", "target_season"], how="left")
        if out["later_line"].isna().any():
            missing = out.loc[out["later_line"].isna(), ["position", "target_season"]].drop_duplicates()
            raise StashSelectionError(f"no starter line for {missing.to_dict('records')}; a missing line is not zero")
        appeared = out["appeared"].astype(bool)          # a zero bar never creates a contributor from an absent record
        out["contributor"] = appeared & (out["realized_points"] >= out["later_line"])
        out["contributor_abs"] = appeared & (out["realized_points"] >= float(absolute_line))
        out["contributor_deep"] = (appeared & (out["realized_points"] >= out["later_deep_line"])).where(out["later_deep_line"].notna(), other=pd.NA)
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


def attach_forecasts(rows: pd.DataFrame, history: pd.DataFrame, *, on_missing: str = "refuse") -> pd.DataFrame:
    """Join the frozen producer's out-of-fold forecasts for (player, origin, horizon). A candidate-horizon
    row without a history row is never a zero: it refuses (default) or, for the sparse exploratory
    horizons, is excluded and counted in `.attrs["excluded_missing_forecast"]`."""
    parts = []
    excluded = 0
    for j, g in rows.groupby("horizon"):
        j = int(j)
        cols = {f"policy_e_points_year{j}": "future_points", f"policy_p_appear_year{j}": "future_appear",
                f"candidate_e_points_year{j}": "future_candidate", f"baseline_e_points_year{j}": "null_reference"}
        h = history[history["horizon"] == j][["player_id", "feature_season", *cols]].rename(columns=cols)
        h = h.rename(columns={"feature_season": "origin"}).drop_duplicates(["player_id", "origin"])
        m = g.merge(h, on=["player_id", "origin"], how="left", indicator=True)
        missing = m["_merge"] != "both"
        if missing.any():
            if on_missing != "exclude":
                raise StashSelectionError(f"{int(missing.sum())} candidate rows have no frozen history row at horizon {j} "
                                          f"(e.g. {m.loc[missing, ['player_id', 'origin']].head(3).to_dict('records')})")
            excluded += int(missing.sum())
            m = m[~missing]
        parts.append(m.drop(columns=["_merge"]))
    out = pd.concat(parts, ignore_index=True) if parts else rows.copy()
    out.attrs["excluded_missing_forecast"] = excluded
    return out


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
    r["rank_null"] = _rank_desc(r, "null_reference")            # legacy name; identical to rank_persistence
    r["rank_persistence"] = r["rank_null"]
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


def selection_weights(sorted_ranks: np.ndarray, budget: int) -> tuple[np.ndarray, int, bool]:
    """Fractional selection weights for ranks sorted ascending: 1 for rows strictly better than the cutoff,
    slots-left ÷ tied-rows for a tie straddling the boundary (disclosed), 0 beyond. One definition, shared by
    the selection and its bounds."""
    r = np.asarray(sorted_ranks, dtype=float)
    n = len(r)
    k = min(int(budget), n)
    weight = np.zeros(n)
    if not k:
        return weight, 0, False
    cutoff = r[k - 1]
    better, tied = r < cutoff, r == cutoff
    slots_left = k - int(better.sum())
    weight[better] = 1.0
    if tied.sum() > slots_left:
        weight[tied] = slots_left / tied.sum()
        return weight, int(tied.sum()), True
    weight[tied] = 1.0
    return weight, 0, False


def select_at_budget(rows: pd.DataFrame, rank_col: str, budget: int, flag_col: str = "contributor",
                     points_col: str = "realized_points") -> pd.DataFrame:
    """Pick the `budget` best-ranked candidates in each cell. A tie straddling the boundary is
    disclosed and credited fractionally (slots left ÷ tied rows); it is never broken by an arbitrary order."""
    out = []
    for key, g in rows.groupby(CELL):
        g = g.sort_values(rank_col)
        flag = g[flag_col].astype(bool).to_numpy().astype(float)
        pts = g[points_col].to_numpy(dtype=float)
        bust = (~g["appeared"].astype(bool)).to_numpy().astype(float)
        n = len(g)
        k = min(int(budget), n)
        weight, boundary, fractional = selection_weights(g[rank_col].to_numpy(dtype=float), budget)
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
EXCL_BAR = "bar_unavailable"


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
                     "bar_points": np.nan if short else float(pts[n - 1]), "short_panel": bool(short)})   # short = unavailable, not zero
    return pd.DataFrame(rows, columns=["position", "season", "bar_count", "rows_in_panel", "bar_points", "short_panel"])


def contributor_flags(outcome_rows: pd.DataFrame, bars: pd.DataFrame, *, position: str) -> pd.Series:
    """appeared AND points >= bar of that season; a zero bar never creates a contributor from an absent record."""
    b = bars[bars["position"] == position].set_index("season")["bar_points"]
    bar = outcome_rows["season"].map(b)
    appeared = outcome_rows["appeared"].map(lambda v: False if pd.isna(v) else parse_bool(v))
    return (appeared & (pd.to_numeric(outcome_rows["points"], errors="coerce") >= bar) & bar.notna()).astype(bool)


def validated_draft(draft: pd.DataFrame) -> pd.DataFrame:
    """One verified draft row per gsis id; two rows for one id with different facts refuse (never silently pick one)."""
    if not len(draft):
        return pd.DataFrame(columns=["player_id", "draft_season", "draft_round", "draft_pick"])
    d = draft.dropna(subset=["gsis_id"])[["gsis_id", "season", "round", "pick"]].drop_duplicates()
    if d.duplicated("gsis_id").any():
        ids = sorted(d.loc[d.duplicated("gsis_id"), "gsis_id"].unique())[:3]
        raise StashSelectionError(f"conflicting draft rows for the same gsis id (e.g. {ids}); a conflict is never resolved by picking one")
    return d.rename(columns={"gsis_id": "player_id", "season": "draft_season", "round": "draft_round", "pick": "draft_pick"})


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
    c = c.merge(validated_draft(draft), on="player_id", how="left")
    visible = c["draft_season"].notna() & (c["draft_season"] <= c["origin"])
    c["draft_visible"] = visible
    for col in ("draft_season", "draft_round", "draft_pick"):
        c[col] = c[col].where(visible)
    c["nfl_years_since_draft"] = (c["origin"] - c["draft_season"] + 1).where(visible)
    c["observed_history_seasons"] = pd.to_numeric(c["seasons_played"], errors="coerce") if "seasons_played" in c else np.nan
    panel_bars = contribution_bars(cohort, outcomes, bars=bars)
    o = validated_outcomes(outcomes)
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
            available = panel_bars[(panel_bars["position"] == r["position"]) & panel_bars["bar_points"].notna()]["season"]
            if any(sn not in set(available.astype(int)) for sn in seasons):
                verdicts.append((EXCL_BAR, len(seasons), 0))            # a prior season without an available bar cannot be verified
                continue
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


# ── v2 primary test: summed t+2 / t+3 future on identical complete candidates ────────────────

V2_ORDERINGS = ("rank_future_sum", "rank_future_year1", "rank_origin_points", "rank_draft", "rank_persistence")
V2_CELL = ["origin", "position"]


def _history_pivot(history: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Frozen forecasts at one horizon keyed by (player_id, position, feature_season). Ambiguous duplicate
    identities refuse; forecast_season must equal feature_season + horizon with finite integral years."""
    j = int(horizon)
    h = history[pd.to_numeric(history["horizon"], errors="coerce") == j].copy()
    for col in ("feature_season", "forecast_season"):
        vals = pd.to_numeric(h[col], errors="coerce")
        if not np.isfinite(vals.to_numpy(dtype=float)).all() or (vals != np.floor(vals)).any():
            raise StashSelectionError(f"history {col} must be finite integral years at horizon {j}")
        h[col] = vals.astype(int)
    bad = h[h["forecast_season"] != h["feature_season"] + j]
    if len(bad):
        raise StashSelectionError(f"{len(bad)} history rows at horizon {j} have forecast_season != feature_season + horizon")
    keys = ["player_id", "position", "feature_season"]
    if h.duplicated(keys).any():
        n = int(h.duplicated(keys).sum())
        raise StashSelectionError(f"{n} duplicate forecast identities at horizon {j} on (player_id, position, feature_season)")
    cols = {f"policy_e_points_year{j}": f"policy_{j}", f"baseline_e_points_year{j}": f"persistence_{j}"}
    return h[[*keys, *cols]].rename(columns=cols).rename(columns={"feature_season": "origin"})


def summed_future_rows(cands: pd.DataFrame, history: pd.DataFrame, outcomes: pd.DataFrame, bars: pd.DataFrame, *,
                       last_complete_season: int = 2025, horizons=(2, 3)) -> pd.DataFrame:
    """Per candidate: the frozen policy expected points summed over `horizons` (each required finite; a missing
    one is a counted exclusion, never zero), the year-1 expected points (help now), the persistence
    comparator summed over the same horizons, and the realized DG-179 points over the same seasons with
    per-season label sources; contributor_any = contributor (appeared AND >= bar) in any of those seasons.
    A target season without a full-panel bar is a counted exclusion (missing_bar)."""
    horizons = tuple(int(j) for j in horizons)
    exclusions = {"missing_forecast": 0, "open_season": 0, "missing_bar": 0}
    c = cands.copy()
    open_rows = (c["origin"] + max(horizons)) > last_complete_season
    exclusions["open_season"] = int(open_rows.sum())
    c = c[~open_rows]
    for j in dict.fromkeys((1, *horizons)):                   # year 1 (help now) plus the window, each joined once
        c = c.merge(_history_pivot(history, j), on=["player_id", "position", "origin"], how="left")
    need = list(dict.fromkeys(["policy_1", *[f"policy_{j}" for j in horizons], *[f"persistence_{j}" for j in horizons]]))
    finite = np.isfinite(c[need].to_numpy(dtype=float)).all(axis=1) if len(c) else np.array([], dtype=bool)
    exclusions["missing_forecast"] = int((~finite).sum())
    c = c[finite].copy()
    c["future_sum"] = c[[f"policy_{j}" for j in horizons]].sum(axis=1)
    c["future_year1"] = c["policy_1"]
    c["persistence_sum"] = c[[f"persistence_{j}" for j in horizons]].sum(axis=1)
    bar_lookup = {(r.position, int(r.season)): float(r.bar_points) for r in bars.itertuples() if not pd.isna(r.bar_points)}
    o = validated_outcomes(outcomes)
    keep, labels, realized, contrib, appeared_any, no_record_any = [], [], [], [], [], []
    for _, r in c.iterrows():
        seasons = [int(r["origin"]) + j for j in horizons]
        if any((r["position"], s) not in bar_lookup for s in seasons):
            exclusions["missing_bar"] += 1
            keep.append(False)
            for lst, val in ((labels, ""), (realized, np.nan), (contrib, False), (appeared_any, False), (no_record_any, False)):
                lst.append(val)
            continue
        t = pd.DataFrame({"player_id": r["player_id"], "target_season": seasons})
        pts, lab = _window_points(t, o, "target_season")
        m = t.merge(o[["player_id", "season", "appeared"]], left_on=["player_id", "target_season"], right_on=["player_id", "season"], how="left")
        app = m["appeared"].map(lambda v: False if pd.isna(v) else bool(v))
        flags = contributor_flags(pd.DataFrame({"season": seasons, "points": pts.to_numpy(), "appeared": app.to_numpy()}), bars,
                                  position=r["position"])
        keep.append(True)
        labels.append("+".join(lab.tolist()))
        realized.append(float(pts.sum()))
        contrib.append(bool(flags.any()))
        appeared_any.append(bool(app.any()))
        no_record_any.append(bool((lab == LABEL_NO_RECORD).any()))
    c["label_sources"] = labels
    c["realized_sum"] = realized
    c["contributor_any"] = contrib
    c["appeared"] = appeared_any                      # any appearance in the window seasons (bust = none)
    c["any_no_record"] = no_record_any
    c = c[np.array(keep, dtype=bool)] if len(c) else c
    c["horizon"] = int("".join(str(j) for j in horizons))   # pseudo-horizon (23, 2345) so the cell helpers work unchanged
    c["realized_points"] = c["realized_sum"]
    if len(c) and not np.isfinite(c[["future_sum", "persistence_sum", "realized_sum"]].to_numpy(dtype=float)).all():
        raise StashSelectionError("a summed quantity is not finite")
    c.attrs["exclusions"] = exclusions
    return c.reset_index(drop=True)


def v2_orderings(rows: pd.DataFrame) -> pd.DataFrame:
    r = rows.copy()
    r["rank_future_sum"] = _rank_desc(r, "future_sum")
    r["rank_future_year1"] = _rank_desc(r, "future_year1")
    r["rank_origin_points"] = _rank_desc(r, "origin_points")
    pick = pd.to_numeric(r["draft_pick"], errors="coerce").where(r["draft_visible"].astype(bool))
    r["_draft_key"] = (-pick).fillna(-np.inf)
    r["rank_draft"] = _rank_desc(r, "_draft_key")
    r = r.drop(columns=["_draft_key"])
    r["rank_persistence"] = _rank_desc(r, "persistence_sum")
    return r


def selection_bounds_no_record_unknown(rows: pd.DataFrame, rank_col: str, budget: int, flag_col: str = "contributor_any") -> dict:
    """Sensitivity with the EXACT selection weights: treat a window that contains a no-record season as
    unknown unless a known positive already exists. lower = Σ weight × known contributor; upper = lower +
    Σ weight × (unknown window AND no known positive). A known positive is a hit for both bounds."""
    lower = unknown_weight = 0.0
    boundary_total = 0
    for _, g in rows.groupby(CELL):
        g = g.sort_values(rank_col)
        weight, boundary, _ = selection_weights(g[rank_col].to_numpy(dtype=float), budget)
        known_pos = g[flag_col].astype(bool).to_numpy()
        unknown = g["any_no_record"].astype(bool).to_numpy() & ~known_pos
        lower += float((weight * known_pos).sum())
        unknown_weight += float((weight * unknown).sum())
        boundary_total += int(boundary)
    return {"hits_lower": lower, "hits_upper": lower + unknown_weight, "unknown_weight": unknown_weight,
            "boundary_ties": boundary_total,
            "meaning": "lower counts only known contributors; upper adds every selected weight whose window has a no-record season "
                       "and no known positive; the same fractional weights as the selection"}


# ── paired player-cluster bootstrap and per-season disclosure ────────────────────────────────

CONDITIONAL_ON = "realized origins and the fixed frozen fits"


def metric_fn(name: str, *, budget: int = 2, flag_col: str = "contributor_any", points_col: str = "realized_points"):
    """A pooled metric of one ordering over a rows frame: n-weighted Spearman or AUC over cells, or the
    total hits / points captured of a fixed-budget selection."""
    if name == "spearman":
        return lambda rows, col: _pooled(spearman_by_cell(rows, col))["value"]
    if name == "auc":
        return lambda rows, col: _pooled(auc_by_cell(rows, col, flag_col))["value"]
    if name == "hits_at_budget":
        return lambda rows, col: float(select_at_budget(rows, col, budget, flag_col, points_col)["hits"].sum())
    if name == "points_at_budget":
        return lambda rows, col: float(select_at_budget(rows, col, budget, flag_col, points_col)["points_captured"].sum())
    raise StashSelectionError(f"unknown metric {name!r}")


def paired_difference_bootstrap(rows: pd.DataFrame, metric, ordering_a: str, ordering_b: str, *, draws: int, seed: int) -> dict:
    """metric(b) − metric(a) on identical rows, resampling PLAYERS: every origin and horizon of a drawn player
    moves as one block, drawn from the union of both arms' rows (the same rows, because the comparison is
    paired). Conditional on the realized origins and the fixed frozen fits; no future-season or
    model-selection uncertainty is claimed."""
    def delta(frame: pd.DataFrame) -> float:
        return float(metric(frame, ordering_b) - metric(frame, ordering_a))

    point = delta(rows)
    players = rows["player_id"].to_numpy()
    keys = np.array(sorted(set(players)), dtype=object)
    members = {k: rows.index[players == k].to_numpy() for k in keys}
    counts = rows.groupby("player_id")["origin"].nunique()
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(int(draws)):
        picked = rng.choice(keys, size=len(keys), replace=True)
        idx = np.concatenate([members[k] for k in picked])
        samples.append(delta(rows.loc[idx]))
    arr = np.asarray(samples, dtype=float)
    arr = arr[np.isfinite(arr)]
    lo, hi = (float(v) for v in np.percentile(arr, [5, 95])) if arr.size else (float("nan"), float("nan"))
    return {"point": point, "ci90": [lo, hi], "draws": int(draws), "seed": int(seed), "rows": int(len(rows)),
            "clusters": int(len(keys)), "repeated_players": int((counts > 1).sum()), "conditional_on": CONDITIONAL_ON,
            "ordering_a": ordering_a, "ordering_b": ordering_b}


def season_table(rows: pd.DataFrame, ordering_cols, *, budget: int = 2, flag_col: str = "contributor_any",
                 points_col: str = "realized_points") -> pd.DataFrame:
    """Per origin season, position and ordering: n, Spearman, AUC and the fixed-budget selection, so the
    season clustering is visible instead of pooled away."""
    frames = []
    for col in ordering_cols:
        sp = spearman_by_cell(rows, col).rename(columns={"value": "spearman"})
        auc = auc_by_cell(rows, col, flag_col).rename(columns={"value": "auc"})[[*CELL, "n_positive", "auc"]]
        sel = select_at_budget(rows, col, budget, flag_col, points_col)[[*CELL, "picks", "hits", "points_captured", "misses", "busts",
                                                                          "boundary_ties"]]
        frames.append(sp.merge(auc, on=CELL).merge(sel, on=CELL))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=CELL)


# ── glue for the exploratory per-year horizons, and the manifest ─────────────────────────────

def bars_as_lines(primary: pd.DataFrame, strict: pd.DataFrame) -> pd.DataFrame:
    """The per-year machinery reads `line_points` (primary bar) and `deep_line_points` (strict bar)."""
    p = primary.rename(columns={"bar_points": "line_points", "bar_count": "slots", "rows_in_panel": "rows_in_cell", "short_panel": "short_cell"})
    s = strict.rename(columns={"bar_points": "deep_line_points"})[["position", "season", "deep_line_points"]]
    return p.merge(s, on=["position", "season"], how="left")


SCHEMA_VERSION = "dg177_stash_selection_v1"
CLAIM = ("historical low-production candidate screen on frozen out-of-fold forecasts and DG-179 outcomes; not a waiver backtest "
         "(no point-in-time ownership source); no breakout probability; budgets are declared scenarios")


def build_manifest(*, definitions: dict, sources: dict, launch: dict, counts: dict, outputs: dict, bars_override_used: bool = False,
                   origins_override: list | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "producer": "DG-177 stash-selection evaluation (report-only)",
        "definitions": {"version": definitions["version"], **definitions["_file"]},
        "sources": sources, "launch": launch, "counts": counts, "outputs": outputs, "claim": CLAIM,
        "uncertainty_conditional_on": CONDITIONAL_ON, "not_an_untouched_confirmation": True,
        "not_an_untouched_confirmation_meaning": "the selection policy was chosen historically on these folds; this is a retrospective "
                                                 "frozen-policy evaluation, not an untouched confirmation",
        "bars_override_used": bool(bars_override_used), "origins_override": origins_override,
        "year5_disclosure": "the frozen year-5 horizon exists for origin 2020 only (one-origin evidence)",
    }
