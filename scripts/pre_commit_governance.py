#!/usr/bin/env python3
"""Local pre-commit checks for the Dynasty Genius governance loop."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BANNED_MARKET_RE = re.compile(
    r"\b("
    r"ktc|keeptradecut|ktc_market_value|ktc_value|"
    r"dynastynerds|dynasty_nerds|fantasypros|fantasy_pros|"
    r"adp|market_value|market_consensus|market_overlay|market-derived"
    r")\b",
    re.IGNORECASE,
)

ENGINE_FEATURE_PATTERNS = [
    re.compile(r"^app/data/pipeline/train_models\.py$"),
    re.compile(r"^app/.*/features?[^/]*\.py$"),
    re.compile(r"^app/.*[^/]*feature[^/]*\.py$"),
    re.compile(r"^src/.*/features?[^/]*\.py$"),
    re.compile(r"^src/.*[^/]*feature[^/]*\.py$"),
]


def run(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True)


def fail(message: str) -> int:
    print(f"pre-commit governance check failed: {message}", file=sys.stderr)
    return 1


def validate_governance() -> int:
    result = run([sys.executable, "scripts/validate_governance.py"])
    if result.returncode == 0:
        return 0
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return fail("scripts/validate_governance.py failed")


def validate_today_ledger() -> int:
    today = dt.datetime.now().strftime("%Y-%m-%d")
    ledger = ROOT / "docs" / "agent-ledger" / f"{today}.md"
    if not ledger.is_file():
        return fail(f"missing today's ledger file: {ledger.relative_to(ROOT)}")

    text = ledger.read_text(encoding="utf-8")
    if not re.search(r"^## .+ - .+", text, re.MULTILINE):
        return fail(f"today's ledger has no session entry: {ledger.relative_to(ROOT)}")
    return 0


def staged_files() -> list[str]:
    result = run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMR",
        ]
    )
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(fail("could not inspect staged files"))
    return [line for line in result.stdout.splitlines() if line]


def is_engine_feature_file(path: str) -> bool:
    return any(pattern.search(path) for pattern in ENGINE_FEATURE_PATTERNS)


def staged_content(path: str) -> str:
    result = run(["git", "show", f":{path}"])
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(fail(f"could not read staged content for {path}"))
    return result.stdout


def validate_no_market_leakage() -> int:
    failures: list[str] = []
    for path in staged_files():
        if not is_engine_feature_file(path):
            continue
        for line_number, line in enumerate(staged_content(path).splitlines(), start=1):
            if BANNED_MARKET_RE.search(line):
                failures.append(f"{path}:{line_number}: {line.strip()}")

    if not failures:
        return 0

    print(
        "pre-commit governance check failed: market-derived terms in staged Engine A/B feature logic",
        file=sys.stderr,
    )
    for item in failures:
        print(f"- {item}", file=sys.stderr)
    return 1


def main() -> int:
    for check in (validate_governance, validate_today_ledger, validate_no_market_leakage):
        result = check()
        if result:
            return result
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
