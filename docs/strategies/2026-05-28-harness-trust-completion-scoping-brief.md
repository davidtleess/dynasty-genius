---
title: Backtest Trust Completion — Engine A/B Model-vs-Market Validation — Scoping Brief
status: SCOPING BRIEF (side-session authored by Claude; NOT a cockpit spec; awaiting David routing → multi-agent merge → spec)
date: 2026-05-28
author: Claude (side session — read-only investigation of artifacts + governance + Phase 10/11 harness)
parent_findings: side-session validation audit of 2026-05-28 (TLaw model-vs-market exercise)
governance_hold: Frontend Phase 12 HOLD intact. decision_supported=False throughout. NOISE_BAND lock untouched. No Engine A/B model .pkl/manifest/contract changes except where a workstream explicitly proposes a metric-reporting (not feature) change.
SCOPE GUARD: This is NOT Subsystem 4. S4 (in flight) is the mock-draft-consensus harness (backtest_mock_draft.py). THIS brief extends the Phase 10/11 model-validation harness (backtest_harness.py + market_snapshot_store.py + backtest_metrics.py). The two share the word "backtest" and nothing else.
---

# Backtest Trust Completion — Engine A/B Model-vs-Market Validation

## 0. Why this exists

On 2026-05-28 a side-session audit (prompted by a Trevor Lawrence model-vs-market read) found that the *form* of Dynasty Genius's headline value — "our valuation vs the market's price, and the gap" — is fully built and honest, but the *scientific substance* behind it is **unvalidated**:

- The **divergence ledger is empty** — no `MODEL_LOW_MARKET_HIGH`-style flag has ever been tested against realized forward outcomes.
- **G3 (market-superiority gate) is deferred / unpopulated** — `fc_snapshots.db` historical backfill never ran; every market-NDCG comparison field is `null`. The system **cannot currently claim it beats the market**.
- **Gate 4 (divergence forward-return validity)** awaits ~6 months of native FantasyCalc snapshots that aren't being collected yet.
- **R² is not computed in the backtest harness** (only Spearman/Kendall/RMSE). The QB model — the one a TLaw-type read leans on — is the weakest (Spearman ≈0.71; last-measured R² **negative, −0.208**).

This brief scopes the work that converts the faithful-but-unproven anchor into a **validated** one. It is the unfinished half of the Phase 10/11 "backtesting is a trust layer, not optional QA" constitutional mandate.

## 1. Scope boundary (read this first)

**This work extends the EXISTING Phase 10/11 + Phase 12 production harness.** Touch surface (expected):
- `src/dynasty_genius/eval/backtest_harness.py` (add R² to fold metrics; wire G3)
- `src/dynasty_genius/eval/backtest_artifact.py` + `eval/model_card.py` (report R²; G3 verdict fields)
- `src/dynasty_genius/eval/backtest_metrics.py` (R²; Gate 4 stat tests)
- `src/dynasty_genius/eval/market_snapshot_store.py` + the Phase 10.2 daily snapshot script + Phase 10.10 community-CSV ingest (backfill + forward collection)
- `app/api/routes/trust_surface.py` (QB-reliability stamp; G3 status surfacing)

**HARD SEQUENCING CONSTRAINT — blocked on S4.** Subsystem 4's design spec (`docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md` §11.1 + §11.2 Task-14 SHA-256 audit) declares all of the files above **byte-inviolate for the duration of S4 work**. Therefore **this initiative cannot begin implementation until S4 has merged to main.** Attempting it during S4 would break S4's inviolate-paths contract test. Queue now; execute after S4.

**Not in scope / explicitly barred:**
- Any change to Engine A/B *feature* sets or training (market data stays overlay-only — the existing wall is correct and untouched).
- Any touch to S4's mock-draft modules.
- Frontend (Phase 12 HOLD).

## 2. Workstreams

Four workstreams (W1–W4); one separate research stub (R5, its own doc).

### W1 — Historical market backfill → run G3 (market superiority) **[keystone]**

**Problem:** G3 has never run; no evidence the model beats the market.

**Approach:** Use the *already-built* Phase 10.10 community-CSV ingest + `market_snapshot_store` (SQLite) to backfill historical FantasyCalc dynasty values at the harness's evaluation dates (the spec targets Sep 2021/2022/2023/2024). Then execute the market-NDCG comparison the harness was designed for.

**Draft acceptance gate (David sets final thresholds — they are product rulings):**
- G3 is *evaluable* for ≥3 of 4 folds per position (i.e., market data present at those dates).
- Artifact reports, per position: `ndcg_at_24_model`, `ndcg_at_24_market`, and the per-fold win/loss — honestly, whether the model wins, loses, or ties.
- A loss is a valid, publishable result. The deliverable is *truth about the edge*, not a passing grade.

### W2 — Native daily FantasyCalc snapshots → start the Gate-4 clock **[time-gated, start first]**

**Problem:** Gate 4 (does a divergence flag predict forward returns?) needs a forward-collected, point-in-time snapshot series that doesn't exist yet. Every day not collecting pushes Gate 4 out a day.

**Approach:** Confirm whether the Phase 10.2 daily snapshot script is actually scheduled/running; if not, activate it. Snapshots must be immutable + provenance-stamped.

**Draft acceptance gate:**
- Daily native FC snapshot writes verified (immutable, timestamped, deduped).
- A written Gate-4 readiness date (~6 months out) and the exact stat test locked (spec calls for Mann-Whitney U + BCa bootstrap on flagged-vs-matched-control forward returns).
- **Note:** this workstream has *no* file-lock conflict with S4 (it's the daily script + store, but if those are in the inviolate set, it still waits for S4 merge — verify at spec time). It is the one piece that benefits from starting the *clock* as early as legally possible post-S4.

### W3 — Compute & report R² in the harness

**Problem:** Rank metrics (Spearman) hide magnitude-prediction failure. QB R² was last seen *negative*.

**Approach:** Add in-fold and out-of-sample R² to fold metrics, the artifact, and the ModelCard.

**Draft acceptance gate:**
- R² reported per position per fold (in-fold + OOS).
- **Open decision for David:** does R² *gate* promotion or merely *disclose*? (This ties directly to the open `step_0_5_followups` grader-gate question — resolve them together.)

### W4 — Stamp QB-model reliability on consuming surfaces

**Problem:** A TLaw-type QB divergence read silently inherits the least-validated engine.

**Approach:** Surface a QB-model-reliability caveat on Trust Surface and anywhere divergence is consumed, so QB reads visibly carry their lower confidence.

**Draft acceptance gate:**
- QB outputs carry an explicit reliability stamp tied to W3's measured R²/Spearman.
- Banned-David-facing-language guard stays green; no false-confidence phrasing.

### R5 — (separate research stub) Phase 20 Engine A null root-cause

Out of this initiative; its own research-only doc (`2026-05-28-phase20-engine-a-null-rootcause-research-stub.md`). Question: is the Phase 20 college-metric null a **CFBD data-coverage** problem or a **genuine finding** that draft-capital + age is the ceiling? **Hard lock: no production model change emerges from a research spec.**

## 3. Sequencing

1. **S4 must merge first** (releases the Phase 10/11 inviolate-path lock).
2. **W3 (R²)** is the smallest, lowest-risk — good first RED/GREEN warm-up.
3. **W2 (snapshot clock)** kicks off ASAP post-S4 — it's a calendar dependency, not effort.
4. **W1 (G3 backfill)** is the keystone and the riskiest (data provenance) — most adversarial scrutiny.
5. **W4 (QB stamp)** depends on W3's metrics.
6. **R5** is parallel/independent, research-only, any time.

## 4. Adversarial review checklist (fuel for the cockpit gauntlet)

Pre-loaded "what the skeptic must attack," per workstream:

- **W1 / G3:** Are the community FC archives **point-in-time correct** (no post-hoc revision / survivorship leakage)? Does the historical join to player identity hold across seasons? Is `NDCG@k` the right metric and the cohort defined honestly? With **n≈43 QBs/fold, is "model ≥ market in 3/4 folds" actually statistically powered**, or is it noise dressed as a verdict? Multiple-comparisons exposure across 4 positions? **Existential check: does any backfilled market row leak into a training/feature path?** (must not — verify the wall holds under the new data volume).
- **W2:** Is the daily script *actually* running and writing immutable, provenance-stamped rows? Is cadence defensible for a 6-month Gate-4 horizon? Is the Gate-4 stat test (Mann-Whitney + BCa) appropriate for the forward-return distribution, or does it need a different test?
- **W3:** In-fold vs OOS R² clearly separated? Does negative QB R² **gate** or **disclose** — and is that consistent with the existing grader-gate semantics?
- **W4:** Contract/test change on a decision surface — does the wording avoid implying false confidence while staying honest, and survive the banned-language guard?
- **R5:** CFBD coverage problem vs genuine ceiling? Scope-lock held (no production model change)?

## 5. Role assignment (cockpit, per locked review pattern)

- **Codex = spine.** Test-drives the statistical gates (G3 NDCG comparison, Gate-4 Mann-Whitney/BCa, R² computation) RED-first. Stats-heavy, test-first — its lane.
- **Claude Code = implementer.** Greens the gates; owns the backfill adapter + snapshot-store plumbing.
- **Gemini = governance review ONLY** (per `[[feedback_multi_agent_review]]` — keep it off metric/buy-sell design where it overreaches). Point it at: **leakage compliance** (W1's backfilled data must stay overlay-only), banned-language, source provenance, and **scope-boundary enforcement** (especially R5 staying research-only, and this whole initiative not bleeding into S4).
- **David = arbiter.** Owns the PASS thresholds (validation bars are product rulings) and the W3 gate-vs-disclose decision. Keeper of "be right, not fast."

## 6. Governance & escalation flags (name these up front)

- **Escalation trigger — external data source:** W1's historical FC archive source needs explicit David sign-off (operating-loop "new external data source" trigger), even though the *ingest path* is already architected.
- **Escalation trigger — model-input expansion:** R5 must not expand model inputs without validation; any drift toward a production model change is a hard stop.
- **Leakage boundary:** market data remains overlay-only and never trains Engine A/B; W1 increases market-data *volume* but not its *role* — the wall is unchanged and must be re-verified under load.
- **Local-first / spend:** all of this is local; no Databricks execution without per-session David override (`[[project_databricks_spend_limit]]`).
- **Process:** one agent owns each cross-cutting file at a time; AGENT_SYNC + daily ledger per session; close-the-loop confirmations to both agents (`[[feedback_close_the_loop]]`).

## 7. Counter-argument (Rule 5 — mandatory)

1. **"This is premature — finish the subsystem chain (S4→S1→S2) first."** Fair: the mock-consensus subsystems are the active build order, and validation work competes for cockpit attention. *Response:* this is queued explicitly behind S4 and can slot whenever David chooses; but note the **W2 clock** — the longer Gate-4 collection is deferred, the longer until the divergence signal can *ever* be validated. There's a real option-value cost to delay on W2 specifically.
2. **"G3 may just tell us we don't beat the market."** Yes — and that is the point. A model that loses to the market is vital to know *before* leaning on its divergence calls. An honest loss redirects effort; a hidden loss compounds into bad trades.
3. **"R² on small QB samples (n≈43) is itself noisy."** True; that's why W3 reports it per-fold with CIs and W1 stress-tests statistical power. The cure for one weak metric is more honest metrics, not fewer.
4. **"Risk of scope creep into a generic backtest platform"** — the exact thing S4 §11.1 guards against. *Response:* this brief is deliberately narrow (4 workstreams against named files) and explicitly forbids touching S4's modules or Engine A/B features.

## 8. Self-review note (side session)

Reviewed before saving. Key correction caught during review: an earlier side-session message mis-framed these findings as "Subsystem 4's validation backbone." Reading the actual S4 spec (§11.1 Risk A) showed S4 is the *mock-consensus* harness and has locked the Phase 10/11 files inviolate — so this work is a **separate initiative, hard-blocked on S4 merge**, not part of S4. That correction is now load-bearing in §1 and §3. Remaining open items intentionally left for the cockpit/David: exact G3/Gate-4/R² PASS thresholds (product rulings), and verification of whether the Phase 10.2 daily snapshot script is already scheduled.

## 9. Kickoff prompts (ready to send — fire only AFTER S4 merges)

Three standalone, copy-paste-per-pane prompts (shared context + per-agent lens already merged). Send each to the matching cockpit pane via send-keys. **Do not fire until S4 is merged to main** — this work is hard-blocked on that (§1).

### → CODEX pane (spine / test-driver)

```
New scoping brief for adversarial review — DO NOT start implementation.

Read:
- docs/strategies/2026-05-28-harness-trust-completion-scoping-brief.md
- docs/strategies/2026-05-28-phase20-engine-a-null-rootcause-research-stub.md

Guardrails (non-negotiable):
- This is NOT Subsystem 4. It extends the EXISTING Phase 10/11 model-validation
  harness (backtest_harness.py, market_snapshot_store.py, backtest_metrics.py,
  trust_surface.py).
- S4 is now merged, which releases the §11.1 inviolate-path lock on those files —
  but this session is still DOCUMENT review + spec-readiness ONLY. No code yet.
- Authored by a side session as a proposal. Stress-test it; it is not authority.
  Every acceptance threshold in it is a DRAFT.

Before engaging: run the governance bootstrap (operating loop, constitution,
north-star, AGENT_SYNC, today's ledger).

Your lens: statistical methodology + test-drivability. Attack W1's G3 power at
n≈43 QBs, the NDCG cohort/metric choice, the Gate-4 Mann-Whitney/BCa fit, and
whether each acceptance gate is RED-authorable. Sketch the gate assertions you'd
write first.

Deliver: adversarial findings on the 4 workstreams + draft acceptance gates
(§2, §4), confirmation the scope boundary is correct, any leakage/scope-creep
risks, and a go / no-go on advancing this to a full design spec. Log to today's
ledger.
```

### → GEMINI pane (PM / governance ONLY)

```
New scoping brief for governance review — DO NOT start implementation, DO NOT
redesign metrics.

Read:
- docs/strategies/2026-05-28-harness-trust-completion-scoping-brief.md
- docs/strategies/2026-05-28-phase20-engine-a-null-rootcause-research-stub.md

Guardrails (non-negotiable):
- This is NOT Subsystem 4. It extends the EXISTING Phase 10/11 model-validation
  harness. S4 is now merged (lock released), but this is DOCUMENT review only.
- Authored by a side session as a proposal. It is not authority; every threshold
  is a DRAFT.

Before engaging: run the governance bootstrap (operating loop, constitution,
north-star, AGENT_SYNC, today's ledger).

Your lens: governance ONLY. Assess leakage compliance (W1's backfilled FantasyCalc
data must stay overlay-only and never enter Engine A/B training), banned-language,
source sign-off for the historical FC archive (external-source escalation trigger),
and scope-boundary enforcement (R5 stays research-only; this initiative must not
bleed into S4 or expand model inputs). Do NOT redesign metrics or add buy/sell
scope — flag, don't expand.

Deliver: governance findings + a go / no-go on advancing to a design spec, from a
constitution-compliance standpoint. Log to today's ledger.
```

### → CLAUDE CODE pane (author / reconciler)

```
New scoping brief — you will OWN brief→spec if it clears review. DO NOT start
implementation yet.

Read:
- docs/strategies/2026-05-28-harness-trust-completion-scoping-brief.md
- docs/strategies/2026-05-28-phase20-engine-a-null-rootcause-research-stub.md

Guardrails (non-negotiable):
- This is NOT Subsystem 4. It extends the EXISTING Phase 10/11 model-validation
  harness (backtest_harness.py, market_snapshot_store.py, backtest_metrics.py,
  trust_surface.py). S4 is now merged, releasing the §11.1 lock — but this is
  DOCUMENT review + spec-readiness ONLY.
- Authored by a side session as a proposal; every threshold is a DRAFT.

Before engaging: run the governance bootstrap (operating loop, constitution,
north-star, AGENT_SYNC, today's ledger).

Your lens: you own the spec if this clears. Reconcile the Codex (statistical) and
Gemini (governance) reviews, flag any internal contradictions in the brief, verify
the §1 touch-surface file list against current main (post-S4), and surface the open
David rulings that the spec will need: G3 / Gate-4 / R² PASS thresholds, the R²
gate-vs-disclose decision (tie to the open step_0.5 grader-gate question), and
whether the Phase 10.2 daily snapshot script is already scheduled.

Deliver: a reconciled go / no-go, and — if go — the skeleton of the design spec
(workstreams, gates, open rulings). Log to today's ledger.
```

**Note:** these read "S4 is now merged" — correct only at fire time. If for any reason you send them while S4 is *not* yet merged, change that line back to the blocked-on-S4 wording from the earlier draft.
