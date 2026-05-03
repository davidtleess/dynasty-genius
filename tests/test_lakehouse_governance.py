import pytest

from app.services.trade_analyzer import analyze_trade, deliver_trade_decision
from app.utils.compliance import RANK_1_GROUND_TRUTH, RANK_3_MARKET_SIGNAL
from app.utils.lakehouse_governance import (
    ANCHORS_TABLE,
    anchor_records,
    enforce_medallion_write_path,
    validate_adjusted_yac_source,
    verify_anchor_lock,
)


def test_anchor_lock_records_are_cryptographically_verifiable() -> None:
    records = anchor_records()
    verify_anchor_lock(records)
    assert {row["player_name"] for row in records} == {"Jeremiah Smith", "Arch Manning"}
    assert {row["dvu_floor"] for row in records} == {120.0}
    assert {row["table_name"] for row in records} == {ANCHORS_TABLE}


def test_anchor_lock_rejects_market_depreciation() -> None:
    records = anchor_records()
    records[0] = {**records[0], "dvu_floor": 99.0}
    with pytest.raises(ValueError, match="Anchor floor changed"):
        verify_anchor_lock(records)


def test_adjusted_yac_requires_rank_1_pff_or_next_gen() -> None:
    validate_adjusted_yac_source(
        {
            "metric": "adjusted_yac",
            "source_rank": RANK_1_GROUND_TRUTH,
            "source_name": "PFF",
        }
    )
    with pytest.raises(ValueError, match="COMPLIANCE_FAILURE"):
        validate_adjusted_yac_source(
            {
                "metric": "adjusted_yac",
                "source_rank": RANK_3_MARKET_SIGNAL,
                "source_name": "KTC",
            }
        )


def test_gold_writes_must_pass_through_silver() -> None:
    enforce_medallion_write_path("bronze", "silver")
    enforce_medallion_write_path("silver", "gold")
    with pytest.raises(ValueError, match="Gold writes must pass through Silver"):
        enforce_medallion_write_path("bronze", "gold")


def test_trade_decision_signal_requires_verification_delay_completion() -> None:
    response = analyze_trade(
        my_assets=[{"type": "pick", "year": 2027, "round": 1}],
        their_assets=[],
    )
    with pytest.raises(ValueError, match="Lakebase transaction not verified"):
        deliver_trade_decision(response, "ACCEPT")
