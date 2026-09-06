"""Consume the COMMON league-season outcome artifact (Codex / DG-179).

Schema ``dg179_league_season_outcomes_v1`` (read-only reference:
``dg-wt/DG-179/src/dynasty_genius/eval/league_season_outcomes.py``): ``outcomes.csv`` with
player_id, season, points, games, appeared, plus ``manifest.json`` naming the scoring preset
``nflverse_default_ppr_championship_window_v1`` (``league_scoring_exact: false``, with the
exact-league gaps listed), the per-season windows (REG weeks 1-16 through 2020, 1-17 from
2021, weight 1.0), the exposure definition, the source identity and validation facts, a
``coverage_status`` and the output hash. One global artifact is shared by both models; this
lane reconstructs nothing.

What this module does and refuses:
  * it mirrors the ACTUAL keys, never provisional aliases;
  * it binds the CSV bytes and length to ``outputs["outcomes.csv"]`` and hashes the manifest;
  * it requires the preset, ``league_scoring_exact: false``, the windows, the exposure
    definition, a known ``coverage_status`` and the limitations note;
  * it derives an internal validated-research attribute ONLY after those checks, retains
    the qualification note, and never converts "qualified research" into "complete
    individual data" (``individual_stat_completeness_proven`` stays False);
  * it requires points, games and appearance to agree row by row (one mask);
  * seasons outside the artifact are not in ``seasons_covered`` and are censored by
    ``annual_outcomes.annual_targets`` as unknown, never zero.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "dg179_league_season_outcomes_v1"
SCORING_PRESET = "nflverse_default_ppr_championship_window_v1"
EXPOSURE_DEFINITION = "unique stat_record weeks within the outcome window"
COVERAGE_QUALIFIED = "qualified_research_game_complete_identified_rows"
COVERAGE_FIXTURE = "calendar_checked_game_coverage_unverified"
KNOWN_COVERAGE = (COVERAGE_QUALIFIED, COVERAGE_FIXTURE)
EXPECTED_COLUMNS: list[str] = ["player_id", "season", "points", "games", "appeared"]
SCOPE_LABEL = "REG_league_window"
WINDOW_ID = "championship_week17"


class CommonArtifactError(ValueError):
    """The common outcome artifact or its manifest does not say what a consumer must know."""


def _require(manifest: dict[str, Any], key: str) -> Any:
    if key not in manifest or manifest[key] in (None, ""):
        raise CommonArtifactError(f"manifest does not state {key}")
    return manifest[key]


def _sha(value: Any, what: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise CommonArtifactError(f"{what} must be a lowercase hexadecimal sha256")
    return value


def validate_common_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Assert the manifest's schema, preset, exactness, windows, exposure, coverage and
    hashes; return the facts a consumer records. No validated bool is invented here."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CommonArtifactError(f"schema_version must be {SCHEMA_VERSION!r}, got {manifest.get('schema_version')!r}")
    if manifest.get("scoring_preset") != SCORING_PRESET:
        raise CommonArtifactError(f"scoring_preset must be {SCORING_PRESET!r}, got {manifest.get('scoring_preset')!r}")
    if manifest.get("league_scoring_exact") is not False:
        raise CommonArtifactError("league_scoring_exact must be false; this artifact is not David's exact scoring")
    gaps = manifest.get("exact_league_scoring_gaps")
    if not isinstance(gaps, dict) or not gaps:
        raise CommonArtifactError("exact_league_scoring_gaps must list the components whose equivalence is not established")
    windows = _require(manifest, "season_windows")
    if not isinstance(windows, dict) or not windows:
        raise CommonArtifactError("season_windows must map each season to its window")
    seasons: list[int] = []
    for key, w in windows.items():
        try:
            year = int(key)
        except (TypeError, ValueError) as err:
            raise CommonArtifactError(f"season_windows key {key!r} is not a year") from err
        final = 18 if year >= 2021 else 17
        if list(w.get("included_reg_weeks", [])) != list(range(1, final)):
            raise CommonArtifactError(f"season_windows[{key}].included_reg_weeks must be 1..{final - 1} (championship ends NFL week 17)")
        if w.get("excluded_final_reg_week") != final or list(w.get("expected_full_reg_weeks", [])) != list(range(1, final + 1)):
            raise CommonArtifactError(f"season_windows[{key}] must exclude final REG week {final} of the full {final}-week calendar")
        if w.get("weekly_weight") != 1.0:
            raise CommonArtifactError(f"season_windows[{key}].weekly_weight must be 1.0 (equal weights)")
        seasons.append(year)
    if manifest.get("exposure_definition") != EXPOSURE_DEFINITION:
        raise CommonArtifactError(f"exposure_definition must be {EXPOSURE_DEFINITION!r}")
    coverage = manifest.get("coverage_status")
    if coverage not in KNOWN_COVERAGE:
        raise CommonArtifactError(f"coverage_status {coverage!r} is not one of {KNOWN_COVERAGE}; a consumer may not read it as complete individual data")
    limitations = manifest.get("source_validation_limitations")
    if not isinstance(limitations, str) or not limitations.strip():
        raise CommonArtifactError("source_validation_limitations (the qualification note) must be present")
    facts = manifest.get("source_validation")
    if not isinstance(facts, dict) or "seasons" not in facts:
        raise CommonArtifactError("source_validation must carry the per-season facts")
    outputs = manifest.get("outputs") or {}
    entry = outputs.get("outcomes.csv") if isinstance(outputs, dict) else None
    if not isinstance(entry, dict):
        raise CommonArtifactError("outputs must carry outcomes.csv with its sha256 and bytes")
    csv_sha = _sha(entry.get("sha256"), "outputs.outcomes.csv.sha256")
    for key in ("source_identity_sha256", "scoring_identity", "window_identity", "target_identity"):
        _sha(_require(manifest, key), key)
    last_complete = int(_require(manifest, "last_complete_season"))
    return {
        "schema_version": SCHEMA_VERSION, "scoring": SCORING_PRESET, "league_scoring_exact": False,
        "exact_league_scoring_gaps": dict(gaps), "scope": SCOPE_LABEL, "window_id": WINDOW_ID,
        "season_windows": windows, "seasons_covered": sorted(seasons), "last_complete_season": last_complete,
        "exposure": EXPOSURE_DEFINITION, "coverage_status": coverage, "qualification_note": limitations,
        "facts": facts, "csv_sha256": csv_sha, "csv_bytes": entry.get("bytes"),
        "source_identity_sha256": manifest["source_identity_sha256"], "scoring_identity": manifest["scoring_identity"],
        "window_identity": manifest["window_identity"], "target_identity": manifest["target_identity"],
        "appearance_definition": manifest.get("appearance_definition"), "zero_definition": manifest.get("zero_definition"),
    }


def load_common_outcomes(artifact_dir: Path | str, *, require_qualified: bool = False) -> pd.DataFrame:
    """Read ``outcomes.csv`` + ``manifest.json`` from the artifact directory as the outcome
    frame ``annual_targets`` consumes, with its attrs. ``require_qualified`` refuses a
    fixture-grade artifact (coverage unverified) — a producer handoff must set it."""
    d = Path(artifact_dir)
    manifest_bytes = (d / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    facts = validate_common_manifest(manifest)
    csv_bytes = (d / "outcomes.csv").read_bytes()
    actual = hashlib.sha256(csv_bytes).hexdigest()
    if actual != facts["csv_sha256"]:
        raise CommonArtifactError(f"outcomes.csv sha256 {actual[:12]}… does not match the manifest's {facts['csv_sha256'][:12]}…")
    if facts["csv_bytes"] is not None and int(facts["csv_bytes"]) != len(csv_bytes):
        raise CommonArtifactError("outcomes.csv byte length does not match the manifest")
    qualified = facts["coverage_status"] == COVERAGE_QUALIFIED
    if require_qualified and not qualified:
        raise CommonArtifactError(
            f"artifact coverage_status is {facts['coverage_status']!r}; a producer handoff requires the qualified research status"
        )
    raw = pd.read_csv(d / "outcomes.csv")
    missing = [c for c in EXPECTED_COLUMNS if c not in raw.columns]
    if missing:
        raise CommonArtifactError(f"artifact lacks columns {missing}")
    out = pd.DataFrame({
        "player_id": raw["player_id"].astype(str),
        "season": pd.to_numeric(raw["season"], errors="coerce"),
        "games": pd.to_numeric(raw["games"], errors="coerce"),
        "points": pd.to_numeric(raw["points"], errors="coerce"),
        "appeared": raw["appeared"].map(lambda v: str(v).strip().lower() in ("true", "1", "1.0", "yes")),
    })
    if out[["season", "games", "points"]].isna().any().any():
        raise CommonArtifactError("artifact carries a missing season, games or points value; unknown must be an absent row, not a blank")
    out["season"] = out["season"].astype(int)
    out["games"] = out["games"].astype(int)
    out["points"] = out["points"].astype(float)
    inconsistent = (out["appeared"] != (out["games"] >= 1)) | ((out["games"] == 0) & (out["points"] != 0.0))
    if inconsistent.any():
        raise CommonArtifactError(
            f"{int(inconsistent.sum())} rows where points, games and appearance do not come from the same mask "
            "(appeared must equal games >= 1; zero games must carry zero points)"
        )
    if out.duplicated(subset=["player_id", "season"]).any():
        raise CommonArtifactError("duplicate (player_id, season) rows")
    outside = sorted(set(out["season"].unique()) - set(facts["seasons_covered"]))
    if outside:
        raise CommonArtifactError(f"artifact carries rows for seasons its windows do not declare: {outside}")
    out = out.sort_values(["player_id", "season"]).reset_index(drop=True)
    out.attrs.update({
        "scope": facts["scope"], "window_id": facts["window_id"], "season_types": ["REG"],
        "season_windows": facts["season_windows"], "scoring": facts["scoring"],
        "league_scoring_exact": False, "exact_league_scoring_gaps": facts["exact_league_scoring_gaps"],
        "event": facts["appearance_definition"] or "appeared: >= 1 stat record inside the outcome window",
        "exposure": facts["exposure"], "zero_definition": facts["zero_definition"],
        "seasons_covered": facts["seasons_covered"], "last_complete_season": facts["last_complete_season"],
        "csv_sha256": facts["csv_sha256"], "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "source_identity_sha256": facts["source_identity_sha256"], "scoring_identity": facts["scoring_identity"],
        "window_identity": facts["window_identity"], "target_identity": facts["target_identity"],
        # Derived HERE, after schema, hash and coverage checks; the qualification note travels with it.
        "source_validation": {
            "validated": True, "derived_by": "dg177 consumer after schema/hash/coverage checks",
            "coverage_status": facts["coverage_status"], "qualified_research": qualified,
            "individual_stat_completeness_proven": False, "qualification_note": facts["qualification_note"],
            "facts": facts["facts"],
        },
    })
    return out
