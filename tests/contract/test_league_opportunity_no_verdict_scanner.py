"""T1 RED: No-Verdict scanner for league_opportunity + League Pulse debt.

These tests define the scanner contract only. T1 GREEN should add the scanner
implementation and exact known-debt allowlist without changing producer/API/FE
semantics yet. The allowlist-empty assertion is intentionally skipped until T4
closeout, when the semantic reconciliation and generated clients have landed.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path


def _scanner():
    try:
        return import_module("scripts.scan_league_opportunity_no_verdict")
    except ModuleNotFoundError as exc:
        raise AssertionError("No-Verdict scanner module is not implemented yet") from exc


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _tokens(findings: list[object]) -> set[str]:
    return {str(getattr(finding, "token")) for finding in findings}


def _paths(findings: list[object]) -> set[str]:
    return {str(getattr(finding, "path")) for finding in findings}


def _token_paths(findings: list[object], token: str) -> set[str]:
    return {
        str(getattr(finding, "path"))
        for finding in findings
        if str(getattr(finding, "token")) == token
    }


def test_scanner_fails_closed_on_new_no_verdict_tokens_outside_allowlist(tmp_path: Path) -> None:
    """New recommendation/target/rank-order language outside the allowlist fails."""
    scanner = _scanner()
    dirty = _write(
        tmp_path / "new_surface.json",
        """
        {
          "recommended_drop": {"full_name": "Tool Selected Player"},
          "tool_nominated_target": "123",
          "opportunity_score_rank": 1
        }
        """,
    )

    findings = scanner.scan_paths([dirty], allowlist=scanner.KNOWN_DEBT_ALLOWLIST)

    assert _tokens(findings) >= {
        "recommended_drop",
        "tool_nominated_target",
        "opportunity_score_rank",
    }


def test_allowlist_is_exact_by_path_token_and_reason(tmp_path: Path) -> None:
    """A known token passes only at its pinned path; the same token elsewhere fails."""
    scanner = _scanner()
    allowlisted = _write(
        tmp_path / "frontend" / "openapi.json",
        '{"recommended_drop": {"$ref": "#/components/schemas/LeaguePulseRecommendedDrop"}}',
    )
    new_path_same_token = _write(
        tmp_path / "frontend" / "unexpected_openapi_copy.json",
        '{"recommended_drop": {"$ref": "#/components/schemas/LeaguePulseRecommendedDrop"}}',
    )
    allowlist = [
        scanner.AllowlistEntry(
            path=str(allowlisted.relative_to(tmp_path)),
            token="recommended_drop",
            reason="preexisting league_opportunity.v1 debt removed by Phase 1 T2/T4",
        ),
        scanner.AllowlistEntry(
            path=str(allowlisted.relative_to(tmp_path)),
            token="LeaguePulseRecommendedDrop",
            reason="preexisting league_opportunity.v1 debt removed by Phase 1 T2/T4",
        ),
    ]

    findings = scanner.scan_paths([allowlisted, new_path_same_token], root=tmp_path, allowlist=allowlist)

    assert _paths(findings) == {"frontend/unexpected_openapi_copy.json"}
    assert _tokens(findings) == {"recommended_drop", "LeaguePulseRecommendedDrop"}


def test_candidate_action_language_is_banned_but_descriptive_pool_noun_is_allowed(
    tmp_path: Path,
) -> None:
    """Action-shaped candidate terms fail; descriptive roster-capacity pool nouns pass."""
    scanner = _scanner()
    action_card_type = _write(
        tmp_path / "app" / "data" / "valuation" / "league_opportunity_latest.json",
        '{"cards": [{"card_type": "WAIVER_CANDIDATE"}]}',
    )
    visible_action_label = _write(
        tmp_path / "frontend" / "src" / "league-pulse" / "OpportunityCards.tsx",
        '<p>Activation candidate</p>',
    )
    field_path_action = _write(
        tmp_path / "app" / "api" / "routes" / "league_pulse_models.py",
        "tool_nominated_candidate: str | None = None",
    )
    descriptive_pool = _write(
        tmp_path / "src" / "dynasty_genius" / "roster_capacity" / "models.py",
        "class CapacityAuditResult(BaseModel):\n    candidates: list[CapacityCandidate] = []\n",
    )

    findings = scanner.scan_paths(
        [action_card_type, visible_action_label, field_path_action, descriptive_pool],
        root=tmp_path,
        allowlist=[],
    )

    assert _tokens(findings) >= {
        "WAIVER_CANDIDATE",
        "Activation candidate",
        "tool_nominated_candidate",
    }
    assert str(descriptive_pool.relative_to(tmp_path)) not in _paths(findings)


def test_action_candidate_field_names_fail_but_descriptive_candidate_names_pass(
    tmp_path: Path,
) -> None:
    """Singular action-candidate fields are banned; descriptive pool/class names are not."""
    scanner = _scanner()
    dirty = _write(
        tmp_path / "action_fields.py",
        "\n".join(
            [
                "drop_candidate = None",
                "activation_candidate = None",
                "cut_candidate_id = None",
                "waiver_candidate = None",
                "trade_candidate = None",
                "tool_nominated_candidate = None",
            ]
        ),
    )
    clean = _write(
        tmp_path / "descriptive_pool.py",
        "\n".join(
            [
                "cut_candidates = []",
                "top_candidates = []",
                "forced_cut_candidates = []",
                "class CapacityCandidate: ...",
                "class RosterCutCandidate: ...",
                "class WhatChangedCutCandidate: ...",
            ]
        ),
    )

    findings = scanner.scan_paths([dirty, clean], root=tmp_path, allowlist=[])

    assert _token_paths(findings, "drop_candidate") == {"action_fields.py"}
    assert _token_paths(findings, "activation_candidate") == {"action_fields.py"}
    assert _token_paths(findings, "cut_candidate_id") == {"action_fields.py"}
    assert _token_paths(findings, "waiver_candidate") == {"action_fields.py"}
    assert _token_paths(findings, "trade_candidate") == {"action_fields.py"}
    assert _token_paths(findings, "tool_nominated_candidate") == {"action_fields.py"}
    assert "descriptive_pool.py" not in _paths(findings)


def test_path_outside_root_fails_loud_without_uncaught_relative_to_error(
    tmp_path: Path,
) -> None:
    """A path outside root is a controlled scanner error, not an uncaught ValueError."""
    scanner = _scanner()
    root = tmp_path / "root"
    outside = _write(tmp_path / "outside" / "openapi.json", '{"recommended_drop": true}')

    try:
        findings = scanner.scan_paths([outside], root=root, allowlist=[])
    except ValueError as exc:
        raise AssertionError(
            f"outside-root path leaked uncaught ValueError: {exc}"
        ) from exc

    assert findings
    assert "scanner_path_outside_root" in _tokens(findings)


def test_missing_expected_surface_file_fails_loud(tmp_path: Path) -> None:
    """A typo in the surface list must not pass vacuously as a clean scan."""
    scanner = _scanner()
    missing = tmp_path / "frontend" / "missing_openapi.json"

    findings = scanner.scan_paths([missing], root=tmp_path, allowlist=[])

    assert findings
    assert _tokens(findings) == {"scanner_file_unavailable"}
    assert _paths(findings) == {"frontend/missing_openapi.json"}


def test_current_known_debt_allowlist_enumerates_real_phase1_surface_debt() -> None:
    """The temporary allowlist is fully discharged after What-Changed cleanup."""
    scanner = _scanner()

    assert scanner.LEAGUE_PULSE_PHASE_1_DEBT == []
    assert scanner.WHAT_CHANGED_GOVERNANCE_DEBT == []
    assert scanner.KNOWN_DEBT_ALLOWLIST == []


def test_current_phase1_surfaces_scan_clean_after_exact_known_debt_allowlist() -> None:
    """Current debt is allowed only because each known occurrence is pinned exactly."""
    scanner = _scanner()
    current_surfaces = [
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

    findings = scanner.scan_paths(current_surfaces, allowlist=scanner.KNOWN_DEBT_ALLOWLIST)

    assert findings == []


def test_empty_whitespace_and_case_insensitive_tokens(tmp_path: Path) -> None:
    """Whitespace-only values are ignored; token matching is case-insensitive."""
    scanner = _scanner()
    clean = _write(tmp_path / "clean.json", '{"label": "   "}')
    dirty = _write(tmp_path / "dirty.json", '{"Recommended_Action": "DROP NOW"}')

    findings = scanner.scan_paths([clean, dirty], root=tmp_path, allowlist=[])

    assert _paths(findings) == {"dirty.json"}
    assert "Recommended_Action" in _tokens(findings)


def test_allowlist_buckets_are_disjoint_and_union_to_known_debt() -> None:
    """Both buckets are empty after the final No-Verdict rename."""
    scanner = _scanner()

    league_pulse = set(scanner.LEAGUE_PULSE_PHASE_1_DEBT)
    what_changed = set(scanner.WHAT_CHANGED_GOVERNANCE_DEBT)
    known = set(scanner.KNOWN_DEBT_ALLOWLIST)

    assert league_pulse == set()
    assert what_changed == set()
    assert league_pulse.isdisjoint(what_changed)
    assert known == league_pulse | what_changed


def test_what_changed_governance_debt_bucket_is_empty_after_descriptive_rename() -> None:
    """What-Changed's former directive field names are reconciled, not carved out."""
    scanner = _scanner()

    assert scanner.WHAT_CHANGED_GOVERNANCE_DEBT == []


def test_scanner_source_no_longer_pins_old_what_changed_field_names() -> None:
    """The cordon cannot carry its own stale What-Changed allowlist prose."""
    scanner_source = Path("scripts/scan_league_opportunity_no_verdict.py").read_text(
        encoding="utf-8"
    )

    assert "promote_recommended" not in scanner_source
    assert "recommendation_reasons" not in scanner_source


def test_what_changed_consumes_league_opportunity_renames_in_league_pulse_bucket() -> None:
    """What-Changed consumption of league_opportunity fields moves with Phase 1."""
    scanner = _scanner()

    league_pulse_entries = {
        (entry.path, entry.token) for entry in scanner.LEAGUE_PULSE_PHASE_1_DEBT
    }

    # T3 removed the What-Changed opportunity_score consumption field + report.py
    # assignment + regenerated openapi. T4a removed the BACKEND recommended_drop /
    # recommended_drop_name consumption (report.py now emits a non-nominating
    # roster_capacity_context; the WhatChangedCard field + openapi were dropped).
    # T4b regenerated the FE client (types.gen / zod.gen) from the v2 OpenAPI and
    # rewrote the visible FE render, so the FE codegen + render tokens are GONE.
    assert not (
        {
            # T4a backend cordon shrink:
            ("src/dynasty_genius/what_changed/report.py", "recommended_drop"),
            ("src/dynasty_genius/what_changed/report.py", "recommended_drop_name"),
            ("app/api/routes/league_what_changed_models.py", "recommended_drop_name"),
            ("frontend/openapi.json", "recommended_drop_name"),
            # T4b FE codegen + render cordon shrink:
            ("frontend/src/lib/api/types.gen.ts", "recommended_drop_name"),
            ("frontend/src/lib/api/types.gen.ts", "opportunity_score"),
            ("frontend/src/lib/api/zod.gen.ts", "recommended_drop_name"),
            ("frontend/src/lib/api/zod.gen.ts", "opportunity_score"),
            ("frontend/src/league-pulse/OpportunityCards.tsx", "opportunity_score"),
            ("frontend/src/league-pulse/OpportunityCards.tsx", "recommended_drop"),
            ("frontend/src/league-pulse/LeaguePulseHeader.tsx", "recommended_drops"),
        }
        & league_pulse_entries
    )


def test_scanner_reports_debt_bucket_for_allowlisted_tokens() -> None:
    """Bucket reporting remains available when both buckets are empty."""
    scanner = _scanner()
    by_bucket = scanner.allowlist_by_bucket()

    assert set(by_bucket) == {
        "LEAGUE_PULSE_PHASE_1_DEBT",
        "WHAT_CHANGED_GOVERNANCE_DEBT",
    }
    assert set(by_bucket["LEAGUE_PULSE_PHASE_1_DEBT"]) == set(
        scanner.LEAGUE_PULSE_PHASE_1_DEBT
    )
    assert set(by_bucket["WHAT_CHANGED_GOVERNANCE_DEBT"]) == set(
        scanner.WHAT_CHANGED_GOVERNANCE_DEBT
    )


def test_league_pulse_phase_1_debt_is_empty_at_t4_closeout() -> None:
    """The final No-Verdict cordon is enforcing across both buckets."""
    scanner = _scanner()

    assert scanner.LEAGUE_PULSE_PHASE_1_DEBT == []
    assert scanner.WHAT_CHANGED_GOVERNANCE_DEBT == []
    assert scanner.KNOWN_DEBT_ALLOWLIST == []
