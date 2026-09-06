"""Round 2, item 5 — a longer BASIC historical cohort from first-party football statistics.

The served Engine B feature file starts in 2018 and carries modern tracking columns that
do not exist further back. For horizons of three to five seasons that file cannot
produce a closed label before 2020 at the earliest, so the evaluable history is one or
two folds. This module builds a plain cohort from what exists for every season since the
weekly stats begin: production, games, age, one lag, and where the player was last seen.

Definitions (each is a stated rule, not an inference):
  * ``ppg_t`` and ``games_t`` are ALL games with a stat line in season t (regular season
    and postseason), the DG-024 definition of the production feature. The REG-scope
    LABEL is built separately by ``annual_outcomes`` on the agreed event.
  * A player has a row for season t if he appeared in t or in t-1 (``COHORT_RULE``). A
    whole missed season after an active one is therefore a row with ``games_t = 0`` and
    ``ppg_t = NaN`` — an observation of absence, never a fabricated stat line. After two
    straight absent seasons he leaves the cohort; his next appearance re-enters him.
  * ``position`` is the season's modal stat-line position (what he did that year);
    ``listed_position`` is the players table's current listing, kept beside it.
  * ``age`` is season minus birth year from the players table; a missing birth date is
    ``identity_status = resolved_no_birth_date`` with ``age = NaN``, not a guess.
  * ``seasons_played`` counts seasons OBSERVED since the first pulled season; it is
    left-censored, not career length (a 32-year-old in the first season shows 1).
  * ``position`` is the season's modal stat-line position when that is an offensive one.
    When it is not (a two-way player whose stat lines say CB), a SAME-SEASON historical
    roster role may stand in: roster rows dated inside that season, exactly one distinct
    offensive role among their position/depth-chart columns, else abstain. Today's listing
    never resolves a historical fold; the stat-line position and the evidence stay on the
    row (``statline_position``, ``position_source``, ``role_evidence``). Role evidence
    chooses the MODEL cohort only — league eligibility is Sleeper's to say.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from src.dynasty_genius.eval.annual_outcomes import SCORING_COLUMN

OFFENSIVE_POSITIONS: frozenset[str] = frozenset({"QB", "RB", "WR", "TE"})
ROLE_SOURCES: tuple[str, ...] = (
    "statline", "roster_same_season", "conflicting_roster_roles", "no_offensive_role", "no_roster_evidence",
)
ROSTER_ROLE_COLUMNS = ["gsis_id", "season", "week", "position", "depth_chart_position"]


def resolve_offensive_role(statline_position: str | None, roster_rows: pd.DataFrame) -> tuple[str | None, str, dict]:
    """Which offensive position models this player-season, and on what evidence.

    ``roster_rows`` must already be the player's rows for THAT season only (the caller
    filters by season; this function never looks at another season). Returns
    ``(position or None, source, evidence)``.
    """
    evidence: dict = {"statline_position": statline_position}
    if statline_position in OFFENSIVE_POSITIONS:
        return statline_position, "statline", evidence
    positions = sorted({str(x) for x in roster_rows["position"].dropna()}) if len(roster_rows) else []
    depths = sorted({str(x) for x in roster_rows["depth_chart_position"].dropna()}) if len(roster_rows) else []
    weeks = sorted({int(w) for w in roster_rows["week"].dropna()}) if len(roster_rows) else []
    roles = sorted((set(positions) | set(depths)) & OFFENSIVE_POSITIONS)
    evidence.update({"roster_positions": positions, "roster_depth_positions": depths,
                     "roster_weeks": weeks, "offensive_roles_seen": roles})
    if len(roster_rows) == 0:
        return None, "no_roster_evidence", evidence
    if len(roles) == 1:
        return roles[0], "roster_same_season", evidence
    if len(roles) > 1:
        return None, "conflicting_roster_roles", evidence
    return None, "no_offensive_role", evidence

BASIC_FEATURES: list[str] = [
    "ppg_t", "games_t", "age", "ppg_t_minus_1", "games_t_minus_1", "ppg_t_minus_1_available",
    "ppg_last_observed", "seasons_since_last_observed", "seasons_played",
]
COHORT_RULE = (
    "a row exists for season t if the player appeared in season t or t-1 (a whole missed "
    "season after an active one is a zero-games row); two straight absent seasons leave the cohort"
)
PRODUCTION_SCOPE = "ALL games with a stat line (REG + POST), the DG-024 production definition"


def validate_players_table(players: pd.DataFrame) -> dict:
    """The identity source must have one row per gsis id with the id present."""
    required = ["gsis_id", "position", "birth_date"]
    missing = [c for c in required if c not in players.columns]
    if missing:
        raise ValueError(f"players table lacks columns {missing}")
    ids = players["gsis_id"]
    n_missing = int(ids.isna().sum() + (ids.astype(str).str.strip() == "").sum())
    if n_missing:
        raise ValueError(f"{n_missing} players rows have no gsis id")
    dup = int(ids.duplicated().sum())
    if dup:
        raise ValueError(f"{dup} duplicate gsis ids in the players table")
    return {"rows": int(len(players)), "duplicate_gsis": dup, "missing_gsis": n_missing,
            "missing_birth_date": int(players["birth_date"].isna().sum())}


def _season_production(weekly: pd.DataFrame) -> pd.DataFrame:
    """Per (player, season): all-games games and PPG, and the modal stat-line position."""
    w = weekly.copy()
    w["season"] = w["season"].astype(int)
    w[SCORING_COLUMN] = pd.to_numeric(w[SCORING_COLUMN], errors="coerce")
    grouped = w.groupby(["player_id", "season"], sort=True)
    prod = pd.concat([
        grouped["week"].nunique().rename("games_t"),
        grouped[SCORING_COLUMN].sum().rename("points_all"),
        grouped["position"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else None).rename("position"),
    ], axis=1).reset_index()
    prod["ppg_t"] = prod["points_all"] / prod["games_t"]
    return prod


def build_basic_cohort(
    weekly: pd.DataFrame,
    players: pd.DataFrame,
    *,
    seasons: Iterable[int],
    roster_roles: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """One feature row per (player, season) under COHORT_RULE, for the requested seasons.

    ``roster_roles`` (gsis_id, season, week, position, depth_chart_position) enables the
    same-season offensive-role fallback for non-offensive stat-line positions.
    """
    import json as _json

    seasons = sorted(int(s) for s in seasons)
    roster_by_key: dict[tuple[str, int], pd.DataFrame] = {}
    if roster_roles is not None:
        rr = roster_roles[ROSTER_ROLE_COLUMNS].copy()
        rr["season"] = rr["season"].astype(int)
        for (pid, season), part in rr.groupby(["gsis_id", "season"], sort=False):
            roster_by_key[(str(pid), int(season))] = part
    empty_roster = pd.DataFrame(columns=ROSTER_ROLE_COLUMNS)
    prod = _season_production(weekly)
    prod = prod[prod["season"].isin(seasons) | prod["season"].isin([seasons[0] - 1])]
    identity = players.set_index("gsis_id")
    birth_year = pd.to_datetime(identity["birth_date"], errors="coerce").dt.year

    rows: list[dict] = []
    for player_id, part in prod.sort_values("season").groupby("player_id", sort=True):
        by_season = part.set_index("season")
        active = set(int(s) for s in by_season.index)
        first = min(active)
        played_so_far = 0
        last_seen: int | None = None
        last_ppg = np.nan
        for t in range(first, seasons[-1] + 1):
            if t in active:
                played_so_far += 1
            in_cohort = (t in active) or ((t - 1) in active)
            if t in seasons and in_cohort and t >= seasons[0]:
                this = by_season.loc[t] if t in active else None
                prev = by_season.loc[t - 1] if (t - 1) in active else None
                listed = identity["position"].get(player_id) if player_id in identity.index else None
                by = birth_year.get(player_id) if player_id in identity.index else np.nan
                if player_id not in identity.index:
                    status = "unresolved_in_players_table"
                elif pd.isna(by):
                    status = "resolved_no_birth_date"
                else:
                    status = "resolved"
                statline = (this["position"] if this is not None else (prev["position"] if prev is not None else None))
                resolved, source, evidence = resolve_offensive_role(
                    statline, roster_by_key.get((str(player_id), t), empty_roster) if roster_roles is not None else empty_roster,
                )
                rows.append({
                    "player_id": player_id,
                    "feature_season": t,
                    "position": resolved if resolved is not None else statline,
                    "statline_position": statline,
                    "position_source": source,
                    "role_evidence": _json.dumps(evidence, default=str),
                    "listed_position": listed,
                    "identity_status": status,
                    "age": float(t - by) if not pd.isna(by) else np.nan,
                    "ppg_t": float(this["ppg_t"]) if this is not None else np.nan,
                    "games_t": int(this["games_t"]) if this is not None else 0,
                    "ppg_t_minus_1": float(prev["ppg_t"]) if prev is not None else np.nan,
                    "games_t_minus_1": int(prev["games_t"]) if prev is not None else 0,
                    "ppg_t_minus_1_available": int(prev is not None),
                    "ppg_last_observed": float(this["ppg_t"]) if this is not None else last_ppg,
                    "seasons_since_last_observed": 0 if this is not None else (t - last_seen if last_seen is not None else np.nan),
                    "seasons_played": played_so_far,
                    "total_points_t": float(this["points_all"]) if this is not None else 0.0,
                })
            if t in active:
                last_seen = t
                last_ppg = float(by_season.loc[t, "ppg_t"])
    out = pd.DataFrame(rows)
    out.attrs.update({"cohort_rule": COHORT_RULE, "production_scope": PRODUCTION_SCOPE,
                      "features": list(BASIC_FEATURES),
                      "role_fallback": "none supplied" if roster_roles is None else
                      "same-season roster role for non-offensive stat-line positions; exactly one offensive role or abstain"})
    return out.sort_values(["player_id", "feature_season"]).reset_index(drop=True)
