"""Executable S1-S34 contract packet for the v9 D2a behavioral RED.

This is deliberately not named ``test_*``: F2 imports and executes the whole
packet as one test, preserving the ratified one-failure RED ratchet.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

TARGET_SEASONS = list(range(2016, 2026))
WEEKLY_NEW_COLUMNS = (
    "completions",
    "sack_yards_lost",
    "passing_epa",
)
SEASON_SUMMARY_COLUMNS = ("player_id", "season", "position", "passing_cpoe")
ATTRITION_KEYS = {
    "no_target_season",
    "rookie_no_priors",
    "cohort_ineligible_prior",
    "cohort_ineligible_unobserved",
}

# These are the shipped-suite changes authorized by amendment B5. GREEN must
# update the old R27/R30 fixtures to carry both axes, reasons, flags, games,
# and all four explicit count keys; target_season remains invalid at F28.
F28_SHIPPED_SUITE_DELTAS = (
    "classified rows add eligibility,target,reasons,decision_supported",
    "all rows carry qualifying_games under the two-axis games law",
    "attrition counts use exactly four keys with explicit zeros",
    "cohort_ineligible_prior and cohort_ineligible_unobserved are admitted",
    "rookie_no_priors plus no_target_season refuses universe_membership_violation",
    "F28 identity stays player_id,season; target_season is rejected",
)


def _weekly_row(player: str, season: int, **overrides: Any) -> dict[str, Any]:
    row = {
        "player_id": player,
        "player_name": player,
        "position": "QB",
        "team": "A",
        "season": season,
        "week": 1,
        "season_type": "REG",
        "attempts": 20,
        "completions": 10,
        "sacks_suffered": 2,
        "passing_yards": 100,
        "passing_tds": 1,
        "passing_interceptions": 1,
        "sack_yards_lost": -10,
        "passing_epa": 2.0,
        "carries": 2,
        "rushing_yards": 10,
        "rushing_tds": 0,
        "receptions": 0,
        "receiving_yards": 0,
        "receiving_tds": 0,
        "sack_fumbles_lost": 0,
        "rushing_fumbles_lost": 0,
        "receiving_fumbles_lost": 0,
        "passing_2pt_conversions": 0,
        "rushing_2pt_conversions": 0,
        "receiving_2pt_conversions": 0,
    }
    row.update(overrides)
    return row


def _state(tmp_path: Path, name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot = tmp_path / f"{name}.parquet"
    snapshot.write_bytes(b"v9-red-snapshot")
    return {
        "status": "ok",
        "frame": pd.DataFrame(rows),
        "metadata": {
            "dataset": name,
            "raw_snapshot_path": str(snapshot),
            "source_timestamp": "2026-07-20T20:36:00-04:00",
            "parser_version": "qb_validation_ingest.v2",
            "completeness": "ok",
        },
    }


def _sources(tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    weekly = [_weekly_row("veteran", season) for season in range(2015, 2026)]
    weekly += [
        _weekly_row("no-target", 2023),
        _weekly_row("rookie", 2025),
        _weekly_row("prior-zero-target", 2025),
        _weekly_row(
            "both-reasons",
            2023,
            attempts=0,
            completions=0,
            sacks_suffered=0,
            passing_yards=0,
            passing_tds=0,
            passing_interceptions=0,
            sack_yards_lost=0,
            passing_epa=None,
            carries=1,
        ),
        _weekly_row("both-reasons", 2025),
        _weekly_row("zero-denom", 2023),
        _weekly_row(
            "zero-denom",
            2024,
            attempts=0,
            completions=0,
            sacks_suffered=0,
            passing_yards=-5,
            passing_tds=0,
            passing_interceptions=0,
            sack_yards_lost=0,
            passing_epa=None,
            carries=1,
        ),
        _weekly_row("zero-denom", 2025),
        _weekly_row(
            "traded",
            2024,
            week=1,
            team="A",
            attempts=20,
            completions=10,
            sacks_suffered=2,
            passing_yards=100,
            passing_tds=1,
            passing_interceptions=1,
            sack_yards_lost=-10,
            passing_epa=None,
            rushing_tds=1,
        ),
        _weekly_row(
            "traded",
            2024,
            week=2,
            team="B",
            attempts=10,
            completions=5,
            sacks_suffered=3,
            passing_yards=50,
            passing_tds=0,
            passing_interceptions=0,
            sack_yards_lost=-15,
            passing_epa=3.0,
            rushing_tds=1,
        ),
        _weekly_row("traded", 2025),
        _weekly_row(
            "rb-team-b",
            2024,
            position="RB",
            team="B",
            attempts=0,
            completions=0,
            sacks_suffered=0,
            passing_yards=0,
            passing_tds=0,
            passing_interceptions=0,
            sack_yards_lost=0,
            passing_epa=None,
            carries=10,
            rushing_tds=3,
        ),
        _weekly_row("old-qb", 2024),
        _weekly_row("old-qb", 2025),
        # round-1 B2 regression (implementer-added per Codex's 21:30 request):
        # prior NON-QB weekly history must block rookie classification.
        _weekly_row(
            "hist-rb",
            2024,
            position="RB",
            team="C",
            attempts=0,
            completions=0,
            sacks_suffered=0,
            passing_yards=0,
            passing_tds=0,
            passing_interceptions=0,
            sack_yards_lost=0,
            passing_epa=None,
            carries=6,
            rushing_tds=0,
        ),
        _weekly_row("hist-rb", 2025, team="C"),
    ]
    roster_rows = [
        {
            "player_id": "veteran",
            "gsis_id": "veteran",
            "season": season,
            "week": 1,
            "position": "QB",
            "game_type": "REG",
            "status": "ACT",
        }
        for season in range(2015, 2026)
    ]
    roster_rows += [
        {
            "player_id": player,
            "gsis_id": player,
            "season": 2024,
            "week": 1,
            "position": "QB",
            "game_type": "REG",
            "status": status,
        }
        for player, status in (
            ("no-target", "RES"),
            ("prior-zero-target", "ACT"),
            ("zero-unobserved", "DEV"),
            ("zero-denom", "ACT"),
            ("traded", "ACT"),
            ("old-qb", "ACT"),
        )
    ]
    players = [
        {
            "gsis_id": player,
            "display_name": player,
            "birth_date": "1980-01-01" if player == "old-qb" else "1995-01-01",
            "college_name": "Example U",
        }
        for player in (
            "veteran",
            "no-target",
            "rookie",
            "prior-zero-target",
            "zero-unobserved",
            "both-reasons",
            "zero-denom",
            "traded",
            "old-qb",
        )
    ]
    summaries = [
        {
            "player_id": "veteran",
            "season": season,
            "position": "QB",
            "passing_cpoe": 2.5,
        }
        for season in range(2015, 2026)
    ]
    summaries += [
        {
            "player_id": "traded",
            "season": 2024,
            "position": "QB",
            "passing_cpoe": 7.125,
        },
        {"player_id": "old-qb", "season": 2024, "position": "QB", "passing_cpoe": -1.0},
    ]
    pbp = [
        {
            "season": season,
            "week": 1,
            "season_type": "REG",
            "pass": 1,
            "pass_oe": 0.1,
            "offense_team": team,
        }
        for season in range(2015, 2026)
        for team in ("A", "B")
    ]
    for row in pbp:
        if row["season"] == 2024 and row["offense_team"] == "B":
            row["pass_oe"] = 0.2
    states = {
        "weekly": _state(tmp_path, "weekly", weekly),
        "season_summary": _state(tmp_path, "season_summary", summaries),
        "players": _state(tmp_path, "players", players),
        "rosters": _state(tmp_path, "rosters", roster_rows),
        "ff_playerids": _state(
            tmp_path,
            "ff_playerids",
            [
                {
                    "gsis_id": p["gsis_id"],
                    "sleeper_id": f"s-{p['gsis_id']}",
                    "name": p["display_name"],
                }
                for p in players
            ],
        ),
        "draft_picks": _state(
            tmp_path,
            "draft_picks",
            [
                {
                    "gsis_id": "someone-else",
                    "pfr_player_name": "Someone Else",
                    "season": 2020,
                    "round": 1,
                    "pick": 1,
                    "age": 21,
                    "college": "Elsewhere",
                }
            ],
        ),
        "pbp": _state(tmp_path, "pbp", pbp),
    }
    return states


def _registration(module: Any) -> tuple[dict[str, Any], str]:
    registration = {"study": "qb-validation-v9", "matrix": "D2a"}
    digest = module.build_registration(registration)["sha256"]
    return registration, digest


def _build(module: Any, sources: dict[str, Any]) -> dict[str, Any]:
    registration, digest = _registration(module)
    return module.build_study_matrix(
        sources, registration=registration, expected_registration_hash=digest
    )


def _find(rows: list[dict[str, Any]], player: str, season: int) -> dict[str, Any]:
    return next(
        row
        for row in rows
        if row["player_id"] == player and row["target_season"] == season
    )


def _reason(exc: pytest.ExceptionInfo[BaseException]) -> str:
    return str(getattr(exc.value, "reason", exc.value))


def exercise_s1_s34(module: Any, tmp_path: Path) -> None:
    """Exercise every canonical v9 amendment seed under one F2 test row."""
    sources = _sources(tmp_path)
    artifact = _build(module, sources)

    # S1-S5, S20, S27, S29: exact feature construction and missingness.
    traded = _find(artifact["matrix"], "traded", 2025)
    assert traded["epa_per_dropback"] == pytest.approx(3 / 13)
    assert traded["sack_rate"] == pytest.approx(5 / 35)
    assert traded["any_a"] == pytest.approx((150 + 20 - 45 - 25) / 35)
    assert traded["completion_pct"] == pytest.approx(15 / 30)
    assert traded["cpoe"] == 7.125
    assert traded["rush_td_share"] == pytest.approx(0.25)
    assert traded["team_proe"] == pytest.approx(0.2)
    zero = _find(artifact["matrix"], "zero-denom", 2025)
    assert zero["completion_pct"] is None and zero["sack_rate"] is None
    assert zero["cpoe"] is None and zero["epa_per_dropback"] is None
    old = _find(artifact["matrix"], "old-qb", 2025)
    assert old["age_at_season_start"] >= 41

    # S10-S12, S14, S17-S18, S23-S24: total, deterministic output schema.
    assert artifact["matrix_version"] == "qb_validation_matrix.v1"
    assert artifact["decision_supported"] is False
    assert artifact["coverage"]["target_seasons"] == TARGET_SEASONS
    assert set(artifact["coverage"]["rows_per_season"]) == {
        str(year) for year in TARGET_SEASONS
    }
    for year in TARGET_SEASONS:
        assert artifact["coverage"]["rows_per_season"][str(year)] == sum(
            row["target_season"] == year for row in artifact["matrix"]
        )
    matrix_keys = {(r["player_id"], r["target_season"]) for r in artifact["matrix"]}
    audit = [
        row for season in artifact["attrition"].values() for row in season["audit"]
    ]
    audit_keys = {(r["player_id"], r["target_season"]) for r in audit}
    assert matrix_keys.isdisjoint(audit_keys)
    assert len(matrix_keys) == len(artifact["matrix"])
    assert len(audit_keys) == len(audit)
    assert all(
        row["eligibility"] == "cohort_admitted"
        and row["target"] in {"target_evaluable", "no_target_season"}
        and row["decision_supported"] is False
        for row in artifact["matrix"]
    )
    by_player = {row["player_id"]: row for row in audit if row["target_season"] == 2025}
    assert by_player["rookie"]["outcome_class"] == "rookie_no_priors"
    assert by_player["prior-zero-target"]["outcome_class"] == "cohort_ineligible_prior"
    assert (
        by_player["zero-unobserved"]["outcome_class"] == "cohort_ineligible_unobserved"
    )
    assert by_player["both-reasons"]["reasons"] == [
        "zero_career_dropbacks",
        "no_prior_roster_presence",
    ]
    # round-1 B2 regression (implementer-added per Codex's 21:30 request):
    # a prior REG RB weekly row is NFL history — never rookie_no_priors.
    assert by_player["hist-rb"]["outcome_class"] == "cohort_ineligible_prior"
    assert by_player["hist-rb"]["reasons"] == [
        "zero_career_dropbacks",
        "no_prior_roster_presence",
    ]
    assert _find(artifact["matrix"], "no-target", 2025)["target"] == "no_target_season"
    assert module.scan_banned_language(artifact) is None
    missing_flag = copy.deepcopy(artifact)
    missing_flag["matrix"][0].pop("decision_supported")
    with pytest.raises(Exception, match="decision_supported_missing_on_model"):
        module.scan_banned_language(missing_flag)

    # S9, S19, S24: copies, as-of isolation, and input-order determinism.
    frozen = copy.deepcopy(artifact)
    sources["weekly"]["frame"].loc[0, "passing_yards"] = 999_999
    assert artifact == frozen
    reordered = _sources(tmp_path / "reordered")
    for state in reordered.values():
        state["frame"] = (
            state["frame"].sample(frac=1, random_state=7).reset_index(drop=True)
        )
    assert _build(module, reordered) == artifact
    future = _sources(tmp_path / "future")
    mask = (future["weekly"]["frame"]["player_id"] == "veteran") & (
        future["weekly"]["frame"]["season"] == 2025
    )
    future["weekly"]["frame"].loc[mask, "passing_yards"] = 50_000
    assert _find(_build(module, future)["matrix"], "veteran", 2025) == _find(
        artifact["matrix"], "veteran", 2025
    )
    negative = _sources(tmp_path / "negative-any-a")
    traded_prior = (negative["weekly"]["frame"]["player_id"] == "traded") & (
        negative["weekly"]["frame"]["season"] == 2024
    )
    negative["weekly"]["frame"].loc[traded_prior, "passing_yards"] = -1_000
    assert _find(_build(module, negative)["matrix"], "traded", 2025)["any_a"] < 0
    non_qb_summary = _sources(tmp_path / "non-qb-summary")
    summary_mask = non_qb_summary["season_summary"]["frame"]["player_id"] == "traded"
    non_qb_summary["season_summary"]["frame"].loc[summary_mask, "position"] = "RB"
    assert (
        _find(_build(module, non_qb_summary)["matrix"], "traded", 2025)["cpoe"] is None
    )

    # S35 (amendment r7, implementer-added): coverage.cpoe_non_qb_joins under
    # the TOTAL precedence rule — position is tested independently of value.
    counts_2025 = artifact["coverage"]["cpoe_non_qb_joins"]
    assert set(counts_2025) == {str(year) for year in TARGET_SEASONS}
    assert set(counts_2025) == set(artifact["coverage"]["rows_per_season"])
    assert all(type(value) is int for value in counts_2025.values())
    # (a) absent 1b row → cpoe null, NOT counted (canonical fixture: every
    # present summary reads QB, so the whole counter is zero).
    assert zero["cpoe"] is None
    assert set(counts_2025.values()) == {0}
    # (b) joined non-QB row with a PRESENT cpoe → counted once, cpoe null.
    non_qb_artifact = _build(module, non_qb_summary)
    assert _find(non_qb_artifact["matrix"], "traded", 2025)["cpoe"] is None
    non_qb_counts = non_qb_artifact["coverage"]["cpoe_non_qb_joins"]
    assert non_qb_counts["2025"] == 1
    assert all(count == 0 for season, count in non_qb_counts.items() if season != "2025")
    # (b') OVERLAP: joined non-QB row whose cpoe is ALSO null → STILL counted.
    overlap = _sources(tmp_path / "non-qb-and-null-cpoe")
    overlap_mask = overlap["season_summary"]["frame"]["player_id"] == "traded"
    overlap["season_summary"]["frame"].loc[overlap_mask, "position"] = "RB"
    overlap["season_summary"]["frame"].loc[overlap_mask, "passing_cpoe"] = None
    overlap_artifact = _build(module, overlap)
    assert _find(overlap_artifact["matrix"], "traded", 2025)["cpoe"] is None
    assert overlap_artifact["coverage"]["cpoe_non_qb_joins"]["2025"] == 1
    # (c) joined QB-position row with null cpoe → cpoe null, NOT counted.
    qb_null = _sources(tmp_path / "qb-position-null-cpoe")
    qb_null_mask = qb_null["season_summary"]["frame"]["player_id"] == "traded"
    qb_null["season_summary"]["frame"].loc[qb_null_mask, "passing_cpoe"] = None
    qb_null_artifact = _build(module, qb_null)
    assert _find(qb_null_artifact["matrix"], "traded", 2025)["cpoe"] is None
    assert set(qb_null_artifact["coverage"]["cpoe_non_qb_joins"].values()) == {0}
    assert module.scan_banned_language(overlap_artifact) is None

    # S6, S32: semantic numeric and all seven null-count/yardage refusals.
    corruptions = (
        ("attempts", float("inf")),
        ("attempts", -1),
        ("attempts", 1.5),
        ("completions", 21),
        ("sack_yards_lost", 1),
    )
    for column, value in corruptions:
        bad = _sources(tmp_path / f"bad-{column}-{str(value).replace('.', '-')}")
        # pandas 3 refuses lossy float assignment into an int64 column before
        # the product boundary can inspect the deliberately corrupt scalar.
        # Object dtype keeps the fixture executable without normalizing it.
        if column == "attempts" and value in {float("inf"), 1.5}:
            bad["weekly"]["frame"][column] = bad["weekly"]["frame"][
                column
            ].astype(object)
        bad["weekly"]["frame"].loc[0, column] = value
        with pytest.raises(Exception) as exc:
            _build(module, bad)
        assert "stat_value_invalid" in _reason(exc)
    for column in {
        "attempts",
        "completions",
        "sacks_suffered",
        "passing_tds",
        "passing_interceptions",
        "sack_yards_lost",
        "passing_yards",
    }:
        bad = _sources(tmp_path / f"null-{column}")
        bad["weekly"]["frame"].loc[0, column] = None
        with pytest.raises(Exception) as exc:
            _build(module, bad)
        assert "stat_value_invalid" in _reason(exc)

    # S7-S8: gate order and exact registration behavior.
    registration, digest = _registration(module)
    for reg, pin in ((None, digest), (registration, None), (registration, "0" * 64)):
        with pytest.raises(Exception, match="preregistration_missing"):
            module.build_study_matrix(
                sources, registration=reg, expected_registration_hash=pin
            )
    naked = {
        name: state["frame"] for name, state in _sources(tmp_path / "naked").items()
    }
    with pytest.raises(Exception) as exc:
        module.build_study_matrix(
            naked, registration=registration, expected_registration_hash=digest
        )
    assert "source_unavailable" in _reason(exc)
    missing_season = _sources(tmp_path / "missing-season")
    missing_season["weekly"]["frame"] = missing_season["weekly"]["frame"].loc[
        missing_season["weekly"]["frame"]["season"] != 2024
    ]
    with pytest.raises(Exception, match="source_season_missing"):
        _build(module, missing_season)
    # round-1 B1 regression (implementer-added per Codex's 21:30 request):
    # coverage is exact for EVERY time-scoped dataset, not weekly alone.
    for gapped in ("season_summary", "rosters", "pbp"):
        bad = _sources(tmp_path / f"missing-2015-{gapped}")
        bad[gapped]["frame"] = bad[gapped]["frame"].loc[
            bad[gapped]["frame"]["season"] != 2015
        ]
        with pytest.raises(Exception, match="source_season_missing"):
            _build(module, bad)
    # round-2 B1 regression (implementer-added per Codex's 21:47 request):
    # coverage is an EXACT SET — a surplus out-of-window 2014 REG row refuses
    # on every time-scoped dataset (it would otherwise leak into career
    # aggregates outside the registered window).
    surplus_rows = {
        "weekly": _weekly_row("veteran", 2014),
        "season_summary": {
            "player_id": "veteran", "season": 2014, "position": "QB",
            "passing_cpoe": 1.0,
        },
        "rosters": {
            "player_id": "veteran", "gsis_id": "veteran", "season": 2014,
            "week": 1, "position": "QB", "game_type": "REG", "status": "ACT",
        },
        "pbp": {
            "season": 2014, "week": 1, "season_type": "REG", "pass": 1,
            "pass_oe": 0.1, "offense_team": "A",
        },
    }
    for dataset, extra in surplus_rows.items():
        bad = _sources(tmp_path / f"surplus-2014-{dataset}")
        bad[dataset]["frame"] = pd.concat(
            [bad[dataset]["frame"], pd.DataFrame([extra])], ignore_index=True
        )
        with pytest.raises(Exception, match="season_out_of_scope"):
            _build(module, bad)

    # S13, S15-S16, S34: the authorized F28 shipped-suite delta.
    assert F28_SHIPPED_SUITE_DELTAS == tuple(F28_SHIPPED_SUITE_DELTAS)
    rows = [
        {
            "player_id": "p1",
            "season": 2025,
            "eligibility": "cohort_admitted",
            "target": "target_evaluable",
            "outcome_class": "evaluable",
            "qualifying_games": 2,
            "reasons": [],
            "decision_supported": False,
            "ppg": 10.0,
        },
        {
            "player_id": "p2",
            "season": 2025,
            "eligibility": "cohort_admitted",
            "target": "no_target_season",
            "outcome_class": "no_target_season",
            "qualifying_games": 0,
            "reasons": [],
            "decision_supported": False,
        },
        {
            "player_id": "p3",
            "season": 2025,
            "eligibility": "rookie_no_priors",
            "target": "target_evaluable",
            "outcome_class": "rookie_no_priors",
            "qualifying_games": 1,
            "reasons": [],
            "decision_supported": False,
        },
        {
            "player_id": "p4",
            "season": 2025,
            "eligibility": "cohort_ineligible_prior",
            "target": "target_evaluable",
            "outcome_class": "cohort_ineligible_prior",
            "qualifying_games": 1,
            "reasons": ["zero_career_dropbacks"],
            "decision_supported": False,
        },
        {
            "player_id": "p5",
            "season": 2025,
            "eligibility": "cohort_ineligible_prior",
            "target": "no_target_season",
            "outcome_class": "cohort_ineligible_unobserved",
            "qualifying_games": 0,
            "reasons": ["zero_career_dropbacks"],
            "decision_supported": False,
        },
    ]
    counts = dict.fromkeys(sorted(ATTRITION_KEYS), 0)
    counts.update(
        {
            "no_target_season": 1,
            "rookie_no_priors": 1,
            "cohort_ineligible_prior": 1,
            "cohort_ineligible_unobserved": 1,
        }
    )
    module.validate_attrition_classes(rows, counts)
    unreachable = dict(
        rows[2], player_id="unreachable", target="no_target_season", qualifying_games=0
    )
    with pytest.raises(Exception, match="universe_membership_violation"):
        module.validate_attrition_classes(rows + [unreachable], counts)
    for mutation in (
        dict(rows[1], player_id="bad-no-target-games", qualifying_games=1),
        dict(rows[3], player_id="bad-evaluable-games", qualifying_games=0),
        dict(rows[4], player_id="bad-attrition-metric", ppg=0.0),
    ):
        with pytest.raises(Exception):
            module.validate_attrition_classes(rows + [mutation], counts)
    with pytest.raises(Exception, match="attrition_count_mismatch"):
        module.validate_attrition_classes(rows, {**counts, "stale": 0})
    wrong_key = dict(rows[0])
    wrong_key["target_season"] = wrong_key.pop("season")
    with pytest.raises(Exception):
        module.validate_attrition_classes([wrong_key], counts)

    # S21-S22: every new pin is mandatory and the context registry is untouched.
    from src.dynasty_genius.adapters import nflreadpy_qb_adapter as adapter
    from src.dynasty_genius.sources.source_registry import SOURCE_REGISTRY

    assert tuple(module.VALIDATION_DATASETS) == (
        "weekly",
        "season_summary",
        "players",
        "rosters",
        "ff_playerids",
        "draft_picks",
        "pbp",
    )
    assert set(WEEKLY_NEW_COLUMNS) <= set(adapter.VALIDATION_DATASET_COLUMNS["weekly"])
    assert set(SEASON_SUMMARY_COLUMNS) == set(
        adapter.VALIDATION_DATASET_COLUMNS["season_summary"]
    )
    assert "position" in adapter.VALIDATION_DATASET_COLUMNS["rosters"]
    assert set(SOURCE_REGISTRY["nflreadpy_qb_context"].allowed_fields) == {
        "cpoe",
        "dakota",
        "dropback_count",
        "epa_per_dropback",
        "pass_attempts",
    }
    for dataset, column in (
        *(("weekly", column) for column in WEEKLY_NEW_COLUMNS),
        ("rosters", "position"),
        *(("season_summary", column) for column in SEASON_SUMMARY_COLUMNS),
        # round-1 B3 regression (implementer-added per Codex's 21:30 request):
        # the pbp pin is checked under its post-parse rename via the REAL F15.
        ("pbp", "offense_team"),
    ):
        bad = _sources(tmp_path / f"missing-{dataset}-{column}")
        bad[dataset]["frame"] = bad[dataset]["frame"].drop(columns=[column])
        with pytest.raises(Exception, match="manifest_column_missing"):
            _build(module, bad)

    # S25-S26: manifest ownership/composition and market-alias exclusion.
    manifests = artifact["manifests"]
    names = {
        key: {entry["name"] for entry in value["features"]}
        for key, value in manifests.items()
    }
    assert names["h1"].isdisjoint(names["h2"])
    assert names["h1"].isdisjoint(names["h3"])
    assert names["h2"].isdisjoint(names["h3"])
    assert names["h4"] == names["h1"] | names["h2"] | names["h3"] | {
        "age_at_season_start",
        "draft_round",
        "draft_overall",
        "is_udfa",
    }
    aliases = ("ktc", "fc", "dp", "adp")
    assert not any(alias in name.lower() for name in names["h4"] for alias in aliases)
    assert not any(
        alias in key.lower()
        for row in artifact["matrix"]
        for key in row
        for alias in aliases
    )

    # S28, S30, S33: roster semantics, draft triage/UDFA, duplicate 1b refusal.
    assert by_player["prior-zero-target"]["eligibility"] == "cohort_ineligible_prior"
    post_only = _sources(tmp_path / "post-only-roster")
    post_mask = post_only["rosters"]["frame"]["player_id"] == "prior-zero-target"
    post_only["rosters"]["frame"].loc[post_mask, "game_type"] = "POST"
    post_audit = [
        row
        for season in _build(module, post_only)["attrition"].values()
        for row in season["audit"]
    ]
    assert (
        next(
            row
            for row in post_audit
            if row["player_id"] == "prior-zero-target" and row["target_season"] == 2025
        )["eligibility"]
        == "rookie_no_priors"
    )
    assert _find(artifact["matrix"], "veteran", 2025)["is_udfa"] == 1
    assert _find(artifact["matrix"], "veteran", 2025)["draft_round"] == 8
    assert _find(artifact["matrix"], "veteran", 2025)["draft_overall"] == 263
    triage = module.resolve_draft_join(
        {"gsis_id": None, "display_name": "Ambiguous", "birth_date": "2000-01-01"},
        [
            {
                "gsis_id": None,
                "pfr_player_name": "Ambiguous",
                "season": 2021,
                "round": 1,
                "pick": 1,
                "age": 21,
                "college": "A",
            },
            {
                "gsis_id": None,
                "pfr_player_name": "Ambiguous",
                "season": 2021,
                "round": 2,
                "pick": 40,
                "age": 21,
                "college": "B",
            },
        ],
    )
    assert triage["resolution"] == "TRIAGE"
    assert not {"is_udfa", "draft_round", "draft_overall"} & set(triage)
    duplicate = _sources(tmp_path / "duplicate-summary")
    duplicate["season_summary"]["frame"] = pd.concat(
        [
            duplicate["season_summary"]["frame"],
            duplicate["season_summary"]["frame"].iloc[[0]],
        ],
        ignore_index=True,
    )
    with pytest.raises(Exception, match="duplicate_player_season"):
        _build(module, duplicate)

    # S31: exact-plain normalization and system-exception preservation.
    class IntSubclass(int):
        pass

    scalar = _sources(tmp_path / "scalar-subclass")
    scalar["weekly"]["frame"].loc[0, "attempts"] = IntSubclass(20)
    normalized = _build(module, scalar)
    assert type(_find(normalized["matrix"], "veteran", 2016)["completion_pct"]) is float
    # round-1 B4 regression (implementer-added per Codex's 21:30 request):
    # EVERY manifest feature on every matrix row is exact plain float|None.
    feature_names = {entry["name"] for entry in artifact["manifests"]["h4"]["features"]}
    assert all(
        row[name] is None or type(row[name]) is float
        for row in artifact["matrix"]
        for name in feature_names
    )
    # round-1 H1 regression (implementer-added per Codex's 21:30 request):
    # null rushing_yards is corruption, never an observed zero.
    null_rush = _sources(tmp_path / "null-rushing-yards")
    null_rush["weekly"]["frame"].loc[0, "rushing_yards"] = None
    with pytest.raises(Exception) as exc:
        _build(module, null_rush)
    assert "stat_value_invalid" in _reason(exc)
    # round-2 H1 regressions (implementer-added per Codex's 21:47 request).
    # (a) The adapter's own coverage law refuses a requested season with zero
    # fetched rows — loader-level, not only the D2a re-check.
    from src.dynasty_genius.adapters import nflreadpy_qb_adapter as adapter_mod

    with pytest.raises(Exception, match="source_season_missing"):
        adapter_mod.load_validation_weekly_stats(
            [2015, 2016],
            loader=lambda: pd.DataFrame([_weekly_row("veteran", 2015)]),
            snapshot_dir=tmp_path / "adapter-missing-season",
        )
    # (b) Spy proof: the REAL F14 then F15 run once per dataset, in order, on
    # frames that are NOT the caller's objects (true defensive copies).
    from src.dynasty_genius.eval.qb_validation import guards as guards_module

    spy_sources = _sources(tmp_path / "guard-spy")
    caller_frame_ids = {id(state["frame"]) for state in spy_sources.values()}
    spy_calls: list[tuple[str, str]] = []
    real_shape = guards_module.validate_dataset_shape
    real_columns = guards_module.validate_manifest_columns

    def _spy_shape(frame: Any, *args: Any, **kwargs: Any) -> None:
        assert id(frame) not in caller_frame_ids
        spy_calls.append(("shape", kwargs.get("dataset", "?")))
        return real_shape(frame, *args, **kwargs)

    def _spy_columns(frame: Any, *args: Any, **kwargs: Any) -> None:
        assert id(frame) not in caller_frame_ids
        spy_calls.append(("columns", kwargs.get("dataset", "?")))
        return real_columns(frame, *args, **kwargs)

    guards_module.validate_dataset_shape = _spy_shape
    guards_module.validate_manifest_columns = _spy_columns
    try:
        _build(module, spy_sources)
    finally:
        guards_module.validate_dataset_shape = real_shape
        guards_module.validate_manifest_columns = real_columns
    assert [kind for kind, _ in spy_calls] == ["shape", "columns"] * 7
    assert [name for kind, name in spy_calls if kind == "shape"] == list(
        module.VALIDATION_DATASETS
    )

    class ExplodingSources(dict):
        def get(self, key: object, default: object = None) -> object:
            raise MemoryError("preserve me")

    with pytest.raises(MemoryError, match="preserve me"):
        module.build_study_matrix(
            ExplodingSources(_sources(tmp_path / "system-error")),
            registration=registration,
            expected_registration_hash=digest,
        )
