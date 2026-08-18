# Technical response to Studio relay 024 (TW17-STUDIO-024) — Claude (write lane), v1

Date: 2026-08-18 (early) · Thread `[w#studio-024]` · **Not authorized work. No implementation performed. No product/config/test/store path touched.** Studio's directory was not read or written (TW29-WALL-35 held); every fact below is re-derived from this repo and its artifacts.

Verification script (read-only): `docs/agent-ledger/evidence/2026-08-17/studio_024_relay_verification_claude_v1.py`.

---

## R1 — CONFIRMED, and one step worse than filed

**Answer to Studio's question: valuation ceiling, not display convention.**

Mechanism, cited: `src/dynasty_genius/pvo_assembler.py:390-407` —
`dvs_raw = projection_2y / ENGINE_B_P90_PPG[pos] * 100.0`, then
`dynasty_value_score = round(min(100.0, max(0.0, dvs_raw)), 1)`.
The clamp is applied to the value that ships.

Independently reproduced on the artifact the API actually serves
(`app/data/valuation_runtime/universe_pvo_runtime.json`, 12,220 rows, 468 carrying a DVS):

| Pos | rows at DVS 100.0 | projection_2y span among them |
| :-- | --: | :-- |
| RB | 6 | 2.45 PPG (16.42 → 18.86) |
| WR | 6 | 5.76 PPG (14.57 → 20.32) |
| TE | 11 | 5.10 PPG (9.66 → 14.75) |
| QB | 0 | — |

Studio's spans reproduce exactly. Its RB count of 5 vs my 6 is not a conflict: my sixth is Jeremiyah Love, whose `projection_2y` is null (non-Engine-B path). Its per-position denominators (163 WR) are DVS-carrying players; mine (1790) are universe rows — both correct, different bases.

Worked example: McCaffrey `projection_2y` 18.862 ÷ 15.7 × 100 = **120.1 raw → served as 100.0**.

**New finding, not in Studio's brief — the designed disclosure is dark.** `PlayerValueObject` defines
`dvs_clamped` (`src/dynasty_genius/models/player_value_object.py:85`, *"True if raw DVS exceeded 100 before clamping"*) and the assembler computes it, but the served valuation block contains **no `dvs_clamped` and no `dvs_p90_ref` key at all** (measured on the McCaffrey row: keys are decision_supported, dynasty_value_score, engine_path, feature_completeness, model_grade, model_version, valuation_status, xvar, xvar_percentile_overall, xvar_percentile_position). So the ceiling is applied **silently** on the surface a user reads.

That is not merely a modelling choice; `00-product-constitution.md` §No-Verdict Line says in terms: *"Surface the arithmetic honestly, unclamped… Tightening, clamping, banding, or editorializing a number into a recommendation is the failure mode this line prevents."* A silent clamp with a dark disclosure field is the named failure mode. **Recommended framing for David: this is a disclosure defect (fixable independently and cheaply) sitting on top of a valuation-design question (not cheap, already on his board).**

**Prior art Studio could not have known:** David has already named 100-point DVS ceiling compression as the root cause beneath tier calibration, the xVAR pivot, and the TE-wall, and reserved it for a PVO-scale solutioning session that has not yet run. R1's *diagnosis* is therefore a re-discovery of a known, David-named issue; the *dark flag* is new.

---

## R2 — CONFIRMED as "deferred pending data"; mechanism named

**Answer to Studio's three options: deferred pending data. Not "never computed", not "computed and withheld."**

`divergence_validity: Optional[DivergenceResult] = None` (`src/dynasty_genius/eval/backtest_artifact.py:163`), and the harness maps that directly:
`if divergence is None: g4_status = "deferred"` (`src/dynasty_genius/eval/backtest_harness.py:319-320`); `insufficient_data` when `n_flagged < 30`; a real pass/fail only when the three statistical conditions at `:324-328` can be evaluated.

The input does not exist yet by construction: Gate-4 requires forward-accrued point-in-time market data. The infrastructure shipped (PR #75); the earliest real run is gated on accrual (~Dec 2026). Nothing buildable accelerates it.

**Studio's sharper point stands and is confirmed:** divergence labels ship while the validity that would justify them is null. That is permissible *only* under the descriptive cordon — every divergence block carries `decision_supported: false`, and the standing rule is that model-minus-market is a **hypothesis, never a proven edge**. The moment any surface presents divergence as decision-grade, or as an "edge", it becomes a defect. Studio's own nDCG figures (QB −0.0240, RB −0.0311, WR −0.0006, TE +0.0032) are zero-to-negative and consistent with that cordon; **I did not reproduce them** (Studio's harness and fold definitions), so I neither endorse nor dispute the numbers — flagged as unverified-by-me.

---

## R3 — CONFIRMED exactly; one framing refined, one caveat added

Constants are `ENGINE_B_P90_PPG` (`src/dynasty_genius/models/engine_b_contract.py:24-29`): QB 20.1, RB 15.7, WR 14.5, TE 9.4. Therefore the ratio is `100 / P90`:

| Pos | 100/P90 (shipped) | Studio measured |
| :-- | --: | --: |
| QB | 4.9751 | 4.9752 |
| RB | 6.3694 | 6.3688 |
| WR | 6.8966 | 6.8976 |
| TE | 10.6383 | 10.6371 |

My QB standard deviation is 0.0019 — identical to Studio's. (My RB/WR/TE sd is larger only because I included the clamped rows, whose ratio is by definition broken; that is itself further evidence of the clamp.)

**Refinement to Studio's "same quantity at zero modelling cost":** true in the unclamped region — DVS is a strictly monotone rescaling of `projection_2y` within a position and adds no information there. It is **not** a rescaling in the clamped region, where information is destroyed rather than transformed. So the honest statement is stronger than Studio's: DVS is PPG rescaled *and truncated*. Whether to surface PPG instead is a product decision for David, not a technical defect.

**Studio's secondary point (cross-position incomparability) — CONFIRMED as a property, with one place worth checking that Studio's sweep may have missed.** `roster_cut_engine._tier_sort_key` (`:171-180`) sorts a **mixed-position roster** by `(tier, score)` where `score = dvs` for tiers B and C. Two players of different positions with equal DVS therefore sort as equal despite different underlying PPG. Whether that constitutes a "comparator mixing positions on DVS" depends on what the surface claims the ordering means — I am flagging it as an open verification for whoever picks this up, not asserting a defect.

---

## R4 — Neither confirmed nor refuted; correctly aimed, governance-gated

Constants verified: `CLIFF_AGES = {RB 26.0, WR 28.0, TE 30.0, QB 33.0}` (`src/dynasty_genius/roster_cut_engine.py:12-17`), consumed only by `_age_cliff_warning` (`:154-158`) which emits a boolean `age_cliff_warning`.

Studio is measuring the right object. Under `00` §Locked Analytical Rulings these four ages are **human-readable decision warnings only**; predictive models consume fitted continuous curves and *must not* encode binary cliffs. So a mis-calibrated constant is a **display** defect, not a model defect — which makes it cheap to fix and safe to change.

Studio's method is careful in the way that matters: the −17.1% all-ages baseline is exactly the right control, and its stated caveats (20–60 per-cell samples, survivor bias understating decline) are the correct ones. **One caveat I would add:** "14 of 27 gone next season" is an *attrition* statistic while "−32.1 vs baseline" is a *production* statistic; they answer different questions and only the attrition figure is well-powered at RB-29 cell sizes. Conflating them would overstate the wall.

**Verdict: plausible and worth acting on, but not actionable by a lane.** The four ages are named explicitly in the constitution, so changing one is a governance amendment requiring David's ruling — not a code edit. The QB-33 hole is honestly reported as a hole; I agree it is not a confirmation.

---

## R5 — CONFIRMED on every fact I can reach; one citation I cannot

Verified: `grep -rl "nflverse\|playerprofiler\|pff_export\|ff_opportunity" app/api/routes/` returns **nothing** — zero routes reference these sources. `app/data/nflverse_usage.db` is **843,481,088 bytes**, 15 tables, `ff_opportunity` 47,282 rows spanning seasons 2018–2025, `depth_charts` 812,074 rows spanning 2018–2024; `app/data/playerprofiler.db` is 472,104,960 bytes.

**The shipped constraint copy is materially stale, and I can name the exact repair.** `frontend/src/shell/ParkedSurfaceCard.tsx:23` reads: *"This surface needs in-season usage signals (routes, snaps) that only accrue while games are played; building it now would ship an empty surface."* Routes and snaps for 2018–2025 **exist on disk**. What does not exist is **current-season (2026)** usage, because the season has not started. The sentence as written implies the data class is absent; the truth is that the *current* vintage is absent. That distinction is exactly the kind of thing that costs trust when the user knows the store is sitting there — the copy should say current-season, or the surface should serve history.

`PRODUCT_BRIEFING.md` does not exist in this repository. If it lives in Studio's directory, the standing wall bars me from reading it, so I neither confirm nor dispute that citation.

---

## Summary for David (no priority claimed, nothing started)

- **R1, R3: confirmed** — DVS is truncated PPG-per-position; the truncation is silent because a designed disclosure field is not serialized. The *disclosure* half is a small, self-contained repair; the *valuation* half is your already-named PVO-scale question.
- **R2: confirmed as deferred** — honest state, contingent on the descriptive cordon holding on every surface.
- **R4: correctly aimed, governance-gated** — a constitution amendment, not a code change.
- **R5: confirmed** — 1.3 GB of usage data unreachable, and shipped copy that misstates why.
- Cheapest true statements to fix, if you ever want them ranked by cost: the `ParkedSurfaceCard` sentence (one line), then `dvs_clamped`/`dvs_p90_ref` serialization (contract already defines both).
