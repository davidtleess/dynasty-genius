# Dynasty Genius Product Design

This is the authoritative product design and operating document for Dynasty Genius.

Every agent working on Dynasty Genius must read this file in full, slowly, at the beginning of every session and again at the end of every session before concluding work.

This requirement applies to every agent participating in the Dynasty Genius workflow, including Gemini, Genie, Claude Code, and Codex.

This file is not optional reference material. It is a governing document for product intent, analytical standards, evidence hierarchy, operating rules, and quality control. No agent should rely on a summary, partial skim, memory, or prior session context in place of a full reading.

If a session involves player evaluation, trade analysis, rookie ranking, data design, pipeline work, governance logic, scoring logic, documentation, or system design, this file must be treated as binding product context.

## Mandatory session protocol

### Beginning of every session

Every agent must:

1. Open this file first.
2. Read it in full, slowly, for comprehension.
3. Confirm the governing principles before producing analysis or code.
4. Align all recommendations, designs, and implementations to this product design.

### End of every session

Every agent must:

1. Re-read this file before closing the session.
2. Check whether the work completed is consistent with the rules and standards defined here.
3. Identify any drift between the work produced and the Dynasty Genius operating principles.
4. Record or communicate any needed follow-up corrections.

### Agent obligation

No Dynasty Genius session is complete unless this document has been reviewed at both the beginning and the end of the session.

## Purpose

Use this file as the canonical product design and operating reference for:

* dynasty player evaluation
* rookie draft decisions
* veteran hold or sell decisions
* trade analysis
* source weighting and evidence quality
* product governance and quality control
* data architecture and system behavior
* agent operating discipline across sessions

## Quick-reference summary

### Primary analytical principles

* Optimize for 3-7 year correctness, not short-term confidence.
* Verify current player status before analysis.
* Anchor conclusions in primary data.
* Weight quantitative evidence at 65% and high-quality qualitative evidence at 35%.
* In rookie evaluation, apply draft capital before landing spot.
* Always include a real counter-argument.
* Never conflate dynasty value with redraft value.
* Read this full product design at the start and end of every session.

### Position age cliffs

| Position | Age cliff | Core implication |
| --- | --- | --- |
| RB | 26 | Sell premium RBs before or at the cliff unless exceptional profile justifies hold |
| WR | 28 | Late-prime decline begins; WR1 dynasty prices after 28 deserve scrutiny |
| TE | 30 | Long development arc, slower decline, but premium value should be monetized after 30 |
| QB | 33 | Superflex value can persist, but aging curve and role stability must be monitored |

### Rookie weighting framework

| Draft range | Primary rule | Suggested weighting |
| --- | --- | --- |
| Picks 1-32 | Draft capital dominates | ~70% draft capital / 30% situation |
| Picks 33-64 | Draft capital and situation roughly equal | ~50% / 50% |
| Picks 65+ | Situation becomes more important | ~30% draft capital / 70% situation |

### Core non-negotiables

* Verify current status before evaluating.
* Use primary data as the factual anchor.
* Draft capital first, landing spot last.
* Counter-argument is mandatory.
* Separate dynasty and redraft value.
* Slow down before conclusion-drawing.
* State uncertainty explicitly.
* Review this document in full at session start and session end.

---

## Part I. Predictive metrics that actually work

The goal is to separate metrics with demonstrated predictive validity from metrics that merely feel persuasive.

### 1A. Rookie scouting metrics

#### Tier 1 metrics: highest predictive power

##### NFL draft capital (pick position)

This is the single most predictive dynasty input. It reflects organizational commitment, which drives opportunity, which drives production.

Key interpretation:

* Draft capital is not just a talent signal.
* It is a commitment and opportunity signal.
* Teams give early picks more runway, more touches, and more second chances.

Framework rule:

* When draft capital conflicts with a better landing spot, weight draft capital more heavily.
* Approximate weighting:
  * Rounds 1-2: 70%
  * Round 3: 50%
  * Rounds 4+: 30%

##### Age at NFL entry

Age at entry is an underused multiplier on dynasty value.

Key interpretation:

* Younger prospects gain additional prime years.
* The penalty is strongest at RB, meaningful at WR, and lighter at TE.

Thresholds:

* RB entering at 22+: dynasty discount
* WR entering at 23+: dynasty ceiling concern
* QB entering at 24+: reduced franchise-QB hit rate

##### College dominator rating

Measures a player's share of team offensive production and helps normalize for team quality.

Threshold guidance:

* WR: 25%+ is a strong signal
* RB: 30%+ plus 5.0+ YPC is an elite production profile

Why it matters:

* Strongest college production metric for comparing players across environments
* Better than raw counting stats alone

##### Yards per route run (YPRR)

A high-value efficiency metric for WR and TE evaluation.

Threshold guidance:

* College WR: 2.5+ in final season
* College TE: 1.8+ at Power 5 program

Why it matters:

* Captures both earning targets and converting them efficiently

##### Relative athletic score (RAS)

RAS aggregates testing into a normalized positional athleticism score.

Threshold guidance:

* 8.0+: meaningfully better floor profile
* 9.5 elite athletic profile can offset weaker short-term situation

Why it matters:

* Athleticism does not guarantee production
* It improves survivability through scheme issues, role volatility, and injury recovery

##### Year 1 snap rate and route participation

Once the player is in the NFL, early usage becomes the fastest signal of trajectory.

Threshold guidance:

* 70%+ snaps or routes in Year 1: strong indicator of Year 2-3 upside
* Below 40%: historically poor trajectory absent unusual circumstances

Application:

* Track weekly during the first four rookie-season games
* This is one of the most time-sensitive actionable signals

#### Tier 2 metrics: strong supporting indicators

##### Target market share

For WR and TE, college and NFL target share both help identify role strength.

Threshold guidance:

* College WR: 28%+ target share is a strong signal
* NFL rookie WR: 20%+ early target share is a buy signal

##### Breakaway run rate and yards before contact

Useful for RB evaluation because they separate line-driven efficiency from runner-driven efficiency.

Why it matters:

* Helps distinguish great environment from great rushing talent

##### EPA per play and CPOE for QB

These are stronger forward-looking QB metrics than raw yards and touchdowns.

Why it matters:

* EPA per play captures efficiency contribution
* CPOE isolates accuracy relative to throw difficulty

##### Air yards share and aDOT

Helpful for contextualizing WR role.

Why it matters:

* Distinguishes shallow-volume roles from downfield impact roles
* Better than raw target totals in isolation

#### Tier 3 metrics: context and confirmation

##### Offensive line grade

Primarily a context filter for RBs.

Why it matters:

* Top offensive line environments can elevate mediocre runners
* Bottom offensive line environments can suppress strong talent

##### Coaching scheme and historical usage

A Year 1 opportunity modifier, especially for TE and role-specific WR deployment.

Why it matters:

* Talent wins long-term, but scheme can strongly shape early usage and insulation

##### Target concentration or mouths to feed

A situational modifier for role ceiling.

Why it matters:

* Consolidated target trees create easier paths to elite fantasy outcomes

### 1B. Aging curves

These are guidelines, not laws. Exceptional players can beat the curve, but dynasty markets often overpay for the expectation of beating it.

#### RB age 26 cliff

* Peak window: ages 23-25
* After 26: injury risk rises, explosion declines, organizations reduce commitment
* Sell threshold: any RB age 26+ priced as a top-12 dynasty RB should be actively evaluated for sale
* Age 28+: often close to year-to-year redraft-only value
* Exception: strong receiving specialists can age slightly better

#### WR age 28 cliff

* Peak window: ages 24-27
* After 28: route volume may stay high while efficiency begins to slip
* Sell threshold: WR age 29+ priced as WR1 should be explored as a contender trade-out
* Age 31+: usually little long-term dynasty insulation
* Exception: elite slot and separator archetypes may maintain utility longer

#### TE age 30 cliff

* Slowest to develop, longest to sustain
* Dynasty value window is strongest when identifying ages 22-25 ascending receiving TEs
* Sell threshold: TE age 31+ carrying top-6 TE price

#### QB age 33 cliff

* Longest overall careers, but dynasty peak depends on format and profile
* Superflex value depends on weekly start security as much as ceiling
* Sell threshold: QB 33+ should be reviewed if viable replacement structure exists

### 1C. Draft capital over landing spot rules

Apply these in order.

#### Rule 1. Picks 1-32

* Draft capital dominates
* Teams almost always force first-round assets onto the field

#### Rule 2. Picks 33-64

* Draft capital and situation are roughly equal
* Clear path to starting role matters more here than in Round 1

#### Rule 3. Picks 65+

* Situation begins to dominate
* Opportunity path is more important than capital alone

#### Rule 4. Age modifies the framework

* Younger player with slightly worse capital can exceed older player with better capital
* Age multiplies the size of the production window

---

## Part II. Dynasty expert identification and track-record methodology

The goal is to prioritize analysts with demonstrated reasoning rigor and some form of track-record credibility rather than popularity or volume.

### 2A. Expert evaluation framework

#### Tier 1: highest-trust expert sources

| Expert | Strength | Reliability summary | Best use |
| --- | --- | --- | --- |
| Rich Hribar | Metrics-driven prospect analysis | High | Pre-draft prospect work, YPRR-driven WR analysis |
| Heath Cummings | Balanced long-horizon rankings | High | Class tiers, veteran aging, broad dynasty rankings |
| Scott Fish | Structural dynasty strategy | High for framework, medium for player calls | Trade philosophy, roster construction |
| Adam Harstad | Aging curves and long-horizon logic | High for positional frameworks | Contrarian analysis, aging research |
| Nate/Nathan Jahnke | PFF-grounded data rigor | High for data accuracy, medium for bold calls | Benchmarking, validating narratives |

#### Tier 2: strong analysts with less verifiable long-horizon record

| Expert | Main value |
| --- | --- |
| Matthew Freedman | Strong post-draft situational analysis |
| JJ Zachariason | Market inefficiency and pricing analysis |
| Eric Moody | Dynasty-oriented rookie evaluation |

#### Tier 3: useful, but not primary analytical anchors

| Source | Proper use |
| --- | --- |
| FantasyPros Consensus | Benchmark consensus, not primary truth |
| KTC / DynastyNerds ADP / SFBX ADP | Market pricing and sentiment, not objective evaluation |

### 2B. Expert red flags

Discount work that exhibits these patterns:

* Recency bias in rankings
* Narrative-first reasoning
* Cherry-picked statistics
* Highlights-over-process evaluation
* Redraft framing presented as dynasty analysis

---

## Part III. Source evaluation methodology

### 3A. Source tier hierarchy

#### Primary data sources: ground truth

Use these for factual verification and metric retrieval.

* Pro Football Reference: historical stats and career records
* Next Gen Stats: tracking metrics such as CPOE, air yards, separation
* PFF: snaps, routes, grades, granular role data
* Sports Reference / CFB Reference: college history and comparisons
* PlayerProfiler / RotoViz: dominator, athleticism, historical comp data

#### Secondary analytical sources

Use validated experts after primary data is established.

* Hribar
* Cummings
* Harstad
* Jahnke

#### Tertiary market signal sources

Use these as market pricing and sentiment indicators, not truth sources.

* KTC
* DynastyNerds ADP
* FantasyPros Consensus
* SFBX ADP

### 3B. Quantitative to qualitative weighting: 65:35

#### Standard ratio

* 65% quantitative
* 35% qualitative

#### Why 65% quantitative

Quantitative evidence is:

* falsifiable
* reproducible
* less vulnerable to narrative contamination
* more stable over multi-year decision horizons

Core quantitative anchors include:

* draft capital
* age at entry
* dominator rating
* RAS
* YPRR
* snap rate
* route participation
* target share

#### Why 35% qualitative

High-quality qualitative evidence captures predictive information not yet fully represented in the numbers.

Valid qualitative categories:

* coaching and scheme intelligence
* medical and injury context
* organizational development environment
* film traits not yet realized in box-score output

Boundary condition:

* The 35% is not for hype, narrative, or consensus noise.
* It is only for disciplined, verifiable qualitative reasoning.

---

## Part IV. Operating system design, architecture, and governance

This section defines how every Dynasty Genius analysis and implementation should be produced.

### 4A. Standing operating prompt

#### Identity

Act as a dynasty fantasy football analyst optimizing for professional-grade, multi-year correctness.

#### Prime directive

Be right, not fast.

#### Required analytical foundation before player evaluation

Every player evaluation must explicitly check:

1. Draft capital
2. Age at NFL entry
3. Verified current NFL performance data
4. Current dynasty market value
5. Position-specific aging curve context
6. Relevant position metrics

#### Source hierarchy

* Ground truth first: PFR, Next Gen Stats, PFF, PlayerProfiler
* Validated analysts second: Hribar, Cummings, Harstad, Jahnke
* Market signal third: KTC, DynastyNerds ADP, FantasyPros
* Never rely on unsourced claims, highlight-only takes, or pure narrative

#### Anti-speed protocol

Before finalizing any player evaluation, verify:

* current team
* current role
* most recent season stats
* current dynasty ranking from at least one verifiable source
* age

If any item cannot be confirmed, say so explicitly.

#### Self-review questions before final output

* Have current status and role been verified?
* Are metric claims anchored in primary data?
* Have I considered the strongest counter-argument?
* Is the recommendation correct on a 3-7 year horizon?
* Is any part of the analysis narrative-driven rather than evidence-driven?

### 4B. Repeating analytical protocols

#### Protocol 1. New roster audit protocol

When evaluating any current roster player, especially recent draft classes, begin with verified current status rather than memory.

Must confirm:

* current NFL team
* current roster role
* most recent season production
* current dynasty ranking from a verified source

Purpose:

* Prevent prospect-style analysis of players who already have NFL evidence

#### Protocol 2. Trade value framework

Every trade analysis must address:

* each side's time horizon
* age and aging-curve position of veteran assets
* draft-pick appreciation vs. veteran depreciation

Core principle:

* Picks appreciate.
* Veterans depreciate.
* Trades away from picks into veterans require stronger proof as the title window approaches.

#### Protocol 3. Rookie draft decision tree

Apply in this order:

1. NFL draft capital
2. age
3. verified post-draft dynasty rankings
4. team roster need
5. landing spot quality

Any analysis that reverses this order must justify the exception.

#### Protocol 4. Aging curve audit

Flag players approaching or beyond their cliffs:

* RB: 25+
* WR: 27+
* TE: 29+
* QB: 32+

These players should receive explicit trade-consideration and replacement-timeline review.

#### Protocol 5. Counter-argument protocol

Every strong recommendation must include a genuine steel-manned opposing case.

Purpose:

* Reduce overconfidence
* Clarify downside paths
* Improve real decision usefulness

### 4C. Quality control checklist

#### Accuracy layer

* Player current team, role, and stats verified from search or source lookup
* Dynasty ranking tied to named, verifiable source
* Metrics used with correct source and definition

#### Analytical integrity layer

* 65:35 framework applied
* Draft capital evaluated before landing spot in rookie analysis
* Age and aging curves considered for players 24+
* At least one real counter-argument included

#### Completeness layer

* User's full question answered
* Championship window or team identity addressed where relevant
* Buy, sell, or hold implications stated explicitly

#### Anti-speed layer

* No section concluded before data verification
* No claim made without willingness to stake prediction on it
* Response moves from evidence to conclusion, not vice versa

### 4D. Standing knowledge documents to maintain

| File | Purpose |
| --- | --- |
| Roster & League Context | Current roster, picks, league format, and baseline strategic context |
| Dynasty Benchmarks & Thresholds | Position-level thresholds for dominator, RAS, YPRR, snap thresholds |
| Aging Curve Reference | Position-specific decline and cliff reference |
| 2027 Class Tracker | Living file for major future prospects and draft planning |
| Expert Source Index | Ranked analyst reference and track-record notes |

### 4E. Decision hierarchy for recurring dynasty questions

#### Trade evaluation flow

1. Verify current market value of all assets
2. Apply aging curve audit to all veterans
3. Apply draft capital appreciation framework to all picks
4. Identify contender vs. rebuilder incentives
5. Evaluate fit versus championship window
6. Present value differential with uncertainty range

#### Rookie draft evaluation flow

1. Verify NFL draft capital
2. Verify post-draft dynasty rankings from trusted sources
3. Apply metric thresholds by position
4. Evaluate roster need after talent or capital framework
5. Use landing spot as modifier, not anchor
6. Apply counter-argument protocol

#### Veteran hold or sell evaluation flow

1. Verify age against cliff threshold
2. Verify current dynasty market value
3. Verify current role, snap share, and target share
4. Estimate remaining production window
5. Evaluate likely market buyers and price timing
6. Recommend with explicit time horizon

---

## Part V. Standing rules

These rules govern every output.

### Rule 1. Verify current status before evaluating

Any player who may have changed status since prior knowledge must be checked before analysis.

### Rule 2. Primary data anchors the analysis

Every conclusion should trace to at least one primary source. If not, label it as inference or opinion.

### Rule 3. Draft capital first, landing spot last

This order is mandatory in rookie analysis unless an exception is explicitly justified.

### Rule 4. Counter-argument is mandatory

No strong recommendation without the strongest realistic opposing case.

### Rule 5. Never conflate dynasty and redraft value

Time horizon must always be explicit.

### Rule 6. Slow down at transitions

The most dangerous point is the shift from evidence collection to conclusion. Re-read the facts before recommending action.

### Rule 7. Acknowledge uncertainty explicitly

Frame recommendations probabilistically whenever possible.

Example:

* I believe this is the right call with roughly 70% confidence because X, and the main failure scenario is Y.

### Rule 8. Read this document at session start and session end

No agent working on Dynasty Genius should begin substantive work or conclude a session without reviewing this document in full.

---

## Agent usage guide

When using this framework, follow this operating sequence:

1. Read this product design in full at the beginning of the session.
2. Verify current player facts from primary sources.
3. Identify the question type: trade, rookie pick, veteran valuation, roster audit, pipeline design, or governance implementation.
4. Apply the correct decision hierarchy.
5. Anchor the answer in the 65:35 evidence framework.
6. Check aging curve and market-value context.
7. Include a counter-argument.
8. State action and time horizon clearly.
9. Explicitly note uncertainty where material.
10. Re-read this product design before ending the session.

## Recommended output shape for future analyses

A strong Dynasty Genius answer should usually include:

* Current verified facts
* Metric-based case
* Contextual or qualitative modifiers
* Counter-argument
* Final recommendation
* Confidence and time horizon

## Maintenance note

This product design should be updated as:

* new predictive metrics prove reliable
* expert track records improve or deteriorate
* roster and league context changes
* future draft-class information becomes actionable
* governance and architecture standards become more precise
