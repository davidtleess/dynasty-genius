# Realized-Outcome Loop v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. **In this project, execution is cockpit-TDD:** for each task, Codex authors the failing tests (RED), Claude implements (GREEN), both lanes review to dual-CLEAR, David authorizes the commit, then both lanes post-commit zero-divergence audit. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a backend forward-accrual loop that scores the frozen model's predictions against actual NFL fantasy production over time, leading with within-position rank accuracy + Model Input Fidelity.

**Architecture:** Three physically separate stores (a companion prediction-snapshot table on the existing model PIT capture DB; a new append-only outcome store; a derived scorecard artifact) joined through a point-in-time identity bridge, scored by a pure scorer, emitted by a read-only CLI producer on a weekly in-season cadence. We score the frozen model artifact (the anchor), never the daily estimate overlay.

**Tech Stack:** Python 3.14, SQLite (mirroring the existing capture stores), nflreadpy (outcomes), existing `src/dynasty_genius/eval/backtest_metrics.py` (rank metrics), pytest.

**Spec:** `docs/superpowers/specs/2026-06-27-realized-outcome-loop-design.md` (cockpit dual-CLEARed, commit `d1191c7`).

## Global Constraints

- Python 3.14; always invoke `.venv/bin/python3.14 -m pytest` (NOT `.venv/bin/python`, NOT poetry).
- `decision_supported=False` on every emitted row and the scorecard root (recursive).
- Score the **frozen model artifact** (`projection_2y` from the captured PVO row), never the daily estimate overlay.
- Market data is overlay-only — **excluded from all scoring inputs** in v1 (model-vs-market scorekeeping is a deferred increment).
- Banned-language discipline: descriptive identifiers only (`realized_vs_expected_delta`, `route_participation_delta`); never buy/sell/target/tier/verdict in code, fields, logs, or reports.
- The existing `model_forward_capture` core store immutability/vintage contract (`_CONTENT_COLUMNS`) MUST remain byte-unchanged — additions go in a **companion table**, never new core columns.
- Survivorship-complete: never silently drop captured players from a cohort.
- Fail-closed everywhere (robustness boundary, spec §8): API-misuse → fail loud; data-corruption → fail closed with explicit report; non-finite/range violations → reject with status, never silently score.
- Frontend HOLD intact — v1 adds NO API route and NO UI.
- Writes go only to gitignored data dirs + the new stores; producers NEVER auto-commit.
- Each task: Codex RED → Claude GREEN → dual-CLEAR → David-authorized commit → both-lane post-commit zero-divergence.

## File Structure

| File | Responsibility |
|---|---|
| `src/dynasty_genius/capture/prediction_snapshot_store.py` (new) | Companion table: store/read `projection_2y` + utilization snapshot keyed to the model PIT PK; preserves core immutability. |
| `src/dynasty_genius/capture/model_forward_capture_store.py` (modify) | Expose a shared-connection write path so the core append + companion append commit in one transaction; core PK/`_DATA_COLUMNS`/`_CONTENT_COLUMNS` unchanged. |
| `src/dynasty_genius/capture/model_forward_capture_driver.py` (modify) | Hook the companion-row write into the existing capture, in one transaction with the core row. |
| `src/dynasty_genius/identity/outcome_identity_bridge.py` (new) | Point-in-time sleeper↔gsis↔dg↔pfr resolution; fail-closed. |
| `src/dynasty_genius/capture/outcome_forward_capture_store.py` (new) | Append-only realized-outcome store + week-finalized gate. |
| `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py` (new) | Pure scorer: join → per-player tracking rows + cohort metrics. |
| `scripts/run_realized_outcome_scoring.py` (new) | Read-only CLI producer; weekly cadence; `--preflight`; honest exit codes; no auto-commit. |
| `ops/launchd/com.davidleess.dynasty-realized-outcome-scoring.plist` (new) | Optional weekly LaunchAgent (David-gated load). |
| `tests/contract/...`, `tests/unit/...` | Per-task tests (see each task). |

---

## Task 1: Companion prediction-snapshot store + capture-driver hook

**Files:**
- Create: `src/dynasty_genius/capture/prediction_snapshot_store.py`
- Modify: `src/dynasty_genius/capture/model_forward_capture_store.py` (Codex D1 — expose a shared-connection write path so the core append and the companion append commit in ONE transaction; do NOT change `_DATA_COLUMNS`/`_CONTENT_COLUMNS`/PK of the core tables)
- Modify: `src/dynasty_genius/capture/model_forward_capture_driver.py` (companion write hook at the entry-construction point, lines ~386-395, in the same transaction as the core capture row)
- Test: `tests/contract/test_prediction_snapshot_store.py`, extend `tests/contract/test_model_forward_capture_driver.py`

**Interfaces:**
- Consumes: the existing model PIT capture row PK `(capture_date, source, semantic_output_hash, provenance_hash, player_key)`; the driver's `feature_source` (where the utilization snapshot is resolved); the PVO row field `projection_2y`.
- Produces:
  - `PredictionSnapshotStore(db_path)` with `append_snapshot(row, *, conn=None) -> None` (**immutable insert-or-ignore + conflict-check vs existing content, mirroring `ModelForwardCaptureStore.append_entries` — NOT an upsert/mutation**; accepts an optional shared `sqlite3.Connection` so the driver can write core+companion in one transaction) and `read_snapshot(pk) -> PredictionSnapshotRow | None`.
  - `PredictionSnapshotRow` fields: the 5 PK columns; `projection_2y: float | None`; `utilization: dict[str, UtilField]` where `UtilField = {value: float|None, role: "model_input"|"diagnostic_only"}` over canonical columns `snap_share, route_participation, target_share_nfl, air_yards_share, weighted_opportunity, yprr, tprr`; `prediction_ppg_status: "captured"|"missing_legacy_capture"|"capture_incomplete"`; `util_snapshot_status: str`; `schema_version: int`; `source_hash: str`.

**Test design (RED must cover):**
- Nominal: a captured prediction writes a companion row readable by PK with `projection_2y` and the canonical util fields each carrying a `role`.
- **Immutability proof:** importing/initializing the companion store and writing companion rows leaves the core `model_forward_capture` `_CONTENT_COLUMNS`/`_DATA_COLUMNS` signature and core-row bytes unchanged (assert against the core store's signature + a captured core row hash before/after).
- **Atomicity:** if the companion write fails, the core row write is rolled back (single transaction) — OR, if separate, the row is marked `capture_incomplete` and a later read reports it fail-closed. Pick the transactional path; test the rollback.
- **Rollout marker when the companion row is ABSENT (Codex D3):** an absent companion row has no row-level `schema_version` to read, so legacy-vs-failed-write must be resolved at the **store level** — the companion store records a one-time `rollout_capture_date` (meta marker) when first created. A core row with **no** companion row whose `capture_date` is **before** `rollout_capture_date` → `missing_legacy_capture`; **on/after** it → `capture_incomplete` (fail-closed, excluded with a count). Row-level `schema_version` still distinguishes companion-row format versions when a row exists.
- Falsification rows: missing `projection_2y` (null + status), util column absent from feature source (null + status, not assumed), wrong-type value (fail loud), non-finite `projection_2y` (reject), duplicate PK (idempotent no-dup).

**Implementation guidance:** Mirror the append-only/immutable SQLite pattern of `model_forward_capture_store.py` (same PK columns, table-create-if-not-exists, conflict handling). Do NOT add columns to the core table. The driver hook: at the point where the core capture row is built/written, also build the companion row from the same PVO row and write both in one SQLite transaction. Limit util fields to those actually present in the resolved feature source; tag each with `role` per the Engine B contract (model_input vs diagnostic_only by position).

**Steps:**
- [ ] **1.1 (Codex RED)** Author `tests/contract/test_prediction_snapshot_store.py` covering the behaviors above; run to confirm FAIL.
- [ ] **1.2 (Claude GREEN)** Implement `prediction_snapshot_store.py` + the driver hook (single transaction) until tests pass.
- [ ] **1.3** Run focused suite: `.venv/bin/python3.14 -m pytest tests/contract/test_prediction_snapshot_store.py tests/contract/test_model_forward_capture_driver.py -v` — expect PASS; run the core-store immutability test to prove zero change.
- [ ] **1.4 (dual-CLEAR)** Codex technical (falsification matrix + immutability) + Gemini governance.
- [ ] **1.5 (commit)** On David's authorization: `git add` the new store, driver, tests → commit `feat(outcome-loop): companion prediction-snapshot store + driver hook`.

---

## Task 2: Point-in-time identity bridge

**Files:**
- Create: `src/dynasty_genius/identity/outcome_identity_bridge.py`
- Test: `tests/contract/test_outcome_identity_bridge.py`

**Interfaces:**
- Consumes: `PlayerIdentity` records / `generate_dg_id(...)` from `src/dynasty_genius/identity`; the sleeper/gsis/dg/pfr ids present on captured rows and outcome rows.
- Produces: `resolve(sleeper_id: str|None, capture_date: str) -> BridgeResolution` where `BridgeResolution = {gsis_id: str|None, dg_player_id: str|None, pfr_id: str|None, resolution_status: "resolved"|"unresolved"|"conflict"}`. Bridge rows carry `season`, `valid_from`/`valid_to` (or `snapshot_date`), `source_hash`.

**Test design (RED must cover):**
- Nominal: a sleeper_id resolves to the gsis_id valid at `capture_date`.
- **Point-in-time:** when a mapping changed between capture_date and today, `resolve` returns the mapping valid AT capture_date, not today's.
- **Fail-closed:** unresolved id → `resolution_status="unresolved"` (caller excludes with a count); many-to-one (one sleeper → two gsis in the same window) → `resolution_status="conflict"` (quarantine/abort), never silently pick one.
- Falsification: null sleeper_id, unknown id, duplicate bridge rows, overlapping validity windows (must be detected as conflict).

**Implementation guidance:** A standalone resolver over a bridge table/structure; never join ad-hoc in the scorer. Reuse `PlayerIdentity` shape; do not invent new identity logic (north-star §Identity).

**Steps:**
- [ ] **2.1 (Codex RED)** `tests/contract/test_outcome_identity_bridge.py`; run → FAIL.
- [ ] **2.2 (Claude GREEN)** Implement `outcome_identity_bridge.py`; run → PASS.
- [ ] **2.3** Focused suite green.
- [ ] **2.4 (dual-CLEAR)** Codex (point-in-time + conflict fail-closed) + Gemini.
- [ ] **2.5 (commit)** `feat(outcome-loop): point-in-time identity bridge`.

---

## Task 3: Outcome ingestion store + week-finalized gate

**Files:**
- Create: `src/dynasty_genius/capture/outcome_forward_capture_store.py`
- Test: `tests/contract/test_outcome_forward_capture_store.py`

**Interfaces:**
- Consumes: nflreadpy player_stats (load pattern mirrored from `scripts/assemble_engine_b_dataset.py:145-194`), keyed by gsis `player_id`; the canonical fantasy/utilization columns incl. `fantasy_points_ppr`.
- Produces:
  - `OutcomeForwardCaptureStore(db_path)` with `ingest_week(season:int, week:int, *, stat_rows, util_rows, schedule) -> IngestResult` and `read_outcomes(season, gsis_id) -> OutcomeRow`.
  - `week_status(season:int, week:int, *, schedule) -> "finalized"|"not_finalized"` (Codex D4 — finality is computed from an **injected schedule/finality input**, not inferred from stat rows; player stat rows alone cannot reveal a missing/postponed game).
  - `OutcomeRow`: `gsis_id, season, games_played, ppg_to_date, ppg_rolling_{3,5,8}`, **explicit realized-utilization fields** `snap_share_realized`, `route_participation_realized`, `target_share_nfl_realized` each with a per-field `status: "ok"|"unavailable"` (Codex D5 — sourced from separate nflreadpy loaders; `unavailable` when a loader has no data, never imputed), and `player_status: "active"|"bye"|"injured"|"not_yet_played"|"departed"`.

**Test design (RED must cover):**
- **Week-finalized gate (via injected schedule):** RED covers all four — fully finalized week (ingest proceeds), a missing game, a postponed game, and no-games-scheduled. Any non-final game → `week_status="not_finalized"` and `ingest_week` no-ops (no partial-week ingest). Finality is read from the injected `schedule`, never inferred from stat rows.
- **Survivorship-complete:** retired/cut/injured players present in a prior week are retained with explicit `player_status`, never dropped.
- Append-only/idempotent: re-ingesting the same finalized week produces no duplicate rows.
- Rolling windows computed correctly (3/5/8) on finalized weeks.
- Falsification: malformed row (fail closed), non-finite points (reject), 0-game player (retained, status), empty week.

**Implementation guidance:** Mirror the append-only immutable-store convention of `model_forward_capture_store.py` / `fc_forward_capture_store.py` (PK + `_CONTENT_COLUMNS`, `CREATE TABLE IF NOT EXISTS`, `INSERT OR IGNORE`, conflict check vs immutable rows). Realized fantasy production comes from `nfl.load_player_stats(seasons)` (exact columns: `fantasy_points_ppr`, `targets`, `receptions`, `receiving_air_yards`, `week` for games-played via `nunique`, `player_id`=gsis, `season`, `position`) — pattern at `scripts/assemble_engine_b_dataset.py:145-172`.

**Realized-utilization sourcing caveat (important):** `load_player_stats` does **NOT** contain `snap_share` or `route_participation`. Realized snap share comes from nflreadpy snap-count data; route participation from participation/PBP data; `target_share_nfl` is derivable from team target totals. Confirm the exact loaders at RED time. **Fail-closed:** if a realized-utilization field cannot be sourced for a week, the corresponding Model Input Fidelity field is `status="unavailable"` (Task 4) — never assumed/imputed. The week-finalized check (spec §4.3) gates all scoring; exact nflreadpy "all games final" call confirmed at RED time.

**Steps:**
- [ ] **3.1 (Codex RED)** `tests/contract/test_outcome_forward_capture_store.py`; run → FAIL.
- [ ] **3.2 (Claude GREEN)** Implement store + week gate; run → PASS.
- [ ] **3.3** Focused suite green.
- [ ] **3.4 (dual-CLEAR)** Codex (week-gate + survivorship + idempotency) + Gemini.
- [ ] **3.5 (commit)** `feat(outcome-loop): outcome ingestion store + week-finalized gate`.

---

## Task 4: Pure realized-outcome scorer

**Files:**
- Create: `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py`
- Test: `tests/unit/test_realized_outcome_scorer.py`

**Interfaces:**
- Consumes: companion snapshots (Task 1), the identity bridge (Task 2), outcome rows (Task 3), and `backtest_metrics` rank functions.
- Produces:
  - `score(predictions, outcomes, bridge, as_of_week) -> Scorecard`.
  - Per-player `TrackingRow`: `predicted_ppg, realized_ppg_to_date, realized_vs_expected_delta, maturity_pct, settlement_status: "partial"|"settled", model_input_fidelity: dict[field, {delta|status}], decision_supported=False`.
  - Cohort `CohortMetric` per (position): `spearman{value,bca_ci}, kendall{value,bca_ci}, ndcg{value} (point-estimate only), precision_at_k{value,k,truth_def}, status: "ok"|"power_floor_not_met"`.

**Test design (RED must cover):**
- **CI coverage is metric-specific (spec §5.1):** Spearman/Kendall return BCa CIs (via `compute_rank_correlation`); NDCG returns a point estimate only (no CI); Precision@k uses an explicit top-k truth set and reports point/counts. Assert NO BCa CI is attached to NDCG.
- **Status gating, no maturity weighting:** a cohort below floors (`< 4 eligible games/player` or `< min cohort size`) → `status="power_floor_not_met"`, metric descriptive-only, never a settled-looking number. No maturity-weighted rank metric exists.
- **Model Input Fidelity early gate:** no 4-week delta before ≥4 eligible games → field `status="partial_window"`, no value.
- **Survivorship floor:** a 0-game settled player gets the position 5th-percentile penalty (Gate-4 parity), included in the cohort (assert the cohort count includes them and the rank metric reflects the penalty).
- **Partial vs settled:** an in-season player is `settlement_status="partial"` with `maturity_pct < 100`; never labeled settled before the 2-year horizon completes.
- `decision_supported=False` on every row and the scorecard root.
- Falsification: unresolved identity excluded with count; missing outcome → partial/empty handled; non-finite → rejected; empty cohort → no crash.

**Implementation guidance:** Pure functions (no I/O) — all inputs injected, mirroring `backtest_harness`/`gate4` purity. Exact existing signatures (confirmed):
- `compute_rank_correlation(predicted, realized, n_bootstrap=1000, rng_seed=42) -> (kendall_tau, kendall_bca_ci95, spearman_rho, spearman_bca_ci95)` — **returns all-NaN when n < 10** (a built-in power floor; the per-position cohort minimum must therefore be **≥ 10**, and NaN → `status="power_floor_not_met"`, never surfaced as a number).
- `compute_ndcg(predicted_ranks, realized_ppg, k) -> float` — point estimate only, attach NO CI.
- `compute_precision_at_k(model_top_k, market_top_k, realized_top_k, k) -> TopKResult` is **model-vs-market** (its `diff_wilson_ci95` requires `market_top_k`). v1 excludes market, so **write a thin model-only wrapper (Codex D6)** `compute_model_precision_at_k(model_top_k, realized_top_k, k) -> {model_hit_rate, hits, k}` rather than passing a dummy `market_top_k`. v1 tests **explicitly ban** calling or reporting `diff_wilson_ci95`. Define the realized top-k truth set explicitly (realized top-k within position).
- `compute_ndcg_diff_bootstrap(...)` is model-vs-market — **out of v1 scope** (do not call).

Power-floor numeric minimums per position (≥10 floor from the rank fn, plus any higher per-position minimum) calibrated against real cohort counts at GREEN time and recorded in the report.

**Steps:**
- [ ] **4.1 (Codex RED)** `tests/unit/test_realized_outcome_scorer.py` covering the matrix above; run → FAIL.
- [ ] **4.2 (Claude GREEN)** Implement the pure scorer; run → PASS.
- [ ] **4.3** Focused suite green; verify CI-coverage and status-gating assertions explicitly.
- [ ] **4.4 (dual-CLEAR)** Codex (metric-CI correctness, gating, survivorship, falsification) + Gemini (overclaim / MIF-as-input-audit framing).
- [ ] **4.5 (commit)** `feat(outcome-loop): pure realized-outcome scorer`.

---

## Task 5: Scorecard report producer + CLI (+ optional LaunchAgent)

**Files:**
- Create: `scripts/run_realized_outcome_scoring.py`
- Create: `ops/launchd/com.davidleess.dynasty-realized-outcome-scoring.plist`
- Test: `tests/contract/test_run_realized_outcome_scoring.py` (incl. the standalone-execution regression guard)

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: a gitignored scorecard artifact JSON (per-player tracking + cohort aggregates, `decision_supported=false` root); honest exit codes.

**Test design (RED must cover):**
- `--preflight` reports readiness without writing/scoring.
- **Off-season no-op:** when no finalized in-season week exists → honest no-op exit (no artifact mutation), exit code per convention.
- **Week-not-finalized no-op:** mirrors Task 3 gate.
- Writes ONLY the gitignored artifact; NEVER calls git (patch `subprocess.run` to forbid, mirroring `promote_pvo_seed.py` guard).
- **Standalone-execution regression:** invoking the script as a subprocess (launchd-style, mirroring the existing standalone guard test) does not `ModuleNotFoundError`.
- Report carries `decision_supported=false`; no banned-language tokens.

**Implementation guidance:** Mirror `scripts/run_model_forward_capture.py` / `run_fc_forward_capture.py` structure (argparse, `--preflight`, exit codes, report JSON, no-auto-commit, sys.path bootstrap). The plist mirrors `com.davidleess.dynasty-model-pvo-refresh.plist` with `RunAtLoad=false`, weekly cadence (exact day/time confirmed at GREEN time, in-season after stats finalize). Add `app/data/realized_outcome/` to `.gitignore`.

**Steps:**
- [ ] **5.1 (Codex RED)** `tests/contract/test_run_realized_outcome_scoring.py` (incl. standalone guard + off-season no-op); run → FAIL.
- [ ] **5.2 (Claude GREEN)** Implement the CLI producer + plist + gitignore; run → PASS.
- [ ] **5.3** Focused suite green.
- [ ] **5.4 (closeout)** `scripts/verify_sprint_closeout.py --base origin/main` → ENFORCE PASS (full pytest + `ruff check src app` + standalone-scripts). Dual-CLEAR.
- [ ] **5.5 (commit)** `feat(outcome-loop): scorecard CLI producer + weekly LaunchAgent`.

---

## Post-build (separate, David-gated)
- Push branch → PR → CI green → David merge (preserve-commits).
- Operational go-live: David-gated `launchctl load` of the plist; first live run is once the 2026 season produces a finalized week (off-season = no-op until then).
- Later increments (own specs): read-only API + UI surface; off-season backtest-seeded historical baseline; league-audit angle; model-vs-market scorekeeping.

## Self-Review (against spec)
- **Coverage:** §4.1→T1, §4.2→T2, §4.3+outcome store→T3, §5.1/§5.2/§5.3+§6→T4, §4.5+§7 cadence→T5. Robustness boundary §8 + falsification §10 → embedded in each task's RED. ✓
- **Placeholders:** the only deferred items are the spec-§12 genuine operational values (exact cron time, exact nflreadpy week-final call, numeric per-position cohort minimums) — each is explicitly assigned to a named GREEN-time step in T3/T4/T5, not left vague. ✓
- **Type consistency:** `projection_2y`, `prediction_ppg_status`, `BridgeResolution.resolution_status`, `CohortMetric.status`, `settlement_status`, `model_input_fidelity` field statuses used consistently across tasks. ✓
