# Roster Capacity Scenario Simulator v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: this project executes via **cockpit-TDD**, not subagent/inline. For each task: **Codex authors the failing tests (RED) → Claude implements (GREEN) → both lanes adversarially review to genuine three-way convergence (no premature "locks") → David authorizes the commit → both lanes post-commit zero-divergence audit.** Steps use checkbox (`- [ ]`) tracking.

**Goal:** A standalone, read-only backend that reflects the descriptive consequences of a David-proposed roster cut hypothesis (or "clear N") during the off-season squeeze — capacity pressure, raw value-at-risk vs a volatile waiver baseline, marginal cost, and positional depth — making no choices and issuing no verdicts.

**Architecture:** A pure core (`simulate_capacity_scenarios`) over injected PVO + Sleeper snapshot + scenarios, reusing `roster_cut_engine` for capacity/order and joining the PVO for raw value; a thin read-only producer writes a gitignored JSON artifact. No optimizer, no API/UI.

**Tech Stack:** Python 3.14, Pydantic (typed `extra=forbid` models), pytest. Always invoke `.venv/bin/python3.14 -m pytest`.

**Spec:** `docs/superpowers/specs/2026-06-28-roster-capacity-scenario-simulator-design.md` (cockpit dual-CLEARed, commit `0a4b7a1`).

## Global Constraints (every task inherits these — copied from the spec)
- **No verdicts / no normative labels.** No `value_loss_band`, `sub_replacement_flag`, `replacement_gap`, severity adjective, or `safe/severe/keep/cut/must/protect/drop`-as-imperative in any emitted **value or caveat**. Neutral descriptive **field names** (`proposed_cuts`, `cut_set`, `clear_n`, `candidate_source`, `marginal_next_candidate_cost`) are allowed (spec §10).
- **No optimizer / no "best set."** The tool reflects David's scenarios; it never selects which players to cut (spec §2, §9).
- **No 10/90 projection envelopes** (only the point estimate `projection_2y` exists; spec §6).
- `decision_supported=False` recursive on every emitted object + the report root.
- **Market-out:** value is Engine-B model xVAR/DVS; no FantasyCalc market value in the value math (spec §2).
- **Read-only:** never writes Sleeper, never auto-commits, writes only the gitignored `app/data/roster_capacity/` artifact; the producer's `subprocess` import is a guarded seam (tests patch `subprocess.run` to forbid git).
- **Reuse, don't rebuild:** call `roster_cut_engine.compute_roster_cut_candidates` for capacity/order/exempt/`xvar_pct`/`dvs`; **join the PVO by `sleeper_player_id`** for raw `valuation.xvar` + top-level `projection_2y`. Do NOT call `trade_lab/reconciler.py`.
- **Robustness boundary (spec §8):** API-misuse → fail loud; data-corruption → fail closed with status; non-finite/missing value → per-field status, excluded-with-count, never imputed/crashed; survivorship-complete (no candidate silently dropped).

## File Structure

| File | Responsibility |
|---|---|
| `src/dynasty_genius/roster_capacity/__init__.py` (new) | Package marker. |
| `src/dynasty_genius/roster_capacity/models.py` (new) | Typed Pydantic models: `ScenarioRequest`, `CapacityCandidate`, `CapacityHealth`, `PoolRange`, `ScenarioResult`, `CapacityAuditResult` (`extra=forbid`; `decision_supported: Literal[False]`). |
| `src/dynasty_genius/roster_capacity/scenario_simulator.py` (new) | Pure `simulate_capacity_scenarios(...)` + helpers (capacity/candidate read, PVO join, unrostered-pool range, value-at-risk + scenario rollup). No I/O. |
| `scripts/run_roster_capacity_audit.py` (new) | Thin read-only producer: argparse, `--preflight`, `resolve_pvo_source`, load snapshot, call core, write gitignored artifact, honest exit codes, never git. |
| `ops/...` | none (no scheduler in v1). |
| `.gitignore` (modify) | add `app/data/roster_capacity/`. |
| `tests/contract/test_roster_capacity_simulator.py`, `tests/contract/test_run_roster_capacity_audit.py` (new) | Per-task tests. |

---

## Task 1: Capacity health + candidates (reuse engine + PVO join-back)

**Files:**
- Create: `src/dynasty_genius/roster_capacity/__init__.py`, `models.py`, `scenario_simulator.py` (the candidate/capacity portion)
- Test: `tests/contract/test_roster_capacity_simulator.py`

**Interfaces:**
- Consumes: `roster_cut_engine.compute_roster_cut_candidates(universe_pvo, sleeper_snapshot, david_roster_id) -> RosterCutResult` (provides capacity slots, `cut_candidates` in `cut_priority` order with `xvar_pct`/`dvs`/taxi-IR status, `cuts_required`); the PVO `players[]` (`identity_ids.sleeper_id` / `sleeper_player_id`, `valuation.xvar`, `projection_2y`, `player.position`).
- Produces: `simulate_capacity_scenarios(universe_pvo, sleeper_snapshot, david_roster_id=1, *, scenarios=None) -> CapacityAuditResult`. T1 fills `capacity_health` + `candidates`.
  - `CapacityAuditResult{status:Literal["ok","blocked"], capacity_health, candidates, scenarios, unrostered_pool_range, excluded_counts:dict[str,int], caveats:list[str], decision_supported:Literal[False]}` — **the fail-closed observable contract (Codex R1 #5):** data-corruption (malformed/missing-required PVO or snapshot) → `status="blocked"` + caveat, no partial credit; the function returns a blocked result (it does NOT raise for data-corruption; it raises `TypeError`/`ValueError` only for API-misuse / wrong-type args). `excluded_counts` carries every excluded-with-count reason.
  - `CapacityHealth{total_players, total_capacity, total_capacity_cuts_required:int, active_slot_overflow:int, by_slot_class:dict, reserve_unrestricted:bool}`.
  - `CapacityCandidate{sleeper_player_id, full_name, position, cut_priority:int, candidate_source:Literal["forced_review","capacity_ordered"], raw_xvar:float|None, dvs:float|None, xvar_pct:float|None, median_projection_2y:float|None, value_field_status:dict[Literal["xvar","dvs","projection_2y","position","model"], str]}` — **a STABLE per-field dict (Codex R1 #2; no `| str` union):** `xvar`/`dvs`/`projection_2y` each `"ok"|"unavailable"`; `position` `"ok"|"unknown_position"`; `model` `"ok"|"pre_model"`.

**Test design (RED must cover):**
- Nominal: roster over capacity → `total_capacity_cuts_required == cuts_required` from the engine AND `active_slot_overflow == max(0, non_reserve_count - active_slots)`; both reported; candidates in engine order.
- **Both overflow concepts distinct:** a roster legal on total capacity but over active slots → `active_slot_overflow>0, total_capacity_cuts_required==0`.
- **PVO join-back:** `raw_xvar`/`median_projection_2y` come from the PVO (NOT the cut engine, which only has `xvar_pct`/`dvs`). A candidate present in the engine but absent from the PVO → `value_field_status` marks the missing fields `unavailable`, excluded-with-count, no crash.
- **candidate_source:** a `cut_priority==0` forced/illegal row → `candidate_source="forced_review"`; normal rows → `capacity_ordered`.
- Falsification: malformed PVO/snapshot → fail closed; wrong-type args → fail loud; non-finite xvar/dvs/projection → per-field `unavailable`; `decision_supported=False` on result + every candidate.

**Implementation guidance:** the simulator calls `compute_roster_cut_candidates`, then builds a PVO index by sleeper id (`_pvo_by_sleeper`), joins each candidate. Compute `non_reserve_count`/`active_slots` from the same league-context the engine uses (read from `RosterCutResult` capacity fields where exposed; otherwise recompute from the snapshot consistently with the engine — confirm at RED). Per-field `value_field_status` (not a single enum) so a missing DVS ≠ an xVAR issue.

**Steps:** `- [ ]` 1.1 Codex RED `tests/contract/test_roster_capacity_simulator.py` (capacity + candidates rows) → FAIL · `- [ ]` 1.2 Claude GREEN models + the candidate/capacity portion of `scenario_simulator.py` → PASS · `- [ ]` 1.3 focused suite + ruff · `- [ ]` 1.4 dual-CLEAR (Codex falsification + reuse-accuracy; Gemini no-verdict) · `- [ ]` 1.5 David-authorized commit `feat(roster-capacity): capacity health + candidates (engine reuse + PVO join)`.

---

## Task 2: Unrostered-pool replacement range (wide, volatile, fail-closed)

**Files:**
- Modify: `src/dynasty_genius/roster_capacity/scenario_simulator.py` (add the pool-range builder), `models.py` (`PoolRange`)
- Test: extend `tests/contract/test_roster_capacity_simulator.py`

**Interfaces:**
- Consumes: the Sleeper snapshot (rostered set = the union `players ∪ starters ∪ taxi ∪ reserve` across all teams per `sleeper_universe.py` — Codex R2 #1, NOT `players` alone; the player universe − rostered → unrostered), the PVO (value per unrostered player), position.
- Produces: `unrostered_pool_range: dict[position, PoolRange]` where `PoolRange{status:Literal["ok","waiver_range_unavailable"], low:float|None, high:float|None, top_k_values:list[float], pool_size:int|None, caveats:list[str]}`. It is `current_unrostered_pool_range` — `low`/`high` = min/max of the position's top-K unrostered values (a wide range, NOT a confidence interval). **`top_k_values` carries the ordered (descending) raw xVAR values themselves (Codex R1 #3)** — T3's depletion math needs the per-member values (top-N / bottom-N-of-top-K sums); `low`/`high` alone are insufficient for `N>1`. **Retain enough members for the largest scenario (Codex R2 #2):** the builder keeps the top-`max(K, max scenario N at that position)` values, so `top_k_values` never under-serves a scenario. If the actual unrostered pool has fewer members than a scenario's `N_p` (`N_p > len(top_k_values)` AND pool exhausted), that is a real deficit (`pool_size` honestly reported), surfaced by T3 as insufficient replacement — distinct from `waiver_range_unavailable` (which is a data/coverage failure, not an exhausted-but-valid pool).

**Test design (RED must cover):**
- Nominal: per position, unrostered = players on no roster; take top-K by value; `PoolRange.low/high` = min/max of that pool, `status="ok"`. Deliberately wide (no tightening).
- **Fail-closed:** snapshot staleness beyond bound / incomplete roster coverage / valuation coverage below floor / `pool_size < min_pool` → `status="waiver_range_unavailable"`, `low/high=None`, caveated. Never fabricate a range.
- Survivorship/typing: non-finite/missing valuations excluded-with-count; empty position pool → unavailable, no crash.

**Implementation guidance:** derive the rostered set to **match the snapshot builder exactly (Codex R1 #1):** `sleeper_universe.py` treats rostered as the union `players ∪ starters ∪ taxi ∪ reserve` across every team (NOT `players` alone) — confirm the exact field set against `sleeper_universe.py` at RED. unrostered = player universe − rostered, grouped by position; value via the PVO index from T1. `K`, `min_pool`, the freshness bound, and coverage floors are GREEN-time constants recorded in the report (spec §12) — propose at RED.

**Steps:** `- [ ]` 2.1 Codex RED (pool-range nominal + all fail-closed rows) → FAIL · `- [ ]` 2.2 Claude GREEN pool-range builder → PASS · `- [ ]` 2.3 focused suite + ruff · `- [ ]` 2.4 dual-CLEAR (Codex fail-closed matrix; Gemini wide-not-tight + volatility caveat honesty) · `- [ ]` 2.5 commit `feat(roster-capacity): unrostered-pool replacement range (fail-closed)`.

---

## Task 3: Value-at-risk + scenario rollup (depletion-aware, no verdict)

**Files:**
- Modify: `scenario_simulator.py` (value-at-risk + scenarios), `models.py` (`ScenarioRequest`, `ScenarioResult`)
- Test: extend `tests/contract/test_roster_capacity_simulator.py`

**Interfaces:**
- Consumes: T1 candidates (raw value + position), T2 `unrostered_pool_range`, `scenarios: list[ScenarioRequest]` (`{"clear_n": int}` or `{"proposed_cuts": [sleeper_id,...]}`; `None` → single default `clear_n = total_capacity_cuts_required`).
- Produces: `scenarios: list[ScenarioResult]` where `ScenarioResult{cut_set:list[str], cumulative_value_at_risk:tuple[float,float], marginal_next_candidate_cost:tuple[float,float]|None, per_position_depth_impact:dict[str,dict[str,int]], caveats:list[str]}`. **`marginal_next_candidate_cost` is a RANGE, xVAR-based (Codex R1 #4 + Gemini R1):** the single-player value-at-risk range of the next `capacity_ordered` candidate not in `cut_set` — same orientation `[next_xvar − pool_max, next_xvar − pool_min]` as every other value-at-risk; a scalar would be ambiguous (xVAR vs PPG) and inconsistent with the range contract. `None` when no candidate remains.

**Test design (RED must cover):**
- **Single-player value-at-risk orientation pinned:** for pool `[pool_min, pool_max]`, value-at-risk = `[player_value − pool_max, player_value − pool_min]`; negatives **unclamped**.
- **Depletion-aware cumulative (exact formula, spec §6):** per position `p`, `cut_sum_p − upper_recovery_p` (upper=Σ top-`N_p` pool) for the low bound and `cut_sum_p − lower_recovery_p` (lower=Σ bottom-`N_p`-of-top-K) for the high bound, summed across positions. Assert it is NOT `N × single-player range`; assert the orientation cannot invert.
- **`N_p` exceeds the valid pool** (`N_p > pool_size`, pool otherwise `ok`) → explicit **deficit** (`N_p − pool_size` spots with no replacement), distinct from `waiver_range_unavailable` (a data/coverage failure); no fabricated replacement (Codex R2 #2).
- **`N_p > K` but pool larger than K** → must NOT mis-read retained-data exhaustion as pool exhaustion: the builder retains top-`max(K, max scenario N_p)` so this resolves correctly; RED asserts the cumulative uses the real N-deep pool, not just K (Codex R2 #2).
- `marginal_next_candidate_cost` = the xVAR-based value-at-risk **range** of the next `capacity_ordered` candidate NOT in `cut_set`, same orientation as §6 (never selects/recommends a player; it is purely "the next in the existing forced order"); `None` when none remain.
- `per_position_depth_impact` descriptive (e.g. `{"QB":{"active_after":3,"bench_after":1}}`).
- David-supplied `proposed_cuts` honored; taxi/IR-exempt or off-roster proposed cut → caveated, not silently dropped. `clear_n` > available → fail-closed/caveated, no crash.
- `decision_supported=False`; banned-language/no-verdict scan (phrase-based per spec §10); no optimizer output.

**Implementation guidance:** pure functions; group the cut-set per position, sort each position's unrostered pool, take N-deep from each end for the recovery bounds. Keep `marginal_next_candidate_cost` strictly the next-in-order value.

**Steps:** `- [ ]` 3.1 Codex RED (orientation + depletion formula + deficit + marginal + proposed_cuts + falsification) → FAIL · `- [ ]` 3.2 Claude GREEN → PASS · `- [ ]` 3.3 focused suite + ruff · `- [ ]` 3.4 dual-CLEAR (Codex metric/orientation/depletion correctness; Gemini verdict-free + nudge check) · `- [ ]` 3.5 commit `feat(roster-capacity): value-at-risk + depletion-aware scenario rollup`.

---

## Task 4: Read-only producer + gitignored artifact

**Files:**
- Create: `scripts/run_roster_capacity_audit.py`
- Modify: `.gitignore` (+`app/data/roster_capacity/`)
- Test: `tests/contract/test_run_roster_capacity_audit.py` (incl. standalone-execution guard)

**Interfaces:**
- Consumes: T1–T3 core; `resolve_pvo_source` (seed/runtime, fail-closed); the Sleeper snapshot loader.
- Produces: a gitignored `app/data/roster_capacity/<report>_latest.json` (the `CapacityAuditResult`, `decision_supported=false` root). **Explicit exit/report contract (Codex R1 #6 + R2 #3):** the PRODUCER emits its own `ProducerReport{producer_status:Literal["ok","blocked","preflight_ready"], scorecard:CapacityAuditResult|None, decision_supported:Literal[False]}` — **distinct from the core `CapacityAuditResult.status` (`ok|blocked`)** so preflight (which never produces a CapacityAuditResult) is representable. `main(argv) -> int` returns `0` for `producer_status` `ok`/`preflight_ready`, `1` for `blocked`/corrupt-input. `--preflight` prints a `preflight_ready` ProducerReport (`scorecard=None`) and returns `0` WITHOUT scoring or writing. A `blocked` run writes **no** artifact (does not overwrite a prior good `_latest`) and prints the blocked ProducerReport to stdout. An `ok` run writes the `CapacityAuditResult` artifact.

**Test design (RED must cover):**
- `--preflight` reports readiness, returns 0, writes nothing.
- Full path (injected fixtures): writes ONLY the gitignored artifact; NEVER calls git (patch `subprocess.run` to forbid, mirroring `promote_pvo_seed.py`); report `decision_supported=false`; no banned imperative/verdict phrases in values.
- Fail-closed: corrupt/missing PVO or snapshot → honest non-zero/abort status, no partial artifact.
- Standalone-execution regression: invoking the script as a subprocess (launchd-style) → no `ModuleNotFoundError` (ROOT `sys.path` bootstrap).
- `.gitignore` includes `app/data/roster_capacity/`.

**Implementation guidance:** mirror `scripts/run_model_forward_capture.py` (argparse, ROOT `sys.path` bootstrap, `--preflight`, `main(argv)->int`, exit `0` for `ok`/`preflight_ready` else `1`, `subprocess` guarded seam). No API route, no plist in v1.

**Steps:** `- [ ]` 4.1 Codex RED → FAIL · `- [ ]` 4.2 Claude GREEN producer + gitignore → PASS · `- [ ]` 4.3 **closeout:** `scripts/verify_sprint_closeout.py --base origin/main` → ENFORCE PASS (full pytest + ruff src app + standalone-scripts) · `- [ ]` 4.4 dual-CLEAR · `- [ ]` 4.5 commit `feat(roster-capacity): read-only producer + gitignored artifact`.

---

## Post-build (separate, David-gated)
- Push branch → PR → CI green → David merge (preserve-commits) → close the loop.
- Later increments (own specs): read-only API + UI surface; Trade Lab integration; v2 Cut-N optimizer (only behind a governed "best" objective that survives the no-verdict line).

## Self-Review (against spec)
- **Coverage:** §2/§5 honesty + capacity + candidates → T1; §7 pool range → T2; §6 value-at-risk + scenarios → T3; §4 producer + §3 artifact → T4. Robustness §8 + falsification §10 embedded per task. ✓
- **Placeholders:** the only deferred items are the spec-§12 GREEN-time numeric constants (`K`, `min_pool`, freshness bound, coverage floors) — each explicitly assigned to a named RED step (T2). ✓
- **Type consistency:** `CapacityAuditResult` / `CapacityCandidate` / `PoolRange` / `ScenarioResult` / `ScenarioRequest` field names + types used consistently T1→T4; `marginal_next_candidate_cost` (never `_cut_cost`; a RANGE not scalar); `active_slot_overflow` clamped; `total_capacity_cuts_required` vs `active_slot_overflow` distinct; `value_field_status` is a stable per-field dict (no `| str`); `PoolRange.top_k_values` feeds T3. ✓

## Change log
- **plan v2 (2026-06-28):** integrated cockpit plan-review round 1 — Codex R1 (6): T2 rostered-set =
  `players ∪ starters ∪ taxi ∪ reserve` per `sleeper_universe.py` (not `players` alone); `value_field_status`
  → stable per-field dict (no `| str`); `PoolRange.top_k_values` added so T3 depletion math has per-member
  values for arbitrary `N`; `marginal_next_candidate_cost` → xVAR-based **range** (oriented); `CapacityAuditResult`
  gains root `status`/`caveats`/`excluded_counts` + the fail-closed-returns-blocked vs raise-on-API-misuse
  contract; T4 explicit `status` ∈ {ok,blocked,preflight_ready} + exit codes + no-artifact-on-blocked.
  Gemini R1: folded the `marginal_next_candidate_cost` xVAR/PPG ambiguity into Codex #4 (range, xVAR-based);
  otherwise no-verdict line + Global Constraints confirmed carried per task.
- **plan v3 (2026-06-28):** integrated cockpit plan-review round 2 — Codex R2 (3): T2 *interface* line's stale
  `rosters[].players` aligned to `players ∪ starters ∪ taxi ∪ reserve` (the guidance was already fixed —
  parallel-location sweep miss); `PoolRange.top_k_values` retains top-`max(K, max scenario N_p)` so it never
  under-serves a scenario, with `N_p > pool_size` deficit DISTINCT from `waiver_range_unavailable` + a
  `N_p > K` RED row; `ProducerReport.status` (ok/blocked/preflight_ready) separated from the core
  `CapacityAuditResult.status` (ok/blocked) so preflight is representable. Gemini R2: plan v2 solid, no new
  product/honesty defect, lane boundaries intact.
