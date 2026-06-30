"""Artifact Freshness T1 RED: preflight + acceptance/parity verifier."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

NOW = datetime(2026, 6, 22, 15, 0, tzinfo=timezone.utc)


def _verifier():
    return import_module("scripts.verify_league_intelligence_refresh")


def _write_json(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)


def _cache_payload(fetched_at: datetime) -> str:
    return (
        '{"fetched_at":"'
        + fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        + '","ttl_hours":24,"data":[{"player":{"sleeperId":"p1"},"value":123}]}'
    )


def _valid_response() -> dict:
    return {
        "status": "degraded",
        "perspective_roster_id": 1,
        "source_artifacts": {
            "team_posture": {"schema_version": "team_posture.v1"},
            "team_value_matrix": {"schema_version": "team_value_matrix.v1"},
            "league_opportunity": {"schema_version": "league_opportunity.v1"},
        },
        "captured_at": "2026-06-22T15:00:00+00:00",
        "caveats": ["league_pulse_artifact_state_2026-06-22"],
        "team_postures": [
            {
                "decision_supported": False,
                "roster_id": 1,
                "team_name": "David",
                "posture_label": "CONTENDER",
                "score": 0.7,
                "components": {"starter_weighted_xvar_z": 1.0},
                "caveats": [],
            }
        ],
        "team_values": [
            {
                "decision_supported": False,
                "roster_id": 1,
                "team_name": "David",
                "value_views": {
                    "decision_supported": False,
                    "starter_weighted_xvar": 40.0,
                    "lineup_xvar": 35.0,
                    "depth_credit_xvar": 5.0,
                    "total_xvar_capped": 42.0,
                    "top_n_xvar": 39.0,
                },
                "age_profile": {"value_weighted_age": 25.4},
                "positional_summary": {"WR": {"z_score": 0.8, "surplus_label": "surplus"}},
                "future_picks": {"owned_count": 4, "pick_value_status": "unvalued"},
            }
        ],
        "partner_rankings": [
            {
                "decision_supported": False,
                "counterparty_roster_id": 2,
                "counterparty_team_name": "Counterparty",
                "partner_score": 0.6,
                "matched_positions": ["WR"],
                "score_components": {"divergence_density_score": 0.3},
                "evidence": {"divergence_row_count": 2},
                "market_influenced": True,
                "caveats": ["partner_score_market_influenced"],
            }
        ],
        "model_native_cards": [
            {
                "decision_supported": False,
                "card_id": "roster-fit",
                "card_type": "ROSTER_SURPLUS_DEFICIT_MATCH",
                "evidence_status": "evidence_gated",
                "sort_key": "positional_z_differential_desc",
                "sort_value": 2.0,
                "rationale_primary": "opportunity_signal",
                "rationale_secondary": [],
                "evidence": {
                    "position": "WR",
                    "perspective_position_z": -0.9,
                    "counterparty_position_z": 1.1,
                    "positional_z_differential": 2.0,
                    "perspective_surplus_label": "deficit",
                    "counterparty_surplus_label": "surplus",
                },
                "score_components": {"fit_score": 0.5, "feasibility_score": 0.6},
                "caveats": [],
            }
        ],
        "market_overlay_cards": [
            {
                "decision_supported": False,
                "card_id": "waiver",
                "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
                "evidence_status": "evidence_complete",
                "sort_key": "absolute_model_market_delta_desc",
                "sort_value": 0.4,
                "rationale_primary": "market_divergence_context",
                "rationale_secondary": [],
                "evidence": {
                    "signal": "MODEL_HIGH_MARKET_LOW",
                    "evidence_status": "evidence_complete",
                    "model_minus_market_delta": 0.4,
                    "asset_xvar": 1.1,
                },
                "score_components": {
                    "fit_score": 0.4,
                    "divergence_score": 0.7,
                    "feasibility_score": 0.8,
                },
                "caveats": ["market_overlay_unvalidated_divergence"],
                "roster_capacity_candidates": {
                    "decision_supported": False,
                    "pool_status": "constrained_single_candidate",
                    "selection_rule": "descriptive_candidate_pool_no_tool_selection",
                    "narrowing_rule": "only_one_capacity_candidate_available",
                    "sort_key": "xvar_pct_ascending_then_full_name_then_sleeper_player_id",
                    "items": [
                        {
                            "decision_supported": False,
                            "sleeper_player_id": "drop-1",
                            "full_name": "Drop Candidate",
                            "position": "WR",
                            "value_status": "valued",
                            "xvar_pct": 12.0,
                            "dvs": 30.0,
                            "capacity_conflict_status": "hard_roster_rules_conflict",
                            "rule_conflict_label": "IR compliance violation",
                            "caveats": [],
                        }
                    ],
                    "caveats": [],
                },
            }
        ],
        "dropped": {
            "decision_supported": False,
            "team_postures": 0,
            "team_values": 0,
            "partner_rankings": 0,
            "model_native_cards": 0,
            "market_overlay_cards": 0,
            "roster_capacity_candidate_pools": 0,
        },
        "decision_supported": False,
    }


def test_market_source_probe_is_side_effect_free_for_fresh_cache(tmp_path: Path) -> None:
    v = _verifier()
    cache_file = tmp_path / "app/cache/fantasycalc/market_values.json"
    _write_json(cache_file, _cache_payload(NOW - timedelta(hours=1)))
    before = cache_file.read_bytes()

    def api_reachable() -> bool:
        raise AssertionError("fresh cache classification must not touch the network")

    result = v.classify_market_source(
        cache_file=cache_file,
        now=NOW,
        ttl_hours=24,
        api_reachable=api_reachable,
    )

    assert result.status == "fresh-cache"
    assert result.should_abort is False
    assert cache_file.read_bytes() == before


@pytest.mark.parametrize(
    ("cache_age_hours", "api_ok", "expected"),
    [
        (48, False, "stale-cache"),
        (None, False, "cold-empty"),
        (None, True, "live"),
    ],
)
def test_market_source_probe_classifies_abort_states_without_writes(
    tmp_path: Path,
    cache_age_hours: int | None,
    api_ok: bool,
    expected: str,
) -> None:
    v = _verifier()
    cache_file = tmp_path / "app/cache/fantasycalc/market_values.json"
    if cache_age_hours is not None:
        _write_json(cache_file, _cache_payload(NOW - timedelta(hours=cache_age_hours)))
        before = cache_file.read_bytes()
    else:
        before = None

    result = v.classify_market_source(
        cache_file=cache_file,
        now=NOW,
        ttl_hours=24,
        api_reachable=lambda: api_ok,
    )

    assert result.status == expected
    assert result.should_abort is (expected in {"stale-cache", "cold-empty"})
    if before is None:
        assert not cache_file.exists()
    else:
        assert cache_file.read_bytes() == before


def test_preflight_fails_closed_on_missing_inputs_schema_mismatch_or_route_failure(
    tmp_path: Path,
) -> None:
    v = _verifier()
    required = tmp_path / "resources/prospect_cards.json"
    _write_json(required, "{}")
    posture = tmp_path / "app/data/valuation/team_posture_latest.json"
    _write_json(posture, '{"schema_version":"team_posture.v1"}')
    market = v.MarketSourceClassification(status="live", should_abort=False)

    passed = v.verify_preflight(
        required_inputs=[required],
        current_artifacts={"team_posture": posture},
        expected_schema_versions={"team_posture": "team_posture.v1"},
        route_probe=lambda: True,
        market_source=market,
    )
    assert passed.status == "passed"

    with pytest.raises(v.RefreshVerificationError, match="missing input"):
        v.verify_preflight(
            required_inputs=[tmp_path / "missing.json"],
            current_artifacts={"team_posture": posture},
            expected_schema_versions={"team_posture": "team_posture.v1"},
            route_probe=lambda: True,
            market_source=market,
        )

    with pytest.raises(v.RefreshVerificationError, match="schema_version"):
        v.verify_preflight(
            required_inputs=[required],
            current_artifacts={"team_posture": posture},
            expected_schema_versions={"team_posture": "wrong.v1"},
            route_probe=lambda: True,
            market_source=market,
        )

    with pytest.raises(v.RefreshVerificationError, match="route"):
        v.verify_preflight(
            required_inputs=[required],
            current_artifacts={"team_posture": posture},
            expected_schema_versions={"team_posture": "team_posture.v1"},
            route_probe=lambda: False,
            market_source=market,
        )


def test_physical_shape_gate_calls_app_route_and_validates_response(monkeypatch) -> None:
    v = _verifier()
    route = import_module("app.api.routes.league_pulse")
    monkeypatch.setattr(route, "_load_team_posture", lambda: {"schema_version": "team_posture.v1"})
    monkeypatch.setattr(
        route,
        "_load_team_value_matrix",
        lambda: {"schema_version": "team_value_matrix.v1"},
    )
    monkeypatch.setattr(
        route,
        "_load_league_opportunity",
        lambda: {"schema_version": "league_opportunity.v1"},
    )
    monkeypatch.setattr(route, "assemble_league_pulse", lambda *_args: _valid_response())
    from app.main import app

    body = v.verify_league_pulse_route_shape(TestClient(app))

    assert body["decision_supported"] is False
    assert body["market_overlay_cards"][0]["card_type"] == "UNROSTERED_MODEL_MARKET_DIVERGENCE"


@pytest.mark.parametrize(
    "mutator,match",
    [
        (
            lambda body: body["model_native_cards"][0]["evidence"].update(
                {"market_percentile": 0.9}
            ),
            "market-bleed",
        ),
        # T1-F1: raw market keys are forbidden in ALL non-overlay sections.
        (
            lambda body: body["team_postures"][0]["components"].update(
                {"market_percentile": 0.9}
            ),
            "market-bleed",
        ),
        (
            lambda body: body["team_values"][0]["value_views"].update(
                {"model_minus_market_delta": 0.9}
            ),
            "market-bleed",
        ),
        (
            lambda body: body["partner_rankings"][0]["evidence"].update(
                {"market_percentile": 0.9}
            ),
            "market-bleed",
        ),
        (lambda body: body.update({"market_overlay_cards": []}), "UNROSTERED_MODEL_MARKET_DIVERGENCE"),
        (
            lambda body: body["market_overlay_cards"][0].update(
                {"roster_capacity_candidates": None}
            ),
            "capacity-pairing",
        ),
        (
            lambda body: body["team_values"][0].update({"decision_supported": True}),
            "decision_supported",
        ),
        (lambda body: body["caveats"].append("SELL_NOW"), "banned"),
    ],
)
def test_acceptance_contract_fails_on_leakage_missing_drop_or_bad_framing(
    mutator,
    match: str,
    tmp_path: Path,
) -> None:
    v = _verifier()
    body = _valid_response()
    mutator(body)

    with pytest.raises(v.RefreshVerificationError, match=match):
        v.verify_acceptance(
            response=body,
            artifact_paths=[],
            previous_captured_at="2026-05-24T00:00:00+00:00",
            run_date="2026-06-22",
            market_source_status="live",
            changed_paths=[tmp_path / "app/data/valuation/league_opportunity_latest.json"],
        )


def test_acceptance_contract_passes_and_reports_counts_and_hashes(tmp_path: Path) -> None:
    v = _verifier()
    artifact = tmp_path / "app/data/valuation/league_opportunity_latest.json"
    _write_json(artifact, '{"schema_version":"league_opportunity.v1"}')

    report = v.verify_acceptance(
        response=_valid_response(),
        artifact_paths=[artifact],
        previous_captured_at="2026-05-24T00:00:00+00:00",
        run_date="2026-06-22",
        market_source_status="live",
        changed_paths=[artifact],
    )

    assert report.status == "passed"
    assert report.counts["team_count"] == 1
    assert report.counts["waiver_cards"] == 1
    assert report.counts["waiver_capacity_pools"] == 1
    assert report.artifacts[0]["path"].endswith("league_opportunity_latest.json")
    assert len(report.artifacts[0]["sha256"]) == 64
    assert report.artifacts[0]["byte_size"] > 0


def test_acceptance_report_schema_is_locked_and_rejects_missing_audit_fields() -> None:
    v = _verifier()
    report = {
        "schema_version": "league_intelligence_refresh_report.v1",
        "status": "passed",
        "steps": [{"phase": "preflight", "status": "passed"}],
        "market_source": {"status": "live"},
        "artifacts": [{"path": "app/data/valuation/a.json", "sha256": "a" * 64, "byte_size": 2}],
        "captured_at_delta": {"before": "2026-05-24", "after": "2026-06-22"},
        "counts": {"team_count": 12, "waiver_cards": 1, "waiver_capacity_pools": 1},
        "checks": {
            "shape_drift": "passed",
            "market_bleed": "passed",
            "drop_pairing": "passed",
            "decision_supported": "passed",
            "banned_language": "passed",
            "freshness": "passed",
            "guardrails": "passed",
        },
        "rollback_guardrail_diff": {"forbidden_paths_changed": []},
        "decision_supported": False,
    }

    assert v.validate_report_schema(report).status == "passed"

    broken = dict(report)
    broken["artifacts"] = [{"path": "app/data/valuation/a.json", "byte_size": 2}]
    with pytest.raises(v.RefreshVerificationError, match="sha256"):
        v.validate_report_schema(broken)
