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
EXCEPTION_CANDIDATE_RE = re.compile(
    r"\b(?:gen_alpha\.)?gold\.exception_archetype_candidates\b|\bexception_archetype_candidates\b",
    re.IGNORECASE,
)
EXCEPTION_CANDIDATE_WRITE_RE = re.compile(
    r"\b(?:insert\s+into|merge\s+into)\s+(?:gen_alpha\.)?gold\.exception_archetype_candidates\b"
    r"|\bcreate\s+(?:or\s+replace\s+)?(?:view|table)\s+(?:gen_alpha\.)?gold\.exception_archetype_candidates\b",
    re.IGNORECASE,
)
ROOKIE_EVALUATION_RE = re.compile(
    r"\b(?:gen_alpha\.)?gold\.rookie_draft_evaluations\b|\brookie_draft_evaluations\b",
    re.IGNORECASE,
)
ROOKIE_EVALUATION_WRITE_RE = re.compile(
    r"\b(?:insert\s+into|merge\s+into)\s+(?:gen_alpha\.)?gold\.rookie_draft_evaluations\b"
    r"|\bcreate\s+(?:or\s+replace\s+)?(?:view|table)\s+(?:gen_alpha\.)?gold\.rookie_draft_evaluations\b",
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
PRIMARY_TRACKING_SOURCE_RE = re.compile(
    r"\bdata_source\b\s+in\s*\([^)]*(?:'PFF'|\"PFF\"|'NGS'|\"NGS\"|'NEXTGENSTATS'|\"NEXTGENSTATS\"|'NEXT_GEN_STATS'|\"NEXT_GEN_STATS\"|'NEXT GEN STATS'|\"NEXT GEN STATS\")[^)]*\)"
    r"|\bdata_source\b\s*=\s*(?:'PFF'|\"PFF\"|'NGS'|\"NGS\"|'NEXTGENSTATS'|\"NEXTGENSTATS\"|'NEXT_GEN_STATS'|\"NEXT_GEN_STATS\"|'NEXT GEN STATS'|\"NEXT GEN STATS\")",
    re.IGNORECASE,
)
MARKET_HYPE_SOURCE_RE = re.compile(
    r"\b(?:KTC|KEEPTRADECUT|MARKET_HYPE|SOCIAL|TWITTER|REDDIT|PRICE_DISCOVERY)\b",
    re.IGNORECASE,
)
SUSTAINED_WINDOW_RE = re.compile(
    r"\bover\s*\([^)]*(?:rows\s+between\s+3\s+preceding\s+and\s+current\s+row|range\s+between|partition\s+by)[^)]*\)"
    r"|\brows\s+between\s+3\s+preceding\s+and\s+current\s+row\b"
    r"|\brolling[_\s-]*(?:4|four)[_\s-]*(?:week|game|window)"
    r"|\b(?:4|four)[_\s-]*(?:week|game)[_\s-]*(?:rolling|window)"
    r"|\bweek_window_count\b\s*>=\s*4\b"
    r"|\bsustained[_\s-]*window\b",
    re.IGNORECASE,
)
PICK_ASSET_RE = re.compile(
    r"\b(?:rookie[\s_]+)?(?:draft[\s_]+)?pick\b|\b[0-9]{4}[\s_]+(?:1st|2nd|3rd|4th|first|second|third|fourth)\b",
    re.IGNORECASE,
)
PICK_DEPRECIATION_RE = re.compile(
    r"\b(?:rookie[\s_]+)?(?:draft[\s_]+)?pick\b[\s\S]{0,240}?"
    r"(?:depreciat|discount|decay|haircut|time_penalty|months_until_draft|days_until_draft|draft_proximity)"
    r"[\s\S]{0,240}?(?:-\s*\d+(?:\.\d+)?\s*(?:%|/)|\*\s*0\.\d+|\*\s*\(\s*1\s*-|<\s*1(?:\.0+)?)"
    r"|(?:depreciat|discount|decay|haircut|time_penalty|months_until_draft|days_until_draft|draft_proximity)"
    r"[\s\S]{0,240}?\b(?:rookie[\s_]+)?(?:draft[\s_]+)?pick\b[\s\S]{0,240}?"
    r"(?:-\s*\d+(?:\.\d+)?\s*(?:%|/)|\*\s*0\.\d+|\*\s*\(\s*1\s*-|<\s*1(?:\.0+)?)",
    re.IGNORECASE,
)
PICK_MULTIPLIER_LT_ONE_RE = re.compile(
    r"\bpick_appreciation_multiplier\b\s*(?:<|<=|=)\s*0\.\d+"
    r"|\bpick_appreciation_multiplier\b\s+between\s+0(?:\.0+)?\s+and\s+0\.\d+"
    r"|(?:then|=)\s*0\.\d+[\s\S]{0,120}\bpick_appreciation_multiplier\b"
    r"|\bpick_appreciation_multiplier\b[\s\S]{0,120}(?:then|=)\s*0\.\d+",
    re.IGNORECASE,
)
PICK_DVU_REDUCTION_RE = re.compile(
    r"\b(?:rookie[\s_]+)?(?:draft[\s_]+)?pick\b[\s\S]{0,200}?\b\w*dvu\w*\b[\s\S]{0,120}?"
    r"(?:-\s*\d+(?:\.\d+)?\s*(?:%|/)|\*\s*0\.\d+|\*\s*\(\s*1\s*-)"
    r"|\b\w*dvu\w*\b[\s\S]{0,120}?(?:-\s*\d+(?:\.\d+)?\s*(?:%|/)|\*\s*0\.\d+|\*\s*\(\s*1\s*-)"
    r"[\s\S]{0,200}?\b(?:rookie[\s_]+)?(?:draft[\s_]+)?pick\b",
    re.IGNORECASE,
)
FIRST_ROUND_PICK_CONDITION_RE = re.compile(
    r"\bnfl[_\s]*overall[_\s]*pick\b\s+between\s+1\s+and\s+32\b"
    r"|\bnfl[_\s]*overall[_\s]*pick\b\s*(?:<=|<)\s*32\b"
    r"|\bnfl[_\s]*overall[_\s]*pick\b\s*<=\s*32\b"
    r"|\bnfl[_\s]*overall[_\s]*pick\b\s*<\s*33\b"
    r"|\bnfl[_\s]*overall[_\s]*pick\b\s*>=\s*1\s+and\s+\bnfl[_\s]*overall[_\s]*pick\b\s*<=\s*32\b",
    re.IGNORECASE,
)
SITUATION_WEIGHT_RE = re.compile(
    r"\bsituation[_\s]*weight\b|\bsituation[_\s]*score\b|\boffensive[_\s]*line[_\s]*grade\b|\btarget[_\s]*competition\b|\bqb[_\s]*epa\b",
    re.IGNORECASE,
)
SITUATION_OVERWEIGHT_RE = re.compile(
    r"(?:situation[_\s]*(?:weight|score)|offensive[_\s]*line[_\s]*grade|target[_\s]*competition|qb[_\s]*epa)"
    r"[\s\S]{0,140}(?:\*\s*(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)|(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)\s*\*)"
    r"|(?:then|=)\s*(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)\s+as\s+situation[_\s]*weight\b"
    r"|\bsituation[_\s]*weight\b\s*(?:=|:=)\s*(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)",
    re.IGNORECASE,
)
CASE_WHEN_RE = re.compile(
    r"\bwhen\b(?P<condition>[\s\S]*?)\bthen\b(?P<result>[\s\S]*?)(?=\bwhen\b|\belse\b|\bend\b)",
    re.IGNORECASE,
)
SITUATION_RESULT_OVERWEIGHT_RE = re.compile(
    r"(?:situation[_\s]*(?:weight|score)|offensive[_\s]*line[_\s]*grade|target[_\s]*competition|qb[_\s]*epa)"
    r"[\s\S]{0,140}(?:\*\s*(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)|(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)\s*\*)"
    r"|(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)\s+as\s+situation[_\s]*weight\b"
    r"|\bsituation[_\s]*weight\b\s*(?:=|:=)\s*(?:0\.(?:3[1-9]|[4-9]\d*)|[1-9](?:\.\d+)?)",
    re.IGNORECASE,
)


def strip_sql_comments(text: str) -> str:
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    return re.sub(r"--.*", " ", text)


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


def has_first_round_situation_overweight(text: str) -> bool:
    for match in CASE_WHEN_RE.finditer(text):
        condition = match.group("condition")
        result = match.group("result")
        if FIRST_ROUND_PICK_CONDITION_RE.search(condition) and SITUATION_RESULT_OVERWEIGHT_RE.search(result):
            return True
    return bool(
        FIRST_ROUND_PICK_CONDITION_RE.search(text)
        and SITUATION_OVERWEIGHT_RE.search(text)
        and not CASE_WHEN_RE.search(text)
    )


def audit_sql_file(path: Path) -> list[str]:
    text = strip_sql_comments(path.read_text(encoding="utf-8"))
    touches_trade_table = bool(TRADE_TABLE_RE.search(text))
    touches_exception_candidates = bool(EXCEPTION_CANDIDATE_RE.search(text))
    touches_rookie_evaluation = bool(ROOKIE_EVALUATION_RE.search(text))
    mutates_anchors = bool(ANCHORS_MUTATION_RE.search(text))
    touches_pick_asset = bool(PICK_ASSET_RE.search(text))
    if not touches_trade_table and not touches_exception_candidates and not touches_rookie_evaluation and not mutates_anchors and not touches_pick_asset:
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
    writes_exception_candidates = bool(EXCEPTION_CANDIDATE_WRITE_RE.search(text))
    writes_rookie_evaluation = bool(ROOKIE_EVALUATION_WRITE_RE.search(text))

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

    if PICK_DEPRECIATION_RE.search(text) or PICK_MULTIPLIER_LT_ONE_RE.search(text) or PICK_DVU_REDUCTION_RE.search(text):
        failures.append(
            "reduces DVU for a future rookie draft pick; picks may appreciate or stay flat over time, "
            "but the framework forbids time-based pick depreciation."
        )

    if writes_exception_candidates and not EFFICIENCY_METRICS_RE.search(text):
        failures.append(
            "defines or writes gold.exception_archetype_candidates without sourcing from "
            "gen_alpha.silver.efficiency_metrics."
        )

    if writes_exception_candidates and not SOURCE_RANK_ONE_RE.search(text):
        failures.append(
            "defines or writes gold.exception_archetype_candidates without requiring source_rank = 1."
        )

    if writes_exception_candidates and not PRIMARY_TRACKING_SOURCE_RE.search(text):
        failures.append(
            "defines or writes gold.exception_archetype_candidates without constraining data_source "
            "to primary tracking data such as PFF or NGS."
        )

    if writes_exception_candidates and MARKET_HYPE_SOURCE_RE.search(text):
        failures.append(
            "defines or writes gold.exception_archetype_candidates with market/hype sources; "
            "KTC and social/market feeds cannot trigger exception archetype candidacy."
        )

    if writes_exception_candidates and not SUSTAINED_WINDOW_RE.search(text):
        failures.append(
            "defines or writes gold.exception_archetype_candidates without a sustained rolling/window "
            "calculation; one-week spikes cannot grant exception archetype candidacy."
        )

    if (
        writes_rookie_evaluation
        and SITUATION_WEIGHT_RE.search(text)
        and has_first_round_situation_overweight(text)
    ):
        failures.append(
            "overweights situation for first-round rookie draft capital; NFL_Overall_Pick 1-32 "
            "must cap Situation Score weight at 0.30."
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
