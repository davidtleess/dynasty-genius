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
    "HORIZONS",
    "SKILL_POSITIONS",
    "first_full_reg_season",
    "never_record_population",
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
