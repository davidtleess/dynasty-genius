import copy
import json
from pathlib import Path

import pytest

from scripts.validate_surface3_regen_integrity import (
    IntegrityAuditError,
    validate_regen_integrity,
)

PHASE15_REPORT = "docs/validation/phase15-2026-rookie-rank-refresh.md"
PROSPECT_JSON = "resources/prospect_cards.json"
PROSPECT_JS = "resources/prospect_cards.js"
UNIVERSE_JSON = "app/data/valuation/universe_pvo_latest.json"
UNIVERSE_COVERAGE = "app/data/valuation/universe_pvo_coverage_latest.json"


def _write_json(root: Path, rel_path: str, payload: object) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _write_js(root: Path, payload: object) -> None:
    path = root / PROSPECT_JS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "/* synthetic prospect cards */\n"
        f"window.PROSPECT_CARDS = {json.dumps(payload, separators=(',', ':'))};\n"
    )


def _write_report(root: Path, text: str) -> None:
    path = root / PHASE15_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _prospect_cards() -> list[dict]:
    return [
        {
            "sleeper_id": "13269",
            "player_id": "fernando_mendoza_qb",
            "full_name": "Fernando Mendoza",
            "position": "QB",
            "dynasty_value_score": 85.14,
            "xvar": 10.31,
            "xvar_class_rank": 8,
            "dvs_class_rank": 5,
            "engine_used": "engine_a_rookie_forecast_ridge",
            "model_grade": "PROSPECT_D",
            "counter_argument": "Elite valuation assumes continued rushing.",
            "assembled_at": "2026-05-24T16:54:53+00:00",
            "source_versions": {"identity_source": "snapshot-a"},
            "source_season": None,
            "source_snapshot_captured_at": "2026-05-24T00:00:00+00:00",
            "lineage": {"identity_hash": "sha256:prospect"},
        },
        {
            "sleeper_id": "99999",
            "player_id": "stable_wr",
            "full_name": "Stable WR",
            "position": "WR",
            "dynasty_value_score": 70.0,
            "xvar": 2.0,
            "xvar_class_rank": 18,
            "dvs_class_rank": 20,
            "engine_used": "engine_a_rookie_forecast_ridge",
            "model_grade": "PROSPECT_C",
            "counter_argument": None,
            "assembled_at": "2026-05-24T16:54:54+00:00",
            "source_versions": {},
            "source_season": None,
            "source_snapshot_captured_at": "2026-05-24T00:00:00+00:00",
            "lineage": {"identity_hash": "sha256:stable"},
        },
    ]


def _universe_pvo() -> dict:
    return {
        "schema_version": "universe_pvo_batch.v1",
        "captured_at": "2026-05-24T17:00:00+00:00",
        "source_snapshot_captured_at": "2026-05-24T00:00:00+00:00",
        "players": [
            {
                "sleeper_player_id": "13269",
                "dg_player_id": "fernando_mendoza_qb",
                "captured_at": "2026-05-24T17:00:00+00:00",
                "pipeline_run_id": None,
                "player": {"full_name": "Fernando Mendoza", "position": "QB"},
                "valuation": {
                    "engine_path": "ENGINE_A",
                    "dynasty_value_score": 85.14,
                    "xvar": 10.31,
                    "model_grade": "PROSPECT_D",
                    "model_version": "engine_a_v3",
                    "decision_supported": False,
                },
                "dvs_engine": "A",
                "lineage": {"sleeper_snapshot_hash": "sha256:universe"},
            },
            {
                "sleeper_player_id": "88888",
                "dg_player_id": "active_rb",
                "captured_at": "2026-05-24T17:00:00+00:00",
                "pipeline_run_id": None,
                "player": {"full_name": "Active RB", "position": "RB"},
                "valuation": {
                    "engine_path": "ENGINE_B",
                    "dynasty_value_score": 72.0,
                    "xvar": 8.5,
                    "model_grade": "ACTIVE_B",
                    "model_version": "engine_b_v2",
                    "decision_supported": False,
                },
                "dvs_engine": "B",
                "lineage": {"sleeper_snapshot_hash": "sha256:universe"},
            },
        ],
    }


def _coverage() -> dict:
    return {
        "total_players": 2,
        "counts_by_engine_path": {"ENGINE_A": 1, "ENGINE_B": 1},
        "decision_supported_true_count": 0,
        "market_overlay_present_count": 0,
        "allowed_engine_routes": ["ENGINE_A", "ENGINE_B", "PRE_MODEL"],
        "rostered_skill_players_missing_route": [],
    }


def _add_surface3_keys(row: dict, *, counter_argument: str | None = None) -> None:
    row.update(
        {
            "counter_argument": counter_argument,
            "risk_flags": [],
            "top_drivers": ["age_not_near_position_cliff"],
            "caveats": ["synthetic caveat"],
            "draft_class": 2026,
            "nfl_draft_pick": 1,
            "nfl_draft_round": 1,
            "projection_1y": None,
            "projection_2y": None,
            "projection_3y": None,
        }
    )


def _artifact_payloads() -> tuple[dict[str, object], dict[str, object]]:
    prospect_pre = _prospect_cards()
    universe_pre = _universe_pvo()
    coverage_pre = _coverage()

    prospect_post = copy.deepcopy(prospect_pre)
    prospect_post[0]["counter_argument"] = (
        "Premium valuation assumes continued rushing."
    )
    prospect_post[0]["assembled_at"] = "2026-06-07T00:00:00+00:00"

    universe_post = copy.deepcopy(universe_pre)
    universe_post["captured_at"] = "2026-06-07T00:00:00+00:00"
    for row in universe_post["players"]:
        row["captured_at"] = "2026-06-07T00:00:00+00:00"
        row["pipeline_run_id"] = "surface3-test-run"
        _add_surface3_keys(
            row,
            counter_argument=(
                "Premium valuation assumes continued rushing."
                if row["sleeper_player_id"] == "13269"
                else None
            ),
        )

    return (
        {
            PROSPECT_JSON: prospect_pre,
            UNIVERSE_JSON: universe_pre,
            UNIVERSE_COVERAGE: coverage_pre,
            PHASE15_REPORT: (
                "# Phase 15 Refresh\n\n"
                "Generated at: 2026-05-24T17:00:00+00:00\n"
                "- 13269 counter_argument: Elite valuation assumes continued rushing.\n"
            ),
        },
        {
            PROSPECT_JSON: prospect_post,
            UNIVERSE_JSON: universe_post,
            UNIVERSE_COVERAGE: copy.deepcopy(coverage_pre),
            PHASE15_REPORT: (
                "# Phase 15 Refresh\n\n"
                "Generated at: 2026-06-07T00:00:00+00:00\n"
                "- 13269 counter_argument: Premium valuation assumes continued rushing.\n"
            ),
        },
    )


def _write_artifacts(root: Path, payloads: dict[str, object]) -> None:
    for rel_path, payload in payloads.items():
        if rel_path.endswith(".json"):
            _write_json(root, rel_path, payload)
        elif rel_path.endswith(".md"):
            _write_report(root, str(payload))
    _write_js(root, payloads[PROSPECT_JSON])


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    pre_payloads, post_payloads = _artifact_payloads()
    pre_root = tmp_path / "pre"
    post_root = tmp_path / "post"
    _write_artifacts(pre_root, pre_payloads)
    _write_artifacts(post_root, post_payloads)
    return pre_root, post_root


def _mutate_json(root: Path, rel_path: str, mutator) -> None:
    path = root / rel_path
    payload = json.loads(path.read_text())
    mutator(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    if rel_path == PROSPECT_JSON:
        _write_js(root, payload)


def test_integrity_audit_passes_for_only_allowlisted_surface3_regen_diffs(
    tmp_path: Path,
) -> None:
    pre_root, post_root = _roots(tmp_path)

    result = validate_regen_integrity(pre_root, post_root)

    assert result["status"] == "pass"
    assert result["checked_artifacts"] == [
        PROSPECT_JSON,
        PROSPECT_JS,
        UNIVERSE_JSON,
        UNIVERSE_COVERAGE,
        PHASE15_REPORT,
    ]


def test_integrity_audit_fails_on_model_field_value_drift(tmp_path: Path) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload["players"][0]["valuation"].update(
            {"dynasty_value_score": 86.0}
        ),
    )

    with pytest.raises(IntegrityAuditError, match="dynasty_value_score"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_key_set_closure_violation(tmp_path: Path) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload["players"][0].update({"unexpected_new_key": True}),
    )

    with pytest.raises(IntegrityAuditError, match="unexpected_new_key"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_prospect_identity_mismatch(
    tmp_path: Path,
) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        PROSPECT_JSON,
        lambda payload: payload[0].update({"sleeper_id": "changed"}),
    )

    with pytest.raises(IntegrityAuditError, match="identity"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_universe_identity_mismatch(
    tmp_path: Path,
) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload["players"][0].update({"dg_player_id": "changed"}),
    )

    with pytest.raises(IntegrityAuditError, match="identity"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_stable_provenance_drift(tmp_path: Path) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        PROSPECT_JSON,
        lambda payload: payload[0].update(
            {"source_versions": {"identity_source": "changed"}}
        ),
    )

    with pytest.raises(IntegrityAuditError, match="source_versions"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_when_js_payload_differs_from_json(
    tmp_path: Path,
) -> None:
    pre_root, post_root = _roots(tmp_path)
    js_path = post_root / PROSPECT_JS
    payload = json.loads((post_root / PROSPECT_JSON).read_text())
    payload[0]["full_name"] = "Wrong JS Payload"
    js_path.write_text(
        f"window.PROSPECT_CARDS = {json.dumps(payload, separators=(',', ':'))};\n"
    )

    with pytest.raises(IntegrityAuditError, match="prospect_cards.js"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_any_coverage_delta(tmp_path: Path) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_COVERAGE,
        lambda payload: payload.update({"decision_supported_true_count": 1}),
    )

    with pytest.raises(IntegrityAuditError, match="coverage"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_universe_top_level_new_none_key(
    tmp_path: Path,
) -> None:
    # Escape-hatch regression: a NEW top-level key whose value is None must not
    # slip past a value comparison (None == None).
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload.update({"surprise_top_key": None}),
    )

    with pytest.raises(IntegrityAuditError, match="surprise_top_key"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_duplicate_universe_identity(tmp_path: Path) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload["players"].append(copy.deepcopy(payload["players"][0])),
    )

    with pytest.raises(IntegrityAuditError, match="duplicate"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_duplicate_prospect_identity(tmp_path: Path) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        PROSPECT_JSON,
        lambda payload: payload.append(copy.deepcopy(payload[0])),
    )

    with pytest.raises(IntegrityAuditError, match="duplicate"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_non_cleaned_prospect_counter_argument_change(
    tmp_path: Path,
) -> None:
    # counter_argument may change only on the cleaned QB/TE ids; row 99999 is not one.
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        PROSPECT_JSON,
        lambda payload: payload[1].update({"counter_argument": "Unexpected drift."}),
    )

    with pytest.raises(IntegrityAuditError, match="counter_argument"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_report_extra_counter_argument_line(
    tmp_path: Path,
) -> None:
    # Escape-hatch regression: an added line containing 'counter_argument:' must
    # not slip past via substring filtering (line count changes).
    pre_root, post_root = _roots(tmp_path)
    path = post_root / PHASE15_REPORT
    path.write_text(
        path.read_text() + "- 99999 counter_argument: unrelated report drift.\n"
    )

    with pytest.raises(IntegrityAuditError, match="line count"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_report_extra_generated_at_line(
    tmp_path: Path,
) -> None:
    pre_root, post_root = _roots(tmp_path)
    path = post_root / PHASE15_REPORT
    path.write_text(path.read_text() + "Generated at: arbitrary extra generated line\n")

    with pytest.raises(IntegrityAuditError, match="line count"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_report_unrelated_line_drift(tmp_path: Path) -> None:
    # Same line count, but a non-timestamp / non-cleaned-row line changed.
    pre_root, post_root = _roots(tmp_path)
    path = post_root / PHASE15_REPORT
    path.write_text(path.read_text().replace("# Phase 15 Refresh", "# Tampered Heading"))

    with pytest.raises(IntegrityAuditError, match="line drift"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_report_wrong_row_mentions_cleaned_id(
    tmp_path: Path,
) -> None:
    # A non-cleaned-row line that merely MENTIONS a cleaned id in its text must
    # not be treated as a cleaned-row edit (id is parsed, not substring-matched).
    pre_root, post_root = _roots(tmp_path)
    path = post_root / PHASE15_REPORT
    path.write_text(
        path.read_text().replace(
            "- 13269 counter_argument: Premium valuation assumes continued rushing.",
            "- 99999 counter_argument: unrelated drift mentions 13269",
        )
    )

    with pytest.raises(IntegrityAuditError, match="line drift"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_malformed_prospect_shape(tmp_path: Path) -> None:
    # A malformed shape must fail through the HARD STOP path (IntegrityAuditError),
    # not crash with a raw AttributeError the CLI cannot catch.
    pre_root, post_root = _roots(tmp_path)
    (post_root / PROSPECT_JSON).write_text(json.dumps({"not": "a list"}))

    with pytest.raises(IntegrityAuditError, match="malformed"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_malformed_universe_players_shape(
    tmp_path: Path,
) -> None:
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload.update({"players": {"bad": "shape"}}),
    )

    with pytest.raises(IntegrityAuditError, match="malformed"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_report_cleaned_id_swap(tmp_path: Path) -> None:
    # Swapping the report row from one cleaned id to another is still drift.
    pre_root, post_root = _roots(tmp_path)
    path = post_root / PHASE15_REPORT
    path.write_text(
        path.read_text().replace(
            "- 13269 counter_argument: Premium valuation assumes continued rushing.",
            "- 13330 counter_argument: Premium valuation assumes continued rushing.",
        )
    )

    with pytest.raises(IntegrityAuditError, match="line drift"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_fails_on_banned_standalone_word_in_post_evidence(
    tmp_path: Path,
) -> None:
    # Spec §2.4/§6: emitted evidence text must carry zero banned standalone words
    # post-regen. counter_argument is an allowlisted-new universe key, so the shape
    # checks pass — only the banned-vocab scan catches it.
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload["players"][0].update(
            {"counter_argument": "Elite valuation assumes continued rushing."}
        ),
    )

    with pytest.raises(IntegrityAuditError, match="banned"):
        validate_regen_integrity(pre_root, post_root)


def test_integrity_audit_allows_word_boundary_false_positive_in_evidence(
    tmp_path: Path,
) -> None:
    # 'robust' contains the substring 'bust' but is not the standalone banned word.
    pre_root, post_root = _roots(tmp_path)
    _mutate_json(
        post_root,
        UNIVERSE_JSON,
        lambda payload: payload["players"][0].update(
            {"caveats": ["robust projection model"]}
        ),
    )

    result = validate_regen_integrity(pre_root, post_root)
    assert result["status"] == "pass"


def test_integrity_audit_fails_on_banned_word_in_report_counter_argument(
    tmp_path: Path,
) -> None:
    # The report cleaned-row counter_argument line is structurally allowed to edit,
    # but its evidence text must still be banned-vocab clean (spec §2.4/§6).
    pre_root, post_root = _roots(tmp_path)
    path = post_root / PHASE15_REPORT
    path.write_text(
        path.read_text().replace(
            "- 13269 counter_argument: Premium valuation assumes continued rushing.",
            "- 13269 counter_argument: Elite valuation assumes continued rushing.",
        )
    )

    with pytest.raises(IntegrityAuditError, match="banned"):
        validate_regen_integrity(pre_root, post_root)
