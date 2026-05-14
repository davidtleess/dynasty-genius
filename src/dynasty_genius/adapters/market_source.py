"""Market source abstraction.

MarketSource defines the interface for all market overlay providers.
FantasyCalcMarketSource is the only active implementation.
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
