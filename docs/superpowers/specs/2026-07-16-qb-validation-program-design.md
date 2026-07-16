# QB Validation Program — Increment 1: Computed Backtest of the David QB Research Pair

**Date:** 2026-07-16
**Status:** DRAFT — awaiting cockpit CLEAR, then David authorization. Review-only session; nothing here is authorized to build.
**Authoring lane:** Claude spec · Codex RED · Gemini advisory (product-edge review received + integrated 2026-07-16 — see §4 F13 and the synthesis's Gemini lane; Codex technical review received + integrated same day — see §4b).
**Scope:** a research-only validation pipeline that computes the backtests both research documents defer. It produces **reports and artifacts, no product surface, no model promotion, no served-API change**. It is explicitly NOT the valuation engine, NOT a new Engine B QB head, NOT a UI card — those are gated increments 2–3 in the parking lot (§3).

## 1. Problem (measured, not inferred)

David's directive (via Tower, 2026-07-16, verbatim): "Note both reports flag their backtests as directional rather than computed — numeric validation is part of the assessment."

Both documents say so themselves. Prediction doc: "the per-model error metrics in this report are reasoned from gathered correlations rather than fully computed... should be re-run numerically in the pipeline above before you trust exact figures." Valuation doc: "that computation was not run here... Treat the results above as directional validation, not a statistically closed proof."

**Root cause — the computation is not runnable in-repo today.** Reproduced (not asserted):

```
$ .venv/bin/python3.14 -c "import nfl_data_py; print(nfl_data_py.__version__)"
ModuleNotFoundError: No module named 'nfl_data_py'
```

and the existing QB walk-forward harness predicts **per-horizon binary survival labels, not PPG** (`src/dynasty_genius/eval/qb_v3_walk_forward.py:8`: "per-horizon binary survival labels are graded on..."; label plumbing at `:36-37,78-80`) — there is no PPG regression target, no Sleeper-scored PPG label table, and no stat-ingestion adapter for the 2015–2025 seasons the study needs. The fold machinery and `backtest_metrics.py` (Spearman/Kendall with BCa CI95, `:58-75`) ARE reusable.

**Consequence today:** five hypotheses and a valuation-engine design carry only reasoned-estimate support; building either engine on uncomputed numbers would violate Prime Directive ("be right, not fast") and repeat the exact overclaim pattern the constitution exists to prevent.

## 2. Design

One increment, four deliverables, all research-lane:

**D1 — Stat ingestion adapter (`src/dynasty_genius/adapters/nflverse_stats_adapter.py`).** One adapter on **`nflreadpy` (already installed, 0.1.5, `requirements.txt:12` — the repo's existing nflverse client; David's docs name `nfl_data_py`, which is NOT in the stack and is not added)** per source-adapter rules: raw snapshot written before parse, source timestamp + parser version + completeness flags attached, stale/missing → named fail-closed caveat, never silent substitution. Seasons 2015–2025, QB scope. **No new ML dependencies**: Ridge-first for a ~300-row sample (Codex probe: QB feature store = 326 rows, 2018–2023 + 2025 with a **2024 gap**, 264 labeled) — XGBoost/LightGBM are unjustified at this N and are not added.

**D2 — Sleeper-scored QB PPG label table (`src/dynasty_genius/features/qb_ppg_labels.py`).** PPG computed from box-score components under the league's exact scoring, **derived from a versioned settings snapshot + hash, never hardcoded** — a live correction already caught this way: the research doc's backtest assumes INT = −1, the league scores `pass_int = −2.0` (`app/data/league_snapshots/sleeper_universe_snapshot_latest.json`, probe-verified 2026-07-16). Versioned table keyed player-season with games, dropbacks, completeness flags; fail-closed validation (duplicates, non-finite, missing games); **no 200-dropback inclusion filter** — it would survivorship-bias away exactly the bust/bench outcomes the study must see (Codex finding 8); low-volume/injury/missing-next-year outcomes get explicit named handling instead.

**D3 — H1–H5 walk-forward study (extends `src/dynasty_genius/eval/`).** Fold contract (expanding vs rolling) **pre-registered, not chosen after seeing results**; train ≤ t−1, predict t; models: naive carryforward baseline, market baseline (H5 — market values in the **baseline lane only**), H1 efficiency, H2 rushing, H3 volume, H4 composite (Ridge/regularized; features exclude ALL market-derived values — the doc's "KTC as a feature" recommendation is constitutionally severed; H4 = the declared football-feature union ONLY, disjoint manifests per hypothesis). The 2024 feature-store gap is handled by a named policy (backfill via D1 or an explicitly skipped fold), never silently. Metrics: per-fold Spearman + RMSE/MAE + top-6/12/24 hit rate with BCa CIs and paired deltas; named `fold_starved` below a minimum-n floor; **no winner may be declared when power gates fail**. Case-level panel REQUIRED: Daniels/Nix 2024, Mayfield 2025, Richardson 2025, Maye 2025, **and the ex-ante Allen-2019/Richardson-2024 twin test of the efficiency screen** (both outcomes reported, no cherry-pick). NOTE: this is a **new validation-only prediction head** — the existing harness driver is coupled to the Engine B feature/target contract (`backtest_harness.py:42`) and the qb_v3 driver is a classifier; fold isolation/BCa/metric patterns are reused, the drivers are not. Frozen `qb_v2` and NOT-PROMOTED `qb_v3_candidate` artifacts and registry pointers are untouched.

**D4 — Pre-registered DP-proxy market-delta study.** The DynastyProcess path is not just precedent — **the loader exists** (`scripts/load_dynastyprocess_archive.py`; Codex probe: 2,185 DP rows across four dates, 2021–2024), so H5/delta folds are computable against those four dates today. `dynastyprocess_ecr_2qb` labeling mandatory; raw files gitignored; GPL-3.0 boundary respected; market snapshots must be dated on/before the prediction date (after-date joins fail). Registration doc (hypotheses, thresholds, metrics) committed and hash-pinned BEFORE the study runs; the runner refuses to execute without a matching registration hash. Honest framing baked into every output: this tests model-vs-**expert-consensus**; the trade-market verdict remains accrual-gated (~Dec 2026, Gate-4). KTC is NOT touched (ruled out-of-spec 2026-05-30; the doc's KTC-history backtest is not computable as written and is not attempted).

All outputs `decision_supported=False` recursively; report artifacts land under `app/data/backtest/qb_validation/` (gitignored, backup-manifest-covered if irreplaceable) + a committed summary doc only on David's word.

## 3. Out of scope (named, not hidden)

1. **The valuation engine (DCF value-over-replacement, archetype survival curves, discount slider)** — increment 2; its scale/discount design belongs in the PVO-scale solutioning session (it is a live candidate for deliverable (iii), market-comparable normalization). Building it before QB-1 reports would be building on uncomputed numbers.
2. **Any Engine B QB model change or promotion** — frozen qb_v2 stays the anchor; qb_v3_candidate stays NOT PROMOTED; a promotion needs its own pre-registered bake-off.
3. **Any David-facing surface (delta card, buy/sell anything)** — increment 3, design-gated; Buy/Sell/Hold tiers as proposed violate the No-Verdict Line and do not ship in that form regardless.
4. **KTC integration (live or historical)** — previously ruled out-of-spec; re-opening is a named David decision, and its absence will surface by name in the study's source disclosure, not as a mystery.
5. **Replacement-basis change** (league-derived QB24 vs model-defined constants at `pvo_assembler.py:471-491`) — a real fork the valuation increment must put to David; untouched here.
6. **In-season cadence/refresh design** — meaningless until the study exists; season-aware cadence rules apply later.

## 4. Falsification seeds — the RED matrix (Codex authors the binding RED)

Test path: `tests/contract/test_qb_validation_program_red.py`. All hermetic — injected fixtures/seams, no network, no gitignored artifact asserted (drive functions directly; monkeypatch paths).

| Seed | Input/state | Required behavior |
|---|---|---|
| F1 | adapter fetch with source unavailable/stale fixture | named fail-closed caveat; raw snapshot absent ⇒ no parsed rows; never silent substitution |
| F2 | fold construction fed a feature row containing year-t data for a year-t prediction | rejected loudly (leakage guard), fold aborts with named error |
| F3 | H4 feature-spec containing any market-derived column (ktc/fc/dp/adp aliases) | banned-column scan fails the build; market columns legal ONLY in the baseline lane |
| F4 | hand-computed golden PPG rows under league scoring fixture (incl. rush-TD-heavy + INT-heavy edge rows) | D2 output matches exactly; scoring read from settings, not constants |
| F5 | rookie row with no NFL history entering the veteran model path | rejected to the prior/routing lane, never silently scored |
| F6 | fold with n below the floor | emits named `fold_starved`, no point estimate; metrics always carry BCa CIs |
| F7 | D4 runner invoked with absent/mismatched registration hash | refuses to run, named `preregistration_missing` failure |
| F8 | DP history row lacking `dynastyprocess_ecr_2qb` provenance | fail-closed rejection |
| F9 | every emitted artifact root + nested models | `decision_supported=False` exactly; banned-language scan (buy/sell/hold/verdict lexicon) clean |
| F10 | report generation without the required case-level panel (incl. the Allen/Richardson twin pair) | report build fails — the panel is contractual, not optional |
| F11 | duplicate player-season / non-finite PPG / missing games in the label table | D2 validation fail-closed with named reasons |
| F12 | any hardcoded age constant introduced on the model code path | guard test fails (aging enters only via versioned curve artifacts with provenance) |
| F13 | report generated without the archetype threshold-sensitivity panel (binary dual-threat gate vs continuous rushing-volume moderator, boundary cases ±1 yd/g around the threshold) | report build fails — Gemini lane finding 2026-07-16: a hard archetype threshold creates cliff artifacts at the boundary; the study must quantify the sensitivity, and the existing binary `is_dual_threat` flag (`feature_assembly.py:250-269`) is in scope of the panel |

## 4b. Codex-lane RED seeds (received 2026-07-16, evidence-cited; Codex owns RED authorship)

Codex's independent review contributed seeds beyond F1–F13, adopted here by reference: frozen-artifact hash pins (qb_v2 registry pointers unchanged); recursive market-column rejection incl. FantasyCalc/DP/ADP aliases; exact scoring-settings hash asserting `pass_int = −2`; train-season < test-season with imputers/scalers fitted on train only; explicit expanding-vs-rolling fold contract; no dropback survivorship filter; separate rookie route with no same-season NFL-stat leakage; disjoint per-hypothesis feature manifests; continuous rushing fields required (no silent scramble/designed proxying); no age discontinuity at 29/33/36/37 and no forced terminal-zero age; market snapshot dating ≤ prediction date; paired-delta + BCa + minimum-evaluable-fold gates with no winner on failed power gates; static xVAR unchanged with any intrinsic-VOR output versioned + basis-stamped; recursive banned-verdict scan; unclamped negative deltas and ranges.

## 5. Sequence (cockpit-TDD)

1. Cockpit CLEAR on this spec (Codex technical; Gemini advisory — both lanes' independent reads of David's source docs are COMPLETE and consolidated; the spec itself still needs its own CLEAR cycle).
2. **David authorizes** the increment + the `src/dynasty_genius/eval/` allowlist amendment (new eval files require the exact-set allowlist at `tests/contract/test_subsystem_4_audit.py:106` — a David-authorized amendment, per Codex) + the DP-study pre-registration, each by name. No new dependency PR is needed (nflreadpy is already in the stack; no ML deps added).
3. Codex authors the RED (F1–F12+), demonstrably red on `main`.
4. Claude GREENs; focused suite + full closeout gate (locked eval surface touched); self-probes the falsification matrix.
5. Codex independent review with cited evidence → CLEAR.
6. **Only then, David-authorized:** commit/PR/merge; CI is the merge gate. Study execution and any committed summary are separate David words.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Small-N inconclusiveness (~25–30 QB-seasons/fold) — the likely honest outcome is "H4 not separable from H2 within CIs" | BUILD-4 precedent normalized this; `fold_starved` + CIs everywhere; the study's value is calibrated truth, not a promotable verdict |
| DP-proxy conflated with a trade-market edge claim | mandatory framing string in every D4 artifact; Gate-4 stays the trade-market gate |
| Garden-of-forking-paths in the delta study | F7 pre-registration hash gate |
| nflverse data drift/schema change | raw snapshots + parser version per adapter rules; re-parse is replayable |
| Scope creep toward the engine/surface | §3 parking lot; increments 2–3 open only on David's word after QB-1 reports |
| Cost | Codex estimate: 5–8 focused days Ridge-first scope (this spec); 8–12 days for the documents' full ambition (PROE/pressure features, rookie submodel, discounted-VOR evaluation) — the delta is why increment 2 is gated, not bundled |
| 2024 feature-store gap distorts folds | named gap policy in D3 (backfill or explicit fold skip); never silent |
| The efficiency screen's ex-ante indistinguishability (Allen/Richardson twins) invalidating the bust-gate design | F10 makes the twin panel contractual; if the screen fails it, that finding gates increment 2's design |
