import pytest
import nfl_data_py as nfl

def test_nfl_data_py_2026_results():
    picks = nfl.import_draft_picks([2026])
    assert not picks.empty
    assert "pfr_player_name" in picks.columns
    # Verify top pick
    mendoza = picks[picks["pick"] == 1].iloc[0]
    assert mendoza["pfr_player_name"] == "Fernando Mendoza"
