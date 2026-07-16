# QB Research Synthesis — Evidence-Graded Brief on David's Prediction + Valuation Research Pair

**Date:** 2026-07-16 · **Author lane:** Claude Code (spokesperson) · **Status:** v3 — ALL THREE LANES CONSOLIDATED (Claude synthesis; Gemini product-edge received ~09:1x ET; Codex technical received ~09:4x ET after one infrastructure-failed attempt). Each lane read David's originals independently, unanchored. Ready for David.
**Sources under review:** `docs/strategies/2026-07-16-david-qb-prediction-research.md` (David-authored, deep research; five hypotheses H1–H5 + backtest design) · `docs/strategies/2026-07-16-david-qb-valuation-research.md` (David-authored, deep research; discounted value-over-replacement engine + market delta). Both self-flag their backtests as **directional, not computed** — the prediction doc: "the per-model error metrics in this report are reasoned estimates, not computed outputs"; the valuation doc: "treat the results above as directional validation, not a statistically closed proof."

## Question and scope

Should Dynasty Genius open a QB-focused thread building (a) an upgraded QB prediction model and (b) a discounted value-over-replacement valuation engine with a model-vs-market delta — and in what sequence relative to the current board (Morning Tape G4, PVO-scale solutioning)? This synthesis grades the evidence, maps architecture fit, and assesses what numeric validation is actually computable in-repo. It is a map for David's decision, not a build authorization.

## Themes, with evidence grades

**T1 — Rushing volume is the stickiest QB signal (y/y ≈0.80–0.89; strongest next-season PPG correlate ≈0.576).**
Sources: 4for4 correlation table, PFF rushing study, Fantasy Points (Ryan Heath) — three independent external shops converging, cited with numbers. Grade: **Provisional** — externally multi-sourced and mechanistically coherent (rushing scores 0.1/yd vs 0.04/yd passing; 6-pt rush TD), but **not reproduced in-repo** under our exact Sleeper scoring. Cheap to reproduce (see falsification seeds).

**T2 — Passing-TD rate regresses hard (y/y ≈0.26; 90.2% of +1.0pp overachievers regress).**
Sources: 4for4, FanDuel Research. Grade: **Provisional** — same status as T1; the Mayfield 2024→2025 case is consistent but is one case.

**T3 — H4 (composite ML) beats every single-factor model and the market baseline.**
Source: the prediction doc's own reasoned backtest — explicitly not computed. The case studies (Daniels, Nix, Mayfield, Richardson, Maye) are illustrative and selected after the fact. Grade: **Hypothesis.** This is the load-bearing claim of the prediction doc and it is exactly what the in-repo walk-forward must test. BUILD-4 precedent is a live warning: our own qb_v3_candidate ranked well (AUC .67–.78) but was honestly NOT PROMOTED because CIs spanned zero at n≈33/fold — expect the same small-N reality here.

**T4 — QB aging is bimodal by archetype (rushing decay after ~29; pocket-passer plateau into late 30s), and the market prices it archetype-blind.**
Sources: aggregate age distributions, the 500+-rush-yard-after-29 scarcity count, Adam Harstad's mortality-table framing (Harstad is a constitution-validated analyst source), Koalaty Stats on market age-blindness, Stafford-at-37 case. Grade: **Provisional** for the bimodal aging shape; **Hypothesis** for "the market misprices it" (that is the edge claim — unvalidated by definition until a pre-registered study). Constitutional note: any implementation must be a **fitted archetype-conditional survival curve**, never a hardcoded fade-at-29 — hard cliffs are display warnings only (constitution, Locked Rulings), and the current QB display warning is age 33.

**T5 — Discounted multi-year value-over-replacement is the right valuation structure (d≈12–18%, default 15%).**
Sources: practitioner convention (Footballguys, DraftSharks 3D). Grade: structure **Provisional** (it is standard asset-pricing logic and extends our existing xVAR naturally); the **15% number is Hypothesis** — folklore-calibrated, not fitted. A fitted alternative exists: imply the discount rate from observed pick-value/trade behavior rather than assume it.

**T6 — The model-vs-market delta is the product.**
Grade: **Validated as product direction** — this is DG's David-ratified core thesis (the Value Board margin column) independently re-derived by David's research. The **edge claim stays Hypothesis** per the Gate-4 posture: descriptive margin now, no proven edge until pre-registered validation on accrued forward data.

**T7 — Three market sources triangulated, divergence-as-signal (KTC sentiment / FantasyCalc trades / DynastyProcess consensus).**
Grade: **Provisional** concept with major repo-state qualifications: FantasyCalc live + daily forward capture is LIVE; DynastyProcess git-history ingestion has David-approved precedent (2026-05-30 W1 cycle: `dynastyprocess_ecr_2qb` labeling, gitignored raw files, GPL-3.0 caveat) **but is an expert-consensus proxy, not a trade market**; **KTC was ruled out-of-spec 2026-05-30 (no API; scraping forbidden; 0.5-PPR baseline mismatch in the available export)** — re-opening KTC is a new-external-source escalation, David's call, not a default.

## Where the documents conflict with standing law (must be reconciled in any spec)

1. **KTC as a model feature.** The prediction doc's recommended architecture includes "KTC value as a feature" and "blend the model output with the market value." This is a **direct violation of the locked KTC ruling** — market-derived values never enter Engine A/B features; blending market into the served model value breaches the market-overlay wall. The constitutional shape: market as **benchmark** (H5 as a baseline-to-beat is not only legal but required by the Backtesting ruling) and as **overlay delta** — never as feature, never blended.
2. **Buy/Sell/Hold signal tiers.** The valuation doc's Delta thresholds ("Buy ≥ +15%, Strong Buy ≥ +30%...") are **No-Verdict Line violations** as running-software output. The doc's own staging ("informational until the backtest clears a bar") aligns with pre-registered-validation-earns-decision-grade — but the surfaced form stays descriptive (signed delta, disclosed basis, receipts) regardless, and any decision-grade promotion is a David-ratified event.
3. **Hardcoded age cliffs.** "Begin fading the rushing component at age 29" must become a fitted curve parameter, not encoded law (Locked Ruling: Aging Curves).
4. **Replacement-level basis.** The valuation doc proposes a live-league Sleeper-derived QB24 replacement; current xVAR uses model-defined per-position constants (`pvo_assembler.py:471–491`), and a prior review explicitly rejected "league-derived replacement" copy. Real design fork — surface to David, don't silently pick.
5. **Dependencies/sources.** The docs name `nfl_data_py`; the repo's nflverse client is **`nflreadpy` (installed, `requirements.txt:12`)** — same data, existing stack, no new dependency (Codex lane, probe-confirmed by Claude). XGBoost/LightGBM are not in the stack and stay out: Ridge-first at ~300 rows. The DynastyProcess loader already exists (`scripts/load_dynastyprocess_archive.py`; 2,185 rows / four dates 2021–2024 per Codex probe).

## Disagreements between the two documents (small but real)

- The prediction doc recommends market-as-feature; the valuation doc uses market only as the comparator (the valuation doc is closer to DG law).
- Stafford's 2025 PPG appears as 21.1 in the prediction doc vs 20.2 in the valuation doc; Maye 21.2 vs 20.7. Different external sources — neither should be inherited; the computed backtest derives PPG from play-by-play under our exact league scoring.

## Falsification seeds (what would refute the load-bearing findings)

- **F-T1:** Compute y/y stability for rush att/g, rush yd/g, PPG, TD rate 2015–2025 under Sleeper scoring. Refuted if rushing stability lands materially below the cited 0.80 band or below prior-PPG stability.
- **F-T3:** The full H1–H5 walk-forward. Refuted if H4's Spearman/top-12 advantage over H2 and the carryforward is inside the BCa CI noise — the honest outcome BUILD-4 already taught us to expect.
- **F-T4:** Fit archetype-conditional survival on 2000–2025 QB seasons. Refuted if the rushing-QB hazard at 29–30 is not separable from pocket passers at the same ages.
- **F-gate (the sharpest one): the Allen/Richardson twin problem.** The efficiency bust-screen that "correctly" flags Richardson (47.7% comp) would plausibly have flagged **2019 Josh Allen** (sub-60% completion, contemporaneous sell takes cited in the valuation doc itself) — the doc counts Allen as a buy WIN and Richardson as a sell WIN, but what separates them **ex ante**? If the screen can't distinguish them on information available at the time, its false-positive rate on young rushing QBs may erase the edge. This must be a named test case in any backtest.
- **F-T5:** Fit the implied discount rate from observed dynasty trade/pick behavior; refuted if far outside 12–18%.
- **F-T7:** Pre-registered DP-proxy delta study (2021–2024): buy/sell hit rate vs a market-neutral baseline. Refuted if buys don't beat baseline. Caveat inherited from the W1 cycle: this tests model-vs-**expert-consensus**, not model-vs-trade-market; the trade-market verdict stays accrual-gated (~Dec 2026, Gate-4).

**Cheapest next probe:** the stability table (F-T1) — a read-only local computation on the existing `nflreadpy` stack; it quantifies the single assumption everything else stands on. NOT run this session (research review only).

## Architecture-fit summary

**The concrete gap the research exposes (verified):** the frozen Engine B QB model consumes NO continuous rushing-volume feature. `ENGINE_B_FEATURES_QB` = base (age, ppg, games, snap share, aging-curve state, t−1/t−2 history) + `epa_per_dropback`, `cpoe`, `dakota`, `is_dual_threat` (`src/dynasty_genius/models/engine_b_contract.py:159-161`); rushing enters only as the **binary** `is_dual_threat` threshold flag (`feature_assembly.py:250-269`) and implicitly inside fantasy PPG. If the external stability claims (T1) reproduce in-repo, qb_v2 is missing its strongest *legal* feature class (rushing volume is NFL usage — an allowed Engine B class). Any feature addition remains a human-gated, pre-registered promotion — which is exactly what the QB-1 computed study would justify or refute.

**Reusable today:** walk-forward fold machinery + Spearman/Kendall with BCa CIs (`src/dynasty_genius/eval/`); BUILD-4 cohort-prior table as the rookie prior; FantasyCalc forward capture + divergence artifact + Value Board margin column as the delta's home; league-context layer for the contender/rebuilder posture (the architecture doc explicitly wants posture to propagate without touching training data — the valuation doc's per-team discount slider fits this cleanly).
**New:** PPG regression target + label build (the existing harness predicts binary role-survival, not PPG — verified; the general driver is also coupled to the Engine B contract at `backtest_harness.py:42`, so this is a new validation-only head reusing fold/CI/metric patterns, not a rerun); archetype classifier; fitted survival curves; the discount engine (a deterministic overlay transform on frozen projections — model-anchor safe by construction); an `nflreadpy`-based stat-ingestion adapter (one adapter, raw snapshots, per source-adapter rules; 2015–2025, and the feature store's 2024 gap gets a named policy).
**Synergy flag:** the DCF engine produces a market-comparable value scale as a side effect — it is a concrete candidate answer to **deliverable (iii) of the already-named PVO-scale solutioning session** (market-comparable normalization), pilotable at QB. These two threads should be sequenced together, not independently.

## Gemini product-edge lane (advisory, attributed; received 2026-07-16 ~09:1x ET)

Gemini reviewed David's originals independently (no anchoring on this synthesis) and web-verified the load-bearing 2025-season claims as-of 2026-07-16: **Stafford 4,707 yds / 46 TD, 2025 AP MVP at 37 — verified; Mayfield 41→26 TD regression — verified; Maye's sophomore line (4,394/31 + 450 rush) — verified; Richardson benched for Daniel Jones August 2025, season ended by an orbital fracture — verified.** Its distinct findings, all advisory:

1. **Binary-archetype cliff risk (new, and real).** A hard dual-threat threshold (~4–5 carries or ~25 rush yd/g) creates an artifact at the boundary — a 24-yd/g QB ages "gracefully," a 26-yd/g QB gets the post-29 decay. Recommendation: a **continuous rushing-volume moderator** on the survival curve, not a binary gate. (Repo note, Claude: the current `is_dual_threat` feature is exactly such a binary threshold flag — `feature_assembly.py:250-269` — so this critique applies to the existing stack too.)
2. **Designed-rush vs scramble split** for aging: scramble production decays later and tracks pocket navigation, not foot speed; the decay model should distinguish them (charting-data dependent).
3. **Rookie-year utilization stabilizes fast** even though rookie PFF passing grade doesn't (R²≈0.10) — don't let the "noisy rookie year" finding discard rookie usage/structural metrics.
4. **No-Verdict convergence:** independently flags Buy/Sell/Hold tiers as a direct 00 violation (treated here as an advisory restatement of existing law, not a new ruling).
5. **Discount slider framing:** auto-suggest from Sleeper standing/roster age is right, but label it descriptively ("strategic horizon"), never "Contender/Rebuilder Mode" as a system-declared identity.
6. **Missing angles:** (a) **forced-cut coupling** — acquiring a QB costs a roster spot; the shipped Roster Capacity / forced-cut-penalty infra should join the valuation view rather than the engine valuing in a vacuum; (b) **dynamic replacement** — league-scoped QB24 from live Sleeper state vs a static constant (feeds the replacement-basis fork in §"conflicts", it does not settle it); (c) **Superflex illiquidity friction** — startable QBs trade at a premium to index values; any delta-to-action translation must carry a friction caveat. Claude scope note: Gemini's "trade viability rating" phrasing would itself need No-Verdict-safe framing if ever built.
7. **UX:** the delta belongs in the Daily Open macro answer in manager prose; model-blue/market-amber lane isolation holds; uncertainty bands rendered visually, not as diagnostics.

## Codex technical lane (independent, evidence-cited; received 2026-07-16 ~09:4x ET)

Codex reviewed unanchored (its harness's first attempt died on a transient command-host outage; it correctly refused to review without bootstrap and completed on retry). Findings, all with `file:line` or probe evidence:

- **Two BLOCKERs converging with the Claude lane:** KTC/market as an H4 feature or blend (banned at 00:119, 01:268, enforced at `engine_b_contract.py:191`); Buy/Sell/Hold tiers (banned at 00:154, 01:283).
- **HIGH — hard age/archetype cliffs** (age-29/36–37 terminal curves) conflict with the fitted-continuous law; archetype survival is compatible only if estimated, continuous, versioned, uncertainty-bearing.
- **HIGH — dynamic QB24 VOR forks the unified valuation basis** (static xVAR at `pvo_assembler.py:471`): a discounted-VOR engine must be a separately versioned candidate head/overlay or a governed PVO-contract amendment — it may not silently coexist as a second "true value."
- **HIGH — a new validation-only PPG head is required:** qb_v2 is the active frozen artifact (`app/config/model_registry.json:81`); qb_v3_candidate is a NOT-PROMOTED classifier; neither may be altered or made to serve.
- **HIGH — the H4 "winner" is unsupported** until pre-registered paired metrics are computed (the docs say so themselves).
- **HIGH — the docs' scoring target is wrong for this league:** the backtest assumes INT −1; the league scores `pass_int = −2.0` (probe-verified against the live Sleeper snapshot by both Codex and Claude). Targets must derive from a versioned settings hash.
- **MEDIUM — under-specified temporal/cohort rules:** expanding-vs-rolling, injuries, rookies, missing-next-year; and the docs' 200-dropback filter would **survivorship-bias away the bust/bench outcomes** the model most needs to learn.
- **Feasibility/cost:** computable in-repo but not by rerunning BUILD-4 — QB feature store has 326 rows (2018–2023 + 2025, a 2024 gap, 264 labeled) and only the binary `is_dual_threat`, no continuous rushing volume; the repo client is `nflreadpy` (not `nfl_data_py`); XGBoost/LightGBM absent and unjustified at ~300 rows → Ridge-first; DP archive loadable today (`scripts/load_dynastyprocess_archive.py`, 2,185 rows / 4 dates 2021–2024) so H5 runs vs DP, not vs unobtainable KTC history; new `eval/` files need a David-authorized allowlist amendment (`tests/contract/test_subsystem_4_audit.py:106`). **Estimate: 5–8 focused days (Ridge-first scope) / 8–12 days (the documents' full ambition).**
- Codex also contributed the RED-seed list adopted into the proposed spec §4b, and separately confirmed the morning's two state-doc commits zero-divergent.

## Recommended next cockpit action (David sequences)

1. **QB-1 — Numeric-validation increment (recommended first):** spec + build the computed backtest both documents defer: ingestion (2015–2025), stability table, H1–H5 walk-forward vs the two constitutional baselines (carryforward, market), pre-registered DP-proxy delta study. Research-only, no product surface, no model promotion. **Codex-estimated 5–8 focused days.** Proposed spec drafted at `docs/superpowers/specs/2026-07-16-qb-validation-program-design.md` (DRAFT — needs its own cockpit CLEAR cycle, then David's authorization).
2. **QB-2 —** fold the valuation-engine scale/discount design into the PVO-scale solutioning session rather than running a parallel scale effort.
3. **QB-3 —** the QB delta surface (descriptive card: signed delta, archetype receipt, efficiency-screen flag, current/future split) only after QB-1 reports, through the full design gates.

Interleaving with Morning Tape G4 is David's call; QB-1 is offline compute and does not touch the tape thread.
