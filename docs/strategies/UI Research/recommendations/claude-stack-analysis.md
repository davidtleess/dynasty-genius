# Frontend Stack Pressure Test — Engineering Analysis (Claude Code)

**Author:** Claude Code · **Date:** 2026-05-25
**Mandate:** Do the engineering analysis that should have preceded the stack vote. Test whether the "one React island" framing (Stack B) survives the project's actual final-state shape. Section 3 (Alpine `$store` pseudocode) is treated as the load-bearing artifact.
**Sources read for this analysis:** all UI Research docs (prior), `docs/superpowers/specs/2026-05-13-phase8-decision-surfaces.md`, `docs/roadmap.md`, the live route surface (`app/api/routes/*`), the **actual current frontend** (`src/dynasty_genius/dashboard/rookie_board.html`, 475 lines), the product constitution + north-star architecture.

**Stacks under test:**
- **Stack A:** Vite + React + TypeScript, served by FastAPI.
- **Stack B:** HTMX/Jinja/Alpine + one React island for Trade Lab.

---

## Grounding fact that frames everything

The current Rookie Board (`rookie_board.html`) is **already a stateful client surface** with **no framework**: tab state, position filter, client-side sort, a derived "available-now" panel, live draft-state dimming, and a `fetch('/refresh', POST)` — ~300 lines of hand-rolled vanilla JS with `onclick` + `innerHTML` re-render. So the question "is there client statefulness beyond Trade Lab?" is already answered *in the shipped code*: yes, in the simplest surface. The only question is how much more arrives at end-state and whether it isolates.

---

## Section 1 — Every surface in the final-state app

From the Phase 8 spec (8.1–8.5), the UI corpus, and the cross-cutting patterns named in the challenge. Nothing skipped for being "later/experimental."

**Primary surfaces:**
1. Home / Command Center
2. Roster Audit (Phase 8.1)
3. Rookie Board (Phase 8.2)
4. Trade Lab (Phase 8.3 experimental → Phase 23 W5b standalone page)
5. League Opportunity Map / League Pulse (Phase 8.5, deferred)
6. Market Divergence scanner (Phase 17.4 artifacts)
7. Trust / Governance surface
8. Settings / League Context
9. Research Assistant (gen-UI query workspace, deferred/gated)
10. Waiver Radar (Phase 8.4, deferred)

**Cross-cutting UI patterns (each is a surface-spanning concern, not contained to one page):**
11. Player Detail drawer (opens from any row on any surface; URL-hash addressable; interactive comparables that re-target the drawer; must preserve underlying scroll/sort/filter)
12. ⌘K command palette (fuzzy search ~500 players + ~60 rookies + 12 owners + surfaces + saved research; keyboard nav; recents-at-top; virtualized at 600+)
13. Posture selector (global; filters UI on multiple surfaces)
14. Trust Strip (global; reads decision_supported + freshness on every surface)
15. Trade Lab horizon control (1/3/5-yr re-render — part of Trade Lab)
16. "Open Decision Items" continuity strip (saved scenarios + pinned questions, written by Trade Lab and Research, read on Home)
17. Saved Trade scenarios (persisted, replayable)
18. Per-table filter/sort (on Roster, Rookie, Market Divergence, League)

---

## Section 2 — Statefulness matrix

Axes scored 0–3: **CO** = constructed-object complexity · **CC** = cross-component coordination · **GS** = global-state ripple · **RT** = real-time interaction density. Total /12. **≥6 = island candidate; ≥9 = unambiguous island.** Scored, not argued.

| Surface | CO | CC | GS | RT | **Total** | Verdict |
|---|---|---|---|---|---|---|
| **Trade Lab** | 3 | 3 | 2 | 3 | **11** | **Unambiguous island** |
| **Research Assistant** | 3 | 3 | 2 | 2 | **10** | **Unambiguous island** |
| **Player Detail drawer** (cross-cutting) | 1 | 3 | 3 | 2 | **9** | **Unambiguous island** |
| **⌘K command palette** (cross-cutting) | 0 | 2 | 2 | 3 | **7** | **Island candidate** |
| **League Opportunity Map** | 1 | 2 | 2 | 2 | **7** | **Island candidate** |
| **Open Decision Items** (cross-cutting) | 1 | 2 | 3 | 1 | **7** | **Island candidate** |
| **Roster Audit** | 0 | 2 | 2 | 2 | **6** | **Island candidate** (borderline; ~28 rows ⇒ RT soft) |
| **Rookie Board** | 0 | 2 | 1 | 2 | **5** | Stateful, sub-island (already vanilla-JS today) |
| Posture selector (cross-cutting) | 0 | 1 | 3 | 1 | 5 | Global writer, small UI |
| Trust Strip (cross-cutting) | 0 | 1 | 3 | 1 | 5 | Global reader, present everywhere |
| Market Divergence | 0 | 1 | 1 | 2 | 4 | Virtualized table, else static |
| Home / Command Center | 0 | 1 | 2 | 1 | 4 | Read-mostly widgets |
| Trust / Governance | 0 | 1 | 2 | 1 | 4 | Source of global state; surface is read-mostly |
| Settings | 0 | 1 | 3 | 0 | 4 | Global writer (posture/density); low interactivity |

**Result:** **3 unambiguous islands (Trade Lab, Research Assistant, Player Detail drawer) + 4 island candidates (⌘K, League Map, Open Decision Items, Roster Audit).** Critically, **three of the seven are cross-cutting** (drawer, ⌘K, Open Decision Items) — they overlay/coordinate across the whole app and cannot be walled into a single isolated island. The single-island assumption fails on the matrix alone, and it fails *robustly*: even under conservative scoring (drop Roster Audit and Rookie Board entirely), Trade Lab + Research + drawer + ⌘K remain, and two of those are cross-cutting.

---

## Section 3 — Alpine `$store` pseudocode (the load-bearing artifact)

The two highest-scoring non-Trade-Lab surfaces are **Research Assistant (10)** and **Player Detail drawer (9)**; the challenge also names **⌘K (7)**. I do Research Assistant and ⌘K as instructed (drawer is costed in Section 4).

### 3a. Research Assistant — branched query threads, parent-inherit/child-override, edit-parent-watch-child-drift

```js
Alpine.store('research', {
  // ---- state ----
  threads: {},        // id -> {id, parentId, label, overrides, status, result, chartSpec, childIds:[], dirty}
  rootIds: [],
  activeId: null,
  // query shape: {positions, ageRange, draftRound, season, metric, ...} ; DEFAULT_QUERY is the base

  // ---- DERIVED (no memoization in Alpine — recomputed every access) ----
  effectiveQuery(id) {                         // walk parent chain, layer overrides (child wins)
    const t = this.threads[id]; if (!t) return null
    const base = t.parentId ? this.effectiveQuery(t.parentId) : DEFAULT_QUERY   // O(depth) recursion
    return deepMerge(base, t.overrides)
  },
  isDrifted(id) {                              // result computed against an effectiveQuery that changed
    const t = this.threads[id]
    return t.result && t.result.queryHash !== hash(this.effectiveQuery(id))     // O(depth) per node
  },
  flatten() {                                  // tree -> depth-indexed list for x-for (Alpine can't recurse)
    const out = []
    const walk = (id, depth, collapsedAncestor) => {
      const t = this.threads[id]
      out.push({id, depth, collapsed: t.collapsed, hidden: collapsedAncestor})
      const hide = collapsedAncestor || t.collapsed
      t.childIds.forEach(c => walk(c, depth + 1, hide))
    }
    this.rootIds.forEach(r => walk(r, 0, false))
    return out                                  // recomputed on every render pass
  },

  // ---- mutations ----
  createRoot(q){ const id=uid(); this.threads[id]={id,parentId:null,label:'',overrides:q,status:'idle',result:null,chartSpec:null,childIds:[],collapsed:false,dirty:true}; this.rootIds.push(id); this.activeId=id; this.persist(); return id },
  branch(parentId,ov){ const id=uid(); this.threads[id]={id,parentId,label:'',overrides:ov,status:'idle',result:null,chartSpec:null,childIds:[],collapsed:false,dirty:true}; this.threads[parentId].childIds.push(id); this.activeId=id; this.persist(); return id },
  editQuery(id,patch){
    this.threads[id].overrides = deepMerge(this.threads[id].overrides, patch)
    this.threads[id].dirty = true
    this._markDescendantsDirty(id)             // every descendant whose effectiveQuery changed
    this.persist()
  },
  _markDescendantsDirty(id){ this.threads[id].childIds.forEach(c=>{ if(this.isDrifted(c)) this.threads[c].dirty=true; this._markDescendantsDirty(c) }) },
  async run(id){
    const t=this.threads[id]; t.status='running'; const eq=this.effectiveQuery(id)
    try { const r=await api.research(eq); t.result={...r, queryHash:hash(eq)}; t.chartSpec=r.chartSpec||null; t.dirty=false; t.status='done'; this._mountChart(id) }
    catch(e){ t.status='error'; t.error=e.message } finally { this.persist() }
  },
  setActive(id){ this.activeId=id },
  toggleCollapse(id){ this.threads[id].collapsed=!this.threads[id].collapsed },
  rename(id,l){ this.threads[id].label=l; this.persist() },
  remove(id){ /* detach from parent.childIds; reparent-or-orphan descendants; prune rootIds; destroy charts */ this.persist() },

  // ---- chart lifecycle (Observable Plot has NO framework cleanup; you manage it) ----
  _charts: {},                                  // id -> Plot node
  _mountChart(id){ const t=this.threads[id]; if(!t.chartSpec) return; this._destroyChart(id); const el=document.getElementById('chart-'+id); if(el){ const node=Plot.plot(t.chartSpec); el.replaceChildren(node); this._charts[id]=node } },
  _destroyChart(id){ const n=this._charts[id]; if(n){ n.remove(); delete this._charts[id] } },
  // ⚠ must call _mountChart/_destroyChart on collapse/expand, thread switch, drift-rerun, and remove —
  //   i.e. hand-rolled effect-cleanup that React's useEffect return does automatically.

  // ---- persistence ----
  persist(){ localStorage.setItem('dg.research', JSON.stringify({threads:this.threads, rootIds:this.rootIds})) },
  hydrate(){ const s=JSON.parse(localStorage.getItem('dg.research')||'null'); if(s){ this.threads=s.threads; this.rootIds=s.rootIds } },
})
```
Plus the template: a recursive thread tree. **Alpine has no native recursive component**, so you render `flatten()` (above) as a flat `x-for` with manual depth-indentation and manual collapse-hiding, OR hand-roll recursive `x-html` injection. Plus a query-builder form (controlled inputs for positions/age/round/metric), the result table renderer, and the drift-banner per node.

**Honest line count:** `$store` (~120) + `flatten`/recursion shim + indentation/collapse (~50) + chart lifecycle management (~40) + query-builder form state + result/table render + drift banners (~150) ≈ **~360–480 lines**, and it **reinvents three React primitives by hand**: recursive rendering (React: a 15-line recursive `<Thread>`), memoized derived state (`effectiveQuery`/`isDrifted` are recomputed O(depth) per node per render with no memo — React: `useMemo`), and effect-cleanup for chart mount/unmount (React: `useEffect` return).

> **VERDICT (3a):** Research Assistant **exceeds 300 lines AND reinvents React reconciliation/memoization/cleanup. It is a second unambiguous island.** Stated explicitly, as required.

### 3b. ⌘K command palette — fuzzy search over 600+ items, keyboard nav, recents-first, virtualized

```js
Alpine.store('cmdk', {
  open:false, query:'', activeIndex:0, scrollTop:0,
  recents:[],                                   // recent ids
  index:[],                                     // ~600 {id,type,label,keywords,route} built once at boot
  ROW:36, VISIBLE:14,

  get results(){
    const base = this.query ? fuzzyRank(this.index, this.query) : [...this._byIds(this.recents), ...this.index]
    return base.slice(0, 200)                   // cap
  },
  get windowStart(){ return Math.max(0, Math.floor(this.scrollTop/this.ROW) - 3) },
  get windowed(){ return this.results.slice(this.windowStart, this.windowStart + this.VISIBLE + 6) },
  get padTop(){ return this.windowStart * this.ROW },
  get padBottom(){ return Math.max(0, (this.results.length - this.windowStart - this.windowed.length) * this.ROW) },

  openPalette(){ this.open=true; this.query=''; this.activeIndex=0; this.scrollTop=0; this.$nextTick(()=>this._focus()) },
  close(){ this.open=false },
  move(d){
    this.activeIndex = clamp(this.activeIndex + d, 0, this.results.length - 1)
    this._scrollActiveIntoView()                // must keep activeIndex inside the rendered window
  },
  _scrollActiveIntoView(){
    const top = this.activeIndex * this.ROW, bot = top + this.ROW
    const viewTop = this.scrollTop, viewBot = this.scrollTop + this.VISIBLE*this.ROW
    if (top < viewTop) this.scrollTop = top
    else if (bot > viewBot) this.scrollTop = bot - this.VISIBLE*this.ROW
    // setting scrollTop must also imperatively set the list element's scrollTop (two-way sync)
    const el=document.getElementById('cmdk-list'); if(el) el.scrollTop=this.scrollTop
  },
  choose(){ const r=this.results[this.activeIndex]; if(!r) return; this.recents.unshift(r.id); navigate(r.route); this.close() },
  onScroll(e){ this.scrollTop = e.target.scrollTop },     // re-derives windowed slice
  onKey(e){ ({'ArrowDown':()=>this.move(1),'ArrowUp':()=>this.move(-1),'Enter':()=>this.choose(),'Escape':()=>this.close()}[e.key]||(()=>{}))() },
})
// fuzzyRank: subsequence match + score by gap/position/recency. ~80–120 lines done well, OR add Fuse.js (npm).
```
Plus template: an overlay, an input, a scroll container with `padTop`/`padBottom` spacer divs and an `x-for` over `windowed`, active-row highlight, type badges.

**Honest line count:** `$store` (~90) + `fuzzyRank` hand-rolled (~100) **or Fuse.js (npm dependency)** + virtualization window/scroll-sync + keyboard-into-view (~120) ≈ **~250–390 lines**. The virtualized-list-with-keyboard-pointer is exactly a **windowed reconciler kept in sync with an index pointer** — the thing React + a virtual-list lib expresses declaratively. And the "good" fuzzy path is **Fuse.js, which is npm** — puncturing Stack B's zero-dependency premise on a cross-cutting surface.

> **VERDICT (3b):** ⌘K is **borderline-to-over 300 lines AND either reinvents windowed reconciliation or pulls in npm anyway. It is a third island (and it breaks zero-build).** Stated explicitly.

---

## Section 4 — Cross-cutting Player Detail drawer

Requirements: opens from any row on ≥5 surfaces; URL-hash addressable; clicking a comparable inside re-targets the drawer **without** changing the underlying surface's selection; preserves underlying scroll/sort/filter.

**Stack B (HTMX/Alpine):**
- Store slice: `Alpine.store('drawer', { open, stack:[], get id(){return this.stack.at(-1)}, openTo(id){...}, push(id){...}, back(){...}, close(){} })`. **Underlying surface selection is NOT in this slice** — each surface keeps its own selection/scroll/filter in its own `x-data`; the drawer is a *global overlay* that reads `drawer.id`. This decoupling is the whole game.
- Hash wiring: a `hashchange` listener maps `#player/4881` → `drawer.openTo('4881')`; back button pops `stack`.
- **Discipline that must hold:** the drawer is an **Alpine overlay + a `fetch` for its content**, NEVER an `hx-get` that swaps the surface region. If you ever implement it as an HTMX swap of the surface, you clobber the surface's scroll/sort/filter — the exact failure mode to avoid. So `hx-preserve`/`hx-target` are essentially *not* the tool here; the correct Stack-B pattern is "Alpine overlay, leave the surface DOM untouched."
- Drawer internals are themselves stateful (comparable re-target, aging-curve Plot, model-route tabs) — i.e., the drawer *is* island #3 from Section 2.
- **Cost:** one global drawer component ≈ **80–140 lines** (store + hash + history + fetch + Plot lifecycle + comparable re-target) + **~1–5 lines per consuming surface** (`@click="$store.drawer.openTo(row.id)"`). The per-surface cost is low *if* discipline holds; the footgun (hx-swap clobbering) is real and repeats as a review hazard on every surface.

**Stack A (React):**
- `DrawerProvider` context holds `{stack, openTo, push, back}`; route `/player/:id` (or `?player=`) drives it via the router; underlying surface selection lives in each surface's own state/context — **naturally separate components, so no clobbering is possible**. `<PlayerDrawer>` owns its own history `useState`; comparable click = `push(id)` (local); aging curve in a `useEffect`-managed chart or a React chart lib.
- **Cost:** ≈ **80–120 lines** once + **~1 line per surface** (`onClick={() => openTo(id)}`).

**Honest comparison:** roughly a **wash on line count**, but Stack B requires *explicit, repeated discipline* (never hx-swap the surface; hand-manage hash/history/Plot-cleanup) where Stack A's component/context model makes the surface↔drawer separation structural and the clobbering failure mode impossible by construction. The drawer doesn't by itself sink Stack B — but it is a cross-cutting stateful component that adds a per-surface review hazard, and its internals are island-grade.

---

## Section 5 — 18-month end-state under Stack B (counted honestly)

Assuming the full surface list ships:
- **React islands (≥6 in §2):** Trade Lab, Research Assistant, Player Detail drawer, ⌘K, League Map, Open Decision Items, Roster Audit = **up to 7**; conservatively (drop the two borderline-6/7 you could force into Alpine) **≥4–5**, of which Trade Lab + Research are unambiguous and drawer + ⌘K are cross-cutting.
- **Cross-cutting React-coordinated patterns:** drawer, ⌘K, Open Decision Items, posture/Trust-strip global state = **~4**.
- **HTMX↔React DOM seams:** one per island mount + the drawer and ⌘K overlay *every* surface, so the seam is effectively **app-wide (~5–7 distinct, 2 of them everywhere)**.
- **Vite bundles:** with ≥4–5 islands + 2 cross-cutting overlays, you build **one shared React bundle mounted at many points** — i.e., a React app — not "a tiny island."
- **Hand-rolled Alpine/vanilla `$store` LoC:** Research (~400) + ⌘K (~300) + drawer (~120) + Roster (~150) + League (~150) + Open Decision Items (~100) + posture/trust (~80) + (Trade Lab if Alpine ~300) ≈ **~1,300–1,600 lines**, much of it reinventing React.

**Direct answer:** At the projected end state, **is Stack B meaningfully different from "Stack A with some Jinja templates for the static pages"? No — I admit it.** Once Trade Lab + Research + drawer + ⌘K (+ likely League Map) are React/heavy-state and the drawer + ⌘K overlay every surface, you have a React application whose only non-React parts are the genuinely static surfaces (Trust tables, Settings, Home widgets, Market Divergence table, the static shell of Roster/Rookie). **Where it remains different:** those static ~40% *can* stay server-rendered Jinja and that is genuinely simpler than React-ifying them — but you pay a two-model seam tax to keep them, and the seam runs straight through the cross-cutting drawer/⌘K that touch everything. The promised "one contained island, everything else simple HTML" is not the end state; "a React app plus Jinja for the static pages" is.

---

## Section 6 — Stack A's real costs (equal rigor)

**npm-maintenance burden (Vite + React + TS + TanStack Query + Tailwind v4 + Zod + shadcn-ish):**
- **2027:** ~8–16 hrs. Most likely forced rewrites: **Tailwind** (v3→v4 already changed the config model; further churn likely), **TanStack Query** (historically a major ~every 12–18 mo with cache-API changes), **React 18→19** semantics (Actions, `use()`).
- **2028:** ~12–24 hrs. A **React 19→20** and/or **Vite 6→7→8** bump plausibly forces a 1–2 day migration; Radix-under-shadcn bumps.
- **2029:** ~12–24 hrs cumulative. The compounding hazard is the **"come back after 6 months and `npm install` won't resolve"** problem (peer-dep conflicts, deprecated transitive deps) — directly in tension with David's documented multi-month-gap, personal-project usage and the constitution's longevity posture.
- **Most rot-prone:** TanStack Query > Tailwind > React majors. **Lower-risk:** Zod, Vite (usually smooth), shadcn (copy-paste, insulated).
- **Forced 2–3-day migration probability by 2029:** **moderate–high (~60–70%)** with the full 6–8-dep stack.
- **Solo-learning-dev / multi-month-gap tolerance:** this is Stack A's sharpest, most legitimate cost. "No build, so the build can't break while you were away" is a real, load-bearing advantage of the light path for *this* user.

**Stack B's equivalent (honest):**
- HTMX 2.x→3.x: **low** risk, small migrations (HTMX is deliberately stability-focused). Alpine: **low** churn, tiny API. Observable Plot: you manage lifecycle by hand (ongoing minor friction) + ~yearly minor API changes. Tailwind standalone: same Tailwind churn as A *if used* — **avoidable** by using plain CSS variables (drops the single highest-churn dep).
- **The sting:** the cumulative npm cost of **N islands** + Fuse.js for ⌘K means Stack B, at end-state, **reintroduces npm/Vite/React anyway** for the islands — so it pays *most of* Stack A's rot cost **plus** the two-model seam tax. Stack B's low-maintenance promise only holds if the islands stay few and tiny, which §2–§3 show they do not.

---

## Section 7 — Learning curve to ship the Rookie Board visual migration (Stage 3)

**Stack A — concepts David must learn first (counted):**
1. JSX 2. Components + props 3. `useState` 4. controlled vs uncontrolled inputs 5. `useEffect` + dependency arrays 6. Rules of Hooks 7. TanStack Query (`useQuery`, queryKey, cache, invalidation, staleTime) 8. Zod schema authoring 9. TypeScript (types, generics for the client, interfaces) 10. list keys / reconciliation 11. Suspense / error boundaries 12. Vite dev/build + how FastAPI serves the bundle 13. npm / package.json / lockfile 14. Observable Plot (or a React chart lib) in React via `useRef`+effect 15. synthetic events → **~13–15 concepts**, several being the exact ones that bite beginners (Hooks rules, `useEffect` deps, Query cache, TS generics).

**Stack B — concepts for the same surface (counted):**
1. Jinja2 (loops/conditionals/includes/macros) 2. HTMX core (~6 attributes: `hx-get/post/target/swap/trigger`) 3. Alpine (~8 directives: `x-data/on/show/for/model/...`) 4. Alpine `$store` 5. Tailwind utilities *or* plain CSS 6. Observable Plot (same as A) 7. FastAPI HTML partials vs JSON 8. basic JS → **~7–8 concepts**, smaller API surfaces, and **David is already operating here** — the current Rookie Board is vanilla JS doing exactly tab/filter/sort. The Stack-B migration is "formalize what's already there," a far shorter leap.

**Honest two-sided read:** Stack B is **~half the new concepts** for the *first/easy* surface and re-learns faster after a gap. **But** for the *hard* surfaces (§3), Stack B forces David to hand-roll recursion/memoization/virtualization/effect-cleanup in vanilla JS — arguably **harder to do well than learning React**, because he reinvents primitives without guardrails. So: Stack B is easier early and on the static majority; **harder, and more dangerous, exactly where the islands are.**

---

## Section 8 — Final recommendation

**RECOMMENDATION:** **Stack A** (Vite + React + TypeScript, served by FastAPI) — adopted with a **longevity-hardened minimal dependency budget** (load-bearing deps: React + Vite + TS + Zod; **defer** TanStack Query/Table and the full shadcn kit until a surface's complexity earns them; prefer **plain CSS variables over Tailwind** to drop the highest-churn dependency; pin versions and keep a working lockfile committed).

**PRIMARY BASIS:** The stateful surfaces are **not isolable** — Trade Lab, Research Assistant, the Player Detail drawer, and ⌘K are all island-grade, and the drawer + ⌘K + Open Decision Items are *cross-cutting overlays on every surface* — so Stack B's defining advantage ("one contained island, everything else simple server-rendered HTML") dissolves into "a React app plus Jinja for the static pages," at which point you've paid Stack B's two-model seam tax to build Stack A by hand (§2, §3, §5).

**KEY RISK:** Dependency rot for a solo learning developer who returns after multi-month gaps (~60–70% chance of a forced 2–3-day migration by 2029) — mitigated, not eliminated, by the minimal-dependency budget above; this is the genuine price of Stack A and David must accept it knowingly.

**FALSIFIABLE TRIGGER:** If, after Trade Lab (W5b) + Trust + Roster Audit + Rookie Board ship, David has **not committed within ~12 months to building the Research Assistant / generative-UI workspace, the ⌘K palette, or the League Opportunity Map** — i.e., the realistic end-state collapses to ~4 mostly-static surfaces with a single Trade Lab island — then the single-island assumption would have held, Stack B (HTMX-hybrid) would have been lighter and cheaper, and the Stack A dependency tax was unearned. The two surfaces that most decisively break the single-island assumption (Research Assistant / gen-UI and ⌘K) are precisely the *deferrable* ones; if they stay deferred forever, revisit and prefer the hybrid.

**DELTA FROM PRIOR VOTE:** **Moved — from Stack B (my prior "HTMX-hybrid, one React island" vote) to Stack A.** What moved it: my prior vote explicitly rested on the single-island assumption, and the analysis falsifies it. §2 yields **3 unambiguous islands + 4 candidates, three of them cross-cutting**; §3 shows the two named non-Trade-Lab surfaces **exceed/approach 300 lines and reinvent React's recursion, memoization, effect-cleanup, and windowed reconciliation** (and ⌘K likely needs npm regardless); §5's honest count is that end-state Stack B ≈ "Stack A with Jinja for the static pages" + a seam tax. This is independent convergence with Codex/Gemini's earlier Stack-A vote, but on a *stronger* basis than they gave (they cited Trade Lab statefulness + Zod + gen-UI generically; the load-bearing reason is the **cross-cutting non-isolability** demonstrated by the matrix and the pseudocode) — and with a longevity-hardening dependency mandate they did not specify. What did **not** change: Stack B's longevity/learning-curve advantages are **real and were not erased** (§6, §7); they are simply outweighed because the islands are cross-cutting rather than contained. If the falsifiable trigger fires, the verdict flips back.
