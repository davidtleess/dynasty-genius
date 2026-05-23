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

**PFF covers the same schools NFL scouts cover.** The players in the LOOCV training set who have RYPTPA and YPRR data are predominantly from Power 5 and high-major G5 programs. Draft capital (pick+round) already prices in everything the market knows about these players — and the market has access to the same PFF grades and efficiency metrics. Adding RYPTPA or YPRR to a model trained on this population cannot produce lift because the signal is already embedded in where the player was drafted.

**True late-round sleepers are invisible to PFF by design.** Players like Puka Nacua (BYU, round 5), DeMario Douglas (Liberty, round 6), and Andrei Iosivas (Princeton, round 6) — exactly the players a dynasty manager wants to identify — come from programs PFF does not cover. Their college efficiency data does not exist in the PFF export. The 11 CFBD denominator gaps in the current dataset (schools with no pass_attempts record) are early evidence of this coverage pattern.

**Spearman rank correlation by pick tier:** Tested at the end of Phase 19 Task 6 analysis. Near-zero correlation in every bucket including R4+ (picks 129+), confirming no monotonic relationship between PFF college efficiency and eventual dynasty PPG within any draft position stratum.

**Mann-Whitney U (late-round sleepers):** R4+ players with ppg≥8 vs ppg<5 — p=0.644. No statistically significant difference in RYPTPA between eventual sleeper hits and busts in the same pick range.

---

## Strategic Direction (David-Confirmed)

> *"Yes. It's important we try to be smarter than the market. Anyone can look at draft capital."*  
> — David, 2026-05-23

The goal is edge over other dynasty managers, not reconstruction of consensus. PFF college metrics are consensus inputs — available to all managers and already priced into draft capital. Three candidate directions were identified:

1. **Dominator rating re-framed as draft-position signal** — school-adjusted production relative to pick expectations (beats the market by controlling for program strength separately from PFF coverage)
2. **CFBD production for non-PFF schools** — college receiving stats from CFBD cover all FBS programs and many FCS programs. This is the only path to data on Puka Nacua's BYU years, DeMario Douglas's Liberty years, etc. CFBD quota confirmed available (66,449 requests remaining).
3. **Beat-rate target variable** — instead of predicting absolute PPG, train Engine A to predict whether a player outperforms his draft slot. A round-6 pick who becomes a WR2 is a better dynasty asset than a round-1 pick who becomes a WR2.

These directions are not mutually exclusive. They are candidates for Phase 19 strategic planning, subject to David's direction.

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
