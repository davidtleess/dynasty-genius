"""MFL rookie ADP divergence report (Follow-up B, Increment B).

Read-only over model output. Joins normalized MFL rookie ADP rows to prospect_cards
(by normalized name + position within draft_class == season, fail-closed on ambiguity)
and emits a standalone divergence artifact. Never mutates model/PVO state.
"""
from __future__ import annotations

from typing import Any, Callable

from src.dynasty_genius.adapters.prospect_identity_resolver import normalize_name

ALIGNED_BAND_DEFAULT = 3
_BANNED_VERDICT_WORDS = frozenset(
    {"buy", "sell", "win", "loss", "verdict", "accept", "reject", "target", "fade"}
)


def _key(name: str | None, position: str | None) -> tuple[str, str]:
    return (normalize_name(name or ""), (position or "").upper())


def _index_unique(
    items: list[dict], name_of: Callable[[dict], Any], pos_of: Callable[[dict], Any]
) -> tuple[dict[tuple[str, str], dict], list[dict]]:
    """(unique_by_key, ambiguous_rows). Keys appearing >1x are excluded from unique."""
    by_key: dict[tuple[str, str], list[dict]] = {}
    for it in items:
        by_key.setdefault(_key(name_of(it), pos_of(it)), []).append(it)
    unique = {k: v[0] for k, v in by_key.items() if len(v) == 1}
    ambiguous_rows = [it for v in by_key.values() if len(v) > 1 for it in v]
    return unique, ambiguous_rows


def _flag(rank_gap: int, aligned_band: int) -> str:
    if abs(rank_gap) <= aligned_band:
        return "aligned"
    return "model_higher_than_market" if rank_gap > aligned_band else "market_higher_than_model"


def _coverage(artifact: dict, *, total_adp_rows: int) -> dict:
    banned = sorted(
        {
            w
            for r in artifact["matched"]
            for w in _BANNED_VERDICT_WORDS
            if w in str(r.get("divergence_flag", "")).lower()
        }
    )
    return {
        "total_adp_rows": total_adp_rows,
        "matched_count": len(artifact["matched"]),
        "unmatched_adp_count": len(artifact["unmatched_adp"]),
        "unmatched_model_count": len(artifact["unmatched_model"]),
        "ambiguous_count": len(artifact["ambiguous"]),
        "model_rank_unavailable_count": len(artifact["model_rank_unavailable"]),
        "decision_supported_true_count": sum(
            1 for r in artifact["matched"] if r.get("decision_supported") is True
        ),
        "banned_language_present": banned,
    }


def build_mfl_rookie_adp_divergence(
    adp_rows: list[dict],
    prospect_cards: list[dict],
    *,
    season: int,
    captured_at: str,
    caveats: list[str],
    aligned_band: int = ALIGNED_BAND_DEFAULT,
) -> dict:
    cards = [c for c in prospect_cards if c.get("draft_class") == season]
    model_unique, model_ambiguous = _index_unique(
        cards, lambda c: c.get("full_name"), lambda c: c.get("position")
    )
    adp_unique, adp_ambiguous = _index_unique(
        adp_rows, lambda r: r.get("full_name"), lambda r: r.get("position")
    )

    matched: list[dict] = []
    model_rank_unavailable: list[dict] = []
    unmatched_adp: list[dict] = []
    matched_model_keys: set[tuple[str, str]] = set()

    for k, row in adp_unique.items():
        ident = {
            "mfl_id": row.get("mfl_id"),
            "full_name": row.get("full_name"),
            "position": row.get("position"),
        }
        card = model_unique.get(k)
        if card is None:
            unmatched_adp.append(ident)
            continue
        matched_model_keys.add(k)
        model_rank = card.get("xvar_class_rank")
        market_adp_rank = row.get("market_adp_rank")
        if model_rank is None or market_adp_rank is None:
            model_rank_unavailable.append({**ident, "reason": "model_rank_unavailable"})
            continue
        rank_gap = market_adp_rank - model_rank
        matched.append(
            {
                **ident,
                "market_adp_rank": market_adp_rank,
                "market_average_pick": row.get("market_average_pick"),
                "model_rank": model_rank,
                "dvs_class_rank": card.get("dvs_class_rank"),
                "xvar": card.get("xvar"),
                "dynasty_value_score": card.get("dynasty_value_score"),
                "rank_gap": rank_gap,
                "divergence_flag": _flag(rank_gap, aligned_band),
                "decision_supported": False,
            }
        )

    unmatched_model = [
        {
            "full_name": c.get("full_name"),
            "position": c.get("position"),
            "model_rank": c.get("xvar_class_rank"),
        }
        for k, c in model_unique.items()
        if k not in matched_model_keys
    ]
    ambiguous = (
        [
            {
                "mfl_id": r.get("mfl_id"),
                "full_name": r.get("full_name"),
                "position": r.get("position"),
                "side": "adp",
                "reason": "adp_identity_ambiguous",
            }
            for r in adp_ambiguous
        ]
        + [
            {
                "full_name": c.get("full_name"),
                "position": c.get("position"),
                "side": "model",
                "reason": "model_identity_ambiguous",
            }
            for c in model_ambiguous
        ]
    )

    artifact = {
        "captured_at": captured_at,
        "source": "mfl_rookie_adp",
        "adp_draft_class": season,
        "rank_source": "xvar_class_rank_v1",
        "aligned_band": aligned_band,
        "decision_supported": False,
        "caveats": list(caveats),
        "matched": matched,
        "model_rank_unavailable": model_rank_unavailable,
        "unmatched_adp": unmatched_adp,
        "unmatched_model": unmatched_model,
        "ambiguous": ambiguous,
    }
    artifact["coverage"] = _coverage(artifact, total_adp_rows=len(adp_rows))
    return artifact
