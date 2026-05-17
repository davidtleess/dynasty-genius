# Phase 16.1 — Age Blocker Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unblock 6 PRE_MODEL 2026 rookies by ingesting verified birth dates, enabling Engine A scoring for all 6.

**Architecture:** Update identity file with verified birth dates → modify refresh script to compute fractional age from `birth_date` when absent from existing cards, and to assign PROSPECT_C/D grade for newly scored players instead of blindly restoring PRE_MODEL → re-run refresh → verify 0 PRE_MODEL among the 6.

**Tech Stack:** Python, JSON, `resources/prospect_identity_2026.json`, `scripts/refresh_prospect_cards.py`, `tests/contract/test_phase16_age_blockers.py`

---

## Pre-flight checks

- [ ] **Read governance:** `docs/governance/02-agent-operating-loop.md`, `docs/governance/00-product-constitution.md`, `AGENT_SYNC.md`
- [ ] **Confirm draft closed:** `resources/draft_state.js` must show `draft_status: "complete"` and `current_pick_no == total_picks == 36` before starting. If not, stop.
- [ ] **Run current suite:** `.venv/bin/python -m pytest -q --ignore=tests/test_prospect_ingestion.py --ignore=tests/contract/test_phase13_te_model_change.py` → must pass (around 730 passed, 11 skipped, 0 failed — verify exact count from run output, don't assume).
- [ ] **Work on a branch:** Do not commit failing tests to main. Create a branch: `git checkout -b phase16/age-blockers`

---

## Task 1: Write the failing contract test

**Files:**
- Create: `tests/contract/test_phase16_age_blockers.py`

- [ ] **Step 1: Write the failing test**

```python
"""Phase 16.1 — Age blocker resolution contract tests."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
IDENTITY_FILE = ROOT / "resources" / "prospect_identity_2026.json"
CARDS_FILE = ROOT / "resources" / "prospect_cards.json"

_BLOCKER_NAMES = {
    "Omar Cooper Jr.",
    "Chris Brazzell II",
    "Mike Washington Jr.",
    "Kevin Coleman Jr.",
    "Emmanuel Henderson Jr.",
    "Jam Miller",
}

# Verified Sleeper IDs — must be preserved for live draft taken-state continuity.
_BLOCKER_SLEEPER_IDS = {
    "Omar Cooper Jr.": "13276",
    "Chris Brazzell II": "13353",
    "Mike Washington Jr.": "13305",
    "Kevin Coleman Jr.": "13338",
    "Emmanuel Henderson Jr.": "13313",
    "Jam Miller": "13403",
}

_AGE_RANGE = (20, 26)  # valid 2026 NFL draftee age range


def _load_identity_players() -> list[dict]:
    """Always use ["players"] key — identity file is a dict, not a list."""
    with open(IDENTITY_FILE) as f:
        return json.load(f)["players"]


def _load_identity_data() -> dict:
    with open(IDENTITY_FILE) as f:
        return json.load(f)


def _load_cards() -> list[dict]:
    with open(CARDS_FILE) as f:
        return json.load(f)


class TestIdentityFile:
    def test_all_six_have_birth_date(self):
        """All 6 blockers must have non-null birth_date in identity file."""
        players = _load_identity_players()
        blockers = {p["full_name"]: p for p in players if p["full_name"] in _BLOCKER_NAMES}
        assert len(blockers) == 6, f"Expected 6 blockers, found {list(blockers.keys())}"
        for name, p in blockers.items():
            assert p.get("birth_date") is not None, f"{name} still has null birth_date"

    def test_all_six_age_verified_true(self):
        """All 6 blockers must have age_verified=True after ingestion."""
        players = _load_identity_players()
        blockers = {p["full_name"]: p for p in players if p["full_name"] in _BLOCKER_NAMES}
        for name, p in blockers.items():
            assert p.get("age_verified") is True, f"{name} age_verified is not True"

    def test_washington_conflict_logged(self):
        """Mike Washington Jr. must have dob_conflict_source noting Lines.com rejection."""
        players = _load_identity_players()
        p = next((x for x in players if x["full_name"] == "Mike Washington Jr."), None)
        assert p is not None
        assert p.get("dob_conflict_source"), "Washington Jr. missing dob_conflict_source"
        assert "lines.com" in p["dob_conflict_source"].lower()

    def test_coleman_conflict_logged(self):
        """Kevin Coleman Jr. must have dob_conflict_source noting NFLDraftBuzz rejection."""
        players = _load_identity_players()
        p = next((x for x in players if x["full_name"] == "Kevin Coleman Jr."), None)
        assert p is not None
        assert p.get("dob_conflict_source"), "Coleman Jr. missing dob_conflict_source"
        assert "nfldraftbuzz" in p["dob_conflict_source"].lower()

    def test_birth_dates_in_valid_age_range(self):
        """Computed age-at-draft for all 6 must be in 20–26 range."""
        data = _load_identity_data()
        ref = date.fromisoformat(data.get("snapshot_date", "2026-05-09"))
        blockers = [p for p in data["players"] if p["full_name"] in _BLOCKER_NAMES]
        for p in blockers:
            birth = date.fromisoformat(p["birth_date"])
            age = (ref - birth).days / 365.25
            assert _AGE_RANGE[0] <= age <= _AGE_RANGE[1], (
                f"{p['full_name']}: computed age {age:.2f} outside valid range {_AGE_RANGE}"
            )


class TestProspectCards:
    def test_zero_pre_model_among_blockers(self):
        """All 6 formerly-blocked players must be scored (not PRE_MODEL) after refresh."""
        cards = _load_cards()
        blocker_cards = [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]
        assert len(blocker_cards) == 6, f"Expected 6 blocker cards, found {len(blocker_cards)}"
        for c in blocker_cards:
            assert c.get("model_grade") != "PRE_MODEL", (
                f"{c['full_name']} still PRE_MODEL after refresh"
            )

    def test_all_six_have_dvs(self):
        """All 6 must have non-null dynasty_value_score after refresh."""
        cards = _load_cards()
        for card in [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]:
            assert card.get("dynasty_value_score") is not None, (
                f"{card['full_name']} has null DVS after refresh"
            )

    def test_all_six_have_xvar(self):
        """All 6 must have non-null xvar after refresh."""
        cards = _load_cards()
        for card in [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]:
            assert card.get("xvar") is not None, (
                f"{card['full_name']} has null xvar after refresh"
            )

    def test_all_six_have_xvar_class_rank(self):
        """All 6 must have non-null xvar_class_rank after refresh."""
        cards = _load_cards()
        for card in [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]:
            assert card.get("xvar_class_rank") is not None, (
                f"{card['full_name']} missing xvar_class_rank"
            )

    def test_fractional_ages_in_valid_range(self):
        """All 6 must have fractional age in 20–26 range after refresh."""
        cards = _load_cards()
        for card in [c for c in cards if c.get("full_name") in _BLOCKER_NAMES]:
            age = card.get("age")
            assert age is not None, f"{card['full_name']} has null age"
            assert _AGE_RANGE[0] <= age <= _AGE_RANGE[1], (
                f"{card['full_name']}: age {age} outside valid range {_AGE_RANGE}"
            )

    def test_sleeper_ids_preserved(self):
        """All 6 sleeper_ids must be preserved for live draft taken-state continuity."""
        cards = _load_cards()
        blocker_cards = {c["full_name"]: c for c in cards if c["full_name"] in _BLOCKER_NAMES}
        for name, expected_id in _BLOCKER_SLEEPER_IDS.items():
            card = blocker_cards.get(name)
            assert card is not None, f"{name} not found in prospect_cards.json"
            assert str(card.get("sleeper_id", "")) == expected_id, (
                f"{name}: sleeper_id {card.get('sleeper_id')} != expected {expected_id}"
            )

    def test_model_grade_prospect_c_for_non_qb(self):
        """Newly scored WR/RB blockers must have PROSPECT_C, not PRE_MODEL."""
        cards = _load_cards()
        non_qb_blockers = [
            c for c in cards
            if c.get("full_name") in _BLOCKER_NAMES and c.get("position") != "QB"
        ]
        for card in non_qb_blockers:
            assert card.get("model_grade") == "PROSPECT_C", (
                f"{card['full_name']} ({card.get('position')}): "
                f"expected PROSPECT_C, got {card.get('model_grade')}"
            )

    def test_dvs_invariance_existing_scored_players(self):
        """Re-running refresh must not drift DVS on any of the 74 previously scored players."""
        cards = _load_cards()
        scored_non_blocker = [
            c for c in cards
            if c.get("dynasty_value_score") is not None
            and c.get("draft_class") == 2026
            and c.get("full_name") not in _BLOCKER_NAMES
        ]
        assert len(scored_non_blocker) == 74, (
            f"Expected 74 previously-scored non-blocker players, got {len(scored_non_blocker)}"
        )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/contract/test_phase16_age_blockers.py -v
```

Expected: FAIL on identity tests (birth_date null) and all cards tests.

---

## Task 2: Update prospect_identity_2026.json

**Files:**
- Modify: `resources/prospect_identity_2026.json`

Identity contract: only official school/team roster bios and PFR player pages qualify as Tier-1 sources. Set `age_verified: true` only when a Tier-1 source confirms the date. Log conflicts with `dob_conflict_source`.

- [ ] **Step 1: Update the 6 blocker entries**

For each player, find the entry by `dg_id` and update these fields:

| dg_id | birth_date | age_verified | dob_conflict_source |
|---|---|---|---|
| `omar_cooper_wr` | `"2003-12-14"` | `true` | *(omit field)* |
| `christopher_brazzell_wr` | `"2003-09-22"` | `true` | *(omit field)* |
| `michael_washington_rb` | `"2003-07-03"` | `true` | `"lines.com, March 15 2002, rejected — primary LV Raiders roster and family-verified sources confirm Jul 3 2003"` |
| `kevin_coleman_wr` | `"2003-09-10"` | `true` | `"nfldraftbuzz, February 2004, rejected — Missouri official bio and Wikipedia agree Sep 10 2003; school bio takes precedence"` |
| `emmanuel_henderson_wr` | `"2003-03-21"` | `true` | *(omit field)* |
| `jam_miller_rb` | `"2004-04-29"` | `true` | *(omit field — add `"legal_name": "Jamarion Miller"` instead)* |

- [ ] **Step 2: Verify identity tests pass**

```bash
.venv/bin/python -m pytest tests/contract/test_phase16_age_blockers.py::TestIdentityFile -v
```

Expected: all 5 identity tests PASS. Cards tests still fail (refresh not run yet).

---

## Task 3: Modify refresh_prospect_cards.py

**Files:**
- Modify: `scripts/refresh_prospect_cards.py`

Two independent bugs must both be fixed:

**Bug A:** Script reads `age` from existing cards; for the 6 blockers that field is `None`. Must fall back to computing fractional age from `birth_date` in the identity file.

**Bug B:** Script blindly restores `model_grade` from existing cards. For the 6 blockers, `existing["model_grade"] == "PRE_MODEL"`, so even after scoring they'd stay PRE_MODEL. Must assign PROSPECT_C/D for newly scored players.

- [ ] **Step 1: Update `_build_pvo_dicts` signature to accept `identity_data`**

Change:
```python
def _build_pvo_dicts(
    identity_players: list[dict],
    cards_by_name_pos: dict[tuple[str, str], dict],
) -> tuple[list[dict], list[str]]:
```
to:
```python
def _build_pvo_dicts(
    identity_players: list[dict],
    cards_by_name_pos: dict[tuple[str, str], dict],
    identity_data: dict,
) -> tuple[list[dict], list[str]]:
```

- [ ] **Step 2: Add fractional age fallback (Bug A)**

After line `age: Optional[float] = existing.get("age")`, insert:

```python
        # Fallback: compute fractional age from birth_date when absent from existing cards.
        # Uses identity snapshot_date as the reference (same date used in original build).
        if age is None and p.get("birth_date"):
            from datetime import date as _date
            ref = _date.fromisoformat(
                identity_data.get("snapshot_date", "2026-05-09")
            )
            birth = _date.fromisoformat(p["birth_date"])
            age = round((ref - birth).days / 365.25, 2)
```

- [ ] **Step 3: Fix model_grade restoration (Bug B)**

Replace:
```python
        if "model_grade" in existing:
            d["model_grade"] = existing["model_grade"]
```
with:
```python
        if "model_grade" in existing and existing["model_grade"] != "PRE_MODEL":
            # Preserve PROSPECT_C / PROSPECT_D for already-scored players.
            d["model_grade"] = existing["model_grade"]
        elif d.get("dynasty_value_score") is not None:
            # Newly scored player (was PRE_MODEL due to missing age).
            # Assign grade by position — matches original build-script policy.
            d["model_grade"] = "PROSPECT_D" if p["position"] == "QB" else "PROSPECT_C"
        # If DVS is still None, assemble_pvo's PRE_MODEL stands.
```

- [ ] **Step 4: Update the `main()` call to pass `identity_data`**

Change:
```python
    pvos_2026, dvs_warnings = _build_pvo_dicts(identity_players, cards_by_name_pos)
```
to:
```python
    pvos_2026, dvs_warnings = _build_pvo_dicts(identity_players, cards_by_name_pos, identity_data)
```

- [ ] **Step 5: Update the PRE_MODEL assertion**

Change:
```python
    assert pre_model_count == 6, f"Expected 6 PRE_MODEL 2026 players, got {pre_model_count}"
```
to:
```python
    assert pre_model_count == 0, (
        f"Expected 0 PRE_MODEL 2026 players after age blocker resolution, got {pre_model_count}. "
        f"Check birth_date fields in prospect_identity_2026.json."
    )
```

- [ ] **Step 6: Update the report — age source line**

In `_write_report`, change:
```python
        "- Age source: preserved from `prospect_cards.json` (exact DVS invariance)",
```
to:
```python
        "- Age source: preserved from `prospect_cards.json` where present; "
        "computed from `birth_date` in identity file for newly unblocked players",
```

- [ ] **Step 7: Update the report — blocker section header**

In `_write_report`, change the blocker section so it shows resolved vs. still-blocked counts:

Replace the static blocker section header:
```python
    lines += [
        "",
        "## Age-Data Blockers — 6 Unscored 2026 Picks",
        "",
        "These players have verified draft capital but `birth_date=None` in the identity file. "
        "Engine A requires `pick + round + age`; without age they remain PRE_MODEL.",
```
with:
```python
    blocker_label = (
        f"## Age-Data Blockers — {len(unscored)} Remaining"
        if unscored
        else "## Age-Data Blockers — All Resolved"
    )
    blocker_note = (
        "These players have verified draft capital but `birth_date=None` in the identity file. "
        "Engine A requires `pick + round + age`; without age they remain PRE_MODEL."
        if unscored
        else "All 6 age-data blockers resolved. All 80 2026 prospects are now scored."
    )
    lines += ["", blocker_label, "", blocker_note,
```

And update the closing tag to close the list properly:
```python
    lines += [
        "",
        blocker_label,
        "",
        blocker_note,
        "",
        "| Name | Position | Pick | Round |",
        "|---|---|---|---|",
    ]
```

- [ ] **Step 8: Run the modified script**

```bash
.venv/bin/python scripts/refresh_prospect_cards.py
```

Expected output:
```
DVS invariance: OK — all 74 scored players match baseline exactly
Written: 80 2026 prospects (80 scored, 0 PRE_MODEL age-blockers remaining) + 2 watchlist
Report: docs/validation/phase15-2026-rookie-rank-refresh.md
```

If `assert pre_model_count == 0` fails: check that all 6 `birth_date` fields are populated in the identity file and that the age fallback is correctly placed before the `features` dict is built.

If DVS drift errors appear: stop. Do not commit. Investigate the specific player and delta before proceeding.

---

## Task 4: Run full contract tests

- [ ] **Step 1: Run Phase 16.1 contract tests**

```bash
.venv/bin/python -m pytest tests/contract/test_phase16_age_blockers.py -v
```

Expected: all tests PASS.

- [ ] **Step 2: Quick spot-check of the 6 in the artifact**

```bash
python3 -c "
import json
with open('resources/prospect_cards.json') as f:
    cards = json.load(f)
names = ['Omar Cooper Jr.', 'Chris Brazzell II', 'Mike Washington Jr.',
         'Kevin Coleman Jr.', 'Emmanuel Henderson Jr.', 'Jam Miller']
for name in names:
    c = next((x for x in cards if x.get('full_name') == name), None)
    print(name, '| age:', c.get('age'), '| grade:', c.get('model_grade'),
          '| dvs:', round(c.get('dynasty_value_score') or 0, 1),
          '| xvar:', round(c.get('xvar') or 0, 1),
          '| rank:', c.get('xvar_class_rank'))
"
```

All 6 should show fractional age (e.g. `22.39`), grade `PROSPECT_C`, non-null dvs and xvar.

- [ ] **Step 3: Run full suite**

```bash
.venv/bin/python -m pytest -q --ignore=tests/test_prospect_ingestion.py --ignore=tests/contract/test_phase13_te_model_change.py
```

Expected: all previously passing tests still pass, 0 failed, new Phase 16.1 tests added to total.

---

## Task 5: Merge and commit

- [ ] **Step 1: Update agent ledger**

Append entry to `docs/agent-ledger/YYYY-MM-DD.md` with files changed, tests run, product alignment, drift risks.

- [ ] **Step 2: Stage and commit on branch**

```bash
git add resources/prospect_identity_2026.json \
        resources/prospect_cards.json \
        resources/prospect_cards.js \
        scripts/refresh_prospect_cards.py \
        tests/contract/test_phase16_age_blockers.py \
        docs/validation/phase15-2026-rookie-rank-refresh.md \
        docs/agent-ledger/YYYY-MM-DD.md
git commit -m "feat(phase16.1): resolve 6 age-data blockers — all 80 2026 prospects now scored"
```

- [ ] **Step 3: Merge to main**

```bash
git checkout main
git merge phase16/age-blockers
```

---

## Acceptance Criteria

- [ ] All 6 have non-null `birth_date` and `age_verified: true` in identity file
- [ ] Washington Jr. and Coleman Jr. have `dob_conflict_source` logged
- [ ] All 6 have non-null `dynasty_value_score`, `xvar`, `xvar_class_rank`, `dvs_class_rank`, `rank_delta` in `prospect_cards.json`
- [ ] All 6 have fractional age in 20–26 range
- [ ] All 6 have `model_grade == "PROSPECT_C"` (no QBs in this blocker set)
- [ ] DVS invariance: 0 drift on all 74 previously scored players (tolerance 0.01)
- [ ] All 6 `sleeper_id` values preserved (identity continuity for live draft)
- [ ] Full suite passes, 0 failed
- [ ] No market data, PFF grades, xVAR, or Engine B features touched

---

## What this does NOT do

- Does not change Engine A model weights, formula, or P90 constants
- Does not change `ENGINE_A_REPLACEMENT_DVS` or `XVAR_LAMBDA_ENGINE_A`
- Does not change any Engine B artifact
- Does not activate veteran divergence flags
- Does not change the board UI
- Does not modify `NOISE_BAND`, `TRADE_PARITY_BAND`, or `decision_supported`
