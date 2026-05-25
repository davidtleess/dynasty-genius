# **Dynasty Genius UI/UX Architecture and Design System Specification**

## **Executive Recommendation**

This document establishes the official front-end design system and visual architecture for Dynasty Genius, a private, data-dense asset-management cockpit optimized for a 12-team Superflex PPR dynasty league. The system is designed to support long-term strategic decision-making over a 3–7 year horizon.1 The architecture is governed by two immutable engineering principles:

* **Zero-Dependency file:// Compatibility:** The entire user interface operates directly via the file:// protocol. It eliminates compiled web frameworks, external packages, and active web server dependencies. It relies entirely on native CSS Custom Properties (Design Tokens), semantic HTML5, and vanilla ECMAScript 6 (ES6) JavaScript loading data from disk-resident, pre-generated arrays.2  
* **Valuation Isolation:** The visual layer consumes pre-calculated, immutable Player Value Objects (PVO) and league context. It never performs real-time mathematical valuations, fantasy projection calculations, or roster scoring logic.

To maintain strict analytical objectivity, the interface completely rejects binary decision-grade terms such as "win/loss", "buy/sell", "approve/reject", or "veto".1 Instead, the visual layouts focus on showing multidimensional portfolio risk, displaying uncertainty ranges, ![][image1] (WR-equivalent replacement-adjusted value) delta margins, capacity costs, and positional age warnings as continuous spectrums rather than discrete verdicts.

## **Key Findings**

### **1\. Unified CSS Custom Properties System (Design Tokens)**

The design system uses a dark canvas archetype built on Slate and Zinc hues.5 This establishes a clear visual hierarchy that reduces cognitive fatigue during long sessions. The background canvas utilizes deep slate colors to create a high-contrast layout, while panels use elevated zinc tones to represent depth without relying on decorative shadows.6  
To visually represent roster balance, the interface uses calibrated, high-contrast HSL color tokens for the four core fantasy positions. These colors are mathematically aligned with empirical positional point differentials.8  
Positional point scarcity metrics indicate that the gap between elite production and replacement-level play varies significantly by position.8 The visual system represents these differences using specific HSL values that stand out against the dark canvas while remaining cohesive:

* **Quarterback (QB):** Teal HSL 8  
* **Running Back (RB):** Emerald HSL 8  
* **Wide Receiver (WR):** Amber HSL 8  
* **Tight End (TE):** Amethyst HSL 8

The font system uses "Outfit" for structural headers to ensure clean geometric lines at larger scale, and "Inter" for tabular and quantitative data to provide high readability for dense metrics and values.

CSS  
:root {  
    /\* \--- Slate Canvas System (Dark Mode Archetype) \--- \*/  
    \--color\-bg-canvas: hsl(222, 47%, 4%);             /\* Obsidian Base \*/  
    \--color\-bg-surface: hsl(220, 25%, 8%);            /\* Default Panel Background \*/  
    \--color\-bg-surface-elevated: hsl(220, 25%, 12%);   /\* Hover / Active Panels \*/  
    \--color\-border\-subtle: hsl(217, 19%, 17%);        /\* System Grid Lines \*/  
    \--color\-border\-muted: hsl(215, 16%, 27%);         /\* Inactive Panel Outlines \*/  
    \--color\-border\-focus: hsl(210, 100%, 66%);        /\* High Contrast Focus \*/

    /\* \--- Typography Colors \--- \*/  
    \--color\-text-primary: hsl(210, 40%, 98%);         /\* Main Headers / Data Values \*/  
    \--color\-text-secondary: hsl(215, 20%, 75%);       /\* Labels / Subheadings \*/  
    \--color\-text-muted: hsl(215, 12%, 50%);           /\* Secondary Metadata \*/

    /\* \--- Calibrated Positional Colors (High Contrast HSL) \--- \*/  
    \--color\-pos-qb: hsl(195, 85%, 55%);               /\* Cyan (Precision, Strategy) \*/  
    \--color\-pos-qb-trans: hsla(195, 85%, 55%, 0.12);  
    \--color\-pos-rb: hsl(142, 70%, 45%);               /\* Emerald (Ground, Workhorse) \*/  
    \--color\-pos-rb-trans: hsla(142, 70%, 45%, 0.12);  
    \--color\-pos-wr: hsl(38, 92%, 55%);                /\* Amber (Explosive, Value Apex) \*/  
    \--color\-pos-wr-trans: hsla(38, 92%, 55%, 0.12);  
    \--color\-pos-te: hsl(271, 81%, 63%);               /\* Amethyst (Scarce, Specialized) \*/  
    \--color\-pos-te-trans: hsla(271, 81%, 63%, 0.12);

    /\* \--- Quantitative Delta States \--- \*/  
    \--color\-accent-positive: hsl(142, 76%, 36%);      /\* Above Market Delta \*/  
    \--color\-accent-negative: hsl(350, 89%, 60%);      /\* Below Market Delta \*/  
    \--color\-accent-neutral: hsl(215, 15%, 50%);       /\* Inside Arbitrage Band \*/  
    \--color\-warning-alt: hsl(48, 96%, 53%);           /\* Roster Cliff Warnings \*/

    /\* \--- Drop Shadows & Glassmorphic Filters \--- \*/  
    \--shadow-sm: 0 1px 2px 0 hsla(0, 0%, 0%, 0.4);  
    \--shadow-md: 0 4px 6px \-1px hsla(0, 0%, 0%, 0.5), 0 2px 4px \-2px hsla(0, 0%, 0%, 0.5);  
    \--shadow-lg: 0 10px 15px \-3px hsla(0, 0%, 0%, 0.6), 0 4px 6px \-4px hsla(0, 0%, 0%, 0.6);  
    \--backdrop-blur-glass: blur(12px);  
    \--border\-glass-spec: 1px solid hsla(0, 0%, 100%, 0.08);

    /\* \--- Typography Scales \--- \*/  
    \--font\-headers: 'Outfit', \-apple-system, sans-serif;  
    \--font\-data: 'Inter', ui-monospace, SFMono-Regular, monospace;  
}

* **Source:** 5  
* **Confidence Level:** High.  
* **Implementation Implication:** These tokens must be declared in a global :root block in the primary CSS sheet (styles/main.css). They are referenced across all panels to maintain visual consistency.  
* **Claim Status:** Model-ready.

### **2\. Standalone Trade Lab Splits (Double-Panel Layout)**

The Trade Lab interface is built as a double-panel workspace. It separates model evaluation from volatile market signals to prevent the manager from making decisions based on short-term market hype.1

* **Left Panel (Model Lane):** Displays metrics calculated by Engine B. This includes roster-aware ![][image1] changes, consolidation premium gauges, and active "forced cuts" (such as AJ Barner) priced in model-equivalent value. This panel uses the active position's HSL color as a left border accent to emphasize roster fit.  
* **Right Panel (Market Lane):** Displays consensus public pricing from FantasyCalc.4 It shows draft pick slot values within a ![][image2] volatility range to reflect market uncertainty. It also highlights arbitrage deltas, indicating whether the team's model values the asset higher or lower than the market, or if the asset's price falls within the expected variance band.

HTML  
\<section class\="trade-lab-container"\>  
  \<div class\="trade-pane model-lane"\>  
    \<div class\="pane-header"\>  
      \<h3 class\="pane-title"\>Quantitative Model Evaluation\</h3\>  
      \<span class\="badge badge-model"\>Engine B Active\</span\>  
    \</div\>  
      
    \<div class\="roster-aware-metrics"\>  
      \<div class\="metric-group"\>  
        \<span class\="metric-label"\>Roster-Adjusted xVAR Delta\</span\>  
        \<div class\="metric-value-display"\>  
          \<span class\="metric-number text-positive"\>\+4.12\</span\>  
          \<span class\="metric-unit"\>xVAR\</span\>  
        \</div\>  
      \</div\>  
        
      \<div class\="premium-gauge-wrapper"\>  
        \<div class\="gauge-meta"\>  
          \<span class\="gauge-title"\>Consolidation Premium (CP)\</span\>  
          \<span class\="gauge-value"\>12.5%\</span\>  
        \</div\>  
        \<div class\="gauge-track"\>  
          \<div class\="gauge-bar" style\="width: 72.5%;"\>\</div\>  
        \</div\>  
        \<span class\="gauge-caption"\>Receiving elite asset tier; positive variance adjustment applied.\</span\>  
      \</div\>  
    \</div\>

    \<div class\="forced-cuts-container"\>  
      \<h4 class\="section-subtitle"\>Forced Roster Constraints\</h4\>  
      \<div class\="forced-cut-card warning-state"\>  
        \<div class\="player-meta"\>  
          \<span class\="player-name"\>AJ Barner\</span\>  
          \<span class\="player-position pos-te"\>TE\</span\>  
        \</div\>  
        \<div class\="capacity-cost"\>  
          \<span class\="cost-label"\>Model Drag Value\</span\>  
          \<span class\="cost-value font-mono"\>0.12 xVAR\</span\>  
        \</div\>  
      \</div\>  
    \</div\>  
  \</div\>

  \<div class\="trade-pane market-lane"\>  
    \<div class\="pane-header"\>  
      \<h3 class\="pane-title"\>Public Market Overlay\</h3\>  
      \<span class\="badge badge-market"\>FantasyCalc Realtime\</span\>  
    \</div\>

    \<div class\="market-value-matrix"\>  
      \<div class\="metric-group"\>  
        \<span class\="metric-label"\>Consensus Raw Value\</span\>  
        \<div class\="metric-value-display"\>  
          \<span class\="metric-number font-mono"\>14,250\</span\>  
          \<span class\="metric-unit"\>Points\</span\>  
        \</div\>  
      \</div\>

      \<div class\="volatility-band-wrapper"\>  
        \<span class\="band-title"\>Generic Pick Slot Range (±40% Volatility)\</span\>  
        \<div class\="volatility-spectrum"\>  
          \<span class\="spectrum-boundary min-value"\>8,550\</span\>  
          \<div class\="spectrum-bar"\>  
            \<div class\="market-current-pointer" style\="left: 50%;"\>\</div\>  
          \</div\>  
          \<span class\="spectrum-boundary max-value"\>19,950\</span\>  
        \</div\>  
      \</div\>  
    \</div\>

    \<div class\="arbitrage-status-card status-model-higher"\>  
      \<div class\="status-indicator-light pulse-active"\>\</div\>  
      \<div class\="status-details"\>  
        \<span class\="status-headline"\>Model Outvaluing Market\</span\>  
        \<p class\="status-paragraph"\>The model evaluation projects \+18.4% above consensus market value, indicating an optimal target acquisition window.\</p\>  
      \</div\>  
    \</div\>  
  \</div\>  
\</section\>

CSS  
.trade-lab-container {  
    display: grid;  
    grid-template-columns: repeat(2, 1fr);  
    gap: 24px;  
    background-color: var(--color-bg-canvas);  
    padding: 24px;  
    border-radius: 8px;  
    min-height: 500px;  
}

@media (max-width: 1024px) {  
   .trade-lab-container {  
        grid-template-columns: 1fr;  
    }  
}

.trade-pane {  
    background-color: var(--color-bg-surface);  
    border: 1px solid var(--color-border-subtle);  
    border-radius: 6px;  
    padding: 20px;  
    display: flex;  
    flex-direction: column;  
    gap: 24px;  
    transition: border-color 0.2s ease-in-out;  
}

.model-lane {  
    border-left: 4px solid var(--color-pos-qb);  
}

.market-lane {  
    border-left: 4px solid var(--color-text-muted);  
}

.pane-header {  
    display: flex;  
    justify-content: space-between;  
    align-items: center;  
    border-bottom: 1px solid var(--color-border-subtle);  
    padding-bottom: 12px;  
}

.pane-title {  
    font-family: var(--font-headers);  
    font-size: 1.25rem;  
    color: var(--color-text-primary);  
    font-weight: 600;  
}

.badge {  
    padding: 4px 8px;  
    border-radius: 4px;  
    font-size: 0.75rem;  
    font-weight: 700;  
    font-family: var(--font-headers);  
    text-transform: uppercase;  
}

.badge-model {  
    background-color: var(--color-pos-qb-trans);  
    color: var(--color-pos-qb);  
}

.badge-market {  
    background-color: hsla(215, 15%, 50%, 0.15);  
    color: var(--color-text-secondary);  
}

.metric-group {  
    display: flex;  
    flex-direction: column;  
    gap: 6px;  
}

.metric-label {  
    font-size: 0.815rem;  
    color: var(--color-text-secondary);  
    text-transform: uppercase;  
    letter-spacing: 0.05em;  
}

.metric-value-display {  
    display: flex;  
    align-items: baseline;  
    gap: 8px;  
}

.metric-number {  
    font-family: var(--font-data);  
    font-size: 2.25rem;  
    font-weight: 800;  
}

.text-positive {  
    color: var(--color-accent-positive);  
}

.metric-unit {  
    font-size: 1rem;  
    color: var(--color-text-muted);  
    font-weight: 500;  
}

.font-mono {  
    font-family: var(--font-data);  
}

/\* Consolidation Premium Gauge \*/  
.premium-gauge-wrapper {  
    margin-top: 16px;  
    background: hsla(0, 0%, 100%, 0.02);  
    padding: 12px;  
    border-radius: 6px;  
    border: 1px solid var(--color-border-subtle);  
}

.gauge-meta {  
    display: flex;  
    justify-content: space-between;  
    font-size: 0.815rem;  
    margin-bottom: 8px;  
}

.gauge-title {  
    color: var(--color-text-secondary);  
}

.gauge-value {  
    color: var(--color-text-primary);  
    font-weight: 700;  
    font-family: var(--font-data);  
}

.gauge-track {  
    background-color: var(--color-border-subtle);  
    height: 6px;  
    border-radius: 3px;  
    overflow: hidden;  
}

.gauge-bar {  
    background-color: var(--color-pos-wr);  
    height: 100%;  
    border-radius: 3px;  
}

.gauge-caption {  
    font-size: 0.75rem;  
    color: var(--color-text-muted);  
    display: block;  
    margin-top: 6px;  
}

/\* Forced Cuts \*/  
.forced-cuts-container {  
    border-top: 1px solid var(--color-border-subtle);  
    padding-top: 16px;  
}

.section-subtitle {  
    font-family: var(--font-headers);  
    font-size: 0.95rem;  
    color: var(--color-text-primary);  
    margin-bottom: 12px;  
}

.forced-cut-card {  
    background-color: hsla(0, 0%, 100%, 0.01);  
    border: 1px solid var(--color-border-subtle);  
    border-radius: 6px;  
    padding: 12px;  
    display: flex;  
    justify-content: space-between;  
    align-items: center;  
}

.forced-cut-card.warning-state {  
    border-color: var(--color-accent-negative);  
    background-color: hsla(350, 89%, 60%, 0.03);  
}

.player-meta {  
    display: flex;  
    align-items: center;  
    gap: 8px;  
}

.player-name {  
    color: var(--color-text-primary);  
    font-weight: 600;  
}

.player-position {  
    padding: 2px 6px;  
    border-radius: 3px;  
    font-size: 0.7rem;  
    font-weight: 800;  
}

.pos-te {  
    background-color: var(--color-pos-te-trans);  
    color: var(--color-pos-te);  
}

.capacity-cost {  
    text-align: right;  
}

.cost-label {  
    font-size: 0.75rem;  
    color: var(--color-text-muted);  
}

.cost-value {  
    color: var(--color-text-secondary);  
    font-size: 0.875rem;  
}

/\* Volatility Band \*/  
.volatility-band-wrapper {  
    background: hsla(0, 0%, 100%, 0.02);  
    padding: 12px;  
    border-radius: 6px;  
    border: 1px solid var(--color-border-subtle);  
}

.band-title {  
    font-size: 0.815rem;  
    color: var(--color-text-secondary);  
    display: block;  
    margin-bottom: 12px;  
}

.volatility-spectrum {  
    display: flex;  
    align-items: center;  
    gap: 12px;  
}

.spectrum-boundary {  
    font-family: var(--font-data);  
    font-size: 0.815rem;  
    color: var(--color-text-muted);  
}

.spectrum-bar {  
    flex-grow: 1;  
    background: linear-gradient(to right, hsla(350, 89%, 60%, 0.3), var(--color-border-muted), hsla(142, 76%, 36%, 0.3));  
    height: 8px;  
    border-radius: 4px;  
    position: relative;  
}

.market-current-pointer {  
    width: 4px;  
    height: 16px;  
    background-color: var(--color-text-primary);  
    position: absolute;  
    top: \-4px;  
    border-radius: 2px;  
}

/\* Arbitrage Status Cards \*/  
.arbitrage-status-card {  
    border-radius: 6px;  
    padding: 16px;  
    display: flex;  
    gap: 16px;  
    align-items: flex-start;  
    border: 1px solid var(--color-border-subtle);  
}

.status-model-higher {  
    background-color: hsla(142, 76%, 36%, 0.05);  
    border-color: var(--color-accent-positive);  
}

.status-indicator-light {  
    width: 10px;  
    height: 10px;  
    border-radius: 50%;  
    margin-top: 4px;  
}

.status-model-higher.status-indicator-light {  
    background-color: var(--color-accent-positive);  
}

.status-details {  
    display: flex;  
    flex-direction: column;  
    gap: 4px;  
}

.status-headline {  
    font-family: var(--font-headers);  
    font-size: 0.95rem;  
    font-weight: 700;  
    color: var(--color-text-primary);  
}

.status-paragraph {  
    font-size: 0.815rem;  
    color: var(--color-text-secondary);  
    line-height: 1.4;  
    margin: 0;  
}

* **Source:** 1  
* **Confidence Level:** High.  
* **Implementation Implication:** The trade pane elements must be styled inside styles/components/trade-lab.css. The layout must automatically adapt to smaller screens, transitioning to stacked columns below ![][image3] to remain readable.  
* **Claim Status:** Model-ready.

### **3\. Roster Audit & Capacity Gauges**

A team's roster state is governed by physical capacity limits (active spots, taxi squad, and injured reserve 2) and positional age cliffs.1  
The visual layout represents this using clean, interactive status widgets:

* **SVG Circular Progress Gauge:** Renders active roster utilization as a fractional fill arc based on Sleeper API data. It maps occupied spots (![][image4]) against maximum spots (![][image5]) 9:  
  ![][image6]  
  where ![][image7] for a circle of radius ![][image8].  
* **Positional Age Warning Limits:** Highlight players who have crossed critical development or career age cliffs. The system flags assets that have reached or exceeded these limits: Running Backs ![][image9], Wide Receivers ![][image10], Tight Ends ![][image11], and Quarterbacks ![][image12].1  
* **Advisory Drop Lists:** Automatically ranks low-value assets (such as AJ Barner) to make roster cuts straightforward when executing trades or activating players from injured reserve.

HTML  
\<div class\="roster-audit-widget"\>  
  \<div class\="widget-header"\>  
    \<h3 class\="widget-title"\>Roster Capacity Audit\</h3\>  
  \</div\>

  \<div class\="capacity-dashboard"\>  
    \<div class\="circular-gauge-container"\>  
      \<svg class\="radial-gauge" viewBox\="0 0 100 100"\>  
        \<circle class\="gauge-bg-circle" cx\="50" cy\="50" r\="40" /\>  
        \<circle class\="gauge-fill-circle" cx\="50" cy\="50" r\="40" style\="stroke-dasharray: 251.2; stroke-dashoffset: calc(251.2 \- (251.2 \* 23\) / 25);" /\>  
      \</svg\>  
      \<div class\="gauge-center-text"\>  
        \<span class\="count-numerator"\>23\</span\>  
        \<span class\="count-denominator"\>/ 25\</span\>  
      \</div\>  
    \</div\>

    \<div class\="capacity-meta-fields"\>  
      \<div class\="meta-field"\>  
        \<span class\="meta-dot bg-active"\>\</span\>  
        \<span class\="meta-name"\>Active Roster\</span\>  
        \<span class\="meta-stats font-mono"\>23 / 25\</span\>  
      \</div\>  
      \<div class\="meta-field"\>  
        \<span class\="meta-dot bg-taxi"\>\</span\>  
        \<span class\="meta-name"\>Taxi Squad\</span\>  
        \<span class\="meta-stats font-mono"\>3 / 4\</span\>  
      \</div\>  
      \<div class\="meta-field"\>  
        \<span class\="meta-dot bg-ir"\>\</span\>  
        \<span class\="meta-name"\>Injured Reserve\</span\>  
        \<span class\="meta-stats font-mono"\>1 / 2\</span\>  
      \</div\>  
    \</div\>  
  \</div\>

  \<div class\="roster-cliffs-section"\>  
    \<h4 class\="section-subtitle"\>Positional Age Warning Limits\</h4\>  
    \<div class\="cliff-cards-grid"\>  
        
      \<div class\="cliff-card status-critical"\>  
        \<div class\="cliff-player"\>  
          \<div class\="player-identity"\>  
            \<span class\="player-badge pos-rb"\>RB\</span\>  
            \<span class\="player-name-string"\>Christian McCaffrey\</span\>  
          \</div\>  
          \<span class\="cliff-metric font-mono"\>Age 29.9\</span\>  
        \</div\>  
        \<div class\="cliff-warning-badge"\>RB Cliff Exceeded (\>=26)\</div\>  
      \</div\>

      \<div class\="cliff-card status-alert"\>  
        \<div class\="cliff-player"\>  
          \<div class\="player-identity"\>  
            \<span class\="player-badge pos-wr"\>WR\</span\>  
            \<span class\="player-name-string"\>Deebo Samuel\</span\>  
          \</div\>  
          \<span class\="cliff-metric font-mono"\>Age 30.3\</span\>  
        \</div\>  
        \<div class\="cliff-warning-badge"\>WR Cliff Exceeded (\>=28)\</div\>  
      \</div\>

    \</div\>  
  \</div\>  
\</div\>

CSS  
.roster-audit-widget {  
    background-color: var(--color-bg-surface);  
    border: 1px solid var(--color-border-subtle);  
    border-radius: 6px;  
    padding: 20px;  
}

.widget-header {  
    border-bottom: 1px solid var(--color-border-subtle);  
    padding-bottom: 12px;  
    margin-bottom: 20px;  
}

.widget-title {  
    font-family: var(--font-headers);  
    font-size: 1.15rem;  
    color: var(--color-text-primary);  
    font-weight: 600;  
}

.capacity-dashboard {  
    display: flex;  
    align-items: center;  
    gap: 32px;  
    margin-bottom: 24px;  
}

.circular-gauge-container {  
    position: relative;  
    width: 120px;  
    height: 120px;  
}

.radial-gauge {  
    transform: rotate(-90deg);  
    width: 100%;  
    height: 100%;  
}

.gauge-bg-circle {  
    fill: none;  
    stroke: var(--color-border-subtle);  
    stroke-width: 8;  
}

.gauge-fill-circle {  
    fill: none;  
    stroke: var(--color-pos-qb);  
    stroke-width: 8;  
    stroke-linecap: round;  
    transition: stroke-dashoffset 0.3s ease;  
}

.gauge-center-text {  
    position: absolute;  
    top: 50%;  
    left: 50%;  
    transform: translate(-50%, \-50%);  
    text-align: center;  
    display: flex;  
    flex-direction: column;  
}

.count-numerator {  
    font-family: var(--font-data);  
    font-size: 1.5rem;  
    font-weight: 800;  
    color: var(--color-text-primary);  
    line-height: 1;  
}

.count-denominator {  
    font-family: var(--font-data);  
    font-size: 0.815rem;  
    color: var(--color-text-muted);  
}

.capacity-meta-fields {  
    display: flex;  
    flex-direction: column;  
    gap: 12px;  
    flex-grow: 1;  
}

.meta-field {  
    display: flex;  
    align-items: center;  
    font-size: 0.875rem;  
}

.meta-dot {  
    width: 8px;  
    height: 8px;  
    border-radius: 50%;  
    margin-right: 12px;  
}

.bg-active { background-color: var(--color-pos-qb); }  
.bg-taxi { background-color: var(--color-pos-wr); }  
.bg-ir { background-color: var(--color-pos-te); }

.meta-name {  
    color: var(--color-text-secondary);  
    flex-grow: 1;  
}

.meta-stats {  
    color: var(--color-text-primary);  
    font-weight: 700;  
}

/\* Roster Cliffs Section \*/  
.roster-cliffs-section {  
    border-top: 1px solid var(--color-border-subtle);  
    padding-top: 20px;  
}

.cliff-cards-grid {  
    display: grid;  
    grid-template-columns: 1fr;  
    gap: 12px;  
}

.cliff-card {  
    border-radius: 6px;  
    border: 1px solid var(--color-border-subtle);  
    padding: 12px 16px;  
    display: flex;  
    flex-direction: column;  
    gap: 8px;  
    background-color: hsla(0, 0%, 100%, 0.01);  
}

.cliff-card.status-critical {  
    border-left: 4px solid var(--color-accent-negative);  
    background-color: hsla(350, 89%, 60%, 0.02);  
}

.cliff-card.status-alert {  
    border-left: 4px solid var(--color-warning-alt);  
    background-color: hsla(48, 96%, 53%, 0.02);  
}

.cliff-player {  
    display: flex;  
    justify-content: space-between;  
    align-items: center;  
}

.player-identity {  
    display: flex;  
    align-items: center;  
    gap: 8px;  
}

.player-badge {  
    font-size: 0.7rem;  
    font-weight: 800;  
    padding: 2px 6px;  
    border-radius: 3px;  
}

.pos-rb {  
    background-color: var(--color-pos-rb-trans);  
    color: var(--color-pos-rb);  
}

.pos-wr {  
    background-color: var(--color-pos-wr-trans);  
    color: var(--color-pos-wr);  
}

.player-name-string {  
    color: var(--color-text-primary);  
    font-weight: 600;  
}

.cliff-metric {  
    font-size: 0.875rem;  
    color: var(--color-text-secondary);  
    font-weight: 700;  
}

.cliff-warning-badge {  
    font-size: 0.75rem;  
    color: var(--color-text-muted);  
}

.status-critical.cliff-warning-badge {  
    color: var(--color-accent-negative);  
    font-weight: 600;  
}

.status-alert.cliff-warning-badge {  
    color: var(--color-warning-alt);  
    font-weight: 600;  
}

* **Source:** 1  
* **Confidence Level:** High.  
* **Implementation Implication:** CSS layout definitions must be configured inside styles/components/roster-audit.css. The circular gauge arc properties require manual coordinate mapping to display correctly in SVG elements.  
* **Claim Status:** Model-ready.

### **4\. Heatmap & Matrix Layouts (League Pulse)**

To visualize opportunities and assess rival teams, the cockpit uses a dense 12-team value matrix. This provides a clear overview of the league's competitive landscape.1  
The matrix maps:

* Positional strength using absolute, color-coded ![][image1] values.8  
* Rival team postures, categorized into clear strategic lanes: "Contender" or "Rebuilder".1  
* Future draft capital distributions, tracking accumulated draft assets.1  
* Market divergence opportunities, highlighting target areas where the internal model differs from market consensus (such as the wide receiver target share dynamics in Chicago and New York 4).

HTML  
\<div class\="league-pulse-section"\>  
  \<div class\="section-header"\>  
    \<h3 class\="panel-main-title"\>12-Team Value Matrix & Opportunity Map\</h3\>  
  \</div\>

  \<div class\="pulse-matrix-grid"\>  
    \<div class\="matrix-row matrix-header-row"\>  
      \<div class\="grid-cell"\>Manager Team\</div\>  
      \<div class\="grid-cell text-center"\>Postures\</div\>  
      \<div class\="grid-cell text-right"\>QB xVAR\</div\>  
      \<div class\="grid-cell text-right"\>RB xVAR\</div\>  
      \<div class\="grid-cell text-right"\>WR xVAR\</div\>  
      \<div class\="grid-cell text-right"\>TE xVAR\</div\>  
      \<div class\="grid-cell text-center"\>Future Draft Capital\</div\>  
      \<div class\="grid-cell text-center"\>Target Arbitrage\</div\>  
    \</div\>

    \<div class\="matrix-row"\>  
      \<div class\="grid-cell manager-meta"\>  
        \<span class\="manager-name font-sans"\>David (Contender)\</span\>  
      \</div\>  
      \<div class\="grid-cell text-center"\>  
        \<span class\="posture-tag tag-championship"\>Contender\</span\>  
      \</div\>  
      \<div class\="grid-cell text-right font-mono text-qb"\>34.12\</div\>  
      \<div class\="grid-cell text-right font-mono text-rb"\>18.55\</div\>  
      \<div class\="grid-cell text-right font-mono text-wr"\>48.90\</div\>  
      \<div class\="grid-cell text-right font-mono text-te"\>12.10\</div\>  
      \<div class\="grid-cell text-center font-mono"\>1.04, 2.04\</div\>  
      \<div class\="grid-cell text-center"\>  
        \<span class\="opp-badge opp-neutral"\>Optimized\</span\>  
      \</div\>  
    \</div\>

    \<div class\="matrix-row"\>  
      \<div class\="grid-cell manager-meta"\>  
        \<span class\="manager-name font-sans"\>A. Smith (Rebuilding)\</span\>  
      \</div\>  
      \<div class\="grid-cell text-center"\>  
        \<span class\="posture-tag tag-rebuild"\>Rebuilder\</span\>  
      \</div\>  
      \<div class\="grid-cell text-right font-mono text-qb"\>12.05\</div\>  
      \<div class\="grid-cell text-right font-mono text-rb"\>4.12\</div\>  
      \<div class\="grid-cell text-right font-mono text-wr font-weight-900"\>55.10\</div\>  
      \<div class\="grid-cell text-right font-mono text-te"\>3.40\</div\>  
      \<div class\="grid-cell text-center font-mono"\>2027 1st (x3)\</div\>  
      \<div class\="grid-cell text-center"\>  
        \<span class\="opp-badge opp-divergence-high"\>Buy WR\</span\>  
      \</div\>  
    \</div\>  
  \</div\>  
\</div\>

CSS  
.league-pulse-section {  
    background-color: var(--color-bg-surface);  
    border: 1px solid var(--color-border-subtle);  
    border-radius: 6px;  
    padding: 20px;  
    overflow-x: auto;  
}

.panel-main-title {  
    font-family: var(--font-headers);  
    font-size: 1.15rem;  
    color: var(--color-text-primary);  
    font-weight: 600;  
    margin-bottom: 16px;  
}

.pulse-matrix-grid {  
    display: flex;  
    flex-direction: column;  
    min-width: 900px;  
}

.matrix-row {  
    display: grid;  
    grid-template-columns: 2fr 1.5fr 1fr 1fr 1fr 1fr 2fr 1.5fr;  
    border-bottom: 1px solid var(--color-border-subtle);  
    padding: 10px 0;  
    align-items: center;  
}

.matrix-row:hover {  
    background-color: var(--color-bg-surface-elevated);  
}

.matrix-header-row {  
    border-bottom: 2px solid var(--color-border-muted);  
    font-weight: 700;  
    color: var(--color-text-secondary);  
    font-size: 0.815rem;  
    text-transform: uppercase;  
}

.grid-cell {  
    padding: 4px 8px;  
    font-size: 0.875rem;  
    color: var(--color-text-primary);  
}

.text-center { text-align: center; }  
.text-right { text-align: right; }

.font-sans { font-family: var(--font-headers); }  
.font-mono { font-family: var(--font-data); }

.text-qb { color: var(--color-pos-qb); }  
.text-rb { color: var(--color-pos-rb); }  
.text-wr { color: var(--color-pos-wr); }  
.text-te { color: var(--color-pos-te); }

/\* Posture Tags \*/  
.posture-tag {  
    padding: 2px 8px;  
    border-radius: 4px;  
    font-size: 0.75rem;  
    font-weight: 700;  
    font-family: var(--font-headers);  
    text-transform: uppercase;  
}

.tag-championship {  
    background-color: hsla(142, 70%, 45%, 0.12);  
    color: var(--color-pos-rb);  
}

.tag-rebuild {  
    background-color: hsla(195, 85%, 55%, 0.12);  
    color: var(--color-pos-qb);  
}

/\* Opportunity Badges \*/  
.opp-badge {  
    padding: 4px 8px;  
    border-radius: 4px;  
    font-size: 0.75rem;  
    font-weight: 700;  
    text-transform: uppercase;  
}

.opp-neutral {  
    background-color: hsla(215, 15%, 50%, 0.15);  
    color: var(--color-text-muted);  
}

.opp-divergence-high {  
    background-color: hsla(38, 92%, 55%, 0.15);  
    color: var(--color-pos-wr);  
    border: 1px solid var(--color-pos-wr);  
}

* **Source:** 1  
* **Confidence Level:** High.  
* **Implementation Implication:** CSS layout grids must be styled inside styles/components/league-pulse.css. Standard horizontal overflows must be applied to prevent wide columns from breaking mobile layouts.  
* **Claim Status:** Model-ready.

### **5\. Micro-Animations & Dynamic States**

The user interface uses hardware-accelerated animations to improve usability. Card transitions use smooth transforms rather than sudden position changes to reduce visual distraction during analysis.  
Active draft assets and high-priority waiver pickups use subtle glowing pulse rings to draw attention to time-sensitive items. When background synchronization scripts fail to run, the system uses custom CSS filters to grey out stale panels, alerting the manager to old data snapshots without taking the entire interface offline.2

CSS  
/\* \--- Card Drawer Expansion Transition Rules \--- \*/  
.card-drawer-expandable {  
    max-height: 40px;  
    overflow: hidden;  
    transition: max-height 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease-out;  
    opacity: 0.85;  
}

.card-drawer-expandable.active {  
    max-height: 500px;  
    opacity: 1;  
}

/\* \--- Live Target Ring Pulse Animation \--- \*/  
@keyframes live-pulse {  
    0% {  
        box-shadow: 0 0 0 0 hsla(195, 85%, 55%, 0.7);  
    }  
    70% {  
        box-shadow: 0 0 0 8px hsla(195, 85%, 55%, 0);  
    }  
    100% {  
        box-shadow: 0 0 0 0 hsla(195, 85%, 55%, 0);  
    }  
}

.waiver-target-pulse {  
    position: relative;  
    border-radius: 50%;  
}

.waiver-target-pulse::after {  
    content: '';  
    position: absolute;  
    width: 100%;  
    height: 100%;  
    top: 0;  
    left: 0;  
    border-radius: 50%;  
    animation: live-pulse 2s infinite ease-in-out;  
    pointer-events: none;  
}

/\* \--- Stale Snapshot Degradation State CSS \--- \*/  
.stale-data-degraded {  
    filter: saturate(0.25) contrast(0.85);  
    opacity: 0.65;  
    position: relative;  
}

.stale-data-degraded::before {  
    content: 'STALE PAYLOAD SNAPSHOT — RUN LOCAL SYNC SHELL';  
    position: absolute;  
    top: 4px;  
    right: 4px;  
    background-color: var(--color-accent-negative);  
    color: var(--color-text-primary);  
    font-family: var(--font-headers);  
    font-size: 0.7rem;  
    font-weight: 800;  
    padding: 2px 6px;  
    border-radius: 3px;  
    z-index: 10;  
}

* **Source:** 2  
* **Confidence Level:** High.  
* **Implementation Implication:** Keyframes and animation classes must be declared inside styles/base/animations.css. Stale data classes must be applied to UI containers using native JavaScript checks that run after loading local data scripts.  
* **Claim Status:** Model-ready.

## **Evidence Table**

The styling choices, layout designs, and data mappings in this document are based on direct design rules, technical platform structures, and quantitative fantasy football principles.

| Design Parameter / UI Block | Empirically Backed Value / Visual Mapping | Source Reference | Confidence Level | Implementation Status | Implication for Layouts & Assets |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Dark Theme Base Hues** | Slate (\#020617 base) paired with elevated Zinc panels. | 5 | High | Model-ready | Provides clean high-contrast visual layers without causing eye strain. |
| **Positional Visual Hierarchy** | QB (Teal), RB (Emerald), WR (Amber), TE (Amethyst). | 8 | High | Model-ready | Aligns with positional point differentials: RB (127.7), TE (113.0), QB (96.6), WR (88.9). |
| **Roster Spot Tracking** | Native SVG gauge mapping active slots, taxi squads, and IR limits. | 9 | High | Model-ready | Directly processes Sleeper's rosters JSON schema (players, starters, taxi). |
| **Positional Age Cliffs** | Warnings at QB ![][image12], RB ![][image9], WR ![][image10], TE ![][image11]. | 1 | High | Model-ready | Flags high-risk veterans to help manage roster decline and preserve future value. |
| **Trade Lab Lane Split** | Left: Model evaluation (Engine B). Right: Market context overlay. | 1 | High | Model-ready | Separates internal projection models from volatile public market data. |
| **Pick Value Ranges** | Symmetric distribution displaying ![][image2] market volatility. | 4 | Medium | Validation-only | Prevents over-reacting to shifting trade values by showing potential price ranges. |
| **Postures Mapping** | Visual indicators representing "Contender" vs "Rebuilder" teams. | 1 | High | Model-ready | Identifies matching trade partners based on their competitive direction. |
| **Waiver & Target Pulse** | Glow rings for priority draft targets and waiver claims. | 11 | High | Model-ready | Highlights top-tier players in thin landing spots to prioritize waiver transactions. |
| **Local Offline Fallback** | CSS filters highlighting stale or missing local data snapshots. | 2 | High | Model-ready | Shows when data sync is lagging without breaking the core system interface. |

## **Conflicts and Resolutions**

### **Conflict 1: Real-Time Roster Synchronization vs. file:// Direct Execution**

* **The Conflict:** Standard web architectures fetch real-time roster changes 9 using asynchronous JavaScript requests (such as fetch()). However, running the application locally via the file:// protocol triggers browser-level CORS security blocks, preventing live API requests from running directly in the browser.  
* **Source Quality Ranking:** Official Sleeper API documentation 9 ranks highest for data integrity, followed by automated sync workflows.2  
* **The Resolution:** The cockpit uses a split-process model to work around browser security blocks. Local shell scripts handle live API requests in the background, saving the responses as static data. The web interface then loads these static files synchronously using standard script tags:  
  HTML  
  \<script src\="resources/sleeper\_rosters.js"\>\</script\>  
  \<script src\="resources/engine\_outputs.js"\>\</script\>

  This approach bypasses CORS restrictions while keeping the front-end clean and zero-dependency.

### **Conflict 2: Market Sentiment Fluctuations vs. Model Stability**

* **The Conflict:** Public market sites (like FantasyCalc 4) update prices rapidly based on short-term news, whereas internal projection models (Engine B) change slowly based on long-term performance and historical career trends.1 This difference can lead to conflicting signals, especially during draft windows or trade negotiations.  
* **Source Quality Ranking:** Analytical research on positional value 8 and long-term dynasty management 1 ranks higher for strategic decision-making than crowd-sourced market data.4  
* **The Resolution:** The user interface separates these calculations into two distinct lanes. The left panel shows internal value calculations, while the right panel displays public market sentiment. In addition, market values for draft picks are shown within a wide ![][image2] range to represent market volatility, helping the manager focus on internal valuation models rather than short-term price swings.

### **Conflict 3: Roster Space vs. Player Retention Decisions**

* **The Conflict:** When executing multi-player trades, managers often focus on the core players involved and overlook the roster spots required to complete the transaction, which can lead to forced drops that waste asset value.1  
* **Source Quality Ranking:** Roster limit rules from the Sleeper API 9 rank higher than trade analyzer models 4 because roster limits are hard constraints.  
* **The Resolution:** The Trade Lab automatically displays a warning card when a trade would exceed roster capacity. It also lists the team's lowest-value players, highlighting the immediate ![][image1] cost of the forced drops required to complete the trade.

## **Implementation Implications**

This design system acts as the direct visual interface for the active modeling engines. To preserve the accuracy of internal projections, the UI must follow strict data boundaries:

                  ┌───────────────────────────────┐  
                  │      DATA/ENGINE LAYER        │  
                  │  (Internal Valuation Models)  │  
                  └───────────────┬───────────────┘  
                                  │ Pre-Calculated  
                                  │ Player Value  
                                  ▼ Objects (PVO)  
                  ┌───────────────────────────────┐  
                  │        ISOLATION ZONE         │  
                  │  (Immutable Value Structures) │  
                  └───────────────┬───────────────┘  
                                  │ Read-Only  
                                  │ Consumption  
                                  ▼  
                  ┌───────────────────────────────┐  
                  │       DISPLAY LAYER (UI)      │  
                  │  (Visual Layout/Interactions)  │  
                  └───────────────────────────────┘

The user interface must read pre-calculated Player Value Objects from local arrays and display them directly. It must never perform real-time calculation changes or alter underlying value properties.

### **Impact of Layout Decisions on Phase 16 & 17 Transitions**

* **Phase 16 Focus (Engine A Upgrades):** The design system supports this phase by using color-coded metrics to show college production values and draft-capital adjustments. These metrics are displayed with visible confidence ratings to represent modeling uncertainty clearly.  
* **Phase 17 Focus (Universe Valuation & League Mapping):** The 12-team value matrix provides the foundational layout for this phase. It maps relative positional strength and team posturing to highlight trade opportunities across the league.

### **Spec and Governance Requirements**

┌────────────────────────────────────────────────────────────────────────────┐  
│                       GOVERNANCE & SPEC REQUIREMENTS                       │  
├─────────────────────────┬─────────────────────────┬────────────────────────┤  
│     NO SPEC REQUIRED    │    NEW SPEC REQUIRED    │ DAVID APPROVAL REQUIRED │  
├─────────────────────────┼─────────────────────────┼────────────────────────┤  
│ • Minor styling tweaks  │ • New dashboard panels  │ • Age warning limits   │  
│ • Font adjustments      │ • New data integrations │ • xVAR display rules   │  
│ • Color theme tuning    │ • Trade calculation UI  │ • Blocked terms list   │  
└─────────────────────────┴─────────────────────────┴────────────────────────┘

* **No Spec Required:** Minor layout styling tweaks, font adjustments, and local color theme tuning do not require a separate specification.  
* **New Spec Required:** Introducing new dashboard panels, draft tracking boards, or new local data integrations requires a separate, detailed specification.  
* **David Approval Required:** Any changes to the core positional age warning limits (e.g., changing the running back cliff from 26 to 25), the visual layout of ![][image1] calculations, or the list of blocked decision-grade terms require David's direct review and approval.

## **Recommended Workstreams and Ordering**

To build and integrate this design system cleanly, development should follow a structured sequence:

┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐  
│      WORKSTREAM 1      ├─────►│      WORKSTREAM 2      ├─────►│      WORKSTREAM 3      │  
│  CSS Custom Properties │      │  Trade Lab & Dividers  │      │  Audit Widgets & SVGs  │  
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘  
                                                                             │  
┌────────────────────────┐      ┌────────────────────────┐                   │  
│      WORKSTREAM 5      │◄─────┤      WORKSTREAM 4      │◄──────────────────┘  
│ System Integrity Gates │      │  12-Team Matrix Grid   │  
└────────────────────────┘      └────────────────────────┘

### **Workstream 1: Foundation Setup & CSS Variables**

* **Action Items:** Create the primary stylesheet directory (styles/base/) and declare all global custom properties inside :root. Configure Google Fonts "Outfit" and "Inter" references.  
* **Validation Gate:** Confirm that color contrast levels meet accessibility standards and verify that text elements display clearly against the dark background.

### **Workstream 2: Double-Pane Trade Lab Layout**

* **Action Items:** Build the double-pane container layout. Configure the Model Lane with its colored left-border accent, and set up the Market Lane to display volatility ranges and price comparisons.  
* **Validation Gate:** Resize the browser window to confirm the split panels stack cleanly on smaller screens, and verify that the layout displays correctly without a local web server running.

### **Workstream 3: Roster Audit Widgets & SVG Meters**

* **Action Items:** Create the SVG capacity gauges and configure their progress arcs. Write the card styles for positional age warnings and integrate the low-value advisory drop list.  
* **Validation Gate:** Test the SVG gauges using mock data inputs to confirm the progress arcs scale accurately, and verify that age warnings are triggered correctly for players past their positional limits.

### **Workstream 4: 12-Team Value Matrix & Opportunity Grid**

* **Action Items:** Build the dense value matrix using CSS Grid. Color-code the cells based on positional strength and set up horizontal scroll fallbacks for small screens.  
* **Validation Gate:** Verify that cells align correctly across columns, and confirm that posture tags and opportunity badges display cleanly.

### **Workstream 5: UI Integrity Check & Offline Fallbacks**

* **Action Items:** Apply the card expansion transitions, waiver pulse animations, and the stale-data fallback styling. Add JavaScript checks to run after loading data arrays to detect delayed updates.  
* **Validation Gate:** Simulate data update delays to verify that the stale-data fallback stylesheet triggers correctly, and inspect rendering performance to ensure animations run smoothly.

## **Risks and Failure Modes**

### **1\. Browser Security CORS Block on Local Storage**

* **Risk Description:** Developers may attempt to load data dynamically using standard asynchronous web requests, which will trigger browser CORS security blocks when running the application locally via the file:// protocol.  
* **Technical Mitigation:** Ensure all local datasets are stored as static variables in standard JavaScript files (e.g., const SLEEPER\_ROSTERS \= \[...\]) and loaded synchronously via standard script tags in the main HTML file.

### **2\. Missing or Corrupted Local Data Snapshot**

* **Risk Description:** If the background data sync script fails or is interrupted, the web interface may load empty variables, leading to broken UI elements or incorrect metrics.  
* **Technical Mitigation:** Add fallback initialization checks in the main script file. If a dataset is missing or incomplete, the interface must automatically display the stale-data warning overlay to alert the manager.

### **3\. Layout Performance Issues with Dense Datasets**

* **Risk Description:** Rendering large datasets across several detailed panels can cause noticeable frame rate drops and sluggish page scrolling on older devices.  
* **Technical Mitigation:** Avoid complex shadow effects and unnecessary layout filters on repeating grid cells. Use hardware-accelerated CSS properties (like transform and opacity) for all transitions to ensure smooth rendering.

## **Explicit Out-of-Scope Items**

To keep development focused on the core system priorities for Phase 16 and 17, the following items are excluded from this project scope:

* **Active Server Environments:** Setting up local web servers (such as Node.js or Express) or active backend databases is outside the project scope.  
* **External CSS Frameworks:** Utilizing Tailwind, Bootstrap, or other compiled layout frameworks is prohibited; all styling must use vanilla CSS.  
* **Write-Back API Integrations:** The interface is read-only and designed for analysis; it will not send roster changes or trade requests back to the Sleeper platform.9  
* **Automated Trade Negotiation bots:** Building automated trade messaging or communication systems is not included in the scope.

## **Open Decisions for David**

The following design and system choices are pending review and feedback from David:

* **Trade Variance Bounds:** Confirm whether the volatility range for draft pick values should remain fixed at ![][image2] 4, or if it should dynamically scale based on historical draft windows (e.g., widening as the draft approaches).  
* **Age Warning Limits:** Verify if the standard positional age warnings (RB ![][image9], WR ![][image10], TE ![][image11], QB ![][image12]) 1 align with his roster strategy, or if they should be adjusted to better fit his team's competitive window.  
* **Data Degradation Window:** Decide the timeframe for marking local data snapshots as stale (e.g., 24 hours, 48 hours, or 7 days) before the interface automatically triggers the stale-data warning overlay.2

## **Acceptance Criteria for a Future Spec**

A future implementation specification will be considered complete and ready for development when it meets the following criteria:

* **Zero-Dependency Portability:** The interface loads and renders correctly in standard web browsers directly from a local folder, without requiring an active local server or compilation steps.  
* **Complete Data Isolation:** Roster calculations, trade decisions, and valuation metrics are strictly read-only. Modifying visual layout components does not alter the underlying data arrays.  
* **No Verdict Terms:** The interface is completely free of binary decision labels like "Approve," "Veto," or "Reject." Statuses and metrics are shown exclusively as continuous values or warning bands.  
* **High Performance:** Transition animations run smoothly at 60 frames per second on standard laptop displays, verified by browser performance profiles that show no layout bottlenecks during dynamic panel expansions.

#### **Works cited**

1. How big actually is the skill gap in dynasty fantasy football : r/DynastyFF \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/DynastyFF/comments/1sz87kr/how\_big\_actually\_is\_the\_skill\_gap\_in\_dynasty/](https://www.reddit.com/r/DynastyFF/comments/1sz87kr/how_big_actually_is_the_skill_gap_in_dynasty/)  
2. View fantasy football roster details with Sleeper API and Telegram chatbot \- N8N, accessed May 25, 2026, [https://n8n.io/workflows/6655-view-fantasy-football-roster-details-with-sleeper-api-and-telegram-chatbot/](https://n8n.io/workflows/6655-view-fantasy-football-roster-details-with-sleeper-api-and-telegram-chatbot/)  
3. Daily sync of NFL players from Sleeper API to Airtable for fantasy football \- N8N, accessed May 25, 2026, [https://n8n.io/workflows/6602-daily-sync-of-nfl-players-from-sleeper-api-to-airtable-for-fantasy-football/](https://n8n.io/workflows/6602-daily-sync-of-nfl-players-from-sleeper-api-to-airtable-for-fantasy-football/)  
4. This might be stupid but I just feel Odunze is in a better situation : r/SleeperApp \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/SleeperApp/comments/1smekin/this\_might\_be\_stupid\_but\_i\_just\_feel\_odunze\_is\_in/](https://www.reddit.com/r/SleeperApp/comments/1smekin/this_might_be_stupid_but_i_just_feel_odunze_is_in/)  
5. Theme variables \- Core concepts \- Tailwind CSS, accessed May 25, 2026, [https://tailwindcss.com/docs/theme](https://tailwindcss.com/docs/theme)  
6. Theming \- Flux UI, accessed May 25, 2026, [https://fluxui.dev/docs/theming](https://fluxui.dev/docs/theming)  
7. \[v4\] Improve the usage of CSS variables for dark/light mode · tailwindlabs tailwindcss · Discussion \#15083 · GitHub, accessed May 25, 2026, [https://github.com/tailwindlabs/tailwindcss/discussions/15083](https://github.com/tailwindlabs/tailwindcss/discussions/15083)  
8. Positional point differential : r/fantasyfootball \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/fantasyfootball/comments/15rdic4/positional\_point\_differential/](https://www.reddit.com/r/fantasyfootball/comments/15rdic4/positional_point_differential/)  
9. Sleeper API: introduction, accessed May 25, 2026, [https://docs.sleeper.com/](https://docs.sleeper.com/)  
10. Down and Dynasty. Genius is patience — Sir Isaac Newton | by, accessed May 25, 2026, [https://medium.com/fantasy-life-app/down-and-dynasty-3e5759abf110](https://medium.com/fantasy-life-app/down-and-dynasty-3e5759abf110)  
11. 2025 NFL Draft: Wide Receiver Landing Spots \- Fantasy Footballers Podcast, accessed May 25, 2026, [https://www.thefantasyfootballers.com/dynasty/2025-nfl-draft-wide-receiver-landing-spots/](https://www.thefantasyfootballers.com/dynasty/2025-nfl-draft-wide-receiver-landing-spots/)  
12. People with powerhouse Dynasty teams who are (or will be) perennial contenders, let's hear how you built your team, if you have any specific strategy, and ultimately share your roster. : r/fantasybaseball \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/fantasybaseball/comments/d65tvf/people\_with\_powerhouse\_dynasty\_teams\_who\_are\_or/](https://www.reddit.com/r/fantasybaseball/comments/d65tvf/people_with_powerhouse_dynasty_teams_who_are_or/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAaCAYAAADrCT9ZAAADEElEQVR4Xu2WWahOURiGX/NUhkzJlFyQWS4UFyehpFwgIeRCMiWZc0NSREIkShlCioy5UOSUMRcoLmQ8xxQ3yBCZ4n19a59/7+/8Z+8/Dm72U0/n7O9bZ+191lrfWgvIycn5yyyl7Xzwf9GTPqYV9D59QO/SprE2jUP8aWhXSfvF8mlMpD9omU8E1Pcd+py+pC/oI9g7HtITdFLUuLaoT/fDPmyBy0W0oR/oYpQ+Wxq0J7B+J7icZzas3YrwXIe2ostCfEOI1xrLYR3rBcVYSFf5YAZrYKtF/c5zOc9uWLtBPgGb+fe0uU/8CZNhL9zmE6QjvU4b+UQK3egVOg3W7+pkuhoqmTe0ros3pF/od9rF5YoygA5H4WPb0sGFdBVDYB920ifIETrCBzM4RofC/k797kimE2hAa3r3VFhuu094GtDDdB/dSm/TlXQXPU43FZr+ojOs45suPpoedLEsRsL2BKEBV78agJqYAmujsonQZqYS0lLejOQmWpT1KOxuWhbq8AJtTb/S8yEXUY9+o69isSb0Bm0fi2Whgb5GO4TnaCAvVbWojiZBbS7T0+HnW9i7B8bapaJRiegN63AGbPdbRHvE8hE6ntSuWXheS+cU0iWhvpfEnjUz6vNeLOZR/b5Gsn5nwer2t46kubCXaiNJ4yKsnc7mXrAV4TeRNLQS9OE6UytQOE/Vp2asGJ1QvH61uhQ/6+IlcRQ2e1moVvWSUbSc9k+mM9kLq3mPZlD9qi490S6ulREnqn0Neia6SGg5joPVpkb9QCw/PuQ862Av0XGy0eWy0C5/ygcDV2H9dvUJsgeW8+fv/BDXTSuTMlhjLeUx4XdtYqIFbJfWoHii204lCnVcCn1hS7jY7IpzsH41KHH0DbquvkP10tG5rb85FJ5nIqWedfXTaG+BXSTGwv6JnbAR61PVMomWsl5S04d7tPtX0k/0c/g5LJafDqtnxaXquBxWn7dgN6iPwWewYzOie4hpIDURZ1DCJMQ3KdWPDvg0dHfNuvP+S1rCLi6a2WIrMicnJycnJ+c/8xNB6a/Y6s/bdQAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAZCAYAAAB6v90+AAACvElEQVR4Xu2W26tNURTGP3cP7kWkdMotkRJS/gC5lMQLJcKTktyOEnGSByXXUhTK5UXKi5BrR0KeiOQWUa4RxQsSvs+Y05577MVea58H52H96ldrjjn32mvMNeZcEygpaStdaH8fdHSgfXywPTOZ3qFH6UE6oLr7Nx3pXrrUdxRhjg/kYCQ97YOBSXQ93UDHuT7xkM4M11voG7qJTqTD6FzaSq/BEmyITvScD9ZBf3advvUdZA29R2fTefQRXZb0N9GftG9oD6WH6Ci6hLbQWfQWHRHGNIRq/bwP1mEV/YLaxPRweugJSWwK/YrKQy6EjdGECv2/n1jdf7WLFaYriiU2nJ4N+sR20E8upvv/gJWlmApLrFdoD6LbwrVQiV9EG0owUiQx7VKaXa2DM6hN7DZ97mJCyV4K19oJ9ba1nsQC2FsVeouX0cYSjBRJTGtFZSKyEnsJ2xg87+j9pK1kbsDWlBLpHuJrUbl/IbbTE86TsAf0canFH2miF1ApkazEtJbSBCIa58eOpvNpv9DW+tRbjfdXyW+kM0L7n/SGlULqYNjW6uMyzqQ4BfvzSFZiKrEHLiY07pUPJqgEW2HJiLGwkp5OD6B6gnOTpxQX03UulpXYC/rYxcR72Af5b+jeK5L2Hlh1CU3uvqQvN3kSOwKbwWf0aVBl9z1c7w7jbqI2WW04GqtdNAuVZFriQm99ZdI+BvssFCJPYlncRW0SLbCtPS3hgbDtfXkSi3SmV2Af6YgS/Ibqo9Rh1D9X1tBoYprVDy6mB/wMOzlEVMY6MilBj45d6akkos+GTjCR/cl1JlqImqHUq/RjRlwusp9VsQtWlvo2ST30zqR/Gn1NN9Ot9Ams3DxjYOWpUvU0w45l3eh4VNbbf6cHbEdTkj1dX+Q4HeKDCZosrT2Z9bbbLXmOTHnGlJSUlJT84Rf1V5cz7RtceAAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAZCAYAAACGqvb0AAADO0lEQVR4Xu2WWchPQRjGH/uSLSVr9iWKLKVcKES2kmxxQ4TImpTIjcgSopSyu7AkywVZs3yWKMsVSsgSLoiyi2zP0zvDnHGOvr++PvSdp379zzxn5n/mPeeddwbIlStXWVdzMi42A7Uk08lSMji651WbTCUryUzSMHk7VSvIsNgsDbUny8k18pUcTt7+od7kIZlF+pDTZE+iB9CWXCYzyGRyg7wlQ8NOkQaSb7AXVurqTiaQbuQj0oOvQB6TuYFXl7xBMlOKonY98pm8c9exlCV38ReDD5UV/BDYBLtG/gVy0l2XJ59g2dPoRw/LEI2dGHhem8h8/OPBr4VNsEXkH4SNqeja62Hjfdt7GqvsCtWPbIBlXhx8G9ITtlxqkPqw/lpuykKvOrA5NXE0IOVIU3ct0jIuVVnB74RNMC5ee52vyWXpCiz1w0kooPOkFtKD3w1bUvIPkF2wJXeV3CMdXD8VybOwjFPfHaQKeeHaL2HFuVjKCv440oNUwZOvopkmfS3d3xz568ggd50WvKRg5U8LvJqwovuIVA38MbC+Y117H2w5KQuKLQV/JDapY7A/VxqF8sGrysfSRG/BvlzlwFc6bwvaWcFPcX7nyPfLaHzkbyGvYC9te/JW8aTgj8YmLJ30wMaRrzcsX5U/lNa8/kcTCteovpbSNOyfFfwk58fBj3L+6sivTm6SD7BaULCygtchJC29T8C2sTi9FLTGeHWEnRO6wNJW3Iet36ew/37u2r6oZgU/wvmrIl8vVnVEMeiAVbA0UCkeqxfsgf0j36d1qEVkXuQtgE06TcNR2Jdf5vxOkb8RtuZnw7bbAcnbv1clWNU8h+RWJSl1r8O2PC+tc6VY38DTqU5V+gxsfy8iF2FrUV8/TaNhwejkGMoHvyTwWsNOjIcCrx1ZQy4F3inyjDQLvFSp6t4hT8hrh1LxNuwE5qW98wHZSubATmaqsl7VYFuaJhzzBcnqLLWCPVfbkp6pF5SW9top9sOKpAJfjJ8fRxmll63x72EvQsgT+m/Ns0Skh/YgI/Hrnl/SCtNee7fqzR8Vsv9RfqtTkSxTUsB+e10IWyJlRiqsqi1a7/qNi2GuXLlyFaTvLIHXltB+QVcAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAaCAYAAABVX2cEAAABG0lEQVR4Xu2TvUoDQRRGr6YylYRgYylEJKTxAVIkPoAYLG1VrNOkC6SxEoQ0qdIEYnwJQQsDioiCjSBiYzptxEL8OePMsjuX2TRWwh447Mz9hvljRyTjr9TwAZ9xggM//uUCH/Fe7NgDLw1whK/4hUsqy2EbT3HRj8LcYBO/JbzyPm7qYohlPMZ5fMMXzHsjRM5wQdWC7OCea/fE7m47jmUOrxL9qQxxxbUrYiczx46oYzfRn8q16p+InbDq+h1sxHE60X0l2RA7WVQ391WM43R2Jb6vCPMrPOEHlvDSj9MZYVkXoSV2d+d4qLIgM3jnvhpzrHexE66rLMgW3uKsDhx9/MSCDpKsiX2HZmWjeUbmjWpWcayLGRn/mh8UWTQnAIlpcgAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAaCAYAAACzdqxAAAABV0lEQVR4Xu2UvS8EQRjGn/gMSkchmosQNf+AHB2VyFUq8dHpRSiIKFTiNEREIQqVSusaIVEIaiFI0EpEQvC8985kZvZ2k9Wo9pf8kp33mZmbfXf3gIz/pp/e0mfjaRhXMQw395Huh3E1e/SeftK6SGZpocf0hx7RmjCO55KuQRflI5lllc5D58xEsljaaZlOQBcNhnGFPrpAN6BzesI4njG6RAvQRZNhjFpoLxvpNX0K42TkFLKptEA2XgljzNIB2ka/keKBWS5oE/ShfdEDL+uk6+Za7kx+eMrFyeSg/bXIm3Hmjbdpq7kuQTfudnEycoplb3xCX8z1KB13EW7wh/5u0iFvvAs9VQf03bbImyP11P29os3eeBG6gXwIXV69aOrTXi2REfpAG7ya3LpsMOfVhB1T743UA+T/QXr1Tj/oG7TXNjun9Wa8Re/g5r7SQ5NlZGSk5RfvEEdmU//r2gAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJcAAAAaCAYAAAC6sc5/AAAFSUlEQVR4Xu2Zd6hcRRSHj703rLEQo8aCimIX21OwoP8oWIg1EQuKDXuPUaPYsGJJLE/9Q1FUIthC1GfvBSxYIZYIKvYG9t/Hudc3O2/27dwnu/hkPvixe8/M7t45c+6ZM7NmhUKhUCgUMplfWl/aTRoT2BeXVgiuC4VslpOuln6UXpSmSfdLV0rLS89Lm/3Tu3csIR0hXSIdY60B/39hG2lKpV2jNhgrHSttJS0qjZP2lg4IOwXMLU2SVoobhqFrfubGv5dul5aJ2k6Wfqg0b9TWbdY0D/SjpcOkN82Df/ew0yjnUnO/7yddIf0hzZIWDPpsL/0VaY60RdAHDpXulr4y77Npa3Nbuubno8xvhKhNwVL4p/RI3NADBqSDgutlpd+ln6r3o50+6XXzkqOGlYL5uDiw9UmfmgcAq8kZli5RCA7KmcusWXANWBf8TGolcG6OGyJek06NjV2G1P6r+f2tGNgfM3fcIYGt11AmzBUbI+aJDQnONB/L9YFt28pGMIW2/uC6E6dZfnB1xc+LSF+af0GntZmstXls7AHXSg9Y63KMjXs+OLABNQO1yOrSGtL4SrxfLejHd+0gLVVdL2n+tOOPTrAMvSH9Jn1u/lC2q00oJ8KMlILJf0HaI7BR+zK+jwMbNVl/cN2JJsEFTfycxYnmH34lbkjA5HR6UnvFS+YpO0zX50k/m48nJeoYAg3uMA8KasyTpDulqdK7NvwYKaSfMw/Ehc2XJZanj8wL4AUGu9rK0lPBdRP4fu75qsC2tTSjsj1qPmcEXDuaBleKlJ+zwVHcwOS4YYQcKT3RRgOVHjdPtzjocj7UkB3N7/nGwHa6dJe0c/V+uvmuaqY0oXq/XtWX5eVcaV3z7+FeKJxxJMG5UNUvBU/wlrHRPMhuMs9kN5gHwWxL7/pyeMY88NcJbPzu19Im1fVa0hfmwZ3i3wZXys+N+Mb8CzaKG/6jLCa9I91rfhYHvLL81Bmn39wxQKHMUhlC/cCkTTQfe320so8Nfq4dnbI3AXucdIK11i5NYKfGrpxlO4SgHxvZbjHPLCz7MXVwjeToKOXnRsxn/uO/xA0JzrehA+s11AIPmWeIdoUyGYinmYnAKd+2NrfAskgmoJhtAv0PN9/unyNt3NLayoY2fCaM4bjhM8vPNizlzGGqJqqDq2mdnOPnLKgVuAFqiXZQHJOmc+DJ5unPVa4TgcFeFFzzDwKTEXKg+bILG5iPjWI9xYfSfbExA4reh6XjzZdXim4ySHw2SBCy5HYq6GsYDxuFtQMbZ481T0svW+vDwO8zRo6SYkYaXDl+zuJC8xuggEzBQKhlqFly2MV8a52rSf6xjkyRTols1FZ7RjaOS7BDn/nYUo5hZ0xbOHk5bGe+5IXwpLMxmm3uTyaDB+dW8wnOYRXzQOS1hpWFXSSwFM8xX6rC3RzHF4wjNT91cMWHrEBWT2XcXD9nsbT0vvSeDV3jKVJJjxMje6+paxAyEhMwID0rfWc+kTVMPM6s68dVq2syTAxFPm1ktyZwXBDXcDWce10jfWD+Nxm1V069QmZ9y/xEnE0O43xSelu6J+jHgWq4QeBzZE2OiFJMNh/jTnGDeV1K2/6BLdfPjRhnfoP82KvSWdJt5oGV2hn1EuoVClbuLRZHC+HfI9eZZ6664OYVx3BEEUOGIQsMV5z3iqk2dGy1Lgj68bATfP3mgcMS+qD5mVgISzYBTr3J+AkYEsjZQR+W0U9ssNhv4ucRwU5nL2nf6v1og3On2AljLB1A7IboPxoZbz5HbBYKhUKhUCgUCoVCoVAoFAqFQpf4G2FYQxCQCymTAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADoAAAAaCAYAAADmF08eAAAB+0lEQVR4Xu2VTSilURjHn2HKVwobX0UsRBYyC2UjzMhC2UlshrKSUkKJlULKQtlYWRGTQUn5SD5qatQsbShErKfxndXM//Gca8497/ve60aXt86vfnXf/zkv97nn4yGyWCyWlxEHV2CuOQDyYQcchnXGmO8YhX9hkZFXwTPYCavhFvwWNMNHlMEbchYaCy9gt5alwWv4Vct8AW/ZXThGzkLrVfZJy5gfcNPIgvhIsvyp6jmFZM8nPc2IPkOwGfaSs9BxleVpGbMMH0jqcWUWTsEr2APnSP7RIfygzYsWpXBBfXYrdEZlmVrGzKs83cgfqYCDsJhkEh/qePgL3sGE/1MdlJNsLy934DbJ32RXSbZkKHg1+J0s9exW6LrKzIL4MjLnPtFGMtBCMokvAKYR1qjP0aQftmrPboWuqSxDy5hAoQVGHgRv3d8wxhyIIlwMnzMdt0KnVZatZcx3lfMN7MkxXDLDMPDlxav+XD+TtAYv2kl64yk8UV6SfPlzuKfmefXWDXhLIe4V/mX4RW6+kVAIByKwj8KfUZMJchZVqbJaLWMO4KKRBdFE8mKJOfAOmCTnd+NdsU/SZgLwubyHX7TMwQjJr+G55G8A91A+Tn9I2h7fHz+18RySLc53Sxc8IlmwkCTDRDP0AdyKuMU1kLOnWiwWi8VieSX+AevFc2wsjezCAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAZCAYAAABHLbxYAAACEElEQVR4Xu2WS0hVURSGl2Y+8YmpEwcOgiQMJ4aT0nKWTgRxoE4kjEaKSRNRRMQUaZCKEYggShCEijhw4gMKpUZGaoQDByqOpUaCof9y7aPr7CT2uQoang8+7r3/Pueyz17rLi5RSMj15gHsND6x1mwKYTusgonW2gklcBZWwmhrLVJew3FYC9/AP3AOxuuLQBxchKOwDPbCGX2BTQbsgMvwKYz1LweiFH6DKSrrh4ewT2XMGBxRn3nT/FDpKjuTJPgCfoXN5nNQ2kg29U5lD022o7JnJstXWQVJCzjDJeEv4g3zSfOJu1JEch+3kkcWyaa2VDYF98z7VJip1gJzA9bAJZKy5fiXnSkn2eiAyrbhT9hN0gIrJK3HDxUx3LMfSUrHpx0UftBfdFpm74QPYIPJouAkXKUIftQJsJGklC9hsn/ZCW6h3/Cxyu6SbHSfpGoez03OFXCCe6YVfiG52R4rrjyCuyR9q7lFsqENK68z+ZCV/0U27IGfSXpTP21QCkjKeEdlTeaVS8ut8F2tMTx37YnhIxcOkgxlHhHcL+eBv2/BvHrcJGkhjw/kH1eMN7KqrfyYYjhNMusugjS4DtfgPMkQ/wR/wAl1XQnJcL+vsvck7Xbeg3KCxw2fylm+UtcxLXATdpG0G48n3SpXCp7N9SR/XP55kjwjbzuaZ+65FO7BYUffwhi5LSQk5L/jCJobaqE1i1SvAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAZCAYAAABHLbxYAAACIElEQVR4Xu2WzUsWURTGn7KyiD4UrMCCQgRb1M5wo761aJFtWoW5S5BWRoERJYQLC8KFHyCCglFLkYggF1lBltouSAuCCEv6AxTa9fE8nHnzzH0VZt4KieYHv8Wce2fe89577pkBMjL+b+ppV+SpYCzPJpqDzTlLd8VGAxrpBD1DNwZjxdJD79EW2ku/0Um61c3ZQO/SUXqcnqcf6TE3p4ByeoNO01a6JT6cihx9TXe6WB/9QW+7mH5n2F2LJvqObg7iBWynl+kreim6TksnLKkhF2uIYosuNkIfu2uxGzavIoivSSltgyWsldaKJ6UWdp9KKc8eWAKfXOxiFNMq50tC2//014wUlNBz9CXsgfviw4nRliqpfherpJ+j+Ht6FVZ6iheNanYMtnVa7bTojy7Rw0G8ii7DkpV3UFy5YRtth21lB90RH06ESkjJnAjiZfQF7LlX6FdYso9gO5kI9bNrdJZeQLytpEFt5wusbkMe0lvuuprOwJJtdvFV2Qu7eQpWm4n/2SocoW9ojYvpAIn99Ds94MaETr1KxNdyDN0wAGvKp2HN+HfQ83R6fSLqjSohoS6il0CYqLhPr4dBUUcfwHrdn0CrMk/n6BP6jD6nb+m4m6c/oheBX5SDdAF2yP463Vg5xaE33TytqmryA+xdr+1Wqaz1XbCuaDXVsnQeTiL+2i1APVInLomHonvWhaOwj4MkDsI+zTIyMv5FfgKZAmk77T2SNQAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAZCAYAAABHLbxYAAACLUlEQVR4Xu2WS0gWURiG37S8ZBdpYwUtgiIlaeEiLEJbRJuKaNGFtkG4UjRKMyowRIoQVOhCCynSiNoURCIupKtu3LoQdwW6sk2LILL37TujZ2b+v39+EROaB57FvHP+8ZtzvnNGICXl/2YbvUYv0cN0beiuUUBP0E7aDPtNVurpW3oK9sPloJU+o6fpSTpLP9AN3pgi+pK+oXX0Cv1KD3hjYmyhN+knegH2kKWiZ/2iA17WQefpVS9rgL3Aei/TzE4h8+yHKKMtdBy2FLrOFxX6g057WVDoDS+boK+9a3EENu5QJM9KMb0IK1gzrT+eD+q1Td71MKyAPe663F0/Xhhh1Lj8eiTPSSE9Tz/SO3Rr+HZO1sD69TtshQJ2wwp66GVir8vvR/LEqGdf0C+w2U7CQdgGUh+qIL10gDZMpoKqXP48kueklDbCWuAy3Ri+nQi92BCsJytdVgsr6EEwyBEUOhjJs7KZttMx2O4sCd/Om6MIz9Qud/1oYYRR7fLeSB6jgnbR97De9JcrKZq1u1jcOGInrACdBloVnac/EV9itYvGqa8zsoP20RF6HLYJlko/4hul3mUzWHz2KP0cDHCcg43bF8n/oH55Bfs6LAdqlW90v5e1wQq47WVnYafBdi97AnuBFaObvoN961XcHO1BfKVu0UnaRJ/Cvoz++bsi6FA/BttIf9uMOpvPwI6sdZF7IXRG6gBOojbFP0ONq2MiifeQ4B+GlJSUVcpv5p5pYKgg7uIAAAAASUVORK5CYII=>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAZCAYAAABHLbxYAAACKUlEQVR4Xu2WS6hPURSHl0fer0y8UpdySZGRZMAdyISSgUIZKVG64iZvykQeia4IAxkgGRmRlPI2YaQYGCgDRG5xEwrfr3XOv733/f/vPedySc5X32CvtTtnn3PWXvuYVVT830zAXdiGLTgwyjr9cCkewFU4OU7HLMRruBz7J7nesg0v4Qpchm/wLo4I5kzEm7gbF+AZ/IwrgzldGIv78D6uxUFxuhS61ne8EMT24w/cEcSO4Tucl411z2/4AYfmkxoxHLfgI9ycjcuihX7BF0EsX+jeIHY4i63JxkPwK37CYfmknhiM68wXrDetm5dB9TkqGN8wX9T0IKYymxaM55vPUcmUZgCuxnt4CMfH6R7RZlG9dpp/oUZowU/MX0xTnCqH6ucKvjJ/20XQG9IG0kY6bf7Q9TiFT/EtzkpyhVFRt5o/6VYcGacLoQe7jo9xRpILWYQfcU+a6I7RuBMf4nrzQv8VFpvX3+U0kaCuo3kz00TKOPPme8e8Nht9ru7QWzti8caZYr4AdYP8q2zCjbUZznnzeVpDXXQitJs3YJ0U2gS95Zz5zVSXOTpUFHttfu2mbCzV+HNuZbENQayGGu5V89Phd6BS6cC5QWy7+QIOZmPV7Uu8WJvhPft95qQg3qccxdvmZ70Wp9PmuMVfqhmf4Qnz/4EH+BznBHP+CGNwiflGarQZtXC1JP2QTE1yXVCPVMMtojbFX2M2ni3oSav/u1ZRUfEv8BMC5WYjE/X2OgAAAABJRU5ErkJggg==>