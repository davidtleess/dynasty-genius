from __future__ import annotations

from src.dynasty_genius.team_value_matrix import (
    build_team_value_matrix,
    optimize_best_legal_lineup,
)

ROSTER_POSITIONS = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "SUPER_FLEX"]


def _pvo(
    sleeper_id: str,
    position: str,
    xvar: float | None,
    roster_id: int,
    *,
    age: float | None = 25.0,
    on_taxi: bool = False,
    on_ir: bool = False,
) -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "player": {"full_name": f"Player {sleeper_id}", "position": position, "age": age},
        "league_context": {
            "rostered": True,
            "roster_id": roster_id,
            "owner_user_id": f"user-{roster_id}",
            "owner_display_name": f"Team {roster_id}",
            "on_taxi": on_taxi,
            "on_ir": on_ir,
            "in_starters": False,
        },
        "valuation": {
            "engine_path": "ENGINE_B" if xvar is not None else "PRE_MODEL",
            "xvar": xvar,
            "dynasty_value_score": None if xvar is None else 60 + xvar,
            "decision_supported": False,
        },
    }


def test_best_legal_lineup_optimizes_slots_not_actual_sleeper_starters():
    players = [
        _pvo("qb1", "QB", 10, 1),
        _pvo("qb2", "QB", 7, 1),
        _pvo("rb1", "RB", 8, 1),
        _pvo("rb2", "RB", 6, 1),
        _pvo("wr1", "WR", 9, 1),
        _pvo("wr2", "WR", 5, 1),
        _pvo("wr3", "WR", 4, 1),
        _pvo("te1", "TE", 3, 1),
        _pvo("rb3", "RB", 2, 1),
    ]

    lineup = optimize_best_legal_lineup(players, ROSTER_POSITIONS)

    assert len(lineup["starters"]) == 9
    assert lineup["starter_xvar"] == 54
    slots = {starter["slot"] for starter in lineup["starters"]}
    assert "SUPER_FLEX" in slots
    assert any(starter["sleeper_player_id"] == "qb2" and starter["slot"] == "SUPER_FLEX" for starter in lineup["starters"])


def test_team_value_matrix_applies_depth_credit_only_after_starters_and_preserves_player_xvar():
    players = [
        _pvo("qb1", "QB", 10, 1),
        _pvo("qb2", "QB", 7, 1),
        _pvo("rb1", "RB", 8, 1),
        _pvo("rb2", "RB", 6, 1),
        _pvo("wr1", "WR", 9, 1),
        _pvo("wr2", "WR", 5, 1),
        _pvo("wr3", "WR", 4, 1),
        _pvo("te1", "TE", 3, 1),
        _pvo("rb3", "RB", 2, 1),
        _pvo("wr_bench", "WR", 6, 1),
    ]
    matrix = build_team_value_matrix(
        universe_pvo={"league_id": "L1", "players": players},
        league_snapshot={
            "league_id": "L1",
            "league": {"roster_positions": ROSTER_POSITIONS},
            "rosters": [{"roster_id": 1, "owner_id": "user-1", "players": [p["sleeper_player_id"] for p in players]}],
            "users": [{"user_id": "user-1", "display_name": "Team 1"}],
            "future_picks": [],
        },
    )

    team = matrix["teams"][0]
    bench = next(player for player in team["players"] if player["sleeper_player_id"] == "rb3")
    assert bench["raw_xvar"] == 2
    assert bench["lineup_role"] == "bench"
    assert bench["depth_credit_xvar"] < bench["raw_xvar"]
    assert team["team_value_views"]["starter_weighted_xvar"] > team["lineup"]["starter_xvar"]


def test_bench_stuffing_cannot_outrank_elite_starter_concentration():
    elite = [
        _pvo("e_qb1", "QB", 20, 1),
        _pvo("e_qb2", "QB", 18, 1),
        _pvo("e_rb1", "RB", 18, 1),
        _pvo("e_rb2", "RB", 16, 1),
        _pvo("e_wr1", "WR", 19, 1),
        _pvo("e_wr2", "WR", 17, 1),
        _pvo("e_wr3", "WR", 16, 1),
        _pvo("e_te1", "TE", 12, 1),
        _pvo("e_rb3", "RB", 15, 1),
    ]
    bench_stuffed = [
        _pvo(f"b_qb{i}", "QB", 3, 2) for i in range(2)
    ] + [
        _pvo(f"b_rb{i}", "RB", 3, 2) for i in range(8)
    ] + [
        _pvo(f"b_wr{i}", "WR", 3, 2) for i in range(10)
    ] + [
        _pvo(f"b_te{i}", "TE", 3, 2) for i in range(3)
    ]

    matrix = build_team_value_matrix(
        universe_pvo={"league_id": "L1", "players": elite + bench_stuffed},
        league_snapshot={
            "league_id": "L1",
            "league": {"roster_positions": ROSTER_POSITIONS},
            "rosters": [
                {"roster_id": 1, "owner_id": "user-1", "players": [p["sleeper_player_id"] for p in elite]},
                {"roster_id": 2, "owner_id": "user-2", "players": [p["sleeper_player_id"] for p in bench_stuffed]},
            ],
            "users": [
                {"user_id": "user-1", "display_name": "Elite"},
                {"user_id": "user-2", "display_name": "Depth"},
            ],
            "future_picks": [],
        },
    )

    by_roster = {team["roster_id"]: team for team in matrix["teams"]}
    assert by_roster[1]["team_value_views"]["starter_weighted_xvar"] > by_roster[2]["team_value_views"]["starter_weighted_xvar"]
    assert by_roster[2]["team_value_views"]["depth_credit_xvar"] < by_roster[2]["team_value_views"]["lineup_xvar"]


def test_taxi_and_future_picks_are_represented_without_numeric_pick_value():
    players = [
        _pvo("taxi_wr", "WR", 20, 1, on_taxi=True),
        _pvo("qb1", "QB", 10, 1),
        _pvo("qb2", "QB", 9, 1),
        _pvo("rb1", "RB", 8, 1),
        _pvo("rb2", "RB", 7, 1),
        _pvo("wr1", "WR", 6, 1),
        _pvo("wr2", "WR", 5, 1),
        _pvo("te1", "TE", 4, 1),
        _pvo("rb3", "RB", 3, 1),
        _pvo("wr3", "WR", 2, 1),
    ]
    matrix = build_team_value_matrix(
        universe_pvo={"league_id": "L1", "players": players},
        league_snapshot={
            "league_id": "L1",
            "league": {"roster_positions": ROSTER_POSITIONS},
            "rosters": [{"roster_id": 1, "owner_id": "user-1", "players": [p["sleeper_player_id"] for p in players], "taxi": ["taxi_wr"]}],
            "users": [{"user_id": "user-1", "display_name": "Team 1"}],
            "future_picks": [
                {"season": 2027, "round": 1, "original_roster_id": 1, "current_roster_id": 1, "pick_value_status": "deferred"},
                {"season": 2027, "round": 2, "original_roster_id": 1, "current_roster_id": 2, "pick_value_status": "deferred"},
            ],
        },
    )

    team = matrix["teams"][0]
    taxi = next(player for player in team["players"] if player["sleeper_player_id"] == "taxi_wr")
    assert taxi["lineup_role"] == "taxi"
    assert taxi["starter_weight_multiplier_current_year"] == 0.0
    assert taxi["long_term_value_multiplier"] == 1.0
    assert taxi["taxi_activation_cost"] == "requires_active_roster_spot_and_irreversible_taxi_loss"
    assert not any(starter["sleeper_player_id"] == "taxi_wr" for starter in team["lineup"]["starters"])
    owned_pick = team["future_picks"]["owned"][0]
    assert owned_pick["pick_value_status"] == "deferred"
    assert "xvar" not in owned_pick
    assert "dynasty_value_score" not in owned_pick
