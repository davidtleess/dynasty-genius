"""Phase 23 W4 competitive realism warning contract tests."""
from __future__ import annotations

from src.dynasty_genius.trade_lab.market_reconciler import (
    MarketAssetRef,
    MarketRealismWarning,
    attach_competitive_realism_warnings,
    reconcile_trade_market,
)

BANNED_WARNING_TERMS = {
    "accept",
    "reject",
    "approve",
    "block",
    "buy",
    "sell",
    "target",
}


def _fc_player_row(sleeper_id: str, value: int, name: str) -> dict:
    return {
        "player": {
            "name": name,
            "sleeperId": sleeper_id,
            "position": "WR",
        },
        "value": value,
        "trend30Day": 0,
        "maybeMovingStandardDeviation": None,
    }


def _base_reconciliation(sent_ids: list[str], received_ids: list[str], values: dict[str, int]):
    return reconcile_trade_market(
        sent_assets=[
            MarketAssetRef(asset_kind="player", player_id=sid, sleeper_id=sid)
            for sid in sent_ids
        ],
        received_assets=[
            MarketAssetRef(asset_kind="player", player_id=sid, sleeper_id=sid)
            for sid in received_ids
        ],
        david_roster_penalty={
            "roster_id": 1,
            "post_trade_overflow": 0,
            "forced_cut_candidates": [],
        },
        fantasycalc_entries=[
            _fc_player_row(sid, value, f"Player {sid}")
            for sid, value in values.items()
        ],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        count = 1 if value.get("decision_supported") is True else 0
        return count + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(v) for v in value)
    return 0


def test_market_realism_warning_decision_supported_false():
    warning = MarketRealismWarning(
        warning_type="package_dilution_warning",
        severity="advisory",
        message="Market realism warning: package average is below premium asset threshold.",
        metrics={"average_package_ratio": 0.12},
        caveats=["market_realism_warning_only"],
        decision_supported=True,
    )

    assert warning.decision_supported is False
    assert _decision_supported_true_count(warning.model_dump()) == 0


def test_many_for_one_package_emits_advisory_warnings_only():
    reconciliation = _base_reconciliation(
        sent_ids=["premium"],
        received_ids=["filler-a", "filler-b", "filler-c"],
        values={
            "premium": 10000,
            "filler-a": 900,
            "filler-b": 1100,
            "filler-c": 1200,
        },
    )
    original_math = (
        reconciliation.market_sent_raw,
        reconciliation.market_received_raw,
        reconciliation.adjusted_market_sent,
        reconciliation.adjusted_market_received,
        reconciliation.market_delta_for_david,
    )

    enriched = attach_competitive_realism_warnings(
        reconciliation,
        gamma=0.15,
        psi=0.25,
    )

    assert [w.warning_type for w in enriched.realism_warnings] == [
        "package_dilution_warning",
        "roster_filler_warning",
    ]
    assert all(w.severity == "advisory" for w in enriched.realism_warnings)
    assert all(w.decision_supported is False for w in enriched.realism_warnings)
    assert (
        enriched.market_sent_raw,
        enriched.market_received_raw,
        enriched.adjusted_market_sent,
        enriched.adjusted_market_received,
        enriched.market_delta_for_david,
    ) == original_math


def test_balanced_one_for_one_has_no_realism_warning():
    reconciliation = _base_reconciliation(
        sent_ids=["sent"],
        received_ids=["received"],
        values={
            "sent": 5000,
            "received": 5100,
        },
    )

    enriched = attach_competitive_realism_warnings(reconciliation)

    assert enriched.realism_warnings == []


def test_realism_warning_language_excludes_verdict_terms():
    reconciliation = _base_reconciliation(
        sent_ids=["premium"],
        received_ids=["filler-a", "filler-b"],
        values={
            "premium": 10000,
            "filler-a": 1000,
            "filler-b": 1000,
        },
    )

    enriched = attach_competitive_realism_warnings(reconciliation)
    serialized = str(enriched.model_dump()).lower()

    for banned in BANNED_WARNING_TERMS:
        assert banned not in serialized
    assert "market realism warning" in serialized
    assert "capacity cost" in serialized


def test_realism_warnings_on_reconciliation_recursive_decision_supported_false():
    reconciliation = _base_reconciliation(
        sent_ids=["premium"],
        received_ids=["filler-a", "filler-b"],
        values={
            "premium": 10000,
            "filler-a": 1000,
            "filler-b": 1000,
        },
    )

    enriched = attach_competitive_realism_warnings(reconciliation)

    assert enriched.decision_supported is False
    assert _decision_supported_true_count(enriched.model_dump()) == 0
