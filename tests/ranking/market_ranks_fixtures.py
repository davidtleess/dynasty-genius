"""Synthetic source fixture; no paid records or local run dependencies."""

import hashlib
import json


def content_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def synthetic_sources():
    scoring = {"rec": 1, "pass_td": 4}
    positions = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "FLEX", "SUPER_FLEX", "BN"]
    captured = "2026-09-06T13:00:00Z"
    models = []
    for sid, value in [("1", 20), ("2", 0), ("3", 0)]:
        models.append(
            dict(
                sleeper_id=sid,
                name=f"Synthetic {sid}",
                position="QB",
                fantasy_positions=["QB"],
                value=value,
                readiness="comparable",
                evidence_verified=True,
                on_davids_roster=sid == "1",
                rostered_by=1 if sid == "1" else None,
                reference_player="Synthetic reference",
                seasons=[
                    dict(season=year, expected_margin=value / 5, advantage=value / 5)
                    for year in range(2026, 2031)
                ],
            )
        )
    report = dict(
        run="synthetic",
        forecast_date="2026-09-06",
        inputs={"snapshot": {"sha256": "filled-at-write"}},
        league={
            "teams": 12,
            "te_premium": 0,
            "scoring": scoring.copy(),
            "captured_at": captured,
            "slots": {p: positions.count(p) for p in positions},
        },
        board_target=dict(
            window="championship_week17",
            scoring="PPR_nflverse_default",
            quantity="season_points",
            scope="REG",
            event="appearance",
            clock="per_season",
            labels_through=2025,
        ),
        comparable_views={"h5": "horizon_board"},
        horizon_board={
            "horizons_summed": 5,
            "readiness": {"comparable": 3},
            "all_inspectable": models,
        },
        davids_best_lineup_served_h0={"excluded_taxi_or_reserve": []},
    )
    snapshot = dict(
        captured_at=captured,
        david_roster_id=1,
        league={
            "season": "2026",
            "settings": {"num_teams": 12, "type": 2},
            "roster_positions": positions,
            "scoring_settings": scoring.copy(),
        },
        rosters=[{"roster_id": 1, "players": ["1"], "taxi": [], "reserve": []}],
        players=[
            {
                "sleeper_player_id": s,
                "player": {"position": "QB", "team": "MIN"},
                "league_context": {"rostered": s == "1"},
            }
            for s in ("1", "2", "3", "4")
        ],
    )
    entries = []
    for sid, value, pos, published in [
        ("1", 10, "QB", 3),
        ("2", 50, "QB", 1),
        ("4", 20, "QB", 2),
        ("pick", 30, "PICK", 2),
    ]:
        fields = dict(
            sleeper_id=sid,
            player_name=f"Synthetic {sid}",
            position=pos,
            value=value,
            overall_rank=published,
            position_rank=published,
            trend_30day=None,
            market_volatility=None,
            market_volatility_status="unknown",
        )
        entries.append(
            dict(
                **fields,
                player_key=sid,
                payload_hash=content_hash(fields),
                source="fc_native",
                snapshot_date="2026-09-06",
                settings_hash="e27351d720e9fcf0",
                retrieved_at=captured,
            )
        )
    market = dict(
        schema_version=1,
        source="fc_native",
        snapshot_date="2026-09-06",
        retrieved_at=captured,
        settings_hash="e27351d720e9fcf0",
        settings=dict(isDynasty=True, numQbs=2, numTeams=12, ppr=1),
        entries=entries,
    )
    market["capture_report"] = {
        key: market[key]
        for key in ("source", "snapshot_date", "retrieved_at", "settings_hash")
    }
    market["capture_report"].update(
        status="ok",
        joinable_rows_written=4,
        raw_entries_written=4,
        store_hash=content_hash(
            {"sigs": sorted(e["player_key"] + ":" + e["payload_hash"] for e in entries)}
        ),
    )
    return [report, market, snapshot]
