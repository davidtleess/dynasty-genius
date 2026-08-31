"""Phase 8.1 contract tests: GET /roster/audit returns PVO-shaped objects.

Verifies:
1. run_audit_pvo() returns a dict with "players" containing PVO-shaped objects.
2. No banned field appears on any player object.
3. TE players carry engine_b_experimental_v1_fallback caveat and EXPERIMENTAL grade.
4. market_overlay is None on every player object.
5. decision_supported is False on every player object.
6. counter_argument is present on players with a non-null dynasty_value_score.
7. Response envelope carries "status" = "active" and "engine" = "pvo_assembler_v1".
8. Non-skill positions are excluded from the players array.
9. Players are sorted by years_to_cliff ascending.
10. Empty roster returns an empty players array.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from unittest.mock import AsyncMock, patch

from app.services.roster_auditor import run_audit_pvo

# ── Constants ─────────────────────────────────────────────────────────────────

BANNED_FIELDS = {"action", "verdict", "dynasty_tier", "confidence", "my_total", "their_total"}

# ── Fixtures ──────────────────────────────────────────────────────────────────

_RB_PLAYER = {
    "player_id": "sleeper_rb_001",
    "full_name": "Test RB",
    "position": "RB",
    "team": "KC",
    "age": 25,
    "gsis_id": "gsis_rb_001",
}

_WR_PLAYER = {
    "player_id": "sleeper_wr_001",
    "full_name": "Test WR",
    "position": "WR",
    "team": "DET",
    "age": 24,
    "gsis_id": "gsis_wr_001",
}

_TE_PLAYER = {
    "player_id": "sleeper_te_001",
    "full_name": "Test TE",
    "position": "TE",
    "team": "KC",
    "age": 27,
    "gsis_id": "gsis_te_001",
}

_QB_PLAYER = {
    "player_id": "sleeper_qb_001",
    "full_name": "Test QB",
    "position": "QB",
    "team": "BUF",
    "age": 28,
    "gsis_id": "gsis_qb_001",
}

_NON_SKILL_PLAYER = {
    "player_id": "sleeper_k_001",
    "full_name": "Test Kicker",
    "position": "K",
    "team": "NE",
    "age": 30,
    "gsis_id": "gsis_k_001",
}

_ROOKIE_PLAYER = {
    "player_id": "13414",
    "full_name": "Kaelon Black",
    "position": "RB",
    "team": "SF",
    "age": 24,
    "gsis_id": None,
}

_RB_ENGINE_B_SCORE = {
    "player_id": "gsis_rb_001",
    "predicted_avg_ppg_t1_t2": 15.5,
    "engine": "engine_b_v2_rb",
    "feature_season": 2024,
    "position": "RB",
    "decision_supported": False,
    "experimental": False,
    "caveats": ["engine_b_not_decision_grade"],
}

_TE_ENGINE_B_SCORE = {
    "player_id": "gsis_te_001",
    "predicted_avg_ppg_t1_t2": 9.0,
    "engine": "engine_b_v1",
    "feature_season": 2024,
    "position": "TE",
    "decision_supported": False,
    "experimental": True,
    "caveats": [
        "engine_b_not_decision_grade",
        "engine_b_does_not_beat_baseline_for_this_position",
    ],
}


def _default_roster():
    return [_RB_PLAYER, _WR_PLAYER, _TE_PLAYER, _QB_PLAYER, _NON_SKILL_PLAYER]


def _default_scores():
    return [_RB_ENGINE_B_SCORE, _TE_ENGINE_B_SCORE]


def _run(roster=None, scores=None):
    roster = roster if roster is not None else _default_roster()
    scores = scores if scores is not None else _default_scores()
    with (
        patch(
            "app.services.roster_auditor.get_my_roster",
            new_callable=AsyncMock,
            return_value=roster,
        ),
        patch(
            "app.services.roster_auditor.score_inference_partition",
            return_value=scores,
        ),
        patch(
            "app.services.roster_auditor.load_qb_identity_bridge",
            return_value={"players": {}},
        ),
    ):
        return asyncio.run(run_audit_pvo())


def _universe_row_for_rookie() -> dict:
    return {
        "sleeper_player_id": "13414",
        "dg_player_id": "kaelon_black_rb",
        "identity_status": "resolved",
        "identity_ids": {"sleeper_id": "13414"},
        "player": {
            "full_name": "Kaelon Black",
            "position": "RB",
            "team": "SFO",
            "age": 24.0,
            "dg_status": "ENGINE_A",
        },
        "league_context": {
            "rostered": True,
            "roster_id": 1,
            "in_current_draft": True,
            "on_taxi": False,
        },
        "valuation": {
            "engine_path": "ENGINE_A",
            "valuation_status": "MODEL_SUPPORTED",
            "dynasty_value_score": 61.55,
            "xvar": 13.4,
            "model_grade": "PROSPECT_C",
            "feature_completeness": 0.2857,
            "decision_supported": False,
        },
    }


def _run_with_universe(tmp_path, universe_rows, roster=None, scores=None):
    path = tmp_path / "universe_pvo_latest.json"
    path.write_text(json.dumps({"players": universe_rows}))
    roster = roster if roster is not None else [_ROOKIE_PLAYER, _RB_PLAYER]
    scores = scores if scores is not None else [_RB_ENGINE_B_SCORE]
    with (
        patch(
            "app.services.roster_auditor.get_my_roster",
            new_callable=AsyncMock,
            return_value=roster,
        ),
        patch(
            "app.services.roster_auditor.score_inference_partition",
            return_value=scores,
        ),
        patch(
            "app.services.roster_auditor.load_qb_identity_bridge",
            return_value={"players": {}},
        ),
        # F-seed-split T4: roster_auditor reads the PVO pair via resolve_pvo_source.
        # Point the seed at the fixture and the runtime dir at a nonexistent path so
        # the resolver serves the committed-seed fixture (runtime absent → seed).
        patch("app.services.roster_auditor.PVO_SEED_PATH", path),
        patch(
            "app.services.roster_auditor.PVO_RUNTIME_DIR",
            tmp_path / "no_runtime",
        ),
        patch(
            "src.dynasty_genius.services.market_overlay_service.enrich_pvo_list_with_market_overlay",
            return_value=None,
        ),
    ):
        return asyncio.run(run_audit_pvo())


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_with_runtime_universe(tmp_path, universe_rows, roster=None, scores=None):
    runtime_dir = tmp_path / "valuation_runtime"
    runtime_dir.mkdir(parents=True)
    pvo_path = runtime_dir / "universe_pvo_runtime.json"
    coverage_path = runtime_dir / "universe_pvo_coverage_runtime.json"
    pvo_path.write_text(json.dumps({"players": universe_rows}))
    coverage_path.write_text(
        json.dumps(
            {
                "captured_at": "2026-06-27T13:30:00+00:00",
                "decision_supported": False,
                "counts_by_engine_path": {"ENGINE_A": len(universe_rows)},
            },
            sort_keys=True,
        )
    )
    (runtime_dir / "universe_pvo_runtime.ready.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "pvo_sha256": _sha256(pvo_path),
                "coverage_sha256": _sha256(coverage_path),
                "source_as_of": "2026-06-27T13:30:00+00:00",
                "decision_supported": False,
            },
            sort_keys=True,
        )
    )
    roster = roster if roster is not None else [_ROOKIE_PLAYER, _RB_PLAYER]
    scores = scores if scores is not None else [_RB_ENGINE_B_SCORE]
    with (
        patch(
            "app.services.roster_auditor.get_my_roster",
            new_callable=AsyncMock,
            return_value=roster,
        ),
        patch(
            "app.services.roster_auditor.score_inference_partition",
            return_value=scores,
        ),
        patch(
            "app.services.roster_auditor.load_qb_identity_bridge",
            return_value={"players": {}},
        ),
        patch(
            "app.services.roster_auditor.PVO_RUNTIME_DIR",
            runtime_dir,
        ),
        patch(
            "src.dynasty_genius.services.market_overlay_service.enrich_pvo_list_with_market_overlay",
            return_value=None,
        ),
    ):
        return asyncio.run(run_audit_pvo()), pvo_path


# ── Test 1: PVO-shaped players array ─────────────────────────────────────────

def test_response_has_pvo_shaped_players():
    result = _run()
    assert "players" in result
    assert isinstance(result["players"], list)
    assert len(result["players"]) > 0
    required = {"player_id", "position", "model_grade", "caveats", "decision_supported", "signal_completeness"}
    for player in result["players"]:
        for field in required:
            assert field in player, f"PVO field {field!r} missing from {player.get('player_id')}"


# ── Test 2: Envelope shape ────────────────────────────────────────────────────

def test_response_envelope():
    result = _run()
    assert result["status"] == "active"
    assert result["engine"] == "pvo_assembler_v1"
    assert result["decision_supported"] is False
    assert "reason" in result
    assert "caveats" in result


# ── Test 3: No banned fields on any player ───────────────────────────────────

def test_no_banned_fields_on_players():
    result = _run()
    for player in result["players"]:
        found = BANNED_FIELDS & set(player.keys())
        assert not found, f"Banned fields on {player.get('player_id')}: {found}"


# ── Test 4: TE carries experimental caveat and grade ─────────────────────────

def test_te_carries_experimental_caveat_and_grade():
    result = _run()
    te_players = [p for p in result["players"] if p.get("position") == "TE"]
    assert te_players, "No TE players in result"
    for te in te_players:
        assert "engine_b_experimental_v1_fallback" in te["caveats"], (
            f"TE {te.get('player_id')} missing engine_b_experimental_v1_fallback"
        )
        assert te["model_grade"] == "EXPERIMENTAL", (
            f"TE {te.get('player_id')} model_grade={te['model_grade']!r}"
        )


# ── Test 5: market_overlay is None on all players ────────────────────────────

def test_market_overlay_is_none():
    result = _run()
    for player in result["players"]:
        assert player.get("market_overlay") is None, (
            f"market_overlay={player['market_overlay']!r} for {player.get('player_id')}"
        )


# ── Test 6: decision_supported is False on all players ───────────────────────

def test_decision_supported_is_false():
    result = _run()
    for player in result["players"]:
        assert player["decision_supported"] is False, (
            f"decision_supported not False for {player.get('player_id')}"
        )


# ── Test 7: counter_argument present when dynasty_value_score is non-null ────

def test_counter_argument_present_when_scored():
    result = _run()
    for player in result["players"]:
        if player.get("dynasty_value_score") is not None:
            assert player.get("counter_argument") is not None, (
                f"counter_argument missing on scored player {player.get('player_id')}"
            )


# ── Test 8: Non-skill positions excluded ─────────────────────────────────────

def test_non_skill_positions_excluded():
    result = _run()
    positions = {p["position"] for p in result["players"]}
    assert "K" not in positions
    assert "DEF" not in positions
    assert "P" not in positions


# ── Test 9: Players sorted by years_to_cliff ascending ───────────────────────

def test_players_sorted_by_years_to_cliff():
    result = _run()
    cliffs = [
        p["roster_audit"]["years_to_cliff"]
        for p in result["players"]
        if p.get("roster_audit") and p["roster_audit"].get("years_to_cliff") is not None
    ]
    assert cliffs == sorted(cliffs), f"Not sorted by years_to_cliff: {cliffs}"


# ── Test 10: Empty roster returns empty players array ────────────────────────

def test_empty_roster_returns_empty_players():
    result = _run(roster=[], scores=[])
    assert result["players"] == []
    assert result["status"] == "active"


def test_current_draft_rookie_uses_engine_a_universe_pvo(tmp_path):
    result = _run_with_universe(tmp_path, [_universe_row_for_rookie()])
    rookie = next(p for p in result["players"] if p["sleeper_id"] == "13414")
    assert rookie["player_id"] == "kaelon_black_rb"
    assert rookie["model_grade"] == "PROSPECT_C"
    assert rookie["engine_used"] == "engine_a"
    assert rookie["dynasty_value_score"] == 61.55
    assert rookie["xvar"] == 13.4
    assert rookie["decision_supported"] is False


def test_current_draft_rookie_source_versions_stamp_resolved_runtime_pvo(tmp_path):
    result, runtime_pvo_path = _run_with_runtime_universe(
        tmp_path, [_universe_row_for_rookie()]
    )
    rookie = next(p for p in result["players"] if p["sleeper_id"] == "13414")

    assert rookie["source_versions"]["universe_pvo_batch"] == str(runtime_pvo_path)
    assert rookie["source_versions"]["pvo_source_kind"] == "runtime"


def test_engine_a_row_without_resolved_source_kind_omits_pvo_source_kind():
    """D1: no-metadata fallback / explicit override must not stamp a None source kind.

    source_versions is typed dict[str, str]; pvo_source_kind is omitted (not None) when the
    resolver provenance is absent, so the PlayerValueObject validates without crashing.
    """
    from app.services.roster_auditor import _pvo_from_universe_row

    row = _universe_row_for_rookie()
    live_player = {"full_name": "Kaelon Black", "position": "RB", "age": 24}

    # provenance=None (no resolver metadata threaded)
    pvo_none = _pvo_from_universe_row(row, live_player, provenance=None)
    assert "pvo_source_kind" not in pvo_none.source_versions
    assert pvo_none.source_versions["universe_pvo_batch"]

    # provenance present but source_kind None (explicit-path seam)
    pvo_kindless = _pvo_from_universe_row(
        row,
        live_player,
        provenance={"universe_pvo_batch": "app/data/valuation/universe_pvo_latest.json",
                    "pvo_source_kind": None},
    )
    assert "pvo_source_kind" not in pvo_kindless.source_versions


def test_engine_a_rookie_reconciliation_preserves_veteran_engine_b_path(tmp_path):
    result = _run_with_universe(tmp_path, [_universe_row_for_rookie()])
    veteran = next(p for p in result["players"] if p["sleeper_id"] == "sleeper_rb_001")
    assert veteran["model_grade"] == "ACTIVE_B"
    assert veteran["engine_used"] == "engine_b"
    assert veteran["dynasty_value_score"] is not None


# ── The gsis-less veteran: production's actual shape ──────────────────────────
# Every fixture above hands the route a `gsis_id`. Sleeper does not: it returns
# null for that field on ALL 27 of David's players, so the gsis-keyed Engine B
# join resolved 0 of 27 and silently dropped 20 real scores while the endpoint
# reported dropped_player_count: 0. The suite stayed green because the fixture
# supplied the one field production has never had. These tests reproduce the
# real shape.
_VETERAN_NO_GSIS = {
    "player_id": "8146",
    "full_name": "Test Veteran WR",
    "position": "WR",
    "team": "NYJ",
    "age": 25,
    # deliberately NO gsis_id
}


def _universe_row_for_engine_b_veteran(**overrides) -> dict:
    row = {
        "sleeper_player_id": "8146",
        "dg_player_id": "test_veteran_wr",
        "identity_status": "resolved",
        "identity_ids": {"sleeper_id": "8146"},
        "player": {
            "full_name": "Test Veteran WR",
            "position": "WR",
            "team": "NYJ",
            "age": 25.0,
            "dg_status": "ENGINE_B",
        },
        "league_context": {
            "rostered": True,
            "roster_id": 1,
            "in_current_draft": False,
            "on_taxi": False,
        },
        "valuation": {
            "engine_path": "ENGINE_B",
            "valuation_status": "MODEL_SUPPORTED",
            "dynasty_value_score": 77.6,
            "xvar": 8.4,
            "model_grade": "ACTIVE_B",
            "feature_completeness": 1.0,
            "decision_supported": False,
        },
    }
    row.update(overrides)
    return row


def test_rostered_engine_b_veteran_without_gsis_id_still_gets_his_score(tmp_path):
    result = _run_with_universe(
        tmp_path,
        [_universe_row_for_engine_b_veteran()],
        roster=[_VETERAN_NO_GSIS],
        scores=[],
    )
    vet = next(p for p in result["players"] if p["sleeper_id"] == "8146")
    assert vet["dynasty_value_score"] == 77.6
    assert vet["engine_used"] == "engine_b"
    assert vet["model_grade"] == "ACTIVE_B"
    assert vet["dvs_engine"] == "B"


def test_engine_b_veteran_completeness_is_the_real_one_not_the_empty_features_constant(
    tmp_path,
):
    """signal_completeness on this surface was 4/17 = 0.2353 for every player --
    a constant of the code path (features={"age": ...}) presented as a
    measurement of the player, and it dragged a "fewer than 50% of required
    signals present" caveat under every row. The universe row carries the real
    figure; the route must not manufacture one."""
    result = _run_with_universe(
        tmp_path,
        [_universe_row_for_engine_b_veteran()],
        roster=[_VETERAN_NO_GSIS],
        scores=[],
    )
    vet = next(p for p in result["players"] if p["sleeper_id"] == "8146")
    assert vet["signal_completeness"] == 1.0


def test_engine_b_veteran_under_the_games_gate_keeps_its_honest_null(tmp_path):
    """Wilson (7 games) and Allen (4) are correctly withheld by
    ENGINE_B_MIN_GAMES_T. Reading the universe row inherits that refusal; a
    naive join-key swap would have recomputed and PRINTED an invented number,
    because the gate reads games_t from the features dict the route never fills."""
    gated = _universe_row_for_engine_b_veteran(
        valuation={
            "engine_path": "ENGINE_B",
            "valuation_status": "MODEL_UNCERTAIN",
            "dynasty_value_score": None,
            "xvar": None,
            "model_grade": "ACTIVE_B",
            "feature_completeness": 1.0,
            "decision_supported": False,
        }
    )
    result = _run_with_universe(
        tmp_path, [gated], roster=[_VETERAN_NO_GSIS], scores=[]
    )
    vet = next(p for p in result["players"] if p["sleeper_id"] == "8146")
    assert vet["dynasty_value_score"] is None
    assert vet["dvs_engine"] is None


def test_engine_a_rookie_carries_counter_argument_when_dvs_above_80(tmp_path):
    high_dvs_row = {
        **_universe_row_for_rookie(),
        "sleeper_player_id": "99999",
        "dg_player_id": "mendoza_wr",
        "identity_ids": {"sleeper_id": "99999"},
        "player": {"full_name": "Fernando Mendoza", "position": "WR", "team": "MIA", "age": 22.0},
        "valuation": {
            "engine_path": "ENGINE_A",
            "valuation_status": "MODEL_SUPPORTED",
            "dynasty_value_score": 85.14,
            "xvar": 10.31,
            "model_grade": "PROSPECT_B",
            "feature_completeness": 0.28,
            "decision_supported": False,
        },
    }
    high_dvs_player = {
        "player_id": "99999",
        "full_name": "Fernando Mendoza",
        "position": "WR",
        "team": "MIA",
        "age": 22,
        "gsis_id": None,
    }
    result = _run_with_universe(
        tmp_path,
        [_universe_row_for_rookie(), high_dvs_row],
        roster=[_ROOKIE_PLAYER, high_dvs_player, _RB_PLAYER],
        scores=[_RB_ENGINE_B_SCORE],
    )
    mendoza = next(p for p in result["players"] if p["sleeper_id"] == "99999")
    assert mendoza["dynasty_value_score"] == 85.14
    assert mendoza["counter_argument"] is not None, "Product Constitution Rule 4: counter_argument required for DVS > 80"


def test_roster_audit_degrades_when_universe_artifact_absent(tmp_path):
    missing_path = tmp_path / "missing.json"
    with (
        patch(
            "app.services.roster_auditor.get_my_roster",
            new_callable=AsyncMock,
            return_value=[_ROOKIE_PLAYER],
        ),
        patch("app.services.roster_auditor.score_inference_partition", return_value=[]),
        patch("app.services.roster_auditor.load_qb_identity_bridge", return_value={"players": {}}),
        # F-seed-split T4: absent seed + absent runtime → resolver/loader degrade to {}.
        patch("app.services.roster_auditor.PVO_SEED_PATH", missing_path),
        patch(
            "app.services.roster_auditor.PVO_RUNTIME_DIR",
            tmp_path / "no_runtime",
        ),
        patch(
            "src.dynasty_genius.services.market_overlay_service.enrich_pvo_list_with_market_overlay",
            return_value=None,
        ),
    ):
        result = asyncio.run(run_audit_pvo())
    rookie = result["players"][0]
    assert rookie["sleeper_id"] == "13414"
    assert rookie["model_grade"] == "PRE_MODEL"
