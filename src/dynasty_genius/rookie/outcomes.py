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
SCORING_CAVEAT = ("nflverse default-PPR league-window research outcomes; exact-league scoring is unsupported pending complete "
                  "attribution of lost-fumble scope, fum_rec_td, st_ff and st_fum_rec; nothing missing is fabricated as zero")


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
        closure = self.manifest.get("closure") or {}
        value = closure.get("labels_through") or self.manifest.get("labels_through")
        if value is None:
            raise ValueError("outcome manifest does not state closure.labels_through")
        return int(value)

    @property
    def scoring_id(self) -> str:
        scoring = self.manifest.get("scoring") or {}
        value = scoring.get("id") if isinstance(scoring, dict) else scoring
        if not value:
            raise ValueError("outcome manifest does not state a scoring id")
        return str(value)

    @property
    def window_rule(self) -> str:
        window = self.manifest.get("window") or {}
        value = window.get("rule") if isinstance(window, dict) else window
        if not value:
            raise ValueError("outcome manifest does not state the window rule")
        return str(value)


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
    appeared = pd.to_numeric(frame["appeared"], errors="coerce")
    if games.isna().any() or appeared.isna().any() or not set(appeared.unique()) <= {0, 1}:
        raise ValueError("games and appeared must be present on every row and appeared must be 0/1 (one mask)")
    if ((appeared == 1) != (games >= 1)).any():
        bad = int(((appeared == 1) != (games >= 1)).sum())
        raise ValueError(f"mask disagreement on {bad} rows: appeared must equal games >= 1")
    frame["games"] = games.astype(int)
    frame["appeared"] = appeared.astype(int)
    frame["points"] = pd.to_numeric(frame["points"], errors="coerce")
    manifest = json.loads(manifest_path.read_text())
    return CommonOutcomes(frame=frame, manifest=manifest, csv_path=csv_path, manifest_path=manifest_path,
                          csv_sha256=_sha(csv_path), manifest_sha256=_sha(manifest_path))


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
    return {
        "artifact": outcomes.manifest.get("artifact"),
        "csv_path": str(outcomes.csv_path), "csv_sha256": outcomes.csv_sha256,
        "manifest_path": str(outcomes.manifest_path), "manifest_sha256": outcomes.manifest_sha256,
        "scoring_id": outcomes.scoring_id, "window_rule": outcomes.window_rule, "labels_through": outcomes.labels_through,
        "mask": outcomes.manifest.get("mask"), "rows": int(len(outcomes.frame)),
        "seasons": [int(outcomes.frame["season"].min()), int(outcomes.frame["season"].max())],
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
