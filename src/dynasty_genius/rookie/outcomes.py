"""Adapter for the common player-season outcome artifact (DG-179, owned by Codex).

Both producers consume ONE artifact so their labels are identical outcomes: per
(player_id, season) the league-window points, games and appearance under one mask
(appeared = games >= 1 within the window; points, games and appearance never disagree).

This adapter:
* loads the CSV + manifest and FAILS CLOSED on a mask that disagrees, duplicate keys or
  id-less rows — it never repairs an artifact it did not build;
* turns appeared rows into the ``season_stats`` map the labels already consume, keeping a
  missing points value missing;
* builds the qualification panel with the position rule the increment set: a cohort player
  is ranked at his DRAFT role in every season (an offensive draftee listed defensive today
  is still offensive), every other player at his weekly-stats position for that season;
* binds the artifact's hashes, scoring id, window rule and closure into the run manifest.

Scoring caveat, carried verbatim: the artifact's points are nflverse default-PPR league-
window research outcomes; exact-league scoring remains unsupported pending complete
attribution; nothing missing is fabricated as zero.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

__all__ = ["CommonOutcomes", "OutcomeInputs", "load_common_outcomes", "outcome_binding", "outcome_inputs",
           "qualification_panel", "season_stats_from_outcomes", "weekly_positions_by_player_season"]

REQUIRED = ("player_id", "season", "points", "games", "appeared")
SCHEMA_VERSION = "dg179_league_season_outcomes_v1"
COVERAGE_STATUSES = ("qualified_research_game_complete_identified_rows", "calendar_checked_game_coverage_unverified")
SCORING_CAVEAT = ("nflverse default-PPR championship-window research outcomes; exact-league scoring is unsupported pending complete "
                  "attribution of lost-fumble scope, fum_rec_td, st_ff and st_fum_rec; nothing missing is fabricated as zero")
QUALIFICATION_NOTE = ("coverage_status 'qualified_research_game_complete_identified_rows' means admitted game ids match the source and the "
                      "exact unattributed-row quarantine is disclosed; it is NOT proof of perfect individual stats and must not be read as "
                      "complete individual data")
TRUE_VALUES = {True, 1, "1", "true", "True", "TRUE"}
FALSE_VALUES = {False, 0, "0", "false", "False", "FALSE"}


@dataclass(frozen=True)
class CommonOutcomes:
    frame: pd.DataFrame
    manifest: Mapping
    csv_path: Path
    manifest_path: Path
    csv_sha256: str
    manifest_sha256: str

    @property
    def labels_through(self) -> int:
        return int(self.manifest["last_complete_season"])

    @property
    def scoring_preset(self) -> str:
        return str(self.manifest["scoring_preset"])

    @property
    def window_rule(self) -> str:
        return str(self.manifest["window_rule"])

    @property
    def covered_seasons(self) -> list[int]:
        """Seasons the artifact labels; anything outside them is UNKNOWN to a consumer."""
        return sorted(int(s) for s in self.manifest["season_windows"])


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_common_outcomes(csv_path: Path | str, manifest_path: Path | str) -> CommonOutcomes:
    csv_path, manifest_path = Path(csv_path), Path(manifest_path)
    frame = pd.read_csv(csv_path)
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise ValueError(f"common outcome artifact lacks columns {missing}")
    idless = frame["player_id"].isna() | (frame["player_id"].astype(str).str.strip() == "")
    if idless.any():
        raise ValueError(f"{int(idless.sum())} rows without a player_id; the artifact must decide them, this adapter will not")
    frame["player_id"] = frame["player_id"].astype(str).str.strip()
    frame["season"] = frame["season"].astype(int)
    if frame.duplicated(["player_id", "season"]).any():
        raise ValueError(f"{int(frame.duplicated(['player_id', 'season']).sum())} duplicate (player_id, season) rows")
    games = pd.to_numeric(frame["games"], errors="coerce")
    appeared = frame["appeared"].map(lambda v: 1 if v in TRUE_VALUES else (0 if v in FALSE_VALUES else None)).astype(float)
    if games.isna().any() or appeared.isna().any():
        raise ValueError("games and appeared must be present on every row and appeared must be boolean (one mask)")
    if ((appeared == 1) != (games >= 1)).any():
        bad = int(((appeared == 1) != (games >= 1)).sum())
        raise ValueError(f"mask disagreement on {bad} rows: appeared must equal games >= 1")
    frame["games"] = games.astype(int)
    frame["appeared"] = appeared.astype(int)
    frame["points"] = pd.to_numeric(frame["points"], errors="coerce")
    manifest = json.loads(manifest_path.read_text())
    _verify_manifest(manifest, csv_path)
    covered = {int(k) for k in manifest["season_windows"]}
    outside = sorted(set(frame["season"].unique()) - covered)
    if outside:
        raise ValueError(f"outcome rows for seasons {outside} that the manifest's season_windows do not cover")
    return CommonOutcomes(frame=frame, manifest=manifest, csv_path=csv_path, manifest_path=manifest_path,
                          csv_sha256=_sha(csv_path), manifest_sha256=_sha(manifest_path))


def _verify_manifest(manifest: Mapping, csv_path: Path) -> None:
    """Fail closed on the implemented DG-179 schema: version, declared CSV hash, honest flags."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version {manifest.get('schema_version')!r} is not {SCHEMA_VERSION!r}")
    for key in ("scoring_preset", "window_rule", "season_windows", "exposure_definition", "last_complete_season", "coverage_status",
                "source_identity", "source_identity_sha256", "scoring_identity", "window_identity", "target_identity", "outputs"):
        if key not in manifest:
            raise ValueError(f"outcome manifest lacks {key}")
    if manifest.get("league_scoring_exact") is not False:
        raise ValueError("league_scoring_exact must be False for this research artifact; an exact-league claim is refused")
    if manifest["coverage_status"] not in COVERAGE_STATUSES:
        raise ValueError(f"coverage_status {manifest['coverage_status']!r} is not a recognised value {COVERAGE_STATUSES}")
    declared = (manifest["outputs"].get("outcomes.csv") or {}).get("sha256")
    actual = _sha(csv_path)
    if declared != actual:
        raise ValueError(f"outcomes.csv sha256 {actual[:12]}… does not match the manifest's declared {str(declared)[:12]}…")


def season_stats_from_outcomes(outcomes: CommonOutcomes) -> dict[tuple[str, int], tuple[float, int]]:
    """(player_id, season) -> (points, games) for APPEARED rows only; absence is the measured zero."""
    rows = outcomes.frame.loc[outcomes.frame["appeared"] == 1]
    return {(str(p), int(s)): (float(pts) if pd.notna(pts) else float("nan"), int(g))
            for p, s, pts, g in rows[["player_id", "season", "points", "games"]].itertuples(index=False)}


def qualification_panel(
    outcomes: CommonOutcomes,
    *,
    weekly_positions: Mapping[tuple[str, int], str],
    draft_roles: Mapping[str, str],
) -> tuple[pd.DataFrame, dict]:
    """The panel the bar is cut on: appeared rows with a position.

    Cohort players (``draft_roles``) rank at their draft role in every season; everyone
    else at the weekly-stats position for that season. Rows with neither are excluded from
    the ranking and COUNTED — they still exist in the outcomes; they just cannot be ranked
    at a position.
    """
    rows = outcomes.frame.loc[outcomes.frame["appeared"] == 1].copy()
    positions = []
    for pid, season in zip(rows["player_id"], rows["season"]):
        role = draft_roles.get(pid)
        positions.append(role if role else weekly_positions.get((pid, int(season))))
    rows["position"] = positions
    without = rows["position"].isna() | (rows["position"].astype(str) == "")
    report = {"appeared_rows": int(len(rows)), "rows_without_position": int(without.sum()),
              "ranked_at_draft_role": int(rows["player_id"].isin(set(draft_roles)).sum())}
    panel = rows.loc[~without, ["player_id", "position", "season", "points", "games"]].reset_index(drop=True)
    return panel, report


def outcome_binding(outcomes: CommonOutcomes) -> dict:
    """What the run manifest carries so nobody can pair these labels with another artifact."""
    m = outcomes.manifest
    return {
        "schema_version": m["schema_version"],
        "csv_path": str(outcomes.csv_path), "csv_sha256": outcomes.csv_sha256,
        "manifest_path": str(outcomes.manifest_path), "manifest_sha256": outcomes.manifest_sha256,
        "declared_outputs": m["outputs"],
        "scoring_preset": outcomes.scoring_preset, "league_scoring_exact": bool(m["league_scoring_exact"]),
        "saved_league_scoring_sha256": m.get("saved_league_scoring_sha256"), "exact_league_scoring_gaps": m.get("exact_league_scoring_gaps"),
        "window_rule": outcomes.window_rule, "season_windows": m["season_windows"], "covered_seasons": outcomes.covered_seasons,
        "labels_through": outcomes.labels_through, "exposure_definition": m["exposure_definition"],
        "appearance_definition": m.get("appearance_definition"), "zero_definition": m.get("zero_definition"),
        "coverage_status": m["coverage_status"], "qualification_note": QUALIFICATION_NOTE,
        "source_validation_limitations": m.get("source_validation_limitations"),
        "source_identity_sha256": m["source_identity_sha256"], "scoring_identity": m["scoring_identity"],
        "window_identity": m["window_identity"], "target_identity": m["target_identity"],
        "outcome_rows": int(len(outcomes.frame)), "captured_at": m.get("captured_at"),
        "scoring_caveat": SCORING_CAVEAT,
    }


def weekly_positions_by_player_season(weekly: pd.DataFrame) -> dict[tuple[str, int], str]:
    """(player_id, season) -> the modal REG-season position string; ties resolve alphabetically
    so the map is deterministic; rows without a position or a player id contribute nothing."""
    rows = weekly.loc[(weekly["season_type"] == "REG") & weekly["position"].notna() & weekly["player_id"].notna()]
    out: dict[tuple[str, int], str] = {}
    for (pid, season), g in rows.groupby(["player_id", "season"]):
        counts = g["position"].astype(str).value_counts()
        best = counts[counts == counts.max()].index
        out[(str(pid), int(season))] = sorted(best)[0]
    return out


@dataclass(frozen=True)
class OutcomeInputs:
    """Everything the labels need, built from the common artifact and bound to it."""
    outcomes: CommonOutcomes
    season_stats: dict
    qualifying: set
    panel: pd.DataFrame
    panel_report: dict
    binding: dict

    @property
    def labels_through(self) -> int:
        return self.outcomes.labels_through

    @property
    def covered_seasons(self) -> set[int]:
        return set(self.outcomes.covered_seasons)


def outcome_inputs(
    csv_path: Path | str,
    manifest_path: Path | str,
    *,
    cohort: pd.DataFrame,
    weekly_positions: Mapping[tuple[str, int], str],
    bar: Mapping[str, int],
    require_positions: tuple[str, ...] = ("QB", "RB", "WR", "TE"),
) -> OutcomeInputs:
    """Load, verify and bind the common artifact; cut the qualification bar on it.

    ``cohort`` supplies the draft roles (gsis_id -> draft-table position) so every cohort
    player is ranked at his draft role in every season. The bar is cut only on positions the
    bar names; a (season, position) group smaller than its bar rank raises, as before.
    """
    from src.dynasty_genius.rookie.labels import qualifying_season_keys

    outcomes = load_common_outcomes(csv_path, manifest_path)
    draft_roles = {str(g): str(p) for g, p in zip(cohort["gsis_id"], cohort["position"]) if pd.notna(g)}
    panel, report = qualification_panel(outcomes, weekly_positions=weekly_positions, draft_roles=draft_roles)
    ranked = panel.loc[panel["position"].isin(require_positions)]
    qualifying = qualifying_season_keys(ranked, {p: bar[p] for p in require_positions if p in bar})
    return OutcomeInputs(outcomes=outcomes, season_stats=season_stats_from_outcomes(outcomes), qualifying=qualifying,
                         panel=panel, panel_report=report, binding=outcome_binding(outcomes))
