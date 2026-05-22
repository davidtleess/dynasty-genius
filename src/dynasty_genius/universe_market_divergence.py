from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.dynasty_genius.services.market_overlay_service import pct_rank

SCHEMA_VERSION = "universe_market_divergence.v1"
NOISE_BAND = 0.10
DEFAULT_MIN_COHORT_SIZE = 30
DEFAULT_VOLATILITY_THRESHOLD = 150.0
MODEL_BACKED_STATUSES = frozenset({"MODEL_SUPPORTED", "MODEL_UNCERTAIN"})
MODEL_BACKED_ROUTES = frozenset({"ENGINE_A", "ENGINE_B", "BLEND_AB"})
INACTIVE_OR_CONTEXT_ROUTES = frozenset({"INACTIVE", "CONTEXT_ONLY", "PRE_MODEL", "MARKET_ONLY"})
BANNED_LANGUAGE = frozenset({"buy", "sell", "target", "fade"})


def _market_lookup(fc_response: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, list[float]]]:
    by_sleeper: dict[str, dict[str, Any]] = {}
    cohorts: dict[str, list[float]] = defaultdict(list)
    for entry in fc_response:
        player = entry.get("player") or {}
        sleeper_id = player.get("sleeperId")
        position = player.get("position")
        value = entry.get("value")
        if sleeper_id is not None:
            by_sleeper[str(sleeper_id)] = entry
        if position and value is not None:
            cohorts[str(position)].append(float(value))
    return by_sleeper, cohorts


def _model_cohorts(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    cohorts: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        player = row.get("player") or {}
        valuation = row.get("valuation") or {}
        position = player.get("position")
        xvar = valuation.get("xvar")
        if (
            position
            and xvar is not None
            and valuation.get("engine_path") in MODEL_BACKED_ROUTES
            and valuation.get("valuation_status") in MODEL_BACKED_STATUSES
        ):
            cohorts[str(position)].append(float(xvar))
    return cohorts


def _market_overlay(entry: dict[str, Any], *, source_timestamp: str, fetch_caveats: list[str]) -> dict[str, Any]:
    return {
        "source": "fantasycalc",
        "market_value": entry.get("value"),
        "trend_delta": entry.get("trend30Day"),
        "market_volatility": entry.get("maybeMovingStandardDeviation"),
        "position_rank": entry.get("positionRank"),
        "overall_rank": entry.get("overallRank"),
        "source_timestamp": source_timestamp,
        "caveats": sorted(set(["source_timestamp_is_fetch_time_not_publish_time", *fetch_caveats])),
    }


def _empty_divergence(signal: str, status: str, notes: list[str], failed_gates: list[str] | None = None) -> dict[str, Any]:
    return {
        "signal": signal,
        "signal_status": status,
        "model_percentile": None,
        "market_percentile": None,
        "model_minus_market_delta": None,
        "failed_gates": failed_gates or [],
        "notes": notes,
        "decision_supported": False,
    }


def _signal_from_delta(delta: float) -> tuple[str, str]:
    if abs(delta) < NOISE_BAND:
        return "INSIDE_BAND", "inside_band"
    if delta > 0:
        return "MODEL_HIGH_MARKET_LOW", "gates_passed"
    return "MODEL_LOW_MARKET_HIGH", "gates_passed"


def _is_unresolved(row: dict[str, Any]) -> bool:
    valuation = row.get("valuation") or {}
    return (
        row.get("identity_status") == "unresolved"
        or valuation.get("engine_path") == "UNRESOLVED_IDENTITY"
        or valuation.get("valuation_status") == "UNRESOLVED_IDENTITY"
    )


def _is_model_backed(row: dict[str, Any]) -> bool:
    valuation = row.get("valuation") or {}
    return (
        valuation.get("engine_path") in MODEL_BACKED_ROUTES
        and valuation.get("valuation_status") in MODEL_BACKED_STATUSES
        and valuation.get("xvar") is not None
    )


def _blocked_signal(failed_gates: list[str]) -> str:
    if "stale_market_data" in failed_gates:
        return "SUPPRESSED_STALE_MARKET"
    if "volatile_market" in failed_gates:
        return "SUPPRESSED_VOLATILE_MARKET"
    if "small_cohort" in failed_gates:
        return "SUPPRESSED_SMALL_COHORT"
    return "UNAVAILABLE"


def build_universe_market_divergence(
    universe_pvo_batch: dict[str, Any],
    fc_response: list[dict[str, Any]],
    *,
    fetch_caveats: list[str] | None = None,
    captured_at: str | None = None,
    min_cohort_size: int = DEFAULT_MIN_COHORT_SIZE,
    volatility_threshold: float = DEFAULT_VOLATILITY_THRESHOLD,
) -> dict[str, Any]:
    """Build a full-universe post-scoring FantasyCalc overlay artifact.

    This reads model outputs from the Phase 17.2 PVO batch and writes market data
    only into `market_overlay` and `divergence`. It does not mutate the input
    batch and does not add market fields to `valuation`.
    """

    captured = captured_at or datetime.now(timezone.utc).isoformat()
    fetch_notes = list(fetch_caveats or [])
    source_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = copy.deepcopy(universe_pvo_batch)
    rows = result.get("players") or []
    fc_by_sleeper, market_cohorts = _market_lookup(fc_response)
    model_cohorts = _model_cohorts(rows)

    for row in rows:
        sleeper_id = str(row.get("sleeper_player_id"))
        player = row.get("player") or {}
        position = str(player.get("position") or "")
        valuation = row.get("valuation") or {}

        if _is_unresolved(row):
            row["divergence"] = _empty_divergence(
                "UNRESOLVED_IDENTITY",
                "unavailable",
                ["identity_unresolved"],
                ["unresolved_identity"],
            )
            continue

        fc_entry = fc_by_sleeper.get(sleeper_id)
        if fc_entry is None:
            row["divergence"] = _empty_divergence(
                "UNAVAILABLE",
                "unavailable",
                ["market_data_unavailable"],
                ["market_data_unavailable"],
            )
            continue

        row["market_overlay"] = _market_overlay(
            fc_entry,
            source_timestamp=source_timestamp,
            fetch_caveats=fetch_notes,
        )

        if not _is_model_backed(row) or valuation.get("engine_path") in INACTIVE_OR_CONTEXT_ROUTES:
            row["divergence"] = _empty_divergence(
                "UNAVAILABLE",
                "unavailable",
                ["model_backed_valuation_unavailable"],
                ["model_status_unavailable"],
            )
            continue

        market_cohort = market_cohorts.get(position, [])
        model_cohort = model_cohorts.get(position, [])
        failed_gates: list[str] = []
        if "stale_market_data" in fetch_notes:
            failed_gates.append("stale_market_data")
        if len(market_cohort) < min_cohort_size or len(model_cohort) < min_cohort_size:
            failed_gates.append("small_cohort")
        volatility = fc_entry.get("maybeMovingStandardDeviation")
        if volatility is not None and float(volatility) > volatility_threshold:
            failed_gates.append("volatile_market")

        xvar = float(valuation["xvar"])
        market_value = float(fc_entry.get("value") or 0.0)
        model_percentile = round(pct_rank(model_cohort, xvar), 3)
        market_percentile = round(pct_rank(market_cohort, market_value), 3)
        delta = round(model_percentile - market_percentile, 3)

        if failed_gates:
            row["divergence"] = {
                "signal": _blocked_signal(failed_gates),
                "signal_status": "gates_blocked",
                "model_percentile": model_percentile,
                "market_percentile": market_percentile,
                "model_minus_market_delta": delta,
                "failed_gates": failed_gates,
                "notes": failed_gates.copy(),
                "decision_supported": False,
            }
        else:
            signal, status = _signal_from_delta(delta)
            row["divergence"] = {
                "signal": signal,
                "signal_status": status,
                "model_percentile": model_percentile,
                "market_percentile": market_percentile,
                "model_minus_market_delta": delta,
                "failed_gates": [],
                "notes": [],
                "decision_supported": False,
            }

        if position == "TE":
            row["divergence"]["te_review"] = True
            row["divergence"]["notes"].append("te_review_period")
            row["market_overlay"]["caveats"].append("te_review_period")

    result["schema_version"] = SCHEMA_VERSION
    result["source_schema_version"] = universe_pvo_batch.get("schema_version")
    result["captured_at"] = captured
    result["coverage"] = build_market_divergence_coverage(result)
    return result


def build_market_divergence_coverage(batch: dict[str, Any]) -> dict[str, Any]:
    rows = batch.get("players") or []
    signal_counts = Counter(str((row.get("divergence") or {}).get("signal")) for row in rows)
    status_counts = Counter(str((row.get("divergence") or {}).get("signal_status")) for row in rows)
    language_surface = [
        {
            "signal": (row.get("divergence") or {}).get("signal"),
            "signal_status": (row.get("divergence") or {}).get("signal_status"),
            "failed_gates": (row.get("divergence") or {}).get("failed_gates"),
            "notes": (row.get("divergence") or {}).get("notes"),
        }
        for row in rows
    ]
    serialized = json.dumps(language_surface, sort_keys=True).lower()
    banned_terms_present = sorted(term for term in BANNED_LANGUAGE if term in serialized)
    te_rows = [row for row in rows if (row.get("player") or {}).get("position") == "TE" and row.get("divergence")]
    return {
        "total_players": len(rows),
        "market_overlay_present_count": sum(1 for row in rows if row.get("market_overlay") is not None),
        "signals_by_type": dict(sorted(signal_counts.items())),
        "signal_status_counts": dict(sorted(status_counts.items())),
        "decision_supported_true_count": sum(
            1 for row in rows if (row.get("divergence") or {}).get("decision_supported") is True
        ),
        "banned_language_present": banned_terms_present,
        "te_position_suppressed_count": sum(
            1
            for row in te_rows
            if (row.get("divergence") or {}).get("signal") == "UNAVAILABLE"
            and (row.get("divergence") or {}).get("failed_gates") == ["position_te"]
        ),
        "phase17_4_exit_criteria": {
            "market_data_overlay_only": all(
                "market_value" not in (row.get("valuation") or {}) for row in rows
            ),
            "decision_supported_false": not any(
                (row.get("divergence") or {}).get("decision_supported") is True for row in rows
            ),
            "no_imperative_language": not banned_terms_present,
            "te_not_suppressed_by_position_alone": True,
        },
    }


def write_market_divergence_artifacts(
    batch: dict[str, Any],
    *,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = run_id or str(batch["captured_at"]).replace(":", "").replace("-", "")
    batch_path = output_dir / f"universe_market_divergence_{safe_run_id}.json"
    latest_path = output_dir / "universe_market_divergence_latest.json"
    coverage_path = output_dir / f"universe_market_divergence_coverage_{safe_run_id}.json"
    coverage_latest_path = output_dir / "universe_market_divergence_coverage_latest.json"
    batch_payload = json.dumps(batch, indent=2, sort_keys=True) + "\n"
    coverage_payload = json.dumps(batch["coverage"], indent=2, sort_keys=True) + "\n"
    batch_path.write_text(batch_payload)
    latest_path.write_text(batch_payload)
    coverage_path.write_text(coverage_payload)
    coverage_latest_path.write_text(coverage_payload)
    return {
        "batch": batch_path,
        "batch_latest": latest_path,
        "coverage": coverage_path,
        "coverage_latest": coverage_latest_path,
    }
