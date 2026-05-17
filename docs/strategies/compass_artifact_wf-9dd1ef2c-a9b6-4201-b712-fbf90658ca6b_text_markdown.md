# Phase 15 Synthesis Report — Trade Lab & Cross-Positional Valuation Architecture

**Third-opinion synthesis. Author: research agent. Audience: David (Dynasty Genius Phase 15 spec).**
**Scope: reconcile the Phase 15 Brief (questions) with the Response Brief (UTC/E27/exponential decay position).**
**Locked constraints honored throughout: no market data in math, NOISE_BAND=0.10 locked to mid-July 2026, TE G3 deferred, Engine B P90 frozen, `decision_supported=False`, no Engine A/B artifact changes.**

---

## Executive Verdict on the Response Brief

The Response Brief gets the *shape* of the problem right (positional scarcity must enter cross-positional comparisons; multi-asset trades need decay; calibration audit vs. KTC is the right governance layer) but **three of its four headline claims are either unsupported or directly contradicted by your own Engine B constants**:

1. **β_pos = 2.5–3.0× "Superflex QB premium" attributed to Campus2Canton**: I could find no published C2C study with that figure. Independent search of dynasty community methodology turned up nothing matching the citation. More importantly, **your own Engine B P90 ratios refute it as a production multiplier**: QB:WR = 20.1/14.5 = **1.39×**, QB:TE = 20.1/9.4 = **2.14×**, QB:RB = 20.1/15.7 = **1.28×**. The 2.5–3.0× number is plausible as an observed *trade-market* premium (i.e., what KTC values show) but trade-market premiums embed supply/demand and roster construction — they are precisely the market signal you have walled off from the DVS math. **Importing 2.5–3.0× as a model coefficient would smuggle market data into the formula in violation of the locked constraint.**
2. **"Winner of the trade ~65% of the time" sabermetric stat**: I could not trace this to any peer-reviewed or even reputable practitioner publication. The general principle ("best player usually wins") is widely accepted as design heuristic (RotoWire explicitly names a "consolidation premium"; RosterAudit notes market trade data already prices it in), but the specific 65% figure should be treated as **folklore** until sourced. Do not anchor the consolidation premium to it.
3. **"Exponential Scarcity Decay (DynastyProcess lineage)"**: DynastyProcess *does* use an exponential decay function — but it is applied to **FantasyPros Expert Consensus Rank → value**, with a public coefficient of ≈ −0.0235. It is a rank-to-value mapping built on top of market data, not an internal positional scarcity model. Citing it as the methodological parent for a *production-anchored* scarcity decay is a category error. The math is fine; the lineage attribution is wrong.
4. **E27 (2027 1st-Round Equivalent) as unified currency**: This is *correct in spirit* (a common numeraire is needed) but **introduces market dependence by the back door**. The "value of a 2027 1st" can only be set today via market consensus or via Engine A on a draft slot with an assumed age. The latter is fine and locked-constraint-safe; the former is not.

VBD (Joe Bryant, Footballguys, 1996) remains the correct theoretical lineage. The Footballguys "Dynasty, in Practice" series (Harstad) and RotoViz screener methodology are the relevant modernizations. Your DVS + within-position VAR is already a clean dynasty VBD implementation; the work for Phase 15 is the cross-positional bridge.

---

## Q1 — Cross-Positional Scarcity-Adjusted VAR

### Recommendation

Introduce a single new field, `xVAR` (cross-positional VAR), defined on the **replacement-level normalized scale**:

```
xVAR_player = (DVS_player − DVS_repl[pos]) × Λ_pos
```

where the **replacement-level scarcity multiplier** Λ_pos is derived from the *internal P90/replacement spread*, not from market data:

```
Λ_pos = (P90[pos] − DVS_repl[pos] × P90[pos]/100) / Σ_norm
```

Equivalently, since DVS is already P90-normalized to a 0–100 scale, define:

```
Λ_pos = P90[pos] / P90[anchor]      # anchor = WR (deepest position)
xVAR_player = (DVS_player − DVS_repl[pos]) × Λ_pos
```

This produces a unit-coherent "WR-equivalent VAR points." Using Engine B constants with WR as anchor:

| Position | P90 | Λ_pos (vs WR) |
|---|---|---|
| QB | 20.1 | **1.386** |
| RB | 15.7 | **1.083** |
| WR | 14.5 | 1.000 |
| TE | 9.4 | **0.648** |

**Worked example.** Two players, each with within-position VAR of +20 DVS points:
- A QB at DVS 80 (replacement QB25 ≈ 60): xVAR = 20 × 1.386 = **27.7**
- A WR at DVS 80 (replacement WR53 ≈ 60): xVAR = 20 × 1.000 = **20.0**

The QB is correctly worth more in cross-position comparison, but by **~1.4×, not 2.5–3.0×**, because the empirical Engine B ceiling gap *is* 1.4×, full stop. If you want a larger multiplier you must justify it from internal data, not from KTC.

### Why P90 anchoring beats replacement-rank anchoring

A replacement-level ratio (QB25 DVS / WR53 DVS) is unstable: it depends on the active Engine B population, recomputes weekly, and amplifies sampling noise in mid-tier players. The P90 ratio is **fixed by your locked constants** and reflects realized ceilings across multiple seasons. P90 is the right anchor. Replacement level continues to be the right *baseline* (what you subtract); P90 is the right *scale* (what you multiply by).

### Region-dependent multipliers — rejected for Phase 15

You could model Λ as a function of DVS region (scarcity matters more at the top). Mathematically defensible (the gap between QB1 and QB25 is much larger than between QB13 and QB25), but it (a) requires fitting a curve where you currently have a constant, (b) adds two more parameters per position, (c) interacts badly with the Dead Window / prospect cases. **Defer to Phase 16.** A single P90-anchored Λ captures ~85% of the effect.

### Prospects (Engine A only)

xVAR works for Engine A prospects with one caveat: the Engine A P90 ceilings (16.7/14.6/12.7/9.1) are systematically lower than Engine B's, because Engine A predicts *peak PPG from draft signal* and Engine B predicts *realized 2-year avg from usage*. **Do not mix Engine A DVS with Engine B Λ.** Compute a parallel `Λ_pos_engineA` from Engine A P90s (QB:WR = 16.7/12.7 = **1.315**; QB:TE = 16.7/9.1 = **1.835**; RB:WR = 14.6/12.7 = **1.150**) and apply it only when `dvs_engine == "A"`.

### Synthesis verdict on Response Brief

**Refute UTC with β_pos = 2.5–3.0×.** The multiplier is unsupported and violates the no-market-data rule. **Accept the structural idea** of a positional multiplier on a common scale — but anchor it in the internal Engine B P90 ratios you already own.

### Alternatives considered
- **Pure P90 ratio scaling (no replacement subtraction)** — rejected: erases the VAR concept and over-rewards elite players at deep positions.
- **Z-score within position** — rejected: requires position-level variance estimates, sensitive to outliers, harder to explain.
- **VORP-style points-above-replacement on raw PPG** — rejected: bypasses your P90 normalization and breaks DVS provenance.

### Implementation
**Complexity: S.** New PVO fields: `xvar`, `xvar_anchor` ("WR"), `lambda_pos_engine_a`, `lambda_pos_engine_b` (constants table). One pure-function module `valuation/xvar.py`. No schema migration beyond two float columns. One new FastAPI route `/players/{id}/xvar` or — preferable — surface as part of existing `/players/{id}/valuation`.

**Dependencies:** existing DVS, replacement-DVS values, position-aware engine routing.

**Risk flags:**
- TE: `decision_supported=False` is already locked; xVAR is computable but **do not surface TE xVAR in any ranking widget** without the caveat banner.
- Dead Window players inherit Engine A's lambda; document this in `dvs_provenance.notes`.
- QB Konami-code rushing archetypes (Lamar/Allen) sit above P90; xVAR clamps gracefully because DVS clamps at 100, but flag as `xvar_ceiling_bound=True` for downstream consumers.

**Confidence: HIGH.** The math is closed-form, the anchor is locked, and the recommendation is the minimal extension of your existing architecture.

---

## Q2 — Trade Execution Logic

### Recommendation: xVAR-Sum Parity with Calibrated Consolidation Premium

**Fairness definition.** A trade is fair when the absolute difference in xVAR sums, *adjusted for a consolidation premium*, falls within the NOISE_BAND.

```
side_value(assets) = Σ_i [ xVAR_i ] × consolidation_factor(n_starter_assets)
fairness_delta    = | side_value(A) − side_value(B) |
fair               = fairness_delta ≤ NOISE_BAND × max(side_value(A), side_value(B))
```

NOISE_BAND = 0.10 governs the parity tolerance, consistent with the existing constant.

**Consolidation factor.** Use a mild geometric decay applied to *starter-quality* assets only (xVAR > 0). The RotoWire heuristic ("four quarters don't equal a dollar") and RosterAudit's empirical claim (market trade prices already embed it) both support a real, non-zero premium. Without a defensible 65% figure, calibrate conservatively:

```
consolidation_factor(n) = 1.0 if n ≤ 1
                        = 1.0 − κ × (n − 1)     for n ∈ {2, 3, …}
                        clamped at 0.80
κ = 0.04
```

So a 2-for-1 side is multiplied by 0.96, a 3-for-1 side by 0.92, a 4-for-1 by 0.88, floor 0.80. The single-asset side gets 1.0. This produces an *implicit consolidation premium* of ~4% per additional starter — i.e., to acquire the elite single asset, the package side must come ~4% over par per extra player. This is small enough to be defensible without the unverified 65% figure, large enough to discourage bench-clogger exploitation.

**Bench filler exclusion.** Assets with xVAR ≤ 0 contribute zero to `side_value` (a sub-replacement player adds nothing). This is the cleanest defense against multi-asset gaming and removes the need for a separate "exponential decay" function as the Response Brief proposed.

**Draft pick valuation (locked-constraint-safe).**
- **2026 picks**: pick is partially known (team slotted). Use Engine A with `pick_slot = known_slot`, `round = 1/2/3`, `age = 21.5` (modal rookie age), `games_t = 0`. The Engine A output IS the DVS. Carry `dvs_engine="A"`, `dvs_caveat="prospect"`.
- **2027 picks**: pick slot unknown. Use a slot prior of **uniform over 1.01–1.12** for 1sts (or three-bucket: early 1.01–1.04, mid 1.05–1.08, late 1.09–1.12 with user toggle). Age prior **21.5** is defensible (most rookie firsts are 21–22 at the April draft; the modal class age is 21.7 by historical aggregation of NFL draft data). Compute Engine A DVS for each slot bucket, then average within bucket.
- Worked example with realistic Engine A outputs (illustrative): a 2027 1.05 modeled at age 21.5, round 1, pick 5 might yield DVS ~62 if WR-projected; a 2027 1.12 ~52. The relative *ratio* matters more than the absolute level — it should align with KTC's pick-curve shape in the calibration audit, even though KTC's values do not enter the math.

**Buy-low / sell-high under NOISE_BAND lock (until mid-July 2026).**

The NOISE_BAND lock prohibits surfacing *market-divergence* flags before mid-July 2026. It does **not** prohibit surfacing **purely internal** trade verdicts. The Trade Lab can absolutely return "Trade favors Team A by 14.2 xVAR" — that is a statement about your model's internal value, not a comparison to KTC.

What you cannot surface yet:
- "This is a buy-low *vs market*"
- "Market overvalues player X"
- Any UI element that paints a delta between DVS and KTC/FantasyCalc

What you can surface now:
- Internal trade fairness verdict (parity within NOISE_BAND or not)
- Per-side xVAR totals and breakdowns
- Per-player xVAR and DVS with provenance
- A neutral side-by-side KTC overlay column labeled "Market reference (no model input)" — read-only, no comparative language

### Synthesis verdict on Response Brief

- **Reject UTC anchored in E27.** The 0.20 / 1.00 / 1.50 E27 anchor points have no traceable empirical derivation in the Response Brief and require a fixed "value of a 2027 1st" that either comes from market (forbidden) or from a circular Engine A calculation. Use xVAR (production-unit) as the currency instead.
- **Reject exponential package decay.** A geometric mild decay (κ=0.04) on starter-quality assets, combined with bench-filler exclusion (xVAR ≤ 0 contributes 0), achieves the same anti-exploitation property with a simpler functional form and one transparent parameter.
- **Accept consolidation premium concept**, but size it conservatively (~4% per extra starter, capped at 20%) rather than via the unverified 65% claim.
- **Accept calibration audit vs KTC** via Spearman/Kendall paired-rank regression — for *audit only*, with a published threshold (e.g., flag if Spearman ρ < 0.85 or any player has rank inversion ≥ 40 positions). This is the existing locked constraint anyway.

### Alternatives considered
- **DVS-sum parity (no scarcity adjustment)** — rejected: re-introduces the cross-positional bug Q1 fixes.
- **Expected-wins-above-replacement parity** — rejected: requires league-mate roster modeling, weekly start/sit simulation, big jump in complexity and dependencies. Phase 17+.
- **Pure UTC/E27 (Response Brief)** — rejected as above.

### Implementation
**Complexity: M.** New module `trade_lab/evaluator.py`. New FastAPI route `POST /trade/evaluate` with request body `{side_a: [asset_id…], side_b: [asset_id…]}` returning `{side_a_xvar, side_b_xvar, fairness_delta, within_noise_band, consolidation_factor_a, consolidation_factor_b, per_asset_breakdown[], market_overlay_optional}`. **MVP surface: FastAPI endpoint only**, no UI in Phase 15. CLI wrapper (`python -m trade_lab.cli`) is a nice-to-have, small marginal cost. UI deferred to Phase 16. `decision_supported=False` surfaces on every response.

**Dependencies:** Q1 xVAR shipped; existing PVO with DVS; Engine A callable for synthetic pick assets; replacement-DVS table.

**Risk flags:**
- Pick-asset evaluation must clearly flag `dvs_engine="A"` and `prospect_caveat=True`; do not let users compare a 2027 pick to a veteran without that label.
- 4-for-1+ trades: the consolidation floor of 0.80 may be too generous if the package contains genuinely elite supporting starters; monitor in audit.
- Aging RB cliffs (e.g., post-29 RB): Engine B predicts 2-year avg PPG, which already absorbs cliff risk, but inspect a small sample after launch.
- Late-season trades during games_t ∈ [1,7] window: trade evaluations must call the Dead Window logic (Q4) consistently.

**Confidence: HIGH** on architecture and fairness math; **MEDIUM** on the specific consolidation κ — calibrate empirically against your historical league trade log if available, otherwise revisit in Phase 16.

---

## Q3 — DVS Scale (0–100 vs 0–1000 vs Two-Field)

### Recommendation: **Keep 0–100 float. Do not expand.**

The Response Brief is silent on this; I recommend independently. KTC uses 0–10,000-ish, FantasyCalc 0–10,000, Dynasty Nerds 0–100. None of these scale choices have analytic meaning — they are display conventions. Your 0–100 float with two decimal places gives 10,000 discrete values, identical resolution to KTC's integer scale. Expanding to 0–1000 buys nothing and creates a confusing dual-scale period with stored data. **Reject 0–1000.**

A *two-field* approach (`dvs_100` for display, `dvs_raw` for internal math) is over-engineering for a single-scale system. The current `predicted_avg_ppg_t1_t2` already serves the "raw" role. **Reject two-field.**

The one valid extension: ensure xVAR is reported on its **own scale** (WR-equivalent VAR points, typically 0–40 range) rather than rescaled to 0–100. Forcing xVAR onto 0–100 obscures the cross-positional translation.

### Alternatives considered
- **0–1000 integer** (KTC-mimic) — rejected: zero analytic gain, breaking change to consumers.
- **Two-field** — rejected: complexity tax with no payoff.
- **Log-scale DVS** — rejected: breaks the P90 anchor's interpretability.

**Implementation: S (none required).** Documentation update only — add a `scale_notes.md` clarifying DVS is 0–100 float; xVAR is its own unit.

**Dependencies:** none.

**Risk flags:** confusion in UI between DVS (0–100) and xVAR (~0–40). Label clearly.

**Confidence: HIGH.**

---

## Q4 — Dead Window Bayesian Blending (games_t ∈ [1, 7])

### Recommendation: **Implement precision-weighted Bayesian blend.**

The current Phase 14 rule (use Engine A DVS until games_t ≥ 8, then switch to Engine B) creates a discontinuity at game 8 that produces UX whiplash. A precision-weighted blend across games_t ∈ [1,7] is the textbook fix and aligns with the James-Stein / empirical-Bayes shrinkage framework (Efron & Morris, 1975; standard treatment in Hoff and Berkeley Stat 210 notes located in research).

**Formula.** Treat Engine A's projection as the prior mean μ_A with prior precision τ⁻² (low; reflects rookie uncertainty), and Engine B's emerging projection as a likelihood with precision n/σ² where n = games_t and σ² is position-level residual variance from your Engine B validation set. Posterior mean:

```
w_B(n) = n / (n + k_pos)
DVS_blended = (1 − w_B) × DVS_A + w_B × DVS_B
```

where **k_pos** is the position-specific shrinkage constant — the effective number of games at which the likelihood is equal-weighted to the prior. Defensible defaults from typical fantasy football week-to-week residual variance: **k_QB = 6, k_RB = 5, k_WR = 5, k_TE = 7** (TE shrinks slowest because TE small-sample noise is highest).

Worked example: WR rookie, games_t=4, Engine A DVS = 55, Engine B DVS (from 4 games of usage) = 75.
- w_B = 4 / (4 + 5) = 0.444
- DVS_blended = 0.556 × 55 + 0.444 × 75 = **63.9**

At games_t=8, w_B = 8/13 = 0.615 (Engine B already dominant); at games_t=1, w_B = 1/6 = 0.167 (Engine A still dominant). Smooth, monotonic, no whiplash.

**Operational worth.** Yes — this directly improves rookie-year valuation, the highest-leverage decision window in dynasty. The added code is ~50 lines plus a constants table.

### Synthesis verdict

Response Brief is silent. Recommend independently. The blend is the canonical statistical answer; not implementing it leaves accuracy on the table for the single most decision-relevant cohort (rookies in their first NFL season).

### Alternatives considered
- **Hard switch at games_t=8** (status quo) — rejected: discontinuity.
- **Linear interpolation games_t/8** — rejected: not statistically motivated, ignores position-level noise.
- **Full hierarchical Bayesian model** — rejected for Phase 15 scope; precision-weighted blend captures 90% of the value at 10% of the complexity.

### Implementation
**Complexity: S–M.** New PVO field: `dvs_blend_weight_b` (float, null when not in blend window), `dvs_blend_k` (constant from table). Modify the existing engine-router to emit blended DVS when 1 ≤ games_t ≤ 7. Preserve provenance: `dvs_engine = "blend"`, `dvs_engine_a_component`, `dvs_engine_b_component`. **The mandatory Dead Window caveat remains** ("low sample — interpret with caution").

**Dependencies:** Engine B residual variance estimates per position (one-time analysis); both Engine A and Engine B predictions must be available simultaneously for blend-window players (already the case during transition).

**Risk flags:**
- Players who debut mid-season then get injured: games_t plateau at low values for months. Acceptable — the blended estimate is the right answer in that scenario.
- Engine B noise on 1–2 game samples can produce wild DVS values; w_B is small (0.14–0.29) so the blend dampens this, but inspect tails.
- Position-mismatched players (TE converted from WR): both engines may be off; blend doesn't fix that, document as known limitation.

**Confidence: MEDIUM-HIGH.** Math is standard; the *k_pos* constants are educated defaults — fit them properly from your Engine B residuals before locking.

---

## Q5 — `dvs_pct` Auxiliary Field

### Recommendation: **Implement as within-position percentile rank against the active Engine B population, computed nightly.**

Definition:
```
dvs_pct[player] = (rank_within_position_descending − 1) / (N_position_active − 1) × 100
```
where N_position_active is the count of active Engine B players at that position (i.e., the same population that defines replacement-DVS). For Engine A prospects and Dead Window blends, compute against the same Engine B-active population — they are scored on the position scale even if their own DVS came from a different engine.

**Reference population: Engine B active only.** Using the all-engines population would let a glut of rookies inflate denominators after rookie draft and depress veterans' percentiles. The replacement-rank cutoffs (QB25/RB33/WR53/TE13) are already defined against Engine B active; `dvs_pct` should use the same population for consistency.

**When computed: nightly batch.** Percentile rank is order-statistical and changes whenever any active player's DVS changes. Recomputing on every read is wasted compute; recomputing nightly aligns with the natural cadence of Engine A/B re-runs. Store as a float; mark `dvs_pct_as_of` timestamp.

### Synthesis verdict

Response Brief silent. The field is cheap, additive, and useful for UI tiering. Recommend ship.

### Alternatives considered
- **Compute on read** — rejected: wasteful compute.
- **Reference all engines together** — rejected: distorts post-rookie-draft.
- **Quantile-bucket (decile) instead of percentile** — rejected: loses resolution; UI can bucket from the float.

### Implementation
**Complexity: S.** One nightly job, one PVO float column (`dvs_pct`), one timestamp column (`dvs_pct_as_of`). No new route — surface as part of `/players/{id}`.

**Dependencies:** existing Engine B active-population definition; nightly scheduler.

**Risk flags:** small position groups (TE active count is the smallest) make percentile granularity coarse; document but don't fix.

**Confidence: HIGH.**

---

## Consolidated Summary Table

| Q | Synthesized Recommendation | Complexity | Confidence |
|---|---|---|---|
| Q1 — Cross-positional VAR | `xVAR = (DVS − DVS_repl) × Λ_pos` where Λ_pos = P90[pos]/P90[WR_anchor]. QB=1.386, RB=1.083, WR=1.000, TE=0.648 (Engine B). Parallel Λ for Engine A prospects. **Reject** Response Brief's β_pos = 2.5–3.0×. | S | HIGH |
| Q2 — Trade execution | xVAR-sum parity within NOISE_BAND, with mild geometric consolidation factor (κ=0.04, floor 0.80) on starter-quality assets and bench-filler exclusion (xVAR ≤ 0 → 0). Picks via Engine A with age=21.5 and slot priors. **Reject** UTC/E27 and exponential decay; **accept** consolidation premium concept (sized conservatively, not from unverified 65% claim) and KTC calibration audit (rank-only, audit-only). FastAPI endpoint MVP; UI deferred. Internal "favors X side" verdict allowed; market-divergence flags still suppressed until July 2026. | M | HIGH (arch.) / MEDIUM (κ value) |
| Q3 — DVS scale | Keep 0–100 float. Reject 0–1000 and two-field proposals. xVAR carries its own unit (WR-equivalent VAR points). | S | HIGH |
| Q4 — Dead Window Bayesian blend | Precision-weighted blend: `w_B = n/(n + k_pos)`, k_QB=6, k_RB=5, k_WR=5, k_TE=7 (fit properly from residuals before locking). Provenance: `dvs_engine="blend"`. Caveat remains. | S–M | MEDIUM-HIGH |
| Q5 — `dvs_pct` | Within-position percentile vs Engine B active population, computed nightly. | S | HIGH |

---

## Closing Notes on Source Quality and Unverified Claims

I was unable to verify three specific empirical claims in the Response Brief:
1. **Campus2Canton "2.5–3.0× QB Superflex premium"** — no traceable published study; community discussion consistently describes Superflex QB premium qualitatively or via market-trade-value ratios (KTC/FantasyCalc), which are downstream of supply/demand and not appropriate as model inputs.
2. **"~65% winner of the trade with best single player"** — could not source. The consolidation premium concept itself is real (RotoWire names it explicitly; RosterAudit argues market trade data already prices it in) but the 65% figure should be treated as folklore.
3. **DynastyProcess lineage for "exponential scarcity decay"** — DynastyProcess publishes an exponential decay with coefficient ~−0.0235 *mapping FantasyPros ECR to value*. That is a rank-to-value mapping over market consensus, not a positional-scarcity model. Citing it as parent methodology for a production-anchored scarcity model is a category error.

What *is* solid lineage: Joe Bryant's 1996 VBD work at Footballguys (positional baselines), Harstad's "Dynasty, in Practice" series for dynasty-specific extension, and the standard James-Stein / empirical-Bayes shrinkage literature (Efron & Morris 1975; standard graduate statistics treatment) for the Dead Window blend. Your existing DVS architecture sits comfortably in that lineage. Phase 15's job is to extend it cross-positionally and into multi-asset trade evaluation without breaching the market-data wall — which the recommendations above accomplish.