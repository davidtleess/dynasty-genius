"""Roster Audit Increment 1 — typed, allowlist-mapped, leakage-safe contract models.

Task 1 (this commit): live, fail-closed Engine-B trust loader. Subsequent tasks add
the typed response models, allowlist mapper, and envelope assembler.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.dynasty_genius.eval.backtest_artifact import BacktestResult

TRUST_DIR = Path("app/data/backtest/trust_surface/latest")
_VALID = {"VALIDATED", "PROVISIONAL", "EXPERIMENTAL"}


def _manifest_versions() -> dict[str, str]:
    """Live manifest model_version per position (upper-cased). Fail-closed: any read or
    parse failure yields an empty map, which disables the stale check rather than crashing."""
    try:
        manifest = json.loads((TRUST_DIR / "manifest.json").read_text(encoding="utf-8"))
        return {
            k.upper(): v.get("model_version")
            for k, v in manifest.get("positions", {}).items()
        }
    except Exception:
        return {}


def load_model_status_by_position(
    positions: list[str],
) -> tuple[dict[str, str], list[str]]:
    """LIVE per-position Engine-B model_status via BacktestResult.load. Fail-closed:
    missing / malformed / out-of-domain / unverifiable-freshness / STALE -> EXPERIMENTAL
    + caveat; keys are NEVER omitted (no fail-open). Freshness can only be trusted when
    the live manifest carries this position's model_version: if the manifest is missing,
    malformed, or lacks the position key, the artifact is treated as unverified
    (trust_status_unavailable) rather than trusted. Stale (R2-4) = the position IS in the
    manifest but the artifact model_version differs (trust_status_stale). Positions are
    upper-cased and de-duplicated; an empty list yields an empty status map and no
    caveats."""
    manifest = _manifest_versions()
    status: dict[str, str] = {}
    caveats: set[str] = set()
    for pos in sorted({p.upper() for p in positions}):
        path = TRUST_DIR / f"backtest_result_{pos}.json"
        try:
            result = BacktestResult.load(path)
            value = result.promotion_gate.model_status
            if value not in _VALID:
                status[pos] = "EXPERIMENTAL"
                caveats.add("trust_status_unavailable")
            elif pos not in manifest:
                # Cannot verify freshness without a manifest version -> fail closed.
                status[pos] = "EXPERIMENTAL"
                caveats.add("trust_status_unavailable")
            elif result.model_version != manifest[pos]:
                status[pos] = "EXPERIMENTAL"
                caveats.add("trust_status_stale")
            else:
                status[pos] = value
        except Exception:
            status[pos] = "EXPERIMENTAL"
            caveats.add("trust_status_unavailable")
    return status, sorted(caveats)
