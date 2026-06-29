---
document: Roster Capacity Scenario Simulator v1 — Design Spec
date: 2026-06-28
status: DRAFT (for cockpit adversarial review; NOT yet dual-CLEARed; NOT David-approved-to-commit)
authors: Claude (impl), cockpit-scoped (Codex + Gemini, 4-round scope debate → genuine convergence on Option A)
---

# Roster Capacity Scenario Simulator v1

## 1. Mission / decision it improves

A **descriptive, read-only** backend that helps David navigate the **off-season roster squeeze** (August
cutdowns, taxi locks, bench congestion in his 25-man Superflex PPR league). David drives a scenario —
"clear N spots" or a **proposed cut hypothesis** ("what if I cut my backup QB to stash this rookie WR?")
— and the tool **reflects the consequences back** descriptively: how much value is at risk, the marginal
cost of the next cut, and the positional-depth impact, against a wide/volatile estimate of what the
waiver wire could replace.

It is a **simulator, not a recommender.** David proposes; the tool reflects. It makes **no choices** and
issues **no verdicts.**

## 2. The honesty line (the core constraint — settled in the scope debate)

This is a capacity **audit**, not a cut advisor. The cockpit debate established the bright line:

- **Allowed (descriptive):** capacity pressure; **raw** value per candidate (raw xVAR, raw `dvs`, raw
  median `projection_2y`) **read against the §7 dynamic unrostered-pool range** (no static replacement
  constant, no binary flag — Gemini R1); cumulative value-at-risk + marginal next-candidate cost +
  per-position depth impact for a scenario; the **wide, explicitly-volatile** unrostered-pool range. The
  existing `roster_cut_engine` `cut_priority` ordering is reused as-is — honest because it is
  **capacity-ordering within a forced constraint** ("if you must trim, this is the order"), not a value
  verdict.
- **Banned (normative / verdict):** value-loss severity bands (`none…severe`), "ceiling-protection"
  framing, any `safe`/`severe`/`must_keep`/`drop_candidate`/keep/cut label, and any **optimizer** that
  selects "the best cut-set" — selecting an optimal combination is an implicit cut-recommendation and
  assumes a precision our delta math does not have. All deferred (see §9).
- `decision_supported=False` is set recursively on every emitted object and the report root.
- **Read-only**: never writes to Sleeper, never auto-commits, writes only a gitignored artifact.
- **Market-out**: player value is the Engine-B model xVAR/DVS. FantasyCalc market value is overlay-only
  and excluded from v1 (no market in the value-at-risk math); divergence stays out of scope.

## 3. Scope

**In v1:**
1. **Capacity health** for David's current roster (over/under, by slot class).
2. **Per-candidate raw value-at-risk** (no normative bands, no 10/90 envelopes — see §6).
3. **Scenario rollup** for a David-supplied cut-set OR a "clear N" default: cumulative value-at-risk
   surrendered, marginal next-candidate cost, per-position depth impact.
4. **Wide, volatile `current_unrostered_pool_range`** per position, fail-closed.
5. A **pure evaluator** + a thin **read-only report producer** writing a gitignored JSON artifact.

**Out (deferred / owned elsewhere):**
- Cut-N combinatorial **optimizer** ("best set to cut") → v2, gated on a governed definition of "best"
  that does not violate the no-verdict boundary.
- **10/90 projection envelopes** → blocked: the stores hold only a single expected-value `projection_2y`
  per player; no model-derived distribution exists, so any band would fabricate precision.
- **Prospective *trade* what-ifs** → already owned by Trade Lab (`trade_lab/reconciler.py`); do NOT call
  it here. This tool is standing-roster, not trade-triggered.
- **API + UI** → later (the producer ships a backend artifact first).
- Any Sleeper write / roster mutation.

## 4. Architecture

A new bounded package `src/dynasty_genius/roster_capacity/` with a **pure core** + a thin producer:

```
src/dynasty_genius/roster_capacity/
  scenario_simulator.py   # pure: simulate_capacity_scenarios(...) -> CapacityAuditResult
  models.py               # typed result/scenario/candidate/pool-range models (Pydantic, extra=forbid)
scripts/run_roster_capacity_audit.py   # thin read-only producer (argparse, --preflight, no git, gitignored artifact)
```

- The **pure core** takes all inputs injected (PVO dict, Sleeper snapshot dict, optional scenarios); no
  I/O, no wall-clock, mirroring `roster_cut_engine` / the scorer purity convention. This makes it fully
  unit-testable with fixtures.
- The **producer** resolves the live PVO via `resolve_pvo_source` (seed-vs-runtime, fail-closed), loads
  the Sleeper snapshot, calls the core, and writes a gitignored report (`app/data/roster_capacity/`,
  added to `.gitignore`), following the existing `write_{report}_artifacts` JSON+`-latest` convention.

## 5. Interfaces

```python
def simulate_capacity_scenarios(
    universe_pvo: dict,
    sleeper_snapshot: dict,
    david_roster_id: int = 1,
    *,
    scenarios: list[ScenarioRequest] | None = None,   # None -> single default "clear cuts_required"
) -> CapacityAuditResult
```

- `ScenarioRequest`: either `{"clear_n": int}` (cut N from the capacity-driven order) OR
  `{"proposed_cuts": [sleeper_player_id, ...]}` (David's own hypothesis). Both are honored descriptively;
  a proposed cut that is taxi/IR-exempt or not on the roster is flagged in caveats, not silently dropped.

**Reuse (do NOT rebuild) + the join-back (Codex R1):** the core calls
`roster_cut_engine.compute_roster_cut_candidates(universe_pvo, sleeper_snapshot, david_roster_id)` ONLY for
capacity math (active+reserve+taxi, IR-protected), candidate ordering/`cut_priority`, candidate
source/status, and exempt status. **`RosterCutCandidate` exposes `xvar_pct` and `dvs`, NOT raw `xvar` or
`projection_2y`** (`roster_cut_engine.py:69`), so the simulator **joins each candidate back to
`universe_pvo` by `sleeper_player_id`** for raw `valuation.xvar` and top-level `projection_2y`. The
simulator enriches; it introduces no new cut-priority model.

### Output (`CapacityAuditResult`, all `decision_supported=False`)
- `capacity_health`: `total_players`, `total_capacity`, `total_capacity_cuts_required` (= engine
  `cuts_required = max(0, total_players - total_capacity)`) AND `active_slot_overflow`
  (= `max(0, non_reserve_count - active_slots)` — **clamped to zero** since it is named "overflow"; a
  roster under its active slots reports 0, never a negative; Codex R2) — **both pressure concepts surfaced
  explicitly** (Codex R1: they differ; do not collapse into one ambiguous `over_by`), breakdown by slot
  class (active / reserve / taxi /
  IR), `reserve_unrestricted`.
- `candidates: list[CapacityCandidate]` — every cut-eligible candidate the engine returns, in engine
  order, each with `candidate_source` (`forced_review` for priority-0 illegal/IR-forced rows |
  `capacity_ordered`) (Codex R1): `sleeper_player_id`, `full_name`, `position`, `cut_priority`,
  `raw_xvar` (joined from PVO), `dvs`, `xvar_pct`, `median_projection_2y` (joined from PVO),
  `value_field_status` — **per-field** (`xvar`/`dvs`/`projection_2y` each `ok | unavailable`, plus
  `unknown_position`, `pre_model`) so a missing DVS is not mislabeled an xVAR issue (Codex R1).
  **No `replacement_gap`, no `sub_replacement_flag`, no band, no label** — the static
  `ENGINE_B_REPLACEMENT_DVS` baseline is REMOVED (Gemini R1: it contradicts the §7 *dynamic* pool and the
  binary flag is an editorial cut-nudge). Replacement reality comes ONLY from the §7 dynamic pool range,
  which David reads against the raw `dvs`/`projection_2y` himself.
- `scenarios: list[ScenarioResult]` — for each requested scenario: the resolved `cut_set`,
  `cumulative_value_at_risk` (a **range**, computed depletion-aware per §6 — NOT N× a single-player range),
  `marginal_next_candidate_cost` (Gemini R1 — renamed off "cut"; strictly the value of the next candidate
  in capacity-priority order NOT already in the simulated set; never selects/recommends a player),
  `per_position_depth_impact` (e.g. `{"QB": {"active_after": 3, "bench_after": 1}}`), `caveats`.
- `unrostered_pool_range: dict[position, PoolRange]` — see §7.
- `caveats: list[str]`, `decision_supported: Literal[False]`.

## 6. Value-at-risk metric (raw, descriptive)

- Primary value is **raw xVAR** (cross-position-comparable, already on the PVO); raw `median_projection_2y`
  (PPG point estimate) is surfaced alongside. No static replacement constant (removed per §5/Gemini R1).
- **Single-player value-at-risk = raw value − the position's unrostered-pool range**, with the orientation
  **pinned** (Codex R1): for pool range `[pool_min, pool_max]`, value-at-risk = `[player_value − pool_max,
  player_value − pool_min]`. **No clamp** — a negative value-at-risk is descriptive (the pool currently
  out-values the player) and is shown as-is. Never a single "loss" number, never a severity label.
- **Cumulative value-at-risk is depletion-aware** (Gemini R1 — the pool is consumed as spots are filled).
  **Explicit formula (orientation pinned — Codex R2):** per position `p` with `N_p` cuts, let
  `cut_sum_p = Σ value(cut players at p)`, `upper_recovery_p = Σ top-N_p of p's unrostered pool`,
  `lower_recovery_p = Σ bottom-N_p of the top-K of p's pool`. Then
  `cumulative_value_at_risk = [ Σ_p (cut_sum_p − upper_recovery_p),  Σ_p (cut_sum_p − lower_recovery_p) ]`
  (low bound uses the BEST recovery, high bound the WORST). This is **not** `N ×` a single-player range
  (which would assume N copies of the best FA and understate the at-risk value). When `N_p` exceeds the
  available pool at `p`, the deficit is surfaced explicitly (no fabricated replacement), tied to the §7
  fail-closed status. RED locks the orientation so an implementation cannot invert the range.
- **No 10/90 projection envelopes** (no validated per-player distribution exists; the stores hold only the
  point estimate `projection_2y`). Showing an invented band would fabricate precision.

## 7. Unrostered-pool replacement range (wide, volatile, fail-closed)

- **Derivation (net-new aggregation):** from the Sleeper snapshot, take all players NOT on any roster, by
  position; score them via the PVO; take the top **K** (K configurable, default ~8–10) per position; emit
  a **deliberately wide** range (min/max of that pool's value, not a tight interval) labeled
  `current_unrostered_pool_range`.
- It is **explicitly NOT** a confidence interval or projection interval — it represents "what the active
  waiver pool currently looks like," which shifts daily in the preseason.
- **Fail-closed** to `status="waiver_range_unavailable"` (no range emitted, caveated) when any of:
  snapshot staleness exceeds a freshness bound, roster coverage is incomplete, valuation coverage of the
  unrostered pool is below a floor, or the position pool size `< min_pool`. Never fabricate a range.

## 8. Robustness boundary (per 02 §Falsification #8)

- **API-misuse (wrong argument types / shapes)** → fail loud (`TypeError`/`ValueError`).
- **Data-corruption (malformed PVO or Sleeper snapshot; missing required keys)** → fail closed with an
  explicit aborted/degraded status + caveat; never partial-credit a corrupt input.
- **Semantic / range / finiteness** → a non-finite or missing `xvar`/`projection_2y`/`dvs` for a player
  yields `value_field_status != "ok"` and excludes that player's value from ranges with a count; never
  silently imputed, never crashes the run.
- **Survivorship / completeness** → every cut-eligible player appears in `candidates` (none silently
  dropped); exempt (taxi/IR-compliant) players are listed as exempt, not omitted.

## 9. Deferred to v2 (explicitly, with the gate)

- **Cut-N optimizer** — only after a **governed objective** defines "best" in a way that is auditable and
  does not read as a cut-recommendation (it must survive the §2 no-verdict line). Until then, the
  simulator reflects David's scenarios; it does not choose them.
- **Computed market lane / divergence** in the value-at-risk (kept overlay-only here).
- **Validated per-player projection distribution** → unlocks honest envelopes if/when an engine update
  produces one.
- **API route + UI.**

## 10. Falsification matrix seeds (for the implementation plan's RED)

- Nominal: roster over capacity → `total_capacity_cuts_required` and `active_slot_overflow` BOTH reported
  (and may differ); candidates in engine order with `candidate_source`; default scenario clears
  `total_capacity_cuts_required` with a depletion-aware cumulative value-at-risk range.
- **Both overflow concepts** distinguished: a roster legal on total capacity but over active slots reports
  `active_slot_overflow>0, total_capacity_cuts_required==0` (Codex R1).
- **`forced_review` candidates**: an illegal/IR-forced `cut_priority==0` row appears with
  `candidate_source="forced_review"`, ahead of `capacity_ordered`; `clear_n` semantics for whether
  priority-0 rows count toward N are asserted explicitly (Codex R1).
- **Join-back**: raw `xvar`/`projection_2y` come from the PVO join (not the cut engine); a candidate
  present in the cut engine but missing from the PVO → per-field `value_field_status="unavailable"`,
  excluded-with-count, not crashed (Codex R1).
- **Value-at-risk orientation** pinned: `[player − pool_max, player − pool_min]`, negatives unclamped
  (Codex R1).
- **Depletion-aware cumulative**: cutting N at a position uses top-N..bottom-N of the pool, NOT N× a single
  range; N exceeding the pool surfaces the deficit (Gemini R1).
- David-supplied `proposed_cuts` honored; a proposed cut that is taxi/IR-exempt or off-roster → caveated,
  not silently dropped. `clear_n` larger than available candidates → fail-closed/caveated, no crash.
- Waiver pool thin / stale snapshot / low coverage → `waiver_range_unavailable` (no fabricated range).
- Non-finite / missing `xvar`/`dvs`/`projection_2y` → the right per-field `value_field_status`,
  excluded-with-count; `unknown_position` handled.
- Malformed PVO / snapshot → fail closed. Wrong-type args → fail loud.
- Banned-language / no-verdict scan (Codex R2 — phrase-based, not token-based): the ban targets
  **imperative / verdict PHRASES** in emitted *values/caveats* — e.g. "cut X", "must keep", "drop him",
  "safe to cut", "sell now", any severity adjective applied to a player. It does **NOT** ban the neutral
  descriptive **field names** the schema needs (`proposed_cuts`, `cut_set`, `clear_n`,
  `marginal_next_candidate_cost`, `candidate_source` — these are David's inputs / descriptive structure,
  explicitly allowed). Absence checks: no `sub_replacement_flag` / `replacement_gap` field; no optimizer /
  "best set" output; no 10/90 envelope fields; no market value in the value math.
  `decision_supported=False` recursive on every object + root.
- Read-only: producer patches `subprocess.run` to forbid git; writes only the gitignored artifact.

## 11. Reuse map (existing infra this consumes)

| Need | Reuse | Path |
|---|---|---|
| Capacity math + ordering + candidate source/exempt + `xvar_pct`/`dvs` | `compute_roster_cut_candidates` / `RosterCutResult` (NOT raw xvar/projection) | `src/dynasty_genius/roster_cut_engine.py` |
| Raw `xvar` + `projection_2y` per candidate | join by `sleeper_player_id` into the PVO (`valuation.xvar`, top-level `projection_2y`) | `universe_pvo` (the static `ENGINE_B_REPLACEMENT_DVS` is already baked into xVAR; not a direct dep) |
| Live PVO resolution (seed/runtime, fail-closed) | `resolve_pvo_source` | `src/dynasty_genius/pvo_source` |
| Unrostered-pool membership | Sleeper snapshot rosters/players | `app/data/league_snapshots/` |
| Artifact write convention | `write_{report}_artifacts` JSON + `-latest` | existing producers |
| Display-token policy | **Local** no-verdict policy for THIS artifact's caveats/statuses (Codex R2 — the API `SAFE_TOKENS` in `roster_audit_models.py` is roster-audit/API-specific and does NOT cover this backend artifact's fields; do not reuse it. API token mapping deferred to the later API surface) | n/a (v1 backend artifact) |

**Do NOT call** `trade_lab/reconciler.py` (trade-induced overflow is its job, not standing-roster health).

## 12. Open questions (RED-time calibration / confirmations)

- Exact freshness bound + coverage floors + `min_pool` / `K` for §7 (numeric calibration — propose at RED).
- Confirm the Sleeper-snapshot unrostered derivation handles taxi/IR/other-roster membership correctly
  (unrostered = players on no `rosters[].players`; exclude taxi/IR/reserve of all teams as appropriate).
- `cumulative_value_at_risk` surfaces both raw xVAR (primary, cross-position) and raw PPG, depletion-aware
  (§6) — confirm the per-position pool-sort + N-deep aggregation contract at RED.

## 13. Change log
- **v2 (2026-06-28):** integrated cockpit review round 1 — Codex R1 (5: PVO join-back for raw
  xvar/projection; `over_by`→both `total_capacity_cuts_required`+`active_slot_overflow`; `candidate_source`
  forced_review/capacity_ordered; value-at-risk orientation pinned + unclamped; per-field
  `value_field_status`) + Gemini R1 (3: removed static `replacement_gap`/`sub_replacement_flag`;
  depletion-aware cumulative value-at-risk; `marginal_next_cut_cost`→`marginal_next_candidate_cost`).
- **v3 (2026-06-28):** integrated cockpit review round 2 — Codex R2 (5: §2 stale "replacement gap /
  sub-replacement flag" removed from the allowed list; §11 `SAFE_TOKENS` row replaced with a local
  no-verdict token policy [API allowlist is API-specific]; §10 banned-language narrowed to imperative/
  verdict PHRASES, neutral field names `proposed_cuts`/`cut_set`/`clear_n` explicitly allowed;
  `active_slot_overflow` clamped to `max(0, …)`; §6 explicit depletion aggregate range formula pinned).
  Gemini R2: all R1 resolved, no new product/honesty defects.
