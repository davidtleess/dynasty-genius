# David's rulings — 2026-07-25 — Studio 009 findings + pick valuation standard
Recorded by Tower from David's own words. Binding. Relay to crew on release of hold.

## RULING A — pick valuation: the negative-value gate (confirmed standard)
A pick's value is floored at zero UNTIL the valuation can demonstrably price all three of these:
1. **The draft-and-cut option** — draft the player, release him after training camp. Cost is near zero, so this alone bounds a pick's downside at roughly zero.
2. **The pick's own trade value** — what another manager will pay for it, independent of whether it fits David's roster.
3. **The rookie-as-trade-chip option** — draft a rookie, then use him against a market-vs-model gap to acquire a player worth more than our model says.

David's words: "if the valuation of picks is considering all of those things and STILL showing its worth less than zero, i would be okay with that being surfaced. but if it's not thinking like that - then its not valuing picks correctly."

**Verified by Tower 2026-07-25:** the current curve (`scripts/build_draft_pick_value_curve.py`) is built solely from realized player production (`prospects_with_outcomes.csv`, mature classes 2015-2022, y24_ppg -> DVS -> xVAR). No optionality, no liquidity, no roster-spot cost, no trade value anywhere in it. Therefore negatives are NOT permitted to surface today, and any negative the current model produces is an artifact of an incomplete model, not a finding.

Economic note that supports the floor: a pick's worth is the MAX of (keep the player, trade the pick, draft-and-cut). In David's league all three are always available, so a genuinely negative pick would require being unable to drop the player AND unable to trade the pick. Neither holds.

## RULING B — Studio finding 1: stale surfaces. APPROVED.
David: "the frontend must show our freshest data."
Every league-snapshot surface must read the newest capture on disk, not a pinned older run. Four surfaces, one root cause. Measured cost: 4 of 12 team posture labels are wrong on the served data, including the labels used to choose a trade counterparty; David's own rebuild progress is hidden from him.

## RULING C — Studio finding 2: IR/taxi exclusion. APPROVED, PLUS A NEW PRODUCT RULE.
David: "yes we must account for taxi and IR."

**NEW RULE — Starter Strength must be computed from the OPTIMAL starting lineup, not the manager's actual starters.** David's words: "Starter Strength should not be calculated by the players in starting slots, people often don't start their best players, especially if they are rebuilding. Instead it should be calculated by the OPTIMAL starting roster - Genius needs to place the best configuration of starters in the spots available then calculate."

Consequence to be respected, not glossed: starter strength drives ~60% of the posture score and is the base of every positional z-score, every surplus/deficit label, and the partner rankings. Changing the basis changes all of them.

**TAXI SQUAD RULES — David's own league knowledge, treat as domain truth:**
- A taxi player may be moved out of the taxi squad onto the regular roster **at any point in the season**.
- Promoting him does **NOT** create a roster spot — a player must be dropped to make room.
- **Nobody can be added to the taxi squad until after the rookie draft in the offseason.**

Therefore taxi value is real and available, but converting it carries a roster-spot cost, and the taxi squad cannot be refilled mid-season. Taxi players are neither invisible (today's bug) nor equivalent to active players. Model the conversion cost.

## RULING D — Studio finding 3: model-vs-market comparison. INVESTIGATE, HIGHEST PRIORITY.
David: "Im not sure i fully understand but we must get to the bottom of it... this is the products core analysis."

The claim to be resolved: our side of the divergence uses xVAR (value above replacement, roughly current-season) while the market side uses FantasyCalc's dynasty price (a discounted future value). Comparing them may systematically report AGE as OPPORTUNITY. Evidence offered: 8 of the top 14 "we like far more than the market" players are 29+, while the market-preferred side is uniformly young. Studio states this reproduces the 005 age artifact **even with the within-position control David previously asked for**, which would mean that control does not address the cause.

This is not a patch item. Required: a written diagnosis of exactly what each side measures, whether the artifact is real and how large, and a recommendation for which comparison the product should make — then David decides. Nothing about the divergence surface changes until he rules.

### RULING D.1 — the direction is settled. NO REDRAFT.
David's words: "absolutely no redraft market analysis - this is a dynasty tool we must go EXTREMELY deep and diligent on the shape the thinking the thesis and the build of a dynasty-horizon value."

The now-vs-now option (comparing our current-season measure to redraft market prices) is **REFUSED and closed**. The only permitted direction is to build a **dynasty-horizon value on our own side** and compare future-to-future.

Standard for that build — David's bar, carried from the pick-valuation thread and applied here: the shape, the thinking, the thesis and the build all get extreme depth and diligence. Thesis before implementation. Falsifiers declared and frozen before anything is fit. Benchmarked against the market curve, the current artifact, and at least one alternative, naming wins AND losses. Qualitative football judgment may be blended but must be labelled. Honest limits stay on-surface.

## RULING E — architecture principle, standing. Optimal-lineup logic lives in ONE place.
David's words: "as substantial as it may be, its the right way to do it, but if we're building the product correctly we should be able to determine the logic for optimal starting lineup and the data should simply feed that logic and the app surfaces should simply display and surface the answer."

Read as a general principle, not only about lineups: the optimal-lineup determination is computed once as product logic; data feeds that logic; every surface displays the single answer. No per-surface reimplementation, no surface deriving its own version of starter strength. If more than one surface needs it, they read the same computed answer.

## RULING F — the contention window. David's product direction, 2026-07-25.
David's words: "if i am in contending mode it would be interesting to have the ability to analyze a trade based on how much time i want the player im trading for… what if i wanted to look at the value they could bring to the team during a short period of time - say the next two seasons - two seasons i think i can win the championship, analyze that window of value against a younger player who may be a more valuable dynasty asset but will give me less value during the 2 years i am in contention. almost like a scenario builder or a simulator… I still think the CORE of the product is Dynasty-Horizon Value, but i want to callout that in dynasty, when you can win the championship sometimes you have to GO FOR IT."

Standing: **dynasty-horizon value remains the core.** The contention window is an additional lens over the same quantity, never a replacement for it, and never a redraft measure (Ruling D.1 still binds — the window is multi-season, not current-season).

### HARD DESIGN REQUIREMENT that follows, to be settled in the thesis BEFORE any implementation
Dynasty-horizon value must be constructed as a **per-season stream of projected value with an explicit discount**, not as a single scalar. If it is built as one number, the window lens becomes a rewrite instead of a query.

With a stream, one construction serves three features:
- **Dynasty-horizon value** = discounted sum across all remaining seasons.
- **Contention-window value** = sum across the seasons David selects (e.g. the next two).
- **Pick value** = the same stream, beginning at the rookie's debut season, which is why picks cannot be priced without it.

Consequence for trade analysis: two players can be correctly ranked in opposite orders depending on the selected window, and the product must be able to show that WITHOUT contradicting itself — same underlying stream, different summation range, both labelled.

Football truth being encoded: championships are won by correctly timing a push. Paying a long-term asset for two years of a declining star can be the right move. The tool must support that judgment rather than always favouring the longer horizon.

## RULING G — apples-to-apples, BOTH modes. David approved 2026-07-25.
Both comparison modes are approved: rank-vs-rank AND our value translated into market currency. Condition, his words: "let's make sure we are doing it correctly against the correct values - both market and model."

## RULING H — the market-measurement mandate. David's words, treat as binding.
"we ABSOLUTELY MUST verify and decompose and understand WHICH MARKET VALUES we are using HOW THOSE VALUES ARE CREATED and WHAT THEY MEASURE - if we don't know what the market is measuring we are blind."
Commissioned to Codex 2026-07-25. No comparison work is trustworthy until this is answered.

## RULING I — league fact: NO TIGHT-END PREMIUM.
David: "we DO NOT HAVE TE Premium in our league." He notes TEP is only a scoring calculation and can be reverse-engineered if needed. Our ingestion sends no TEP parameter and the provider default is UNKNOWN — settling this is part of Ruling H. If we are storing TEP-on values, every tight-end comparison is wrong, and his one striking finding today (Kraft, our TE1 vs market TE5) is the suspect case.

## RULING J — horizon shape: David's lean, strengthened.
David: "this once again makes me lean to the year-by-year full career projection, obviously updating itself as real data about the player lands." Two engines currently disagree on horizon (Engine B: T+1..T+2 average; Engine A: Years 2-4) and the divergence pools both — which he read as further evidence for one explicit season-by-season construction. Still open to crew dissent WITH REASONS; not yet a mandate.

## EXTERNAL RESEARCH — what FantasyCalc's number actually is (Tower, 2026-07-25)
Provider's own published material: values are generated from ~3.6M real fantasy trades; the value curve is EXPONENTIAL, not linear; top-of-market players are traded less often so their values are more sensitive to individual trades. **Critically: FantasyCalc explicitly adds a bench-spot value into its prices, scaled by how many bench spots a trade consumes, calibrated to an average league of 11.3 teams and 26.7 roster spots (a 2-for-1 assumes the dropped player is ~300th best, worth ~425).**
Two consequences: (1) the market price is NOT a pure production forecast — it already prices roster scarcity, which is the same mechanism David reasoned through on pick values; (2) currency conversion from a roughly linear value-above-replacement onto an exponential price scale cannot be a linear calibration, or it will be systematically wrong at the top of the market.

## TOWER'S SYNTHESIS — one missing quantity, three features
Both of today's headline problems reduce to the same root cause: **the product has no dynasty-horizon (multi-year, discounted) value of its own.**
- The divergence surface therefore compares a current-season quantity against a market price that IS dynasty-horizon — so it reports age as opportunity.
- Pick valuation therefore cannot price a pick, because a pick is nothing but future value.
Building the dynasty-horizon value is the shared prerequisite. It should be sequenced as one foundational thread, not two.
