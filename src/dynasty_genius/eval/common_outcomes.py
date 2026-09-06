"""Consume the COMMON player-season outcome artifact (Codex / DG-179).

One CSV + manifest per research window: player_id, season, points, games, appeared,
built by Codex from the full validated weekly source with regular-season weeks 1-16
through 2020 and 1-17 from 2021 (the league's championship ends NFL week 17), equal
week weights, and a scoring identifier of "nflverse-default-PPR league-window research".
That is NOT David's exact league scoring (special-teams and fumble rules are not fully
reconstructable yet), and this module refuses any manifest that claims it is.

What this module does and does not do:
  * it never re-scores anything — no duplicate scorer, no implied equivalence;
  * it binds the CSV bytes to the manifest's sha256 before reading;
  * it requires points, games and appearance to come from the same mask, row by row
    (appeared <=> games >= 1; zero games means zero points);
  * it keeps a source-complete absence (a row with 0 games, appeared false) distinct
    from unknown (no row, or a season the manifest does not cover), which
    ``annual_outcomes.annual_targets`` then censors rather than zeroes.

The manifest field names below are the schema this lane expects; if DG-179 publishes
different names the validator says which one is missing rather than guessing.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

EXPECTED_COLUMNS: list[str] = ["player_id", "season", "points", "games", "appeared"]
SCOPE_LABEL = "REG_league_window"
WEEKS_THROUGH_2020 = [1, 16]
WEEKS_FROM_2021 = [1, 17]
EVENT = "appeared: >= 1 stat-row game in the league-window regular season"
EXPOSURE = "games: weekly stat-row games within the league window (equal week weights)"


class CommonArtifactError(ValueError):
    """The common outcome artifact or its manifest does not say what a consumer must know."""


def _require(manifest: dict[str, Any], key: str, message: str) -> Any:
    if key not in manifest or manifest[key] in (None, "", []):
        raise CommonArtifactError(f"manifest does not state {key}: {message}")
    return manifest[key]


def validate_common_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Assert the manifest names the window, the scoring and its validation; return facts."""
    scoring = _require(manifest, "scoring_identifier", "the scoring identifier (e.g. nflverse-default-PPR league-window research)")
    if not isinstance(scoring, str):
        raise CommonArtifactError("scoring_identifier must be a string")
    if manifest.get("exact_league_scoring") is not False:
        raise CommonArtifactError(
            "manifest must state exact_league_scoring: false — this artifact is nflverse-default PPR over the "
            "league window, not David's exact scoring, and a consumer must not imply otherwise"
        )
    scope = _require(manifest, "scope", "season_type, weeks and week_weights")
    if scope.get("season_type") != "REG":
        raise CommonArtifactError(f"scope.season_type must be REG, got {scope.get('season_type')!r}")
    weeks = scope.get("weeks") or {}
    if list(weeks.get("through_2020", [])) != WEEKS_THROUGH_2020 or list(weeks.get("from_2021", [])) != WEEKS_FROM_2021:
        raise CommonArtifactError(
            f"scope.weeks must be through_2020 {WEEKS_THROUGH_2020} and from_2021 {WEEKS_FROM_2021} "
            f"(championship ends NFL week 17), got {weeks!r}"
        )
    if scope.get("week_weights") != "equal":
        raise CommonArtifactError("scope.week_weights must be 'equal'")
    if manifest.get("source_validated") is not True:
        raise CommonArtifactError("manifest must state source_validated: true (full source validated before any filter)")
    if list(manifest.get("columns", [])) != EXPECTED_COLUMNS:
        raise CommonArtifactError(f"columns must be {EXPECTED_COLUMNS}, got {manifest.get('columns')!r}")
    covered = _require(manifest, "seasons_covered", "the seasons the artifact covers")
    sha = _require(manifest, "csv_sha256", "the sha256 of the CSV it describes")
    if not isinstance(sha, str) or len(sha) != 64:
        raise CommonArtifactError("csv_sha256 must be a 64-character sha256")
    return {
        "scoring": scoring, "exact_league_scoring": False, "scope": SCOPE_LABEL, "season_types": ["REG"],
        "weeks": {"through_2020": WEEKS_THROUGH_2020, "from_2021": WEEKS_FROM_2021, "week_weights": "equal"},
        "seasons_covered": [int(s) for s in covered], "csv_sha256": sha,
        "source_validation": {"validated": True, "by": manifest.get("artifact", "common outcome artifact"),
                              "detail": manifest.get("source_validation")},
    }


def load_common_outcomes(csv_path: Path | str, manifest: dict[str, Any]) -> pd.DataFrame:
    """Read the artifact as the outcome frame ``annual_targets`` consumes, with its attrs."""
    facts = validate_common_manifest(manifest)
    csv_path = Path(csv_path)
    actual = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if actual != facts["csv_sha256"]:
        raise CommonArtifactError(f"csv sha256 {actual[:12]}… does not match the manifest's {facts['csv_sha256'][:12]}…")
    raw = pd.read_csv(csv_path)
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
    out = out.sort_values(["player_id", "season"]).reset_index(drop=True)
    out.attrs.update({
        "scope": SCOPE_LABEL, "season_types": ["REG"], "weeks": facts["weeks"], "scoring": facts["scoring"],
        "exact_league_scoring": False, "event": EVENT, "exposure": EXPOSURE,
        "seasons_covered": facts["seasons_covered"], "csv_sha256": facts["csv_sha256"],
        "source_validation": facts["source_validation"],
    })
    return out
