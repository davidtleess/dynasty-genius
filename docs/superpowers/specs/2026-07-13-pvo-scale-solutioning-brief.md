# PVO-Scale Solutioning Session — Decision Brief (David-named priority)

**Status:** session input, uncommitted. The session's deliverable is a David-ratified SCOPED PLAN, not authorized implementation (Codex 2026-07-08 framing holds). This brief makes the session one read away.

## The problem, quantified (all verified)
- The public DVS clamp (`min(100, projection_2y / position_p90 × 100)`, `pvo_assembler.py:389–407`) flattens the top end: raw maxima QB 99.0 / RB 120.1 / WR 140.2 / **TE 156.9**.
- Live consequence (re-verified 2026-07-11): **6 WRs tie at the top xVAR (39.4)** and **11 TEs tie at 2.85** — the model literally cannot separate Tucker Kraft from ten other TEs; competition-ranked ties (T-TE1 ×11) are the honest rendering the Value Board comp now uses.
- Fresh calibration audit (2026-07-13 run, `app/data/backtest/phase14/dvs_calibration_audit_20260713_111645.json`, diagnostic-only, no market data): Spearman ρ — WR .791 · RB .769 · QB .703 · **TE .572**; ECE — WR .046 · RB .085 · QB .117 · **TE .126**. TE is weakest exactly where the clamp bites hardest; the QB curve is flat-zero through the 30th percentile (floor compression too, not just ceiling).

## The three deliverables the session must SEPARATE (do not bundle)
1. **Unclamped latent basis** — the shared prerequisite. Additive/versioned only (`dvs_raw` + `dvs_basis_version` + `dvs_clamped` on `universe_pvo_batch`; emitted DVS is load-bearing in 4 systems). Tier calibration is impossible on a clamped top end.
2. **Tier-calibration producer** (`tier_calibration_latest.json` shape) — Value-Board-scoped; comp-doc §11 already pins its RED seeds (no fixed percentiles, no market inputs, no clamped basis, historical support for named labels, boundary honesty).
3. **Market-comparable rescale (0–2000)** — universe-wide, largest blast radius, explicitly the last and most deferrable.

## Contracts to settle up front (from the 2026-07-08 hardening + this week's rounds)
- Margin axis: divergence stays percentile-space (comp-ratified; the rescale changes display, never the arithmetic).
- PIT continuity: `market_divergence_history` accrues on the current basis — a basis change stamps `dvs_basis_version` per row (the movement feed's basis-stamping prerequisite is the same mechanism; one design, two consumers).
- Frozen-model constitution: the realized-outcome scorer grades frozen predictions; a scale change must not rewrite what the model said.
- **NEW since the reset — the void-season policy (§12.8 diagnosis, 2026-07-13):** Wilson/Braelon/Dell carry NULL xVAR because they have ZERO rows in the runtime feature store (no qualifying 2025 usage). The market prices Wilson WR14; our model goes silent. The session should rule the policy family: explicit "no qualifying usage" state (status quo, now honestly rendered) vs prior-season carry-forward with staleness caveats vs a pedigree/injury prior. This is a REAL scouting question (injury discount, age, pedigree) — the fundamentals David asked for.
- Interim guardrail (both lanes, standing): any tier bands remain position-specific until (3) exists.
- **Gemini's void-season position (advisory, 2026-07-13, screened):** recommends the pedigree/injury-prior carry-forward with a VISIBLE staleness marker — its dynasty argument: a silent model on injured studs disadvantages the manager exactly when trade windows open on them. (Screen note: its message said "Mike Williams"; the data-backed name is Garrett Wilson — corrected here, flagged per the evidence directive.) Counter-position to weigh in-session: a carried-forward number can read fresher than it is even with a marker; the frozen-model constitution requires the carried value be the FROZEN prior output, never a re-estimate. David rules.

## Session inputs on file
Gemini (product): positional exchange rates, liquidity discount, franchise-equity segmentation, tier hysteresis. Codex (technical): basis versioning, PIT continuity, frozen-model interaction, margin-axis contract. Group-value basis: RULED (Option A, team_value_matrix, provisional) — the session inherits it.
