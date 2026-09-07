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
    "assert_capture_coverage",
    "evaluate_candidate",
    "export_sidecar",
    "first_full_reg_season",
    "fit_arms",
    "never_record_population",
    "paired_rmse_bootstrap",
    "predict_arms",
    "render_candidate_report",
    "support_table",
    "unresolved_from_ledger",
    "verify_capture",
    "write_candidate_run",
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


GSIS_PATTERN = r"\d{2}-\w+"  # two digits, a dash, a token: rejects placeholders like unresolved:2015:10 and bare ids


def _strict_bool(values: pd.Series, name: str) -> pd.Series:
    """True/False only; strings, NaN and anything else refuse — bool(NaN) and bool('False') are both True."""
    out = []
    for v in values.tolist():
        if isinstance(v, (bool, np.bool_)):
            out.append(bool(v))
        elif isinstance(v, (int, np.integer)) and not isinstance(v, bool) and v in (0, 1):
            out.append(bool(v))
        else:  # strings (even 'False'), NaN, floats and everything else refuse: the artifact writes real booleans
            raise ValueError(f"{name}: value {v!r} is not a strict boolean")
    return pd.Series(out, index=values.index, dtype=bool)


def assert_capture_coverage(capture_dir: Path | str, *, required_seasons) -> dict[str, str]:
    """Every required season must be declared exactly once with no recorded failure; an omitted season can never read
    as 'no NFL record'. Returns season -> declared file."""
    capture_dir = Path(capture_dir)
    manifest = json.loads((capture_dir / "manifest.json").read_text())
    failures = manifest.get("failures") or []
    if failures:
        raise ValueError(f"capture manifest records failures: {failures[:3]}")
    files = manifest.get("files") or {}
    entries = list(files.values()) if isinstance(files, dict) else list(files)
    by_season: dict[str, list[str]] = {}
    for meta in entries:
        season = meta.get("season") if isinstance(meta, dict) else None
        path = meta.get("path") if isinstance(meta, dict) else None
        if season is None:
            continue
        by_season.setdefault(str(int(season)), []).append(str(path))
    if isinstance(files, dict):
        by_season = {}
        for rel, meta in files.items():
            if isinstance(meta, dict) and meta.get("season") is not None:
                by_season.setdefault(str(int(meta["season"])), []).append(rel)
    out = {}
    for s in required_seasons:
        got = by_season.get(str(int(s)), [])
        if len(got) != 1:
            raise ValueError(f"capture does not affirm season {s} exactly once (found {len(got)} files); an omitted season is not 'no record'")
        out[str(int(s))] = got[0]
    return out


def _age_at(birth: pd.Series, year: pd.Series) -> np.ndarray:
    bd = pd.to_datetime(birth, errors="coerce")
    ref = pd.to_datetime(year.astype(int).astype(str) + AGE_MONTH_DAY)
    return ((ref - bd).dt.days / 365.25).to_numpy(dtype=float)


def never_record_population(*, cohort: pd.DataFrame, first_reg: pd.Series, outcomes: pd.DataFrame, players: pd.DataFrame,
                            last_complete_season: int) -> pd.DataFrame:
    """One row per eligible draftee (frozen definition) with origin-dated features and horizon labels."""
    if "label_basis" not in cohort.columns:
        raise ValueError("cohort carries no label_basis column; an affirmative resolved identity basis is required")
    basis = cohort["label_basis"].astype("string")
    resolved = basis.notna() & (basis.str.strip() != "") & (basis != "unresolved")
    c = cohort.loc[resolved.fillna(False).to_numpy()].copy()
    c["gsis_id"] = c["gsis_id"].astype(str)
    if not c["gsis_id"].str.fullmatch(GSIS_PATTERN).all():
        bad = c.loc[~c["gsis_id"].str.fullmatch(GSIS_PATTERN), "gsis_id"].head(5).tolist()
        raise ValueError(f"cohort rows with a resolved basis carry ids that are not gsis ids, e.g. {bad}")
    if c["gsis_id"].duplicated().any():
        raise ValueError(f"cohort has duplicate gsis ids, e.g. {c.loc[c['gsis_id'].duplicated(), 'gsis_id'].head(5).tolist()}")
    if c.duplicated(["draft_season", "pick"]).any():
        dup = c.loc[c.duplicated(["draft_season", "pick"], keep=False), ["gsis_id", "draft_season", "pick"]].head(5).to_dict("records")
        raise ValueError(f"cohort has duplicate draft keys (season, pick), e.g. {dup}")
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
    pl = players.loc[players["gsis_id"].notna(), ["gsis_id", "birth_date"]].copy()
    pl["gsis_id"] = pl["gsis_id"].astype(str)
    distinct = pl.dropna(subset=["birth_date"]).drop_duplicates()
    conflicting = distinct.loc[distinct["gsis_id"].duplicated(keep=False), "gsis_id"].unique()
    conflicting = [g for g in conflicting if g in set(pop["gsis_id"])]
    if conflicting:
        raise ValueError(f"conflicting birth dates in the players table for {conflicting[:5]}; refusing to choose one")
    birth = pop["gsis_id"].map(distinct.drop_duplicates("gsis_id").set_index("gsis_id")["birth_date"])
    pop["birth_date"] = birth
    pop["age_at_origin"] = _age_at(birth, pop["origin_year"])
    # labels from the artifact: complete season with no row -> convention zero; beyond last complete -> unknown
    o = outcomes.copy()
    o["player_id"] = o["player_id"].astype(str)
    o["appeared"] = _strict_bool(o["appeared"], "appeared")
    closed = o["season"].astype(int) <= last_complete_season
    for col in ("points", "games"):
        vals = pd.to_numeric(o[col], errors="coerce")
        bad = closed & (~np.isfinite(vals.to_numpy(float)))
        if bad.any():
            raise ValueError(f"outcome artifact: {int(bad.sum())} closed-season rows carry a missing or non-finite {col}; malformed, refusing")
        o[col] = vals
    if o.duplicated(["player_id", "season"]).any():
        raise ValueError("outcome artifact: duplicate (player_id, season) rows")
    games_closed = o.loc[closed, "games"].to_numpy(float)
    app_closed = o.loc[closed, "appeared"].to_numpy(bool)
    pts_closed = o.loc[closed, "points"].to_numpy(float)
    incoherent = (app_closed != (games_closed >= 1)) | ((pts_closed != 0.0) & ~app_closed) | (games_closed < 0) | (games_closed != np.floor(games_closed))
    if incoherent.any():
        sample = o.loc[closed].loc[incoherent, ["player_id", "season", "appeared", "points", "games"]].head(5).to_dict("records")
        raise ValueError(f"outcome artifact: {int(incoherent.sum())} closed rows are incoherent (appeared must equal games >= 1; points "
                         f"require an appearance; games integral and non-negative), e.g. {sample}")
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
            complete = population[f"appear_{h}"].notna() & population[f"points_{h}"].notna() & population[f"games_{h}"].notna()
            train = population.loc[(population["draft_season"] + h < T) & complete]
            test = population.loc[(population["draft_season"] == T - 1) & complete]
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
B1_MIN_CONDITIONAL_APPEARERS = 1  # frozen: zero appearers -> conditional unsupported; >= 1 gives a ROUGH conditional baseline
L2_C = 1.0
RIDGE_ALPHA = 1.0
GAMES_BOUND = (1, 17)  # declared before fitting: conditional games (given appearance) are bounded to the modern window; points are never clamped
ARMS = ("candidate", "b1", "b2")
SELECTION_RULE = ("per horizon, on the same paired supported rows: the candidate is selected only if BOTH the paired Brier(appear) "
                  "difference and the paired RMSE(unconditional points) difference vs B1 have 90% player-cluster bootstrap "
                  "intervals entirely below zero; otherwise B1's estimate is a baseline_research_candidate with its measured "
                  "out-of-time error and support; a horizon whose arms are unsupported at the final origin is unsupported")
CAVEATS = {
    "selection": ("selecting a policy on this historical evaluation is retrospective model selection, NOT independent confirmation "
                  "of the selected policy; both arms are reported at every horizon"),
    "bootstrap": ("the 90% intervals are player-cluster bootstraps conditional on the fixed fits and the realized origins 2012-2025; "
                  "they carry no season or model-fit uncertainty and are not forecast intervals"),
    "population": ("a draft-population prior for drafted players with no rookie-year regular-season record; not conditioned on remaining "
                   "on a current roster; direction and size of this mismatch have not been measured"),
    "appearance": "P(appear) is the probability of at least one championship-window stat row; it is not a breakout or usefulness probability",
    "horizons": "each horizon is fitted, evaluated and selected independently; acceptance at one horizon never validates another",
    "labels": "a complete season with no artifact row is the producers' shared convention zero (tagged); seasons beyond 2025 are unknown",
    "scoring": ("outcomes are the common research default PPR championship-window target (nflverse default scoring), not exact league "
                "scoring; league_scoring_exact is false on the bound artifact"),
}


PROB_BLOCK_CANDIDATE = ("log_pick", "round", "age_at_origin")   # + position dummies
PROB_BLOCK_B2 = ("log_pick", "round")                          # + position dummies (age removed; exploratory)
COND_BLOCK = ("log_pick",)                                       # + position dummies (frozen conditional features)


def _design(frame: pd.DataFrame, *, block: tuple[str, ...], positions: tuple[str, ...], age_median: dict | None) -> np.ndarray:
    cols = []
    for name in block:
        if name == "age_at_origin":
            age = frame["age_at_origin"].to_numpy(float).copy()
            fill = frame["draft_position"].map(age_median or {}).to_numpy(float)
            cols.append(np.where(np.isnan(age), fill, age))
        else:
            cols.append(frame[name].to_numpy(float))
    pos = frame["draft_position"].to_numpy()
    for p in positions:
        cols.append((pos == p).astype(float))
    return np.column_stack(cols)


def _block_names(block: tuple[str, ...], positions: tuple[str, ...]) -> list[str]:
    return list(block) + [f"pos_{p}" for p in positions]


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
    prob_block = PROB_BLOCK_CANDIDATE if with_age else PROB_BLOCK_B2
    age_fallback = None
    if with_age:
        ages = train["age_at_origin"]
        missing = ages.isna()
        pos_has = train["draft_position"].map(lambda p: ages[train["draft_position"] == p].notna().any())
        age_fallback = {"rule": "training position median first, then the overall training median only when the same position has no observed age; "
                                "unsupported when no training age exists at all (ex-ante missing-feature rule)",
                        "observed": int((~missing).sum()), "position_median": int((missing & pos_has).sum()),
                        "overall_median": int((missing & ~pos_has).sum())}
    out = {"supported": not reasons, "age_fallback": age_fallback, "reason": "; ".join(reasons) if reasons else None, "n_train": int(len(train)), "n_appearers": int(y.sum()),
           "positions": positions, "with_age": with_age, "age_median_by_position": age_median,
           "feature_blocks": {"probability": _block_names(prob_block, positions), "conditional": _block_names(COND_BLOCK, positions)}}
    if reasons:
        return out
    X = _design(train, block=prob_block, positions=positions, age_median=age_median)
    scaler = StandardScaler().fit(X)
    logit = LogisticRegression(C=L2_C, max_iter=2000).fit(scaler.transform(X), y)
    app = y == 1.0
    Xc = _design(train.loc[app], block=COND_BLOCK, positions=positions, age_median=None)
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
    prob_block = PROB_BLOCK_CANDIDATE if fit["with_age"] else PROB_BLOCK_B2
    X = _design(frame, block=prob_block, positions=fit["positions"], age_median=fit["age_median_by_position"])
    p = fit["logit"].predict_proba(fit["scaler"].transform(X))[:, 1]
    Xc = _design(frame, block=COND_BLOCK, positions=fit["positions"], age_median=None)
    pts = fit["ridge_points"].predict(fit["scaler_c"].transform(Xc))
    games = np.clip(fit["ridge_games"].predict(fit["scaler_c"].transform(Xc)), GAMES_BOUND[0], GAMES_BOUND[1])
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


def paired_rmse_bootstrap(pred_a: np.ndarray, pred_b: np.ndarray, actual: np.ndarray, units: np.ndarray, *, seed: int, draws: int) -> dict:
    """RMSE(a) - RMSE(b) with a 90% player-cluster interval computed IN RMSE UNITS: each draw resamples units, recomputes
    both arms' mean squared error on the resampled rows, and takes sqrt(mean SE a) - sqrt(mean SE b)."""
    se_a = (np.asarray(pred_a, float) - np.asarray(actual, float)) ** 2
    se_b = (np.asarray(pred_b, float) - np.asarray(actual, float)) ** 2
    uniq, inverse = np.unique(np.asarray(units), return_inverse=True)
    sum_a = np.bincount(inverse, weights=se_a, minlength=len(uniq))
    sum_b = np.bincount(inverse, weights=se_b, minlength=len(uniq))
    counts = np.bincount(inverse, minlength=len(uniq)).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(draws, len(uniq)))
    n = counts[idx].sum(axis=1)
    stats = np.sqrt(sum_a[idx].sum(axis=1) / n) - np.sqrt(sum_b[idx].sum(axis=1) / n)
    point = float(np.sqrt(se_a.mean()) - np.sqrt(se_b.mean()))
    return {"point": point, "lo": float(np.percentile(stats, 5)), "hi": float(np.percentile(stats, 95)), "n_units": int(len(uniq)),
            "units": "RMSE points"}


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
            complete = population[f"appear_{h}"].notna() & population[f"points_{h}"].notna() & population[f"games_{h}"].notna()
            train = population.loc[(population["draft_season"] + h < T) & complete]
            test = population.loc[(population["draft_season"] == T - 1) & complete].copy()
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
            diffs[arm] = {"brier_diff": _cluster_bootstrap(brier_d, units, seed=seed, draws=draws),
                          "mean_sq_err_points_diff": _cluster_bootstrap(sq_d, units, seed=seed, draws=draws),
                          "rmse_points_diff": paired_rmse_bootstrap(paired[f"{arm}_e_points"].to_numpy(float), paired["b1_e_points"].to_numpy(float),
                                                                    pts, units, seed=seed, draws=draws)}
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


SIDECAR_ROUTE = "never_appeared_drafted"
SIDECAR_CLASS_YEAR = 2025
REQUIRED_BINDING = ("origin_year", "capture_manifest_sha256", "artifact_sha256", "cohort_sha256", "coverage_run")


def export_sidecar(candidates: pd.DataFrame, predictions: pd.DataFrame, *, selected_per_horizon: dict, origin_year: int,
                   binding: dict | None = None) -> pd.DataFrame:
    """Sidecar rows for the verified new-eligible candidates only; per horizon the selected arm's numbers or an explicit
    'unsupported'. Refuses invalid or duplicate identities, a wrong route/class/draft position, a missing or conflicting
    origin/binding, invalid support flags, non-finite values, probabilities outside [0, 1], impossible games and a
    P × conditional mismatch. Never touches the accepted 825 or the recovery rows."""
    binding = binding or {}
    missing_b = [k for k in REQUIRED_BINDING if not binding.get(k)]
    if missing_b:
        raise ValueError(f"sidecar binding is incomplete: missing {missing_b}")
    if int(binding["origin_year"]) != int(origin_year):
        raise ValueError(f"origin year {origin_year} conflicts with the binding's origin_year {binding['origin_year']}")
    if int(origin_year) != SIDECAR_CLASS_YEAR + 1:
        raise ValueError(f"origin year must be exactly draft season + 1 = {SIDECAR_CLASS_YEAR + 1} (seasons {SIDECAR_CLASS_YEAR + 1}-{SIDECAR_CLASS_YEAR + 5}); got {origin_year}")
    c = candidates.copy()
    c["gsis_id"] = c["gsis_id"].astype(str)
    c["sleeper_id"] = c["sleeper_id"].astype(str)
    if c["gsis_id"].duplicated().any() or c["sleeper_id"].duplicated().any():
        raise ValueError("duplicate candidate identities (gsis_id or sleeper_id)")
    if "identity_status" not in c.columns or (c["identity_status"].astype(str) != "verified_nfl_join").any():
        raise ValueError("every candidate needs identity_status == verified_nfl_join")
    if (c["route"].astype(str) != SIDECAR_ROUTE).any():
        raise ValueError(f"every candidate must carry route {SIDECAR_ROUTE!r}")
    if (c["draft_season"].astype(int) != SIDECAR_CLASS_YEAR).any():
        raise ValueError(f"every candidate must be a {SIDECAR_CLASS_YEAR} draftee")
    if (~c["draft_position"].isin(SKILL_POSITIONS)).any():
        raise ValueError("every candidate must carry a skill draft position (QB/RB/WR/TE)")
    if "draft_status" not in c.columns or (c["draft_status"].astype(str) != "drafted_verified").any():
        raise ValueError("every candidate must be affirmatively drafted_verified")
    pred = predictions.copy()
    pred["gsis_id"] = pred["gsis_id"].astype(str)
    if pred["gsis_id"].duplicated().any():
        raise ValueError("predictions are not unique by gsis_id")
    pred = pred.set_index("gsis_id")
    rows = []
    for _, r in c.iterrows():
        pid = r["gsis_id"]
        if pid not in pred.index:
            raise ValueError(f"{r['name']} ({pid}) has no prediction row; refusing to export")
        p = pred.loc[pid]
        row = {"sleeper_id": r["sleeper_id"], "gsis_id": pid, "name": r["name"], "draft_position": r["draft_position"],
               "route": r["route"], "draft_status": r.get("draft_status"), "origin_year": int(origin_year),
               "source_binding": json.dumps({k: binding[k] for k in REQUIRED_BINDING}, sort_keys=True)}
        for j in range(1, 6):
            sel = selected_per_horizon.get(j, "unsupported")
            arm = "candidate" if sel == "cold_start_candidate" else ("b1" if sel == "baseline_research_candidate" else None)
            row[f"season_year{j}"] = int(origin_year) + j - 1
            names = {"p_appear": f"p_appear_year{j}", "e_points": f"e_points_year{j}", "e_games": f"e_games_year{j}",
                     "e_points_given_appear": f"e_points_year{j}_given_appear", "e_games_given_appear": f"e_games_year{j}_given_appear"}
            if arm is not None:
                flag = p.get(f"{arm}_supported_{j}")
                if not isinstance(flag, (bool, np.bool_)):
                    raise ValueError(f"{r['name']} ({pid}) horizon {j}: {arm}_supported flag {flag!r} is not a strict boolean")
                if not bool(flag):
                    sel, arm = "unsupported", None
            row[f"estimate_class_year{j}"] = sel
            if arm is None:
                for out_name in names.values():
                    row[out_name] = np.nan
                continue
            vals = {q: p.get(f"{arm}_{q}_{j}") for q in names}
            cond_missing = [q for q in ("e_points_given_appear", "e_games_given_appear") if vals[q] is None or pd.isna(vals[q])]
            if cond_missing and arm == "b1":
                # a declared-unsupported baseline conditional cell: the horizon is explicitly unsupported, never a partial path
                row[f"estimate_class_year{j}"] = "unsupported"
                for out_name in names.values():
                    row[out_name] = np.nan
                continue
            if cond_missing:
                raise ValueError(f"{r['name']} ({pid}) horizon {j}: a supported {arm} carries no conditional value for {cond_missing}; the conditional is required")
            for q in ("p_appear", "e_points", "e_games", "e_points_given_appear", "e_games_given_appear"):
                v = vals[q]
                if v is None or not np.isfinite(float(v)):
                    raise ValueError(f"{r['name']} ({pid}) horizon {j}: {arm} {q} is not finite")
            pv = float(vals["p_appear"])
            if not (0.0 <= pv <= 1.0):
                raise ValueError(f"{r['name']} ({pid}) horizon {j}: probability {pv} outside [0, 1]")
            g = float(vals["e_games_given_appear"])
            if not (GAMES_BOUND[0] <= g <= GAMES_BOUND[1]):
                raise ValueError(f"{r['name']} ({pid}) horizon {j}: conditional games {g} outside {GAMES_BOUND}")
            if abs(pv * g - float(vals["e_games"])) > 1e-6 or not (0.0 <= float(vals["e_games"]) <= GAMES_BOUND[1]):
                raise ValueError(f"{r['name']} ({pid}) horizon {j}: e_games {vals['e_games']} is not P x conditional games {pv * g} within bounds")
            cp = float(vals["e_points_given_appear"])
            if abs(pv * cp - float(vals["e_points"])) > 1e-6:
                raise ValueError(f"{r['name']} ({pid}) horizon {j}: e_points {vals['e_points']} != P x conditional product {pv * cp}")
            for q, out_name in names.items():
                v = vals[q]
                row[out_name] = float(v) if (v is not None and pd.notna(v)) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- unresolved list and the immutable run writer

NEXT_EXPERIMENT = {
    "never_appeared_no_draft_record": ("no draft record in any held source, no championship-window row: a separately specified no-record "
                                       "entry cohort (entry season, position, age) with its own frozen population is the smallest valid next "
                                       "experiment; no roster-survivor selection"),
    "dormant_drafted": "appeared before, then absent: a dormant-return experiment on last observed production and absence length (separate population)",
    "dormant_no_draft_record": "appeared before, then absent, no draft record: the dormant-return experiment without draft features",
    "draft_sources_conflict_unresolved": "adjudicate the conflicting draft records at the source before any estimate",
    "no_held_source_history": "no entry/draft history in any held source: acquire a source-backed entry record before any estimate",
    "never_appeared_drafted": "drafted, no rookie-year record, but outside the frozen candidate population (class or draft position): a separately frozen population",
}


def unresolved_from_ledger(ledger: pd.DataFrame, *, candidate_ids: set) -> pd.DataFrame:
    """Every ledger player NOT in the candidate set, with an honest reason and the smallest valid next experiment.
    Recovered join failures are listed with their own status; nothing here is an estimate."""
    rows = []
    for _, r in ledger.iterrows():
        pid = str(r["gsis_id"])
        if pid in candidate_ids:
            continue
        route = str(r["route"])
        if route == "existing_forecast_join_failure":
            rows.append({"sleeper_id": str(r["sleeper_id"]), "gsis_id": pid, "name": r["name"], "route": route, "status": "recovered_existing_forecast",
                         "why": "an accepted DG-177 forecast exists for this identity; delivered in the coverage run's recovery sidecar, not re-estimated",
                         "smallest_next_experiment": "none needed; consumption is root's numerical/identity acceptance"})
            continue
        why = ""
        dp = str(r.get("draft_position"))
        if route.endswith("_drafted") and dp not in SKILL_POSITIONS:
            why = f"draft position {dp} is outside the skill cohort (QB/RB/WR/TE); no silent mapping to a skill prior"
        elif route == "never_appeared_drafted":
            why = f"drafted in {r.get('entry_season')}, outside the frozen 2025-class candidate population"
        else:
            why = {"never_appeared_no_draft_record": "no draft record in the held sources and no championship-window stat row",
                   "dormant_drafted": "appeared before and left DG-177's cohort after two absent seasons",
                   "dormant_no_draft_record": "appeared before and left DG-177's cohort after two absent seasons; no draft record",
                   "draft_sources_conflict_unresolved": "positive draft records disagree across sources",
                   "no_held_source_history": "no entry/draft history in any held source; current census identity verified"}.get(route, route)
        rows.append({"sleeper_id": str(r["sleeper_id"]), "gsis_id": pid, "name": r["name"], "route": route, "status": "unresolved", "why": why,
                     "smallest_next_experiment": NEXT_EXPERIMENT.get(route, "a separately specified population")})
    return pd.DataFrame(rows)


CANDIDATE_OUTPUTS = ("population.csv", "support.csv", "evaluation.json", "paired_rows.csv", "cold_start_estimates.csv", "unresolved.csv",
                     "REPORT.md", "manifest.json")


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.DataFrame):
        return f"<frame {len(value)} rows>"
    return value


def _fmt(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def render_candidate_report(evaluation: dict, support: pd.DataFrame, sidecar: pd.DataFrame, unresolved: pd.DataFrame) -> str:
    cav = evaluation["caveats"]
    lines = ["# DG-165 cold-start candidate — drafted players with no rookie-year regular-season record", "",
             f"Population caveat: {cav['population']}.", f"Selection caveat: {cav['selection']}.", f"Appearance: {cav['appearance']}.", "",
             f"Selection rule: {evaluation['selection_rule']}", "", "## Per horizon (career years 2–6)", ""]
    for h, b in evaluation["horizons"].items():
        lines.append(f"### Horizon {h}")
        if b.get("paired_rows", 0) == 0:
            lines += ["", "No paired supported rows; unsupported.", ""]
            continue
        lines += ["", f"Paired supported rows: {b['paired_rows']} of {b['total_test_rows']} test rows (excluded as unsupported: {b['support']['excluded_rows_unsupported']}).", "",
                  "| arm | n | Brier(appear) | RMSE points | MAE points | bias points |", "|---|---|---|---|---|---|"]
        for arm, m in b["arms"].items():
            lines.append(f"| {arm} | {m['n']} | {_fmt(m['brier'], 4)} | {_fmt(m['rmse_points'])} | {_fmt(m['mae_points'])} | {_fmt(m['bias_points'])} |")
        d = b["paired_vs_b1"]
        lines += ["", f"Candidate − B1, 90% player-cluster intervals: Brier {_fmt(d['brier_diff']['point'], 4)} [{_fmt(d['brier_diff']['lo'], 4)}, {_fmt(d['brier_diff']['hi'], 4)}]; "
                  f"RMSE points {_fmt(d['rmse_points_diff']['point'])} [{_fmt(d['rmse_points_diff']['lo'])}, {_fmt(d['rmse_points_diff']['hi'])}] (RMSE units).",
                  f"**Selection at this horizon: {b['selection']}** (both arms reported; this is retrospective model selection).", "",
                  "| draft position | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |", "|---|---|---|---|---|---|"]
        for pos, m in b["by_position"].items():
            lines.append(f"| {pos} | {m['candidate']['n']} | {_fmt(m['candidate']['brier'], 4)} | {_fmt(m['b1']['brier'], 4)} | {_fmt(m['candidate']['rmse_points'])} | {_fmt(m['b1']['rmse_points'])} |")
        lines += ["", "| origin | n | candidate Brier | B1 Brier | candidate RMSE | B1 RMSE |", "|---|---|---|---|---|---|"]
        for T, m in b["by_origin"].items():
            lines.append(f"| {T} | {m['candidate']['n']} | {_fmt(m['candidate']['brier'], 4)} | {_fmt(m['b1']['brier'], 4)} | {_fmt(m['candidate']['rmse_points'])} | {_fmt(m['b1']['rmse_points'])} |")
        lines.append("")
    lines += ["## Support (recorded before fitting)", "", f"{len(support)} origin × horizon cells; see support.csv for training rows, appearers, per-position counts and test rows.", ""]
    lines += ["## Sidecar", "", f"{len(sidecar)} candidate rows; estimate classes per horizon: "
              + "; ".join(f"year {j}: " + ", ".join(f"{k} {v}" for k, v in sidecar[f'estimate_class_year{j}'].value_counts().items()) for j in range(1, 6) if len(sidecar)), ""]
    n_unres = int((unresolved["status"] == "unresolved").sum()) if "status" in unresolved.columns else int(len(unresolved))
    n_rec = int((unresolved["status"] == "recovered_existing_forecast").sum()) if "status" in unresolved.columns else 0
    lines += ["## Status partition", "", f"{len(sidecar)} new candidate rows; {n_unres} unresolved (no new estimate; see unresolved.csv for the reason and the "
              f"smallest valid next experiment per player); {n_rec} recovered existing forecasts (delivered by the coverage run's recovery sidecar, "
              "not re-estimated).", ""]
    lines += ["## Scoring and interval conditions", "", "Outcomes are the common research default PPR championship-window target, not exact league scoring "
              "(league_scoring_exact is false on the bound artifact). Intervals are conditional on the fixed fits and the realized origins; they carry "
              "no season or model-fit uncertainty.", ""]
    lines += ["## Caveats", ""] + [f"- **{k}**: {v}" for k, v in cav.items()] + [""]
    return "\n".join(lines)


def write_candidate_run(run_dir: Path, *, population: pd.DataFrame, support: pd.DataFrame, evaluation: dict, paired_rows: pd.DataFrame,
                        sidecar: pd.DataFrame, unresolved: pd.DataFrame, inputs: dict, git_sha: str, launched_utc: str | None = None) -> dict:
    """``git_sha`` and ``launched_utc`` are the LAUNCH provenance captured before any work; written_utc is the write time."""
    from datetime import datetime, timezone
    run_dir = Path(run_dir)
    existing = [n for n in CANDIDATE_OUTPUTS if (run_dir / n).exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing candidate outputs in {run_dir}: {existing}")
    ev = {k: v for k, v in evaluation.items() if k != "paired_rows_frame"}
    population.to_csv(run_dir / "population.csv", index=False)
    support.to_csv(run_dir / "support.csv", index=False)
    (run_dir / "evaluation.json").write_text(json.dumps(_jsonable(ev), indent=2, sort_keys=True, allow_nan=False))
    paired_rows.to_csv(run_dir / "paired_rows.csv", index=False)
    sidecar.to_csv(run_dir / "cold_start_estimates.csv", index=False)
    unresolved.to_csv(run_dir / "unresolved.csv", index=False)
    (run_dir / "REPORT.md").write_text(render_candidate_report(ev, support, sidecar, unresolved))
    names = [n for n in CANDIDATE_OUTPUTS if n != "manifest.json"]
    outputs = {n: _sha((run_dir / n).read_bytes()) for n in names}
    manifest = {"schema_version": "dg165_cold_start_candidate_v1", "ticket": "DG-165", "launch_git_sha": git_sha, "git_sha": git_sha,
                "launched_utc": launched_utc, "written_utc": datetime.now(timezone.utc).isoformat(), "run_dir": str(run_dir), "inputs": inputs,
                "selection_rule": SELECTION_RULE, "caveats": CAVEATS, "support_floors": ev.get("support_floors"),
                "feature_blocks": {"candidate_probability": list(PROB_BLOCK_CANDIDATE) + ["position dummies"], "conditional": list(COND_BLOCK) + ["position dummies"],
                                   "b2_probability": list(PROB_BLOCK_B2) + ["position dummies"]},
                "games_bound_declared": list(GAMES_BOUND), "seed": ev.get("seed"), "draws": ev.get("draws"), "origins": ev.get("origins"),
                "outputs_sha256": outputs, "frozen_inputs_untouched": True,
                "not": "a research candidate for root's review; the accepted 825 rows and the recovery sidecar are untouched"}
    (run_dir / "manifest.json").write_text(json.dumps(_jsonable(manifest), indent=2, sort_keys=True))
    return manifest
