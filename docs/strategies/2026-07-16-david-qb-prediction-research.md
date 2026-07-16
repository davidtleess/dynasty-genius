# Predicting QB Fantasy Performance for Dynasty Genius: Data Fields, Five Hypotheses, and an Out-of-Sample Backtest

## TL;DR
- For a 12-team Superflex Full PPR dynasty build, the single most predictive and stable signal for future QB fantasy points is rushing volume (rush attempts and rushing yards per game, year-over-year correlation of roughly 0.80 to 0.89), followed by prior fantasy points per game and pass-efficiency metrics like EPA per dropback. Raw passing touchdowns and touchdown rate are the least reliable inputs and should be regressed hard.
- The winning modeling philosophy is a composite gradient-boosted or regularized model (H4) that weights rushing production heavily, adds age and draft capital, blends in EPA/CPOE and ANY/A for a passing floor, and uses dynasty market value (KTC) as both a feature and a benchmark. A pure rushing model (H2) is the strongest single-factor approach and beats the naive prior-year carryforward and a pure volume model.
- The 2024 and 2025 seasons validate the framework: rushing-driven rookies (Jayden Daniels, Bo Nix) and dual-threat vets hit, touchdown-spike pocket passers regressed (Baker Mayfield), and a high-rushing but inaccurate QB busted exactly as an efficiency screen predicted (Anthony Richardson). The backtest here is approximate rather than a fully computed grid, and I flag that explicitly.

## Key Findings

**1. Rushing is the closest thing to a cheat code at QB.** Multiple independent research shops converge on this. 4for4's year-over-year correlation table (2012 to 2022, QBs starting 10-plus games in consecutive seasons) shows rush attempts per game at 0.89 and rush yards per game at 0.85, the two highest of any QB stat. PFF, in "Leveraging Quarterback Rushing Yards Into a Competitive Advantage," found QB rushing yards per game carry a roughly 0.80 year-over-year correlation ("The 0.80 strength of correlation among year-to-year quarterback rushing numbers is amazing"). Fantasy Points' Ryan Heath, testing which stats best predict next-season fantasy points per game, found rushing attempts at 0.576, "the strongest relationship on the list." Rushing points are also worth more per unit: rushing yards score at 0.1 per yard versus 0.04 for passing, and QB rushing touchdowns (6 points) outweigh passing touchdowns (4 points in Sleeper default).

**2. Prior fantasy points per game is a legitimate baseline, but weaker than people assume.** 4for4 pegs QB fantasy points per game year-over-year at just 0.44. It carries real signal ("if a player has already been good, he is likely to be good again") but is materially less stable than rushing volume, largely because it bakes in volatile touchdowns.

**3. Passing touchdowns and touchdown rate regress hard.** 4for4's table shows passing TD per game at 0.38 and touchdown rate at just 0.26 year-over-year. FanDuel Research ("Touchdown Regression: What It Is and How to Use It") found that among the 52 outlier overachievers (QBs beating their expected TD rate by 1.0-plus percentage points), 90.2% saw their touchdown rate drop the following year, by an average of 1.5 points. This is the mechanism behind Baker Mayfield's 2024 spike (a 7.2% TD rate, second in the NFL, versus a roughly 4.5% career mark) and his 2025 regression.

**4. Efficiency metrics form a solid second tier.** SumerSports ("Sticky Stats: Predictive NFL Metrics") found that "Expected Points Added per Passing Attempt has been the stickiest statistic since 2021 (correlation of about 0.60)." Heath's tiering places EPA per dropback, pressure-to-sack ratio, ANY/A, and passer rating in a clear second tier behind rushing and prior scoring, and notes that at QB, unlike other positions, passing efficiency is more predictive than passing volume (passer rating beats total pass attempts). CPOE is relatively stable but limited by charting-data availability.

**5. PFF grade is descriptive first, predictive second, and the rookie year is noisy.** PFF's own research found the multi-year body of work (posterior mean) of PFF passing grade predicts the future better than the most recent season, and that a QB's rookie season carries little predictive power (Year 1 to Year 2 R-squared of only 0.10). This is a direct warning against overreacting to a single rookie campaign in either direction.

**6. Draft capital and age are the best pre-NFL and dynasty-context signals.** First-round draft capital is the strongest predictor of QB fantasy success; over the last decade only a handful of non-first-round QBs (Jalen Hurts, Dak Prescott, Brock Purdy) reached QB1 production. QBs peak roughly ages 25 to 33, with about 67% of QB1 seasons since 2000 coming from QBs age 30 and younger, and dual-threat rushing production falling off notably after age 28 to 29 while pocket passers age more gracefully.

## Details

### Deliverable 1: Data Field Catalog (predictive value and stability)

Fields are organized into tiers by how well they predict next-season fantasy points, with published stability numbers where available.

**Tier 1 (highest predictive value): Rushing volume and prior scoring**
- Rush attempts per game: 4for4 y/y 0.89; Heath's next-season FPG correlation 0.576 (his strongest). The backbone of the "Konami Code" concept (originally surfaced by Rich Hribar). Pull from nfl_data_py rushing data.
- Rush yards per game: 4for4 y/y 0.85; PFF y/y roughly 0.80.
- Rush TD per game: 4for4 y/y 0.56, falling to about 0.46 for QBs with 4-plus rush TDs (some regression at the top). Inside-the-five carry share is valuable but less stable and situation-dependent (Heath).
- Designed rush vs scramble splits: scramble yards have about a 0.61 correlation to next-season designed rush attempts; designed attempts predict themselves at about 0.88 (Heath/Fantasy Points). Requires charting data (FTN/PFF) or play-by-play tagging.
- Prior fantasy points per game: 4for4 y/y 0.44. Also fantasy points per dropback and per opportunity (Tier 1B in Heath's framework).

**Tier 2 (moderate, "real-life results" that gate a QB staying on the field)**
- EPA per dropback / EPA per passing attempt: SumerSports about 0.60 y/y (stickiest efficiency stat). Available directly from nflfastR via nfl_data_py (qb_epa column, which does not penalize QBs for receiver fumbles).
- CPOE: relatively stable and captures accuracy independent of scheme, but nflverse charting inputs are strongest for 2022-plus. Combine into an EPA+CPOE composite as nfeloapp and others do.
- ANY/A (adjusted net yards per attempt): a strong sack-and-turnover-aware passing efficiency measure; available via Pro Football Reference / Stathead.
- Pressure-to-sack ratio and sack rate: sack rate y/y about 0.50 (4for4), sack-avoidance ratios about 0.50 (SumerSports). Bo Nix posted the best single-season pressure-to-sack ratio among all QBs in 2025 (8.9%) and the best career mark since 2021 (11.3%).
- Passer rating: Heath notes it "beats out total pass attempts" for predicting future fantasy.
- Completion percentage: y/y stable at about 0.52 but weak as a next-season FPG predictor (Heath 0.154). Useful mainly as a bust screen at the low end (see Anthony Richardson below).

**Tier 3 (low predictive value in isolation, use only with context)**
- Passing yards per game: 4for4 y/y 0.57 but declining in fantasy relevance as league passing volume falls (2025 saw the fewest pass attempts per game since 2006, lowest dropback rate since 2011 at 59.2%).
- Pass attempts / dropback volume: y/y about 0.52 but prone to game-script inflation (bad defense forces throwing).
- Passing TD per game (0.38) and TD rate (0.26): regress to baseline.
- Yards per attempt (0.31), interception rate (0.27): noisy.
- aDOT, time to throw, deep ball rate, play-action rate, off-target rate: these are "tendency/style" stats that affect pass-catchers more than the QB's own fantasy line, per Heath. Useful as explanatory context, not standalone predictors.

**Contextual and pre-NFL fields**
- Draft capital: strongest QB success predictor; first-rounders return by far the highest hit rate.
- Age / age curve: QB1 seasons concentrated ages 25 to 33; dual-threat rushing declines after about 28, pocket passers last into late 30s (Matthew Stafford was QB3 in 2025 at age 37).
- College production and breakout age: draft capital dominates, but efficiency (sack rate, adjusted yards) thresholds help separate hits from busts for young QBs.
- Offensive context: team pass rate over expectation, offensive line quality, weapons, and OC/scheme changes. Team offensive EPA per play has a strong positive relationship with QB fantasy output. Best used as adjustment factors, not core predictors.
- Dynasty market signals: KTC crowdsourced values (adapted ELO algorithm), DynastyProcess historical values (available through nfl_data_py), and FantasyCalc. Useful as a feature and as a benchmark to beat.

### Deliverable 2: Five Strategic Hypotheses

**H1 — Efficiency-stability hypothesis.** A model built on stable pass-efficiency metrics (EPA per dropback, CPOE, ANY/A) predicts next-season fantasy PPG better than prior-season fantasy PPG alone. Prediction: an EPA+CPOE+ANY/A model beats the naive prior-year PPG carryforward on rank correlation and top-12 hit rate.

**H2 — Rushing floor hypothesis.** QB rushing volume (rush attempts per game, rush yards per game, rush TD share) is the single most predictive and stable component; a model weighting rushing heavily outperforms passing-centric models. Prediction: a rushing-weighted model produces the best Spearman correlation of any single-factor model and beats prior-year PPG.

**H3 — Volume/opportunity hypothesis.** Dropback volume and team pass rate over expectation dominate efficiency; opportunity-based models beat efficiency-based models. Prediction: a dropback-and-PROE model outperforms H1's efficiency model.

**H4 — Composite ML hypothesis.** A regularized regression or gradient-boosted model (Ridge/Lasso/XGBoost) combining age, draft capital, rushing, efficiency, and volume beats any single-factor model and beats simple market signals. Prediction: the composite has the lowest RMSE/MAE and highest top-12 hit rate overall.

**H5 — Market-signal hypothesis.** Dynasty market values (KTC, DynastyProcess) and ADP already encode most predictable information; market-based projections are as good or better than stat-based models. Prediction: the KTC/ADP baseline is competitive with or beats stat models, especially for veterans.

### Deliverable 3: Backtest Against Real 2024 and 2025 Stats

Scoring assumption: Sleeper default (4 pt pass TD, 0.04/pass yd, 6 pt rush TD, 0.1/rush yd, -1 INT). QB "PPR" and standard are effectively identical since QBs almost never catch passes. All PPG figures below are real, pulled from FantasyPros full-season data.

**Actual 2024 QB fantasy PPG (top 12):** Lamar Jackson 25.6, Josh Allen 22.7, Joe Burrow 22.5, Baker Mayfield 22.5, Jayden Daniels 21.5, Jalen Hurts 21.3, Jared Goff 19.8, Bo Nix 19.4, Sam Darnold 18.8, Patrick Mahomes 18.4, Kyler Murray 18.1, Justin Herbert 17.0. (Note: total-points ranks differ from PPG ranks because of games missed; Daniels was QB5 by total points at 364.7.)

**Actual 2025 QB fantasy PPG (top 12):** Josh Allen 22.0, Drake Maye 21.2, Patrick Mahomes 21.2, Matthew Stafford 21.1, Brock Purdy 20.8 (9 games), Trevor Lawrence 20.6, Caleb Williams 19.1, Jalen Hurts 19.1, Dak Prescott 19.0, Justin Herbert 18.7, Bo Nix 18.6, Joe Burrow 17.4 (8 games). Baker Mayfield fell to 16.6 (QB12 by total points).

**How each hypothesis would have done (training on 2020-2023 inputs, blind to the future):**

- **Rookies expose the market and the carryforward.** Prior-year PPG carryforward and any veteran-only model structurally miss rookies. Jayden Daniels (no NFL history) finished QB5 by total points at 21.5 PPG, and Bo Nix finished QB7 at 19.4. Only rushing-aware and draft-capital-aware models flagged them: Daniels was the #2 overall pick with a historic college rushing profile, and both projected for heavy designed-run volume. This is a clear win for H2 and H4 over H3 and H5. Daniels' 891 rushing yards set an NFL rookie QB rushing record and were the ninth-highest single-season total by any QB in NFL history, paired with 3,568 passing yards and 25 passing TDs (Offensive Rookie of the Year).

- **Touchdown regression validated H1's logic against H5.** Baker Mayfield's 2024 QB4 finish (22.5 PPG) was driven by a 7.2% TD rate (2nd in the NFL, on career-high 41 TDs and 4,500 yards) versus his roughly 4.5% career mark. A regression-aware efficiency model would have faded him for 2025, and he duly fell to 16.6 PPG (QB12). The market (dynasty and redraft ADP) largely kept him as a top-7 QB into 2025 and was wrong. Point to H1 and H4, against H5.

- **The Anthony Richardson bust is the key nuance for H2.** A naive rushing-only model loved Richardson (499 rushing yards and 6 rushing TDs in just 11 games in 2024, elite rushing efficiency in his rookie sample). But he posted a 47.7% completion rate, the worst by any qualified passer since Tim Tebow's 46.5% in 2011, and a 54.9% on-target rate that was last in the league by more than 12 percentage points. He finished QB25 and lost his job to Daniel Jones in 2025. The lesson: rushing volume needs an efficiency/accuracy gate (a passing floor). This is precisely why H4 (composite) should beat H2 (pure rushing) at the extremes.

- **Pocket-passer volume can hit but is fragile.** Joe Burrow finished QB3 by PPG in 2024 (22.5) on a league-leading 4,918 yards and 43 TDs with almost no rushing, validating that elite volume-plus-efficiency can overcome zero rushing. But it is fragile: a Grade 3 turf toe injury limited him to 8 games and 17.4 PPG in 2025. Jared Goff (QB6/QB8) is the stable-pocket archetype. This tempers H2's absolutism and supports a composite view.

- **Aging and efficiency both mattered on the vet side.** Matthew Stafford at 37 rode elite efficiency (a league-best 91.7 PFF passing grade, 46 TDs) to QB3 in 2025, showing pocket passers defy age curves when the situation and efficiency hold. Drake Maye's 2025 leap to QB2 (21.2 PPG) was foreshadowed by strong rookie rushing (421 yards) and efficiency, which the dynasty market underrated (he went behind several veterans in 2024 dynasty startups). Another win for rushing-plus-efficiency composites over the market.

**Approximate evaluation-metric read (illustrative, not a fully computed grid):**
- Rank correlation (Spearman) of prior-year PPG carryforward vs actual: moderate for the veteran core (Allen, Jackson, Hurts, Goff repeat) but penalized heavily by rookies and injuries, consistent with the 0.44 y/y PPG stability figure.
- A rushing-weighted model (H2) would have correctly ranked the top of the position (Allen, Jackson, Hurts, Daniels, Nix) and is the best single factor, but mis-ranks Richardson without an efficiency gate.
- The composite (H4) would have the best top-12 hit rate because it captures rookies (draft capital + college rushing), fades TD-spike vets (regression), and screens out inaccurate rushers (efficiency).
- The market baseline (H5/KTC) is a strong veteran benchmark but is beaten on rookies and on regression calls.

I want to be honest that a fully reproducible numeric backtest (exact Spearman, RMSE, MAE per model) requires running the pipeline described below on the real 2020-2025 tables; the figures I gathered support the directional ranking above, but the per-model error metrics here are reasoned estimates, not computed outputs.

### Deliverable 4: Testing Framework Design (implement in Python)

**Data pipeline (all free/public):**
- `nfl_data_py` (`import_pbp_data`, `import_seasonal_data`, `import_weekly_data`) for play-by-play EPA, CPOE (qb_epa and cpoe columns), dropbacks, rushing volume, and computed fantasy points. Aggregate per the standard nflfastR recipe: group by passer and team, average qb_epa and cpoe, count dropbacks, filter to 200-plus dropbacks to control noise.
- `nfl_data_py` also exposes DynastyProcess values and draft-pick data; pull historical dynasty market values from the DynastyProcess GitHub for the market baseline.
- Sleeper API for your league's rosters, scoring, and current player universe; KTC and FantasyCalc for live Superflex market values; PFF and PlayerProfiler for grade and charting overlays where licensed.
- Compute fantasy points yourself from box-score components using your exact Sleeper scoring so training targets match your league.

**Validation protocol:**
- Walk-forward / expanding-window: train on seasons t-3 to t-1, predict season t, then roll forward one year and repeat. This mirrors how you would actually use the model each offseason and prevents leakage.
- Strict no-leakage rules: features for predicting year t may only use data through the end of year t-1 (including market values as of the pre-season snapshot). Never let year-t stats leak into features. Freeze the feature snapshot date.
- Handle rookies explicitly: they have no NFL history, so route them through a separate rookie sub-model using draft capital, age, college rushing/efficiency, and landing spot, then merge onto the veteran model's scale.

**Evaluation metrics:**
- Spearman rank correlation between predicted and actual PPG (primary, since dynasty is about ordering assets).
- RMSE and MAE of predicted vs actual PPG.
- Top-12 hit rate (and top-6, top-24 for Superflex depth), plus calibration curves.
- Case-level checks on breakouts and declines (did the model foresee Daniels, Maye, the Mayfield regression, the Richardson bust).

**Baselines to beat:**
- Naive prior-year PPG carryforward.
- Market baseline: KTC / DynastyProcess dynasty value and redraft ADP.
- Any model must clear both to justify production use.

**Small-sample caveats:**
- Roughly 32 starters means N is tiny; a single season is about 20 to 30 usable QB-seasons. Regularization (Ridge/Lasso) and priors matter more than at RB/WR. Report confidence intervals, avoid overfitting to one breakout, and lean on multi-year posterior means (per PFF's finding that career body of work beats last season).

**Recommended production architecture:**
- Ship H4: a gradient-boosted model (XGBoost or LightGBM) or a regularized linear model, with features weighted toward rushing (attempts/game, rush yards/game, designed vs scramble, rush TD share), prior fantasy PPG and FP/dropback, EPA per dropback, CPOE, ANY/A, pressure-to-sack, age, and draft capital, plus KTC value as a feature. Blend the model output with the market value and shade toward youth and rushing for Superflex.

### Deliverable 5: Verdict

**Ranking of the five hypotheses by out-of-sample accuracy (best to worst):**

1. **H4 (Composite ML) — winner.** It is the only approach that simultaneously captures rookies (Daniels, Nix, Maye via draft capital and college rushing), fades touchdown-spike veterans (Mayfield), and screens out high-volume-but-inaccurate rushers (Richardson). Highest expected top-12 hit rate and lowest error.
2. **H2 (Rushing floor) — strongest single factor.** Rushing volume's 0.80 to 0.89 stability and per-snap scoring premium make it the best one-variable model and the core of H4. Its weakness is the Richardson case: it needs an efficiency gate.
3. **H1 (Efficiency-stability).** EPA/CPOE/ANY/A (EPA per attempt about 0.60 stability) beat the naive prior-year carryforward and correctly flag regression, but they under-rate pure rushers and slightly under-perform rushing on raw rank correlation.
4. **H5 (Market signal).** KTC/ADP is a genuinely strong veteran baseline and hard to beat on established players, but it lags on rookies and on regression calls, and it is what your app is trying to add value over.
5. **H3 (Volume/opportunity) — weakest.** In a league throwing less every year, raw dropback volume is game-script-driven and less stable than rushing or efficiency; it loses to every other approach.

**Why H4 wins and what would change the call:** rushing carries the signal, efficiency provides the floor, draft capital and age handle the players with no track record, and the market keeps you honest. If a future season showed rushing stability collapsing (for example a rules change reducing QB runs) or the market beating your model two years running on out-of-sample Spearman, you would downgrade H2's weight and lean harder on H1/H5.

**Limitations:** N is tiny (about 32 starters), 2025 introduced heavy injury noise at the top (Burrow, Jackson, Daniels, Murray, Purdy all missed significant time), and the per-model error metrics in this report are reasoned from gathered correlations rather than fully computed. The backtest is directionally sound but should be re-run numerically in the pipeline above before you trust exact figures.

**Concrete next steps:**
1. Build the nfl_data_py ingestion for 2015-2025, compute Sleeper-scored PPG and all Tier 1/Tier 2 features, and cache locally.
2. Implement the walk-forward validator with the two baselines (carryforward, KTC).
3. Train H4 (XGBoost + Ridge ensemble) with a separate rookie sub-model; report Spearman, RMSE, MAE, and top-12 hit rate per fold.
4. Blend model output with live KTC Superflex values and expose a "model vs market" delta in Dynasty Genius to surface buy-low/sell-high targets (the Daniels-style buy window, the Mayfield-style sell).
5. Re-fit every offseason and monitor whether rushing stability and market-beating performance hold.