# Valuing Dynasty Quarterbacks as Assets: A Build Spec for Dynasty Genius

## TL;DR
- Value a dynasty QB as **discounted future fantasy value over replacement**: forecast multi-year PPG (rushing volume is the anchor because it is the stickiest QB input at roughly 0.80-0.89 year-over-year, and rushing attempts show the strongest single correlation with next-season fantasy PPG at about 0.576, versus just 0.154 for completion percentage), multiply by expected remaining startable seasons from an archetype-specific aging curve, discount future seasons at about 12-18% per year, and compare the result to the live market price from KTC and FantasyCalc. Buy when your intrinsic value clears market by a set threshold; sell when market clears you.
- The single biggest exploitable inefficiency at QB in Superflex is **archetype-blind aging**: the market prices a 28-year-old rushing QB and a 28-year-old pocket passer similarly, but rushing production falls off a cliff after age 29 while pocket passers stay useful into their late 30s (Matthew Stafford was the QB3 at 20.2 PPG at age 37 in 2025). The second biggest is **recency bias** in both directions (rookie hype inflation and post-breakout overpricing versus injury/benching overshoots like Anthony Richardson).
- For the app: pull stats from nfl_data_py, market values from DynastyProcess (free, historical) plus a KTC/FantasyCalc scrape for live prices, and league context from the Sleeper API. Compute a model-minus-market delta per QB, surface it as a buy/sell signal with a strength tier, refresh weekly in-season and monthly in the offseason, and be honest that the QB sample is small and the market can stay irrational longer than your rebuild window.

## Key Findings

1. **Rushing is the load-bearing input.** Rushing attempts and rushing yards per game are the stickiest QB stats year-over-year, far more stable than passing touchdown rate, which regresses hard to the mean. Rushing attempts carry a roughly 0.576 correlation with next-season fantasy PPG, the strongest single relationship at the position, while completion percentage sits at just 0.154. Fantasy points per dropback and rushing yards per game are the two most predictive inputs for next-season fantasy PPG. A rate above 0.55 fantasy points per dropback signals a likely big season ahead; below 0.45 is a red flag.

2. **QB aging is bimodal by archetype, and the market mostly ignores this.** Top-12 QB seasons cluster at ages 25-30, but the mechanism differs: dual-threat QBs decay when their legs go (sell window 27-28, rushing falls off after 29), while pocket passers can plateau into their late 30s given a good situation. This is the central pricing edge.

3. **The three market sources are built differently and disagree in useful ways.** KTC is crowdsourced via an adapted ELO on keep/trade/cut votes; FantasyCalc is computed from real completed trades in synced leagues; DynastyProcess is derived from FantasyPros expert consensus rankings run through an exponential decay curve. Divergence among them is itself a signal.

4. **Documented, repeatable inefficiencies exist:** rookie pick and rookie QB hype inflation (especially April-May), age cliffs priced too early for pocket passers and too late for rushers, recency bias after breakouts and down years, injury discounts that overshoot, and a seasonal drift where values rise in the offseason and bleed during the season for non-producers.

5. **Case studies confirm the framework wins more than it loses**, but they also show the market can take a full season or more to correct, so signals need patience and position sizing.

## Details

### Part 1 — Production Forecast (multi-year)

**Inputs and why, ordered by predictive weight:**

- **Rushing profile (attempts and yards per game).** This is the anchor. Rushing volume is the stickiest QB trait and, unlike passing TD rate, it carries year to year, with rushing attempts posting the strongest single correlation to next-season fantasy PPG (about 0.576) of any QB stat tested. It also converts efficiently to fantasy points in Sleeper scoring: 0.1 per rush yard plus 6 per rush TD, and rushing points are additive on top of passing. Rich Hribar's work found that only three weekly overall QB1 games all season came with fewer than 4.4 rushing points (Kirk Cousins in Week 5, Joe Burrow in Week 10, Jameis Winston in Week 13), and the top three weekly scorers averaged 7.3 rushing points per game. Per PFF, there have been 34 instances since 2000 of a QB starting 12-plus games and averaging at least 5.5 rush attempts per game, and those player-seasons averaged 18.7 fantasy PPG, with 30 of the 34 finishing as a fantasy QB1 in PPG. Weight rushing heavily and treat it as the primary separator between tiers.
- **Prior fantasy PPG / fantasy points per dropback.** If a player has already been good, he is likely to be good again. Fantasy points per dropback is the most predictive single stat for next-season PPG. Use it as the production base and as a sustainability check on a QB's current PPG.
- **Age curve.** Applied in Part 2 as the longevity multiplier, but it also shapes the year-1-to-5 growth/decay path within the forecast.
- **Draft capital.** For QBs with little or no NFL data this is the dominant prior. Per Dynasty Nerds' study of 37 first-round QBs, they hit at a 59.5% rate for at least one QB1 season and roughly 75% produce at least QB2-level seasons; since 2015 only five QBs posted a rookie QB1 season, four of them first-rounders (Dak Prescott the lone exception). PFF and others report that for rookie QBs, nothing they have found is more predictive than draft capital alone.
- **Efficiency floor / bust screen.** EPA per dropback, CPOE, ANY/A, and completion percentage as guardrails, not drivers. In 2024 every QB with eight-plus starts except Anthony Richardson completed 60% or higher; Richardson ranked 41st of 43 in PFF passing grade across 2023-24 and last in uncatchable throw rate at 31.1%. Use the efficiency screen to flag rushing-dependent QBs whose passing is so poor their job (and therefore their rushing volume) is at risk.

**Multi-year decay/growth across the forecast horizon (years 1-5+):**

- **Young ascending QBs (ages 22-25) with real rushing volume:** grow years 1-3 (passing usually improves while rushing holds), plateau 4-5. Drake Maye is the template: QB29 by raw 2024 rookie PPG but about 17 PPG in full games, then a 2025 leap to 20.7 PPG (QB2), completing 71.9% for 4,394 yards and 31 TDs plus 450 rush yards.
- **Peak dual-threat QBs (ages 26-29):** flat for 1-2 years, then bake in rushing decay starting at age 29-30. This is where the model should be most aggressive relative to market.
- **Pocket passers (any age up to mid-30s):** near-flat plateau tied to situation and supporting cast rather than age, with a sudden-cliff risk rather than gradual decline.
- **Rookies / no NFL data:** anchor year-1 to draft capital and landing spot, add a college rushing bump for dual-threats, then converge toward archetype norms by years 2-3. Fernando Mendoza-type pocket passers get a lower rushing prior; Taylen Green-type athletes get a higher rushing prior but a wider bust band.

The practical model: project PPG per season out five-plus years, then convert to **PPG over replacement** (subtract the Superflex QB replacement baseline, which in a 12-team Superflex sits around the QB24 level, materially higher than 1QB because roughly 24 QBs start each week).

### Part 2 — Longevity and Risk (expected remaining startable seasons)

**The aging data:**

- Top-12 QB seasons since 2000 average about age 28.5 (median 27), but the average hides the archetype split. The number of qualifying QB1 seasons per year is far higher now (the 2020s produce roughly 10 per year versus 2.6 in the 2000s) because of rushing and rule changes.
- **Rushing QBs:** production cliff after 29. Of the 21 QBs since 2000 to rush for 500-plus yards in a season, only a handful (Wilson, Newton, Vick, Gannon) did it after age 29, and only Gannon after 31. Lamar Jackson's rushing dipped to about 30 yards per game in an injury-hit 2025 at age 28-29. Mobile QBs also carry higher injury/decline risk because running is Plan A.
- **Pocket passers:** Brady to 44, Brees to 39, Rodgers into his mid-30s, Stafford the QB3 at 20.2 PPG at age 37 in 2025 (after leading the NFL with 46 passing TDs and winning MVP). Age matters far less than situation.
- **Aging is not a smooth curve; it is a plateau with sudden drops.** Adam Harstad's mortality-table framing (Footballguys) models this with "Expected Years Remaining" and a "death rate" that spikes, and forces survival to zero past age 42. QBs pop in and out of relevance (Kurt Warner, Boomer Esiason), which makes point estimates of "decline age" misleading and argues for a probabilistic remaining-seasons estimate.

**Discounted career value formula (recommended core of the engine):**

Intrinsic value = sum over future years t of [ projected PPG-over-replacement in year t ] × [ P(still startable in year t) ] × [ 1 / (1 + d)^t ]

where P(startable) comes from an archetype-specific survival curve keyed on current age, archetype, and current performance level, and d is the annual discount rate.

**Discount rate:** dynasty future seasons lose present value fast because of roster churn, league turnover, and win-now urgency. The established practitioner approach (Footballguys' Jeff Bell/Dan values, DraftSharks 3D) is to multiply a current-year value-over-replacement by a capped "seasons remaining" number with a time-value discount baked in. A reasonable range is **12-18% per year**; use about **15%** as a default. At 15%, a season five years out is worth roughly half a season now, which matches how dynasty managers actually behave. Contenders should run a higher discount (they care about now, so 20%+), rebuilders a lower one (8-10%). This is exactly why the same QB is a "win-win" trade between a contender and rebuilder: they are applying different discount rates to the same cash-flow stream.

**Injury and job-security risk** enters through the P(startable) term, not as a separate fudge factor. Marginal starters get a benching haircut (Anthony Richardson lost his job to Daniel Jones; Justin Fields has bounced across four teams). Injury-prone profiles (Burrow sidelined 16 games since the start of 2023; Daniels' thin frame and 2025 elbow/knee issues) get a lower games-played probability in near years.

### Part 3 — Market Delta (the product)

**How the three sources are constructed:**

- **KeepTradeCut:** crowdsourced. Users rank three players keep/trade/cut; an adapted ELO algorithm converts millions of these votes into values on a roughly 0-9999 scale, with separate Superflex and 1QB databases. Strength: fast-reacting, huge sample. Weakness: reflects sentiment, so it overshoots on news and hype.
- **FantasyCalc:** computed from real completed trades in synced leagues (2.6 million-plus trades), updated multiple times per day, with historicalValues and impliedValues available via API. Strength: revealed preference from actual trades. Weakness: thinner on rarely-traded players.
- **DynastyProcess:** scrapes FantasyPros Dynasty Expert Consensus Ranks and converts to values along an exponential decay curve; free and historical via GitHub and nfl_data_py/ffscrapr. Strength: transparent, backtestable history. Weakness: it is expert opinion, not trades, and lags fast news.

Using all three and treating disagreement as signal is the right architecture. When FantasyCalc (trades) lags KTC (sentiment), the market has not yet "paid" for a narrative move.

**Documented inefficiencies to target:**

- **Rookie hype / pick inflation:** rookie pick values spike in April-May on draft buzz; DynastyProcess explicitly notes managers value picks near their ceiling ("perfect knowledge") rather than realistic hit rates, so picks lose value the moment they convert to a player.
- **Age cliffs mispriced by archetype:** the market devalues QBs on a birthday rather than on rushing decay. A data-driven model (Koalaty Stats) flagged Goff, Geno Smith, Mayfield, Stafford, and Cousins as market-undervalued because the market has "a really bad grasp of a QB's aging curve." That is the pocket-passer edge.
- **Recency bias:** breakout seasons get overpriced, down seasons underpriced.
- **Injury discount overshoot:** Burrow's value is "shrouded" by injury history despite elite per-game production; these become buy-lows for rebuilders.
- **Seasonal drift:** values rise in the offseason on hope and bleed in-season for non-producers, and rebuilders systematically buy injured stars cheap at the deadline.

**Case studies with real numbers and dates (Superflex, KTC unless noted; live values fetched July 16, 2026):**

- **Josh Allen — buy-the-breakout won big.** Offseason 2019/2020 he was going around pick 27, QB8 in DLF Superflex startups; a RotoBaller piece in early 2020 openly worried his sub-60% completion rate made him a sell and that his value was "at the highest level it'll ever be." After his 2020 breakout (PFF grade 64.1 to 91.1, completion 56.3% to 69.2%) he became the 1.02 in 2021 Superflex startups and has been the consensus dynasty QB1 since. Today: KTC 9989, overall #4, QB1. Intrinsic logic (elite and rising rushing plus improving efficiency in a young QB) screamed buy exactly when sentiment was wobbling.
- **Jayden Daniels — rookie pick to near-elite, then injury fade.** Pre-2024 draft he was a 1.02-1.05 Superflex rookie pick; his rookie QB5 finish (about 20.9 PPG) spiked him to near-QB2 in early 2025. A 7-game, injury-hit 2025 (completion 69.0% to 60.6%) faded him to QB4, about 7,818-7,858 today. The rushing-QB injury/decay risk showed up on schedule.
- **Drake Maye — buy-the-sophomore-leap won.** A 2024 top-3 rookie pick (1.02-1.03) who looked ordinary as a rookie (market roughly QB8-13), then broke out in 2025 (20.7 PPG, QB2, 71.9% completion) and climbed to about QB2, roughly 9,350-9,410 today. Buying in early 2025 before the leap was the edge; by his own account "if you want to buy now, you won't get a discount." (Note: some sources cited Maye near KTC 9986; the July 16, 2026 snapshots show him at roughly 9,350-9,410, behind Allen at 9989.)
- **Anthony Richardson — the benching/efficiency bust.** A top-10 rookie pick by ADP in 2023 and a top-5/QB5-6 dynasty QB by spring 2024 (peak roughly 6,000-7,000 range), now at an all-time low of 2,151, QB38, overall #253, after being benched for Daniel Jones and an injury-marred 2025. The efficiency screen (worst-in-class passing) plus job-security risk would have flagged the sell near the peak. He is now a lottery-ticket buy at the bottom, not a hold at the top.
- **Baker Mayfield — the market never fully paid for the veteran.** Near-zero in early 2023, then a real-life QB3 season in 2024. KTC moved him only from about QB35 (August 2023) to about QB23 (mid-2024) despite that production, and he sits around 4,805, QB20 today. The veteran/age discount capped him. Lesson: buying an aging non-rushing QB coming off a spike rarely pays in dynasty even when the real-life production is real.
- **Joe Burrow — injury discount, elite when healthy.** QB3 in real fantasy in 2024 (league-high 4,918 yards, 43 TDs), then only 8 games in 2025 on a toe injury; sidelined 16 games since the start of 2023. Nearly all his dynasty value is future value; he is the archetypal rebuilder buy-low at the deadline while contenders won't pay.
- **Justin Fields — rushing hype versus efficiency reality.** A top-8 dynasty QB (QB6/QB7 in startups) before 2023 on rushing hype, now about QB40 (roughly 1,982 on KTC) and QB42 on Dynasty Nerds. The efficiency floor (accuracy, job security) was the tell; his rushing kept a floor only as long as he started, and he stopped starting.
- **Stafford / Cousins — aging pocket passers.** Stafford was the QB3 at 20.2 PPG at 37 in 2025 (46 passing TDs and MVP that year); the DLF note is that his "value really can't go up" because any season could be his last, yet he keeps producing. The market's age fear on pocket passers is the exploitable gap; a model that prices situation over birthday buys these cheaply.
- **Patrick Mahomes — elite talent holds through down years, then dips on age plus injury.** QB8 and QB9 in PPG in 2023-24 raised ceiling questions, then a QB3-through-week-15 bounce-back in 2025 (career-high 422 rush yards) before a Week 15 ACL tear. Market "already started to slip" in 2025 on age even at 30. Elite talent held his value through the down years better than a lesser QB's would have, validating a talent/floor term in the model.

### Part 4 — Backtest of Model-vs-Market Signals

**Design (point-in-time, information available at time t):** take offseason snapshots (2021, 2022, 2023, 2024) of DynastyProcess/KTC Superflex values, compute an intrinsic value with the rushing-weighted multi-year forecast and the 15% archetype-discounted longevity model, flag QBs where intrinsic diverges from market by more than a threshold, then measure the 12-24 month forward change in market value. Metrics: buy hit rate (did buys gain value), sell hit rate (did sells lose value), average value change versus a market-neutral baseline, and a portfolio simulation.

**What the public data lets me verify (approximate, not a fully computed sweep):**

- **Buy signals that won:** Josh Allen (offseason 2020, QB8/pick 27 to sustained QB1); Drake Maye (early 2025, market QB8-13 to QB2 about 9,350-9,410); Jayden Daniels (2024 rookie pick to near-QB2). All three shared the model's core buy fingerprint: young, real rushing volume, improving or elite efficiency, market lagging.
- **Sell signals that won:** Anthony Richardson (spring 2024 peak about 6,000-7,000 to 2,151 today) on the efficiency-plus-job-security screen; Justin Fields (top-8 pre-2023 to about QB40) on the same screen; and, more subtly, aging rushing QBs like Lamar Jackson entering age 29-30 where the model would fade rushing faster than the market.
- **A signal that correctly said "don't buy":** Baker Mayfield's 2024 real-life QB3 spike, where the model's age discount would have kept him a low QB2 and the market indeed never lifted him past about QB20-23.
- **A "hold/patience" case:** Joe Burrow, where the model separates high future value from low current value and says rebuilders buy, contenders pass, exactly matching how the market actually traded him.

**Honest limits of this backtest:** KTC does not expose historical point values in machine-readable text (its history graphs render client-side), so exact dated point series for past snapshots are approximate and anchored to dated positional ranks and ADP rather than fully computed. DynastyProcess history is retrievable via GitHub/ffscrapr and is the right source to run the real, fully-computed backtest inside the app; that computation was not run here. The QB sample per year is small (roughly 24 startable), so hit-rate confidence intervals will be wide. Treat the results above as directional validation, not a statistically closed proof.

**Portfolio framing:** a manager who systematically bought the young-rushing-QB-with-lagging-market signal (Allen 2020, Daniels 2024, Maye early 2025) and sold the poor-efficiency-plus-job-risk signal (Richardson, Fields) near peak would have compounded roster value substantially, because Superflex QB is the position where single correct calls move the most value. The losing scenarios are the aging-pocket-passer buys that never pay (Mayfield) and holding a rushing QB one year too long past the age-29 cliff.

### Part 5 — Verdict and Implementation

**The engine (concrete parameters):**

- **Core formula:** DynastyValue = Σ_t (PPGOR_t × P_startable_t × (1.15)^(-t)), t = 0..~8, where PPGOR is projected PPG minus the Superflex QB24-level replacement baseline.
- **Discount rate d:** default 15% (0.15). Expose a slider: contenders 20%, rebuilders 10%, tied to the team's Sleeper standing and roster age so the app can auto-suggest.
- **Age curve by archetype (classify first, value second):** tag each QB as rushing/dual-threat vs pocket passer using rush attempts per game and rush yards per game (a threshold around 4-5 designed carries or roughly 25-plus rush yards per game marks dual-threat). Rushing QBs: begin fading the rushing component at age 29, steeper each year after; passing floor persists. Pocket passers: near-flat P_startable into age 36-37, then a sharp sudden-drop hazard rather than a gradual slope.
- **Rookie priors:** anchor year-1 PPG to NFL draft capital (first-round QBs get a QB2-ish prior with a QB1 tail; day-2/day-3 get backup priors), add a college rushing bonus for dual-threats, plus a landing-spot adjustment. Converge to archetype norms by year 3.
- **Efficiency bust screen:** flag any QB whose value is rushing-dependent but whose EPA/dropback, CPOE, or completion% is bottom-tier (Richardson profile) with a job-security haircut on P_startable.

**Data pipeline:**

- **nfl_data_py (nflfastR):** play-by-play for EPA/dropback, CPOE, rush attempts/yards per game, ANY/A, historical fantasy PPG. This feeds Parts 1-2.
- **DynastyProcess (via GitHub CSVs / nfl_data_py / ffscrapr dp_values):** free historical Superflex and 1QB market values for the backtest and for a stable secondary market reference.
- **KTC and FantasyCalc:** live prices. FantasyCalc has a clean JSON API (values/current with isDynasty, numQbs, numTeams, ppr params, plus historicalValues per player); KTC requires a scrape of the Superflex profile/rankings pages. Use FantasyCalc as the primary live "trades" market and KTC as the "sentiment" market.
- **Sleeper API:** league settings (confirm 12-team Superflex, full PPR, roster of QBs), standings and roster age to set each team's discount rate and contender/rebuilder mode, and to scope replacement level to the actual league.

**Surfacing the signal:**

- Compute Delta = (IntrinsicValue − MarketValue) / MarketValue per QB, normalized to a common scale across the three market sources.
- **Buy** when Delta ≥ +15%, **Strong Buy** ≥ +30%; **Sell** when Delta ≤ −15%, **Strong Sell** ≤ −30%; **Hold** in between. Require agreement direction from at least two of {KTC, FantasyCalc, DynastyProcess} before firing a "strong" signal to avoid chasing one noisy source.
- Show the "why" (rushing trend, archetype/age, efficiency screen, injury/job flag) and the current vs future value split so contenders and rebuilders read the same card differently.

**Refresh cadence:** weekly in-season (Tuesday, after the week's games and market reaction), monthly in the offseason with event-driven refreshes on the NFL Draft, free agency, major injuries, and depth-chart/benching news. FantasyCalc updates multiple times daily, so live prices can refresh more often than the model recompute.

**Signal-strength thresholds and staged next steps:**

1. Ship the intrinsic-value model on DynastyProcess history plus nfl_data_py first, because it is free and backtestable, and validate the buy/sell hit rate on 2021-2024 snapshots before trusting live signals.
2. Layer in live KTC/FantasyCalc scraping and the three-source agreement rule.
3. Add the Sleeper-driven per-team discount rate and contender/rebuilder mode.
4. Only after the backtest hit rate clears a bar (say buys beat the market-neutral baseline by a meaningful margin over 12-24 months) should the app present signals as actionable rather than informational.

**Thresholds that would change the recommendation:** if the backtest shows buy signals not beating baseline, widen the Delta threshold or downweight sentiment (KTC) relative to trades (FantasyCalc); if rushing stickiness weakens in future data, reduce the rushing weight; if the league's replacement level shifts (injuries, bye weeks), recompute the QB24 baseline from live Sleeper rosters.

## Recommendations

- **Build the model on the discounted-value-over-replacement formula with a 15% default discount and archetype-specific survival curves.** Classify every QB as rushing or pocket before applying any age logic; this single step captures the largest market inefficiency.
- **Weight rushing volume as the primary forecast input and use efficiency (EPA/dropback, CPOE, completion%) only as a bust screen and job-security flag.** Fantasy points per dropback is the best sustainability check, and rushing attempts are the single most predictive input for next-season PPG.
- **Use three market sources and treat their disagreement as signal.** FantasyCalc for revealed-preference prices, KTC for fast sentiment, DynastyProcess for free backtestable history. Fire "strong" signals only on two-source agreement.
- **Buy young rushing QBs whose market lags a rising production/efficiency trend** (the Allen 2020 / Maye early-2025 / Daniels 2024 pattern) and **sell rushing-dependent QBs with poor efficiency or shaky jobs near their peak** (the Richardson / Fields pattern). **Do not chase aging non-rushing QBs coming off a spike** (the Mayfield lesson); the age discount almost always wins.
- **Set the discount rate by team state:** higher for contenders, lower for rebuilders, auto-suggested from Sleeper standings and roster age. This turns the same QB into a legitimate win-win trade and is where most value is captured.
- **Backtest first, signal second.** Run the 2021-2024 DynastyProcess snapshots, measure buy/sell hit rate and average value change versus a market-neutral baseline, and gate live actionable signals on clearing that bar.
- **Refresh weekly in-season, monthly in the offseason, with event-driven updates** on draft, free agency, injuries, and benchings.

## Caveats

- **Small sample.** Only about 24 QBs are startable in a 12-team Superflex at any time, so hit-rate confidence intervals are wide and one or two hits or misses swing the numbers. Do not over-trust a clean backtest.
- **The market can stay irrational longer than your window.** Baker Mayfield's real-life QB3 season never got fully paid; Richardson stayed overpriced for a year after the efficiency red flags were clear. Signals need patience and position sizing, and a rebuild timeline may expire before a correct call pays.
- **Aging is a plateau with sudden drops, not a smooth slope.** Any survival curve will misprice the exact year a specific QB falls off; use probabilities, not point estimates, and expect Kurt Warner-style comebacks and Anthony Richardson-style collapses to defy the curve.
- **Value versus wins tension.** The engine maximizes asset value, which is not the same as maximizing this year's championship odds. A contender should sometimes knowingly "lose" value (pay up for a win-now QB) and a rebuilder should sometimes hold a depreciating asset for a title run. Surface both the value delta and the current/future split so the manager, not the model, makes that call.
- **Data gaps.** KTC historical point values are not cleanly machine-readable, so the fully-computed longitudinal backtest should be run on DynastyProcess history inside the app; the case-study numbers here are anchored to dated ranks/ADP and live values fetched July 16, 2026, and some past peaks are directional estimates. FantasyCalc and KTC are unofficial data sources subject to change, so the scrape/API layer needs monitoring.