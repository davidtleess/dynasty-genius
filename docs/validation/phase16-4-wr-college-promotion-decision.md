# Phase 16.4 WR College Efficiency Signal — Promotion Decision

**Date:** 2026-05-23  
**Decision:** NOT PROMOTED  
**Authored by:** Claude Code (Phase 19 Task 7)  
**Reviewed by:** Codex (Task 6 review), David (strategic direction confirmed)

---

## Decision Summary

RYPTPA (Receiving Yards Per Team Pass Attempt) and YPRR (Yards Per Route Run from PFF college exports) do not enter Engine A active feature sets. Neither signal passes the Phase 16.4 three-part promotion gate. Production model pkl files and `latest.json` are unchanged.

---

## Bake-Off Results

**Method:** Leave-One-Draft-Class-Out Cross-Validation (LOOCV), 7 folds (2018–2024 draft classes), Ridge regression (α=100), target=`y24_ppg`.

**Baseline features:** `pick`, `round`, `age`

**Coverage (in-scope, 2018–2024):**  
- RYPTPA: 200/228 LOOCV-eligible WR rows (87.7%)  
- YPRR: 207/228 LOOCV-eligible WR rows (90.8%)

**Row-aligned gate comparisons** (baseline re-run on the same cohort as each candidate):

| Candidate | Aligned Baseline MAE | Candidate MAE | MAE Δ | Folds Improved | Gate |
|---|---|---|---|---|---|
| baseline_ryptpa | 3.8168 | 3.8276 | −0.28% | 2/7 | FAIL |
| baseline_yprr_college | 3.8238 | 3.8345 | −0.28% | 0/7 | FAIL |
| baseline_ryptpa_yprr | 3.8168 | 3.8359 | −0.50% | 2/7 | FAIL |

**Gate thresholds (all three required):**
- MAE improvement ≥ 3% aggregate
- ≥ 3 of 7 folds improved
- TE MAE regression < 1% absolute (all candidates: 0.0 — no TE harm)

**VIF:** RYPTPA=2.26, YPRR=2.26 — both_acceptable (no collinearity concern)

**TE regression guard:** Not triggered. TE predictions unaffected by either signal.

> **Note on prior ledger entry:** The first bake-off run (artifact `20260523T162935Z_1626ce17`) reported +0.4–0.6% improvement. That comparison was invalid — baseline MAE was computed on 228 rows while candidates ran on 200/207 rows. The corrected row-aligned numbers above (artifact `20260523T174335Z_0795f28f`) are the authoritative results.

---

## Why the Signals Fail: Structural Analysis

The gate failure is not a data quality problem that more normalization can fix. It reflects a structural limitation in what PFF college data can measure.

**Coverage skews toward high-draft programs.** The players in the LOOCV training set who have RYPTPA and YPRR data are predominantly from Power 5 and high-major G5 programs. One inference is that the market has access to the same PFF metrics and those signals are already embedded in draft capital — but the bake-off only demonstrates that no incremental lift was measured in this setup; it does not prove the mechanism.

**Notable late-round players are not present in our governed PFF exports.** Players like Puka Nacua (BYU, round 5), DeMario Douglas (Liberty, round 6), and Andrei Iosivas (Princeton, round 6) — exactly the players a dynasty manager wants to identify — have no rows in the PFF exports used in this analysis. The 11 CFBD denominator gaps in the current dataset (matched schools with no recorded pass_attempts) are early evidence of this coverage pattern.

---

## Hypotheses for Next Phase

The bake-off result motivates a direction shift, confirmed by David (2026-05-23): the goal is edge over other dynasty managers, not reconstruction of consensus. The following are hypotheses for Phase 20 scoping — they are not validated findings and require their own spec and gate process.

1. **CFBD production for non-PFF schools** — college receiving stats from CFBD cover all FBS programs and many FCS programs. This is the only path to efficiency data for players from programs not present in our governed PFF exports (e.g., BYU, Liberty, Princeton). CFBD quota confirmed available (66,449 requests remaining).
2. **Dominator rating re-framed as draft-position signal** — school-adjusted production relative to pick expectations, controlling for program strength independently of PFF coverage.
3. **Beat-rate target variable** — instead of predicting absolute PPG, train Engine A to predict whether a player outperforms his draft slot. A round-6 pick who produces WR2 output is a more valuable dynasty signal than a round-1 pick who produces the same output.

These are candidates for Phase 20 scoping, not commitments. Each requires David's direction before spec or implementation work begins.

---

## Governance Checklist

- [x] Production model pkl unchanged
- [x] `latest.json` unchanged
- [x] No market data (KTC, FantasyCalc, ADP) in any feature set
- [x] Raw PFF CSV rows not committed
- [x] CFBD_API_KEY loaded from `.env`, never hardcoded
- [x] All bake-off artifacts gitignored (`app/data/backtest/phase16/`)
- [x] Decision recorded in ledger and this validation document
- [x] David notified of result and strategic options

---

## Next Steps

- **Task 8:** `docs/validation/phase16-5-rb-age-governance.md` — RB age de-emphasis governance ruling (document only, no code)
- **Task 9:** Update `AGENT_SYNC.md` with Phase 19 state
- **Phase 20 scoping:** David to choose strategic direction from the three candidates above before any new Engine A signal work begins
