from app.services.roster_auditor import liquidity_risk
from src.dynasty_genius.models.league_context import DraftPick, LeagueContext


def test_league_context_loading(tmp_path):
    json_path = tmp_path / "test_context.json"
    json_path.write_text("""{
      "league_id": "test-league",
      "league_name": "Test League",
      "season": "2026",
      "david_user_id": "d1",
      "david_display_name": "David",
      "david_roster_id": 1,
      "is_superflex": true,
      "is_ppr": true,
      "te_premium": 0.75,
      "my_future_picks": [
        {"year": 2026, "round": 1, "is_acquired": false},
        {"year": 2026, "round": 2, "is_acquired": true, "original_owner_id": 2}
      ],
      "league_mates": [
        {"roster_id": 1, "user_id": "d1", "display_name": "David", "is_opponent": false},
        {"roster_id": 2, "user_id": "a1", "display_name": "Opponent", "is_opponent": true}
      ]
    }""")

    ctx = LeagueContext.load_from_json(json_path)
    assert ctx.league_name == "Test League"
    assert ctx.te_premium == 0.75
    assert len(ctx.my_future_picks) == 2
    assert ctx.my_future_picks[1].original_owner_id == 2
    assert ctx.my_future_picks[1].is_acquired is True

def test_liquidity_risk_from_context():
    # Helper to test that liquidity_risk logic correctly interprets the pick list
    def get_liquidity(picks):
        has_26 = any(p.year == 2026 and p.round == 2 for p in picks)
        has_27 = any(p.year == 2027 and p.round == 2 for p in picks)
        return liquidity_risk(has_26, has_27)

    low_risk_picks = [
        DraftPick(year=2026, round=2),
        DraftPick(year=2027, round=2)
    ]
    assert get_liquidity(low_risk_picks) == "LOW"

    high_risk_picks = [
        DraftPick(year=2026, round=1),
        DraftPick(year=2027, round=3)
    ]
    assert get_liquidity(high_risk_picks) == "HIGH_NO_SECOND_ROUND_ESCAPE_HATCH"

def test_scoring_propagation_into_caveats():
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    ctx = LeagueContext(
        league_id="1", league_name="N", season="2026",
        david_user_id="u", david_display_name="D", david_roster_id=1,
        is_superflex=True, te_premium=1.5
    )

    # QB in Superflex
    qb_id = PlayerIdentity(dg_id="q1", full_name="QB1", position="QB")
    pvo_qb = assemble_pvo(qb_id, league_context=ctx)
    assert "Superflex scoring active: QB value is elevated" in pvo_qb.caveats

    # TE in TE Premium
    te_id = PlayerIdentity(dg_id="t1", full_name="TE1", position="TE")
    pvo_te = assemble_pvo(te_id, league_context=ctx)
    assert "TE Premium (1.5) active: TE scarcity is elevated" in pvo_te.caveats

    # WR (no specific scoring caveat expected other than generic ones)
    wr_id = PlayerIdentity(dg_id="w1", full_name="WR1", position="WR")
    pvo_wr = assemble_pvo(wr_id, league_context=ctx)
    assert any("Superflex scoring active" in c for c in pvo_wr.caveats)
    assert not any("QB value is elevated" in c for c in pvo_wr.caveats)
    assert not any("TE Premium" in c for c in pvo_wr.caveats)
