"""Harness Trust Completion W1.5: market backfill must stay overlay-only."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Engine A/B model contracts, scoring, feature pipelines, and training/feature builders.
# Eval/reporting/overlay services are intentionally out of scope: they are the authorized
# consumers of market data. This test guards the model-input/training boundary.
ENGINE_MODEL_PATHS = (
    Path("src/dynasty_genius/models/engine_a_contract.py"),
    Path("src/dynasty_genius/models/engine_b_contract.py"),
    Path("src/dynasty_genius/models/head_b_contract.py"),
    Path("src/dynasty_genius/scoring/engine_a.py"),
    Path("src/dynasty_genius/pipelines"),
    Path("scripts/assemble_engine_b_dataset.py"),
    Path("scripts/backtest_engine_a_cfbd_only.py"),
    Path("scripts/build_college_features.py"),
    Path("scripts/build_w2_features.py"),
    Path("scripts/enrich_training_data.py"),
    Path("scripts/train_engine_b.py"),
    Path("scripts/validate_training_csv.py"),
)

BANNED_IMPORTS = {
    "scripts.backfill_market_archive",
    "src.dynasty_genius.eval.market_snapshot_store",
    "dynasty_genius.eval.market_snapshot_store",
}

# Exact symbols / artifact names that represent market-overlay or backfill data.
# Do not ban "market_share": in football data that is a legitimate production feature
# (e.g. WR receiving-market-share), not external dynasty-price data.
BANNED_SYMBOLS = {
    "MarketSnapshotStore",
    "backfill_market_archive",
    "fc_value",
    "fc_rank",
    "fc_snapshots",
    "market_rows",
    "market_store",
    "market_value",
    "market_overlay",
    "market_percentile",
    "market_volatility",
    "model_minus_market_delta",
    "ndcg_at_12_market",
    "ndcg_at_24_market",
    "ndcg_diff_bca_ci95",
    "ndcg_diff_primary_k",
}

BANNED_STRING_FRAGMENTS = (
    "backfill_market_archive",
    "fc_snapshots",
    "market_snapshot_store",
    "ndcg_at_12_market",
    "ndcg_at_24_market",
    "ndcg_diff_bca_ci95",
    "ndcg_diff_primary_k",
)


def _python_files(paths: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for rel in paths:
        path = REPO_ROOT / rel
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(
                p for p in path.rglob("*.py")
                if "__pycache__" not in p.parts
            )
    return sorted(files)


def _import_name(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    return ""


def _market_leakage_offenders() -> list[str]:
    offenders: list[str] = []
    for path in _python_files(ENGINE_MODEL_PATHS):
        rel = path.relative_to(REPO_ROOT)
        tree = ast.parse(path.read_text(), filename=str(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BANNED_IMPORTS:
                        offenders.append(f"{rel}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = _import_name(node)
                if module in BANNED_IMPORTS:
                    offenders.append(f"{rel}: from {module} import ...")
                for alias in node.names:
                    if alias.name in BANNED_SYMBOLS:
                        offenders.append(f"{rel}: imported symbol {alias.name}")
            elif isinstance(node, ast.Name) and node.id in BANNED_SYMBOLS:
                offenders.append(f"{rel}: name {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr in BANNED_SYMBOLS:
                offenders.append(f"{rel}: attr {node.attr}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for fragment in BANNED_STRING_FRAGMENTS:
                    if fragment in node.value:
                        offenders.append(f"{rel}: string fragment {fragment}")
    return offenders


def test_no_market_backfill_symbols_enter_engine_model_or_feature_paths() -> None:
    offenders = _market_leakage_offenders()

    assert offenders == []
