#!/usr/bin/env python3.14
"""Phase 24 — calibrate the SF-QB ordering knob (sf_qb_promote_slots).

Measures per-QB slot promotion (nfl_skill_rank - ff_slot) across real SF rookie
drafts (David's league via the Sleeper previous_league_id chain + a seed fixture)
and recommends a global K = clamp(round_half_up(median), 0, 3). Read-only Sleeper.
Does NOT change the production curve — the recommended K is reported for David's
explicit approval before any sf_qb_promote_slots / curve regeneration.

Usage: .venv/bin/python3.14 scripts/calibrate_sf_qb_knob.py
"""
from __future__ import annotations

import asyncio
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402  (import after sys.path setup — scripts convention)

from app.data.sleeper import (  # noqa: E402
    get_draft,
    get_draft_picks,
    get_league,
    get_league_drafts,
)

_LEAGUE_ID = "1314363401744416768"
_SEED_PATH = _ROOT / "resources" / "seed_rookie_drafts.json"
_BYO_PATH = _ROOT / "resources" / "sf_rookie_draft_ids.json"
_OUTCOMES_CSV = _ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
_PROSPECT_CARDS = _ROOT / "resources" / "prospect_cards.json"
_SKILL = {"QB", "RB", "WR", "TE"}
_BOARD_SIZE = 36
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


# ── Pure helpers ────────────────────────────────────────────────────────────


def round_half_up(m: float) -> int:
    """Half-up rounding (math.floor(m + 0.5)) — NOT Python's banker round()."""
    return math.floor(m + 0.5)


def recommend_k(promotions: list[float]) -> int:
    """K = clamp(round_half_up(median(promotions)), 0, 3); empty -> 0."""
    if not promotions:
        return 0
    return max(0, min(3, round_half_up(statistics.median(promotions))))


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, drop generational suffixes."""
    cleaned = re.sub(r"[^a-z0-9 ]", "", (name or "").lower())
    tokens = [t for t in cleaned.split() if t not in _SUFFIXES]
    return " ".join(tokens)


def is_rookie_draft(draft: dict) -> bool:
    """A completed rookie draft: status complete + small round count (excludes startup)."""
    rounds = (draft.get("settings") or {}).get("rounds", 99)
    return draft.get("status") == "complete" and int(rounds) <= 6


def nfl_skill_ranks_from_outcomes(df: "pd.DataFrame", draft_class: int) -> dict[str, int]:
    """{normalized_name: nfl_skill_rank} = first-36 skill players by NFL pick for a class."""
    rows = df[(df["season"] == draft_class) & (df["position"].isin(_SKILL))]
    rows = rows.sort_values("pick").head(_BOARD_SIZE)
    return {
        normalize_name(str(r["pfr_player_name"])): i
        for i, (_, r) in enumerate(rows.iterrows(), start=1)
    }


def nfl_skill_ranks(draft_class: int) -> dict[str, int]:
    """NFL-skill-rank map for a class: prospect_cards for 2026, outcomes CSV otherwise."""
    if draft_class == 2026:
        cards = json.loads(_PROSPECT_CARDS.read_text())
        rows = [
            c for c in cards
            if c.get("draft_class") == 2026 and c.get("position") in _SKILL
            and isinstance(c.get("nfl_draft_pick"), (int, float))
        ]
        rows.sort(key=lambda c: c["nfl_draft_pick"])
        return {
            normalize_name(c["full_name"]): i
            for i, c in enumerate(rows[:_BOARD_SIZE], start=1)
        }
    df = pd.read_csv(_OUTCOMES_CSV)
    return nfl_skill_ranks_from_outcomes(df, draft_class)


def _board_qbs(board: dict) -> list[tuple[int, str]]:
    """Return (ff_slot, player_name) for QBs in a board (seed `qbs` or live `picks` shape)."""
    if "qbs" in board:
        return [(int(q["slot"]), q["player_name"]) for q in board["qbs"]]
    return [
        (int(p["ff_slot"]), p["player_name"])
        for p in board.get("picks", [])
        if p.get("position") == "QB"
    ]


def _board_qb_promotions(board: dict, ranks: dict[str, int]):
    """One board's (promotions, matched, unmatched) given its class rank map."""
    promotions: list[float] = []
    matched = 0
    unmatched = 0
    for ff_slot, name in _board_qbs(board):
        rank = ranks.get(normalize_name(name))
        if rank is None:
            unmatched += 1
            continue
        promotions.append(float(rank - ff_slot))
        matched += 1
    return promotions, matched, unmatched


def qb_promotions(boards: list[dict], rank_maps: dict[int, dict[str, int]]):
    """Per-QB promotion = nfl_skill_rank - ff_slot. Returns (promotions, matched, unmatched)."""
    promotions: list[float] = []
    matched = 0
    unmatched = 0
    for board in boards:
        p, bm, bu = _board_qb_promotions(board, rank_maps.get(board["draft_class"], {}))
        promotions.extend(p)
        matched += bm
        unmatched += bu
    return promotions, matched, unmatched


# ── Live fetch (read-only Sleeper; monkeypatched in tests) ───────────────────


async def _collect_rookie_boards(league_id: str) -> list[dict]:
    boards: list[dict] = []
    current: str | None = league_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        league = await get_league(current)
        season = int(league.get("season"))
        for d in await get_league_drafts(current):
            draft = await get_draft(d["draft_id"])
            if not is_rookie_draft(draft):
                continue
            draft_class = int(draft.get("season") or season)
            picks = await get_draft_picks(d["draft_id"])
            boards.append(
                {
                    "draft_class": draft_class,
                    "draft_id": d["draft_id"],
                    "source": f"sleeper_league:{current}",
                    "picks": [
                        {
                            "ff_slot": int(p["pick_no"]),
                            "player_name": (
                                f"{(p.get('metadata') or {}).get('first_name', '')} "
                                f"{(p.get('metadata') or {}).get('last_name', '')}".strip()
                            ),
                            "position": (p.get("metadata") or {}).get("position"),
                        }
                        for p in picks
                    ],
                }
            )
        current = league.get("previous_league_id")
    return boards


def _fetch_league_rookie_drafts(league_id: str) -> list[dict]:
    """Live read-only Sleeper fetch (monkeypatched in tests)."""
    return asyncio.run(_collect_rookie_boards(league_id))


async def _collect_byo_boards(draft_ids: list[str], chain_draft_ids: set[str]):
    """Gate + build curated BYO drafts. Returns (boards, rejections). Fail-closed; never silent."""
    boards: list[dict] = []
    rejections: list[dict] = []
    for did in draft_ids:
        if did in chain_draft_ids:
            rejections.append({"draft_id": did, "reason": "duplicate_existing_draft"})
            continue
        try:
            draft = await get_draft(did)
            league_id = draft.get("league_id")
            if not league_id:
                rejections.append({"draft_id": did, "reason": "missing_league_id"})
                continue
            league = await get_league(league_id)
        except Exception:
            rejections.append({"draft_id": did, "reason": "fetch_failed"})
            continue
        # Gate on draft+league BEFORE fetching picks — a hard-gate reject must never be
        # mislabeled fetch_failed, and we skip the picks read for excluded drafts.
        accepted, reason, fmt = gate_byo_draft(draft, league)
        if not accepted:
            rejections.append({"draft_id": did, "reason": reason, "format_meta": fmt})
            continue
        try:
            picks = await get_draft_picks(did)
        except Exception:
            rejections.append({"draft_id": did, "reason": "fetch_failed", "format_meta": fmt})
            continue
        board, breason = _build_byo_board(did, draft, league, picks)
        if board is None:
            rejections.append({"draft_id": did, "reason": breason, "format_meta": fmt})
            continue
        boards.append(board)
    return boards, rejections


def _fetch_byo_drafts(draft_ids: list[str], chain_draft_ids: set[str]):
    """Live read-only Sleeper fetch for BYO drafts (monkeypatched in tests)."""
    return asyncio.run(_collect_byo_boards(draft_ids, chain_draft_ids))


def _load_seed_drafts() -> list[dict]:
    return json.loads(_SEED_PATH.read_text())["drafts"]


def _load_byo_draft_ids() -> tuple[list[str], list[str]]:
    """(unique_ordered_ids, dropped_within_file_duplicates). Missing/empty/malformed -> ([], [])."""
    if not _BYO_PATH.exists():
        return [], []
    try:
        raw = (json.loads(_BYO_PATH.read_text()).get("draft_ids") or [])
    except Exception:
        return [], []
    seen: set[str] = set()
    unique: list[str] = []
    dupes: list[str] = []
    for did in raw:
        did = str(did)
        if did in seen:
            dupes.append(did)
            continue
        seen.add(did)
        unique.append(did)
    return unique, dupes


_SF_TOKEN = "SUPER_FLEX"


def is_superflex(league: dict) -> bool:
    """Exact-token SF test on roster_positions (never fuzzy draft metadata)."""
    return _SF_TOKEN in (league.get("roster_positions") or [])


def is_twelve_team(league: dict) -> bool:
    """12-team test; total_rosters coerced to int; non-int/missing -> False."""
    try:
        return int(league.get("total_rosters")) == 12
    except (TypeError, ValueError):
        return False


def league_format_metadata(league: dict) -> dict:
    """Recorded-only format snapshot (never a gate). Reads Sleeper `scoring_settings`."""
    scoring = league.get("scoring_settings") or {}
    return {
        "superflex": is_superflex(league),
        "total_rosters": league.get("total_rosters"),
        "ppr": scoring.get("rec"),
        "te_premium": (scoring.get("bonus_rec_te") or 0) > 0,
    }


def gate_byo_draft(draft: dict, league: dict) -> tuple[bool, str | None, dict]:
    """Draft+league gate ONLY (no picks). Returns (accepted, reason, format_meta)."""
    fmt = league_format_metadata(league)
    if draft.get("status") != "complete":
        return False, "not_rookie", fmt
    rounds = (draft.get("settings") or {}).get("rounds")
    try:
        rounds_int = int(rounds)
    except (TypeError, ValueError):
        return False, "malformed_draft_settings", fmt
    if rounds_int > 6:
        return False, "not_rookie", fmt
    if draft.get("type") == "auction":
        return False, "unsupported_draft_type", fmt
    if not is_superflex(league):
        return False, "not_superflex", fmt
    if not is_twelve_team(league):
        return False, "not_12_team", fmt
    return True, None, fmt


def _build_byo_board(draft_id: str, draft: dict, league: dict, picks: list[dict]):
    """Build a capped BYO board or reject. Returns (board, None) | (None, reason)."""
    season = draft.get("season") or league.get("season")
    try:
        draft_class = int(season)
    except (TypeError, ValueError):
        return None, "invalid_draft_class"

    parsed: list[tuple[int, dict]] = []
    for p in picks:
        try:
            pick_no = int(p["pick_no"])
        except (TypeError, ValueError, KeyError):
            return None, "malformed_picks"
        parsed.append((pick_no, p))

    n_raw = len(parsed)
    parsed.sort(key=lambda t: t[0])
    used = [(pn, p) for pn, p in parsed if pn <= _BOARD_SIZE]
    board = {
        "draft_class": draft_class,
        "draft_id": draft_id,
        "source": f"sleeper_draft:{draft_id}",
        "format_meta": league_format_metadata(league),
        "n_picks_raw": n_raw,
        "n_picks_used": len(used),
        "n_picks_excluded_after_36": n_raw - len(used),
        "picks": [
            {
                "ff_slot": pn,
                "player_name": (
                    f"{(p.get('metadata') or {}).get('first_name', '')} "
                    f"{(p.get('metadata') or {}).get('last_name', '')}".strip()
                ),
                "position": (p.get("metadata") or {}).get("position"),
            }
            for pn, p in used
        ],
    }
    return board, None


def main(out_path: Path | None = None, league_id: str = _LEAGUE_ID) -> int:
    chain_boards = list(_fetch_league_rookie_drafts(league_id))
    seed_drafts = _load_seed_drafts()
    chain_draft_ids = {b["draft_id"] for b in chain_boards if b.get("draft_id")}

    byo_ids, byo_dupes = _load_byo_draft_ids()
    byo_boards, byo_rejections = _fetch_byo_drafts(byo_ids, chain_draft_ids)
    rejected: list[dict] = [{"draft_id": d, "reason": "duplicate_draft_id"} for d in byo_dupes]
    rejected.extend(byo_rejections)

    boards = chain_boards + seed_drafts + byo_boards
    classes = {b["draft_class"] for b in boards}
    rank_maps = {c: nfl_skill_ranks(c) for c in classes}

    # Exclude boards whose draft_class has no NFL skill-rank map (a data-coverage miss,
    # NOT a name-match miss) so they never inflate the unmatched denominator or the K math.
    surviving: list[dict] = []
    for board in boards:
        if not rank_maps.get(board["draft_class"]):
            rejected.append(
                {
                    "draft_id": board.get("draft_id"),
                    "reason": "rank_map_unavailable",
                    "draft_class": board["draft_class"],
                }
            )
        else:
            surviving.append(board)
    boards = surviving

    # Per-draft provenance (spec §4) — keeps the audit trail for a thin corpus:
    # which drafts/classes contributed and where unmatched QBs came from.
    per_draft = []
    for board in boards:
        p, bm, bu = _board_qb_promotions(board, rank_maps.get(board["draft_class"], {}))
        entry = {
            "draft_class": board["draft_class"],
            "source": board.get("source") or board.get("league") or "unknown",
            "n_qbs_matched": bm,
            "n_qbs_unmatched": bu,
            "promotions": sorted(p),
        }
        if "draft_id" in board:
            entry["draft_id"] = board["draft_id"]
        if "format_meta" in board:
            entry["format_meta"] = board["format_meta"]
        for key in ("n_picks_raw", "n_picks_used", "n_picks_excluded_after_36"):
            if key in board:
                entry[key] = board[key]
        per_draft.append(entry)

    promotions, matched, unmatched = qb_promotions(boards, rank_maps)
    k = recommend_k(promotions)
    artifact = {
        "recommended_k": k,
        "median_raw": (statistics.median(promotions) if promotions else None),
        "n_drafts": len(boards),
        "n_qbs_matched": matched,
        "n_qbs_unmatched": unmatched,
        "promotions": sorted(promotions),
        "classes": sorted(classes),
        "per_draft": per_draft,
        "rejected": rejected,
        "caveats": ["sf_qb_calibration_thin_sample"],
    }
    if out_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = (
            _ROOT / "app" / "data" / "backtest" / "phase24"
            / f"sf_qb_knob_calibration_{ts}.json"
        )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2))
    print(
        f"Wrote {out_path}; recommended_k={k} (median={artifact['median_raw']}, "
        f"matched={matched}, unmatched={unmatched}, drafts={len(boards)}, "
        f"rejected={len(rejected)})"
    )
    return k


if __name__ == "__main__":
    main()
