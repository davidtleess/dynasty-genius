# **Dynasty Genius: Product UI Architecture & Design System**

## **1\. Product Philosophy: The "Honest Terminal"**

The UI must function as a **decision-support laboratory**, not a verdict engine. Where competitors offer "Buy/Sell" heatmaps, Dynasty Genius offers "Divergence Discovery."

* **Evidence-First Layout:** No "top-line score" without immediate visibility into the underlying drivers (Draft Capital, Model Confidence, Variance).  
* **The Second Lane:** Market price (FantasyCalc) is treated as an *independent variable*. It is never used to "correct" the model; rather, the gap between the two is the primary insight.  
* **State-Aware Surfaces:** Any surface drawing from incomplete data or experimental models is visually "de-saturated" to signal lower reliability.

## **2\. Visual Design Language: "Neutral Analytical"**

A principled palette ensures that "Red/Green" binary thinking (Win/Loss) is replaced by "Confidence/Divergence" analysis.

## **Color & Typography**

| Token \[1\] | Value / Strategy | Rationale |
| :---- | :---- | :---- |
| **Model Lane** | Indigo (\#4F46E5) | Reserved for proprietary "Genius" valuations; signals intelligence. |
| **Market Lane** | Sage (\#10B981) | Reserved for external price data (FantasyCalc); signals "The Street." |
| **Divergence** | Gold (\#F59E0B) | High-contrast but neutral. Used for gaps where Model \> Market. |
| **Uncertainty** | Gradients / Opacity | Darker color \= Higher Probability; Lighter/Blurry \= High Variance. |
| **Typeface** | Mono-spaced / Grotesque | High legibility for dense tables (e.g., JetBrains Mono or Inter). |

## **Component Inventory**

* **The Decision Card:** A structured block containing the base signal, the **Mandatory Counter-Argument**, and a confidence band.  
* **Divergence Rows:** A split-table row showing Model Value on the left, Market Price on the right, and a "Divergence Delta" sparkline in the center.  
* **Caveat Chips:** Small, non-dismissible tags (e.g., \! Low Sample, ? Missing ADP) that float near player names.  
* **Aging Fan Charts:** Visualizing the 3–7 year trajectory with shaded regions showing potential outcomes. \[2, 3\]

[12 Financial Dashboard Examples & Templates](https://www.qlik.com/us/dashboard-examples/financial-dashboards)[7+ Best Stock Market Dashboard Templates for 2026 | TailAdmin7+ Best Stock Market Dashboard Templates for 2026 | TailAdmin](https://tailadmin.com/blog/stock-market-dashboard-templates)

## **3\. Information Architecture: The "Decision Hub"**

The app shell unifies seven distinct surfaces through a persistent **League Context Bar**.

## **Primary Navigation Model**

* **Global Sidebar:** Surfaces (Rookie Board, Trade Lab, etc.) \+ Settings.  
* **League Header (The Context):** Always visible. Shows your current Roster Health (e.g., "Contender" vs. "Rebuilder"), available Draft Picks, and League Scoring rules.  
* **The "Contextual Flyout":** Clicking any player opens a persistent right-side panel with their full profile, aging curve, and market history, allowing you to research without leaving the active decision surface (e.g., comparing players while in the Trade Lab).

## **Page Inventory & Flow**

1. **Rookie Board:** Multi-pane view comparing ADP vs. Model Tier.  
2. **Trade Lab:** A "two-pane" drafting table where assets are dragged to Evaluate.  
3. **Backtest Surface:** A "Credibility Layer" showing historical model hits/misses vs. market price to earn user trust over time.

## **4\. Decision-UX: Uncertainty as a Feature**

Following "Be Right, Not Fast," we replace verdict language with **probability distributions**.

## **The "Divergence Insight" View**

Instead of a "Win Trade" verdict, the UI presents:

* **Value Ranges:** Shaded bands representing the 25th to 75th percentile outcomes.  
* **The Strongest Counter-Argument:** A hard-coded section for each model signal. (e.g., "The model loves this trade on 3-year value, but it leaves you with 0 startable RBs for 2026.")  
* **Hypothetical Outcome Plots (HOPs):** Animated or togglable "scenarios" showing "If the player hits their ceiling" vs. "If they fall to their floor". \[2, 4\]

## **Banned vs. Recommended Language**

| Banned (False Certainty) | Recommended (Decision Support) |
| :---- | :---- |
| "Accept this trade" | "Value Surplus: \+14% over Market" |
| "Bust Prospect" | "High Variance (Bottom 10th Percentile Floor)" |
| "Sell Now" | "Aging Curve: Projected Value Decay in 18 months" |

[How to Visualize Uncertainty: 5 Techniques That Work \- YouTube](https://www.youtube.com/watch?v=yxzKv6TKtdY)[Uncertainty Visualization](https://bleu-azur-consulting.eu/2020/05/03/uncertainty-visualization/)[Fundamentals of Data Visualization](https://clauswilke.com/dataviz/visualizing-uncertainty.html)

## **5\. Tech Stack Recommendation: HTMX \+ Alpine.js**

For a solo, learning developer managing a local-first FastAPI tool, **HTMX** is the superior choice over a full SPA framework (React/Next).

## **Recommendation: The "Low-JS" Stack**

* **Backend:** Python/FastAPI (Existing).  
* **Templating:** Jinja2 (Serverside HTML).  
* **Interactivity:** [HTMX](https://tailadmin.com/blog/best-analytics-dashboard) for partial page updates (e.g., loading trade results) \+ [Alpine.js](https://tailadmin.com/blog/best-analytics-dashboard) for client-side UI states (toggles, modals).  
* **Styling:** [Tailwind CSS](https://tailadmin.com/blog/best-analytics-dashboard) for rapid, maintainable styling.  
* **Charts:** [Chart.js](https://tailadmin.com/blog/best-analytics-dashboard) or **Apache ECharts** (powerful for data-density).

## **Migration Path**

1. **Phase 1:** Wrap your static HTML in a Jinja2 base template to create a shared "App Shell."  
2. **Phase 2:** Convert the **Trade Lab** into an HTMX-powered surface that updates results without a page refresh.  
3. **Phase 3:** Introduce Chart.js components for aging curves and uncertainty bands.

## **6\. Phased Build Roadmap**

1. **Foundation (Month 1):** Shared App Shell \+ Navigation \+ Player Detail Modal.  
2. **The "Active Target" (Month 2):** **Trade Lab**. Implement the two-lane model-vs-market view and "Forced Cut" warnings.  
3. **The Credibility Layer (Month 3):** **Backtest / Trust Surface**. Visualize model accuracy over the last year to validate the system before making roster-altering moves.  
4. **Maturation:** Migrate Rookie Board to the new design system.  
5. **Experimental Expansion:** Roster Audit and Waiver Radar.

I've outlined a design system that turns **uncertainty into an asset** rather than a weakness. By using **HTMX and Alpine.js**, you can build professional-grade interactivity without the overhead of a full JavaScript build pipeline, keeping your focus on the underlying FastAPI logic.

Would you like to start by sketching the **HTML structure for the "Trade Lab" two-lane view** using this new design language?**bolding** on key terms to make it scannable.

\[1\] [https://medium.com](https://medium.com/multiple-views-visualization-research-explained/uncertainty-visualization-explained-part-2-continuous-encodings-967a7f7c38d0)  
\[2\] [https://medium.com](https://medium.com/@marketingtd64/how-should-ux-visualize-data-uncertainty-c8628c6a1bf8)  
\[3\] [https://agentic-design.ai](https://agentic-design.ai/patterns/ui-ux-patterns/confidence-visualization-patterns)  
\[4\] [https://medium.com](https://medium.com/data-science/uncertainty-visualization-made-easy-with-hypothetical-outcome-plots-89558574d069)