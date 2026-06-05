"""Surface 2 Trade Lab — read-only tradeable asset catalog.

A pure builder over the universe PVO + Sleeper snapshot that returns
pre-shaped, selectable assets so the frontend never invents TradeAsset /
MarketAssetRef payloads. Read-only, model-blind (no market value enters the
model payload), ``decision_supported`` coercion-locked False.

Backs ``GET /api/trade/assets``. v1 assets = rostered players + future
round-only draft picks (rookies-as-players; no unrostered prospects).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

from src.dynasty_genius.trade_lab.draft_pick_valuation import value_pick
from src.dynasty_genius.trade_lab.evaluator import TradeAsset
from src.dynasty_genius.trade_lab.market_reconciler import MarketAssetRef

_MIN_Q = 3
_MAX_LIMIT = 100
_VALID_SEASONS = {2027, 2028, 2029}
_VALID_ROUNDS = {1, 2, 3}


class TradeAssetCatalogEntry(BaseModel):
    """A single selectable asset, pre-shaped in both payload forms."""

    asset_id: str
    label: str
    kind: Literal["player", "future_pick"]
    position: str | None = None
    roster_owner_id: int | None = None
    roster_owner_name: str | None = None
    model_payload: TradeAsset
    market_ref: MarketAssetRef
    caveats: list[str] = []
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False


class TradeAssetCatalogResponse(BaseModel):
    """The catalog envelope for a single search query."""

    query: str
    source_timestamp: str | None = None
    results: list[TradeAssetCatalogEntry] = []
    caveats: list[str] = []
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock_decision_supported(cls, _v: object) -> bool:
        return False


def _is_num(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def build_asset_catalog(
    query: str,
    universe_pvo: dict,
    sleeper_snapshot: dict,
    pick_curve: dict,
    *,
    limit: int = 50,
) -> TradeAssetCatalogResponse:
    """Build the read-only tradeable-asset catalog for a search query.

    Filters to rostered players (any roster) + shape-valid future picks,
    prices picks via ``value_pick`` (snapshot rows carry no xVAR), and
    synthesizes a deterministic, unique ``quantity_id`` per pick. Short /
    blank queries short-circuit to an empty result without scanning the
    full universe.
    """
    q = (query or "").strip()
    response = TradeAssetCatalogResponse(
        query=q,
        source_timestamp=sleeper_snapshot.get("captured_at"),
        caveats=["future_picks_from_snapshot_not_live_sleeper"],
    )
    if len(q) < _MIN_Q:
        return response

    ql = q.lower()
    entries: list[TradeAssetCatalogEntry] = []

    # Players: rostered only (any roster). A rostered rookie is a normal,
    # roster-consuming player (is_prospect False); missing xVAR stays
    # selectable with xvar=None rather than being dropped.
    for player_row in universe_pvo.get("players", []):
        league_context = player_row.get("league_context", {})
        if not league_context.get("rostered"):
            continue
        player = player_row.get("player", {})
        # Real PVO rows can carry full_name=None (unresolved / pseudo players);
        # such rows are not selectable assets — skip rather than crash on .lower().
        name = player.get("full_name") or ""
        if not name or ql not in name.lower():
            continue
        sleeper_id = str(player_row["sleeper_player_id"])
        position = player.get("position")
        entries.append(
            TradeAssetCatalogEntry(
                asset_id=sleeper_id,
                label=name,
                kind="player",
                position=position,
                roster_owner_id=league_context.get("roster_id"),
                roster_owner_name=league_context.get("owner_display_name"),
                model_payload=TradeAsset(
                    player_id=sleeper_id,
                    xvar=player_row.get("valuation", {}).get("xvar"),
                    position=position or "",
                    is_prospect=False,
                    dvs_engine=player_row.get("dvs_engine"),
                ),
                market_ref=MarketAssetRef(
                    asset_kind="player", sleeper_id=sleeper_id, player_id=sleeper_id
                ),
            )
        )

    # Future picks: round-only/generic. Shape gate excludes malformed,
    # wrong-type, and out-of-range rows. Only picks are non-roster-consuming.
    for pick in sleeper_snapshot.get("future_picks", []):
        season, round_ = pick.get("season"), pick.get("round")
        if not (
            _is_num(season)
            and int(season) in _VALID_SEASONS
            and _is_num(round_)
            and int(round_) in _VALID_ROUNDS
            and _is_num(pick.get("current_roster_id"))
            and _is_num(pick.get("original_roster_id"))
        ):
            continue
        season, round_ = int(season), int(round_)
        owner = int(pick["current_roster_id"])
        original = int(pick["original_roster_id"])
        label = f"{season} round {round_} (via {original})"
        if ql not in label.lower() and ql != str(season):
            continue
        quantity_id = f"pick:{season}:r{round_}:orig{original}:owner{owner}"
        priced = value_pick(year=season, round_=round_, curve=pick_curve)
        entries.append(
            TradeAssetCatalogEntry(
                asset_id=quantity_id,
                label=label,
                kind="future_pick",
                roster_owner_id=owner,
                model_payload=TradeAsset(
                    player_id=quantity_id,
                    xvar=priced.xvar,
                    position="PICK",
                    is_prospect=True,
                ),
                market_ref=MarketAssetRef(
                    asset_kind="future_pick",
                    year=season,
                    round=round_,
                    quantity_id=quantity_id,
                ),
                caveats=list(priced.caveats),
            )
        )

    entries.sort(key=lambda e: (-(e.model_payload.xvar or 0.0), e.label))
    safe_limit = max(0, min(int(limit), _MAX_LIMIT))
    response.results = entries[:safe_limit]
    return response
