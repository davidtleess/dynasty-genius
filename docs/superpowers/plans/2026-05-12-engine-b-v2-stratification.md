# Engine B v2 — Phase 6 Design Spec

**Date:** 2026-05-12
**Status:** Pending David approval
**Base:** `main @ 55f1351`
**Authors:** Claude Code · Codex · Gemini (PM)
**Doctrine:** v1.0.0

---

## Section 1: Hybrid Refinement Sequence

Phase 6 proceeds in two sequential stages. Stage 6.2 is independent of Stage 6.1's outcome.

### Stage 6.1 — Engine B v1.1 (Hygiene Control)

**Status:** Validation artifact only — not production promoted.

- **Goal:** Isolate the impact of removing `route_participation` from the unified model.
- **Architecture:** Unified Ridge (unchanged). Single artifact.
- **Change:** Remove `route_participation` from `ENGINE_B_ALLOWED_FEATURES`. No other modifications.
- **Artifact path:** `runs/v1_1_control/` — does not replace `engine_b_v1.pkl`.
- **Result usage:** Validation report is retained as the Stage 6.2 comparison baseline. Informs but does not gate Stage 6.2.

### Stage 6.2 — Engine B v2.0 (Stratification Target)

**Status:** Production candidate — the only Phase 6 promotion target.

- **Goal:** Transition to 4 independent, position-stratified Ridge models with explicit feature contracts.
- **Architecture:** 4 independent Ridge artifacts, each trained on its own position's rows only.
- **Artifacts:** `qb_v2.pkl` · `rb_v2.pkl` · `wr_v2.pkl` · `te_v2.pkl`
- **Constraint:** Proceeds regardless of v1.1 TE result.
- **Production handoff:** Engine B v1 remains active in production until v2.0 passes its promotion gate.

**Sequencing rule:** A positive v1.1 TE result confirms collinearity was a primary blocker. A negative result means the TE problem is more fundamental. Both outcomes are informational — neither stops Stage 6.2.

---

## Section 2: Explicit Feature Contracts

**Architecture mandate:** Four independent model artifacts. WR and TE share the same eligible feature list but are trained on separate position-specific data subsets and receive independent alpha search, validation reports, and promotion decisions.

### Per-Position Feature Matrix

| Feature | Class | QB | RB | WR | TE | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `age` | Foundational | ✓ | ✓ | ✓ | ✓ | Required |
| `ppg_t` | Foundational | ✓ | ✓ | ✓ | ✓ | Required |
| `games_t` | Foundational | ✓ | ✓ | ✓ | ✓ | Required |
| `snap_share` | Foundational | ✓ | ✓ | ✓ | ✓ | Required |
| `aging_curve_value` | Aging | ✓ | ✓ | ✓ | ✓ | Required |
| `ppg_t_minus_1` | Historical | ✓ | ✓ | ✓ | ✓ | Avail. flag |
| `ppg_t_minus_2` | Historical | ✓ | ✓ | ✓ | ✓ | Avail. flag |
| `snap_share_t_minus_1` | Historical | ✓ | ✓ | ✓ | ✓ | Avail. flag |
| `epa_per_dropback` | Efficiency | ✓ | — | — | — | Required (QB) |
| `cpoe` | Efficiency | ✓ | — | — | — | Required (QB) |
| `dakota` | Efficiency | ✓ | — | — | — | Required (QB) |
| `is_dual_threat` | Archetype | ✓ | — | — | — | Required (QB) |
| `weighted_opportunity` | Usage | — | — | ✓ | ✓ | Required (WR/TE) |
| `yprr` | Usage | — | — | ✓ | ✓ | Required (WR/TE) |
| `tprr` | Usage | — | — | ✓ | ✓ | Required (WR/TE) |
| `route_participation` | **Excluded** | — | — | — | — | Excluded all — r=0.785 collinear with `snap_share` |
| `total_points_t` | **Excluded** | — | — | — | — | Excluded all — redundant with `ppg_t × games_t` |
| `dropback_count` | **Excluded** | — | — | — | — | Excluded all — redundant with `snap_share + games_t` |
| `pass_attempts` | **Excluded** | — | — | — | — | Excluded all — redundant with `snap_share + games_t` |

### Rules of Engagement

1. **Hard exclusion.** Features marked `—` must be mathematically dropped from the X matrix before fitting. Not zero-filled, not imputed — absent entirely. A WR model must not contain EPA columns at all.
2. **Missing required features.** If a `Required` feature is absent for a specific row (e.g., YPRR missing for a 2018 WR), apply position-group median imputation within that stratified model only.
3. **Historical availability flags.** Include `ppg_t_minus_1_available`, `ppg_t_minus_2_available`, `snap_share_t_minus_1_available` so the model can differentiate consistent multi-year producers from Year 1 profiles. Year 1 players with no historical data receive median imputation.
4. **Market data stays out.** KTC, ADP, FantasyPros, DynastyNerds, and all market-derived values are excluded from every model training matrix. Any market-derived feature in a training row is a leakage defect.

### RB Feature Contract Note

RBs use the Foundational + Historical + Aging set only in Phase 6. No new RB-specific usage metrics are added in the first stratification pass. See Section 6 (RB Follow-On) for deferred candidates.

---

## Section 3: Hyperparameter Optimization & Validation

### Alpha Search

Replace static `alpha=100.0` with per-position `RidgeCV`. Each of the 4 models searches independently. QBs may favor higher regularization (smaller N). TE alpha is independent of WR despite shared features.

### Validation Report Structure

Each training run produces a per-position `validation_report.json` with a three-way comparison:

| Model | Architecture | `route_participation` | Stratified | Role |
| :--- | :--- | :---: | :---: | :--- |
| v1.0 Baseline | Unified Ridge | Included | No | Historical reference |
| v1.1 Control | Unified Ridge | Removed | No | Collinearity isolation |
| v2.0 Target | 4× Position Ridge | Removed | Yes | Production candidate |

All three rows reported per position for clean attribution.

### Promotion Gate

A v2.0 artifact is promoted only if it beats the naive baseline (prior-year PPG) on **≥ 2 of 3 metrics: RMSE, R², Spearman rank correlation** — the same gate used for Engine B v1.0. Per-position decisions are independent. A failing position is not promoted; its v1.0 counterpart remains active with appropriate caveats.

---

## Section 4: TE Promotion Rules & Experimental Caveat

TE is currently marked `ENGINE_B_EXPERIMENTAL_POSITIONS = {"TE"}` because v1.0 does not beat the naive baseline. This status is **evidence-gated** — not cleared by design decision, architectural change, or assumption.

**If `te_v2.pkl` passes gate (≥ 2/3 metrics):**
- Promote `te_v2.pkl` to production
- Remove TE from `ENGINE_B_EXPERIMENTAL_POSITIONS`
- Update service layer and roster auditor display
- Log promotion evidence in validation report and ledger

**If `te_v2.pkl` fails gate (< 2/3 metrics):**
- `te_v2.pkl` is not promoted
- TE remains in `ENGINE_B_EXPERIMENTAL_POSITIONS`
- v1.0 TE artifact remains active with existing caveat
- Failure is logged as Phase 6.2 evidence for future TE diagnosis

**Hard rule:** No agent may remove TE from `ENGINE_B_EXPERIMENTAL_POSITIONS` without a passing validation report in the ledger. The TE experimental caveat propagates through the service layer, API response, and all roster auditor display surfaces until cleared by evidence.

---

## Section 5: Roster Auditor Hardening

Verification work only — executes after v2.0 models are validated and promoted.

- [ ] Verify Engine B v2.0 predictions surface correctly in roster auditor output for all promoted positions.
- [ ] Confirm `ENGINE_B_EXPERIMENTAL_POSITIONS` caveats propagate to the roster auditor display layer.
- [ ] Confirm market overlay (`ktc_value`, etc.) remains physically and semantically separated from model scores in all output rows.
- [ ] Confirm banned David-facing output fields (`dynasty_tier`, `verdict`, `action`, `confidence`) are absent from any new output surface introduced by v2.0 integration.
- [ ] Run the full test suite (≥ 261 pass, 0 fail) after integration. New integration tests for stratified model routing must be added before this section is marked complete.

---

## Section 6: RB Feature Enrichment — Phase 6 Follow-On

Deferred from Phase 6 to preserve clean attribution. Phase 6 answers one question: "Does explicit position stratification improve Engine B using the current validated feature universe?"

After the stratified RB model benchmarks, if R² or Spearman underperforms, the following are the prioritized candidates. All require source coverage check, leakage check, and validation gate before promotion.

**Candidates (priority order):**
1. `red_zone_touches` — highest priority for PPR dynasty value; not captured by `snap_share`
2. `targets_per_game` — receiving role signal for pass-catching backs
3. `weighted_opportunity_rb` — RB-specific WOPR variant if data available
4. `carries_per_game` — likely high correlation with `snap_share`; lowest priority
5. `goal_line_touches` — role signal; data availability TBD

**Note:** `carries_per_game` is likely r > 0.80 with `snap_share` for RBs. Do not add without collinearity check.

---

## Governance

| Document | Version | Authority |
| :--- | :--- | :--- |
| `00-product-constitution.md` | 1.0.0 | Analytical decisions — supersedes all others |
| `01-north-star-architecture.md` | 1.0.0 | Technical architecture |
| `02-agent-operating-loop.md` | 1.0.0 | Session workflow and ledger protocol |
| `AGENT_SYNC.md` | Current | Sprint state board — update at session end |

## Agent Directives

**Claude Code:**
- Own implementation of Stage 6.1 and Stage 6.2
- Update `assemble_engine_b_dataset.py` and `train_engine_b.py` only after this spec is approved by David
- Branch: `phase6/engine-b-v2` from `main`
- Update ledger and `AGENT_SYNC.md` at session end

**Codex:**
- Audit new stratified artifacts after training
- Verify `model_grade` guard respects per-position results
- Review PR — confirm no market-derived features entered training
- Do not modify implementation files before design gate clears

**Gemini:**
- Monitor storage for new stratified `.pkl` artifacts
- Flag any artifact size anomalies or missing validation reports
- Confirm per-position validation reports land in correct run directories

**All agents:**
- Do not modify `engine_b_v1.pkl` or its run directory
- Do not remove TE from `ENGINE_B_EXPERIMENTAL_POSITIONS` without passing gate evidence in the ledger
- Do not introduce market-derived features into any training matrix
- Log all material work in `docs/agent-ledger/YYYY-MM-DD.md`

---

*Dynasty Genius · Phase 6 Design Spec · 2026-05-12 · Doctrine v1.0.0*
*Approved by David before implementation begins.*
