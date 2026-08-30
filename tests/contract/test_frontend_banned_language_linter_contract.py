from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Literal, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPO_ROOT / "frontend"
VOCABULARY_PATH = FRONTEND_ROOT / "src" / "shell" / "banned_vocabulary.json"
SCANNER_PATH = FRONTEND_ROOT / "scripts" / "check-banned-language.mjs"
PACKAGE_JSON = FRONTEND_ROOT / "package.json"

FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "frontend_banned_language"
MUST_TRIP_FIXTURE = FIXTURE_ROOT / "must_trip"
MUST_NOT_TRIP_FIXTURE = FIXTURE_ROOT / "must_not_trip"

Expected = Literal["pass", "fail", "out_of_scope"]


class FalsificationRow(TypedDict):
    row_id: str
    expected: Expected
    fixture: str | None
    rationale: str


# Matrix comes first by design: reviewers challenge these rows before GREEN review.
#
# DG-104 re-scope (David's ruling 2026-08-29, verbatim in DG091-DESIGN-BRIEF.md /
# DG-094): the frontend speaks plain fantasy-football prose and MAY state overall
# recommendations. The scanner's presentation-language gates (banned_phrase,
# banned_standalone_word, CSS content scanning) died under that authority — every
# fixture that tripped them moved to must_not_trip/legal_voice/ and now MUST pass.
# The evidence-typing gates are measurement law and stay ARMED, in BOTH the
# forms that publish a typed field:
#   banned_field_render - rendering a typed verdict/dynasty_tier/confidence/
#       recommended_action/roster_action property in visible JSX.
#   banned_field_label  - publishing the same typed field as a label in visible
#       rendered text ("Confidence score: 82%"). Splitting at gate granularity
#       alone would have left the render gate bypassable by retyping the
#       machinery as prose; the label gate's phrase list is DERIVED from the
#       vocabulary (banned_phrases naming a humanized banned_fields entry), so
#       exactly "confidence score" / "dynasty tier" / "recommended action"
#       survive and every other phrase died with the presentation gate.
# The backend contract does not grow verdict fields; only the frontend's voice
# is freed.
FALSIFICATION_MATRIX: tuple[FalsificationRow, ...] = (
    {
        "row_id": "generated_types_may_declare_verdict_and_dynasty_tier",
        "expected": "pass",
        "fixture": "must_not_trip/generated-client/src/lib/api/types.gen.ts",
        "rationale": "Generated API typing/import surfaces are carved out; rendering is not.",
    },
    {
        "row_id": "generated_zod_may_declare_banned_shape_fields",
        "expected": "pass",
        "fixture": "must_not_trip/generated-client/src/lib/api/zod.gen.ts",
        "rationale": "Generated validators are not David-facing UI copy.",
    },
    {
        "row_id": "event_target_and_html_target_attribute_are_code_mechanics",
        "expected": "pass",
        "fixture": "must_not_trip/code-mechanics/TargetMechanics.tsx",
        "rationale": "React events and HTML attributes are not rendered decision language.",
    },
    {
        "row_id": "constitutional_metric_labels_are_allowed",
        "expected": "pass",
        "fixture": "must_not_trip/metrics/MetricLabels.tsx",
        "rationale": "Target Share, TPRR, and Air Yards Share are required football metrics.",
    },
    {
        "row_id": "trade_buttons_and_sleeper_status_are_allowed",
        "expected": "pass",
        "fixture": "must_not_trip/status/TradeStatus.tsx",
        "rationale": "User actions and external Sleeper states are factual UI, not model advice.",
    },
    {
        "row_id": "win_loss_record_copy_is_allowed",
        "expected": "pass",
        "fixture": "must_not_trip/league/WinLossRecord.tsx",
        "rationale": "League record copy is factual context, not a trade verdict.",
    },
    {
        "row_id": "banned_substrings_inside_nonvisible_attributes_are_allowed",
        "expected": "pass",
        "fixture": "must_not_trip/attributes/HiddenAttributes.tsx",
        "rationale": "className, data attributes, keys, and ids are not visible UI text.",
    },
    {
        "row_id": "surname_winston_does_not_match_win_boundary",
        "expected": "pass",
        "fixture": "must_not_trip/names/Winston.tsx",
        "rationale": (
            "Player-name copy is legal; the phrase gate that once needed word "
            "boundaries here died under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "vocabulary_artifact_does_not_trip_production_scan",
        "expected": "pass",
        "fixture": "must_not_trip/vocabulary/banned_vocabulary.json",
        "rationale": (
            "The scanner must exclude its own vocabulary artifact from production "
            "source scanning."
        ),
    },
    {
        "row_id": "net_wins_plural_does_not_match_net_win_phrase",
        "expected": "pass",
        "fixture": "must_not_trip/copy/NetWinsPlural.tsx",
        "rationale": (
            "Record copy is legal; the phrase gate that once needed boundary "
            "matching here died under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "standalone_tier_words_inside_compound_copy_do_not_trip",
        "expected": "pass",
        "fixture": "must_not_trip/copy/TierWordCompounds.tsx",
        "rationale": (
            "Compound football copy is legal; the standalone-word gate died "
            "under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "jsx_text_decision_phrases_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/BannedJsxText.tsx",
        "rationale": (
            "Sell now, Buy low, Strong Win, and Shop actively are plain "
            "fantasy-football prose under David's 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "visible_verdict_field_binding_fails",
        "expected": "fail",
        "fixture": "must_trip/fields/VerdictBinding.tsx",
        "rationale": "Rendering evaluation.verdict exposes a banned decision field.",
    },
    {
        "row_id": "visible_dynasty_tier_field_binding_fails",
        "expected": "fail",
        "fixture": "must_trip/fields/DynastyTierBinding.tsx",
        "rationale": "Rendering card.dynasty_tier exposes a banned rookie verdict field.",
    },
    {
        "row_id": "visible_confidence_field_binding_fails",
        "expected": "fail",
        "fixture": "must_trip/fields/ConfidenceBinding.tsx",
        "rationale": "Rendering rookie.confidence exposes unsupported confidence framing.",
    },
    {
        "row_id": "visible_recommended_action_field_binding_fails",
        "expected": "fail",
        "fixture": "must_trip/fields/RecommendedActionBinding.tsx",
        "rationale": "Specific decision-action fields are banned when rendered.",
    },
    {
        "row_id": "visible_roster_action_field_binding_fails",
        "expected": "fail",
        "fixture": "must_trip/fields/RosterActionBinding.tsx",
        "rationale": "Specific roster-action fields are banned when rendered.",
    },
    {
        "row_id": "typed_field_published_as_label_prose_fails",
        "expected": "fail",
        "fixture": "must_trip/fields/FieldLabelProse.tsx",
        "rationale": (
            "'Confidence score: 82%' / 'Dynasty tier: X' publish the same typed "
            "machinery the render gate bans, only spelled as prose. The repealed "
            "phrases in the same file (sell high, must start, strong win, buy "
            "low) must stay silent, so this row pins the split itself."
        ),
    },
    {
        "row_id": "plain_confidence_and_tier_prose_stays_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/PlainConfidenceProse.tsx",
        "rationale": (
            "The label gate is derived from field-naming phrases only: bare "
            "'confidence', 'second tier', 'verdict', and 'recommendation' are "
            "plain prose David green-lit and must not be re-blocked."
        ),
    },
    {
        "row_id": "bare_action_field_binding_is_allowed",
        "expected": "pass",
        "fixture": "must_not_trip/fields/FormActionBinding.tsx",
        "rationale": "Bare .action is unbounded and legitimate for form/UI mechanics.",
    },
    {
        "row_id": "aria_title_and_button_recommendation_copy_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/AccessibleBannedCopy.tsx",
        "rationale": (
            "Accessible labels and button text may carry recommendation prose "
            "under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "jsx_child_string_expression_recommendation_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/StringExpressionChild.tsx",
        "rationale": (
            "Visible JSX expression string literals may carry recommendation "
            "prose under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "visible_attribute_string_expression_recommendation_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/StringExpressionAttribute.tsx",
        "rationale": (
            "Visible JSX attribute expression string literals may carry "
            "recommendation prose under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "jsx_child_template_expression_recommendation_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/TemplateExpressionChild.tsx",
        "rationale": (
            "Visible JSX no-substitution template literals may carry "
            "recommendation prose under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "accept_this_trade_confirmation_dialog_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/ConfirmationDialog.tsx",
        "rationale": (
            "Confirmation-dialog copy no longer needs a suppression hatch; the "
            "phrase gate died under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "reasoned_tsx_suppression_hatch_allows_intentional_fire_point",
        "expected": "pass",
        "fixture": "must_not_trip/suppression/ReasonedSuppression.tsx",
        "rationale": (
            "A line-level banned-language-ok marker with a non-empty reason allows "
            "a documented intentional render of a banned field."
        ),
    },
    {
        "row_id": "empty_tsx_suppression_hatch_still_fails",
        "expected": "fail",
        "fixture": "must_trip/suppression/EmptySuppression.tsx",
        "rationale": (
            "Suppression markers require a non-empty reason; the hatch now guards "
            "the surviving banned_field_render gate."
        ),
    },
    {
        "row_id": "css_files_are_no_longer_scanned",
        "expected": "pass",
        "fixture": "must_not_trip/suppression/reasoned-content.css",
        "rationale": (
            "CSS content was only ever presentation copy; with the presentation "
            "gates repealed, .css files are outside the scanner's scope."
        ),
    },
    {
        "row_id": "must_start_deadline_copy_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/MustStartDeadline.tsx",
        "rationale": (
            "Lineup-deadline copy containing 'must start' is plain prose under "
            "the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "hardcoded_tier_ladder_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/TierLadder.tsx",
        "rationale": (
            "Elite/Starter/Depth/Bust ladder COPY is frontend voice, now free; a "
            "typed dynasty_tier FIELD render still fails the armed field gate."
        ),
    },
    {
        "row_id": "bare_starter_heading_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/BareStarterHeading.tsx",
        "rationale": (
            "The standalone-word gate died under the 2026-08-29 ruling; a bare "
            "tier word heading is legal copy."
        ),
    },
    {
        "row_id": "css_content_bust_now_legal",
        "expected": "pass",
        "fixture": "must_not_trip/legal_voice/bust-content.css",
        "rationale": (
            "CSS generated content is presentation copy; the gate that scanned "
            "it died under the 2026-08-29 ruling."
        ),
    },
    {
        "row_id": "single_hop_alias_rendering_is_out_of_scope_v1",
        "expected": "out_of_scope",
        "fixture": None,
        "rationale": "V1 structural gate is syntactic; alias/dataflow tracking is a documented gap.",
    },
)


def _rows(expected: Expected) -> list[FalsificationRow]:
    return [row for row in FALSIFICATION_MATRIX if row["expected"] == expected]


def _run_scanner(path: Path) -> subprocess.CompletedProcess[str]:
    assert SCANNER_PATH.exists(), (
        "Missing T6 scanner CLI: frontend/scripts/check-banned-language.mjs"
    )
    assert VOCABULARY_PATH.exists(), (
        "Missing T6 vocabulary artifact: frontend/src/shell/banned_vocabulary.json"
    )
    return subprocess.run(
        [
            "node",
            str(SCANNER_PATH),
            "--vocabulary",
            str(VOCABULARY_PATH),
            "--root",
            str(path),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_t6_falsification_matrix_covers_seeded_boundaries() -> None:
    row_ids = {row["row_id"] for row in FALSIFICATION_MATRIX}

    assert len(row_ids) == len(FALSIFICATION_MATRIX), "Matrix row ids must be unique"
    assert len(_rows("pass")) >= 8
    # DG-104: the presentation gates died under David's 2026-08-29 ruling, so the
    # only fail rows left are the armed evidence-typing gate (5 banned fields)
    # plus the empty-suppression hatch guard.
    assert len(_rows("fail")) >= 6
    assert {row["row_id"] for row in _rows("out_of_scope")} == {
        "single_hop_alias_rendering_is_out_of_scope_v1",
    }
    assert all(row["rationale"] for row in FALSIFICATION_MATRIX)


def test_t6_vocabulary_artifact_is_single_source_of_truth() -> None:
    # DG-104: the artifact is deliberately UNCHANGED. banned_phrases and
    # banned_standalone_words no longer drive the frontend scanner, but they
    # still bind the BACKEND evidence surfaces (app/api/routes/players.py
    # runtime suppression, scripts/validate_surface3_regen_integrity.py,
    # tests/test_counter_arguments.py) — backend machinery stays armed, so the
    # lists stay pinned here.
    vocabulary = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))

    assert set(vocabulary) == {
        "banned_phrases",
        "banned_fields",
        "banned_standalone_words",
    }
    assert vocabulary["banned_phrases"] == [
        "sell now",
        "shop actively",
        "buy now",
        "sell high",
        "buy low",
        "must add",
        "must draft",
        "must start",
        "strong win",
        "strong loss",
        "winning side",
        "losing side",
        "fade him",
        "accept this trade",
        "reject this trade",
        "recommended action",
        "recommend accept",
        "recommend reject",
        "should accept",
        "should reject",
        "confidence score",
        "dynasty tier",
        "side total",
        "net win",
        "net loss",
    ]
    assert vocabulary["banned_fields"] == [
        "verdict",
        "dynasty_tier",
        "confidence",
        "recommended_action",
        "roster_action",
    ]
    assert vocabulary["banned_standalone_words"] == [
        "elite",
        "starter",
        "depth",
        "bust",
    ]
    assert "action" not in vocabulary["banned_fields"]
    assert "confidence_band" not in vocabulary["banned_fields"]
    assert "confidence_interval" not in vocabulary["banned_fields"]
    assert "confidence_range" not in vocabulary["banned_fields"]


def test_t6_fixture_locations_are_test_only_and_complete() -> None:
    fixture_paths = [
        row["fixture"] for row in FALSIFICATION_MATRIX if row["fixture"] is not None
    ]

    assert fixture_paths
    for fixture_path in fixture_paths:
        path = FIXTURE_ROOT / fixture_path
        assert path.exists(), f"Missing T6 fixture for matrix row: {fixture_path}"

    assert not (FRONTEND_ROOT / "src" / "__fixtures__").exists(), (
        "Seeded banned fixtures must stay in tests/fixtures, not real frontend surfaces"
    )


def test_t6_package_script_wires_linter_into_frontend_checks() -> None:
    package_json = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

    assert package_json["scripts"]["banned-language"] == (
        "node scripts/check-banned-language.mjs"
    )
    assert "npm run banned-language" in package_json["scripts"]["gate"]


def test_t6_false_positive_fixtures_do_not_trip() -> None:
    for row in _rows("pass"):
        assert row["fixture"] is not None
        result = _run_scanner(FIXTURE_ROOT / row["fixture"])
        assert result.returncode == 0, (
            f"{row['row_id']} should pass.\nstdout:\n{result.stdout}\nstderr:\n"
            f"{result.stderr}"
        )


def test_t6_banned_language_fixtures_trip_with_deterministic_output() -> None:
    multi_finding_rows = 0

    for row in _rows("fail"):
        assert row["fixture"] is not None
        fixture = FIXTURE_ROOT / row["fixture"]
        result = _run_scanner(fixture)
        output = result.stdout + result.stderr
        lines = [line for line in output.splitlines() if line.strip()]

        assert result.returncode != 0, f"{row['row_id']} should fail"
        assert str(fixture.relative_to(REPO_ROOT)) in output
        assert lines == sorted(lines), "Scanner output must be deterministic and sorted"
        if len(lines) > 1:
            multi_finding_rows += 1

    # A one-element list is always sorted, so the assertion above proves nothing
    # unless at least one fail fixture emits several findings whose SOURCE order
    # differs from their sorted order. FieldLabelProse.tsx binds on lines 9 and
    # 10 precisely so ":10:" must sort ahead of ":9:".
    assert multi_finding_rows >= 1, (
        "Sortedness is unfalsifiable without a multi-finding fail fixture"
    )


def test_t6_scanner_fails_closed_on_parse_error(tmp_path: Path) -> None:
    malformed = tmp_path / "Malformed.tsx"
    malformed.write_text("export function Broken( { return <span>ok</span>; }\n")

    result = _run_scanner(malformed)
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "parse" in output.lower() or "scanner_error" in output.lower()
