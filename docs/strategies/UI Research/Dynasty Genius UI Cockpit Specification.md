# **Technical Systems Architecture and Design Specifications for the Dynasty Genius Phase 17 UI Cockpit**

## **Executive Recommendation**

The transition of the Dynasty Genius analytical interface from Phase 16 (focused on Engine A rookie profiles) to Phase 17 (incorporating Sleeper universe valuations, team value matrices, league opportunity mapping, and version 2 of the market divergence model) demands a rigorous re-engineering of the frontend architecture.1 The primary engineering challenge lies in delivering a high-fidelity, data-dense cockpit that operates with zero external dependencies directly via the local filesystem (file:// protocol).1 In modern web browsers, the security sandboxing of local files introduces severe execution constraints, specifically blocking asynchronous requests (fetch, XMLHttpRequest) and ES module imports when attempting to load local companion assets or datasets.3 To bypass these sandbox limitations without exposing the user to security vulnerabilities or requiring a local web server, the system must employ a programmatic ingestion pipeline utilizing the HTML5 File API and native in-memory array buffers.5  
Furthermore, the design must strictly uphold the Dynasty Genius Constitution. This requires maintaining absolute structural, visual, and computational separation between the proprietary predictive outputs of Engine B (such as Expected Value Above Replacement, ![][image1], and Dynasty Value Score, ![][image2]) and external market price overlays (derived from consensus sources like FantasyCalc). Merging these lanes into a single composite index or outputting binary "buy/sell" recommendations is constitutionally prohibited. Instead, the UI must act as an objective analytical canvas that highlights divergence, leaving transactional interpretation to the user.  
To achieve maximum performance and stability within a single-threaded browser runtime, the UI must avoid resource-heavy external libraries or framework overhead.1 Layout structures, capacity indicators, and density heatmaps must be executed using pure CSS custom properties, native layouts (CSS Grid and Flexbox), and hardware-accelerated transitions.1

## **Evidence Table**

The engineering specifications of the Phase 17 cockpit are derived directly from established security, performance, and analytical rules:

| Engineering Domain | Technical Constraint / Empirical Fact | Architectural Design Specification | Target Validation Metric | Source Citation |
| :---- | :---- | :---- | :---- | :---- |
| **Data Ingestion** | Local file:// protocol execution blocks standard asynchronous file reads and module imports due to strict browser origin security controls (specifically CVE-2019-11730). | Implement programmatic file selection utilizing FileReader.readAsText() to ingest local JSON payloads (e.g., Sleeper league files, FantasyCalc value matrices) directly into active document memory. | Zero origin or security exceptions in the browser console during payload loading. | 3 |
| **State Persistence** | localStorage behavior on file:// is highly variable; Firefox isolates storage keys uniquely per file URL, while Chrome and Safari may block storage writes entirely or throw a SecurityError. | Implement an abstract, self-testing storage driver that utilizes standard localStorage when permitted, automatically falling back to an in-memory session object coupled with serialized JSON state exports. | Flawless cross-session state restoration without script crashes under restricted local configurations. | 8 |
| **Visual Isolation** | Merging machine-learning projections with raw market sentiment can lead to analytical bias, violating the core system rules. | Build distinct physical visual lanes utilizing contrasting HSL tokens, isolating predictive metrics from raw market pricing. | Clear visual separation between models and market consensus, preventing any combined "buy/sell" outputs. | 6 |
| **Age Cliff Modeling** | Player aging curves do not exhibit linear decay; instead, performance remains stable before hitting sudden, position-specific cliffs. | Map progress-bar states to step-functions using CSS variables, highlighting critical age thresholds (Running Backs at age 27, Wide Receivers at age 29\) through sudden, high-contrast color shifts. | Gauge fill transitions from green to amber/red at precise step-function age boundaries rather than through a gradual color gradient. | 12 |
| **UI Performance** | Intensive real-time operations, such as filtering a 12x12 heatmap grid, can cause layout thrashing and main-thread freezing in single-threaded environments. | Utilize absolute-positioned CSS grid containers, hardware-accelerated transforms, and pure CSS transitions to keep visual updates fast and fluid. | Main-thread frame rates remain at a stable 60 frames-per-second (FPS) during active visual rendering and filtering. | 1 |

## **Conflicts and Resolutions**

### **Conflict 1: Local Origin Sandboxing vs. Dynamic JSON Ingestion**

Under modern browser implementations of the Same-Origin Policy, any resource executed via the file:// protocol is assigned an opaque, unique origin.3 Consequently, an index.html file running locally is blocked from making local asynchronous requests (e.g., fetch('./data/questions.json')), as the browser treats any local file on the hard drive as a cross-origin resource.3 This prevents the dynamic loading of updated player tables or league rosters.3

* **Resolution**: The cockpit will handle data loading through a dedicated, local-first file drop zone. The interface registers a change listener on a standard, non-cors-restricted HTML \<input type="file" multiple\> element.5 This triggers a FileReader instance to parse the files locally as text.5 This architecture shifts data ingestion from an origin-bound network request to an explicit, user-initiated file import, completely bypassing local security sandbox restrictions without requiring browser security workarounds.3

### **Conflict 2: Inconsistent Local Storage Engines under file://**

The Web Storage specification states that browsers are not required to support localStorage for resources loaded via the file:// protocol.10 In practice, Firefox creates separate local storage objects for every unique file URL, while Chrome and Chromium-based Edge throw a SecurityError or block writing entirely depending on the user's active privacy policies and cookie-blocking configurations.9

* **Resolution**: The application will implement a unified storage driver that runs an immediate write-and-delete test upon initialization to detect storage capabilities:  
  JavaScript  
  const LocalStorageDriver \= {  
      isAvailable: () \=\> {  
          try {  
              const testKey \= "\_\_dynasty\_test\_\_";  
              localStorage.setItem(testKey, "1");  
              localStorage.removeItem(testKey);  
              return true;  
          } catch (error) {  
              return false;  
          }  
      }  
  };

  If local storage access is restricted, the engine automatically falls back to an in-memory session object. To ensure user changes are not lost between sessions, the UI will display a persistent "Export Session" action button when operating in fallback mode. This allows the user to download their settings and configurations as a single, portable JSON backup file.5

### **Conflict 3: Model Purity vs. Market Overlays (The Dynasty Genius Constitution)**

Merging predictive indicators (Engine B ![][image1] and ![][image2]) with consensus market pricing (such as FantasyCalc data) can easily lead to analytical bias. Additionally, displaying binary "buy/sell" recommendations violates the project's core focus on delivering objective, multi-layered data.

* **Resolution**: The Trade Lab cockpit enforces strict physical and visual separation between model evaluations and consensus market data. Predictive evaluations are positioned in a dedicated left-hand pane (styled with high-contrast cyan accents), while consensus market metrics are isolated in a right-hand pane (styled with purple/amethyst accents).6 Value divergence is calculated using a clean, objective formula:  
  ![][image3]  
  The interface displays this calculated delta as a neutral numerical variance without attaching subjective labels (such as "undervalued" or "bad deal"), preserving analytical objectivity.

### **Conflict 4: Age Cliff Modeling Complexity vs. Performance-Friendly Rendering**

Player aging curves do not follow a smooth, continuous decline. Historical analysis indicates that elite fantasy football assets experience stable, step-like performance fluctuations followed by a steep cliff, which varies significantly by position.13 For example, running backs often hit a sharp performance drop-off at age 27 14, whereas elite wide receivers maintain production longer, hitting a distinct decline phase around age 29\.15 Displaying these complex, multi-variable age cliffs without overloading the browser's rendering thread presents a performance challenge.

* **Resolution**: The UI uses high-performance SVG-driven progress gauges that map these positional decay patterns to discrete color phases.12 Calculations use simple CSS custom properties, avoiding heavy JavaScript loops on every paint cycle. Positional age-out thresholds are computed using step-function logic:  
  ![][image4]  
  These thresholds are rendered in-browser using performance-optimized SVG layout engines.12

## **Workstreams and Ordering**

To successfully deploy the Phase 17 upgrade, engineering teams must execute the following sequential development phases:

### **Task Execution and Complexity Matrix**

To ensure systematic deployment, tasks are categorized by complexity, estimated effort, and structural dependencies:

| Task ID | Component Group | Primary Task Description | Dependencies | Complexity Weight |
| :---- | :---- | :---- | :---- | :---- |
| **TS-01** | Core Architecture | Implement programmatic file reader drop zones and load JSON data directly into the active document memory.5 | None | Medium |
| **TS-02** | Core Architecture | Build the unified local storage driver with safe try-catch wrappers and programmatic JSON backup fallbacks.8 | None | Low |
| **TS-03** | Core Architecture | Map the global application state object (window.DYNASTY\_STATE) to handle dynamic updates.1 | TS-01, TS-02 | Medium |
| **DS-01** | Layout Engine | Design and implement the global design tokens and HSL system variables to support clean dark mode styling.6 | None | Low |
| **DS-02** | Layout Engine | Code the foundational CSS Grid and Flexbox layouts for the dual-panel Trade Lab interface.2 | DS-01 | Medium |
| **DS-03** | Layout Engine | Build the responsive 12x12 grid container for the League Pulse heatmap module.2 | DS-01 | High |
| **CP-01** | Component Rendering | Develop SVG-driven circular progress bars to display roster capacity costs.12 | DS-01, DS-02 | Medium |
| **CP-02** | Component Rendering | Code the dynamic data-rendering logic for the League Pulse heatmap cells. | TS-03, DS-03 | High |
| **CP-03** | Component Rendering | Implement smooth, hardware-accelerated CSS transitions and interactive hover effects.6 | DS-01, DS-02 | Low |
| **QA-01** | Logic Verification | Integrate position-specific step-function age cliff calculations into the roster audit metrics.14 | TS-03, CP-01 | High |
| **QA-02** | Logic Verification | Create explicit validation warning overlays for unverified or fuzzy player name matches. | TS-03, DS-02 | Medium |
| **QA-03** | Logic Verification | Run a comprehensive design and copy audit to ensure the application remains strictly objective and fully compliant with the project's constitution. | All | Low |

### **Phase 1: Core Storage and Parser Foundation**

The initial phase focuses on establishing a robust, serverless storage and data-loading layer.1 First, developers will implement the HTML5 file reader drop zone (TS-01) to parse local Sleeper and FantasyCalc JSON files.5 Next, the team will deploy the unified storage driver (TS-02) to handle browsers with restricted or sandboxed localStorage capabilities.10 These components will then feed into a unified, in-memory state manager (TS-03), which serves as the single source of truth for the active session.8

### **Phase 2: Design System Variables and Layout Framework**

With the data-loading layer in place, developers will build the core design framework. This begins with defining system-wide HSL design tokens (DS-01) to support high-contrast dark mode styling.11 These tokens will then be integrated into the CSS Grid layout for the dual-panel Trade Lab interface (DS-02), keeping active projections visually separate from external market overlays.2 Finally, the team will build the structural layout for the 12x12 League Pulse heatmap grid (DS-03), which maps out team values and league-wide trading opportunities.2

### **Phase 3: Component Development and Animations**

The third phase brings the interface to life with interactive, high-performance visual components.6 Developers will build the SVG-based circular progress bars (CP-01) to display roster capacity indicators using dynamic CSS variables.12 Next, the dynamic rendering logic for the League Pulse heatmap cells (CP-02) will be implemented, populating the grid with calculated team valuations. These components will be styled with lightweight, hardware-accelerated CSS transitions (CP-03) to ensure responsive user feedback without adding framework overhead.6

### **Phase 4: Logic Integration, Validation, and Alignment**

The final phase focuses on system calibration and compliance validation. Developers will integrate position-specific, step-function age cliff calculations into the roster audit metrics (QA-01).14 To protect analytical integrity, the team will build explicit warning overlays (QA-02) that flag unverified or fuzzy player name matches for manual review. Finally, the entire cockpit will undergo a rigorous design and copy audit (QA-03) to ensure all features remain strictly objective and fully compliant with the project's constitution.

## **Risks**

The zero-dependency, filesystem-driven architecture introduces specific risks that must be managed through careful code design:

### **1\. Data Mismatch Errors in Multi-System Environments**

When combining data from different sources (such as Sleeper API exports and FantasyCalc valuation tables), discrepancies between player identification systems can result in silent data mapping failures or incorrect player valuations.20 For example, minor variations in spelling or the absence of a unique ID link can cause the system to misattribute a player's market value.

* **Mitigation Strategy**: The cockpit will not attempt to guess or auto-resolve ambiguous matches. If a player is not linked by a verified, explicit ID, the interface will display a clear warning badge requiring manual user validation instead of silently matching with unverified values.

### **2\. Rendering Lag Under High-Density Data Grids**

Loading and rendering large rosters or interactive 12x12 heatmaps can cause significant layout thrashing and main-thread freezing in a single-threaded vanilla JavaScript environment.1

* **Mitigation Strategy**: The interface will use absolute-positioned grid layouts and offload non-visual calculations to non-blocking runtime tasks, ensuring smooth performance. Updates to the DOM are managed efficiently using inline CSS custom properties, preventing costly layout calculations.6

### **3\. State Invalidation Due to Restricted File System Storage**

Because the application runs via the file:// protocol, browser security rules can prevent the application from writing state data to disk, causing the user to lose their settings and notes between sessions.10

* **Mitigation Strategy**: The application isolates all storage-access APIs inside safe try-catch blocks. If storage write requests fail, the driver seamlessly falls back to an in-memory session object and alerts the user to export their configuration manually.8

## **Open Decisions for David**

The following strategic architectural choices require direct sign-off before finalizing production-ready source code:

| Decision Point | Strategic Trade-Off Analysis | Architectural Impact | Compliance Footprint |
| :---- | :---- | :---- | :---- |
| **Fuzzy Match Logic** | **Option A**: Lock trading features if any player in the deal has an unverified ID match. **Option B**: Allow simulations to continue, but display a persistent, high-contrast warning badge on unverified players. | **Option A**: Prevents any chance of incorrect valuations skewing results, but creates a more restrictive user experience. **Option B**: Offers a more flexible workflow while using clear visual warnings to ensure transparency. | **Option B** is recommended. This approach keeps the platform highly usable while ensuring users are clearly informed of any unverified data. |
| **Local Storage Fallback** | **Option A**: Prompt the user to manually export a state JSON file whenever they make changes.5 **Option B**: Serialize the entire application state into a compressed URL hash string. | **Option A**: Highly reliable and secure, but requires manual file management from the user. **Option B**: Automatic and seamless, but long configurations can exceed browser URL length limits. | **Option A** is recommended. This approach ensures maximum reliability and stability across all browsers when running on the local file system.10 |
| **Age Cliff Visual States** | **Option A**: Apply fixed, standard positional cliffs to all players (e.g., age 27 for Running Backs, age 29 for Wide Receivers).14 **Option B**: Adjust thresholds dynamically, extending warning triggers for players with historically elite profiles.15 | **Option A**: Simple, clean, and highly objective, but may oversimplify career trajectories for elite players. **Option B**: Offers a more nuanced analysis of elite assets, but introduces subjective tier assignments. | **Option A** is recommended. This keeps the metric simple and objective, avoiding subjective tiering in compliance with the system's core design rules. |

## **Acceptance Criteria**

### **CSS Design Tokens and Variables**

CSS  
:root {  
  /\* Systemic HSL Color Palette \*/  
  \--color\-bg-dark: hsl(224, 71%, 4%);  
  \--color\-panel-glass: rgba(10, 15, 30, 0.6);  
  \--color\-border\-glass: rgba(255, 255, 255, 0.08);  
    
  /\* Strictly Segregated Analytical Lanes \*/  
  \--color\-engine-b\-cyan: hsl(180, 100%, 45%);    /\* Proprietary ML Models (xVAR/DVS) \*/  
  \--color\-market-amethyst: hsl(275, 90%, 60%);  /\* Consensus Market Overlays \*/  
    
  /\* Roster Audit and Age-Out Warnings \*/  
  \--color\-shelf-optimal: hsl(145, 80%, 45%);    /\* Young / High Longevity \*/  
  \--color\-shelf-warning: hsl(38, 92%, 50%);     /\* Approaching Age Cliff \*/  
  \--color\-shelf-critical: hsl(0, 85%, 55%);      /\* Cliff Exceeded \*/  
    
  /\* Text and High-Contrast Accessibility \*/  
  \--color\-text-primary: hsl(210, 40%, 98%);  
  \--color\-text-muted: hsl(215, 20%, 65%);  
    
  /\* Sizing and Transition Controls \*/  
  \--border-radius\-panel: 12px;  
  \--transition\-normal: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);  
}

* **Verified Behavior**: Elements styled with these variables must render correctly in both Chromium-based browsers and Firefox without requiring external stylesheets.1 Analytical lanes must display clear visual separation, using distinct colors to distinguish proprietary projections from market overlays.6

### **Standalone Trade Lab Splits (Double-Panel Layout)**

HTML  
\<div class\="trade-lab" style\="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; box-sizing: border-box; width: 100%;"\>  
    
  \<div class\="panel-evaluation" style\="background: var(--color-panel-glass); border: 1px solid var(--color-border-glass); border-radius: var(--border-radius-panel); padding: 20px; backdrop-filter: blur(12px); \-webkit-backdrop-filter: blur(12px);"\>  
    \<div class\="panel-header" style\="border-bottom: 2px solid var(--color-engine-b-cyan); margin-bottom: 15px; padding-bottom: 10px;"\>  
      \<h2 style\="color: var(--color-text-primary); font-size: 1.25rem; font-weight: 700; margin: 0; text-transform: uppercase;"\>  
        Engine B Evaluations  
      \</h2\>  
    \</div\>  
    \<div class\="panel-content" id\="engine-b-assets-container"\>  
      \</div\>  
  \</div\>  
    
  \<div class\="panel-market" style\="background: var(--color-panel-glass); border: 1px solid var(--color-border-glass); border-radius: var(--border-radius-panel); padding: 20px; backdrop-filter: blur(12px); \-webkit-backdrop-filter: blur(12px);"\>  
    \<div class\="panel-header" style\="border-bottom: 2px solid var(--color-market-amethyst); margin-bottom: 15px; padding-bottom: 10px;"\>  
      \<h2 style\="color: var(--color-text-primary); font-size: 1.25rem; font-weight: 700; margin: 0; text-transform: uppercase;"\>  
        Market Consensus Overlays  
      \</h2\>  
    \</div\>  
    \<div class\="panel-content" id\="market-consensus-assets-container"\>  
      \</div\>  
  \</div\>  
    
\</div\>

* **Verified Behavior**: The Trade Lab must scale fluidly across different viewport sizes. The analytical panes must remain visually distinct, with no structural or data overlap between the proprietary model lane and the market consensus lane.6

### **Roster Audit Capacity Gauge**

HTML  
\<div class\="gauge-wrapper" style\="align-items: center; display: flex; flex-direction: column; position: relative; width: 140px;"\>  
  \<div class\="svg-container" style\="position: relative; width: 120px; height: 120px;"\>  
    \<svg viewBox\="0 0 100 100" style\="width: 100%; height: 100%; transform: rotate(-90deg);"\>  
      \<circle cx\="50" cy\="50" r\="42" fill\="transparent" stroke\="rgba(255, 255, 255, 0.05)" stroke-width\="8" /\>  
      \<circle class\="capacity-ring" cx\="50" cy\="50" r\="42" fill\="transparent"   
              stroke\="var(--color-shelf-optimal)"   
              stroke-width\="8"   
              stroke-linecap\="round"  
              stroke-dasharray\="263.89"   
              style\="stroke-dashoffset: calc(263.89 \- (263.89 \* var(--capacity-percent, 75)) / 100); transition: var(--transition-smooth);" /\>  
    \</svg\>  
    \<div class\="percentage-display" style\="color: var(--color-text-primary); font-family: monospace; font-size: 1.25rem; font-weight: 700; left: 50%; position: absolute; top: 50%; transform: translate(-50%, \-50%);"\>  
      \<span id\="capacity-value"\>75%\</span\>  
    \</div\>  
  \</div\>  
  \<span class\="gauge-label" style\="color: var(--color-text-muted); font-size: 0.75rem; margin-top: 10px; text-transform: uppercase; letter-spacing: 0.05em;"\>Roster Lifespan\</span\>  
\</div\>

* **Verified Behavior**: The circular progress ring must update its length dynamically using its CSS transition rules.12 The color of the progress bar must update immediately based on the age characteristics of the players on the roster, shifting colors at exact positional age thresholds.14

### **Heatmap & Matrix Layouts (League Pulse Grid)**

HTML  
\<div class\="heatmap-wrapper" style\="background: var(--color-panel-glass); border: 1px solid var(--color-border-glass); border-radius: var(--border-radius-panel); padding: 20px; width: 100%; box-sizing: border-box;"\>  
  \<div class\="heatmap-header" style\="margin-bottom: 15px;"\>  
    \<h3 style\="color: var(--color-text-primary); font-size: 1.1rem; margin: 0; text-transform: uppercase;"\>League Pulse Valuation Grid\</h3\>  
  \</div\>  
    
  \<div class\="heatmap-grid" style\="display: grid; grid-template-columns: repeat(12, 1fr); gap: 4px; width: 100%;"\>  
    \<div class\="heatmap-cell"   
         style\="background-color: hsla(180, 100%, 45%, var(--val-density, 0.8));   
                aspect-ratio: 1;   
                border-radius: 4px;   
                transition: var(--transition-normal);   
                position: relative;"  
         onmouseenter\="this.style.transform='scale(1.15)'; this.style.zIndex='10'; this.style.boxShadow='0 0 12px var(--color-engine-b-cyan)';"  
         onmouseleave\="this.style.transform='scale(1)'; this.style.zIndex='1'; this.style.boxShadow='none';"\>  
           
         \<div class\="cell-tooltip" style\="display: none; position: absolute; bottom: 125%; left: 50%; transform: translateX(-50%); background: \#000; color: \#fff; padding: 4px 8px; border-radius: 4px; font-size: 0.7rem; white-space: nowrap; pointer-events: none;"\>  
           Team 4 Val: \+1.4 VAR  
         \</div\>  
    \</div\>  
  \</div\>  
\</div\>

* **Verified Behavior**: The heatmap grid must align correctly, mapping 12 equal-width columns. Cell hover transformations must render smoothly at 60 FPS without triggering layout recalculations in the browser's rendering thread.2

### **Micro-Animations and Dynamic States**

CSS  
/\* Card Focus and Selection Effects \*/  
.card-interactive {  
  background: var(--color-panel-glass);  
  border: 1px solid var(--color-border-glass);  
  border-radius: 8px;  
  padding: 12px;  
  position: relative;  
  transition: var(--transition-normal);  
  will-change: transform, border-color, box-shadow;  
}

.card-interactive:hover {  
  transform: translateY(-3px);  
  border-color: var(--color-engine-b-cyan);  
  box-shadow: 0 8px 20px rgba(6, 182, 212, 0.15);  
  cursor: pointer;  
}

.card-interactive:active {  
  transform: translateY(-1px);  
  box-shadow: 0 4px 10px rgba(6, 182, 212, 0.1);  
}

/\* Warning Badge for Fuzzy Match Flags \*/  
.match-warning-badge {  
  background: hsla(38, 92%, 50%, 0.15);  
  border: 1px solid var(--color-shelf-warning);  
  color: var(--color-shelf-warning);  
  font-size: 0.75rem;  
  font-weight: bold;  
  padding: 4px 8px;  
  border-radius: 4px;  
  display: inline-flex;  
  align-items: center;  
  gap: 6px;  
  animation: pulse-border 2s infinite ease-in-out;  
}

@keyframes pulse-border {  
  0% { border-color: hsla(38, 92%, 50%, 0.5); }  
  50% { border-color: hsla(38, 92%, 50%, 1); }  
  100% { border-color: hsla(38, 92%, 50%, 0.5); }  
}

* **Verified Behavior**: Interactable cards must scale and transform smoothly on hover. Warning badges must pulse dynamically using pure CSS keyframes, completely avoiding JavaScript runtime overhead.6

## **Conclusions**

Implementing this zero-dependency, filesystem-driven architecture ensures the Dynasty Genius Phase 17 UI cockpit remains secure and highly performant across all browsers without requiring a local web server.1 Programmatic data loading through a local file drop zone completely bypasses local browser security restrictions, while the unified storage driver guarantees reliable state persistence.5  
By strictly segregating proprietary projections and market overlays, the cockpit preserves analytical objectivity in alignment with the project's constitutional mandates. The layout specifications outlined in this report provide developers with a production-ready, high-performance blueprint to execute the Phase 17 upgrade.

#### **Works cited**

1. How I Built a Real-Time Dashboard from Scratch Using Vanilla JavaScript (No Frameworks\!), accessed May 25, 2026, [https://medium.com/@michaelpreston515/how-i-built-a-real-time-dashboard-from-scratch-using-vanilla-javascript-no-frameworks-f93f3dce98a9](https://medium.com/@michaelpreston515/how-i-built-a-real-time-dashboard-from-scratch-using-vanilla-javascript-no-frameworks-f93f3dce98a9)  
2. Building a Vanilla JS Intranet Dashboard: A Developer-Centric Approach \- DEV Community, accessed May 25, 2026, [https://dev.to/discovered12345/building-a-vanilla-js-intranet-dashboard-a-developer-centric-approach-47jo](https://dev.to/discovered12345/building-a-vanilla-js-intranet-dashboard-a-developer-centric-approach-47jo)  
3. How to import data from .json file in local machine using vanilla JS? \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/learnjavascript/comments/uoxz4e/how\_to\_import\_data\_from\_json\_file\_in\_local/](https://www.reddit.com/r/learnjavascript/comments/uoxz4e/how_to_import_data_from_json_file_in_local/)  
4. Requesting files with javascript when using file:// protocol \[duplicate\] \- Stack Overflow, accessed May 25, 2026, [https://stackoverflow.com/questions/66298382/requesting-files-with-javascript-when-using-file-protocol](https://stackoverflow.com/questions/66298382/requesting-files-with-javascript-when-using-file-protocol)  
5. How to build a file upload service with vanilla JavaScript \- LogRocket Blog, accessed May 25, 2026, [https://blog.logrocket.com/how-to-build-file-upload-service-vanilla-javascript/](https://blog.logrocket.com/how-to-build-file-upload-service-vanilla-javascript/)  
6. Prompting for frontend aesthetics | Claude Cookbook, accessed May 25, 2026, [https://platform.claude.com/cookbook/coding-prompting-for-frontend-aesthetics](https://platform.claude.com/cookbook/coding-prompting-for-frontend-aesthetics)  
7. How to Fetch data from local JSON file and render it to HTML document by using Vanilla JavaScript \- Medium, accessed May 25, 2026, [https://medium.com/@akshaykrdas001/how-to-fetch-data-from-local-json-file-and-render-it-to-html-document-with-using-vanilla-javascript-a0191a894f25](https://medium.com/@akshaykrdas001/how-to-fetch-data-from-local-json-file-and-render-it-to-html-document-with-using-vanilla-javascript-a0191a894f25)  
8. State Management in Vanilla JS: 2026 Trends | by Chirag Dave \- Medium, accessed May 25, 2026, [https://medium.com/@chirag.dave/state-management-in-vanilla-js-2026-trends-f9baed7599de](https://medium.com/@chirag.dave/state-management-in-vanilla-js-2026-trends-f9baed7599de)  
9. Accessing localStorage for local files from Chrome and Firefox \- Stack Overflow, accessed May 25, 2026, [https://stackoverflow.com/questions/78146699/accessing-localstorage-for-local-files-from-chrome-and-firefox](https://stackoverflow.com/questions/78146699/accessing-localstorage-for-local-files-from-chrome-and-firefox)  
10. Window: localStorage property \- Web APIs | MDN, accessed May 25, 2026, [https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)  
11. light-dark() CSS function \- MDN Web Docs \- Mozilla, accessed May 25, 2026, [https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/color\_value/light-dark](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/color_value/light-dark)  
12. Creating a circular progress bar with CSS | Reintech media, accessed May 25, 2026, [https://reintech.io/blog/creating-a-circular-progress-bar-with-css](https://reintech.io/blog/creating-a-circular-progress-bar-with-css)  
13. We (Still) Probably Think about Age the Wrong Way and Dented Cans: RSP Film and Theory with Adam Harstad and Matt Waldman \- Rookie Scouting Portfolio, accessed May 25, 2026, [https://mattwaldmanrsp.com/2024/11/14/we-still-probably-think-about-age-the-wrong-way-and-dented-cans-rsp-film-and-theory-with-adam-harstad-and-matt-waldman/](https://mattwaldmanrsp.com/2024/11/14/we-still-probably-think-about-age-the-wrong-way-and-dented-cans-rsp-film-and-theory-with-adam-harstad-and-matt-waldman/)  
14. Has the "RB Cliff" moved? : r/DynastyFF \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/DynastyFF/comments/1gqk7ki/has\_the\_rb\_cliff\_moved/](https://www.reddit.com/r/DynastyFF/comments/1gqk7ki/has_the_rb_cliff_moved/)  
15. When to Expect an Elite Wide Receiver to Decline in Fantasy Football \- Footballguys, accessed May 25, 2026, [https://www.footballguys.com/article/2025-when-to-expect-an-elite-wide-receiver-to-decline-fantasy-football](https://www.footballguys.com/article/2025-when-to-expect-an-elite-wide-receiver-to-decline-fantasy-football)  
16. Using localStorage in Modern Applications \- A Comprehensive Guide \- RxDB, accessed May 25, 2026, [https://rxdb.info/articles/localstorage.html](https://rxdb.info/articles/localstorage.html)  
17. Upload File with Vanilla JavaScript and Loading Animation \- Stack Abuse, accessed May 25, 2026, [https://stackabuse.com/upload-file-with-vanilla-javascript-and-loading-animation/](https://stackabuse.com/upload-file-with-vanilla-javascript-and-loading-animation/)  
18. How To Make Circular Progress Bar | HTML CSS JavaScript \- DEV Community, accessed May 25, 2026, [https://dev.to/robsonmuniz16/how-to-make-circular-progress-bar-html-css-javascript-1cl8](https://dev.to/robsonmuniz16/how-to-make-circular-progress-bar-html-css-javascript-1cl8)  
19. stroke-dasharray CSS property \- MDN Web Docs, accessed May 25, 2026, [https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/stroke-dasharray](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/stroke-dasharray)  
20. Sleeper users: Here's a Google Sheets doc I made to export all of your fantasy football league data \- Reddit, accessed May 25, 2026, [https://www.reddit.com/r/fantasyfootball/comments/1qv4uqm/sleeper\_users\_heres\_a\_google\_sheets\_doc\_i\_made\_to/](https://www.reddit.com/r/fantasyfootball/comments/1qv4uqm/sleeper_users_heres_a_google_sheets_doc_i_made_to/)  
21. fast\_scraper\_roster: Get team rosters for multiple seasons \- RDocumentation, accessed May 25, 2026, [https://www.rdocumentation.org/packages/nflfastR/versions/4.3.0/topics/fast\_scraper\_roster](https://www.rdocumentation.org/packages/nflfastR/versions/4.3.0/topics/fast_scraper_roster)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAaCAYAAADrCT9ZAAADEElEQVR4Xu2WWahOURiGX/NUhkzJlFyQWS4UFyehpFwgIeRCMiWZc0NSREIkShlCioy5UOSUMRcoLmQ8xxQ3yBCZ4n19a59/7+/8Z+8/Dm72U0/n7O9bZ+191lrfWgvIycn5yyyl7Xzwf9GTPqYV9D59QO/SprE2jUP8aWhXSfvF8mlMpD9omU8E1Pcd+py+pC/oI9g7HtITdFLUuLaoT/fDPmyBy0W0oR/oYpQ+Wxq0J7B+J7icZzas3YrwXIe2ostCfEOI1xrLYR3rBcVYSFf5YAZrYKtF/c5zOc9uWLtBPgGb+fe0uU/8CZNhL9zmE6QjvU4b+UQK3egVOg3W7+pkuhoqmTe0ros3pF/od9rF5YoygA5H4WPb0sGFdBVDYB920ifIETrCBzM4RofC/k797kimE2hAa3r3VFhuu094GtDDdB/dSm/TlXQXPU43FZr+ojOs45suPpoedLEsRsL2BKEBV78agJqYAmujsonQZqYS0lLejOQmWpT1KOxuWhbq8AJtTb/S8yEXUY9+o69isSb0Bm0fi2Whgb5GO4TnaCAvVbWojiZBbS7T0+HnW9i7B8bapaJRiegN63AGbPdbRHvE8hE6ntSuWXheS+cU0iWhvpfEnjUz6vNeLOZR/b5Gsn5nwer2t46kubCXaiNJ4yKsnc7mXrAV4TeRNLQS9OE6UytQOE/Vp2asGJ1QvH61uhQ/6+IlcRQ2e1moVvWSUbSc9k+mM9kLq3mPZlD9qi490S6ulREnqn0Neia6SGg5joPVpkb9QCw/PuQ862Av0XGy0eWy0C5/ygcDV2H9dvUJsgeW8+fv/BDXTSuTMlhjLeUx4XdtYqIFbJfWoHii204lCnVcCn1hS7jY7IpzsH41KHH0DbquvkP10tG5rb85FJ5nIqWedfXTaG+BXSTGwv6JnbAR61PVMomWsl5S04d7tPtX0k/0c/g5LJafDqtnxaXquBxWn7dgN6iPwWewYzOie4hpIDURZ1DCJMQ3KdWPDvg0dHfNuvP+S1rCLi6a2WIrMicnJycnJ+c/8xNB6a/Y6s/bdQAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAaCAYAAADxNd/XAAACjklEQVR4Xu2WSahPURzHv8YksvDwQhnCUxLKKytl2kjJwkIssJBCsbGTpVCGFSVJUTKUoZQhycKQyEIyv2ceMyxYkOH79bund+6vc25Xdrqf+tTr9zvnvHPP/3d+9wINDf8trXQOHRbFxkR/J2mnD+gr+pq+pB30Ee2kt+kmOqQYH9hFn8Lmyod0fWkEsI6+gK0j98bJiNF0Hz1Od9In9ADdQLdE4yo5RH/RaVGsH2wTz2APNDzKifGwOdpkX5cLbKcX6QzarZz6wyDYgS2KYhq3H7b2vCheyWP6kXb3CTITtpgW9XylX3ywoD+9RQf6RIQO7pgPktn0Bx3gEyl0strgCZ8o6EHf0G+0p8vdg81NbXIbXeaDEVrrM93qE7D1rvtgjsWwTaz1iYjLsDEjXfxsEZ/i4pPoBaTLJjAYNlclNM7letOpLpZlD2yhyT4R8R42Rp0iRhdT8flRTGV4iU6IYjluwuarXHTiahgTSyNqoC7yAen6F+pA+ieqdX+iG4vcmii2EraROqgDhV83+B12B2oR6l8tLMcK2JjUJVaNKxfanR5Wp5rrSjnU0VbTa7D1rpbTeZbAJlTV/3nYmLjFBmbBcuom4iCd25XOMpS2+CCs9tW21TRqEWo4V//6KX/COkqKsbD5V2Bv0SPldBa9CKf7YMEZesoHc3QgX/+j6HN6jvZyuUAf2AO8pTdgJ1uHO3SpD8Lm692y3CdStMH++UkXV3tTPX6im2HvgSr0CaJ1VvlEhtAU7qP8XtG9OYyucsyiWta3i7qKFtIT67umE/YdInegfh/WhVMJpX7FFAvpadjFf0ePwrrZXbobf98A/hndE5VbXdTnwyZH0AWwbqbvooaGhoaGhkp+A0dlkDEsRy1tAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,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>