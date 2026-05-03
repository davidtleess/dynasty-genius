---
title: Trade Execution Logic — Liquidation Conversion Layer
type: project-knowledge
framework_protocol: 4D
last_updated: 2026-05-03
status: v1 — initial logic-layer design
parent_strategy: docs/strategies/2027_pick_accumulation.md
governs: trade-acceptance decisions for assets liquidated under The Great Liquidation
---

# Trade Execution Logic — Liquidation Conversion Layer

## 1. Purpose

The parent strategy ([2027 Pick Accumulation](2027_pick_accumulation.md)) defines **what** to liquidate and **into what tier**. This document defines the **conversion math** that determines whether a specific incoming offer meets the strategy's intent.

It exists because the parent strategy's pricing floors (§2.3) are necessary but not sufficient. A floor tells us "do not sell below this." It does not tell us how to compare a complex multi-asset offer (pick + player + future pick) against the floor in a defensible, auditable way.

Per Framework Rule 4 (65/35 quant-qual), this layer is **65% quant** — formula-driven — with explicit annotation of where the 35% qual judgment enters and why.

---

## 2. The Currency Unit: 2027 1st-Equivalents (E27)

All trade returns under this strategy are normalized to a single internal currency: **2027 1st-Equivalents (E27)**.

| Asset Type | E27 Value |
|---|---|
| 2027 Early 1st (1.01–1.04) | **1.50 E27** |
| 2027 Mid 1st (1.05–1.08) | **1.00 E27** *(definitional anchor)* |
| 2027 Late 1st (1.09–1.12) | **0.65 E27** |
| 2027 Early 2nd (2.01–2.04) | **0.40 E27** |
| 2027 Mid 2nd (2.05–2.08) | **0.30 E27** |
| 2027 Late 2nd (2.09–2.12) | **0.20 E27** |
| 2027 3rd (any) | **0.10 E27** |
| 2028 1st (slot unknown) | **0.55 E27** *(uncertainty discount)* |
| 2028 2nd (slot unknown) | **0.20 E27** |
| Startable 2026 player at WR2/RB2 | **0.25 E27** *(qual-adjusted; flag below)* |
| Startable 2026 player at WR3/RB3 | **0.10 E27** |

### 2.1 Anchor Calibration

The mid-1st = 1.00 anchor is **definitional**, not market-derived. It is set so that the strategy's pricing floors in the parent doc translate cleanly:

- Taylor floor of "2027 mid-1st + a startable WR3/RB3" = **1.10 E27**
- Adams floor of "2027 2nd OR 2028 1st (mid)" = **0.30–0.55 E27**
- Hill floor of "2027 2nd (any slot)" = **0.20–0.40 E27**

### 2.2 What These Numbers Are NOT

- They are **not** KTC values. They are internal units for strategy-execution math, not a competing market valuation.
- They are **not** Engine A or Engine B outputs. When Engine B ships, these weights become candidates for empirical re-fitting against realized outcomes.
- The 2028 1st discount (0.55) reflects the maximum-uncertainty posture documented in `class-trackers/2028.md`. If 2028 class shape resolves favorably during 2026 college season, this weight gets revised up.

### 2.3 Player-as-Currency Caveat (35% Qual Lane)

Player E27 weights (the bottom rows) are the **single largest qual-injection point** in this layer. They depend on:
- the receiving player's age vs. position cliff
- our roster need
- the parent strategy's roster-window gate

**Any trade where player-as-currency contributes >25% of total return must be flagged `qual_dominant_override=true`** in the trade record (per `2027_pick_accumulation.md` §5.3 and Codex's `qual_dominant_override` column).

---

## 3. The Points-for-Picks Conversion Ratio

PM directive: "For every 10 PPG of 2026 production liquidated, we must return a minimum of 1.5 'Projected Early 2027 1st' units."

### 3.1 Why This Ratio Needs Calibration

The PM example (1.5 early 2027 1sts per 10 PPG) translates to **2.25 E27 per 10 PPG liquidated**. Applied directly:

| Player | Projected 2026 PPG (PPR) | Implied E27 floor | Comparison to parent strategy floor |
|---|---|---|---|
| Adams (age 33, post-cliff WR1 production) | ~14 (regression-adjusted from 2025) | **3.15 E27** | Parent floor: 0.30–0.55 E27. **6–10× higher than parent.** |
| Taylor (age 27, RB1 ceiling) | ~17 (cliff-uncertainty-adjusted) | **3.83 E27** | Parent floor: 1.10 E27. **3.5× higher than parent.** |
| Hill (age 32, FA + ACL recovery) | ~8 (heavy discount for medical) | **1.80 E27** | Parent floor: 0.20–0.40 E27. **4.5–9× higher than parent.** |

**The PM ratio is materially richer than the dynasty market actually pays for these veteran archetypes.** Holding to it strictly would mean rejecting every realistic offer and holding the assets through their decay curves — which *defeats the strategy's mission*.

### 3.2 Recommended Ratio (proposed for PM approval)

Replace flat "1.5 early 1sts per 10 PPG" with a **position-and-age-weighted ratio**:

```
Required E27 return ≥ Base_PPG_Conversion × Position_Multiplier × Age_Multiplier × Health_Multiplier
```

Where:
- **Base_PPG_Conversion** = `(projected_2026_PPG / 10) × 0.50 E27` *(a far more market-realistic anchor than 2.25)*
- **Position_Multiplier:** WR = 1.0; RB = 1.2 *(RB cliff is steeper, command a premium)*; QB = 0.85 *(SF QB depth dilutes single-asset premium)*; TE = 1.1
- **Mobile_QB_Multiplier (applied multiplicatively to QB position weight only):** Rushing TDs ≥ 8 in most recent verified season: **×1.15**; Rushing TDs ≥ 5: **×1.08**; Rushing TDs < 5: **×1.00**. Rationale: documented rushing-TD volume reduces QB scoring variance — a quant-grounded floor signal, not a points-equivalence claim. Empirically, rushing-floor QBs have narrower week-to-week SD in fantasy points than pure pocket QBs at comparable yardage volumes. Calibration is conservative pending Engine B backtest. *Applies to acquisition pricing on rushing QBs (e.g., Manning at 10 rush TDs → ×1.15) and to liquidation floors on aging QBs who have lost rushing volume.*
- **Age_Multiplier:** Age ≤ 25: 1.5 / Age 26–28: 1.2 / Age 29–30: 1.0 / Age 31–32: 0.75 / Age 33+: 0.55
- **Health_Multiplier:** Healthy: 1.0 / Soft-tissue history: 0.85 / Major surgery within 12 months: 0.55

### 3.3 Worked Examples (Recommended Ratio)

| Player | Calculation | Required E27 Return | Parent Floor | Verdict |
|---|---|---|---|---|
| Adams | (14/10) × 0.50 × 1.0 × 0.55 × 1.0 | **0.39 E27** | 0.30–0.55 E27 | **Aligned with parent** ✓ |
| Taylor | (17/10) × 0.50 × 1.2 × 1.2 × 1.0 | **1.22 E27** | 1.10 E27 | **Aligned with parent** ✓ |
| Hill | (8/10) × 0.50 × 1.0 × 0.75 × 0.55 | **0.17 E27** | 0.20–0.40 E27 | Parent floor binds (slightly higher); **use parent floor** |

The recommended ratio produces required-returns that *match or sit just under* the parent strategy's pricing floors — meaning the floor remains the binding constraint while the ratio provides a defensible *secondary check* on whether an offer's PPG-equivalence is rational.

### 3.4 The Decision Rule

**Accept an offer if:**
1. Total E27 return ≥ Parent strategy floor for that asset (`2027_pick_accumulation.md` §2.3), AND
2. Total E27 return ≥ Recommended-Ratio required return (§3.2), AND
3. Hard exit triggers (parent §2.4) have not flipped the asset to forced-sell mode (in which case condition 1 is the only floor — distressed assets accept distressed prices).

**Reject and counter** if condition 1 fails. **Accept the parent floor** if condition 2 fails but condition 1 holds — the parent floor is the ground truth.

**Forced-sell override:** if the asset has tripped a hard exit trigger (injury, FA limbo, trade rumor), Decision Rule reduces to "accept the best offer received within 72 hours, even below floor." The strategy's logic explicitly acknowledges that ungovernable events override our pricing discipline. This is in §2.4 of the parent strategy and is non-overridable here.

---

## 4. Counter-Argument (Rule 5 — Mandatory)

1. **Currency-weight calibration is opinion-driven until backtested.** The E27 weights in §2 are anchored to the parent strategy's floors — which are themselves heuristic. A circular calibration. Until Engine B ingests realized trade outcomes, this layer's precision is illusory. **Mitigation:** flag every executed trade with the E27 calculation used and the realized outcome 12 months later. Codex's `roster_valuation_signals` audit columns enable this.

2. **The recommended ratio (§3.2) is *less* aggressive than the PM directive.** That is intentional — the PM ratio fails the market-reality check (§3.1). But it also means the strategy will accept lower returns than the PM may have anticipated. **Risk:** the PM may want to formally approve the ratio change before it gates real trades. This document does not assume that approval — it surfaces the recommendation.

3. **Player-as-currency weights (§2.3) are the strategy's largest hidden risk.** When a counterparty offers "pick + player," the player half is where deals get won or lost in retrospect. The 0.10–0.25 E27 weights are conservative but not validated. **Mitigation:** the `qual_dominant_override` flag triggers on >25% player-as-currency contribution, forcing manual review.

---

## 5. Open Items for Codex / Sprint 3

- The `qual_dominant_override` and `qual_rationale` columns approved in PM Memo §II.1 are the storage substrate for §3.4 decision audits. Recommend the column added to `roster_valuation_signals` also reference `e27_required` and `e27_offered` numerics so retrospective analysis has the math, not just the flag.
- Market-Lag Calibration (PM Memo §II.2): the "Priority Exploit" label for assets where KTC has not yet adjusted for cliff status maps directly to the strategy's "stretch target" pricing in parent §2.3. When KTC live integration ships, the trade-execution layer should auto-route Priority Exploit assets to stretch-target asks rather than floor asks.

---

## 6. Sources

- Davante Adams 2025 production: [ESPN gamelog](https://www.espn.com/nfl/player/gamelog/_/id/16800/davante-adams)
- Tyreek Hill release + ACL status: [CBS Sports — Dolphins release Hill](https://www.cbssports.com/nfl/news/tyreek-hill-released-dolphins-wr-contract/), [ESPN — why the Dolphins cut Hill](https://www.espn.com/nfl/story/_/id/47948025/miami-dolphins-cut-tyreek-hill-answering-biggest-questions-injury-whats-next)
- Arch Manning 2025 rushing: [season review](https://atozsports.com/college-football/texas-longhorns-news/arch-manning-2025-season-review-stats-signature-games-and-key-takeaways/), [Citrus Bowl recap](https://sports.yahoo.com/college-football/breaking-news/article/arch-manning-totals-4-touchdowns-as-no-13-texas-beats-no-18-michigan-in-citrus-bowl-235818032.html)
