from __future__ import annotations

import importlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def _feature_frames() -> dict[str, pd.DataFrame]:
    rows = []
    roster_rows = []
    snap_rows = []
    for season, points, week_count, team, birth_year in [
        (2023, 20.0, 5, "MIN", 2000),
        (2024, 22.0, 5, "MIN", 2000),
        (2025, 24.0, 5, "MIN", 2000),
    ]:
        rows.extend(
            [
                {
                    "player_id": "wr1",
                    "season": season,
                    "position": "WR",
                    "team": team,
                    "fantasy_points_ppr": points,
                    "targets": 5,
                    "receptions": 3,
                    "receiving_yards": 60,
                    "rushing_yards": 0,
                    "rushing_tds": 0,
                    "receiving_air_yards": 80,
                    "week": week,
                }
                for week in range(1, week_count + 1)
            ]
        )
        roster_rows.append(
            {
                "gsis_id": "wr1",
                "season": season,
                "birth_date": f"{birth_year}-01-01",
                "depth_chart_position": "WR1",
                "pfr_id": "pfr-wr1",
            }
        )
        snap_rows.append(
            {"pfr_player_id": "pfr-wr1", "season": season, "offense_pct": 0.80}
        )

    rows.extend(
        [
            {
                "player_id": "qb1",
                "season": 2025,
                "position": "QB",
                "team": "KC",
                "fantasy_points_ppr": 30.0,
                "targets": 0,
                "receptions": 0,
                "receiving_yards": 0,
                "rushing_yards": 450,
                "rushing_tds": 3,
                "receiving_air_yards": 0,
                "week": week,
            }
            for week in range(1, 6)
        ]
    )
    roster_rows.append(
        {
            "gsis_id": "qb1",
            "season": 2025,
            "birth_date": "1998-01-01",
            "depth_chart_position": "QB1",
            "pfr_id": "pfr-qb1",
        }
    )
    snap_rows.append(
        {"pfr_player_id": "pfr-qb1", "season": 2025, "offense_pct": 0.95}
    )

    rows.extend(
        [
            {
                "player_id": "te1",
                "season": 2025,
                "position": "TE",
                "team": "SEA",
                "fantasy_points_ppr": 12.0,
                "targets": 2,
                "receptions": 1,
                "receiving_yards": 12,
                "rushing_yards": 0,
                "rushing_tds": 0,
                "receiving_air_yards": 10,
                "week": week,
            }
            for week in range(1, 6)
        ]
    )
    roster_rows.append(
        {
            "gsis_id": "te1",
            "season": 2025,
            "birth_date": "1999-01-01",
            "depth_chart_position": "TE1",
            "pfr_id": "pfr-te1",
        }
    )
    snap_rows.append(
        {"pfr_player_id": "pfr-te1", "season": 2025, "offense_pct": 0.65}
    )

    pbp_rows = []
    participation_rows = []
    for play_id in range(1, 5):
        pbp_rows.append(
            {
                "game_id": "game-2025",
                "play_id": play_id,
                "season": 2025,
                "posteam": "MIN",
                "pass_attempt": 1,
                "qb_dropback": 1,
                "passer_player_id": "qb1",
                "epa": 0.20,
                "cpoe": 5.0,
            }
        )
        participation_rows.append(
            {
                "nflverse_game_id": "game-2025",
                "play_id": play_id,
                "offense_players": "wr1;qb1",
            }
        )
    for play_id in range(5, 7):
        pbp_rows.append(
            {
                "game_id": "game-2025",
                "play_id": play_id,
                "season": 2025,
                "posteam": "SEA",
                "pass_attempt": 1,
                "qb_dropback": 1,
                "passer_player_id": "qb1",
                "epa": 0.10,
                "cpoe": 1.0,
            }
        )
        participation_rows.append(
            {
                "nflverse_game_id": "game-2025",
                "play_id": play_id,
                "offense_players": "te1;qb1",
            }
        )

    return {
        "player_stats": pd.DataFrame(rows),
        "rosters": pd.DataFrame(roster_rows),
        "snap_counts": pd.DataFrame(snap_rows),
        "pbp": pd.DataFrame(pbp_rows),
        "participation": pd.DataFrame(participation_rows),
        "te_rubric": {
            "players": {
                "te-canon": {
                    "labeling_status": "labeled",
                    "detached_rate_from_snaps": 0.70,
                    "inline_rate_from_snaps": 0.20,
                    "yprr_computed": 1.0,
                    "tprr_computed": 0.10,
                }
            }
        },
        "te_eligible": {
            "eligible": [{"gsis_id": "te1", "player_id": "te-canon"}]
        },
    }


def test_build_engine_b_features_extracts_real_engineering_values() -> None:
    assembly = importlib.import_module("src.dynasty_genius.features.feature_assembly")
    engine_b_script = importlib.import_module("scripts.assemble_engine_b_dataset")

    candidate = assembly.build_engine_b_features(
        seasons_window=[2023, 2024, 2025],
        read_fns=_feature_frames(),
    )

    assert list(candidate.columns) == list(engine_b_script.ENGINE_B_OUTPUT_COLUMNS)
    assert set(candidate["feature_season"]) == {2023, 2025}
    assert {
        "ppg_t1",
        "ppg_t2",
        "games_t1",
        "games_t2",
        "targets_t",
        "receptions_t",
        "yards_t",
        "rushing_yards_t",
        "rushing_tds_t",
        "air_yards_t",
    }.isdisjoint(candidate.columns)

    wr_2025 = candidate[
        (candidate["player_id"] == "wr1") & (candidate["feature_season"] == 2025)
    ].iloc[0]
    assert wr_2025["training_eligible"] == False  # noqa: E712
    assert pd.isna(wr_2025["avg_ppg_t1_t2"])
    assert wr_2025["snap_share"] == 0.80
    assert wr_2025["route_participation"] == 1.0
    assert wr_2025["yprr"] == 75.0
    assert wr_2025["tprr"] == 6.25
    assert wr_2025["ppg_t_minus_1_available"] == True  # noqa: E712
    assert wr_2025["ppg_t_minus_2_available"] == True  # noqa: E712
    assert wr_2025["snap_share_t_minus_1_available"] == True  # noqa: E712
    assert wr_2025["ppg_t_minus_1"] == 22.0
    assert wr_2025["ppg_t_minus_2"] == 20.0
    assert wr_2025["snap_share_t_minus_1"] == 0.80
    assert wr_2025["aging_curve_position"] == "WR"
    assert 0.0 < wr_2025["aging_curve_value"] <= 1.0

    qb_2025 = candidate[
        (candidate["player_id"] == "qb1") & (candidate["feature_season"] == 2025)
    ].iloc[0]
    assert qb_2025["epa_per_dropback"] == 0.16666666666666666
    assert qb_2025["cpoe"] == 3.6666666666666665
    assert qb_2025["dakota"] == 0.12766666666666665
    assert qb_2025["dropback_count"] == 6
    assert qb_2025["pass_attempts"] == 6
    assert qb_2025["is_dual_threat"] == True  # noqa: E712
    assert qb_2025["aging_curve_position"] == "QB_dual_threat"

    te_2025 = candidate[
        (candidate["player_id"] == "te1") & (candidate["feature_season"] == 2025)
    ].iloc[0]
    assert te_2025["te_role_is_risk_profile"] == 1.0


def test_assemble_feature_candidate_uses_full_engineering_after_t1b() -> None:
    assembly = importlib.import_module("src.dynasty_genius.features.feature_assembly")

    candidate = assembly.assemble_feature_candidate(
        seasons_window=[2023, 2024, 2025],
        read_fns=_feature_frames(),
    )

    wr_2025 = candidate[
        (candidate["player_id"] == "wr1") & (candidate["feature_season"] == 2025)
    ].iloc[0]
    assert wr_2025["snap_share"] == 0.80
    assert wr_2025["route_participation"] == 1.0
    assert wr_2025["yprr"] == 75.0


def test_assemble_engine_b_dataset_delegates_to_shared_builder() -> None:
    engine_b_script = importlib.import_module("scripts.assemble_engine_b_dataset")
    source = Path(engine_b_script.__file__).read_text()

    assert "build_engine_b_features" in source
    assert "Calculating QB efficiency" not in source
    assert "Calculating route metrics" not in source
    assert "Applying aging curves" not in source
    for name in (
        "ENGINE_B_OUTPUT_COLUMNS",
        "OUTCOME_COLUMN",
        "add_te_role_risk_feature",
        "add_te_role_risk_feature_from_files",
        "fetch_and_agg_stats",
    ):
        assert hasattr(engine_b_script, name)


def test_feature_refresh_cli_real_run_gate_removed_for_t1b(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cli = importlib.import_module("scripts.run_feature_refresh")
    runtime_dir = tmp_path / "features_runtime"
    seed_path = tmp_path / "seed.csv"
    seed_path.write_text("player_id,feature_season,training_eligible\n")

    monkeypatch.setattr(cli, "_load_source", lambda _seasons: _feature_frames())
    monkeypatch.setattr(
        cli,
        "compute_source_hash",
        lambda **_kwargs: "t1b-source-hash",
    )

    rc = cli.main(
        [
            "--runtime-dir",
            str(runtime_dir),
            "--seed-path",
            str(seed_path),
            "--season-start",
            "2023",
            "--season-end",
            "2025",
        ]
    )

    captured = capsys.readouterr()
    # T1b's real-run gate is removed: the CLI reaches candidate generation. In T4, the
    # same CLI also attempts validated publish; this fixture intentionally lacks full
    # position coverage, so the publish gate blocks and the scheduler exit is nonzero.
    assert rc == 1
    assert "blocked" in captured.out
    assert "full feature engineering lands in T1b" not in captured.out + captured.err
    candidate = runtime_dir / "engine_b_features_candidate.csv"
    assert candidate.exists()
    frame = pd.read_csv(candidate)
    assert "snap_share" in frame.columns
    assert frame["snap_share"].notna().any()


def test_cli_source_hash_covers_te_artifacts_and_builder_constants(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Codex F1 regression: the ungated CLI must hash the non-frame inputs the builder
    actually consumes (TE rubric/eligible bytes + builder constants), so a TE-artifact
    change with identical frames changes the source hash — no false noop. Wall-clock
    (C5) stays excluded by the runner."""
    cli = importlib.import_module("scripts.run_feature_refresh")
    runner = importlib.import_module(
        "src.dynasty_genius.features.feature_refresh_runner"
    )
    assemble = importlib.import_module("scripts.assemble_engine_b_dataset")

    frames = {
        "player_stats": pd.DataFrame({"player_id": ["wr1"], "season": [2025]}),
        "rosters": pd.DataFrame({"gsis_id": ["wr1"], "season": [2025]}),
    }
    window = [2023, 2024, 2025]

    rubric = tmp_path / "rubric.json"
    eligible = tmp_path / "eligible.json"
    rubric.write_text('{"players": {}}')
    eligible.write_text('{"eligible": []}')
    monkeypatch.setattr(assemble, "TE_ARCHETYPE_RUBRIC_PATH", rubric)
    monkeypatch.setattr(assemble, "TE_ELIGIBLE_MANIFEST_PATH", eligible)

    prov = cli._source_provenance(frames, window)
    assert "MIN_GAMES_THRESHOLD" in prov["builder_config"]
    assert "DUAL_THREAT_RUSHING_THRESHOLD" in prov["builder_config"]
    assert prov["te_rubric_artifacts"]["te_archetype_rubric"] is not None
    assert prov["te_rubric_artifacts"]["te_eligible_manifest"] is not None

    hash_before = runner.compute_source_hash(**cli._source_provenance(frames, window))

    # Changing the TE rubric bytes (identical frames) MUST change the source hash.
    rubric.write_text('{"players": {"x": {"labeling_status": "labeled"}}}')
    hash_after_rubric = runner.compute_source_hash(
        **cli._source_provenance(frames, window)
    )
    assert hash_after_rubric != hash_before

    # Identical inputs are stable, and wall-clock noise (generated_at) is excluded (C5).
    prov_again = cli._source_provenance(frames, window)
    assert runner.compute_source_hash(**prov_again) == hash_after_rubric
    prov_again["builder_config"] = {**prov_again["builder_config"], "generated_at": "X"}
    assert runner.compute_source_hash(**prov_again) == hash_after_rubric


def test_feature_modules_are_in_market_leakage_scan_allowlist() -> None:
    leakage = importlib.import_module("tests.contract.test_harness_trust_w1_leakage")

    assert (
        Path("src/dynasty_genius/features/feature_assembly.py")
        in leakage.ENGINE_MODEL_PATHS
    )
    assert (
        Path("src/dynasty_genius/features/feature_refresh_runner.py")
        in leakage.ENGINE_MODEL_PATHS
    )
