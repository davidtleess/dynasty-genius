# Rookie Board UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 2026 Dynasty Rookie Board — a local `file://` HTML surface that reads Engine A PVO signals and surfaces BPA context for David's May 11th dynasty rookie draft.

**Architecture:** Three JS artifacts (`prospect_cards.js`, `draft_state.js`, `roster_need_signals.js`) are loaded via `<script src>` tags into a self-contained HTML page. A Python script fetches Sleeper draft state during the slow draft; the board renders TAKEN badges on page reload. All output is PROSPECT_C/D grade; `decision_supported: false` on every card; no directive language.

**Tech Stack:** Python 3.11, Pydantic v2, httpx (async), plain HTML/CSS/JS (no framework), pytest

---

## File Map

| Status | File | Task |
|---|---|---|
| Modify | `app/data/sleeper.py` | 1 |
| Modify | `src/dynasty_genius/models/player_value_object.py` | 2 |
| Modify | `src/dynasty_genius/pvo_assembler.py` | 2 |
| Create | `scripts/build_roster_need_signals.py` | 3 |
| Create | `scripts/refresh_draft_state.py` | 4 |
| Create | `src/dynasty_genius/dashboard/rookie_board.html` | 5 |
| Create | `tests/test_rookie_board_contract.py` | 6 |

---

### Task 1: Sleeper Draft Endpoints

**Files:**
- Modify: `app/data/sleeper.py`
- Create: `tests/test_sleeper_draft_endpoints.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sleeper_draft_endpoints.py`:

```python
"""Tests for Sleeper draft API endpoints added in Task 1."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_league_drafts_returns_list():
    from app.data.sleeper import get_league_drafts
    mock_data = [{"draft_id": "abc123", "status": "drafting", "created": 1715000000}]
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=mock_data)):
        result = await get_league_drafts("league_999")
    assert result == mock_data


@pytest.mark.asyncio
async def test_get_league_drafts_raises_on_none():
    from app.data.sleeper import get_league_drafts
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=None)):
        with pytest.raises(ValueError, match="No drafts found"):
            await get_league_drafts("league_999")


@pytest.mark.asyncio
async def test_get_draft_picks_returns_list():
    from app.data.sleeper import get_draft_picks
    mock_data = [{"pick_no": 1, "player_id": "5849", "picked_by": "user1"}]
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=mock_data)):
        result = await get_draft_picks("draft_abc")
    assert result == mock_data


@pytest.mark.asyncio
async def test_get_draft_picks_returns_empty_list_on_none():
    from app.data.sleeper import get_draft_picks
    with patch("app.data.sleeper._get", new=AsyncMock(return_value=None)):
        result = await get_draft_picks("draft_abc")
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv/bin/pytest tests/test_sleeper_draft_endpoints.py -v
```
Expected: ImportError or AttributeError — `get_league_drafts`/`get_draft_picks` not defined yet.

- [ ] **Step 3: Add the two endpoints to `app/data/sleeper.py`**

Append after the `get_traded_picks` function:

```python
async def get_league_drafts(league_id: str) -> list[dict]:
    data = await _get(f"/league/{league_id}/drafts")
    if data is None:
        raise ValueError(f"No drafts found for league_id: {league_id}")
    return data


async def get_draft_picks(draft_id: str) -> list[dict]:
    data = await _get(f"/draft/{draft_id}/picks")
    if data is None:
        return []
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

```
.venv/bin/pytest tests/test_sleeper_draft_endpoints.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/data/sleeper.py tests/test_sleeper_draft_endpoints.py
git commit -m "feat: add get_league_drafts and get_draft_picks to sleeper client"
```

---

### Task 2: PVO Identity Fields + Risk Flag Fix

**Files:**
- Modify: `src/dynasty_genius/models/player_value_object.py`
- Modify: `src/dynasty_genius/pvo_assembler.py`
- Modify: `tests/test_pvo_assembler.py` (add assertions)

The board needs `sleeper_id` for TAKEN detection, `draft_class` for the 2027 badge, `nfl_draft_pick`/`nfl_draft_round` for the meta line, and `decision_supported: false` as a contract guarantee. The `mock_draft_capital_unverified` flag must not fire for `VERIFIED_NFL_DRAFT` prospects.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pvo_assembler.py`:

```python
# ── Task 2: PVO identity field tests ──────────────────────────────────────────
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _make_prospect_identity(extra: dict | None = None) -> dict:
    base = {
        "source": "test",
        "snapshot_date": "2026-05-09",
        "players": [{
            "full_name": "Test Receiver",
            "position": "WR",
            "birth_date": "2003-01-01",
            "nfl_team": "DAL",
            "is_prospect": True,
            "draft_class": 2026,
            "pick": 15,
            "round": 1,
            "sleeper_id": "99999",
            "verification_status": "VERIFIED_NFL_DRAFT",
            **(extra or {}),
        }]
    }
    return base


def _assemble_from_fixture(fixture: dict) -> list[dict]:
    import tempfile
    from src.dynasty_genius.pvo_assembler import assemble_roster_audit
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(fixture, f)
        tmp_path = Path(f.name)
    try:
        return assemble_roster_audit(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_pvo_has_sleeper_id():
    cards = _assemble_from_fixture(_make_prospect_identity())
    assert cards[0]["sleeper_id"] == "99999"


def test_pvo_has_draft_class():
    cards = _assemble_from_fixture(_make_prospect_identity())
    assert cards[0]["draft_class"] == 2026


def test_pvo_has_nfl_draft_pick():
    cards = _assemble_from_fixture(_make_prospect_identity())
    assert cards[0]["nfl_draft_pick"] == 15


def test_pvo_has_nfl_draft_round():
    cards = _assemble_from_fixture(_make_prospect_identity())
    assert cards[0]["nfl_draft_round"] == 1


def test_pvo_decision_supported_is_false():
    cards = _assemble_from_fixture(_make_prospect_identity())
    assert cards[0]["decision_supported"] is False


def test_verified_prospect_no_unverified_flag():
    """VERIFIED_NFL_DRAFT prospects must not carry mock_draft_capital_unverified."""
    cards = _assemble_from_fixture(_make_prospect_identity())
    assert "mock_draft_capital_unverified" not in cards[0]["risk_flags"]


def test_unverified_prospect_carries_unverified_flag():
    """Prospects with pick data but not VERIFIED_NFL_DRAFT must carry the flag."""
    fixture = _make_prospect_identity({"verification_status": "PENDING"})
    cards = _assemble_from_fixture(fixture)
    assert "mock_draft_capital_unverified" in cards[0]["risk_flags"]
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv/bin/pytest tests/test_pvo_assembler.py -v -k "test_pvo_has_sleeper_id or test_pvo_has_draft_class or test_pvo_has_nfl_draft_pick or test_pvo_has_nfl_draft_round or test_pvo_decision_supported or test_verified_prospect or test_unverified_prospect"
```
Expected: FAIL — fields not yet on PVO.

- [ ] **Step 3: Add fields to `PlayerValueObject`**

In `src/dynasty_genius/models/player_value_object.py`, add after the `is_prospect` field in the Identity section:

```python
    sleeper_id: Optional[str] = None
    draft_class: Optional[int] = None
    nfl_draft_pick: Optional[int] = None
    nfl_draft_round: Optional[int] = None
```

Add after the `market_overlay` field (before Provenance section):

```python
    # ── Governance ────────────────────────────────────────────────────────────
    decision_supported: bool = False
```

- [ ] **Step 4: Propagate new fields in `assemble_pvo`**

In `src/dynasty_genius/pvo_assembler.py`, in the `assemble_pvo` function, find the `PlayerValueObject(...)` constructor call and add these fields:

```python
    pvo = PlayerValueObject(
        player_id=identity.dg_id,
        full_name=identity.full_name,
        position=identity.position,
        nfl_team=identity.nfl_team,
        age=features.get("age"),
        is_prospect=is_prospect,
        sleeper_id=identity.sleeper_id,
        draft_class=int(features["draft_class"]) if features.get("draft_class") is not None else None,
        nfl_draft_pick=int(features["pick"]) if features.get("pick") is not None else None,
        nfl_draft_round=int(features["round"]) if features.get("round") is not None else None,
        decision_supported=False,
        engine_used=engine_used,
        # ... rest of existing fields unchanged ...
```

The full updated constructor (replace the existing `pvo = PlayerValueObject(...)` block):

```python
    pvo = PlayerValueObject(
        player_id=identity.dg_id,
        full_name=identity.full_name,
        position=identity.position,
        nfl_team=identity.nfl_team,
        age=features.get("age"),
        is_prospect=is_prospect,
        sleeper_id=identity.sleeper_id,
        draft_class=int(features["draft_class"]) if features.get("draft_class") is not None else None,
        nfl_draft_pick=int(features["pick"]) if features.get("pick") is not None else None,
        nfl_draft_round=int(features["round"]) if features.get("round") is not None else None,
        decision_supported=False,
        engine_used=engine_used,
        model_version=model_version,
        model_grade=model_grade,
        dynasty_value_score=dynasty_value_score,
        projection_1y=None,
        projection_2y=None,
        projection_3y=None,
        signal_completeness=completeness,
        inputs_present=present,
        inputs_missing=missing,
        top_drivers=top_drivers,
        risk_flags=risk_flags,
        counter_argument=None,
        caveats=caveats,
        roster_audit=roster_audit,
        market_overlay=None,
        assembled_at=datetime.now(timezone.utc).isoformat(),
        source_versions=source_versions or {},
    )
```

- [ ] **Step 5: Fix `mock_draft_capital_unverified` condition in `assemble_roster_audit`**

In `src/dynasty_genius/pvo_assembler.py`, find this block in `assemble_roster_audit`:

```python
        if is_prospect and (p.get("pick") is not None or p.get("round") is not None):
            fixture_features["feature_warnings"] = ["mock_draft_capital_unverified"]
```

Replace with:

```python
        if (
            is_prospect
            and (p.get("pick") is not None or p.get("round") is not None)
            and p.get("verification_status") != "VERIFIED_NFL_DRAFT"
        ):
            fixture_features["feature_warnings"] = ["mock_draft_capital_unverified"]
```

- [ ] **Step 6: Run tests to verify they pass**

```
.venv/bin/pytest tests/test_pvo_assembler.py -v -k "test_pvo_has_sleeper_id or test_pvo_has_draft_class or test_pvo_has_nfl_draft_pick or test_pvo_has_nfl_draft_round or test_pvo_decision_supported or test_verified_prospect or test_unverified_prospect"
```
Expected: 7 passed.

- [ ] **Step 7: Run the full test suite to check for regressions**

```
.venv/bin/pytest tests/ -v --tb=short
```
Expected: all previously passing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add src/dynasty_genius/models/player_value_object.py src/dynasty_genius/pvo_assembler.py tests/test_pvo_assembler.py
git commit -m "feat: add sleeper_id, draft_class, nfl_draft_pick/round, decision_supported to PVO; fix mock_draft_capital_unverified for verified prospects"
```

---

### Task 3: `build_roster_need_signals.py`

**Files:**
- Create: `scripts/build_roster_need_signals.py`
- Create: `tests/test_build_roster_need_signals.py`

Reads `live_roster_cards.json` (PVO dicts with `roster_audit.years_to_cliff`). Aggregates age cliff signals by position. HIGH = ≥2 players at/past cliff (`years_to_cliff <= 0`). MEDIUM = ≥1 at cliff or ≥2 approaching (`years_to_cliff == 1`). LOW = none.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_roster_need_signals.py`:

```python
"""Tests for build_roster_need_signals.py logic."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _card(position: str, years_to_cliff: int | None) -> dict:
    ra = None if years_to_cliff is None else {"years_to_cliff": years_to_cliff}
    return {"position": position, "roster_audit": ra}


# Import the classify function — will fail until file is created
def _classify(cards, position):
    from scripts.build_roster_need_signals import _classify_position
    return _classify_position(cards, position)


def test_high_when_two_players_past_cliff():
    cards = [_card("WR", -1), _card("WR", 0), _card("WR", 3)]
    assert _classify(cards, "WR") == "HIGH"


def test_medium_when_one_at_cliff():
    cards = [_card("RB", 0), _card("RB", 5)]
    assert _classify(cards, "RB") == "MEDIUM"


def test_medium_when_two_approaching():
    cards = [_card("TE", 1), _card("TE", 1), _card("TE", 3)]
    assert _classify(cards, "TE") == "MEDIUM"


def test_low_when_no_cliff_signals():
    cards = [_card("QB", 5), _card("QB", 8)]
    assert _classify(cards, "QB") == "LOW"


def test_low_when_no_roster_audit():
    cards = [_card("WR", None), _card("WR", None)]
    assert _classify(cards, "WR") == "LOW"


def test_low_when_no_players_at_position():
    cards = [_card("WR", 0)]
    assert _classify(cards, "QB") == "LOW"
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv/bin/pytest tests/test_build_roster_need_signals.py -v
```
Expected: ImportError — module does not exist yet.

- [ ] **Step 3: Create `scripts/build_roster_need_signals.py`**

```python
"""Build position-level roster need signals from live_roster_cards.json.

Reads resources/live_roster_cards.json (PVO dicts with roster_audit.years_to_cliff).
Aggregates age cliff signals by position:
  HIGH   — ≥2 players at or past cliff (years_to_cliff ≤ 0)
  MEDIUM — ≥1 at cliff, or ≥2 approaching (years_to_cliff == 1)
  LOW    — no cliff signals

Writes resources/roster_need_signals.js: window.ROSTER_NEED = {...};

Usage:
    .venv/bin/python scripts/build_roster_need_signals.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ROSTER_CARDS = ROOT / "resources" / "live_roster_cards.json"
NEED_JS = ROOT / "resources" / "roster_need_signals.js"

SKILL_POSITIONS = ["WR", "RB", "QB", "TE"]


def _classify_position(cards: list[dict], position: str) -> str:
    pos_cards = [c for c in cards if c.get("position") == position]
    at_cliff = 0
    approaching = 0
    for c in pos_cards:
        ra = c.get("roster_audit") or {}
        ytc = ra.get("years_to_cliff")
        if ytc is not None:
            if ytc <= 0:
                at_cliff += 1
            elif ytc == 1:
                approaching += 1
    if at_cliff >= 2:
        return "HIGH"
    if at_cliff >= 1 or approaching >= 2:
        return "MEDIUM"
    return "LOW"


def main() -> None:
    if not ROSTER_CARDS.exists():
        print(f"ERROR: {ROSTER_CARDS} not found. Run build_live_roster.py first.")
        sys.exit(1)

    cards = json.loads(ROSTER_CARDS.read_text())
    need = {pos: _classify_position(cards, pos) for pos in SKILL_POSITIONS}

    ts = datetime.now(timezone.utc).isoformat()
    content = (
        "/* Auto-generated by scripts/build_roster_need_signals.py — do not edit. */\n"
        f"/* Generated: {ts} */\n"
        "window.ROSTER_NEED = "
        + json.dumps(need, separators=(",", ":"))
        + ";\n"
    )
    NEED_JS.write_text(content)
    print(f"Wrote roster_need_signals.js: {need}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```
.venv/bin/pytest tests/test_build_roster_need_signals.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_roster_need_signals.py tests/test_build_roster_need_signals.py
git commit -m "feat: add build_roster_need_signals.py — age cliff aggregation by position"
```

---

### Task 4: `refresh_draft_state.py`

**Files:**
- Create: `scripts/refresh_draft_state.py`

No unit tests in this task — the artifact shape is validated by `test_rookie_board_contract.py` in Task 6. The script logic is straightforward async Sleeper API consumption.

- [ ] **Step 1: Create `scripts/refresh_draft_state.py`**

```python
"""Fetch Sleeper draft picks and write resources/draft_state.js.

Env vars:
  DYNASTY_SLEEPER_DRAFT_ID   — if set, used directly (no discovery call)
  DYNASTY_SLEEPER_LEAGUE_ID  — fallback: discovers active draft from league

If no active draft is found, writes an empty taken list with a no_active_draft flag.

Usage:
    .venv/bin/python scripts/refresh_draft_state.py
    ! .venv/bin/python scripts/refresh_draft_state.py   (from Claude Code prompt)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.data.sleeper import get_draft_picks, get_league_drafts

DRAFT_STATE_JS = ROOT / "resources" / "draft_state.js"


def _write_state(taken: list[str], draft_id: str | None, caveat: str | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    payload: dict = {"taken": taken, "draft_id": draft_id, "refreshed_at": ts}
    if caveat:
        payload["caveat"] = caveat
    content = (
        "/* Auto-generated by scripts/refresh_draft_state.py — do not edit. */\n"
        f"/* Refreshed: {ts} · {len(taken)} picks taken */\n"
        "window.DRAFT_STATE = "
        + json.dumps(payload, separators=(",", ":"))
        + ";\n"
    )
    DRAFT_STATE_JS.write_text(content)
    print(f"Wrote draft_state.js — {len(taken)} taken picks, draft_id={draft_id}")


async def _find_draft_id() -> str | None:
    draft_id = os.environ.get("DYNASTY_SLEEPER_DRAFT_ID")
    if draft_id:
        print(f"Using DYNASTY_SLEEPER_DRAFT_ID override: {draft_id}")
        return draft_id

    league_id = os.environ.get("DYNASTY_SLEEPER_LEAGUE_ID")
    if not league_id:
        raise ValueError(
            "Set DYNASTY_SLEEPER_DRAFT_ID or DYNASTY_SLEEPER_LEAGUE_ID in .env"
        )

    drafts = await get_league_drafts(league_id)
    if not drafts:
        print("No drafts found for league — writing empty state.")
        return None

    active = [d for d in drafts if d.get("status") in ("drafting", "active")]
    pool = active if active else drafts
    pool.sort(key=lambda d: d.get("created", 0), reverse=True)

    print(f"Found {len(drafts)} draft(s):")
    for d in pool:
        print(f"  draft_id={d['draft_id']} status={d.get('status')} created={d.get('created')}")

    selected = pool[0]["draft_id"]
    print(f"Selected: {selected}")
    return selected


async def main() -> None:
    draft_id = await _find_draft_id()
    if draft_id is None:
        _write_state([], None, caveat="no_active_draft")
        return

    picks = await get_draft_picks(draft_id)
    taken = [str(pick["player_id"]) for pick in picks if pick.get("player_id")]
    _write_state(taken, draft_id)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Smoke-test the script with a dry run (no network)**

```
.venv/bin/python scripts/refresh_draft_state.py
```
Expected without env vars: `ValueError: Set DYNASTY_SLEEPER_DRAFT_ID or DYNASTY_SLEEPER_LEAGUE_ID in .env`

That confirms the guard works. The artifact shape test runs after the board is wired (Task 6).

- [ ] **Step 3: Commit**

```bash
git add scripts/refresh_draft_state.py
git commit -m "feat: add refresh_draft_state.py — Sleeper draft pick sync with env var override"
```

---

### Task 5: `rookie_board.html`

**Files:**
- Create: `src/dynasty_genius/dashboard/rookie_board.html`

The HTML is a self-contained `file://` page. It loads three `<script src>` artifacts from `../../../resources/`. If `draft_state.js` or `roster_need_signals.js` don't exist yet, inline defaults prevent JS errors.

- [ ] **Step 1: Create `src/dynasty_genius/dashboard/rookie_board.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dynasty Genius — 2026 Rookie Board</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; font-size: 14px; }

    /* ── Header ── */
    .header { background: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px; }
    .header-top { display: flex; justify-content: space-between; align-items: flex-start; }
    .title { font-size: 20px; font-weight: 700; color: #f1f5f9; }
    .subtitle { font-size: 11px; color: #475569; margin-top: 4px; }
    .header-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; margin-left: 24px; }
    .league-pills { display: flex; gap: 8px; }
    .pill { padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; }
    .pill-superflex { background: #3b0764; color: #c4b5fd; border: 1px solid #7c3aed; }

    /* ── Refresh button ── */
    .refresh-wrap { position: relative; }
    .refresh-btn { background: #1d4ed8; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; }
    .refresh-btn:hover { background: #1e40af; }
    .refresh-tooltip {
      display: none; position: absolute; right: 0; top: calc(100% + 6px);
      background: #0f172a; border: 1px solid #334155; border-radius: 6px;
      padding: 10px 14px; font-size: 11px; color: #94a3b8;
      white-space: nowrap; z-index: 100; font-family: monospace;
      line-height: 1.6;
    }
    .refresh-tooltip.open { display: block; }

    /* ── Roster need banner ── */
    .need-banner {
      background: #1e293b; border-bottom: 1px solid #334155;
      padding: 10px 24px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
    }
    .need-label { font-size: 10px; color: #475569; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
    .need-badges { display: flex; gap: 8px; }
    .need-badge { padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .need-HIGH  { background: #450a0a; color: #fca5a5; border: 1px solid #991b1b; }
    .need-MEDIUM{ background: #431407; color: #fdba74; border: 1px solid #c2410c; }
    .need-LOW   { background: #052e16; color: #86efac; border: 1px solid #166534; }
    .need-caveat { font-size: 10px; color: #475569; }

    /* ── Tabs ── */
    .tabs { background: #1e293b; border-bottom: 1px solid #334155; padding: 0 24px; display: flex; gap: 2px; }
    .tab { padding: 10px 16px; border: none; background: none; color: #64748b; cursor: pointer; font-size: 13px; font-weight: 500; border-bottom: 2px solid transparent; margin-bottom: -1px; }
    .tab.active { color: #f1f5f9; border-bottom-color: #3b82f6; }
    .tab:hover:not(.active) { color: #94a3b8; }

    /* ── Cards ── */
    .cards-wrap { padding: 16px 24px; max-width: 960px; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
    .card.taken { opacity: 0.35; }
    .card-QB { border-left: 3px solid #7c3aed; }
    .card-WR { border-left: 3px solid #2563eb; }
    .card-RB { border-left: 3px solid #16a34a; }
    .card-body { padding: 12px 16px; display: flex; align-items: flex-start; gap: 16px; }
    .card-rank { font-size: 22px; font-weight: 700; color: #334155; min-width: 36px; text-align: right; line-height: 1; padding-top: 4px; }
    .card-main { flex: 1; min-width: 0; }

    /* name row */
    .name-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .card-name { font-size: 16px; font-weight: 600; color: #f1f5f9; }
    .card-name.taken-name { text-decoration: line-through; color: #475569; }

    /* badges */
    .badge { padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
    .b-WR { background: #1e3a8a; color: #93c5fd; }
    .b-RB { background: #14532d; color: #86efac; }
    .b-QB { background: #2e1065; color: #c4b5fd; }
    .b-TE { background: #1c1917; color: #d6d3d1; border: 1px solid #44403c; }
    .b-sf { background: #2e1065; color: #c4b5fd; border: 1px solid #7c3aed; font-size: 9px; }
    .b-age { background: #431407; color: #fdba74; border: 1px solid #c2410c; }
    .b-taken { background: #1e293b; color: #475569; border: 1px solid #334155; }
    .b-2027 { background: #172554; color: #93c5fd; border: 1px solid #1d4ed8; font-size: 9px; }
    .b-unverified { background: #3b2f00; color: #fcd34d; border: 1px solid #92400e; font-size: 9px; }
    .b-prospect-d { background: #300; color: #fca5a5; border: 1px solid #7f1d1d; font-size: 9px; }

    /* meta + chips */
    .card-meta { font-size: 11px; color: #64748b; margin-top: 3px; }
    .chips { display: flex; gap: 6px; margin-top: 5px; flex-wrap: wrap; }

    /* score side */
    .card-right { text-align: right; min-width: 110px; flex-shrink: 0; }
    .engine-label { font-size: 9px; color: #475569; text-transform: uppercase; letter-spacing: 0.06em; }
    .score-num { font-size: 26px; font-weight: 700; color: #f1f5f9; line-height: 1.1; }
    .score-num.pre-model { font-size: 12px; color: #475569; font-weight: 400; margin-top: 6px; }
    .score-bar-bg { background: #0f172a; border-radius: 4px; height: 6px; margin-top: 6px; overflow: hidden; }
    .score-bar-fill { height: 100%; border-radius: 4px; }
    .model-grade { font-size: 10px; color: #475569; margin-top: 5px; }

    /* counter strip */
    .counter-strip { background: #1a0a0a; border-top: 1px solid #3b1515; padding: 8px 16px 8px 68px; display: flex; align-items: flex-start; gap: 8px; }
    .counter-icon { font-size: 11px; color: #ef4444; flex-shrink: 0; padding-top: 1px; }
    .counter-lbl { font-size: 10px; font-weight: 700; color: #ef4444; text-transform: uppercase; letter-spacing: 0.06em; min-width: 48px; flex-shrink: 0; padding-top: 1px; }
    .counter-text { font-size: 12px; color: #fca5a5; line-height: 1.4; }

    /* empty */
    .empty { padding: 48px 24px; text-align: center; color: #475569; font-size: 13px; }
  </style>
</head>
<body>

<!-- ── JS artifacts — file:// compatible script tags ── -->
<script src="../../../resources/prospect_cards.js"></script>
<script>if(typeof window.DRAFT_STATE==='undefined')window.DRAFT_STATE={taken:[],draft_id:null,refreshed_at:null};</script>
<script src="../../../resources/draft_state.js" onerror="void 0"></script>
<script>if(typeof window.ROSTER_NEED==='undefined')window.ROSTER_NEED={WR:'LOW',RB:'LOW',QB:'LOW',TE:'LOW'};</script>
<script src="../../../resources/roster_need_signals.js" onerror="void 0"></script>

<!-- ── Infer league context from PVO caveats ── -->
<script>
  var _sample = (window.PROSPECT_CARDS || [])[0] || {};
  var _cavs = (_sample.caveats || []).join(' ').toLowerCase();
  var IS_SUPERFLEX = _cavs.indexOf('superflex') !== -1;
  var TE_PREMIUM   = _cavs.indexOf('te premium') !== -1;
</script>

<!-- ── Page ── -->
<div class="header">
  <div class="header-top">
    <div>
      <div class="title">Dynasty Genius — 2026 Rookie Board</div>
      <div class="subtitle">Engine A &middot; PROSPECT_C/D &middot; market overlay excluded &middot; decision_supported: false</div>
    </div>
    <div class="header-right">
      <div class="league-pills" id="leaguePills"></div>
      <div class="refresh-wrap">
        <button class="refresh-btn" onclick="toggleRefreshTip()">&#8635; Refresh Draft</button>
        <div class="refresh-tooltip" id="refreshTip">
          1. Run in terminal:<br>
          <strong>.venv/bin/python scripts/refresh_draft_state.py</strong><br>
          2. Reload this page
        </div>
      </div>
    </div>
  </div>
</div>

<div class="need-banner" id="needBanner"></div>
<div class="tabs" id="tabs"></div>
<div class="cards-wrap" id="cardsWrap"></div>

<script>
// ── Data ──────────────────────────────────────────────────────────────────────
var CARDS      = window.PROSPECT_CARDS || [];
var DRAFT      = window.DRAFT_STATE    || { taken: [] };
var NEED       = window.ROSTER_NEED    || { WR:'LOW', RB:'LOW', QB:'LOW', TE:'LOW' };
var activeTab  = 'All';

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function isTaken(card) {
  var sid = String(card.sleeper_id || '');
  var pid = String(card.player_id  || '');
  return DRAFT.taken.indexOf(sid) !== -1 || (sid === '' && DRAFT.taken.indexOf(pid) !== -1);
}

function scoreColor(n) {
  if (n >= 75) return '#22c55e';
  if (n >= 50) return '#eab308';
  if (n >= 25) return '#f97316';
  return '#ef4444';
}

// ── League pills ──────────────────────────────────────────────────────────────
(function() {
  var el = document.getElementById('leaguePills');
  if (IS_SUPERFLEX) el.innerHTML += '<span class="pill pill-superflex">&#9889; SUPERFLEX</span>';
  if (TE_PREMIUM)   el.innerHTML += '<span class="pill" style="background:#0c3b2e;color:#86efac;border:1px solid #16a34a">TE PREMIUM</span>';
})();

// ── Roster need banner ────────────────────────────────────────────────────────
(function() {
  var el = document.getElementById('needBanner');
  var positions = ['WR','RB','QB','TE'];
  var badges = positions.map(function(pos) {
    var lvl = NEED[pos] || 'LOW';
    return '<span class="need-badge need-' + lvl + '">' + pos + ': ' + lvl + '</span>';
  }).join('');
  el.innerHTML =
    '<span class="need-label">Roster Need</span>' +
    '<span class="need-badges">' + badges + '</span>' +
    '<span class="need-caveat">age-curve only &middot; no Engine B &middot; verify before acting</span>';
})();

// ── Sort: scored cards by DVS desc, PRE_MODEL to bottom ──────────────────────
function sortCards(arr) {
  return arr.slice().sort(function(a, b) {
    var as = a.dynasty_value_score, bs = b.dynasty_value_score;
    if (as == null && bs != null) return 1;
    if (bs == null && as != null) return -1;
    if (as == null && bs == null) return 0;
    return bs - as;
  });
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function renderTabs() {
  var positions = ['All','QB','WR','RB','TE'];
  var el = document.getElementById('tabs');
  el.innerHTML = positions.map(function(pos) {
    var count = pos === 'All' ? CARDS.length : CARDS.filter(function(c){ return c.position === pos; }).length;
    return '<button class="tab' + (activeTab === pos ? ' active' : '') + '" onclick="setTab(\'' + pos + '\')">' +
      pos + ' <span style="color:#475569;font-weight:400">(' + count + ')</span></button>';
  }).join('');
}

function setTab(pos) {
  activeTab = pos;
  renderTabs();
  renderCards();
}

// ── Card HTML ─────────────────────────────────────────────────────────────────
function cardHtml(card, rank) {
  var taken    = isTaken(card);
  var hasScore = card.dynasty_value_score != null;
  var pos      = card.position || '';
  var lvl      = NEED[pos] || 'LOW';
  var isQB     = pos === 'QB';
  var is2027   = card.draft_class === 2027;
  var flags    = card.risk_flags || [];
  var hasUnverified = flags.indexOf('mock_draft_capital_unverified') !== -1;

  // Badges
  var posBadge   = '<span class="badge b-' + pos + '">' + esc(pos) + '</span>';
  var sfBadge    = (IS_SUPERFLEX && isQB) ? '<span class="badge b-sf">&#9889; SUPERFLEX</span>' : '';
  var ageBadge   = (lvl === 'HIGH' || lvl === 'MEDIUM') ? '<span class="badge b-age">AGE RISK</span>' : '';
  var takenBadge = taken   ? '<span class="badge b-taken">TAKEN</span>' : '';
  var cls2027    = is2027  ? '<span class="badge b-2027">2027 Class</span>' : '';

  // Risk chips (below meta)
  var uvChip = hasUnverified ? '<span class="badge b-unverified">&#9888; pick data unverified</span>' : '';
  var pdChip = (isQB && hasScore) ? '<span class="badge b-prospect-d">PROSPECT_D &middot; negative R&sup2;</span>' : '';

  // Meta line
  var meta = [];
  if (card.nfl_team)     meta.push(esc(card.nfl_team));
  if (card.nfl_draft_pick)  meta.push('Pick ' + card.nfl_draft_pick);
  if (card.nfl_draft_round) meta.push('Rd '   + card.nfl_draft_round);
  if (card.age != null)  meta.push('Age ' + Math.round(card.age));
  var metaStr = meta.join(' &middot; ');

  // Score side
  var scoreHtml = hasScore
    ? ('<div class="score-num">' + Math.round(card.dynasty_value_score) + '</div>' +
       '<div class="score-bar-bg"><div class="score-bar-fill" style="width:' + card.dynasty_value_score + '%;background:' +
       (taken ? '#334155' : scoreColor(card.dynasty_value_score)) + '"></div></div>')
    : '<div class="score-num pre-model">PRE-MODEL</div>';

  // Counter strip
  var counterHtml = '';
  if (hasScore && card.counter_argument) {
    var text = String(card.counter_argument).substring(0, 160);
    counterHtml =
      '<div class="counter-strip">' +
        '<span class="counter-icon">&#9873;</span>' +
        '<span class="counter-lbl">Counter</span>' +
        '<span class="counter-text">' + esc(text) + '</span>' +
      '</div>';
  }

  return (
    '<div class="card' + (taken ? ' taken' : '') + ' card-' + pos + '" id="c-' + esc(card.player_id) + '">' +
      '<div class="card-body">' +
        '<div class="card-rank">' + rank + '</div>' +
        '<div class="card-main">' +
          '<div class="name-row">' +
            '<span class="card-name' + (taken ? ' taken-name' : '') + '">' + esc(card.full_name) + '</span>' +
            posBadge + sfBadge + ageBadge + takenBadge + cls2027 +
          '</div>' +
          '<div class="card-meta">' + metaStr + '</div>' +
          (uvChip || pdChip ? '<div class="chips">' + uvChip + pdChip + '</div>' : '') +
        '</div>' +
        '<div class="card-right">' +
          '<div class="engine-label">Engine A</div>' +
          scoreHtml +
          '<div class="model-grade">' + esc(card.model_grade || 'PRE_MODEL') + '</div>' +
        '</div>' +
      '</div>' +
      counterHtml +
    '</div>'
  );
}

// ── Main render ───────────────────────────────────────────────────────────────
function renderCards() {
  var el = document.getElementById('cardsWrap');
  var filtered = activeTab === 'All' ? CARDS : CARDS.filter(function(c){ return c.position === activeTab; });
  var sorted   = sortCards(filtered);

  if (sorted.length === 0) {
    el.innerHTML = '<div class="empty">No prospects found. Run build_prospect_cards.py to generate data.</div>';
    return;
  }

  var rank = 1;
  el.innerHTML = sorted.map(function(card) {
    var r = card.dynasty_value_score != null ? rank++ : '&mdash;';
    return cardHtml(card, r);
  }).join('');
}

// ── Refresh tooltip ───────────────────────────────────────────────────────────
function toggleRefreshTip() {
  var tip = document.getElementById('refreshTip');
  tip.classList.toggle('open');
}
document.addEventListener('click', function(e) {
  if (!e.target.closest('.refresh-wrap')) {
    document.getElementById('refreshTip').classList.remove('open');
  }
});

// ── Boot ──────────────────────────────────────────────────────────────────────
renderTabs();
renderCards();
</script>
</body>
</html>
```

- [ ] **Step 2: Verify the file was written**

```
ls -lh src/dynasty_genius/dashboard/rookie_board.html
```
Expected: file exists, size > 8 KB.

- [ ] **Step 3: Commit**

```bash
git add src/dynasty_genius/dashboard/rookie_board.html
git commit -m "feat: add rookie_board.html — Engine A BPA surface for 2026 dynasty draft"
```

---

### Task 6: Contract Tests

**Files:**
- Create: `tests/test_rookie_board_contract.py`

These tests enforce the spec's governance requirements. Most JS artifact tests are skipped if artifacts haven't been generated yet — they become live after Task 7's integration run.

- [ ] **Step 1: Create `tests/test_rookie_board_contract.py`**

```python
"""Governance contract tests for the 2026 Rookie Board.

Tests HTML structure, banned directive language, artifact shapes,
and parity between the verified prospect manifest and generated cards.
Artifact-dependent tests are skipped if the artifact does not exist yet.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOARD_HTML       = ROOT / "src" / "dynasty_genius" / "dashboard" / "rookie_board.html"
CARDS_JS         = ROOT / "resources" / "prospect_cards.js"
CARDS_JSON       = ROOT / "resources" / "prospect_cards.json"
DRAFT_STATE_JS   = ROOT / "resources" / "draft_state.js"
ROSTER_NEED_JS   = ROOT / "resources" / "roster_need_signals.js"
IDENTITY_2026    = ROOT / "resources" / "prospect_identity_2026.json"

BANNED_PHRASES = [
    "draft target",
    "draft this",
    "trade candidate",
    "verdict",
    "confidence",
]

# ── HTML structure ─────────────────────────────────────────────────────────────

def test_board_loads_prospect_cards_js():
    html = BOARD_HTML.read_text()
    assert "prospect_cards.js" in html, "Board must load prospect_cards.js via <script src>"


def test_board_loads_draft_state_js():
    html = BOARD_HTML.read_text()
    assert "draft_state.js" in html, "Board must load draft_state.js via <script src>"


def test_board_loads_roster_need_js():
    html = BOARD_HTML.read_text()
    assert "roster_need_signals.js" in html, "Board must load roster_need_signals.js via <script src>"


def test_board_displays_decision_supported_false():
    html = BOARD_HTML.read_text()
    assert "decision_supported: false" in html, "Board subtitle must carry decision_supported: false"


# ── Banned directive language ──────────────────────────────────────────────────

@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_board_html_no_banned_phrase(phrase):
    html = BOARD_HTML.read_text().lower()
    assert phrase.lower() not in html, f"Banned phrase in board HTML: {phrase!r}"


@pytest.mark.skipif(not CARDS_JS.exists(), reason="prospect_cards.js not yet generated")
@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_prospect_cards_js_no_banned_phrase(phrase):
    body = CARDS_JS.read_text().lower()
    assert phrase.lower() not in body, f"Banned phrase in prospect_cards.js: {phrase!r}"


@pytest.mark.skipif(not DRAFT_STATE_JS.exists(), reason="draft_state.js not yet generated")
@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_draft_state_js_no_banned_phrase(phrase):
    body = DRAFT_STATE_JS.read_text().lower()
    assert phrase.lower() not in body, f"Banned phrase in draft_state.js: {phrase!r}"


@pytest.mark.skipif(not ROSTER_NEED_JS.exists(), reason="roster_need_signals.js not yet generated")
@pytest.mark.parametrize("phrase", BANNED_PHRASES)
def test_roster_need_js_no_banned_phrase(phrase):
    body = ROSTER_NEED_JS.read_text().lower()
    assert phrase.lower() not in body, f"Banned phrase in roster_need_signals.js: {phrase!r}"


# ── prospect_cards.json governance ────────────────────────────────────────────

@pytest.mark.skipif(not CARDS_JSON.exists(), reason="prospect_cards.json not yet generated")
def test_all_cards_have_decision_supported_false():
    cards = json.loads(CARDS_JSON.read_text())
    assert cards, "prospect_cards.json is empty"
    failures = [c["full_name"] for c in cards if c.get("decision_supported") is not False]
    assert not failures, f"Cards missing decision_supported: false → {failures}"


@pytest.mark.skipif(not CARDS_JSON.exists(), reason="prospect_cards.json not yet generated")
def test_all_2026_cards_have_sleeper_id():
    cards = json.loads(CARDS_JSON.read_text())
    class_2026 = [c for c in cards if c.get("draft_class") == 2026]
    missing = [c["full_name"] for c in class_2026 if not c.get("sleeper_id")]
    assert not missing, f"2026 prospects missing sleeper_id → {missing}"


# ── Parity: manifest vs generated cards ───────────────────────────────────────

@pytest.mark.skipif(
    not (CARDS_JSON.exists() and IDENTITY_2026.exists()),
    reason="artifacts not yet generated",
)
def test_all_2026_manifest_players_have_cards():
    cards = json.loads(CARDS_JSON.read_text())
    manifest = json.loads(IDENTITY_2026.read_text())
    manifest_names = {p["full_name"] for p in manifest["players"]}
    card_names     = {c["full_name"] for c in cards}
    missing = manifest_names - card_names
    assert not missing, f"In 2026 manifest but not in cards: {missing}"


# ── draft_state.js shape ───────────────────────────────────────────────────────

@pytest.mark.skipif(not DRAFT_STATE_JS.exists(), reason="draft_state.js not yet generated")
def test_draft_state_shape():
    body = DRAFT_STATE_JS.read_text()
    match = re.search(r'window\.DRAFT_STATE\s*=\s*(\{.*?\});', body, re.DOTALL)
    assert match, "window.DRAFT_STATE assignment not found in draft_state.js"
    state = json.loads(match.group(1))
    assert isinstance(state.get("taken"), list), "DRAFT_STATE.taken must be a list"
    assert "refreshed_at" in state, "DRAFT_STATE must carry refreshed_at"
    assert isinstance(state["refreshed_at"], str), "DRAFT_STATE.refreshed_at must be a string"


# ── roster_need_signals.js shape ──────────────────────────────────────────────

@pytest.mark.skipif(not ROSTER_NEED_JS.exists(), reason="roster_need_signals.js not yet generated")
def test_roster_need_shape():
    body = ROSTER_NEED_JS.read_text()
    match = re.search(r'window\.ROSTER_NEED\s*=\s*(\{.*?\});', body, re.DOTALL)
    assert match, "window.ROSTER_NEED assignment not found in roster_need_signals.js"
    need = json.loads(match.group(1))
    valid = {"HIGH", "MEDIUM", "LOW"}
    for pos in ["WR", "RB", "QB", "TE"]:
        assert pos in need, f"ROSTER_NEED missing position: {pos}"
        assert need[pos] in valid, f"ROSTER_NEED[{pos}]={need[pos]!r} not in {valid}"
```

- [ ] **Step 2: Run the contract tests (partial — artifacts don't exist yet)**

```
.venv/bin/pytest tests/test_rookie_board_contract.py -v
```
Expected: HTML structure + banned phrase tests pass. Artifact-dependent tests skip.

- [ ] **Step 3: Commit**

```bash
git add tests/test_rookie_board_contract.py
git commit -m "test: add rookie_board_contract tests — HTML structure, banned language, artifact shapes"
```

---

### Task 7: Integration Run + Manual Browser Check

Run all build scripts, generate artifacts, and verify the board renders correctly.

- [ ] **Step 1: Rebuild prospect cards with updated PVO fields**

```
.venv/bin/python scripts/build_prospect_cards.py
```
Expected output: table of prospects with DVS scores for 2026 class (Engine A fired), PRE-MODEL for 2027 class. Example:
```
Player                       Pos  Age     DVS  Engine                                Grade
--------------------------------------------------------------------------------------------
Tetairoa McMillan            WR    21   87.3  engine_a_v0.1.0_prospect              PROSPECT_C
Emeka Egbuka                 WR    22   81.1  engine_a_v0.1.0_prospect              PROSPECT_C
...
Ryan Williams                WR    19      —  PRE_MODEL                             PRE_MODEL
```

- [ ] **Step 2: Build roster need signals**

```
.venv/bin/python scripts/build_roster_need_signals.py
```
Expected: prints `{'WR': '...', 'RB': '...', 'QB': '...', 'TE': '...'}` and writes `resources/roster_need_signals.js`.

- [ ] **Step 3: Run full contract test suite**

```
.venv/bin/pytest tests/test_rookie_board_contract.py -v
```
Expected: all tests pass (no more skips for the artifact tests, since artifacts now exist).

- [ ] **Step 4: Run full test suite to confirm no regressions**

```
.venv/bin/pytest tests/ -v --tb=short
```
Expected: all tests pass.

- [ ] **Step 5: Open the board in a browser and verify manually**

```
open src/dynasty_genius/dashboard/rookie_board.html
```

Manual checklist:
- [ ] Header shows "Dynasty Genius — 2026 Rookie Board" and subtitle with `decision_supported: false`
- [ ] `⚡ SUPERFLEX` pill appears in header (league is superflex)
- [ ] Roster need banner shows WR/RB/QB/TE with color-coded badges
- [ ] "All" tab is default; counts are visible on each tab
- [ ] Cards rank 1–N sorted by DVS descending
- [ ] 2027 class cards (Ryan Williams, Jeremiah Smith) show `2027 Class` badge and `PRE-MODEL` score
- [ ] Every scored card has a red counter-argument strip at the bottom
- [ ] QB cards show `PROSPECT_D · negative R²` chip
- [ ] QB cards (superflex league) show `⚡ SUPERFLEX` context badge
- [ ] 2026 verified cards do NOT show `⚠ pick data unverified`
- [ ] Clicking "↻ Refresh Draft" shows tooltip with terminal command
- [ ] Position tab filter works (WR tab shows only WR cards, etc.)

- [ ] **Step 6: Final commit**

```bash
git add resources/prospect_cards.js resources/prospect_cards.json resources/roster_need_signals.js
git commit -m "chore: regenerate prospect_cards and roster_need_signals artifacts with PVO identity fields"
```

---

## Quick Reference — Refresh During Draft

```
# When a pick is made:
! .venv/bin/python scripts/refresh_draft_state.py

# Then reload the browser tab — TAKEN badges appear automatically.
```

To override the draft ID directly (skip discovery):
```
# In .env:
DYNASTY_SLEEPER_DRAFT_ID=<your_draft_id>
```
