# **Phase 13 Research Brief: Advancing Engine A and Tight End Integrity in the Dynasty Genius Architecture**

## **Executive Recommendation**

The Dynasty Genius product architecture has successfully concluded Phase 12, culminating in the deployment of operational backtest artifacts, a stabilized Trust Surface v2, rigorously calibrated model cards, the foundational Divergence Ledger v0, and strict market-leakage guards.1 As the development lifecycle transitions into Phase 13, the core focus shifts toward resolving persistent feature engineering inaccuracies within the rookie prospect evaluation model (Engine A) and addressing the systemic analytical failure of the Tight End (TE) valuation pipeline (Engine B).1 The empirical evidence gathered during this research cycle dictates a highly rigid sequencing framework to ensure that predictive validity is not compromised by data corruption or architectural drift.

The recommended execution structure mandates that the Identity Resolution Audit (Workstream 3C) serves as an absolute, non-negotiable hard gate before any feature engineering or data ingestion can commence for the Tight End Remodel (Workstream 3B).1 The introduction of granular collegiate alignment data—specifically Pro Football Focus (PFF) collegiate participation metrics—presents a severe risk of silent corruption if player identifiers are improperly mapped across disparate databases.1 In the context of machine learning data pipelines, bad identity joins are categorically worse than missing features; a missing feature triggers a programmatic caveat, whereas an incorrect identity join silently feeds a receiving specialist's profile to an inline blocker, irreparably poisoning the training matrix.1

Conversely, the transition of NFL Draft Capital into a step-function feature (Workstream 3A) relies entirely on pre-existing, verified draft metadata and may proceed asynchronously as an independent analytical pursuit.1 Therefore, the executive recommendation is to split Phase 13 into two sequential subphases to isolate risk and maintain the integrity of the Medallion data platform.

Subphase 13.1 will execute Workstream 3A (Engine A Draft Capital Step Function) in parallel with Workstream 3C (Identity Resolution Audit). This allows the data engineering teams to harden the identity bridge while the machine learning analysts refine the Ridge regression feature matrix for rookie evaluations. Subphase 13.2 will commence exclusively contingent upon the Identity Resolution Audit confirming a mapping loss-rate of less than 2% for the relevant historical cohort.1 Only when this threshold is satisfied will Workstream 3B (TE Remodel) be authorized to ingest PFF collegiate alignment data and engineer the required role-segmentation features. This sequencing strictly adheres to the Dynasty Genius Prime Directive ("Be right, not fast") and the Anti-Speed Protocol, ensuring that foundational data integrity precedes advanced model tuning.2

## **3A Findings: Draft-Capital Step Function**

### **Evidence Summary**

Within the current Engine A architecture, the rookie-prospect scoring model utilizes a Ridge regression framework that treats NFL Draft Capital—specifically pick and round—as continuous linear features.1 This mathematical assumption implies a monotonic, evenly distributed decay in player value from pick 1 to pick 250\. However, historical NFL roster management, financial contract structures, and empirical fantasy hit rates demonstrate that this linear assumption is fundamentally flawed. The relationship between NFL Draft Capital and long-term dynasty fantasy football production is highly nonlinear, operating as a step-function characterized by severe value cliffs.3

Draft capital is not merely a proxy for raw athletic talent; it is the ultimate proxy for organizational commitment.2 NFL front offices invest resources, dictate starter repetitions, and exercise roster patience in direct proportion to the capital expended.2 A player selected sixth overall is contractually insulated from early-career inefficiency, whereas a player selected fifty-sixth overall faces a significantly shorter evaluation leash.2 Traditional expected value curves, such as the Massey-Thaler curve, illustrate that the variance in performance outcomes decays convexly across the draft, meaning that "eliteness" or right-tail probability decays much more steeply than expected mean value.3 General managers value performance nonlinearly because elite players exert an outsized influence on championship outcomes.3

The historical hit rates for fantasy football relevance perfectly mirror this nonlinear decay. When defining a "hit" as a multi-season impact player (Top-15 Running Back, Top-24 Wide Receiver, or Top-12 Quarterback/Tight End), the data reveals stark, position-specific breakpoints.6

| NFL Draft Capital Range | QB Hit Rate (Top 12\) | RB Hit Rate (Top 12\) | WR Hit Rate (Top 24\) | TE Hit Rate (Top 12\) |
| :---- | :---- | :---- | :---- | :---- |
| Picks 1–15 (Early Round 1\) | 59.5% | 66.7% | 49.0% | 90.9% |
| Picks 16–32 (Late Round 1\) | 59.5% | 66.7% | 49.0% | 90.9% |
| Picks 33–64 (Round 2\) | 14.3% | 33.3% | 32.1% | 35.0% |
| Picks 65–100 (Round 3\) | 0.0% | 25.0% | 18.0% | 22.2% |
| Picks 101+ (Day 3 & UDFA) | \< 7.0% | \< 6.5% | \< 2.5% | \< 10.0% |

Data synthesized from comprehensive historical draft analysis (2000–2023).7

This empirical evidence highlights that draft capital breakpoints are not position-invariant. Running Backs dominate the top half of the first round, establishing elite production profiles immediately, with a 70% hit rate for players selected in the top six picks.6 Conversely, Wide Receivers drafted in the top six present a coin-flip hit rate (53%), though their viability extends deeper into the draft, maintaining statistically relevant hit rates through pick 75\.6 Quarterbacks exhibit the most severe cliff; late-first-round and second-round Quarterbacks hit at a fraction of the rate of their early-first-round peers, effectively dropping to a 14.3% hit rate outside the top 32 picks.8

These findings directly support the Dynasty Genius "Draft Capital over Landing Spot" framework. In Picks 1–32, draft capital dominates the projection. In Picks 33–64, capital and situation share equal weighting. By Picks 65 and beyond, situation and collegiate production profiles override the rapidly decaying signal of draft capital.2

### **Recommended Modeling Approach**

To accurately map this nonlinear reality within the sklearn.linear\_model.Ridge training loop required by Engine A, the model must transition to a bucketed, step-function representation.1 The recommended approach is an Ordinal Categorical Encoding utilizing position-weighted bins.

By transforming the continuous integer of overall pick number into discrete, ordinal categories (e.g., Tier 1, Tier 2, Tier 3, Tier 4), the Ridge regression can assign distinct coefficients to each tier without being forced to fit a single linear slope across the entire draft spectrum.1 Because the penalty applied by Ridge regularization shrinks coefficients toward zero to prevent overfitting, grouping players into meaningful tiers allows the model to stabilize the weights assigned to the murky middle rounds (Picks 65–100).

Furthermore, the boundaries of these ordinal bins must be position-specific rather than global.1

* **Quarterbacks:** The Tier 1 bin must be restricted to the top 15 overall picks, as historical data indicates a catastrophic drop-off in franchise viability beyond the early first round.10
* **Running Backs:** The Tier 1 bin encompasses Round 1, Tier 2 encompasses Round 2, and Tier 3 encompasses Round 3\. The cliff after Round 3 is absolute, dropping to a 6.3% hit rate.7
* **Wide Receivers:** The Tier 2 bin should logically extend through pick 75 (mid-third round), as wide receivers possess a flatter decay curve and rely more heavily on collegiate efficiency metrics like Yards Per Route Run (YPRR) to overcome lower capital.9

To maximize predictive accuracy, the model must incorporate interaction terms between these new draft capital tiers and validated collegiate efficiency metrics (e.g., College Dominator Rating and YPRR).1 In Tier 1, the interaction term ensures that draft capital overrides minor efficiency concerns. In Tier 3, the interaction term allows elite collegiate efficiency (such as a WR with a 3.0+ YPRR) to overpower the weak signal of third-round draft capital, correctly identifying arbitrage opportunities.1

### **Rejected Alternatives**

Several alternative modeling approaches for nonlinear features were evaluated and explicitly rejected for the Engine A architecture:

1. **Smooth Log-Decay Transform (![][image1]):** While a logarithmic transformation captures the general convex decay of draft value better than a purely linear fit, it inherently smooths over the acute "cliffs" at the boundaries of NFL draft days.1 NFL general managers operate using categorical trade charts that create artificial cliffs at the end of Round 1 (due to the fifth-year option) and the end of Round 2\.3 A smooth continuous feature fails to capture the psychological and contractual step-functions that dictate actual player deployment.
2. **Spline / Piecewise Transform:** Basis splines allow for flexible, nonlinear modeling but present an unacceptable risk of overfitting the relatively small dataset of historical NFL draft classes (roughly 120–180 relevant players per position per decade).1 Splines are highly sensitive to knot placement and can generate erratic predictions at the tails of the distribution, making them unsuitable for stable dynasty asset management.
3. **Hierarchical Priors:** Utilizing Bayesian hierarchical models to share information across draft classes and positions is theoretically sound but introduces excessive architectural complexity.4 The current mandate requires compatibility with the existing sklearn pipeline.1 Hierarchical priors are explicitly deferred to future phases.

### **Validation Gates**

The promotion of the Engine A Draft-Capital Step Function requires passage through a rigorous, custom validation gate. Because dynasty value relies on multi-year outcomes rather than isolated single-season production, standard cross-validation techniques are insufficient.

The required validation protocol must utilize Leave-One-Class-Out Cross-Validation (LOOCV).1 This methodology trains the model on all historical draft classes except one, using the holdout class to test the model's ability to predict 3-to-7-year dynasty value.1 The primary evaluation metric for this gate must be the rank correlation (Kendall ![][image2]) of players strictly *within* their specific draft class, rather than a global correlation metric.1 A global metric fails to account for the variance in overall class strength, whereas intra-class rank correlation precisely measures the model's ability to identify the best assets available in a given rookie draft. The new step-function model must demonstrate a statistically significant lift in Kendall ![][image2] over the linear baseline across all four validation folds before promotion is authorized.

### **Risks and Counterarguments**

The primary risk of utilizing categorical draft tiers is the potential to overfit the boundaries to historical anomalies, such as Puka Nacua's historic rookie season from the fifth round.2 A rigid binning strategy might inadvertently suppress the evaluation of a Day 3 prospect with an elite athletic or production profile.

The steel-manned counterargument posits that defining strict cutoffs (e.g., isolating WRs after pick 75\) forces arbitrary distinctions between players drafted sequentially. For instance, a player drafted at pick 74 receives a mathematically advantageous weight compared to a player drafted at pick 76, despite nearly identical organizational investment.

To mitigate this risk, the 65:35 Quantitative-to-Qualitative discipline serves as a vital safeguard.2 The quantitative model establishes the baseline probability, heavily penalizing Day 3 assets. However, the architecture permits exception archetypes to be surfaced via risk/context flags. If a Day 3 player possesses a Relative Athletic Score (RAS) above 9.5 and elite YPRR, the system will programmatically flag the player as a high-ceiling anomaly, ensuring that the rigid draft capital step-function does not entirely blind the user to unprecedented outlier profiles.2

## **3B Findings: TE Remodel**

### **Why Current TE Models Fail**

The existing Engine A predictive model for Tight Ends is currently suspended in an EXPERIMENTAL state, constrained by an unacceptable Kendall ![][image2] rank correlation of 0.477.1 An artifact-driven review indicates that the model's failure is rooted in severe "label noise" caused by the homogenization of distinct player archetypes.1

In modern NFL offenses, the "Tight End" designation encompasses two fundamentally different functional roles: the pass-catching specialist (the "Move" or "Big Slot" TE) and the auxiliary offensive tackle (the "Inline Blocker").13 Both archetypes routinely secure high NFL Draft Capital; a team will spend a second-round pick on a dominant inline blocker to solidify a wide-zone rushing scheme, just as readily as they will spend a second-round pick on a vertical seam-stretcher.15 Because the current Engine A architecture relies heavily on raw draft capital and gross college dominator ratings, it lacks the contextual awareness to differentiate between these two profiles.15

Consequently, the model systematically overvalues inline blockers simply because they possess high draft capital, projecting fantasy relevance where none exists. In dynasty fantasy football, pass-block rate is negatively correlated to fantasy points (approximately \-0.38).13 A Tight End who primarily blocks will rarely achieve the necessary target volume to breach the Top-12 positional threshold, regardless of their athletic testing or draft pedigree. Until the model can programmatically segregate these archetypes, the predictive validity of the TE pipeline will remain fundamentally broken.

### **Recommended TE Archetypes and Evidence for Segmentation**

To eliminate label noise, Engine A must segment collegiate TE prospects by their alignment and usage profiles prior to applying regression weights.1 The segmentation relies on tracking the percentage of snaps played in specific formations.

1. **The Pass-Catching Profile ("Move" / Big Slot TE):** This archetype is characterized by high alignment versatility, frequently operating detached from the offensive line to exploit linebacker and safety mismatches in space.13 The defining metric for this profile is the combined collegiate Slot Route Rate and Wide Route Rate. Thresholds established by predictive modeling indicate that prospects who run ![][image3] of their routes from unattached alignments demonstrate a significantly higher probability of transitioning into elite dynasty assets.1 Elite historical producers in this archetype exhibit superior Yards Per Route Run (YPRR) and Targets Per Route Run (TPRR).2
2. **The Blocking-First Profile (Inline TE):** This archetype is characterized by attachment to the offensive tackle, primarily functioning to secure the edge in the run game or stay in for pass protection.14 The defining metric is the Inline Blocking Rate. Prospects who record an inline blocking rate of ![][image4] in their final collegiate season are overwhelmingly relegated to TE2 or TE3 roles in the NFL.1 These players face a structurally limited production ceiling; they are drafted for real-life schematic utility, not fantasy point generation.

### **Recommended Data Sources and Predictive Metrics**

The Dynasty Genius Product Constitution mandates that 65% of the evaluation weight must be grounded in verifiable, falsifiable metrics.2 Therefore, subjective grading systems, including proprietary PFF *grades* (e.g., pff\_grade, pff\_pass\_block\_grade), are strictly prohibited from entering the feature matrix.1 Utilizing subjective grades introduces qualitative bias into the quantitative engine, creating a leakage defect.

Instead, the model must rely exclusively on objective participation and rate metrics.1 The most predictive collegiate TE metrics for NFL fantasy relevance include:

* **Yards Per Route Run (YPRR):** The most efficient single-number metric for receiving talent, capturing both the ability to earn targets and the efficiency of the production. A collegiate YPRR above 1.8 at a Power 5 program indicates a high-hit-rate prospect.2
* **Slot and Wide Route Percentages:** As detailed above, these metrics isolate the "Move" TE archetype from the traditional inline blocker.
* **Route Participation in 1-TE Sets (11 Personnel):** A prospect's ability to stay on the field in single-TE formations demonstrates that the coaching staff trusts their receiving utility over a third wide receiver.17

### **PFF Step 0 Feasibility and Public Fallback Options**

Acquiring granular collegiate alignment data requires accessing high-fidelity tracking sources.

**PFF Step 0 Feasibility:** PFF Collegiate data provides the necessary participation fields, specifically routes\_run, slot\_snaps, inline\_snaps, and wide\_snaps.1 However, automated API scraping of PFF data presents severe fragility risks. Consequently, the architecture dictates that PFF must be classified as a context\_signal source, restricted to a manual CSV export workflow (csv\_fixture cache policy) for the current phase.1 Generating this data requires manually exporting alignment metrics for the 2018–2025 draft classes (approximately 30 to 50 relevant drafted TEs per class).1 This is highly feasible but demands strict adherence to the identity resolution protocols defined in Workstream 3C to ensure the manually exported records map perfectly to the canonical Sleeper IDs.1

**Public Fallback Options:** Should PFF participation data prove inaccessible or violate the manual caching policy, nflverse and nflreadpy personnel data serve as functional, lower-cost proxies.1 By measuring a collegiate program's deployment of 11 personnel (1 RB, 1 TE, 3 WR) versus 12 personnel (1 RB, 2 TE, 2 WR), analysts can infer a prospect's role.17 TEs who maintain high route participation in 11 personnel are highly correlated with future fantasy success, as this indicates they are the primary receiving option at the position, whereas reliance on 12 personnel often masks a blocking-heavy deployment.17

### **Validation Gates and Lock Removal**

Given the limited historical depth of the drafted TE population (roughly 300 athletes between 2018–2025), splitting the data into two entirely independent sub-models (one for receivers, one for blockers) risks severe overfitting, reducing the training population below acceptable thresholds for Ridge regularization.1

The remodel should instead inject slot\_wide\_route\_pct as a continuous feature into the primary Engine A matrix.1 Simultaneously, the blocking\_first flag (triggered by a ![][image4] inline blocking rate) must be utilized as a sample weight to mathematically penalize the projected ceiling of heavy inline blockers.1

Before the EXPERIMENTAL lock can be removed from the TE position, the remodeled engine must achieve specific numeric conditions. The model must cross a minimum Kendall ![][image2] threshold (e.g., ![][image5]) and successfully pass the rank-correlation gate across all four holdout folds.1 Furthermore, the model must demonstrate that it successfully suppressed the projected dynasty value of highly-drafted inline blockers without suppressing the value of highly-drafted receiving specialists.

### **Risks and Counterarguments**

The primary risk of segmenting TEs by collegiate role is that college offensive schemes do not always reflect NFL deployment. An athlete may have operated primarily as an inline blocker in college due to a run-heavy offensive scheme (e.g., Iowa or Wisconsin), yet possess the elite athletic profile (RAS \> 9.0) necessary to transition into a receiving weapon in the NFL (e.g., George Kittle).20

If the model heavily penalizes all prospects with a ![][image4] inline blocking rate, it risks systematically fading elite athletes trapped in archaic collegiate offenses. To mitigate this risk, the 35% Qualitative allocation must be invoked.2 If an inline-heavy collegiate TE records an elite RAS and exceptional YPRR on a limited target volume, the system must generate a caveat flag highlighting the athletic mismatch, ensuring that the user is aware of the prospect's untapped ceiling despite the restrictive quantitative blocking penalty.2

Crucially, the remodel applies exclusively to Engine A (rookie evaluations). Under no circumstances may the veteran Engine B artifacts be modified or promoted as a side effect of this rookie TE remodel.1 Veteran TEs are evaluated purely on post-entry NFL usage metrics, neutralizing the label noise of their collegiate profiles.

## **3C Findings: Identity Audit**

### **The Canonical Identifier Mandate**

The introduction of highly granular collegiate alignment data (Workstream 3B) requires seamlessly joining information from disparate databases: PFF, College Football Data (CFBD), Sleeper, and the nflverse. Identity resolution is the most critical vulnerability in this pipeline. The Dynasty Genius architecture mandates a single canonical player\_id to prevent disjointed datasets from corrupting player valuations.1

The current Prospect Identity Resolver maps rookie requests to a canonical Sleeper ID via a three-stage pipeline: an explicit sleeper\_id in the request, an alias bridge (prospect\_alias\_bridge.json), and a manual review log.1 The architecture strictly prohibits the use of fuzzy matching algorithms (e.g., Levenshtein distance on player names) in production logic.1 In the context of Tight Ends, name collisions (e.g., multiple players sharing common names across overlapping draft classes, or juniors sharing names with seniors) and post-draft position changes make fuzzy matching catastrophic.1 The system must rely entirely on deterministic mapping strategies to ensure 100% loss-less joins.

### **Required ID Map Design and Available Mapping Fields**

To establish a loss-less deterministic join without fuzzy matching, the identity layer must leverage the ff\_playerids crosswalk table maintained within the nflverse ecosystem.1 This table provides a centralized, community-maintained relational mapping across all major fantasy and statistical platforms.22

| Platform / Source | Identifier Field | Format Structure |
| :---- | :---- | :---- |
| Sleeper API | sleeper\_id | Numeric (\~4 digits) 22 |
| NFL / nflverse | gsis\_id | 00-00XXXXX 22 |
| Pro Football Focus | pff\_id | Numeric (3 to 6 digits) 22 |
| College Football Ref | cfbref\_id | firstname-lastname-integer 22 |
| Pro Football Reference | pfr\_id | First 4 chars last name, 2 chars first name, integer 22 |

By utilizing the ff\_playerids dataset, the system can deterministically map a collegiate pff\_id directly to a sleeper\_id using the gsis\_id as the primary structural anchor.1 No individual source adapter is permitted to invent its own identity logic; all mapping must occur within the Silver layer transformations of the Medallion architecture before reaching the feature store.1

### **Failure Mode Taxonomy**

The Identity Resolution Audit must test the pipeline against all TE prospects drafted between 2018 and 2025\.1 The taxonomy of identity failure modes is ranked by severity:

1. **Silent Corruption (Catastrophic):** The resolver returns an incorrect sleeper\_id due to a name collision. The system erroneously joins data, appending a pass-catching specialist's collegiate metrics to an inline blocker with the same name. This poisons the Gold layer feature matrix without throwing a recognizable error code.1
2. **Stage 1 Miss (Critical):** The explicit sleeper\_id is missing or invalid in the base API response.
3. **Stage 2 Miss (Moderate):** The player is not found in the prospect\_alias\_bridge.json, requiring a fallback mechanism or crosswalk resolution.
4. **Stage 3 Miss (Triage):** The player drops into the manual review log and is excluded from the automated pipeline.

A specific failure mode uniquely affecting the 2018–2025 cohort involves "Prospect-to-Veteran" transitions.1 Active veterans (e.g., Sam LaPorta, Brock Bowers) exist in current databases with active sleeper\_ids, but these IDs may fail to resolve backward to their historical prospect aliases. The system must verify that querying a 2018 prospect returns the exact canonical ID used in the Engine B veteran scoring tables without duplicating the player record.1

### **Coverage Thresholds and Fuzzy/Review Policy**

The hard gate for Phase 13 dictates that the identity audit must confirm a mapping loss-rate of strictly less than 2% for the relevant historical cohort (2018–2025 drafted TEs) before any PFF data can feed the model training tables.1 To avoid survivorship bias, the denominator must include all drafted Tight Ends. However, an architectural exception may be documented to exclude pure inline blockers (defined as athletes with fewer than 10 career collegiate receptions) from the denominator, provided their absence does not skew the receiving-specialist training data.1

If a record cannot be deterministically resolved via the ff\_playerids crosswalk or the prospect\_alias\_bridge.json, it must be rejected and sent to a manual review queue.1 Fuzzy string matching is explicitly forbidden at all stages of the automated pipeline. The review queue allows human oversight to manually update the alias bridge, ensuring that the system prioritizes truth and reproducibility over speed and convenience.2

### **Audit Artifacts and Contract Tests**

The execution of the Identity Resolution Audit must produce the following artifacts to satisfy the governance constraints:

1. **Divergence Ledger:** A structured log detailing all name collisions, failed joins, and records sent to the manual review queue.1
2. **Null-Value Log (The "Missing Cohort"):** A script output identifying all active players averaging more than 5.0 PPG who are currently excluded from market overlays due to ID mapping gaps.1
3. **Contract Tests:** CI/CD gating tests verifying row-count preservation across pipeline re-runs, guaranteeing that no records are dropped or duplicated during the pff\_id to sleeper\_id enrichment phase.1

## **Recommended Phase 13 Scope**

To maintain structural integrity and prevent architectural drift, Phase 13 must strictly bound its analytical scope. The discipline of the 65:35 Quantitative-to-Qualitative ratio dictates that all new features must be mathematically verifiable and free from market sentiment bias.2

### **In Scope**

* **Workstream 3A (Engine A Draft Capital):** Execution of the Leave-One-Class-Out Cross-Validation (LOOCV) backtest for the step-function across QBs, RBs, WRs, and TEs. Integration of ordinal categorical bins and position-specific thresholds into the Engine A Ridge regression matrix.
* **Workstream 3C (Identity Audit):** Deployment of the Identity Audit Script. Validation of the 2018–2025 TE cohort mapping between Sleeper, nflverse, and CFBD using the ff\_playerids deterministic crosswalk. Generation of the Null-Value Log and Divergence Ledger.
* **Workstream 3B (TE Remodel):** Contingent on 3C passing the 98% resolution threshold, the manual ingestion of PFF collegiate CSV fixtures for alignment metrics. Generation of the blocking\_first sample weight flag and integration of the slot\_wide\_route\_pct feature into Engine A.

### **Out of Scope**

* **Engine B Retraining:** Any modification to the active NFL player valuation models (Engine B) based on collegiate alignment data is strictly prohibited. Engine B relies exclusively on post-entry NFL usage metrics.1
* **Fuzzy Identity Matching:** The introduction of Levenshtein, Jaro-Winkler, or any other probabilistic string-matching algorithms into the identity resolution layer is strictly forbidden.1
* **Subjective PFF Grades:** The ingestion or modeling of any proprietary PFF *grades* (e.g., pff\_grade, pff\_pass\_block\_grade) is prohibited.1 Only objective participation metrics (routes, snaps, alignment percentages) are permitted.
* **Market Data Feature Injection:** KTC, FantasyCalc, or ADP values must remain strictly separated from the training matrices of Engine A and Engine B. Market data serves only as a post-scoring overlay.1

### **Explicitly Deferred**

* **Dynasty Value Score (DVS) Promotion:** The global dynasty\_value\_score attribute must remain locked (None) for all Player Value Objects (PVO) until Engine A successfully clears the redesigned validation gates and is formally merged into the Gold tier of the Medallion architecture.1
* **Hierarchical Priors for Draft Capital:** Exploring Bayesian hierarchical models for draft capital evaluation introduces excessive architectural complexity and is deferred to future optimization phases.4

## **Implementation Implications**

The execution of the Phase 13 subphases requires specific modifications across the Databricks Medallion architecture and the application repository. No code is required at this stage, but the following architectural surfaces will be impacted:

### **Source Adapters and Identity Bridge Files**

The cfbd\_adapter.py must be updated to securely handle the integration of the ff\_playerids crosswalk table from the nflverse.1 The central alias bridge (app/data/prospect\_alias\_bridge.json) will require structural expansion to append pff\_id mapping arrays alongside the existing sleeper\_id keys.1 No individual adapter may write its own resolution logic; all identity mapping must be processed through the central Silver layer transformations before reaching the feature store.1

### **Feature Store Tables (Silver to Gold Layer)**

The Engine A feature matrix (residing in the Silver layer) must undergo a schema migration. The continuous pick integer column must be deprecated in favor of the new ordinal categorical bins (draft\_tier\_1, draft\_tier\_2, etc.).1 Furthermore, new columns for slot\_wide\_route\_pct and the boolean blocking\_first sample weight must be added to the TE-specific feature views.1 These transformations must be executed ensuring that provenance fields (source timestamps, parser versions) remain intact.1

### **Model Training Gates and Contract Tests**

The engine\_a\_contract.py file must be rewritten to establish the new LOOCV testing harness.1 The evaluation metrics logged to MLflow must shift from tracking global Kendall Tau-b to tracking draft-class-specific rank correlations, ensuring the model accurately predicts intra-class value.1

New contract tests must be instituted to enforce row-count preservation across pipeline re-runs.1 A CI/CD transition test must be written to assert that an identity request for a 2018 TE prospect correctly retrieves the exact canonical Sleeper ID used in the Engine B veteran tables, proving that prospect records smoothly merge with veteran records without generating duplicate PVOs.1

### **Documentation Artifacts**

The completion of Phase 13 requires the generation of a formal formula specification document detailing the team and ID mapping logic, alongside the publication of the Divergence Ledger capturing all unresolved identity collisions sent to the manual review queue.1

## **Open Questions For David**

The following architectural and strategic decisions present conflicts between the quantitative rigor of the models and the subjective evaluation of dynasty asset management. These require explicit judgment from the Product Owner before final execution:

1. **Treatment of Pure Inline Blockers in the Identity Denominator:** When calculating the 2% mapping loss threshold for the 3C Identity Audit, should "pure inline blockers" (defined as drafted athletes who recorded fewer than 10 career collegiate receptions) be excluded from the denominator? Including them risks failing the hard gate due to athletes who possess zero fantasy relevance, but excluding them risks masking underlying flaws in the PFF-to-Sleeper mapping bridge.
2. **Label Noise Caveat vs. Training Exclusion:** For the TE Remodel (3B), when a prospect breaches the ![][image4] Inline Blocking Rate, should the algorithm exclude the athlete entirely from the Engine A training population to purify the dataset, or should the athlete remain in the dataset with a heavy mathematical sample-weight penalty and a low\_production\_ceiling UI caveat? Exclusion purifies the regression weights for pass-catchers but removes the model's ability to natively score blocking-heavy archetypes if they unexpectedly transition into receiving roles.
3. **Position-Specific Draft Capital Thresholds:** For the Draft-Capital Step Function (3A), historical data indicates WRs maintain fantasy viability deep into Round 3 (Pick 75), whereas RBs experience a severe cliff immediately after Round 2 (Pick 64). Should the model enforce unified categorical bins across all skill positions to maintain mathematical simplicity within the Ridge regression, or should it hardcode asymmetric, position-specific integer thresholds for the categorical splits, risking overfitting to the past decade of data?

## **Source Bibliography**

* 2 The Dynasty Genius Framework: A Comprehensive Knowledge Architecture for Machine Learning Product Development in Sports Analytics. (Uploaded Document). Supports the 65:35 Quantitative-to-Qualitative framework, Age cliffs, YPRR benchmarks, and Draft Capital primary anchor rules.
* 1 phase\_13\_research\_prompts.md. (Uploaded Document). Supports the specific research prompts for Workstreams 3A, 3B, and 3C, including the constraints against fuzzy matching and subjective PFF grades.
* 1 01-north-star-architecture.md. (Uploaded Document). Supports the Medallion architecture rules, identity resolution triage requirements, and strict separation of market data from Engine A/B training features.
* 1 Phase-13-Research-Brief.md. (Uploaded Document). Supports the current state of Phase 13 execution, identifying 3C as a hard gate for 3B, and outlining the Divergence Ledger artifacts.
* 1 00-product-constitution.md. (Uploaded Document). Supports the Prime Directive ("Be right, not fast"), the mandate for continuous aging curves over hard cliffs, and the requirement for explicit uncertainty framing.
* 3 Expected value curves and Massey-Thaler exponential decay analysis. Supports the assertion that draft capital decays convexly, justifying the transition to a nonlinear step-function feature in Engine A.
* 22 nflverse ff\_playerids mapping documentation. Supports the deterministic mapping strategy bridging sleeper\_id, gsis\_id, and pff\_id to resolve identity without fuzzy matching.
* 7 Historical NFL draft capital fantasy hit rates by pick position. Supports the specific positional breakpoints for categorical bins (e.g., RB hit rate drop-off after Round 2; QB drop-off after early Round 1).
* 13 Tight End role segmentation analytics. Supports the differentiation between Inline Blockers and Big Slot/Move TEs, utilizing Route Rate and Inline Blocking Rate to resolve Engine A label noise.

#### **Works cited**

1. Phase-13-Research-Brief.md
2. The Dynasty Genius Framework: A Comprehensive Knowledge Architecture for Machine Learning Product Development in Sports Analytics
3. Exploring the discrepancy between NFL draft expected value curves and the observed trade market, accessed May 15, 2026, [https://www.stat.cmu.edu/cmsac/conference/2024/assets/pdf/Brill24.pdf](https://www.stat.cmu.edu/cmsac/conference/2024/assets/pdf/Brill24.pdf)
4. The Winner of the NFL Draft is Not Necessarily Cursed \- arXiv, accessed May 15, 2026, [https://arxiv.org/html/2411.10400v1](https://arxiv.org/html/2411.10400v1)
5. NFL Draft Modelling: Loss Functional Analysis \- arXiv, accessed May 15, 2026, [https://arxiv.org/html/2504.07291v1](https://arxiv.org/html/2504.07291v1)
6. Dynasty Managers: The TRUE Value of Your Rookie Picks (10+ Years of Hit-Rate Data) : r/DynastyFF \- Reddit, accessed May 15, 2026, [https://www.reddit.com/r/DynastyFF/comments/1ot2ard/dynasty\_managers\_the\_true\_value\_of\_your\_rookie/](https://www.reddit.com/r/DynastyFF/comments/1ot2ard/dynasty_managers_the_true_value_of_your_rookie/)
7. NFL Draft Capital Hit Rate: Which Rounds to Target for : r/DynastyFF \- Reddit, accessed May 15, 2026, [https://www.reddit.com/r/DynastyFF/comments/1sifcej/nfl\_draft\_capital\_hit\_rate\_which\_rounds\_to\_target/](https://www.reddit.com/r/DynastyFF/comments/1sifcej/nfl_draft_capital_hit_rate_which_rounds_to_target/)
8. How NFL Draft Capital Predicts Success | Fantasy Football \- Dynasty Nerds, accessed May 15, 2026, [https://www.dynastynerds.com/analytics/nfl-draft-capital-fantasy-football/](https://www.dynastynerds.com/analytics/nfl-draft-capital-fantasy-football/)
9. Wide Receiver Draft Capital: Does It Matter? A Comprehensive Analysis \- BrainyBallers, accessed May 15, 2026, [https://brainyballers.com/wide-receiver-draft-capital-does-it-matter-a-comprehensive-analysis/](https://brainyballers.com/wide-receiver-draft-capital-does-it-matter-a-comprehensive-analysis/)
10. Rookie Draft Hit Rates by Position and NFL Draft Capital : r/DynastyFF \- Reddit, accessed May 15, 2026, [https://www.reddit.com/r/DynastyFF/comments/1lvqbfs/rookie\_draft\_hit\_rates\_by\_position\_and\_nfl\_draft/](https://www.reddit.com/r/DynastyFF/comments/1lvqbfs/rookie_draft_hit_rates_by_position_and_nfl_draft/)
11. Optimizing NFL Draft Selections with Machine Learning Classification \- MDPI, accessed May 15, 2026, [https://www.mdpi.com/2673-2688/6/9/221](https://www.mdpi.com/2673-2688/6/9/221)
12. NFL Draft Capital Is King For Predicting Fantasy Football Success: Is Puka Nacua An Outlier?, accessed May 15, 2026, [https://www.fantasylife.com/articles/dynasty/nfl-draft-capital-is-king-for-predicting-fantasy-football-success-is-puka-nacua-an-outlier](https://www.fantasylife.com/articles/dynasty/nfl-draft-capital-is-king-for-predicting-fantasy-football-success-is-puka-nacua-an-outlier)
13. How TE Usage in 11- and 12-Personnel Impacts Fantasy Football \- Underdog Sports, accessed May 15, 2026, [https://underblog.underdogfantasy.com/how-te-usage-in-11-and-12-personnel-impacts-fantasy-football-d471ebb60076](https://underblog.underdogfantasy.com/how-te-usage-in-11-and-12-personnel-impacts-fantasy-football-d471ebb60076)
14. A Deeper Look At The Tight End Position Through Clustering | by Ajay Patel | Medium, accessed May 15, 2026, [https://ajaypatell8.medium.com/a-deeper-look-at-the-tight-end-position-through-clustering-fa547a2167bd](https://ajaypatell8.medium.com/a-deeper-look-at-the-tight-end-position-through-clustering-fa547a2167bd)
15. 2025 NFL Draft: Top 5 remaining players at every position after Round 1 \- PFF, accessed May 15, 2026, [https://www.pff.com/news/draft-2025-nfl-draft-top-5-remaining-players-at-every-position](https://www.pff.com/news/draft-2025-nfl-draft-top-5-remaining-players-at-every-position)
16. Predicting the Draft and Career Success of Tight Ends in the National Football League, accessed May 15, 2026, [https://www.researchgate.net/publication/273193128\_Predicting\_the\_Draft\_and\_Career\_Success\_of\_Tight\_Ends\_in\_the\_National\_Football\_League](https://www.researchgate.net/publication/273193128_Predicting_the_Draft_and_Career_Success_of_Tight_Ends_in_the_National_Football_League)
17. This TE Data Predicts Fantasy Football Busts \- Underdog Network, accessed May 15, 2026, [https://underdognetwork.com/football/analysis/this-te-data-predicts-fantasy-football-busts](https://underdognetwork.com/football/analysis/this-te-data-predicts-fantasy-football-busts)
18. Does Yards Per Route Run (YPRR) matter when evaluating receiver prospects? \- Reddit, accessed May 15, 2026, [https://www.reddit.com/r/DynastyFF/comments/1q7futb/does\_yards\_per\_route\_run\_yprr\_matter\_when/](https://www.reddit.com/r/DynastyFF/comments/1q7futb/does_yards_per_route_run_yprr_matter_when/)
19. Tight ends always a possibility for Pats \- New England Patriots, accessed May 15, 2026, [https://www.patriots.com/news/tight-ends-always-a-possibility-for-pats-111846](https://www.patriots.com/news/tight-ends-always-a-possibility-for-pats-111846)
20. 2026 NFL Draft: Scouting tight ends using PFF+, accessed May 15, 2026, [https://www.pff.com/news/draft-2026-nfl-draft-scouting-tight-ends-pff](https://www.pff.com/news/draft-2026-nfl-draft-scouting-tight-ends-pff)
21. Step by Step Identity Resolution With Python And Zingg \- Towards Data Science, accessed May 15, 2026, [https://towardsdatascience.com/step-by-step-identity-resolution-with-python-and-zingg-e0895b369c50/](https://towardsdatascience.com/step-by-step-identity-resolution-with-python-and-zingg-e0895b369c50/)
22. Data Dictionary \- FF Player IDs \- nflreadr, accessed May 15, 2026, [https://nflreadr.nflverse.com/articles/dictionary\_ff\_playerids.html](https://nflreadr.nflverse.com/articles/dictionary_ff_playerids.html)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGIAAAAYCAYAAAABHCipAAAFk0lEQVR4Xu2YdYxkRRCHf7hrOFwWODxYCBB0sUAgwd1ywUICJBAguLu7h3DHoQGCuy4S3IIk+OFOcNf6Uq+Znpo3b2Zvd3b3j/mSX3Zfdc/Me13VVdVP6tKly+AzYzQMI3NHwwhgStOoaBxspjPdF40ZU5lmicYOcYTpoGgcIqY2zRyNBdOYnjItEQeq6DGNicYKdjbtF43GyqYfTf+aHgljnWBz05vy6JtYljNtGo0t2MT0nfw57wpjORub3jPNHgdy8NQpphdM/6j6CyP3muaMxoIZTB+p846YS+50HnYgfGp6IxrbYLTcEYfGgcA9pmuiMWcl066mFUy/q31HzGO6OxoDz6nzjjhWHhADhd3AovaXHeWOWC0OBBYz/WZaKg6U0R9HHGzaKRoDz6izjiAVfW7aKg4MIZebflZ7afFh07nRWEZ/HPG0vFhXwZwyR9BpbWvaU74Ty5jW1Gta0TSpPFoPM62TzSEKiUbye2Qy+VxSF0wuz+lEZg7PsG7xtxlzmDaT/x7fk/Ou6cHsmuK8trxRiVxmei0ay2jXEcubxkdjCWWOIAVMkDuBvN5nuk71C7GBPNJJO6eaPpN3Z8eZXsnmsSNxxPSZLXGl/MGpH6Teq037yO/pkGLOQvIoHWf6UI2LTMc3zvSkad/i/7xLnE/++3RsQJq63XSn6cI0KYOujvmzxoFIu444y7R+NJYQHYED/1L9Z+kkWOiLi2sW42vT2f/PkG6Q1xvIH+IoucMi7KLTTfPKH/wB1SJ0S9OfpplMt8jvaYdiXt5iTiKvPSwquwteN/2QXadAWMO0l2kP05KF7YpiTs4W8rGWdQJHtCrA3MSLxd9WREfcpvoHSZwmv8EF5KmK/6lBCRxfFkljTY8HG9BWk66oHXxu9WyMlIiNlvfMwnarvL1k8RP8PkGTHxLZFRtm19QH5uD0VKfYnQeq/HC5jPy3e+NABEfQZlXBjZwRjU2Ijvi4UIStnRaHtvcb1bd6LNTL2XWCNICacb4aC+nxqkUxzGb6w3RMmiDfLeyavsxWxjumn0yfyIOFz1WRUtl6cSDSjiOuNS0bjU2IjiAPs8iRE+U3uHVxTaS+b7pKvsX53NLFWA51oKr4var6Qgp9pl9VezVDlHN+ol4kKLbcD81BM2jfmXO4PPqfl59DpsgnBdaUf2aROBDBEVU9OdHKcb1dnlV9VFEw/5Z/T86jpi9UK9j8BrWCXMp2jkU0gcN+UX1KSRDpLPCRmY3DJ5Gep72X5L8P58g/x25hwbZJkzJSytlePmfV4po3DFwzzkKnAp5D08DzV7a6eJIt+piaP/gYef5rB1pOOhx2Bf/DwvLUlLoW4KY56BCZiT5517GbPN9T5Ci8kd3lD182RlFmjMVN3CgPjvR8BARz9jbNb7qksPPuiCbg6OI6QX25X17jLpKnvbQDKNbUC76b9JfXpcRJ8t1dykamt+V5jkKKiM631JjzaN3KilBkFXknlL6P1wd0J8B3Xmp6SN6R0Iez0DknyxcoFw95vWpOhZ5ibK3MlrhAvlvoxnAAUX+CfJFzbpa3sNxTOnMATQMFHOew8/ge2u20+54w3VT8D6Pk8+8wnZfZc+j+WjVDLcEBrepHfyBNLKrGnEpgTJDnbBYdkc9T28kuyaFGlO1SWk2cDSxS7LhycgdEelRfPxLcfzy04aSy3Qk8BwFPQzIgDlDrVxqDAQWatrAM6heHtJztTF+p/jU0J2F2SkwtwwlnjA/U2Lr3G2pH1WuAwaLX9K3c6Wm3kE7I49+r8ZUIkUbeTwdAcj2ncRyxv/xsMtwQJF+q1hVONIvLj/dDxWh5ZzNWnnNpUynwC+aTMkgt1Bruk507vhCt9i7ZvOGChoG6N2Doq2MkjjR4PcGuGWnQnLBD8yajS5cuTfkPVEku5gOMUmYAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAYCAYAAABjswTDAAABVElEQVR4Xu2WvS/FUBTADwYShIjFRww+JpswCBL+BAkWg0UkBotJIpEgMVuIWCQMJmw2g13E5+wNNqxiEPyu077e3jxPl752uL/kl/aec5qctuc2FfF4cksttrjBvDGMb/iNV04ulzSKNrvtJvLIhGizk24ij6zjlySY2S7swV7Lbmywi1LmEm+wGaewLZ4WGcBb0cdfyqOoNFXq8AMLeIxLon1NhwUdeI+LOIoreIZjOCK6Q5vC4pQZF304e1ZsDZ/CxQz2RznZwQVr/R/12J5Q82rLYRoz89pqxTZEb8CMZIwqfMYhN1GGWdFXlsTV4Jq/uMAHJ3Yq2qx9A78M4qfo7GTBK+5a65ogVrBiRTZF5zcrXnDZWoff3DkrVuQOD91gBTnHg+Dc/B9c40mUjjAb5R3n3UQFMZvIzOw+PuIWVscqLDpFN1mWmDntC44ej8dTgh+MXkB0VGd7HAAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADgAAAAXCAYAAABefIz9AAADAElEQVR4Xu2XWaiNURTH/+Z5LjOleDAWmQnFmyFKpiQhKSKEUroyZHhDGTJdkpIpMjzwYJ4K8eJBmaJ4kBKeiP//rv1117fPd+85LvdGnV/96uy19zn3rLPXXt++QJEiNUUL2iQORmi+fhz8H1hC79MTtATZSbSiN2jfeKKmmE43xUFSm06km+ly2iE9jU70G20bxjfpY7qY9qI96TL6nG4Na3IYTS/TKbA/+LfpSD/BdsCjnThFL9JRdDV9R4e5NXPpEzeeHxwC+0HW0Jn0IW3g1uXQGrb9d2AfkFUGVeU0/YHcBBfRD7Sxi2kntRt1w/gwbNcSxtG1bizO0MFRrEJ0UFfAal6/UL6DnY/ZdAOszOIEH9HzUUwJ/KQjw1hlp3UJ2q3xbjwHlZRmZWi7F8IS1c5qh3+XdvQ6rBriBFvCEjniYmJAiK8L40n0I20Yxvto0/BapX8beUozH3XoLNgHbaft09OVooQGhddxgj1giegLe3qH+B4XO0hLYWf0gItr9wsuzXxoF07StyjsF5tKt7lxnKAaSZyIUFdU3K9V4xsDa4LJ2ZxHtyQLYPPraT8XK4hGdCmsVFfRZunpTFTOKs2krESc4FBYIntdTCQJHo/ins5Il6aSfUDH0quw6siLbg7qVvdg3c5/2XyU0hFRLE6wOyyR/S4m+oT4zijuuUAHuvFT2LNU6P0r3VwOagzaerVmnT2dwd9Fbf41fUlf0FewL/0ljNUJ1Si+I7ezDoet1fMtiwVIXxh0MdD6/i4Wf2YZXegu2BZPoLXS039EG+SeK3GN3o1iM2Brs85SV3oL6We0Hidar9JOuORel6HzcA52m6gO1Hn1Jc5GcV3fvsLafcJRWOJZ6Mbjd0roDqrPTkpW53JH+XT1ox16Tz8H38BKNGEjfQa7Tx6D3aSau/kEPZNL4mBAietRInQ5mezm/gm0w9Ngj4560ZxQg7uC8kdEjBqi7tJK9BAy1qmm1VoLsVt4T01TyD8BFa7RgVa7LsTdyPiFihQpUiV+ARFllvQAH55HAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADgAAAAXCAYAAABefIz9AAADQklEQVR4Xu2XWaiNURTH/+Z5LPOUDJlFMiUUHmQID6YHmZKQeYjoyhBJCZkyS0pEZHjgQeYhRKQMKSEUbzwp/v+79nfP/vb97j2f27231PnXr85ee5199t5r7bX3AXLKqbxUj9QKjYHUXzU0/g9aQB6Q0yQPyYtoQG6S7mFHWasumULWkC5Bn1SRjCGbyRLSLN6NFuQXaezat8hTMh82XmeyiLwhW51PIQ0hV8l42A+WlsaS92QGGUHekT5evyJxllwmg8lK8okM8Hymk2dee5ajH2xDVsE28DGp5vkVUkNY+O/CBkhKg39RT/KDtHNtbeIfsqPAA5hLvpKank2RVDQqu/ZRWNQiDYdlg69zpG9gK1I6qEthOa8dynawk6TJfYCdmUh1yDbSy7M9IRe9tqQFaCMGubbSTn6RFK1RXnsaiknN4qRwz4EtVJFVhNNK0dMkF5MKpA2pFPMA6sN8jgf23s6+zrWV5t9Jddc+QGq7z83JHWRJzWzSxKbCBlIEmsa7E6UU1yQ3kCuwNPtG5nk+HZyPJuyrq7Pv82yHyTHYGT3k2RX91KmZTTqTZ8hHZN+xvbBJvkbGN4rqRNdWIQkXIqkqyu6ntwrfUFgRjM7mTLIlcoD1ryc9PFsq1SALYam6AnaWskkboUmuDexfyCP3uT/MZ3+mO1/RAk8Fdl8tEU9NLfYhGUauw7Ijq/RyULW6D6t20RlIoz2wSSq1fb119kakvft8MOYBdHP2XYHd1yXEr5vnsLtU0veXeX2F1AQWepVmTTAsDmm0HDbJCYFd5V92nWMVit+Ip6I0EOaj+y1Js8kmr62Hgfz96hyOma9WZDcsxKNh1a+k6gT7UU3G12fyEpmxb5B7Bb2mybDvJp2l1uQ24ne0rhP5K7UjqbDFpPNwAfaaKC1po/RCidQRNpGRnm0S+Qkr95FOwBaeJI3nR0rSG1TjRimrc7kz0112Uhq+IOfJdlj0Vsc8TBvJK9h78iTsJaX3ayjdyXmh0UkL11Ui6XEyzusrUykV9QZVlVPlK0raDF0fujqqBH2SCtw1ZK6IUCqIektroUeQ4KecVmlNQ1v3nfJWmj8BRfroQKtcp0GXeKEdyimnnEqkv3NpnNQ7XJBOAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEEAAAAXCAYAAABUICKvAAAC/UlEQVR4Xu2WWchPQRjGH/sSEsqu7GvWCKGPxIX1xpZCSVGWyHKFCyG5kaxZyhoR2bIkXFgulBtZirIXuSOJFM/zvef0zcz//P//8X1xdZ761Zln3vOec+bMvDNArly5cv0/dSFLyRYyKeiLUQeynCwhrYM+KSZ/bTKFbCYrSVu/+99qLHlDVpBx5BY57UWU1lZyj0wn82C5Gjr9Mfnrk7PkChlD1pIPZIQblKopaRCaNVAd8p6sdrwW5CuZ73jFtJA8QdVHbyS/ybSkHZt/MflEGjueZsQLUtfxKjWA3CQbSMugrzqaCnvpwYF/F/acUupHfsKWQKo+ZDtplbRj8z8iF522NB5276jAr1Qt2EjfJjtIR7/7r6T79aDOga8X+oGMv+BI01v3DoRN56z3iMnfHBZzxIuwgZO/PvALpNG6Sg6TXkFfjE7AHhQWoTOJn1XkUh2DxSwjF2Af9pYMd2Ji8ndPrvd7EUDfxN8b+EU1jJyDFZehQV8pXUf2x6pwye8d+K6eovAPanZ8IV2Tdkx+Fb+sj1Wf/LCIlpVGT38orbLldA32oDaBn75kj8B39RkW465ZzUZ5qgtSTH7NHF3v8yKqBuFk4EdJa/M8eYjyO8lx2IPaB75mlHxV8mLSrqCYdo6n84I89Ukx+bsl1we8CCu88ncGfklpVA+RG2RC0FdM22APCqe9cnyDFeFiuozCgdLHynuetGPyNyG/UDjtR8LuXRf4mRpETsH+fubhooQqYA+aGPj6CNUYV0NIPaetvV336k+m6pl4e5J2RdIul/8OeeC0pdmwe/sHvqfR5BKsBmjqVEc6zDyGbWWpNKO+w3aeVAtgL3TQ8XRO+UjWON4iWGFMC2Fs/lmwmeEuraOwwcmURlXTaTcK99/qqBN5DdtmV5GXZI4bAJua7+AfjCQdibUt7oKt/1dkshcRl1/aRJ7Bdhjluk+aeRGJVEl1Vg+3nJpKhxYtpRko3NPLqRHsT86Ff+x1FZtfu8hMWKy79HLlypUrV5b+APFgulhcQ4mDAAAAAElFTkSuQmCC>