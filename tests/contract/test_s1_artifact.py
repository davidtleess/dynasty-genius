"""S1 overlay artifact writer contract tests (spec v4 T6)."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from src.dynasty_genius.mock_consensus.aggregate import ConsensusRecord
from src.dynasty_genius.mock_consensus.artifact import (
    build_mock_consensus_artifact,
    write_mock_consensus_artifact,
)


def _exact_record() -> ConsensusRecord:
    return ConsensusRecord(
        prospect_uuid="cpr_20000000-0000-4000-8000-000000000001",
        n_unique_analysts=5,
        n_sources=3,
        projected_pick_median=13.0,
        projected_pick_iqr=5.0,
        projected_pick_mad=2.0,
        projected_pick_min=10,
        projected_pick_max=17,
        disagreement_flag=False,
        staleness_days=30,
        round_tier="R1.late",
        abstention_tier="exact_pick",
        internal_diagnostic=True,
        raw_row_hashes_used=("hash_a", "hash_b", "hash_c", "hash_d", "hash_e"),
    )


def _walk_dicts(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _walk_strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def test_writer_is_quarantined_to_mock_consensus_directory(tmp_path: Path) -> None:
    app_data_root = tmp_path / "app" / "data"

    result = write_mock_consensus_artifact(
        [_exact_record()],
        run_id="20260424T120000Z",
        app_data_root=app_data_root,
        generated_at="2026-04-24T12:00:00Z",
    )

    expected_run = (
        app_data_root / "mock_consensus" / "mock_consensus_20260424T120000Z.json"
    )
    expected_latest = app_data_root / "mock_consensus" / "mock_consensus_latest.json"
    assert result.run_path == expected_run
    assert result.latest_path == expected_latest
    assert expected_run.exists()
    assert expected_latest.exists()
    assert json.loads(expected_run.read_text(encoding="utf-8")) == json.loads(
        expected_latest.read_text(encoding="utf-8")
    )

    valuation_dir = app_data_root / "valuation"
    assert not valuation_dir.exists()
    assert list(app_data_root.rglob("*_latest.json")) == [expected_latest]


def test_writer_rejects_run_ids_that_could_escape_quarantine(tmp_path: Path) -> None:
    app_data_root = tmp_path / "app" / "data"
    (app_data_root / "mock_consensus" / "mock_consensus_escape").mkdir(parents=True)
    (app_data_root / "valuation").mkdir(parents=True)

    with pytest.raises(ValueError, match="run_id"):
        write_mock_consensus_artifact(
            [_exact_record()],
            run_id="escape/../../valuation/leak",
            app_data_root=app_data_root,
            generated_at="2026-04-24T12:00:00Z",
        )

    assert not (app_data_root / "valuation" / "leak.json").exists()


def test_artifact_serializes_governance_shape_and_t4_internal_diagnostic() -> None:
    artifact = build_mock_consensus_artifact(
        [_exact_record()],
        run_id="20260424T120000Z",
        generated_at="2026-04-24T12:00:00Z",
    )

    assert artifact["run_id"] == "20260424T120000Z"
    assert artifact["decision_supported"] is False
    assert artifact["records"][0]["decision_supported"] is False
    assert artifact["records"][0]["internal_diagnostic"] is True
    assert artifact["records"][0]["projected_pick_median"] == 13.0
    assert artifact["records"][0]["abstention_tier"] == "exact_pick"
    assert artifact["records"][0]["round_tier"] == "R1.late"
    assert any(
        "stacked" in caveat.lower() and "inference" in caveat.lower()
        for caveat in artifact["caveats"]
    )
    assert all(
        node.get("decision_supported") is False
        for node in _walk_dicts(artifact)
        if "decision_supported" in node
    )


def test_artifact_language_is_clean_of_decision_verdicts() -> None:
    artifact = build_mock_consensus_artifact(
        [_exact_record()],
        run_id="20260424T120000Z",
        generated_at="2026-04-24T12:00:00Z",
    )
    text = "\n".join(_walk_strings(artifact)).lower()

    banned_phrases = (
        "must draft",
        "should draft",
        "do not draft",
        "recommendation",
        "decision-grade",
    )
    banned_words = {"buy", "sell", "avoid", "verdict", "confidence"}
    assert all(phrase not in text for phrase in banned_phrases)
    assert not any(f" {word} " in f" {text} " for word in banned_words)


def test_mock_consensus_package_has_no_reverse_imports() -> None:
    root = Path("src/dynasty_genius/mock_consensus")
    forbidden_modules = (
        "src.dynasty_genius.eval.backtest_mock_draft",
        "dynasty_genius.eval.backtest_mock_draft",
        "backtest_mock_draft",
        "src.dynasty_genius.engine_a",
        "dynasty_genius.engine_a",
        "src.dynasty_genius.engine_b",
        "dynasty_genius.engine_b",
        "src.dynasty_genius.scoring",
        "dynasty_genius.scoring",
    )

    failures: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_modules or alias.name.startswith(
                        forbidden_modules
                    ):
                        failures.append(f"{path}:{node.lineno}:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                modules = [module, *(f"{module}.{alias.name}" for alias in node.names)]
                for candidate in modules:
                    if candidate in forbidden_modules or candidate.startswith(
                        forbidden_modules
                    ):
                        failures.append(f"{path}:{node.lineno}:{candidate}")

    assert failures == []
