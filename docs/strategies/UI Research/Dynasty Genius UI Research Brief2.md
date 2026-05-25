# **Architectural Specifications for the Dynasty Genius Decision Intelligence User Interface**

## **Executive Recommendation**

This specification defines the visual, programmatic, and data-flow architecture for the entire Dynasty Genius user interface. Rejecting the over-simplified, low-density patterns of commercial fantasy platforms, this interface is structured as an analytical cockpit designed for a single expert user.1 The primary objective is to facilitate high-stakes, long-horizon dynasty asset-management decisions across a three-to-seven-year window.1 To achieve this, the interface implements a "workspace-first" layout, prioritizing dense data grids, comparative matrices, and localized details panels over empty workspace vacuums or nested consumer menus.1  
The system architecture is structured around a central Home Command Center that manages the transition to seven specialized workspaces 1:

1. **Roster Audit**: An exhaustive evaluation of current assets, aging trajectories, and roster capacity pressure.3  
2. **Rookie Board**: An interactive draft board displaying Engine A outputs and replacement-adjusted metrics.5  
3. **Trade Lab**: A split-screen analytical environment isolating system valuations from market consensus pricing.1  
4. **League Opportunity Map**: A twelve-franchise roster-profile matrix highlighting market-vs-model pricing divergence.8  
5. **Player Detail / Player Card**: A contextual overlay drawer showing modeling pathways and decay curves.10  
6. **Trust / Governance Surface**: A diagnostic dashboard showing data freshness, API sync logs, and model boundaries.5  
7. **Settings / League Context**: A control panel defining core scoring rules, roster limits, and simulation variables.14

                     \+-----------------------------------+  
                     |        HOME COMMAND CENTER        |  
                     |  \- Roster State & Alerts          |  
                     |  \- Roster Pressure: P\_roster      |  
                     |  \- Open Decisions & Stale Syncs   |  
                     \+-----------------------------------+  
                                       |  
     \+-----------------+---------------+---------------+-----------------+  
     |                 |               |               |                 |  
     v                 v               v               v                 v  
\+----------+     \+-----------+   \+-----------+   \+-----------+     \+-----------+  
|  ROSTER  |     |  ROOKIE   |   |   TRADE   |   |  LEAGUE   |     |   TRUST   |  
|  AUDIT   |     |   BOARD   |   |    LAB    |   |   MAP     |     |  SURFACE  |  
\+----------+     \+-----------+   \+-----------+   \+-----------+     \+-----------+  
     |                 |               |               |                 |  
     \+-----------------+---------------+---------------+-----------------+  
                                       |  
                                       v  
                     \+-----------------------------------+  
                     |        PLAYER DETAIL CARD         |  
                     |  \- Model Path & Valuation Drivers |  
                     |  \- Expected Range & Decay Curve   |  
                     \+-----------------------------------+

The first screen visible upon initiating the application is the Home Command Center.3 This workspace acts as a diagnostic landing page, immediate-action registry, and traffic controller.3 It is systematically configured to answer three questions within three seconds of rendering: (1) Is the active roster facing structural capacity constraints or taxi-squad expiration risks? (2) Which asset-valuation projections or market-consensus signals have experienced anomalous deviations since the last sync? (3) What are the immediate, time-sensitive draft or transaction items requiring evaluation? 1  
To preserve the integrity of the underlying valuation models, the user interface enforces a visual and semantic barrier between internal model valuations—defined by the Dynasty Value Score (![][image1]) and Wide Receiver-Equivalent Replacement-Adjusted Value (![][image2])—and external market-derived price discovery signals.1 To communicate projection uncertainty, the interface implements the Modexa Confidence UI framework.5 Rather than displaying uncalibrated point estimates, the system projects probabilistic performance ranges paired with structured reason labels and explicit action-state modifiers that alter the interface based on data freshness and source coverage.5

## **Key Findings**

### **Visual and Semantic Separation of Valuation and Market Price Discovery**

To prevent cognitive anchoring to market consensus (sourced via KeepTradeCut and FantasyCalc), the user interface must establish an absolute separation between internal model metrics and external price discovery data.1 In high-stakes financial tools, market price is treated as a transient liquidity signal, while intrinsic value is modeled independently.1 Treating these distinct signals as a unified value index compromises decision quality.1  
The visual system enforces this separation using strict color temperature tokens and structural containment 1:

* **Internal Model Core (Slate & Cobalt)**: Internal valuations (![][image1] and ![][image2]) are rendered inside dark slate containers using high-contrast white and cobalt typography. These elements dominate the primary visual hierarchy, representing the ground truth calculations of Engines A and B.1  
* **Market Consensus Overlay (Amber)**: External price discovery metrics are strictly contained inside thin, amber-outlined badges carrying the label "Consensus Price Discovery." These badges are placed on the periphery of the layout, indicating that market consensus is a secondary external overlay rather than a system-sanctioned valuation metric.1

\+-------------------------------------------------------------------------+  
| PLAYER CARD: AMON-RA ST. BROWN                                          |  
|                                                                         |  
|  MODEL VALUATION CORE                                 |  
|  \+-------------------------------------------------------------------+  |  
|  | Intrinsic Value (DVS): 88.4 | Expected Value: 16.2 \- 19.8 xVAR     |  |  
|  \+-------------------------------------------------------------------+  |  
|                                                                         |  
|  MARKET PRICE OVERLAY \[Amber Container\]                                 |  
|  \+-------------------------------------------------------------------+  |  
|  | Consensus Price Discovery: KTC 7842 | FantasyCalc 7910            |  |  
|  \+-------------------------------------------------------------------+  |  
\+-------------------------------------------------------------------------+

Furthermore, the interface prevents any scenario where a market price trend is represented as a driver of internal valuation changes.1 In the Trade Lab and League Opportunity Map, market value is presented strictly as a context-only layer, allowing the user to detect pricing anomalies without allowing market sentiment to influence the underlying projection models.1

### **Uncertainty Calibration via the Modexa Confidence Framework**

Dynasty models face varying degrees of data completeness, particularly when transitioning between collegiate data profiles (Engine A) and active NFL veterans (Engine B).5 The user interface addresses these gaps by implementing the Modexa Confidence UI framework, translating numerical error residuals and sample limitations into understandable, tri-state confidence buckets 5:

* **High Confidence (Slate Indicator)**: Applied when source data is fully verified, player status is active, and the model's standard error is within the lowest quartile (![][image3]).5  
* **Medium Confidence (Amber Border)**: Rendered when minor data gaps exist (e.g., transitional injury periods or rookie projections lacking draft capital confirmation) (![][image4]).5  
* **Low Confidence (Dashed Rust Border)**: Initiated under critical data constraints, such as non-FBS prospects, highly volatile usage structures, or stale API endpoints (![][image5]).5

Rather than utilizing math-precise but uncalibrated percentages like "87% Confidence," which users routinely mistake for historical correctness, the system relies on these discrete buckets paired with structured reason labels and interactive "escape hatches".5 This design choice is detailed below:

| Confidence Bucket | Visual Treatment | Reason Label Example | Interactive Escape Hatch |
| :---- | :---- | :---- | :---- |
| **High** | Solid Slate Container 1 | Verified Data Profile 13 | Direct links to PFR/Sleeper raw logs.14 |
| **Medium** | Thin Amber Outlined Badge 1 | Stale Market Data (Last Sync \> 24h) 5 | Manual trigger to force-refresh local API caches.5 |
| **Low** | Dashed Rust-Colored Border 5 | Non-FBS Production Outlier 5 | Deep links to CFB Data to inspect raw yards-per-route-run.5 |

### **Temporal Density and Cognitive Response Latency**

The perception of trust in analytical applications is heavily dependent on temporal density—the speed and predictability with which the user interface handles transaction queries and background calculations.17 In data-dense fintech systems, the application of appropriate loading indicators based on response latency determines user engagement and trust.16

Response Latency (ms)  
  0 ms \+-------------------------------------------------------+  
       | Simultaneous Perception (No animations permitted)      |  
100 ms \+-------------------------------------------------------+  
       | Active Transition Region (Lightweight CSS animations)  |  
  1 s  \+-------------------------------------------------------+  
       | Abandonment Risk (Indeterminate progress loops)        |  
 10 s  \+-------------------------------------------------------+  
       | Long-Running Processes (Determinate progress bars)    |  
 60 s  \+-------------------------------------------------------+

The system's visual state-machine handles response times across four key categories 17:

* **Sub-100 Milliseconds (Simultaneous)**: Interface updates (e.g., swapping players within the Trade Lab or filtering the Rookie Board) must render within 100ms.17 No transition animations are permitted, as they artificially slow down cognitive processing and erode the perception of speed.17  
* **100 Milliseconds to 1 Second (Transition Region)**: For operations requiring localized computation (e.g., recalculating composite portfolio ![][image2] after a simulated trade), a lightweight CSS transition is applied to bridge the gap.17  
* **1 Second to 10 Seconds (Indeterminate)**: For standard background operations (such as syncing weekly matchup states or downloading the Sleeper user directory) 14, the UI displays an indeterminate loading indicator.17  
* **10 Seconds to 1 Minute (Determinate)**: Long-running, multi-step operations (specifically the iterative Sleeper draft-pick reconstruction algorithm) must render a high-contrast determinate progress bar, indicating the percentage of completed roster reconciliations.17

## **Evidence Table**

The visual, structural, and behavioral features of the Dynasty Genius interface are directly mapped to their academic, analytical, and technical sources below.

| Proposed Interface Feature | Visual Treatment | Core Structural Mechanism | Primary Source | Confidence Level | Implementation Category |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Workspace-First Canvas** | High-density dark canvas (![][image6] minimum) with compact padding (![][image7]).1 | Gestalt proximity and similarity rules; tabular layouts over sparse lists.1 | 1 | High | Model-Ready |
| **Dynamic Roster Pressure Gauge** | Segmented progress bar; color transitions from cool slate to rust red.1 | ![][image8] calculation; restricts simulation functions when roster is non-compliant.4 | \[4, 13, 16\] | High | Model-Ready |
| **Modexa Visual Containers** | Cool-toned Slate/Cobalt for model; warm Amber for market overlays.1 | Visual segregation; total omission of market values from Engine A/B calculation loops.1 | 1 | High | Model-Ready |
| **Uncertainty Interval Bands** | Shaded background gradients $$.5 | Visualizes prediction intervals derived from historical model residuals.5 | 5 | High | Model-Ready |
| **Decay Curve Visualization** | Continuous curve graph with hatched late-career shading.11 | ![][image9].11 | 11 | Medium | Validation-Only |
| **Sleeper Pick Reconstruction Ledger** | Dynamic pick portfolio table displayed on Roster & Trade cards.18 | Restores untraded draft picks via chronological traded picks ledger processing.15 | 15 | High | Model-Ready |
| **Divergence Spread Metric** | Neutral numeric display (![][image10]).1 | Standardizes the delta between internal value and external price discovery; no action labels.1 | 1 | High | Model-Ready |
| **High-Stakes Trade Friction Gates** | Multi-step interactive confirmation dialogs.1 | Enforces simulated cut assignment when mock trade triggers ![][image11].1 | 1 | High | Model-Ready |
| **Package Dilution Indicator** | Overlay displaying change in composite team variance (![][image12]).1 | Warns against consolidating concentrated high-value assets into fragmented roster-filling packages.1 | 1 | High | Model-Ready |

## **Conflicts and Resolutions**

### **Conflict 1: Aesthetic Minimalism vs. Analytical Density**

* **The Conflict**: Standard user interface guidelines frequently champion aggressive minimalism, arguing that extensive whitespace, hidden data columns, and simplified visual hierarchies are necessary to reduce cognitive strain.1 However, professional analytics, financial systems, and sports scouting platforms prove that hiding complex metrics behind "friendly" visualizations reduces decision quality by forcing users to navigate nested menus to compare interrelated variables.1  
* **Resolution**: Dynasty Genius rejects modern consumer minimalism.1 The visual system achieves clarity through rigid structure, typographic consistency, and localized grouping rather than empty white space.1 Every pixel is accountable.1 The interface uses compact, tabular layouts with monospace font faces (e.g., Fira Code) for all numeric values, ensuring that large matrices of ![][image1], ![][image2], age, and market price remain readable at a glance.1 The layout utilizes Gestalt proximity rules to group metrics into clear, logical cards, allowing high density to exist without causing visual chaos.2

### **Conflict 2: Sleeper API Draft Pick Ownership Omission**

* **The Conflict**: The Sleeper API documentation outlines robust endpoints for rosters and user profiles, but it does not maintain an endpoint that returns the complete active draft-pick portfolios currently held by each franchise.14 While the /league/{league\_id}/traded\_picks endpoint lists picks that have been involved in completed trades 15, there is no direct database location to fetch untraded picks, creating a major gap when trying to render complete portfolios on the Roster Audit and Trade Lab.18  
* **Resolution**: The system implements an automated, deterministic transaction reconstruction ledger.18 The backend initializes an active pick matrix ![][image13] representing twelve franchise rosters (![][image14]), three upcoming draft years (![][image15]), and five rounds (![][image16]).15 By default, every cell ![][image17] is assigned to its native roster ID (![][image18]), assuming an initial state where every team owns its default picks.18 The system then queries the /league/{league\_id}/traded\_picks endpoint 15, loops chronologically through the traded-picks array, and dynamically updates the owner values in matrix ![][image19].18 This programmatic reconciliation runs on a daily schedule and after every transaction webhook, delivering an accurate, reconstructed active pick matrix to the frontend without relying on manual entry or fragile web scraping.

### **Conflict 3: Numeric Precision vs. Calibrated Modeling Limits**

* **The Conflict**: Designers often display highly specific modeling percentages (e.g., "78.43% Chance of Success") to convey mathematical authority.5 However, quantitative research shows that users treat uncalibrated precision as absolute certainty, leading to a loss of trust when the model's predictions deviate from real-world outcomes.5  
* **Resolution**: The Dynasty Genius interface rejects absolute decimal precision for any predictive value where the modeling variance is high.5 Under the Modexa Confidence UI rules, raw confidence percentages are mapped to broad, calibrated confidence buckets (High, Medium, and Low).5 Furthermore, player performance projections are displayed as expected range intervals $$ based on historical model residuals.5 This shift in visualization forces the user to evaluate assets as a distribution of probabilities rather than anchoring to a single, false decimal point.5

## **Implementation Implications**

To execute these design specifications without compromising the active valuation engines (Engine A and Engine B), the following detailed, surface-by-surface implementation specs are established.

\+-----------------------------------------------------------------------------+  
| SURFACE 1: HOME COMMAND CENTER                                               |  
|                                                                             |  
|  ALERTS REGISTRY                                        |  
|  \+-----------------------------------------------------------------------+  |  
|  |\!\! WARNING: Roster Limit Exceeded (P\_roster \= 1.08). 2 Cuts Required.  |  |  
|  \+-----------------------------------------------------------------------+  |  
|                                                                             |  
|  DIAGNOSTIC GRID                                                            |  
|  \+-----------------------------------+ \+---------------------------------+  |  
|  | David's Roster State              | | Anomalous Divergence Signals    |  |  
|  | \- Active: 14/15 | IR: 2/2         | | \- Breece Hall: \+14.2 D\_spread   |  |  
|  | \- Taxi Squad: 4/4 (1 Expiring)    | | \- Rashee Rice: \-8.4 D\_spread    |  |  
|  \+-----------------------------------+ \+---------------------------------+  |  
|                                                                             |  
|  TIME-SENSITIVE TRANSACTION LOG                                             |  
|  \+-----------------------------------+ \+---------------------------------+  |  
|  | Pending Trade Offers              | | Upcoming Rookie Draft State     |  |  
|  | \- Offer from Roster 4 (Open)      | | \- Active: Pick 1.04 (On Clock)  |  |  
|  \+-----------------------------------+ \+---------------------------------+  |  
\+-----------------------------------------------------------------------------+

### **Surface 1: Home / Command Center**

The Home Command Center acts as the high-density portal for David's daily operations.3 Its architecture is divided into three key quadrants designed to highlight action items and state changes:

* **Active Alerts Registry**: Rendered as a rust-colored top banner when ![][image11], highlighting the exact number of roster cuts or taxi promotions required to restore roster compliance before a trade can be simulated.4  
* **Diagnostic Grid**: Displays active roster metrics (active counts, taxi slots, and occupied IR spots) 15 paired with a list of the top five player records that have experienced the largest model-vs-market divergence swings over the past 24 hours.1  
* **Time-Sensitive Transaction Log**: Integrates pending Sleeper league trade offers, waiver-wire deadlines, and active draft states (e.g., "Pick 1.04 On the Clock") 15, allowing David to immediately navigate to the relevant workspace.

### **Surface 2: Roster Audit**

The Roster Audit workspace shifts from a basic list of players to a structured balance sheet of assets and chronological risks.4

\+-----------------------------------------------------------------------------+  
| SURFACE 2: ROSTER AUDIT                                                     |  
|                                                                             |  
|  ROSTER BALANCE SHEET                                                       |  
|  \+-----------------------------------------------------------------------+  |  
|  | Player       | Age  | Position | DVS  | xVAR Range  | Age Risk Gradient |  |  
|  |--------------|------|----------|------|-------------|-------------------|  |  
|  | J. Allen     | 30.0 | QB       | 91.2 | 18.4 \- 22.1 | \[| | | | \_ \_ \_ \]  |  |  
|  | C. McCaffrey | 29.9 | RB       | 82.4 | 14.1 \- 18.2 | \[| | | | | | |\!\]  |  |  
|  | M. Harrison  | 23.8 | WR       | 89.1 | 15.2 \- 19.4 | \[| \_ \_ \_ \_ \_ \_ \]  |  |  
|  \+-----------------------------------------------------------------------+  |  
\+-----------------------------------------------------------------------------+

The interface is structured as an interactive data table displaying 1:

* **Asset Allocation Matrix**: Lists players sorted by position and ![][image1], displaying their expected range of ![][image2].7 Monospace text is applied to all numerical columns to maintain visual alignment and speed up scanning.1  
* **Age Risk Gradient**: An interactive visual indicator showing each player's position relative to their position-specific cliff.11 Assets within twelve months of their expected decay cliff (e.g., age twenty-six for running backs or age thirty for wide receivers) are flagged with an amber warning border.1  
* **Capacity and Debt Metrics**: Aggregates total team age, "biological debt" (the concentration of assets past their peak efficiency age), and the active roster-pressure metric ![][image8], calculating the structural impact of roster-cut scenarios.4

### **Surface 3: Rookie Board**

The Rookie Board workspace is designed for real-time draft execution and future asset valuation.3

\+-----------------------------------------------------------------------------+  
| SURFACE 3: ROOKIE BOARD                                                     |  
|                                                                             |  
|  ENGINE A DRAFT MATRIX                                                      |  
|  \+-----------------------------------------------------------------------+  |  
|  | Rank | Player       | xVAR Range  | Draft Capital | Positional Fit    |  |  
|  |------|--------------|-------------|---------------|-------------------|  |  
|  | 1    | C. Williams  | 16.8 \- 20.4 | Pick 1.01     | QB Deficit Match  |  |  
|  | 2    | M. Harrison  | 15.2 \- 19.4 | Pick 1.04     | Depth Surplus     |  |  
|  | 3    | J. Daniels   | 13.1 \- 18.2 | Pick 1.02     | QB Deficit Match  |  |  
|  \+-----------------------------------------------------------------------+  |  
\+-----------------------------------------------------------------------------+

The workspace incorporates:

* **Engine A Draft Matrix**: Displays rookie profiles sorted by ![][image2] expectations, draft capital, and positional fit.6  
* **Dynamic Range Shading**: Expected ![][image2] values are rendered as horizontal progress bars with shaded uncertainty bands ($$).5 Wide bands signal non-FBS profiles or incomplete data inputs, prompting caution.5  
* **Live Draft Tracker**: Integrates directly with Sleeper draft endpoints (/draft/{draft\_id}/picks) to gray out selected players in real-time, displaying a sidebar of the best available assets sorted by system value.15

### **Surface 4: Player Detail / Player Card**

Designed as a progressive disclosure pop-out drawer, the Player Detail Card displays deep analytics without forcing the user to leave their active page.10

\+-----------------------------------------------------------------------------+  
| SURFACE 4: PLAYER DETAIL CARD (DRAWER)                                      |  
|                                                                             |  
|  AMON-RA ST. BROWN | WR | DET | AGE: 26.5                                   |  
|                                                                             |  
|  MODELING ROUTE: Engine B \-\> Active Veteran                                 |  
|  VALUATION DRIVERS: Target Share (28.4%), Yards Per Route Run (2.42)|  
|                                                                             |  
|  EXPECTED xVAR DECAY PATH \[Graph Canvas\]                                    |  
|  18 xVAR |---------\\                                                        |  
|  12 xVAR |          \\'''''''''''''''        |  
|   6 xVAR |           \\                                                      |  
|          \+--------------------------------------------                      |  
|            26.5      28.0      30.0 (Cliff)     32.0                        |  
\+-----------------------------------------------------------------------------+

The Player Card contains three structural segments 3:

* **Model Path & Valuation Drivers**: Explicitly displays whether the asset was modeled via Engine A or Engine B, detailing the primary inputs (e.g., target share, yards-per-route-run, and draft capital transform).6  
* **Decay Curve Graph**: A line chart plotting the expected decline curve of the asset's ![][image2].11 The region past age thirty is shaded with a hatched pattern to represent survivor bias, indicating that the baseline curve represents only elite survivors who avoided retirement or performance cliffs.11  
* **Roster Context Overlay**: Displays David's current roster depth at the player's position, highlighting the performance impact of cutting or trading the asset.3

### **Surface 5: Trade Lab**

The Trade Lab is a split-screen workspace structured to evaluate trades without generating simplified "Approve" or "Reject" verdicts.1

\+-----------------------------------------------------------------------------+  
| SURFACE 5: TRADE LAB (SPLIT-SCREEN WORKSPACE)                               |  
|                                                                             |  
|  MODELING EVALUATION (SLATE)        |  MARKET SNAPSHOT (AMBER)              |  
|  \+-------------------------------+  |  \+---------------------------------+  |  
|  | SENDER PROFILE                |  |  | SENDER MARKET VALUE             |  |  
|  | C. Lamb: 86.4 DVS             |  |  | KTC Index: 7810                 |  |  
|  | Portfolio Delta: \-4.2 xVAR    |  |  | FantasyCalc Index: 7920         |  |  
|  | Dilution Warning: High Var    |  |  |                                 |  |  
|  \+-------------------------------+  |  \+---------------------------------+  |  
|  | RECEIVER PROFILE              |  |  | RECEIVER MARKET VALUE           |  |  
|  | D. London: 74.2 DVS           |  |  | KTC Index: 6120                 |  |  
|  | 2027 1st:       |  |  | FantasyCalc Index: 6200         |  |  
|  | Portfolio Delta: \+3.8 xVAR    |  |  |                                 |  |  
|  \+-------------------------------+  |  \+---------------------------------+  |  
|                                                                             |  
|  ROSTER CAPACITY CHECK: Roster Compliant (P\_roster \= 0.86)                  |  
\+-----------------------------------------------------------------------------+

The layout split-screen interface is detailed below:

* **Left Canvas (Slate \- System Value)**: Displays the calculated delta in composite team value (![][image20]) and expected replacement-adjusted value (![][image21]) if the trade is executed.1  
* **Right Canvas (Amber \- Market Consensus)**: Displays consensus prices from KeepTradeCut and FantasyCalc, mapping the market variance to help identify favorable pricing gaps.1  
* **High-Stakes Trade Friction Gate**: If the simulated trade adds more assets than it removes and pushes the team over its roster limit (![][image11]), the "Simulate" function is blocked.1 The interface forces David to select which asset on his active roster or taxi squad will be cut to accommodate the incoming package, reflecting the true structural penalty of the deal.4  
* **Package Dilution Warning**: When evaluating packages of multiple lower-value players in exchange for a single elite performer, the system flags the transaction with a warning: Asset Dilution: High Variance Package.1 This visual indicator warns David against consolidating concentrated value into fragmented roster-filling assets.1

### **Surface 6: League Opportunity Map**

The League Opportunity Map is structured as a competitive intelligence dashboard, allowing David to identify optimal transaction paths across the other eleven franchises.3

\+-----------------------------------------------------------------------------+  
| SURFACE 6: LEAGUE OPPORTUNITY MAP                                           |  
|                                                                             |  
|  12-FRANCHISE OPPORTUNITY MATRIX                                            |  
|  \+-----------------------------------------------------------------------+  |  
|  | Roster ID | Owner Name | Positional Deficit | Surplus Assets (Model)  |  |  
|  |-----------|------------|--------------------|-------------------------|  |  
|  | Roster 2  | Team A     | Running Back       | QB Depth (DVS \> 80.0)   |  |  
|  | Roster 3  | Team B     | Quarterback        | Draft Capital (3 Picks) |  |  
|  | Roster 4  | Team C     | Wide Receiver      | WR Depth (DVS \> 75.0)   |  |  
|  \+-----------------------------------------------------------------------+  |  
\+-----------------------------------------------------------------------------+

The workspace incorporates:

* **12-Franchise Opportunity Matrix**: Displays each opponent's roster profile, highlighting their positional deficits and asset surpluses based on Engine B evaluations.3  
* **Neutral Divergence Spread Display**: Displays market-vs-model divergence opportunities as a normalized numerical spread:  
  ![][image22]  
  The delta is labeled using neutral analytical descriptors (e.g., Model Value Surplus or Market Consensus Premium) rather than transactional calls to action like "Buy" or "Sell".1  
* **Surplus/Deficit Matching Engine**: Highlights logical trade paths by matching David's positional surpluses with opponents' modeled deficits, providing immediate context for initiating trades without using action-oriented or automated language.3

### **Surface 7: Trust / Governance Surface**

The Trust / Governance Surface functions as the system's diagnostic panel, ensuring complete data transparency.5

\+-----------------------------------------------------------------------------+  
| SURFACE 7: TRUST / GOVERNANCE SURFACE                                       |  
|                                                                             |  
|  SYSTEM HEALTH MATRIX                                                       |  
|  \+-----------------------------------------------------------------------+  |  
|  | Diagnostic Artifact          | Status   | Last Sync Timestamp         |  |  
|  |------------------------------|----------|-----------------------------|  |  
|  | Sleeper API Connection       | ACTIVE   | 2026-05-25 10:30:12         |  |  
|  | KeepTradeCut Price Overlay   | ACTIVE   | 2026-05-25 08:15:00         |  |  
|  | Engine A Model Calibration   | CALIBRATED| 2026-05-10 12:00:00        |  |  
|  \+-----------------------------------------------------------------------+  |  
|                                                                             |  
|  KNOWN LIMITATIONS: Engine A projections carry increased variance for non-FBS|  
|  collegiate prospects due to reduced sample sizes.                          |  
\+-----------------------------------------------------------------------------+

The system health matrix displays:

* **System Health Matrix**: Displays connection logs, data freshness timestamps, and sync statuses for all external APIs (Sleeper, KeepTradeCut, and FantasyCalc).13  
* **Model Versions & Validation States**: Outlines current model parameters for Engines A and B, explicitly flagging any stale database tables or uncalibrated projection profiles.5  
* **Limitations Registry**: Explicitly lists known system boundaries, such as missing college metrics or high-variance rookie models, providing clear context for decision-making.5

### **Surface 8: Settings / League Context**

The Settings workspace defines the programmatic rules governing the user interface.14

\+-----------------------------------------------------------------------------+  
| SURFACE 8: SETTINGS / LEAGUE CONTEXT                                        |  
|                                                                             |  
|  SCORING RULES CONFIGURATION                                                |  
|  \+----------------------------------------+------------------------------+  |  
|  | Superflex Format Flag                  | ENABLED                      |  |  
|  | Points Per Reception (PPR)             | 1.00                         |  |  
|  | Active Roster Maximum Limit            | 15 Slots                     |  |  
|  \+----------------------------------------+------------------------------+  |  
|                                                                             |  
|  TACTICAL POSTURE MODEL: CONTENDER MODE                                      |  
\+-----------------------------------------------------------------------------+

The configuration registry manages:

* **Scoring Rules Configuration**: Manages parameters for Superflex, PPR coefficients, and specific premium scoring values.14  
* **Roster Constraint Definitions**: Maps active roster sizes, IR eligibility rules, taxi-squad age limits, and trade deadlines.14  
* **Tactical Posture Toggle**: Defines David's current team posture (Contender, Productive Struggle, or Rebuild), which dynamically adjusts the visual thresholds on the Roster Audit and Rookie Board.4

## **Recommended Workstreams and Ordering**

To implement these interface specifications without destabilizing the active valuation engines (Engine A and Engine B), the following engineering phases are established.

### **Phase 1: Traded Picks Reconstruction and Data Integration**

* **Objective**: Establish a reliable, automated database layer for active draft pick portfolios.18  
* **Requires**: New Spec, David Approval.  
* **Tasks**:  
  1. Build the background database worker that ingests Sleeper league settings to establish baseline draft formats.14  
  2. Implement the transaction-log processor to sequentially apply payloads from /league/{league\_id}/traded\_picks.15  
  3. Reconcile untraded picks to assign current, complete pick portfolios to each roster ID.18  
  4. Expose the verified pick database via local system endpoints for UI consumption.

### **Phase 2: Statistical UI Engine Projections**

* **Objective**: Shift internal valuation displays from point estimates to probabilistic distributions and position-specific curves.5  
* **Requires**: Validation Artifact, David Approval.  
* **Tasks**:  
  1. Modify Engine A and Engine B output interfaces to deliver interval bands $$.5  
  2. Integrate the position-adjusted aging curve formula into the player profile generator.11  
  3. Write the survivor-bias calculation to identify and visually shade late-career high-variance zones on player curves.11

### **Phase 3: Modexa Confidence Framework Implementation**

* **Objective**: Construct the structural layers necessary to display uncertainty and provide user escape hatches.5  
* **Requires**: New Spec, Governance Decision.  
* **Tasks**:  
  1. Write the evaluation logic that maps data freshness, sample completeness, and modeling residuals to High, Medium, and Low Confidence Buckets.5  
  2. Define the exact database of structured reason labels (e.g., Incomplete Draft Capital Transform, Stale Market Data (Last Sync \> 24h)).5  
  3. Configure interactive metadata tooltips that display primary model inputs when clicked.5

### **Phase 4: Visual Interface Layout and Theme CSS**

* **Objective**: Apply the dense, dark-mode, workspace-first styling system.1  
* **Requires**: Validation Artifact.  
* **Tasks**:  
  1. Establish CSS variables for the application canvas, emphasizing neutral dark bases with high-contrast slate, cobalt, and amber accent colors.1  
  2. Set up visual containers that strictly segregate slate-colored model values from amber-outlined market pricing context.1  
  3. Restructure the navigational grid to prioritize compact, proximity-grouped tabular views over spread-out lists.1

### **Phase 5: Trade Lab and Simulation Integration**

* **Objective**: Configure the interactive decision-support tools and visual friction gates.1  
* **Requires**: New Spec, David Approval.  
* **Tasks**:  
  1. Connect multi-asset trade cards to calculate the composite dilution warning based on portfolio variance shifts.1  
  2. Implement the live roster pressure calculations to render the segmented visual capacity warnings.4  
  3. Integrate the two-step simulated confirmation dialog that enforces visual review of roster pressure prior to allowing any mock trade evaluations.1

## **Risks and Failure Modes**

### **Risk 1: Sleeper API Rate Limiting and Sync Failures**

* **Failure Mode**: The Sleeper API enforces strict rate limits, and exceeding 1,000 requests per minute risks temporary or permanent IP blocking.20 Programmatic rebuilding of the traded-picks ledger or constant real-time polling of player databases (which exceed 5MB in raw size) will trigger rate-limit blocks, causing the UI to display stale or blank portfolios.15  
* **Mitigation**: Implement a local, persistent database cache for all Sleeper player mapping data and traded pick transactions.15 Store the 5MB player payload locally, refreshing it only once every 24 hours during off-peak periods.15 Configure the draft-pick reconstruction engine to execute using localized databases, querying the /league/{league\_id}/traded\_picks endpoint strictly via localized state cache or via low-frequency Webhook listeners rather than real-time user-facing polling loops.15

### **Risk 2: Cognitive Fatigue from Uncurated Visual Density**

* **Failure Mode**: While analytical density is a major goal, displaying hundreds of raw data points on a single interface without strict visual hierarchy creates uncurated visual noise.1 This "screaming at the same volume" effect increases cognitive load, inducing fatigue and rendering critical signals indistinguishable from routine data.1  
* **Mitigation**: Enforce the Gestalt similarity and proximity principles explicitly in the design system.17 Reserve high-contrast cobalt and amber colors exclusively for critical, localized metrics.1 Use low-contrast grey and slate variations for secondary background data. Implement progressive disclosure hover states to conceal raw model routing inputs until the user explicitly hover-clicks the primary metric card.1

### **Risk 3: Behavioral Anchoring to Amber Market Overlays**

* **Failure Mode**: Despite visual separation, displaying market consensus badges alongside model metrics may lead the user to subconsciously anchor to the highly volatile market values during trade evaluation.1 This degrades the utility of ![][image1] and ![][image2], leading the user to make decisions based on temporary market sentiment rather than long-horizon model projections.1  
* **Mitigation**: Require the interface to dynamically hide all market overlay badges via a global "Valuation Clean Mode" toggle. In this state, all amber-outlined market containers are completely omitted from the canvas, forcing the user to evaluate trade packages and roster adjustments solely through internal ![][image1] and ![][image2] distributions.

### **Avoided Design Patterns**

To maintain appropriate decision support and prevent false confidence, the design system explicitly prohibits the following UI patterns 1:

* **Apology-First Error Messaging**: The UI must never display apologetic language like "Sorry, I might be wrong".5 Instead, it must state the exact structural reason (e.g., Outdated data profile \- last verified 2024 or Conflicting collegiate sources).5  
* **Dead-End Warnings**: The system must never show a low-confidence or stale data warning without providing an immediate next-step "escape hatch" (e.g., a direct link to the source verification dashboard).5  
* **Action-Oriented Verbiage**: Verbs that imply automated decision-making authority—specifically buy, sell, target, block, approve, and reject—are banned.5 The UI must present options using objective risk and allocation terminology.5  
* **Static Visual Uniformity**: The interface must never use the same visual treatments for high-risk, low-sample prospects (Engine A) as it does for established, active veterans (Engine B).5

## **Explicit Out-of-Scope Items**

To concentrate engineering resources on the decision-intelligence capabilities of Dynasty Genius, the following features are defined as out-of-scope:

* **Mobile Viewport Responsive Layouts**: The application is designed strictly for desktop viewports (minimum width ![][image6]) to accommodate high-density dashboards.1 It will not support mobile screens, touch gestures, or tablet interfaces.  
* **Write-Enabled Sleeper Transactions**: The Sleeper integration is strictly read-only.15 No interface controls will connect to write-enabled endpoints, and no automated waivers, trades, or roster cuts will be executed. All changes must be manually processed within the native Sleeper application.  
* **Multi-League Portability**: The database schema and visual components are built exclusively for David's Superflex PPR Sleeper league, ignoring other platforms like MyFantasyLeague or Yahoo.14  
* **Real-Time Live Trackers**: The interface will not build or display real-time, minute-by-minute live game trackers or fantasy matchup projections. The system is designed for a long-horizon, multi-year asset-management perspective, rendering in-game game-day visualizations irrelevant.4

## **Open Decisions for David**

The following policy choices must be approved by David before entering Phase 1 engineering:

### **Decision 1: Trade Lab Action Restrictions**

* **Context**: When a simulated transaction pushes David's roster over the active limit (![][image11]), the system can handle simulated cuts in two ways.1  
* **Options**:  
  * *Option A (Strict Compliance)*: The interface disables all evaluation panels in the Trade Lab, forcing David to assign simulated cuts before displaying the trade balance.1  
  * *Option B (Informational Alert)*: The interface renders the trade metrics alongside a prominent alert warning of the roster overflow but does not block transaction evaluations.1

### **Decision 2: Confidence Threshold Tuning**

* **Context**: The standard error (![][image23]) limits that define whether a player card displays a Slate (High), Amber (Medium), or Rust (Low) visual container can be adjusted to match David's tolerance for modeling variance.5  
* **Options**:  
  * *Option A (Highly Conservative)*: Classify all rookies from Engine A with less than second-round draft capital (![][image24] overall selection) or non-FBS college histories as "Low Confidence" by default.5  
  * *Option B (Calibrated Baseline)*: Determine confidence classifications strictly by model-derived standard error residuals.5

### **Decision 3: Market Overlay Visibility**

* **Context**: To prevent subconscious anchoring to market consensus during evaluations, David can select the default state of the KeepTradeCut and FantasyCalc displays.1  
* **Options**:  
  * *Option A (Default Hidden)*: Market overlay badges are hidden by default, requiring David to click an "Expose Consensus" toggle to reveal the amber containers.1  
  * *Option B (Default Visible)*: Market overlays render on the periphery by default, separated from the model metrics by container borders.1

## **Acceptance Criteria for a Future Spec**

A future implementation specification will be considered complete and ready for database implementation only when it meets the following objective criteria:

### **Data Parity and API Synchronization**

* **Draft Pick Ledger Parity**: The system must successfully query /league/{league\_id}/traded\_picks 15, execute the reconstruction worker, and verify that the calculated pick portfolios for all twelve franchises perfectly match the active draft board visible on the Sleeper platform.  
* **Sync Interval Integrity**: Background API requests must execute under a rate-limiting queue, verifying that total system calls remain under ![][image25] queries per minute under peak testing conditions, well below the Sleeper IP ban threshold.20

### **Interface Separation and Aesthetics**

* **Valuation Visual Audit**: A static visual audit of every active component must show zero occurrences of amber-colored market context indicators residing in the same layout containers or visual cards as slate-colored model-native valuations (![][image1] and ![][image2]).1  
* **Information Density Ratio**: The spatial design system must verify a visual data-ink ratio exceeding ![][image26], meaning at least ![][image27] of the pixels on the active screen canvas must display actionable data, statistical charts, or structural metric values rather than decorative white space.1

### **Confidence and State Operations**

* **Modexa UI Tri-State Execution**: Manually injecting an incomplete rookie dataset must trigger the correct visual translation: the projection displays as a range $$ 5, the confidence badge reads Low, a clear reason label is appended, and an interactive "escape hatch" button displays pointing to the CFBD query tool.5  
* **Prohibited Verb Audit**: A codebase scanning script must verify the absolute omission of action-oriented terminology (buy, sell, target, block, approve, reject, pass, fail) on all display surfaces, confirming that the system behaves strictly as a decision support cockpit.

#### **Works cited**

1. Fintech UI/UX Design: Best Practices for Financial Apps in 2026 \- The Skins Factory, accessed May 25, 2026, [https://www.theskinsfactory.com/uiux-design-blog/fintech-ui-ux-design](https://www.theskinsfactory.com/uiux-design-blog/fintech-ui-ux-design)  
2. Density vs. Clarity: The Core Tension in Modern UI Design \- terminal istanbul, accessed May 25, 2026, [https://www.terminalistanbul.com/en/editorials/density-vs-clarity-the-core-tension-in-modern-ui-design/](https://www.terminalistanbul.com/en/editorials/density-vs-clarity-the-core-tension-in-modern-ui-design/)  
3. Next-Gen Sports Franchise & Player Analytics Dashboard \- Dribbble, accessed May 25, 2026, [https://dribbble.com/shots/26936367-Next-Gen-Sports-Franchise-Player-Analytics-Dashboard](https://dribbble.com/shots/26936367-Next-Gen-Sports-Franchise-Player-Analytics-Dashboard)  
4. KPI Dashboard for Asset Managers: Metrics That Matter \- InvyMate, accessed May 25, 2026, [https://invymate.com/blog/asset-manager-kpi-dashboard](https://invymate.com/blog/asset-manager-kpi-dashboard)  
5. The “Confidence UI” Pattern That Users Actually Trust | by Modexa ..., accessed May 25, 2026, [https://medium.com/@Modexa/the-confidence-ui-pattern-that-users-actually-trust-ff27e1a8a956](https://medium.com/@Modexa/the-confidence-ui-pattern-that-users-actually-trust-ff27e1a8a956)  
6. Hudl Statsbomb \- The World's Most Advanced Football Data, accessed May 25, 2026, [https://www.hudl.com/en\_gb/products/statsbomb](https://www.hudl.com/en_gb/products/statsbomb)  
7. Top 21 Power BI Dashboard Examples for Finance and Accounting \- GrowExx, accessed May 25, 2026, [https://www.growexx.com/blog/top-power-bi-dashboard-examples-for-finance-and-accounting/](https://www.growexx.com/blog/top-power-bi-dashboard-examples-for-finance-and-accounting/)  
8. Using StatsBomb IQ For Player Recruitment: Full Backs, accessed May 25, 2026, [https://blogarchive.statsbomb.com/articles/soccer/using-statsbomb-iq-for-player-recruitment-full-backs/](https://blogarchive.statsbomb.com/articles/soccer/using-statsbomb-iq-for-player-recruitment-full-backs/)  
9. Using StatsBomb IQ For Player Recruitment: Centre Backs, accessed May 25, 2026, [https://blogarchive.statsbomb.com/articles/soccer/using-statsbomb-iq-for-player-recruitment-centre-backs/](https://blogarchive.statsbomb.com/articles/soccer/using-statsbomb-iq-for-player-recruitment-centre-backs/)  
10. Dashboard Design UX Patterns Best Practices \- Pencil & Paper, accessed May 25, 2026, [https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards)  
11. Joint Model of the WAR Aging Curve | Community Blog \- FanGraphs, accessed May 25, 2026, [https://community.fangraphs.com/joint-model-of-the-war-aging-curve/](https://community.fangraphs.com/joint-model-of-the-war-aging-curve/)  
12. Age Curves 2.0: A New Approach to Projecting Player Potential \- Analytics FC, accessed May 25, 2026, [https://analyticsfc.co.uk/blog/2019/07/17/age-curves-2-0-a-new-approach-to-projecting-player-potential/](https://analyticsfc.co.uk/blog/2019/07/17/age-curves-2-0-a-new-approach-to-projecting-player-potential/)  
13. Executive Dashboards for IT Asset Risk Management: A Complete Guide | Lansweeper, accessed May 25, 2026, [https://www.lansweeper.com/blog/itam/executive-dashboards-for-it-asset-risk-management-a-complete-guide/](https://www.lansweeper.com/blog/itam/executive-dashboards-for-it-asset-risk-management-a-complete-guide/)  
14. SleeperAPI Integration for Fantasy Sports Apps | SportsFirst, accessed May 25, 2026, [https://www.sportsfirst.net/sportsapi/sleeperapi](https://www.sportsfirst.net/sportsapi/sleeperapi)  
15. Sleeper API: introduction, accessed May 25, 2026, [https://docs.sleeper.com/](https://docs.sleeper.com/)  
16. 6 Power BI Dashboard Examples for Finance Teams \- Vena Solutions, accessed May 25, 2026, [https://www.venasolutions.com/blog/power-bi-dashboards-examples](https://www.venasolutions.com/blog/power-bi-dashboards-examples)  
17. UI Density || Matt Ström-Awn, designer-leader, accessed May 25, 2026, [https://mattstromawn.com/writing/ui-density/](https://mattstromawn.com/writing/ui-density/)  
18. Draft Picks in Sleeper API? : r/SleeperApp \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/SleeperApp/comments/1l7pun6/draft\_picks\_in\_sleeper\_api/](https://www.reddit.com/r/SleeperApp/comments/1l7pun6/draft_picks_in_sleeper_api/)  
19. Sleeper API MCP \- LangDB, accessed May 25, 2026, [https://langdb.ai/app/mcp-servers/sleeper-api-mcp-2bef2d2b-8e7c-48d3-bdc1-53c6318c61e1/](https://langdb.ai/app/mcp-servers/sleeper-api-mcp-2bef2d2b-8e7c-48d3-bdc1-53c6318c61e1/)  
20. sleeper package \- github.com/lum8rjack/sleeper-go \- Go Packages, accessed May 25, 2026, [https://pkg.go.dev/github.com/lum8rjack/sleeper-go](https://pkg.go.dev/github.com/lum8rjack/sleeper-go)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAaCAYAAADxNd/XAAACjklEQVR4Xu2WSahPURzHv8YksvDwQhnCUxLKKytl2kjJwkIssJBCsbGTpVCGFSVJUTKUoZQhycKQyEIyv2ceMyxYkOH79bund+6vc25Xdrqf+tTr9zvnvHPP/3d+9wINDf8trXQOHRbFxkR/J2mnD+gr+pq+pB30Ee2kt+kmOqQYH9hFn8Lmyod0fWkEsI6+gK0j98bJiNF0Hz1Od9In9ADdQLdE4yo5RH/RaVGsH2wTz2APNDzKifGwOdpkX5cLbKcX6QzarZz6wyDYgS2KYhq3H7b2vCheyWP6kXb3CTITtpgW9XylX3ywoD+9RQf6RIQO7pgPktn0Bx3gEyl0strgCZ8o6EHf0G+0p8vdg81NbXIbXeaDEVrrM93qE7D1rvtgjsWwTaz1iYjLsDEjXfxsEZ/i4pPoBaTLJjAYNlclNM7letOpLpZlD2yhyT4R8R42Rp0iRhdT8flRTGV4iU6IYjluwuarXHTiahgTSyNqoC7yAen6F+pA+ieqdX+iG4vcmii2EraROqgDhV83+B12B2oR6l8tLMcK2JjUJVaNKxfanR5Wp5rrSjnU0VbTa7D1rpbTeZbAJlTV/3nYmLjFBmbBcuom4iCd25XOMpS2+CCs9tW21TRqEWo4V//6KX/COkqKsbD5V2Bv0SPldBa9CKf7YMEZesoHc3QgX/+j6HN6jvZyuUAf2AO8pTdgJ1uHO3SpD8Lm692y3CdStMH++UkXV3tTPX6im2HvgSr0CaJ1VvlEhtAU7qP8XtG9OYyucsyiWta3i7qKFtIT67umE/YdInegfh/WhVMJpX7FFAvpadjFf0ePwrrZXbobf98A/hndE5VbXdTnwyZH0AWwbqbvooaGhoaGhkp+A0dlkDEsRy1tAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAaCAYAAADrCT9ZAAADEElEQVR4Xu2WWahOURiGX/NUhkzJlFyQWS4UFyehpFwgIeRCMiWZc0NSREIkShlCioy5UOSUMRcoLmQ8xxQ3yBCZ4n19a59/7+/8Z+8/Dm72U0/n7O9bZ+191lrfWgvIycn5yyyl7Xzwf9GTPqYV9D59QO/SprE2jUP8aWhXSfvF8mlMpD9omU8E1Pcd+py+pC/oI9g7HtITdFLUuLaoT/fDPmyBy0W0oR/oYpQ+Wxq0J7B+J7icZzas3YrwXIe2ostCfEOI1xrLYR3rBcVYSFf5YAZrYKtF/c5zOc9uWLtBPgGb+fe0uU/8CZNhL9zmE6QjvU4b+UQK3egVOg3W7+pkuhoqmTe0ros3pF/od9rF5YoygA5H4WPb0sGFdBVDYB920ifIETrCBzM4RofC/k797kimE2hAa3r3VFhuu094GtDDdB/dSm/TlXQXPU43FZr+ojOs45suPpoedLEsRsL2BKEBV78agJqYAmujsonQZqYS0lLejOQmWpT1KOxuWhbq8AJtTb/S8yEXUY9+o69isSb0Bm0fi2Whgb5GO4TnaCAvVbWojiZBbS7T0+HnW9i7B8bapaJRiegN63AGbPdbRHvE8hE6ntSuWXheS+cU0iWhvpfEnjUz6vNeLOZR/b5Gsn5nwer2t46kubCXaiNJ4yKsnc7mXrAV4TeRNLQS9OE6UytQOE/Vp2asGJ1QvH61uhQ/6+IlcRQ2e1moVvWSUbSc9k+mM9kLq3mPZlD9qi490S6ulREnqn0Neia6SGg5joPVpkb9QCw/PuQ862Av0XGy0eWy0C5/ygcDV2H9dvUJsgeW8+fv/BDXTSuTMlhjLeUx4XdtYqIFbJfWoHii204lCnVcCn1hS7jY7IpzsH41KHH0DbquvkP10tG5rb85FJ5nIqWedfXTaG+BXSTGwv6JnbAR61PVMomWsl5S04d7tPtX0k/0c/g5LJafDqtnxaXquBxWn7dgN6iPwWewYzOie4hpIDURZ1DCJMQ3KdWPDvg0dHfNuvP+S1rCLi6a2WIrMicnJycnJ+c/8xNB6a/Y6s/bdQAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF0AAAAaCAYAAADVLFAXAAAEKUlEQVR4Xu2YachVVRSG30YLKwOttAEqK7A5jQYqmmgyEJUwpLDJgqIEw8IoQoqgKIqI6kf9K4KGH0VlUWg0D9hANIuGWpkWREXz+D6sc/z23d8933fOvV/pj/PAyz137X2mtfdea+0jtbS0tPzvbGYdZ022tilsu1rbbujRMqJcZC2x7rKesr62zraWW9sn/Z6wPquhl8sTNhJ7WuflxmHYx7raukVxbjnxco60rrWusw7L2mrDjV63dkxs+1p/W8sSG2xhnWD9Y72gWAVbKR5wjGKVvGa9W/TvB56Hl2MAqxyQMsm62Xpb8exPdzYPyVnWUut8hT++s1ZZE5M+sMD60JppzVZMsMs7etTgAOsv66C8wbxi3ZYbzWUKpy/MGwqmWY/nxgaMV8y2V61zFANdhyOsC60p1m+q7/QdrLWKQSuZoXjHtxIb7dgOT2ynKu61X2IbFkaVC22XNyhCzZm50TyiOIdlVrKbtXtxfIx1Z9JWl72texUriIEjx/RKE6cfq3ifTxIbK/inwk7YgdutHzb0CLZWrCpCTW3uVlz4RmvzrC1NqCnrFDffMrHxQMcXx4daU5O24WCVPWgttk7M2nqlidOZ6YQWfJDykcI3TAZ4TxFycvAF+bA2zCgujL6xHrYusEalnRL2V/Qlzu6hcNglihtXnVPF0Yow9Jg6l+xI0MTp3WAg/rTeT2xfWp8m/0vw28e5cShYwvOtXzTgfPS8OmdySRnPuTkxn4TJCxISmsCq+N2amzeMEP06/SbFe56b2LhmN+ey8lFjRitCwh3Wr4obnt7RI3hUg5PJIuv65D+JsA5USPcrBvi0rK1fcBDhqhcOVkxC8l0KfknjfgkO/yo3VnFIbii4VOFYflNYFSyl79VZUVxjHVUck1ioOvL8MBQkYXLCi4rSrcm5VeD0Z3JjDSZYK9V9BX6h2LfkfKvOMFTJLqoO/sRanE7plXJgYWfzVMXFikHohbGKVUOdT16h/u+VXpxOHH9DUYOXcEzugjc1OIwwEWvfa5a1Qt1rYMq9zzV4xl2hcPpVmb2EgVxt7Zw3NITy9UqF89l4dKughgNHPJsbC3bSQBlYwgCT1E/O7M9Z44rjRYryMH0eQik+mZfYKrlH0XlOZqfGZjdGuZjzpOKctD4HHpjNBBuMB7K2fiBUscyJzRzXhechSb+k7sUAE+oPxacCYLZSshI+KB0RoY6N0fqiD7A7/dGantjYjPHJpFYee0cxc9nSUoHcqrgxtWieQEmeXBiHI455cLTG+lmxq+VFR7r0awKFADGX0o4SFhEO2KrziaLkIesDDWwIT1Fn5ZaK1ZZyhmJy3aD45EC0YFdfi3K2MoP4skgMPWmguWUIGCwGmAFIPwZu8jDYlIx1tFdxTkufUAvfV1Pkn26xuaWlpaWlpaWl5T/hXx1v7xz7hTaIAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF0AAAAaCAYAAADVLFAXAAAEY0lEQVR4Xu2YaahVZRSG3wYbUFGwwczAnBrUBpuMSDPSSsEGKvFPZhMkJgiVjXLTH5VKA1K/yj9qaIklTpFWF5uwsiKKshBpsIEEKy2b9X1Z+/Ous+4+9+xzrl4U9gMv55z17X32N6xvrfVtoKSkpKTDOYS6mBpKHZXZelFH772iZJ9yC/UaNY9aSf1Ijae+orq665ZTXxbQm+mGDqYbdQc1h5pKnVDZXJVLqEnUmTCHOwM2JyPcNYkLqAeoB6mzQ1th7qHepbo72wDqf+oDZxOHwTq4m3oDtgs6wTqqAWuXvEN9lF3fkQyk3qPupG6nPqV2Ulf7i6rwMGxMXm+h9aLdRX1GXUtNgDnYlIorCjCI+o8aEhtgD50bjWQyrFP3xoaMcdTL0RjQ7jkyGttJMzXR/T6W+pf6PfveFk2wRXqfWgQbo5zJcxps3Oc622jqL9iCF0Zerj/qEhtgoWZsNJIXYPdomyVOpHpn3y+innJteWgbr6NmUD1CWyMcSv0N253KQ4nXYX291dnyUD9uisbA49RvwXYE7JkKNYV5GtapWbCOe3xC9fwEe/jhzqYOpfh3FjXGtVVDifsqWJh6kjqpsrlunqFWobJfsml8NztbHg+h9qR/TH0djbC5UD4sjEJBimE/U0tgCaXa1j8ddq0SpSZJYUnxUw+udk8RLqPWUPOpU0Nbe1C4UIipFV7kqY9RL8LGthqtnWArtSnYhObt82hsC3nbNGoXKpPIWlR6TCLFcz1cMV8JUzFN3rovOJ9aRi2lzgtt9TIK1tdnY0MO91EbqWOy39dRv1BX7L3Cxpk3udr5Ut10hoWEJ6g/YZ31D0zIE9Tmk0kTLCYmerrvjaIEvwAWLoaHtiIoUX8BW0DF3Vqoz756E1uozWgJu5oX/WdEE/59NFZDySwP1bmaWH16tCu0lX6FlY4Jecmw7LsG+DZa54dG0PZ+CRYi6gld2qEKVc+hsp9tobFFNA7NQ9/s93ewc0tkG/VJNOZxPKoH/wthDzsn2Adndh2eqnEbbBHag8ovTdirsJKsXnSv4nNCeWek+x1RtSNv1S73rIeNV+MWG9A6jGixFHa0yDW5AbZ18jxB5Z62VvRWHTrUibuDPaGF/IY6LjYURKe7xTDv1sI3gg4504PtfliMTiip9ne/T0F+7Ffe+gMt9XoTrDz0FZ3Cku7V6bcmqZS6MdhVY2+HlYuRFbB7fH0u1KlrqB9gcbhe9L5H/617k1c1gqqoHbCkrvq8GXY6Vjj0hz851D9UH2d7BS3nDKFdrrH6XdsP9v/+hKtSVK9MCuWxD2GeqyOtKhC9q1gIq0VjAlXy1B+rE5K+q+PStzBv0KlWhxOfYGtxOSyE6KxwcmirF72OUGmY+uilvnnvfB52+vQHQi28XoXovDEbNkZ9xgruSphzzaQehUULJf1CJG9V4tMDVZtf2tK831HifQQWkg4UFJ8V1q5H5S6IaLFU6WkB/MvAkpKSkpKSkpKSkpKDiD3Sb+8VIVvJHQAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAaCAYAAAAAPoRaAAADP0lEQVR4Xu2XWciNQRjH/2TPUvYkn6UULpAtSVxIlpSsWeqLS6GUlCzJEkpuKOLCeoGSyJYlIdlSsmTf9yV7trL8/z0zzpw57znf4eKzvf/6dd55njln5pl53mfmAKlSpfrf1ZyUxsY8Gknmx8ZIVclOUhI7qG5kBplJOka+clMbsoicIV/Jrmx3opqQl2Rz7Ii0mHyDjRFqKrlIhpBR5CqZmNWjnNSVjCedyCcUF/xW8gWFg9fvvkNu8HqWrXNg6wsbu3VgK3cVE/xYMpe8R/7gle6HyRLkBr+UvAnaUhVY1ukV+G0qK/hGsKA02ULBLyCjyTTkBn+W3AnaXlqQg0G7NulDarp2PTKc1P3RI6OmZBAyPi1+b9g8i1ZZwSvYLu45X/AqXnotpKTgH5ArQdvrGbnknquTPWQ/bLEmk1VkCjlP+rl+0nSyz30+dn22k4WwOla0CgU/DFbAvJKCr0QOwQqilBS8xvBBhnrikFQQB8JeMX1/nu9ELSOn3XN/sjLwHSPPYeOfgs2xWuAvKE1sd2yEpZPSPfyhpOB1dI0L2knBfySXg7aXAn/onrVrStnlsHHC9F0Bqw+ak8ZrEPiekg3uWUexXpuipeCVbrHWkh6RLQ5eAe4I2lJS8PfJtaDtpR07F9mU4gci21HYAlaO7G1hY4WL/1PKF7wmqyJ1i9wkt2ED6ShTW2f1BNdHPtnEa9fvHjkB00lk0turAnLHro/cE0C14AMsvWNNgo3VMnYUK01gb2xMkCqvBorTPpbez3jn58CCCl+hxrB+KmxeQ52tZ2BT3dH9ortrl5LZ7llZp6zyKoG9PkVJafSZHIEVrkLyk90WOyKpGKlf+8DWirwlgwObLlmq1PpdL79wvl8dch12T5BUB5T+W0hDWEYoq6SKZB1p5tp5NQCW1jqCdNYKpaWunBow1nHYRH3fu7C0D6Uz/gZ5BevzAvY9L1XpR7DLkq7W6tsu8EsXYMecdnQNLLAxWT1scXUEbiS9YIujtv5PKHP+WOnyooXXQtSKfNpJ7fos19YO1si4s6RsUS2QtOMtAt9fqRGw4LWb/5U6wIquDz7pOvvPajVZD7usbIL9O0yVKlWqVL+q7xD3zpqPhLpaAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADgAAAAXCAYAAABefIz9AAACz0lEQVR4Xu2XWaiNURTH/5nJUKYkuXgQXkylKPEgY0rmDN148KAoJZIhJVPkhSIeZEgiD2TKkDlTSvEgU4RCEpKpDP//XWufs8/nc69zO0cH51+/zt5r7XO+tb61vr2/A5RVVlmlqIbkMKlIOvJUJ1KZNLrqkElkLVlIeue6iytd9DvpnnT8hvSdNeQG+UaO5Lqr1IicJivIdHIItnZVvKhY6kfeo/YJ6vszSV/yGekJLifbSN3IdhN2zZGRreBSa54j61H7BGP9KsFTsN+fHNmWuW13ZCu4VpIpZAGKm6AqfJl0jWwTYdfcGdmakyGkqc9bkQmkZWZFVh3IaGR9KtbgjBf2kB/wcbETTNM62DXH+rwxOUZOwtp3LtlK5pFbZLivkxaRE/753NccJKvDgnrkDGnv8z+dYBvyBha4EpPmk1FkGiwWbUhBG8l1H48gWyLfJfIKlsu1YFxMZoQJfk5Q1VVbVYcCSUoJHk0aU7SH3IG1WZDufgOyiXzwcdBm2K6rdlTsukFBL8kuH+sYqkpC23SsZILdyJgaSNv9lKDarDopQFUjDjKWqqpNKdYF8onUT9h7wOKOi4XZ5DF5RB46b2ELn5ArmZX5q6YEK2HBN/O52nNW1o3WsEotiWxa8xHWiknNgcXdJelISj1eqGfweNLoGkb2w3a7oAGwlgwaB4tjYGQbT76S/j7XTdIRI6kTn/pYqojGOdJDqx/umXTkIbXPF3IetonF6kPekYuwN5qzsLZ7BqtCULjRegSkFuQ+2eBzPZdq1X2kLayyV92nV8EdPs5IZ+AD2I6mAF7Dzqt8pGfxHixY/YZ4Qe7CApTUXgo8jaG+RroNOyJUme2w4KdGfknF0PGhF4RBsBugud6l1QElK1VECS/1eUfSJOvOUTtkjxdVrnPkK1mFNxtV5Z9TL9jmFBJMezX7q6V/Gnon1YG9F/YPpaz/Uj8AAuesX8eiFhQAAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAaCAYAAAD1wA/qAAACU0lEQVR4Xu2XS4hOYRzGH/dryUSSa1KsqGHhtvgsRFKUhRisKakpDULEghLZuJT7giQWkqQoslNqxAqRyLAZkpga4Xl63rfzehuLqe+bztT51a9zzv99z/nO/72eD6ioqOgNi+kr+pF+Csc39DV9Sx/TTXRovKHsXKN/6MIkNpxuC/HjSbzUqBe+0kF5AXlHf9GpeUHZmAy3+u28gAyk3+lvOv3fovLRAieyIy8gS+GyS1m8lJyFX3ZeFp9Gn9D3dEJWVkq0amno7KU76R56BZ4zF+nYomp5ifPjKV0dXEVr8KrVb9gIJ3IgizeC/XRcHqwX5+FEalm8EWiTHZ8H64V27590WF6QsJxeplvpQXinF9pzNtB98PwaFeIz6PYQu0DHoNhwz9C2UE/Mp0fhZ2tB0b3n4N/ZQg8XVf/PLPjhj/KCjCH0FP1Cl8ALgbhDN4dzJXSPDqDXUWyeWhGb4Pmm35qCotFW0Lvw82v0JrxvrYc34GX0AXx/j+gz5CXthHvjB7zErk0rZah1YwJCS3NHci266Vy6C37+ETonKVci6dC6Sm/RVngP+wZ/06mxPsCNUneUyInkWsNNPRRRS3bBrTwCHn56UX36xD1Iieh8NjwsX8BJqEeiQom0h/O6kyeillMiE8N1M9yrGjYaIpFjcNJCiU6C59TgcEx7eQ2cTMMSWUmf0ed0dxJfQO/TQ/QGXRTiD+G5oQl8GsWHqJLSi8dn6KVV7yS8Ea+jM+G59hleGNS7fYJeUr2ioRUZGY6jk1ikp5gmc7/5v1NRUdHH/AVwSXKAFX0doQAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,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>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMYAAAAXCAYAAABQ+TDXAAAFhElEQVR4Xu2ad4hkRRCHfybMOeuZsxhBRVHMEcSM8UTBDEZUjBjBnP4wIkbMAQyYTz0RVMxg1tM7T88zYQCzZ6jP6nbe1M7s9og6e2x/8GNnq/u92e3XVV3V/aRKpVKpVCqVSqXSgZlNW5qWN02bbMu2miulrG16zzTZ9KnpE9N40/umCabXTWebFkz9KwOZyfSqaZJ8DBnLCaZx8rFkfG8wrZb6Z/YxTZSPNX3of3dbD2ld+X0/lN/rjfbmv5nNdIZpjOki04umV0x7mp5q9Kv0yG2mP+QPIsNgH2X6SP7wRjXaKgM5WD6GxzdsRO1dTM+bfjBt1mgDxhiH4LrVQ1tme7lj7CFfESJ8x/2my0zTNez7ye97QcNW6ZEPTF+rtfw22VQ+wES9SneulY/TmrHBmFXuGASY5uSFh+TXrRPsmXtMG0djAxzyM9P0wT676UfTtsFeKYSVgAdzb2xI8CAZ+F80cPArLYj8X6lzcIG75OO8YbBflew7Bztsp6ED0oOmF6IxQTo1ZzRWythL/mCOjA0NnpH3WTLYK86i8vEhunfjLHmffYP9xGQnbW3CKvOyaf5gj1B3TDFtExuM9aOhUs7V8gezRmxo8KW8z0KxofIXJcElrxi7B/veyX5xsJ9nOiDYOkGxzfWIVetK09ZtPSr/CHZEBksB2JFi0L83TRPaphbWk+/OdNNY05OmJ5LI+2fkwkJKgstb8j6xltgo2Zs7UqvK/66S8aaAp775XS0HQac1+lR6JNcXg6UAB8r7DJXr/p8wEdkaXSY29Imh6gvOFRjD8RrYZ6nUxs4V4Axj5c7RCwQwVq475ff7TZ6ODQbtixRqrnTNiGC0fBAHSwHYG6dPcyt3OPCFablo7AMlweVkeZ/jYoMxg3wS4+hA+kQaNRRs3Xb7/2+Xf99KsSGAI91aqJPSNSOCazR4CrC5fIkmjx1ucBjZbWJE5jZt0YM4b4jbqt3INUK34EIk/9z0nNwJOjFJPs6LywvuWdqbO7Kb6ZRoTJxg+kYDV6dKISzt3VIAlviPTY+p/YEubTpcHgXJbdkv53DpDvmZx6Gmc5MdDjPdIl+dzlcrx2Z5JjIyoVZJNrYWT5VHVn7Ol+xAhOQ7EROXCFvqGCuqdW2JmFilNcZ1csfodn7xqPyAbonQ1uRZ+T3Y/Ss9d7jcdH00ylMxtmlvjA2VMlaQP4z7gn0B+eQm4jDBY+TEAYhsQK4/j2kx+b3yjgunrvkwi+KQB/VIsh+druFQkYmPM7ABQN+dTC/JISJSBGduMu2fPpOz/6xyx/iv4FyHNwPi4ShOvKPpbdPDpnkbbZ3Ibx5QH5TypulXtddZOAXj+47q+UXPUCuMk+8y8TA4kZ0of7+HyIYuMa2V+kd45eFd0zlqf/+HPHnh9JlJ/q1pk/T7GLVvPVLQ8x4We/eIv2eD1Ma7R7zDRZrAagYUfvy9zQNGHLdfjsHEf03uEIwh/zsOwthNkK9mrJIc0HVajSOMJf8Pq2gJBC9We1bjyfKdtNNNT8sP/Po1LiMaJgV5NQ+eqJ9fMJyilmMQuUjDjki/4xg7pM9wqbxYJUXL4hqcg2jHysEWKxMPqHV+Sp8z/XSMf5uV1dthHId+pLRA/bSVfDXlPpU+0dxvv1D+UADHoC4BJjjL/Kj0e3QMXosg4uXahZWH1O4B0zHJxkRh8o+WnyzjMHkykP9/J0+pKpVhwVh5bXGI6Qq1ahAc40zTQfIlfddkJ+dl14UinjdNMxTwbCviCPmNVOoK3vsh7TpWnq7wXTgQBffN8vtTsPOC3OOqr8RXhgl5K5GiuklOpeaQ1wklkJbFIpE6Iu9oxcIfchv5eMm2ZqXSN8j1KUJJkUqKzUplRMAbopw98DNH9EplquFPtGc527qPDQAAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGgAAAAaCAYAAABb9hlrAAAEHklEQVR4Xu2ZeahVVRTGP600NTTN6WWOKCapoZZoqT1FUTRJEKcc/lZoIBS1QRJFNBoQQStyeFaKioIDGoHS1UBBUJICxaKHOOU/GtIgGer3sc7hnrO407m+i+/5zg8+3r1r3XPuPXvtvdda+wEpKSkpKSn1g5epX6kr1B/B39+p36ha6kdqLtUsvKCR0opa6I1FaEpNplZR71BVcXcydlB3qeER2+PUG4H9s4i9vvI19Qn1jHeUSVtqKXWYukX9HXcXRBN6N3WQGkUtpi4jPr6J0Kr5k3rEO8gF6n+qm3fUQ8ZQh6gaql/clZiO1JvUK9QxJAvQfOoa1TJi00rSbvVoxFYSmnFaJQe8A7ZM/6LuUD3irnrNUGoPbBa/6Hzl8D2SBeg0td/ZxsLGeYSzF2U27MJF3kFGw3w1zt5QeI76hvoOtrrKJUmAnoSN2VZnHxzYlzl7Ub6CXTjE2btTJ6mLVCfna2j0pDZQGVjibhLzFidJgPrAxvNLZ9dkkf1zZy+K9kVtYR9QS6j3qW2wnLQFliwfFpRPbsKKnyQkCZAKgVyBUE6UfaezFyTMP6eo1wK9SlXDqriHhUGwgdlLDXO+UlCA/vHGPOj+GtMvnD0M0HZnL8gc2EXLnb0SfEi198YKMxJW/HxLDXC+JChA/3pjHnrDxlSpI0r/wL7O2QuyCXZRtbNXAjW/HbyxQkyC9S/aZno5XzkkCdATsLbEb2UvwcZaaaRkamFf3Nw7IoyHVSQLqBWwkwWhnul1WFWi/KVuW2hA3gpsm6k2yDbCWvZq2kJeoD6G3VuFiK7dCPse9RKrsx8tilqCadRR6iOqc9x9XyhAalZzoabUF1gZ6oSzzYSNwUBnz0tf2AV6oEI8BquAbsBqeBUQQl3yvOC1AqWHUHW0C9mmVsu8HSyf6bu6IjsZJsDKX92/Gta3aJBnwWbgOOoI7PpSUGDfg5W5dc0P1H+w1eGpgT2b0kXIDFhR8XTEppOOTOR9XlRlnKeuw1aPkp9K6anRDzm0GsLAiO7U1ch7cZt6HnY8ovuvQXy26CGiW5yS5T7YOZV6MFVXmo2aBJeQvBSua56CVbjaZfTbJE3Sc7BdJUQVocZPzXGUldRZ6m1YDjxOtY59og5RgNZG3usH6seGaOZrC9CqaAHbBhUAHSGFPZQCpNfPwrbHX2DB0QoKJRSgn4LXDR1ts9NhiyJ8vorgA6SZrgBVBe/VJWsWafvSVhXyKbKzTQHsAstZOo/S3+iqnAJ7iHIDpN+iJrEUVWwmPwgmUmeon6l3I3bV+6qUtJR15qUqRWRguUeJX1VUeACrYCkg4T0UDH1uPayy0b6tElW5TAeNKii0GktFk0j3K0Xq9RoFGnzNXG1xIeEJbq6EmsumIqCx/78pJSUlJSUlJaUw9wD+CNTyapDkgwAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAXCAYAAACFxybfAAABy0lEQVR4Xu2VSyhFURSGl/erJMqAMvCYGFGKMkGKmQxEGSjKo0gMiCjKQAxIKSUjQxl7xi2MMDCQR9QdKI+BkmSg8K/WPs6+63pcuSm5X311zlr7nL3ae69ziP4p4bASDsJ8lfs1BkiKKIHnsNkn+w71sFAHf0AMfIDV5p4LunHT/mTCJ3hIsoTBohammOsO6HVT/szCR/gCa1QuGITBPdilEw4Z8Ag2khRxQPJQMOmDIzpoMw2bYAQ8IymkymfEz6iDvea6yE44pMFjGGXuuRguYvdtxOfEwyyYDXMsY02+DE6RtGcBnDdxHyZgi3XPxXhJCuHW+ogkOEdymHmstgEmwjsV95AiFZ7AaBVvI3lgR8Ud0uEFXCJpv1Z4CfdhMcmSB9xho7BdB0n6myfhQng5bfjArsFNc+3A77pVsS9Jhqfk7p2mk6SIDRUvN/FSFR8jWfpvFTEMu3XQIg5ek0zIS+wwRDJZpBVjtumd/f4MPjC8Cgk6oeghKYL33mGcZO9tuDOe6Ztt3Q+v4DrJ/q7CFbis3CL3VHN7MXnwntxt5Bb1kHxrAoYPHf9E7LYJxAV+2DBD8lWdhIuwwsr9KvxTyiX5yoYI8fd5BdF1aKKaWXlNAAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHcAAAAaCAYAAACNU8MOAAAEvUlEQVR4Xu2ZV6gkRRSGj2GNK2LOouwaMWd88bL6ICoiRgz4YAYjCor5mnYNu+YcWTGHBwOKGFgREwbEACIiiorpQUUMqKj/t6fr9unanrnTc92F1frgZ7pP9dyZqVN1Ql2zQuE/xBTpbull6X7pFul26Vnp0fDceCwh3SC9JL0gHR7GTpRek56RNgr2QdlVelh6W7rN/PvxulN8qNDONtLf0mrBtq30argflHulNzPbwdI50rKZvQsnSO+H+5Wln6WRYCu0cKo1J27V6nVWsE0N15Hcvqf5Qtmgut9eOq8eHmNxab3cKNY1jwI5D0jXhftJ0q/SycHWCVbvJ9LXlV5pDs8DPyw9+4X5Kp7fLCc9ZP55j0gPSt+af1cc9pF0obR+ekMLj0vXV9dbm4dRSA5K9kukRYLtfGm7cA9M+nfmDsVROCS+J4HtMmnzYNu4si0abImvpH2r68WkUektaZn0wLDMlj6T/jBfcW0Qcp42X7WPWfsXnJ9cab4TVjRf5WlCcewe5jnqmMoW4Xt+b54nWYw4ZqvGEzU4Mk3+BdIOzeExbpQ+lu6Qls7GIvwdosMW0ibSTHPH5eD0v6RLK30gnWW9fdGJd6QrzB3XawfMkM42f+bYbKwLG5pPYtI6zeGe8KPZaeTNPHwxEcCkrxHGgOgU8y27v9/CxKHk1J3zgQA7jHwYc3gv+CwWHmpzLBwnvRvu+X1soAlD/nlROsJ8EqjccihIzjX/UJ7BQV2YLF1jXsDcKV1rvqIvlw4Jz/VjurlzVzf/WxGqYTjUvLiJnGa+ExI4uxdEAxYxc8Fiagu3MGpebQ8CYfkq84iwZTaWINXEBct3JjJMmP3NQ9s0c8cd1Ryeu9oIZ0tK70lfNofHBYfQJpxi/jeG5WKrnXt1NnZf9cqCyUPpk+YtzCCwgNL7Cd15Dk6wGaiOx2Mz83TCHKaFQ4iOYKeG2C/YqDHeqK6Haa3GYMXgWMIxzuUHRU4yL8dXMc8LXYoofhSFz475wBBcZO3OZecTVY6X7gl28hg97Y/mi4t8148DbN5dzU47KLunByUkPyftFsZyqIhHrZkCcCSLYqnqfnfz+uF385477ezTzWugI82j0dCQXygKSN5/mjf6ibWtDoHscJx/dD08LuQmcs2/QXQuEYQi8HnpF/PDA+qAXjltYYTUx84fGhplQkyC1cIqT+CYlaprWonY3w0CoXREWrOPaHUGITr3JvPdyoLbRzojPFeoYHKYtMQc6Zvqml13WD00t6fsmm/ZXVR9RINeIpwOQp5ziTRPSctLt0qb1o8WgEIj5o27zHcnOwrHJKiosXfJt8AhwN65cUgodqZaM+fSSrGLVzDvwVMuK5j3VvEEhFMXnMhEceCeOLCytx0S9ANnfGgTq5ITtCbJubEVop0akXYxb7EKYi/pc2uecxKGceKZwQacxGCnAu0KC4Z2YFI+0BHanLXM64Sbg51ikMXIK2fItFz/Wyj3yZ1Umb9JP5nn3jT2utWOIJd9avWz9GP8a6oLqfxnB/NvMpzDgmrrH9sgp9Lkc4TI6RKf/4N560B7BiPmhSH9Id91tLIXFhCEVI4vnzA/551j7hBshUKhUCgUCoVCoVAoFAoN/gG0KOfFr+eqiwAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAaCAYAAAC+aNwHAAAA30lEQVR4Xu2SzQoBURiGP7/52SllZ2ODhQXZiztwCXZSNnIxNjZWspLCHbgGio0SKUks8U7fSZ+jM6NZn6eeZr6feU/NDJFFpwHXf5pRz3wRgAm4hC9Yh1EYgTGYhQP4VLWRI7zCkD4AKXjQm5IC8ekzrR9X1zBcyYFOmzigJ3olOFT3TlBXzH4YEwdUVO28kylsfTY8OBEHbJU3Vefkkoki8fIcBom/QBPu5ZIbHeKAvujl4UjUrkyIA6qil4RpURtxfqIzmb+/J2Xi0xf6wIsa3MALfMA73JGPIIvFN2++SC9CnIFfXgAAAABJRU5ErkJggg==>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAAAzUlEQVR4Xu3SvwqBURiA8bcYlKTYlSuQVVnYuAGDmSwmuxuwmVyEEgaz0cggf7MYTAwyGPDUOel8J3G+yfI99Svf+55OZyAS9KkC9toaW6wQMQ/RHAdsRJ0tera6Np4Y2wtdCRd0kLZ271J44IqotYtjhqw1/9hU1GsqxiyMCcrG7Gt1UZcMjVkPTeP7Z0nctQRa6HpOODYS9ZqB/h3yrt2qirpkgZi1c64m6pKGvfDTESd76KeMqFf07YVLeSxxxk3UH26HnHkoKOjvvQDegCivxbB6WQAAAABJRU5ErkJggg==>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAaCAYAAAC+aNwHAAABEUlEQVR4Xu2SvUoDQRRGL+YpYhIstU2aoJ0gaKPYWMVaW63t0qTwEYwWBn8aQQSFlOYB0lqIikUwVRQEERXiGe6sXG824gPsgVPM990ddmZXJMMzh3f4hH3sxfUj3uABVn+m/+AUhzgb1zmcwhP8wuWYj+UeX0QftMyIbtxx+S+KokMXvoB50e7WF5aa6NC2L6Ap2q35wrInOlQ22SQe4TNumDyV8HqfeBXt4jseY97MpZKc/9xk4SJbOMBpk6eyLunnX4r5jstH2BcdrLh8K+Z1l4/wIPr9J1x+JrpB2Ggs4Xxh6NIXcC3abcb1IRaSMvzb4ebDJb3hq+i/v5gMwAp+YBsbuGu6f1PCVVzwRUbGNypsPH8K76cQAAAAAElFTkSuQmCC>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADQAAAAaCAYAAAD43n+tAAAClElEQVR4Xu2XyauPURjHv+YMZVaGchGJSPgDTGWBFGKDMl2SrJTMZVwoMm0IWUiRBRvKhkTEwpSyMYQyrCRDEb5fzzn3fc65v3tt9N538fvUp855nvdX533POc85P6BOnTr/k0n0OX0XvJ2mmzELxbNv6Nk0XR3O0Ff0B+2Y5SLd6RX6m16i7dN0tXhA98MGOyzLRfbRLbBnVme5SjGA3qDLYYOdnqb/MpFuo0dgz4xK09ViAd1Jp8EGuzJNowNsr3Shj+nbNF099NX1MlpqeqE9aRrr6RTan/5ChQtB5D7tCisGP+k5lxtCD4W2ZlIvvKpI16RTHiiTfrD9E1Glu+P6J2jf0D4Ke6GRRTpBL3Ie9vuxWa409NV3uf51+j6059HFRQpP0Pr+WQZbrofp4CxXGsfoDNc/DZuFQbCzKaJKqHhr++ca7AO1KY9oN9ffDhu4DtARLr4wxBtdLKIleJB+gu2/RWm6iV50I13qYmr3cP2IZlsrZxzdTGem6drMpq9pZxfTEtPAN7mYOBnio7N4RC//GfZxVOZroXNsDOzaJHrSL7DjwKPr2Fz6FLZ8NeuXkycy9APtha/0O2wgcakodxdFpTpOX6J49gO9EHIe3fFu5cGMyXQNrHCIOfRmkW5iPO1Nv8FmdSCseJXKVth59i+u0iWhfYDudjmPbiv38mCZXISt+5ypSIuOltvw0H7ocjrUV4S20M1Fd8s24wVsf+RoFp65vi64OqgV1xLWgS7mw/bT0NBXUdLtpXT6wA5e/adqCQ1eNMCKh4qB30uRDbDjQuivSum0ox/pDthgaqFZi0vxFF0Lq5S6TTSEuFAR2uv6bYb+cuhrt1SqJ6ComDqc9T9qHZpXLeXicqtTp8r8AdlceMZAUk4iAAAAAElFTkSuQmCC>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAbCAYAAABIpm7EAAAAz0lEQVR4Xu2SMQuBQRyHb5IoFjYM8gXMkpTZbmOSzS4lk4+BD0Ah8RHsTArZfACLFM/bvYP733tvGZWnnuF+v/tf13VK/SRFTMswiATucIp3zJu1zQgP2MMXls3a5oxjzGHFrGyySp/alYUkigVsKz3Q9Nexjz0GNdzgRemBrb8ufewJZIZXGYZxwoUMXSSVvs5A5E6+HvDe3Buoy8KF9/beQEYWLiZ4k2EYe5zL0EUcn9iShaSDa6ziA1NmbXPEldK/c2hWwTRwiX2MiO7PGzmKJHD+O5j/AAAAAElFTkSuQmCC>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAaCAYAAACzdqxAAAABV0lEQVR4Xu2UvS8EQRjGn/gMSkchmosQNf+AHB2VyFUq8dHpRSiIKFTiNEREIQqVSusaIVEIaiFI0EpEQvC8985kZvZ2k9Wo9pf8kp33mZmbfXf3gIz/pp/e0mfjaRhXMQw395Huh3E1e/SeftK6SGZpocf0hx7RmjCO55KuQRflI5lllc5D58xEsljaaZlOQBcNhnGFPrpAN6BzesI4njG6RAvQRZNhjFpoLxvpNX0K42TkFLKptEA2XgljzNIB2ka/keKBWS5oE/ShfdEDL+uk6+Za7kx+eMrFyeSg/bXIm3Hmjbdpq7kuQTfudnEycoplb3xCX8z1KB13EW7wh/5u0iFvvAs9VQf03bbImyP11P29os3eeBG6gXwIXV69aOrTXi2REfpAG7ya3LpsMOfVhB1T743UA+T/QXr1Tj/oG7TXNjun9Wa8Re/g5r7SQ5NlZGSk5RfvEEdmU//r2gAAAABJRU5ErkJggg==>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEEAAAAaCAYAAADovjFxAAADP0lEQVR4Xu2XSchOURjH/+apkAUZ8hUbYyxEQkrKtJBkyLBAQshUFrIwFRlXFiJlI1IiMsdCSoYyJHO9ylymyDz9/z33fu/5nt5z3yurr+6v/ov3+Z9z7rn3O89zng8oKCjIyXRqkA/WE3pTw6i2ye8WVOeynY9u1A/qDtXQeTEWUCXqZaKn1ONET6jL1CKqaTI+5QZs3kPqUaLh4QByCLZeCbbW3DpuGc07Tu2j9lJvqeXUMWpsMC4Xu6kv1B9qkvOqoQ/wnmoexLpS26lPsE02DjwxD/asw1QD5wmNv0Ltono6L2Uo9YLqFcR0Au5Tv6g2Qbwq2vBdajZsYzdReWOV0FzNOeqNhHUwf5aLK+0UP+HiKQOocz4YoNP6nFrsDbKBuuaD1dhJzaEawY6mNje+zog4M2Djl3kjoQ/MP+/iHZP4bRcXesFLVA9vBAyEzR/nDTKR2uKDWXSi7lFNkt/6GFr8au2IbJRGGt/fGwnNqN+w3A7RSftGfXBxsZBa74MOpayee5Jq7TwVxBoXy2QHLD9T9DFKsAeMDuIxVNxUjGLFND0J+tAeFVB5Ye7qhFxH3fpSiXbUT9j8z9QZaiXVPhyUB01QEfHVW1Vfi+tIZqEvrnFHvBEwBfHcvwDz+gaxA9So4HcWI2E3iNZI9Qz/eDVugl1hHh3hdPERzgtJ68FSbwTsh43xhVHoWpOXXmV6eX2Ef0F1bDC1GuU9671yoeP0APFjtwS2oC9oIXtgY2L1QNfVR+oN1dJ5Qnmv+fNh+1AaKB2qoRSrlH66SrXeQW/EWAtrKmLoBV7BFh3ivBTldFY9SK/H2E2jBkj+Rti1poKYh1uIP/MrtcIHK6FqqlPQyhsOFRptUhXYUwPzYv3BGFjhWuPiITr+WkN3+kXEXyykA2zd7t4gE6jvyL5aa1kF6/LUjJyFVdbT1CknbUyblNS8hKQdnz9N2sA22NU31XkejdUaatf7OS/GZNgctcghXWANn1KrKip6r1F+ubxSLy/UoamX18YVf5f8LsEqs7pNfWR1ktVQyqmH2OyNDNTYqfCpFS/B+pStsNT0f5B6w0zEi3Mlwv9yVZCnwRon/XELCgoKCgoKCv6Lv1HZyXxHgFvIAAAAAElFTkSuQmCC>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE0AAAAaCAYAAADygtH/AAAD2klEQVR4Xu2XachXRRTGH5UyTaUSl9xezA9FYW5hLh/UTMzIBUQkNAQ1RRRbCEGFTHEXjT5UlBq4lRhBBrlGbrigYvghUis3jLTCBMV9e5733PE///P+195KhfuDB+49Z+bMvXNnzpwLpKSk3KcMo573xnuYR6nJ3vh/8gR1jfqRqul8/5QR1EnqV+pn6hfqq6wWQBfqN+oEdQw2fql8RF1H/uftBhv7d+o0bBzda6yfqM9QzUWymLpE3aKGOF91qAebLMVt53yBgbAXeZWq43z5aE/dgMVt5Hye1bB2XZP7WlQF9QVs0vsn9rJoBZv5kbDgB6kaWS2qx3pY3M7ekfA11dMbi7AFmY/xjPN5jlLnYJMV8xSs/3ZnL4kPqVGwoOFB9PX/LT6BxRzsHWQAtcwbi6AV+QH1KSxur2x3Fi1gbb7xDlg/+ZQ6yqIZdYh6ILnX5CnQvjstcqM80pvqhMyqfBqWGz1TYDHfcvaHqQMovr1iQp9HqJmwuEOzWmSjwy3X2GIJzFd2OnqfGhvda/KOw4K9FNlj9PV2UXOojdRKagX1LiyRa/XEvAaLp7Fi5lOvO1sxZsE+rHgTFndixl0F5Wq16RDZtFBWUX9TYyJ7STSmDlMPOvs42EA7nT2wjWqdXPeBtZ1NvZxca/JieiT2+ORsC4tTTu5sA8s/oU/4GFpx+dDWU1WwLpFW6WXqc+rxqF3JzKUmeCOpTZ2CPdALzlcB+8KB8bB2eqEm1Nuw+ilGE6w2e5N7vfRW2MSVgw6M+DAJH0m5LRchn6lfQHlbu+Is9WRkL4nHqCPUQ96R8AZswO+9w7EGVi4UQlte5YFqJaEtqa1ZDv2oK8jUc5LqLz3j2qhdzHCY3+czpR3Zpzp7UabDVkU+VC+dgQXv7nwBrZg/qeXekQMVljdh5Y22SN1sd0GUPvZTTZ09rKQ9zh5YCvN3dPaQC2c4e0EawFaZTqJCTIIFV50VaE59DKuN9DDyj47882Av49kNa6sD5BXnK4Z+ld7xRtguUUytulzIrvrM/zEot6pfnGaKohJAW+U7ajO1CXYKbnDaAQsuPVfZE5gGS6zPUgsTn7aOUJtFybUnVOVfekcB9LKq7S5Q9Z1PaNvrL0byE6N8pfG+dXahA0i+UDVop2gx5EVJ/g9kJqNUhZfV/5weRP992t7vUT/A/uNUeuRbvTp09NV13JeCfnm09TUhV2HPrB0S0Ph/JX6dhmqrE1z/kjoxlegvUudhebCvdatEJZFiaqGobFoQ+f4zdAIpNwUaouqJ6VHhmy833g1aUoOoF70jJSUlJSUlJSXl/uA21nfpKB9XAXsAAAAASUVORK5CYII=>

[image22]: <data:image/png;base64,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>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB0AAAAaCAYAAABLlle3AAAB4klEQVR4Xu2VzStnURjHv17GS2ZihbwsbQwRCkkmK5lSNuyUJoqymAWxmdQsiST+ATYzsxmNnaZZYGyEjQWSYmE0i4mFtzJ8H8898zv3nN+vqCkL91OfHM9z7jnnnvuc8wMinogk2kiraEYQK6CZ/3r8Z97R73SaLtJftJPu0VdWvwW6+wCXzQOJGKJrNMeKldC/dN2KCSn0Db2lP6C78AK6M9nQXfpJN4P+cXlNb2i5myArdNwNkn7opMNuIqCNfnWDNvKWMsBLNwHd6rdukHyGPlNrxQppUdBuoFNWzmMGOsBHmuzk7IKyOaFnNNWKTdCmoF1JW62ch2yFTCr+pp9oN023O1mUQvtKoRRDP0svdBGJnvGQY/KeXiA2ubiE8JsYzPfcgX5zKZgraFE9mizolkzSS+jALaEeyhdorsaKjdIP1v/5Vtujwg0E9EEHlr82sivyCU6hR8cwQuuCdhpdhV8f9+RBL4N41EMnrXbiZUFcLo9E9EAXEZcOuo/wig1S7gfwVzsAnXTQiRvkRQ5prpswzEIH6HLicsb+QI+Lyzf451OQG6mdHtM5JxdiA7rybWgFjtF5ugW/gKR45C42lS1t2QnxiJ5Db7VrhAvMw6xWPrz8ssjZbI6lIyIinht3cehl3udRjmQAAAAASUVORK5CYII=>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAZCAYAAABHLbxYAAAB5klEQVR4Xu2VTSimURTHjygrNhJpNEnJV0kZscDGRzaUhTI7zGpWs5DykYWSaIoS2WBhQ77K19SkJivKlg0zxkdJFkL2/E/nXu9zTy/P+zE20/OrX73PPfd9znnuPc99iAICAlJhG+yFhSqmSYab8KMOvDdN8C9sh3XwDyxzZriMwCdYoAOWFJKn+ZeUwFuYa65rSIoYe5nhUg4fyadQvukOHIBpKhYLSfACLnrGeDFGYalnzMKLtAu/k0+hTAJshr/gOMx2w1HBD84Jv5Hcl3su0ZnhMgQ/w26KoFAvtfAHnIX5KhYJnSQJB+E2nIM38Kt3koFXeMX8jrpQC/fNKlyGn1TsLaZIEh5TqPftKrfaSSQtwjuYZa5jLtRSBOfhFqxWsXAskSTsV+PX8MBz3UdyIljiLpThnl0jSeR3QkySJOS+8/LbjKeTFLPuhuMrNA/OwJ+wXsVeo4skYYsaPzHjmST9eg7P4Knx3sQv4b78xR9u8gWSVaxUMT/4BeSEX9T4FTwiOQnCMUFRrGgV3CDpyWIViwY+l7mnLbwzXESjZ0wzTTKHX7xXaSDZXu6vHBWLBd7eQ5Id4YOcV7PHmRGCe5k/r3fwgeSLtufMMFTAYZihA3HCW8zf+A74QcUCAgIC/geeATF4XwxErrpHAAAAAElFTkSuQmCC>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAZCAYAAADJ9/UkAAACNklEQVR4Xu2VTYiOURTH/z6LJsnC19SIBokkWRiGhpQis/NZ05SVhZJJLCRFpljJxkzKDA0lUhSZaUYWomRsLEyZBWJhFrORJqX4/59zn5lzz7yys/H+6lfvPc+5H899zr0vUOV/ZQk9RjfTGrqU7qMtPimxjB6l7XR3eFYyle6hF+hxuih/nLON/gp+oRt9EizvI2yh2+lTeifLAGbSe/QR3UpPwsZq8EmeJvqZvqIP6Wm60CeQabCcEy42j36jrS52hH6ls11MO/CeTnexcbTC7hgMNMN2ZH2IP6f9rv0G9gKeHbC+jSFesAV/n/wybADVg0cT/YC91VxYzo0swxas+JkQL9CKHtArdIAOwhbkuQUbIBbP3RRfQJen351ZBrA6xa+GeIGKYZRuSO2VdAT27Ut6MTGJRwWn+CrYOJUm0TPFY3EWzIIdN08X/UnrU/sJbIBYiOXkK2CnQ787soyJyW+H+B9RharD4dTuSe3a8QxDx0pxVb4Wqt/XsgxgTYrrs05CFfsadjmUnIN10IUiLqa23sLTR7/TKbALSrsVt3cTrO+pEC866RIYQn4OtXXqoFtPNKX2zjIhoX73XfsZfena4gCs79oQL7hEd7m2jswnWJGV6JJ5CztyJfrOY7BzXLIfthOLXewmbFEVURHpiHXTs7BJHtP5LkfU0Q/0Om2jw/SgT0icp+9g17Bq5QWdk2VUQOf0EF0XHzj0aXSk9mLymffohfTnpNwZ4VmVKlX+Hb8Bd2F12ZkQTKQAAAAASUVORK5CYII=>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAACT0lEQVR4Xu2VTYhOURjH/8OMYfKVEGYjUUTyUcZXFhNDTUoUolAkKzOzMSOZjSxkxQZJMjONlPKVpJTJhGwUEUKvjXwspCZf+fw/73PuvM993nPfnd391a/u+Z9z7z33nnOfC+Tk/D+G0LX0MG2jk9PdFRlF19NDdCWtSXcXaadr6EQ6PhxLlskwepFepyvoPvqWLrGDMhhH+6EP0wCd2HM6xoypon+d3+kuM6aMPfQDrTOZ3OQlrTZZjG661WVH6RmXfYVO/jY9Quenu8t5SK+6TJZBnmi5yz2v6AGXraNPXVZw7YqMhd78nMsXhPygyz2X6ADdbrIu2mnawmvXrsgM6M1PuXx2yE+43NNEf0DH3qTHoEsq+9TyhrbSW/Qx3Z3qdchmjt18VsgvuDzGJpQ28G+6N91d5BvdGY7l47hDryFjzy6GXuyky5NJ9brcM48+g5aEsyhNbr8dRGa6tiy3jNvh8iLToZ2nXT4n5MddbhlBP9LVJpNjKSd/aL3JpSxYVkGvL/uvjJH0F8qXaSn0pEoFbgviG7gReq68PUHKi0x+2uCI0hipj1H66H2XbYaeNNdkE6BvNkE+/dikhE90WTg+D/1C7RIm1/flZBDZqF/oFJPJa+0zbaFAf9KpoS1v+TPdkAwIyO/qEUpfYDO0YCbIUl6h76CbPhP5PciGbaE99B4dnRqhm/4JdDIJUpnf07u0A/owD6ClJmEotA5ehr6ZG/QFXWjGZDKJboSWidhPNYtauohugy5Z9DOH/ohl2eQvMdz15eTk5MT4B8G1eJhV8hZpAAAAAElFTkSuQmCC>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAACrElEQVR4Xu2WWaiNURiGX2OmzESmnamUkiFluDjKTCh0zIoLkZBMkSKiXBARhWzDvWQoGUIyhFIulJJwpciYK9P79q219/cve+9zbuhc7Keezv+ttfbe37+Gbx2gSsOhG22cNiZ0TBv+JU3oaXqJXqTzst0FhtBHtFnakdKU1tCdtJa2y/Qai+kc2pe2pmPoOtrbjZlPn4TnLvQjvQD7zv50BN1DP9MpYVxZGtEz9BQdR5fRV3SkH0Ru09+JR2lzNyZPD7r4LB1MJ9LtdCXdSk+6MWVZTo8nbdPoc2Sn+ha9Rx/AEprp+iJ6oV0u3k1Hu1grcT/8rZMT9FrS1h42I1qOyE2ac3EplPR+Fx9BNgnN1GQXV2QtLIl9tEVo03IqEc8N1J2YkrocnjXb+WIXpqKeSxjpQd/CkntBt8CWTO2e63QVvUof00O0ZWYE0IY+pRtgp3NpaNcKaDbrtYSefvQrips6Dzt5HiWkN9ZM6BQfgO3DnBsjWtHZsFMbUZKTwrM+uwg2AV0LI0rQgd6lG+km+h2W3BVYXYoMRLZo9kHxJSoxA9nDpSRVAXTA7qBCIVYh3OviAbCTox9VXYqorHg0cxrzJmn3qLo/pG1D3Jn+QHFJV9Ph4TlDT/qL9kratSe+wPaRmE4/0bmFETabSuy9a0s5Rye4WDeBimtkKN3s4gJ6o5/4OzFxnm4Lzytg45YUu9EdllhaaiKz6LGkTUX2nYt1ixx2cQaVBVVrv1Q5+hp2KIReQOXCF9z1sGTHurZIJ9h20Cn1KNlvLh4Pu+ZKoh/Vl7yE3ZVavmewuuNZA6v+O2BF+QNd6Po9WsKatBH2WypNuneFVqXifxmarUF0Aexei5s1RQVY+00XcLkvHIVs9U8ZBjuNqot62f9KeoJLUbZMVKlSpaHxB/pVe6G7G2r3AAAAAElFTkSuQmCC>