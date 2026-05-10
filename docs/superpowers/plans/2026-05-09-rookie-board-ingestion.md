# 2026 Rookie Board Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingest April 2026 NFL Draft results and create a verified prospect manifest for Engine A scoring.

**Architecture:** Use `nfl_data_py` to fetch ground-truth 2026 draft results, map them to `sleeper_id` and `dg_id`, enrich with birth dates, and persist to `resources/prospect_identity_2026.json`. Update the PVO assembler and prospect card script to consume this manifest.

**Tech Stack:** Python, `nfl_data_py`, `httpx`, Pydantic.

---

### Task 1: Draft Ingestion Script

**Files:**
- Create: `scripts/ingest_2026_draft.py`
- Test: `tests/test_prospect_ingestion.py`

- [ ] **Step 1: Write a basic test for nfl_data_py connectivity**

```python
import pytest
import nfl_data_py as nfl

def test_nfl_data_py_2026_results():
    picks = nfl.import_draft_picks([2026])
    assert not picks.empty
    assert "pfr_player_name" in picks.columns
    # Verify top pick
    mendoza = picks[picks["pick"] == 1].iloc[0]
    assert mendoza["pfr_player_name"] == "Fernando Mendoza"
```

- [ ] **Step 2: Run test to verify it passes in this environment**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_prospect_ingestion.py -v`

- [ ] **Step 3: Implement the ingestion script skeleton**

```python
import asyncio
import json
import os
import sys
from pathlib import Path
import nfl_data_py as nfl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.identity import generate_dg_id
from app.data.sleeper import get_all_players

SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}

async def ingest_2026():
    print("Fetching 2026 NFL Draft results...")
    df = nfl.import_draft_picks([2026])
    df = df[df["position"].isin(SKILL_POSITIONS)]
    
    print("Fetching Sleeper player map...")
    sleeper_players = await get_all_players()
    
    # Map by name (fuzzy fallback or exact)
    # nfl_data_py uses pfr_player_name
    
    manifest = {
        "source": "nfl_data_py_verified_nfl_draft",
        "snapshot_date": "2026-05-09",
        "players": []
    }
    
    for _, row in df.iterrows():
        # TODO: ID Mapping & Age Enrichment
        pass
        
    output_path = ROOT / "resources" / "prospect_identity_2026.json"
    output_path.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written to {output_path}")

if __name__ == "__main__":
    asyncio.run(ingest_2026())
```

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_2026_draft.py tests/test_prospect_ingestion.py
git commit -m "feat: initial 2026 draft ingestion script"
```

---

### Task 2: ID Mapping & Age Enrichment

**Files:**
- Modify: `scripts/ingest_2026_draft.py`

- [ ] **Step 1: Implement robust name-based mapping to Sleeper and birth date lookup**

```python
def _map_to_sleeper(name, pos, sleeper_map):
    # Simple name+pos match for now
    search_name = name.lower().replace(".", "").replace("'", "")
    for sid, p in sleeper_map.items():
        if p.get("position") == pos:
            p_name = p.get("full_name", "").lower().replace(".", "").replace("'", "")
            if p_name == search_name:
                return sid, p.get("birth_date")
    return None, None

# In loop:
sid, bdate = _map_to_sleeper(row["pfr_player_name"], row["position"], sleeper_players)
# Fallback for known top prospects if Sleeper is missing data
if row["pfr_player_name"] == "Fernando Mendoza":
    bdate = bdate or "2003-10-01"
# ... etc for top 10
```

- [ ] **Step 2: Run script to generate first manifest**

Run: `.venv/bin/python scripts/ingest_2026_draft.py`

- [ ] **Step 3: Verify resources/prospect_identity_2026.json contains valid data**

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_2026_draft.py resources/prospect_identity_2026.json
git commit -m "data: generated verified 2026 prospect manifest"
```

---

### Task 3: PVO Assembler Integration

**Files:**
- Modify: `src/dynasty_genius/pvo_assembler.py`
- Modify: `scripts/build_prospect_cards.py`

- [ ] **Step 1: Update assemble_roster_audit to prioritize the 2026 verified manifest**

```python
# In build_prospect_cards.py
def main():
    # Use resources/prospect_identity_2026.json instead of the mock file
    # for the 2026 class.
```

- [ ] **Step 2: Update assemble_pvo caveats for VERIFIED_NFL_DRAFT status**

```python
# In pvo_assembler.py: _build_caveats
if identity.verification_status == "VERIFIED_NFL_DRAFT":
    caveats.append("NFL draft capital verified: Engine A signal active")
```

- [ ] **Step 3: Run build_prospect_cards.py to update dashboard artifacts**

Run: `.venv/bin/python scripts/build_prospect_cards.py`

- [ ] **Step 4: Verify test suite still passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -q`

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/pvo_assembler.py scripts/build_prospect_cards.py
git commit -m "feat: wire verified 2026 draft data into Rookie Board"
```
