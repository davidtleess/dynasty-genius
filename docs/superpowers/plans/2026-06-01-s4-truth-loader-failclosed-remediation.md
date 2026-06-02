# S4 Truth-Loader Fail-Closed Remediation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: cockpit-TDD (Codex RED → Claude GREEN → dual CLEAR → commit → loop-closed). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close two fail-closed gaps surfaced by the session retrospective (loader spec §4a, items 8–9) — both tighten-only.

**Architecture:** Both fixes live in `src/dynasty_genius/identity/prospect_nfl_bridge.py`: (1) an all-rows-skipped guard in the shared `_assemble_truth_result` (covers fixture/live/synthetic via the existing wrapper); (2) a `data_mode` validation at the top of `load_nflreadr_draft_truth`. The §11.2a heading rename (#3) is a docs-only change already applied in the spec amendment.

**Tech Stack:** Python 3.14, pytest, ruff (`E4 E7 E9 F I`). No "edge"/"mock"/"adp" on word boundaries.

---

## Task 1: All-skipped guard + `data_mode` validation

**Files:**
- Modify: `src/dynasty_genius/identity/prospect_nfl_bridge.py` (`_assemble_truth_result`; `load_nflreadr_draft_truth`)
- Test: `tests/contract/test_subsystem_4_truth_loader.py` + `tests/contract/test_subsystem_4_runner.py` + `tests/contract/test_subsystem_4_bridge_script.py` — Codex authors RED

- [ ] **Step 1 (RED, Codex):** assert:
  - **All-skipped (loader):** a NON-empty source (≥1 row) where every row is skipped (e.g. a single row with empty `gsis_id`) → raises `NflreadrEmptyTruthError` whose message indicates zero-usable/all-skipped (distinct from the genuinely-empty `rows == []` message). Cover both a fixture (`data_mode="real", fixture_path=`) and the live path (monkeypatched nflreadpy frame of all-bad rows).
  - **Synthetic all-skipped:** a synthetic fixture whose rows are all skipped → `ValueError` carrying `synthetic_truth_fixture_unavailable` (the wrapper catches the `NflreadrEmptyTruthError` and re-raises, same as the empty-fixture case).
  - **Seam/script propagation:** real-mode `run_backtest_a` over an all-skipped source → the exception propagates, NO `backtest_a_result.json` written; the bridge script over an all-skipped source → exits nonzero, NO discovery artifact written.
  - **`data_mode` validation:** `load_nflreadr_draft_truth(2025, data_mode="bogus", fixture_path=<valid>)` → raises `ValueError` (unknown data_mode) BEFORE any fixture/live dispatch (assert the fixture is never read / nflreadpy never called).
  - **Regression (unchanged):** genuinely-empty source (`rows == []`) still raises `NflreadrEmptyTruthError`; a source with ≥1 valid row (even alongside skipped rows) still SUCCEEDS with `truth_rows_loaded == kept count`.
- [ ] **Step 2:** run → fail (no all-skipped guard; `data_mode` unvalidated).
- [ ] **Step 3 (GREEN, Claude):**
  - In `load_nflreadr_draft_truth`, first line of the body: `if data_mode not in ("real", "synthetic"): raise ValueError(f"unknown data_mode {data_mode!r}: expected 'real' or 'synthetic'")` — before the synthetic/fixture/live dispatch.
  - In `_assemble_truth_result`, after the per-row loop + `diagnostics.truth_rows_loaded = len(truth_rows)`, add: `if not truth_rows: raise NflreadrEmptyTruthError(f"draft-truth source had {len(rows)} row(s) but 0 usable after per-row skips: {diagnostics.model_dump()}")`. (Reached only when `rows` was non-empty — the top-of-function empty check already handled `rows == []`. Contaminated rows raise earlier in the loop, so they never reach this.) The synthetic wrapper's existing `except NflreadrEmptyTruthError` re-raises `synthetic_truth_fixture_unavailable`, so synthetic all-skipped is handled with no extra code. **Polish (Codex CLEAR note):** the wrapper's re-raise message currently hardcodes "contains zero rows" — chain the caught exception's message into it (e.g. `f"synthetic_truth_fixture_unavailable: ... {exc}"` / `from exc`) so an all-skipped synthetic fixture surfaces the actual skip reason, not just "zero rows". RED asserts the synthetic all-skipped message conveys the skip cause (not only "zero rows").
- [ ] **Step 4:** focused pass; full S4 contract suite green; `.venv/bin/ruff check src/dynasty_genius/identity/prospect_nfl_bridge.py` clean. Confirm no existing skip test (which always includes a valid row) regressed.
- [ ] **Step 5:** commit `fix(s4): fail-closed on all-skipped source + validate data_mode (retrospective §4a)`.

## Task 2: Full-suite + audit verification

- [ ] **Step 1:** full project suite `.venv/bin/python3.14 -m pytest -q` green; S4 audit green; ruff clean (no new errors vs the pre-existing 45 E712).
- [ ] **Step 2:** commit only if a fix was needed.

---

## Self-Review

**Spec coverage:** loader spec §4a item 8 (all-skipped → fail loud) → T1 (loader/seam/script + synthetic-via-wrapper); item 9 (`data_mode` validation) → T1; #3 heading rename → already in the §11.2a amendment (docs-only). Genuinely-empty + ≥1-valid regressions pinned.

**Placeholder scan:** none; RED bodies Codex-authored, binding assertions pinned.

**Type/name consistency:** reuses `NflreadrEmptyTruthError` (no new type — keeps the synthetic-wrapper catch + the seam/bridge fail-loud plumbing intact); `data_mode ∈ {"real","synthetic"}`.

**Scope:** strictly the two retrospective fail-closed gaps + the heading rename. No model/market/decision surface; `decision_supported` + the §11.2 caveat untouched.
