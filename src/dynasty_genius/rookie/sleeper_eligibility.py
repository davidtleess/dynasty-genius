"""Sleeper fantasy eligibility — the authoritative placement for David's league.

Read-only public source, captured ONCE per run: ``GET https://api.sleeper.app/v1/players/nfl``
(official docs: https://docs.sleeper.com/). No credentials, no paid provider. The raw payload
is written to the run directory (gitignored, hashed in the manifest); this module extracts
only the fields that decide eligibility and reconciles them with the rookie file.

Rules the round-2 QA gap set:

* ``fantasy_positions`` is the placement authority — not the NFL position, not the draft
  table. A missing field stays UNKNOWN; it is never inferred from ``position``.
* a rostered player is in the universe whatever Sleeper's flags say;
* an ``active``/``status`` flag CLASSIFIES availability (active free / inactive free /
  unknown free); it never quietly suppresses anyone.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

__all__ = ["SLEEPER_PLAYERS_URL", "classify_availability", "extract_players", "reconcile"]

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
FIELDS = ("full_name", "position", "fantasy_positions", "active", "status", "team", "injury_status", "years_exp", "gsis_id")


def _clean(value):
    if value is None or (isinstance(value, float) and value != value):
        return None
    if isinstance(value, str):
        value = value.strip()  # Sleeper pads some ids: " 00-0035057"
        return value or None
    return value


def extract_players(payload: dict) -> pd.DataFrame:
    """One row per Sleeper player id with the eligibility fields; nothing dropped, nothing inferred."""
    rows = []
    for sleeper_id, rec in payload.items():
        rec = rec or {}
        fp = rec.get("fantasy_positions")
        rows.append({
            "sleeper_id": str(sleeper_id),
            "full_name": _clean(rec.get("full_name")) or " ".join(x for x in (rec.get("first_name"), rec.get("last_name")) if x) or None,
            "position": _clean(rec.get("position")),
            "fantasy_positions": "|".join(str(p) for p in fp) if isinstance(fp, list) and fp else None,
            "active": _clean(rec.get("active")),
            "status": _clean(rec.get("status")),
            "team": _clean(rec.get("team")),
            "injury_status": _clean(rec.get("injury_status")),
            "years_exp": _clean(rec.get("years_exp")),
            "gsis_id": _clean(rec.get("gsis_id")),
        })
    frame = pd.DataFrame(rows, columns=["sleeper_id", *FIELDS]).astype(object)
    return frame.where(frame.notna(), None)


# Sleeper's ``status`` vocabulary seen live (2026-09-06): Active, Inactive, Injured Reserve,
# Physically Unable to Perform, Non Football Injury, Practice Squad, and missing. Everything
# but Inactive is an NFL roster status; Inactive is "not on an NFL roster" (cut, retired,
# unsigned). Neither suppresses anyone — a class is carried, never a deletion.
NFL_ROSTER_STATUSES = {"active", "injured reserve", "physically unable to perform", "non football injury", "practice squad"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def classify_availability(row, rostered_ids: set[str]) -> str:
    """rostered → always in the universe; else by Sleeper's own flags, unknown when absent."""
    sleeper_id = str(row.name) if row.name is not None and "sleeper_id" not in row else str(row.get("sleeper_id"))
    if sleeper_id in rostered_ids:
        return "rostered"
    active, status = row.get("active"), row.get("status")
    if active is None and status is None:
        return "unknown_free"
    if active is False or (status is not None and str(status).lower() == "inactive"):
        return "inactive_free"
    if active is True and (status is None or str(status).lower() in NFL_ROSTER_STATUSES):
        return "active_free"
    return "unknown_free"


def _norm(name) -> str:
    """Lower-case letters only, suffixes (Jr., II, ...) dropped: "Omar Cooper Jr." == "Omar Cooper"."""
    parts = [p for p in re.sub(r"[^a-z ]", "", str(name or "").lower()).split() if p not in SUFFIXES]
    return "".join(parts)


def _last(name) -> str:
    parts = [p for p in re.sub(r"[^a-z ]", "", str(name or "").lower()).split() if p not in SUFFIXES]
    return parts[-1] if parts else ""


def reconcile(
    players: pd.DataFrame,
    *,
    rookies: pd.DataFrame,
    extra_ids: Iterable[str] = (),
    pool_ids: Iterable[str] = (),
    rostered_ids: Iterable[str] = (),
) -> pd.DataFrame:
    """Rookies (by gsis, then name + position), plus named extra ids and the candidate pool,
    each with Sleeper's eligibility and an availability class. Unmatched rookies are kept
    with ``match_basis = "unmatched"`` and eligibility unknown."""
    rostered = {str(i) for i in rostered_ids}
    by_id = players.set_index("sleeper_id")
    by_gsis = {g: sid for sid, g in zip(players["sleeper_id"], players["gsis_id"]) if g}
    by_name, by_last = {}, {}
    for sid, name, pos, team, yexp in zip(players["sleeper_id"], players["full_name"], players["position"], players["team"], players["years_exp"]):
        by_name.setdefault((_norm(name), pos), []).append(sid)
        by_name.setdefault((_norm(name), None), []).append(sid)
        if yexp in (0, 0.0):
            by_last.setdefault((_last(name), team, pos), []).append(sid)
    out = []

    def row_for(sid, source, basis, rookie=None):
        rec = by_id.loc[sid] if sid in by_id.index else None
        fp = rec["fantasy_positions"] if rec is not None else None
        entry = {
            "sleeper_id": sid, "source": source, "match_basis": basis,
            "sleeper_name": rec["full_name"] if rec is not None else None,
            "sleeper_position": rec["position"] if rec is not None else None,
            "fantasy_positions": fp,
            "league_eligibility": fp if fp else "unknown",
            "active": rec["active"] if rec is not None else None,
            "status": rec["status"] if rec is not None else None,
            "team": rec["team"] if rec is not None else None,
            "injury_status": rec["injury_status"] if rec is not None else None,
            "years_exp": rec["years_exp"] if rec is not None else None,
            "availability_class": classify_availability(rec, rostered) if rec is not None else ("rostered" if sid in rostered else "unknown_free"),
        }
        if rookie is not None:
            entry.update({"my_gsis_id": rookie.get("gsis_id"), "name": rookie.get("name"), "draft_season": rookie.get("draft_season"),
                          "pick": rookie.get("pick"), "draft_position": rookie.get("position"),
                          "position_current_nflverse": rookie.get("position_current")})
        return entry

    for _, rk in rookies.iterrows():
        sid, basis = None, "unmatched"
        if rk.get("gsis_id") in by_gsis:
            sid, basis = by_gsis[rk["gsis_id"]], "gsis_id"
        else:
            cands = by_name.get((_norm(rk.get("name")), rk.get("position"))) or by_name.get((_norm(rk.get("name")), rk.get("position_current"))) \
                or by_name.get((_norm(rk.get("name")), None)) or []
            cands = list(dict.fromkeys(cands))
            if len(cands) == 1:
                sid, basis = cands[0], "name+position"
            elif len(cands) > 1:
                basis = f"ambiguous_name({len(cands)})"
            else:
                # nickname on one side ("Matthew" / "Matt"): last name + team + position among rookies, unique only
                fallback = list(dict.fromkeys(by_last.get((_last(rk.get("name")), rk.get("team"), rk.get("position")), [])
                                              or by_last.get((_last(rk.get("name")), rk.get("team"), rk.get("position_current")), [])))
                if len(fallback) == 1:
                    sid, basis = fallback[0], "last_name+team+position+rookie"
        if sid is None:
            out.append({**row_for("", "rookie", basis, rk), "sleeper_id": None})
        else:
            out.append(row_for(sid, "rookie", basis, rk))
    seen = {e["sleeper_id"] for e in out}
    for sid in (str(i) for i in extra_ids):
        if sid not in seen:
            out.append(row_for(sid, "extra", "sleeper_id"))
            seen.add(sid)
    for sid in (str(i) for i in pool_ids):
        if sid not in seen:
            out.append(row_for(sid, "candidate_pool", "sleeper_id"))
            seen.add(sid)
    return pd.DataFrame(out)
