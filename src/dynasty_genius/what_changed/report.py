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

from src.dynasty_genius.what_changed.daily_diff import build_daily_what_changed_diff

_SCHEMA_VERSION = "war_room_2_what_changed_v1"
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
            "david_team_name": david.get("owner") if david else None,
            "david_posture": david.get("posture") if david else None,
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
    section["david_value_summary"] = {
        "roster_id": david_roster_id,
        "team_name": david.get("owner") if david else None,
        "posture": david.get("posture") if david else None,
        "raw_total_xvar": views.get("raw_total_xvar"),
        "starter_xvar": views.get("starter_xvar"),
        "bench_xvar": views.get("bench_xvar"),
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
            "asset_name": (c.get("asset") or {}).get("name"),
            "opportunity_score": c.get("opportunity_score"),
            "recommended_drop_name": (c.get("recommended_drop") or {}).get("name"),
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
