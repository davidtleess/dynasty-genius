"""Rookie -> veteran transition audit (DG-165 build 2026-09-06): join the accepted rookie forecast
to the accepted veteran forecast on the same realized outcome and report paired errors, calibration
and an exclusions ledger. An AUDIT: it changes no player value and proposes no correction.

Fail-closed everywhere: an undeclared or altered input byte, a different outcome target, a
duplicate key or a label that differs between the two producers RAISES. Nothing falls back.

Experience k of a drafted player is feature_season - draft_season + 1 from the draft table.
DG-177's ``seasons_played`` is left-censored at 2005 and is never used for it.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "DRAFT_STATUS",
    "JOINED_COLUMNS",
    "LEDGER_CATEGORIES",
    "LABEL_ATOL",
    "THIN_HISTORY_MAX_GAMES",
    "RookieRun",
    "VeteranRun",
    "classify_draft_status",
    "coverage_ledger",
    "fold_sign_summary",
    "join_transition",
    "load_rookie_run",
    "load_veteran_run",
    "metrics_by",
    "overlap_classes",
    "paired_bootstrap",
    "paired_metrics",
    "rookie_draft_time_frame",
    "verify_same_target",
    "veteran_horizon1_frame",
    "veteran_population_ledger",
]

ROOKIE_FILES = ("cohort.csv", "out_of_time_predictions.csv")
LABEL_BASIS_UNRESOLVED = "unresolved"  # the only label_basis that means "identity unknown"; all others name the resolving source
SKILL_POSITIONS = ("QB", "RB", "WR", "TE")
DRAFT_STATUS = (
    "drafted_skill",                  # in the modelling cohort with a resolved identity
    "drafted_skill_unresolved",       # in the modelling cohort, identity unresolved (never reaches a veteran row)
    "drafted_skill_outside_cohort",   # raw draft table says a skill position, but outside the modelling cohort (e.g. pre-2001)
    "drafted_other_position",         # raw draft table says a non-skill position
    "no_draft_record",                # absent from the raw draft table: UNKNOWN draft status, not evidence of going undrafted
    "unknown_identity",               # the veteran side could not resolve the identity
)
ROOKIE_INPUT_FILES = {"inputs/nflverse_draft_picks.parquet": "nflverse_draft_picks"}
VETERAN_FILES = ("historical_predictions.csv", "basic_cohort.csv.gz")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_verified(run_dir: Path, name: str, declared: str | None) -> bytes:
    """Read a file once, hash those bytes, compare to the producer's declaration; the same bytes are parsed."""
    if not declared:
        raise ValueError(f"{run_dir}: manifest declares no sha256 for {name}")
    path = run_dir / name
    if not path.exists():
        raise ValueError(f"{run_dir}: declared file missing: {name}")
    data = path.read_bytes()
    actual = _sha(data)
    if actual != declared:
        raise ValueError(f"{run_dir}: sha256 mismatch for {name}: declared {declared[:12]}…, actual {actual[:12]}…")
    return data


@dataclass(frozen=True)
class RookieRun:
    run_dir: Path
    manifest: dict
    cohort: pd.DataFrame
    out_of_time: pd.DataFrame
    draft_picks: pd.DataFrame
    verified: dict[str, str]


@dataclass(frozen=True)
class VeteranRun:
    run_dir: Path
    manifest: dict
    historical: pd.DataFrame
    cohort: pd.DataFrame
    verified: dict[str, str]


def load_rookie_run(run_dir: Path | str) -> RookieRun:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    declared = manifest.get("outputs_sha256") or {}
    verified: dict[str, str] = {}
    raw: dict[str, bytes] = {}
    for name in ROOKIE_FILES:
        raw[name] = _read_verified(run_dir, name, declared.get(name))
        verified[name] = declared[name]
    for rel, key in ROOKIE_INPUT_FILES.items():
        sha = ((manifest.get("inputs") or {}).get(key) or {}).get("sha256")
        raw[rel] = _read_verified(run_dir, rel, sha)
        verified[rel] = sha
    cohort = pd.read_csv(io.BytesIO(raw["cohort.csv"]))
    oot = pd.read_csv(io.BytesIO(raw["out_of_time_predictions.csv"]))
    picks = pd.read_parquet(io.BytesIO(raw["inputs/nflverse_draft_picks.parquet"]))
    return RookieRun(run_dir, manifest, cohort, oot, picks, verified)


def load_veteran_run(run_dir: Path | str) -> VeteranRun:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    declared = manifest.get("outputs_sha256") or {}
    verified: dict[str, str] = {}
    raw: dict[str, bytes] = {}
    for name in VETERAN_FILES:
        raw[name] = _read_verified(run_dir, name, declared.get(name))
        verified[name] = declared[name]
    historical = pd.read_csv(io.BytesIO(raw["historical_predictions.csv"]))
    cohort = pd.read_csv(io.BytesIO(gzip.decompress(raw["basic_cohort.csv.gz"])))
    return VeteranRun(run_dir, manifest, historical, cohort, verified)


def verify_same_target(rookie: RookieRun, veteran: VeteranRun) -> dict:
    """Both producers must label from the SAME outcome artifact; asserted from identities, never assumed."""
    r = rookie.manifest.get("outcomes") or {}
    v = veteran.manifest.get("label_source") or {}
    pairs = {
        "target_identity": (r.get("target_identity"), v.get("target_identity")),
        "outcomes_csv_sha256": (r.get("csv_sha256"), v.get("csv_sha256")),
        "outcomes_manifest_sha256": (r.get("manifest_sha256"), v.get("manifest_sha256")),
        "scoring_preset": (r.get("scoring_preset"), v.get("scoring_preset")),
    }
    for key, (a, b) in pairs.items():
        if not a or not b:
            raise ValueError(f"{key}: missing on one side (rookie={a!r}, veteran={b!r})")
        if a != b:
            raise ValueError(f"{key}: rookie {str(a)[:16]}… != veteran {str(b)[:16]}…")
    return {"status": "same_target", **{k: a for k, (a, _) in pairs.items()}}


def classify_draft_status(player_ids: pd.Series, identity_status: pd.Series, rookie: RookieRun) -> pd.Series:
    """Drafted at a skill position (inside or outside the modelling cohort), drafted elsewhere, no draft
    record, or unknown identity — never conflated. Absence from the raw draft table is an UNKNOWN draft
    status while coverage and id matching are incomplete; it is not evidence that a player went undrafted."""
    cohort = rookie.cohort
    basis = cohort["label_basis"].astype(str)
    skill_resolved = set(cohort.loc[basis != LABEL_BASIS_UNRESOLVED, "gsis_id"].astype(str))
    skill_unresolved = set(cohort.loc[basis == LABEL_BASIS_UNRESOLVED, "gsis_id"].astype(str))
    picks = rookie.draft_picks.loc[rookie.draft_picks["gsis_id"].notna()]
    raw_position = {str(pid): str(pos) for pid, pos in zip(picks["gsis_id"], picks["position"])}
    out = []
    for pid, status in zip(player_ids.astype(str), identity_status.astype(str)):
        if status != "resolved":
            out.append("unknown_identity")
        elif pid in skill_resolved:
            out.append("drafted_skill")
        elif pid in skill_unresolved:
            out.append("drafted_skill_unresolved")
        elif pid in raw_position:
            out.append("drafted_skill_outside_cohort" if raw_position[pid] in SKILL_POSITIONS else "drafted_other_position")
        else:
            out.append("no_draft_record")
    return pd.Series(out, index=player_ids.index, dtype="object")


# ----------------------------------------------------------------------------- the join

JOINED_COLUMNS = [
    "player_id", "name", "draft_season", "pick", "round", "draft_position", "veteran_position", "experience",
    "target_season", "rookie_forecast_year", "rookie_information_through_season",
    "veteran_feature_season", "veteran_information_through_season", "information_gap_seasons",
    "appeared", "points", "games",
    "rookie_p_appear", "rookie_e_points", "rookie_e_points_given_appear", "rookie_e_games",
    "veteran_p_appear", "veteran_e_points", "veteran_e_points_given_appear", "veteran_e_games",
    "veteran_games_t", "thin_history", "veteran_row_without_window_appearance",
    "err_rookie", "err_veteran", "abs_err_rookie", "abs_err_veteran", "sq_err_rookie", "sq_err_veteran", "veteran_closer",
]
THIN_HISTORY_MAX_GAMES = 4
# Labels on both sides come from the SAME artifact and are exactly equal; "identical" means identical.
# A relative tolerance would pass 250 vs 250.002 while the audit claims identity, so there is none.
LABEL_ATOL = 1e-9


def _assert_unique(frame: pd.DataFrame, keys: list[str], what: str) -> None:
    dup = frame.duplicated(keys, keep=False)
    if dup.any():
        sample = frame.loc[dup, keys].head(5).to_dict("records")
        raise ValueError(f"{what}: keys {keys} are not unique; {int(dup.sum())} rows involved, e.g. {sample}")


def rookie_draft_time_frame(rookie: RookieRun, *, experience: int) -> pd.DataFrame:
    """The draft-time forecast for NFL season j = experience + 1 with its label, one row per player.

    Every row of the frozen history is a draft-time forecast (forecast_year == draft_season). A row
    that is not would be a different forecast origin; it is refused, never filtered in silence.
    """
    j = experience + 1
    oot = rookie.out_of_time
    off = oot["forecast_year"].astype(int) != oot["draft_season"].astype(int)
    if off.any():
        raise ValueError(
            f"rookie out_of_time_predictions carries {int(off.sum())} rows with forecast_year != draft_season; "
            "this audit compares the draft-time forecast only and will not choose among origins silently"
        )
    needed = [f"p_appear_year{j}", f"e_points_year{j}", f"e_points_year{j}_given_appear", f"e_games_year{j}",
              f"appear_{j}", f"points_{j}", f"games_{j}", f"appear_{experience}", f"games_{experience}"]
    missing = [c for c in needed if c not in oot.columns]
    if missing:
        raise ValueError(f"rookie out_of_time_predictions lacks {missing} for experience {experience}")
    frame = oot.copy()
    # the history's draft keys must be the cohort's draft keys
    cohort_keys = rookie.cohort.set_index(rookie.cohort["gsis_id"].astype(str))[["draft_season", "pick", "position"]]
    ids = frame["gsis_id"].astype(str)
    unknown_ids = sorted(set(ids) - set(cohort_keys.index))
    if unknown_ids:
        raise ValueError(f"rookie history carries {len(unknown_ids)} ids absent from cohort.csv, e.g. {unknown_ids[:5]}")
    ck = cohort_keys.loc[ids]
    disagree = (ck["draft_season"].to_numpy() != frame["draft_season"].to_numpy()) | (ck["pick"].to_numpy() != frame["pick"].to_numpy()) \
        | (ck["position"].astype(str).to_numpy() != frame["position"].astype(str).to_numpy())
    if disagree.any():
        sample = frame.loc[disagree, ["gsis_id", "draft_season", "pick", "position"]].head(5).to_dict("records")
        raise ValueError(f"rookie history draft keys disagree with cohort.csv on {int(disagree.sum())} rows, e.g. {sample}")
    out = pd.DataFrame({
        "player_id": ids.to_numpy(), "name": frame["name"].to_numpy(), "draft_season": frame["draft_season"].astype(int).to_numpy(),
        "pick": frame["pick"].astype(int).to_numpy(), "round": frame["round"].astype(int).to_numpy(),
        "draft_position": frame["position"].to_numpy(), "rookie_forecast_year": frame["forecast_year"].astype(int).to_numpy(),
        "rookie_p_appear": frame[f"p_appear_year{j}"].to_numpy(), "rookie_e_points": frame[f"e_points_year{j}"].to_numpy(),
        "rookie_e_points_given_appear": frame[f"e_points_year{j}_given_appear"].to_numpy(), "rookie_e_games": frame[f"e_games_year{j}"].to_numpy(),
        "rookie_label_appeared": frame[f"appear_{j}"].to_numpy(), "rookie_label_points": frame[f"points_{j}"].to_numpy(),
        "rookie_label_games": frame[f"games_{j}"].to_numpy(),
        "feature_season_window_appearance": frame[f"appear_{experience}"].to_numpy(),
    })
    out["veteran_feature_season"] = out["draft_season"] + experience - 1
    _assert_unique(out, ["player_id", "draft_season"], "rookie draft-time forecasts")
    return out


def veteran_horizon1_frame(veteran: VeteranRun) -> pd.DataFrame:
    """Horizon-1 rows with their labels and the feature season's games_t; a prediction without its
    feature row is a broken input and refuses (thin history must never default from a missing key)."""
    h = veteran.historical
    frame = h.loc[h["horizon"] == 1].copy()
    off = frame["forecast_season"].astype(int) != frame["feature_season"].astype(int) + 1
    if off.any():
        sample = frame.loc[off, ["player_id", "feature_season", "forecast_season"]].head(5).to_dict("records")
        raise ValueError(f"veteran horizon-1 rows with forecast_season != feature_season + 1: {int(off.sum())}, e.g. {sample}")
    out = pd.DataFrame({
        "player_id": frame["player_id"].astype(str).to_numpy(), "veteran_feature_season": frame["feature_season"].astype(int).to_numpy(),
        "veteran_forecast_season": frame["forecast_season"].astype(int).to_numpy(), "veteran_position": frame["position"].to_numpy(),
        "veteran_p_appear": frame["policy_p_appear_year1"].to_numpy(), "veteran_e_points": frame["policy_e_points_year1"].to_numpy(),
        "veteran_e_points_given_appear": frame["policy_e_points_year1_given_appear"].to_numpy(),
        "veteran_e_games": frame["policy_e_games_year1"].to_numpy(),
        "veteran_label_appeared": frame["appeared_year1"].to_numpy(), "veteran_label_points": frame["points_year1"].to_numpy(),
        "veteran_label_games": frame["games_year1"].to_numpy(),
    })
    _assert_unique(out, ["player_id", "veteran_feature_season"], "veteran horizon-1 predictions")
    c = veteran.cohort
    games = pd.DataFrame({"player_id": c["player_id"].astype(str).to_numpy(), "veteran_feature_season": c["feature_season"].astype(int).to_numpy(),
                          "veteran_games_t": c["games_t"].to_numpy()})
    _assert_unique(games, ["player_id", "veteran_feature_season"], "veteran basic cohort")
    merged = out.merge(games, on=["player_id", "veteran_feature_season"], how="left", indicator=True)
    orphan = merged["_merge"] != "both"
    if orphan.any():
        sample = merged.loc[orphan, ["player_id", "veteran_feature_season"]].head(5).to_dict("records")
        raise ValueError(f"{int(orphan.sum())} veteran predictions have no basic cohort feature row, e.g. {sample}")
    return merged.drop(columns="_merge")


def join_transition(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> pd.DataFrame:
    """Pair the draft-time rookie forecast for season experience+1 with the veteran forecast made after
    `experience` NFL seasons, on the same realized outcome, keyed by identity and years — never row order."""
    if experience < 1:
        raise ValueError("experience must be >= 1 (seasons of NFL information the veteran side has)")
    r = rookie_draft_time_frame(rookie, experience=experience)
    known = r["rookie_label_points"].notna() & r["rookie_label_appeared"].notna()
    r = r.loc[known]  # unknown labels are ledger rows (label_unknown), never joined rows
    v = veteran_horizon1_frame(veteran)
    j = r.merge(v, on=["player_id", "veteran_feature_season"], how="inner")
    wrong_year = j["veteran_forecast_season"] != j["draft_season"] + experience
    if wrong_year.any():
        sample = j.loc[wrong_year, ["player_id", "draft_season", "veteran_feature_season", "veteran_forecast_season"]].head(5).to_dict("records")
        raise ValueError(f"veteran forecast_season != draft_season + experience on {int(wrong_year.sum())} rows, e.g. {sample}")
    rp, vp = j["rookie_label_points"].to_numpy(float), j["veteran_label_points"].to_numpy(float)
    bad_p = ~(np.abs(rp - vp) <= LABEL_ATOL)  # NaN on either side is a mismatch
    bad_a = j["rookie_label_appeared"].to_numpy(float) != j["veteran_label_appeared"].to_numpy(float)
    bad_g = j["rookie_label_games"].to_numpy(float) != j["veteran_label_games"].to_numpy(float)
    bad = bad_p | bad_a | bad_g
    if bad.any():
        sample = j.loc[bad, ["player_id", "veteran_feature_season", "rookie_label_points", "veteran_label_points"]].head(5).to_dict("records")
        raise ValueError(f"label mismatch between producers on {int(bad.sum())} joined rows, e.g. {sample}")
    j["experience"] = experience
    j["target_season"] = j["draft_season"] + experience
    j["rookie_information_through_season"] = j["draft_season"] - 1
    j["veteran_information_through_season"] = j["veteran_feature_season"]
    j["information_gap_seasons"] = experience
    j["appeared"] = j["rookie_label_appeared"]
    j["points"] = j["rookie_label_points"]
    j["games"] = j["rookie_label_games"]
    j["thin_history"] = j["veteran_games_t"] <= THIN_HISTORY_MAX_GAMES
    j["veteran_row_without_window_appearance"] = (j["veteran_games_t"] >= 1) & (j["feature_season_window_appearance"] == 0)
    for side in ("rookie", "veteran"):
        j[f"err_{side}"] = j[f"{side}_e_points"] - j["points"]
        j[f"abs_err_{side}"] = j[f"err_{side}"].abs()
        j[f"sq_err_{side}"] = j[f"err_{side}"] ** 2
    j["veteran_closer"] = j["abs_err_veteran"] < j["abs_err_rookie"]
    j = j.sort_values(["experience", "draft_season", "pick", "player_id"]).reset_index(drop=True)
    return j[JOINED_COLUMNS]


# ----------------------------------------------------------------------------- ledgers

LEDGER_CATEGORIES = (
    "paired",
    "no_veteran_row_no_window_appearance",
    "no_veteran_row_despite_window_appearance",
    "veteran_row_without_rookie_forecast",
    "label_unknown",
    "outside_overlap_classes",
    "identity_unresolved",
)


def overlap_classes(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> list[int]:
    """Draft classes whose draft-time forecast exists AND whose veteran feature season is evaluated."""
    oot = rookie.out_of_time
    rookie_years = set(oot.loc[oot["forecast_year"] == oot["draft_season"], "draft_season"].astype(int))
    vet_years = set(veteran.historical.loc[veteran.historical["horizon"] == 1, "feature_season"].astype(int))
    return sorted(c for c in rookie_years if c + experience - 1 in vet_years)


def coverage_ledger(rookie: RookieRun, veteran: VeteranRun, *, experience: int) -> pd.DataFrame:
    """One row per cohort player; the denominator is the modelling cohort, never the paired set."""
    classes = set(overlap_classes(rookie, veteran, experience=experience))
    r = rookie_draft_time_frame(rookie, experience=experience).set_index("player_id")
    v = veteran_horizon1_frame(veteran).set_index(["player_id", "veteran_feature_season"])
    joined_ids = set(join_transition(rookie, veteran, experience=experience)["player_id"])
    rows = []
    for row in rookie.cohort.itertuples(index=False):
        pid = str(row.gsis_id)
        cls = int(row.draft_season)
        fs = cls + experience - 1
        appear_k = float(r.loc[pid, "feature_season_window_appearance"]) if pid in r.index else np.nan
        games_t = float(v.loc[(pid, fs), "veteran_games_t"]) if (pid, fs) in v.index else np.nan
        if str(row.label_basis) == LABEL_BASIS_UNRESOLVED:
            cat = "identity_unresolved"
        elif cls not in classes:
            cat = "outside_overlap_classes"
        elif pid in joined_ids:
            cat = "paired"
        elif pid in r.index and pd.isna(r.loc[pid, "rookie_label_points"]):
            cat = "label_unknown"
        elif (pid, fs) not in v.index:
            cat = "no_veteran_row_despite_window_appearance" if appear_k == 1 else "no_veteran_row_no_window_appearance"
        else:
            cat = "veteran_row_without_rookie_forecast"
        rows.append({"player_id": pid, "name": row.name, "draft_season": cls, "pick": int(row.pick),
                     "draft_position": row.position, "experience": experience, "category": cat,
                     "feature_season_window_appearance": appear_k, "veteran_games_t": games_t})
    out = pd.DataFrame(rows)
    if len(out) != len(rookie.cohort):
        raise AssertionError("ledger rows must equal cohort rows")
    return out


def veteran_population_ledger(rookie: RookieRun, veteran: VeteranRun, joined: pd.DataFrame, *, experience: int) -> pd.DataFrame:
    """Veteran horizon-1 rows at the overlap feature seasons, by draft status; drafted skill split paired/unpaired."""
    seasons = {c + experience - 1 for c in overlap_classes(rookie, veteran, experience=experience)}
    v = veteran_horizon1_frame(veteran)
    v = v.loc[v["veteran_feature_season"].isin(seasons)].copy()
    if "identity_status" in veteran.cohort.columns:
        ident = veteran.cohort.set_index([veteran.cohort["player_id"].astype(str), veteran.cohort["feature_season"].astype(int)])["identity_status"]
        status = pd.Series([ident.get((p, s), "unknown") for p, s in zip(v["player_id"], v["veteran_feature_season"])], index=v.index)
    else:
        status = pd.Series(["resolved"] * len(v), index=v.index)
    v["draft_status"] = classify_draft_status(v["player_id"], status, rookie)
    paired_keys = set(zip(joined["player_id"], joined["veteran_feature_season"]))
    is_paired = pd.Series([(p, s) in paired_keys for p, s in zip(v["player_id"], v["veteran_feature_season"])], index=v.index)
    v.loc[(v["draft_status"] == "drafted_skill") & is_paired, "draft_status"] = "drafted_skill_paired"
    v.loc[(v["draft_status"] == "drafted_skill") & ~is_paired, "draft_status"] = "drafted_skill_unpaired"
    out = v.groupby(["veteran_feature_season", "draft_status"]).size().rename("rows").reset_index()
    out["experience_note"] = ("experience is computed from the draft table for drafted players only; rows without a draft "
                              "record carry no experience (DG-177 seasons_played is left-censored at 2005)")
    return out


# ----------------------------------------------------------------------------- metrics

def _calibration_line(pred: np.ndarray, actual: np.ndarray) -> tuple[float, float]:
    """Slope and intercept of actual on predicted (1 and 0 when calibrated); NaN when undefined."""
    if len(pred) < 3 or float(np.nanstd(pred)) == 0.0:
        return float("nan"), float("nan")
    slope, intercept = np.polyfit(pred, actual, 1)
    return float(slope), float(intercept)


def paired_metrics(joined: pd.DataFrame) -> dict:
    """Accuracy (RMSE, MAE) and BIAS reported apart, appearance Brier and reliability, points calibration,
    and the paired differences (veteran minus rookie; negative favours the veteran)."""
    n = int(len(joined))
    out: dict = {"n": n}
    if n == 0:
        return out
    actual = joined["points"].to_numpy(float)
    appeared = joined["appeared"].to_numpy(float)
    for side in ("rookie", "veteran"):
        err = joined[f"err_{side}"].to_numpy(float)
        p = joined[f"{side}_p_appear"].to_numpy(float)
        slope, intercept = _calibration_line(joined[f"{side}_e_points"].to_numpy(float), actual)
        out[side] = {
            "rmse": float(np.sqrt(np.mean(err ** 2))), "mae": float(np.mean(np.abs(err))), "bias": float(np.mean(err)),
            "brier_appear": float(np.mean((p - appeared) ** 2)), "appear_base_rate": float(np.mean(appeared)),
            "mean_p_appear": float(np.mean(p)),
            "points_calibration_slope": slope, "points_calibration_intercept": intercept,
        }
    out["paired"] = {
        "mean_sq_err_diff": float(np.mean(joined["sq_err_veteran"] - joined["sq_err_rookie"])),
        "mean_abs_err_diff": float(np.mean(joined["abs_err_veteran"] - joined["abs_err_rookie"])),
        "brier_diff": float(np.mean((joined["veteran_p_appear"] - appeared) ** 2 - (joined["rookie_p_appear"] - appeared) ** 2)),
        "share_veteran_closer": float(np.mean(joined["veteran_closer"].astype(float))),
        "sign_convention": "veteran minus rookie; negative favours the veteran forecast",
    }
    bins = min(10, n)
    deciles = pd.qcut(joined["veteran_p_appear"].rank(method="first"), q=bins, labels=False)
    rel = []
    for d, g in joined.groupby(deciles, sort=True):
        rel.append({"decile": int(d), "n": int(len(g)), "mean_p_rookie": float(g["rookie_p_appear"].mean()),
                    "mean_p_veteran": float(g["veteran_p_appear"].mean()), "observed": float(g["appeared"].mean())})
    out["reliability"] = rel
    return out


def metrics_by(joined: pd.DataFrame, by: str) -> dict[str, dict]:
    return {str(key): paired_metrics(g) for key, g in joined.groupby(by, sort=True)}


def fold_sign_summary(joined: pd.DataFrame) -> dict:
    """Each draft class is one temporal fold; kept as a table beside the bootstrap, which does not resample folds."""
    folds = {}
    for cls, g in joined.groupby("draft_season", sort=True):
        folds[str(int(cls))] = {"n": int(len(g)),
                                "mean_sq_err_diff": float(np.mean(g["sq_err_veteran"] - g["sq_err_rookie"])),
                                "mean_abs_err_diff": float(np.mean(g["abs_err_veteran"] - g["abs_err_rookie"]))}
    better = sum(1 for f in folds.values() if f["mean_sq_err_diff"] < 0)
    return {"by_draft_class": folds, "classes_veteran_better": better, "classes_total": len(folds),
            "meaning": ("each draft class is one temporal fold; the count of classes where the veteran side has lower "
                        "mean squared error preserves the fold structure the bootstrap does not resample")}


DEFAULT_STATISTICS = ("mean_sq_err_diff", "mean_abs_err_diff", "brier_diff")
BOOTSTRAP_CONDITIONAL_ON = ("both frozen fits and the realized seasons; player-sampling variability only — not model, "
                            "not selection, not season uncertainty, and not a forecast interval")


def paired_bootstrap(joined: pd.DataFrame, *, seed: int, draws: int, unit: str = "player_id",
                     statistic_columns: dict[str, str] | None = None) -> dict:
    """Percentile interval of mean paired differences, resampling UNITS (players) with replacement.

    Justification of the unit: a player contributes one row per experience stratum and those rows share
    his career; resampling rows would treat them as independent. The interval is conditional on both
    frozen fits and on the realized seasons: it is player-sampling variability only — not model,
    selection or season uncertainty, and not a forecast interval. Temporal folds are reported beside it
    (fold_sign_summary), not resampled. Deterministic given the seed.
    """
    frame = joined.copy()
    if statistic_columns is None:
        frame["mean_sq_err_diff"] = frame["sq_err_veteran"] - frame["sq_err_rookie"]
        frame["mean_abs_err_diff"] = frame["abs_err_veteran"] - frame["abs_err_rookie"]
        frame["brier_diff"] = ((frame["veteran_p_appear"] - frame["appeared"]) ** 2
                               - (frame["rookie_p_appear"] - frame["appeared"]) ** 2)
        statistic_columns = {k: k for k in DEFAULT_STATISTICS}
    units = frame[unit].astype(str).to_numpy()
    uniq, inverse = np.unique(units, return_inverse=True)
    n_units = len(uniq)
    rng = np.random.default_rng(seed)
    sums = {name: np.bincount(inverse, weights=frame[col].to_numpy(float), minlength=n_units)
            for name, col in statistic_columns.items()}
    counts = np.bincount(inverse, minlength=n_units).astype(float)
    result: dict = {"seed": int(seed), "draws": int(draws), "unit": unit, "level": 0.90, "n_units": int(n_units),
                    "n_rows": int(len(frame)), "conditional_on": BOOTSTRAP_CONDITIONAL_ON,
                    "folds": "draft classes are not resampled; see fold_sign_summary"}
    index_draws = rng.integers(0, n_units, size=(draws, n_units))
    for name, col in statistic_columns.items():
        point = float(frame[col].mean())
        stats = sums[name][index_draws].sum(axis=1) / counts[index_draws].sum(axis=1)
        result[name] = {"point": point, "lo": float(np.percentile(stats, 5)), "hi": float(np.percentile(stats, 95))}
    return result
