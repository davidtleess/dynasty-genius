from __future__ import annotations

import copy


def _team(
    roster_id: int,
    *,
    qb_z: float = 0.0,
    rb_z: float = 0.0,
    wr_z: float = 0.0,
    te_z: float = 0.0,
    players: list[dict] | None = None,
) -> dict:
    labels = {
        "QB": "surplus" if qb_z >= 0.75 else "deficit" if qb_z <= -0.75 else "neutral",
        "RB": "surplus" if rb_z >= 0.75 else "deficit" if rb_z <= -0.75 else "neutral",
        "WR": "surplus" if wr_z >= 0.75 else "deficit" if wr_z <= -0.75 else "neutral",
        "TE": "surplus" if te_z >= 0.75 else "deficit" if te_z <= -0.75 else "neutral",
    }
    z_values = {"QB": qb_z, "RB": rb_z, "WR": wr_z, "TE": te_z}
    return {
        "schema_version": "team_value_matrix.v1",
        "roster_id": roster_id,
        "owner": {
            "display_name": f"owner{roster_id}",
            "team_name": f"Team {roster_id}",
            "user_id": f"user{roster_id}",
        },
        "positional_summary": {
            position: {
                "z_score": z_values[position],
                "surplus_label": labels[position],
                "starter_xvar": 10.0 * z_values[position],
                "depth_xvar_adj": 0.0,
                "n_rostered": 3,
            }
            for position in ("QB", "RB", "WR", "TE")
        },
        "team_value_views": {
            "starter_weighted_xvar": 100.0 + roster_id,
            "lineup_xvar": 100.0 + roster_id,
        },
        "posture": {"label": "UNCLASSIFIED", "score": None},
        "future_picks": {"owned": [], "outgoing": []},
        "players": players or [],
        "decision_supported": False,
    }


def _player(
    sleeper_id: str,
    *,
    name: str,
    position: str,
    roster_id: int | None,
    signal: str = "MODEL_HIGH_MARKET_LOW",
    status: str = "gates_passed",
    delta: float = 0.25,
    xvar: float = 12.0,
    on_taxi: bool = False,
) -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "dg_player_id": f"dg_{sleeper_id}",
        "player": {"full_name": name, "position": position, "dg_status": "ENGINE_B"},
        "league_context": {
            "rostered": roster_id is not None,
            "roster_id": roster_id,
            "on_taxi": on_taxi,
            "on_ir": False,
        },
        "valuation": {
            "engine_path": "ENGINE_B",
            "valuation_status": "MODEL_SUPPORTED",
            "xvar": xvar,
            "decision_supported": False,
        },
        "market_overlay": {"market_value": 1000.0, "source": "fantasycalc"},
        "divergence": {
            "signal": signal,
            "signal_status": status,
            "model_minus_market_delta": delta,
            "model_percentile": 0.75,
            "market_percentile": 0.50,
            "failed_gates": [],
            "notes": [],
            "decision_supported": False,
        },
    }


def _fixtures() -> tuple[dict, dict]:
    team_matrix = {
        "schema_version": "team_value_matrix.v1",
        "league_id": "league",
        "captured_at": "2026-05-22T12:00:00+00:00",
        "teams": [
            _team(
                1,
                rb_z=-1.2,
                wr_z=-1.0,
                te_z=-1.4,
                players=[
                    {
                        "sleeper_player_id": "taxi1",
                        "full_name": "Taxi Back",
                        "position": "RB",
                        "raw_xvar": 9.5,
                        "lineup_role": "taxi",
                    }
                ],
            ),
            _team(
                2,
                rb_z=1.3,
                wr_z=0.1,
                players=[
                    {
                        "sleeper_player_id": "r2rb",
                        "full_name": "Roster Two Back",
                        "position": "RB",
                        "raw_xvar": 21.0,
                        "lineup_role": "starter",
                    }
                ],
            ),
            _team(3, wr_z=1.4, rb_z=-0.3),
        ],
    }
    market_divergence = {
        "schema_version": "universe_market_divergence.v1",
        "league_id": "league",
        "captured_at": "2026-05-22T12:01:00+00:00",
        "players": [
            _player("r2rb", name="Roster Two Back", position="RB", roster_id=2, delta=0.31),
            _player(
                "r3wr",
                name="Roster Three Wide",
                position="WR",
                roster_id=3,
                signal="MODEL_LOW_MARKET_HIGH",
                delta=-0.22,
                xvar=8.0,
            ),
            _player("waiver1", name="Waiver Runner", position="RB", roster_id=None, delta=0.28, xvar=7.5),
            _player("taxi1", name="Taxi Back", position="RB", roster_id=1, delta=0.18, xvar=9.5, on_taxi=True),
        ],
    }
    return team_matrix, market_divergence


def test_opportunity_map_emits_evidence_backed_cards_without_decision_support():
    from src.dynasty_genius.league_opportunity_map import build_league_opportunity_map

    team_matrix, market_divergence = _fixtures()
    result = build_league_opportunity_map(team_matrix, market_divergence, perspective_roster_id=1)

    assert result["schema_version"] == "league_opportunity.v1"
    assert result["decision_supported"] is False
    assert result["coverage"]["decision_supported_true_count"] == 0
    assert result["coverage"]["cards_with_evidence_count"] == len(result["cards"])
    assert result["coverage"]["phase17_5_exit_criteria"]["opportunity_cards_evidence_backed"] is True
    assert result["coverage"]["phase17_5_exit_criteria"]["no_automated_trade_execution"] is True
    assert result["coverage"]["banned_language_present"] == []
    assert {card["card_type"] for card in result["cards"]} >= {
        "ROSTER_SURPLUS_DEFICIT_MATCH",
        "DIVERGENCE_MODEL_HIGH",
        "DIVERGENCE_MARKET_HIGH",
        "WAIVER_CANDIDATE",
        "TAXI_ACTIVATION_CANDIDATE",
    }
    for card in result["cards"]:
        assert card["decision_supported"] is False
        assert card["rationale"]["evidence"]
        assert "opportunity_score" in card


def test_partner_ranking_prioritizes_counterparty_surplus_matching_david_deficit():
    from src.dynasty_genius.league_opportunity_map import build_league_opportunity_map

    team_matrix, market_divergence = _fixtures()
    result = build_league_opportunity_map(team_matrix, market_divergence, perspective_roster_id=1)

    assert result["partner_rankings"][0]["counterparty_roster_id"] == 2
    assert "RB" in result["partner_rankings"][0]["matched_positions"]
    assert result["partner_rankings"][0]["partner_score"] > 0
    assert all(ranking["counterparty_roster_id"] != 1 for ranking in result["partner_rankings"])


def test_opportunity_map_does_not_mutate_inputs():
    from src.dynasty_genius.league_opportunity_map import build_league_opportunity_map

    team_matrix, market_divergence = _fixtures()
    original_team_matrix = copy.deepcopy(team_matrix)
    original_market_divergence = copy.deepcopy(market_divergence)
    build_league_opportunity_map(team_matrix, market_divergence, perspective_roster_id=1)
    assert team_matrix == original_team_matrix
    assert market_divergence == original_market_divergence


def test_opportunity_artifact_writer_outputs_json_and_markdown(tmp_path):
    from src.dynasty_genius.league_opportunity_map import (
        build_league_opportunity_map,
        write_league_opportunity_artifacts,
    )

    team_matrix, market_divergence = _fixtures()
    result = build_league_opportunity_map(team_matrix, market_divergence, perspective_roster_id=1)
    paths = write_league_opportunity_artifacts(result, output_dir=tmp_path, run_id="phase17-5-test")

    assert paths["batch"].exists()
    assert paths["batch_latest"].exists()
    assert paths["markdown"].exists()
    assert paths["markdown_latest"].exists()
    markdown = paths["markdown"].read_text()
    assert "League Opportunity Map" in markdown
    assert "decision_supported: false" in markdown
    for banned in ("buy", "sell", "target", "fade"):
        assert banned not in markdown.lower()
