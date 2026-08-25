"""DG-041 — a stream is never reported degraded for a limit it can never exceed.

``load_participation``'s own first line is ``max_season = get_current_season(
roster=True) - 1`` — the source publishes on a historical basis and refuses the
current roster season *by construction*, not by outage. Asking for it anyway
guarantees a ``ValueError``, a recorded fallback, and an ``inputs_degraded``
gate on every scheduled run, forever. A gate that is always red carries exactly
as much information as one that is always green.

The fix under test: a per-stream source CEILING beside the existing floor in
``_STREAM_LOADERS``, so the window never requests a season the source cannot
serve. ``fallback_used`` then goes back to meaning *something happened*.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pandas as pd
import pytest

from app.api.routes.system_health_models import summarize_input_provenance

cli = importlib.import_module("scripts.run_feature_refresh")


def _frame(*seasons: int) -> pd.DataFrame:
    return pd.DataFrame(
        {"season": list(seasons), "row_id": [f"row-{s}" for s in seasons]}
    )


class _Recorder:
    """Fake nflreadpy: records every (stream, window) request it receives.

    ``load_participation`` mirrors the installed client exactly: any season
    past ``get_current_season(roster=True) - 1`` raises the same ValueError
    the real client raises today.
    """

    def __init__(self, roster_season: int) -> None:
        self.roster_season = roster_season
        self.calls: list[tuple[str, list[int]]] = []

    def get_current_season(self, roster: bool = False) -> int:
        assert roster is True, "the participation ceiling is a ROSTER-year bound"
        return self.roster_season

    def _loader(self, name: str, ceiling: int | None = None):
        def load(*, seasons: list[int]) -> pd.DataFrame:
            self.calls.append((name, list(seasons)))
            if ceiling is not None and any(s > ceiling for s in seasons):
                raise ValueError(f"Season must be between 2016 and {ceiling}")
            return _frame(*seasons)

        return load

    def windows(self, name: str) -> list[list[int]]:
        return [w for n, w in self.calls if n == name]


def _load_source_with(
    monkeypatch: pytest.MonkeyPatch, provider: _Recorder, window: list[int]
) -> dict:
    import sys

    fake = SimpleNamespace(
        get_current_season=provider.get_current_season,
        load_player_stats=provider._loader("player_stats"),
        load_rosters=provider._loader("rosters"),
        load_snap_counts=provider._loader("snap_counts"),
        load_pbp=provider._loader("pbp"),
        load_participation=provider._loader(
            "participation", ceiling=provider.roster_season - 1
        ),
    )
    monkeypatch.setitem(sys.modules, "nflreadpy", fake)
    monkeypatch.setattr(cli, "load_nextgen_from_export", lambda seasons: {})
    return cli._load_source(window)


def test_a_stream_is_never_asked_for_a_season_its_source_cannot_serve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Recorder(roster_season=2026)

    sources = _load_source_with(monkeypatch, provider, [2024, 2025, 2026])

    # Exactly ONE participation request, already capped at the source's own
    # bound — no refusal, no retry. The window reflects reality up front.
    assert provider.windows("participation") == [[2024, 2025]]
    # The ceiling is PER-STREAM: pbp has no such limit and is still asked
    # for the full window.
    assert provider.windows("pbp") == [[2024, 2025, 2026]]

    entry = sources["__stream_provenance__"]["participation"]
    assert entry["status"] == "loaded"
    assert entry["effective_season"] == 2025
    # The whole ticket: nothing was refused, so nothing "happened".
    assert entry["fallback_used"] is False
    assert entry["error_type"] is None


def test_the_gate_reads_a_healthy_day_as_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Recorder(roster_season=2026)

    sources = _load_source_with(monkeypatch, provider, [2024, 2025, 2026])
    degraded, basis = summarize_input_provenance(sources["__stream_provenance__"])

    # Five healthy streams, one of them source-capped by construction:
    # the operator is told the inputs are LIVE, not "degraded" — cry-wolf
    # was the disease, and this line is the cure holding.
    assert degraded is False
    assert basis.startswith("inputs_live")
    assert "participation" in basis


def test_the_ceiling_mirrors_the_clients_bound_not_a_hardcoded_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Roll the clock forward: in the 2031 roster year the same code must cap
    # at 2030 with no edit. A hardcoded 2025 would rot exactly like the
    # permanent red it replaces.
    provider = _Recorder(roster_season=2031)

    _load_source_with(monkeypatch, provider, [2028, 2029, 2030, 2031])

    assert provider.windows("participation") == [[2028, 2029, 2030]]
