# DYNASTY GENIUS — STRATEGIC ROADMAP & PRODUCT VISION

This document establishes the strategic roadmap and product vision for Dynasty Genius. It outlines the core product thesis, translates quantitative and qualitative theories into concrete feature specs, and defines the visual and technical guidelines for implementation.

## 1. The Core Analytical Thesis: The "Rational Anchor"

In highly competitive dynasty leagues, generic trade calculators fail because they treat player values as absolute, stable truths. KeepTradeCut (KTC) and FantasyCalc are not maps of objective player quality; they are liquid charts of emotional market sentiment—prone to severe recency bias, rookie hype, and narrative fatigue.

Our backtesting (G3 ECR validation) suggests that our quantitative model (Engine B) is statistically tied with rational expert consensus (ECR). This is not a limitation—it is our rational anchor.

The structural edge does not come from trying to out-predict the sharpest minds in the industry. It comes from:
1. Identifying emotional divergence: Detecting when the emotional trade market has drifted dangerously far from our rational utilization baseline.
2. Contextualizing valuation: Translating those rational baselines into David's exact league context (roster limits, starter requirements, and championship posture).

```
    graph TD
        A[Sleeper / NFL Usage Data] --> B(Engine B Utilization Model)
        C[Expert Consensus ECR] --> D(Rational Anchor Baseline)
        B --> D
        E[KeepTradeCut / FantasyCalc] --> F(Emotional Market Price)
        D & F --> G{Divergence Radar}
        G -->|Anomaly Spike| H[Trade Target Heatmap]
        G -->|Post-Trade Roster Capacity| I[Trade Lab Reconciler]
        I -->|David's Posture: Contender/Rebuilder| J[Decision: Win David's League]
```

## 2. Four Lenses of the Product PM

To execute this vision, the system must evaluate every feature through four distinct lenses:

- **NFL Scout**: Raw talent priors & utilization reality. Weights draft capital and entry age for rookies; tracks route participation, target shares, and weighted opportunities for active players.
- **Data Scientist**: Strict model integrity & leak prevention. Guarantees that emotional market data (KTC/ADP) is strictly kept out of Engine A/B training rows. The model remains a cold, mathematical baseline.
- **UI/UX Designer**: "System 2" cognitive bias protection. Enforces slate styling, separates model vs. market lanes, displays raw confidence intervals where a validation interval exists (otherwise label interval unavailable), and prevents visual overclaims.
- **Advanced Analyst**: League-context translation. Interprets base xVAR/DVS through starter expectancy, roster cuts, and championship posture.

## 3. Workstream B: The Emotional Divergence Radar (Surface 5)

Rather than rendering action instructions—which promote lazy "System 1" thinking—the Divergence Radar highlights statistical anomalies where market price has drifted from utilization reality.

### A. The Divergence Formula

The system computes the percentile difference between the rational model anchor and the emotional market value:

  Divergence Delta = Model/ECR Percentile - Market (KTC) Percentile

* **Market Below Model Anchor**: High utilization (e.g., constant 85% route participation, 22% target share) but depressed market price due to narrative fatigue, a scoreless streak, or a poor team environment. Internal hypothesis: investigate acquisition-side opportunities, not an active recommendation.
* **Market Above Model Anchor**: Low utilization (e.g., touchdown-dependent production on a 35% snap share) but inflated market price due to temporary highlight-reel hype. Internal hypothesis: investigate trade-away-side opportunities, not an active recommendation.

### B. UI/UX Specifications

* **Divergence Heatmap**: A visual table ranking players in David's league by the magnitude of their Divergence Delta.
* **Hype-vs-Utilization Chart**: On the player detail page, plot the player's KTC price trend against their route participation % and weighted opportunity share over time.
* **Neutral Anomaly Labels**: Replace action terminology with descriptive status text:
  * "Market below model anchor" (Amber market line sits below Blue model line).
  * "Market above model anchor" (Amber market line sits above Blue model line).
  * "Aligned" (Value is within the normal ±0.25σ noise band).

## 4. Workstream C: Contextualization & Scenario Overlays

### A. Roster Capacity Cost (Forced-Cut Penalty)

Trades do not happen in a vacuum. Receiving three depth pieces for one star forces David to drop two players to meet roster limits. Standard calculators count this as a net gain; Dynasty Genius counts the lost value.

* **Formula**:
  Adjusted Received Value = Raw Received Value - Forced-Cut Penalty (DVS/xVAR of candidates dropped)

* **Implementation**: The Trade Lab UI must explicitly show the forced-cut candidates and subtract their cumulative value from the trade balance. If the transaction results in roster overflow, the system triggers a mandatory warning displaying the adjusted value.

### B. Posture-Aware Scenario Analysis

David's championship posture (Contender, Neutral, Rebuilder) determines how he should discount future value against immediate points. Crucially, these discounts are layered context overlays in the Trade Lab—they never mutate the raw model outputs or pollute training data.

```
  Trade Lab Valuation Lanes
  ├─ [Model Lane (Blue)]   --> Base, posture-neutral DVS/xVAR (Raw production value)
  └─ [Scenario Overlay]    --> Applies posture-specific discount curves:
                               ├─ Contender: applies a near-term roster-context discount to future pick liquidity; inflates near-term PPG
                               └─ Rebuilder: Appreciates young developmental assets and future pick liquidity, while applying position-specific continuous aging curve alerts to older assets.
```

## 5. Workstream D: Structured Qualitative Registry (The 35% Layer)

Qualitative adjustments are restricted to highly credible, structured expert sources (e.g., Harstad, Cummings, Hribar, Jahnke). They are kept strictly out of the quantitative model equations until out-of-sample backtesting validates their predictive lift.

We establish three flat-file registries (.json or .jsonl formats) to catalog qualitative facts:
1. **Coaching & Scheme Registry**: Tracks offensive coordinator changes, pace of play, pass rate over expectation (PROE), and personnel usage (e.g., 11-personnel rates). Used to flag players whose past production profile is structurally misaligned with their new offensive environment.
2. **Medical & Injury Recovery Registry**: Curates recovery timelines by injury type. Renders injury context and recovery caveats on player details; no numeric adjustment of baseline expectations is applied unless validated.
3. **Beat-Reporter Hype Filter**: Logs camp narrative sources and applies a time-decay factor. If a player's draft profile sits in the 20th percentile but beat reporters claim they are "dominating camp," the system flags a "Beat Hype Caveat" to warn David.

* **UI Visualization**: Rendered strictly as Evidence Cards / Caveats in the sidebar of the player detail panel. They act as qualitative context warnings alongside the quantitative projections.

## 6. System 2 UI/UX Design System Guidelines

To combat FOMO and emotional decision-making, the frontend must strictly adhere to these design mandates:
1. **Neutral Slate Styling**: The visual theme must use a low-chroma, premium dark slate palette. Banned: Green/Red color coding, checkmark icons, and success-colored banners for trades or players. All visual labels must remain neutral.
2. **Lane Isolation**: Keep Model predictions (Blue) and Market sentiment (Amber) in physically separate visual lanes. Never blend or average them into a single score.
3. **Honest Uncertainty Disclosure**: Always render raw confidence intervals (BCa bootstrap CI95) with equal visual weight next to any point estimate where a validation interval exists; otherwise label interval unavailable. If a trend or delta crosses zero, it must be explicitly labeled "(inc. 0)" to highlight that the signal is statistically indistinguishable from noise.
4. **Degradation Banners**: If key data is missing or stale (e.g., cold market feeds or incomplete player records), the UI must show a non-dismissible warning: "Trust data degraded - [specific reason]".

## 7. Out-of-Sample Emotional Market Backtesting (Workstream E)

Before any divergence or posture feature is promoted to "decision-supported" status, it must undergo rigorous out-of-sample backtesting.

* **Data Sourcing**: We must continuously run the daily FantasyCalc snapshot scheduler (snapshot_fantasycalc.py) to build a point-in-time database of market values.
* **The ROI Validation Test**:
  * Do players flagged with high positive Divergence Deltas ("market below model anchor") systematically outperform their KTC price over a 1-year and 2-year horizon?
  * Do players flagged with negative Divergence Deltas systematically decline in trade value?
  * Does factoring in the Forced-Cut Penalty result in better long-term roster strength compared to raw market-trade values?
* **Promotion Gate**: Features remain marked `decision_supported = False` unless a future cockpit-cleared validation spec defines and passes promotion gates.

## 8. Development Phases & Execution Order

We will build these features in five discrete, sequential stages:
1. **Phase A: Model Trust Console (Tasks 1–10)**
   * *Status*: Active (T4 committed; T5 committed at fd14e1e).
   * *Goal*: Complete the current trust surface, wire type-safe backend DTOs, and establish the baseline System 2 visual layout.
2. **Phase B: Emotional Divergence Radar v1**
   * *Goal*: Build the read-only divergence heatmap and utilization trend charts.
3. **Phase C: Posture-Aware Trade Lab Overlays**
   * *Goal*: Integrate the forced-cut penalty visualization and Contender/Rebuilder scenario discount toggles.
4. **Phase D: Structured Qualitative Registry**
   * *Goal*: Establish flat-file schemas for coaching, injury, and narrative tracking, rendering them as evidence caveats.
5. **Phase E: Emotional Market Backtesting**
   * *Goal*: Run out-of-sample evaluations once enough historical snapshot data accumulates to prove the divergence edge.
