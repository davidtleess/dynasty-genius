# Trade Lab Forced-Cut Penalty — RC v1 Reconcile (Design)

**Date:** 2026-06-29
**Status:** Draft for cockpit review → David approval → plan → cockpit-TDD
**Authors:** Claude (impl), with Gemini strategy/UX framing + Codex technical scoping (framing-first protocol, `02` § "Strategy/UX framing first")

## 1. Goal

Re-base the **existing** Trade Lab forced-cut penalty onto the Roster Capacity Simulator v1 substrate so a trade is priced against the **depletion-aware NET value-at-risk** of the cuts it forces — what David actually loses *after* the waiver wire partially replaces a cut — instead of a **gross scalar** that overstates the cost. Bring the surface into compliance with the **No-Verdict Line** (constitution `78cff59`). Additive and non-breaking.

## 2. The gap (repo reality)

`src/dynasty_genius/trade_lab/reconciler.py` (Phase 22) already computes a forced-cut penalty:
- `reconcile_trade_roster(david_assets, received_assets, universe_pvo, sleeper_snapshot, david_roster_id=1) -> TradeRosterReconciliation`.
- Builds a post-trade snapshot, runs the **old** `roster_cut_engine.compute_roster_cut_candidates`, takes `forced_cuts = cut_candidates[:post_trade_overflow]`.
- `forced_cut_penalty_xvar` = **sum of forced-cut raw xVAR** (positive-only; unavailable excluded with caveat) — a **gross scalar**.
- Subtracts that gross from `base.side_b.side_value`; derives `adjusted_favors ∈ {neutral, david, counterparty}`.
- `market_reconciler.py` (Phase 23) has `david_forced_cut_penalty` + `counterparty_forced_cut_penalty` (`MarketRosterPenalty`).
- All models already `decision_supported=False`.

**Two defects this reconcile fixes:**
1. **Gross overstates cost.** Summing the full value of forced cuts ignores that a cut player is partly replaceable from the wire. The honest figure is **net**: `cut_value − waiver_recovery`, which RC v1 already computes (depletion-aware, per position).
2. **Pre-No-Verdict-Line.** A single penalty *number* and a single `adjusted_favors` *verdict* assert precision the data may not support; the constitution now favors descriptive **ranges** and an honest "uncertain" when the math is ambiguous.

## 3. Approach

Reuse RC v1 as the canonical capacity + value-at-risk engine. After building the post-trade snapshot, call:

```
simulate_capacity_scenarios(universe_pvo, post_trade_snapshot, david_roster_id,
                            scenarios=None)   # default scenario = clear total_capacity_cuts_required
```

**Do NOT pass `clear_n=post_trade_overflow`** (Codex R1 #1): that would keep the legacy capacity math partially authoritative. Let RC compute the required cuts from the post-trade snapshot itself (the default scenario), then **compare** the legacy `post_trade_overflow` to RC's `capacity_health.total_capacity_cuts_required` and surface a caveat/reporting field if they diverge. Read from the single resulting `ScenarioResult`:
- `cut_set` → the forced-cut player set (RC is the **canonical cut selector**; it still delegates to `compute_roster_cut_candidates` internally, better-wrapped).
- `cumulative_value_at_risk: tuple[float, float]` → the **depletion-aware NET penalty range** `[low, high]` (best-case recovery → worst-case).
- `pool_deficits: dict[str, int]` → positions where forced cuts exceed the replaceable pool.
- scenario `caveats` → unavailable/barren/deficit annotations.

RC v1's existing behaviors give Gemini's falsification seeds for free: unavailable pool → `[0, cut_sum]` uncertainty band; barren-but-valid pool → net == gross; deficit → unreplaced cuts recover 0 + `pool_deficits`; capacity-positive trade (`overflow == 0`) → no scenario, penalty 0.

**Additive, non-breaking.** Keep every existing scalar field (now documented as the legacy **gross** figure); add range-native fields as the new truth. Consumers migrate to the range fields; the gross fields remain for back-compat and as an honest "absolute value leaving the roster" display (Gemini: show gross *and* net).

## 4. Resolved design decisions (three-way cockpit-converged)

1. **Reuse `simulate_capacity_scenarios`**, do not re-implement the depletion math in Trade Lab. RC is the canonical source of the cut set and required-cut count on the post-trade snapshot. Assert the trade's `post_trade_overflow` agrees with RC's `total_capacity_cuts_required` (or caveat the divergence).
2. **Unavailable-pool posture = RC v1 `[0, cut_sum]`** (NOT a gross `(cut_sum, cut_sum)` fallback). Gemini retracted the gross fallback: it reintroduces the over-penalization defect under a "conservative" label and asserts false precision. Honest uncertainty (best case break-even, worst case full bleed) preserves the No-Verdict Line and stays consistent with RC v1 everywhere.
3. **Additive shape, scalars preserved.** Keep `forced_cut_penalty_xvar` (legacy gross, positive-only); add `forced_cut_value_at_risk_range`, range-native adjusted fields, and `adjusted_favors_status` with a new `uncertain_range_crosses_parity` state. Do not mutate the existing scalar `adjusted_favors` (would break API/cross-lane consumers).
4. **RC `status == "blocked"` → Trade Lab returns a blocked/unavailable penalty surface** — never a fabricated zero, never a 500 from the API route.
5. **Total-capacity overflow drives the penalty.** Active-slot overflow stays descriptive only (not a penalty trigger), matching RC v1's distinction.
6. **Market lane prices an already-model-selected cut set.** `market_reconciler.py` must NOT select cuts by FantasyCalc value — model-native cut selection only, FC stays overlay (KTC/market-overlay leakage guard). David and counterparty penalties computed independently, each failing closed independently.
7. **Display clamp vs raw range.** A displayed `adjusted_received_value` may floor at 0; the **raw net value-at-risk range stays unclamped** (zero-crossing visible — a capacity-positive or net-upgrade trade can read negative).

## 5. New contract (additive)

`RosterPenaltySummary` gains (legacy fields unchanged):
- `forced_cut_value_at_risk_range: tuple[float, float]` — depletion-aware NET, from the RC scenario `cumulative_value_at_risk`.
- `forced_cut_recovery_range: tuple[float, float]` — **the depletion recovery the waiver wire provides** = `(gross − net_high, gross − net_low)` = `[lower_recovery, upper_recovery]`. The descriptive "how much the wire offsets the cut" view (David's offseason decision input). **Strictly mathematically named** — no "savings"/"cushion"/value-laden framing (Gemini R2 #3 nudge-guard). Gives the clean three-view breakdown: gross lost / recovery / net at-risk.
- `pool_deficits: dict[str, int]` — from the RC scenario.
- `penalty_status: Literal["ok", "uncertain_pool_unavailable", "blocked"]` — surfaces the RC pool/audit state.
- (docstring: `forced_cut_penalty_xvar` is the legacy **gross** positive-only sum — an absolute-value-leaving display, not the net cost. Caveats label the net-range bounds: low = `best_case_recovery` (top available claimed), high = `worst_case_recovery` (bottom of top-K) — Gemini R2 #5.)

`TradeRosterReconciliation` — **quantity scalars vs the verdict scalar are treated differently (principled):** the legacy *quantity* scalars `adjusted_received_value`, `adjusted_fairness_delta`, `adjusted_within_parity_band` stay **gross-derived** (the conservative figures, shown alongside the new net ranges — "show gross and net"). Only the *verdict-shaped* `adjusted_favors` is frozen to `base.favors` (§10) — a single directional enum cannot honestly carry a gross OR a collapsed-net penalty claim, so the honest penalty-aware answer lives only in `adjusted_favors_status`. New fields:
- `adjusted_received_value_range: tuple[float, float]` = `(base.side_b − high, base.side_b − low)` where `[low, high]` is the net penalty range. **Raw, unclamped — one field, one meaning (Codex R2 underspec #2):** zero-crossing stays visible; NO separate clamped backend field this increment (display flooring is the future UI's job, not a backend field).
- `adjusted_fairness_delta_range: tuple[float, float]` — **non-monotonic, must be pinned (Codex R1 #2):** `abs(sent − received)` does not move monotonically with received. Let `S = base.side_a.side_value` and the adjusted-received interval be `[r_lo, r_hi]`. Then `delta_lo = 0` if `S ∈ [r_lo, r_hi]`, else `min(|S − r_lo|, |S − r_hi|)`; `delta_hi = max(|S − r_lo|, |S − r_hi|)`. RED pins this.
- `adjusted_favors_status: Literal["neutral", "david", "counterparty", "uncertain_range_crosses_parity"]` — **explicit 4-state machine (Codex R1 #3):** evaluate the adjusted-delta interval against the parity band over the whole range — `neutral` if the entire range is within parity; `david` if the entire range favors David beyond parity; `counterparty` if the entire range favors the counterparty beyond parity; `uncertain_range_crosses_parity` if the range is mixed (straddles the parity boundary or flips sides). RED pins each state.

**Market lane — FC-native, no scale mixing (Codex R1 #4 + Gemini R1 #2):** `MarketRosterPenalty.penalty_market_value` is FantasyCalc scale; RC's net range is xVAR/model scale — **never blend them.** `reconcile_trade_market` does not currently receive `sleeper_snapshot`; **add it** so the market lane can identify the unrostered pool and compute its **own FC-scale net replacement range** on `fantasycalc_entries`, independently per side (david + counterparty). The model-native cut SET is still chosen by the model (no FC cut selection — leakage guard, §4.6); the market lane only prices that already-selected set at FC values + its FC-native recovery range. **Explicit FC-scale field names (Codex R2 underspec #1)** on `MarketRosterPenalty` per side: `forced_cut_market_value_at_risk_range: tuple[float, float]` (net, FC scale), `forced_cut_market_recovery_range: tuple[float, float]` (FC-scale recovery), `market_penalty_status: Literal["ok", "uncertain_pool_unavailable", "blocked"]`. The legacy `penalty_market_value` scalar is preserved as the FC gross. No xVAR-scale field ever appears on a market model.

**Range null contract (Codex R3 #2):** every `*_range` field is `tuple[float, float] | None`. It is **`None` only when `penalty_status`/`market_penalty_status == "blocked"`** — a `(0.0, 0.0)` default on a blocked result would itself be a fabricated zero. An **unavailable** pool still yields a real range `[0, cut_sum]` (honest uncertainty, not None). New fields default safely so existing direct constructors (incl. Phase-23 route fixtures) stay green (Codex R3 #1): the additive fields default to `None`/`{}`/`"ok"`.

**Relative parity band (Codex R3 #3):** `_favors_status` must use the evaluator's existing relative band `delta <= TRADE_PARITY_BAND * max(side_a, received)` — and `max(side_a, received)` **varies across the received range**, so the status cannot use a fixed `sent_value * band`. RED pins boundary cases where `received` is both below and above `sent`.

**Render distinction (Codex R3 #5):** two different render rules — `favors`/`adjusted_favors`/`adjusted_favors_status` are **permanently never rendered** (the UI shows `delta_status`); the new **range fields** (gross/net/recovery) are **backend-only in THIS increment** but are render-intended for the later UI increment (their whole point is an honest gross/recovery/net breakdown). T5's FE guard enforces "not rendered in this increment," not a permanent ban.

All new models/fields keep `decision_supported=False` recursively.

## 6. No-Verdict-Line compliance

- `decision_supported=False` recursive on root + every nested model (already true; preserve).
- Banned-language scan over **new** field names, caveats, and stdout/API JSON fixtures — reject transaction verdicts (`buy`, `sell`, `hold`, `accept`, `reject`, `recommended`, equivalents).
- `adjusted_favors_status` reports `uncertain_range_crosses_parity` rather than a single side when the net range is ambiguous — no false-precision verdict.
- Net range stays unclamped (zero-crossing visible); gross shown alongside net (no hidden absolute value).

## 7. Testing strategy (RED must cover — for the plan)

Behavior contracts, not implementation:
- Net range from RC depletion (not `N × single`); unavailable-pool `[0, cut_sum]`; barren pool net == gross; deficit → `pool_deficits` + unreplaced-cuts recover 0; capacity-positive trade (`overflow 0`) → penalty 0, no cuts.
- RC canonical: call uses `scenarios=None`; legacy `post_trade_overflow` vs RC `total_capacity_cuts_required` divergence → caveat (not silently re-using old overflow).
- RC `status == "blocked"` → Trade Lab blocked surface (no fabricated 0, no 500 at the API route).
- `adjusted_received_value_range` propagation; `adjusted_fairness_delta_range` pins the non-monotonic formula (`delta_lo = 0` when `S` is inside the received interval, else nearer endpoint; `delta_hi` = farther endpoint).
- `adjusted_favors_status` — all **four** states pinned (entirely-in-parity→`neutral`, entirely-david, entirely-counterparty, mixed→`uncertain_range_crosses_parity`), not just a shallow straddle.
- §10 (b): legacy `adjusted_favors` == `base.favors` (capacity-unaware); the rewritten Phase-22 favors tests assert base-direction, NOT gross-penalty direction; `cross_lane_review` + `trade_market` consume `adjusted_favors_status`.
- Dual-side independence (david + counterparty, each fail-closed independently); market lane net range is **FC-scale** (computed from `fantasycalc_entries`), never the xVAR range; market lane does NOT select cuts by FC.
- `decision_supported` recursive + banned-language scan over new field names, caveats, stdout/API JSON fixtures; Surface-2 FE non-render of the new fields.

## 8. Blast radius

- **Core:** `src/dynasty_genius/trade_lab/reconciler.py`, `src/dynasty_genius/trade_lab/market_reconciler.py`.
- **Consumers:** `app/api/routes/trade.py`, `app/api/routes/trade_market.py` (`model_favors_raw=hydrated_recon.adjusted_favors` at :351 — migrate to `adjusted_favors_status`), `src/dynasty_genius/trade_lab/cross_lane_review.py` (normalizes the `adjusted_favors` vocabulary — migrate to `adjusted_favors_status`).
- **Frontend/typed-client surface (Codex R1 #5):** response models change → OpenAPI/typed-client regen. The **Surface-2 rule stands: `favors`/`adjusted_favors`/`adjusted_favors_status` are NEVER rendered** (the UI shows `delta_status`, not favors); new range fields must respect that non-render contract.
- **Tests:** `tests/test_phase22_trade_reconciler.py`, `tests/test_phase22_reconcile_endpoint.py`, Phase-23 market route/tests, Surface-2 FE test (non-render of new fields), plus new RED.

## 9. Out of scope / non-goals (v1)

- No optimizer / "best cut set" selection — RC's existing capacity order only.
- No accept/reject trade verdict; no normative bands.
- No change to Engine A/B, PVO, market overlay, or the consolidation/parity math itself (penalty still deducts from the received side; we add the range view).
- No new UI surface in this increment (range fields are backend-only; UI is a later increment).
- No **removal** of legacy scalar fields this increment. Note: `adjusted_favors` is re-pointed to `base.favors` per §10(b) (a deliberate semantic change to neutralize the gross-penalty verdict); `forced_cut_penalty_xvar` and the other scalars are preserved as the legacy gross figures. Full field removal is a later breaking increment once consumers have migrated to the range-native fields.

## 10. Legacy `adjusted_favors` — RESOLVED (b)

The existing scalar `adjusted_favors` is **gross-penalty-derived** — that is itself the No-Verdict defect we are fixing, so it must not be preserved as-is. Three options were debated: (a) leave gross-derived + disagreement caveat; (b) freeze to `base.favors` (capacity-unaware base label); (c) re-derive from the net range, straddle→`neutral`.

**Resolution: (b)** (Codex + Claude; cockpit-converged). `adjusted_favors` is frozen to `base.favors` and explicitly documented as the **capacity-unaware base trade direction (deprecated)** — it asserts no penalty/capacity claim. ALL capacity/penalty-aware interpretation lives in the new range-native `adjusted_favors_status` (which has the explicit `uncertain_range_crosses_parity` state the 3-value legacy enum cannot represent). The two backend consumers (`cross_lane_review.py`, `trade_market.py:351`) migrate to `adjusted_favors_status` this increment.

Why not (c): it collapses a range into a single directional enum on the legacy scalar and overloads `neutral` to mean both "balanced within parity" AND "uncertain straddle" — two distinct facts conflated. Gemini's (c) rested mainly on a transition-blindness concern that was **falsified**: `adjusted_favors` is never rendered in the FE (Surface-2 RED contract; the UI renders `delta_status`), so freezing it to base cannot blind the UI. The legacy Phase-22 tests that assert the gross-derived favors get rewritten in the RED — they lock in the defect.
