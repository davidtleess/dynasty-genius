# Market-value measurement verdict

**Date:** 2026-07-25
**Lane:** Codex, research and verification only
**Authority:** David's Rulings G–J in `/tmp/tower_david_rulings_2026-07-25.md`
**Scope held:** no implementation, ingestion change, database write, commit, push, or wire action

## Bottom line

### 1. The TEP concern is closed for the values we actually hold

**VERIFIED — the current FantasyCalc values are TEP-OFF. No stored TE price is contaminated by TEP.**

FantasyCalc's current client does not encode no premium as numeric `0`; it encodes the off state as `tep=none`. A literal `tep=0` request returns HTTP 404, so the requested numeric-zero comparison is not a valid provider request. The provider-defined comparison is omitted versus `tep=none`.

At 2026-07-25 15:00 UTC I fetched the same endpoint four ways:

| Request | HTTP/result | Evidence against omitted request |
|---|---:|---|
| exact production request, no `tep` | 200, 475 rows | baseline |
| explicit `tep=0` | 404, `Not found` | invalid provider encoding; not a value response |
| explicit provider off, `tep=none` | 200, 475 rows | all 475 identities, `value`, overall rank, position rank, trend, and volatility fields identical |
| explicit provider premium, `tep=te+` | 200, 475 rows | positive control changed all 68 TE values |

The omitted and explicit-off full responses differ only in `maybeTier` on 412 rows. Dynasty Genius does **not** store that field in the forward-capture database or use it in the current divergence artifact. Every field the current pipeline stores is identical.

The latest held snapshot in `app/data/fc_forward_capture.db` contains 475 rows retrieved at `2026-07-25T13:00:02.457843+00:00`. It matched the live omitted request on **475/475 values**, including **68/68 TE values**. Locators: `src/dynasty_genius/capture/fc_forward_capture_driver.py:30-32,44-90`; latest database table `fc_forward_capture_raw`.

**VERIFIED — Tucker Kraft's striking TE1-versus-TE5 comparison is not a TEP artifact.**

| Player | TEP off value | TEP+ value | Off overall rank | TEP+ overall rank | Off TE rank | TEP+ TE rank |
|---|---:|---:|---:|---:|---:|---:|
| Brock Bowers | 7,814 | 8,978 | 8 | 5 | 1 | 1 |
| Trey McBride | 6,440 | 7,400 | 18 | 9 | 2 | 2 |
| Tucker Kraft | 3,428 | 3,939 | 61 | 48 | **5** | **5** |
| Sam LaPorta | 2,959 | 3,400 | 75 | 63 | 7 | 7 |

All 68 TE prices changed under TEP+, and 65 of 68 overall ranks changed, but **zero of 68 TE position ranks changed**. Therefore:

- currency and cross-position comparisons would be wrong under a TEP misconfiguration;
- this snapshot's within-TE rank comparison would be unchanged;
- the current pipeline is not misconfigured anyway.

The earlier premise that a TEP-on ingestion would make “every tight-end comparison” wrong was too broad for a within-position rank mode. It would make the price mode wrong; it need not change within-TE ordering.

Read-only reproducer: `/tmp/codex_market_measurement_probe.py`, SHA-256 `c52a24e1a91d55103dd21e24eb0efc1fcbb148c72317b4bf5808120ac2cf377f`.

### 2. What FantasyCalc measures

**VERIFIED — FantasyCalc is a recency-weighted, settings-adjusted index inferred from completed trades. It is not a projection, a crowd-ranking poll, an offer book, or a discounted production stream.**

The number is a **unitless, rescaled trade-value index**. It is intended to make trade sides comparable under FantasyCalc's model, but one point is not a dollar, fantasy point, win probability, or season of production. The curve is explicitly exponential, not linear, and displayed values include a waiver/bench adjustment. That makes an ordinary linear conversion from xVAR to FantasyCalc points invalid at the top and bottom of the market.

### 3. The market source is sound today, but the current rank comparison is not yet apples-to-apples

**VERIFIED — today's current source is correctly dynasty, Superflex, 12-team, full-PPR, TEP-off, current, and cleanly joined.**

**VERIFIED — roster size and detailed lineup requirements are not matched.** FantasyCalc's published bench adjustment is calibrated to an average **11.3-team, 26.7-roster-spot** league. Our query pins 12 teams but sends no roster-size or starting-lineup shape. The provider adjusts values through a model; it is not a raw subset of only leagues identical to David's.

**VERIFIED — the current divergence does not rank the same population on both sides.** It ranks each matched player against a full model-side cohort and a different full market-side cohort:

| Position | Model cohort | FantasyCalc cohort | Common matched cohort |
|---|---:|---:|---:|
| QB | 47 | 66 | 44 |
| RB | 111 | 109 | 90 |
| TE | 111 | 68 | 65 |
| WR | 199 | 156 | 139 |

Re-ranking both values over the common matched cohort changes the 338 displayed deltas by **10.67 percentile points on average** (median 9.8, maximum 32.2) and changes whether **127/338** players sit outside the 10-point noise band. This is a larger immediate apples-to-apples defect than TEP.

Locators: `src/dynasty_genius/universe_market_divergence.py:22-51,161-162,207-222`; tie method `src/dynasty_genius/services/market_overlay_service.py:46-53`.

**Verdict:** David's worry that the market construct must be understood is founded. The held FantasyCalc values themselves are not presently corrupted. The current rank-vs-rank comparison nevertheless fails the same-population requirement, and a future currency translation must respect FantasyCalc's nonlinear, roster-adjusted scale.

## Evidence vocabulary

- **VERIFIED** — reproduced from code, stored artifacts, a deterministic calculation, a provider response, or a provider's own published material.
- **ARGUED** — an analytical implication with its assumptions stated.
- **UNKNOWN** — the provider or repository evidence does not settle it; the evidence that would settle it is named.

## 1. Which FantasyCalc values Dynasty Genius actually stores

### 1.1 Request and field selection

**VERIFIED.** Both current ingestion paths request:

`isDynasty=true&numQbs=2&numTeams=12&ppr=1`

Locators:

- cache adapter: `src/dynasty_genius/adapters/fantasycalc_adapter.py:20-23`;
- append-only forward capture: `src/dynasty_genius/capture/fc_forward_capture_driver.py:30-32`;
- current settings hash: `e27351d720e9fcf0`, recorded at `app/data/capture/fc_forward_capture_latest_report.json:11` and `app/data/valuation_runtime/market_divergence_refresh_latest_report.json:17`.

FantasyCalc's own current client labels `numQbs=2` as its **Superflex** state. This is not an inference that David literally starts two QBs; it is the provider's API encoding for its Superflex market.

**VERIFIED.** We store the response's dynasty `value`:

- `isDynasty=true` selects the dynasty response;
- forward capture maps only `row["value"]`, ranks, trend, and volatility (`fc_forward_capture_driver.py:44-90`);
- the cache adapter strips `combinedValue`, `redraftValue`, and `redraftDynastyValueDifference` before writing (`fantasycalc_adapter.py:28-35,111-123,153-170`);
- the current divergence reads `entry["value"]` (`universe_market_divergence.py:22-34,67-78,218-222`).

The cache still retains `redraftDynastyValuePercDifference`, but the current divergence does not read it. That is unused metadata, not a blended-price ingestion.

### 1.2 TEP empirical proof

**Provider contract VERIFIED.** FantasyCalc's current public client:

- defines `Off`, `TEP+`, and `TEP++`;
- maps `Off` to the API token `none`;
- always sends a `tep` parameter from its UI;
- sends `tep` alongside `isDynasty`, `numQbs`, `numTeams`, and `ppr`.

Provider client locators as retrieved 2026-07-25:

- `https://fantasycalc.com/chunk-3RJVJPQZ.js` — TEP enum and `Off -> none` mapping;
- `https://fantasycalc.com/chunk-4S4CGCVS.js` — `/values/current` client and query construction.

The public [trade-value chart](https://fantasycalc.com/trade-value-chart) also displays TEP Off as a first-class setting.

**Empirical response VERIFIED.** Omitted and `tep=none` produced identical held fields for all 475 rows. Raw response hashes differ because `maybeTier` differs, not because any stored market field differs:

- omitted response: `/tmp/codex_fc_tep_omitted.json`, SHA-256 `7fbff0d638ab992c6aed8ab5776df430e180160fc096acf2f447245c35e79edc`;
- explicit off: `/tmp/codex_fc_tep_none.json`, SHA-256 `e4066cd82b06371407657ba52eefdc22bff8012e335333e86f377a4b38aedd12`;
- TEP+ control: `/tmp/codex_fc_tep_plus.json`, SHA-256 `e112b1a98c0de6017bd5022b3969985277f23cb4e90eff56f3757227bf4bb401`.

**ARGUED operational risk.** The current values are clean, but omission is a fragile contract. If FantasyCalc changes the omitted default, the response semantics can change while Dynasty Genius's endpoint string and settings hash remain unchanged. A future plan should make `tep=none` explicit and include it in the settings hash. This is a prevention requirement, not evidence of present corruption.

### 1.3 Current payload quality

**VERIFIED, 2026-07-25 response:**

- 475 rows;
- zero missing Sleeper IDs;
- zero duplicate Sleeper IDs;
- zero null values;
- zero position disagreements among the 338 currently comparable model/market players;
- market value ties are limited: QB 0 tied rows; RB 8; TE 4; WR 12.

**VERIFIED current join behavior.** The pipeline joins exact FantasyCalc `player.sleeperId` to the PVO Sleeper ID (`universe_market_divergence.py:22-34,164-180`). Duplicate provider IDs would silently overwrite earlier rows because `_market_lookup` is last-write-wins; no duplicate conflict gate exists. No duplicate is present today.

## 2. Mechanical decomposition of FantasyCalc's number

Primary provider sources:

- [FantasyCalc FAQ](https://fantasycalc.com/frequently-asked-questions)
- [FantasyCalc About](https://fantasycalc.com/about)
- [FantasyCalc trade-value chart](https://fantasycalc.com/trade-value-chart)
- [FantasyCalc trade database](https://fantasycalc.com/database)

### 2.1 Input event

**VERIFIED.** The input is a database of real, completed fantasy trades collected from multiple fantasy sites. It is not:

- a projection model of future player production;
- a Keep/Trade/Cut preference poll;
- an expressed offer that may never be accepted;
- a bid/ask book;
- an expert ranking.

FantasyCalc's live `/trades/count` endpoint returned **6,586,121** on 2026-07-25. The exact count is dynamic and public page counters can lag; it is not part of the value definition.

**ARGUED.** Completed trades reveal prices at which two managers actually agreed, which is stronger behavioral evidence than a preference poll. They are also selected transactions: they omit rejected offers, assets nobody will trade, and the full range of willingness to pay. The result is a central accepted-trade index, not a complete demand curve.

### 2.2 Optimization and filtering

**VERIFIED.**

1. FantasyCalc runs an initial optimization that assigns values so opposing trade packages balance. Multi-player trades are part of the fit; elite players can receive larger values because their observed trades require larger packages.
2. It removes trades whose two sides have large modeled value differences; those outliers do not enter final values.
3. It uses regression techniques to adjust for Superflex, TEP, PPR, and number of teams.
4. For each player it averages implied trade values over time with higher weight on recent trades. The FAQ says every trade shown on the player's graph enters the final value.

**UNKNOWN — exact estimator contract.** The provider does not publish:

- the optimization objective and constraints;
- outlier cutoff or number/share removed;
- exact regression specification, interactions, or source-league weights;
- recency function, half-life, or maximum lookback;
- how sparse-player shrinkage works;
- platform mix and league-quality filters.

These would require provider documentation or code not publicly supplied. The player graph can illustrate relative recency weighting, but cannot uniquely recover the full formula.

### 2.3 Time window and refresh

**VERIFIED.** Recent trades receive more weight, older displayed trades still contribute, and values update multiple times per day; FantasyCalc describes a three-hour update cadence on its current public site.

**UNKNOWN.** No published numerical half-life or fixed time window was found. “Recency-weighted” is the maximum honest precision.

### 2.4 Magnitude and scale

**VERIFIED.**

- The displayed curve is **exponential, not linear**.
- Values are rescaled for ease of use.
- The current response spans 4 to 10,232, with median 1,156.
- FantasyCalc intends package trade arithmetic to use the values, subject to its waiver adjustment.
- The values are not physical units.

**VERIFIED roster adjustment.** FantasyCalc says its calculator adds the value of the bench/waiver asset displaced when a package consumes extra roster spots. Its calibration assumes an average dynasty league of **11.3 teams and 26.7 roster spots**; in a 2-for-1 it treats the displaced player as roughly the 300th asset, worth about **425** index points, and increases the adjustment as more spots are consumed.

**ARGUED interpretation.** A FantasyCalc point is best described as a point in FantasyCalc's current settings-specific trade-value index. Addition has model-defined meaning inside its trade calculator, but not unrestricted economic meaning:

- it is not stable purchasing power through time unless scale stability is demonstrated;
- it is not linearly comparable to xVAR;
- package totals require the provider's roster/waiver correction;
- a 1,000-point difference at the top need not represent the same rank or transaction gap as 1,000 points in the middle.

### 2.5 What beliefs it embeds

**ARGUED.** Because accepted dynasty trades determine the index, it bundles manager beliefs about future production, longevity, injury and role risk, position scarcity, liquidity, age, rookie optionality, roster scarcity, contention windows, and sentiment. The algorithm does not identify those components separately. It is wrong to call the result a verified discounted production stream merely because managers may consider future seasons.

**VERIFIED.** Top players trade less frequently and therefore have higher estimated volatility/sensitivity to individual trades, according to the FAQ. This weakens precision exactly where the exponential curve is steepest.

## 3. Alternatives: what each number actually is

| Source | Data-generating input | Transformation | What the number measures | Source class |
|---|---|---|---|---|
| **FantasyCalc value** | Completed real dynasty trades | package-balancing optimization; outlier removal; setting regression; recency weighting; rescaling; waiver adjustment | settings-adjusted accepted-trade value index | **Trade-derived** |
| **KeepTradeCut value** | Users repeatedly order three assets Keep/Trade/Cut | adapted Elo plus a designed value distribution; trade calculator adds a separate package adjustment | real-time aggregate preference ordering and synthetic scarcity gradient; users are told to rank intrinsic preference “in a vacuum,” not expected trade price | **Crowd-preference index** |
| **DynastyProcess `value_2qb`** | FantasyPros dynasty ECR | `10500 × exp(ECR × -0.0235)` after a LOESS-based 1QB-to-2QB rank transformation | synthetic exponential trade-value curve over expert-consensus ranks | **Expert-consensus transform** |
| **FantasyPros dynasty ECR** | Submitted expert rankings | rank-point aggregation across experts | collective expert ordinal opinion; no native trade-price currency | **Expert-consensus rank** |
| **FantasyCalc dynasty ADP** | Completed startup drafts from sourced leagues | average draft position under selected settings | actual draft-selection behavior, expressed in pick slots rather than trade price | **Draft-behavior index** |

### 3.1 KeepTradeCut

Primary source: [KTC FAQ](https://keeptradecut.com/frequently-asked-questions).

**VERIFIED.**

- Users rank three assets; responses update the database in real time.
- KTC uses an adapted Elo algorithm and shapes values to represent stud scarcity and the gradient from top to bottom.
- Superflex and 1QB are separate response databases.
- The base dynasty input is 12-team, half-PPR, no TEP. TEP is an algorithmic adjustment over that base, not a separately polled TEP market.
- KTC explicitly tells respondents not to answer based on what an asset might fetch in a trade; they should report raw preference.
- Its trade calculator adds a separate “value adjustment” for package/stud/roster effects.

**ARGUED meaning of divergence.** Model-versus-KTC compares our valuation to community preference, not to observed clearing prices. A gap can mean sentiment disagreement even when no real trade at the KTC number exists.

**UNKNOWN.** KTC does not publish the full Elo parameters, weighting, anti-abuse rules, or exact value-distribution mapping. Its terms prohibit scraping/reproducing the full values, and it offers no API/export. That makes it unsuitable as an unlicensed production ingestion source even though it is a useful conceptual benchmark.

### 3.2 DynastyProcess

Primary sources: [DynastyProcess market-values methodology](https://dynastyprocess.com/values/) and [current calculator](https://calculator.dynastyprocess.com/).

**VERIFIED.**

- Base input is FantasyPros Dynasty Expert Consensus Rank.
- Player value is an exponential transform: `10500 × e^(ECR × -0.0235)`.
- The 2QB/Superflex ordering is generated from a LOESS relationship between 1QB and 2QB ADP because the original method did not have a large FantasyPros 2QB consensus.
- The documented base assumptions are a typical 12-team PPR league, a specified starter shape, and roughly 300 rostered players.
- The valuation-factor parameter changes how strongly the curve favors studs versus depth; it is a preference control, not new evidence.

Repository locators for what Dynasty Genius holds:

- source is explicitly labeled expert consensus, not trade market: `scripts/load_dynastyprocess_archive.py:1-15`;
- stored field is `value_2qb`: `scripts/load_dynastyprocess_archive.py:110-149`;
- verification labels `source_family="dynastyprocess_ecr_2qb"` and methodology `fantasypros_ecr_consensus`: `scripts/verify_dynastyprocess_source.py:1-38,88-108`;
- validation source record: `docs/validation/2026-05-30-step5a-dynastyprocess-source-verification.md`.

**ARGUED meaning of divergence.** A model-versus-DynastyProcess result means disagreement with an exponentially transformed expert consensus. It does **not** establish an edge against the transaction market.

### 3.3 FantasyPros ECR

Primary source: [FantasyPros ECR methodology](https://support.fantasypros.com/hc/en-us/articles/115001219327-What-is-ECR-Expert-Consensus-Rankings-and-how-do-you-calculate-it).

**VERIFIED.** FantasyPros aggregates expert cheat sheets with rank points rather than a simple mean rank. The dynasty Superflex page is an ordinal expert consensus. It is not a trade-value scale unless a third party such as DynastyProcess imposes one.

**ARGUED meaning of divergence.** A rank gap is model versus selected expert opinion. A “currency” gap against raw ECR is undefined; any currency conversion is the converter's construction, not FantasyPros evidence.

### 3.4 FantasyCalc ADP

Primary source: [FantasyCalc overview](https://fantasycalc.com/).

**VERIFIED.** FantasyCalc describes ADP as sourced from thousands of leagues. It measures where assets are selected in completed drafts, not their trade price.

**ARGUED meaning of divergence.** ADP is a credible revealed-preference benchmark for startup opportunity cost. It is sensitive to draft-room strategy, roster construction, and snake-pick constraints, so it should not be relabeled as a trade-value index.

## 4. What each approved comparison mode requires

### 4.1 Rank versus rank

**ARGUED contract.** A defensible rank comparison requires:

1. **Same source vintage.** Model and market rows must be frozen at named timestamps; no current model against stale market.
2. **Same league format.** Dynasty, Superflex, 12-team, full-PPR, TEP-off must be explicit. Roster and starter mismatch must be surfaced because it cannot currently be pinned.
3. **Same asset population on both sides.** Rank only the intersection of eligible, correctly joined player IDs under identical activity/position filters. Lane-native full-population percentiles may be shown separately, but their difference is not an apples-to-apples rank delta.
4. **Same position taxonomy.** A player must be classified the same way on both sides. Multi-position eligibility needs a frozen rule.
5. **Same asset type.** Players, exact picks, and generic future picks must not share a rank pool unless the comparison explicitly defines the combined market.
6. **Declared tie policy.** Ties do not make ranks impossible, but they preclude a strict total order. Current code uses midranks. Model ties are material: 2 tied QB rows, 10 RB, 25 TE, and 29 WR in the current modeled cohorts.
7. **Missingness is not zero.** Unmatched, null, inactive, or unresolved assets must be excluded and counted, never assigned a bottom price.
8. **Direction and population are explicit.** Within-position percentile is not an overall dynasty rank. A headline must say which one it is.

**VERIFIED current failure.** Requirement 3 is not met by the shipped universe divergence. The model and market denominators differ, with the quantified 10.67-point average delta change reported above.

### 4.2 Our value translated into FantasyCalc currency

**ARGUED contract.** “Market currency” must mean **FantasyCalc index points under a named settings/vintage contract**, not dollars or intrinsic value. An honest mapping requires:

1. **A raw, unclamped model quantity.** The DVS/xVAR clamp creates many-to-one ties; no mapping can reconstruct headroom that was discarded.
2. **A common matched training sample** with exact identities, positions, timestamps, and league settings.
3. **A nonlinear monotone mapping.** FantasyCalc publishes an exponential curve; a single linear coefficient is structurally wrong.
4. **Position and cross-position discipline.** Separate position mappings improve local fit but destroy the cross-position exchange rate needed for trades. A global mapping needs explicit position/scarcity effects and validation.
5. **Package adjustment separated from player price.** Do not compare a sum of our player values with FantasyCalc's package-adjusted calculator total unless the same bench/waiver displacement is represented.
6. **Out-of-sample validation.** Fit on earlier dates or a training player subset and assess later dates/held-out players. Evaluating “divergence” on the same observations used to calibrate the mapping mechanically shrinks the residual.
7. **Tail and extrapolation rules.** The top of the market is steep and sparse; extrapolation beyond the matched xVAR range must refuse or carry wide uncertainty.
8. **Versioned drift evidence.** Refitting can move the currency scale even when our player value does not. The mapping needs rolling stability checks across the forward-capture history.
9. **Uncertainty.** Report a market-equivalent interval or residual error, not a falsely exact converted point.
10. **No construct laundering.** The translated number is a market-equivalent quote conditional on the calibration. It does not turn xVAR into a market price or prove the market correct.

**Invalid mappings include:**

- linear xVAR-to-FantasyCalc regression;
- fitting on one source and applying to another (for example DynastyProcess history to FantasyCalc current);
- mixing TEP or roster formats;
- fitting per-position curves and then adding their values as if the curves share a common exchange rate;
- using a current cross-section without a vintage/holdout test;
- using FantasyCalc's redraft or combined fields;
- treating an FC point as stable through time without evidence.

## 5. Blind spots: every current route by which “market” can silently differ from David's league

### Settings and league structure

1. **TEP omission — currently clean, contract-fragile.** Omitted equals provider off on all stored fields today. A default change would be silent because `tep` is absent from both endpoint and settings hash.
2. **Roster size — mismatched/unknown.** No roster-size parameter is sent. Published waiver calibration uses 11.3 teams and 26.7 roster spots, not David's exact league.
3. **Starter configuration — not pinned.** Beyond the provider's Superflex/TEP adjustments, the request does not specify David's RB/WR/TE/flex starter counts.
4. **Platform/source mix — UNKNOWN.** FantasyCalc says multiple sites but does not publish the current platform weights. David's Sleeper league may trade differently.
5. **Trade-package shape.** Displayed player values and calculator package adjustments are not interchangeable. A 2-for-1 carries a roster cost a 1-for-1 does not.
6. **Provider regression versus exact subset.** The settings are model adjustments over trade data, not proof that every underlying trade came from a league exactly matching David's.

### Position and population

7. **Different percentile denominators — current material defect.** Model and market cohorts are not the same matched population.
8. **Position reclassification.** No fail-closed guard rejects a Sleeper/FantasyCalc position disagreement. None exists today, but a future mismatch would put the two values in different cohorts.
9. **Picks versus players.** The current response contains 76 `PICK` rows. The position-keyed player divergence keeps them out of QB/RB/WR/TE cohorts, but generic consumers of the same response must preserve that separation.
10. **Tie compression.** Model ties are much more common than market ties, especially at TE/WR. A strict “ours TE1” label can overstate distinction among clamped equal-valued players.

### Identity

11. **Exact Sleeper ID dependence.** Current payload quality is excellent, but the join has no secondary name/team validation.
12. **Duplicate overwrite.** `_market_lookup` silently keeps the last row for a duplicate Sleeper ID. Current duplicate count is zero.
13. **Coverage selection.** 399 of 12,202 universe rows have a market overlay; only 338 have both a usable model and market rank. Conclusions apply to that selected set, not the full league universe.

### Timing and lineage

14. **Fetch time is not provider publish time.** The artifact correctly caveats this (`universe_market_divergence.py:67-78,149-158`), but exact market age inside the provider's three-hour cycle is unknown.
15. **Cache and forward capture have different clocks.** The cache was fetched 2026-07-24 19:59 UTC; the owned current divergence uses the 2026-07-25 forward snapshot. A caller using the cache can disagree with the current artifact.
16. **Settings hash is absent from the divergence artifact itself.** It lives in the refresh report, so a detached artifact reader cannot decode or independently verify its market settings.
17. **Mixed historical instruments share one store.** `app/data/fc_snapshots.db` contains 2021–2024 `dp_archive` expert-consensus rows and 2026 `fc_native` trade-market rows. Consumers must filter and label `source`.
18. **Historical settings hash can overstate equivalence.** `scripts/ingest_market_archive.py:22-24,129-140` stamps the FantasyCalc query hash on imported rows even when the source is DynastyProcess. Source labeling prevents confusion in governed backtests, but a consumer filtering only by hash can mistake expert consensus for the same FantasyCalc market.

### Field selection

19. **Current dynasty field selection is correct.** `value` under `isDynasty=true` is stored; `redraftValue` and `combinedValue` are excluded from the current price path.
20. **Residual redraft-difference metadata exists in the cache.** It is not used today. Future generic consumers must not treat it as a second market value.
21. **Null-to-zero hazard.** The current payload has no null values, but `float(fc_entry.get("value") or 0.0)` at `universe_market_divergence.py:219` would turn a matched null into a real zero. The market cohort excludes nulls, so a future provider null could become a false bottom-ranked player rather than unavailable.

### Provider-method blind spots

22. **Accepted-trade selection bias.** No rejected offers or no-trade assets.
23. **Outlier removal.** Unusual but genuine league trades can be removed; the cutoff is unknown.
24. **Elite illiquidity.** Top values are more sensitive to individual trades.
25. **Unknown decay.** Exact recency half-life/window is unpublished.
26. **Unknown scale stability.** Values are rescaled; one FC point is not proven constant over dates.

## Required evidence before either comparison is approved

This is research guidance, not an implementation plan.

1. Pin a human-readable market contract: `dynasty=true`, provider Superflex, 12 teams, full PPR, `tep=none`, source `fc_native`, retrieved timestamp, and explicit roster/starter caveat.
2. Prove omitted-versus-explicit-off equivalence as a regression fixture over every stored field, then use the explicit setting so a provider-default change cannot hide.
3. For rank mode, produce a common-population report with counts before/after identity, position, activity, model, and market filters; demonstrate both ranks use that exact ordered ID set and one tie rule.
4. Recompute the current artifact on that common population and show every changed signal/noise-band classification. The 127/338 diagnostic above means this cannot be treated as a cosmetic adjustment.
5. For currency mode, pre-register candidate nonlinear mappings, holdout dates/players, stability limits, tail refusal, package-adjustment treatment, and the rule for preserving cross-position exchange rates.
6. Keep FantasyCalc, KTC, DynastyProcess, FantasyPros, and ADP source labels distinct in every artifact. “Market” alone is insufficient because they measure transactions, preferences, expert opinion, and draft behavior respectively.

## Unknowns and what would settle them

| Unknown | What would settle it |
|---|---|
| FantasyCalc recency half-life/window | provider formula/code or a formal methodology statement |
| Optimization objective/constraints | provider technical documentation or code |
| Outlier threshold/share removed | provider technical documentation or audit output |
| Platform mix and league weights | provider data dictionary/lineage report |
| Exact regression and interaction terms for settings | provider model documentation |
| Scale anchor and historical rescaling policy | provider methodology/version history |
| David-versus-provider roster/lineup adjustment | a provider endpoint that accepts those settings, or a separately validated local adjustment |
| Stability of an xVAR-to-FC mapping | forward, point-in-time holdout results across multiple market regimes |

## Final verdict to Tower

**The market side is not blindly wrong. It is understood well enough to say what it is and is not: a TEP-off, dynasty, Superflex, 12-team, full-PPR, recency-weighted accepted-trade index with an exponential, waiver-adjusted scale.**

The TEP fear is **unfounded for the data currently held**, and Tucker Kraft's TE rank is **not** explained by TEP.

The broader concern is **not** unfounded:

- roster size and starter shape are not matched;
- exact provider decay/model details remain proprietary;
- the current rank comparison uses different populations and is materially altered by a common-cohort rebase;
- a linear “market currency” conversion would be structurally wrong;
- historical stores contain distinct instruments that must never be called one generic market.

Therefore no current finding should be withdrawn merely because FantasyCalc was misunderstood, but neither comparison mode is ready to be called apples-to-apples until the population contract (rank mode) and nonlinear calibration/holdout contract (currency mode) are satisfied.
