# Trade Lab Forced-Cut Penalty — RC v1 Reconcile — Implementation Plan

> **For agentic workers:** This project executes via **cockpit-TDD** (Codex authors the RED → Claude GREEN → adversarial dual-CLEAR → David-authorized commit → both-lane post-commit zero-divergence), NOT the default subagent/inline execution. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Re-base the existing Trade Lab forced-cut penalty onto the RC v1 substrate so a trade is priced against the depletion-aware **net** value-at-risk *range* of the cuts it forces (not a gross scalar), and bring the surface into No-Verdict-Line compliance.

**Architecture:** Reuse `simulate_capacity_scenarios(scenarios=None)` as the canonical capacity + value-at-risk engine on the post-trade snapshot. Additive, non-breaking — keep legacy gross scalars (relabeled), add net-range fields; the only deliberate semantic change is `adjusted_favors → base.favors` (§10(b)). Model lane (xVAR) and market lane (FantasyCalc) reconciled in the **same PR**, scales never mixed.

**Tech Stack:** Python 3.14, Pydantic v2, pytest, pinned `ruff@0.15.12`. Spec: `docs/superpowers/specs/2026-06-29-trade-lab-forced-cut-penalty-rcv1-reconcile-design.md`.

## Global Constraints

- **No-Verdict Line** (constitution `78cff59`): `decision_supported=False` recursive on every new/changed model; no transaction verdict (buy/sell/hold/accept/reject/recommended); banned-language scan over new field names, caveats, and serialized JSON fixtures (not just source).
- **RC v1 is canonical:** call `simulate_capacity_scenarios(..., scenarios=None)`; the legacy `post_trade_overflow` becomes a cross-check caveat vs RC `total_capacity_cuts_required`, never authoritative.
- **Scale isolation:** model-lane range fields are xVAR only; market-lane range fields are FantasyCalc only. No xVAR field ever appears on a market model; FC never selects cuts (leakage guard).
- **Additive/non-breaking** except `adjusted_favors` (frozen to `base.favors`, §10(b)). Legacy quantity scalars stay gross (conservative, shown alongside net ranges). No field removal this increment.
- **Keep the full suite green at each task** (711-suite + RC suite). Pinned ruff clean each task. **Both lanes ship in one PR** (do not auto-split model-first — it distorts David's model-vs-market comparison; if the market lane balloons, revisit with David).
- **Fail-closed:** RC `status == "blocked"` → Trade Lab blocked/unavailable surface, never a fabricated 0, never a 500 at the API route.

## File Structure

- `src/dynasty_genius/trade_lab/reconciler.py` — model lane: new fields + RC v1 wiring + `adjusted_favors_status` + §10(b) freeze.
- `src/dynasty_genius/trade_lab/market_reconciler.py` — market lane: `sleeper_snapshot` arg + FC-native net/recovery ranges.
- `src/dynasty_genius/trade_lab/cross_lane_review.py` — migrate to `adjusted_favors_status`.
- `app/api/routes/trade.py`, `app/api/routes/trade_market.py` — route schemas + blocked-not-500 + consumer migration.
- Tests: `tests/test_phase22_trade_reconciler.py`, `tests/test_phase22_reconcile_endpoint.py`, Phase-23 market route/tests, Surface-2 FE non-render test; new RED files per task.

---

## Task 1: Additive model contract + pure range helpers

Isolate the hardest math (pure, no RC) before any RC wiring.

**Files:**
- Modify: `src/dynasty_genius/trade_lab/reconciler.py` (model fields + pure helpers).
- Test: new `tests/contract/test_trade_forced_cut_helpers.py`.

**Interfaces:**
- Produces (pure helpers, no I/O):
  - `_favors_status(received_range: tuple[float,float], sent_value: float, parity_band: float) -> Literal["neutral","david","counterparty","uncertain_range_crosses_parity"]`.
  - `_fairness_delta_range(sent_value: float, received_range: tuple[float,float]) -> tuple[float,float]` (non-monotonic per spec §5).
  - `_recovery_range(gross: float, net_range: tuple[float,float]) -> tuple[float,float]` = `(gross − net_high, gross − net_low)`.
- New `RosterPenaltySummary` fields (safe defaults so existing direct constructors stay green, `decision_supported=False`): `forced_cut_value_at_risk_range: tuple[float,float] | None = None`, `forced_cut_recovery_range: tuple[float,float] | None = None`, `pool_deficits: dict[str,int] = {}`, `penalty_status: Literal["ok","uncertain_pool_unavailable","blocked"] = "ok"`.
- New `TradeRosterReconciliation` fields **also default safely** (Codex R3 #1 — Phase-23 route fixtures construct it directly): `adjusted_received_value_range: tuple[float,float] | None = None`, `adjusted_fairness_delta_range: tuple[float,float] | None = None`, `adjusted_favors_status: Literal["neutral","david","counterparty","uncertain_range_crosses_parity"] = "neutral"`.
- Every `*_range` is `| None` and is `None` only on `penalty_status == "blocked"` (no fabricated zero); unavailable still yields `[0, cut_sum]`.

**Steps:**
- [ ] 1.1 **Codex RED** (`test_trade_forced_cut_helpers.py`): pin `_favors_status` all four states (entirely-in-parity→neutral; entirely-david; entirely-counterparty; mixed→uncertain_range_crosses_parity) **using the relative band `delta <= TRADE_PARITY_BAND * max(side_a, received)`, with `received` both below and above `sent`** so GREEN cannot use a fixed `sent_value * band` (Codex R3 #3); `_fairness_delta_range` with `S` below / inside / above the received interval (inside → `delta_lo == 0`); `_recovery_range` math; new model fields (both models) default safely (`*_range` default `None`) with `decision_supported=False` recursive. → FAIL (helpers/fields absent).
- [ ] 1.2 **Claude GREEN**: implement the pure helpers + add the fields with safe defaults. No behavior change to `reconcile_trade_roster` yet. → PASS.
- [ ] 1.3 Focused suite + pinned ruff; full `test_phase22_*` still green (additive).
- [ ] 1.4 **Dual-CLEAR** (Codex: math correctness + 4-state machine + non-monotonic delta; Gemini: field naming honesty / no nudge).
- [ ] 1.5 **David-authorized commit** `feat(trade-lab): forced-cut penalty range helpers + additive model fields`.

---

## Task 2: Model reconciler uses RC v1 (net range, gross preserved)

**Files:**
- Modify: `src/dynasty_genius/trade_lab/reconciler.py` (`reconcile_trade_roster`).
- Test: `tests/test_phase22_trade_reconciler.py` (extend).

**Interfaces:**
- Consumes: `simulate_capacity_scenarios` (RC v1), the post-trade snapshot.
- Produces: `RosterPenaltySummary` populated with the RC net range (`cumulative_value_at_risk`), recovery range, `pool_deficits`, `penalty_status`; legacy `forced_cut_penalty_xvar` preserved as gross. `TradeRosterReconciliation` adjusted range fields populated; quantity scalars stay gross.

**Steps:**
- [ ] 2.1 **Codex RED**: build post-trade snapshot → call `simulate_capacity_scenarios(..., scenarios=None)` (RED spies/asserts `scenarios is None`, not `clear_n=overflow`); read default scenario. Cover with real RC fixtures: net range = RC depletion (not `N × single`); unavailable pool → `[0, cut_sum]` + `penalty_status="uncertain_pool_unavailable"`; barren pool → net == gross; deficit → `pool_deficits` + unreplaced recover 0; capacity-positive trade (`overflow 0`) → penalty 0, no cuts; RC `status="blocked"` → `penalty_status="blocked"` with **`*_range` fields `None`** (no fabricated `(0.0, 0.0)`); unavailable → `[0, cut_sum]` (a real range, not None); legacy `post_trade_overflow` vs RC `total_capacity_cuts_required` divergence → caveat. **Gemini seeds:** same-player trade-and-cut (post-trade snapshot removes the traded-away player BEFORE capacity eval → never a cut candidate); pre-model wire (coverage < floor) → `[0, cut_sum]` + `valuation_coverage_below_floor`, no TypeError. → FAIL.
- [ ] 2.2 **Claude GREEN**: wire RC v1 into `reconcile_trade_roster`; populate net/recovery/deficits/status; preserve gross scalar + gross-derived quantity scalars; caveat the overflow divergence. → PASS.
- [ ] 2.3 Focused + pinned ruff; full `test_phase22_*` green.
- [ ] 2.4 **Dual-CLEAR** (Codex: RC wiring, fail-closed matrix, scenarios=None; Gemini: gross-and-net honesty, recovery field).
- [ ] 2.5 **David-authorized commit** `feat(trade-lab): model-lane forced-cut net value-at-risk via RC v1`.

---

## Task 3: §10(b) legacy `adjusted_favors` freeze + backend consumer migration

**Files:**
- Modify: `src/dynasty_genius/trade_lab/reconciler.py` (freeze), `src/dynasty_genius/trade_lab/cross_lane_review.py`, `app/api/routes/trade_market.py:351`.
- Test: `tests/test_phase22_trade_reconciler.py` (rewrite gross-favors), cross-lane review tests.

**Interfaces:**
- Produces: `adjusted_favors == base.favors` (capacity-unaware base label); `adjusted_favors_status` is the only capacity-aware favors field. Consumers (`cross_lane_review`, `trade_market.model_favors_raw`) read `adjusted_favors_status`.

**Steps:**
- [ ] 3.1 **Codex RED**: assert `adjusted_favors == base.favors` even when `adjusted_favors_status` differs (the old gross-derived direction no longer controls the legacy field); **rewrite the Phase-22 "gross favors" tests** to assert base-direction; `cross_lane_review` + `trade_market` consume `adjusted_favors_status`, not `adjusted_favors`; normalization handles the new `uncertain_range_crosses_parity` token (fail-loud on unknown preserved). → FAIL.
- [ ] 3.2 **Claude GREEN**: freeze `adjusted_favors = base.favors`; migrate the two consumers to `adjusted_favors_status`; extend the cross-lane vocabulary normalizer. → PASS.
- [ ] 3.3 Focused + pinned ruff; full suite green.
- [ ] 3.4 **Dual-CLEAR** (Codex: consumer-migration completeness, no stray reader of the legacy field for capacity meaning; Gemini: No-Verdict separation — no penalty verdict on the legacy scalar).
- [ ] 3.5 **David-authorized commit** `refactor(trade-lab): freeze legacy adjusted_favors to base; migrate consumers to range status`.

---

## Task 4: Market lane FC-native range (no scale mixing)

**Files:**
- Modify: `src/dynasty_genius/trade_lab/market_reconciler.py` (`reconcile_trade_market` gains `sleeper_snapshot`), `app/api/routes/trade_market.py`.
- Test: Phase-23 market route/tests.

**Interfaces:**
- Consumes: `sleeper_snapshot` (NEW arg), `fantasycalc_entries`, the model-selected cut set.
- Produces: `MarketRosterPenalty` per side gains `forced_cut_market_value_at_risk_range`, `forced_cut_market_recovery_range` (FC scale), `market_penalty_status`. Legacy `penalty_market_value` preserved as FC gross.

**Steps:**
- [ ] 4.1 **Codex RED**: `reconcile_trade_market` accepts `sleeper_snapshot` and computes an FC-scale unrostered pool + net/recovery range for the **already-model-selected** cut set (FC never selects cuts — leakage guard). **FC unrostered pool uses RC's rostered-union semantics (Codex R3 #4): rostered = players ∪ starters ∪ taxi ∪ reserve across all teams** — RED includes the "rostered only via starters/taxi/reserve is excluded from the wire" case and a missing-FC-value-coverage fail-closed case. david + counterparty penalties independent (one side's unavailable pool does NOT suppress the other); **no xVAR-scale value appears on any market field** (scale-isolation assertion); FC-native unavailable pool → `[0, cut_sum]` in FC scale; blocked → `None` ranges. → FAIL.
- [ ] 4.2 **Claude GREEN**: thread `sleeper_snapshot`; compute FC-native ranges per side; preserve `penalty_market_value` gross. → PASS.
- [ ] 4.3 Focused + pinned ruff; full Phase-23 suite green.
- [ ] 4.4 **Dual-CLEAR** (Codex: scale isolation + dual-side independence + FC-no-cut-selection; Gemini: market/model comparison honesty).
- [ ] 4.5 **David-authorized commit** `feat(trade-lab): market-lane FC-native forced-cut range (no scale mixing)`.

---

## Task 5: API routes + frontend guard + closeout

**Files:**
- Modify: `app/api/routes/trade.py`, `app/api/routes/trade_market.py` (response schemas + blocked-not-500), OpenAPI/typed-client if tracked, Surface-2 FE non-render test.
- Test: `tests/test_phase22_reconcile_endpoint.py`, Phase-23 endpoint tests, Surface-2 FE test.

**Interfaces:**
- Produces: API responses carrying the new range fields; `decision_supported=false` root; blocked surface (HTTP 200 with `penalty_status="blocked"` payload, NOT 500) when RC blocks.

**Steps:**
- [ ] 5.1 **Codex RED**: both routes return the new range fields; RC-blocked input (malformed PVO duplicate / malformed snapshot) → blocked/unavailable payload at HTTP 200, NOT a 500 and NOT a fabricated 0; banned-language scan over the serialized API JSON fixtures; Surface-2 FE test asserts **two distinct render rules (Codex R3 #5):** `favors`/`adjusted_favors`/`adjusted_favors_status` are **permanently** not rendered; the new **range fields** (gross/net/recovery) are **not rendered IN THIS (backend-only) increment** — phrased as a this-increment guard, not a permanent ban (they are render-intended for the later UI increment). → FAIL.
- [ ] 5.2 **Claude GREEN**: surface the new fields in the route responses; map RC-blocked → blocked payload; regenerate OpenAPI/typed-client if the repo tracks it; extend the FE non-render guard. → PASS.
- [ ] 5.3 **Closeout:** `scripts/verify_sprint_closeout.py --base origin/main` → ENFORCE PASS (full pytest + ruff src app + standalone-scripts + FE vitest if wired).
- [ ] 5.4 **Dual-CLEAR** (Codex: route contract, blocked-not-500, typed-client drift; Gemini: end-to-end no-verdict + non-render).
- [ ] 5.5 **David-authorized commit** `feat(trade-lab): forced-cut range API surface + FE non-render guard`.

---

## Post-build (David-gated)
- One PR (both lanes), 5 commits → push → CI green → David merge (preserve-commits) → close the loop → ledger/AGENT_SYNC close-out → branch delete.
- Deferred (own increments): UI surface rendering gross/recovery/net honestly; full removal of the legacy scalar fields once consumers have migrated.

## Self-Review (against spec)
- **Coverage:** §3/§4 RC reuse + posture → T2; §5 net/recovery/range fields + favors machine + delta math → T1/T2; §10(b) freeze + migration → T3; market FC-native + `sleeper_snapshot` → T4; §8 API/FE/typed-client → T5; §6 No-Verdict (decision_supported recursive + banned-language scan over fixtures) embedded each task. ✓
- **Placeholders:** none — every task has explicit files, interfaces, RED coverage, and a commit. ✓
- **Type consistency:** `forced_cut_value_at_risk_range` / `forced_cut_recovery_range` / `pool_deficits` / `penalty_status` (model lane, xVAR); `forced_cut_market_value_at_risk_range` / `forced_cut_market_recovery_range` / `market_penalty_status` (market lane, FC); `adjusted_favors_status` 4-state; `adjusted_*_range` quantity ranges; `adjusted_favors == base.favors`. Names used consistently T1→T5 and match the spec. ✓
