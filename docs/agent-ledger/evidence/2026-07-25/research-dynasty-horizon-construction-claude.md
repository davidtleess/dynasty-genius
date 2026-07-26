# Dynasty-Horizon Value — CONSTRUCTION research (Claude lane)

**Author:** Claude Code · **Date:** 2026-07-25 · **Status:** research + design-space survey.
**Not a decision, not a plan, not code.** No convergence sought with Codex or Gemini — Tower diffs the three.

**Authority:** David's rulings `/tmp/tower_david_rulings_2026-07-25.md`, read in full. Ruling D.1 binds:
no redraft comparison; the only permitted direction is a dynasty-horizon value on our own side.
Ruling F binds: dynasty-horizon value is the core; the contention window is a lens over it.

**Verification legend.** **[VERIFIED]** = read in the repo this session, locator given.
**[ARGUED]** = my reasoning, falsifiable, no locator. **[UNKNOWN]** = I do not know; what would settle it is stated.

---

## §0 Headline — the premise the whole diagnosis rests on is WRONG as relayed

Tower told David that xVAR is "roughly current-season," taken on trust from an outside report.
**That is false against the code.** This is item 6, and I put it first because it changes what the
rest of the work is for.

**[VERIFIED] xVAR is a TWO-SEASON-FORWARD, age-aware, undiscounted flat mean.** The chain:

| Step | Locator | What it is |
|---|---|---|
| Engine B training target | `models/engine_b_contract.py:15` | `OUTCOME_COLUMN = "avg_ppg_t1_t2"` |
| Model output | `pvo_assembler.py:382` | `projection_2y = engine_b_resolved["predicted_avg_ppg_t1_t2"]` |
| DVS | `pvo_assembler.py:405,407` | `dvs_raw = projection_2y / P90_B * 100`, clamped to `[0,100]` |
| xVAR | `pvo_assembler.py:487` | `xvar = (DVS − replacement_DVS) × Λ_pos` |

Corroborated in the design record: *"Output: `predicted_avg_ppg_t1_t2` — predicted PPG average over
next 2 seasons"* (`docs/strategies/Dynasty Genius Phase 14 Research Brief.md:46`).

**[VERIFIED] The projection is already age-aware.** `age` and `aging_curve_value` are model inputs
for every position (`engine_b_contract.py:153-157`, `ENGINE_B_BASE_FEATURES`), and the fitted curve
is a real piecewise ascent/plateau/decline multiplier (`models/aging_curves.py:7-9,26-48`).

### What this does and does not do to the age-artifact diagnosis

**It kills the stated mechanism.** "We measure now, the market prices the future, so age reads as
opportunity" is not what the code does. Our side is already a forward, aging-aware quantity.

**It does not clear the artifact.** [ARGUED] The mismatch survives in a different and more precise
form — **horizon length and shape**, not now-vs-future:

1. **Length.** Ours is a 2-season window. A dynasty market price capitalises the whole remaining
   career (plausibly 8–15 seasons for a 23-year-old). A 30-year-old with two strong seasons left and
   a 23-year-old with two strong seasons *plus eight more* receive **identical** `projection_2y`,
   hence identical DVS and identical xVAR. The 23-year-old's extra seasons are invisible to us and
   fully visible to the market. **That reproduces exactly the observed signature** — we "like" the
   older player, because the thing that distinguishes them is outside our window.
2. **Shape.** Ours is a flat *mean* of two seasons, so it carries no discounting, no survival, and
   no within-window ordering. A player worth 20/5 and one worth 5/20 across t+1,t+2 are identical
   to us and are not identical to a contender.
3. **Ceiling compression.** [VERIFIED] DVS is clamped at 100 (`pvo_assembler.py:407`). Elite upside
   is truncated *before* xVAR is computed, and the young/elite side is where truncation bites. This
   is the previously-named PVO-scale ceiling problem sitting underneath the age artifact — the two
   are plausibly the same defect seen twice. [ARGUED]
4. **Static replacement.** [VERIFIED] Replacement DVS baselines are "Frozen at May 2026 values. Do
   NOT refresh dynamically" (`engine_b_contract.py:70-73`). xVAR is measured against a fixed bar
   while the market re-prices continuously.

**Consequence for Ruling D.** The diagnosis should be rewritten from "current vs future" to
"**2-season window vs whole-career capitalisation, plus a truncated ceiling and a frozen bar**."
The remedy direction (build a dynasty-horizon value on our side) is unchanged and still correct.
The *magnitude* claim in the Studio report is [UNKNOWN] to me — I did not re-measure the 8-of-14
figure. What would settle it: recompute the divergence top-N with age bucketed, on the current
artifact, after correcting the horizon description.

**Honest note against my own finding:** a 2-season forward mean is nearer to a dynasty quantity than
"current-season," so if anyone argued the artifact must therefore be small, that is not established
either. Direction is argued; size is unmeasured.

---

## §1 Candidate mathematical FORMS (no winner pre-selected)

Notation: player *i*, season index *t = 1…T* from now. `v_{i,t}` = value contributed in season *t*
(in some unit — PPG-above-replacement, xVAR-equivalent, or wins). `S_{i,t}` = probability the player
is still *useful* in season *t*.

### A. Per-season projected stream with explicit discount
`V_i = Σ_t d_t · S_{i,t} · E[v_{i,t}]`

- **Expresses:** any window (partial sum), pick value (stream starting at debut), the
  ranking-inversion property David wants, and per-season narrative ("year 3 is where he passes him").
- **Cannot express:** path dependence (value of a title *won*, not points accumulated); manager-state
  interactions; option value of trading mid-stream. It is additive by construction.
- **Data demanded:** a per-season projection out to T. We have T=2 as one blended number. **This is
  the single largest data gap in the whole survey.**
- **Validated by:** per-season realized PPG at each horizon, calibration by (age, position, horizon);
  and the summation property must be checked, not assumed — `V(1..5)` vs `V(1..2)+V(3..5)`.
- **Fails by:** compounding projection error at long horizons; a fabricated per-season shape that
  looks like resolution the data cannot support (the same failure the pick-curve baseline showed —
  n=8 per slot, monotonicity violated 15/35); and by making the discount rate carry meaning it
  cannot bear (§3).

### B. Single-scalar composite (today's shape, extended)
One number per player, e.g. DVS/xVAR fit against a longer target.

- **Expresses:** ranking, trade balance, a market comparison. Cheapest by far; it is what exists.
- **Cannot express:** the window lens *at all* without a second construction, and cannot price a pick
  whose value begins in a future season. Ruling F's inversion property is unreachable.
- **Data demanded:** almost none beyond a longer training target (`avg_ppg_t1_t5`, say).
- **Validated by:** the existing backtest machinery, unchanged.
- **Fails by:** exactly the failure being diagnosed today — a horizon mismatch that is invisible
  because the horizon is baked into a constant.

### C. State-transition / simulation (Markov or micro-sim)
States like {elite starter, starter, committee, backup, out}, with age/usage-conditioned transitions;
value accrues per state per season; simulate many paths.

- **Expresses:** role loss and recovery, breakout *and* collapse, full outcome distributions (so
  P(top-5 season in my window) is directly available), and correlations if simulated jointly.
- **Cannot express:** cheaply — it is the most expensive to build, calibrate, and explain. Also
  hardest to keep honest: a simulator produces confident-looking distributions from assumed
  transitions.
- **Data demanded:** state labels per player-season (derivable from snap_share/games — we have the
  inputs) and transition counts by age/position. Plausibly the *most* achievable rich model on
  current data, because transitions need only historical panel data, not future projections. [ARGUED]
- **Validated by:** transition-matrix backtesting on held-out seasons; calibration of predicted state
  distributions vs realized.
- **Fails by:** state definitions being arbitrary; sparse cells at old ages; and simulation variance
  being mistaken for real uncertainty.

### D. Option-pricing / contingent-claim
Treat a player (or pick) as a claim with optionality: draft-and-cut, trade, stash.

- **Expresses:** precisely the three things Ruling A demands a pick price must include — the
  draft-and-cut floor, the trade-value floor, the rookie-as-chip option. It gives a *principled*
  reason a pick cannot be negative: value = max(keep, trade, cut) ≥ 0.
- **Cannot express:** a defensible "price" without a traded underlying and a volatility estimate.
  There is no risk-neutral measure in a 12-team league; Black–Scholes machinery is not transferable.
  [ARGUED] What survives is the *max-of-alternatives* logic, which is real and cheap.
- **Data demanded:** for the qualitative floor, nothing. For actual pricing, a distribution of
  outcomes (which is form C) plus a liquidity model.
- **Validated by:** whether realized decisions (cuts, trades) fall where the option boundary predicts.
- **Fails by:** importing finance vocabulary that implies precision we do not have. **[ARGUED] This
  form is probably right as a *floor and framing layer over* another form, not as the value engine.**

### E. Survival-based expected career value
`V_i = Σ_t S_{i,t} · E[v_{i,t} | alive]` — i.e. form A with the survival term promoted to first class
and *no* discount rate.

- **Expresses:** the honest reason far-future seasons are worth less — the player probably will not
  be useful — rather than an invented interest rate. **[ARGUED] This is the technically important
  point of the whole survey:** if `S_{i,t} → 0` fast enough, the infinite sum **converges without any
  discount factor at all**. Ruling F's "discounted sum across all remaining seasons" may not need a
  discount rate to be well-defined.
- **Cannot express:** manager time preference or contention urgency — deliberately. Those move to the
  window (§3).
- **Data demanded:** a survival/hazard model (§4) plus conditional-on-alive value.
- **Validated by:** survival calibration (predicted vs realized attrition by age/position) separately
  from value calibration — a real advantage, two independently checkable halves.
- **Fails by:** censoring handled wrongly; "useful" being defined circularly from the same value
  measure; and by survival-conditional value being estimated on survivors only (survivorship bias).

### F. Direct multi-horizon regression (horizon-indexed targets)
Fit a family `V_i(k)` = realized value over the next *k* seasons, one model per horizon *k*
(or one model with *k* as an input), trained directly against realized k-season outcomes.

- **Expresses:** any *contiguous-from-now* window directly, with each horizon validated against its
  own realized target. No discount assumption, no survival model, no per-season decomposition.
- **Cannot express:** windows not starting now (so **picks remain unpriceable**, which is fatal to
  one of the three features), and it gives no internal consistency guarantee.
- **Data demanded:** only longer realized outcome windows — which is a *data-availability* question,
  and on the pick thread the mature-cohort ceiling was measured at **n=9** (2015–2023). Long-horizon
  targets shrink the usable sample fast. [VERIFIED for the pick cohort; ARGUED that it generalises.]
- **Validated by:** directly, per horizon. Cleanest validation story of any form here.
- **Fails by:** horizon proliferation, inconsistency between horizons, and sample starvation at long *k*.

### G. Hybrid actually worth naming: **survival-weighted stream with a two-parameter shape**
Form E for the engine; form D as a floor/framing layer for picks; form F as the **validation
benchmark** for the summed windows. [ARGUED] I am naming this because §2 requires me to hold the
per-season-stream claim to account, not because it is a recommendation.

---

## §2 ATTACK on Tower's claim

**Tower's claim (to David, now a HARD DESIGN REQUIREMENT in Ruling F):** value must be built as a
per-season stream, because that one construction yields dynasty value, the contention window, and
pick value as three summations.

**Where it is true.** The summation property is real: if a credible per-season stream exists, all
three features *are* range queries over it, and the ranking-inversion property falls out for free.
That is a genuine architectural elegance, and Ruling F's warning is correct that a scalar makes the
window a rewrite.

**Where it breaks — five places, and I think at least three are serious.**

1. **It assumes the decomposition is identifiable. [ARGUED — my strongest objection.]** A per-season
   stream has T free quantities per player. Our current model produces **one** number for two seasons
   (`avg_ppg_t1_t2`) and `projection_1y` is **hardcoded `None`** (`pvo_assembler.py:517` [VERIFIED]).
   Splitting even *two* seasons is not a modelling refinement — it is a target we have never fit. For
   T=8 we would be asserting eight numbers where the data may support two. This is precisely the
   failure the pick-curve baseline exhibited: 36 free per-slot parameters from 288 noisy observations,
   monotonicity violated in 15 of 35 adjacent pairs — *resolution that looks like signal*. A stream
   invites the same error at greater scale and with more authority.
2. **Additivity is an assumption, not a fact.** A championship is a threshold event, not a sum. Two
   seasons of 18 PPG and one of 36 are not interchangeable to a contender. The stream is exactly the
   form that *cannot* express that, and it is the form being mandated to serve the contention lens.
3. **Pick value needs more than the stream.** Ruling A requires a pick price to include draft-and-cut,
   pick trade value, and the rookie-as-chip option. **None of the three is a summation over a
   production stream** — they are optionality and liquidity. So "pick value = the same stream from the
   debut season" is **insufficient by David's own standard in the same document.** The stream gives
   the *expected-production* term only; the floor and the option terms come from form D. [ARGUED]
4. **It bakes in a discount before deciding what a discount means** (§3).
5. **Error compounds and is never validated per-season.** If only the *sums* are checked, a stream
   with badly wrong per-season shape but right totals passes — and then the contention window, which
   reads a *sub*-range, is wrong exactly where it is used. **A stream must be validated at the
   per-season level or the window lens is unvalidated.** This is a concrete, checkable falsifier.

**A construction that serves the window WITHOUT a per-season stream — form F.**
Fit `V(k)` directly against realized k-season outcomes for k ∈ {1,2,3,5}. The window lens is then a
model *query*, not a summation.

- **Better than the stream at:** validation honesty (each horizon checked against its own realized
  target, no per-season fiction); sample efficiency (no decomposition invented); resistance to the
  identifiability failure in point 1.
- **Worse than the stream at:** picks — a pick needs a window *starting in the future*, and form F has
  no such query, which is disqualifying for one of the three features unless paired with something
  else; internal consistency (`V(5) ≠ V(2) + V(3..5)` with nothing forcing agreement); and surface
  narrative (no "which season flips it" story).
- **Honest verdict:** [ARGUED] **worse overall as the single engine, better as the validator.** Its
  right role is as the benchmark the stream's summed windows must match — if the stream's `V(1..2)`
  disagrees materially with a directly-fit `V(2)`, the stream's decomposition is wrong. That is a
  falsifier the stream cannot generate for itself, and I would want it declared before any fit.

**Net:** Tower's claim is **directionally right and over-stated**. The stream is the only surveyed
form that serves all three features from one construction — but it does not do so *for free*, it does
not price picks unaided (point 3, against David's own Ruling A), and it carries an identifiability
risk that must be pre-registered against rather than discovered later.

---

## §3 The DISCOUNT problem

**The core observation.** In dynasty there is no interest rate, no borrowing, no cash. A "discount
rate" imported from finance silently bundles at least five distinct things:

| Bundled component | What it really is | Where it belongs structurally |
|---|---|---|
| Outcome uncertainty | Variance of the projection | **Nowhere in the mean.** An expectation already integrates it. Discounting for it double-counts unless the manager is explicitly risk-averse — which is a *preference*, not a fact. |
| Injury / career end | Probability the player is gone | A **survival term `S_t`**, multiplicative, estimable from data (§4) |
| Role loss / displacement | Probability he is *useless while rostered* | Also survival — of usefulness, not of career |
| Roster-spot scarcity | Opportunity cost of the slot he occupies | A **subtracted rent per season**, not a rate. Ruling C makes this concrete: a taxi promotion costs a roster spot. |
| League turnover / world risk | The league or product may not exist | The **only** component that behaves like a genuine exponential discount, and it is small |
| Manager time preference | "I want to win in the next two years" | **The window** (Ruling F), not a rate |

**[ARGUED] Once decomposed, very little is left for a discount rate to do.** Three of the six belong
in survival, one is a rent, one is a preference that Ruling F already relocates to the window. The
residue is world-risk, which is small and arguably not worth a parameter.

### The real tension David and Tower flagged — options, not a resolution

**If the window expresses time preference, does a global discount double-count it?**

- **Option 1 — Window-only (no discount rate).** `V = Σ_t S_t · (E[v_t] − rent_t)`, summed over the
  chosen window; dynasty-horizon = window "all remaining." Time preference is expressed *entirely* by
  which seasons you sum.
  *For:* no double-counting by construction; every term is separately estimable and separately
  falsifiable; convergence comes from `S_t → 0`, not from an invented rate.
  *Against:* two managers with identical windows but different urgency are indistinguishable; and
  "all remaining" needs a truncation rule or a survival model good enough to make the tail vanish.
- **Option 2 — Discount = uncertainty only, window = preference.** Keep a rate but define it strictly
  as world-risk/estimation-decay, never as impatience.
  *For:* preserves a familiar single-number knob; keeps a smooth tail.
  *Against:* [ARGUED] the moment a rate exists, it will absorb whatever the fitter needs it to absorb.
  A rate is a *sink for unmodelled effects*, and that is exactly how "age reads as opportunity" style
  artifacts get created and hidden.
- **Option 3 — Two explicit parameters.** `δ_hazard` (estimated, from data) and `δ_pref` (manager-set,
  default 1.0, moved by the window UI).
  *For:* names both; makes double-counting visible rather than structural; lets the window and the
  rate be reconciled arithmetically (a 2-season window ≈ some `δ_pref`).
  *Against:* two knobs is one more than most users will reason about; and the mapping between window
  and `δ_pref` is not unique.
- **Option 4 — No aggregation at all at the top.** Report the stream (or the window sums) as a
  *profile*, and refuse a single dynasty number.
  *For:* maximally honest; matches the No-Verdict line; the surface shows a shape, not a verdict.
  *Against:* directly contradicts Ruling F's "dynasty-horizon value remains the core" — David asked
  for a core quantity. Recorded for completeness, not advocacy.

**[UNKNOWN] Which option David wants.** This is a product-values question, not a technical one.
What would settle it: David ruling on whether a single dynasty number must exist alongside the
window, and whether he wants an urgency knob distinct from window choice.

**One thing I would argue hard for regardless [ARGUED]:** whatever is chosen, the discount must not
be *fit*. A fitted discount rate on ~9 usable cohort-years will absorb age effects and become
unfalsifiable. It should be set, declared, and sensitivity-tested across a declared range — the same
discipline the pick plan applies to its margin.

---

## §4 ATTRITION AND SURVIVAL (Tower omitted this entirely)

Any multi-season value needs `P(still useful in season t)`. Without it, a 34-year-old's season-5
projection is a fiction with the same standing as a 24-year-old's.

**Forms available:**

| Form | Fit to our data | Notes |
|---|---|---|
| **Discrete-time hazard** (logistic per player-season) | **Best fit [ARGUED]** | Our data *is* a season-level panel; handles right-censoring naturally; covariates (age, snap_share, games, position) already exist as features |
| Kaplan–Meier by (position, age band) | Easy, non-parametric | No covariates; needs enough players per cell; a good *baseline* and a sanity check |
| Cox proportional hazards | Standard, covariate-rich | Proportional-hazards assumption is testable and likely violated across age; still a strong comparator |
| Parametric (Weibull / Gompertz) | Smooth, extrapolates past observed ages | Extrapolation is the point *and* the risk |
| Markov multi-state (form C) | Richest — models role loss AND recovery | Most expensive; "useful" becomes a state, not a threshold |

**The definitional trap [ARGUED].** "Still useful" must not be defined by the same value measure the
model outputs, or the survival term and the value term are circular. A cleaner definition is
external and observable — e.g. *rostered and playing above a snap/route threshold* — and it should be
declared before fitting, not chosen after seeing which definition helps.

**Survivorship bias [ARGUED].** `E[v_t | alive]` estimated on survivors is biased upward, and the bias
grows with t and age. The survival term does not fix it; it must be estimated on the full cohort
including exits, or the tail is systematically flattering to old players — **which is the same
direction as the artifact under investigation**, so this one matters here specifically.

**[UNKNOWN] Do we have exit/censoring records?** I did not verify whether the training panel
distinguishes "left the league" from "row absent." What would settle it: inspect
`app/data/training/` panel construction for an explicit exit or last-season flag; if absent, exits
must be reconstructed from roster presence across seasons before any survival model is fit.

---

## §5 WHAT WE HAVE vs WHAT IS MISSING

### Have — [VERIFIED] unless noted
- `projection_2y` = `predicted_avg_ppg_t1_t2` — a 2-season forward mean (`pvo_assembler.py:382`).
  **Could seed t=1,2 of a stream, but only as their average — it does not separate them.**
- **`aging_curve_value(position, age)`** — a fitted piecewise ascent/plateau/decline multiplier,
  evaluable at *any* age (`models/aging_curves.py:26-48`). **This is the most under-used asset for
  this problem:** because it is a function of age, it can generate a per-season *shape* for a player
  at ages a, a+1, a+2… without any new model. [ARGUED] It is a shape prior, not a projection, and
  must be labelled as such — it is fitted from data but it is not a forecast of *this* player.
- Position replacement baselines and cross-positional Λ (`engine_b_contract.py:54-88`) — the unit
  machinery a stream would accumulate in.
- Season-level feature panel: `ppg_t`, `ppg_t_minus_1/2`, `snap_share`, `games_t`, `age`
  (`engine_b_contract.py:126-145`) — the substrate for a discrete-time hazard model.
- Forward PIT capture (model + market) accruing since 2026 — the only path to a *native* multi-year
  validation series, and it is young.

### Missing — [VERIFIED] unless noted
- **Any per-season decomposition.** `projection_1y=None` is hardcoded (`pvo_assembler.py:517`).
  There is no t=1 number, and nothing beyond t=2 at all.
- **Any projection past t+2.** The training target stops there (`engine_b_contract.py:15`).
- **Any survival/attrition model.** None found in `src/`. [ARGUED — absence-of-evidence from a
  targeted search, not an exhaustive audit.]
- **Any discount framework.** None.
- **Roster-spot rent / taxi-conversion cost.** Ruling C names it as real; not modelled.
- **Pick optionality** (draft-and-cut, trade value, chip) — Ruling A requires all three; the curve
  contains none (Tower verified this independently in the rulings doc).
- **Headroom above the ceiling.** DVS clamps at 100 (`pvo_assembler.py:407`), so a stream built on
  DVS inherits a truncated top. [ARGUED] Any stream work should be done in an *unclamped* unit and
  the clamp applied only at display, or the ceiling problem propagates into every future season.

**The gap in one line:** we have a 2-season point estimate, an age *shape*, and the accounting units —
and we lack the per-season targets, the survival term, and the time-preference framework that would
turn those into a horizon value.

---

## §6 UNKNOWNs and what would settle each

1. **Magnitude of the age artifact** under the corrected description (2-season window vs career
   capitalisation). → Recompute divergence top-N by age bucket on the current artifact.
2. **What FantasyCalc's dynasty price actually capitalises** (horizon, discount, method). Their
   derivation is unpublished; the 008 thread established only that the generic pick price is the
   exact-slot median. → Cannot be settled from inside the product; treat the market side as an
   unlabelled black box and never fit to it (the standing market wall).
3. **Whether exits/censoring are recoverable** from the training panel (§4).
4. **Whether a per-season decomposition is identifiable at all** on our sample. → Fit `V(1)` and
   `V(2)` directly as separate targets and compare against the existing blended `avg_ppg_t1_t2`; if
   the two-season split is already unstable, T=8 is not available and the stream must be coarse
   (banded seasons) or the mandate revisited.
5. **Whether David wants a single dynasty scalar alongside the window** (§3 Option 4 tension).
6. **Sample ceiling for long-horizon targets.** On the pick cohort it measured n=9 mature years;
   whether the active-player panel is deeper is unverified here. → Count usable player-seasons with a
   full k-season realized outcome, per k.

---

## §7 What I would flag to David before any build (not a plan — a warning list)

1. **The relayed premise was wrong.** Correct the record first: xVAR is a 2-season forward mean, not
   a current-season measure. A thesis built on the wrong diagnosis inherits it.
2. **A stream is a licence to fabricate resolution.** The identifiability check (§6.4) should be a
   *gate before* the stream is adopted, not a finding after.
3. **Pick value needs form D, not just a stream** — by David's own Ruling A, which the Ruling F
   summation story does not satisfy on its own.
4. **Do not fit the discount.** Set it, declare it, sensitivity-test it.
5. **Survivorship bias runs in the same direction as the artifact under investigation.** That
   coincidence deserves explicit falsification, not a footnote.
