"""War Room #2 T1 — pure Daily What-Changed diff engine.

A pure read/diff layer over the two injected forward-capture PIT stores and an
injected *current* Sleeper snapshot. It computes day-over-day market deltas (focused
slices: David's roster + a capped top-N mover list), reports honest model quiet
states keyed on the ``(semantic_output_hash, provenance_hash)`` vintage pair, and
degrades per-source independently.

Deliberately NOT in scope for T1 (T2/T3 own these): the overwrite-latest report
emit, the structural-context assembler, the read-only API, and any frontend. This
module performs no output-file side effects and reads no real-fs / wall-clock state
beyond the injected paths.

Sign conventions (locked, spec C3):
- ``value_delta = latest - prior`` → positive = ``rose`` (value went up).
- ``*_rank_delta = latest - prior`` → negative = ``improved`` (toward rank #1).

Guardrails: ``decision_supported`` is always ``False``; market content is a
descriptive overlay only; no market field is ever surfaced into a model/PVO path.

Design spec: docs/superpowers/specs/2026-06-24-war-room-2-daily-what-changed-diff-design.md
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

_FC_JOINABLE_TABLE = "fc_forward_capture_joinable"
_MODEL_JOINABLE_TABLE = "model_forward_capture_joinable"

# A section is "healthy" (does not drag the overall report to ``degraded``) when it
# either reports real movement (``ok``) or an HONEST no-movement state. Only true data
# insufficiency / unavailability degrades the overall status.
_HEALTHY_SECTION_STATUSES = frozenset(
    {"ok", "baseline_holding", "vintage_changed_no_score_delta"}
)


def build_daily_what_changed_diff(
    *,
    fc_db_path: Path | str,
    model_db_path: Path | str,
    sleeper_snapshot_path: Path | str,
    top_n: int = 25,
) -> dict[str, Any]:
    """Compute the day-over-day What-Changed diff over the injected PIT stores.

    All inputs are injected paths (no module-level fs/clock coupling). Each source
    section degrades independently: one source's insufficiency never aborts another.
    Returns a plain dict; emits no files (the report writer is T2).
    """
    market = _build_market_section(
        fc_db_path=Path(fc_db_path),
        sleeper_snapshot_path=Path(sleeper_snapshot_path),
        top_n=top_n,
    )
    model = _build_model_section(model_db_path=Path(model_db_path))

    if market["status"] == "unavailable":
        overall_status = "unavailable"
    elif (
        market["status"] in _HEALTHY_SECTION_STATUSES
        and model["status"] in _HEALTHY_SECTION_STATUSES
    ):
        overall_status = "ok"
    else:
        overall_status = "degraded"

    return {
        # Descriptive overlay only — never a decision-grade verdict (recursive guard
        # is enforced again at the report/API layers in T2/T3).
        "decision_supported": False,
        "overall_status": overall_status,
        "market": market,
        "model": model,
    }


# ── market (FantasyCalc overlay) ─────────────────────────────────────────────
def _build_market_section(
    *,
    fc_db_path: Path,
    sleeper_snapshot_path: Path,
    top_n: int,
) -> dict[str, Any]:
    """Day-over-day FC market deltas, focused on David's roster + capped top movers.

    Fails closed (``status='unavailable'``) when the current Sleeper snapshot — the
    source of David's roster membership — is missing or unusable; reports
    ``insufficient_history`` when fewer than two FC capture dates exist.
    """
    roster_ids = _load_david_roster_ids(sleeper_snapshot_path)
    if roster_ids is None:
        return {
            "status": "unavailable",
            "decision_supported": False,
            "aborted_reason": "missing_sleeper_snapshot",
            "market_source": "fantasycalc_overlay",
        }

    rows = _read_table_rows(fc_db_path, _FC_JOINABLE_TABLE)
    dates = sorted({r["snapshot_date"] for r in rows if r.get("snapshot_date")})
    if len(dates) < 2:
        return {
            "status": "insufficient_history",
            "decision_supported": False,
            "comparison_window": {"status": "insufficient_history"},
            "market_source": "fantasycalc_overlay",
        }

    from_date, to_date = dates[-2], dates[-1]
    prior = {r["sleeper_id"]: r for r in rows if r["snapshot_date"] == from_date}
    latest = {r["sleeper_id"]: r for r in rows if r["snapshot_date"] == to_date}

    in_both = set(prior) & set(latest)
    entered_ids = set(latest) - set(prior)
    exited_ids = set(prior) - set(latest)

    deltas_by_id = {
        sid: _market_delta_row(sid, prior[sid], latest[sid]) for sid in in_both
    }

    # Roster focus: every roster player present in both snapshots, even if flat.
    roster_deltas = sorted(
        (deltas_by_id[sid] for sid in in_both if sid in roster_ids),
        key=lambda row: abs(row["value_delta"]),
        reverse=True,
    )

    # Movers = players whose market value actually changed; ranked by magnitude and
    # capped at top_n. The full universe is NEVER dumped — only the capped slice plus
    # an honest total count.
    movers = sorted(
        (row for row in deltas_by_id.values() if row["value_delta"] != 0),
        key=lambda row: abs(row["value_delta"]),
        reverse=True,
    )

    return {
        "status": "ok",
        "decision_supported": False,
        "comparison_window": {"from_date": from_date, "to_date": to_date},
        "roster_deltas": roster_deltas,
        "top_movers": movers[:top_n],
        "total_movers_count": len(movers),
        "entered": [
            {"sleeper_id": sid, "player_key": latest[sid]["player_key"]}
            for sid in sorted(entered_ids)
        ],
        "exited": [
            {"sleeper_id": sid, "player_key": prior[sid]["player_key"]}
            for sid in sorted(exited_ids)
        ],
        "market_source": "fantasycalc_overlay",
    }


def _market_delta_row(sleeper_id: str, prior: dict, latest: dict) -> dict[str, Any]:
    value_delta = _int(latest.get("value")) - _int(prior.get("value"))
    overall_rank_delta = _int(latest.get("overall_rank")) - _int(prior.get("overall_rank"))
    position_rank_delta = _int(latest.get("position_rank")) - _int(prior.get("position_rank"))
    return {
        "sleeper_id": sleeper_id,
        "player_key": latest.get("player_key"),
        "player_name": latest.get("player_name"),
        "position": latest.get("position"),
        "value_delta": value_delta,
        "value_delta_direction": _value_direction(value_delta),
        "overall_rank_delta": overall_rank_delta,
        "overall_rank_delta_direction": _rank_direction(overall_rank_delta),
        "position_rank_delta": position_rank_delta,
        "position_rank_delta_direction": _rank_direction(position_rank_delta),
    }


# ── model (PVO/DVS/xVAR — quiet until distinct vintages exist) ────────────────
def _build_model_section(*, model_db_path: Path) -> dict[str, Any]:
    """Day-over-day model deltas, honest about vintage-driven quiet states.

    The model only "moves" when a new ``(semantic_output_hash, provenance_hash)``
    vintage produces different scores. Until then it reports ``baseline_holding``
    (vintage unchanged) or ``vintage_changed_no_score_delta`` (new vintage, identical
    scores) — never fabricated movement — and ``insufficient_history`` below two dates.
    """
    rows = _read_table_rows(model_db_path, _MODEL_JOINABLE_TABLE)
    dates = sorted({r["capture_date"] for r in rows if r.get("capture_date")})
    if len(dates) < 2:
        return {
            "status": "insufficient_history",
            "decision_supported": False,
            "comparison_window": {"status": "insufficient_history"},
            "deltas": [],
        }

    from_date, to_date = dates[-2], dates[-1]
    prior_rows = [r for r in rows if r["capture_date"] == from_date]
    latest_rows = [r for r in rows if r["capture_date"] == to_date]

    # A clean capture is a single vintage per date. If either compared date carries
    # more than one (semantic_output_hash, provenance_hash) pair — legitimately
    # possible since the store key includes the vintage pair, e.g. a same-day manual
    # re-capture after a model/feature change — both the reported window vintage and
    # the per-player delta selection become ambiguous. Refuse to emit an internally
    # inconsistent comparison; degrade with an explicit, honest status (no fabricated
    # deltas). Same-day multi-vintage comparison semantics are a later increment.
    ambiguous_dates = [
        date
        for date, date_rows in ((from_date, prior_rows), (to_date, latest_rows))
        if len(_distinct_vintages(date_rows)) > 1
    ]
    if ambiguous_dates:
        return {
            "status": "model_multi_vintage_ambiguous",
            "decision_supported": False,
            "comparison_window": {
                "status": "model_multi_vintage_ambiguous",
                "from_date": from_date,
                "to_date": to_date,
                "ambiguous_dates": ambiguous_dates,
            },
            "deltas": [],
        }

    from_vintage = _date_vintage(prior_rows)
    to_vintage = _date_vintage(latest_rows)
    vintage_changed = from_vintage != to_vintage

    comparison_window = {
        "from_date": from_date,
        "to_date": to_date,
        "from_vintage": dict(zip(("semantic_output_hash", "provenance_hash"), from_vintage)),
        "to_vintage": dict(zip(("semantic_output_hash", "provenance_hash"), to_vintage)),
    }

    deltas = _model_score_deltas(prior_rows, latest_rows) if vintage_changed else []

    if not vintage_changed:
        status = "baseline_holding"
        deltas = []
    elif not deltas:
        status = "vintage_changed_no_score_delta"
    else:
        status = "ok"

    return {
        "status": status,
        "decision_supported": False,
        "vintage_changed": vintage_changed,
        "comparison_window": comparison_window,
        "deltas": deltas,
    }


def _distinct_vintages(rows: list[dict]) -> set[tuple[Optional[str], Optional[str]]]:
    """The distinct ``(semantic_output_hash, provenance_hash)`` pairs in a row set."""
    return {(r.get("semantic_output_hash"), r.get("provenance_hash")) for r in rows}


def _date_vintage(rows: list[dict]) -> tuple[Optional[str], Optional[str]]:
    """The single ``(semantic_output_hash, provenance_hash)`` vintage for a date.

    Callers must have already rejected multi-vintage dates (see
    ``model_multi_vintage_ambiguous``); this returns the lone pair, defaulting to
    ``(None, None)`` for an empty set.
    """
    pairs = _distinct_vintages(rows)
    return min(pairs) if pairs else (None, None)


def _model_score_deltas(prior_rows: list[dict], latest_rows: list[dict]) -> list[dict]:
    """Per-player model score deltas for players present in both captures.

    Empty when no score actually moved (so a new vintage with identical scores is
    reported as ``vintage_changed_no_score_delta`` rather than fabricated movement).
    """
    prior = {r["player_key"]: r for r in prior_rows}
    latest = {r["player_key"]: r for r in latest_rows}
    deltas: list[dict] = []
    for key in sorted(set(prior) & set(latest)):
        dvs_delta = _float(latest[key].get("dynasty_value_score")) - _float(
            prior[key].get("dynasty_value_score")
        )
        dvs_pct_delta = _float(latest[key].get("dvs_pct")) - _float(prior[key].get("dvs_pct"))
        xvar_delta = _float(latest[key].get("xvar")) - _float(prior[key].get("xvar"))
        if dvs_delta == 0 and dvs_pct_delta == 0 and xvar_delta == 0:
            continue
        deltas.append(
            {
                "sleeper_id": latest[key].get("sleeper_id"),
                "player_key": key,
                "player_name": latest[key].get("player_name"),
                "position": latest[key].get("position"),
                "dynasty_value_score_delta": dvs_delta,
                "dynasty_value_score_delta_direction": _value_direction(dvs_delta),
                "dvs_pct_delta": dvs_pct_delta,
                "xvar_delta": xvar_delta,
            }
        )
    return deltas


# ── shared helpers ───────────────────────────────────────────────────────────
def _load_david_roster_ids(sleeper_snapshot_path: Path) -> Optional[set[str]]:
    """David's current roster sleeper-ids from the injected snapshot, or None.

    None signals fail-closed (missing/malformed snapshot or no matching roster) so
    the market section reports ``unavailable`` rather than silently inventing a roster.
    """
    if not sleeper_snapshot_path.exists():
        return None
    try:
        snapshot = json.loads(sleeper_snapshot_path.read_text())
    except (ValueError, OSError):
        return None
    david_roster_id = snapshot.get("david_roster_id")
    rosters = snapshot.get("rosters")
    if david_roster_id is None or not isinstance(rosters, list):
        return None
    for roster in rosters:
        if roster.get("roster_id") == david_roster_id:
            players = roster.get("players") or []
            return {str(p) for p in players}
    return None


def _read_table_rows(db_path: Path, table: str) -> list[dict[str, Any]]:
    """Read every row of a joinable PIT table; empty on missing db/table (degrade)."""
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608 (fixed table name)
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def _value_direction(delta: float) -> str:
    if delta > 0:
        return "rose"
    if delta < 0:
        return "fell"
    return "unchanged"


def _rank_direction(delta: float) -> str:
    # Rank #1 is best, so a negative delta (moved toward #1) is an improvement.
    if delta < 0:
        return "improved"
    if delta > 0:
        return "declined"
    return "unchanged"


def _int(value: object) -> int:
    return int(value) if value is not None else 0


def _float(value: object) -> float:
    return float(value) if value is not None else 0.0
