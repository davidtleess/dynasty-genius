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


def main(out_path: Path | None = None, league_id: str = _LEAGUE_ID) -> int:
    boards = list(_fetch_league_rookie_drafts(league_id)) + _load_seed_drafts()
    classes = {b["draft_class"] for b in boards}
    rank_maps = {c: nfl_skill_ranks(c) for c in classes}

    # Per-draft provenance (spec §4) — keeps the audit trail for a thin corpus:
    # which drafts/classes contributed and where unmatched QBs came from.
    per_draft = []
    for board in boards:
        p, bm, bu = _board_qb_promotions(board, rank_maps.get(board["draft_class"], {}))
        per_draft.append(
            {
                "draft_class": board["draft_class"],
                "source": board.get("source") or board.get("league") or "unknown",
                "n_qbs_matched": bm,
                "n_qbs_unmatched": bu,
                "promotions": sorted(p),
            }
        )

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
        f"matched={matched}, unmatched={unmatched}, drafts={len(boards)})"
    )
    return k


if __name__ == "__main__":
    main()
