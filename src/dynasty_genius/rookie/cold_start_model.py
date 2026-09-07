"""Cold-start candidate for drafted skill players with no rookie-year record (DG-165, 2026-09-06).

Population, chronology and evaluation were FROZEN by root before any fit:

* Eligible: resolved skill draftees (draft position QB/RB/WR/TE), classes 2001–2025, with NO
  full-regular-season stat record through the draft season — read from the raw weekly REG captures
  (every parquet hashed against the capture manifest first). Every washout stays regardless of any
  later roster; roster membership at any date is never used.
* Origin T = draft season + 1 (career year 2); horizons h = 1..5 = career years 2–6.
* A class-c row's horizon-h label is usable at origin T only if c + h < T (season complete by T−1).
* Labels: the DG-179 championship-window artifact; a complete season with no artifact row is the
  producers' shared convention zero (tagged); a season beyond the last complete one is UNKNOWN.

This module produces the population and its support table (Task 5) and — after root's authorisation —
the per-horizon hurdle candidate, baselines, paired evaluation and sidecar (Task 6).
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "CAVEATS",
    "HORIZONS",
    "SELECTION_RULE",
    "SKILL_POSITIONS",
    "evaluate_candidate",
    "export_sidecar",
    "first_full_reg_season",
    "fit_arms",
    "never_record_population",
    "predict_arms",
    "support_table",
    "verify_capture",
]

SKILL_POSITIONS = ("QB", "RB", "WR", "TE")
HORIZONS = (1, 2, 3, 4, 5)
FIRST_CLASS = 2001
AGE_MONTH_DAY = "-09-01"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_capture(capture_dir: Path | str) -> dict[str, str]:
    """Hash every raw parquet the capture manifest declares; a missing or altered file refuses."""
    capture_dir = Path(capture_dir)
    manifest = json.loads((capture_dir / "manifest.json").read_text())
    files = manifest.get("files") or {}
    if not files:
        raise ValueError(f"{capture_dir}: capture manifest declares no files")
    # the real capture manifest declares a LIST of {path, sha256, ...}; a mapping rel -> {sha256} is also accepted
    entries: list[tuple[str, dict]] = []
    if isinstance(files, dict):
        entries = [(str(rel), meta if isinstance(meta, dict) else {}) for rel, meta in files.items()]
    else:
        for meta in files:
            if not isinstance(meta, dict) or not meta.get("path"):
                raise ValueError(f"{capture_dir}: a capture manifest file entry has no path")
            entries.append((str(meta["path"]), meta))
    verified: dict[str, str] = {}
    for rel, meta in entries:
        declared = meta.get("sha256")
        if not declared:
            raise ValueError(f"{capture_dir}: no sha256 declared for {rel}")
        path = Path(rel) if Path(rel).is_absolute() else capture_dir / rel
        if not path.exists():
            raise ValueError(f"{capture_dir}: declared capture file missing: {rel}")
        actual = _sha(path.read_bytes())
        if actual != declared:
            raise ValueError(f"{capture_dir}: sha256 mismatch for {rel}: declared {declared[:12]}…, actual {actual[:12]}…")
        verified[rel] = declared
    return verified


def first_full_reg_season(capture_dir: Path | str) -> pd.Series:
    """gsis_id -> first season with ANY regular-season stat row (any week), from the verified capture files."""
    capture_dir = Path(capture_dir)
    verified = verify_capture(capture_dir)
    frames = []
    for rel in verified:
        raw = (Path(rel) if Path(rel).is_absolute() else capture_dir / rel).read_bytes()
        df = pd.read_parquet(io.BytesIO(raw), columns=["player_id", "season", "season_type"])
        df = df.loc[(df["season_type"] == "REG") & df["player_id"].notna()]
        frames.append(df[["player_id", "season"]])
    if not frames:
        return pd.Series(dtype=int)
    reg = pd.concat(frames, ignore_index=True)
    reg["player_id"] = reg["player_id"].astype(str)
    return reg.groupby("player_id")["season"].min().astype(int)


def _age_at(birth: pd.Series, year: pd.Series) -> np.ndarray:
    bd = pd.to_datetime(birth, errors="coerce")
    ref = pd.to_datetime(year.astype(int).astype(str) + AGE_MONTH_DAY)
    return ((ref - bd).dt.days / 365.25).to_numpy(dtype=float)


def never_record_population(*, cohort: pd.DataFrame, first_reg: pd.Series, outcomes: pd.DataFrame, players: pd.DataFrame,
                            last_complete_season: int) -> pd.DataFrame:
    """One row per eligible draftee (frozen definition) with origin-dated features and horizon labels."""
    c = cohort.loc[cohort["label_basis"].astype(str) != "unresolved"].copy()
    c["gsis_id"] = c["gsis_id"].astype(str)
    c = c.loc[c["draft_season"].astype(int).between(FIRST_CLASS, last_complete_season) & c["position"].isin(SKILL_POSITIONS)].copy()
    first = c["gsis_id"].map(first_reg)
    eligible = first.isna() | (first > c["draft_season"].astype(int))
    pop = c.loc[eligible].copy()
    pop["first_full_reg_season"] = first.loc[eligible]
    pop["draft_season"] = pop["draft_season"].astype(int)
    pop["origin_year"] = pop["draft_season"] + 1
    pop = pop.rename(columns={"position": "draft_position"})
    pop["pick"] = pop["pick"].astype(int)
    pop["round"] = pop["round"].astype(int)
    pop["log_pick"] = np.log(pop["pick"].astype(float))
    pl = players.copy()
    pl["gsis_id"] = pl["gsis_id"].astype(str)
    birth = pop["gsis_id"].map(pl.drop_duplicates("gsis_id").set_index("gsis_id")["birth_date"])
    pop["birth_date"] = birth
    pop["age_at_origin"] = _age_at(birth, pop["origin_year"])
    # labels from the artifact: complete season with no row -> convention zero; beyond last complete -> unknown
    o = outcomes.copy()
    o["player_id"] = o["player_id"].astype(str)
    key = o.set_index(["player_id", o["season"].astype(int)])
    window_first = o.loc[o["appeared"].astype(bool)].groupby("player_id")["season"].min()
    wf = pop["gsis_id"].map(window_first)
    pop["window_absent_through_draft_season"] = wf.isna() | (wf > pop["draft_season"])
    for h in HORIZONS:
        season = pop["origin_year"] + h - 1
        appear, points, games, source = [], [], [], []
        for pid, s in zip(pop["gsis_id"], season):
            if s > last_complete_season:
                appear.append(np.nan)
                points.append(np.nan)
                games.append(np.nan)
                source.append("unknown")
            elif (pid, int(s)) in key.index:
                row = key.loc[(pid, int(s))]
                appear.append(float(bool(row["appeared"])))
                points.append(float(row["points"]))
                games.append(float(row["games"]))
                source.append("artifact")
            else:
                appear.append(0.0)
                points.append(0.0)
                games.append(0.0)
                source.append("convention_zero")
        pop[f"appear_{h}"] = appear
        pop[f"points_{h}"] = points
        pop[f"games_{h}"] = games
        pop[f"label_source_{h}"] = source
    keep = ["gsis_id", "name", "draft_season", "origin_year", "draft_position", "pick", "round", "log_pick", "birth_date", "age_at_origin",
            "first_full_reg_season", "window_absent_through_draft_season"]
    keep += [f"{q}_{h}" for h in HORIZONS for q in ("appear", "points", "games", "label_source")]
    return pop[keep].sort_values(["draft_season", "pick", "gsis_id"]).reset_index(drop=True)


def support_table(population: pd.DataFrame, *, origins=range(2012, 2026), horizons=HORIZONS) -> pd.DataFrame:
    """Per origin × horizon: training rows (c + h < T with a complete label), appearers, per-position counts, test rows.
    Recorded BEFORE any fit; the numbers do not depend on any model."""
    rows = []
    for T in origins:
        for h in horizons:
            train = population.loc[(population["draft_season"] + h < T) & population[f"appear_{h}"].notna()]
            test = population.loc[(population["draft_season"] == T - 1) & population[f"appear_{h}"].notna()]
            by_pos_rows = {p: int((train["draft_position"] == p).sum()) for p in SKILL_POSITIONS}
            by_pos_app = {p: int(train.loc[train["draft_position"] == p, f"appear_{h}"].sum()) for p in SKILL_POSITIONS}
            rows.append({"origin": int(T), "horizon": int(h), "train_rows": int(len(train)), "train_appearers": int(train[f"appear_{h}"].sum()),
                         "train_rows_by_position": json.dumps(by_pos_rows, sort_keys=True), "train_appearers_by_position": json.dumps(by_pos_app, sort_keys=True),
                         "test_rows": int(len(test)), "test_appearers": int(test[f"appear_{h}"].sum())})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- Task 6: arms, evaluation, sidecar (root-frozen rules)

from sklearn.linear_model import LogisticRegression, Ridge  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

CANDIDATE_MIN_TRAIN = 60
CANDIDATE_MIN_APPEARERS = 15
B1_MIN_POSITION_ROWS = 10
B1_MIN_CONDITIONAL_APPEARERS = 3
L2_C = 1.0
RIDGE_ALPHA = 1.0
ARMS = ("candidate", "b1", "b2")
SELECTION_RULE = ("per horizon, on the same paired supported rows: the candidate is selected only if BOTH the paired Brier(appear) "
                  "difference and the paired RMSE(unconditional points) difference vs B1 have 90% player-cluster bootstrap "
                  "intervals entirely below zero; otherwise B1's estimate is a baseline_research_candidate with its measured "
                  "out-of-time error and support; a horizon whose arms are unsupported at the final origin is unsupported")
CAVEATS = {
    "selection": ("selecting a policy on this historical evaluation is retrospective model selection, NOT independent confirmation "
                  "of the selected policy; both arms are reported at every horizon"),
    "population": ("a draft-population prior for drafted players with no rookie-year regular-season record; not conditioned on remaining "
                   "on a current roster; direction and size of this mismatch have not been measured"),
    "appearance": "P(appear) is the probability of at least one championship-window stat row; it is not a breakout or usefulness probability",
    "horizons": "each horizon is fitted, evaluated and selected independently; acceptance at one horizon never validates another",
    "labels": "a complete season with no artifact row is the producers' shared convention zero (tagged); seasons beyond 2025 are unknown",
}


def _design(frame: pd.DataFrame, *, positions: tuple[str, ...], with_age: bool, age_median: dict | None) -> np.ndarray:
    cols = [frame["log_pick"].to_numpy(float), frame["round"].to_numpy(float)]
    if with_age:
        age = frame["age_at_origin"].to_numpy(float).copy()
        fill = frame["draft_position"].map(age_median or {}).to_numpy(float)
        age = np.where(np.isnan(age), fill, age)
        cols.append(age)
    pos = frame["draft_position"].to_numpy()
    for p in positions:
        cols.append((pos == p).astype(float))
    return np.column_stack(cols)


def _fit_hurdle(train: pd.DataFrame, h: int, *, with_age: bool) -> dict:
    y = train[f"appear_{h}"].to_numpy(float)
    reasons = []
    if len(train) < CANDIDATE_MIN_TRAIN:
        reasons.append(f"{len(train)} training rows < {CANDIDATE_MIN_TRAIN}")
    if int(y.sum()) < CANDIDATE_MIN_APPEARERS:
        reasons.append(f"{int(y.sum())} training appearers < {CANDIDATE_MIN_APPEARERS}")
    if len(set(y.tolist())) < 2:
        reasons.append("training rows hold a single appearance class")
    positions = tuple(p for p in SKILL_POSITIONS if (train["draft_position"] == p).any())
    age_median = None
    if with_age:
        ages = train["age_at_origin"]
        overall = float(ages.median()) if ages.notna().any() else float("nan")
        age_median = {p: (float(ages[train["draft_position"] == p].median()) if ages[train["draft_position"] == p].notna().any() else overall)
                      for p in SKILL_POSITIONS}
        if not np.isfinite(overall):
            reasons.append("no training age is known")
    out = {"supported": not reasons, "reason": "; ".join(reasons) if reasons else None, "n_train": int(len(train)), "n_appearers": int(y.sum()),
           "positions": positions, "with_age": with_age, "age_median_by_position": age_median}
    if reasons:
        return out
    X = _design(train, positions=positions, with_age=with_age, age_median=age_median)
    scaler = StandardScaler().fit(X)
    logit = LogisticRegression(C=L2_C, max_iter=2000).fit(scaler.transform(X), y)
    app = y == 1.0
    Xc = _design(train.loc[app], positions=positions, with_age=False, age_median=None)
    scaler_c = StandardScaler().fit(Xc)
    ridge_pts = Ridge(alpha=RIDGE_ALPHA).fit(scaler_c.transform(Xc), train.loc[app, f"points_{h}"].to_numpy(float))
    ridge_games = Ridge(alpha=RIDGE_ALPHA).fit(scaler_c.transform(Xc), train.loc[app, f"games_{h}"].to_numpy(float))
    out.update({"scaler": scaler, "logit": logit, "scaler_c": scaler_c, "ridge_points": ridge_pts, "ridge_games": ridge_games})
    return out


def _fit_b1(train: pd.DataFrame, h: int) -> dict:
    cells = {}
    for p in SKILL_POSITIONS:
        rows = train.loc[train["draft_position"] == p]
        n = int(len(rows))
        appearers = int(rows[f"appear_{h}"].sum()) if n else 0
        supported = n >= B1_MIN_POSITION_ROWS
        cond_ok = supported and appearers >= B1_MIN_CONDITIONAL_APPEARERS
        cell = {"n": n, "appearers": appearers, "supported": supported, "conditional_supported": cond_ok,
                "reason": None if supported else f"{n} same-position training rows < {B1_MIN_POSITION_ROWS}",
                "p_appear": float(rows[f"appear_{h}"].mean()) if supported else None,
                "e_points": float(rows[f"points_{h}"].mean()) if supported else None,
                "e_games": float(rows[f"games_{h}"].mean()) if supported else None,
                "e_points_given_appear": float(rows.loc[rows[f"appear_{h}"] == 1.0, f"points_{h}"].mean()) if cond_ok else None,
                "e_games_given_appear": float(rows.loc[rows[f"appear_{h}"] == 1.0, f"games_{h}"].mean()) if cond_ok else None}
        cells[p] = cell
    return {"cells": cells, "min_position_rows": B1_MIN_POSITION_ROWS, "min_conditional_appearers": B1_MIN_CONDITIONAL_APPEARERS}


def fit_arms(train: pd.DataFrame, *, horizon: int, origin: int) -> dict:
    """Fit the candidate hurdle, B1 position cells and exploratory B2 on THIS fold's training rows only."""
    return {"horizon": int(horizon), "origin": int(origin), "candidate": _fit_hurdle(train, horizon, with_age=True),
            "b1": _fit_b1(train, horizon), "b2": _fit_hurdle(train, horizon, with_age=False)}


def _predict_hurdle(fit: dict, frame: pd.DataFrame, prefix: str) -> dict[str, np.ndarray]:
    n = len(frame)
    nan = np.full(n, np.nan)
    if not fit["supported"]:
        return {f"{prefix}_p_appear": nan, f"{prefix}_e_points_given_appear": nan, f"{prefix}_e_games_given_appear": nan,
                f"{prefix}_e_points": nan, f"{prefix}_e_games": nan, f"{prefix}_supported": np.zeros(n, dtype=bool)}
    known_pos = frame["draft_position"].isin(fit["positions"]).to_numpy()
    X = _design(frame, positions=fit["positions"], with_age=fit["with_age"], age_median=fit["age_median_by_position"])
    p = fit["logit"].predict_proba(fit["scaler"].transform(X))[:, 1]
    Xc = _design(frame, positions=fit["positions"], with_age=False, age_median=None)
    pts = fit["ridge_points"].predict(fit["scaler_c"].transform(Xc))
    games = fit["ridge_games"].predict(fit["scaler_c"].transform(Xc))
    p = np.where(known_pos, p, np.nan)
    pts = np.where(known_pos, pts, np.nan)
    games = np.where(known_pos, games, np.nan)
    return {f"{prefix}_p_appear": p, f"{prefix}_e_points_given_appear": pts, f"{prefix}_e_games_given_appear": games,
            f"{prefix}_e_points": p * pts, f"{prefix}_e_games": p * games, f"{prefix}_supported": known_pos}


def _predict_b1(fit: dict, frame: pd.DataFrame) -> dict[str, np.ndarray]:
    cells = fit["cells"]
    cols = {k: [] for k in ("b1_p_appear", "b1_e_points_given_appear", "b1_e_games_given_appear", "b1_e_points", "b1_e_games", "b1_supported")}
    for p in frame["draft_position"]:
        cell = cells.get(str(p))
        if cell is None or not cell["supported"]:
            for k in cols:
                cols[k].append(False if k == "b1_supported" else np.nan)
            continue
        cols["b1_p_appear"].append(cell["p_appear"])
        cols["b1_e_points"].append(cell["e_points"])
        cols["b1_e_games"].append(cell["e_games"])
        cols["b1_e_points_given_appear"].append(cell["e_points_given_appear"] if cell["conditional_supported"] else np.nan)
        cols["b1_e_games_given_appear"].append(cell["e_games_given_appear"] if cell["conditional_supported"] else np.nan)
        cols["b1_supported"].append(True)
    return {k: np.asarray(v, dtype=(bool if k == "b1_supported" else float)) for k, v in cols.items()}


def predict_arms(fit: dict, frame: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"gsis_id": frame["gsis_id"].astype(str).to_numpy()})
    for k, v in _predict_hurdle(fit["candidate"], frame, "candidate").items():
        out[k] = v
    for k, v in _predict_b1(fit["b1"], frame).items():
        out[k] = v
    for k, v in _predict_hurdle(fit["b2"], frame, "b2").items():
        out[k] = v
    return out


def _cluster_bootstrap(values: np.ndarray, units: np.ndarray, *, seed: int, draws: int) -> dict:
    uniq, inverse = np.unique(units, return_inverse=True)
    sums = np.bincount(inverse, weights=values, minlength=len(uniq))
    counts = np.bincount(inverse, minlength=len(uniq)).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(draws, len(uniq)))
    stats = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return {"point": float(values.mean()), "lo": float(np.percentile(stats, 5)), "hi": float(np.percentile(stats, 95)), "n_units": int(len(uniq))}


def _arm_metrics(rows: pd.DataFrame, prefix: str, h: int) -> dict:
    y = rows[f"appear_{h}"].to_numpy(float)
    pts = rows[f"points_{h}"].to_numpy(float)
    p = rows[f"{prefix}_p_appear"].to_numpy(float)
    ep = rows[f"{prefix}_e_points"].to_numpy(float)
    err = ep - pts
    return {"n": int(len(rows)), "brier": float(np.mean((p - y) ** 2)), "rmse_points": float(np.sqrt(np.mean(err ** 2))),
            "mae_points": float(np.mean(np.abs(err))), "bias_points": float(np.mean(err)), "mean_p_appear": float(np.mean(p)),
            "appear_rate": float(np.mean(y))}


def _calibration(rows: pd.DataFrame, prefix: str, h: int) -> dict:
    y = rows[f"appear_{h}"].to_numpy(float)
    p = rows[f"{prefix}_p_appear"].to_numpy(float)
    bins = min(5, len(rows))
    rel = []
    if bins >= 2:
        q = pd.qcut(pd.Series(p).rank(method="first"), q=bins, labels=False)
        for b in range(bins):
            m = (q == b).to_numpy()
            rel.append({"bin": int(b), "n": int(m.sum()), "mean_p": float(p[m].mean()), "observed": float(y[m].mean())})
    slope, intercept = (float("nan"), float("nan"))
    if len(rows) >= 3 and float(np.std(p)) > 0:
        slope, intercept = (float(v) for v in np.polyfit(p, y, 1))
    return {"reliability": rel, "slope": slope, "intercept": intercept}


def evaluate_candidate(population: pd.DataFrame, *, origins=range(2012, 2026), horizons=HORIZONS, seed: int, draws: int) -> dict:
    """Walk-forward evaluation: at origin T fit on rows with c + h < T, predict class T-1; every metric on the SAME paired
    supported rows (candidate AND B1 AND B2 supported); paired 90% player-cluster bootstrap vs B1; per-horizon selection."""
    per_h: dict[str, dict] = {}
    all_rows = []
    for h in horizons:
        collected = []
        fold_support = []
        for T in origins:
            train = population.loc[(population["draft_season"] + h < T) & population[f"appear_{h}"].notna()]
            test = population.loc[(population["draft_season"] == T - 1) & population[f"appear_{h}"].notna()].copy()
            fit = fit_arms(train, horizon=h, origin=T)
            fold_support.append({"origin": int(T), "train_rows": fit["candidate"]["n_train"], "train_appearers": fit["candidate"]["n_appearers"],
                                 "candidate_supported": bool(fit["candidate"]["supported"]), "candidate_reason": fit["candidate"]["reason"],
                                 "b1_cells": {p: {"n": c["n"], "appearers": c["appearers"], "supported": c["supported"], "conditional_supported": c["conditional_supported"]}
                                              for p, c in fit["b1"]["cells"].items()}, "test_rows": int(len(test))})
            if not len(test):
                continue
            pred = predict_arms(fit, test)
            merged = test.reset_index(drop=True).join(pred.drop(columns=["gsis_id"]))
            merged["origin"] = int(T)
            merged["horizon"] = int(h)
            collected.append(merged)
        if not collected:
            per_h[str(h)] = {"paired_rows": 0, "selection": "unsupported", "support": {"folds": fold_support}}
            continue
        rows = pd.concat(collected, ignore_index=True)
        paired = rows.loc[rows["candidate_supported"] & rows["b1_supported"] & rows["b2_supported"]].copy()
        excluded = int(len(rows) - len(paired))
        block: dict = {"paired_rows": int(len(paired)), "total_test_rows": int(len(rows)),
                       "support": {"folds": fold_support, "excluded_rows_unsupported": excluded}}
        if len(paired) == 0:
            block["selection"] = "unsupported"
            per_h[str(h)] = block
            continue
        block["arms"] = {arm: _arm_metrics(paired, arm, h) for arm in ARMS}
        y = paired[f"appear_{h}"].to_numpy(float)
        pts = paired[f"points_{h}"].to_numpy(float)
        units = paired["gsis_id"].astype(str).to_numpy()
        diffs = {}
        for arm in ("candidate", "b2"):
            brier_d = (paired[f"{arm}_p_appear"].to_numpy(float) - y) ** 2 - (paired["b1_p_appear"].to_numpy(float) - y) ** 2
            sq_d = (paired[f"{arm}_e_points"].to_numpy(float) - pts) ** 2 - (paired["b1_e_points"].to_numpy(float) - pts) ** 2
            rmse_a = float(np.sqrt(np.mean((paired[f"{arm}_e_points"].to_numpy(float) - pts) ** 2)))
            rmse_b = float(np.sqrt(np.mean((paired["b1_e_points"].to_numpy(float) - pts) ** 2)))
            rmse_boot = _cluster_bootstrap(sq_d, units, seed=seed, draws=draws)
            diffs[arm] = {"brier_diff": _cluster_bootstrap(brier_d, units, seed=seed, draws=draws),
                          "mean_sq_err_points_diff": rmse_boot,
                          "rmse_points_diff": {"point": rmse_a - rmse_b, "lo": rmse_boot["lo"], "hi": rmse_boot["hi"],
                                               "note": "point = RMSE difference; lo/hi = 90% player-cluster interval on the paired mean "
                                                       "squared-error difference, which has the same sign"}}
        block["paired_vs_b1"] = diffs["candidate"]
        block["b2_vs_b1_exploratory"] = diffs["b2"]
        d = diffs["candidate"]
        selected = "cold_start_candidate" if (d["brier_diff"]["hi"] < 0 and d["rmse_points_diff"]["hi"] < 0) else "baseline_research_candidate"
        block["selection"] = selected
        block["selection_rule"] = SELECTION_RULE
        block["by_origin"] = {str(int(T)): {arm: _arm_metrics(g, arm, h) for arm in ARMS} for T, g in paired.groupby("origin", sort=True)}
        block["by_position"] = {str(p): {arm: _arm_metrics(g, arm, h) for arm in ARMS} for p, g in paired.groupby("draft_position", sort=True)}
        block["calibration"] = {arm: _calibration(paired, arm, h) for arm in ARMS}
        block["label_sources"] = {str(k): int(v) for k, v in paired[f"label_source_{h}"].value_counts().items()}
        per_h[str(h)] = block
        all_rows.append(paired.assign(horizon=h))
    return {"horizons": per_h, "origins": [int(t) for t in origins], "seed": int(seed), "draws": int(draws),
            "selection_rule": SELECTION_RULE, "caveats": CAVEATS,
            "support_floors": {"candidate_min_train": CANDIDATE_MIN_TRAIN, "candidate_min_appearers": CANDIDATE_MIN_APPEARERS,
                               "b1_min_position_rows": B1_MIN_POSITION_ROWS, "b1_min_conditional_appearers": B1_MIN_CONDITIONAL_APPEARERS},
            "paired_rows_frame": pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()}


def export_sidecar(candidates: pd.DataFrame, predictions: pd.DataFrame, *, selected_per_horizon: dict, origin_year: int) -> pd.DataFrame:
    """Sidecar rows for the 2026 candidates: per horizon the selected arm's numbers (or none), explicit seasons and classes."""
    pred = predictions.copy()
    pred["gsis_id"] = pred["gsis_id"].astype(str)
    if pred["gsis_id"].duplicated().any():
        raise ValueError("predictions are not unique by gsis_id")
    pred = pred.set_index("gsis_id")
    rows = []
    for _, c in candidates.iterrows():
        pid = str(c["gsis_id"])
        if pid not in pred.index:
            raise ValueError(f"{c['name']} ({pid}) has no prediction row; refusing to export")
        p = pred.loc[pid]
        row = {"sleeper_id": str(c["sleeper_id"]), "gsis_id": pid, "name": c["name"], "draft_position": c["draft_position"],
               "route": c.get("route"), "draft_status": c.get("draft_status"), "origin_year": int(origin_year)}
        for j in range(1, 6):
            sel = selected_per_horizon.get(j, "unsupported")
            arm = "candidate" if sel == "cold_start_candidate" else ("b1" if sel == "baseline_research_candidate" else None)
            supported = bool(p.get(f"{arm}_supported_{j}", False)) if arm else False
            if arm is None or not supported:
                sel = "unsupported"
            row[f"season_year{j}"] = int(origin_year) + j - 1
            row[f"estimate_class_year{j}"] = sel
            names = {"p_appear": f"p_appear_year{j}", "e_points": f"e_points_year{j}", "e_games": f"e_games_year{j}",
                     "e_points_given_appear": f"e_points_year{j}_given_appear", "e_games_given_appear": f"e_games_year{j}_given_appear"}
            for q, out_name in names.items():
                val = p.get(f"{arm}_{q}_{j}") if arm else None
                row[out_name] = float(val) if (arm and sel != "unsupported" and val is not None and pd.notna(val)) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
