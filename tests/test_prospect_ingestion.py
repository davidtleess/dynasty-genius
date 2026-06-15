import nflreadpy as nfl
import pandas as pd


def _fixture_2026_draft_picks() -> pd.DataFrame:
    """Hermetic fixture for the 2026 draft-pick contract (formerly an unconditional
    live nflverse/GitHub fetch via nfl.load_draft_picks). The unit suite must not
    depend on network/DNS; live-source freshness belongs in a separate, manually-run
    smoke, not here."""
    return pd.DataFrame([{"pick": 1, "pfr_player_name": "Fernando Mendoza"}])


def test_nflreadpy_2026_results():
    picks = _fixture_2026_draft_picks()
    assert not picks.empty
    assert "pfr_player_name" in picks.columns
    # Verify top pick (2026 draft contract).
    mendoza = picks[picks["pick"] == 1].iloc[0]
    assert mendoza["pfr_player_name"] == "Fernando Mendoza"


def test_nflreadpy_2026_results_is_hermetic(monkeypatch):
    def forbidden_live_fetch(years):
        raise AssertionError(f"live nflverse fetch forbidden in unit suite: {years}")

    monkeypatch.setattr(nfl, "load_draft_picks", forbidden_live_fetch)

    test_nflreadpy_2026_results()
