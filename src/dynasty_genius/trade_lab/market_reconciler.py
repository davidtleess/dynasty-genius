"""Phase 23 W1 — Trade Lab market overlay resolver.

Resolves trade assets (players and future picks) to raw FantasyCalc market
values. This lane is market-blind to the model: it never imports or calls
Engine A, Engine B, xVAR, or RosterCutEngine, and FantasyCalc values are kept
on their raw market scale — never converted to xVAR. Every response schema
coerces ``decision_supported`` to ``False`` (governance rule 12.5).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional, Union

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


class MarketDivergenceContext(BaseModel):
    signal_label: Literal[
        "model_higher_than_market",
        "model_lower_than_market",
        "inside_band",
        "unavailable",
    ]
    percentile_delta: Optional[float]
    sigma_threshold: float
    source_signal_status: Optional[str]
    caveats: list[str]
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
    divergence_context: Optional[MarketDivergenceContext] = None
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class PickKeyResolution(BaseModel):
    lookup_key: Optional[str]
    resolution: Literal["pick_exact_slot", "pick_generic_year_round", "unresolved"]
    caveats: list[str]


class MarketRosterPenalty(BaseModel):
    roster_id: int
    post_trade_overflow: int
    forced_cut_candidates: list[MarketAssetOverlay]
    penalty_market_value: int
    unresolved_cut_count: int
    caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class MarketRealismWarning(BaseModel):
    warning_type: Literal[
        "package_dilution_warning",
        "roster_filler_warning",
        "market_package_requires_manual_review",
    ]
    severity: Literal["advisory"]
    message: str
    metrics: dict[str, float]
    caveats: list[str]
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


class TradeMarketReconciliation(BaseModel):
    market_source: Literal["fantasycalc"]
    format_key: str
    source_timestamp: Optional[str]
    sent_assets: list[MarketAssetOverlay]
    received_assets: list[MarketAssetOverlay]
    market_sent_raw: int
    market_received_raw: int
    david_forced_cut_penalty: Optional[MarketRosterPenalty]
    counterparty_forced_cut_penalty: Optional[MarketRosterPenalty]
    adjusted_market_sent: int
    adjusted_market_received: int
    market_delta_for_david: int
    coverage_gaps: list[str]
    caveats: list[str]
    realism_warnings: list[MarketRealismWarning] = []
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, v: object) -> bool:
        return False


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


# ── Trade market reconciliation (W2) ────────────────────────────────────────


def _price_forced_cuts(
    david_roster_penalty: dict,
    fantasycalc_entries: list[dict],
    current_draft_year: int,
    format_key: str,
    source_timestamp: Optional[str],
) -> MarketRosterPenalty:
    """Price an already-selected, model-native forced-cut set at raw FC value.

    The cut set comes from Phase 22 RosterCutEngine output (passed in); this
    function never selects or reorders cuts — it only resolves their market
    value. Unresolved cuts are preserved as overlays and counted, never imputed.
    """
    cut_overlays: list[MarketAssetOverlay] = []
    penalty_caveats: list[str] = []

    for cut in david_roster_penalty.get("forced_cut_candidates", []):
        ref = MarketAssetRef(
            asset_kind="player",
            sleeper_id=cut.get("sleeper_player_id"),
            player_id=cut.get("full_name"),
        )
        overlay = resolve_market_asset(
            ref, fantasycalc_entries, current_draft_year, format_key, source_timestamp
        )
        cut_overlays.append(overlay)
        if overlay.market_value is None:
            penalty_caveats.append(
                f"{overlay.label} ({overlay.asset_ref.sleeper_id}): "
                "no FantasyCalc value — excluded from market penalty"
            )

    penalty_market_value = sum(
        o.market_value for o in cut_overlays if o.market_value is not None
    )
    unresolved_cut_count = sum(1 for o in cut_overlays if o.market_value is None)

    return MarketRosterPenalty(
        roster_id=int(david_roster_penalty.get("roster_id", 0)),
        post_trade_overflow=int(david_roster_penalty.get("post_trade_overflow", 0)),
        forced_cut_candidates=cut_overlays,
        penalty_market_value=penalty_market_value,
        unresolved_cut_count=unresolved_cut_count,
        caveats=penalty_caveats,
    )


def reconcile_trade_market(
    sent_assets: list[MarketAssetRef],
    received_assets: list[MarketAssetRef],
    david_roster_penalty: dict,
    fantasycalc_entries: list[dict],
    current_draft_year: int,
    format_key: str,
    source_timestamp: Optional[str] = None,
) -> TradeMarketReconciliation:
    """Single-sided David market reconciliation (spec section 8).

    Prices the trade's sent/received assets and David's already-selected forced
    cuts at raw FantasyCalc value, then computes the market-only directional
    delta. Cut selection is model-native and passed in via ``david_roster_penalty``;
    no roster/PVO data is fetched here. Counterparty penalty is deferred to
    Phase 23.5 and always ``None``.
    """
    sent_overlays = resolve_market_assets(
        sent_assets, fantasycalc_entries, current_draft_year, format_key, source_timestamp
    )
    received_overlays = resolve_market_assets(
        received_assets, fantasycalc_entries, current_draft_year, format_key, source_timestamp
    )

    market_sent_raw = sum(
        o.market_value for o in sent_overlays if o.market_value is not None
    )
    market_received_raw = sum(
        o.market_value for o in received_overlays if o.market_value is not None
    )

    david_penalty = _price_forced_cuts(
        david_roster_penalty, fantasycalc_entries, current_draft_year, format_key, source_timestamp
    )

    adjusted_market_sent = market_sent_raw
    adjusted_market_received = max(
        0, market_received_raw - david_penalty.penalty_market_value
    )
    market_delta_for_david = adjusted_market_received - adjusted_market_sent

    coverage_gaps: list[str] = []
    for overlay in sent_overlays + received_overlays + david_penalty.forced_cut_candidates:
        if overlay.coverage_gap and overlay.coverage_gap not in coverage_gaps:
            coverage_gaps.append(overlay.coverage_gap)

    return TradeMarketReconciliation(
        market_source="fantasycalc",
        format_key=format_key,
        source_timestamp=source_timestamp,
        sent_assets=sent_overlays,
        received_assets=received_overlays,
        market_sent_raw=market_sent_raw,
        market_received_raw=market_received_raw,
        david_forced_cut_penalty=david_penalty,
        counterparty_forced_cut_penalty=None,
        adjusted_market_sent=adjusted_market_sent,
        adjusted_market_received=adjusted_market_received,
        market_delta_for_david=market_delta_for_david,
        coverage_gaps=coverage_gaps,
        caveats=list(_BASE_MARKET_CAVEATS),
    )


# ── Arbitrage divergence context (W3) ───────────────────────────────────────


def load_market_divergence_artifact(path: Union[str, Path]) -> dict:
    """Read a `universe_market_divergence_latest.json`-style artifact from disk."""
    return json.loads(Path(path).read_text())


def _divergence_delta(divergence: dict) -> Optional[float]:
    """Extract the model-minus-market percentile delta.

    The contract test supplies `percentile_delta`; the live artifact stores the
    same value as `model_minus_market_delta` (model_percentile - market_percentile).
    """
    delta = divergence.get("percentile_delta")
    if delta is None:
        delta = divergence.get("model_minus_market_delta")
    return delta


_BANNED_STATUS_TOKENS = (
    "buy", "sell", "target", "block", "approve", "reject", "pass", "fail",
)


def _safe_source_status(status: Optional[str]) -> Optional[str]:
    """Echo the source signal_status for provenance, but never surface a value
    carrying a banned-language token (e.g. `gates_passed` contains `pass`).
    Such values collapse to None so display surfaces stay neutral."""
    if status is None:
        return None
    low = status.lower()
    if any(token in low for token in _BANNED_STATUS_TOKENS):
        return None
    return status


def _classify_divergence(
    divergence: Optional[dict],
    sigma_threshold: float,
) -> MarketDivergenceContext:
    """Map an existing divergence signal to a neutral model-vs-market label.

    No new metric is computed — this overlays the artifact's existing signal.
    `gates_passed` rows are classified directionally by |delta| vs σ. Rows the
    artifact already marks `inside_band` surface as `inside_band` (delta within
    the normal range — David ruling 2026-05-25). Missing rows or any other
    status surface as `unavailable` rather than being coerced into a signal.
    """
    if not divergence:
        return MarketDivergenceContext(
            signal_label="unavailable",
            percentile_delta=None,
            sigma_threshold=sigma_threshold,
            source_signal_status=None,
            caveats=["market_comparison_unavailable"],
        )

    status = divergence.get("signal_status")
    delta = _divergence_delta(divergence)
    safe_status = _safe_source_status(status)

    if status == "gates_passed" and delta is not None:
        if delta >= sigma_threshold:
            signal_label = "model_higher_than_market"
        elif delta <= -sigma_threshold:
            signal_label = "model_lower_than_market"
        else:
            signal_label = "inside_band"
        return MarketDivergenceContext(
            signal_label=signal_label,
            percentile_delta=delta,
            sigma_threshold=sigma_threshold,
            source_signal_status=safe_status,
            caveats=["market_comparison_display_only"],
        )

    if status == "inside_band":
        return MarketDivergenceContext(
            signal_label="inside_band",
            percentile_delta=delta,
            sigma_threshold=sigma_threshold,
            source_signal_status=safe_status,
            caveats=["market_comparison_display_only"],
        )

    return MarketDivergenceContext(
        signal_label="unavailable",
        percentile_delta=delta,
        sigma_threshold=sigma_threshold,
        source_signal_status=safe_status,
        caveats=["market_comparison_unavailable"],
    )


def attach_market_divergence_context(
    overlays: list[MarketAssetOverlay],
    divergence_artifact: dict,
    sigma_threshold: float = 0.25,
) -> list[MarketAssetOverlay]:
    """Enrich market overlays with model-vs-market divergence context by Sleeper ID.

    Read-only overlay of the existing divergence artifact — selection, scoring,
    and market values are untouched. Pick overlays (no Sleeper ID) and players
    absent from the artifact are reported as `unavailable`.
    """
    by_sleeper: dict[str, dict] = {
        row.get("sleeper_player_id"): row
        for row in divergence_artifact.get("players", [])
        if row.get("sleeper_player_id") is not None
    }

    enriched: list[MarketAssetOverlay] = []
    for overlay in overlays:
        row = by_sleeper.get(overlay.asset_ref.sleeper_id)
        divergence = row.get("divergence") if row else None
        context = _classify_divergence(divergence, sigma_threshold)
        enriched.append(overlay.model_copy(update={"divergence_context": context}))
    return enriched


# ── Competitive realism warnings (W4) ───────────────────────────────────────

_ROSTER_CONSUMING_KINDS = ("player", "prospect_player")


def attach_competitive_realism_warnings(
    reconciliation: TradeMarketReconciliation,
    gamma: float = 0.15,
    psi: float = 0.25,
) -> TradeMarketReconciliation:
    """Attach advisory-only "many-for-one" realism warnings to a reconciliation.

    These are display warnings, never gating logic — no accept/reject/approve
    semantics. The underlying market math is left untouched; warnings are added
    on a copy. `market_package_requires_manual_review` is intentionally not
    emitted here because it requires the model-native xVAR delta, which this
    market-blind lane does not have.
    """
    sent = reconciliation.sent_assets
    received = reconciliation.received_assets

    all_values = [
        o.market_value for o in sent + received if o.market_value is not None
    ]
    incoming_values = [
        o.market_value
        for o in received
        if o.market_value is not None
        and o.asset_ref.asset_kind in _ROSTER_CONSUMING_KINDS
    ]

    warnings: list[MarketRealismWarning] = []
    if all_values and incoming_values:
        premium_asset_value = max(all_values)
        if premium_asset_value > 0:
            average_package_ratio = (
                sum(incoming_values) / len(incoming_values) / premium_asset_value
            )
            low_quality_asset_count = sum(
                1 for v in incoming_values if v < gamma * premium_asset_value
            )

            if average_package_ratio < psi:
                warnings.append(
                    MarketRealismWarning(
                        warning_type="package_dilution_warning",
                        severity="advisory",
                        message=(
                            "Market realism warning: the incoming package averages a small "
                            "fraction of the premium asset value. Review the roster capacity "
                            "cost of absorbing several players for one premium asset."
                        ),
                        metrics={
                            "average_package_ratio": round(average_package_ratio, 4),
                            "psi": float(psi),
                            "premium_asset_value": float(premium_asset_value),
                            "incoming_asset_count": float(len(incoming_values)),
                        },
                        caveats=["market_realism_warning_only", "market_overlay_display_only"],
                    )
                )

            if low_quality_asset_count >= 2:
                warnings.append(
                    MarketRealismWarning(
                        warning_type="roster_filler_warning",
                        severity="advisory",
                        message=(
                            "Market realism warning: multiple incoming assets fall below the "
                            "roster-filler threshold. Weigh the capacity cost of the added "
                            "bench spots when reviewing this package."
                        ),
                        metrics={
                            "low_quality_asset_count": float(low_quality_asset_count),
                            "gamma": float(gamma),
                            "premium_asset_value": float(premium_asset_value),
                        },
                        caveats=["market_realism_warning_only", "market_overlay_display_only"],
                    )
                )

    return reconciliation.model_copy(update={"realism_warnings": warnings})
