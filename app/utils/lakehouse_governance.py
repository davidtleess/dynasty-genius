from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.utils.compliance import RANK_1_GROUND_TRUTH, RANK_3_MARKET_SIGNAL

CATALOG = "gen_alpha"
BRONZE_SCHEMA = "bronze"
SILVER_SCHEMA = "silver"
GOLD_SCHEMA = "gold"
ANCHORS_TABLE = f"{CATALOG}.{GOLD_SCHEMA}.anchors"
ANCHOR_FLOOR_DVU = 120.0


@dataclass(frozen=True)
class AnchorLock:
    player_name: str
    position: str
    draft_class: int
    dvu_floor: float
    table_name: str
    lock_hash: str


def _anchor_hash(player_name: str, position: str, draft_class: int, dvu_floor: float) -> str:
    payload = f"{player_name}|{position}|{draft_class}|{dvu_floor}|{ANCHORS_TABLE}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


STRATEGIC_ANCHOR_LOCKS = {
    "Jeremiah Smith": AnchorLock(
        player_name="Jeremiah Smith",
        position="WR",
        draft_class=2027,
        dvu_floor=ANCHOR_FLOOR_DVU,
        table_name=ANCHORS_TABLE,
        lock_hash="c270546a0d1ffe9ba52c47a00009ea562a4d7a7c554dd913f43ef682b06a9496",
    ),
    "Arch Manning": AnchorLock(
        player_name="Arch Manning",
        position="QB",
        draft_class=2027,
        dvu_floor=ANCHOR_FLOOR_DVU,
        table_name=ANCHORS_TABLE,
        lock_hash="0e7914ec3234582bfbf9ce43645cf48138c92d55b502efff24ddb620e67f8b32",
    ),
}


def anchor_records() -> list[dict]:
    return [
        {
            "player_name": anchor.player_name,
            "position": anchor.position,
            "draft_class": anchor.draft_class,
            "dvu_floor": anchor.dvu_floor,
            "table_name": anchor.table_name,
            "lock_hash": anchor.lock_hash,
            "compliance_tag": "STRATEGIC_ANCHOR_LOCK",
            "source_rank": RANK_1_GROUND_TRUTH,
        }
        for anchor in STRATEGIC_ANCHOR_LOCKS.values()
    ]


def verify_anchor_lock(rows: list[dict]) -> None:
    by_name = {row.get("player_name"): row for row in rows}
    for anchor in STRATEGIC_ANCHOR_LOCKS.values():
        row = by_name.get(anchor.player_name)
        if row is None:
            raise ValueError(f"Missing anchor row: {anchor.player_name}")
        if float(row.get("dvu_floor", 0.0)) != anchor.dvu_floor:
            raise ValueError(f"Anchor floor changed for {anchor.player_name}")
        expected_hash = _anchor_hash(
            anchor.player_name,
            anchor.position,
            anchor.draft_class,
            anchor.dvu_floor,
        )
        if row.get("lock_hash") != expected_hash or anchor.lock_hash != expected_hash:
            raise ValueError(f"Anchor hash mismatch for {anchor.player_name}")
        if int(row.get("source_rank", 0)) != RANK_1_GROUND_TRUTH:
            raise ValueError(f"Anchor source rank must be Rank 1: {anchor.player_name}")


def enforce_medallion_write_path(source_layer: str, target_layer: str) -> None:
    source = source_layer.lower()
    target = target_layer.lower()
    if target == GOLD_SCHEMA and source != SILVER_SCHEMA:
        raise ValueError("Gold writes must pass through Silver normalization first")
    if target == SILVER_SCHEMA and source != BRONZE_SCHEMA:
        raise ValueError("Silver writes must originate from Bronze raw/refined snapshots")


def validate_adjusted_yac_source(metric: dict) -> None:
    source_rank = int(metric.get("source_rank", 0))
    source_name = str(metric.get("source_name", "")).lower()
    if source_rank == RANK_3_MARKET_SIGNAL:
        raise ValueError("COMPLIANCE_FAILURE: Adjusted YAC cannot use Rank 3 market data")
    if source_rank != RANK_1_GROUND_TRUTH:
        raise ValueError("COMPLIANCE_FAILURE: Adjusted YAC requires Rank 1 ground truth")
    if not any(name in source_name for name in ("pff", "next gen", "nextgen", "ngs")):
        raise ValueError("COMPLIANCE_FAILURE: Adjusted YAC source must be PFF or Next Gen")


def verify_trade_decision_prerequisites(response: dict) -> None:
    if response.get("source_hierarchy_verified") is not True:
        raise ValueError("Anti-Speed violation: source hierarchy not verified")
    if response.get("lakebase_transaction_verified") is not True:
        raise ValueError("Anti-Speed violation: Lakebase transaction not verified")
    if any(
        asset.get("valuation_status") != "VALUATION_STATUS_OK"
        for asset in [
            *response.get("my_assets_breakdown", []),
            *response.get("their_assets_breakdown", []),
        ]
    ):
        raise ValueError("Anti-Speed violation: all assets must be valuation-ready")
