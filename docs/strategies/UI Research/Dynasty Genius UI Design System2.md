# **Design System Synthesis and Technical Specification for Dynasty Genius Phase 17 UI**

## **Executive Recommendation**

To support the transition of Dynasty Genius from Phase 16 to Phase 17, this technical specification establishes a zero-dependency, local file-system compatible analytics cockpit designed to run under the file:// protocol directly inside standard web browsers.1 The system transitions the user interface from simple data displays to a multi-layered analytics dashboard. This transition supports the integration of Phase 17 core features: Sleeper universe valuation, league opportunity mapping, and Market Divergence v2.3  
The architectural core of this design system is its independence from external frameworks, Node.js runtimes, package compilation steps, or local server requirements.1 By leveraging modern browser APIs, native CSS custom properties, CSS Grid layouts, and the client-side Web Storage API, the interface delivers high performance and low rendering latency directly from local files.6  
The layout enforces visual separation between model-equivalent value lanes and market-equivalent value lanes.5 Model-equivalent metrics, calculated using the proprietary Engine A and Engine B predictive models, are displayed in a primary emerald-to-teal visual lane. Market-equivalent metrics, sourced from external platforms like FantasyCalc or KeepTradeCut, are shown as secondary purple overlays used solely for price discovery.5 These market values are never used as inputs for internal predictive calculations.5  
Engine outputs are represented by the Player Value Object (PVO) and the expected Value Above Replacement (![][image1]), which is calculated as:  
![][image2]  
where ![][image3] represents the player's modeled value and ![][image4] represents the dynamic roster capacity cost.  
To prevent cognitive bias, the interface avoids binary labels like "win/loss" or "buy/sell." Instead, it represents value deltas using continuous numerical margins and calibrated ![][image5] prediction intervals 11:  
![][image6]  
This range defines the ![][image7] to the ![][image8] percentile uncertainty limits.11  
Client-side local storage caches read-only Sleeper API payloads to protect the user's IP from being blocked by rate-limiting controls.2 The interface also uses direct ID validation gates to prevent UI-first recommendations without model verification.5

\+-----------------------------------------------------------------------------------+  
|                            DYNASTY GENIUS PHASE 17 COCKPIT                        |  
\+-----------------------------------------------------------------------------------+  
| ACTIVE LEAGUE: 12-Team SuperFlex (Sleeper ID: 82914\)                              |  
\+-----------------------------------------------------------------------------------+  
| MODEL-EQUIVALENT VALUATION (ENGINE A/B)   |   MARKET PRICE DISCOVERY OVERLAY      |  
| Color: Emerald-Teal Gradient              |   Color: Neon Purple/Cyan             |  
|                                           |                                       |  
| Player A: PVO \= 8,420                     |   Market Value: 7,950                 |  
| xVAR: \+1,240                              |   Implied Rank: QB12                  |  
| Capacity Cost: 210                        |   Divergence Delta: \-470              |  
|                                           |                                       |  
| \[======\*======\]    |   \[===========\[===o=======\]    |  
| 5th        90% Uncertainty       95th     |   Market Pricing Position             |  
\+-----------------------------------------------------------------------------------+  
| TRADE LAB SIMULATOR: Player A \<---\> Future Draft Capital (2027 1st)               |  
\+-----------------------------------------------------------------------------------+

## **Evidence Table**

The layout structure and engine integrations are based on verified browser capabilities and data parameters. The table below outlines these elements to establish a technical baseline:

| Integration Layer | Ingestion Point / API Path | Source Reference | Functional Application in Phase 17 UI |
| :---- | :---- | :---- | :---- |
| **Sleeper Base Endpoint** | https://api.sleeper.app/v1 | 13 | Primary ingest point for read-only user, league, roster, and matchup datasets. |
| **Sleeper Rate Limits** | Max 1,000 API calls per minute | 3 | Enforces client-side rate throttling and local storage cache checks to prevent IP bans. |
| **User Resolution** | /user/\<user\_id\> or /user/\<username\> | 3 | Resolves Sleeper identities and fetches user profile avatars. |
| **League Retrieval** | /user/\<user\_id\>/leagues/nfl/\<season\> | 3 | Retrieves active league lists, team counts, roster slot configurations, and scoring parameters. |
| **Roster State Ingestion** | /league/\<league\_id\>/rosters | 3 | Fetches roster IDs, player allocations, co-owner assignments, and tax squad rosters. |
| **User Directory Mapping** | /league/\<league\_id\>/users | 3 | Maps display names, team nicknames, and avatars to respective roster objects. |
| **Matchup Ingestion** | /league/\<league\_id\>/matchups/\<week\> | 3 | Captures starters, total points scored, and matchup IDs to evaluate head-to-head strength. |
| **Playoff Bracket** | /league/\<league\_id\>/winners\_bracket | 3 | Evaluates post-season progressions to calculate dynamic pick values. |
| **Draft Pick Tracking** | /league/\<league\_id\>/traded\_picks | 3 | Isolates future draft assets traded across teams to resolve roster draft capital. |
| **Client-Side Storage** | Window.localStorage API | 1 | Caches parsed JSON structures up to 5 MB per local context, eliminating external databases. |
| **Visual Radial Meters** | conic-gradient() CSS properties | 9 | Renders circular progress meters and radial value distributions on the GPU without JS. |
| **Uncertainty Bounds** | **![][image9]** (5th percentile) & ![][image10] (95th percentile) | 11 | Standardizes the ![][image5] prediction interval to map engine variance visually. |
| **High-Density Grids** | CSS Grid & Flexbox templates | 6 | Powers multi-column responsive dashboard matrices with sub-millisecond redraws. |

## **The Five Core Layout Specifications**

The design system is split into five core modules. Each module contains detailed CSS, HTML, and JavaScript structures to ensure high performance and smooth browser rendering.

\+-----------------------------------------------------------------------------------+  
|                            CORE LAYOUT ARCHITECTURE                               |  
\+-----------------------------------------------------------------------------------+  
|  1\. DESIGN TOKEN ENGINE                                                            |  
|     ├── Unified Palette (Model Emerald vs. Market Purple)                         |  
|     └── Typography, Spatial Scale, & Layer Coordinates                           |  
|                                                                                   |  
|  2\. TRADE LAB SIMULATOR                                                           |  
|     ├── Dual-Track Canvas & Drag-and-Drop Dropzones                               |  
|     └── Strict Player ID Validation & Linear Uncertainty Renders                  |  
|                                                                                   |  
|  3\. ROSTER AUDIT VISUALIZER                                                       |  
|     ├── Roster Capacity Cost Meter & Standings Matrix                             |  
|     └── Conic-Gradient Progress Rings & Mask Layers                               |  
|                                                                                   |  
|  4\. LEAGUE PULSE                                                                  |  
|     ├── Interactive Matchup Matrix & Transaction Ticker                           |  
|     └── Read-Only Sleeper API Integration & Local Cache Controller                |  
|                                                                                   |  
|  5\. MICRO-ANIMATIONS ENGINE                                                       |  
|     ├── Hardware-Accelerated Transitions                                          |  
|     └── Mouse-Tracking Radial Spotlights & Dynamic Focus Highlighting             |  
\+-----------------------------------------------------------------------------------+

### **1\. Design Token Engine (Tokens)**

The token engine establishes the layout's visual hierarchy, typography, and colors using native CSS variables. The system uses a strict palette that separates internal predictive values from external market pricing overlays.5

CSS  
:root {  
  /\* System Depth & Base Surfaces \*/  
  \--bg-base: \#080a0f;  
  \--bg-surface-lowest: \#0e111a;  
  \--bg-surface-mid: \#151a26;  
  \--bg-surface-highest: \#1e2538;  
  \--border\-subtle: rgba(255, 255, 255, 0.04);  
  \--border\-strong: rgba(255, 255, 255, 0.12);

  /\* Model-Equivalent Lane (Emerald & Teal Track) \*/  
  \--color\-model-primary: \#10b981;  
  \--color\-model-secondary: \#0d9488;  
  \--color\-model-glow: rgba(16, 185, 129, 0.15);  
  \--color\-model-bg: rgba(16, 185, 129, 0.02);  
  \--gradient-model: linear-gradient(135deg, var(--color-model-primary), var(--color-model-secondary));

  /\* Market Price Discovery Lane (Neon Purple & Cyan Track) \*/  
  \--color\-market-primary: \#a855f7;  
  \--color\-market-secondary: \#06b6d4;  
  \--color\-market-glow: rgba(168, 85, 247, 0.15);  
  \--color\-market-bg: rgba(168, 85, 247, 0.02);  
  \--gradient-market: linear-gradient(135deg, var(--color-market-primary), var(--color-market-secondary));

  /\* Status Neutral Elements \*/  
  \--color\-text-primary: \#f3f4f6;  
  \--color\-text-secondary: \#9ca3af;  
  \--color\-text-muted: \#6b7280;  
  \--color\-warning: \#f59e0b;

  /\* Typography Scale \*/  
  \--font-family\-mono: 'JetBrains Mono', 'Fira Code', monospace;  
  \--font-family\-sans: 'Inter', system-ui, \-apple-system, sans-serif;  
  \--text-xs: clamp(0.7rem, 0.65rem \+ 0.25vw, 0.8rem);  
  \--text-sm: clamp(0.8rem, 0.75rem \+ 0.25vw, 0.95rem);  
  \--text-base: clamp(0.95rem, 0.9rem \+ 0.25vw, 1.1rem);  
  \--text-lg: clamp(1.15rem, 1.1rem \+ 0.25vw, 1.35rem);  
  \--text-xl: clamp(1.4rem, 1.3rem \+ 0.5vw, 1.75rem);

  /\* Layout Spacing \*/  
  \--space-xs: 4px;  
  \--space-sm: 8px;  
  \--space-md: 16px;  
  \--space-lg: 24px;  
  \--space-xl: 32px;  
    
  /\* Layer Coordinates (Z-Index Hierarchy) \*/  
  \--z-index\-base: 1;  
  \--z-index\-card: 10;  
  \--z-index\-overlay: 100;  
  \--z-index\-tooltip: 1000;  
}

The system is optimized for high-density layouts.6 The typography system uses CSS clamp() functions to keep text readable on different viewport widths without needing layout-breaking media queries.

HTML  
\<div class\="dg-token-demo" style\="background: var(--bg-base); color: var(--color-text-primary); font-family: var(--font-family-sans);"\>  
  \<div style\="border: 1px solid var(--border-strong); padding: var(--space-md); border-radius: 8px; background: var(--bg-surface-lowest);"\>  
    \<span style\="font-family: var(--font-family-mono); font-size: var(--text-xs); color: var(--color-text-muted);"\>SYSTEM STATUS: ACTIVE\</span\>  
    \<h2 style\="font-size: var(--text-lg); margin-top: var(--space-xs); font-weight: 700;"\>Model Integration Alpha\</h2\>  
  \</div\>  
\</div\>

| Element Group | Property | System Value | Visual Application |
| :---- | :---- | :---- | :---- |
| **Typography** | Font Family Mono | JetBrains Mono, Fira Code, monospace | Code blocks, statistical value grids, and data labels. |
| **Color Base** | Background Base | \#080a0f | Main browser viewport background. |
| **Color Base** | Surface Low | \#0e111a | Base background color for workspace grids and modules. |
| **Model Lane** | Model Primary | \#10b981 (Emerald) | Visual indicators representing internal project forecasts. |
| **Market Lane** | Market Primary | \#a855f7 (Purple) | External price overlays from KeepTradeCut and FantasyCalc.5 |

### **2\. Trade Lab Simulator (Trade Lab)**

The Trade Lab Simulator lets users evaluate transactions side-by-side using a clean, split-lane visual canvas.6 To prevent cognitive bias, the interface avoids binary labels like "win" or "lose," showing value deltas using continuous numerical margins and standard error indicators.11

HTML  
\<div class\="tradelab-canvas" style\="display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-lg); background: var(--bg-base); padding: var(--space-lg); border-radius: 12px; border: 1px solid var(--border-strong);"\>  
  \<div class\="lane-model" style\="background: var(--bg-surface-lowest); border: 1px solid var(--color-model-primary); padding: var(--space-lg); border-radius: 8px; position: relative;"\>  
    \<div style\="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-md);"\>  
      \<h3 style\="font-family: var(--font-family-sans); font-size: var(--text-base); color: var(--color-model-primary); font-weight: 700; margin: 0;"\>Predictive Model-Equivalent\</h3\>  
      \<span style\="font-family: var(--font-family-mono); font-size: var(--text-xs); background: rgba(16, 185, 129, 0.1); color: var(--color-model-primary); padding: 2px 6px; border-radius: 4px;"\>Engine A / B\</span\>  
    \</div\>  
      
    \<div id\="model-dropzone" class\="dropzone" style\="border: 2px dashed rgba(16, 185, 129, 0.2); background: var(--bg-surface-mid); padding: var(--space-xl); border-radius: 6px; text-align: center; margin-bottom: var(--space-md); transition: background 0.2s ease-in-out;"\>  
      \<p style\="font-family: var(--font-family-sans); font-size: var(--text-sm); color: var(--color-text-secondary); margin: 0;"\>Drag player from roster list to assess model values\</p\>  
    \</div\>

    \<div class\="valuation-readout" style\="display: flex; flex-direction: column; gap: var(--space-sm);"\>  
      \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-sm);"\>  
        \<span style\="color: var(--color-text-secondary);"\>Player Value Object (PVO):\</span\>  
        \<span id\="model-pvo-val" style\="color: var(--color-model-primary); font-weight: 700;"\>8,420\</span\>  
      \</div\>  
      \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-sm);"\>  
        \<span style\="color: var(--color-text-secondary);"\>Capacity Cost ($R\_c$):\</span\>  
        \<span id\="model-capacity-val" style\="color: var(--color-warning);"\>210\</span\>  
      \</div\>  
      \<hr style\="border: none; border-top: 1px solid var(--border-subtle); margin: var(--space-xs) 0;"\>  
      \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-sm);"\>  
        \<span style\="color: var(--color-text-secondary);"\>Expected xVAR Delta:\</span\>  
        \<span id\="model-xvar-val" style\="color: var(--color-model-primary); font-weight: 700;"\>\+1,240\</span\>  
      \</div\>  
        
      \<div class\="uncertainty-wrapper" style\="margin-top: var(--space-md);"\>  
        \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-xs); color: var(--color-text-muted); margin-bottom: var(--space-xs);"\>  
          \<span\>Q05: \+800\</span\>  
          \<span\>90% Uncertainty Interval\</span\>  
          \<span\>Q95: \+1,600\</span\>  
        \</div\>  
        \<div class\="uncertainty-track" style\="height: 6px; background: var(--bg-surface-highest); border-radius: 3px; position: relative; overflow: hidden;"\>  
          \<div class\="uncertainty-range" style\="position: absolute; left: 20%; width: 60%; height: 100%; background: linear-gradient(90deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.6) 50%, rgba(16, 185, 129, 0.1) 100%);"\>\</div\>  
          \<div class\="uncertainty-point" style\="position: absolute; left: 55%; width: 6px; height: 6px; background: var(--color-text-primary); border-radius: 50%; top: 0;"\>\</div\>  
        \</div\>  
      \</div\>  
    \</div\>  
  \</div\>

  \<div class\="lane-market" style\="background: var(--bg-surface-lowest); border: 1px solid var(--color-market-primary); padding: var(--space-lg); border-radius: 8px; position: relative;"\>  
    \<div style\="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-md);"\>  
      \<h3 style\="font-family: var(--font-family-sans); font-size: var(--text-base); color: var(--color-market-primary); font-weight: 700; margin: 0;"\>Market Price Discovery\</h3\>  
      \<span style\="font-family: var(--font-family-mono); font-size: var(--text-xs); background: rgba(168, 85, 247, 0.1); color: var(--color-market-primary); padding: 2px 6px; border-radius: 4px;"\>KTC / FantasyCalc\</span\>  
    \</div\>

    \<div id\="market-dropzone" class\="dropzone" style\="border: 2px dashed rgba(168, 85, 247, 0.2); background: var(--bg-surface-mid); padding: var(--space-xl); border-radius: 6px; text-align: center; margin-bottom: var(--space-md); transition: background 0.2s ease-in-out;"\>  
      \<p style\="font-family: var(--font-family-sans); font-size: var(--text-sm); color: var(--color-text-secondary); margin: 0;"\>Drag player from roster list to assess market values\</p\>  
    \</div\>

    \<div class\="valuation-readout" style\="display: flex; flex-direction: column; gap: var(--space-sm);"\>  
      \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-sm);"\>  
        \<span style\="color: var(--color-text-secondary);"\>Market Value Ingest:\</span\>  
        \<span id\="market-pvo-val" style\="color: var(--color-market-primary); font-weight: 700;"\>7,950\</span\>  
      \</div\>  
      \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-sm);"\>  
        \<span style\="color: var(--color-text-secondary);"\>Implied Roster Position:\</span\>  
        \<span id\="market-rank-val" style\="color: var(--color-market-secondary);"\>QB12\</span\>  
      \</div\>  
      \<hr style\="border: none; border-top: 1px solid var(--border-subtle); margin: var(--space-xs) 0;"\>  
      \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-sm);"\>  
        \<span style\="color: var(--color-text-secondary);"\>Model-to-Market Divergence:\</span\>  
        \<span id\="market-divergence-val" style\="color: var(--color-market-primary); font-weight: 700;"\>\-470\</span\>  
      \</div\>  
        
      \<div class\="uncertainty-wrapper" style\="margin-top: var(--space-md);"\>  
        \<div style\="display: flex; justify-content: space-between; font-family: var(--font-family-mono); font-size: var(--text-xs); color: var(--color-text-muted); margin-bottom: var(--space-xs);"\>  
          \<span\>Low Consensus\</span\>  
          \<span\>Market Consensus Range\</span\>  
          \<span\>High Consensus\</span\>  
        \</div\>  
        \<div class\="uncertainty-track" style\="height: 6px; background: var(--bg-surface-highest); border-radius: 3px; position: relative; overflow: hidden;"\>  
          \<div class\="uncertainty-range" style\="position: absolute; left: 35%; width: 45%; height: 100%; background: linear-gradient(90deg, rgba(168, 85, 247, 0.1) 0%, rgba(168, 85, 247, 0.6) 50%, rgba(168, 85, 247, 0.1) 100%);"\>\</div\>  
          \<div class\="uncertainty-point" style\="position: absolute; left: 50%; width: 6px; height: 6px; background: var(--color-text-primary); border-radius: 50%; top: 0;"\>\</div\>  
        \</div\>  
      \</div\>  
    \</div\>  
  \</div\>  
\</div\>

JavaScript  
// Strict ID-based Validation Engine  
class TradeValidationGate {  
  constructor(activePlayerRegistry) {  
    this.playerRegistry \= activePlayerRegistry; // Dictionary containing validated Sleeper IDs  
  }

  // Prevents fuzzy matching or UI-first recommendations without direct ID validation  
  validatePlayerIngestion(playerId) {  
    if (\!playerId) {  
      throw new Error("Validation Error: Player ID is null or undefined.");  
    }  
      
    const validatedPlayer \= this.playerRegistry\[playerId\];  
    if (\!validatedPlayer) {  
      throw new Error(\`Validation Error: Player ID ${playerId} is not mapped in the internal registry.\`);  
    }

    // Returns structural player metadata, blocking fuzzy matches   
    return {  
      id: validatedPlayer.player\_id,  
      name: validatedPlayer.full\_name,  
      position: validatedPlayer.position,  
      team: validatedPlayer.team,  
      pvo: validatedPlayer.pvo\_vector,  
      modelChecked: true  
    };  
  }  
}

The validation class processes player drops into the Trade Lab, ensuring that only players mapped directly in the internal registry are ingested.5 If the database fails to locate an exact ID match, the entry is rejected, preventing mismatched player profiles.5

### **3\. Roster Audit Visualizer (Roster Audit)**

The Roster Audit Visualizer monitors team construction, roster capacity costs, and taxi squad allocations.3 The system uses custom conic-gradient() progress rings and radial CSS masks to display metrics dynamically without loading heavy JavaScript canvas libraries.9

HTML  
\<div class\="roster-audit-panel" style\="background: var(--bg-surface-lowest); border: 1px solid var(--border-strong); border-radius: 8px; padding: var(--space-lg); display: grid; grid-template-columns: 200px 1fr; gap: var(--space-xl); align-items: center;"\>  
  \<div class\="radial-gauge-container" style\="display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative;"\>  
    \<div class\="progress-ring-wrapper" style\="width: 140px; height: 140px; position: relative; display: flex; align-items: center; justify-content: center;"\>  
      \<div id\="capacity-radial-meter" class\="progress-ring" style\="  
        width: 100%;   
        height: 100%;   
        border-radius: 50%;   
        background: conic-gradient(var(--color-model-primary) calc(var(--capacity-percentage, 0\) \* 3.6deg), var(--bg-surface-highest) 0deg);  
        mask: radial-gradient(circle, transparent 65%, black 66%);  
        \-webkit-mask: radial-gradient(circle, transparent 65%, black 66%);  
        transition: background 0.3s ease-in-out;"\>  
      \</div\>  
      \<div class\="ring-label" style\="position: absolute; display: flex; flex-direction: column; align-items: center; justify-content: center;"\>  
        \<span id\="radial-capacity-text" style\="font-family: var(--font-family-mono); font-size: var(--text-lg); font-weight: 700; color: var(--color-text-primary);"\>84%\</span\>  
        \<span style\="font-family: var(--font-family-sans); font-size: var(--text-xs); color: var(--color-text-muted);"\>Capacity\</span\>  
      \</div\>  
    \</div\>  
  \</div\>

  \<div class\="roster-matrix-details" style\="display: flex; flex-direction: column; gap: var(--space-md);"\>  
    \<h4 style\="font-family: var(--font-family-sans); font-size: var(--text-base); color: var(--color-text-primary); font-weight: 700; margin: 0;"\>Roster Capacity & Position Audit\</h4\>  
      
    \<div style\="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-md);"\>  
      \<div style\="background: var(--bg-surface-mid); padding: var(--space-sm); border-radius: 6px; border-left: 3px solid var(--color-model-primary);"\>  
        \<span style\="font-family: var(--font-family-sans); font-size: var(--text-xs); color: var(--color-text-muted); display: block;"\>Active Slots\</span\>  
        \<span id\="active-slots-count" style\="font-family: var(--font-family-mono); font-size: var(--text-sm); font-weight: 700; color: var(--color-text-primary);"\>24 / 25\</span\>  
      \</div\>  
      \<div style\="background: var(--bg-surface-mid); padding: var(--space-sm); border-radius: 6px; border-left: 3px solid var(--color-model-secondary);"\>  
        \<span style\="font-family: var(--font-family-sans); font-size: var(--text-xs); color: var(--color-text-muted); display: block;"\>Taxi Squad\</span\>  
        \<span id\="taxi-slots-count" style\="font-family: var(--font-family-mono); font-size: var(--text-sm); font-weight: 700; color: var(--color-text-primary);"\>4 / 5\</span\>  
      \</div\>  
      \<div style\="background: var(--bg-surface-mid); padding: var(--space-sm); border-radius: 6px; border-left: 3px solid var(--color-warning);"\>  
        \<span style\="font-family: var(--font-family-sans); font-size: var(--text-xs); color: var(--color-text-muted); display: block;"\>Capacity Cost ($R\_c$)\</span\>  
        \<span id\="roster-rc-score" style\="font-family: var(--font-family-mono); font-size: var(--text-sm); font-weight: 700; color: var(--color-text-primary);"\>1,480\</span\>  
      \</div\>  
    \</div\>

    \<div class\="high-density-roster-grid" style\="max-height: 150px; overflow-y: auto; border: 1px solid var(--border-subtle); border-radius: 6px;"\>  
      \<table style\="width: 100%; border-collapse: collapse; font-family: var(--font-family-mono); font-size: var(--text-xs); text-align: left;"\>  
        \<thead\>  
          \<tr style\="background: var(--bg-surface-mid); border-bottom: 1px solid var(--border-strong); color: var(--color-text-muted);"\>  
            \<th style\="padding: 6px var(--space-sm);"\>Player\</th\>  
            \<th style\="padding: 6px var(--space-sm);"\>Position\</th\>  
            \<th style\="padding: 6px var(--space-sm); text-align: right;"\>PVO Vector\</th\>  
            \<th style\="padding: 6px var(--space-sm); text-align: right;"\>Capacity Cost\</th\>  
          \</tr\>  
        \</thead\>  
        \<tbody id\="roster-grid-body"\>  
          \<tr style\="border-bottom: 1px solid var(--border-subtle); color: var(--color-text-primary);"\>  
            \<td style\="padding: 6px var(--space-sm);"\>Lamar Jackson\</td\>  
            \<td style\="padding: 6px var(--space-sm); color: var(--color-model-primary);"\>QB\</td\>  
            \<td style\="padding: 6px var(--space-sm); text-align: right; font-weight: 700;"\>9,120\</td\>  
            \<td style\="padding: 6px var(--space-sm); text-align: right; color: var(--color-warning);"\>320\</td\>  
          \</tr\>  
          \<tr style\="border-bottom: 1px solid var(--border-subtle); color: var(--color-text-primary);"\>  
            \<td style\="padding: 6px var(--space-sm);"\>Breece Hall\</td\>  
            \<td style\="padding: 6px var(--space-sm); color: var(--color-model-secondary);"\>RB\</td\>  
            \<td style\="padding: 6px var(--space-sm); text-align: right; font-weight: 700;"\>8,240\</td\>  
            \<td style\="padding: 6px var(--space-sm); text-align: right; color: var(--color-warning);"\>280\</td\>  
          \</tr\>  
        \</tbody\>  
      \</table\>  
    \</div\>  
  \</div\>  
\</div\>

The radial capacity meter dynamically updates via dynamic CSS values:

JavaScript  
function updateRosterCapacityMeter(percentage) {  
  const element \= document.getElementById('capacity-radial-meter');  
  const label \= document.getElementById('radial-capacity-text');  
    
  if (element && label) {  
    // Set native CSS custom property to recalculate conic-gradient angle   
    element.style.setProperty('--capacity-percentage', percentage);  
    label.innerText \= \`${percentage}%\`;  
  }  
}

This method avoids manual drawing or DOM recreation, letting the browser process structural updates natively using hardware acceleration.

### **4\. League Pulse (League Pulse)**

The League Pulse module processes and visualizes data from Sleeper endpoints, including active matchups, playoff brackets, transactions, and future traded draft picks.3 The system features an integrated cache layer to store league data in local storage and protect users from rate limits.2

JavaScript  
// Rate-limited, locally cached Sleeper API client  
class SleeperApiClient {  
  constructor() {  
    this.baseUrl \= "https://api.sleeper.app/v1"; // Base API URL   
    this.rateLimitBuffer \=; // Local history of calls to track query velocity  
  }

  // Returns cached browser storage data or fetches updates from the Sleeper API   
  async fetchWithCache(cacheKey, endpointPath, ttlSeconds \= 900) {  
    const cachedRecord \= localStorage.getItem(cacheKey); // Check cache   
    const currentTimeStamp \= Math.floor(Date.now() / 1000);

    if (cachedRecord) {  
      const parsedRecord \= JSON.parse(cachedRecord); // Parse JSON data \[8\]  
      if (currentTimeStamp \- parsedRecord.timestamp \< ttlSeconds) {  
        return parsedRecord.payload; // Return data if cache is still valid  
      }  
    }

    // Rate Limit Safety Guard  
    this.evaluateRateLimitVelocity();

    try {  
      const response \= await fetch(\`${this.baseUrl}/${endpointPath}\`);  
      if (\!response.ok) {  
        throw new Error(\`Sleeper API Ingestion Failed: Status ${response.status}\`);  
      }  
      const rawPayload \= await response.json();

      // Compress and store the payload inside local storage   
      const cacheObject \= {  
        timestamp: currentTimeStamp,  
        payload: rawPayload  
      };  
      localStorage.setItem(cacheKey, JSON.stringify(cacheObject)); // Store compressed string \[8\]  
      return rawPayload;  
    } catch (error) {  
      if (cachedRecord) {  
        const fallback \= JSON.parse(cachedRecord);  
        return fallback.payload; // Fallback to stale cache if the API request fails  
      }  
      throw error;  
    }  
  }

  evaluateRateLimitVelocity() {  
    const windowStart \= Date.now() \- 60000; // Track calls in the last 60 seconds  
    this.rateLimitBuffer \= this.rateLimitBuffer.filter(timestamp \=\> timestamp \> windowStart);

    if (this.rateLimitBuffer.length \>= 950) { // Limit calls before hitting the 1,000 call ceiling   
      throw new Error("Rate limit safety breaker triggered. Network request blocked client-side.");  
    }  
    this.rateLimitBuffer.push(Date.now());  
  }

  // Resolves traded picks to reconstruct league draft capital   
  async getTradedPicks(leagueId) {  
    return this.fetchWithCache(  
      \`dg\_cache\_picks\_${leagueId}\`,  
      \`league/${leagueId}/traded\_picks\`,  
      43200 // Cache for 12 hours  
    );  
  }

  // Ingests transaction logs for the active week   
  async getTransactions(leagueId, currentWeek) {  
    return this.fetchWithCache(  
      \`dg\_cache\_tx\_${leagueId}\_w${currentWeek}\`,  
      \`league/${leagueId}/transactions/${currentWeek}\`,  
      300 // Cache for 5 minutes  
    );  
  }  
}

HTML  
\<div class\="league-pulse-module" style\="background: var(--bg-surface-lowest); border: 1px solid var(--border-strong); border-radius: 8px; padding: var(--space-lg); display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-lg);"\>  
  \<div class\="pulse-column-matchups"\>  
    \<h4 style\="font-family: var(--font-family-sans); font-size: var(--text-sm); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;"\>Active Matchups Mapping\</h4\>  
    \<div id\="matchups-container" style\="display: flex; flex-direction: column; gap: var(--space-sm); max-height: 220px; overflow-y: auto;"\>  
      \<div style\="background: var(--bg-surface-mid); padding: var(--space-sm); border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 2px solid var(--color-model-primary);"\>  
        \<span style\="font-family: var(--font-family-sans); font-size: var(--text-xs); color: var(--color-text-primary); font-weight: 500;"\>Matchup \#1\</span\>  
        \<span style\="font-family: var(--font-family-mono); font-size: var(--text-xs); color: var(--color-text-secondary);"\>Team A (142.5) vs Team B (138.2)\</span\>  
      \</div\>  
    \</div\>  
  \</div\>

  \<div class\="pulse-column-draft"\>  
    \<h4 style\="font-family: var(--font-family-sans); font-size: var(--text-sm); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;"\>Draft Capital Valuation\</h4\>  
    \<div id\="traded-picks-container" style\="display: flex; flex-direction: column; gap: var(--space-sm); max-height: 220px; overflow-y: auto;"\>  
      \<div style\="background: var(--bg-surface-mid); padding: var(--space-sm); border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 2px solid var(--color-market-primary);"\>  
        \<span style\="font-family: var(--font-family-mono); font-size: var(--text-xs); color: var(--color-text-primary);"\>2027 Rnd 1 (Team X)\</span\>  
        \<span style\="font-family: var(--font-family-mono); font-size: var(--text-xs); color: var(--color-model-primary); font-weight: 700;"\>PVO: 4,120\</span\>  
      \</div\>  
    \</div\>  
  \</div\>  
\</div\>

The dynamic template uses the asynchronous fetch interface to populate the transaction feed and matchup cards, handling API operations and caching under a unified wrapper.5

### **5\. GPU-Accelerated Micro-Animations (Micro-Animations)**

To ensure the local file-system dashboard loads and runs smoothly without compilation pipelines, all interactive animations run on the GPU. The layout restricts dynamic animations to transform and opacity properties to prevent browser reflows.15

CSS  
/\* Optimized CSS Micro-Animations \*/

/\* Card hover animation with smooth shadow scales \*/  
.interactive-card {  
  background: var(--bg-surface-lowest);  
  border: 1px solid var(--border-strong);  
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),   
              border-color 0.2s cubic-bezier(0.16, 1, 0.3, 1),   
              box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1);  
  will-change: transform, border-color, box-shadow; /\* Forces GPU compositing Layer \*/  
}

.interactive-card:hover {  
  transform: translateY(-2px);  
  border-color: var(--color-model-primary);  
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2), 0 0 12px var(--color-model-glow);  
}

/\* Mouse-Tracking Spotlight Overlay \*/  
.spotlight-container {  
  position: relative;  
  overflow: hidden;  
}

.spotlight-container::before {  
  content: "";  
  position: absolute;  
  top: 0;  
  left: 0;  
  width: 100%;  
  height: 100%;  
  background: radial-gradient(  
    circle 150px at var(--mouse-x, 0) var(--mouse-y, 0),  
    rgba(255, 255, 255, 0.04),  
    transparent 100%  
  );  
  pointer-events: none;  
  z-index: var(--z-index-base);  
  transition: opacity 0.3s ease;  
  opacity: 0;  
}

.spotlight-container:hover::before {  
  opacity: 1;  
}

/\* Loading Shimmer Bar \*/  
@keyframes shimmer-sweep {  
  0% {  
    transform: translateX(-100%);  
  }  
  100% {  
    transform: translateX(100%);  
  }  
}

.shimmer-active {  
  position: relative;  
  overflow: hidden;  
}

.shimmer-active::after {  
  content: "";  
  position: absolute;  
  top: 0;  
  left: 0;  
  width: 100%;  
  height: 100%;  
  background: linear-gradient(  
    90deg,  
    transparent 0%,  
    rgba(255, 255, 255, 0.05) 50%,  
    transparent 100%  
  );  
  animation: shimmer-sweep 1.6s infinite linear;  
  will-change: transform;  
}

JavaScript  
// Lightweight mouse coordinate tracker for CSS Spotlights  
document.addEventListener('DOMContentLoaded', () \=\> {  
  const spotlightCards \= document.querySelectorAll('.spotlight-container');

  spotlightCards.forEach(card \=\> {  
    card.addEventListener('mousemove', (event) \=\> {  
      const cardRect \= card.getBoundingClientRect();  
      const xCoordinate \= event.clientX \- cardRect.left;  
      const yCoordinate \= event.clientY \- cardRect.top;

      // Dynamic CSS values update mouse coordinates smoothly on the GPU  
      card.style.setProperty('--mouse-x', \`${xCoordinate}px\`);  
      card.style.setProperty('--mouse-y', \`${yCoordinate}px\`);  
    });  
  });  
});

This dynamic approach runs efficiently on standard hardware, supporting mouse-tracking visual highlights without complex render loops.

## **Conflicts and Resolutions**

Building a zero-dependency, local file-system compatible analytics cockpit introduces several architecture and layout conflicts. The following analyses outline the resolutions designed for the Phase 17 system:

### **Conflict 1: Framework-Free Reactivity versus Real-Time High-Density Updates**

High-density visual layouts often rely on framework reactivity (like React or Vue) to synchronize state changes across the workspace.7 Under a zero-dependency file:// protocol constraint, executing compilation pipelines is prohibited.

#### **Resolution**

The UI uses a native pub-sub design pattern built on ES6 class modules and custom DOM events. Global state is preserved inside a single, lightweight JavaScript store. This store dispatches localized updates whenever a Player Value Object or draft pick changes.  
Interactive elements listen to these updates and re-render isolated components via standard DOM manipulation (Element.innerHTML or Element.style.setProperty). CSS custom properties drive the layout's color, scale, and positioning, bypassing the need for a compile step.

JavaScript  
// Core State Publisher-Subscriber Engine  
class StateController {  
  constructor() {  
    this.subscribers \= {};  
    this.state \= {  
      activeLeagueId: null,  
      selectedPlayers:,  
      modelMetrics: { pvo: 0, xvar: 0, capacityCost: 0 }  
    };  
  }

  subscribe(eventKey, callback) {  
    if (\!this.subscribers\[eventKey\]) {  
      this.subscribers\[eventKey\] \=;  
    }  
    this.subscribers\[eventKey\].push(callback);  
  }

  dispatch(eventKey, updatedPayload) {  
    this.state \= {...this.state,...updatedPayload };  
    if (this.subscribers\[eventKey\]) {  
      this.subscribers\[eventKey\].forEach(callback \=\> callback(this.state));  
    }  
  }  
}

### **Conflict 2: Storage Exhaustion and Blocking under Local file Protocols**

The local storage API offers reliable, synchronous string-based persistence under local directories, but browser-allocated thresholds are limited to approximately 5 MB.1 The full NFL player metadata database fetched via /players/nfl is dense and exceeds this threshold, leading to storage failures and browser event blocking.2

#### **Resolution**

The database structure is normalized prior to storage. Instead of storing the complete player object, the application maintains a lightweight database schema containing only active, rostered player IDs.  
The player names, team abbreviations, and positions are cross-referenced with a local, compressed JSON dictionary stored directly in the local folder. The browser's active cache stores dynamic attributes, such as ![][image3], ![][image1], and capacity costs, while purging outdated league data. This optimization keeps storage consumption below 1.5 MB, well within standard browser thresholds.

### **Conflict 3: Model and Market Valuation Interface Bleed**

Mixing subjective market trends with objective, model-driven predictive values leads to decision bias. Standard dashboards often display market metrics (like KeepTradeCut consensus values) alongside algorithmic performance models without clear separation, causing users to mistake market sentiment for objective projections.5

#### **Resolution**

The system implements visual isolation using color theory and separate spatial columns. The layout divides the workspace into two distinct areas:

* **Predictive Model Lane (Left):** Rendered using a deep, dark emerald-to-teal monochrome color scale. Values are displayed alongside a shaded linear uncertainty area that represents standard error margins and prediction intervals.17 No absolute market ranks are permitted in this track.  
* **Market Price Discovery Lane (Right):** Rendered using a neon purple and cyan outline style. This lane is reserved for KeepTradeCut and FantasyCalc value overlays.

These lanes use distinct CSS selector prefixes (.lane-model and .lane-market) to ensure their presentation remains separate.

### **Conflict 4: Rate-Limit Preservation under Direct Ingestion**

The Sleeper platform rate limits requests to 1,000 queries per minute.3 Without a proxy or backend server, rapid dashboard reloads, multi-league scanning, or quick-firing interface actions can trigger IP bans.3

#### **Resolution**

The UI implements an automated local caching layer directly in front of the network fetch module. When requesting roster, user, or matchup data, the application checks local storage first.2 The system caches these data objects with variable Time-To-Live (TTL) values, as detailed in the following table:

| Ingest Endpoint | Update Frequency | Local Storage TTL | Performance Impact |
| :---- | :---- | :---- | :---- |
| /league/{id} | Static per season | 86,400 seconds (24 hr) | Eliminates repetitive structural lookups. |
| /league/{id}/users | Infrequent | 43,200 seconds (12 hr) | Minimizes redundant identity requests. |
| /league/{id}/rosters | Moderate | 900 seconds (15 min) | Safeguards active rosters while preserving bandwidth. |
| /league/{id}/matchups/{w} | Highly dynamic | 300 seconds (5 min) | Ensures active matchup data updates without hitting API limits. |

If the cache is still valid, the application reads the data from local storage, bypassing the network request completely.

## **Workstreams and Ordering**

To transition the system to Phase 17 systematically, development is divided into five sequential, dependency-mapped workstreams.

\+-----------------------------------------------------------------------------------+  
|                            PHASE 17 IMPLEMENTATION TIMELINE                       |  
\+-----------------------------------------------------------------------------------+  
| WORKSTREAM                               | DELIVERABLES                           |  
\+-----------------------------------------------------------------------------------+  
| WS1: Token Framework & Storage Engine    | tokens.css, store.js, local storage    |  
|   └── Dependency: None                   | compression utility                    |  
|                                          |                                        |  
| WS2: Sleeper API & Cache Controller      | api.js, client-side rate limiter,      |  
|   └── Dependency: WS1                    | payload normalization routines         |  
|                                          |                                        |  
| WS3: Trade Lab Dual-Track Canvas         | split-lane UI, dropzones, player ID    |  
|   └── Dependency: WS2                    | validation gates, prediction bars      |  
|                                          |                                        |  
| WS4: Roster Audit & League Pulse         | conic-gradient meters, matchup grid,   |  
|   └── Dependency: WS3                    | traded-pick ledger components          |  
|                                          |                                        |  
| WS5: Animation & Render Tuning           | spotlight hover effects, composited    |  
|   └── Dependency: WS4                    | layer setups, paint loop profiling     |  
\+-----------------------------------------------------------------------------------+

### **Workstream 1: Core Token Framework and Local Storage Engine**

* **System Objectives:** Establish the design tokens, theme attributes, utility variables, and state management engine in a single, local stylesheet (tokens.css) and script (store.js).  
* **Technical Implementations:**  
  * Define dark-theme variables including background levels (--bg-depth-0: \#0a0c10, \--bg-depth-1: \#121620, \--bg-depth-2: \#1b2030), brand colors, and status-neutral accents.  
  * Configure utility metrics for layout typography, using variable viewport units (clamp()) to ensure responsiveness across different screen sizes.  
  * Build a serialized local storage helper class that automatically compresses and extracts state arrays to prevent storage capacity limits.2

### **Workstream 2: Sleeper API Ingestion and Cache Controller**

* **System Objectives:** Construct the client-side data integration engine, enabling users to fetch and cache league information directly from Sleeper.3  
* **Technical Implementations:**  
  * Program a clean, asynchronous fetch wrapper (api.js) targeting the base Sleeper URL.13  
  * Integrate a request interceptor that evaluates cached timestamps inside local storage prior to initiating network requests.2  
  * Build a client-side rate-limit monitor that blocks requests and shows a cool-down warning in the UI if calls approach the 1,000 per minute limit.3  
  * Implement data-shaping filters that extract only critical properties from the incoming roster, user, draft, and matchup payloads, trimming excess data before saving to disk.3

### **Workstream 3: Trade Lab Dual-Track Visualization Component**

* **System Objectives:** Build the high-density trading canvas, featuring split lanes that isolate predictive models from market pricing.  
* **Technical Implementations:**  
  * Create a split layout using CSS Grid:

.tradelab-canvas {display: grid;grid-template-columns: repeat(2, minmax(320px, 1fr));gap: 24px;}\`\`\`

* Style the left side (.lane-model) to display Model-Equivalent values. Use deep forest emerald backgrounds, teal borders, and standard text styling.  
  * Style the right side (.lane-market) to show Price Discovery values. Use carbon-gray backgrounds, thin purple borders, and neon badge components.  
  * Implement the trade balance calculation engine. It calculates comparative value gaps using ![][image1] deltas and capacity costs, while preventing market values from influencing the calculation.

### **Workstream 4: Roster Audit and League Pulse Modules**

* **System Objectives:** Develop analytical dashboard modules, including a roster capacity visualizer and a league transaction feed.  
* **Technical Implementations:**  
  * Build dynamic progress meters using conic-gradient() CSS custom properties and radial masks.9  
  * Create a reusable uncertainty bar component using linear gradients to display standard error margins:

.uncertainty-bar {background: linear-gradient(90deg,rgba(16, 185, 129, 0.1) 0%,rgba(16, 185, 129, 0.4) 20%,rgba(16, 185, 129, 0.4) 80%,rgba(16, 185, 129, 0.1) 100%);position: relative;}\`\`\`

* Integrate the league transaction feed to process trades and roster moves from /league/\<league\_id\>/transactions/\<week\> and display traded picks from the draft endpoints.3

### **Workstream 5: Micro-Animations and Rendering Optimization**

* **System Objectives:** Enhance interface performance and interactivity using hardware-accelerated transitions and optimized rendering loops.  
* **Technical Implementations:**  
  * Write CSS transitions using only performance-friendly properties like transform, opacity, and custom CSS variables to ensure smooth frame rates.  
  * Create a subtle, glowing hover effect for high-density tables using a lightweight mouse-tracking radial gradient.  
  * Ensure layout reflows are minimized during data loading by using fixed-size grid placeholders, preventing content shifting as data arrives from the API.

## **Risks**

Running an analytics application directly in the browser introduces potential technical risks. The table below outlines these hazards and their mitigation strategies:

| Threat Category | Detailed Hazard Scenario | Potential System Impact | Technical Mitigation Strategy |
| :---- | :---- | :---- | :---- |
| **API Limit** | Multiple browser tabs open simultaneously, triggering duplicate queries.3 | IP block from the Sleeper API, disabling data fetching.3 | Use a tab-synchronized request coordinator using browser storage events to manage API calls.2 |
| **Storage Block** | Browser security policies blocking storage access under the file:// protocol.1 | Inability to cache player metadata, leading to performance issues and empty lists. | Build an in-memory fallback state class, and let users manually export or import cache snapshots as JSON files. |
| **Stale Cache** | Mismatched draft picks and transaction histories when trading in-season.3 | Inaccurate opportunity mapping and calculation errors. | Add manual cache refresh controls to core views, and automatically clear stale caches during active weeks. |
| **Layout Stress** | Complex, multi-column tables causing frame drops on low-end hardware.16 | High rendering latency, sluggish interactions, and UI freezing. | Use virtual rendering lists for deep directories, and restrict mouse effects to hardware-accelerated CSS properties.15 |

## **Open Decisions for David**

The following architectural questions require executive review and approval prior to beginning production:

### **Decision 1: Visual Overlay Strategy for Unrostered Players**

* **Context:** Unrostered free agents are not mapped to active rosters. Consequently, calculating their capacity costs (![][image4]) is problematic because capacity cost is calculated dynamically based on total active roster sizes and league-wide bench utilization.3  
* **Option A:** Display a flat, normalized bench capacity cost of ![][image11] for all unrostered players, using a generic profile index.  
* **Option B:** Dynamically estimate a player's capacity cost by analyzing the average value of players on the roster of the weakest active team.

\+-----------------------------------------------------------------------------------+  
|               UNROSTERED PLAYER DEVIATION STRATEGY TRADE-OFF MATRIX               |  
\+-----------------------------------------------------------------------------------+  
| CRITERIA           | OPTION A (Flat Value)        | OPTION B (Dynamic Analysis)   |  
\+--------------------+------------------------------+-------------------------------+  
| Performance Impact | Negligible (Static lookup)   | Moderate (Calculates rosters) |  
| Statistical Accuracy | Moderate                     | High                          |  
| Complexity         | Low (Simple constant)        | High (Scans league users)     |  
\+-----------------------------------------------------------------------------------+

* **Recommendation:** Option A for the alpha release to minimize rendering delays, with plans to transition to Option B for the beta release once the indexing performance is verified.

### **Decision 2: Local Player Dictionary Storage Strategy**

* **Context:** The full NFL player metadata payload fetched via /players/nfl is exceptionally dense and exceeds the browser's storage limits.2  
* **Option A:** Instruct users to run a simple, optional prep script that downloads and compresses the player dictionary into their local workspace directory.  
* **Option B:** Fetch player metadata dynamically using a CDN-hosted, pre-chunked JSON structure organized by position or roster percentage.

\+-----------------------------------------------------------------------------------+  
|                LOCAL DICTIONARY STORAGE STRATEGY TRADE-OFF MATRIX                 |  
\+-----------------------------------------------------------------------------------+  
| CRITERIA           | OPTION A (Prep Script)       | OPTION B (Dynamic CDN Chunks) |  
\+--------------------+------------------------------+-------------------------------+  
| Setup Friction     | High (Requires execution)    | Low (Instant file loading)    |  
| Offline Access     | Absolute (Fully local)       | Dependent on network          |  
| Storage Footprint  | 15 MB local disk             | \< 1.0 MB local storage        |  
\+-----------------------------------------------------------------------------------+

* **Recommendation:** Option B. Organising the CDN payload by position (e.g., loading QB and RB datasets on demand) reduces setup friction for new users while keeping storage consumption within standard limits.2

### **Decision 3: Display of Draft Capital for Future Years**

* **Context:** Sleeper draft picks traded across rosters must be reconstructed from /league/\<league\_id\>/traded\_picks.3 Evaluating future draft picks (e.g., 2027 and 2028 picks) requires setting baseline valuations for picks that have not yet been assigned to a specific draft position.  
* **Option A:** Apply a flat, mid-tier valuation to all picks of the same round (e.g., valuing all future first-round picks as a generic mid-first).  
* **Option B:** Adjust future pick values dynamically based on the current roster strength and projected finish of the pick's original owner.

\+-----------------------------------------------------------------------------------+  
|                  FUTURE DRAFT VALUATION STRATEGY TRADE-OFF MATRIX                 |  
\+-----------------------------------------------------------------------------------+  
| CRITERIA           | OPTION A (Mid-Tier Flat)     | OPTION B (Dynamic Roster Est) |  
\+--------------------+------------------------------+-------------------------------+  
| Calculation Load   | Zero (Static scale lookup)   | High (Re-evaluates rosters)   |  
| Realism            | Low                          | High                          |  
| Visual Precision   | Fixed indicator              | Dynamic uncertainty bands     |  
\+-----------------------------------------------------------------------------------+

* **Recommendation:** Option B. This aligns with the predictive nature of the ![][image1] model, using actual roster data to forecast pick values instead of applying flat-rate assumptions.

## **Acceptance Criteria**

To successfully complete Phase 17, the implemented UI cockpit must meet the following technical and functional requirements:

### **File System Independence**

* The dashboard must open and run directly from the local file system using the file:/// protocol in modern desktop browsers, including Chrome, Safari, and Firefox.1  
* The system must load instantly without requiring local servers, build pipelines, node modules, tailwind compilers, or external asset dependencies.

### **Dependency Audits**

* The codebase must consist entirely of standard, hand-written HTML, CSS, and ES module JavaScript files.  
* No external stylesheets, design frameworks, tailwind compilation loops, or React/Vue dependencies are permitted in the repository.

### **Rate-Limit Controls**

* The application must include an automated caching manager that blocks API requests if they approach the Sleeper platform limit of 1,000 queries per minute.3  
* Data must be served from local storage whenever the cache is still valid.2

### **Visual Separations**

* Predictive model metrics and market price badges must be displayed in visually distinct areas of the layout.  
* The styles for these areas must be managed using separate CSS files with distinct, non-overlapping selector prefixes (.lane-model and .lane-market).

### **Verdict Avoidance**

* The user interface must not contain any binary labels, such as "buy," "sell," "win," or "loss."  
* All player and trade evaluations must be represented using continuous numerical margins, standard error indicators, and calibrated ![][image5] prediction intervals (![][image9] to ![][image10]).11

### **Mechanical Authenticity**

* All data visualizations, including the trade ledger and roster audit panels, must display calculations derived directly from the underlying mathematical models.  
* The interface must not display stylized visual elements, progress bars, or placeholder metrics that are not backed by real data from the calculation engine.

#### **Works cited**

1. Javascript/HTML Storage Options Under File Protocol (file://) \- Stack Overflow, accessed May 25, 2026, [https://stackoverflow.com/questions/5914029/javascript-html-storage-options-under-file-protocol-file](https://stackoverflow.com/questions/5914029/javascript-html-storage-options-under-file-protocol-file)  
2. JavaScript and localStorage in a nutshell with examples \- TinyMCE, accessed May 25, 2026, [https://www.tiny.cloud/blog/javascript-localstorage/](https://www.tiny.cloud/blog/javascript-localstorage/)  
3. Sleeper API: introduction, accessed May 25, 2026, [https://docs.sleeper.com/](https://docs.sleeper.com/)  
4. Sleeper API MCP \- LangDB, accessed May 25, 2026, [https://langdb.ai/app/mcp-servers/sleeper-api-mcp-2bef2d2b-8e7c-48d3-bdc1-53c6318c61e1/](https://langdb.ai/app/mcp-servers/sleeper-api-mcp-2bef2d2b-8e7c-48d3-bdc1-53c6318c61e1/)  
5. Sleeper API Explained: A Complete Guide for Developers & Fantasy Founders \- SportsFirst, accessed May 25, 2026, [https://www.sportsfirst.net/post/sleeper-api-explained-a-complete-guide-for-developers-fantasy-founders](https://www.sportsfirst.net/post/sleeper-api-explained-a-complete-guide-for-developers-fantasy-founders)  
6. Building a Professional Dashboard: From CSS Grid to Complete PWA \- Medium, accessed May 25, 2026, [https://medium.com/uxdworld/building-a-professional-dashboard-from-css-grid-to-complete-pwa-45b0d455d28c](https://medium.com/uxdworld/building-a-professional-dashboard-from-css-grid-to-complete-pwa-45b0d455d28c)  
7. Interactive JavaScript dashboards \- Highcharts, accessed May 25, 2026, [https://www.highcharts.com/products/dashboards/](https://www.highcharts.com/products/dashboards/)  
8. localStorage in JavaScript: A complete guide \- LogRocket Blog, accessed May 25, 2026, [https://blog.logrocket.com/localstorage-javascript-complete-guide/](https://blog.logrocket.com/localstorage-javascript-complete-guide/)  
9. An Animated Circle Progress Component FSCSS plugin \- GitHub, accessed May 25, 2026, [https://github.com/Figsh/Circle-progress.fscss/](https://github.com/Figsh/Circle-progress.fscss/)  
10. Trading UI designs, themes, templates and downloadable graphic elements on Dribbble, accessed May 25, 2026, [https://dribbble.com/tags/trading-ui](https://dribbble.com/tags/trading-ui)  
11. Technical Specification | Planet Documentation, accessed May 25, 2026, [https://docs.planet.com/data/planetary-variables/forest-carbon-diligence/techspec/](https://docs.planet.com/data/planetary-variables/forest-carbon-diligence/techspec/)  
12. Technical Specification \- Planet Documentation \- Planet Labs, accessed May 25, 2026, [https://docs.planet.com/data/planetary-variables/forest-carbon-monitoring/techspec/](https://docs.planet.com/data/planetary-variables/forest-carbon-monitoring/techspec/)  
13. A Comprehensive Guide to the Sleeper API \- Zuplo, accessed May 25, 2026, [https://zuplo.com/learning-center/sleeper-api](https://zuplo.com/learning-center/sleeper-api)  
14. conic-gradient() CSS function \- MDN Web Docs \- Mozilla, accessed May 25, 2026, [https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/gradient/conic-gradient](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/gradient/conic-gradient)  
15. 176 CSS Grid Examples \- FreeFrontend, accessed May 25, 2026, [https://freefrontend.com/css-grid/](https://freefrontend.com/css-grid/)  
16. Browse thousands of Dashboard Data Grid images for design inspiration | Dribbble, accessed May 25, 2026, [https://dribbble.com/search/dashboard-data-grid](https://dribbble.com/search/dashboard-data-grid)  
17. Mapping data sensitivities in global QCD analysis with linear response and influence functions \- arXiv, accessed May 25, 2026, [https://arxiv.org/html/2604.28154v1](https://arxiv.org/html/2604.28154v1)  
18. Estimation and uncertainties of profiles and equilibria for fusion modelling codes \- MPG.PuRe, accessed May 25, 2026, [https://pure.mpg.de/rest/items/item\_3266718/component/file\_3277323/content](https://pure.mpg.de/rest/items/item_3266718/component/file_3277323/content)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAaCAYAAADrCT9ZAAADEElEQVR4Xu2WWahOURiGX/NUhkzJlFyQWS4UFyehpFwgIeRCMiWZc0NSREIkShlCioy5UOSUMRcoLmQ8xxQ3yBCZ4n19a59/7+/8Z+8/Dm72U0/n7O9bZ+191lrfWgvIycn5yyyl7Xzwf9GTPqYV9D59QO/SprE2jUP8aWhXSfvF8mlMpD9omU8E1Pcd+py+pC/oI9g7HtITdFLUuLaoT/fDPmyBy0W0oR/oYpQ+Wxq0J7B+J7icZzas3YrwXIe2ostCfEOI1xrLYR3rBcVYSFf5YAZrYKtF/c5zOc9uWLtBPgGb+fe0uU/8CZNhL9zmE6QjvU4b+UQK3egVOg3W7+pkuhoqmTe0ros3pF/od9rF5YoygA5H4WPb0sGFdBVDYB920ifIETrCBzM4RofC/k797kimE2hAa3r3VFhuu094GtDDdB/dSm/TlXQXPU43FZr+ojOs45suPpoedLEsRsL2BKEBV78agJqYAmujsonQZqYS0lLejOQmWpT1KOxuWhbq8AJtTb/S8yEXUY9+o69isSb0Bm0fi2Whgb5GO4TnaCAvVbWojiZBbS7T0+HnW9i7B8bapaJRiegN63AGbPdbRHvE8hE6ntSuWXheS+cU0iWhvpfEnjUz6vNeLOZR/b5Gsn5nwer2t46kubCXaiNJ4yKsnc7mXrAV4TeRNLQS9OE6UytQOE/Vp2asGJ1QvH61uhQ/6+IlcRQ2e1moVvWSUbSc9k+mM9kLq3mPZlD9qi490S6ulREnqn0Neia6SGg5joPVpkb9QCw/PuQ862Av0XGy0eWy0C5/ygcDV2H9dvUJsgeW8+fv/BDXTSuTMlhjLeUx4XdtYqIFbJfWoHii204lCnVcCn1hS7jY7IpzsH41KHH0DbquvkP10tG5rb85FJ5nIqWedfXTaG+BXSTGwv6JnbAR61PVMomWsl5S04d7tPtX0k/0c/g5LJafDqtnxaXquBxWn7dgN6iPwWewYzOie4hpIDURZ1DCJMQ3KdWPDvg0dHfNuvP+S1rCLi6a2WIrMicnJycnJ+c/8xNB6a/Y6s/bdQAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADEAAAAaCAYAAAAe97TpAAACh0lEQVR4Xu2WSahOYRjH/4bMC0oo4wohMqSwucpCKGVYmBasKOWKUISF2EiJbKR7C6UskKxviIUMC0nGe2VIiiSxIPz/Pe/xPR7nfOfcstL51S/dZzjvOa93+ICamv+eHnQ6XUInh1wp8+gT+oa+Tf8+p09pJ71O19E+qX4ifZFy6lPdIzog5UW/FH+Z6rroVJf3DKbH6TN6lO6C9Tyks11dJc7Rn3SOi+llNqf4ERfvTU+n+BYX9wyln+k2OizkMhbT1/QA7GMyNCFt9Cud5eKlaPY/0l4xAZv573SMi+2EfcQOF/Nspfti0LGcfqOtMZEYB3t+R4gXMgrWcDkmSE/YjP6APThjFaznmItljKR3aN+YSIymn+h92POL0DLVGINiIo81sOLtMUHmw3LtIT43xS+FuDhPF8Sg4wqsd1lMBG7D6qbFRB4nYcUzQ3wsvQXboMNDTrOpnnshvoieDTHPDFifZlknUhFa1toTqtVYpeiU0XLZA1vru2Evoj3SRoc0Sn+jQbRP3rtYf3oXf3+wR2Poxc7ERGACrE7LrpRsP2gNL03qrG6BnU7N0IZX78D090G6qZHOpQPWo8lqhk411V2MiTzWwor3h3gVdIeoV3fHJHoNzTequAHr0bIrQnfSK9jqqLQfTsEe2hLiVdCSU+9C2AxXGTAbb3VMONbDalRbiU7YBio6DptxCDbYTXo45IrYAOs5ERMJ/fT4ALt8damWkm2eqzFRkY2w/i409kUZWm766HewF/bodNQHtCP/0v0D/bR4DGvQ/8IX2DGqW7Q7aBmVre88RtALsEt0L2yT68MewH6nNTt6/zk6elfGYDcYT1fAnjEF5YdCTU1NTU1NJX4BCpOPeXzbBkkAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAaCAYAAABctMd+AAABU0lEQVR4Xu2UyytFURSHVyhDM/IuBoyIicdMKVJkYsSYKSNhxoDyF8ijkMfklhRliLkpJWQgRiiSUHy7te+xW0nnXErpfvXV3b+1WufcvU9bJMtf04pneI03eOXXl3iMS9gUdWfIJr5ji1/nYiVu4Bt2+zwjzvFedGhIrehDD0wemzLRAdu2AG2itVNbiEu/6IARW4AF0VqfLcRlXnRAQ5CV4Bre4WCQJ8b95Vfc9R7hM65jcdCXmPR+bwWZO9RVvMWaIE/MgHy9350+nzB5IhZFhzSafNjnkyZPxIXo951j8pTocPcQSyGO4RRWmVqE2083YMcWYF+0NuTXK1iKdXiIFTiKy74e4e4K94W4A3vCB9G7pCPo6cEX3MNpnMV8PMF231ONRf53YsqxVz6HNeMj5kUdv0i96I2ZpgC7gvWPmcNx0YOekW8ONFPcGzuz/Hc+AHEcRhdhSuMuAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAACr0lEQVR4Xu2VW4iOURSGl9MFOeU0pJRDjKJpzMwFoiFnJWJiirg0zYzJMI1ELkhxIUKU0wgXInIqpySUU8rhxgUhStxISES8b2vtz/q2/5uZm6m5+N96mu9de097/3utvbZIXu1HA0HHOBipTxxoS3UCR8FFcAEsSQ8nKgIPQZd4IFYHMA9sB2tA7/RwomGgBmwFc6MxqhI8su/+4BM4BxaDEaBU9H8/g9k2L1NdwTVjJlgN3oPhfhI0BbwBdWAquAFOpmaINIFdzh8DY8AMsBFUgfXgkJuTqT3gq6RP6QR44DxT9A6sdTHWyBew3MVegc3ObwETnO8F7trfZsUc/wRPongt+ANGmWea6cclM1R3wHXn74Edzu+V9CZ4UrOczxQX5oL3o/gKi1eb32l+aJhgOg9+gM7mualL9s0f3WTf1BxpZQqpQaILxifGDTHOVFBMLT3ne52yeIH57uCxaMp5O0OaWSY8zRZT6PVStKi99osuuM/8FfNhA0EsfsZHu1g3sBBMdDFukheL4ukuBevAgGRGDvHa/wbTzQ8R3SwX5NWmLptn4/QKGxsZxb1Ynwec5yaPiK57S1poxMw/Gx5P5iBoEF1wpY0fNz/YfNBpi2d1ccZZvz3N9wO/5F9K2RNL7LtV2iS64Fjz28z7lFFXwTfRBp1L/EEhExRfAjbXoGLQ6HxK7Mp8Qnq42E1w2/ly0Y2FOgl6Ds5EsaD5orXqxSb7wXm+JOyjObVbtMYKzS8Q/VVlyQxtsM9E20YQ6+o7mOZiQX1FGylvqRc3y2YexP9d5HxK7GVPwQbRW/gRTErNUPFSvAaHQT14Ifo25hJTWB4HRWvuLVhm/qzFMsX3ko/qZNHTyRKv+nhQIf/3tCCO++4fi68HbyNfjFXRWJsr6zJ4Ndsm8sorr/akv13sgvGLzaEiAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAZCAYAAAAmNZ4aAAABxklEQVR4Xu2UPSiGURTHj++U8hUZlBQpk8HgOwYDkY9CkcVkEIsYDMrHYlEmm9cmWRjEYGKQmEQyUKKEJDYp/qdzb85zPe/76lmknn/96r3/e+57zr3PuZco1D9UAsgGqe5ELBWBMVALMkAx6AWDOiiGtsAH+AQ1zlxMNZEs0tyBKh1kNOUaJLsdpwCJG8EtOCKpnv+8QAcYJZHE+ambAiRuABHX9FEzeHRNo04KkLie4ieuBpfgGZQauJmsOug7cRrJZirUvK/qwCZYAnvghKQYq0KwA+7BO9g19KmYdpLEoySxE2AfnIEUFecR74Z3UmnGZeCBfjbSOkU/apv4nKTZWOXGG7BBrtJJrpTWCskVKVHebxIPKy/PeLPKi6t5kkVDyuPET2qsZRO3KS/XeHPK8+gAHINE5c2QLBpRHifmT2LVpX7b5mpRHjdf1MT8PfixuADJyl8mWcSvmdUaeFFjbkQrLsJNnGM8Pj1fLYBWNc4CNySdqzVJ8t3523FPrKq5fpIkPcrjR4i9ReV5xAFcfQRMg1OwDfJVDCsTHIIrkutnG28DvCr4ZLhIPkkev4FrE+srfhS48ngXnwu1VyZUqFB/qy84XWVx03vJ/gAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAZCAYAAABD2GxlAAACf0lEQVR4Xu2VS6hOURiGX/fLcTcy4eSeMjBQymVAco0USXKZkVsuiYFCREnJLQaUiYmZMnE5+kVyzWXAAAM6UUKOw0SJ9z3fWmd/e/327z8yMNhvPfWvd31rr+//9rfWBkqV+ufqQQamZj3qRBaQQ2QbGZCfbtMKspgMJw1kMtlMhvqgAk0hreQnuZLM/VG9yNXALLKFvCMjfBB1A7aB5xTp7oOoSWRG4kn9yFv8RYInyFfkq3ae3HNjqUJukzuwxBbmZjPtIutTM+gpOphgN/KdPEn8jbAKjXHeddLoxkW6heIEH6ODCSoBJXI38VcH32/UhNoJ9iEHYev2klFkZC4CeIQswWFkNumfTVdrCOyBaQWVmPz9zrtG1pHL5AE5BuvfqJ2w6mndsxB3yc1LD2Fv4jA5Q3aTb2SVD0r1irxOvNPIDkGUNjwLa4uu5Ah5jnxVx6G68l5KUPPLnHeBvHDjKs0jP8jMMNa1oaT1oAMxiBpNOruxXpFizjmvngSbSRfnnYSt8V6V5pL7sCqp9Nthi9a6GN2VXqqkYt44Lya4wXleSlDt4XUctkZvpW6pN7RofBjPJ5/JkvYI+8eK+eC8mOCmMJ4Aq3SUDkl6II/C1ugP/1ZLYc3c13kVctON18DaYKXz4gHTBR81Nnj6wkg7kLWOpMOYJqjDVjNBlVib6+HSItJCJrZHAINg14x/yFbYOn3GonqTj7BNJbVLvGpUcR0qXda+l+OBLLxudBdqkb4AOrXvydRchEmvrUL2wDZWIsvdfJT69hO5SPYFT8/T5/NLQL+nk5ew1pGnVinq3bb7bA6ZhtqnqSesHxWrqhZJ3+fBqVmqVKlS/5l+ARY9j4HwLM3LAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAaCAYAAADWm14/AAACJUlEQVR4Xu2VS0jUURSHD5VYmAltLMEWQYULcWFK0EMTouxFC8UHRCquQnttqkUpCJEUGlG4r6BVQVqBkEuJQlAQhBYWBKVEYAs1Ek1/vzn379w5ODo6M+JiPvjg3nvu3LnP8xdJscFJh8fgGbjbxJLKAdgNP8FHsAuOwV6Y7fVLCrfhb1hv2jPgCPwGt5tYwuiEs/C4DThOwnnYYgOJ4ILo4K2m3Yfbzz4DNhAvWfAHnBDd6uWYE+2XUG6IruyBDRh4Odnvqw3EywfRgctswBBM9J0NxEMa/Ce6tTtMzBJM9LrXthU2waswx2vfD5vhUVgBL3mxCJhs/ou+8+XIhDPwJ9zmtffAE6L3qA8WuPbzouNOi+aPPa59SUbhX7jJBjyYjLj6Oq8tX/S3AVfgQ1c+59wSDkfnmejgvGTkJnwjuq3kmovfc/WABtFsGVAL37vyWdFdOA2LF3tEgXmeT+sVLBVdCbkvmhF5R+yfE06036tXimZKUg6fwzzR13Un6BSNIjgM/4ie6y34GQ7Bg64Pj8g/f76Kj169Cn535c1Okit6xCvlmNB5FcKLopmxHT7x4ncl8jJxywe9Om86J024Yo5Bggx62NVjhs9oCnbAt/BFZDg08C8JX15+I9pc+SU85cr840m409VjpkR05nQc7osMh2BOeApr4GsJfymPiH7KL8MvsNq1rwoeSSN8DPeamM8u0aOzT4455pCsYeUpUqwbC/0mZLDz79ZiAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAaCAYAAADWm14/AAACG0lEQVR4Xu2VSajNURzHf6YkU9nIgoWMa0PKbGMeCqUkxMrwDBssDAsZMyRlZYOykIWpKBuxIUkpZYGVYaFIhsj0+b7f73De6b77bu59srif+tT/nN+5Zz6/a9bkP6cnTsG5OKiIdSoj8TLexeN4Cl/hDRyYtesUduAbXF3U98bH+Bz7FLGGcQy/4fQyEMzEn7i7DDSCRead7ynqc7T9anO/DNRLf3yBb823uhrfzds1lK3mKztcBgp0OdXuWRmol5vmHc8oAwVpotfKQD30wC/mW9uviJWkiW7J6rriYtyLo7P6EbgRJ+MSXJnF2qBk88P8nVejL37Fl9gr6rrjLZxvPvk7ODxiC8z7/WSeP4ZEfUWe4mfz1bSHkpFWvyqrW4jvs/Ih3BbfmpTUJDvkjHnnumRCnVzCTVHeHPF9UU6sx9dZeSeej+955rswB8f/btEOyvN6WhdxGrZE/QHzjKg7Ug4uJuFH+7Nzp/FRfM/Gs+b3Qq9Lk6vKOPMfv8MruB3v4UMcG200UDr/xEncj0vxtvkiRLdQDDY/4o5yTOt5jcEV5pnxoPkAiV1W+TJplcPwCG6IOq1YfYiUQSdGuWb0jLTFR/Eqnmsbbn3C181X2AUf4KiI6S7Mim8N/AEHRLlmpprPXOqypSeWo9ywHC/gmqxe90N/5evwCS7LYjWjI1mLJ3BoEUvonHVslZKYcswE+4uVN2nyz/gFd1hkp58uGrgAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAACL0lEQVR4Xu2WTUhVQRTHT2ghohs3+QGSBYG0SgRxpYkVGUQkBeEiaB0KUSrkIoXENuG2TasiInEhQh+UILRpJ0aofVBCaVEbFVE35v/cM/Pu3PPue2/e6+28P/jBvefM4LnjmZlHlJCQ8D+0GTPRAu/AIXhS5SxH4Q04Cs+rXNE5DR/Cb/AfvB1Np7gFP8JL8Cr8RFKkyym4DPtgB5yBzyIjPDkAn+hgDN3wCuyhzMU3kuSandgZuAOPm/cS+IPkIy1VcANec2JelMLXOpiFVspc/AO4rmKH4C5JCzEXSOY3pUYI7+AbFcvJQSpe8XMk7aDhD3prnsdJ5jeE6YApkv8QL6Y3vDLFKv4nXNJB8AcumGduUZ5fE6YDnpv4YRXPSjGL55WzRbr8NjKvKL5I3rAc530TC2+MWuUROBsTZ8uDWVFs8f06Abbhog6SFL5inl+SzK8O0wG2eLux07gPnyp50q+YOMuni8YWP6ATJKfIZx0Ef+G8eX5MMr8uTAdMmDgvsDeFtk1c8e8pbA8LH8XcTi/MOy9gXHtwDZsk470ptPhBnQB3SY7FMifG7cHje817u3k/awcYuN0mVSwn+RbfRvLH7+kEOEZy2Vx0YtdJ2tL2OF9SH0iOTAv3+RbsdGJe+BY/TNLPfOytkZzdfKZPu4PAObgKR+AY/ApPREYQ1cPv8BG8Cb+Q/JTIG9/i86ECdpF8SKXKWfgy4ha8TOlnvje8QfjKTkhISNjn7AET238sZ/a0gQAAAABJRU5ErkJggg==>