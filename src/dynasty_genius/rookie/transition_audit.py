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
from datetime import datetime, timezone
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
    "render_report",
    "rookie_draft_time_frame",
    "run_audit",
    "verify_same_target",
    "veteran_horizon1_frame",
    "veteran_population_ledger",
    "write_audit",
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
    manifest_sha256: str
    artifact_labels: dict  # (player_id, season) -> (points, games, appeared) as the bound outcome artifact records them


@dataclass(frozen=True)
class VeteranRun:
    run_dir: Path
    manifest: dict
    historical: pd.DataFrame
    cohort: pd.DataFrame
    verified: dict[str, str]
    manifest_sha256: str
    corrected_manifest_sha256: str | None  # the companion that is the target of record when present
    outcome_binding: dict  # from the companion's outcome block when present, else manifest label_source


def load_rookie_run(run_dir: Path | str, *, outcomes_csv: Path | str | None = None) -> RookieRun:
    """``outcomes_csv`` overrides the artifact path recorded in the manifest; its BYTES must still hash to the
    manifest's bound csv_sha256, so an override can only relocate the same artifact, never substitute one."""
    run_dir = Path(run_dir)
    manifest_bytes = (run_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
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
    outcomes_block = manifest.get("outcomes") or {}
    art_path = Path(outcomes_csv) if outcomes_csv is not None else Path(str(outcomes_block.get("csv_path") or ""))
    art_sha = outcomes_block.get("csv_sha256")
    if not art_sha or not str(art_path):
        raise ValueError(f"{run_dir}: manifest binds no outcome artifact (outcomes.csv_path / csv_sha256)")
    if not art_path.exists():
        raise ValueError(f"{run_dir}: bound outcome artifact missing at {art_path} (outcomes.csv)")
    art_bytes = art_path.read_bytes()
    if _sha(art_bytes) != art_sha:
        raise ValueError(f"{run_dir}: outcomes.csv sha256 mismatch at {art_path}: bound {art_sha[:12]}…, actual {_sha(art_bytes)[:12]}…")
    verified["outcomes.csv"] = art_sha
    art = pd.read_csv(io.BytesIO(art_bytes), usecols=["player_id", "season", "points", "games", "appeared"])
    art_keys = pd.DataFrame({"player_id": art["player_id"].astype(str), "season": _strict_int(art["season"], "outcome artifact season")})
    _assert_unique(art_keys, ["player_id", "season"], "outcome artifact")
    labels = {(pid, int(season)): (float(points), float(games), float(bool(appeared)))
              for pid, season, points, games, appeared in zip(art_keys["player_id"], art_keys["season"], art["points"], art["games"], art["appeared"])}
    return RookieRun(run_dir, manifest, cohort, oot, picks, verified, _sha(manifest_bytes), labels)


def load_veteran_run(run_dir: Path | str) -> VeteranRun:
    run_dir = Path(run_dir)
    manifest_bytes = (run_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    declared = manifest.get("outputs_sha256") or {}
    verified: dict[str, str] = {}
    raw: dict[str, bytes] = {}
    for name in VETERAN_FILES:
        raw[name] = _read_verified(run_dir, name, declared.get(name))
        verified[name] = declared[name]
    historical = pd.read_csv(io.BytesIO(raw["historical_predictions.csv"]))
    cohort = pd.read_csv(io.BytesIO(gzip.decompress(raw["basic_cohort.csv.gz"])))
    companion = run_dir.parent / f"{run_dir.name}.manifest.corrected.json"
    corrected_sha: str | None = None
    binding = dict(manifest.get("label_source") or {})
    if companion.exists():
        companion_bytes = companion.read_bytes()
        corrected = json.loads(companion_bytes)
        if (corrected.get("outputs_sha256") or {}) != declared:
            raise ValueError(f"{companion.name}: corrected companion declares different outputs_sha256 than manifest.json; refusing")
        corrected_sha = _sha(companion_bytes)
        outcome = corrected.get("outcome") or {}
        required = ("target_identity", "outcomes_csv_sha256", "manifest_sha256", "scoring_preset")
        missing = [k for k in required if not outcome.get(k)]
        if missing:
            raise ValueError(f"{companion.name}: a present corrected companion is the binding of record and must carry a complete "
                             f"outcome block; missing {missing}")
        binding = {"target_identity": outcome["target_identity"], "csv_sha256": outcome["outcomes_csv_sha256"],
                   "manifest_sha256": outcome["manifest_sha256"], "scoring_preset": outcome["scoring_preset"],
                   "source": companion.name}
    binding.setdefault("source", "manifest.json#label_source")
    return VeteranRun(run_dir, manifest, historical, cohort, verified, _sha(manifest_bytes), corrected_sha, binding)


def verify_same_target(rookie: RookieRun, veteran: VeteranRun) -> dict:
    """Both producers must label from the SAME outcome artifact; asserted from identities, never assumed."""
    r = rookie.manifest.get("outcomes") or {}
    v = veteran.outcome_binding
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
    return {"status": "same_target", **{k: a for k, (a, _) in pairs.items()}, "veteran_binding_source": v.get("source")}


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
    "appeared", "points", "games", "label_source",
    "rookie_p_appear", "rookie_e_points", "rookie_e_points_given_appear", "rookie_e_games",
    "veteran_p_appear", "veteran_e_points", "veteran_e_points_given_appear", "veteran_e_games",
    "veteran_games_t", "thin_history", "veteran_row_without_window_appearance",
    "err_rookie", "err_veteran", "abs_err_rookie", "abs_err_veteran", "sq_err_rookie", "sq_err_veteran", "veteran_closer",
]
THIN_HISTORY_MAX_GAMES = 4
# Labels on both sides come from the SAME artifact and are exactly equal; "identical" means identical.
# A relative tolerance would pass 250 vs 250.002 while the audit claims identity, so there is none.
LABEL_ATOL = 1e-9


def _strict_int(values: pd.Series, name: str) -> np.ndarray:
    """Year and key columns must be finite AND integral BEFORE any cast; astype(int) would truncate 2012.25 to 2012."""
    arr = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    bad = ~np.isfinite(arr) | (arr != np.floor(arr))
    if bad.any():
        sample = values[bad].head(5).tolist()
        raise ValueError(f"{name}: {int(bad.sum())} values are not integral (or not numeric), e.g. {sample}")
    return arr.astype(int)


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
    for col in ("draft_season", "forecast_year", "pick", "round"):
        _strict_int(oot[col], f"rookie history {col}")
    for col in ("draft_season", "pick"):
        _strict_int(rookie.cohort[col], f"cohort {col}")
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
    for col in ("horizon", "feature_season", "forecast_season"):
        _strict_int(h[col], f"veteran history {col}")
    _strict_int(veteran.cohort["feature_season"], "veteran basic cohort feature_season")
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
    merged = merged.drop(columns="_merge")
    gt = merged["veteran_games_t"].to_numpy(float)
    bad_games = ~np.isfinite(gt) | (gt < 0)
    if bad_games.any():
        sample = merged.loc[bad_games, ["player_id", "veteran_feature_season", "veteran_games_t"]].head(5).to_dict("records")
        raise ValueError(f"veteran games_t missing or negative on {int(bad_games.sum())} feature rows — a required measurement; "
                         f"refusing rather than labelling them not-thin, e.g. {sample}")
    return merged


REQUIRED_FINITE = ("rookie_e_points", "rookie_e_points_given_appear", "rookie_e_games",
                   "veteran_e_points", "veteran_e_points_given_appear", "veteran_e_games",
                   "rookie_label_points", "veteran_label_points", "rookie_label_games", "veteran_label_games",
                   "rookie_label_appeared", "veteran_label_appeared")
REQUIRED_PROBABILITY = ("rookie_p_appear", "veteran_p_appear")


def _assert_required_values(j: pd.DataFrame) -> None:
    """Every required forecast, probability and label on a joined row must be a finite number, and every
    probability must lie in [0, 1]. Negative fantasy points are valid. A missing value here is a broken
    input and refuses at the join, never a cryptic failure inside the metrics."""
    for col in REQUIRED_FINITE:
        vals = j[col].to_numpy(float)
        bad = ~np.isfinite(vals)
        if bad.any():
            sample = j.loc[bad, ["player_id", "veteran_feature_season", col]].head(5).to_dict("records")
            raise ValueError(f"{col}: {int(bad.sum())} joined rows are not finite, e.g. {sample}")
    for col in REQUIRED_PROBABILITY:
        vals = j[col].to_numpy(float)
        bad = ~np.isfinite(vals) | (vals < 0.0) | (vals > 1.0)
        if bad.any():
            sample = j.loc[bad, ["player_id", "veteran_feature_season", col]].head(5).to_dict("records")
            raise ValueError(f"{col}: {int(bad.sum())} joined rows carry a probability outside [0, 1] or not finite, e.g. {sample}")
    blank = (j["player_id"].astype(str).str.strip() == "") | j["player_id"].isna()
    if blank.any():
        raise ValueError(f"{int(blank.sum())} joined rows carry a blank player_id")


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
    _assert_required_values(j)
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
    keys = list(zip(j["player_id"], (int(s) for s in j["target_season"])))
    in_artifact = np.array([k in rookie.artifact_labels for k in keys], dtype=bool)
    # an artifact-backed label must EQUAL the artifact's own values; two producers agreeing is not evidence
    art_points = np.array([rookie.artifact_labels[k][0] if k in rookie.artifact_labels else np.nan for k in keys], dtype=float)
    art_games = np.array([rookie.artifact_labels[k][1] if k in rookie.artifact_labels else np.nan for k in keys], dtype=float)
    art_appeared = np.array([rookie.artifact_labels[k][2] if k in rookie.artifact_labels else np.nan for k in keys], dtype=float)
    disagree = in_artifact & ~((np.abs(j["points"].to_numpy(float) - art_points) <= LABEL_ATOL)
                               & (j["games"].to_numpy(float) == art_games) & (j["appeared"].to_numpy(float) == art_appeared))
    if disagree.any():
        sample = j.loc[disagree, ["player_id", "target_season", "points", "games", "appeared"]].head(5).to_dict("records")
        raise ValueError(f"{int(disagree.sum())} paired rows carry a label that disagrees with the outcome artifact's own row "
                         f"(both producers agreeing is not artifact evidence), e.g. {sample}")
    zero_label = (j["points"].to_numpy(float) == 0.0) & (j["games"].to_numpy(float) == 0.0) & (j["appeared"].to_numpy(float) == 0.0)
    contradiction = ~in_artifact & ~zero_label
    if contradiction.any():
        sample = j.loc[contradiction, ["player_id", "target_season", "points", "games", "appeared"]].head(5).to_dict("records")
        raise ValueError(f"{int(contradiction.sum())} paired rows carry a non-zero label for a (player, season) the outcome "
                         f"artifact does not contain; a label without an artifact row can only be the zero convention, e.g. {sample}")
    j["label_source"] = np.where(in_artifact, "artifact", "convention_zero")
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
    "no_veteran_row_no_window_appearance",        # measured 0 appearances in the feature season, no veteran row
    "no_veteran_row_despite_window_appearance",   # measured appearance, no veteran row (e.g. role abstain)
    "no_veteran_row_appearance_unknown",          # no veteran row and the appearance flag itself is unknown
    "rookie_forecast_missing",                    # cohort player with no draft-time forecast row at all
    "label_unknown",                              # any of the target season's appearance / points / games is unknown
    "veteran_row_without_rookie_forecast",        # fail-safe; unreachable when the join's own guards hold
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
    joined = join_transition(rookie, veteran, experience=experience)
    joined_ids = set(joined["player_id"])
    joined_source = dict(zip(joined["player_id"], joined["label_source"]))
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
        elif pid not in r.index:
            cat = "rookie_forecast_missing"
        elif r.loc[pid, ["rookie_label_appeared", "rookie_label_points", "rookie_label_games"]].isna().any():
            cat = "label_unknown"
        elif (pid, fs) not in v.index:
            if appear_k == 1:
                cat = "no_veteran_row_despite_window_appearance"
            elif appear_k == 0:
                cat = "no_veteran_row_no_window_appearance"
            else:
                cat = "no_veteran_row_appearance_unknown"
        else:
            cat = "veteran_row_without_rookie_forecast"
        rows.append({"player_id": pid, "name": row.name, "draft_season": cls, "pick": int(row.pick),
                     "draft_position": row.position, "experience": experience, "category": cat,
                     "label_source": joined_source.get(pid, "not_paired"),
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


# ----------------------------------------------------------------------------- run, report, write

OUTPUT_FILES = ("joined_rows.csv", "coverage_ledger.csv", "veteran_population_ledger.csv", "metrics.json", "REPORT.md", "manifest.json")

ROLE_CAVEAT = ("DG-177's basic cohort trusts the offensive STATLINE position and its weekly snapshot carries historic role "
               "disagreements with the roster source (e.g. Jordan Matthews 2014 TE vs WR, Logan Thomas 2014 TE vs QB, "
               "N'Keal Harry 2019 TE vs WR, Cordarrelle Patterson 2013 RB vs WR). The audit keeps draft_position and "
               "veteran_position as attributes, never joins on position, and counts disagreements; equal targets do not "
               "prove historic role integrity. No role repair and no refit in this scope.")
WINDOW_CAVEAT = ("veteran_row_without_window_appearance flags a veteran feature row whose games_t counts stat lines "
                 "outside the championship window (final regular-season week or postseason) while the window label "
                 "records no appearance. Those rows are VALID paired evidence — the feature window and the label window "
                 "differ by design — and are flagged, never rejected.")
ROOKIE_MENU_CAVEAT = ("the rookie producer's policy menu was refined after inspecting the historical years, so its "
                      "historical evaluation is a retrospective evaluation with forecast cutoffs enforced, not untouched "
                      "independent confirmation; this audit inherits that caveat for the rookie side")
NOT_A_CORRECTION = ("an audit of two frozen forecasts on one realized target; no correction, blend, uplift, youth bonus, "
                    "market input, added feature or refit is proposed here")


def _jsonable(value):
    """NaN -> null so metrics.json is valid JSON and an unknown stays unknown rather than a token."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


LABEL_CONVENTION_CAVEAT = ("a paired row whose (player, target season) the outcome artifact does not contain carries a "
                           "0 points / 0 games / not-appeared label by the convention BOTH frozen producers share (no stat "
                           "record in a covered season is a measured zero, per each producer's definitions); the artifact's "
                           "own zero_definition calls an absent pair unknown. Such rows are tagged label_source = "
                           "convention_zero in joined_rows.csv and coverage_ledger.csv and counted per experience; they are "
                           "internally consistent between the two producers but are NOT artifact-backed rows, and a board "
                           "consumer must not read them as such. An absent pair with a non-zero label refuses.")
EXPERIENCE_COMPARISON_CAVEAT = ("the experience strata are separate paired samples (different players and class ranges "
                                "at each experience), so a comparison across experiences is between samples, not a "
                                "within-person trend; a larger veteran advantage at higher experience is not an automatic "
                                "'more NFL information' effect and must be read alongside the per-stratum populations")


def _validate_audit_args(experiences: tuple[int, ...], seed: int, draws: int) -> tuple[int, ...]:
    exps = tuple(experiences)
    if not exps:
        raise ValueError("experience: at least one experience stratum is required")
    if any((not isinstance(e, (int, np.integer))) or isinstance(e, bool) or e < 1 for e in exps):
        raise ValueError(f"experience: every value must be an integer >= 1, got {exps}")
    if len(set(exps)) != len(exps):
        raise ValueError(f"experience: duplicate strata would double-count rows and ledger entries, got {exps}")
    if not isinstance(draws, (int, np.integer)) or isinstance(draws, bool) or draws < 1:
        raise ValueError(f"draws: must be an integer >= 1, got {draws!r}")
    if not isinstance(seed, (int, np.integer)) or isinstance(seed, bool):
        raise ValueError(f"seed: must be an integer, got {seed!r}")
    return tuple(int(e) for e in exps)


def run_audit(rookie: RookieRun, veteran: VeteranRun, *, experiences: tuple[int, ...], seed: int, draws: int) -> dict:
    experiences = _validate_audit_args(experiences, seed, draws)
    binding = verify_same_target(rookie, veteran)
    raw_rows = ((rookie.manifest.get("cohort") or {}).get("coverage") or {}).get("rows")
    raw_excluded = int(raw_rows) - int(len(rookie.cohort)) if raw_rows is not None else None
    joined_all, coverage_all, population_all = [], [], []
    per_k: dict[str, dict] = {}
    for k in experiences:
        j = join_transition(rookie, veteran, experience=k)
        cov = coverage_ledger(rookie, veteran, experience=k)
        pop = veteran_population_ledger(rookie, veteran, j, experience=k)
        joined_all.append(j)
        coverage_all.append(cov)
        population_all.append(pop.assign(experience=k))
        per_k[str(k)] = {
            "overall": paired_metrics(j),
            "by_position": metrics_by(j, "draft_position") if len(j) else {},
            "by_draft_class": metrics_by(j, "draft_season") if len(j) else {},
            "by_thin_history": metrics_by(j, "thin_history") if len(j) else {},
            "folds": fold_sign_summary(j) if len(j) else {"by_draft_class": {}, "classes_veteran_better": 0, "classes_total": 0},
            "bootstrap": paired_bootstrap(j, seed=seed, draws=draws) if len(j) else {"n_rows": 0},
            "coverage_counts": {c: int((cov["category"] == c).sum()) for c in LEDGER_CATEGORIES},
            "label_source_counts": {s: int((j["label_source"] == s).sum()) for s in ("artifact", "convention_zero")},
            "cohort_rows": int(len(cov)),
            "raw_source_population_excluded": raw_excluded,
            "overlap_classes": overlap_classes(rookie, veteran, experience=k),
            "flags": {"veteran_row_without_window_appearance": int(j["veteran_row_without_window_appearance"].sum()) if len(j) else 0,
                      "position_disagreement": int((j["draft_position"] != j["veteran_position"]).sum()) if len(j) else 0},
        }
    joined = pd.concat(joined_all, ignore_index=True) if joined_all else pd.DataFrame(columns=JOINED_COLUMNS)
    metrics = {
        "experiences": per_k,
        "pooled_bootstrap": paired_bootstrap(joined, seed=seed, draws=draws) if len(joined) else {"n_rows": 0},
        "definitions": {
            "experience": "feature_season - draft_season + 1 from the draft table; never DG-177 seasons_played (left-censored at 2005)",
            "thin_history": f"veteran games_t <= {THIN_HISTORY_MAX_GAMES} in the feature season",
            "origins": ("rookie forecast made at draft time with NFL information through draft_season - 1; veteran forecast "
                        "made after the feature season with information through it; the gap is the experience in seasons"),
            "sign_convention": "diff = veteran minus rookie; negative favours the veteran forecast",
            "position_basis": "metrics are grouped by DRAFT position; the veteran role position is retained beside it",
            "not": NOT_A_CORRECTION,
            "caveats": {
                "rookie_policy_menu": ROOKIE_MENU_CAVEAT,
                "experience_comparison": EXPERIENCE_COMPARISON_CAVEAT,
                "label_convention": LABEL_CONVENTION_CAVEAT,
                "rookie_evidence_status_verbatim": rookie.manifest.get("evidence_status"),
                "bootstrap": BOOTSTRAP_CONDITIONAL_ON,
                "role": ROLE_CAVEAT,
                "window": WINDOW_CAVEAT,
            },
        },
    }
    return {"joined": joined, "coverage": pd.concat(coverage_all, ignore_index=True),
            "population": pd.concat(population_all, ignore_index=True), "metrics": metrics, "binding": binding}


def _fmt(x, nd: int = 1) -> str:
    if x is None:
        return "n/a"
    try:
        if np.isnan(x):
            return "n/a"
    except TypeError:
        return str(x)
    return f"{x:.{nd}f}"


def render_report(metrics: dict, coverage: pd.DataFrame, population: pd.DataFrame, binding: dict) -> str:
    """Every number below is read from the metrics/frames; nothing is typed."""
    d = metrics["definitions"]
    lines = ["# DG-165 rookie → veteran transition audit", "",
             f"Same realized target on both sides: `{binding['target_identity'][:16]}…` ({binding['scoring_preset']}).", "",
             f"This is {d['not']}.", ""]
    for k, block in metrics["experiences"].items():
        o = block["overall"]
        lines += [f"## Experience {k} (the veteran forecast has {k} more season(s) of NFL information)", ""]
        if o.get("n", 0) == 0:
            lines += ["No paired rows.", ""]
        else:
            oc = block["overlap_classes"]
            lines += [f"Paired rows: n = {o['n']} over draft classes {oc[0]}–{oc[-1]}.", "",
                      "| forecast | RMSE | MAE | bias | Brier(appear) | calib slope |", "|---|---|---|---|---|---|"]
            for side in ("rookie", "veteran"):
                s = o[side]
                lines.append(f"| {side} | {_fmt(s['rmse'])} | {_fmt(s['mae'])} | {_fmt(s['bias'])} | {_fmt(s['brier_appear'], 3)} | "
                             f"{_fmt(s['points_calibration_slope'], 2)} |")
            p, b, f = o["paired"], block["bootstrap"], block["folds"]
            lines += ["", f"Paired difference (veteran − rookie): mean squared error {_fmt(p['mean_sq_err_diff'])} "
                      f"[90% player-bootstrap {_fmt(b['mean_sq_err_diff']['lo'])}, {_fmt(b['mean_sq_err_diff']['hi'])}]; "
                      f"mean absolute error {_fmt(p['mean_abs_err_diff'])} [{_fmt(b['mean_abs_err_diff']['lo'])}, "
                      f"{_fmt(b['mean_abs_err_diff']['hi'])}]; veteran closer on {_fmt(100 * p['share_veteran_closer'])}% of rows; "
                      f"classes where the veteran side is better: {f['classes_veteran_better']} of {f['classes_total']}.", "",
                      f"The interval is conditional on {b['conditional_on']}.", "",
                      "| draft position | n | rookie RMSE | veteran RMSE | rookie MAE | veteran MAE | rookie bias | veteran bias |",
                      "|---|---|---|---|---|---|---|---|"]
            for pos, m in block["by_position"].items():
                lines.append(f"| {pos} | {m['n']} | {_fmt(m['rookie']['rmse'])} | {_fmt(m['veteran']['rmse'])} | {_fmt(m['rookie']['mae'])} | "
                             f"{_fmt(m['veteran']['mae'])} | {_fmt(m['rookie']['bias'])} | {_fmt(m['veteran']['bias'])} |")
            lines += ["", "| draft class (temporal fold) | n | mean sq err diff | mean abs err diff |", "|---|---|---|---|"]
            for cls, m in f["by_draft_class"].items():
                lines.append(f"| {cls} | {m['n']} | {_fmt(m['mean_sq_err_diff'])} | {_fmt(m['mean_abs_err_diff'])} |")
            lines += ["", f"| thin history ({d['thin_history']}) | n | rookie RMSE | veteran RMSE |", "|---|---|---|---|"]
            for flag, m in block["by_thin_history"].items():
                lines.append(f"| {flag} | {m['n']} | {_fmt(m['rookie']['rmse'])} | {_fmt(m['veteran']['rmse'])} |")
        lsc = block.get("label_source_counts", {})
        lines += ["", f"Label provenance on the paired rows: {lsc.get('artifact', 0)} artifact-backed, "
                  f"{lsc.get('convention_zero', 0)} convention_zero (0 / 0 / not appeared for a player-season the artifact does "
                  "not contain — both producers' shared convention, not artifact rows).", ""]
        lines += ["", f"Coverage of the WHOLE modelling cohort ({block['cohort_rows']} players) at this experience — paired rows are "
                  "not all drafted players:", ""]
        for cat, n in block["coverage_counts"].items():
            lines.append(f"- {cat}: {n}")
        if block["raw_source_population_excluded"] is not None:
            lines.append(f"- raw source population excluded before modelling (documented in the rookie run): {block['raw_source_population_excluded']}")
        lines += ["", f"Flags: veteran rows without a window appearance {block['flags']['veteran_row_without_window_appearance']}; "
                  f"draft/role position disagreements {block['flags']['position_disagreement']}.", ""]
    lines += ["## Veteran population at the overlap feature seasons, by draft status", ""]
    if len(population):
        for (k, status), g in population.groupby(["experience", "draft_status"], sort=True):
            lines.append(f"- experience {k}, {status}: {int(g['rows'].sum())} rows")
        lines += ["", f"_{population['experience_note'].iloc[0]}_", ""]
    lines += ["## Caveats", ""]
    for name, text in d["caveats"].items():
        if text is not None:
            lines.append(f"- **{name}**: {text if isinstance(text, str) else json.dumps(text)}")
    lines.append("")
    return "\n".join(lines)


def write_audit(run_dir: Path, result: dict, *, rookie: RookieRun, veteran: VeteranRun, seed: int, draws: int,
                experiences: tuple[int, ...], git_sha: str) -> dict:
    """Write the immutable artifact; refuses if any output already exists in run_dir."""
    run_dir = Path(run_dir)
    existing = [name for name in OUTPUT_FILES if (run_dir / name).exists()]
    if existing:
        raise FileExistsError(f"refusing to overwrite existing audit outputs in {run_dir}: {existing}")
    started = datetime.now(timezone.utc).isoformat()
    result["joined"].to_csv(run_dir / "joined_rows.csv", index=False)
    result["coverage"].to_csv(run_dir / "coverage_ledger.csv", index=False)
    result["population"].to_csv(run_dir / "veteran_population_ledger.csv", index=False)
    (run_dir / "metrics.json").write_text(json.dumps(_jsonable(result["metrics"]), indent=2, sort_keys=True, allow_nan=False))
    (run_dir / "REPORT.md").write_text(render_report(result["metrics"], result["coverage"], result["population"], result["binding"]))
    outputs = {name: _sha((run_dir / name).read_bytes()) for name in OUTPUT_FILES if name != "manifest.json"}
    manifest = {
        "schema_version": "dg165_transition_audit_v1", "ticket": "DG-165", "git_sha": git_sha, "run_dir": str(run_dir),
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "rookie": {"run_dir": str(rookie.run_dir), "manifest_sha256": rookie.manifest_sha256,
                       "model_version": rookie.manifest.get("model_version"), "scoring_arm_id": rookie.manifest.get("scoring_arm_id"),
                       "git_sha": rookie.manifest.get("git_sha"), "verified": rookie.verified},
            "veteran": {"run_dir": str(veteran.run_dir), "manifest_sha256": veteran.manifest_sha256,
                        "corrected_manifest_sha256": veteran.corrected_manifest_sha256,
                        "binding_of_record": veteran.outcome_binding.get("source"),
                        "producer": veteran.manifest.get("producer"), "candidate_arm": veteran.manifest.get("candidate_arm"),
                        "git_head": veteran.manifest.get("git_head"), "verified": veteran.verified,
                        "forecast_columns": "policy_* (what the board consumes); candidate_* and baseline_* are not audited here"},
        },
        "binding": result["binding"], "experiences": list(experiences), "seed": seed, "draws": draws,
        "definitions": _jsonable(result["metrics"]["definitions"]), "outputs_sha256": outputs,
        "frozen_inputs_untouched": True,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest
