"""T1 RED: No-Verdict scanner for league_opportunity + League Pulse debt.

These tests define the scanner contract only. T1 GREEN should add the scanner
implementation and exact known-debt allowlist without changing producer/API/FE
semantics yet. The allowlist-empty assertion is intentionally skipped until T4
closeout, when the semantic reconciliation and generated clients have landed.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest


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
    """The temporary allowlist must be real inventory, not an empty or broad rule."""
    scanner = _scanner()

    entries = {
        (entry.path, entry.token, entry.reason)
        for entry in scanner.KNOWN_DEBT_ALLOWLIST
    }

    expected_entries = {
        # T2 removed the producer/DTO/assembler recommendation-language tokens
        # (_select_recommended_drop, LeaguePulseRecommendedDrop, recommended_drop);
        # the sole surviving legacy reference is the T4-removed v1-compat shim.
        (
            "app/api/routes/league_pulse_v1_compat.py",
            "recommended_drop",
            "transitional stale league_opportunity.v1 compatibility read; removed at Phase 1 T4 when v1 support is dropped",
        ),
        (
            "src/dynasty_genius/league_opportunity_map.py",
            "WAIVER_CANDIDATE",
            "preexisting action-shaped card type renamed by Phase 1 T3",
        ),
        (
            "src/dynasty_genius/league_opportunity_map.py",
            "opportunity_score",
            "preexisting action-order score renamed by Phase 1 T3",
        ),
        # openapi.json regenerated to v2 in T2 → its LeaguePulseRecommendedDrop /
        # recommended_drop / recommended_drops entries are gone (no longer real
        # findings). The still-stale generated FE clients (types.gen/zod.gen,
        # node codegen) remain T4 and are still pinned below.
        (
            "frontend/src/lib/api/types.gen.ts",
            "recommended_drop",
            "preexisting generated client debt removed by Phase 1 T4",
        ),
        (
            "frontend/src/lib/api/zod.gen.ts",
            "recommended_drop",
            "preexisting generated validator debt removed by Phase 1 T4",
        ),
        (
            "frontend/src/league-pulse/OpportunityCards.tsx",
            "recommended_drop",
            "preexisting visible label debt removed by Phase 1 T4",
        ),
    }

    assert expected_entries <= entries
    assert scanner.KNOWN_DEBT_ALLOWLIST
    assert all(entry.reason.strip() for entry in scanner.KNOWN_DEBT_ALLOWLIST)
    assert all("*" not in entry.path for entry in scanner.KNOWN_DEBT_ALLOWLIST)


def test_current_phase1_surfaces_scan_clean_after_exact_known_debt_allowlist() -> None:
    """Current debt is allowed only because each known occurrence is pinned exactly."""
    scanner = _scanner()
    current_surfaces = [
        Path("src/dynasty_genius/league_opportunity_map.py"),
        Path("app/api/routes/league_pulse_models.py"),
        Path("app/api/routes/league_pulse_assembler.py"),
        Path("app/api/routes/league_pulse_v1_compat.py"),
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
    """T4 empties only League Pulse debt; What-Changed own debt remains ticketed."""
    scanner = _scanner()

    league_pulse = set(scanner.LEAGUE_PULSE_PHASE_1_DEBT)
    what_changed = set(scanner.WHAT_CHANGED_GOVERNANCE_DEBT)
    known = set(scanner.KNOWN_DEBT_ALLOWLIST)

    assert league_pulse
    assert what_changed
    assert league_pulse.isdisjoint(what_changed)
    assert known == league_pulse | what_changed


def test_what_changed_own_debt_bucket_contains_only_independent_tripwire_tokens() -> None:
    """What-Changed's own recommendation-language debt is ticketed separately."""
    scanner = _scanner()

    what_changed_entries = {
        (entry.path, entry.token) for entry in scanner.WHAT_CHANGED_GOVERNANCE_DEBT
    }
    what_changed_tokens = {token for _, token in what_changed_entries}

    assert what_changed_tokens == {
        "promote_recommended",
        "recommendation_reasons",
    }
    assert {
        ("src/dynasty_genius/what_changed/report.py", "promote_recommended"),
        ("app/api/routes/league_what_changed_models.py", "promote_recommended"),
        ("app/api/routes/league_what_changed_models.py", "recommendation_reasons"),
        ("frontend/openapi.json", "promote_recommended"),
        ("frontend/openapi.json", "recommendation_reasons"),
        ("frontend/src/lib/api/types.gen.ts", "promote_recommended"),
        ("frontend/src/lib/api/types.gen.ts", "recommendation_reasons"),
        ("frontend/src/lib/api/zod.gen.ts", "promote_recommended"),
        ("frontend/src/lib/api/zod.gen.ts", "recommendation_reasons"),
    } <= what_changed_entries

    assert all("recommended_drops" != token for _, token in what_changed_entries)
    assert all("recommended_drop_name" != token for _, token in what_changed_entries)
    assert all("opportunity_score" != token for _, token in what_changed_entries)


def test_what_changed_consumes_league_opportunity_renames_in_league_pulse_bucket() -> None:
    """What-Changed consumption of league_opportunity fields moves with Phase 1."""
    scanner = _scanner()

    league_pulse_entries = {
        (entry.path, entry.token) for entry in scanner.LEAGUE_PULSE_PHASE_1_DEBT
    }

    assert {
        ("src/dynasty_genius/what_changed/report.py", "recommended_drop"),
        ("src/dynasty_genius/what_changed/report.py", "recommended_drop_name"),
        ("src/dynasty_genius/what_changed/report.py", "opportunity_score"),
        ("app/api/routes/league_what_changed_models.py", "recommended_drop_name"),
        ("app/api/routes/league_what_changed_models.py", "opportunity_score"),
        ("frontend/openapi.json", "recommended_drop_name"),
        ("frontend/openapi.json", "opportunity_score"),
        ("frontend/src/lib/api/types.gen.ts", "recommended_drop_name"),
        ("frontend/src/lib/api/types.gen.ts", "opportunity_score"),
        ("frontend/src/lib/api/zod.gen.ts", "recommended_drop_name"),
        ("frontend/src/lib/api/zod.gen.ts", "opportunity_score"),
    } <= league_pulse_entries


def test_scanner_reports_debt_bucket_for_allowlisted_tokens() -> None:
    """Allowlisted debt can be reported by bucket without claiming full generated-client zero."""
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


def test_allowlist_empty_assertion_is_deferred_to_t4_closeout() -> None:
    """T4 flips this to enforce only the Phase 1 bucket; What-Changed remains ticketed."""
    pytest.skip("Phase 1 T4 closeout flips this to assert LEAGUE_PULSE_PHASE_1_DEBT == []")

    scanner = _scanner()
    assert scanner.LEAGUE_PULSE_PHASE_1_DEBT == []
