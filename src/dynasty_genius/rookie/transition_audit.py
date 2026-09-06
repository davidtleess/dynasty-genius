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

import pandas as pd

__all__ = [
    "RookieRun",
    "VeteranRun",
    "load_rookie_run",
    "load_veteran_run",
    "verify_same_target",
]

ROOKIE_FILES = ("cohort.csv", "out_of_time_predictions.csv")
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
