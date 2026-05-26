---
title: Draft Pick Valuation (Dynasty Rookie Slots) — Design Spec
status: v1 DIRECTION APPROVED (David, 2026-05-26) — Codex + Gemini consulted; pending final spec review → writing-plans
date: 2026-05-26
author: Claude Code (brainstormed with David; Codex engineering + Gemini PM consults folded in)
supersedes_approach: docs/strategies/trade_execution_logic.md "E27 currency" (rejected — §1)
phase_note: Reopens the Phase 17.3 future-pick-value lock — David-approved 2026-05-26 (§6)
governance_hold: Frontend remains on the Phase 12 HOLD; this is backend only.
---

# Draft Pick Valuation (Dynasty Rookie Slots) — Design Spec

## 0. What we're building

Assign a **value to a dynasty rookie draft pick** (e.g. "a 2027 mid-1st") in the **same unit
players already use (`xVAR`)**, so trades mixing players and picks reduce to one comparable
number. v1 is the **historical backbone + SF-QB ordering knob only**; near-class projection and
external ADP are explicitly deferred.

## 1. Rejected: the "E27 currency"

`docs/strategies/trade_execution_logic.md`'s hand-set "2027 1st-equivalent (E27)" currency is
**not** being built: its weights are definitional/self-described as "illusory until backtested"
(its own counter-argument #1, "a circular calibration"), it invents a third currency, and it is
written in banned verdict language (Accept/Reject/Sell-now). **We value picks in `xVAR`,
derived from data.**

## 2. Rejected: how picks are valued today

`evaluator.py:value_draft_pick(round, bucket, position, age)` **fakes one player** — maps
`early/mid/late` to an NFL pick number (3.0/6.5/10.5) and scores a `<position>` prospect through
Engine A. David ruled this unacceptable: it forces an **assumed position**, **conflates a
dynasty slot with an NFL pick**, and values **one made-up player**. This spec **replaces** it.

## 3. Unit and the two regimes

**Unit:** `xVAR` (and underlying `dynasty_value_score`), exactly as players carry today.

- **Regime A — drafted class (e.g. 2026):** per-prospect Engine A values already exist
  (`prospect_cards.json`); picks could use the realistic distribution of available prospects.
  **v1 DEFERS Regime A wiring (Codex):** v1 values only future/unknown slots via the §4
  historical curve. Drafted-class / current-year per-prospect valuation is a later path (David
  may pull it in, but it is out of v1 scope).
- **Regime B — undrafted future class (2027, 2028+):** value from a **historical
  realized-value-by-dynasty-slot curve** (§4). Near-class named projection (§5) is **deferred**.
  **This is v1.**

## 4. The historical dynasty-slot value curve (the backbone)

**Goal:** "dynasty rookie slot N has historically delivered X `xVAR`."

**Construction — David's 36-skill-player NFL bridge, built directly from realized outcomes:**
His league's rookie draft is **36 picks (12×3)**. For each *mature* historical class in
`app/data/training/prospects_with_outcomes.csv`:
1. Take the **first 36 QB/RB/WR/TE in NFL draft order** → the assumed FF rookie board.
2. For each of those players, compute `xVAR` **directly from their realized `y24_ppg`**:
   `y24_ppg → DVS (÷ position P90 ×100, clamped) → xVAR ((DVS − replacement_pos) × λ_pos)`,
   using each player's **actual position-specific** constants. **Constant sources (do not let
   the plan infer these — Codex):** P90 from `scoring/engine_a.py` `_P90_PPG`
   (WR 12.7 / RB 14.6 / TE 9.1 / QB 16.7); replacement DVS + λ from `engine_b_contract.py`
   (`ENGINE_A_REPLACEMENT_DVS`, `XVAR_LAMBDA_ENGINE_A`). Implementation may export these into one
   governed constants module. **Do NOT route through `score_prospect()`** (that re-introduces
   the fake-player flaw — Codex).
3. Assign each player to FF slot `k` (1..36) by board order; per player compute the
   **option-value floor `priced_xvar = max(0, xVAR)`** — a busted pick is benched/cut and
   contributes 0, never negative (aligns with the Phase 17 best-legal-lineup guardrail).
4. Slot **expected value = MEAN of `priced_xvar`** across all (slot, year) samples (mean, NOT
   median — median zeroes deep slots and erases the upside; the mean of floored payoffs is the
   expected option value, e.g. a 10%×+50 / 90%×bust slot → +5). Preserve `raw_samples`
   (negatives intact) + `priced_samples` + raw/priced stats for audit; the monotonic clamp and
   median tier rollups then operate on the mean-priced expected value.

   > **Option A — adopted 2026-05-26 (in-flight correction).** The first real-data build
   > produced negative round-2/3 xVAR because xVAR is value-above-replacement and most late
   > picks bust. A pick is a call option, so bust outcomes floor at 0, not negative. Codex
   > (engineering) + Gemini (governance) consensus; Gemini ruled it an in-flight correction
   > (not a policy override) aligning pick math with the Phase 17 starting-lineup rule. Every
   > pick value carries the caveat `pick_value_floored_at_replacement`.

**Data-maturity gate (Codex):** `y24_ppg` is realized **Year 2+3** PPG, so recent classes are
empty/low-sample (2024/2025 = 0/36 usable; 2023 mostly low-sample). **v1 uses mature classes
~2015–2022.** The doc must be honest that the usable sample is **smaller than the full 11
classes** and reconcile `low_sample_holdout` semantics with `validation-gates.md`.

**Granularity + smoothing (Codex):**
- Persist **per-pick (1..36)** internally; expose **tier rollups** (early/mid/late 1st, 2nd, 3rd)
  for generic future picks (tier **median / trimmed mean**, not a noisy single pick).
- Expected value is **monotonic-smoothed** across slots; keep **raw samples** for audit.
- Store per slot: `n_years`, `mean`, `median`, `p25/p75`, `stdev/MAD`, `low_sample_count`,
  `mature_years_used`.
- Output as a **versioned artifact** with provenance (e.g. `draft_pick_value_curve_v1.json`).

**SF-QB adjustment — an ORDERING knob, not an xVAR multiplier (Codex):** before slot
aggregation, **promote QBs meeting pick/round thresholds by K slots**, then regenerate the
curve. **Calibrate K** by minimizing rank/slot-residual error against real Sleeper rookie-draft
history (§4.1), leave-one-year-out only if the sample supports it. Until calibrated, ship as
**manually-set with a thin-sample caveat**.

### 4.1 Calibration corpus (honest reality)

Plan: **blend David's own league rookie-draft history with curated seed data; decay the seed
weight as his own sample grows.** Tempered by `docs/strategies/Rookie Draft Seed Data.md`:
- The strict 12T/SF/Full-PPR/non-TEP **per-league** corpus **does not exist publicly** (~3
  partial-match drafts; "Full PPR?" unverified).
- Sleeper has **no league-search-by-settings**; we can only pull known league IDs. We *can*
  pull **David's league history** (`previous_league_id` chaining + `/league/{id}/drafts` +
  `/draft/{id}/picks`; repo wraps these in `app/data/sleeper.py`).
- Aggregate rookie ADP (DLF MFL) is the report's suggested proxy but is **external,
  settings-approximate, seasonal — deferred** (§7).

**Net:** v1 leans on the in-repo NFL-bridge curve as the backbone; the seed drafts + David's
league are a **calibration/validation layer that strengthens over time**, not a launch
dependency. v1 is an NFL-derived **expectation**, not a dynasty-market-**measured** price.

## 5. Near-class projection (Regime B near years) — DEFERRED (mandatory per Gemini)

Projecting a named-prospect board for an undrafted near class (project NFL capital from
consensus mocks → Engine A → order into FF slots via rookie-ADP) requires **two cascading
projection layers** on analyst/consensus data. **Deferred** until the §4 historical curve is
stable and validated against David's league history. Not in v1.

## 6. Governance

- **Reopens the Phase 17.3 future-pick-value lock** (`PICK_VALUE_STATUS = "deferred"`) —
  **David-approved 2026-05-26**. Deliverables: record in `AGENT_SYNC.md` (Phase 23/24) and a
  short PM decision memo at `docs/validation/2026-05-26-future-pick-valuation-reopening-decision.md`
  documenting the deferred→active transition (Gemini).
- **Descriptive signals only** (`pick_value_xvar`, `expected_historical_slot_value`); **no
  buy/sell/win/loss/verdict tokens**. Downstream (Trade Lab) only **sums pick `xVAR`** into the
  package total; no verdict labeling.
- **Recursive `decision_supported=False`** whenever a pick asset is present in a trade
  (`TradeAsset` and any package object). Top-level §12 caveats incl.
  `pick_value_historical_expected`, `pick_value_floored_at_replacement`,
  `sf_qb_ordering_assumption`, `pick_value_thin_sample`.
- **Model/market separation — absolute:** consensus mocks / ADP are overlay/inference-only and
  **never** written to `prospects_with_outcomes.csv` or any training dataframe. Add a contract
  test (`test_pick_valuation_remains_strictly_inference_only`) scanning model-training files for
  zero mock/ADP-adapter imports (Gemini).
- **Static for v1** — no pick-appreciation-over-time (David's call; documented later
  enhancement).
- **Consumer scope (Codex):** v1 may surface numeric pick `xVAR` in the `future_picks` block,
  but **keeps pick values OUT of team-strength / posture aggregates** until a separate posture
  spec approves that math. The Team Value Matrix contracts that currently assert
  `future_picks_present_unvalued` must be **explicitly updated**.

## 7. v1 scope

**In:**
- Versioned **historical dynasty-slot → xVAR curve** artifact built per §4 (mature 2015–2022,
  direct realized-outcome xVAR, per-position aggregation, monotonic smoothing, stats,
  SF-QB ordering knob).
- New **`src/dynasty_genius/trade_lab/draft_pick_valuation.py`** boundary:
  `load_curve()` + `value_pick(year, round, slot_or_tier, curve, league_format) -> xVAR + caveats`
  — **no position required**, model-blind beyond reading the curve artifact. Keep `evaluator.py`
  thin.
- Replace `value_draft_pick`: migrate callers to `value_dynasty_pick(...)`, or keep
  `value_draft_pick` as a **deprecated, caveated compat wrapper** (position/age deprecated).
- Wire future-pick `xVAR` into PVO / Trade Lab (display + package sums); update Team Value
  Matrix contracts (values present, excluded from aggregates).
- PM decision memo + AGENT_SYNC record (§6).

**Deferred (later specs):** §5 near-class projection; aggregate-ADP (DLF MFL) ingestion + broader
seed corpus; pick appreciation over time; any decision-rule / accept-floor logic (only after the
valuation core is trusted, and only in neutral non-verdict language).

## 8. Contract-test intent (for the TDD pass)

- No position argument required; fake-player path removed; `score_prospect()` not used in the
  curve build.
- Exact-slot and tier values resolve; tiers use median/trimmed-mean; monotonic smoothing holds.
- Mature-year gate excludes **immature** classes (incomplete Year 2+3) and **records
  `low_sample_count`** — it does NOT drop individual low-sample rows from otherwise-mature years
  unless explicitly intended; stats fields populated; artifact versioned.
- Per-position lambda/replacement applied per-player **before** slot aggregation.
- `decision_supported=False` recursively whenever a pick is present; §12 caveats present.
- Model-training isolation: no mock/ADP imports reachable from training code.
- Team Value Matrix: pick values surfaced in `future_picks`, excluded from team-strength
  aggregates; old `future_picks_present_unvalued` assertion intentionally updated.

## 9. Counter-argument (Rule 5 — mandatory)

1. **Backbone rests on "FF order ≈ NFL skill order,"** materially wrong for SF QBs and
   landing-spot reorders. Mitigation: SF-QB ordering knob + real-draft calibration; explicit
   caveats; static v1.
2. **Calibration corpus is thin and may stay thin** (no public strict-spec corpus; no Sleeper
   settings search). Mitigation: honest framing — v1 is an NFL-derived expectation, not a
   measured dynasty price; `decision_supported=False` throughout; mature-year sample disclosed.
3. **Reopening the lock invites false confidence** in coarse expected values. Mitigation: heavy
   caveats, descriptive-only signals, picks excluded from team-strength aggregates, and the
   decision-rule layer kept out of scope until the valuation is trusted.
