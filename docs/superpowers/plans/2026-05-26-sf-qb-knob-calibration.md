# SF-QB Knob Calibration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.
> **Cockpit note:** TMUX Codex-test-driver / Claude-implementer loop. Codex authors each failing contract test; Claude implements to green. The test code below is the contract.

**Goal:** Calibrate the SF-QB ordering knob (`sf_qb_promote_slots`) by measuring how many slots earlier QBs go in real SF rookie drafts vs NFL-skill order, and recommend a global `K` — without changing the production curve until David approves the computed K.

**Architecture:** A `scripts/calibrate_sf_qb_knob.py` with **pure, unit-tested helpers** (name-normalize, NFL-skill-rank resolver, per-QB promotions, half-up K) and a **monkeypatchable live-fetch seam** (Sleeper `previous_league_id` chain + rookie-draft filter). It combines your league's rookie drafts with a curated seed fixture, computes `K = clamp(round_half_up(median(promotions)), 0, 3)`, and writes a recommended-K artifact. Setting K + curve regen is a separate, David-gated step.

**Tech Stack:** Python 3.14, pandas, pytest, Sleeper read-only API (`app/data/sleeper.py`).

**Spec:** `docs/superpowers/specs/2026-05-26-sf-qb-knob-calibration-design.md`

---

## File Structure

- **Create** `scripts/calibrate_sf_qb_knob.py` — pure helpers + fetch seam + `main()` artifact writer.
- **Create** `resources/seed_rookie_drafts.json` — curated QB rows from the 3 usable seed drafts.
- **Create** `tests/test_calibrate_sf_qb_knob.py` — unit tests on the pure helpers (no live network).
- **Generated (not committed by a task)** `app/data/backtest/phase24/sf_qb_knob_calibration_<ts>.json`.

Scripts insert repo root into `sys.path` before `src` imports (`scripts/**` `E402` is ignored).

---

## Task 1: Seed-draft fixture (QB rows from the 3 usable drafts)

**Files:** Create `resources/seed_rookie_drafts.json`

Only QBs are needed (the metric is QB-only). `slot` = overall 1-based pick number = `(round-1)*12 + pick`. Transcribed from `docs/strategies/Rookie Draft Seed Data.md` (Draft B 2024, Draft A 2022, Draft F 2025 — the partial-but-strict-spec SF drafts).

- [ ] **Step 1: Create the fixture**

```json
{
  "source": "docs/strategies/Rookie Draft Seed Data.md (Drafts B/A/F; QB rows; partial boards)",
  "drafts": [
    {"draft_class": 2024, "league": "seed_draft_B", "qbs": [
      {"slot": 1, "player_name": "Caleb Williams"},
      {"slot": 4, "player_name": "Jayden Daniels"},
      {"slot": 5, "player_name": "J.J. McCarthy"},
      {"slot": 8, "player_name": "Drake Maye"},
      {"slot": 16, "player_name": "Bo Nix"},
      {"slot": 18, "player_name": "Michael Penix Jr."}
    ]},
    {"draft_class": 2022, "league": "seed_draft_A", "qbs": [
      {"slot": 3, "player_name": "Kenny Pickett"},
      {"slot": 14, "player_name": "Desmond Ridder"},
      {"slot": 15, "player_name": "Malik Willis"},
      {"slot": 22, "player_name": "Matt Corral"}
    ]},
    {"draft_class": 2025, "league": "seed_draft_F", "qbs": [
      {"slot": 5, "player_name": "Cam Ward"},
      {"slot": 10, "player_name": "Jaxson Dart"}
    ]}
  ]
}
```

- [ ] **Step 2: Verify it loads** — `.venv/bin/python3.14 -c "import json; d=json.load(open('resources/seed_rookie_drafts.json')); print(sum(len(x['qbs']) for x in d['drafts']), 'QB rows across', len(d['drafts']), 'drafts')"` → `12 QB rows across 3 drafts`.

- [ ] **Step 3: Commit** — `git add resources/seed_rookie_drafts.json && git commit -m "data(sf-qb-cal): curated seed rookie-draft QB rows"`

---

## Task 2: Half-up rounding + `recommend_k`

**Files:** Create `scripts/calibrate_sf_qb_knob.py`; Test `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.calibrate_sf_qb_knob import recommend_k, round_half_up

def test_round_half_up_is_not_bankers():
    assert round_half_up(0.5) == 1
    assert round_half_up(2.5) == 3
    assert round_half_up(1.5) == 2

def test_recommend_k_clamps_and_half_up():
    assert recommend_k([0.0, 1.0]) == 1        # median 0.5 -> half-up 1
    assert recommend_k([2.0, 3.0]) == 3        # median 2.5 -> 3 (clamped at 3 anyway)
    assert recommend_k([5.0, 5.0, 5.0]) == 3   # clamp high
    assert recommend_k([-2.0, -1.0]) == 0      # negative median -> clamp 0
    assert recommend_k([]) == 0                # empty -> 0
```

- [ ] **Step 2: Run, verify fail** — `.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -q` → FAIL (module/functions missing).

- [ ] **Step 3: Implement** — create `scripts/calibrate_sf_qb_knob.py`:

```python
#!/usr/bin/env python3.14
"""Phase 24 — calibrate the SF-QB ordering knob (sf_qb_promote_slots).

Measures per-QB slot promotion (nfl_skill_rank - ff_slot) across real SF rookie
drafts (David's league via Sleeper + a seed fixture) and recommends a global K =
clamp(round_half_up(median), 0, 3). Read-only Sleeper. Does NOT change the curve.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import pandas as pd  # noqa: E402

_LEAGUE_ID = "1314363401744416768"
_SEED_PATH = _ROOT / "resources" / "seed_rookie_drafts.json"
_OUTCOMES_CSV = _ROOT / "app" / "data" / "training" / "prospects_with_outcomes.csv"
_PROSPECT_CARDS = _ROOT / "resources" / "prospect_cards.json"
_SKILL = {"QB", "RB", "WR", "TE"}
_BOARD_SIZE = 36


def round_half_up(m: float) -> int:
    """Half-up rounding (math.floor(m + 0.5)) — NOT Python's banker round()."""
    return math.floor(m + 0.5)


def recommend_k(promotions: list[float]) -> int:
    """K = clamp(round_half_up(median(promotions)), 0, 3); empty -> 0."""
    if not promotions:
        return 0
    return max(0, min(3, round_half_up(statistics.median(promotions))))
```

- [ ] **Step 4: Run, verify pass** — same command, the two tests pass.

- [ ] **Step 5: Commit** — `git add scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py && git commit -m "feat(sf-qb-cal): half-up rounding + recommend_k"`

---

## Task 3: `normalize_name` + `is_rookie_draft`

**Files:** Modify `scripts/calibrate_sf_qb_knob.py`; Test `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing tests**

```python
from scripts.calibrate_sf_qb_knob import normalize_name, is_rookie_draft

def test_normalize_name_strips_case_punct_suffix():
    assert normalize_name("Michael Penix Jr.") == normalize_name("michael penix")
    assert normalize_name("Ja'Marr Chase") == "jamarr chase"
    assert normalize_name("Marvin Harrison Jr.") == "marvin harrison"

def test_is_rookie_draft_requires_small_rounds_and_complete():
    assert is_rookie_draft({"status": "complete", "settings": {"rounds": 3}}) is True
    assert is_rookie_draft({"status": "complete", "settings": {"rounds": 15}}) is False  # startup
    assert is_rookie_draft({"status": "drafting", "settings": {"rounds": 3}}) is False   # in-progress
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement** — add to the script:

```python
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

def normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]", "", (name or "").lower())
    tokens = [t for t in cleaned.split() if t not in _SUFFIXES]
    return " ".join(tokens)

def is_rookie_draft(draft: dict) -> bool:
    """A completed rookie draft: status complete and small round count (excludes startup)."""
    rounds = (draft.get("settings") or {}).get("rounds", 99)
    return draft.get("status") == "complete" and int(rounds) <= 6
```

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** — `feat(sf-qb-cal): name normalization + rookie-draft filter`

---

## Task 4: `nfl_skill_ranks(draft_class)` resolver

**Files:** Modify `scripts/calibrate_sf_qb_knob.py`; Test `tests/test_calibrate_sf_qb_knob.py`

Builds `{normalized_name: nfl_skill_rank}` = first-36 skill players by NFL pick for a class. 2026 → `prospect_cards.json`; other years → `prospects_with_outcomes.csv`.

- [ ] **Step 1: Write the failing test** (inject tiny fixtures via params, not the real files)

```python
import pandas as pd
from scripts.calibrate_sf_qb_knob import nfl_skill_ranks_from_outcomes

def test_nfl_skill_ranks_first36_by_pick_skill_only():
    df = pd.DataFrame([
        {"season": 2024, "pick": 1, "position": "QB", "pfr_player_name": "Caleb Williams"},
        {"season": 2024, "pick": 2, "position": "OT", "pfr_player_name": "Joe Alt"},   # non-skill skipped
        {"season": 2024, "pick": 10, "position": "QB", "pfr_player_name": "J.J. McCarthy"},
        {"season": 2023, "pick": 1, "position": "QB", "pfr_player_name": "Bryce Young"},  # other year
    ])
    ranks = nfl_skill_ranks_from_outcomes(df, 2024)
    assert ranks["caleb williams"] == 1
    assert ranks["jj mccarthy"] == 2   # 2nd skill player by pick (OT skipped)
    assert "bryce young" not in ranks
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement**

```python
def nfl_skill_ranks_from_outcomes(df: "pd.DataFrame", draft_class: int) -> dict[str, int]:
    rows = df[(df["season"] == draft_class) & (df["position"].isin(_SKILL))]
    rows = rows.sort_values("pick").head(_BOARD_SIZE)
    return {
        normalize_name(str(r["pfr_player_name"])): i
        for i, (_, r) in enumerate(rows.iterrows(), start=1)
    }

def nfl_skill_ranks(draft_class: int) -> dict[str, int]:
    if draft_class == 2026:
        cards = json.loads(_PROSPECT_CARDS.read_text())
        rows = [c for c in cards
                if c.get("draft_class") == 2026 and c.get("position") in _SKILL
                and isinstance(c.get("nfl_draft_pick"), (int, float))]
        rows.sort(key=lambda c: c["nfl_draft_pick"])
        return {normalize_name(c["full_name"]): i
                for i, c in enumerate(rows[:_BOARD_SIZE], start=1)}
    df = pd.read_csv(_OUTCOMES_CSV)
    return nfl_skill_ranks_from_outcomes(df, draft_class)
```

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** — `feat(sf-qb-cal): NFL-skill-rank resolver`

---

## Task 5: `qb_promotions(boards, rank_maps)`

**Files:** Modify `scripts/calibrate_sf_qb_knob.py`; Test `tests/test_calibrate_sf_qb_knob.py`

`boards` = list of `{draft_class, qbs: [{slot, player_name}]}` (seed) or `{draft_class, picks: [{ff_slot, player_name, position}]}` (live). Returns `(promotions, n_matched, n_unmatched)`.

- [ ] **Step 1: Write the failing test**

```python
from scripts.calibrate_sf_qb_knob import qb_promotions

def test_qb_promotions_matched_unmatched_and_nonqb_ignored():
    boards = [
        {"draft_class": 2024, "picks": [
            {"ff_slot": 1, "player_name": "Caleb Williams", "position": "QB"},
            {"ff_slot": 5, "player_name": "J.J. McCarthy", "position": "QB"},
            {"ff_slot": 2, "player_name": "Marvin Harrison Jr.", "position": "WR"},  # non-QB ignored
            {"ff_slot": 9, "player_name": "Unknown Qb", "position": "QB"},           # unmatched
        ]},
    ]
    rank_maps = {2024: {"caleb williams": 1, "jj mccarthy": 2}}
    promos, matched, unmatched = qb_promotions(boards, rank_maps)
    # Caleb: 1-1=0 ; McCarthy: 2-5=-3
    assert sorted(promos) == [-3.0, 0.0]
    assert matched == 2 and unmatched == 1
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement** (supports both `picks` and seed `qbs` shapes)

```python
def _board_qbs(board: dict) -> list[tuple[int, str]]:
    if "qbs" in board:  # seed fixture (already QB-only)
        return [(int(q["slot"]), q["player_name"]) for q in board["qbs"]]
    return [(int(p["ff_slot"]), p["player_name"])
            for p in board.get("picks", []) if p.get("position") == "QB"]

def qb_promotions(boards, rank_maps):
    promotions, matched, unmatched = [], 0, 0
    for board in boards:
        ranks = rank_maps.get(board["draft_class"], {})
        for ff_slot, name in _board_qbs(board):
            rank = ranks.get(normalize_name(name))
            if rank is None:
                unmatched += 1
                continue
            promotions.append(float(rank - ff_slot))
            matched += 1
    return promotions, matched, unmatched
```

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit** — `feat(sf-qb-cal): per-QB promotion calc`

---

## Task 6: Live-fetch seam + `main()` artifact writer

**Files:** Modify `scripts/calibrate_sf_qb_knob.py`; Test `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing test** (monkeypatch the fetch seam; no live network)

```python
import json as _json
import scripts.calibrate_sf_qb_knob as cal

def test_main_writes_artifact_with_monkeypatched_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(cal, "_fetch_league_rookie_drafts", lambda league_id: [
        {"draft_class": 2026, "picks": [
            {"ff_slot": 1, "player_name": "Fernando Mendoza", "position": "QB"}]}
    ])
    out = tmp_path / "cal.json"
    k = cal.main(out_path=out)
    art = _json.loads(out.read_text())
    assert art["recommended_k"] == k
    assert "sf_qb_calibration_thin_sample" in art["caveats"]
    assert art["n_qbs_matched"] >= 1
    assert isinstance(k, int) and 0 <= k <= 3
```

- [ ] **Step 2: Run, verify fail.**

- [ ] **Step 3: Implement** — the fetch seam (uses the async Sleeper adapter via `asyncio.run`) + `main()`:

```python
import asyncio  # add to imports
from datetime import datetime, timezone

from app.data.sleeper import (  # noqa: E402
    get_draft, get_draft_picks, get_league, get_league_drafts,
)

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
            boards.append({
                "draft_class": draft_class,
                "picks": [
                    {"ff_slot": int(p["pick_no"]),
                     "player_name": f"{(p.get('metadata') or {}).get('first_name','')} "
                                    f"{(p.get('metadata') or {}).get('last_name','')}".strip(),
                     "position": (p.get("metadata") or {}).get("position")}
                    for p in picks
                ],
            })
        current = league.get("previous_league_id")
    return boards

def _fetch_league_rookie_drafts(league_id: str) -> list[dict]:
    """Live read-only Sleeper fetch (monkeypatched in tests)."""
    return asyncio.run(_collect_rookie_boards(league_id))

def _load_seed_drafts() -> list[dict]:
    return json.loads(_SEED_PATH.read_text())["drafts"]

def main(out_path: Path | None = None, league_id: str = _LEAGUE_ID) -> int:
    boards = list(_fetch_league_rookie_drafts(league_id)) + _load_seed_drafts()
    classes = {b["draft_class"] for b in boards}
    rank_maps = {c: nfl_skill_ranks(c) for c in classes}
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
        "caveats": ["sf_qb_calibration_thin_sample"],
    }
    if out_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = _ROOT / "app" / "data" / "backtest" / "phase24" / f"sf_qb_knob_calibration_{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2))
    print(f"Wrote {out_path}; recommended_k={k} "
          f"(median={artifact['median_raw']}, matched={matched}, unmatched={unmatched}, "
          f"drafts={len(boards)})")
    return k

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run, verify pass** — the monkeypatched test passes.

- [ ] **Step 5: Commit** — `feat(sf-qb-cal): live-fetch seam + main artifact writer`

---

## Task 7: Run calibration live + verification (K-gated)

**Files:** none (run + report)

- [ ] **Step 1: Full suite + ruff**

Run: `.venv/bin/python3.14 -m pytest -q` (prior baseline + new tests, 0 failed); `.venv/bin/ruff check scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py` (clean; `ruff check --select I --fix` if I001); `.venv/bin/python3.14 scripts/validate_governance.py` (passed).

- [ ] **Step 2: Run the live calibration** (read-only Sleeper)

Run: `.venv/bin/python3.14 scripts/calibrate_sf_qb_knob.py`
Capture: `recommended_k`, median, matched/unmatched counts, n_drafts. Commit the generated artifact.

- [ ] **Step 3: STOP — report the recommended K to David.** Do NOT set `_SF_QB_PROMOTE_SLOTS` or regenerate the curve. Surface K + the match rate + thin-sample caveat; the curve change is gated on David's explicit approval of this K value (spec §5).

- [ ] **Step 4:** Open the PR for the calibration capability (script + fixture + tests + artifact). Curve regen, if approved, is a follow-up commit/PR.

---

## Self-Review

- **Spec coverage:** §1 metric → Task 2 (`recommend_k`/half-up); §2 corpus → Task 1 (seed) + Task 6 (league chain + `is_rookie_draft` rounds≤6 & complete & `draft_class` from season); §3 resolver → Task 4; §4 components → Tasks 2–6 (pure helpers + seam + artifact); §5 gated apply → Task 7 Step 3 (STOP/report; no regen); §6 governance (read-only, no training) → fetch seam read-only, no model touch; §7 scope → Tasks 1–7; §8 tests → Tasks 2–6 (half-up ties, empty→0, clamp, normalize, rookie filter incl. status, promotions matched/unmatched/non-QB, monkeypatched main). All covered.
- **No placeholders:** every step has concrete code/commands.
- **Type consistency:** `round_half_up`/`recommend_k`/`normalize_name`/`is_rookie_draft`/`nfl_skill_ranks(_from_outcomes)`/`qb_promotions`/`_fetch_league_rookie_drafts`/`main` consistent across tasks; `_SKILL`/`_BOARD_SIZE` reused; board shapes (`qbs` seed vs `picks` live) handled by `_board_qbs`.
