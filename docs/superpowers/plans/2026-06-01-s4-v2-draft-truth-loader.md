# S4 v2 — Real nflreadr Draft-Capital Truth Loader — Implementation Plan

> **For agentic workers:** This project executes via the **tmux cockpit TDD loop** (Codex authors the RED contract tests; Claude implements GREEN; independent technical CLEAR + governance CLEAR *before* each commit), NOT superpowers subagent dispatch. Steps use checkbox (`- [ ]`) syntax. Authoritative spec: `docs/superpowers/specs/2026-06-01-s4-v2-draft-truth-loader-design.md` (dual-CLEARED). Each task pins exact files + the precise RED assertions (the binding contract); Codex writes the RED test bodies in the loop.

**Goal:** Replace the empty `_load_nflreadr_truth` v1 seam with a real, hardened, verified-column draft-**capital** truth loader so real-mode Backtest-A runs (no more `nflreadr_truth_unavailable`).

**Architecture:** One shared `load_nflreadr_draft_truth(...) -> NflreadrTruthLoadResult(rows, diagnostics)` in `identity/prospect_nfl_bridge.py`, consumed by both the backtest seam (`eval/backtest_mock_draft.py`) and the bridge script (`scripts/build_prospect_nfl_bridge.py`, replacing its buggy copy). Fixture-or-real seam; synthetic mode uses a committed synthetic-truth fixture; fail-closed throughout.

**Tech Stack:** Python 3.14, `.venv/bin/python3.14`, pytest, pydantic v2, polars (nflreadpy returns a polars DataFrame), ruff (`E4 E7 E9 F I`). nflreadpy imported lazily.

---

## File Structure

- **Modify** `src/dynasty_genius/identity/prospect_nfl_bridge.py` — add `NflTruthLoadDiagnostics` (BaseModel), `NflreadrTruthLoadResult` (BaseModel), `NflreadrSchemaDriftError`/`NflreadrSourceContaminationError` (exceptions), `load_nflreadr_draft_truth(...)`, and a `_REQUIRED_DRAFT_COLUMNS` frozenset. **No "mock" substring** anywhere in this file (S4 audit `test_mock_data_and_market_field_isolation`).
- **Modify** `src/dynasty_genius/eval/backtest_mock_draft.py` — `_load_nflreadr_truth` calls the shared loader for **both** real and synthetic modes (synthetic resolves the committed synthetic-truth fixture so the join is non-degenerate; **no bare `[]` hedge**) and **returns the full `NflreadrTruthLoadResult`** (its return type changes from `list[NflTruthRow]` to `NflreadrTruthLoadResult` so diagnostics survive — this is an internal seam change, not a public-signature change). `run_backtest_a` then does `truth_result = _load_nflreadr_truth(...)`, `truth_rows = truth_result.rows`, and threads `truth_result.diagnostics.model_dump()` into `BacktestAResult.metadata["truth_load_diagnostics"]`. The b-gate still abstains for `synthetic_data` (its hedge is unchanged); the truth join must NOT blanket `truth_row_missing` in synthetic mode.
- **Modify** `scripts/build_prospect_nfl_bridge.py` — replace `_load_nflreadr_draft_truth` with a call to the shared loader (kills the broad `except → []`).
- **Create** `tests/contract/test_subsystem_4_truth_loader.py` — the RED suite (Codex).
- **Create fixtures:** real-mode at `tests/fixtures/backtest_mock_draft/draft_truth/2024.json` (source-shaped; reaches the loader via `fixture_path` arg, never hardcoded in production); synthetic at `resources/synthetic_draft_truth/<year>.json` (production-owned committed asset, resolved package-relative — relocated out of `tests/fixtures/backtest_mock_draft/synthetic_truth/` per the 2026-06-01 David-approved §3 amendment so production's by-convention resolution carries no `mock` substring / no prod-reads-`tests/` dependency).
- **Modify only** these files + fixtures. No Engine A/B, PVO, trade, frontend, or eval-allowlist change.

**Module boundary check:** `load_nflreadr_draft_truth` (source rows → validated `NflTruthRow` list + diagnostics) is independently testable with hand-built source-shaped rows; the seam + bridge-script wrappers are thin adapters.

---

## Task 1: Typed models + exceptions scaffold

**Files:** Modify `src/dynasty_genius/identity/prospect_nfl_bridge.py`; Test `tests/contract/test_subsystem_4_truth_loader.py`.

- [ ] **Step 1 (RED, Codex):** assert the module exposes — `NflTruthLoadDiagnostics` (BaseModel, `extra="forbid"`) with int fields `truth_rows_loaded, skipped_missing_gsis_id, skipped_bad_pick, skipped_bad_round, skipped_missing_name, skipped_missing_position, skipped_missing_team` (default 0) + `required_columns_seen: list[str]`; `NflreadrTruthLoadResult` (BaseModel) with `rows: list[NflTruthRow]` + `diagnostics: NflTruthLoadDiagnostics`; `NflreadrSchemaDriftError`, `NflreadrSourceContaminationError`, and `NflreadrEmptyTruthError` all subclass `ValueError`. (No "mock" token introduced.)
- [ ] **Step 2:** run → ImportError/AttributeError.
- [ ] **Step 3 (GREEN, Claude):** add the two models + three exceptions + `_REQUIRED_DRAFT_COLUMNS = frozenset({"season","round","pick","team","gsis_id","pfr_player_id","pfr_player_name","position","college"})`.
- [ ] **Step 4:** focused test passes; `.venv/bin/ruff check` clean; `test_subsystem_4_audit.py::test_mock_data_and_market_field_isolation` still passes.
- [ ] **Step 5:** commit `feat(s4v2): truth-load diagnostics + result models + typed exceptions`.

## Task 2: `load_nflreadr_draft_truth` fixture mode — schema gate + mapping + row validation

**Files:** Modify the module; create `tests/fixtures/backtest_mock_draft/draft_truth/2024.json`; extend the test.

- [ ] **Step 1 (RED):** fixture `2024.json` = `{"metadata": {"fetched_at": "2026-01-01T00:00:00Z"}, "rows": [<source-shaped nflreadr rows>]}`. Tests for `load_nflreadr_draft_truth(2024, data_mode="real", fixture_path=<2024.json>)`:
  (a) returns `NflreadrTruthLoadResult`; rows are mapped `NflTruthRow` (gsis_id, pfr_id←pfr_player_id, full_name/normalized_name←pfr_player_name via S3 `normalize_name`, position, college, draft_year=2024, draft_pick_no←pick, draft_round←round, nfl_team←team, fetched_at←metadata.fetched_at);
  (b) **schema gate (missing COLUMN, not bad value):** a required column is "present" iff its KEY appears in every source row (live path: in `df.columns`). If any `_REQUIRED_DRAFT_COLUMNS` key (incl. `pfr_player_id`) is **absent from the source** → raises `NflreadrSchemaDriftError`. This is distinct from a present-column-with-empty/invalid-value, which is a per-row skip (e) — `"pick" not in row` (drift) vs `row["pick"]` empty/non-int (skip). RED covers both: a fixture row-set missing the `pfr_player_id` key entirely → drift raise; a row with `pfr_player_id` key present but null → mapped to `pfr_id=None` (no raise, per (d)).
  (c) **pre-normalized fixture rejected:** a fixture whose rows are NflTruthRow-shaped (no raw `pick`/`round`/`pfr_player_name`) → raises `NflreadrSchemaDriftError` (gate not bypassed);
  (d) **pfr_player_id present-column, null value** → `pfr_id=None` (no raise);
  (e) **per-row skips (present column, bad VALUE — counted, no silent default):** rows where a required column's KEY is present but its value is bad are each skipped and tallied in the matching `diagnostics.skipped_*`; `truth_rows_loaded` = kept count; `college` may be empty (kept). **Numeric coercion is pinned to a single rule (no ambiguity):** `pick`/`round` are valid iff `type(value) is int` — this accepts the real polars/nflreadpy `int`, and **skips** `bool` (`type(True) is bool`, not `int`), `float` (`1.0`), and numeric strings (`"1"`); any of those → `skipped_bad_pick`/`skipped_bad_round`. Other skips: empty `gsis_id`, empty `pfr_player_name`, empty `position`, empty `team`. **(Note: an *absent* `pick`/`round` KEY is schema drift (b), NOT a skip. Single expected outcome per RED case: `"pick" not in row` → `NflreadrSchemaDriftError`; `"pick" in row` with `type(row["pick"]) is not int` (incl. `True`/`1.0`/`"1"`) → `skipped_bad_pick`.)**
  (f) **fetched_at (verbatim, no normalization):** all rows take `fetched_at` as the **exact string** in `metadata.fetched_at` — it is preserved byte-for-byte, never parsed/reformatted, so a `+00:00` form stays `+00:00` and a `Z` form stays `Z` (two loads of the identical fixture → bit-identical rows). Fixture missing `metadata.fetched_at` → raises unless a `fetched_at=` override is passed (the override string is likewise stored verbatim). (Only the live no-fixture path *generates* a `…Z` string — Task 5.)
  (g) **empty source (fail-closed, not vacuous success):** a fixture with `rows == []` (or a live df with zero rows) must NOT pass the schema gate vacuously and return an empty truth universe. Real/live empty source → raises `NflreadrEmptyTruthError`; synthetic empty fixture → raises `synthetic_truth_fixture_unavailable` (Task 4). Never returns an empty-rows success (that would re-create `nflreadr_truth_unavailable` / synthetic degeneracy).
  (h) **duplicate `gsis_id` preserved (no dedupe):** two source rows with the same `gsis_id` → BOTH appear in `result.rows` (the loader does not deduplicate). Rationale: the join stage (`join_bridge_to_realized`) owns the duplicate-`gsis_id` hard-block (there is already a join test for it); the loader silently de-duping would erase that fail-closed evidence. If duplicate diagnostics are ever wanted, that is a separate spec increment.
  (i) **extra source columns dropped safely (`extra="forbid"` guard):** a source row carrying columns beyond `_REQUIRED_DRAFT_COLUMNS` (real nflreadr frames have many) loads successfully, and the extra keys do **not** appear in the produced `NflTruthRow.model_dump()` — proving the mapping constructs `NflTruthRow` from explicitly-mapped fields only and never splats the raw source row into the `extra="forbid"` model (which would raise in live mode).
- [ ] **Step 2:** run → fail (function missing).
- [ ] **Step 3 (GREEN):** implement the fixture branch: parse `{metadata, rows}`; **empty-source guard first** — if `rows` is empty (real/live) → raise `NflreadrEmptyTruthError` (do NOT let `all(...)` pass vacuously); verify each required column KEY is present in **every** source row (`rows and all(col in row for row in rows)`; live path: `_REQUIRED_DRAFT_COLUMNS ⊆ df.columns` with a non-empty df) → else `NflreadrSchemaDriftError` (missing column ≠ present-but-empty value, which is a per-row skip); per-row: season-contamination check (Task 3), then `type(...) is int` validation for `pick`/`round` (skip+tally otherwise), map via S3 `normalize_name`; **construct each `NflTruthRow` from explicitly-mapped fields only — never `NflTruthRow(**row)` / splat the raw source row** (extra source columns must not reach the `extra="forbid"` model); `fetched_at` taken verbatim from `metadata` (or override); duplicates by `gsis_id` are kept (no dedupe); return `NflreadrTruthLoadResult`. No `.get(col, default)` on required columns; no silent `0`.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4v2): fixture-mode draft-truth loader — schema gate + mapping + fail-closed rows`.

## Task 3: Season-integrity contamination (fail loud)

**Files:** Modify the module; extend the test.

- [ ] **Step 1 (RED):** a fixture row with `season != draft_year` (e.g. a 2023 row in the 2024 load) → raises `NflreadrSourceContaminationError` naming `(season, draft_year)` + a row id; it is NOT a counted skip and the bad row is NOT coerced to `draft_year`. **Season type is pinned (no silent `int()` coercion):** a row is valid only if `type(row["season"]) is int and row["season"] == draft_year`; a non-int season (`"2024"` string, `2024.0` float, `True`) → `NflreadrSourceContaminationError` (treated as source malformation/contamination, never `int("2024")`-coerced into a pass). A fixture whose rows all have integer `season == draft_year` → no raise.
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** in the row loop, before mapping, raise `NflreadrSourceContaminationError` when `type(row["season"]) is not int or row["season"] != draft_year` (no `int(...)` coercion).
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4v2): season-integrity contamination fail-loud`.

## Task 4: Synthetic mode — committed synthetic-truth fixture, fail-closed

**Files:** Modify the module; create `resources/synthetic_draft_truth/2025.json` (production-owned committed asset, per the §3 amendment); extend the test.

- [ ] **Step 1 (RED):** `load_nflreadr_draft_truth(2025, data_mode="synthetic")` (no `fixture_path`) loads the committed `resources/synthetic_draft_truth/2025.json` (source-shaped, same gate/mapping); returns non-empty mapped rows; **never calls nflreadpy** (monkeypatch `nflreadpy.load_draft_picks` to raise → still succeeds from the fixture); a missing/invalid synthetic fixture → raises with an explicit `synthetic_truth_fixture_unavailable` message (NOT a silent `[]`). `fixture_path` overrides the convention path.
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** synthetic branch resolves the convention path (`Path(__file__).resolve().parents[3] / "resources" / "synthetic_draft_truth" / f"{draft_year}.json"`) unless `fixture_path` given; if the resolved file is absent → raise `ValueError("synthetic_truth_fixture_unavailable: ... {draft_year}")`; else reuse the Task-2 `_load_draft_truth_from_fixture`, re-raising its `NflreadrEmptyTruthError` as `synthetic_truth_fixture_unavailable` (empty synthetic fixture → unavailable token, not the real-mode empty error). Never import/call nflreadpy in this branch (carries no `mock`/`adp`/nflreadpy substring).
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

- [ ] **Step 1 (RED):** Assert the **single** seam behavior (no round-1 `[]` alternative): `_load_nflreadr_truth(draft_year, *, data_mode)` calls the shared `load_nflreadr_draft_truth` for **both** modes and **returns the full `NflreadrTruthLoadResult`** (return type changes from `list[NflTruthRow]` to `NflreadrTruthLoadResult`) — in **synthetic** mode it calls the shared loader's synthetic branch, which resolves the committed synthetic-truth fixture, so the join sees real-shaped synthetic truth and does **NOT** blanket-emit `truth_row_missing`; in **real** mode it returns the real rows and `run_backtest_a` no longer appends `nflreadr_truth_unavailable`. **Test seam (no public-signature change):** RED imports the module under test exactly as the existing S4 tests do — `from src.dynasty_genius.eval import backtest_mock_draft as bmd` — and calls `monkeypatch.setattr(bmd, "load_nflreadr_draft_truth", fake_loader)` (patches the attribute on the imported module object; `fake_loader` returns a known `NflreadrTruthLoadResult(rows=[...], diagnostics=NflTruthLoadDiagnostics(...))`). Then asserts: (a) the rows reach the join; (b) `BacktestAResult.metadata["truth_load_diagnostics"]` carries `truth_result.diagnostics.model_dump()` (serialized into `backtest_a_result.json`); **(c) synthetic abstain proof — with a non-empty synthetic truth join, `backtest_b_gate_status.overall_status == "always_abstain_synthetic_data"` still holds** (loading real-shaped synthetic truth does NOT flip the gate to pass/fail — the exact risk David flagged). `run_backtest_a`'s public signature stays stable — **no fixture arg is added**; the loader is reached only via the module-level seam.
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN):** `backtest_mock_draft` imports the loader at **module level**, matching the repo's import style — `from src.dynasty_genius.identity.prospect_nfl_bridge import load_nflreadr_draft_truth` (the module already imports from `src.dynasty_genius.identity.prospect_nfl_bridge`, lines 561+) — so the Step-1 `monkeypatch.setattr(bmd, "load_nflreadr_draft_truth", …)` resolves; `_load_nflreadr_truth` calls `load_nflreadr_draft_truth(draft_year, data_mode=data_mode)` and **returns the full `NflreadrTruthLoadResult`**. `run_backtest_a` then does `truth_result = _load_nflreadr_truth(...)`; `truth_rows = truth_result.rows`; `metadata["truth_load_diagnostics"] = truth_result.diagnostics.model_dump()`. Remove the `nflreadr_truth_unavailable` hard-block when rows are present; do not blanket `truth_row_missing` in synthetic mode.
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

**Plan additions BEYOND spec §7's 11 REDs (adversarial-review hardening — flag for ratification):** the Codex falsification round surfaced six contract points the spec's 11 REDs under-specify; the plan adds them as Task-2/3/6 REDs and one new typed exception (`NflreadrEmptyTruthError`): (12) empty source fails closed (not vacuous schema-gate success); (13) duplicate `gsis_id` preserved for the join hard-block; (14) extra source columns dropped (no splat into `extra="forbid"`); (15) numeric coercion pinned to `type(x) is int`; (16) `fetched_at` stored verbatim. These only **tighten** the spec's fail-closed direction (§4.5 "never returns []") — they do not loosen any contract. **Resolved (2026-06-01, David-approved; cockpit unanimous — Codex technical + Gemini governance Option (b)):** folded into a **spec addendum** — `docs/superpowers/specs/2026-06-01-s4-v2-draft-truth-loader-design.md` §9 + RED 12–16 + `NflreadrEmptyTruthError`. Spec and plan are now in formal sync; both files re-CLEAR together before build.

**Placeholder scan:** no TBD/TODO; each task names exact files + concrete RED assertions. (Full RED test *bodies* are Codex-authored in the cockpit loop per project workflow; each task specifies exactly what the test must assert — the binding contract.)

**Type/name consistency:** `NflTruthLoadDiagnostics`, `NflreadrTruthLoadResult`, `NflreadrSchemaDriftError`, `NflreadrSourceContaminationError`, `NflreadrEmptyTruthError`, `load_nflreadr_draft_truth`, `_REQUIRED_DRAFT_COLUMNS`, `truth_load_diagnostics`, `synthetic_truth_fixture_unavailable` are used consistently across all tasks and match the spec. Imports use the repo convention `from src.dynasty_genius...` (verified against existing S4 tests + `backtest_mock_draft.py`). `_load_nflreadr_truth` returns `NflreadrTruthLoadResult` (not `list[NflTruthRow]`) so diagnostics survive to the artifact.

**Resolved task-level decisions (cockpit plan convergence, 2026-06-01):** (1) Task 6 synthetic-seam — `_load_nflreadr_truth(data_mode='synthetic')` calls the shared loader's synthetic branch (committed synthetic-truth fixture), **never a bare `[]`**; the join stays non-degenerate while the b-gate still abstains for `synthetic_data`. (2) Test seam — `run_backtest_a`'s public signature stays stable; both Task 6 and Task 9 reach the loader via the module-level `load_nflreadr_draft_truth` seam (`monkeypatch.setattr(bmd, ...)` with `from src.dynasty_genius.eval import backtest_mock_draft as bmd`) or live nflreadpy — **no fixture arg is threaded through `run_backtest_a`**; `_load_nflreadr_truth` returns the full `NflreadrTruthLoadResult` so `run_backtest_a` can thread `.diagnostics.model_dump()` into the artifact. (3) Schema gate (Task 2) — a required column is "present" iff its KEY appears in every (non-empty) source row (live: `df.columns`); empty source → `NflreadrEmptyTruthError` (real) / `synthetic_truth_fixture_unavailable` (synthetic), never vacuous success; missing column → `NflreadrSchemaDriftError`; present-key/bad-value → per-row skip. (4) **Adversarial-review hardening (2026-06-01, Codex falsification round):** numeric coercion pinned to `type(x) is int` (rejects bool/float/str); season `type is int and == draft_year` (no `int()` coercion); `fetched_at` stored verbatim; duplicate `gsis_id` preserved (join owns the hard-block); extra source columns dropped via explicit field-mapping (never splat into `extra="forbid"` `NflTruthRow`); synthetic b-gate abstain asserted with non-empty join.
