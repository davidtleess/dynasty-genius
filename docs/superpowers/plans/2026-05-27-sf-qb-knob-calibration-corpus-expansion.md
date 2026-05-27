# SF-QB Calibration Corpus Expansion (Increment 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `scripts/calibrate_sf_qb_knob.py` ingest curated bring-your-own (BYO) Sleeper rookie-draft IDs, each hard-gated as a real Superflex + 12-team + completed rookie draft, to thicken the thin SF-QB calibration corpus — keeping the recommended-K math unchanged and diagnostic-only.

**Architecture:** Extend the existing script (no new module, no market abstraction). Add a curated input loader, pure draft+league gate helpers, a separate pick-level board builder (draft_class + malformed-picks + first-36 cap), a fail-closed async BYO collector behind a monkeypatchable seam, and `main()` integration (cross-source de-dup + rank-map-unavailable exclusion + additive `rejected`/`format_meta` artifact provenance).

**Tech Stack:** Python 3.14, `pytest` (run via `.venv/bin/python3.14 -m pytest`), `monkeypatch` for the Sleeper async functions. Read-only Sleeper.

**Spec:** `docs/superpowers/specs/2026-05-27-sf-qb-knob-calibration-corpus-expansion-design.md`

**Cockpit execution:** Codex test-drives each RED contract; Claude implements to green. One agent edits at a time (tmux focus is the lock). Run after each task:
`./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -q`

**Scope fences (do NOT do these):** no K application / no curve regen / no `draft_pick_value_curve_v1.json` change · MFL aggregate barred from calibration · no new module / market abstraction · no model pkl/manifest/contract change · no frontend/NOISE_BAND change.

---

## File Structure

- **Create** `resources/sf_rookie_draft_ids.json` — curated BYO draft-ID input; ships with an **empty** `draft_ids` list (backward-compatible no-op until David populates it).
- **Modify** `scripts/calibrate_sf_qb_knob.py` — add `_BYO_PATH`, `_load_byo_draft_ids`, `is_superflex`, `is_twelve_team`, `league_format_metadata`, `gate_byo_draft`, `_build_byo_board`, `_collect_byo_boards`, `_fetch_byo_drafts`; add `draft_id` to chain boards; integrate in `main()`.
- **Modify** `tests/test_calibrate_sf_qb_knob.py` — add unit tests for each helper + the collector + the `main()` integration.

Existing constants reused: `_ROOT`, `_BOARD_SIZE = 36`, `normalize_name`, `is_rookie_draft`, `nfl_skill_ranks`, `qb_promotions`, `recommend_k`, and the Sleeper imports (`get_draft`, `get_draft_picks`, `get_league`).

---

## Task 1: Curated BYO input file + `_load_byo_draft_ids`

**Files:**
- Create: `resources/sf_rookie_draft_ids.json`
- Modify: `scripts/calibrate_sf_qb_knob.py`
- Test: `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Create the curated input file (empty = no-op)**

`resources/sf_rookie_draft_ids.json`:
```json
{
  "note": "Curated real Superflex 12-team rookie draft IDs for the SF-QB knob calibration corpus. Each ID is fetched and hard-gated (SF + 12-team + completed rookie) before inclusion. Empty list = chain + seed only.",
  "draft_ids": []
}
```

- [ ] **Step 2: Write the failing test**

Add to `tests/test_calibrate_sf_qb_knob.py`:
```python
def test_load_byo_draft_ids_dedupes_order_preserving(tmp_path, monkeypatch):
    p = tmp_path / "byo.json"
    p.write_text(json.dumps({"draft_ids": ["A", "B", "A", "C", "B"]}))
    monkeypatch.setattr(cal, "_BYO_PATH", p)
    ids, dupes = cal._load_byo_draft_ids()
    assert ids == ["A", "B", "C"]
    assert dupes == ["A", "B"]


def test_load_byo_draft_ids_missing_file_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(cal, "_BYO_PATH", tmp_path / "does_not_exist.json")
    assert cal._load_byo_draft_ids() == ([], [])


def test_load_byo_draft_ids_empty_list(tmp_path, monkeypatch):
    p = tmp_path / "byo.json"
    p.write_text(json.dumps({"draft_ids": []}))
    monkeypatch.setattr(cal, "_BYO_PATH", p)
    assert cal._load_byo_draft_ids() == ([], [])
```

- [ ] **Step 3: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k byo_draft_ids -v`
Expected: FAIL (`AttributeError: module ... has no attribute '_BYO_PATH'` / `_load_byo_draft_ids`).

- [ ] **Step 4: Implement**

In `scripts/calibrate_sf_qb_knob.py`, near the other path constants (after `_SEED_PATH`):
```python
_BYO_PATH = _ROOT / "resources" / "sf_rookie_draft_ids.json"
```
And add the loader (in the pure-helpers section):
```python
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
```

- [ ] **Step 5: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k byo_draft_ids -q`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add resources/sf_rookie_draft_ids.json scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py
git commit -m "feat(sf-qb-cal): curated BYO draft-id input + order-preserving de-dupe loader"
```

---

## Task 2: Pure gate helpers (`is_superflex`, `is_twelve_team`, `league_format_metadata`)

**Files:**
- Modify: `scripts/calibrate_sf_qb_knob.py`
- Test: `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing test**

```python
def test_is_superflex_exact_token():
    assert cal.is_superflex({"roster_positions": ["QB", "RB", "SUPER_FLEX", "BN"]}) is True
    assert cal.is_superflex({"roster_positions": ["QB", "RB", "WR", "BN"]}) is False
    assert cal.is_superflex({}) is False


def test_is_twelve_team_int_coerced():
    assert cal.is_twelve_team({"total_rosters": 12}) is True
    assert cal.is_twelve_team({"total_rosters": "12"}) is True
    assert cal.is_twelve_team({"total_rosters": 10}) is False
    assert cal.is_twelve_team({}) is False
    assert cal.is_twelve_team({"total_rosters": "oops"}) is False


def test_league_format_metadata_reads_scoring_settings():
    league = {
        "roster_positions": ["QB", "SUPER_FLEX"],
        "total_rosters": 12,
        "scoring_settings": {"rec": 1.0, "bonus_rec_te": 0.5},
    }
    meta = cal.league_format_metadata(league)
    assert meta == {"superflex": True, "total_rosters": 12, "ppr": 1.0, "te_premium": True}
    # absent scoring -> ppr None, te_premium False
    meta2 = cal.league_format_metadata({"roster_positions": [], "total_rosters": 10})
    assert meta2["ppr"] is None
    assert meta2["te_premium"] is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k "superflex or twelve_team or format_metadata" -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Implement**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k "superflex or twelve_team or format_metadata" -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py
git commit -m "feat(sf-qb-cal): SF/12-team gate helpers + scoring_settings format metadata"
```

---

## Task 3: `gate_byo_draft` (draft + league gates only)

**Files:**
- Modify: `scripts/calibrate_sf_qb_knob.py`
- Test: `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing test**

```python
def _sf12_league():
    return {"roster_positions": ["QB", "SUPER_FLEX"], "total_rosters": 12,
            "scoring_settings": {"rec": 1.0}}


def test_gate_byo_draft_accepts_sf_12team_complete_rookie():
    draft = {"status": "complete", "settings": {"rounds": 4}, "type": "snake"}
    accepted, reason, fmt = cal.gate_byo_draft(draft, _sf12_league())
    assert accepted is True and reason is None and fmt["superflex"] is True


def test_gate_byo_draft_reject_reasons():
    sf12 = _sf12_league()
    # not complete
    a, r, _ = cal.gate_byo_draft({"status": "drafting", "settings": {"rounds": 4}}, sf12)
    assert (a, r) == (False, "not_rookie")
    # malformed rounds (non-int) -> malformed_draft_settings, not a raise
    a, r, _ = cal.gate_byo_draft({"status": "complete", "settings": {"rounds": "x"}}, sf12)
    assert (a, r) == (False, "malformed_draft_settings")
    # startup (rounds > 6)
    a, r, _ = cal.gate_byo_draft({"status": "complete", "settings": {"rounds": 15}}, sf12)
    assert (a, r) == (False, "not_rookie")
    # auction
    a, r, _ = cal.gate_byo_draft({"status": "complete", "settings": {"rounds": 4}, "type": "auction"}, sf12)
    assert (a, r) == (False, "unsupported_draft_type")
    # not SF
    a, r, _ = cal.gate_byo_draft({"status": "complete", "settings": {"rounds": 4}},
                                 {"roster_positions": ["QB"], "total_rosters": 12})
    assert (a, r) == (False, "not_superflex")
    # not 12-team
    a, r, _ = cal.gate_byo_draft({"status": "complete", "settings": {"rounds": 4}},
                                 {"roster_positions": ["SUPER_FLEX"], "total_rosters": 10})
    assert (a, r) == (False, "not_12_team")
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k gate_byo_draft -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Implement**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k gate_byo_draft -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py
git commit -m "feat(sf-qb-cal): gate_byo_draft draft+league gate (defensive rounds, auction reject)"
```

---

## Task 4: `_build_byo_board` (draft_class + malformed picks + first-36 cap)

**Files:**
- Modify: `scripts/calibrate_sf_qb_knob.py`
- Test: `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing test**

```python
def _pick(no, first, last, pos):
    return {"pick_no": no, "metadata": {"first_name": first, "last_name": last, "position": pos}}


def test_build_byo_board_caps_at_36_and_sorts():
    draft = {"season": "2024"}
    league = _sf12_league()
    picks = [
        _pick(40, "Late", "Qb", "QB"),     # excluded (>36)
        _pick(2, "Early", "Wr", "WR"),
        _pick(1, "First", "Qb", "QB"),
    ]
    board, reason = cal._build_byo_board("D1", draft, league, picks)
    assert reason is None
    assert board["draft_class"] == 2024
    assert board["draft_id"] == "D1"
    assert board["source"] == "sleeper_draft:D1"
    assert board["n_picks_raw"] == 3
    assert board["n_picks_used"] == 2
    assert board["n_picks_excluded_after_36"] == 1
    assert [p["ff_slot"] for p in board["picks"]] == [1, 2]   # sorted, capped
    assert board["format_meta"]["superflex"] is True


def test_build_byo_board_invalid_draft_class():
    board, reason = cal._build_byo_board("D1", {"season": None}, {}, [])
    assert board is None and reason == "invalid_draft_class"


def test_build_byo_board_malformed_picks_whole_draft_reject():
    draft = {"season": "2024"}
    picks = [_pick(1, "Ok", "Qb", "QB"), {"metadata": {}}]  # missing pick_no
    board, reason = cal._build_byo_board("D1", draft, _sf12_league(), picks)
    assert board is None and reason == "malformed_picks"


def test_build_byo_board_draft_class_falls_back_to_league_season():
    board, reason = cal._build_byo_board("D1", {"season": None}, dict(_sf12_league(), season="2025"), [])
    assert reason is None and board["draft_class"] == 2025
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k build_byo_board -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 3: Implement**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k build_byo_board -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py
git commit -m "feat(sf-qb-cal): _build_byo_board — fail-closed draft_class, malformed picks, first-36 cap"
```

---

## Task 5: `_collect_byo_boards` + `_fetch_byo_drafts` seam + chain `draft_id`

**Files:**
- Modify: `scripts/calibrate_sf_qb_knob.py`
- Test: `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing test**

```python
def test_collect_byo_boards_accept_reject_and_dedup(monkeypatch):
    drafts = {
        "GOOD": {"status": "complete", "settings": {"rounds": 4}, "type": "snake",
                 "season": "2024", "league_id": "L_GOOD"},
        "NOSF": {"status": "complete", "settings": {"rounds": 4}, "season": "2024",
                 "league_id": "L_NOSF"},
        "NOLG": {"status": "complete", "settings": {"rounds": 4}, "season": "2024"},  # no league_id
    }
    leagues = {
        "L_GOOD": {"roster_positions": ["SUPER_FLEX"], "total_rosters": 12,
                   "scoring_settings": {"rec": 1.0}},
        "L_NOSF": {"roster_positions": ["QB"], "total_rosters": 12, "scoring_settings": {}},
    }
    picks = {"GOOD": [_pick(1, "Caleb", "Williams", "QB")]}

    async def fake_get_draft(did):
        if did == "BOOM":
            raise RuntimeError("network")
        return drafts[did]

    async def fake_get_league(lid):
        return leagues[lid]

    async def fake_get_draft_picks(did):
        return picks.get(did, [])

    monkeypatch.setattr(cal, "get_draft", fake_get_draft)
    monkeypatch.setattr(cal, "get_league", fake_get_league)
    monkeypatch.setattr(cal, "get_draft_picks", fake_get_draft_picks)

    boards, rejections = cal._fetch_byo_drafts(
        ["GOOD", "NOSF", "NOLG", "BOOM", "INCHAIN"], chain_draft_ids={"INCHAIN"}
    )
    assert [b["draft_id"] for b in boards] == ["GOOD"]
    reasons = {r["draft_id"]: r["reason"] for r in rejections}
    assert reasons["NOSF"] == "not_superflex"
    assert reasons["NOLG"] == "missing_league_id"
    assert reasons["BOOM"] == "fetch_failed"
    assert reasons["INCHAIN"] == "duplicate_existing_draft"
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k collect_byo_boards -v`
Expected: FAIL (`AttributeError: ... _fetch_byo_drafts`).

- [ ] **Step 3: Implement**

Add the async collector + sync seam (in the live-fetch section, near `_fetch_league_rookie_drafts`):
```python
async def _collect_byo_boards(draft_ids: list[str], chain_draft_ids: set[str]):
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
            picks = await get_draft_picks(did)
        except Exception:
            rejections.append({"draft_id": did, "reason": "fetch_failed"})
            continue
        accepted, reason, fmt = gate_byo_draft(draft, league)
        if not accepted:
            rejections.append({"draft_id": did, "reason": reason, "format_meta": fmt})
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
```
Then add a non-breaking `draft_id` to each chain board in `_collect_rookie_boards` (inside the `boards.append({...})`), immediately after `"draft_class": draft_class,`:
```python
                    "draft_id": d["draft_id"],
```

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k collect_byo_boards -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py
git commit -m "feat(sf-qb-cal): _collect_byo_boards (fail-closed fetch + cross-source dedup) + chain draft_id"
```

---

## Task 6: `main()` integration — BYO corpus, rank-map exclusion, artifact provenance

**Files:**
- Modify: `scripts/calibrate_sf_qb_knob.py`
- Test: `tests/test_calibrate_sf_qb_knob.py`

- [ ] **Step 1: Write the failing test**

```python
def test_main_includes_byo_and_excludes_rank_map_unavailable(tmp_path, monkeypatch):
    # Chain + seed disabled to isolate BYO behavior.
    monkeypatch.setattr(cal, "_fetch_league_rookie_drafts", lambda league_id: [])
    monkeypatch.setattr(cal, "_load_seed_drafts", lambda: [])
    # BYO: one good 2024 board + one 2027 board (no rank map).
    good = {"draft_class": 2024, "draft_id": "G", "source": "sleeper_draft:G",
            "format_meta": {"superflex": True, "total_rosters": 12, "ppr": 1.0, "te_premium": False},
            "n_picks_raw": 1, "n_picks_used": 1, "n_picks_excluded_after_36": 0,
            "picks": [{"ff_slot": 1, "player_name": "Caleb Williams", "position": "QB"}]}
    future = dict(good, draft_class=2027, draft_id="F", source="sleeper_draft:F")
    monkeypatch.setattr(cal, "_load_byo_draft_ids", lambda: (["G", "F"], []))
    monkeypatch.setattr(cal, "_fetch_byo_drafts", lambda ids, chain: ([good, future], []))
    # Rank maps: 2024 has Caleb at rank 1; 2027 empty (unsupported).
    monkeypatch.setattr(cal, "nfl_skill_ranks",
                        lambda c: {"caleb williams": 1} if c == 2024 else {})

    out = tmp_path / "cal.json"
    cal.main(out_path=out)
    art = json.loads(out.read_text())

    classes = {e["draft_class"] for e in art["per_draft"]}
    assert 2024 in classes and 2027 not in classes          # 2027 excluded from counts
    rejected = {(r["draft_id"], r["reason"]) for r in art["rejected"]}
    assert ("F", "rank_map_unavailable") in rejected
    # capped/format provenance surfaced for the BYO board
    g = next(e for e in art["per_draft"] if e["draft_id"] == "G")
    assert g["format_meta"]["superflex"] is True
    assert g["n_picks_used"] == 1
    # matched-count invariant holds against surviving boards
    assert art["n_qbs_matched"] == sum(e["n_qbs_matched"] for e in art["per_draft"])


def test_main_byo_dupe_within_file_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(cal, "_fetch_league_rookie_drafts", lambda league_id: [])
    monkeypatch.setattr(cal, "_load_seed_drafts", lambda: [])
    monkeypatch.setattr(cal, "_load_byo_draft_ids", lambda: ([], ["DUP"]))
    monkeypatch.setattr(cal, "_fetch_byo_drafts", lambda ids, chain: ([], []))
    monkeypatch.setattr(cal, "nfl_skill_ranks", lambda c: {})
    out = tmp_path / "cal.json"
    cal.main(out_path=out)
    art = json.loads(out.read_text())
    assert ("DUP", "duplicate_draft_id") in {(r["draft_id"], r["reason"]) for r in art["rejected"]}
```

- [ ] **Step 2: Run to verify it fails**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -k "main_includes_byo or main_byo_dupe" -v`
Expected: FAIL (`KeyError: 'rejected'` / per_draft missing draft_id / format_meta).

- [ ] **Step 3: Implement — rewrite `main()`**

Replace the body of `main()` so it collects BYO, excludes rank-map-unavailable boards, and emits the additive provenance. Full new `main()`:
```python
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

    # Exclude boards whose draft_class has no NFL skill-rank map (data-coverage miss,
    # not a name-match miss) so they never inflate the unmatched denominator.
    surviving: list[dict] = []
    for board in boards:
        if not rank_maps.get(board["draft_class"]):
            rejected.append({
                "draft_id": board.get("draft_id"),
                "reason": "rank_map_unavailable",
                "draft_class": board["draft_class"],
            })
        else:
            surviving.append(board)
    boards = surviving

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
        for k in ("n_picks_raw", "n_picks_used", "n_picks_excluded_after_36"):
            if k in board:
                entry[k] = board[k]
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
```
Note: `classes` is reported as all classes seen (incl. excluded) for transparency; counts use `boards` (surviving). The existing per-draft consistency test still holds because `qb_promotions` and `per_draft` both iterate the surviving `boards`.

- [ ] **Step 4: Run to verify it passes**

Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -q`
Expected: PASS (all — new + existing; the existing `test_main_writes_artifact_with_monkeypatched_fetch` still passes because chain boards now also carry `draft_id` and BYO defaults to empty).

- [ ] **Step 5: Commit**

```bash
git add scripts/calibrate_sf_qb_knob.py tests/test_calibrate_sf_qb_knob.py
git commit -m "feat(sf-qb-cal): main() ingests BYO corpus; excludes rank_map_unavailable; rejected/provenance artifact"
```

---

## Task 7: Full-suite + governance guard + ledger

**Files:**
- Modify: `docs/agent-ledger/2026-05-27.md`
- Verify only: full suite + `validate_governance.py`

- [ ] **Step 1: Confirm the existing monkeypatched-fetch test still passes**

The pre-existing `test_main_writes_artifact_with_monkeypatched_fetch` monkeypatches `_fetch_league_rookie_drafts` to return a board WITHOUT `draft_id`. Confirm `chain_draft_ids = {b["draft_id"] for b in chain_boards if b.get("draft_id")}` tolerates that (the `if b.get("draft_id")` guard handles it) and the test still passes.
Run: `./.venv/bin/python3.14 -m pytest tests/test_calibrate_sf_qb_knob.py -q`
Expected: PASS (all).

- [ ] **Step 2: Run the full suite**

Run: `./.venv/bin/python3.14 -m pytest -q`
Expected: PASS, 0 failed (no regressions; the calibration artifact gains `rejected`/provenance keys but no other module asserts that artifact's exact shape).

- [ ] **Step 3: Governance validation**

Run: `./.venv/bin/python3.14 scripts/validate_governance.py`
Expected: PASS.

- [ ] **Step 4: Confirm no curve change / no K application**

Run: `git status --porcelain app/data/valuation/draft_pick_value_curve_v1.json src/dynasty_genius/trade_lab/draft_pick_valuation.py`
Expected: empty (no curve regen, no `sf_qb_promote_slots` change — diagnostic-only).

- [ ] **Step 5: Append ledger entry and commit**

Add a Claude Code build-complete entry to `docs/agent-ledger/2026-05-27.md` (corpus expansion shipped; SF+12-team gate; first-36 cap; rank-map exclusion; diagnostic-only/K-gated; MFL barred; full suite + governance green), then:
```bash
git add docs/agent-ledger/2026-05-27.md
git commit -m "docs(ledger): SF-QB calibration corpus expansion (Increment 2) build complete"
```

---

## Self-Review

**1. Spec coverage:**
- §2 curated file + within-file de-dupe → Task 1. ✓
- §3.1 SF/12T/format helpers + `gate_byo_draft` (defensive rounds, auction) → Tasks 2, 3. ✓
- §3.2 `_build_byo_board` (invalid_draft_class, malformed_picks, first-36 cap + provenance) → Task 4. ✓
- §3.3 fail-closed fetch (missing_league_id, fetch_failed) → Task 5. ✓
- §3.4 cross-source de-dup (duplicate_existing_draft) + chain `draft_id`; rank_map_unavailable exclusion → Tasks 5, 6. ✓
- §4 components / `main()` data flow → Tasks 5, 6. ✓
- §5 artifact (`rejected` reason set, per_draft `format_meta` + cap provenance, matched-count invariant) → Task 6. ✓
- §6 governance (read-only, no K/curve, MFL barred) → Task 7 verification. ✓
- §7 testing intent → covered across Tasks 1–6 + Task 7 full-suite. ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows full code; the curated file ships empty by design (documented no-op), not as a placeholder.

**3. Type consistency:** `gate_byo_draft(draft, league) -> (bool, str|None, dict)` and `_build_byo_board(draft_id, draft, league, picks) -> (dict|None, str|None)` and `_fetch_byo_drafts(draft_ids, chain_draft_ids) -> (boards, rejections)` are consistent across Tasks 3–6; board keys (`draft_class`, `draft_id`, `source`, `format_meta`, `n_picks_raw/used/excluded_after_36`, `picks`) match between Task 4 (producer), Task 5 (collector), and Task 6 (`per_draft` consumer); reject reasons match the §5 enumerated set.
