import nflreadpy as nfl

def test_nflreadpy_2026_results():
    picks = nfl.load_draft_picks([2026]).to_pandas()
    assert not picks.empty
    assert "pfr_player_name" in picks.columns
    # Verify top pick
    mendoza = picks[picks["pick"] == 1].iloc[0]
    assert mendoza["pfr_player_name"] == "Fernando Mendoza"
