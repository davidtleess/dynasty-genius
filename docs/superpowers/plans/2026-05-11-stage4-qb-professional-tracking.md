# Stage 4 QB Professional Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add roster-facing QB professional tracking context for active NFL quarterbacks using nflreadpy, while keeping Engine A unchanged and deferring any Engine B model training until the aging-curve and outcome-variable decisions are explicitly approved.

**Architecture:** Stage 4 is Option C. The work splits into two bounded tracks. Track 1 reruns the QB college backtest with the `college_team` fix so Engine A’s QB path is closed on corrected data. Track 2 builds a separate QB professional-context layer: an nflreadpy adapter, a deterministic identity bridge, governed context fields, and a roster-audit surface that shows EPA, CPOE, and DAKOTA as decision context only. The pro layer is not a model-input lane, and it is not Engine B training. It is a display/context lane that can be promoted later only after Phase 5 exists.

**Tech Stack:** Python 3.9/3.11 compatible repo code, `nflreadpy`, pandas at the boundary, `pytest`, `python-dotenv`, Markdown docs, standard library JSON and dataclasses.

---

## File Map

| Status | File | Purpose |
|---|---|---|
| Modify | `scripts/backtest_qb_cfbd.py` | Re-run the Engine A QB backtest with the `college_team` fix |
| Modify | `src/dynasty_genius/adapters/cfbd_qb_adapter.py` | Keep the `college_team` override path for the validation rerun |
| Modify | `src/dynasty_genius/models/engine_a_contract.py` | Add QB professional-context column constants, without touching Engine A model inputs |
| Modify | `src/dynasty_genius/sources/source_registry.py` | Add a governed context-only source for QB pro telemetry |
| Modify | `app/services/roster_auditor.py` | Surface QB professional context alongside the existing age-curve audit |
| Create | `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py` | Normalize nflreadpy QB telemetry into a context-only dict |
| Create | `scripts/build_nflreadpy_qb_identity_bridge.py` | Build the QB name/gsis_id bridge from roster data |
| Create | `resources/nflreadpy_qb_id_map.json` | Identity map for active/recent QBs |
| Create | `tests/test_nflreadpy_qb_adapter.py` | Adapter contract, None semantics, and coverage tests |
| Create | `tests/test_nflreadpy_qb_identity_bridge.py` | Identity-bridge coverage and determinism tests |
| Create | `tests/test_roster_qb_context.py` | Roster-audit QB context surface tests |
| Modify | `tests/test_source_registry.py` | Registry expectations for the new QB context source |

---

## Task 0: Close the Engine A QB College Loop

**Goal:** Re-run the QB college backtest with the `college_team` fix so the current Engine A QB path is evaluated on the corrected data rather than the stale null-heavy path.

**Files:**
- Modify: `scripts/backtest_qb_cfbd.py`
- Modify: `src/dynasty_genius/adapters/cfbd_qb_adapter.py`
- Modify: `docs/validation/qb_cfbd_backtest_report.md` (regenerated output)

- [ ] **Step 1: Re-run the backtest with the corrected team lookup**

Run:

```bash
.venv/bin/python scripts/backtest_qb_cfbd.py
```

Expected:
- The team-stats lookup uses `entry["cfbd_college"]` when available.
- `sack_rate` and `passing_yards_share` null counts drop from the old 125/126 pattern.

- [ ] **Step 2: Regenerate the report**

Confirm `docs/validation/qb_cfbd_backtest_report.md` is rewritten and captures the new metrics.

- [ ] **Step 3: Decide Engine A QB closure**

If the rerun still fails the promotion gate, close the Engine A QB college path cleanly and stop expanding it.
If the rerun improves materially, document the result but keep it separate from Stage 4 pro tracking.

- [ ] **Step 4: Commit**

```bash
git add scripts/backtest_qb_cfbd.py src/dynasty_genius/adapters/cfbd_qb_adapter.py docs/validation/qb_cfbd_backtest_report.md
git commit -m "fix(qb): rerun CFBD backtest with college_team lookup"
```

---

## Task 1: Define QB Professional Context Contract

**Goal:** Create a governed context-only schema for active-QB pro telemetry so the display layer has explicit allowed fields and the registry can enforce role separation.

**Files:**
- Modify: `src/dynasty_genius/models/engine_a_contract.py`
- Modify: `src/dynasty_genius/sources/source_registry.py`
- Modify: `tests/test_source_registry.py`

**Contract choice:**
- New constant: `QB_CONTEXT_COLUMNS`
- Fields:
  - `epa_per_dropback`
  - `cpoe`
  - `dakota`
  - `dropback_count`
  - `pass_attempts`
- Provenance siblings remain explicit in the surface layer as `source_epa_per_dropback`, `source_cpoe`, `source_dakota`, `source_dropback_count`, and `source_pass_attempts`.
- Source registry entry name: `nflreadpy_qb_context`
- Roles: `context_signal`
- `provenance_required=True`
- `failure_behavior="skip_enrichment"`
- `cache_policy="json_cache"`
- `freshness_hours=24`

- [ ] **Step 1: Write the failing registry tests**

Update `tests/test_source_registry.py` so it asserts:
- `nflreadpy_qb_context` exists
- it is `context_signal`
- it is not `model_input`
- its allowed fields do not intersect `ALLOWED_ENRICHMENT_COLUMNS`
- every source gate string still points to a real test file path

- [ ] **Step 2: Add the contract constant**

Add `QB_CONTEXT_COLUMNS` to `src/dynasty_genius/models/engine_a_contract.py` and keep it out of `ALLOWED_ENRICHMENT_COLUMNS`.

- [ ] **Step 3: Add the source registry entry**

Add `nflreadpy_qb_context` to `src/dynasty_genius/sources/source_registry.py` with the fields and role above.

- [ ] **Step 4: Run the registry tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_source_registry.py -q
```

Expected:
- pass with the new source classification enforced.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/models/engine_a_contract.py src/dynasty_genius/sources/source_registry.py tests/test_source_registry.py
git commit -m "feat: add governed qb pro context source"
```

---

## Task 2: Build the nflreadpy QB Adapter

**Goal:** Fetch active-QB professional telemetry from nflreadpy and normalize it into a context-only dict with explicit None semantics.

**Files:**
- Create: `src/dynasty_genius/adapters/nflreadpy_qb_adapter.py`
- Create: `tests/test_nflreadpy_qb_adapter.py`

- [ ] **Step 1: Write the failing adapter tests**

Create tests that assert:
- the adapter returns a stable dict shape for a QB/season input
- missing snaps or missing source data return `None`, not `0.0`
- the adapter accepts a `gsis_id` and seasons list
- output includes only the QB context fields from `QB_CONTEXT_COLUMNS`
- no Engine A pre-NFL feature names appear in the adapter output

Example test scaffold:

```python
from unittest.mock import patch


def test_fetch_qb_nfl_stats_returns_none_without_snaps():
    with patch("src.dynasty_genius.adapters.nflreadpy_qb_adapter.load_pbp") as load_pbp:
        load_pbp.return_value = None
        result = fetch_qb_nfl_stats("00-0031234", [2024])
    assert result["epa_per_dropback"] is None
    assert result["cpoe"] is None
```

- [ ] **Step 2: Run the adapter tests and confirm failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_nflreadpy_qb_adapter.py -q
```

Expected:
- import/implementation failures until the adapter exists.

- [ ] **Step 3: Implement the adapter**

Implement:
- `fetch_qb_nfl_stats(gsis_id: str, seasons: list[int]) -> dict[str, Any]`
- conversion from nflreadpy Polars output to pandas at the boundary, then to plain dicts
- season-level aggregation for EPA, CPOE, DAKOTA, dropback count, and pass attempts
- defensive None semantics for missing or partial data

Do **not** add the result to Engine A feature matrices.

- [ ] **Step 4: Run the adapter tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_nflreadpy_qb_adapter.py -q
```

Expected:
- pass, with all non-integration tests green.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/adapters/nflreadpy_qb_adapter.py tests/test_nflreadpy_qb_adapter.py
git commit -m "feat: add nflreadpy qb professional telemetry adapter"
```

---

## Task 3: Build the QB Identity Bridge

**Goal:** Map active/recent QBs from roster identity into nflreadpy identities so professional telemetry can be fetched deterministically and audited.

**Files:**
- Create: `scripts/build_nflreadpy_qb_identity_bridge.py`
- Create: `resources/nflreadpy_qb_id_map.json`
- Create: `tests/test_nflreadpy_qb_identity_bridge.py`

- [ ] **Step 1: Write the failing bridge tests**

Create tests that assert:
- the bridge emits a JSON map keyed by the repo’s canonical QB identity key
- each resolved QB has a stable `gsis_id`
- unresolved players are explicitly marked `NONE`, not silently dropped
- combined coverage is reported and asserted against an 80% threshold for the active-QB set

- [ ] **Step 2: Run the bridge tests and confirm failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_nflreadpy_qb_identity_bridge.py -q
```

Expected:
- import/implementation failures until the bridge script exists.

- [ ] **Step 3: Implement the bridge**

Use roster data from `nflreadpy.load_rosters(...)` and the repo’s canonical identity source to produce a deterministic map with:
- `pfr_player_name`
- `gsis_id`
- `season`
- coverage status
- fallback reason for unresolved rows

Keep the bridge reviewable and export the JSON artifact under `resources/`.

- [ ] **Step 4: Run the bridge tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_nflreadpy_qb_identity_bridge.py -q
```

Expected:
- pass with the agreed coverage threshold and stable output.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_nflreadpy_qb_identity_bridge.py resources/nflreadpy_qb_id_map.json tests/test_nflreadpy_qb_identity_bridge.py
git commit -m "feat: build nflreadpy qb identity bridge"
```

---

## Task 4: Surface QB Context in the Roster Audit

**Goal:** Extend the roster audit response so active QBs show EPA/CPOE/DAKOTA context cards without changing the existing age-curve-only decision model.

**Files:**
- Modify: `app/services/roster_auditor.py`
- Create: `tests/test_roster_qb_context.py`

- [ ] **Step 1: Write the failing surface tests**

Create tests that assert:
- `run_audit()` returns a new `qb_context_cards` field for active QBs
- each QB context card contains the QB context fields and their `source_` siblings
- non-QB roster assets still behave exactly as before
- the roster audit remains `decision_supported: False`

Example test scaffold:

```python
def test_run_audit_includes_qb_context_cards():
    result = asyncio.run(run_audit())
    qb_cards = result["qb_context_cards"]
    assert qb_cards
    assert all("epa_per_dropback" in card for card in qb_cards)
    assert all(card["decision_supported"] is False for card in qb_cards)
```

- [ ] **Step 2: Run the surface tests and confirm failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_roster_qb_context.py -q
```

Expected:
- import/implementation failures until the roster audit is extended.

- [ ] **Step 3: Wire the adapter + bridge into the roster audit**

In `app/services/roster_auditor.py`, load the QB identity bridge, fetch QB professional telemetry for active QBs, and attach the resulting context cards to the audit payload.

Keep the existing age-curve audit behavior intact for non-QB and QB roster assets.

- [ ] **Step 4: Run the surface tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_roster_qb_context.py -q
```

Expected:
- pass with QB context cards present and age-curve audit behavior preserved.

- [ ] **Step 5: Commit**

```bash
git add app/services/roster_auditor.py tests/test_roster_qb_context.py
git commit -m "feat: surface qb professional context in roster audit"
```

---

## Task 5: Final Verification and Handoff

**Goal:** Verify the Stage 4 display/context layer is green and the repo state is honest about what is and is not a model input.

**Files:**
- None new; verify the files changed in Tasks 0-4

- [ ] **Step 1: Run the targeted QB test suites**

Run:

```bash
.venv/bin/python -m pytest tests/test_cfbd_qb_adapter.py tests/test_nflreadpy_qb_adapter.py tests/test_nflreadpy_qb_identity_bridge.py tests/test_roster_qb_context.py -q
```

Expected:
- pass

- [ ] **Step 2: Run the full suite**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected:
- all previously passing tests still pass
- any live integration tests remain skipped if they are still intentionally gated

- [ ] **Step 3: Update governance state**

Append the session record to the daily ledger and update `AGENT_SYNC.md` if the sprint state changed.

- [ ] **Step 4: No additional commit**

Each earlier task has its own commit. If Task 5 reveals a final verification-only fix, commit that fix with the exact task files involved and the message that matches the affected task.

---

## Non-Goals

- No Engine B training code.
- No addition of EPA/CPOE/DAKOTA to `POSITION_FEATURE_MATRIX` as model inputs.
- No change to the QB rookie/college feature contract.
- No new outcome variable for Engine B until Phase 5 is explicitly defined.
- No promotion of active-QB telemetry to model inputs in this stage.
