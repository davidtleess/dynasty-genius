"""Phase 23 W3 arbitrage divergence context contract tests."""
from __future__ import annotations

from pathlib import Path

from src.dynasty_genius.trade_lab.market_reconciler import (
    MarketAssetRef,
    MarketDivergenceContext,
    attach_market_divergence_context,
    load_market_divergence_artifact,
    resolve_market_asset,
)


BANNED_ARBITRAGE_TERMS = {
    "buy",
    "sell",
    "target",
    "block",
    "approve",
    "reject",
    "pass",
    "fail",
}


def _overlay(sleeper_id: str):
    return resolve_market_asset(
        MarketAssetRef(asset_kind="player", player_id=f"dg-{sleeper_id}", sleeper_id=sleeper_id),
        fantasycalc_entries=[
            {
                "player": {
                    "name": f"Player {sleeper_id}",
                    "sleeperId": sleeper_id,
                    "position": "WR",
                },
                "value": 1000,
            }
        ],
        current_draft_year=2026,
        format_key="dynasty_sf_ppr",
    )


def _divergence_row(
    sleeper_id: str,
    percentile_delta: float | None,
    signal_status: str = "gates_passed",
) -> dict:
    return {
        "sleeper_player_id": sleeper_id,
        "identity_ids": {"sleeper_id": sleeper_id},
        "divergence": {
            "percentile_delta": percentile_delta,
            "model_minus_market_delta": percentile_delta,
            "signal_status": signal_status,
            "decision_supported": False,
        },
    }


def _decision_supported_true_count(value: object) -> int:
    if isinstance(value, dict):
        count = 1 if value.get("decision_supported") is True else 0
        return count + sum(_decision_supported_true_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_decision_supported_true_count(v) for v in value)
    return 0


def test_market_divergence_context_decision_supported_false():
    context = MarketDivergenceContext(
        signal_label="model_higher_than_market",
        percentile_delta=0.31,
        sigma_threshold=0.25,
        source_signal_status="gates_passed",
        caveats=["market_comparison_display_only"],
        decision_supported=True,
    )

    assert context.decision_supported is False
    assert _decision_supported_true_count(context.model_dump()) == 0


def test_attach_market_divergence_context_classifies_neutral_labels():
    overlays = [_overlay("p-high"), _overlay("p-low"), _overlay("p-band")]
    divergence_artifact = {
        "players": [
            _divergence_row("p-high", 0.31),
            _divergence_row("p-low", -0.29),
            _divergence_row("p-band", 0.08),
        ]
    }

    enriched = attach_market_divergence_context(
        overlays,
        divergence_artifact,
        sigma_threshold=0.25,
    )

    assert [o.divergence_context.signal_label for o in enriched] == [
        "model_higher_than_market",
        "model_lower_than_market",
        "inside_band",
    ]
    assert [o.divergence_context.percentile_delta for o in enriched] == [0.31, -0.29, 0.08]
    assert all(o.divergence_context.decision_supported is False for o in enriched)


def test_attach_market_divergence_context_uses_live_model_minus_market_delta_fallback():
    """Live Phase 17.4 artifacts store model-minus-market delta, not percentile_delta."""
    overlays = [_overlay("live-shaped")]
    divergence_artifact = {
        "players": [
            {
                "sleeper_player_id": "live-shaped",
                "divergence": {
                    "model_minus_market_delta": 0.26,
                    "signal_status": "gates_passed",
                    "decision_supported": False,
                },
            }
        ]
    }

    enriched = attach_market_divergence_context(
        overlays,
        divergence_artifact,
        sigma_threshold=0.25,
    )

    assert enriched[0].divergence_context.signal_label == "model_higher_than_market"
    assert enriched[0].divergence_context.percentile_delta == 0.26


def test_attach_market_divergence_context_maps_live_inside_band_status():
    """David ruling: live inside-band rows surface as inside_band, not unavailable."""
    overlays = [_overlay("inside-band-live")]
    divergence_artifact = {
        "players": [
            {
                "sleeper_player_id": "inside-band-live",
                "divergence": {
                    "model_minus_market_delta": -0.096,
                    "signal_status": "inside_band",
                    "decision_supported": False,
                },
            }
        ]
    }

    enriched = attach_market_divergence_context(
        overlays,
        divergence_artifact,
        sigma_threshold=0.25,
    )
    serialized = str(enriched[0].model_dump()).lower()

    assert enriched[0].divergence_context.signal_label == "inside_band"
    assert enriched[0].divergence_context.percentile_delta == -0.096
    assert enriched[0].divergence_context.source_signal_status == "inside_band"
    assert enriched[0].divergence_context.caveats == ["market_comparison_display_only"]
    assert enriched[0].divergence_context.decision_supported is False
    for banned in BANNED_ARBITRAGE_TERMS:
        assert banned not in serialized


def test_attach_market_divergence_context_unavailable_without_error():
    overlays = [_overlay("missing"), _overlay("not-gated")]
    divergence_artifact = {
        "players": [
            _divergence_row("not-gated", None, signal_status="unavailable"),
        ]
    }

    enriched = attach_market_divergence_context(
        overlays,
        divergence_artifact,
        sigma_threshold=0.25,
    )

    assert [o.divergence_context.signal_label for o in enriched] == [
        "unavailable",
        "unavailable",
    ]
    assert enriched[0].divergence_context.caveats == ["market_comparison_unavailable"]
    assert enriched[1].divergence_context.source_signal_status == "unavailable"


def test_arbitrage_context_uses_only_neutral_language():
    overlays = attach_market_divergence_context(
        [_overlay("p-high"), _overlay("p-low")],
        {
            "players": [
                _divergence_row("p-high", 0.30),
                _divergence_row("p-low", -0.30),
            ]
        },
        sigma_threshold=0.25,
    )

    serialized = " ".join(str(o.model_dump()).lower() for o in overlays)

    for banned in BANNED_ARBITRAGE_TERMS:
        assert banned not in serialized
    assert "model_higher_than_market" in serialized
    assert "model_lower_than_market" in serialized


def test_load_market_divergence_artifact_reads_players_payload(tmp_path: Path):
    artifact_path = tmp_path / "universe_market_divergence_latest.json"
    artifact_path.write_text(
        '{"players": [{"sleeper_player_id": "p1", "divergence": {"percentile_delta": 0.1}}]}'
    )

    artifact = load_market_divergence_artifact(artifact_path)

    assert artifact["players"][0]["sleeper_player_id"] == "p1"
