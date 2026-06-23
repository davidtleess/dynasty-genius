"""League-intelligence refresh verifier — preflight + acceptance/parity gates.

This is the SAFETY GATE for the artifact-freshness run (and the human-review
substitute, since the regenerated artifacts are multi-MB JSON). It is pure +
side-effect-free: it never fetches live data, never writes the FantasyCalc
cache, and never mutates a tracked artifact. The T3 operational run invokes it;
on any abort the on-disk state is left exactly as found.

Design spec: docs/superpowers/specs/2026-06-23-league-intelligence-artifact-freshness-design.md
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Market keys that must NEVER appear in a model-native card section (Q3=B / D3).
_MARKET_KEYS = frozenset(
    {
        "market_percentile",
        "model_minus_market_delta",
        "model_percentile",
        "divergence_score",
        "xvar",
        "raw_xvar",
        "signal",
        "signal_status",
        "asset_roster_id",
        "lineup_role",
    }
)
_BANNED_WORDS = frozenset({"buy", "sell", "target", "fade"})
_ABORT_STATES = frozenset({"stale-cache", "cold-empty"})


class RefreshVerificationError(Exception):
    """Raised on any preflight/acceptance failure → the run aborts, no mutation."""


@dataclass(frozen=True)
class MarketSourceClassification:
    status: str  # live | fresh-cache | stale-cache | cold-empty
    should_abort: bool


@dataclass(frozen=True)
class PreflightResult:
    status: str


@dataclass
class AcceptanceReport:
    status: str
    counts: dict[str, int]
    artifacts: list[dict[str, Any]] = field(default_factory=list)


# ── Market-source classification (strictly read-only; no network on fresh cache) ──


def classify_market_source(
    *,
    cache_file: Path,
    now: datetime,
    ttl_hours: int,
    api_reachable: Callable[[], bool],
) -> MarketSourceClassification:
    """Classify FantasyCalc availability WITHOUT side effects.

    Reads the cache file only; never writes/refreshes it, never invokes the
    builder. A FRESH cache short-circuits and does NOT touch the network.
    """
    if cache_file.exists():
        try:
            payload = json.loads(cache_file.read_text())
            fetched_at = datetime.strptime(
                payload["fetched_at"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            age_hours = (now - fetched_at).total_seconds() / 3600.0
        except (ValueError, KeyError, json.JSONDecodeError):
            age_hours = None
        if age_hours is not None and age_hours < ttl_hours:
            return MarketSourceClassification("fresh-cache", should_abort=False)
        # cache present but stale → fresh data only if the API is reachable.
        status = "live" if api_reachable() else "stale-cache"
    else:
        # no cache → fresh data only if the API is reachable, else cold-empty.
        status = "live" if api_reachable() else "cold-empty"
    return MarketSourceClassification(status, should_abort=status in _ABORT_STATES)


# ── Preflight ────────────────────────────────────────────────────────────────


def verify_preflight(
    *,
    required_inputs: list[Path],
    current_artifacts: dict[str, Path],
    expected_schema_versions: dict[str, str],
    route_probe: Callable[[], bool],
    market_source: MarketSourceClassification,
) -> PreflightResult:
    """Fail-closed preflight. Raises RefreshVerificationError on any gate."""
    if market_source.should_abort:
        raise RefreshVerificationError(
            f"market source not fresh: {market_source.status} (abort, no run)"
        )
    for path in required_inputs:
        if not Path(path).exists():
            raise RefreshVerificationError(f"missing input: {path}")
    for key, path in current_artifacts.items():
        expected = expected_schema_versions.get(key)
        try:
            actual = json.loads(Path(path).read_text()).get("schema_version")
        except (OSError, json.JSONDecodeError) as exc:
            raise RefreshVerificationError(
                f"artifact unreadable for schema_version check: {key}"
            ) from exc
        if actual != expected:
            raise RefreshVerificationError(
                f"schema_version mismatch for {key}: expected {expected!r}, got {actual!r}"
            )
    if not route_probe():
        raise RefreshVerificationError("league pulse route probe failed to parse artifacts")
    return PreflightResult("passed")


# ── Physical shape-drift gate (D2) ───────────────────────────────────────────


def verify_league_pulse_route_shape(client: Any) -> dict[str, Any]:
    """Hit GET /api/league/pulse and model_validate the body. Hard fail on drift."""
    from app.api.routes.league_pulse_models import LeaguePulseResponse

    res = client.get("/api/league/pulse")
    if res.status_code != 200:
        raise RefreshVerificationError(
            f"shape gate: route returned {res.status_code}, expected 200"
        )
    body = res.json()
    try:
        LeaguePulseResponse.model_validate(body)
    except Exception as exc:  # pydantic ValidationError → hard FAIL
        raise RefreshVerificationError(f"shape drift: {exc}") from exc
    return body


# ── Acceptance (semantic dict checks; NOT model_validate — see D3 bleed) ──────


def _iter_decision_supported_true(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("decision_supported") is True:
            return True
        return any(_iter_decision_supported_true(v) for v in value.values())
    if isinstance(value, list):
        return any(_iter_decision_supported_true(v) for v in value)
    return False


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _iter_strings(v)


def verify_acceptance(
    *,
    response: dict[str, Any],
    artifact_paths: list[Path],
    previous_captured_at: str,
    run_date: str,
    market_source_status: str,
    changed_paths: list[Path],
) -> AcceptanceReport:
    """Acceptance/parity over the assembled response + the changed artifacts."""
    # Market-bleed: raw market keys must NEVER appear in any NON-overlay section
    # (D3/F5, spec §4). model_native_cards / team_postures / team_values /
    # partner_rankings are all scanned against the EXACT _MARKET_KEYS set —
    # partner_rankings is scanned (not exempt): its sanctioned market-derived
    # field (`divergence_density_score`) is not in _MARKET_KEYS so it passes,
    # while a raw `market_percentile`/`model_minus_market_delta` leak is caught.
    def _market_leak(*key_sources: Any) -> set[str]:
        keys: set[str] = set()
        for src in key_sources:
            if isinstance(src, dict):
                keys |= set(src)
        return keys & _MARKET_KEYS

    for card in response.get("model_native_cards", []):
        leaked = _market_leak(card.get("evidence"), card.get("score_components"))
        if leaked:
            raise RefreshVerificationError(
                f"market-bleed: model-native card carries market keys {sorted(leaked)}"
            )
    for team in response.get("team_postures", []):
        leaked = _market_leak(team.get("components"))
        if leaked:
            raise RefreshVerificationError(
                f"market-bleed: team_postures carries market keys {sorted(leaked)}"
            )
    for team in response.get("team_values", []):
        leaked = _market_leak(
            team.get("value_views"),
            team.get("age_profile"),
            team.get("positional_summary"),
            team.get("future_picks"),
        )
        if leaked:
            raise RefreshVerificationError(
                f"market-bleed: team_values carries market keys {sorted(leaked)}"
            )
    for ranking in response.get("partner_rankings", []):
        leaked = _market_leak(ranking.get("evidence"), ranking.get("score_components"))
        if leaked:
            raise RefreshVerificationError(
                f"market-bleed: partner_rankings carries raw market keys {sorted(leaked)}"
            )

    # Non-vacuous drop-pairing (F4).
    waiver_cards = [
        c
        for c in response.get("market_overlay_cards", [])
        if c.get("card_type") == "WAIVER_CANDIDATE"
    ]
    if not waiver_cards:
        raise RefreshVerificationError(
            "drop-pairing: zero WAIVER_CANDIDATE cards (manual review required)"
        )
    waiver_drops = 0
    for card in waiver_cards:
        if card.get("recommended_drop") is None:
            raise RefreshVerificationError(
                "drop-pairing: WAIVER_CANDIDATE missing recommended_drop"
            )
        waiver_drops += 1

    # Decision framing.
    if _iter_decision_supported_true(response):
        raise RefreshVerificationError("decision_supported=True leaked into a response row")

    # Banned-language (word-token level so SELL_NOW is caught).
    for text in _iter_strings(response):
        for token in re.split(r"[^a-z0-9]+", text.lower()):
            if token in _BANNED_WORDS:
                raise RefreshVerificationError(f"banned-language token rendered: {text!r}")

    # Guardrail: no forbidden (model/training) path changed.
    for path in changed_paths:
        s = str(path)
        if s.endswith(".pkl") or "/models/" in s or "engine_a" in s or "engine_b" in s:
            raise RefreshVerificationError(f"guardrail: forbidden path changed: {s}")

    artifacts = []
    for path in artifact_paths:
        raw = Path(path).read_bytes()
        artifacts.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_size": len(raw),
            }
        )

    counts = {
        "team_count": len(response.get("team_values", [])),
        "waiver_cards": len(waiver_cards),
        "waiver_recommended_drops": waiver_drops,
    }
    return AcceptanceReport(status="passed", counts=counts, artifacts=artifacts)


# ── Report schema (F6 — locked) ──────────────────────────────────────────────

_REQUIRED_REPORT_FIELDS = (
    "schema_version",
    "status",
    "steps",
    "market_source",
    "artifacts",
    "captured_at_delta",
    "counts",
    "checks",
    "rollback_guardrail_diff",
    "decision_supported",
)
_REQUIRED_ARTIFACT_FIELDS = ("path", "sha256", "byte_size")


def validate_report_schema(report: dict[str, Any]) -> PreflightResult:
    """Lock the machine-readable refresh-report schema (test-backed)."""
    for key in _REQUIRED_REPORT_FIELDS:
        if key not in report:
            raise RefreshVerificationError(f"report missing required field: {key}")
    artifacts = report.get("artifacts") or []
    if not isinstance(artifacts, list) or not artifacts:
        raise RefreshVerificationError("report artifacts must be a non-empty list")
    for entry in artifacts:
        for key in _REQUIRED_ARTIFACT_FIELDS:
            if key not in entry:
                raise RefreshVerificationError(f"report artifact missing {key}")
    return PreflightResult("passed")
