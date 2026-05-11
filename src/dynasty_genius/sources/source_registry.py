"""Dynasty Genius Source Registry.

Machine-readable classification of every data source the system may touch.
Roles, allowed fields, failure behavior, and leakage guards are defined here
and enforced by tests/test_source_registry.py.

Source roles:
    model_input             — allowed as Engine A or Engine B training feature;
                              must carry source_ provenance sibling.
    training_label          — contributes outcome labels (prediction target only);
                              labels are never model inputs.
    context_signal          — surfaces in decision UI or validation docs only;
                              never a model input by any path.
    market_overlay          — price/rank discovery only; never enters Engine A/B
                              by constitution regardless of feature name.
    prohibited_current_phase — blocked for cost/licensing reasons (not analytical
                              impurity); requires David's explicit approval before
                              any pipeline access.
    prohibited              — cannot enter any pipeline layer under any circumstance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.dynasty_genius.models.engine_a_contract import (
    CFBD_MODEL_INPUT_COLUMNS,
    PLAYERPROFILER_CONTEXT_COLUMNS,
    PROHIBITED_COLUMNS,
)

SourceRole = Literal[
    "model_input",
    "training_label",
    "context_signal",
    "market_overlay",
    "prohibited_current_phase",
    "prohibited",
]

FailureBehavior = Literal["fail_closed", "skip_enrichment", "use_cached"]


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    roles: frozenset[SourceRole]
    allowed_fields: tuple[str, ...]      # empty = no field restriction within role
    prohibited_fields: tuple[str, ...]   # always excluded regardless of role
    provenance_required: bool            # True = every data field needs source_ sibling
    cache_policy: str                    # "json_cache" | "parquet_snapshot" | "csv_fixture" | "none"
    freshness_hours: int | None          # None = static / manual
    failure_behavior: FailureBehavior
    test_gate: str                       # pytest node path for gate test
    notes: str = ""


def _make(
    name: str,
    roles: list[SourceRole],
    allowed_fields: list[str] = (),
    prohibited_fields: list[str] = (),
    provenance_required: bool = False,
    cache_policy: str = "none",
    freshness_hours: int | None = None,
    failure_behavior: FailureBehavior = "skip_enrichment",
    test_gate: str = "",
    notes: str = "",
) -> SourceDefinition:
    return SourceDefinition(
        name=name,
        roles=frozenset(roles),
        allowed_fields=tuple(allowed_fields),
        prohibited_fields=tuple(prohibited_fields),
        provenance_required=provenance_required,
        cache_policy=cache_policy,
        freshness_hours=freshness_hours,
        failure_behavior=failure_behavior,
        test_gate=test_gate,
        notes=notes,
    )


SOURCE_REGISTRY: dict[str, SourceDefinition] = {
    s.name: s for s in [
        _make(
            name="nfl_data_py",
            roles=["model_input", "training_label"],
            allowed_fields=["pick", "round", "age", "team", "draft_year"],
            provenance_required=True,
            cache_policy="parquet_snapshot",
            freshness_hours=168,  # 7 days
            failure_behavior="use_cached",
            test_gate="tests/test_source_registry.py",
            notes=(
                "model_input for draft capital and age features; "
                "training_label for historical NFL outcome columns (y24_ppg etc). "
                "training_label columns are the prediction target — never model inputs."
            ),
        ),
        _make(
            name="cfbd",
            roles=["model_input"],
            allowed_fields=list(CFBD_MODEL_INPUT_COLUMNS),
            prohibited_fields=list(PROHIBITED_COLUMNS),
            provenance_required=True,
            cache_policy="json_cache",
            freshness_hours=720,  # 30 days for historical seasons
            failure_behavior="skip_enrichment",
            test_gate="tests/test_engine_a_v2_feature_contract.py",
            notes=(
                "Primary auditable college-production source for Engine A v2. "
                "Implementation uses httpx directly; cfbd PyPI library is not used. "
                "Formula version locked in docs/data-sources/cfbd-formula-spec.md."
            ),
        ),
        _make(
            name="playerprofiler",
            roles=["context_signal"],
            allowed_fields=list(PLAYERPROFILER_CONTEXT_COLUMNS),
            prohibited_fields=list(PROHIBITED_COLUMNS),
            provenance_required=True,
            cache_policy="json_cache",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_playerprofiler_decision_gate.py",
            notes=(
                "Task 3 is under corrected gate review as of 2026-05-11. "
                "The original 0% probe was superseded by a two-step retrieval path, "
                "but clean target_share coverage remains below the 80% promotion gate. "
                "PlayerProfiler remains context_signal; PP-only fields may appear in "
                "artifacts for coverage review but are not model inputs and are not "
                "imputed as model evidence. "
                "Shadow API: POST wp-admin/admin-ajax.php."
            ),
        ),
        _make(
            name="ras",
            roles=["context_signal"],
            allowed_fields=["low_ras_risk_flag", "missing_athletic_profile", "source_ras_score"],
            provenance_required=True,
            cache_policy="json_cache",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_ras_adapter.py",
            notes=(
                "Risk and context signal only. low_ras_risk_flag=True when RAS<4.0 AND "
                "record exists. missing_athletic_profile=True when no RAS record found — "
                "this is a caveat, not evidence of low athleticism. "
                "No positive model boost without validated backtest lift."
            ),
        ),
        _make(
            name="pff",
            roles=["context_signal"],
            allowed_fields=[],
            provenance_required=True,
            cache_policy="csv_fixture",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_manual_export_adapter.py",
            notes=(
                "Manual CSV export from PFF Premium Stats dashboard only in this phase. "
                "API is enterprise-only (Teamworks Intelligence / B2B). "
                "pff_grade and pff_route_grade are in PROHIBITED_COLUMNS — "
                "PFF fields never enter model features under any name."
            ),
        ),
        _make(
            name="rotoviz",
            roles=["context_signal"],
            allowed_fields=[],
            provenance_required=True,
            cache_policy="csv_fixture",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_manual_export_adapter.py",
            notes="Manual CSV export only. No public API.",
        ),
        _make(
            name="campus2canton",
            roles=["context_signal"],
            allowed_fields=[],
            provenance_required=True,
            cache_policy="csv_fixture",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_manual_export_adapter.py",
            notes=(
                "CSV export from Player Metric Data Table. "
                "ryptpa and dominator_pct used as secondary CFBD validation only."
            ),
        ),
        _make(
            name="fantasycalc",
            roles=["market_overlay"],
            allowed_fields=[],
            prohibited_fields=list(PROHIBITED_COLUMNS),
            provenance_required=False,
            cache_policy="json_cache",
            freshness_hours=24,
            failure_behavior="use_cached",
            test_gate="tests/test_market_overlay.py",
            notes=(
                "Free undocumented JSON API. Primary market signal source. "
                "Values from actual completed trades, not crowdsourced opinions. "
                "All fields are market_overlay — never enter Engine A/B training."
            ),
        ),
        _make(
            name="dynasty_data_lab",
            roles=["market_overlay"],
            allowed_fields=[],
            provenance_required=False,
            cache_policy="none",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_market_overlay.py",
            notes="$4 per 1000 requests. Deferred until market comparison UI exists.",
        ),
        _make(
            name="dynasty_nerds",
            roles=["market_overlay"],
            allowed_fields=[],
            provenance_required=False,
            cache_policy="none",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_market_overlay.py",
            notes="Expert consensus. No clean public API. Deferred.",
        ),
        _make(
            name="ktc",
            roles=["market_overlay"],
            allowed_fields=[],
            prohibited_fields=list(PROHIBITED_COLUMNS),
            provenance_required=False,
            cache_policy="none",
            freshness_hours=None,
            failure_behavior="skip_enrichment",
            test_gate="tests/test_market_leakage_gate.py",
            notes=(
                "ToS explicitly prohibits scraping rankings. "
                "FantasyCalc is primary market signal. "
                "KTC deferred until official API exists. "
                "ktc_value and ktc_rank are in PROHIBITED_COLUMNS."
            ),
        ),
        _make(
            name="sleeper",
            roles=["context_signal"],
            allowed_fields=[],
            provenance_required=False,
            cache_policy="json_cache",
            freshness_hours=1,
            failure_behavior="use_cached",
            test_gate="tests/test_source_registry.py",
            notes=(
                "Free read-only API, no auth. Provides David's league state, "
                "roster composition, and trending players. "
                "Never a model input — context and decision surface only."
            ),
        ),
        _make(
            name="sportradar",
            roles=["prohibited_current_phase"],
            allowed_fields=[],
            provenance_required=False,
            cache_policy="none",
            freshness_hours=None,
            failure_behavior="fail_closed",
            test_gate="tests/test_source_registry.py",
            notes=(
                "Enterprise B2B only. ~$7200/year for live feeds. "
                "Blocked for cost/licensing — not analytical impurity. "
                "Requires David's explicit approval to unlock."
            ),
        ),
        _make(
            name="genius_sports",
            roles=["prohibited_current_phase"],
            allowed_fields=[],
            provenance_required=False,
            cache_policy="none",
            freshness_hours=None,
            failure_behavior="fail_closed",
            test_gate="tests/test_source_registry.py",
            notes=(
                "Exclusive official NFL data distributor. Enterprise pricing. "
                "Blocked for cost/licensing. Requires David's explicit approval."
            ),
        ),
        _make(
            name="stats_perform",
            roles=["prohibited_current_phase"],
            allowed_fields=[],
            provenance_required=False,
            cache_policy="none",
            freshness_hours=None,
            failure_behavior="fail_closed",
            test_gate="tests/test_source_registry.py",
            notes=(
                "X-Info feed tailored for broadcast/sportsbook enterprise clients. "
                "Blocked for cost/licensing. Requires David's explicit approval."
            ),
        ),
        _make(
            name="rolling_insights",
            roles=["prohibited_current_phase"],
            allowed_fields=[],
            provenance_required=False,
            cache_policy="none",
            freshness_hours=None,
            failure_behavior="fail_closed",
            test_gate="tests/test_source_registry.py",
            notes=(
                "DataFeeds NFL API: $4200/year post-game, $7200/year live. "
                "Blocked for cost/licensing. Requires David's explicit approval."
            ),
        ),
    ]
}

# Validate at import time: no model_input source should list a field in PROHIBITED_COLUMNS.
for _src in SOURCE_REGISTRY.values():
    if "model_input" in _src.roles:
        _leakage = set(_src.allowed_fields) & PROHIBITED_COLUMNS
        if _leakage:
            raise ValueError(
                f"Source '{_src.name}' is model_input but lists prohibited fields: {_leakage}"
            )
