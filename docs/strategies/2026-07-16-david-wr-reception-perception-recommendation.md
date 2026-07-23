# Formal Recommendation: Reception Perception Adoption for Dynasty Genius WR Valuation

**To:** Engineering, Product, UI/UX
**From:** David (Owner), via research advisor
**Date:** July 16, 2026
**Status:** Approved direction, pending Phase 2 backtest gate
**Scope:** Single-user application. No commercial redistribution of any third-party data.

## Decision

Adopt Reception Perception (RP) as a supplemental analyst layer and a candidate feature set for WR valuation. Do not adopt it as a foundational data source. Build the WR valuation engine on public and already-licensed data first, then test whether RP metrics earn model weight through our own backtest. RP graduates from "informational" to "load-bearing" only if it passes that gate.

## Background

Reception Perception is Matt Harmon's manual WR charting project, running since 2014. It charts every route over an 8-game sample per receiver and produces success rate vs coverage (SRVC, split by man/zone/press/double), success rate by route, route participation, alignment, contested catch, drop, and tackle-breaking data. Its core value: it measures separation ability independent of quarterback play and situation, which is the WR analog of what rushing volume is to QB valuation, a talent signal the market prices poorly because the market prices production.

Constraints that shape this recommendation:
1. Coverage is partial. Roughly 50-90 WRs charted per year, chosen by the analyst. Our engine must value the full WR universe.
2. Predictive value is unproven at scale. Unlike our QB inputs (published year-over-year stability figures), SRVC has no public backtest showing it adds power beyond draft capital, target share, yards per route run, and age.
3. Single-rater, small samples. One analyst's judgment on 8-game route samples. Usable as a prior, not as an unaudited regression input.
4. Access is subscription-based with no API. Acquisition must be legitimate: subscription plus manual entry, or a direct data request to the author. No scraping.

## Recommendation Details

### Phase 1: Foundation (build now, no RP dependency)
The WR valuation engine mirrors the approved QB architecture: multi-year production forecast times archetype-aware longevity, discounted (15% default, contender/rebuilder slider), minus replacement level, compared against market (KTC, FantasyCalc, DynastyProcess) to produce buy/sell deltas. Core WR inputs: target share, yards per route run, targets per route run, breakout age, draft capital, age curve, and market values. All sourced from nfl_data_py, DynastyProcess, FantasyCalc API, KTC, and existing PFF access.

### Phase 2: RP as candidate features (test before trusting)
Acquire RP data legitimately (top-tier subscription; owner will pursue a direct historical-data request to the author). Manually key the sortable tables into our database, roughly 90 players by a dozen fields per season, backfilling as many historical seasons as obtainable. Join to subsequent fantasy outcomes and run the same walk-forward validation used for QBs: does adding SRVC-family features improve out-of-sample rank correlation and top-24/top-36 hit rate, especially for WRs in years 1-3 where production data is thin? Keep features that earn weight. Drop features that do not. Publish the result to the team either way.

### Phase 3: RP as analyst layer (ship regardless of Phase 2 outcome)
Add a manual "conviction adjustment" field to every WR valuation. The owner reads RP profiles and applies a bounded nudge (suggest plus or minus 15% of intrinsic value, logged with a note and date). This captures the scouting value of RP without making the automated pipeline depend on it.

## Team-Specific Directions

**Engineering**
- Schema: WR feature store keyed on player-season; RP fields nullable by design. Missingness is expected and is itself informative (RP charts relevant players), so include a "charted by RP" boolean as a feature.
- No scraping of receptionperception.com. Build a simple admin form or CSV importer for manual entry of RP tables.
- Reuse the QB walk-forward validation harness for the Phase 2 gate. Metrics: Spearman rank correlation, top-24 and top-36 hit rate, MAE on PPG-over-replacement, measured separately for years 1-3 WRs vs veterans.
- Gate definition: RP features are promoted only if they improve out-of-sample Spearman for the years 1-3 cohort across at least two of three validation folds.

**Product**
- Position RP as a differentiator on young WRs, not a general ranking source. The product story: the market prices production; RP-informed intrinsic value prices talent; the delta is the trade signal.
- Treat Harmon's published dynasty rankings as another market/expert signal (like DynastyProcess), not as raw input. If displayed, display them alongside KTC and FantasyCalc, not inside the model.
- Sequence: Phase 1 ships before any RP work is scheduled. Phase 3 (conviction adjustment) can ship with Phase 1 since it has no data dependency.

**UI/UX**
- WR player card shows: intrinsic value, market value, delta signal, and a clearly labeled "analyst adjustment" chip when the owner has applied one, with the note and date on hover/tap.
- Show RP coverage honestly: a "charted" badge when RP data exists for a player, and nothing implying data exists when it does not. Never render a null RP field as a zero.
- Keep the buy/sell signal presentation consistent with the QB cards (Delta thresholds: buy at +15%, strong buy at +30%, sell at -15%, strong sell at -30%) so the owner reads one visual language across positions.

## Success Criteria
1. Phase 1 WR engine beats both baselines (prior-year carryforward and market values) on out-of-sample rank correlation, matching the QB standard.
2. Phase 2 produces a definitive keep/drop answer on RP features with documented metrics.
3. Phase 3 adjustments are logged and auditable, so the owner can later measure whether his RP-informed nudges added value over the raw model.

## Risks and Mitigations
- **Data acquisition falls through:** Phase 2 is skipped, Phases 1 and 3 are unaffected. The app loses nothing structural.
- **RP features fail the gate:** cost is a few hundred dollars in subscription fees and one evening per season of data entry. Acceptable research spend.
- **Single-source key-man risk:** RP is one person's project and could stop publishing. Because it is never load-bearing, discontinuation degrades nothing.
- **Overfitting risk in the gate itself:** small WR-season sample with RP coverage. Mitigate with the multi-fold requirement and by reporting confidence intervals, not point estimates.

## Summary for Control Tower Distillation
Build the WR engine on public data (Phase 1). Buy and hand-enter Reception Perception data, then let the backtest decide if it earns model weight (Phase 2). Ship a logged manual conviction-adjustment field either way (Phase 3). Never scrape, never depend, always audit.
