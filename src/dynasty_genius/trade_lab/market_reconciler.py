"""Phase 23 W1 — Trade Lab market overlay resolver.

Resolves trade assets (players and future picks) to raw FantasyCalc market
values. This lane is market-blind to the model: it never imports or calls
Engine A, Engine B, xVAR, or RosterCutEngine, and FantasyCalc values are kept
on their raw market scale — never converted to xVAR. Every response schema
coerces ``decision_supported`` to ``False`` (governance rule 12.5).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator

AssetKind = Literal["player", "prospect_player", "future_pick"]

# Caveats attached to every market overlay row, regardless of resolution
# (governance section 12 required caveat set).
_BASE_MARKET_CAVEATS = [
    "market_overlay_display_only",
    "fantasycalc_raw_scale_not_xvar",
    "market_values_not_model_inputs",
    "decision_supported_false",
    "source_timestamp_is_fetch_time_not_publish_time",
]


# ── Schemas ─────────────────────────────────────────────────────────────────


class MarketAssetRef(BaseModel):
    asset_kind: AssetKind
    player_id: Optional[str] = None
    sleeper_id: Optional[str] = None
    year: Optional[int] = None
    round: Optional[int] = None
    slot: Optional[int] = None  # 1-12 when exact order is known
    bucket: Optional[Literal["early", "mid", "late"]] = None
    quantity_id: Optional[str] = None
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class MarketAssetOverlay(BaseModel):
    asset_ref: MarketAssetRef
    label: str
    source: Literal["fantasycalc"]
    format_key: str
    market_value: Optional[int]
    resolution: Literal[
        "player_sleeper_id",
        "pick_exact_slot",
        "pick_generic_year_round",
        "unresolved",
    ]
    coverage_gap: Optional[str]
    trend_30d: Optional[int] = None
    market_volatility: Optional[float] = None
    source_timestamp: Optional[str] = None
    caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class PickKeyResolution(BaseModel):
    lookup_key: Optional[str]
    resolution: Literal["pick_exact_slot", "pick_generic_year_round", "unresolved"]
    caveats: list[str]


# ── Pick key resolver ───────────────────────────────────────────────────────


def resolve_pick_market_key(
    asset_ref: MarketAssetRef,
    current_draft_year: int,
) -> PickKeyResolution:
    """Map a future-pick ref to a deterministic FantasyCalc lookup key.

    Current-year picks with a known slot resolve to the 0-indexed exact-slot key
    ``DP_{round-1}_{slot-1}``. Generic future picks resolve to ``FP_{year}_{round}``
    and carry a slot-spread caveat. Picks without enough information to form a key
    are unresolved.
    """
    year = asset_ref.year
    rnd = asset_ref.round
    slot = asset_ref.slot

    if year is None or rnd is None:
        return PickKeyResolution(
            lookup_key=None,
            resolution="unresolved",
            caveats=["fantasycalc_pick_unavailable"],
        )

    if year == current_draft_year and slot is not None:
        return PickKeyResolution(
            lookup_key=f"DP_{rnd - 1}_{slot - 1}",
            resolution="pick_exact_slot",
            caveats=[],
        )

    # Early/mid/late bucket picks have no deterministic FC key (spec section 7).
    if asset_ref.bucket is not None:
        return PickKeyResolution(
            lookup_key=None,
            resolution="unresolved",
            caveats=["fantasycalc_bucket_pick_unavailable"],
        )

    return PickKeyResolution(
        lookup_key=f"FP_{year}_{rnd}",
        resolution="pick_generic_year_round",
        caveats=[
            "generic_future_pick_market_value",
            f"±40% slot-spread within {year} round {rnd} — exact slot unknown",
        ],
    )


# ── FantasyCalc row lookup ──────────────────────────────────────────────────


def _find_fc_row(entries: list[dict], key: Optional[str]) -> Optional[dict]:
    """Find an FC entry whose player ID fields match ``key`` (pick or player)."""
    if key is None:
        return None
    for entry in entries:
        player = entry.get("player", {})
        if key in (
            player.get("sleeperId"),
            player.get("mflId"),
            player.get("fleaflickerId"),
        ):
            return entry
    return None


def _pick_label(asset_ref: MarketAssetRef) -> str:
    year, rnd, slot = asset_ref.year, asset_ref.round, asset_ref.slot
    if year is None or rnd is None:
        return asset_ref.quantity_id or "future pick"
    if slot is not None:
        return f"{year} Pick {rnd}.{slot:02d}"
    return f"{year} Round {rnd} Pick"


# ── Asset resolvers ─────────────────────────────────────────────────────────


def _resolve_pick_asset(
    asset_ref: MarketAssetRef,
    entries: list[dict],
    current_draft_year: int,
    format_key: str,
    source_timestamp: Optional[str],
) -> MarketAssetOverlay:
    key_res = resolve_pick_market_key(asset_ref, current_draft_year)
    label = _pick_label(asset_ref)

    # No deterministic FC key (bucket-only / insufficient info): preserve the
    # specific coverage caveat from the key resolver rather than overwriting it.
    if key_res.lookup_key is None:
        gap = key_res.caveats[0] if key_res.caveats else "fantasycalc_pick_unavailable"
        return MarketAssetOverlay(
            asset_ref=asset_ref,
            label=label,
            source="fantasycalc",
            format_key=format_key,
            market_value=None,
            resolution="unresolved",
            coverage_gap=gap,
            source_timestamp=source_timestamp,
            caveats=_BASE_MARKET_CAVEATS + key_res.caveats,
        )

    row = _find_fc_row(entries, key_res.lookup_key)
    if row is None:
        return MarketAssetOverlay(
            asset_ref=asset_ref,
            label=label,
            source="fantasycalc",
            format_key=format_key,
            market_value=None,
            resolution="unresolved",
            coverage_gap="fantasycalc_pick_unavailable",
            source_timestamp=source_timestamp,
            caveats=_BASE_MARKET_CAVEATS + ["fantasycalc_pick_unavailable"],
        )

    return MarketAssetOverlay(
        asset_ref=asset_ref,
        label=label,
        source="fantasycalc",
        format_key=format_key,
        market_value=row.get("value"),
        resolution=key_res.resolution,
        coverage_gap=None,
        trend_30d=row.get("trend30Day"),
        market_volatility=row.get("maybeMovingStandardDeviation"),
        source_timestamp=source_timestamp,
        caveats=_BASE_MARKET_CAVEATS + key_res.caveats,
    )


def _resolve_player_asset(
    asset_ref: MarketAssetRef,
    entries: list[dict],
    format_key: str,
    source_timestamp: Optional[str],
) -> MarketAssetOverlay:
    row = None
    if asset_ref.sleeper_id is not None:
        for entry in entries:
            if entry.get("player", {}).get("sleeperId") == asset_ref.sleeper_id:
                row = entry
                break

    fallback_label = asset_ref.player_id or asset_ref.sleeper_id or "player"

    if row is None:
        return MarketAssetOverlay(
            asset_ref=asset_ref,
            label=fallback_label,
            source="fantasycalc",
            format_key=format_key,
            market_value=None,
            resolution="unresolved",
            coverage_gap="fantasycalc_uncovered",
            source_timestamp=source_timestamp,
            caveats=_BASE_MARKET_CAVEATS + ["fantasycalc_uncovered"],
        )

    player = row.get("player", {})
    return MarketAssetOverlay(
        asset_ref=asset_ref,
        label=player.get("name") or fallback_label,
        source="fantasycalc",
        format_key=format_key,
        market_value=row.get("value"),
        resolution="player_sleeper_id",
        coverage_gap=None,
        trend_30d=row.get("trend30Day"),
        market_volatility=row.get("maybeMovingStandardDeviation"),
        source_timestamp=source_timestamp,
        caveats=list(_BASE_MARKET_CAVEATS),
    )


def resolve_market_asset(
    asset_ref: MarketAssetRef,
    fantasycalc_entries: list[dict],
    current_draft_year: int,
    format_key: str,
    source_timestamp: Optional[str] = None,
) -> MarketAssetOverlay:
    """Resolve one asset ref to a FantasyCalc market overlay row."""
    if asset_ref.asset_kind == "future_pick":
        return _resolve_pick_asset(
            asset_ref, fantasycalc_entries, current_draft_year, format_key, source_timestamp
        )
    return _resolve_player_asset(
        asset_ref, fantasycalc_entries, format_key, source_timestamp
    )


def resolve_market_assets(
    asset_refs: list[MarketAssetRef],
    fantasycalc_entries: list[dict],
    current_draft_year: int,
    format_key: str,
    source_timestamp: Optional[str] = None,
) -> list[MarketAssetOverlay]:
    """Resolve a list of asset refs, preserving order and duplicate entries.

    Duplicate identical picks are kept as separate overlay rows (distinguished
    by ``quantity_id``); they are never collapsed by FantasyCalc key.
    """
    return [
        resolve_market_asset(
            ref, fantasycalc_entries, current_draft_year, format_key, source_timestamp
        )
        for ref in asset_refs
    ]
