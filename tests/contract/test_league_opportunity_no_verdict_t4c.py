"""Phase 1 T4c RED: enforce the No-Verdict cordon and go live on v2 artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HEADER_COPY = (
    "Diagnostic Workspace: Surfaces raw model outputs and market variance. "
    "Valuation data is descriptive only, does not nominate players or direct "
    "trades, and requires manual qualitative evaluation."
)
OLD_LEAGUE_OPPORTUNITY_TOKENS = {
    "recommended_drop",
    "recommended_drops",
    "recommended_drop_name",
    "LeaguePulseRecommendedDrop",
    "opportunity_score",
    "WAIVER_CANDIDATE",
    "TAXI_ACTIVATION_CANDIDATE",
}


def _posture_artifact() -> dict:
    return {
        "schema_version": "team_posture.v1",
        "captured_at": "2026-06-30T12:00:00Z",
        "teams": [
            {
                "roster_id": 1,
                "owner": {"team_name": "David"},
                "posture": {
                    "label": "CONTENDER",
                    "score": 0.75,
                    "components": {},
                    "caveats": [],
                },
            },
            {
                "roster_id": 2,
                "owner": {"team_name": "Counterparty"},
                "posture": {
                    "label": "REBUILDING",
                    "score": -0.2,
                    "components": {},
                    "caveats": [],
                },
            },
        ],
    }


def _value_artifact() -> dict:
    return {
        "schema_version": "team_value_matrix.v1",
        "captured_at": "2026-06-30T12:01:00Z",
        "teams": [
            {
                "roster_id": 1,
                "owner": {"team_name": "David"},
                "team_value_views": {
                    "starter_weighted_xvar": 42.0,
                    "lineup_xvar": 39.0,
                    "depth_credit_xvar": 3.0,
                    "total_xvar_capped": 45.0,
                    "top_n_xvar": 43.0,
                },
                "age_profile": {},
                "positional_summary": {},
                "future_picks": {},
            },
            {
                "roster_id": 2,
                "owner": {"team_name": "Counterparty"},
                "team_value_views": {
                    "starter_weighted_xvar": 38.0,
                    "lineup_xvar": 35.0,
                    "depth_credit_xvar": 4.0,
                    "total_xvar_capped": 42.0,
                    "top_n_xvar": 40.0,
                },
                "age_profile": {},
                "positional_summary": {},
                "future_picks": {},
            },
        ],
    }


def _v2_opportunity_artifact() -> dict:
    return {
        "schema_version": "league_opportunity.v2",
        "captured_at": "2026-06-30T12:02:00Z",
        "perspective_roster_id": 1,
        "decision_supported": False,
        "card_section_counts": [
            {
                "sort_key": "absolute_model_market_delta_desc",
                "total_count": 1,
                "shown_count": 1,
                "section_cap": 20,
                "decision_supported": False,
            }
        ],
        "partner_rankings": [
            {
                "counterparty_roster_id": 2,
                "counterparty_team_name": "Counterparty",
                "partner_score": 0.61,
                "matched_positions": ["WR"],
                "score_components": {"divergence_density_score": 0.3},
                "evidence": {"divergence_row_count": 2},
            }
        ],
        "cards": [
            {
                "card_id": "market-v2",
                "card_type": "UNROSTERED_MODEL_MARKET_DIVERGENCE",
                "evidence_status": "evidence_complete",
                "sort_key": "absolute_model_market_delta_desc",
                "sort_value": 0.42,
                "rationale": {
                    "primary": "UNROSTERED_MODEL_MARKET_ASYMMETRY",
                    "secondary": ["FANTASYCALC_PERCENTILE_DIVERGENCE"],
                    "evidence": {
                        "signal": "MODEL_HIGH_MARKET_LOW",
                        "evidence_status": "evidence_complete",
                        "model_minus_market_delta": 0.42,
                        "asset_xvar": 1.2,
                    },
                },
                "score_components": {
                    "fit_score": 0.4,
                    "divergence_score": 0.7,
                    "feasibility_score": 0.9,
                },
                "roster_capacity_candidates": {
                    "decision_supported": False,
                    "pool_status": "available",
                    "selection_rule": "descriptive_candidate_pool_no_tool_selection",
                    "narrowing_rule": "all_safe_candidates",
                    "sort_key": "xvar_pct_ascending_then_full_name_then_sleeper_player_id",
                    "items": [],
                    "caveats": [],
                },
                "caveats": ["market_overlay_unvalidated_divergence"],
                "decision_supported": False,
            }
        ],
    }


def _stale_v1_opportunity_artifact() -> dict:
    return {
        "schema_version": "league_opportunity.v1",
        "captured_at": "2026-06-30T11:59:00Z",
        "perspective_roster_id": 1,
        "cards": [],
        "partner_rankings": [],
    }


def test_t4c_scanner_bucket_is_enforcing_and_reclassifies_what_changed_titles() -> None:
    import scripts.scan_league_opportunity_no_verdict as scanner

    league_pulse_entries = {
        (entry.path, entry.token) for entry in scanner.LEAGUE_PULSE_PHASE_1_DEBT
    }
    what_changed_entries = {
        (entry.path, entry.token) for entry in scanner.WHAT_CHANGED_GOVERNANCE_DEBT
    }
    reclassified = {
        ("frontend/openapi.json", "Recommendation"),
        ("frontend/openapi.json", "Recommended"),
        ("frontend/src/lib/api/types.gen.ts", "Recommendation"),
        ("frontend/src/lib/api/types.gen.ts", "Recommended"),
    }

    assert scanner.LEAGUE_PULSE_PHASE_1_DEBT == []
    assert reclassified <= what_changed_entries
    assert not (reclassified & league_pulse_entries)

    surfaces = [
        Path("src/dynasty_genius/league_opportunity_map.py"),
        Path("app/api/routes/league_pulse_models.py"),
        Path("app/api/routes/league_pulse_assembler.py"),
        Path("frontend/openapi.json"),
        Path("frontend/src/lib/api/types.gen.ts"),
        Path("frontend/src/lib/api/zod.gen.ts"),
        Path("frontend/src/league-pulse/OpportunityCards.tsx"),
        Path("frontend/src/league-pulse/LeaguePulseHeader.tsx"),
        Path("src/dynasty_genius/what_changed/report.py"),
        Path("app/api/routes/league_what_changed_models.py"),
    ]
    raw = scanner.scan_paths(surfaces, allowlist=[])
    raw_pairs = {(finding.path, finding.token) for finding in raw}
    allow_pairs = {(entry.path, entry.token) for entry in scanner.KNOWN_DEBT_ALLOWLIST}

    assert scanner.scan_paths(surfaces, allowlist=scanner.KNOWN_DEBT_ALLOWLIST) == []
    assert raw_pairs == allow_pairs


def test_t4c_assembler_is_v2_only_and_stale_v1_fails_closed() -> None:
    from app.api.routes import league_pulse_assembler as assembler

    source = Path(assembler.__file__).read_text(encoding="utf-8")

    assert assembler.ACCEPTED_LEAGUE_OPPORTUNITY_SCHEMAS == frozenset(
        {"league_opportunity.v2"}
    )
    assert "league_pulse_v1_compat" not in source

    with pytest.raises(assembler.LeaguePulseDependencyError):
        assembler.assemble_league_pulse(
            _posture_artifact(),
            _value_artifact(),
            _stale_v1_opportunity_artifact(),
        )

    response = assembler.assemble_league_pulse(
        _posture_artifact(),
        _value_artifact(),
        _v2_opportunity_artifact(),
    )
    assert response.source_artifacts.league_opportunity["schema_version"] == (
        "league_opportunity.v2"
    )
    assert len(response.market_overlay_cards) == 1
    assert response.card_section_counts[0].sort_key == "absolute_model_market_delta_desc"


def test_t4c_go_live_artifacts_and_refresh_verifier_are_v2() -> None:
    from app.main import app
    from scripts import run_league_intelligence_refresh, run_what_changed_report

    artifact_path = ROOT / "app" / "data" / "valuation" / "league_opportunity_latest.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact_text = json.dumps(artifact, sort_keys=True)

    assert artifact["schema_version"] == "league_opportunity.v2"
    assert not (OLD_LEAGUE_OPPORTUNITY_TOKENS & set(artifact_text.split('"')))
    for token in OLD_LEAGUE_OPPORTUNITY_TOKENS:
        assert token not in artifact_text

    assert (
        run_league_intelligence_refresh.EXPECTED_SCHEMA_VERSIONS["opportunity"]
        == "league_opportunity.v2"
    )
    assert (
        run_what_changed_report._resolve_inputs()["league_opportunity_path"]
        == artifact_path
    )

    response = TestClient(app).get("/api/league/what-changed")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "war_room_2_what_changed_v1"
    assert "recommended_drop_name" not in json.dumps(body, sort_keys=True)


def test_t4c_header_copy_is_scanner_clean_under_full_no_verdict_rules() -> None:
    import scripts.scan_league_opportunity_no_verdict as scanner

    header_path = ROOT / "frontend" / "src" / "league-pulse" / "LeaguePulseHeader.tsx"
    header_text = header_path.read_text(encoding="utf-8")

    assert HEADER_COPY in header_text
    assert "recommend" not in header_text.lower()
    assert scanner.scan_text(HEADER_COPY) == set()


def test_t4c_opportunity_latest_write_publishes_latest_via_atomic_replace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Happy path: the shared *_latest pointers are published only via os.replace,
    never written in place, so a concurrent reader never observes a partial write."""
    from src.dynasty_genius.league_opportunity_map import (
        write_league_opportunity_artifacts,
    )

    latest = tmp_path / "league_opportunity_latest.json"
    markdown_latest = tmp_path / "league_opportunity_latest.md"
    write_targets: list[Path] = []
    original_write_text = Path.write_text

    def spy_write_text(self: Path, data: str, *args: object, **kwargs: object) -> int:
        write_targets.append(self)
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy_write_text)

    write_league_opportunity_artifacts(
        {**_v2_opportunity_artifact(), "captured_at": "2026-06-30T12:30:00Z"},
        output_dir=tmp_path,
        run_id="atomic-green",
    )

    assert latest not in write_targets
    assert markdown_latest not in write_targets

    served = json.loads(latest.read_text(encoding="utf-8"))
    assert served["schema_version"] == "league_opportunity.v2"
    assert served["captured_at"] == "2026-06-30T12:30:00Z"
    assert markdown_latest.read_text(encoding="utf-8").strip()


def test_t4c_opportunity_latest_write_preserves_original_on_replace_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Failure injection: an interrupted atomic publish leaves the prior latest
    fully intact and valid, with no partial/temp bytes visible to readers."""
    import os

    from src.dynasty_genius.league_opportunity_map import (
        write_league_opportunity_artifacts,
    )

    latest = tmp_path / "league_opportunity_latest.json"
    existing = _v2_opportunity_artifact()
    latest.write_text(json.dumps(existing, sort_keys=True) + "\n", encoding="utf-8")

    original_replace = os.replace

    def flaky_replace(src: object, dst: object, *args: object, **kwargs: object) -> None:
        if Path(dst) == latest:
            raise OSError("simulated interrupted atomic publish")
        return original_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", flaky_replace)

    with pytest.raises(OSError):
        write_league_opportunity_artifacts(
            {**_v2_opportunity_artifact(), "captured_at": "2026-06-30T12:45:00Z"},
            output_dir=tmp_path,
            run_id="atomic-fail",
        )

    still_served = json.loads(latest.read_text(encoding="utf-8"))
    assert still_served["schema_version"] == "league_opportunity.v2"
    assert still_served["captured_at"] == existing["captured_at"]
    assert not list(tmp_path.glob("league_opportunity_latest.json.*.tmp"))


def test_t4c_capacity_pool_dto_and_generated_clients_carry_no_v1_legacy_state() -> None:
    """T4c deleted the v1-compat shim. The public capacity-pool schema must not
    advertise or accept the shim-only ``legacy_single_candidate`` migration state
    (it is outside the No-Verdict vocabulary, so the scanner cannot catch it)."""
    import pydantic

    from app.api.routes.league_pulse_models import LeaguePulseCapacityCandidatePool

    surfaces = {
        "dto": ROOT / "app" / "api" / "routes" / "league_pulse_models.py",
        "openapi": ROOT / "frontend" / "openapi.json",
        "types": ROOT / "frontend" / "src" / "lib" / "api" / "types.gen.ts",
        "zod": ROOT / "frontend" / "src" / "lib" / "api" / "zod.gen.ts",
    }
    for name, path in surfaces.items():
        text = path.read_text(encoding="utf-8")
        assert "legacy_single_candidate" not in text, name
        assert "v1 artifact migrated" not in text, name

    base = {
        "selection_rule": "descriptive_candidate_pool_no_tool_selection",
        "narrowing_rule": "all_safe_candidates",
        "sort_key": "xvar_pct_ascending_then_full_name_then_sleeper_player_id",
        "items": [],
        "caveats": [],
    }
    for status in ("available", "constrained_single_candidate", "empty"):
        LeaguePulseCapacityCandidatePool(pool_status=status, **base)
    with pytest.raises(pydantic.ValidationError):
        LeaguePulseCapacityCandidatePool(pool_status="legacy_single_candidate", **base)


def test_t4c_closeout_uses_existing_sprint_tollgate_and_no_verdict_scanner() -> None:
    governance = (
        ROOT / "docs" / "governance" / "02-agent-operating-loop.md"
    ).read_text(encoding="utf-8")
    scanner_tests = (
        ROOT / "tests" / "contract" / "test_league_opportunity_no_verdict_scanner.py"
    ).read_text(encoding="utf-8")

    assert "scripts/verify_sprint_closeout.py" in governance
    assert "LEAGUE_PULSE_PHASE_1_DEBT == []" in scanner_tests
    assert "pytest.skip" not in scanner_tests.split(
        "test_league_pulse_phase_1_debt_is_empty_at_t4_closeout", 1
    )[1]
