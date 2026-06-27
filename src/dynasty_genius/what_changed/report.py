"""War Room #2 T2 — report emitter + structural current-context assembler.

Composes the T1 pure diff (:func:`build_daily_what_changed_diff`) with an
allowlisted structural *current-context* view (posture / team value / league
opportunity / drop pressure / roster snapshot) into the §4 machine-readable
report, and writes it overwrite-latest to an injected path.

Backend-only: no API and no frontend surface (those are T3 / a later increment).

Guardrails: ``decision_supported`` is False recursively (top level + every
section); structural sections are CURRENT context only (``current_not_delta=True``,
never a delta) and carry an explicit staleness caveat; each section exposes only an
ALLOWLISTED summary (no raw object/evidence dumps); market content stays a
descriptive overlay and no market field is surfaced into the model section.

Determinism: the clock (``now_fn``) and every path are injected — no module-level
wall-clock or filesystem coupling.

Design spec: docs/superpowers/specs/2026-06-24-war-room-2-daily-what-changed-diff-design.md
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from src.dynasty_genius.features.feature_source import (
    FeatureSourceNotReadyError,
    resolve_feature_source,
)
from src.dynasty_genius.pvo_source import (
    PvoSourceNotReadyError,
    resolve_pvo_source,
)
from src.dynasty_genius.what_changed.daily_diff import build_daily_what_changed_diff

_SCHEMA_VERSION = "war_room_2_what_changed_v1"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENGINE_B_FEATURE_SEED_PATH = (
    _REPO_ROOT / "app" / "data" / "training" / "engine_b_features_v2.csv"
)
_FEATURES_RUNTIME_DIR = _REPO_ROOT / "app" / "data" / "features_runtime"
_PVO_SEED_PATH = _REPO_ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
_PVO_SEED_COVERAGE_PATH = (
    _REPO_ROOT / "app" / "data" / "valuation" / "universe_pvo_coverage_latest.json"
)
_PVO_RUNTIME_DIR = _REPO_ROOT / "app" / "data" / "valuation_runtime"
# Structural artifacts refresh on the daily cadence, so a full cadence-period (24h)
# or older is "a prior day's context" — flagged stale for the daily-login product.
_STALE_THRESHOLD_HOURS = 24.0
# Cap allowlisted list summaries so a structural section can never become a raw dump.
_STRUCTURAL_TOP_K = 5


def emit_daily_what_changed_report(
    *,
    fc_db_path: Path | str,
    model_db_path: Path | str,
    sleeper_snapshot_path: Path | str,
    team_posture_path: Path | str,
    team_value_matrix_path: Path | str,
    league_opportunity_path: Path | str,
    roster_cut_report_path: Path | str,
    report_path: Path | str,
    now_fn: Callable[[], datetime],
    top_n: int = 25,
) -> dict[str, Any]:
    """Build the §4 report (T1 diff + structural context) and write it overwrite-latest.

    ``now_fn`` is invoked exactly once; its value stamps ``generated_at`` and anchors
    every structural staleness caveat. Returns the report dict (identical to the JSON
    written at ``report_path``).
    """
    generated_at = now_fn()

    diff = build_daily_what_changed_diff(
        fc_db_path=fc_db_path,
        model_db_path=model_db_path,
        sleeper_snapshot_path=sleeper_snapshot_path,
        top_n=top_n,
    )
    # Disclose engine_b feature freshness on the model section: which feature CSV backed the
    # vintage (published runtime vs committed seed) + its hashes/as-of. Descriptive only.
    model_feature_freshness = _model_feature_freshness()
    if isinstance(diff.get("model"), dict):
        diff["model"]["feature_freshness"] = model_feature_freshness
    # Disclose PVO source provenance on the model section (runtime vs committed seed) and,
    # ONLY when the §3.6 drift tripwire recommends promotion, the passive seed_staleness
    # block. Descriptive, decision_supported=False, never a decision/instruction.
    model_pvo_staleness = _model_pvo_staleness()
    if isinstance(diff.get("model"), dict):
        diff["model"]["pvo_staleness"] = model_pvo_staleness
    structural_context = assemble_structural_context(
        team_posture_path=team_posture_path,
        team_value_matrix_path=team_value_matrix_path,
        league_opportunity_path=league_opportunity_path,
        roster_cut_report_path=roster_cut_report_path,
        sleeper_snapshot_path=sleeper_snapshot_path,
        generated_at=generated_at,
    )

    report = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "decision_supported": False,
        "overall_status": _report_overall_status(
            diff["overall_status"], structural_context["status"]
        ),
        "daily_diff": diff,
        "structural_context": structural_context,
    }

    out_path = Path(report_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    return report


def _model_feature_freshness() -> Optional[dict[str, Any]]:
    """Resolved engine_b feature-source freshness for the model section (descriptive only).

    Returns the resolver's metadata (source kind + hashes + as-of). The READ-ONLY daily
    digest must not crash on a not-ready runtime, but it must NOT silently hide it either —
    an unverified runtime is DISCLOSED as explicit ``not_ready`` metadata (honest-uncertainty
    mandate), never omitted. ``decision_supported`` stays False and no market field appears.
    """
    try:
        resolved = resolve_feature_source(
            seed_path=_ENGINE_B_FEATURE_SEED_PATH,
            runtime_dir=_FEATURES_RUNTIME_DIR,
        )
    except FeatureSourceNotReadyError as exc:
        return {
            "decision_supported": False,
            "feature_source_status": "not_ready",
            "feature_source_kind": None,
            "aborted_reason": str(exc),
        }
    meta = resolved.metadata()
    return {
        "decision_supported": False,
        "feature_source_kind": meta["feature_source_kind"],
        "feature_csv_sha256": meta["feature_csv_sha256"],
        "source_as_of": meta["source_as_of"],
        "feature_csv_path": meta["feature_csv_path"],
        "published_seed_sha256": meta["published_seed_sha256"],
    }


def _model_pvo_staleness() -> dict[str, Any]:
    """Resolved PVO source provenance + (passive) seed-staleness for the model section.

    Always discloses the PVO source provenance (kind/hashes/as-of/paths) so the digest can
    show which artifact backed the vintage (DQ-A). The §3.6 ``seed_staleness`` drift block is
    surfaced ONLY when ``promote_recommended`` is True (silent on quiet drift — no nagging).
    A present-but-unverified runtime is DISCLOSED as ``not_ready`` (a fault, never silent —
    DQ-D), mirroring the feature-freshness honest-uncertainty contract. The block reads the
    pre-computed staleness O(1) from the resolver metadata (no PVO JSON diff here).
    ``decision_supported`` stays False and no market field appears.
    """
    try:
        resolved = resolve_pvo_source(
            seed_paths={"pvo": _PVO_SEED_PATH, "coverage": _PVO_SEED_COVERAGE_PATH},
            runtime_dir=_PVO_RUNTIME_DIR,
        )
    except PvoSourceNotReadyError as exc:
        return {
            "decision_supported": False,
            "pvo_source_status": "not_ready",
            "pvo_source_kind": None,
            "aborted_reason": str(exc),
        }
    meta = resolved.metadata()
    seed_staleness = meta.get("seed_staleness")
    # Silent-unless-promote_recommended: only surface the drift metrics when the tripwire
    # recommends a manual promotion review; otherwise quiet (None).
    if not (isinstance(seed_staleness, dict) and seed_staleness.get("promote_recommended")):
        seed_staleness = None
    return {
        "decision_supported": False,
        "pvo_source_kind": meta["pvo_source_kind"],
        "pvo_sha256": meta["pvo_sha256"],
        "coverage_sha256": meta["coverage_sha256"],
        "source_as_of": meta["source_as_of"],
        "pvo_path": meta["pvo_path"],
        "coverage_path": meta["coverage_path"],
        "seed_staleness": seed_staleness,
    }


def _report_overall_status(diff_status: str, structural_status: str) -> str:
    if diff_status == "unavailable":
        return "unavailable"
    if diff_status == "ok" and structural_status == "ok":
        return "ok"
    return "degraded"


# ── structural current-context assembler ─────────────────────────────────────
def assemble_structural_context(
    *,
    team_posture_path: Path | str,
    team_value_matrix_path: Path | str,
    league_opportunity_path: Path | str,
    roster_cut_report_path: Path | str,
    sleeper_snapshot_path: Path | str,
    generated_at: datetime,
) -> dict[str, Any]:
    """Assemble the allowlisted current-context view from the five injected artifacts.

    David's roster id is resolved from the current Sleeper snapshot and used to focus
    the posture / team-value / drop-pressure summaries. A missing artifact degrades
    only its own section (``unavailable``), never the whole context.
    """
    snapshot = _load_json(sleeper_snapshot_path)
    david_roster_id = snapshot.get("david_roster_id") if snapshot else None

    sections = {
        "team_posture": _build_team_posture_section(
            team_posture_path, david_roster_id, generated_at
        ),
        "team_value": _build_team_value_section(
            team_value_matrix_path, david_roster_id, generated_at
        ),
        "league_opportunity": _build_league_opportunity_section(
            league_opportunity_path, generated_at
        ),
        "drop_pressure": _build_drop_pressure_section(
            roster_cut_report_path, generated_at
        ),
        "sleeper_snapshot": _build_sleeper_snapshot_section(
            sleeper_snapshot_path, david_roster_id, generated_at
        ),
    }
    status = "ok" if all(s["status"] == "ok" for s in sections.values()) else "degraded"
    return {
        "status": status,
        "decision_supported": False,
        "current_not_delta": True,
        "sections": sections,
    }


def _build_team_posture_section(
    path: Path | str, david_roster_id: Any, generated_at: datetime
) -> dict[str, Any]:
    artifact = _load_json(path)
    if artifact is None:
        return _unavailable_section(path)
    section = _section_envelope(path, artifact, generated_at)
    teams = artifact.get("teams") or []
    david = _find_by_roster_id(teams, david_roster_id)
    section.update(
        {
            "david_roster_id": david_roster_id,
            "david_team_name": _team_name(david),
            "david_posture": _posture_label(david),
            "team_count": len(teams),
        }
    )
    return section


def _build_team_value_section(
    path: Path | str, david_roster_id: Any, generated_at: datetime
) -> dict[str, Any]:
    artifact = _load_json(path)
    if artifact is None:
        return _unavailable_section(path)
    section = _section_envelope(path, artifact, generated_at)
    david = _find_by_roster_id(artifact.get("teams") or [], david_roster_id)
    views = (david or {}).get("team_value_views") or {}
    # Allowlisted real team_value_views keys; market_overlay_total is a MARKET field
    # and is deliberately EXCLUDED (market stays overlay-only, out of this summary).
    section["david_value_summary"] = {
        "roster_id": david_roster_id,
        "team_name": _team_name(david),
        "posture_label": _posture_label(david),
        "depth_credit_xvar": views.get("depth_credit_xvar"),
        "lineup_xvar": views.get("lineup_xvar"),
        "starter_weighted_xvar": views.get("starter_weighted_xvar"),
        "top_n_xvar": views.get("top_n_xvar"),
        "total_xvar_capped": views.get("total_xvar_capped"),
    }
    return section


def _build_league_opportunity_section(
    path: Path | str, generated_at: datetime
) -> dict[str, Any]:
    artifact = _load_json(path)
    if artifact is None:
        return _unavailable_section(path)
    section = _section_envelope(path, artifact, generated_at)
    partners = artifact.get("partner_rankings") or []
    cards = artifact.get("cards") or []
    section["top_partner_rankings"] = [
        {
            "counterparty_roster_id": p.get("counterparty_roster_id"),
            "counterparty_team_name": p.get("counterparty_team_name"),
            "partner_score": p.get("partner_score"),
            "matched_positions": p.get("matched_positions"),
        }
        for p in partners[:_STRUCTURAL_TOP_K]
    ]
    section["top_cards"] = [
        {
            "card_id": c.get("card_id"),
            "card_type": c.get("card_type"),
            "asset_name": (c.get("asset") or {}).get("full_name"),
            "opportunity_score": c.get("opportunity_score"),
            "recommended_drop_name": (c.get("recommended_drop") or {}).get("full_name"),
        }
        for c in cards[:_STRUCTURAL_TOP_K]
    ]
    return section


def _build_drop_pressure_section(
    path: Path | str, generated_at: datetime
) -> dict[str, Any]:
    artifact = _load_json(path)
    if artifact is None:
        return _unavailable_section(path)
    section = _section_envelope(path, artifact, generated_at)
    report = artifact.get("roster_cut_report") or {}
    section["summary"] = {
        "roster_id": report.get("roster_id"),
        "total_players": report.get("total_players"),
        "total_capacity": report.get("total_capacity"),
        "cuts_required": report.get("cuts_required"),
    }
    section["top_candidates"] = [
        {
            "sleeper_player_id": c.get("sleeper_player_id"),
            "player_name": c.get("full_name"),
            "position": c.get("position"),
            "cut_priority": c.get("cut_priority"),
            "dvs": c.get("dvs"),
            "xvar_pct": c.get("xvar_pct"),
        }
        for c in (report.get("cut_candidates") or [])[:_STRUCTURAL_TOP_K]
    ]
    return section


def _build_sleeper_snapshot_section(
    path: Path | str, david_roster_id: Any, generated_at: datetime
) -> dict[str, Any]:
    artifact = _load_json(path)
    if artifact is None:
        return _unavailable_section(path)
    section = _section_envelope(path, artifact, generated_at)
    rosters = artifact.get("rosters") or []
    david = _find_by_roster_id(rosters, david_roster_id)
    section["david_roster_id"] = david_roster_id
    section["david_roster_player_count"] = len(david.get("players") or []) if david else 0
    section["league_roster_count"] = len(rosters)
    return section


# ── section helpers ──────────────────────────────────────────────────────────
def _section_envelope(
    path: Path | str, artifact: dict, generated_at: datetime
) -> dict[str, Any]:
    """Standard current-context envelope: provenance + staleness caveat (no summary)."""
    captured_dt = datetime.fromisoformat(artifact["captured_at"])
    age_hours = round((generated_at - captured_dt).total_seconds() / 3600.0, 1)
    return {
        "status": "ok",
        "decision_supported": False,
        "current_not_delta": True,
        "source_path": str(path),
        "captured_at": captured_dt.isoformat(),
        "staleness_caveat": {
            "basis": "captured_at_vs_report_generated_at",
            "report_generated_at": generated_at.isoformat(),
            "age_hours": age_hours,
            "is_stale": age_hours >= _STALE_THRESHOLD_HOURS,
        },
    }


def _unavailable_section(path: Path | str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "decision_supported": False,
        "current_not_delta": True,
        "source_path": str(path),
        "aborted_reason": "missing_structural_artifact",
    }


def _team_name(team: Optional[dict]) -> Optional[str]:
    """David's team name from the real nested owner object (mirrors League Pulse).

    Surfaces only the scalar ``owner.team_name`` — never the raw owner object (which
    carries ``user_id``/``display_name``). Tolerates a plain-string owner defensively.
    """
    owner = (team or {}).get("owner")
    if isinstance(owner, dict):
        return owner.get("team_name")
    return owner if isinstance(owner, str) else None


def _posture_label(team: Optional[dict]) -> Optional[str]:
    """David's posture LABEL only — never the raw posture object (allowlist).

    The real posture is a nested object (``label``/``score``/``components``); only the
    ``label`` scalar is surfaced (mirrors League Pulse's ``posture_label``).
    """
    posture = (team or {}).get("posture")
    if isinstance(posture, dict):
        return posture.get("label")
    return posture if isinstance(posture, str) else None


def _find_by_roster_id(entries: list[dict], roster_id: Any) -> Optional[dict]:
    if roster_id is None:
        return None
    for entry in entries:
        if entry.get("roster_id") == roster_id:
            return entry
    return None


def _load_json(path: Path | str) -> Optional[dict]:
    path = Path(path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        return None
