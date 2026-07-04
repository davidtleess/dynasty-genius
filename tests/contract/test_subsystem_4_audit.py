"""Subsystem 4 audit contracts (§6.3, §8.8, §11)."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
from pathlib import Path

from pydantic import BaseModel

from src.dynasty_genius.eval import backtest_mock_draft as bmd
from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import CollegeProspectBridge

REPO_ROOT = Path(__file__).resolve().parents[2]

# NOTE (2026-05-30, David-authorized rescope — Harness Trust Completion spec §1.1):
# The §11.1 byte-lock on Phase 10/11 files was a BUILD-DURATION guardrail for S4
# ("inviolate for the duration of S4 work") and EXPIRED when S4 merged to main
# (95345ea). The sanctioned Harness Trust Completion initiative now legitimately
# modifies those files, so the 6 harness-trust-owned files were removed from this
# byte-baseline. The 2 Phase-10/11 files harness-trust does NOT touch remain locked.
#
# ADDENDUM (2026-05-30, David-authorized — Harness Trust Step-5b.2): the original
# rescope kept scripts/run_backtest.py locked on the assumption harness-trust would
# not touch the CLI entrypoint. Step-5b.2 (deterministic --id-map-csv G3 join) now
# legitimately modifies it, so scripts/run_backtest.py is released here under the
# same justification as the 6 engine files. backtest_report.py remains locked
# (untouched). ALL permanent guardrails below (S4-module isolation, S3 byte-locks,
# AST anti-laundering, eval allowlist, banned-language/decision_supported, Engine
# A/B leakage wall) are UNCHANGED. These two are the only authorized edits to
# test_subsystem_4_*.
INVIOLATE_BASELINE_SHA256_A41E0C6 = {
    "src/dynasty_genius/eval/backtest_report.py": (
        "659da032440ac31498183486ee08b2f9fb938043ff0ea0356afd555711c9d49a"
    ),
}

# ADDENDUM (2026-06-02, David-authorized — S3 Task-10A 2025-registry curation):
# The byte baseline for college_prospect_identity.py is refreshed to its post-Task-10A
# state. This file is an S3-OWNED module, and Task-10A is sanctioned S3 work (spec
# docs/superpowers/specs/2026-06-01-s3-task10a-2025-registry-curation-design.md). Two
# legitimate S3-owned edits land here:
#   1. f4d7685 — ingest_fixture accepts a bare-list Task-10A fixture (Task-4 compat). This
#      edit shipped WITHOUT refreshing this baseline, leaving the byte-lock stale at HEAD
#      (caught by this audit during the Task-5 full-suite run, 2026-06-02).
#   2. Task-5 review-edge closure — promote_review_candidate now closes an additional
#      review edge on an idempotent same-decision rerun (the Jaylin Lane two-edge case).
# This refresh re-pins college_prospect_identity.py ONLY. The byte-lock itself remains a
# PERMANENT guardrail; every other S3 inviolate artifact (the two _runs registries, the
# alias bridge, the resolver, identity/__init__.py) is UNCHANGED.
S3_INVIOLATE_SHA256 = {
    "app/data/identity/_runs/prospect_registry.json": (
        "d779e617fc62041955aee53ef371efedc418f1aac8212b7518f852d75a1ad823"
    ),
    "app/data/identity/_runs/composite_registry.json": (
        "60037ccb89d11f94514a0462ef3d7a12f2f1208ed57a6bd6524a970ae7c15a42"
    ),
    "app/data/prospect_alias_bridge.json": (
        "85008911259a9af4a71aa1f800393ccbee656450c16dc87116c6a493fb5d5675"
    ),
    "src/dynasty_genius/adapters/prospect_identity_resolver.py": (
        "faa141095b5f52ee237df29bb31cf6b85f697de93361452560a5fdd5f16d7663"
    ),
    "src/dynasty_genius/identity/__init__.py": (
        "7f458537b7d788fbdf6dd8c270823efa36cd32a49d682180e1f2657a294eb291"
    ),
    # Refreshed 2026-06-02 (David-authorized — see ADDENDUM above): f4d7685 compat +
    # Task-5 review-edge closure. Prior baseline: 7b78a7c46ddb53bb735c40eb1dc57c9966ecf731afc656bd1743ee25b08a90f6
    "src/dynasty_genius/identity/college_prospect_identity.py": (
        "f6fd6571b53bab1ba3756936ca9f4e1680463989c646dbcb60f6537dd96f0067"
    ),
}

# ADDENDUM (2026-05-31, David-authorized — Task B Subpopulation/Axis-of-Edge Study):
# subpopulation_landscape.py is added to AUTHORIZED_EVAL_FILES below. It is a
# deliberate, dual-CLEARED, model-blind, descriptive/diagnostic eval module per spec
# docs/superpowers/specs/2026-05-31-subpopulation-axis-of-edge-study-design.md (11e3c2d)
# and plan docs/superpowers/plans/2026-05-31-subpopulation-axis-of-edge-study.md
# (cd8f2b8). This EXTENDS the authorized set only; the exact-set allowlist semantics
# are preserved (any other new, unlisted eval file still fails this audit). All
# permanent S4 guardrails remain UNCHANGED: S4-module isolation, S3 byte-locks, AST
# anti-laundering, mock/market isolation, banned-language/decision_supported, and the
# Engine A/B leakage wall.
# ADDENDUM (2026-06-13, David-authorized — Step 0.5 Unified Composite Validation Gate):
# composite_gate.py is added to AUTHORIZED_EVAL_FILES below. It is a deliberate,
# dual-CLEARED, model-blind validity-gate module (pure per-fold predicates + the
# recency-aware compute_model_status; no market/G3 coupling, no Engine A/B feature or
# training change). This EXTENDS the authorized set only; the exact-set allowlist
# semantics are preserved (any other new, unlisted eval file still fails this audit).
# ADDENDUM (2026-06-23, David-authorized — Gate-4 Divergence-Edge Validation):
# gate4_divergence_edge.py is added to AUTHORIZED_EVAL_FILES below. It is a deliberate,
# dual-CLEARED, pure (no DB/file/network I/O, no model call) validation engine per the
# pre-registered spec docs/superpowers/specs/2026-06-23-gate4-divergence-edge-validation-design.md
# (84531dc). Validation-study only: no Engine A/B feature or training change, no PVO/
# scoring change, no product/UI change, market data overlay-only, decision_supported=False.
# This EXTENDS the authorized set only; the exact-set allowlist semantics are preserved
# (any other new, unlisted eval file still fails this audit). All permanent S4 guardrails
# remain UNCHANGED: S4-module isolation, S3 byte-locks, AST anti-laundering, mock/market
# isolation, banned-language/decision_supported, and the Engine A/B leakage wall.
#
# ADDENDUM (2026-07-03, David-authorized — BUILD-4 T3 Superflex-QB candidate validation):
# qb_v3_walk_forward.py is added to AUTHORIZED_EVAL_FILES below. It is a pre-registered
# diagnostic/eval module per the ratified BUILD-4 spec
# docs/superpowers/specs/2026-07-03-build4-superflex-qb-design.md (df64699): the qb_v3
# classification walk-forward validation driver. No Engine A/B active artifact change,
# no PVO/scoring/UI change, market wall unchanged, decision_supported=False throughout.
# This EXTENDS the authorized set only; the exact-set allowlist semantics are preserved
# (any other new, unlisted eval file still fails this audit).
AUTHORIZED_EVAL_FILES = {
    "__init__.py",
    "backtest_artifact.py",
    "backtest_harness.py",
    "backtest_metrics.py",
    "backtest_mock_draft.py",
    "backtest_report.py",
    "composite_gate.py",
    "draft_capital_bakeoff.py",
    "draft_capital_manifest.py",
    "draft_class_loocv.py",
    "gate4_divergence_edge.py",
    "market_snapshot_store.py",
    "model_card.py",
    "qb_v3_walk_forward.py",
    "subpopulation_landscape.py",
    "te_archetype_bakeoff.py",
    "te_regularization_bakeoff.py",
    "te_role_risk_experiment.py",
}

AST_AUDIT_SCAN_ROOTS = (
    Path("src/dynasty_genius/mock_consensus"),
    Path("src/dynasty_genius/scoring"),
    Path("src/dynasty_genius/models"),
    Path("src/dynasty_genius/pvo_assembler.py"),
    Path("src/dynasty_genius/trade_lab"),
    Path("src/dynasty_genius/adapters"),
    Path("src/dynasty_genius/pipelines"),
    Path("src/dynasty_genius/decision_logic"),
    Path("src/dynasty_genius/valuation"),
    Path("src/dynasty_genius/sources"),
    Path("app/services"),
)

BANNED_IMPORT_MODULES = {
    "dynasty_genius.eval.backtest_mock_draft",
    "src.dynasty_genius.eval.backtest_mock_draft",
    "dynasty_genius.identity.prospect_nfl_bridge",
    "src.dynasty_genius.identity.prospect_nfl_bridge",
}
MOCK_CONSENSUS_BANNED_IMPORT_PREFIXES = (
    "dynasty_genius.models.engine_a",
    "src.dynasty_genius.models.engine_a",
    "dynasty_genius.models.engine_b",
    "src.dynasty_genius.models.engine_b",
    "dynasty_genius.scoring",
    "src.dynasty_genius.scoring",
)
BANNED_S4_ARTIFACT_STRINGS = (
    "backtest_mock_draft",
    "backtest_a_result",
    "backtest_b_abstain",
)
BANNED_MARKET_FIELD_FRAGMENTS = (
    "adp",
    "ktc",
    "fantasycalc",
    "market_value",
    "market_overlay",
    "draft_selection_pct",
    "drafts_selected_in",
    "dynasty_nerds",
)
BANNED_DECISION_FIELDS = {"action", "verdict", "dynasty_tier", "confidence"}

UUID_A = "cpr_14000000-0000-4000-8000-000000000001"
UUID_B = "cpr_14000000-0000-4000-8000-000000000002"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _python_files_for_roots(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        full = REPO_ROOT / root
        if full.is_file() and full.suffix == ".py":
            files.append(full)
        elif full.is_dir():
            files.extend(path for path in full.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def _round_for_pick(pick_no: int | None) -> int | None:
    if pick_no is None:
        return None
    if pick_no <= 32:
        return 1
    if pick_no <= 64:
        return 2
    if pick_no <= 105:
        return 3
    return min(7, ((pick_no - 1) // 32) + 1)


def _is_banned_import(module: str, *, path: Path) -> bool:
    if module in BANNED_IMPORT_MODULES:
        return True
    if "mock_consensus" not in path.parts:
        return False
    return any(
        module == prefix or module.startswith(f"{prefix}.")
        for prefix in MOCK_CONSENSUS_BANNED_IMPORT_PREFIXES
    )


def _consensus(prospect_uuid: str, projected_pick_median: float | None):
    return bmd.ProspectConsensus(
        prospect_uuid=prospect_uuid,
        projected_pick_median=projected_pick_median,
        projected_pick_iqr=4.0 if projected_pick_median is not None else None,
        projected_pick_min=(
            int(projected_pick_median) if projected_pick_median is not None else None
        ),
        projected_pick_max=(
            int(projected_pick_median) if projected_pick_median is not None else None
        ),
        n_sources=5 if projected_pick_median is not None else 2,
        n_unique_analysts=5 if projected_pick_median is not None else 2,
        snapshot_ids_used=[f"snapshot_{prospect_uuid[-4:]}"],
        staleness_days=1.0,
        abstention_tier="exact_pick" if projected_pick_median is not None else "abstain",
        abstention_reason=None if projected_pick_median is not None else "abstain",
    )


def _outcome(prospect_uuid: str, *, pick_no: int | None, position: str = "WR"):
    return bmd.RealizedOutcome(
        prospect_uuid=prospect_uuid,
        gsis_id=f"00-{prospect_uuid[-4:]}" if pick_no is not None else None,
        pfr_id=None,
        draft_year=2025,
        draft_pick_no=pick_no,
        draft_round=_round_for_pick(pick_no),
        nfl_team="TEN" if pick_no is not None else None,
        udfa=pick_no is None,
        unbridged_prospect=False,
        bridge_stale_warning=False,
        warnings=[],
        evidence_full_name=f"Prospect {prospect_uuid[-4:]}",
        evidence_position=position,
        evidence_college="Test U",
    )


def _joined_rows():
    return [
        (_consensus(UUID_A, 5.0), _outcome(UUID_A, pick_no=5, position="QB")),
        (_consensus(UUID_B, 48.0), _outcome(UUID_B, pick_no=40, position="WR")),
    ]


def _minimal_bridge() -> CollegeProspectBridge:
    return CollegeProspectBridge(
        metadata={"draft_year": 2025, "schema_version": "prospect_nfl_bridge_v1.0.0"},
        entries=[],
    )


def _join_diagnostics(*, reasons=None) -> bmd.JoinDiagnostics:
    return bmd.JoinDiagnostics.model_validate(
        {
            "hard_block_reasons": list(reasons or []),
            "review_queue_payload": [],
            "duplicate_gsis_ids_detected": [],
            "wrong_year_truth_collisions": [],
            "evidence_incomplete_uuids": [],
        }
    )


def _snapshot_coverage(**overrides) -> dict:
    coverage = {
        "total_snapshots_found": 1,
        "snapshots_used": 1,
        "leakage_excluded_snapshots": 0,
        "untrusted_excluded_snapshots": 0,
        "duplicate_pick_no_rejections": 0,
        "duplicate_prospect_uuid_rejections": 0,
        "content_hash_collisions": 0,
        "snapshot_ids_used": ["snapshot_a"],
        "metadata_tuple_keys_used": ["source|analyst|2025-04-01|v1"],
        "total_picks": 2,
        "draft_date_used": "2025-04-24",
        "draft_date_source": "nflreadr.draft_picks",
        "warnings": [],
    }
    coverage.update(overrides)
    return coverage


def _bridge_coverage(**overrides) -> dict:
    coverage = {
        "consensus_unbridged_count": 0,
        "confirmed_class_unbridged_count": 0,
        "orphan_bridges_detected": [],
    }
    coverage.update(overrides)
    return coverage


def _build_result(**overrides):
    kwargs = {
        "run_id": "task14_audit_run",
        "draft_year": 2025,
        "data_mode": "real",
        "draft_date": "2025-04-24",
        "draft_date_source": "nflreadr.draft_picks",
        "snapshots_coverage": _snapshot_coverage(),
        "bridge_coverage": _bridge_coverage(),
        "joined_outcomes": _joined_rows(),
        "join_diagnostics": _join_diagnostics(),
        "bridge": _minimal_bridge(),
        "n_prospects_total_in_class": 2,
    }
    kwargs.update(overrides)
    return bmd.build_backtest_a_result(**kwargs)


def _payload(result) -> dict:
    return result.model_dump(mode="json") if hasattr(result, "model_dump") else result


def _walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _banned_identity_fragments_in_text(text: str) -> list[str]:
    lower = text.lower()
    tokens = set(re.split(r"[^a-z0-9]+", lower))
    banned_identity_fragments = ("mock", *BANNED_MARKET_FIELD_FRAGMENTS)
    found = []
    for item in banned_identity_fragments:
        # 'adp' (the short market fragment) is matched as a discrete TOKEN so the
        # draft-DATA library name nflreadpy — which merely contains the substring
        # 'adp' — is not a false positive. Real ADP field names (adp, player_adp,
        # adp_value) tokenize to a standalone 'adp' and are still caught. 'mock'
        # and the multi-char market fragments stay substring matches so partial
        # leaks (e.g. player_market_value) are still flagged — tighten-preserving.
        matched = ("adp" in tokens) if item == "adp" else (item in lower)
        if matched:
            found.append(item)
    return found


def test_adp_market_fragment_detection_is_token_aware_without_weakening_others():
    assert _banned_identity_fragments_in_text("adp") == ["adp"]
    assert _banned_identity_fragments_in_text("player_adp") == ["adp"]
    assert _banned_identity_fragments_in_text("adp_value") == ["adp"]
    assert _banned_identity_fragments_in_text("adp_rank") == ["adp"]

    assert _banned_identity_fragments_in_text("nflreadpy") == []
    assert _banned_identity_fragments_in_text("readptable") == []

    assert "market_value" in _banned_identity_fragments_in_text("market_value")
    assert "ktc" in _banned_identity_fragments_in_text("ktc")
    assert "mock" in _banned_identity_fragments_in_text("synthetic mock fixture")


def test_phase_10_11_12_inviolate_paths_byte_unchanged():
    observed = {
        rel_path: _sha256(REPO_ROOT / rel_path)
        for rel_path in INVIOLATE_BASELINE_SHA256_A41E0C6
    }

    assert observed == INVIOLATE_BASELINE_SHA256_A41E0C6


def test_s3_inviolate_artifacts_byte_unchanged():
    existing_baselines = {
        rel_path: expected_hash
        for rel_path, expected_hash in S3_INVIOLATE_SHA256.items()
        if (REPO_ROOT / rel_path).exists()
    }
    assert existing_baselines, "S3 byte-check requires at least one tracked artifact"
    observed = {
        rel_path: _sha256(REPO_ROOT / rel_path) for rel_path in existing_baselines
    }

    assert observed == existing_baselines


def test_eval_directory_contains_only_authorized_files():
    actual = {
        path.name
        for path in (REPO_ROOT / "src/dynasty_genius/eval").iterdir()
        if path.is_file() and path.suffix == ".py"
    }

    assert actual == AUTHORIZED_EVAL_FILES


def _scan_file_for_banned_imports(tree: ast.AST, path: Path) -> list[str]:
    """Collect banned-import / banned-string failures for one parsed file.

    For ``ImportFrom`` nodes the imported *names* are also checked against the
    banned set (combined as ``module.name``), so the
    ``from src.dynasty_genius.eval import backtest_mock_draft`` form cannot evade
    the reverse-import guard (U2 hardening).
    """
    failures: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_banned_import(alias.name, path=path):
                    failures.append(f"{path}:{node.lineno} import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_banned_import(module, path=path):
                failures.append(f"{path}:{node.lineno} from {module}")
            else:
                for alias in node.names:
                    full = f"{module}.{alias.name}" if module else alias.name
                    if _is_banned_import(full, path=path):
                        failures.append(
                            f"{path}:{node.lineno} from {module} import {alias.name}"
                        )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "mock_consensus" in path.parts:
                continue
            for banned in BANNED_S4_ARTIFACT_STRINGS:
                if banned in node.value:
                    failures.append(f"{path}:{node.lineno} string {banned!r}")
    return failures


def test_no_s4_imports_in_production_paths():
    failures: list[str] = []
    for path in _python_files_for_roots(AST_AUDIT_SCAN_ROOTS):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        failures.extend(_scan_file_for_banned_imports(tree, path))

    assert failures == []


def test_reverse_import_guard_catches_backtest_import_in_every_form():
    """U2 hardening: a ``mock_consensus`` file importing ``backtest_mock_draft``
    must be caught in EVERY syntactic form, including the
    ``from <package> import <module>`` form that evades a module-only check."""
    mock_consensus_path = Path("src/dynasty_genius/mock_consensus/consensus_math.py")
    for snippet in (
        "import src.dynasty_genius.eval.backtest_mock_draft",
        "import dynasty_genius.eval.backtest_mock_draft",
        "from src.dynasty_genius.eval.backtest_mock_draft import aggregate_per_prospect",
        "from src.dynasty_genius.eval import backtest_mock_draft",
        "from dynasty_genius.eval import backtest_mock_draft",
    ):
        tree = ast.parse(snippet)
        assert _scan_file_for_banned_imports(tree, mock_consensus_path), (
            f"reverse-import guard failed to catch: {snippet!r}"
        )


def test_mock_data_and_market_field_isolation():
    bridge_text = (REPO_ROOT / "src/dynasty_genius/identity/prospect_nfl_bridge.py").read_text(
        encoding="utf-8"
    )
    assert _banned_identity_fragments_in_text(bridge_text) == []

    s4_models = [
        value
        for _name, value in vars(bmd).items()
        if inspect.isclass(value)
        and issubclass(value, BaseModel)
        and value.__module__ == bmd.__name__
    ]
    leaked_fields = []
    for model in s4_models:
        for field_name in model.model_fields:
            lower = field_name.lower()
            # Market-field fragments only (NOT "mock": "mock" is legitimate in
            # backtest_mock_draft model names, e.g. MockSnapshotMetadata.mock_version;
            # it is banned only in the prospect_nfl_bridge.py source text above).
            if any(fragment in lower for fragment in BANNED_MARKET_FIELD_FRAGMENTS):
                leaked_fields.append(f"{model.__name__}.{field_name}")

    assert leaked_fields == []


def test_no_banned_david_facing_decision_fields_in_s4_outputs():
    payloads = [
        _payload(_build_result()),
        bmd.run_backtest_b(upstream_run_id="backtest_a_probe"),
    ]
    banned_paths: list[str] = []

    def visit(value, path: str = "$"):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in BANNED_DECISION_FIELDS:
                    banned_paths.append(f"{path}.{key}")
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    for payload in payloads:
        visit(payload)

    assert banned_paths == []


def test_decision_supported_recursively_absent_or_false_on_s4_surfaces():
    payloads = [
        _payload(_build_result()),
        bmd.run_backtest_b(upstream_run_id="backtest_a_probe"),
    ]
    true_paths: list[str] = []

    def visit(value, path: str = "$"):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "decision_supported" and child is not False:
                    true_paths.append(f"{path}.{key}={child!r}")
                visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    for payload in payloads:
        visit(payload)

    assert true_paths == []


def test_coverage_matrix_reconciles_all_section_4_5_rejection_buckets(tmp_path: Path):
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()

    def snapshot(
        source_label: str,
        *,
        published_date: str = "2025-04-20",
        parse_status: str = "complete",
        picks: list[dict] | None = None,
    ) -> dict:
        return {
            "metadata": {
                "source_url": f"https://example.test/{source_label}",
                "source_label": source_label,
                "analyst": f"{source_label}_analyst",
                "mock_version": "v1",
                "published_date": published_date,
                "fetched_at": "2025-04-20T12:00:00Z",
                "content_hash": f"hash_{source_label}",
                "parser_version": "fixture_v1",
                "parse_status": parse_status,
                "draft_year": 2025,
            },
            "picks": picks
            or [
                {
                    "pick_no": 1,
                    "prospect_uuid": UUID_A,
                }
            ],
        }

    valid_snapshot = snapshot("source_a")
    duplicate_pick_snapshot = snapshot(
        "source_b",
        picks=[
            {"pick_no": 2, "prospect_uuid": UUID_A},
            {"pick_no": 2, "prospect_uuid": UUID_B},
        ],
    )
    untrusted_snapshot = snapshot("source_c", parse_status="untrusted")
    leakage_snapshot = snapshot("source_d", published_date="2025-04-25")

    for filename, payload in {
        "valid.json": valid_snapshot,
        "duplicate_pick.json": duplicate_pick_snapshot,
        "untrusted.json": untrusted_snapshot,
        "leakage.json": leakage_snapshot,
    }.items():
        (snapshots_dir / filename).write_text(json.dumps(payload), encoding="utf-8")

    _normalized, coverage = bmd.ingest_snapshots(
        snapshots_dir=snapshots_dir,
        s3_registry=CollegeProspectRegistry(),
        include_untrusted=False,
        draft_date="2025-04-24",
    )

    accounted = (
        coverage["snapshots_used"]
        + coverage["leakage_excluded_snapshots"]
        + coverage["untrusted_excluded_snapshots"]
        + coverage["duplicate_pick_no_rejections"]
        + coverage["duplicate_prospect_uuid_rejections"]
        + coverage["content_hash_collisions"]
    )
    assert accounted == coverage["total_snapshots_found"]


def test_artifact_acceptance_criteria_failed_emits_section_6_3_hard_blocks():
    payload = _payload(
        _build_result(
            join_diagnostics=_join_diagnostics(reasons=["evidence_snapshot_missing"]),
            bridge_coverage=_bridge_coverage(
                consensus_unbridged_count=1,
                confirmed_class_unbridged_count=2,
                orphan_bridges_detected=[
                    {"prospect_uuid": UUID_A, "reason": "not_in_registry"}
                ],
            ),
        )
    )

    assert payload["metrics"] is None
    assert payload["acceptance_criteria_failed"] == [
        "evidence_snapshot_missing",
        "consensus_unbridged",
        "confirmed_class_unbridged",
        "orphan_bridges_detected",
    ]


def test_spec_documents_section_6_3_acceptance_criteria_and_failure_emission():
    spec = (
        REPO_ROOT
        / "docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md"
    ).read_text(encoding="utf-8")

    assert "### 6.3 Minimum evidence criteria to evaluate Backtest A" in spec
    assert "acceptance_criteria_failed" in spec


def test_artifact_emits_three_segmented_unbridged_counts():
    payload = _payload(
        _build_result(
            bridge_coverage=_bridge_coverage(
                consensus_unbridged_count=1,
                confirmed_class_unbridged_count=2,
                orphan_bridges_detected=[
                    {"prospect_uuid": UUID_A, "reason": "not_in_registry"}
                ],
            )
        )
    )

    assert payload["coverage"]["consensus_unbridged_count"] == 1
    assert payload["coverage"]["confirmed_class_unbridged_count"] == 2
    assert payload["coverage"]["orphan_bridges_detected"] == [
        {"prospect_uuid": UUID_A, "reason": "not_in_registry"}
    ]


def test_artifact_emits_metric_universe_tracked_confirmed():
    payload = _payload(_build_result())

    assert payload["metric_universe"] == "tracked_confirmed_prospect_universe"


def test_normalize_team_code_equivalence_classes():
    equivalence_classes = [
        ("OAK", "LVR"),
        ("SDG", "LAC"),
        ("LAR", "LA"),
        ("WAS", "WSH"),
    ]

    for left, right in equivalence_classes:
        assert bmd.normalize_team_code(left) == bmd.normalize_team_code(right)


def test_artifact_metadata_includes_team_code_normalization_version():
    payload = _payload(_build_result())

    assert payload["metadata"]["team_code_normalization_version"] == (
        bmd.TEAM_CODE_NORMALIZATION_VERSION
    )


def test_artifact_metadata_includes_round_bucket_rounding_policy():
    payload = _payload(_build_result())

    assert payload["metadata"]["round_bucket_rounding_policy"] == "round_half_up"


def test_artifact_emits_selection_bias_caveat_with_constitution_citation():
    payload = _payload(_build_result())

    assert "Truth over convenience" in payload["cohort_selection_bias_caveat"]
    assert "constitution" in payload["cohort_selection_bias_caveat"].lower()
