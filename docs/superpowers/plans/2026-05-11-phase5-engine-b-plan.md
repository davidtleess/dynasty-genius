# Phase 5 / Engine B Planning Document

**Written:** 2026-05-11  
**Status:** PLANNING — No implementation until David approves all open questions below.  
**Scope:** Docs only. No model files, no feature contracts, no adapters, no training code.

---

## What Has Been Built (Current State)

### Engine A — Pre-NFL Rookie Forecast
- Trained on 125 QB / WR / RB / TE draft classes (2015–2023)
- Outcome: `y24_ppg` — average PPG over years 2–4 of NFL career
- Features: pick, round, age + position-specific college stats (CFBD)
- QB college features registered but **NOT promoted** (backtest FAIL 0/3)
- QB scoring today: pick, round, age only

### Stage 4 — QB Professional Context Layer (merged 2026-05-11)
- `nflreadpy_qb_adapter.py`: EPA/dropback, CPOE, DAKOTA, dropback_count, pass_attempts
- `QB_CONTEXT_COLUMNS`: 5 fields, `context_signal` only — never model inputs
- `run_audit()` returns `qb_context_cards` with live telemetry for roster QBs
- Display annotations: bust flags (TD/INT <0.7), mobility signal (APY >3,700), college caveats
- **These are context signals. They do not enter any model.**

---

## What Phase 5 / Engine B Would Add

Engine B is an **active-player forecast model** — separate from Engine A in every way:
- Separate training dataset (NFL seasons, not draft classes)
- Separate feature pipeline (NFL usage + efficiency, not college stats)
- Separate outcome variable (not yet defined — see open questions)
- Separate leakage contract (pre-NFL features are leakage in Engine B)

The system design document (`docs/system-design.md`) defines Engine B as:
> "Inputs: NFL usage, efficiency, multi-year production trends, age curve state, team context. No rookie pre-NFL features."

Phase 5 is the prerequisite: **fitted aging curves**. The roadmap requires Phase 5 to close before Engine B training begins.

---

## Open Questions — All Require David's Decision

### Q1: Outcome Variable

What does Engine B predict?

| Option | Target | Pros | Cons |
|--------|--------|------|------|
| A | Next-season PPG (year T+1) | Simple, direct | Noisy, one bad season ruins signal |
| B | 2-year average PPG (years T+1, T+2) | More stable | Delays signal; requires 2yr lookback to evaluate |
| C | Age-curve-adjusted expected PPG | Most principled | Requires Phase 5 curves first; complex |

**Recommendation:** Option B (2-year average). Reduces single-season noise without requiring fitted curves as input. Aligns with how dynasty value actually works — sustained production, not one-year spikes.

**David must approve before any training code is written.**

---

### Q2: Prediction Horizon

Related to Q1. What "future" window are we predicting?

- **1-year:** Feature year T → outcome year T+1. Immediate signal, fast feedback loop, high noise.
- **2-year:** Feature year T → average of T+1 and T+2. Dynasty-relevant window, better signal.
- **3-year:** Feature year T → average of T+1, T+2, T+3. Most stable, but misses short-window players.

**Recommendation:** 2-year. Matches dynasty decision timescale and reduces noise without requiring the player to have 3+ active seasons.

---

### Q3: Aging Curve Representation (Phase 5 Prerequisite)

The current roster auditor uses hardcoded cliff ages:
```python
CLIFF_AGES = {"RB": 26, "WR": 28, "TE": 30, "QB": 33}
```

Phase 5 replaces these with **fitted curves** — continuous functions that predict production decay as a function of age, position, and (for QBs) mobility archetype.

**Key decision:** How are curves represented?

| Option | Form | Pros | Cons |
|--------|------|------|------|
| A | Polynomial regression on age | Simple, interpretable | Symmetric — doesn't capture asymmetric decline |
| B | Piecewise linear (pre/post-peak) | Intuitive breakpoints | Requires peak age estimation |
| C | Spline fitted to historical PPG | Smooth, data-driven | Harder to explain; needs sufficient per-position data |

**Recommendation:** Option B (piecewise linear) for the MVP. One slope for the ascent phase, one for the decline phase, breakpoint at estimated peak age by position. Interpretable and defensible.

**QB-specific:** Dual-threat QBs get a separate curve with an earlier decline onset (~29) vs. pocket passers (~33). This matches the approved QB strategy. Whether this is a separate model or a single model with an interaction term is Q4.

---

### Q4: QB Archetype Split

Should Engine B train:
- **One QB model** with a `is_dual_threat` indicator feature, or
- **Two separate QB models** (pocket passer and dual-threat)?

**Recommendation:** One model with an interaction term in Phase 5 MVP. If the archetype coefficient is large and significant, split into two models in a follow-up. Don't pre-optimize before seeing the data.

**Archetype classification method is also unresolved.** Options: rushing yards threshold (>500/season = dual-threat), manual classification, or clustering on EPA/rushing share. Must be decided and locked before training.

---

### Q5: Validation Gates for Engine B

Engine A uses a composite gate (RMSE/R²/Spearman, ≥2/3 thresholds). Engine B needs its own gates.

**Proposed Engine B gate structure:**
- Same composite structure (RMSE/R²/Spearman) on a held-out test set
- Holdout: 20% of player-seasons, stratified by position and year
- Promotion threshold: ≥2/3 metrics improve vs. a naive baseline (e.g., prior-year PPG as the prediction)
- Minimum holdout rows: 50 per position (QB will be the binding constraint)

**Open sub-questions:**
- What is the naive baseline? Prior-year PPG is the natural choice.
- What is the QB holdout size? If training covers 2018–2022, holdout is 2023–2024. QB seasons with ≥8 starts: roughly 30–40 per year. This is below the 50-row threshold. Similar to the Engine A QB problem.

---

### Q6: Leakage Contract for Engine B

Engine B's leakage rules are different from Engine A:
- **Engine A leakage:** NFL performance data leaking into pre-NFL model
- **Engine B leakage:** Future NFL stats leaking into current-year features (temporal leakage)

The Engine B leakage contract must explicitly define:
1. Feature cutoff: all features use **season T data only** (no T+1 lookback)
2. Roster/scheme features (OL grade, target competition) use **season T values only**
3. Market data (KTC, ADP, FantasyCalc) remains prohibited from features — already governed
4. Age curve state is derived from **fitted curves applied to age at season T** — not from actual future production

**A new `ENGINE_B_PROHIBITED_COLUMNS` set is needed in `engine_a_contract.py`** (or a separate `engine_b_contract.py`) before any Engine B feature pipeline code is written.

---

## What Is Out of Scope Until Q1–Q6 Are Approved

The following will NOT be built until David explicitly approves answers to the questions above:

- Any Engine B training script or model artifact
- Any `engine_b_contract.py` or `ENGINE_B_*` constants in `engine_a_contract.py`
- Any modification to `POSITION_FEATURE_MATRIX` for active-player features
- Any nflreadpy feature pipeline beyond the current `context_signal` adapter
- Any fitted aging curve artifacts or curve-fitting scripts (Phase 5 itself)
- Any Engine B API route or service layer

**The current `qb_context_cards` and display annotations are the ceiling for QB intelligence until Engine B is approved and built.**

---

## Proposed Phase 5 Task Breakdown (Pending Approval)

Once Q1–Q6 are resolved, Phase 5 would proceed as:

| Task | Description | Agent | Sessions |
|------|-------------|-------|----------|
| 5.1 | Assemble Engine B training dataset — player-season rows with outcome T+1 | Codex | 2 |
| 5.2 | Fit aging curves by position using piecewise linear model | Claude | 1 |
| 5.3 | Write `ENGINE_B_LEAKAGE_CONTRACT` and TDD gate tests | Claude | 1 |
| 5.4 | Train Engine B MVP (Ridge or gradient-boosted per 4.11 decision) | Codex | 2 |
| 5.5 | Composite gate validation report | Claude | 1 |
| 5.6 | Engine B service skeleton + experimental API route | Codex | 1 |

**Estimated total: 8 agent sessions minimum.** Do not start until design is locked.

---

## Recommended Next Step

Before any Phase 5 implementation work:

1. David reviews Q1–Q6 above and records decisions (can be in a short message; Claude will formalize them into a locked decision record).
2. Claude writes the locked decision record as a new doc and updates AGENT_SYNC.
3. Codex begins 5.1 only after the decision record is merged.

**No code. No features. Just alignment.**
