# **Phase 17 Research Brief: Sleeper Universe Valuation and League Opportunity Map**

## **Executive Recommendation**

The fundamental objective of Phase 17 is to transition the Dynasty Genius architecture from a reactive, query-driven valuation tool into a continuous, proactive arbitrage discovery engine. The analysis mandates a rigorous, five-stage phased implementation that begins with the deterministic ingestion of the complete Sleeper player universe and culminates in the generation of an automated league opportunity map. The system must establish a durable daily batch process that ingests all relevant entities, constructs a canonical Player Value Object (PVO) for every valid player, and aggregates these values to identify team-level positional surpluses, deficits, and market pricing divergences.1

To preserve the analytical integrity established in the North Star Architecture, market data—specifically the FantasyCalc overlay—must remain strictly isolated from predictive modeling. Under no circumstances may market pricing influence Engine A or Engine B feature vectors.1 Furthermore, a critical analysis of the Sleeper API reveals a significant failure mode regarding future draft capital: the API lacks a native endpoint to display untraded future draft picks.2 Consequently, the engineering specification must include the implementation of a deterministic pick-reconstruction algorithm utilizing transaction ledgers to accurately map future capital. The initial deliverables for Phase 17 must strictly avoid all user interface polish, concentrating entirely on governed data artifacts, comprehensive coverage reporting, and uncompromising identity resolution.

## **Proposed Phase 17 Objective**

The primary objective of Phase 17 is to construct the Sleeper Universe Valuation and League Opportunity Map, a systematic analytical framework capable of assessing every relevant dynasty asset within the Sleeper ecosystem and evaluating those assets against the specific context of a Superflex PPR league environment.

Historically, the Dynasty Genius system has scored players in isolated contexts, such as the /roster/audit or /trade/analyze decision surfaces.1 By transitioning to a global batch valuation paradigm, the system unlocks several advanced analytical capabilities. It enables the dynamic calculation of baseline replacement levels, the measurement of true positional scarcity across the league, and the programmatic identification of arbitrage opportunities where the internal Dynasty Value Score (DVS) and expected Value Above Replacement (xVAR) diverge significantly from active market consensus. This architectural evolution transforms Dynasty Genius from a system that merely answers valuation questions into an engine that proactively dictates strategic roster movements and trade negotiations.

## **Sleeper Universe Ingestion Design**

The ingestion layer serves as the foundation for the entire Phase 17 architecture. It must process the complete Sleeper ecosystem while ruthlessly filtering irrelevant entities and gracefully handling unstated API behaviors. The architecture mandates strict adherence to the Databricks Medallion pattern, advancing raw JSON payloads into the Bronze layer, normalizing cleaned identities within the Silver layer, and generating actionable roster states in the Gold layer.1

### **API Endpoints and Ingestion Mechanisms**

The Sleeper /v1/players/nfl endpoint provides the core foundational data for the entire valuation universe.3 This endpoint returns a massive, deeply nested JSON dictionary containing every player in the Sleeper database, encompassing active roster personnel, inactive players, practice squad members, and retired individuals.3 Because the response payload is exceptionally large, the API wrapper must fetch and serialize this data into the Bronze storage layer on a highly scheduled cadence. During the offseason, a weekly refresh is sufficient, whereas daily or hourly refreshes are necessary during the active NFL season, training camp, and rookie draft periods to capture real-time depth chart and status modifications.

To map these individual players to specific dynasty league managers, the system requires the ingestion of roster states via the /v1/league/\<league\_id\>/rosters endpoint.3 The resulting JSON payload includes the roster\_id, the canonical list of all player IDs currently held on the active roster, and distinct arrays that categorize the specific subset of players occupying the taxi squad and reserve (Injured Reserve) slots.8 Identifying the precise roster designation is critical, as taxi squad players and injured reserve players possess vastly different immediate-year utility profiles compared to active starting lineup personnel.8

Furthermore, to translate the generic roster\_id integers into human-readable manager profiles, the system must independently query the /v1/league/\<league\_id\>/users endpoint.4 This yields the display names, avatar metadata, and historical league participation records required for the eventual construction of the league opportunity map and partner ranking algorithms.

### **The Draft Pick Reconstruction Algorithm**

The most critical and complex gap identified within the Sleeper API is the complete absence of a consolidated endpoint that explicitly lists all future draft picks currently owned by a specific roster.2 The API documentation only provides access to the /v1/league/\<league\_id\>/traded\_picks endpoint, which returns a historical ledger of picks that have changed hands.2 Relying solely on this endpoint results in severe blind spots regarding natively held future capital, which is a massive liability for any system attempting to execute the "Great Liquidation" strategy aimed at accumulating 2027 first-round draft capital.1

To solve this critical data gap, the Silver layer of the data platform must implement a deterministic Pick Reconstruction Algorithm based on distributed ledger principles. First, the algorithm executes a baseline initialization step. The system must programmatically assume that every active roster\_id in the league begins its existence with a standard, full allocation of future draft picks spanning the next three years. For a standard twelve-team league utilizing a four-round rookie draft, the system instantiates forty-eight virtual picks per future season, assigning each pick sequentially to its original default owner.

Following initialization, the algorithm applies transaction deltas. The system queries the /v1/league/\<league\_id\>/traded\_picks endpoint, ingesting the JSON arrays that contain the season, round, roster\_id (the original owner), previous\_owner\_id, and owner\_id (the current possessor) fields.3 The algorithm treats this array as an ordered event log. It iterates through the traded picks sequentially, matching the season, round, and original roster\_id of the virtual pick instantiated in step one, and mutates the current owner assignment to match the final owner\_id field. By tracing the chain of custody from the previous\_owner\_id to the final owner\_id, the system perfectly reconstructs the current distribution of future capital across the league without requiring a native API endpoint.

Finally, for the current calendar year's draft, the system must execute a reconciliation pass. It must query the /v1/draft/\<draft\_id\>/picks endpoint to identify which specific draft slots have already been converted into actual player assets.3 Any pick that appears in the draft results must be purged from the reconstructed future capital ledger to prevent double-counting the value of the pick and the value of the newly drafted rookie.

### **Identity Resolution and Strict Filtering**

Silent fuzzy matching is strictly and explicitly forbidden by the Dynasty Genius operating principles.1 The Silver layer must filter the massive /v1/players/nfl payload using deterministic, algorithmic criteria rather than probabilistic text matching.

The inclusion criteria dictate that the system must retain players associated with an active NFL team, free agents explicitly categorized under relevant offensive skill positions (Quarterback, Running Back, Wide Receiver, and Tight End), and incoming rookies who are explicitly mapped by the Engine A prospect database. The exclusion criteria demand the immediate purging of all defensive players (as Individual Defensive Player formats are out of scope), explicitly retired personnel, and long-term unsigned free agents who project to provide zero future dynasty value.

The mapping process requires the Sleeper string ID to be deterministically matched to the canonical player\_id established in the Databricks data platform.1 If an identity cannot be resolved perfectly—for example, if a player's name is spelled differently across college and professional datasets without a matching universal identifier—the row must be immediately pushed to a manual triage queue and assigned a PRE\_MODEL status. No adapter is permitted to invent its own production identity logic, as corrupting the identity layer fundamentally destroys the integrity of the valuation metrics.

## **Full-Universe PVO Artifact Design**

The Player Value Object (PVO) represents the canonical data structure for all player valuation within the Dynasty Genius architecture.1 In Phase 17, the system must undergo a significant transition from assembling PVOs in isolation upon user request to orchestrating a full-universe batch process that continuously calculates values for thousands of players simultaneously.

### **Batch Processing and Algorithmic Routing**

The batch valuation pipeline must iterate through every valid entity within the filtered Silver universe table and route each player to the appropriate machine learning engine. The system utilizes a tripartite routing logic.

The first path is the Engine A route, which is strictly applied to incoming rookies and pre-NFL prospects. This pipeline consumes draft capital, entry age, and position-specific college production metrics to output the raw DVS and replacement-adjusted xVAR.1 Crucially, the feature vectors for Engine A must be rigorously protected against temporal leakage; no future NFL statistics or market consensus data may enter this matrix.

The second path is the Engine B route, applied to active NFL veterans possessing sufficient professional usage and efficiency data. Following the Phase 6 specification, this route utilizes position-stratified Ridge models governed by explicit feature contracts.1 Quarterbacks are evaluated on EPA per dropback and Completion Percentage Over Expected (CPOE), while running backs and wide receivers are evaluated on snap share, weighted opportunity, and targets per route run.1

The third path handles the blend window. For players currently in their first or second professional season where historical NFL data remains sparse and volatile, the batch process must establish a mathematically weighted blend between the Engine A pre-draft prior and the emerging Engine B active signal. This prevents massive, erratic swings in valuation based on a small sample size of early-career professional usage.

Players lacking sufficient features to generate a reliable model score across any of these three paths must not be silently imputed with median values or zeros. Instead, the batch processor must assign them an explicit model\_grade of PRE\_MODEL and entirely exclude them from aggregated team-level xVAR calculations.

### **Mandatory PVO Fields and Caveat Enforcement**

Every single row generated within the full-universe valuation artifact must strictly conform to the Phase 8 PVO contract.1 Required payload fields include dynasty\_value\_score, xVAR, projection\_2y, age\_value\_context, risk\_flags, and top\_drivers.1 The counter\_argument field must also be dynamically generated and appended to ensure that no valuation is presented with false certainty.

The batch process must programmatically enforce constraints regarding under-validated positional models. Currently, the Tight End (TE) positional models remain in an experimental state due to validation challenges.1 Therefore, any batch valuation executed for a Tight End must automatically append the "engine\_b\_experimental\_v1\_fallback" string to its caveats array and forcefully set the model\_grade to "EXPERIMENTAL".1 Furthermore, the decision\_supported boolean flag must be permanently hardcoded to false for these specific assets until a future composite validation gate is successfully cleared.

The batch process is also responsible for preserving extensive data lineage. It must attach the specific source timestamp, the parser version, the governing doctrine version, and the exact scoring date to every generated PVO to ensure total auditability of the valuation artifact.1

### **Rigorous Coverage Reporting**

Before any downstream opportunity maps or trade partner algorithms are permitted to execute, the Gold layer of the data platform must emit a versioned coverage report detailing the exact health and scope of the batch run. This represents a critical quality gate.

The acceptance criteria for the batch execution require the report to log the total number of Sleeper players processed, the precise count of fantasy-relevant players retained after exclusion filtering, and the exact distribution of scored Engine A, Engine B, and Blended entities. Furthermore, the report must surface the count of PRE\_MODEL failures and unresolved identities. The pipeline must fail and alert the administrator if the proportion of unresolved identities for top-tier dynasty assets exceeds a zero-tolerance threshold. Most importantly, the coverage report must execute a strict assertion proving that no market data from the FantasyCalc overlay was present in the feature vectors utilized during the scoring of the predictive models.1

## **Team-Level Roster Valuation Design**

Aggregating individual Player Value Objects into a coherent, team-level valuation requires rigorous mathematical design. A simplistic summation of individual player values fundamentally misrepresents the economic reality of dynasty leverage. In a constrained starting lineup format, treating a massive bench composed of mediocre replacement-level players as mathematically equivalent to a highly concentrated roster of elite, top-tier starters is a critical error.1

### **The Sub-Replacement Capping Mechanism**

To accurately reflect the economic realities of a Superflex PPR environment, the team-level valuation logic must heavily prioritize starter-weighted output over raw bench depth. The system must aggregate roster value strictly using normalized Replacement-Adjusted Value (xVAR) rather than the raw Dynasty Value Score (DVS).

The mathematical aggregation formula must apply a non-linear decay weight to bench assets. Assuming a starting lineup requirement of ![][image1] active players, the algorithm sorts all available players on a given roster by their respective xVAR in descending order. The top ![][image1] players, representing the optimal starting lineup, receive a full multiplier weight of ![][image2]. The subsequent tier of players, representing the primary bench depth (![][image3] to ![][image4]), receives a fractional multiplier—for instance, ![][image5] or ![][image6]—to reflect their conditional utility as bye-week fill-ins or injury replacements. Finally, players falling below the replacement threshold or occupying the deepest bench spots receive a strictly capped multiplier approaching ![][image7]. This sub-replacement capping mechanism structurally prevents the "ten bench players equal one elite starter" failure mode explicitly banned by the system operating principles.

### **Handling Non-Standard Roster Slots**

The Sleeper platform features specialized roster designations that must be handled with distinct mathematical logic. Players occupying the taxi squad array 8 must be valued exclusively using their future, multi-year xVAR projections. Because taxi squad rules generally prohibit these players from contributing to immediate weekly starting lineups without a formal promotion, their current-year starter weight must be algorithmically forced to ![][image7].

Conversely, players residing in the reserve array (Injured Reserve) 8 retain their full, long-term dynasty DVS and xVAR. However, the system must programmatically flag their immediate-year production impact as zero. This distinction is vital for accurate contender versus rebuild archetyping; a roster may possess massive aggregate long-term value via injured superstars, but practically function as a tanking team in the current season.1

Future draft picks, reconstructed via the algorithm outlined in Section 3, are integrated into the team valuation matrix by assigning them baseline Engine A expected values. For example, an expected 2027 mid-first-round pick is assigned a fixed E27 equivalent weight of ![][image8], which translates into a static xVAR baseline derived from the historical average return of that specific draft slot.1

### **Positional Surplus and Deficit Mapping**

The system is required to group the aggregated, starter-weighted xVAR into discrete Quarterback, Running Back, Wide Receiver, and Tight End buckets for each individual team. A team's positional strength is measured not as an absolute, isolated number, but as a comparative delta against the dynamic league average for that specific position.

The surplus logic calculates the difference between the team's positional xVAR and the league average positional xVAR. A highly positive surplus indicates inefficient positional hoarding, signaling to the opportunity map that the team is a highly probable seller in that specific market. Conversely, a highly negative delta indicates a structural roster deficit, marking the team as an aggressive buyer and a prime target for arbitrage.1

## **Over/Undervalued Detection Design**

The detection of mispriced assets relies on comparing the internal predictive model's valuation percentiles against active market perception. FantasyCalc serves as the designated active market source for this comparison, while KeepTradeCut (KTC) is explicitly excluded from active production inputs.1

### **Divergence Architecture v2**

Phase 9 of the Dynasty Genius system established a standard NOISE\_BAND \= 0.10 for market divergence. Phase 17 must extend this logic across the entire Sleeper universe. The divergence engine calculates the numerical delta between the player's internal DVS percentile and their corresponding FantasyCalc market percentile.

A player is systematically classified based on the magnitude and direction of this calculated divergence. If the DVS percentile exceeds the market percentile by a margin greater than the established noise band, the asset is flagged as a "Target" (indicating it is undervalued by the broader market relative to the internal model). If the market percentile exceeds the DVS percentile by a margin greater than the noise band, the asset is flagged as a "Fade" (indicating it is overvalued). If the absolute value of the divergence falls within the strict boundaries of the noise band, the asset is classified as a "Hold," indicating alignment between the model and market consensus.

### **Status-Specific Divergence Adjustments**

The baseline divergence architecture requires specific parameter adjustments based on player status. Because rookie market pricing is inherently highly volatile and heavily influenced by severe recency bias immediately following the NFL draft, the standard noise band for Engine A prospects must be algorithmically expanded from ![][image9] to ![][image10]. This prevents the system from generating erratic, false-positive arbitrage signals based on minor fluctuations in rookie draft ADP.

The Tight End positional models require a hardcoded override within the divergence engine. Due to the explicitly documented experimental nature of the Engine B Tight End architecture, any Tight End mathematically triggering a "Target" or "Fade" flag must automatically fail the downstream validation gates. The output layer must forcefully suppress any actionable language for these assets, appending a market\_divergence\_deferred flag instead to comply with the mandate preventing false certainty.1

Furthermore, the system must implement strict stale data mitigation protocols. If a player's FantasyCalc market data timestamp is found to be older than seventy-two hours, the market percentile must be nullified. This critical safeguard prevents the emission of false divergence flags caused by rapid, real-world market shifts, such as catastrophic injury news that has not yet propagated through the scraping infrastructure.

The architecture must strictly sandbox this entire divergence analysis. The divergence output is generated exclusively within a separated reporting layer and must never be permitted to feed backward into the pvo\_assembler or the Medallion Bronze and Silver tables.1

## **League Opportunity Map Design**

The culminating analytical layer of Phase 17 utilizes the team valuation matrix and the market divergence engine to systematically rank potential trade partners and identify highly actionable opportunities perfectly tailored to the user's specific roster context and strategic timeline.1

### **Identifying Actionable Arbitrage**

An actionable opportunity is mathematically defined by the system when three distinct conditions intersect harmoniously. First, the user's roster must possess a calculated positive positional surplus (for example, excess xVAR residing in the Running Back room) or a glaring positional deficit (a lack of viable starting Quarterbacks). Second, an opponent's roster must exhibit the exact inverse conditions—a surplus of Quarterbacks and a deficit of Running Backs.

Third, and most importantly, the specific individual assets required to bridge this roster gap must exhibit favorable market divergence. The opportunity achieves maximum leverage when the opponent holds an asset flagged as a "Target" (undervalued by the market) and the user holds an asset flagged as a "Fade" (overvalued by the market). The execution of this trade leverages the market's inefficiency to extract surplus value while simultaneously optimizing both starting lineups.

### **Partner Ranking Algorithm and Roster Fragility**

The opportunity map must iterate through all opposing rosters within the league and score them algorithmically as potential trade partners. The partner scoring mechanism is heavily influenced by the Roster Fragility Index outlined in the 2027 Target Differentiation strategy.1

The system evaluates opponents based on Roster Fit, which calculates the absolute sum of complementary positional surpluses and deficits. It subsequently evaluates Asset Alignment, measuring the sheer concentration of "Target" flagged assets currently residing on the opponent's roster.

Crucially, the algorithm evaluates the opponent's Rebuild versus Contender Posture. This is measured by analyzing the Biological Debt of the opponent's roster (the count of starting assets operating past their positional age cliffs) and their Quarterback Instability.1 Rebuilding teams displaying high Roster Fragility scores are flagged as the absolute highest-probability targets for the user's veteran "Fade" assets, facilitating the execution of the "Great Liquidation" strategy to acquire Tier 1 2027 draft capital.1 If the opportunity map detects a highly fragile roster holding a premium 2027 first-round pick, the system routes the recommendation toward the "Ambush Swap Protocol" to verify the opponent's true rebuilding intentions.1

### **Output Constraints and Governance**

The resulting opportunity map must generate structured JSON artifacts containing "Opportunity Cards." To adhere to the strictest governance rules, these initial cards must forcefully set the decision\_supported boolean to false. Explicit, actionable language such as "Buy Now" or "Sell Immediately" is strictly prohibited until the heavily calibrated uncertainty bands and composite validation gates are fully integrated into the architecture.1 The cards will surface the quantitative delta, the positional overlap, and the E27 currency translation, allowing the user to interpret the rigorous data without the platform projecting false certainty.

## **External Tool Comparison**

To ensure that the Dynasty Genius architecture provides a distinct, compounding competitive advantage, its design must be contrasted against prevailing commercial market tools, specifically the visual layouts of Dynasty Nerds and the roster analyzers provided by KeepTradeCut.

### **Concepts to Emulate**

The visual positional breakdowns pioneered by Dynasty Nerds are highly effective. Dynasty Nerds excels at displaying aggregate team value categorized strictly by the Quarterback, Running Back, Wide Receiver, Tight End, and Future Pick dimensions. Dynasty Genius will replicate this specific taxonomy within its underlying data schema, allowing for rapid, programmatic digestion of league-wide roster construction. Furthermore, the concept of age-stratification—separating total roster value from "contender value" (short-term utility) and "rebuild value" (long-term optionality)—is highly relevant. Dynasty Genius will adapt this structurally by simultaneously exposing the projection\_2y vector alongside the raw, long-term Dynasty Value Score.

### **Anti-Patterns to Strictly Avoid**

Commercial tools frequently treat their aggregated market data—whether it is KeepTradeCut's crowdsourced inputs or FantasyCalc's scraped transaction logs—as the ultimate, objective arbiter of a trade's mathematical success. Dynasty Genius fundamentally rejects this philosophical premise; market data exists strictly for price discovery and divergence flagging, not absolute truth.

Additionally, KeepTradeCut's roster analyzers frequently utilize uncapped summation methodologies, calculating the entire depth chart as a single aggregate number. This results in the analytical failure where a team hoarding fifteen mediocre depth receivers appears mathematically superior to a team fielding two elite, top-tier superstars. Dynasty Genius will systematically avoid this critical error via the starter-weighted xVAR capping mechanism. Finally, commercial tools frequently rely on fuzzy identity matching, silently merging player identities across disparate platforms. Dynasty Genius will drop unmapped IDs to a completely neutral PRE\_MODEL state rather than risk the catastrophic cross-contamination of predictive features.1

## **Data Source Table**

The following Markdown table outlines the requisite endpoints, the explicit governance status, and the mandatory operational failure parameters for Phase 17 data ingestion.

| Source | Endpoint / Export | Role | Refresh Cadence | Governance Status | Failure Behavior |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Sleeper API** | /v1/players/nfl 3 | Global universe baseline, player metadata, IDs. | Weekly (Offseason) / Daily (In-season) | Approved | Alert on schema change; cache previous valid JSON payload. |
| **Sleeper API** | /v1/league/\<id\>/rosters 3 | Roster slot mapping, taxi squad, IR designation. | Daily | Approved | Retain previous active state; flag the Gold output as stale\_roster. |
| **Sleeper API** | /v1/league/\<id\>/users 4 | Manager identity and display name mapping. | Weekly | Approved | Fallback to displaying raw roster\_id integers if missing. |
| **Sleeper API** | /v1/league/\<id\>/traded\_picks 3 | Future capital mutation logic and tracing. | Daily | Approved | Revert to the baseline un-traded pick state; log a severe warning. |
| **Sleeper API** | /v1/draft/\<id\>/picks 3 | Current-year rookie draft state reconciliation. | Hourly (During Draft) / Weekly | Approved | Exclude the current active draft from valuation totals. |
| **Sleeper API** | /v1/state/nfl 11 | Season type and current week tracking. | Daily | Approved | Default safely to the offseason state if unresolved. |
| **FantasyCalc** | Internal DB / Scraper | Market price discovery and divergence logic. | Daily | Approved (Overlay Only) | Nullify the market overlay; force Divergence \= None. |
| **KeepTradeCut** | Scraper / External API | Legacy market data and crowdsourced pricing. | N/A | **Rejected** (Production) | Deferred to future phases; actively blocked from Engine models. |

## **Proposed Artifacts and Schemas**

Phase 17 must output deeply structured, version-controlled artifacts to the Databricks Gold layer. The following JSON schemas rigorously define the required structural contracts for downstream consumption.

### **1\. Universe Snapshot Schema (universe\_coverage\_report.json)**

This specific artifact fulfills the mandates of Phase 17.1, providing essential administrative governance over the ingestion process and ensuring that no fuzzy matching or market leakage has occurred.

JSON

{  
  "snapshot\_date": "2026-05-17T17:02:00Z",  
  "coverage\_metrics": {  
    "total\_sleeper\_players": 8452,  
    "fantasy\_relevant\_filtered": 3120,  
    "rostered\_players": 336,  
    "free\_agents": 2784,  
    "engine\_a\_scored": 412,  
    "engine\_b\_scored": 680,  
    "blended\_scored": 124,  
    "pre\_model\_failures": 1904,  
    "unresolved\_identities": 15  
  },  
  "validation\_gates": {  
    "market\_leakage\_detected": false,  
    "fuzzy\_matching\_used": false  
  }  
}

### **2\. Full PVO Batch Schema (pvo\_universe\_batch.json)**

This artifact fulfills the mandates of Phase 17.2, generating the raw, mathematically rigorous valuation array for every valid entity in the league ecosystem.

JSON

{  
  "player\_id": "sleeper\_1234",  
  "full\_name": "Garrett Wilson",  
  "position": "WR",  
  "status": "ACTIVE\_B",  
  "valuation": {  
    "dynasty\_value\_score": 88.4,  
    "xVAR": 42.1,  
    "projection\_2y": 18.5,  
    "model\_grade": "A"  
  },  
  "context": {  
    "age\_value\_context": "peak\_production\_window",  
    "risk\_flags":,  
    "top\_drivers": \["target\_share", "route\_participation"\],  
    "counter\_argument": "Declining Quarterback play may heavily suppress absolute ceiling."  
  },  
  "caveats":,  
  "decision\_supported": true  
}

### **3\. Team Value Matrix Schema (team\_value\_matrix.json)**

This artifact fulfills the mandates of Phase 17.3, algorithmically rolling up individual PVOs into actionable, team-level strategic groupings based on positional needs.

JSON

{  
  "roster\_id": 4,  
  "manager\_name": "David",  
  "aggregate\_metrics": {  
    "total\_raw\_xVAR": 210.5,  
    "starter\_weighted\_xVAR": 185.2,  
    "future\_pick\_xVAR": 45.0,  
    "roster\_age\_profile": 25.4  
  },  
  "positional\_surplus": {  
    "QB": 12.5,  
    "RB": \-8.2,  
    "WR": 22.1,  
    "TE": \-4.0  
  },  
  "rebuild\_contender\_profile": "contender"  
}

## **Proposed Workstreams and Sequencing**

The technical execution of Phase 17 must strictly follow a linear, gated progression. Downstream engineering tasks are explicitly prohibited from commencing until upstream data artifacts have unequivocally passed their respective validation gates.

### **Workstream 17.1 — Universe Snapshot & Coverage**

The initial engineering task requires the development of the /v1/players/nfl and /v1/league/\<id\>/rosters ingestion pipelines. The system must implement the deterministic ID mapping logic to bind Sleeper strings to Dynasty Genius canonical IDs, excluding irrelevant defensive and retired players. The output deliverable is the universe\_coverage\_report.json schema. The strict quality gate demands empirical proof of zero silent fuzzy matching and ensures that the count of unresolved\_identities for top-300 dynasty assets equals precisely zero.

### **Workstream 17.2 — Full PVO Batch**

The secondary task involves iterating the Silver universe table through the existing pvo\_assembler. The pipeline must handle data exceptions cleanly by assigning the PRE\_MODEL grade rather than imputing false averages. It must programmatically append Tight End explicit caveats to the output arrays. The final deliverable is the pvo\_universe\_batch.json artifact. The associated quality gate demands automated testing to validate that absolutely no market variables were passed into the Engine A or Engine B mathematical feature arrays.

### **Workstream 17.3 — Team Value Matrix**

The tertiary task centers on constructing the highly complex draft pick reconstruction algorithm. The system must parse the /traded\_picks ledger and successfully mutate the baseline capital allocation. Following this, the engineering team must implement the starter-weighted xVAR capping formula to accurately aggregate team strength, calculating precise positional surplus and deficits against dynamic league averages. The deliverable is the team\_value\_matrix.json artifact. The validation gate requires a mathematical proof demonstrating that a constructed roster of fifteen bench wide receivers yields a significantly lower starter-weighted xVAR than a roster fielding three elite wide receivers.

### **Workstream 17.4 — Market Divergence v2**

The fourth task requires the ingestion of FantasyCalc market percentiles and the mapping of FantasyCalc IDs to the canonical Dynasty Genius identifiers. The pipeline runs the formalized divergence formula utilizing the ![][image9] noise band for established veterans and the expanded ![][image10] band for highly volatile rookies. The deliverable is an augmented PVO batch featuring a distinct market\_overlay object that houses the divergence flags. The critical quality gate requires strict verification that Tight End divergence flags are forcefully suppressed or heavily caveated due to their active experimental status.1

### **Workstream 17.5 — League Opportunity Map**

The final engineering task involves constructing the partner ranking algorithm, which elegantly combines the positional surplus mapping with the divergence flagging and Roster Fragility Index calculations. The system must generate localized opportunity cards tailored to the user's explicit strategic posture. The deliverable is a backend JSON service outlining the top highest-probability trade frameworks currently viable within the specific league ecosystem. The ultimate validation gate ensures all opportunity cards are emitted with the decision\_supported flag set to false, fundamentally preventing premature strategic execution based on uncalibrated predictive models.

## **Acceptance Criteria for Phase 17 Spec**

A developer agent tasked with transitioning this rigorous research brief into a finalized implementation specification must ensure the following highly technical criteria are explicitly detailed and met:

First, the engineering specification must comprehensively detail a Python-based execution script that successfully pulls, parses, and serializes the full Sleeper NFL universe payload without encountering memory faults or timeout errors. Second, the complex logic required for inferring untraded future draft capital from the /v1/league/\<id\>/traded\_picks delta ledger must be fully documented utilizing clear mathematical pseudo-code. Third, the universe\_coverage\_report must flawlessly track the transition of every single Sleeper identifier into either a fully scored PVO, a documented PRE\_MODEL failure, or an explicit categorical exclusion.

Furthermore, the mathematical formula dictating the calculation of starter-weighted xVAR must be rigidly defined within the specification to aggressively decay the assigned value of bench assets. The specification must logically assert, fully backed by automated unit testing protocols, that the FantasyCalc data overlay is processed entirely *after* the pvo\_assembler execution, physically eliminating any possibility of predictive data leakage.1 Finally, all Tight End records and generated Opportunity Cards must demonstrably retain decision\_supported=false and visibly display the mandatory experimental caveats mandated by the architectural doctrine.1

## **Risks and Failure Modes**

Several critical, system-level failure modes possess the potential to jeopardize the stability and strategic viability of Phase 17 if not actively anticipated and systematically mitigated.

The primary technical risk involves Sleeper API Rate Limiting. The official API documentation explicitly warns developers against exceeding a threshold of one thousand calls per minute.3 While the /v1/players/nfl request is a singular, heavy payload, querying individual draft endpoints recursively or looping through transaction ledgers can rapidly trigger aggressive IP blocking from the provider. The requisite mitigation strategy involves implementing robust local caching mechanisms and engineering the fetching algorithms to respect rate limits mathematically. Similarly, memory exhaustion during ingestion remains a significant threat. The /v1/players/nfl JSON response is exceptionally large and deeply nested. The mitigation requires the pipeline to process the JSON response in highly manageable, chunked batches as recommended by standard integration practices.5

Strategic risks involve the inherent fragility of the Future Pick Logic. The algorithm for inferring future draft capital fundamentally assumes standard league settings. If the specific Sleeper league settings mutate unexpectedly, or if a league commissioner manually removes or adds a draft pick outside of a tracked trade, the reconstruction algorithm will instantly drift from economic reality. The primary mitigation strategy demands the provision of a strictly formatted configuration file that maps the expected baseline picks per year, allowing for precise manual intervention when API fidelity degrades.

Furthermore, the system faces severe risks regarding Market Data Timestamp Decay. Relying upon the FantasyCalc integration for divergence flagging implies the necessity for pristine daily freshness. If the external market scraper breaks silently, the Dynasty Genius architecture might erroneously flag a massive "divergence" simply because the internally cached market price is a week old. The required mitigation protocol must instantly invalidate and nullify any market percentiles if the associated source timestamp is determined to be older than seventy-two hours. Finally, Identity Resolution Silencing represents a catastrophic failure mode. If a highly prominent incoming rookie changes their name or identifier arbitrarily within the Sleeper database, they may silently fail the deterministic mapping protocols and plummet to a PRE\_MODEL status, drastically and incorrectly altering a team's positional surplus calculations. Mitigation requires establishing strict, automated telemetry monitoring on the unresolved\_identities metric specifically for the top-300 market-valued players.

## **Explicit Out-of-Scope Items**

To fundamentally prevent architectural scope creep and ensure unwavering focus on data platform integrity, the following items are strictly and explicitly defined as out-of-scope for the entirety of Phase 17:

No engineering resources shall be allocated toward User Interface Polish. There will be no development of frontend dashboards, web rendering logic, or polished graphical views. The required deliverables for this phase are strictly backend JSON artifacts and data engineering pipelines. Furthermore, Phase 17 will not involve any Engine Model Retraining. The phase will not adjust the underlying weights, feature selections, or hyper-parameters of either Engine A or Engine B. Specifically, the Tight End experimental statuses will not be diagnosed, retrained, or resolved during this sprint.

KeepTradeCut data integration remains permanently out of active production consideration; FantasyCalc serves as the sole, explicitly approved market overlay for divergence calculations. The system will programmatically identify strategic arbitrage opportunities but will absolutely not engage in Automated Trade Execution; it will not generate automated messaging to league-mates or programmatically interact with Sleeper transaction endpoints to execute roster moves. Finally, no development resources will be expended attempting to automate or refine fuzzy identity resolution protocols.

## **Open Decisions for David**

The final technical implementation specification cannot be ratified or advanced into active development until the primary system owner provides explicit, documented governance decisions regarding the following strategic variables:

The system requires explicit guidance regarding the Bench Decay Parameters. The owner must dictate exactly how aggressive the mathematical decay should be for assets falling sequentially outside the optimal top starting slots. The configuration must clarify whether the eleventh-best player on a roster should receive fifty percent of their baseline xVAR, or a more punitive twenty-five percent.

The system also requires formal definition of the Future Pick Baseline Configuration. The owner must confirm whether the specific target Superflex PPR league currently utilizes a three-round, four-round, or five-round rookie draft architecture, and precisely how many years into the future league managers are permitted to execute trades. This data strictly dictates the initialization bounds for the required pick reconstruction algorithm.

Furthermore, the Divergence Noise Band requires formal calibration. The owner must decide whether the Phase 9 standard of 0.10 for veterans and 0.15 for rookies should be rigidly maintained, or whether these specific thresholds should be tightened as the transition to full-universe scaling reveals the true extent of broader market volatility. Finally, regarding Opportunity Thresholds, the owner must establish whether the partner ranking algorithm should explicitly prioritize targeting teams that exhibit a severe, singular positional deficit over teams that display moderate, distributed deficits across multiple roster positions.

#### **Works cited**

1. Dynasty Football Genius  
2. Draft Picks in Sleeper API? : r/SleeperApp \- Reddit, accessed May 17, 2026, [https://www.reddit.com/r/SleeperApp/comments/1l7pun6/draft\_picks\_in\_sleeper\_api/](https://www.reddit.com/r/SleeperApp/comments/1l7pun6/draft_picks_in_sleeper_api/)  
3. Sleeper API: introduction, accessed May 17, 2026, [https://docs.sleeper.com/](https://docs.sleeper.com/)  
4. Sleeper API Explained: A Complete Guide for Developers & Fantasy Founders \- SportsFirst, accessed May 17, 2026, [https://www.sportsfirst.net/post/sleeper-api-explained-a-complete-guide-for-developers-fantasy-founders](https://www.sportsfirst.net/post/sleeper-api-explained-a-complete-guide-for-developers-fantasy-founders)  
5. A Comprehensive Guide to the Sleeper API \- Zuplo, accessed May 17, 2026, [https://zuplo.com/learning-center/sleeper-api](https://zuplo.com/learning-center/sleeper-api)  
6. Assignment6 \- RPubs, accessed May 17, 2026, [https://rpubs.com/rzaccour/1364360](https://rpubs.com/rzaccour/1364360)  
7. sleeper-api-wrapper/README.md at master \- GitHub, accessed May 17, 2026, [https://github.com/SwapnikKatkoori/sleeper-api-wrapper/blob/master/README.md](https://github.com/SwapnikKatkoori/sleeper-api-wrapper/blob/master/README.md)  
8. Possible to differentiate Taxi Squad from bench when pulling from Sleepers API? \- Reddit, accessed May 17, 2026, [https://www.reddit.com/r/fantasyfootballcoding/comments/1notjf9/possible\_to\_differentiate\_taxi\_squad\_from\_bench/](https://www.reddit.com/r/fantasyfootballcoding/comments/1notjf9/possible_to_differentiate_taxi_squad_from_bench/)  
9. sleeper package \- github.com/lum8rjack/sleeper-go \- Go Packages, accessed May 17, 2026, [https://pkg.go.dev/github.com/lum8rjack/sleeper-go](https://pkg.go.dev/github.com/lum8rjack/sleeper-go)  
10. How do I set positional limits? \- Sleeper Support Center, accessed May 17, 2026, [https://support.sleeper.com/en/articles/5379935-how-do-i-set-positional-limits](https://support.sleeper.com/en/articles/5379935-how-do-i-set-positional-limits)  
11. sleeper-scraper-mcp/sleeper API Docs.txt at master · einreke, accessed May 17, 2026, [https://github.com/einreke/sleeper-scraper-mcp/blob/master/sleeper%20API%20Docs.txt](https://github.com/einreke/sleeper-scraper-mcp/blob/master/sleeper%20API%20Docs.txt)  
12. lum8rjack/sleeper-go: Go library for the Sleeper fantasy sports API \- GitHub, accessed May 17, 2026, [https://github.com/lum8rjack/sleeper-go](https://github.com/lum8rjack/sleeper-go)  
13. Trying to Use Task Scheduler With a Python Program but it's Not Working \- Reddit, accessed May 17, 2026, [https://www.reddit.com/r/learnpython/comments/17pfsws/trying\_to\_use\_task\_scheduler\_with\_a\_python/](https://www.reddit.com/r/learnpython/comments/17pfsws/trying_to_use_task_scheduler_with_a_python/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAYCAYAAAAh8HdUAAABAklEQVR4Xu3SP0tCcRTG8ZOKFSW4Ce5NEoENEeHSFAWNtQXh1NDg4htwNIiIegUu7W3SFrSEtjRJtAYNjrlUfg/ncu/vHm1zCXzgw4XzR+VcRf5tFlBDFUtRrYzleMKljgdc4x4fOMYAhWAuThNPKAa1NfzgOajFqeAb675BHnHhixr9ll+s+obYTz3wRc2N2FILGdcLD5LKodiS+sQdTrEYDvnomRv4kmRZdZEL5qZmBfu4xEhscS81EWXDF6KciS3pM5WS2Muclm2xpU3fOMIbsr5BrvAuk9eUW7FPO3H1HQzFzj2RHs7xij7a6OBF/jiAZit65sX+2fpudpP2PLPLGJWFLMbXxFTsAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAABRklEQVR4Xu2UvytGURiA3/wsKVI2g8HArMjgD2CSBUkilJhMmAwKg5FsNvkD/BpMYmQShTIZGJUBhed1zr2d+3YvnbKo76mnr/uc03m/bvdekRL/gWYctfEX6nEE13Acq7PLjjZcxXP8wP3s8o804RWuYxdu4TU2hJuUDnH/oB1fJW7ILu6ZdobbpmWIGdIobv+c6cv4IgW3TYkZ0oefOGa6DtXebXpKzJBJcYcNmT7j+4DpKTFDFiT/sGnf9TcXHXJgYwHz4g4bND0ZMmV6ig45tLGACXGHDZs+63u/6SkxQ3ok/7Ys+t5peooOObLRo49sS3BdI+5RXQmaoi/kE5ab/k0lvuEJVpg15R7fxX16EjbxAsv8dRXe4VKyIaEXb/EBn72PeIN1wb4dvMTaoOmhx169bae4Eaz/Ka3i3hf9DpYoIfIFcfxH6saN3DMAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAYCAYAAACFms+HAAABpUlEQVR4Xu2WSygFYRTHj/e7ZKOsbKwkxUKSbiklykaxUEpWFhYWHlvJQpQkyt5N9lZkoZSNsLGSZKcsxIaNx/84M/fOHNPMN3euocyvfk2dc77mzL3fiyghITIFsBu2wXIr1gArMhV/kAl4BDfgPryHI/Aa1jjq4iJl6cssPIW1jlgTfIdnjthP0wu34S38gDPutJtm+AZbdAKcwFUdDICnW1oHDRmCw3CUDBrnX5uLqnWCZNoM6GAAxfBAB0PSSQaNb5IULcJClXMuUlNKKKbGB0mK2Ae4B8dhmbMoBKUUU+M8J6fhC2U/gD0k+dvDElvjNlWwH67BV5KBfa6K79SR7PNOG+GxR5yt/BoVjN04rz9PWnXAYpJkID/9WIa7Sp5qfAboOMs7hgl243M6wdSTHDhe2APbdcKAfE4Vz8b5629gkU6AdZJDQO8yJuSz8XmdYLZIkmMq3gUfSbbCXMhH4ymS3pZ0gjmHU/AKXsAVuAMvKXhR+hGl8QWSuxFvy0/wGd6R3J0ydFhPfhHfCHnv7smmcyZK478Knwt8qCUkJPwXPgHIC1nH8LW5MAAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADQAAAAYCAYAAAC1Ft6mAAACPUlEQVR4Xu2WTUhUYRSGj+ZPmoEIJtTGjaCECBWIiJs2ikLtaieIixRtEYQ7V61EMUStlQvFkMB2QZAVBEmbSF0ohviTutAC3QiKkPq+nevMnTPD3Jk7gz9wH3i4cM53Z85375nzjUhAwIUhA9bBO/CqE7sJ80IrLhGt8DMchO/hFnwMl+B117qzoBOuidZAN+EqXIHr8At8CDOd9VF0we+w0BUrg0fwhyt21mzAPzDbFcuC/fAYdrviIW7Df7DSJsA32GeDHrBt39igD9jqLPqtTYAi0RzfHr8vAr4dJgtsQrT9mmzQAz7BjzboA7Y762qzCXBPNDdnE2RYNPlConvSPRwShe2Rjg29Eq2r3MT5+R/gnugAi+KB6I30r+grboG57kVJkCPp2dCCaD1sL1oMG0QHwidYE14aCXvwGdyX8MbolGj7JEs6NlQiWsMiHIOjzpVTeFq05Ty5BhvhS3gg+oF8IvHgk+OP120p/BojTvP/3+VNvN8PHz5zT2yCVNmAQ7voTbzGowdOGNmynD42Th/pbZ68Fv3+CpsAN0Rzv2yCr5WvMBbsT9501yYSIB0tx2J5/sSCQ4K1LdsEnxaDV2wCDIiezHbqJUKqG7olWvCkTTiMiOaf28TpWGw28Vq4Kzqy/ZDqhvgXjHV1mDin3OkRMyQxDtSf8CmchzOwF47DWfEeBvHwuyEOgN/wULToHdH/c/z/xus2fAfrdXk01c6VBfCA4tlzP5z2jd8NXVjYCjysAwICAs6HE+1benclkZ9aAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAABl0lEQVR4Xu2UPShGURjH/4QkyUAhSiKJKBbkazBYbL7GVxZZZCGFSAYGyoJYCCUmRUb5HMSkJMmk2CwsFP/zPve8zn3e++7K+6tft/u/z/m4555zgTh/mUTaTmfoEM31P45JC+2lVTSVVtI+2uzUhEmhe/SANtFh+kzr3KIYTNFv5RkCJtlPX2mak5k3eqBJThbEJL2lV3SLDtBkt8ByQ/dV1gqZVYPKNRM0pENNJqSzdZVXe/m4yjXmeUiHmhJIZysqL/fyJZVrxugs3aWn9JAW+CogHzeoszIv31G5ZpRe0yzvvoO+0bZIBamFdLbshvgdZFvlmhzIkrs80UfIsQhTDOls1QYeFV6+qHJNgg7IOaRtkQ3S6Reil6UeUjiicpc8yNZfUPkJpK2ZaIRjeukGpAdSaE6wJRvy5pZSSM2akxnu6QfUeemm75CZWTYgg7uYtf6khU52RPOd+xrIwGZDRDFN7+gg3aQXNMNXIZvAnG6zxJZGyCrM0zn64l1j/inMTumCbOvAX0MMzMc3bTrhf8s4/5kfp5RQg0QkCBoAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAABnUlEQVR4Xu2UPShGURjHn+SjfEsKGQwMIsqEpEhkYBI2I5sslMIg7BavLEhKmZQiikEkksFHUj6SQWYlH/E/nnPu+9yn632Nyvur33D/97nnnPvccy5RjL9MHGyF47Af5vlvRyQZ9sBR4jEy/LeZRLgC12AdHIAPsFoW/UAj3IC9sB7uwntYJosMpuCReEUO80ZXMF5kQZzAMwqvvgF+wnWvwnIMV1VmVmiKa1WuOYQfsNBeu0m2XYEh04bzMgSVNh9WuSYFFojrIeLnzDfyKLbhjAxBqc2nVR6JFvgE58jf+u+PGzRYic2XVR5EGtyC1/CIuDs+qogHC6ncTbKk8miMEG+iNhkWEQ82K0PiLWjyKZVHw7TpnfgIeDsz1Ya6LTXEkwyqXJIOJ2GTyu+In22W4Q7clwHoIi4sF1kO8Zs7uolrLkWWAF9tblru0QmfYb7IFognl9zANwqfiQr4QnyYHe4bH4jMYwxewD64CPeI2yExm+CUuMWOdngOJ4jPyC3chFmixkcu7CDe1ua1f0sS8Z/BTJit7sX4r3wBUSBSmoHkEUsAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAABmUlEQVR4Xu2UOyiGYRTHT64lSUohg4EiMlhcwmQxKBlckoEQUWJwK6WQDBbllkEkUSaxGQwum0kMlMnAbhDF/zjnqfOdz2U1fL/69dXvPb1P7/M970sU4z8TBxvgHByG2ZGXfyUddsAF2AWTIy8LSfAAHsNaOAofYaUd+oFceAMXSebX4C3MsENMH3yCKabxE93BBNO+Yw8euXYON12jK3joWh38gNWuWzLhKxxxfRa+kNk23k++2VYISpn2KdctjSQzna7zotxrQijQsB6CUqx91XVLD8lMm+sD2ltC4D/ru5sVad933TJB7mZKv3b+/aJCA58KS1hk13XLOMlMq+thkd4Q8jVshKCUaF9y3dJNMtPu+qD2phBS4TtFb0sVyeCY65Z6ctuiTGovt/EUXtpAsgU8WGoaH1l+8gC/V3xU501jeOufYbyN/MfxcI5p2ySLWx7gG8wzbYXkPePPEsNfj3s4HQYsMySfgyG4Ay9gWsSEHIJrki0O8E1PVN62M7hsrkeRBZtJjnWiu/YXhSTvC5/KGDGIPgF+tlXPWDCe0gAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACIAAAAXCAYAAABu8J3cAAAB+UlEQVR4Xu2VzUtWQRTGjx+piJEEQosWgiJFK0mUFm0FW0mbDBEpLIikhbjIciESpIvcKe7ciX9AaQvdhC5cKCKWX4kIpqauFEETyufxzNw7d7qvcqFNcH/wQ+Y5o3PmHWdekZSU5JTCZj+8hGLYBHvhU5gfLQfUwLewE1Z6tXNuwx44A3/DT9HyhdyE3+AHeA8OwkV43Z0E2uFX+BA+hiuwNTIDVIvu5C48kWSNjMCPXjYFh5wxN/oHVjlZrehaFU4WIUkjJaLz27z8HTyS8Ij64EFYPidP9NPnMcWSpJF60Z0+8XI2xvy+Gc/BjbAcwOYm/NCSpJFnogvyzF1emvyRGf+Ay2E5YE/0/ymWJI10SHRBywuT8yfh34xb8KcxFv7SqB9m4LXogg1ebht5bsbHcCksB7CJLT+0sJExP8xAi+iCjV7Oa8mcV5VswtWwHLAP5/3QkqSROokegeWNyfmAkWn5+wiy5JK1WPzshwZe13JnXCh6Td87GeGjtgtzzLhL9KoW2Anghmizr5ws4Ar8Bb/AXK9G1uGp6NeAZQDOwmwz5vvwXXRxSxk8FL3uFj6gO6INBTwQPUNeM95tyo+Sz/A1Z94wXIBFTsaFx408oknY79QtPMZt2C36dbIG70Rm/CNuib4nfM4zwQ1w02zqqldLSfk/OAMp0HEG1SYqFQAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACIAAAAXCAYAAABu8J3cAAAB90lEQVR4Xu2UT0hVURDGv8RERKWNkK0ELRAjMAIzxLdRwSCIAi3atXIRSqApVFBJ4MqFmxJXSgSCqyhaBa2MNhFh9I8QoVLRTYlQFOo3b+55zJ3eebhwI7wf/Bb3m+N5451zD1CkyO4poefofXqd1qbLuyKTGKOF3qS3aLOrZSmjc/QZbac36HfaahdF6KSTdJFu06F0OccgfU8v0Mv0M72WWkH66CqtMJm8mS+01GT5uEh76BXEG2mE1k6ZrIv+ocdMhjf0iQ1IB/SP21weQ95erJFx+stlMoUt6JiyHIJuMB2ChJNJftvlMQo18pYu+RDa3IvwcBS6gczZ0pTkD1weo1Ajct4++ZCs0Q/hIWzgfzDMddblMQo1Imch94MGOZdiltPQDR7mykpo5LHLY4RG5Ivz/KYffQht4kd4aIBuMJUrK8eTfMLlMUIjw75AvkG/QM86fRceKuk//D+CM4hvnI9CjbyGGUHCAejIntvwJX1lA3IJuvEJk9VA32A+QiMjvkDuQD/VcpMdhq7vNxl66SY9YrIZaIOWRfqX1rlcyEA3lovQU0836HmTXaUr0IZSjEJP9gB9ROdpdWqFHtwF6DgDd6Hzl0/xJ/RukDvjqVkjdNNleo+O0a/QKyIv0p1c1/KaD7raXiD/wFloU1WuVqTI/mAH/u9w+hBDtQcAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACIAAAAXCAYAAABu8J3cAAAB70lEQVR4Xu2VTUhVURDHx7QQEYmw0FYiBkohqJsKUYiEIFwJGbQwMKJdufADokVEi7ZtKlwpYgQtygw3gg8D3bkQISLi6SJCXVn0AQX6H+ecmjPvnvvewk1wf/CD9/5nGMdz7j2PKCOjdA7BXvgQDsH6cLkkup1JjMJL8ASsdZ85CzgCX8K3sAuOwM/wnC6K0AOfwTzchcPh8j5lJGvaX/CGLmJuwU1YpTLemY+wQmVJ9MEr8BrFB2F+wHdwAT6CbeGysAJnTHaRpHGnyWPw7qUNwjuWylGSBhMmb3f5PZPHKDbIJxtYTpE04HPWnHb5E5PHKDbIOrwD5+EqvBms0r8G9g+2uPyFyWMUG+QnHHSfj8FF+IbUM3iWpMFTHzj8INMmj+EH4TcuiWbzfYCk/roPmlww7gPHGZc/NnkMP0jB3eDgV1jDrz3XT/qgGv6hwiM4T+mNLWmD8FWwBRtVdoGknu+vv+Tgsg7AVZLCVpUdJ9nBJPwgY3YBPIffKDwe3/+uyqgffocnVcZbllPfmTz8DRtMznSTNOb/3nKZ5BLz8DG9hl9IHtyAB/A9vA2n4BKsCSrkwV0jOU7PfZIbeBvuwK9wA86qmnKSe+oVyQ7MwQ+wQ9UE1JFc17zNh83aQcA/dnwkfFtXmrWMjP+DPUiwa5aLmwEwAAAAAElFTkSuQmCC>