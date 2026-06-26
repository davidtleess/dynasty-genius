# F-feature-refresh Implementation Plan

> **For agentic workers:** This plan is executed via the project's **cockpit TDD** loop (Codex authors the RED against each task's falsification contract → Claude GREEN → dual-CLEAR → David-authorized commit → post-commit zero-divergence). Steps use checkbox (`- [ ]`) syntax for tracking. Spec: `docs/superpowers/specs/2026-06-25-f-feature-refresh-design.md` (v3, dual-CLEARed).

**Goal:** Let engine_b features (and thus PVO/DVS/xVAR outputs) legitimately change over time as fresh `nflreadpy` data lands, so the dual-capture model series accrues DISTINCT `(semantic_output_hash, provenance_hash)` vintages — with frozen model weights, fail-closed integrity gates, a seed-split artifact model, and an automated no-commit refresh.

**Architecture:** A source-hash-gated runner regenerates the engine_b feature set to a temp **candidate**; fail-closed integrity gates validate it, then an atomic publish promotes it to a **gitignored runtime** CSV (committed **seed** is the durable baseline). One shared resolver makes every feature-CSV consumer read runtime-if-present-else-seed and stamp which. A later LaunchAgent runs the runner automatically (no-commit), honestly `noop`-ing when upstream is unchanged. Model weights stay frozen throughout.

**Tech Stack:** Python 3.14 (`.venv/bin/python3.14`), pandas, `nflreadpy`, scikit-learn Ridge (frozen .pkl), pytest, ruff; FastAPI for the league API.

## Global Constraints

- Run tests with `.venv/bin/python3.14 -m pytest` (NOT bare `python`/`poetry`). Lint: `.venv/bin/ruff check`.
- **Feature-refresh ONLY — model weights FROZEN.** The refresh path is physically barred from `.fit()`, training entrypoints (`scripts/train_engine_b.py`), and writing any `.pkl`/model artifact under `app/data/models/`. Enforced by an audit test.
- **Market is NEVER a feature.** Re-run the `MARKET_PROHIBITED` / `engine_b_contract` leakage check on every candidate; fail-closed.
- `decision_supported=false` everywhere model output is surfaced; divergence remains UNVALIDATED (Gate-4 is a separate forward study — this work enables vintage movement, not a signal).
- **No auto-commit (Option-C / no-scheduler-commits).** The runner/scheduler regenerate on-disk runtime only; committing the seed baseline is exclusively David-gated.
- **Seed-split:** committed seed (`app/data/training/engine_b_features_v2.csv`) is the durable baseline; the runtime CSV + its provenance/report/ready-marker are **gitignored**.
- **Fail-closed:** a runtime CSV that exists but fails validation aborts/refuses to score (preserve/restore prior valid runtime); seed fallback ONLY when runtime is ABSENT.
- Local-first; **no Databricks** (`nflreadpy` is local/free). **Frontend HOLD** — API only, no UI.
- No banned David-facing tokens (literal-list contract test set).
- **Canonical artifact paths (P1) — exact, used verbatim by all tasks/tests:**
  - Seed (committed, durable): `app/data/training/engine_b_features_v2.csv`
  - Runtime dir (gitignored): `app/data/features_runtime/`
  - Candidate (temp, pre-validate): `app/data/features_runtime/engine_b_features_candidate.csv`
  - Runtime CSV (published): `app/data/features_runtime/engine_b_features_runtime.csv`
  - Ready-marker (T2, only after full validation): `app/data/features_runtime/engine_b_features_runtime.ready.json`
  - Runner report/provenance (holds last `source_hash`; written by T1, read for noop-gating): `app/data/features_runtime/feature_refresh_latest_report.json`
  - Lock: `app/data/features_runtime/feature_refresh.lock`
  - Scheduler logs: `app/data/logs/feature_refresh.{out,err}.log`
  - `.gitignore` adds `app/data/features_runtime/` (logs dir already gitignored).
- Every task: Codex RED → Claude GREEN → full `tests/contract` regression + ruff + banned-token probe → dual-CLEAR → David-authorized commit → post-commit zero-divergence audit.

---

## File Structure

| Path | Responsibility | Task |
|---|---|---|
| `src/dynasty_genius/features/feature_refresh_runner.py` | Source-hash-gated regeneration to a temp candidate; status semantics; `--preflight`; no model writes | T1 |
| `scripts/run_feature_refresh.py` | Thin cwd-independent CLI wrapper over the runner (`main(argv)->int`) | T1 |
| `src/dynasty_genius/features/feature_assembly.py` (NEW helper, P4) | T1: `inference_season_rule` + `assemble_feature_candidate` (seam — schema-conformant shape + inference partition). T1b: `build_engine_b_features` (real frame-injectable engineering) | T1, T1b |
| `scripts/assemble_engine_b_dataset.py` | T1: refactor the outcome/drop block (~352–358) to the shared inference rule (no `<2024`/`dropna`). T1b: delegate the 11-step engineering to `build_engine_b_features` (keep module-level names for the 4 dependents). **Do NOT touch `app/data/pipeline/train_models.py`** | T1, T1b |
| `src/dynasty_genius/features/feature_validation.py` | Fail-closed integrity gates (leakage/schema/identity/coverage/range/NaN); drift report-only telemetry | T2 |
| `src/dynasty_genius/features/feature_publish.py` | Atomic temp→validate→rename; ready-marker/manifest; preserve/restore-on-failure | T2 |
| `src/dynasty_genius/features/feature_source.py` | The ONE shared resolved-feature-source helper (runtime-if-present-else-seed) + source metadata | T3 |
| `app/services/engine_b_service.py` | Route `_DATASET_PATH` reads through the shared resolver | T3 |
| `scripts/build_universe_pvo_batch.py` | Route BOTH the direct feature-row read AND `score_inference_partition` through the resolver | T3 |
| `src/dynasty_genius/capture/model_forward_capture_driver.py` | Stamp `feature_source_kind`/hash/`source_as_of` from the resolver | T3 |
| `src/dynasty_genius/what_changed/report.py` + league API | Surface model `as_of`/vintage freshness label | T3 |
| `ops/launchd/com.davidleess.dynasty-feature-refresh.plist` + scheduler-contract test | Automated no-commit source-hash-gated refresh (after gates) | T4 |
| `.gitignore` | Add the gitignored runtime/provenance/report/ready-marker/lock paths | T1 |

---

## Per-task execution conventions (P6) — exact commands + commit scope

Every task uses these verbatim (so steps are executable without guessing):
- **Step 2 (run RED):** `.venv/bin/python3.14 -m pytest tests/contract/<task_test>.py -q` → expected **FAIL** (missing module/function/behavior).
- **Step 4 (run GREEN):** same focused command → expected **PASS**; then `.venv/bin/python3.14 -m pytest tests/contract -q` → expected **all pass** (baseline 1078 + the task's new tests); then `.venv/bin/ruff check <touched paths>` → **All checks passed!**; then the literal-list **banned-token probe** over touched src/docs → **NONE**.
- **Step 5 (commit, David-gated)** — exact per-task scope:
  - **T1:** `src/dynasty_genius/features/feature_assembly.py` (seam) + `feature_refresh_runner.py` + `scripts/run_feature_refresh.py` (real-run gated) + `scripts/assemble_engine_b_dataset.py` (outcome/drop → shared inference rule) + `.gitignore` + `tests/contract/test_feature_refresh_runner.py`
  - **T1b:** `src/dynasty_genius/features/feature_assembly.py` (`build_engine_b_features` extraction) + `scripts/assemble_engine_b_dataset.py` (delegate engineering) + `scripts/run_feature_refresh.py` (remove T1 gate) + `tests/contract/test_feature_engineering_extraction.py`
  - **T2:** `src/dynasty_genius/features/feature_validation.py` + `feature_publish.py` + runner wiring + `tests/contract/test_feature_validation.py` + `test_feature_publish.py`
  - **T3:** `src/dynasty_genius/features/feature_source.py` + the 4 consumer edits (`engine_b_service.py`, `build_universe_pvo_batch.py`, `model_forward_capture_driver.py`, `what_changed/report.py` + API route) + `frontend/openapi.json` (only if the API DTO changed) + `tests/contract/test_feature_source_resolver.py` (+ consumer-test additions)
  - **T4:** `ops/launchd/com.davidleess.dynasty-feature-refresh.plist` + `tests/contract/test_feature_refresh_ops_scheduler.py` + `docs/ARTIFACTS.md` + `docs/development/quick-reference.md`
  - Commit message: `feat(feature-refresh): T<N> — <summary>`, ending with the `Co-Authored-By: Claude Opus 4.8 (1M context)` trailer.

> **Scope split (cockpit-cleared, Option B):** the full frame-injectable feature-engineering extraction is its own task **T1b**, sequenced **before T2**. **T1 produces a SCHEMA-CONFORMANT SEAM candidate** (correct `ENGINE_B_OUTPUT_COLUMNS` shape + inference partition; uncomputable features may be null pre-T1b) — it is **NOT** a "full scoreable" candidate (that is T1b). T1's real-run is **gated** so it cannot publish a misleading seam artifact before T1b. (Codex's 5 conditions: T1b-before-T2; seam-not-scoreable wording; no misleading artifact; T1b RED verifies real values; T2 validates only the T1b candidate.)

## Task 1 — Refresh runner + schema-conformant seam + inference-rule refactor + no-fit audit

**Deliverable:** `scripts/run_feature_refresh.py` + `feature_assembly.assemble_feature_candidate` regenerate a temp **schema-conformant SEAM candidate** (exact `ENGINE_B_OUTPUT_COLUMNS` order; the single latest season preserved as the inference partition with `training_eligible=false`/null outcome; complete-window training rows; no helper/leak columns — feature *values* that need the full engineering may be null until T1b), source-hash-gated, with the model-write guardrail proven by an audit test. The legacy `scripts/assemble_engine_b_dataset.py` outcome/drop block is refactored to the shared `inference_season_rule`/`assemble_feature_candidate` path (no `<2024`, no unconditional `dropna`). **The CLI real-run is GATED (refuses with a clear "full feature engineering lands in T1b" error) so no seam artifact can be published before T1b.** No resolver, no production read of runtime, no scheduler, no validation gates.

**Files:**
- Create: `src/dynasty_genius/features/feature_refresh_runner.py`, `scripts/run_feature_refresh.py`
- Modify: the engine_b feature-assembly inference logic (currently `scripts/assemble_engine_b_dataset.py` ~lines 352–358) — extract the inference-partition rule into a testable function
- Modify: `.gitignore` (add `app/data/features_runtime/` — covers the candidate/runtime/ready-marker/report/lock paths pinned in Global Constraints)
- Test: `tests/contract/test_feature_refresh_runner.py`

**Interfaces — Produces:**
- `compute_source_hash(*, loader_outputs, seasons_window, package_version, builder_config, te_rubric_artifacts, identity_inputs) -> str` — canonical over the C4 input set, EXCLUDES timestamps.
- `inference_season_rule(seasons_window) -> int` — the intended inference season (max completed source season / current-season boundary), NOT hardcoded `< 2024`.
- `assemble_feature_candidate(*, seasons_window, read_fns) -> pd.DataFrame` — training rows require a complete outcome; **intended-inference-season rows are preserved with `training_eligible=False` and a null outcome allowed.**
- `run_feature_refresh(*, runtime_dir, seed_path, now_fn, read_fns, preflight=False) -> dict` — returns `{status, publish_performed, source_hash, candidate_path?, dirty_paths, commit_required_for_repo_baseline, decision_supported: False, ...}`.
  - **T1-only status semantics (P2):** `status` ∈ {`candidate_ready` (source changed → candidate written, NOT published), `noop` (source unchanged), `blocked` (assembly error)}; **`publish_performed=false` always in T1** (publish is T2). The post-T2 contract adds `status=ok` with `publish_performed=true` once the validated runtime is published — T1 never emits `ok` (it would falsely imply runtime freshness before gates exist).
  - **noop hash store (P3):** the last `source_hash` lives in the gitignored runner report JSON `app/data/features_runtime/feature_refresh_latest_report.json` (written by T1 after every candidate run, read at the start to noop-gate) — independent of the T2 runtime/ready-marker, so T1 nooping works before any publish path exists.
- `scripts/run_feature_refresh.py: main(argv)->int`, module-level `ROOT` (monkeypatchable), cwd-independent `sys.path` bootstrap.

**Falsification contract the RED (Codex) must prove:**
1. **Inference-partition (C1):** given a seasons window through the latest season, `assemble_feature_candidate` yields rows for the intended inference season with `training_eligible=False` and null outcome retained; training rows still require a complete outcome. (Direct refutation of the current outcome-drop behavior.)
2. **Inference-season rule:** `inference_season_rule` returns the computed boundary, not a hardcoded `2024`.
3. **Source-hash determinism (C4/C5):** identical injected source inputs → identical `source_hash` regardless of `now_fn`; a changed source input → changed hash; timestamps never affect it.
4. **noop:** when `source_hash` matches the last recorded hash, `status=noop`, `refresh_performed=False`, no candidate write.
5. **`--preflight`:** readiness-only — never assembles/writes; nonzero only on a readiness failure.
6. **No model writes (audit):** running the runner (and importing the runner module) performs NO `.fit()` call, imports/invokes NO training entrypoint, and writes NOTHING under `app/data/models/`. (Use a spy/monkeypatch on `.fit` + assert the models dir mtime/byte-identical + a static scan that the module does not import `train_engine_b`.)
7. **Cwd-independent:** standalone out-of-repo load works (use pytest `tmp_path` for cwd, NOT a hardcoded path — the WR2 CI-portability lesson).
8. **Gitignore:** `git check-ignore` passes for the runtime/candidate paths.
9. **Schema-conformant seam shape (P7):** `assemble_feature_candidate` columns `== ENGINE_B_OUTPUT_COLUMNS` (exact order); inference partition correct (single latest season preserved with `training_eligible=False`/null outcome; complete-window training rows retain outcomes; in-between incomplete-window non-latest seasons dropped); NO helper/outcome-leak columns (`ppg_t1`/`ppg_t2`/`games_t1`/`games_t2`/…). Feature *values* needing the full engineering may be null pre-T1b (seam, not scoreable).
10. **Legacy refactor (P7):** `scripts/assemble_engine_b_dataset.py` source no longer contains `df["training_eligible"] = df["feature_season"] < 2024` or `dropna(subset=[OUTCOME_COLUMN])`; it references `inference_season_rule` + `assemble_feature_candidate`.
11. **CLI real-run gate (P7):** the non-`--preflight` CLI run REFUSES with a clear "full feature engineering lands in T1b" error (no seam artifact can be published before T1b).

**Steps:** (the RED step covers contract items 1–11)
- [ ] **Step 1 — Codex authors the RED** `tests/contract/test_feature_refresh_runner.py` covering contract items 1–11 (injected `read_fns`/`now_fn`/dirs; fixture nflreadpy-shaped frames incl. a latest season with no outcome; schema-conformant seam shape; legacy-refactor source assertions; CLI real-run gate). Verify it is ruff-clean.
- [ ] **Step 2 — Run RED:** `.venv/bin/python3.14 -m pytest tests/contract/test_feature_refresh_runner.py -q` → expect failures (module/functions absent).
- [ ] **Step 3 — Claude GREEN:** implement `feature_refresh_runner.py` + `scripts/run_feature_refresh.py` + the extracted inference-partition rule + `.gitignore` entries; the `.fit`/model-write guardrail (the runner never imports training code; assert at runtime).
- [ ] **Step 4 — Run GREEN:** the RED file passes; then `.venv/bin/python3.14 -m pytest tests/contract -q` (full regression) + `.venv/bin/ruff check` (touched files) + banned-token probe.
- [ ] **Step 5 — Cockpit dual-CLEAR** (Codex technical + Gemini governance), then **David-authorized commit**; post-commit zero-divergence audit.

---

## Task 1b — Frame-injectable full Engine-B feature-engineering extraction

**Deliverable:** Extract `scripts/assemble_engine_b_dataset.py`'s 11-step feature engineering (base stats, min-games filter, roster/age, snap share, PBP QB-efficiency [EPA/CPOE/DAKOTA], route metrics from participation, multi-year trends, QB archetype, aging curves, TE role-risk) into a **frame-injectable, testable** function `feature_assembly.build_engine_b_features(*, read_fns, seasons_window) -> pd.DataFrame`, so `assemble_feature_candidate` produces a **genuinely scoreable** candidate with REAL feature values. `scripts/assemble_engine_b_dataset.py` becomes a thin loader (nflreadpy → frames) that calls the shared function (no behavior change to its committed output; the 4 importing tests + `run_pvo_refresh` stay green). Removes the T1 real-run gate.

**Files:**
- Modify: `src/dynasty_genius/features/feature_assembly.py` (add `build_engine_b_features`; `assemble_feature_candidate` calls it)
- Modify: `scripts/assemble_engine_b_dataset.py` (delegate engineering to the shared function; keep module-level names `ENGINE_B_OUTPUT_COLUMNS`/`OUTCOME_COLUMN`/`add_te_role_risk_feature*`/`fetch_and_agg_stats` for the 4 dependents)
- Modify: `scripts/run_feature_refresh.py` (remove the T1 real-run gate)
- Test: `tests/contract/test_feature_engineering_extraction.py`

**Interfaces — Produces:** `build_engine_b_features(*, read_fns, seasons_window) -> pd.DataFrame` (full engineered features, pre-partition).

**Falsification contract the RED (Codex) must prove (real values, not just shape):** injected `player_stats` + `rosters` + `snap_counts` + `pbp` + `participation` + TE artifacts → **non-null/expected** `snap_share`, `route_participation`, `yprr`/`tprr`, QB-efficiency fields (`epa_per_dropback`/`cpoe`/`dakota`), multi-year availability flags, `aging_curve_*`, `te_role_is_risk_profile`; exact `ENGINE_B_OUTPUT_COLUMNS` order; no helper/outcome-leak columns; inference-season rows preserved with null outcome; and `assemble_engine_b_dataset`'s committed output is byte-equivalent to pre-refactor (regression-guarded by the 4 dependent tests + the 1087 suite).

**Steps:** Codex RED (real-value fixtures) → run RED → Claude GREEN (extract engineering, frame-injectable, robust) → full regression (esp. the 4 dependents + `run_pvo_refresh`) + ruff + banned probe → dual-CLEAR → David-authorized commit → post-commit audit. **T1b lands BEFORE T2.**

---

## Task 2 — Validation gates + atomic publish + ready-marker

> Validates and publishes ONLY the **T1b real candidate** (never the T1 seam).

**Deliverable:** A fail-closed integrity gate module + an atomic publish that promotes a validated candidate to the gitignored runtime with a ready-marker; preserve/restore prior valid runtime on failure; drift as report-only telemetry.

**Files:**
- Create: `src/dynasty_genius/features/feature_validation.py`, `src/dynasty_genius/features/feature_publish.py`
- Modify: `src/dynasty_genius/features/feature_refresh_runner.py` (wire validate→publish; add `status=blocked` path)
- Test: `tests/contract/test_feature_validation.py`, `tests/contract/test_feature_publish.py`

**Interfaces — Consumes:** T1's `run_feature_refresh`, candidate DataFrame/CSV. **Produces:**
- `validate_feature_candidate(df, *, inference_season) -> ValidationResult` (`.ok: bool`, `.failures: list[str]`, `.drift: dict` report-only). Gates: leakage (`MARKET_PROHIBITED`/`engine_b_contract`), schema (exact cols/dtypes, no market-like cols), identity/key (no blank IDs on scored rows, no dup player-season, valid positions), coverage (total + per-position floors + **inference-season presence**), range sanity (rates/shares ∈ [0,1], plausible age, non-negative counts), NaN integrity (no all-null critical features, per-feature NaN ceilings).
- `publish_runtime(candidate_path, *, runtime_dir) -> dict` — atomic `temp → validate → os.replace` rename; writes runtime CSV + provenance + report + **ready-marker** only after full validation; on any PUBLISH failure preserves/restores the prior valid runtime byte-identical and returns `status=blocked` + reason. **(P5) Restore is a PUBLISH-time (write) behavior, exclusive to T2; the T3 resolver is read-only and never restores.**

**Falsification contract the RED must prove:**
1. Each gate fails-closed independently: a market-prohibited column, a missing required column / wrong dtype, a blank/duplicate ID, below row/position floor, **missing the intended inference season**, an out-of-range value, an all-null critical feature → `ok=False` with the specific failure reason.
2. A clean candidate → `ok=True`; drift deltas are POPULATED but never affect `ok` (movement never blocks).
3. Atomic publish: a valid candidate becomes the runtime + ready-marker; a reader never observes a partial bundle (no ready-marker until complete).
4. Failure path: an invalid candidate does NOT replace a prior valid runtime (byte-identical restore) and yields `status=blocked`; report discloses the failed gate.
5. `decision_supported=false` in the report; banned-token clean.

**Steps:**
- [ ] **Step 1 — Codex RED** `test_feature_validation.py` + `test_feature_publish.py` (contract 1–5; fixtures for each failure class + a clean candidate + a pre-existing valid runtime).
- [ ] **Step 2 — Run RED** → expect failures.
- [ ] **Step 3 — Claude GREEN:** implement `feature_validation.py` (reuse `engine_b_contract` + the existing `assemble_engine_b_dataset` leakage check) + `feature_publish.py` (atomic `os.replace`, ready-marker, backup/restore); wire `run_feature_refresh` to validate→publish with the `blocked` path.
- [ ] **Step 4 — Run GREEN:** RED files pass; full `tests/contract` regression + ruff + banned probe.
- [ ] **Step 5 — Cockpit dual-CLEAR → David-authorized commit → post-commit audit.**

---

## Task 3 — Shared resolver + downstream wiring + freshness labeling + 2025 catch-up

**Deliverable:** One shared resolved-feature-source helper routed through EVERY consumer; provenance stamps the source; the league API + What-Changed model section surface the model `as_of`/vintage; the one-time 2025-complete catch-up first run (David-gated) produces the first non-flat vintage.

**Files:**
- Create: `src/dynasty_genius/features/feature_source.py`
- Modify: `app/services/engine_b_service.py` (`_DATASET_PATH` → resolver), `scripts/build_universe_pvo_batch.py` (BOTH the direct feature-row read AND `score_inference_partition`), `src/dynasty_genius/capture/model_forward_capture_driver.py` (stamp source-kind/hash), `src/dynasty_genius/what_changed/report.py` + the league API route (freshness label)
- Test: `tests/contract/test_feature_source_resolver.py` (+ additions to existing consumer tests)

**Interfaces — Consumes:** T2's runtime + ready-marker + seed. **Produces:**
- `resolve_feature_source(*, seed_path, runtime_dir) -> FeatureSource` with `.path`, `.sha256`, `.source_kind` (`runtime`|`seed`), `.source_as_of`, `.ready: bool`. **Resolution rule:** runtime-if-present-AND-ready (ready-marker present) → runtime; runtime present-but-not-ready/invalid → **fail-closed (raise)**; runtime ABSENT → seed. **(P5) The resolver is strictly READ-ONLY — it NEVER writes/restores (restore is T2's publish-time job); a present-but-invalid/not-ready runtime raises, it does not attempt a restore.**

**Falsification contract the RED must prove:**
1. With a valid ready runtime: ALL consumers (`engine_b_service`, `build_universe_pvo_batch` direct-read, `build_universe_pvo_batch` `score_inference_partition`, `model_forward_capture_driver`) resolve the RUNTIME path/hash — proven per consumer (C2).
2. PVO cannot mix: a single run cannot combine feature-rows from one CSV with predictions/provenance from another (assert the same `FeatureSource` instance/hash flows through both PVO paths).
3. Runtime absent → seed fallback, `source_kind=seed` stamped everywhere.
4. Runtime present-but-not-ready/invalid → fail-closed (no silent seed fallback).
5. Provenance/vintage uses the RESOLVED CSV hash (runtime when present); `feature_source_kind`/`feature_csv_sha256`/`source_as_of` stamped; `generated_at` NOT in `provenance_hash` (C5).
6. The league API + What-Changed model section expose the model `as_of`/vintage; `decision_supported=false` preserved; banned-token clean; OpenAPI drift regenerated if the API DTO changes.

**Steps:**
- [ ] **Step 1 — Codex RED** `test_feature_source_resolver.py` + per-consumer assertions (contract 1–6).
- [ ] **Step 2 — Run RED** → expect failures.
- [ ] **Step 3 — Claude GREEN:** implement `feature_source.py`; route all consumers through it; stamp provenance; add the freshness label; regenerate `frontend/openapi.json` if the API DTO changes (keep drift gate green).
- [ ] **Step 4 — Run GREEN:** RED + full `tests/contract` regression + ruff + banned probe + openapi-drift contract.
- [ ] **Step 5 — Cockpit dual-CLEAR → David-authorized commit → post-commit audit.**
- [ ] **Step 6 — One-time 2025 catch-up (David-gated operational run, separate):** David runs `scripts/run_feature_refresh.py` → validate → publish runtime with the 2025-complete inference partition → first non-flat model vintage captured by the existing daily model-capture brick. (Operational; not a code commit. Seed promotion `runtime → seed` is a later David-gated decision.)

---

## Task 4 — Automated source-hash-gated no-commit scheduler (after gates green)

**Deliverable:** A committed LaunchAgent that runs the runner automatically, source-hash-gated, never auto-commits, atomic + locked, scheduled before the 09:30 PVO window; honest `noop`. launchctl go-live is David-gated/separate.

**Files:**
- Create: `ops/launchd/com.davidleess.dynasty-feature-refresh.plist`
- Test: `tests/contract/test_feature_refresh_ops_scheduler.py` (plistlib-based, portable — no `plutil`)
- Modify: `docs/ARTIFACTS.md`, `docs/development/quick-reference.md`

**Interfaces — Consumes:** T1–T3 runner + gates + resolver (all green).

**Falsification contract the RED must prove:**
1. plist parses via `plistlib`; `Label=com.davidleess.dynasty-feature-refresh`; `ProgramArguments=[<venv py>, scripts/run_feature_refresh.py]`; `WorkingDirectory=ROOT`; `StartCalendarInterval` earlier than 09:30 (e.g. 09:15) with buffer; `RunAtLoad=false`; logs under `app/data/logs/feature_refresh.{out,err}.log`.
2. plist invokes NO training/FC/model-refresh/model-capture entrypoint.
3. The runner under scheduler invocation NEVER stages/commits (no-commit assertion); `commit_required_for_repo_baseline` surfaced for David.
4. Advisory lock + reader-side ready-marker honored so the PVO window sees old-valid-or-new-valid, never partial.
5. Docs record the script/plist/runtime path/cadence/`RunAtLoad=false`/`decision_supported=false`/seed-split/no-commit/David-gated framing; banned-token clean on the new ARTIFACTS section.

**Steps:**
- [ ] **Step 1 — Codex RED** `test_feature_refresh_ops_scheduler.py` (contract 1–5).
- [ ] **Step 2 — Run RED** → expect failures.
- [ ] **Step 3 — Claude GREEN:** write the plist + docs; ensure lock-file + ready-marker integration.
- [ ] **Step 4 — Run GREEN:** RED + full regression + ruff + banned probe.
- [ ] **Step 5 — Cockpit dual-CLEAR → David-authorized commit → post-commit audit.**
- [ ] **Step 6 — launchctl go-live (David-gated, separate):** `cp` plist → `~/Library/LaunchAgents/` → `launchctl load`. Then automation keeps the feature set fresh with zero manual memory dependency; honest `noop` in the offseason.

---

## Self-Review

**Spec coverage:** Q1 (frozen weights / no-fit audit) → T1 step contract 6 + Global Constraints. Q2 (automated no-commit scheduler after gates + as_of labeling) → T4 + T3 freshness label. Q3 (seed-split, fail-closed, provenance stamps which) → T2 publish + T3 resolver. Q4 (integrity gates block / drift report-only) → T2 validation. C1 inference-partition → T1 contract 1–2. C2 shared resolver all consumers → T3 contract 1–2. C3 sequencing (resolver after gates) → task order T1→T1b→T2→T3. **Full scoreable candidate → T1b (frame-injectable engineering extraction, real-value RED), sequenced before T2; T1 produces only the schema-conformant seam (real-run gated). T2 validates ONLY the T1b candidate.** C4 source-hash set → T1 contract 3. C5 provenance/audit boundary → T1 contract 3 + T3 contract 5. C6 ready-marker → T2 + T3 contract 4 + T4 contract 4. C7 resolved-CSV wording → T3 resolution rule. One-time 2025 catch-up → T3 step 6. All covered.

**Placeholder scan:** No TBD/TODO; representative test code is sketched in the falsification contracts (final RED authored by Codex per the cockpit-TDD workflow, which is this project's standing practice).

**Type consistency:** `FeatureSource` (`.path/.sha256/.source_kind/.source_as_of/.ready`) used consistently across T3; `run_feature_refresh` status dict shape consistent across T1/T2/T4; `feature_source_kind` naming consistent with the spec.
