# Claude Cross-Read Synthesis — Three Frontend Recommendations

**Author:** Claude Code · **Date:** 2026-05-25
**Read in full:** `codex-frontend-recommendation.md`, `gemini-frontend-recommendation.md` (against my own `claude-frontend-recommendation.md`).
**Purpose:** Identify robust 3-way consensus, the material divergences the merge must resolve, and the strongest idea from each — *before* the merge. No merging here.

---

## 1. Robust 3-way consensus (carry into the merge as settled)

All three agents, working independently, converged on these. They are the spine of the final design and should not be relitigated:

1. **"Honest terminal" / analytical cockpit** — not a consumer fantasy app, not a chatbot, not a verdict engine. (All three use almost the same phrase.)
2. **Strict Model vs. Market two-lane separation**, never blended; **divergence is a neutral, derived third element**, never a buy/sell label.
3. **Uncertainty is first-class** — Morningstar-style shaded bands (thickness = uncertainty), quantile/interval displays, de-saturation of experimental/low-confidence elements. No false-precision single integers.
4. **Banned verdict/action language** (buy, sell, target, approve, reject, fair, win, loss, bust, grade…) replaced by neutral analytical vocabulary; **enforced by a code-level banned-language scan** (all three call for this).
5. **`decision_supported = false` is a visual state**, universal and non-dismissible — not a footnote.
6. **Mandatory Counter-Argument + Caveats panel** on the player/decision card (the constitution's counter-argument rule made structural). Codex names it "Decision Evidence Card," I named it "Decision Card," Gemini "Player Detail Counter-Argument panel" — same component.
7. **Cliff ages are display warnings only, amber not red.** (The *correct* values are the constitution's RB 26 / WR 28 / TE 30 / QB 33 — see divergence E; some docs drifted.)
8. **Cockpit IA:** persistent left rail (~7–8 surfaces), sticky top **Trust/status strip** with the `decision_supported` chip + freshness, **Cmd-K** command palette, **right-rail Player Inspector drawer** (not a modal).
9. **Same surface set:** Command Center · Roster Audit · Rookie Board · Player Detail · Trade Lab · League Opportunity Map · Trust/Governance · Settings.
10. **Reject Databricks for the front end** — unanimous and emphatic. Local **DuckDB/Parquet** (analytical) + **SQLite/Postgres** (mutable UI state) only if needed. Validates the spend-cap concern directly.
11. **If/when generative UI happens, it is constrained:** closed component catalog, **JSON layout spec → registered components (never raw JSX/HTML)**, every number from a backend tool call, player IDs from a known-ID enum. (Agreement on the *pattern*; see divergence B on *timing*.)
12. **UI is read-only over PVO** — no client-side valuation/scoring/identity-matching; market data fetched separately and merged only in the presentation layer.
13. **Trust/Backtest surface is foundational and built early** — it controls the trust state every other surface reads.

That is an unusually strong consensus for three independent passes. The merge can treat all 13 as decided.

---

## 2. Material divergences the merge MUST resolve

### A. Tech stack — the central disagreement (a clean spectrum)
| Agent | Stack | Build tooling | Posture |
|---|---|---|---|
| **Claude** | FastAPI + **Jinja2 + HTMX + Alpine** + Tailwind + Observable Plot | **None** (no Node build) | Lightest; matches current served-HTML reality; React *island* escape hatch for Trade Lab only |
| **Codex** | FastAPI + **Vite + React + TypeScript** + Radix/shadcn + TanStack Query/Table + Zod | Vite (no Next) | Middle; client state for Trade Lab; React as the path to later gen-UI |
| **Gemini** | **Next.js (App Router) + Vercel AI SDK (UI mode)** + shadcn/Radix | Next.js + AI SDK | Heaviest; generative-UI front-loaded |

This is the one decision that changes everything downstream. It is a spectrum: **no-build server-rendered → React SPA → Next.js+AI-SDK.** My read of the tradeoff:
- The constitution favors the light end (local-first, solo *learning* developer, longevity / no dependency rot, frontend-last).
- Codex's strongest counter — which I under-weighted — is that **Trade Lab is genuinely stateful** (editable asset sets, paired model+market requests, horizon toggles, saved scenarios, browser-verified) and that HTMX/Alpine could become "a second migration before gen-UI." That is a fair, concrete critique of my stack.
- Gemini's Next.js+AI-SDK is the hardest to justify *now*: it front-loads orchestration complexity and a heavy dependency tree against the "frontend last" gate, for a generative capability that all three agree is deferred.

**My recommended resolution for the merge:** decide on the **light-vs-React axis** as the gating question, with Trade Lab's statefulness as the test. Two viable merge positions: (1) **HTMX/Jinja for the 7 read-mostly surfaces + a single React-via-Vite island for Trade Lab** (my position, Codex's escape hatch made explicit), or (2) **Vite+React+TS for everything** (Codex's position) if David is comfortable adopting Node build tooling now to avoid a later migration. **Reject Next.js+AI-SDK as the *first* stack.** This is the highest-value question to put to David.

### B. Generative-UI timing
- **Claude + Codex:** defer hard; build deterministic surfaces first; gen-UI is a *later*, constrained, additive layer (Codex Phase 7; me "much later, David-approved"). Both flag the constitution's **"no generic AI chatbot that bypasses structured decision cards"** non-goal.
- **Gemini:** front-loads it — Next.js + Vercel AI SDK chosen *because of* gen-UI, Command Console central, gen-UI in the build roadmap from the start.
- **Resolution:** Claude+Codex (defer + constrain) is the governance-aligned majority and matches "frontend comes last." Gemini's *safe pattern* (JSON-spec → closed catalog) is right and should be the spec for when gen-UI eventually arrives — but it should not drive the stack choice now.

### C. Build order / what ships first
- **Claude:** shell+library → Player Card + Roster Audit → **Trust** → Rookie → **Trade Lab (#5)** → League Map. (Trade Lab late = highest governance risk, build on a hardened system.)
- **Codex:** shell → **Trust** → **Trade Lab W5b (#2)** → Player Drawer → Roster → Rookie → League → gen-UI. (Trade Lab early because **Phase 23 W5b is the literal next deferred UI task and the backend is ready**.)
- **Gemini:** Trade Lab static early (Phase 2) → integration → gen-UI.
- **Resolution:** All three agree **Trust is early** and **Trade Lab is central**. The disagreement is whether Trade Lab is ~#2 or later. **Codex's grounding is the tiebreaker I under-weighted:** AGENT_SYNC explicitly lists *"W5b — standalone two-panel Trade Lab page"* as the deferred next UI work, with the backend (`/api/trade/reconcile` + `/reconcile/market`) already shipped and Codex-cleared. That is a strong, concrete reason to build Trade Lab early — provided the component library + Trust strip land first so it inherits the contracts. I now lean toward: **shell + library + Trust strip → Trade Lab W5b → fan out to the PVO surfaces.**

### D. `file://` vs served-FastAPI
- **Claude + Codex:** the `file://`/FileReader/localStorage premise is **stale** — the app is served by uvicorn/FastAPI; cache Sleeper in the **backend**.
- **Gemini:** internally contradictory — proposes Next.js+FastAPI HTTP *and* a `file://` + FileReader + localStorage path (Phase 1 + Risk 3) simultaneously.
- **Resolution:** Consensus + Codex's repo inspection settle it: **served FastAPI, JSON-over-HTTP, no `file://` gymnastics, no browser-side Sleeper fetch/cache.** Drop Gemini's FileReader/localStorage path.

### E. Palette specifics
- **Claude + Codex:** **cool blue/cyan = model, amber/gold = market, NO green and NO red as signal** (green = "approve," red = "bad/sell" — banned verdict semantics); position hues are a separate, secondary axis.
- **Gemini:** indigo model / amethyst-purple **and sage-green** market + gold divergence — **includes green** (banned) and is muddled ("Warm Amber - Amethyst").
- **Resolution:** Adopt the Claude+Codex consensus: **blue model / amber market, no green/red signal**, position hues orthogonal (and amber reserved for market + cliff, not given to a position).

---

## 3. Strongest single idea from each (the merge should keep these)

- **From Codex — repo grounding + governance-in-the-component-API.** Codex inspected the *actual* code and anchors everything to real endpoints (`/api/trade/reconcile`, `/reconcile/market`, `/roster/audit`, `/trust-surface/{position}`, `/model-card`, `/rookies/score`) and the real PVO schema, and treats **Phase 23 W5b** as the concrete first build. Its idea that **governance is encoded in the component type signatures** — `ModelLane` *cannot accept* market fields, `DecisionEvidenceCard` *requires* `counterArgument`/`caveats`/`horizon`/`asOf` — is the most enforceable expression of the constitution in the corpus. This is the single most valuable contribution to the merge.
- **From Claude (me) — the three structural contracts + corpus drift-correction.** The Decision Card / Two-Lane / Experimental-treatment trio turns constitutional rules into code-level invariants, and the Section-10 drift list (Engine A/B-as-"market" mislabel, DVS = 0–100 not 0–1000, constitution cliff ages, banned-language self-violations in the source docs, stale `file://`) keeps the merge from inheriting the corpus's errors.
- **From Gemini — the DuckDB-not-Databricks economic case + the (eventual) gen-UI context/cost engineering.** Gemini's clearest contributions are the explicit cost argument for local DuckDB over Databricks, the `LeagueContext` XML system-prompt block, the prompt-caching economics (~$30–55/mo), and **signal-density-sorted Review Areas** on the Command Center. These are the right *spec* for the deferred gen-UI layer and the data substrate.

---

## 4. Where I changed my mind after the cross-read

- **Trade Lab timing:** I now lean earlier (after shell+library+Trust), persuaded by Codex's grounding that W5b is the live, backend-ready sprint item. My "build it last" position over-weighted governance risk and under-weighted the actual repo state.
- **Stack:** I still favor the light end, but Codex's "Trade Lab is stateful → HTMX becomes a second migration" critique is legitimate. The honest merge position is a **David decision** on the light-vs-React axis, with my hybrid (HTMX + one React island) and Codex's all-React as the two live options. Gemini's Next.js+AI-SDK is the one option I'd take off the table for v1.

---

## 5. Recommended shape of the merge (for David to steer)

1. **Ratify the 13-point consensus (Section 1)** as settled.
2. **Resolve the stack (divergence A)** — the one true fork. Put the light-vs-React axis to David explicitly.
3. **Adopt Codex's governance-in-component-API + repo-grounded endpoint map** as the implementation backbone.
4. **Adopt the Claude+Codex palette and `file://`-is-stale + cliff-age + DVS-scale corrections**; prune Gemini's green, FileReader path, and 28/31 cliffs.
5. **Sequence:** shell + component library + Trust strip → **Trade Lab W5b** → Player Drawer/Roster/Rookie → League Map → (later, David-approved) constrained gen-UI per Gemini's JSON-spec pattern.
6. **Defer generative UI**; keep Gemini's safe pattern + context/cost engineering as its future spec.
