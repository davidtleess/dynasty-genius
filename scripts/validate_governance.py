#!/usr/bin/env python3
"""Validate Dynasty Genius governance bootstrap and obvious model leakage risks."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/governance/00-product-constitution.md",
    "docs/governance/01-north-star-architecture.md",
    "docs/governance/02-agent-operating-loop.md",
    "docs/governance/archive/originals/DYNASTY_GENIUS_FRAMEWORK.original.md",
    "docs/governance/archive/originals/DYNASTY_GENIUS_NORTH_STAR.original.md",
    "docs/governance/archive/originals/DYNASTY_GENIUS_PRODUCT_DESIGN.original.md",
    "docs/governance/reviews/gemini-product-signoff-2026-05-07.md",
    "docs/governance/platform/databricks-lineage-plan.md",
    "AGENT_SYNC.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".clauderules",
    "# DYNASTY GENIUS — SESSION STARTER.md",
    "AI_CONTEXT.md",
    "README.md",
    "docs/README.md",
    ".github/pull_request_template.md",
]

BOOTSTRAP_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    ".clauderules",
    "# DYNASTY GENIUS — SESSION STARTER.md",
    "AI_CONTEXT.md",
    "README.md",
    "docs/README.md",
]

REQUIRED_BOOTSTRAP_TARGETS = [
    "docs/governance/02-agent-operating-loop.md",
]

REQUIRED_GOVERNANCE_PHRASES = {
    "docs/governance/00-product-constitution.md": [
        "If an architectural pipeline conflicts with this constitution, the architecture is wrong.",
        "KTC, DynastyNerds, FantasyPros, ADP, and market-derived values are overlays only.",
        "High RAS does not mechanically increase dynasty value score",
    ],
    "docs/governance/01-north-star-architecture.md": [
        "Engine A: Rookie Forecast",
        "Engine B: Active Player Forecast",
        "Unified Player Value Object",
        "Data Platform Pattern",
    ],
    "docs/governance/02-agent-operating-loop.md": [
        "Preflight: Session Start",
        "Execution: During Work",
        "Postflight: Session End",
        "It does not have permission to bypass failing tests",
    ],
}

MODEL_FEATURE_FILES = [
    "app/data/pipeline/train_models.py",
]

MODEL_FEATURE_GLOBS = [
    "app/**/features*.py",
    "app/**/*feature*.py",
    "src/**/features*.py",
    "src/**/*feature*.py",
]

MARKET_FEATURE_RE = re.compile(
    r"\b(ktc_value|ktc_market_value|adp|fantasypros|dynastynerds|market_value)\b",
    re.IGNORECASE,
)

ALLOWLIST_MARKET_CONTEXT_RE = re.compile(
    r"market_overlay|market.*overlay|market.*sanity|price discovery",
    re.IGNORECASE,
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_required_files(failures: list[str]) -> None:
    for file_name in REQUIRED_FILES:
        path = ROOT / file_name
        if not path.is_file():
            fail(f"Missing required governance file: {file_name}", failures)

    if not (ROOT / "docs/agent-ledger").is_dir():
        fail("Missing required ledger directory: docs/agent-ledger", failures)

    if not any((ROOT / "docs/agent-ledger").glob("*.md")):
        fail("Missing at least one daily ledger file in docs/agent-ledger", failures)


def validate_bootstrap_files(failures: list[str]) -> None:
    for file_name in BOOTSTRAP_FILES:
        path = ROOT / file_name
        if not path.is_file():
            continue
        text = read_text(path)
        for target in REQUIRED_BOOTSTRAP_TARGETS:
            if target not in text:
                fail(f"{file_name} does not point to {target}", failures)


def validate_governance_phrases(failures: list[str]) -> None:
    for file_name, phrases in REQUIRED_GOVERNANCE_PHRASES.items():
        path = ROOT / file_name
        if not path.is_file():
            continue
        text = read_text(path)
        for phrase in phrases:
            if phrase not in text:
                fail(f"{file_name} is missing required phrase: {phrase}", failures)


def model_feature_paths() -> list[Path]:
    paths = {ROOT / name for name in MODEL_FEATURE_FILES}
    for pattern in MODEL_FEATURE_GLOBS:
        paths.update(ROOT.glob(pattern))
    return sorted(path for path in paths if path.is_file())


def validate_market_feature_leakage(failures: list[str]) -> None:
    for path in model_feature_paths():
        text = read_text(path)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not MARKET_FEATURE_RE.search(line):
                continue
            if ALLOWLIST_MARKET_CONTEXT_RE.search(line):
                continue
            fail(
                f"Potential market-derived model feature in {rel(path)}:{line_number}: {line.strip()}",
                failures,
            )


def main() -> int:
    failures: list[str] = []
    validate_required_files(failures)
    validate_bootstrap_files(failures)
    validate_governance_phrases(failures)
    validate_market_feature_leakage(failures)

    if failures:
        print("Governance validation failed:", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1

    print("Governance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
