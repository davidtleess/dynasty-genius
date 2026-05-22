from __future__ import annotations

from src.dynasty_genius.sleeper_universe import (
    PHASE17_DEFAULTS,
    build_coverage_report,
    build_universe_snapshot,
    reconstruct_future_picks,
)


def test_build_universe_snapshot_classifies_players_and_preserves_rostered_context():
    players = {
        "101": {
            "player_id": "101",
            "full_name": "Starter Quarterback",
            "position": "QB",
            "team": "BUF",
            "status": "Active",
        },
        "202": {
            "player_id": "202",
            "full_name": "Rostered Kicker",
            "position": "K",
            "status": "Active",
        },
        "303": {
            "player_id": "303",
            "full_name": "Retired Tight End",
            "position": "TE",
            "status": "Retired",
        },
    }
    rosters = [
        {
            "roster_id": 1,
            "owner_id": "user-1",
            "players": ["101", "202", "404"],
            "starters": ["101"],
            "taxi": [],
            "reserve": [],
        }
    ]
    users = [{"user_id": "user-1", "display_name": "David"}]

    snapshot = build_universe_snapshot(
        league_id="league-1",
        league={"name": "Example", "season": "2026", "settings": {"draft_rounds": 3}},
        players=players,
        rosters=rosters,
        users=users,
        traded_picks=[],
        draft_state={"status": "complete"},
        draft_picks=[{"player_id": "303"}],
        captured_at="2026-05-21T00:00:00+00:00",
        david_roster_id=1,
    )

    by_id = {row["sleeper_player_id"]: row for row in snapshot["players"]}
    assert by_id["101"]["cohort"] == "FANTASY_RELEVANT"
    assert by_id["101"]["league_context"]["rostered"] is True
    assert by_id["101"]["league_context"]["in_starters"] is True
    assert by_id["202"]["cohort"] == "CONTEXT_ONLY"
    assert by_id["202"]["league_context"]["rostered"] is True
    assert by_id["303"]["cohort"] == "FANTASY_RELEVANT"
    assert by_id["303"]["league_context"]["in_current_draft"] is True
    assert by_id["404"]["cohort"] == "UNRESOLVED_IDENTITY"
    assert snapshot["coverage"]["rostered_players_missing_from_snapshot"] == []
    assert snapshot["coverage"]["david_roster_player_count"] == 3
    assert snapshot["coverage"]["david_roster_players_missing_from_snapshot"] == []


def test_reconstruct_future_picks_uses_automated_baseline_and_defers_values():
    picks = reconstruct_future_picks(
        season=2026,
        roster_ids=[1, 2],
        rounds=2,
        traded_picks=[
            {
                "season": "2027",
                "round": 1,
                "roster_id": 1,
                "owner_id": 2,
                "previous_owner_id": 1,
            }
        ],
        seasons_ahead=2,
    )

    moved = next(
        pick
        for pick in picks
        if pick["season"] == 2027 and pick["round"] == 1 and pick["original_roster_id"] == 1
    )
    assert moved["current_roster_id"] == 2
    assert moved["reconstruction_method"] == "automated_sleeper_traded_picks"
    assert moved["pick_value_status"] == "deferred"
    assert "xvar" not in moved
    assert "dynasty_value_score" not in moved


def test_phase17_defaults_lock_section19_and_bench_guardrail():
    assert PHASE17_DEFAULTS["pick_reconstruction_mode"] == "automated_only"
    assert PHASE17_DEFAULTS["divergence_noise_band"] == 0.10
    assert PHASE17_DEFAULTS["fantasycalc_params"] == {
        "isDynasty": "true",
        "numQbs": "2",
        "numTeams": "12",
        "ppr": "1",
    }
    assert PHASE17_DEFAULTS["bench_depth_decay"] == 0.5
    assert PHASE17_DEFAULTS["player_level_value_decay_allowed"] is False
    assert (
        PHASE17_DEFAULTS["bench_weighting_scope"]
        == "team_strength_after_best_legal_lineup"
    )


def test_coverage_report_publishes_unresolved_and_section19_defaults():
    snapshot = {
        "players": [
            {"cohort": "FANTASY_RELEVANT", "identity_status": "resolved"},
            {"cohort": "UNRESOLVED_IDENTITY", "identity_status": "unresolved"},
        ],
        "coverage": {"rostered_players_missing_from_snapshot": []},
        "defaults": PHASE17_DEFAULTS,
    }

    report = build_coverage_report(snapshot)

    assert report["counts_by_cohort"]["FANTASY_RELEVANT"] == 1
    assert report["counts_by_cohort"]["UNRESOLVED_IDENTITY"] == 1
    assert report["unresolved_identity_count"] == 1
    assert report["section19_defaults"]["pick_reconstruction_mode"] == "automated_only"
    assert report["section19_defaults"]["player_level_value_decay_allowed"] is False
