from app.api.routes.roster_audit_models import assemble_response
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def test_real_assemble_pvo_row_maps_through_assemble_response():
    ident = PlayerIdentity(
        dg_id="x",
        full_name="Vet WR",
        position="WR",
        nfl_team="NYJ",
        sleeper_id="x",
        verification_status="VERIFIED",
    )
    pvo = assemble_pvo(ident, {"age": 27.0}).dict()
    # Inject leak vectors explicitly so this guards the Inc1 leak follow-up even
    # if a future assemble_pvo stops emitting market_overlay (the real dict already
    # carries market_overlay; market_value/future_x are added to prove the allowlist
    # excludes by construction on a real-shaped row).
    pvo["market_value"] = 987654  # distinctive sentinel (won't collide with score decimals)
    pvo["future_x"] = "LEAKVALUE"
    audit = {
        "status": "active",
        "engine": "pvo_assembler_v1",
        "reason": "ok",
        "caveats": ["no_market_overlay"],
        "players": [pvo],
        "qb_context_cards": [],
    }

    resp = assemble_response(audit)

    assert len(resp.players) == 1
    blob = resp.model_dump_json()
    assert "market_overlay" not in blob.replace("no_market_overlay", "")
    assert '"market_value"' not in blob
    assert "future_x" not in blob and "LEAKVALUE" not in blob and "987654" not in blob
    # free-text PVO caveats survive (not token-stripped)
    assert any(" " in c for c in resp.players[0].caveats)
    assert resp.decision_supported is False
