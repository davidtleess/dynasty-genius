# S4 v2 — Real nflreadr Draft-Capital Truth Loader — Implementation Plan

> **For agentic workers:** This project executes via the **tmux cockpit TDD loop** (Codex authors the RED contract tests; Claude implements GREEN; independent technical CLEAR + governance CLEAR *before* each commit), NOT superpowers subagent dispatch. Steps use checkbox (`- [ ]`) syntax. Authoritative spec: `docs/superpowers/specs/2026-06-01-s4-v2-draft-truth-loader-design.md` (dual-CLEARED). Each task pins exact files + the precise RED assertions (the binding contract); Codex writes the RED test bodies in the loop.

**Goal:** Replace the empty `_load_nflreadr_truth` v1 seam with a real, hardened, verified-column draft-**capital** truth loader so real-mode Backtest-A runs (no more `nflreadr_truth_unavailable`).

**Architecture:** One shared `load_nflreadr_draft_truth(...) -> NflreadrTruthLoadResult(rows, diagnostics)` in `identity/prospect_nfl_bridge.py`, consumed by both the backtest seam (`eval/backtest_mock_draft.py`) and the bridge script (`scripts/build_prospect_nfl_bridge.py`, replacing its buggy copy). Fixture-or-real seam; synthetic mode uses a committed synthetic-truth fixture; fail-closed throughout.

**Tech Stack:** Python 3.14, `.venv/bin/python3.14`, pytest, pydantic v2, polars (nflreadpy returns a polars DataFrame), ruff (`E4 E7 E9 F I`). nflreadpy imported lazily.

---

## File Structure

- **Modify** `src/dynasty_genius/identity/prospect_nfl_bridge.py` — add `NflTruthLoadDiagnostics` (BaseModel), `NflreadrTruthLoadResult` (BaseModel), `NflreadrSchemaDriftError`/`NflreadrSourceContaminationError` (exceptions), `load_nflreadr_draft_truth(...)`, and a `_REQUIRED_DRAFT_COLUMNS` frozenset. **No "mock" substring** anywhere in this file (S4 audit `test_mock_data_and_market_field_isolation`).
- **Modify** `src/dynasty_genius/eval/backtest_mock_draft.py` — `_load_nflreadr_truth` calls the shared loader for **both** real and synthetic modes (synthetic resolves the committed synthetic-truth fixture so the join is non-degenerate; **no bare `[]` hedge**); thread `NflTruthLoadDiagnostics` into `BacktestAResult.metadata["truth_load_diagnostics"]`. The b-gate still abstains for `synthetic_data` (its hedge is unchanged); the truth join must NOT blanket `truth_row_missing` in synthetic mode.
- **Modify** `scripts/build_prospect_nfl_bridge.py` — replace `_load_nflreadr_draft_truth` with a call to the shared loader (kills the broad `except → []`).
- **Create** `tests/contract/test_subsystem_4_truth_loader.py` — the RED suite (Codex).
- **Create fixtures** under `tests/fixtures/backtest_mock_draft/`: `draft_truth/2024.json` (real-mode, source-shaped) and `synthetic_truth/<year>.json` (synthetic).
- **Modify only** these files + fixtures. No Engine A/B, PVO, trade, frontend, or eval-allowlist change.

**Module boundary check:** `load_nflreadr_draft_truth` (source rows → validated `NflTruthRow` list + diagnostics) is independently testable with hand-built source-shaped rows; the seam + bridge-script wrappers are thin adapters.

---

## Task 1: Typed models + exceptions scaffold

**Files:** Modify `src/dynasty_genius/identity/prospect_nfl_bridge.py`; Test `tests/contract/test_subsystem_4_truth_loader.py`.

- [ ] **Step 1 (RED, Codex):** assert the module exposes — `NflTruthLoadDiagnostics` (BaseModel, `extra="forbid"`) with int fields `truth_rows_loaded, skipped_missing_gsis_id, skipped_bad_pick, skipped_bad_round, skipped_missing_name, skipped_missing_position, skipped_missing_team` (default 0) + `required_columns_seen: list[str]`; `NflreadrTruthLoadResult` (BaseModel) with `rows: list[NflTruthRow]` + `diagnostics: NflTruthLoadDiagnostics`; `NflreadrSchemaDriftError` and `NflreadrSourceContaminationError` both subclass `ValueError`. (No "mock" token introduced.)
- [ ] **Step 2:** run → ImportError/AttributeError.
- [ ] **Step 3 (GREEN, Claude):** add the two models + two exceptions + `_REQUIRED_DRAFT_COLUMNS = frozenset({"season","round","pick","team","gsis_id","pfr_player_id","pfr_player_name","position","college"})`.
- [ ] **Step 4:** focused test passes; `.venv/bin/ruff check` clean; `test_subsystem_4_audit.py::test_mock_data_and_market_field_isolation` still passes.
- [ ] **Step 5:** commit `feat(s4v2): truth-load diagnostics + result models + typed exceptions`.

## Task 2: `load_nflreadr_draft_truth` fixture mode — schema gate + mapping + row validation

**Files:** Modify the module; create `tests/fixtures/backtest_mock_draft/draft_truth/2024.json`; extend the test.

- [ ] **Step 1 (RED):** fixture `2024.json` = `{"metadata": {"fetched_at": "2026-01-01T00:00:00Z"}, "rows": [<source-shaped nflreadr rows>]}`. Tests for `load_nflreadr_draft_truth(2024, data_mode="real", fixture_path=<2024.json>)`:
  (a) returns `NflreadrTruthLoadResult`; rows are mapped `NflTruthRow` (gsis_id, pfr_id←pfr_player_id, full_name/normalized_name←pfr_player_name via S3 `normalize_name`, position, college, draft_year=2024, draft_pick_no←pick, draft_round←round, nfl_team←team, fetched_at←metadata.fetched_at);
  (b) **schema gate (missing COLUMN, not bad value):** a required column is "present" iff its KEY appears in every source row (live path: in `df.columns`). If any `_REQUIRED_DRAFT_COLUMNS` key (incl. `pfr_player_id`) is **absent from the source** → raises `NflreadrSchemaDriftError`. This is distinct from a present-column-with-empty/invalid-value, which is a per-row skip (e) — `"pick" not in row` (drift) vs `row["pick"]` empty/non-int (skip). RED covers both: a fixture row-set missing the `pfr_player_id` key entirely → drift raise; a row with `pfr_player_id` key present but null → mapped to `pfr_id=None` (no raise, per (d)).
  (c) **pre-normalized fixture rejected:** a fixture whose rows are NflTruthRow-shaped (no raw `pick`/`round`/`pfr_player_name`) → raises `NflreadrSchemaDriftError` (gate not bypassed);
  (d) **pfr_player_id present-column, null value** → `pfr_id=None` (no raise);
  (e) **per-row skips (present column, bad VALUE — counted, no silent default):** rows where a required column's KEY is present but its value is bad — empty `gsis_id` / empty-or-null-or-non-integer `pick` / empty-or-null-or-non-integer `round` / empty `pfr_player_name` / empty `position` / empty `team` — are each skipped and tallied in the matching `diagnostics.skipped_*`; `truth_rows_loaded` = kept count; `college` may be empty (kept). **(Note: an *absent* `pick`/`round` KEY is schema drift (b), NOT a skip — the skip path applies only to present-key/bad-value rows. A single expected outcome per RED case: `"pick" not in row` → `NflreadrSchemaDriftError`; `row["pick"]` present-but-empty/non-int → `skipped_bad_pick`.)**
  (f) **fetched_at:** all rows take `fetched_at` from `metadata.fetched_at`; two loads of the identical fixture → bit-identical rows; fixture missing `metadata.fetched_at` → raises unless a `fetched_at=` override is passed.
- [ ] **Step 2:** run → fail (function missing).
- [ ] **Step 3 (GREEN):** implement the fixture branch: parse `{metadata, rows}`; verify each required column KEY is present in **every** source row (`all(col in row for row in rows)`; live path: `_REQUIRED_DRAFT_COLUMNS ⊆ df.columns`) → else `NflreadrSchemaDriftError` (missing column ≠ present-but-empty value, which is a per-row skip); map + S3 `normalize_name`; per-row validation/skip with tallies; `fetched_at` from `metadata` (or override); return `NflreadrTruthLoadResult`. No `.get(col, default)` on required columns; no silent `0`.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4v2): fixture-mode draft-truth loader — schema gate + mapping + fail-closed rows`.

## Task 3: Season-integrity contamination (fail loud)

**Files:** Modify the module; extend the test.

- [ ] **Step 1 (RED):** a fixture row with `season != draft_year` (e.g. a 2023 row in the 2024 load) → raises `NflreadrSourceContaminationError` naming `(season, draft_year)` + a row id; it is NOT a counted skip and the bad row is NOT coerced to `draft_year`. A fixture whose rows all match `draft_year` → no raise.
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** in the row loop, before mapping, raise `NflreadrSourceContaminationError` when `int(row["season"]) != draft_year`.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4v2): season-integrity contamination fail-loud`.

## Task 4: Synthetic mode — committed synthetic-truth fixture, fail-closed

**Files:** Modify the module; create `tests/fixtures/backtest_mock_draft/synthetic_truth/2025.json`; extend the test.

- [ ] **Step 1 (RED):** `load_nflreadr_draft_truth(2025, data_mode="synthetic")` (no `fixture_path`) loads the committed `tests/fixtures/backtest_mock_draft/synthetic_truth/2025.json` (source-shaped, same gate/mapping); returns non-empty mapped rows; **never calls nflreadpy** (monkeypatch `nflreadpy.load_draft_picks` to raise → still succeeds from the fixture); a missing/invalid synthetic fixture → raises with an explicit `synthetic_truth_fixture_unavailable` message (NOT a silent `[]`). `fixture_path` overrides the convention path.
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** synthetic branch resolves the convention path (`tests/fixtures/backtest_mock_draft/synthetic_truth/<draft_year>.json`) unless `fixture_path` given; if absent → raise `synthetic_truth_fixture_unavailable`; else reuse the Task-2 fixture path. Never import/call nflreadpy in this branch.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4v2): synthetic-mode committed truth fixture, fail-closed`.

## Task 5: Real-no-fixture live path — lazy nflreadpy

**Files:** Modify the module; extend the test.

- [ ] **Step 1 (RED):** `load_nflreadr_draft_truth(2024, data_mode="real")` (no fixture) calls `nflreadpy.load_draft_picks(seasons=[2024])` via a **lazy inline import** (monkeypatch a fake `nflreadpy.load_draft_picks` returning a small polars DF → mapped rows + same schema gate/season check/row validation as fixture mode). Assert: no top-level `nflreadpy` import in the module (the import is inside the function); live mode with `fetched_at=` override uses it; without override uses `datetime.now(timezone.utc)` (assert format `...Z`, not asserting the value). nflreadpy import failure / fetch raise → propagates (NOT `[]`).
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** real-no-fixture branch: lazy `import nflreadpy`; `df = nflreadpy.load_draft_picks(seasons=[draft_year])`; `df.iter_rows(named=True)` → same gate/season/mapping/validation; `fetched_at` = override or `datetime.now(timezone.utc).isoformat().replace("+00:00","Z")`. No broad `except`.
- [ ] **Step 4:** focused pass; ruff clean (confirm no module-level nflreadpy import).
- [ ] **Step 5:** commit `feat(s4v2): real live path — lazy nflreadpy + verified mapping`.

## Task 6: Wire the backtest seam + diagnostics into the artifact

**Files:** Modify `src/dynasty_genius/eval/backtest_mock_draft.py`; extend `tests/contract/test_subsystem_4_runner.py` (or the truth-loader test).

- [ ] **Step 1 (RED):** Assert the **single** seam behavior (no round-1 `[]` alternative): `_load_nflreadr_truth(draft_year, *, data_mode)` calls the shared `load_nflreadr_draft_truth` for **both** modes and returns `result.rows` — in **synthetic** mode it calls the shared loader's synthetic branch, which resolves the committed synthetic-truth fixture, so the join sees real-shaped synthetic truth and does **NOT** blanket-emit `truth_row_missing` (the b-gate still abstains for `synthetic_data` — that hedge is unchanged); in **real** mode it returns the real rows and `run_backtest_a` no longer appends `nflreadr_truth_unavailable`. **Test seam (no signature change):** RED imports the module under test as `bmd` (`from dynasty_genius.eval import backtest_mock_draft as bmd`) and calls `monkeypatch.setattr(bmd, "load_nflreadr_draft_truth", fake_loader)` — patching the **attribute on the imported module object** (robust to src package aliasing), where `fake_loader` returns a known `NflreadrTruthLoadResult(rows=[...], diagnostics=NflTruthLoadDiagnostics(...))`, then asserts (a) the rows reach the join and (b) `BacktestAResult.metadata["truth_load_diagnostics"]` carries the diagnostics (serialized into `backtest_a_result.json`). `run_backtest_a`'s public signature stays stable — **no fixture arg is added**; the loader is reached only via the module-level seam.
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** `backtest_mock_draft` imports the loader at **module level** (`from dynasty_genius.identity.prospect_nfl_bridge import load_nflreadr_draft_truth`) so the Step-1 `monkeypatch.setattr(bmd, "load_nflreadr_draft_truth", …)` resolves; `_load_nflreadr_truth` calls `load_nflreadr_draft_truth(draft_year, data_mode=data_mode)` (synthetic resolves the committed fixture by convention; real resolves fixture/live per the loader); return `result.rows`; capture `result.diagnostics` and thread it into `BacktestAResult.metadata["truth_load_diagnostics"]` in `run_backtest_a`. Remove the `nflreadr_truth_unavailable` hard-block when rows are present; do not blanket `truth_row_missing` in synthetic mode.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4v2): wire backtest seam to shared loader + diagnostics in artifact`.

## Task 7: Replace the bridge-script loader (DRY, kill broad except)

**Files:** Modify `scripts/build_prospect_nfl_bridge.py`; extend the test.

- [ ] **Step 1 (RED):** `scripts/build_prospect_nfl_bridge.py` imports + calls `load_nflreadr_draft_truth`; its old `_load_nflreadr_draft_truth` (with `pfr_id`/`pick=0` bugs + broad `except → []`) is gone. Schema drift / fetch failure → propagates (nonzero exit / raises), never `[]`. (Test via the CLI module's loader call with a drift fixture.)
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** delete the private buggy loader; call the shared one; surface `NflTruthLoadDiagnostics` in the discovery metadata; no broad `except`.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4v2): bridge script uses shared loader, drops buggy copy + broad-except`.

## Task 8: S4 audit + full-suite green

**Files:** none new (verification task).

- [ ] **Step 1:** run `tests/contract/test_subsystem_4_audit.py` — confirm `test_mock_data_and_market_field_isolation` (no "mock" in `prospect_nfl_bridge.py`), AST anti-laundering, `AUTHORIZED_EVAL_FILES` (unchanged — no new eval file), and the production-import wall all pass.
- [ ] **Step 2:** full suite `.venv/bin/python3.14 -m pytest -q` green; ruff `src app` clean.
- [ ] **Step 3:** if any audit/leakage fails, fix (e.g. rename a "mock"-containing identifier) RED-first; do NOT weaken the audit.
- [ ] **Step 4:** commit only if a fix was needed.

## Task 9: e2e real-mode Backtest-A (no nflreadr_truth_unavailable)

**Files:** none new (local run; optional short validation note, cockpit-reviewed).

- [ ] **Step 1:** exercise real-mode `run_backtest_a` end-to-end **without adding a fixture arg to `run_backtest_a`** — reach the loader the same way Task 6 does: either (a) monkeypatch the module-level `load_nflreadr_draft_truth` seam to resolve a committed real source-shaped fixture, or (b) run live `nflreadpy` for a past class. Confirm `acceptance_criteria_failed` no longer contains `nflreadr_truth_unavailable`, metrics are non-null, and `metadata.truth_load_diagnostics` is present in `backtest_a_result.json`. (No committed real fixture is passed *through* `run_backtest_a` — that seam does not exist and is out of scope.)
- [ ] **Step 2:** full suite green; ruff clean.
- [ ] **Step 3:** record a short result note ONLY if warranted (cockpit-reviewed, descriptive). Commit after dual CLEAR; closing-the-loop audit.

---

## Self-Review

**Spec coverage:** §2 models/exceptions → T1; §3 data modes (fixture/synthetic/live) → T2/T4/T5; §4 fail-closed (schema gate, season, mapping, row skips, fetched_at, broad-except, "mock", lazy import) → T2/T3/T5/T7/T8; §5 diagnostics + artifact home → T1/T6; §7 RED 1–11 → T2–T8; §8 out-of-scope respected (no confirmed-class coverage, no production/PPG truth). No spec section uncovered.

**Placeholder scan:** no TBD/TODO; each task names exact files + concrete RED assertions. (Full RED test *bodies* are Codex-authored in the cockpit loop per project workflow; each task specifies exactly what the test must assert — the binding contract.)

**Type/name consistency:** `NflTruthLoadDiagnostics`, `NflreadrTruthLoadResult`, `NflreadrSchemaDriftError`, `NflreadrSourceContaminationError`, `load_nflreadr_draft_truth`, `_REQUIRED_DRAFT_COLUMNS`, `truth_load_diagnostics`, `synthetic_truth_fixture_unavailable` are used consistently across all tasks and match the spec.

**Resolved task-level decisions (cockpit plan convergence, 2026-06-01):** (1) Task 6 synthetic-seam — `_load_nflreadr_truth(data_mode='synthetic')` calls the shared loader's synthetic branch (committed synthetic-truth fixture), **never a bare `[]`**; the join stays non-degenerate while the b-gate still abstains for `synthetic_data`. (2) Test seam — `run_backtest_a`'s public signature stays stable; both Task 6 and Task 9 reach the loader via the module-level `load_nflreadr_draft_truth` seam (monkeypatch) or live nflreadpy — **no fixture arg is threaded through `run_backtest_a`**. (3) Schema gate (Task 2) — a required column is "present" iff its KEY appears in every source row (live: `df.columns`); a missing column → `NflreadrSchemaDriftError`; a present column with empty/invalid value → per-row skip (distinct concerns).
