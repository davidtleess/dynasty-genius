"""Market source abstraction.

MarketSource defines the interface for all market overlay providers.
Active implementations: FantasyCalcMarketSource (crowd trade values) and
MflAdpMarketSource (real completed-draft rookie ADP, overlay-only, unwired).
KTCMarketSource is a stub — KTC ToS prohibits automated access.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class MarketSource(ABC):
    @abstractmethod
    def fetch(self) -> list[dict]:
        """Fetch raw market data. Returns list of normalised player dicts."""
        ...


class FantasyCalcMarketSource(MarketSource):
    """Active market source. Delegates to fantasycalc_adapter."""

    def fetch(self) -> list[dict]:
        from src.dynasty_genius.adapters.fantasycalc_adapter import fetch_with_cache
        data, _caveats = fetch_with_cache()
        return data


class MflAdpMarketSource(MarketSource):
    """MFL rookie ADP overlay. Season via constructor (default = current season).

    fetch() returns rows only (MarketSource contract); intrinsic caveats ride on each
    row, transient cache/source caveats stay on the adapter fetch_*_with_cache() calls.
    Overlay only — never an Engine A/B input. Not for SF-QB calibration.
    """

    def __init__(self, season: int | None = None) -> None:
        from src.dynasty_genius.adapters.mfl_adp_adapter import _current_season
        self.season = season if season is not None else _current_season()

    def fetch(self) -> list[dict]:
        from src.dynasty_genius.adapters.mfl_adp_adapter import (
            fetch_adp_with_cache,
            fetch_players_with_cache,
            normalize_mfl_adp_entry,
        )
        adp_rows, _adp_caveats = fetch_adp_with_cache(self.season)
        players_map, _players_caveats = fetch_players_with_cache(self.season)
        return [normalize_mfl_adp_entry(r, players_map) for r in adp_rows]


class KTCMarketSource(MarketSource):
    """Deferred. KTC ToS prohibits automated collection.

    No official API exists. Implement when a ToS-clean channel appears.
    See: docs/superpowers/specs/2026-05-13-phase9-market-overlay.md §KTC
    """

    def fetch(self) -> list[dict]:
        raise NotImplementedError(
            "KTC integration is deferred — ToS prohibits automated access. "
            "See Phase 9 spec §KTC for trigger conditions."
        )
