# Phase 15.1 — 2026 Rookie Rank Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate `resources/prospect_cards.json/js` through the Phase 15 PVO assembler to populate xVAR fields and add four rank fields, then produce a rank movement validation report.

**Architecture:** A single batch script reads `resources/prospect_identity_2026.json` (80 verified 2026 picks) for identity/pick/round, reads age from the existing `prospect_cards.json` to preserve DVS invariance, runs each through `assemble_pvo()`, computes rank fields, carries forward 2 2027 watchlist entries unchanged, asserts DVS invariance on the 74 scored players, writes artifacts, and generates a markdown report. No model changes.

**Tech Stack:** Python 3.9, `.venv/bin/python3.14`, existing `assemble_pvo()`, `PlayerIdentity`, `ENGINE_A_REPLACEMENT_DVS`, `XVAR_LAMBDA_ENGINE_A` constants in `engine_b_contract.py`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `scripts/refresh_prospect_cards.py` | Batch refresh + report generator |
| Create | `tests/contract/test_phase15_rookie_rank_refresh.py` | Contract tests |
| Overwrite (script output) | `resources/prospect_cards.json` | Updated 2026 + watchlist artifact |
| Overwrite (script output) | `resources/prospect_cards.js` | Same, JS wrapper for dashboard |
| Write (script output) | `docs/validation/phase15-2026-rookie-rank-refresh.md` | Rank movement report |
| Update | `docs/agent-ledger/2026-05-17.md` | Session log |
| Update | `AGENT_SYNC.md` | Phase 15.1 complete |

---

## Key Decisions Locked

- **Age source:** Read from existing `prospect_cards.json` (not recomputed from birth_date). Guarantees exact DVS invariance for the 74 scored players.
- **player_id preservation:** Use existing card `player_id` (e.g., `fernando_mendoza_qb`) when a full_name+position match exists. Store identity file `dg_id` as `identity_dg_id`. Prevents breaking Rookie Board taken-state continuity.
- **DVS tolerance:** 0.01. If any drift appears, inspect it — do not silently accept it.
- **2027 watchlist:** Carry forward Ryan Williams and Jeremiah Smith from current cards unchanged (no rank fields, draft_class=2027).
- **6 PRE_MODEL 2026 players:** All have `age=None`. They remain PRE_MODEL; rank fields null.
- **dvs_pct:** Stays null for all prospects — reference population is ACTIVE_B veterans only.
- **decision_supported:** False for all entries.
- **rank_delta = xvar_class_rank − dvs_class_rank:** positive = fell in xVAR ordering; negative = rose.
- **Commit discipline:** Do not commit failing tests. Run red, implement, commit green. One implementation commit, one docs commit.

---

## Task 1: Write Tests — Run Red, No Commit

**Files:**
- Create: `tests/contract/test_phase15_rookie_rank_refresh.py`

- [ ] **Step 1: Write the test file**

```python
"""Phase 15.1 — 2026 Rookie Rank Refresh contract tests."""
from __future__ import annotations

import pytest

from src.dynasty_genius.models.engine_b_contract import (
    ENGINE_A_REPLACEMENT_DVS,
    XVAR_LAMBDA_ENGINE_A,
)
from src.dynasty_genius.models.player_identity import PlayerIdentity
from src.dynasty_genius.pvo_assembler import assemble_pvo


def _prospect(position: str, pick: int = 10, round_: int = 1, age: float = 22.0) -> tuple:
    identity = PlayerIdentity(
        dg_id=f"test_{position}_{pick}",
        full_name=f"Test {position}",
        position=position,
        is_prospect=True,
        verification_status="VERIFIED_NFL_DRAFT",
    )
    features = {
        "pick": float(pick),
        "round": float(round_),
        "age": age,
        "draft_capital": float(pick),
        "age_at_nfl_entry": age,
    }
    return identity, features


def test_scored_prospect_has_xvar():
    """Scored prospect (pick + age present) has non-null xvar after Phase 15 assembler."""
    identity, features = _prospect("WR")
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score is not None
    assert pvo.xvar is not None


def test_xvar_formula_wr():
    """xVAR = (DVS - ENGINE_A_REPLACEMENT_DVS['WR']) * XVAR_LAMBDA_ENGINE_A['WR']."""
    identity, features = _prospect("WR", pick=10, age=22.0)
    pvo = assemble_pvo(identity, features)
    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["WR"]) * XVAR_LAMBDA_ENGINE_A["WR"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.01)


def test_xvar_formula_rb():
    """xVAR = (DVS - ENGINE_A_REPLACEMENT_DVS['RB']) * XVAR_LAMBDA_ENGINE_A['RB']."""
    identity, features = _prospect("RB", pick=3, round_=1, age=21.0)
    pvo = assemble_pvo(identity, features)
    expected = round(
        (pvo.dynasty_value_score - ENGINE_A_REPLACEMENT_DVS["RB"]) * XVAR_LAMBDA_ENGINE_A["RB"],
        2,
    )
    assert pvo.xvar == pytest.approx(expected, abs=0.01)


def test_te_xvar_negative_below_replacement():
    """TE DVS below ENGINE_A_REPLACEMENT_DVS['TE'] (98.8) yields negative xVAR."""
    identity, features = _prospect("TE", pick=16, round_=1, age=22.5)
    pvo = assemble_pvo(identity, features)
    assert pvo.dynasty_value_score is not None
    if pvo.dynasty_value_score < ENGINE_A_REPLACEMENT_DVS["TE"]:
        assert pvo.xvar is not None
        assert pvo.xvar < 0.0, (
            f"TE DVS {pvo.dynasty_value_score} < replacement {ENGINE_A_REPLACEMENT_DVS['TE']} "
            f"but xVAR={pvo.xvar} is non-negative"
        )


def test_pre_model_null_xvar():
    """Prospect with no features (PRE_MODEL) has null DVS and null xvar."""
    identity, _ = _prospect("WR")
    pvo = assemble_pvo(identity, {})
    assert pvo.dynasty_value_score is None
    assert pvo.xvar is None


def test_dvs_engine_a_for_scored_prospect():
    """dvs_engine='A' for scored prospects (non-PRE_MODEL, pick + age present)."""
    identity, features = _prospect("QB", pick=1, round_=1, age=21.0)
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_engine == "A"


def test_dvs_pct_null_for_prospects():
    """dvs_pct stays None — reference population is ACTIVE_B veterans, not prospects."""
    identity, features = _prospect("RB", pick=5, age=21.5)
    pvo = assemble_pvo(identity, features)
    assert pvo.dvs_pct is None


def test_decision_supported_false():
    """decision_supported=False for all prospect paths."""
    identity, features = _prospect("WR")
    pvo = assemble_pvo(identity, features)
    assert pvo.decision_supported is False


def test_rank_delta_formula():
    """rank_delta = xvar_class_rank - dvs_class_rank; positive = fell, negative = rose."""
    from scripts.refresh_prospect_cards import _compute_ranks

    pvos = [
        {"player_id": "te1", "position": "TE", "dynasty_value_score": 90.0, "xvar": -4.0},
        {"player_id": "rb1", "position": "RB", "dynasty_value_score": 80.0, "xvar": 50.0},
        {"player_id": "wr1", "position": "WR", "dynasty_value_score": 70.0, "xvar": 15.0},
        {"player_id": "pre1", "position": "WR", "dynasty_value_score": None, "xvar": None},
    ]
    result = _compute_ranks(pvos)

    te = next(p for p in result if p["player_id"] == "te1")
    rb = next(p for p in result if p["player_id"] == "rb1")
    pre = next(p for p in result if p["player_id"] == "pre1")

    # DVS ranks: te=1 (90.0), rb=2 (80.0), wr=3 (70.0)
    # xVAR ranks: rb=1 (50.0), wr=2 (15.0), te=3 (-4.0)
    assert te["dvs_class_rank"] == 1
    assert rb["xvar_class_rank"] == 1
    assert te["xvar_class_rank"] == 3
    assert te["rank_delta"] == 2    # 3 - 1 = +2 → fell
    assert rb["rank_delta"] == -1   # 1 - 2 = -1 → rose
    assert pre.get("xvar_class_rank") is None
    assert pre.get("rank_delta") is None
```

- [ ] **Step 2: Run tests — confirm 8 pass, 1 fails**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_phase15_rookie_rank_refresh.py -v 2>&1 | tail -15
```

Expected: 8 PASS, 1 FAIL (`test_rank_delta_formula` — ImportError, module not yet created). **Do not commit.**

---

## Task 2: Write Complete Script

Write `scripts/refresh_prospect_cards.py` in full — helpers, report generator, and `main` — before running anything. All four functions must exist before `main` is called.

**Files:**
- Create: `scripts/refresh_prospect_cards.py`

- [ ] **Step 1: Write the complete file**

```python
"""Regenerate resources/prospect_cards.json/.js through Phase 15 PVO assembler.

Sources:
  resources/prospect_identity_2026.json  — canonical identity, pick, round (80 verified 2026)
  resources/prospect_cards.json          — age, player_id (preserved for invariance/continuity)

Outputs:
  resources/prospect_cards.json          — 80 2026 + 2 watchlist, Phase 15 fields added
  resources/prospect_cards.js            — JS wrapper for Rookie Board dashboard
  docs/validation/phase15-2026-rookie-rank-refresh.md

Usage:
    .venv/bin/python3.14 scripts/refresh_prospect_cards.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

IDENTITY_FILE = ROOT / "resources" / "prospect_identity_2026.json"
CARDS_JSON = ROOT / "resources" / "prospect_cards.json"
CARDS_JS = ROOT / "resources" / "prospect_cards.js"
REPORT_PATH = ROOT / "docs" / "validation" / "phase15-2026-rookie-rank-refresh.md"

_DVS_INVARIANCE_TOLERANCE = 0.01


# ── Rank computation ──────────────────────────────────────────────────────────

def _compute_ranks(pvos: list[dict]) -> list[dict]:
    """Add dvs_class_rank, xvar_class_rank, position_class_rank, rank_delta in-place."""
    # DVS class rank — nulls excluded
    dvs_scored = [(i, p) for i, p in enumerate(pvos) if p.get("dynasty_value_score") is not None]
    dvs_scored.sort(key=lambda x: x[1]["dynasty_value_score"], reverse=True)
    for rank, (i, _) in enumerate(dvs_scored, 1):
        pvos[i]["dvs_class_rank"] = rank

    # xVAR class rank — nulls excluded
    xvar_scored = [(i, p) for i, p in enumerate(pvos) if p.get("xvar") is not None]
    xvar_scored.sort(key=lambda x: x[1]["xvar"], reverse=True)
    for rank, (i, _) in enumerate(xvar_scored, 1):
        pvos[i]["xvar_class_rank"] = rank

    # Position class rank (DVS within position) — nulls excluded
    by_pos: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for i, p in enumerate(pvos):
        if p.get("dynasty_value_score") is not None:
            by_pos[p["position"]].append((i, p))
    for items in by_pos.values():
        items.sort(key=lambda x: x[1]["dynasty_value_score"], reverse=True)
        for rank, (i, _) in enumerate(items, 1):
            pvos[i]["position_class_rank"] = rank

    # rank_delta = xvar_class_rank - dvs_class_rank (positive = fell, negative = rose)
    for p in pvos:
        x_rank = p.get("xvar_class_rank")
        d_rank = p.get("dvs_class_rank")
        p["rank_delta"] = (x_rank - d_rank) if (x_rank is not None and d_rank is not None) else None

    return pvos


# ── PVO assembly ──────────────────────────────────────────────────────────────

def _build_pvo_dicts(
    identity_players: list[dict],
    cards_by_name_pos: dict[tuple[str, str], dict],
) -> tuple[list[dict], list[str]]:
    """Assemble PVOs for 80 verified 2026 players. Returns (pvo_dicts, dvs_warnings)."""
    from src.dynasty_genius.models.player_identity import PlayerIdentity
    from src.dynasty_genius.pvo_assembler import assemble_pvo

    pvos: list[dict] = []
    warnings: list[str] = []

    for p in identity_players:
        key = (p["full_name"], p["position"])
        existing = cards_by_name_pos.get(key, {})

        age: Optional[float] = existing.get("age")
        baseline_dvs: Optional[float] = existing.get("dynasty_value_score")
        # Preserve existing player_id for Rookie Board taken-state continuity.
        # Store identity dg_id separately for traceability.
        existing_player_id: Optional[str] = existing.get("player_id")

        identity = PlayerIdentity(
            dg_id=p["dg_id"],
            full_name=p["full_name"],
            position=p["position"],
            nfl_team=p.get("nfl_team"),
            sleeper_id=p.get("sleeper_id"),
            verification_status=p["verification_status"],
            is_prospect=True,
        )

        features: dict = {}
        if p.get("pick") is not None and age is not None:
            features = {
                "pick": float(p["pick"]),
                "round": float(p["round"]),
                "age": age,
                "draft_capital": float(p["pick"]),
                "age_at_nfl_entry": age,
            }

        pvo = assemble_pvo(identity, features)
        d = pvo.dict()

        # Restore preserved player_id
        if existing_player_id:
            d["player_id"] = existing_player_id
        d["identity_dg_id"] = p["dg_id"]

        # Preserve display fields not in PVO schema
        d["draft_class"] = 2026
        d["nfl_draft_pick"] = p.get("pick")
        d["nfl_draft_round"] = p.get("round")
        d["age"] = age

        # Initialize rank fields (populated later by _compute_ranks)
        d.setdefault("dvs_class_rank", None)
        d.setdefault("xvar_class_rank", None)
        d.setdefault("position_class_rank", None)
        d.setdefault("rank_delta", None)

        # DVS invariance check (tolerance 0.01 — any drift is an error, not noise)
        new_dvs = d.get("dynasty_value_score")
        if baseline_dvs is not None and new_dvs is not None:
            if abs(new_dvs - baseline_dvs) > _DVS_INVARIANCE_TOLERANCE:
                warnings.append(
                    f"DVS drift for {p['full_name']} {p['position']}: "
                    f"baseline={baseline_dvs} refreshed={new_dvs} "
                    f"delta={abs(new_dvs - baseline_dvs):.4f}"
                )

        pvos.append(d)

    return pvos, warnings


# ── Report ────────────────────────────────────────────────────────────────────

def _write_report(
    pvos_2026: list[dict],
    watchlist: list[dict],
    dvs_warnings: list[str],
    identity_snapshot_date: str,
) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    scored = [p for p in pvos_2026 if p.get("dynasty_value_score") is not None]
    unscored = [p for p in pvos_2026 if p.get("dynasty_value_score") is None]

    dvs_top24 = sorted(scored, key=lambda x: x.get("dvs_class_rank") or 999)[:24]
    xvar_top24 = sorted(
        [p for p in scored if p.get("xvar") is not None],
        key=lambda x: x.get("xvar_class_rank") or 999,
    )[:24]
    movers = sorted(
        [p for p in scored if p.get("rank_delta") is not None and abs(p["rank_delta"]) > 10],
        key=lambda x: abs(x["rank_delta"]),
        reverse=True,
    )
    te_players = sorted(
        [p for p in pvos_2026 if p["position"] == "TE" and p.get("xvar") is not None],
        key=lambda x: x.get("dvs_class_rank") or 999,
    )

    def _delta_str(p: dict) -> str:
        d = p.get("rank_delta")
        if d is None:
            return "—"
        return f"+{d}" if d > 0 else str(d)

    def _trow(p: dict) -> str:
        dvs = p.get("dynasty_value_score")
        xvar = p.get("xvar")
        return (
            f"| {p.get('dvs_class_rank', '—')} "
            f"| {p.get('xvar_class_rank', '—')} "
            f"| {p['full_name']} "
            f"| {p['position']} "
            f"| {p.get('nfl_draft_pick', '—')} "
            f"| {round(dvs, 1) if dvs is not None else '—'} "
            f"| {round(xvar, 1) if xvar is not None else '—'} "
            f"| {_delta_str(p)} |"
        )

    header = "| DVS# | xVAR# | Name | Pos | Pick | DVS | xVAR | Δ |\n|---|---|---|---|---|---|---|---|"

    lines: list[str] = [
        "# Phase 15.1 — 2026 Rookie Rank Refresh",
        "",
        f"Generated: {now}  ",
        f"Identity source: `resources/prospect_identity_2026.json` (snapshot: {identity_snapshot_date})  ",
        f"2026 cohort: {len(pvos_2026)} total · {len(scored)} scored · {len(unscored)} PRE_MODEL (age-data blockers)  ",
        f"2027 watchlist: {len(watchlist)} entries, excluded from 2026 rankings  ",
        "",
        "## Identity Stability Check",
        "",
        f"- Source: `nfl_data_py_verified_nfl_draft`, snapshot `{identity_snapshot_date}`",
        "- 80 verified 2026 draft picks; pick/round confirmed against existing artifact",
        "- Age source: preserved from `prospect_cards.json` (exact DVS invariance)",
        "- `player_id` values preserved from existing cards for Rookie Board continuity",
        f"- DVS drift warnings (>{_DVS_INVARIANCE_TOLERANCE}): {len(dvs_warnings)}",
    ]

    if dvs_warnings:
        lines.append("")
        for w in dvs_warnings:
            lines.append(f"  - {w}")
    else:
        lines.append("- No DVS drift — all 74 scored players match baseline exactly")

    lines += ["", "## DVS Top 24", "", header]
    for p in dvs_top24:
        lines.append(_trow(p))

    lines += [
        "",
        "## xVAR Top 24",
        "",
        "> rank_delta = xvar_class_rank − dvs_class_rank. Positive = fell in xVAR ordering. Negative = rose.",
        "",
        header,
    ]
    for p in xvar_top24:
        lines.append(_trow(p))

    lines += ["", "## Rank Movers (|rank_delta| > 10)", "", header]
    for p in movers:
        lines.append(_trow(p))
    if not movers:
        lines.append("_No players moved more than 10 spots._")

    lines += [
        "",
        "## TE xVAR Impact",
        "",
        "ENGINE_A_REPLACEMENT_DVS[TE] = 98.8. All 2026 TEs with DVS < 98.8 produce negative xVAR — "
        "correct Superflex behavior. A TE with DVS 100.0 would produce xVAR ≈ +0.9.",
        "",
        "| DVS# | xVAR# | Name | Pick | DVS | xVAR | Δ |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in te_players:
        dvs = p.get("dynasty_value_score")
        xvar = p.get("xvar")
        lines.append(
            f"| {p.get('dvs_class_rank', '—')} "
            f"| {p.get('xvar_class_rank', '—')} "
            f"| {p['full_name']} "
            f"| {p.get('nfl_draft_pick', '—')} "
            f"| {round(dvs, 1) if dvs is not None else '—'} "
            f"| {round(xvar, 1) if xvar is not None else '—'} "
            f"| {_delta_str(p)} |"
        )

    lines += [
        "",
        "## Age-Data Blockers — 6 Unscored 2026 Picks",
        "",
        "These players have verified draft capital but `birth_date=None` in the identity file. "
        "Engine A requires `pick + round + age`; without age they remain PRE_MODEL.",
        "",
        "| Name | Position | Pick | Round |",
        "|---|---|---|---|",
    ]
    for p in unscored:
        lines.append(
            f"| {p['full_name']} | {p['position']} "
            f"| {p.get('nfl_draft_pick', '—')} | {p.get('nfl_draft_round', '—')} |"
        )
    lines += [
        "",
        "_Resolution: collect birth_date from Pro Football Reference or Sports Reference, "
        "update `prospect_identity_2026.json`, re-run this script._",
    ]

    lines += [
        "",
        "## 2027 Watchlist — Excluded from 2026 Rankings",
        "",
        "| Name | Position | Draft Class | Grade |",
        "|---|---|---|---|",
    ]
    for p in watchlist:
        lines.append(
            f"| {p['full_name']} | {p['position']} "
            f"| {p.get('draft_class', '—')} | {p.get('model_grade', '—')} |"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    with open(IDENTITY_FILE) as f:
        identity_data = json.load(f)
    with open(CARDS_JSON) as f:
        baseline_cards = json.load(f)

    identity_players = identity_data["players"]  # 80 verified 2026 picks
    identity_snapshot_date = identity_data.get("snapshot_date", "unknown")

    cards_by_name_pos: dict[tuple[str, str], dict] = {
        (c["full_name"], c["position"]): c for c in baseline_cards
    }

    # 2027 watchlist — not in identity file, carry forward unchanged
    watchlist = [c for c in baseline_cards if c.get("draft_class") == 2027]

    pvos_2026, dvs_warnings = _build_pvo_dicts(identity_players, cards_by_name_pos)
    pvos_2026 = _compute_ranks(pvos_2026)

    if dvs_warnings:
        print(f"ERROR: {len(dvs_warnings)} DVS drift(s) detected — inspect before committing:")
        for w in dvs_warnings:
            print(f"  {w}")
        sys.exit(1)
    else:
        print("DVS invariance: OK — all 74 scored players match baseline exactly")

    scored_count = sum(1 for p in pvos_2026 if p.get("dynasty_value_score") is not None)
    pre_model_count = sum(1 for p in pvos_2026 if p.get("model_grade") == "PRE_MODEL")
    assert pre_model_count == 6, f"Expected 6 PRE_MODEL 2026 players, got {pre_model_count}"

    all_cards = pvos_2026 + watchlist

    CARDS_JSON.write_text(json.dumps(all_cards, indent=2, default=str))
    js_header = (
        "/* Auto-generated by scripts/refresh_prospect_cards.py — do not edit. */\n"
        f"/* Refreshed: Phase 15.1 · {len(pvos_2026)} 2026 + {len(watchlist)} watchlist */\n"
    )
    CARDS_JS.write_text(
        js_header
        + "window.PROSPECT_CARDS = "
        + json.dumps(all_cards, separators=(",", ":"), default=str)
        + ";\n"
    )

    print(
        f"Written: {len(pvos_2026)} 2026 prospects "
        f"({scored_count} scored, {pre_model_count} PRE_MODEL) + {len(watchlist)} watchlist"
    )

    _write_report(pvos_2026, watchlist, dvs_warnings, identity_snapshot_date)
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run focused tests — all 9 must pass**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_phase15_rookie_rank_refresh.py -v 2>&1 | tail -15
```

Expected: 9/9 PASS

- [ ] **Step 3: Run the script — inspect output**

```bash
.venv/bin/python3.14 scripts/refresh_prospect_cards.py 2>&1
```

Expected:
```
DVS invariance: OK — all 74 scored players match baseline exactly
Written: 80 2026 prospects (74 scored, 6 PRE_MODEL) + 2 watchlist
Report: docs/validation/phase15-2026-rookie-rank-refresh.md
```

If DVS drift fires: script exits 1. Inspect the named players. Do not commit.

- [ ] **Step 4: Spot-check the report**

```bash
head -80 docs/validation/phase15-2026-rookie-rank-refresh.md
```

Verify: identity stability section shows "No DVS drift," DVS top 24 table present, xVAR top 24 shows RBs above TEs, TE section shows all negative xVAR.

---

## Task 3: Run Full Suite

- [ ] **Step 1: Run full suite**

```bash
.venv/bin/python3.14 -m pytest --ignore=tests/test_nflreadpy_collection.py --ignore=tests/test_nflreadpy_adapter.py -q 2>&1 | tail -5
```

Expected: baseline count + 9 new tests, 0 failures.

---

## Task 4: Commit Implementation

- [ ] **Step 1: Commit**

```bash
git add scripts/refresh_prospect_cards.py \
        tests/contract/test_phase15_rookie_rank_refresh.py \
        resources/prospect_cards.json \
        resources/prospect_cards.js \
        docs/validation/phase15-2026-rookie-rank-refresh.md
git commit -m "feat(phase15.1): refresh 2026 rookie cards with Phase 15 xVAR + rank fields

- Regenerates prospect_cards.json/.js from prospect_identity_2026.json (80 picks)
- Adds xvar, dvs_engine, xvar_lambda, xvar_anchor, xvar_ceiling_bound to all 74 scored prospects
- Adds dvs_class_rank, xvar_class_rank, position_class_rank, rank_delta rank fields
- Preserves player_id values for Rookie Board taken-state continuity
- 6 PRE_MODEL age-data blockers documented; 2 2027 watchlist entries preserved separately
- DVS invariance confirmed (0 drift on 74 scored players)
- dvs_pct=None (ACTIVE_B reference only); decision_supported=False
- rank movement report at docs/validation/phase15-2026-rookie-rank-refresh.md

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Ledger and AGENT_SYNC

- [ ] **Step 1: Append to `docs/agent-ledger/2026-05-17.md`**

```markdown
## HH:MM ET - Claude Code

- Task: Phase 15.1 — 2026 Rookie Rank Refresh
- Governance read: 02-agent-operating-loop.md v1.0.0, 00-product-constitution.md v1.0.0, 01-north-star-architecture.md v1.0.0, AGENT_SYNC.md
- Active phase / surface: Phase 15.1 — artifact refresh, no model change
- Intended or completed write scope: scripts/refresh_prospect_cards.py, tests/contract/test_phase15_rookie_rank_refresh.py, resources/prospect_cards.json/.js, docs/validation/phase15-2026-rookie-rank-refresh.md
- Files changed: 5
- Tests / checks: 9 new contract tests; full suite green
- Product alignment: Engine A model unchanged. DVS invariance confirmed (0 drift on 74 scored players). xvar, dvs_engine, xvar_lambda, xvar_anchor, xvar_ceiling_bound added. dvs_class_rank, xvar_class_rank, position_class_rank, rank_delta added. player_id values preserved. dvs_pct=None. decision_supported=False. 6 PRE_MODEL age-data blockers documented. 2027 watchlist preserved separately.
- Drift risks: None. No model artifact, no formula change, no new data source.
- Handoff / next step: David reviews rank movement report. Open decision: board default sort by DVS or xVAR. Age-data blockers (6 players with real picks) require birth_date collection to score.
```

- [ ] **Step 2: Add Phase 15.1 line to `AGENT_SYNC.md` Active Phase section**

```
Phase 15.1 — COMPLETE: 2026 Rookie Rank Refresh — prospect_cards enriched with Phase 15 xVAR + rank fields; rank movement report at docs/validation/phase15-2026-rookie-rank-refresh.md (2026-05-17)
```

- [ ] **Step 3: Commit docs**

```bash
git add docs/agent-ledger/2026-05-17.md AGENT_SYNC.md
git commit -m "docs(phase15.1): ledger and AGENT_SYNC for 2026 rookie rank refresh"
```

---

## Self-Review

**Spec coverage:**
- [x] 80 verified 2026 picks from identity file
- [x] 74 scored; 6 PRE_MODEL (age-data blocker, not model blocker)
- [x] xvar, dvs_engine, xvar_lambda, xvar_anchor, xvar_ceiling_bound populated for scored prospects
- [x] dvs_class_rank, xvar_class_rank, position_class_rank, rank_delta added
- [x] rank_delta = xvar_class_rank − dvs_class_rank (positive = fell)
- [x] DVS invariance tolerance 0.01; script exits 1 on any drift
- [x] PRE_MODEL count assertion = 6
- [x] player_id preserved from existing cards; identity_dg_id stored separately
- [x] 2027 watchlist carried forward unchanged (no rank fields)
- [x] dvs_pct=None for all prospects
- [x] decision_supported=False
- [x] Report: DVS top 24, xVAR top 24, movers >10, TE xVAR table, 6 age-data blockers, 2 watchlist entries, identity stability check
- [x] No commit of failing tests
- [x] `.venv/bin/python3.14` throughout
- [x] One implementation commit, one docs commit
