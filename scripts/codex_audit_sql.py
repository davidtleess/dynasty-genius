#!/usr/bin/env python3
"""Static CI guardrails for governed Dynasty Genius SQL changes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TRADE_TABLE_RE = re.compile(
    r"\b(?:gen_alpha\.)?gold\.trade_evaluations_v2\b|\btrade_evaluations_v2\b",
    re.IGNORECASE,
)
TRADE_DEFINITION_RE = re.compile(
    r"\bcreate\s+(?:or\s+replace\s+)?table\s+(?:if\s+not\s+exists\s+)?"
    r"(?:gen_alpha\.)?gold\.trade_evaluations_v2\b",
    re.IGNORECASE,
)
TRADE_WRITE_RE = re.compile(
    r"\b(?:insert\s+into|merge\s+into)\s+(?:gen_alpha\.)?gold\.trade_evaluations_v2\b"
    r"|\bcreate\s+(?:or\s+replace\s+)?table\s+(?:gen_alpha\.)?gold\.trade_evaluations_v2\b[\s\S]*?\bas\b",
    re.IGNORECASE,
)
VALUES_DML_RE = re.compile(
    r"\binsert\s+into\s+(?:gen_alpha\.)?gold\.trade_evaluations_v2\b[\s\S]*?\bvalues\b",
    re.IGNORECASE,
)
SSOT_RE = re.compile(
    r"\bgen_alpha\.gold\.(?:genius_state|anchors)\b",
    re.IGNORECASE,
)
EFFICIENCY_METRICS_RE = re.compile(
    r"\bgen_alpha\.silver\.efficiency_metrics\b|\bsilver\.efficiency_metrics\b",
    re.IGNORECASE,
)
ANTI_SPEED_RE = re.compile(
    r"\bgen_alpha\.gold\.check_anti_speed_gate_v2\b|anti_speed_gate_triggered|BLOCKED_BY_SPEED_GATE",
    re.IGNORECASE,
)
QUANT_QUAL_RE = re.compile(
    r"quantitative|qualitative|quant_evidence|qual_evidence|quantitative_weight|qualitative_weight|65:35",
    re.IGNORECASE,
)
UNTRUSTED_DVU_RE = re.compile(
    r"\b(?:user[_\s-]*provided|manual|arbitrary|override|input|request|payload|client|form)[_\s-]*dvu\b"
    r"|\bdvu[_\s-]*(?:input|override|payload|request|manual)\b"
    r"|dbutils\.widgets\.[a-z_]+\([^)]*dvu"
    r"|\$\{[^}]*dvu[^}]*\}"
    r"|:[a-z_]*dvu[a-z_]*",
    re.IGNORECASE,
)
SOURCE_RANK_RE = re.compile(r"\bsource_rank\b", re.IGNORECASE)
ANCHORS_MUTATION_RE = re.compile(
    r"\b(?:update|merge\s+into|delete\s+from|insert\s+into)\s+(?:gen_alpha\.)?gold\.anchors\b",
    re.IGNORECASE,
)
DATA_DRIVEN_OVERRIDE_LOG_RE = re.compile(
    r"\binsert\s+into\s+(?:gen_alpha\.)?gold\.data_driven_override(?:_log)?\b"
    r"|\bdata_driven_override_log\b",
    re.IGNORECASE,
)
PLAYER_NAME_CASE_RE = re.compile(
    r"\bcase\b[\s\S]*?\bplayer_name\b[\s\S]*?['\"][^'\"]+['\"]",
    re.IGNORECASE,
)
SOURCE_RANK_ONE_RE = re.compile(
    r"\bsource_rank\b\s*=\s*1\b|\b1\s*=\s*\bsource_rank\b",
    re.IGNORECASE,
)
EXCEPTION_TERMS_RE = re.compile(
    r"exception|outlier|buffer|relief|depreciation|aging|age_cliff|adjusted_dvu|value_depreciation",
    re.IGNORECASE,
)


def discover_sql_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        if path.is_dir():
            files.extend(sorted(path.rglob("*.sql")))
        elif path.suffix.lower() == ".sql":
            files.append(path)
    return files


def audit_sql_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    touches_trade_table = bool(TRADE_TABLE_RE.search(text))
    mutates_anchors = bool(ANCHORS_MUTATION_RE.search(text))
    if not touches_trade_table and not mutates_anchors:
        return []

    failures: list[str] = []
    if VALUES_DML_RE.search(text):
        failures.append(
            "uses INSERT ... VALUES for gold.trade_evaluations_v2; trade ledger writes must be "
            "derived from governed SELECT/MERGE sources."
        )

    if UNTRUSTED_DVU_RE.search(text):
        failures.append(
            "contains a user/manual/input DVU pattern; absolute DVUs must come only from "
            "gen_alpha.gold.genius_state or gen_alpha.gold.anchors."
        )

    writes_trade_table = bool(TRADE_WRITE_RE.search(text))
    defines_trade_table = bool(TRADE_DEFINITION_RE.search(text))

    if writes_trade_table and not SSOT_RE.search(text):
        failures.append(
            "writes gold.trade_evaluations_v2 without referencing "
            "gen_alpha.gold.genius_state or gen_alpha.gold.anchors as the source of truth."
        )

    if writes_trade_table and not EFFICIENCY_METRICS_RE.search(text):
        failures.append(
            "writes gold.trade_evaluations_v2 without referencing "
            "gen_alpha.silver.efficiency_metrics for the quantitative baseline."
        )

    if (writes_trade_table or defines_trade_table) and not ANTI_SPEED_RE.search(text):
        failures.append(
            "defines or writes gold.trade_evaluations_v2 without native Anti-Speed Protocol tracking."
        )

    if (writes_trade_table or defines_trade_table) and not QUANT_QUAL_RE.search(text):
        failures.append(
            "defines or writes gold.trade_evaluations_v2 without 65:35 quantitative/qualitative "
            "compliance fields or terminology."
        )

    if (writes_trade_table or defines_trade_table) and not SOURCE_RANK_RE.search(text):
        failures.append(
            "defines or writes gold.trade_evaluations_v2 without source_rank tracking on team asset evidence."
        )

    if mutates_anchors and not DATA_DRIVEN_OVERRIDE_LOG_RE.search(text):
        failures.append(
            "mutates gen_alpha.gold.anchors without inserting a corresponding "
            "gen_alpha.gold.data_driven_override_log entry."
        )

    if PLAYER_NAME_CASE_RE.search(text):
        failures.append(
            "uses a CASE expression with player_name literals; depreciation and exception logic "
            "must not bypass rules for specific named players."
        )

    if EXCEPTION_TERMS_RE.search(text) and EFFICIENCY_METRICS_RE.search(text) and not SOURCE_RANK_ONE_RE.search(text):
        failures.append(
            "references exception/depreciation logic with efficiency_metrics but does not require source_rank = 1."
        )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        default=["resources"],
        help="SQL files or directories to audit.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    sql_files = discover_sql_files(args.paths)
    for sql_file in sql_files:
        for failure in audit_sql_file(sql_file):
            failures.append(f"{sql_file}: {failure}")

    if failures:
        print("Codex SQL audit failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Codex SQL audit passed for {len(sql_files)} SQL file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
