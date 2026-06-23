# Gate-4 Divergence-Edge Validation — Design Spec (PRE-REGISTERED)

**Status:** DRAFT v3 for cockpit dual-CLEAR (round 3 — integrates Codex round-2 refinements: C1 claim-level distinction [tradeable-edge requires training-cutoff ≤ T vintage models, else explicitly a current-model retrospective diagnostic], C2 stratum-drop `OR` + matched-post-filter floors, C5 effective-month-block floor; Gemini governance CLEAR on v2). Round 2 integrated C1–C5. **All numeric parameters in §3–§6 are PRE-REGISTERED: once this spec is dual-CLEARED and David-ratified, they are LOCKED and MUST NOT be changed after the archive is ingested or any analysis is run.** This is the anti-p-hacking guarantee (both lanes' primary concern). A parameter change after lock invalidates the verdict and requires a new pre-registered spec.

## 0. Question & authorization
The single open North-Star question: **is the Dynasty-Genius model-vs-market divergence a real, tradeable edge?** Today the divergence is DESCRIPTIVE only [[feedback_divergence_is_unvalidated]]; prior W1 ran on SYNTHETIC history so the real Gate-4 verdict was deferred. David has the real FantasyCalc-native archive (~weekly, 12mo+) → this study produces the honest verdict. **This is a VALIDATION STUDY, not a product change.** David authorized B (2026-06-23). No model/product change is authorized by this spec.

## 1. Hypothesis (pre-registered, directional)
At snapshot date `T`, classify each model-eligible active player by the signed gap between its **within-position model percentile** and **within-position market percentile** (§3). Hypothesis:
- **`MODEL_HIGH_MARKET_LOW`** (model rates a player above where the market does) → **outperforms** the NEUTRAL control in *future market movement* over horizon `T→T+N`.
- **`MODEL_LOW_MARKET_HIGH`** → **underperforms** the NEUTRAL control.

**Target = future TRADE-MARKET movement, NOT realized fantasy production** (Gate-4 asks "does divergence anticipate the market"; production is secondary context only). Null hypothesis `H0`: divergence bucket at `T` has no predictive relationship with forward market movement vs. neutral/inside-band controls.

## 2. Archive requirements & ingestion
- **Single source family per verdict.** FantasyCalc-native preferred; KTC / DynastyProcess are SEPARATE verdicts and MUST NOT be mixed into one (`SOURCE_INADEQUATE` if mixed). League settings fixed: `isDynasty=true&numQbs=2&numTeams=12&ppr=1` (the existing `LEAGUE_SETTINGS_HASH`).
- **Coverage:** ≥12 months; **weekly cadence preferred** (monthly is presumptively `UNDERPOWERED` for 30/60-day horizons).
- **Per-row fields:** `snapshot_date` (YYYY-MM-DD), `sleeper_id`, `market_value`, `source`; strongly preferred `position`, `overall_rank`, `position_rank`, player name (audit only).
- **Ingestion:** existing `scripts/ingest_market_archive.py` → `MarketSnapshotStore` (SQLite). The archive file(s) are David-supplied; ingestion is a pre-step, not part of the verdict run. **Source-family isolation (Codex C4):** the current `fc_snapshots` primary key omits `source` and ingest uses `INSERT OR REPLACE`, so a re-ingest or a mixed source can silently overwrite rows for the same (date, player, settings). For a valid single-source verdict the run MUST use a **fresh isolated DB dedicated to this archive/source family** (or, equivalently, source-filtered append-only ingestion with a fail-closed conflict on (date, player, settings, differing source)). The runner asserts a single `source` family across all loaded rows before computing anything; any second source family → `SOURCE_INADEQUATE`.
- **Identity join:** market `sleeper_id` ↔ model universe via the existing identity substrate; **survivorship-safe** (a player absent from a later snapshot is an explicit *missing outcome*, §3.4, never silently dropped).

## 3. Methodology (pre-registered)

### 3.1 Divergence metric
At each `T`, over the model-eligible active universe with a market row:
- `model_pct(p,T)` = within-position percentile rank of the player's **POINT-IN-TIME model value at T**, 0–100. **CRITICAL (Codex C1 — no look-ahead):** the model value MUST reflect only information available at `T`. The current/latest PVO artifact MUST NOT be used against historical market snapshots (that leaks the model's present view into the past). Acceptable PIT sources, in priority: (a) archived PIT PVO/Engine-B snapshots dated ≤ `T`; (b) a **frozen-model reconstruction** — the locked Engine-B `.pkl` re-scored on the player's features **as they were at `T`** (PIT feature reconstruction). If neither a PIT model snapshot nor a defensible PIT feature reconstruction is available for a date, that date is excluded; if PIT model values cannot be established for enough dates to meet §6 floors, the verdict is **`MODEL_PIT_INADEQUATE`** (§6) — never silently fall back to current PVO.

**Claim-level distinction (Codex C1 — MANDATORY, the deepest leakage guard).** Re-scoring the *current* locked Engine-B `.pkl` on PIT features still leaks the future, because the model's *coefficients* were trained on data that includes post-`T` outcomes. The study therefore records a locked `claim_level`, auto-determined from the model artifact's **training-data cutoff** vs. the test window:
- **`tradeable_historical_edge`** — ONLY if every tested `T` uses a model artifact whose training cutoff `≤ T` (true vintage / walk-forward models). This is the only configuration in which a `PASS` may be described as a *tradeable* edge.
- **`current_model_retrospective_diagnostic`** — if the current/locked model (training cutoff `>` some tested `T`) is re-scored on PIT features. This is still informative ("does the current model's divergence associate with subsequent market moves?") but a `PASS` here is a **retrospective association, explicitly NOT a tradeable edge**, and the report + any summary MUST carry that disclaimer. It may never be promoted to decision-grade.

The runner determines `claim_level` from the model artifact metadata; absent a verifiable training cutoff, it defaults to the weaker `current_model_retrospective_diagnostic` (fail-safe, never overclaim).

**Repo-inventory expectation (cockpit-converged 2026-06-23, Codex investigation + Gemini concur).** As of 2026-06-23 the repo contains only **current** Engine-B artifacts (May-2026 `v2`/`te_v3` `.pkl`, gitignored/local; training data `engine_b_features_v2.csv` spans feature_season 2018–2024), **no PIT PVO archive over historical market dates**, and `build_universe_pvo_batch.py` scores through the current model with no vintage-by-date selection. Therefore the **expected achievable `claim_level` for this study is `current_model_retrospective_diagnostic`** — a `PASS` is an *investment justification* for later building true vintage/walk-forward artifacts (NOT product promotion), and a `FAIL` is strong evidence to keep divergence permanently quarantined/tombstoned. `tradeable_historical_edge` requires David to supply or authorize constructing vintage/PIT model artifacts (training cutoff ≤ T) — a separate, larger effort.
- `market_pct(p,T)` = within-position percentile rank of the player's **market value at T**, 0–100.
- `D(p,T) = model_pct − market_pct` (within-position; in [−100, +100]).
Within-position percentiles (not raw cross-position values) neutralize positional scale and market-wide inflation.

### 3.2 Buckets (LOCKED band edges)
- `MODEL_HIGH_MARKET_LOW`: `D ≥ +20`
- `MODEL_LOW_MARKET_HIGH`: `D ≤ −20`
- `NEUTRAL` (control): `|D| ≤ 5`
- **Gray zone `5 < |D| < 20`: EXCLUDED** from the primary test (neither signal nor clean control).

### 3.3 Horizons (LOCKED)
Primary: **60 and 90 calendar days**. Secondary/context: 30 days. A PASS REQUIRES the result to hold across **both** 60 and 90 (stability §4). **Forward-only date resolver (Codex C3):** `T+N` uses the **earliest** available snapshot with date **≥ `T+N`** within a **+7-day forward tolerance**. A NEW forward-only resolver is required — the existing `MarketSnapshotStore._resolve_date()` (closest within ±7, which can pick a date *before* `T+N` and silently shorten the horizon) MUST NOT be used. If no snapshot falls in `[T+N, T+N+7]`, that (player,T,N) observation is dropped *for that horizon only* and counted in the missingness report.

### 3.4 Forward outcome (LOCKED)
`fwdΔ(p,T,N) = market_pct(p, T+N) − market_pct(p, T)` (within-position percentile change — controls for market-wide drift).
**Survivorship rule (LOCKED):** if a player has a market row at `T` but none at `T+N` (left the tradeable market), assign `fwdΔ = the 5th-percentile (worst-decile) forward outcome observed in that position×horizon×date cohort` — i.e., disappearance is treated as a strongly negative outcome, NOT dropped. This is conservative and prevents survivorship inflation.

### 3.5 Regression-to-mean control (Codex C2 — MANDATORY, pre-registered)
`MODEL_HIGH_MARKET_LOW` is by construction partly "low market percentile at `T`," and the outcome is a future market-percentile *change* — so low-market players mean-revert UPWARD regardless of the model. An uncontrolled comparison could PASS purely on mean-reversion, not on a model edge. The primary test MUST therefore hold **initial market percentile fixed**:
- **Stratified matched design (LOCKED):** bin observations by `position × initial market_pct decile × snapshot-date`. Within each stratum, compare `MODEL_HIGH_MARKET_LOW` vs `NEUTRAL` (and `NEUTRAL` vs `MODEL_LOW_MARKET_HIGH`). The signal and its control thus share the same position, the same starting market percentile band, and the same date — any forward-Δ difference is attributable to the model divergence, not to mean-reversion or market-wide drift. Pool strata via sample-weighted mean of per-stratum median differences. **A stratum is dropped (and reported) if it has < 5 signal observations OR < 5 control observations** (Codex C2 — `OR`, not `AND`; a 1-signal/80-control stratum must NOT survive to drive noisy medians). Matched-post-filter coverage floors (§6) are re-checked on the *surviving matched* observations per bucket × horizon, not only on the raw pre-match bucket counts.
- **Secondary confirmation:** a covariate-adjusted estimate (forward-Δ regressed on bucket with `initial market_pct` + position fixed effects) must agree in sign with the stratified primary; disagreement → not a PASS.

### 3.6 Primary statistic
For each horizon, computed on the §3.5 stratified design: `lift_HIGH = pooled stratified [median(fwdΔ | MODEL_HIGH_MARKET_LOW) − median(fwdΔ | NEUTRAL)]` and `lift_LOW = pooled stratified [median(fwdΔ | NEUTRAL) − median(fwdΔ | MODEL_LOW_MARKET_HIGH)]`. Both expected `> 0` under the hypothesis.

## 4. Pre-registered acceptance criteria (ALL required for PASS — LOCKED)
1. **Direction:** `lift_HIGH > 0` AND `lift_LOW > 0`, for BOTH 60d and 90d.
2. **Significance:** bootstrap 95% CI **excludes 0** for `lift_HIGH` and for `lift_LOW`, at BOTH horizons. **Serial-autocorrelation control (Codex C5):** weekly `T` dates with 60/90-day horizons produce heavily *overlapping* forward windows, so per-date clustering alone understates the CI (adjacent dates are serially correlated). The CI MUST be a **block bootstrap blocking by month** (resampling whole calendar-month blocks of dates, preserving within-block serial structure). REQUIRED secondary: a **non-overlapping sensitivity** run using only `T` dates spaced ≥ the horizon apart must agree in sign; disagreement → not a PASS. **Effective-block floor (Codex C5):** ~12 months yields few blocks, making the bootstrap fragile; the report MUST expose the **effective month-block count** after horizon/missingness filtering, and the verdict is **`UNDERPOWERED`** if fewer than **6 effective blocks** survive (a 10k-resample CI over <6 blocks is not trustworthy).
3. **Practical effect size:** median lift ≥ **8 within-position percentile points** for the primary (HIGH) signal at both horizons (statistical-nonzero is insufficient).
4. **Stability:** (a) **leave-one-month-out** — sign of `lift_HIGH` stable across all single-month exclusions; (b) **no single position** contributes > 50% of the pooled effect (re-test excluding the top-contributing position; sign must hold).
5. **Coverage floors met** (§6).

Any acceptance criterion failing **with adequate power** → `FAIL` (a legitimate, publishable "edge NOT confirmed"). Coverage/power floors unmet → `UNDERPOWERED` (not FAIL).

## 5. Falsification battery (each a required guard; failure = study INVALID, not a verdict)
- **Label-shuffle null:** permute divergence bucket labels within (date × position); the lift MUST collapse toward 0 (sanity that the pipeline isn't manufacturing signal).
- **Look-ahead / date-leakage gate:** assert no `T+N` data can influence the `T` bucket assignment; a deliberate leak fixture must be caught.
- **Survivorship test:** disappeared players included as missing outcomes per §3.4; a variant that silently drops them must produce a *materially different* (more optimistic) result, demonstrating the guard bites.
- **Position-leakage test:** confirm percentiles are within-position; a cross-position-raw variant must be rejected by the harness.
- **Source-family split:** a FantasyCalc-native verdict MUST NOT be computed from mixed sources; mixed input → `SOURCE_INADEQUATE`.

## 6. Verdict taxonomy & power/coverage gates (LOCKED)
- `PASS` — all §4 met.
- `FAIL` — adequate power, but §4.1/4.2/4.3/4.4 not met (edge NOT confirmed; legitimate result).
- `UNDERPOWERED` — any coverage floor unmet: **< 8 usable T-dates per horizon**, **< 200 joined player-date observations** overall, or **< 30 observations in any tested bucket** (that bucket abstains; if the primary HIGH bucket abstains → whole verdict UNDERPOWERED).
- `SOURCE_INADEQUATE` — mixed/non-single source family, or settings-hash mismatch.
- `IDENTITY_COVERAGE_INADEQUATE` — **< 90%** of model-eligible actives have a market row at a tested `T` (per-position missingness reported).
- `MODEL_PIT_INADEQUATE` — point-in-time model values (§3.1) cannot be established (no PIT model snapshots and no defensible PIT feature reconstruction) for enough dates to meet the §6 floors. The study does NOT proceed on current/latest PVO (that would be look-ahead).

## 7. Guardrails (hard boundaries)
- **Validation study ONLY.** NO model retraining; NO production PVO scoring change; NO Engine A/B feature/training/`.pkl` change; market data remains **overlay-only / never a model input**.
- **Aggregate-only output** — the report carries bucket/horizon statistics, NOT David-facing per-player buy/sell recommendations; no banned David-facing language.
- Divergence stays **descriptive** until a `PASS` AND a separate David-approved product decision.
- No OpenAPI/contract/UI behavior change in this study.

## 8. Output report schema (test-backed, §6 verdicts)
Machine-readable report under `app/data/backtest/gate4/` (+ human summary under `docs/validation/`). Required fields: `schema_version`; `verdict` (§6 enum); **`claim_level`** (`tradeable_historical_edge` | `current_model_retrospective_diagnostic`, §3.1) + the model artifact's training cutoff used to derive it; `source_family` + `settings_hash`; `archive_provenance` (file hashes, date range, snapshot count, cadence); per-horizon `{lift_HIGH, lift_LOW, bootstrap_ci, effect_size, n_by_bucket, effective_month_block_count, non_overlapping_sensitivity_sign}`; `coverage` (T-dates, joined obs, identity-coverage %, per-position missingness, matched-surviving counts by bucket×horizon); `stability` (leave-one-month-out signs, top-position-excluded re-test); `falsification` (each guard pass/fail); `decision_supported=false`; `pre_registration_lock` (this spec's commit SHA + parameter snapshot, to prove params predate the run). When `claim_level=current_model_retrospective_diagnostic`, every PASS statement in the report MUST be accompanied by the "retrospective association, not a tradeable edge" disclaimer.

## 9. Implementation shape & build sequence (post-approval only)
1. **Spec dual-CLEAR → David ratifies the locked parameters** (pre-registration sealed; spec commit SHA is the lock token).
2. David supplies + we ingest the archive into an **isolated single-source DB** (§2); emit an ingestion/coverage report — **before** any analysis, confirm coverage tier (powered vs likely-underpowered).
2b. **PIT model establishment (gating dependency, Codex C1):** establish point-in-time model values per `T` (§3.1) — locate archived PIT PVO/Engine-B snapshots OR build a frozen-model PIT feature reconstruction. If neither is feasible across enough dates, the study returns `MODEL_PIT_INADEQUATE` and stops. This step's feasibility is assessed early (it may itself be the gating constraint, independent of market-archive richness).
3. **T1:** pure validation engine (divergence bucketing, forward-outcome join, survivorship rule, bootstrap, verdict logic) + falsification fixtures — RED→GREEN→dual-CLEAR. **Tested entirely on fixtures; the real archive is NOT touched in T1.**
4. **T2:** `scripts/run_gate4_divergence_edge_validation.py` runner + §8 report emitter (test-backed schema) — RED→GREEN→dual-CLEAR.
5. **T3 (gated):** run on the real ingested archive → emit the verdict report. David authorizes the run; the verdict (whatever it is) is reported honestly.
6. Verdict-conditional product follow-up (§10) is a SEPARATE, later David decision.

## 10. Verdict-conditional product consequence (DEFERRED — David decides later, not in this study)
Consequences are split by `claim_level` (Codex round-2 — a retrospective-diagnostic PASS must NOT trigger product promotion):
- `PASS` **with `claim_level = tradeable_historical_edge`** → may revisit the League Pulse market-overlay quarantine; divergence may become a validated heuristic (separate spec, David-gated).
- `PASS` **with `claim_level = current_model_retrospective_diagnostic`** → **NO product promotion.** It is only evidence that the *current* model's divergence retrospectively associates with market movement; surfaces unchanged unless David approves a separate vintage / walk-forward validation (training cutoff ≤ T) to upgrade the claim level.
- `FAIL` → the quarantine becomes a permanent honest tombstone ("divergence is unvalidated for trading; do not act on it").
- `UNDERPOWERED` / `SOURCE_INADEQUATE` / `IDENTITY_COVERAGE_INADEQUATE` / `MODEL_PIT_INADEQUATE` → surfaces unchanged; note the limiting cause; revisit if a richer/PIT-adequate archive or vintage models arrive.
