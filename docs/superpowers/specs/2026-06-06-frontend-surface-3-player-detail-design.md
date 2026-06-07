# Frontend Surface-3 Player Detail — Design Spec

**Status: DRAFT (for cockpit dual-CLEAR)**
**Date:** 2026-06-06 · **Author:** Claude Code · **Type:** Design spec — the build contract for Phase-12 frontend Surface 3 (Player Detail)

---

## 0. Scope & standing constraints

Surface 3 is **Player Detail** — instant, explainable evidence for one player (model grade, xVAR/DVS, market overlay, top drivers, risk flags, caveats, a steel-manned counter-argument) to support David's roster-cut and trade decisions. It is the **Decision-Evidence-Card contract applied to a single player**, and the reusable inspector substrate later surfaces consume.

**Binding inputs (do not relitigate):**
- **Frontend design spec** `docs/superpowers/specs/2026-06-03-frontend-design-spec.md` — §2 the three structural contracts (Decision-Evidence-Card, **Two-Lane**, Experimental); §3 invariants; §4 visual system (OKLCH tokens, **model = blue / market = amber**, **no verdict hues**, constitutional age cliffs amber); §5 app shell (left-rail, sticky Trust strip, ⌘K, **right-side collapsible player inspector**); §7 governance-in-UI (banned-language CI linter; `decision_supported=false` universal + non-dismissible).
- **Surface 1** (shell + Trust strip + ⌘K + Hey/Zod codegen seam + banned-language CI) and **Surface 2** (Trade Lab — two-lane panels, neutral divergence, honest degradation, asset catalog) are COMPLETE + MERGED on `main` (`2019424`/`df4b63d`). Surface 3 reuses their primitives.
- Constitution: market data is overlay-only and never a model input; `decision_supported=False` everywhere; banned David-facing patterns (rookie `confidence`/`dynasty_tier`, trade `verdict`, roster `action`) stay banned.
- Runtime-dep budget unchanged (React + ReactDOM + Zod); no TanStack/charting/router lib in v1; `localStorage`/ephemeral client state only.

**This spec is planning only.** No dependency install, no code. The build plan + cockpit TDD follow after this spec is committed.

### 0.1 Locked decisions (David, 2026-06-06)
1. **Form = hybrid** — the right-rail inspector is a **neutral selector/preview**; the full Decision-Evidence-Card is a **page** view.
2. **Scope = (b) active + prospects** — full card only for **modeled** rows (`ENGINE_A` ~80, `ENGINE_B` ~373, `BLEND_AB`); the ~11,700 non-modeled rows (`PRE_MODEL`/`INACTIVE`/`MARKET_ONLY`/`UNRESOLVED_IDENTITY`) return a typed **degraded Experimental** response — never a raw sparse card.
3. **Evidence sourcing = Option A** — extend `universe_pvo_batch.py` to preserve the assembler's evidence fields, rebuild the artifact.
4. **Market source = A-1** — read the precomputed `universe_market_divergence_latest.json` (market overlay + divergence), with a freshness caveat. Live-FantasyCalc is deferred.

---

## 1. Architecture — two parts

Surface 3 = (A) a thin **backend evidence/endpoint layer** (Python; additive, read-only, `decision_supported=False`) + (B) the **Player Detail React surface** inside the existing AppShell.

```text
+------------------------------------------------------------------+
| AppShell (shell state: selectedSleeperId + inspector open/closed)|
|  PlayerInspector (rail: neutral preview)  --Open full detail-->  |
|  PlayerDetailPage (main: full Decision-Evidence-Card)            |
|    Header · ValuationTwoLane (model | market + divergence)       |
|    EvidenceSection (drivers · risk flags · caveats · counter-arg)|
+------------------------------------------------------------------+
| Generated Hey/Zod client (typed at the SDK boundary)            |
+------------------------------------------------------------------+
| FastAPI (read-only):  GET /api/players/{sleeper_id}  (NEW)      |
+------------------------------------------------------------------+
| Read-only artifacts:                                            |
|  universe_pvo_latest.json  (evidence — after Option A)          |
|  universe_market_divergence_latest.json  (market overlay + divg)|
+------------------------------------------------------------------+
```

---

## 2. Backend (Part A)

### 2.1 Option A — preserve the evidence fields
`pvo_assembler.assemble_pvo()` computes `counter_argument` (via `generate_counter_argument`), `risk_flags` (`_build_risk_flags`), `top_drivers`, and `caveats`, but `universe_pvo_batch.py` **drops them** during row serialization (verified: 0 occurrences of these keys in `universe_pvo_latest.json`).

- Extend the row-assembly loop in `universe_pvo_batch.py` to preserve **every DTO-backed source field the row currently drops** — the evidence fields `counter_argument`, `risk_flags`, `top_drivers`, `caveats` AND the identity/projection fields `draft_class`, `nfl_draft_pick`, `nfl_draft_round`, `projection_1y`, `projection_2y`, `projection_3y` (all verified `None` at row level in the current artifact (`universe_pvo_batch.py:88-100`, `:147-178`), but present on the source PVO — `PlayerValueObject.py:68-80`, filled at `pvo_assembler.py:484-502`). Then **rebuild** the artifact. (`roster_audit` signals optional.)
- **Additive-shape contract guard:** the change is ADD-only. Every existing reader (`trade.py`/`trade_market.py` `_load_reconcile_artifacts`, `asset_catalog.py`, `roster_cut_engine.py`) reads specific keys via `.get()`, so new keys are ignored. A contract test MUST assert the existing Trade Lab + asset-catalog suites stay green against the rebuilt artifact, and that the previously-read keys are byte-identical.

### 2.2 New endpoint — `GET /api/players/{sleeper_id}`
A read-only endpoint on the (empty, unmounted) `players.py`, mounted in `main.py`. Returns a **curated typed `PlayerDetailResponse`** — never the raw PVO row.

```text
PlayerDetailResponse {
  sleeper_id: str
  identity: { full_name, position, team, age, draft_class, nfl_draft_pick, nfl_draft_round }
  engine_path: Literal["ENGINE_A","ENGINE_B","BLEND_AB", ... ]   # echoed
  model_status: Literal["modeled","experimental","unavailable"]
  model: PlayerModelLane | null      # null when not modeled
  market: PlayerMarketLane | null    # null when market overlay absent (degrades independently)
  evidence: PlayerEvidence | null    # null/partial when fields absent (auto-Experimental)
  caveats: list[str]
  source_timestamps: { pvo: str|null, market: str|null }
  decision_supported: false          # coercion-locked
}
PlayerModelLane { engine_used, model_grade, model_version, dvs, xvar, xvar_percentile_position, projections }
PlayerMarketLane { source: "fantasycalc", market_value, market_rank_overall, market_rank_position, divergence: { signal_label: model_higher_than_market|model_lower_than_market|inside_band|unavailable, delta }, source_timestamp }
PlayerEvidence { top_drivers: list[str], risk_flags: list[str], counter_argument: str|null, completeness: { drivers, risk_flags, counter_argument, market } }
```

**Source → DTO mapping (the endpoint MUST map artifact names to the DTO, not pass raw):**
`market_rank_overall` ← `market_overlay.overall_rank`; `market_rank_position` ← `market_overlay.position_rank`; `divergence.delta` ← `divergence.model_minus_market_delta` (`universe_market_divergence.py:54-64`, `:210-218`). `nfl_draft_pick`/`nfl_draft_round`/`draft_class`/`projection_*` ← the same-named preserved PVO row fields (§2.1).

Behavior:
- **Modeled row** (`ENGINE_A`/`ENGINE_B`/`BLEND_AB`) → the **full card *shell*** with **per-section completeness/degradation** (NOT guaranteed-complete content): `model` populated; `evidence` populated per the `completeness` flags (a section absent in the data renders Experimental, never fabricated — see the coverage counts in §2.3/§8); `market` from A-1 or degraded (§3).
- **Non-modeled row** → `model_status="experimental"`/`"unavailable"`, `model=null`, `evidence=null`, neutral message surfaced client-side ("No predictive model score active for this player category"); `xvar` null/unranked.
- **Engine-A rows render only the available objective evidence** — the assembler's `top_drivers` **explanation strings** + the preserved `nfl_draft_pick`/`nfl_draft_round`/`draft_class` + `dvs`/`xvar`. There is **NO promised typed raw-feature block**: the batch carries `top_drivers` as strings + draft capital + position-specific provenance (e.g. TE fields at `universe_pvo_batch.py:172-175`); it does NOT carry a typed dominator/breakout/YPRR/target-share feature set. (Engine-A `risk_flags` are also effectively empty — see §2.3 counts.) The endpoint MUST NOT emit rookie `confidence`, `dynasty_tier`, or bucket-% — verified absent from the source *fields*.
- **Banned-term runtime guard (backend) — the field-name check is NOT sufficient.** The preserved evidence **text** is David-facing output, and a source probe found the assembler's `counter_argument` strings literally contain the banned tier word **"Elite"** in 2/80 Engine-A rows (`13269`, `13330`; `counter_arguments.py:30-40`) even though the `dynasty_tier` field is absent — and the frontend banned-language linter scans *source*, not backend data, so it cannot catch this. The endpoint therefore **scans every emitted evidence string** (`counter_argument`, `top_drivers`, `caveats`) against the banned rookie/verdict vocabulary (the `banned_vocabulary.json` terms); any string containing a banned term is **suppressed and that element degraded to Experimental** with an `evidence_suppressed_banned_term` caveat — never emitted. (A governed rewrite of the `counter_arguments.py` source text is a separate later task.) A contract test uses the known offending rows (`13269`/`13330`).
- `decision_supported` recursively coercion-locked False.

### 2.3 Market source (A-1) + a coverage audit
- The `market` lane reads `universe_market_divergence_latest.json` (it populates `market_overlay` + model-minus-market divergence; the PVO writes `market_overlay: null`), joined by **`sleeper_player_id`** (the PVO row key, `universe_pvo_batch.py:152`). The response carries the artifact's **source timestamp** + a `market_overlay_static_caveat` (price is batch-fresh, not live). Usable market delta exists on **62/80 Engine-A and 211/373 Engine-B** modeled rows; rows without it render the market track degraded (§3.2).
- **Coverage counts (measured at source — drive per-section degradation, not a promise of completeness):** after Option-A preservation — **Engine-A (80):** `counter_argument` 8/80, `risk_flags` 0/80, `top_drivers` 80/80, `caveats` 80/80; **Engine-B (373):** `counter_argument` 244/373, `risk_flags` 181/373, `top_drivers` 373/373, `caveats` 373/373. So **the "full card" is a shell**: prospect cards are mostly drivers + caveats + draft capital (counter-argument ~10%, risk-flags ~0%); active cards add a counter-argument ~65% / risk-flags ~49% of the time. Each absent element renders Experimental via the `completeness` flags; the endpoint **never fabricates text**.
- **Artifact loading:** both artifacts are large (~20 MB PVO + ~24 MB divergence); the endpoint loads them once and caches (module-level, like the Trade Lab `_load_reconcile_artifacts`), not per-request. (Caching mechanics are a plan detail.)

---

## 3. Frontend (Part B) — the hybrid

### 3.1 Components
- **`PlayerInspector`** (right rail) — the neutral **selector/preview**. Renders ONLY: identity (name/position/team/age/draft capital), `model_status` + market availability, and a **neutral presence indicator** — a plain count: `"3 caveats · counter-argument available"`. A primary **"Open full evidence card"** action. **Never** renders: a grade, edge, model-vs-market delta, recommendation, truncated counter-argument/caveat text, a subjective tier, or a warning glyph. It carries the universal `decision_supported=false` state ("Preview only — open full detail for evidence"). Missing evidence → "Evidence incomplete — open full detail," not compressed.
- **`PlayerDetailPage`** (main view) — fetches `GET /api/players/{sleeper_id}`, validates at the Zod boundary, renders the full card or the degraded Experimental state.
- **`PlayerDetailCard`** — header (name/age/team/position/draft class+pick) + the sections below.
- **`ValuationTwoLane`** — **model track** (blue: engine_used, model_grade, xVAR/DVS, position percentile, projections) | **market track** (amber: FantasyCalc value, overall/position rank, source timestamp + static caveat) — physically separate, never blended. A neutral **divergence** element (`model_higher_than_market` / `inside_band` / `unavailable`), **descriptive only** (divergence remains unvalidated — never a buy/sell verdict).
- **`EvidenceSection`** — top drivers, risk flags (objective; constitutional age-cliffs amber), caveats list, and the **full** steel-manned counter-argument (no truncation).
- **Shell state:** a single `selectedSleeperId` + inspector open/closed lives in AppShell state; any surface (the asset search, Trade Lab chips) may set it. v1 entry points: the asset-catalog search + (light) Trade Lab chip → inspect. No router/URL deep-linking in v1.
- **Reused from Surface 1/2:** AppShell, tokens, the universal non-dismissible `decision_supported=false` banner, the Experimental treatment, the asset-catalog search, the Zod-boundary fetch + degradation pattern.

### 3.2 Honest degradation
- **Non-modeled player** → the Experimental/unavailable treatment (both inspector + page), neutral message, no sparse card.
- **Per-element degradation:** a modeled player missing `counter_argument` (e.g. `generate_counter_argument` returns null for DVS≤80 with no risk flags) → that section shows an explicit "no counter-argument generated" Experimental state, not fabricated text. The `completeness` flags drive each section.
- **Market track degrades independently** (absent/stale `market_overlay`) without implying the model track is decision-grade.
- `decision_supported=false` universal + non-dismissible across the surface.

## 4. Visual system
Reuse the Surface-1/2 OKLCH tokens unchanged. **Model = blue, market = amber**, physically separate; **no green/red verdict hues**; constitutional age-cliff amber on the relevant risk flags. Uncertainty stays prominent; the counter-argument is a first-class, non-collapsed section. The inspector preview is deliberately sparse (identity + status + presence counts).

## 5. Governance
- **Engine-A objective-features-only** — no rookie `confidence`/`dynasty_tier`/bucket-% (banned), enforced at the endpoint (field absence **+ the backend banned-term scan of evidence *text*, §2.2** — closes the gap that the frontend linter, which scans source not backend data, cannot) and the UI (banned-language linter + a render guard).
- The **banned-language CI linter** (existing, walks `src/`) covers the new components.
- **Two-lane separation** by component structure; **neutral divergence** only; the inspector preview cannot imply a verdict by omission (presence counts only).
- Mandatory counter-argument + caveats (the Decision-Evidence-Card contract); `decision_supported=false` universal.

## 6. Testing (cockpit TDD: Codex RED → Claude GREEN → dual-CLEAR)
- **Backend:** Option-A additive preservation — **all DTO-backed fields present** (`counter_argument`/`risk_flags`/`top_drivers`/`caveats` AND `draft_class`/`nfl_draft_pick`/`nfl_draft_round`/`projection_1y-3y`, not just evidence); the prior-read PVO keys byte-identical; Trade Lab + asset-catalog suites green against the rebuilt artifact. Endpoint contract (modeled→full-shell `PlayerDetailResponse`; non-modeled→typed degraded; raw PVO shielded; Engine-A emits no banned *fields*; **Engine-A evidence TEXT carrying a banned term — rows `13269`/`13330` — is suppressed + degraded, not emitted**; market from A-1 with freshness caveat + source→DTO mapping; `decision_supported` recursively False; missing element→completeness-flag, no fabrication).
- **Frontend (Vitest):** inspector renders identity + status + presence counts ONLY (no grade/edge/delta/truncated-text/glyph/recommendation); full card renders the two physically-separate tracks + the full counter-argument + caveats; neutral divergence (no verdict); non-modeled→Experimental; market track degrades independently; per-element auto-Experimental on null counter-argument; `decision_supported` banner present + non-dismissible.
- **Gates:** `tsc`/Biome/Vitest/build; full Python suite; S4 byte-audit run as a gate (the new endpoint + batch change touch no S4 inviolate path — confirm, don't assume).

## 7. Out of scope (v1)
Live-FantasyCalc market source (deferred — A-2); deep-link/URL routing for the page; cross-surface "selected player" beyond the single shell `selectedSleeperId`; a separate Roster-Audit entry point (Roster Audit is a future surface); any analytical/model/feature change.

---

## 8. Resolved (cockpit, 2026-06-06 — pre-spec brainstorm input)
Surface selection + form/scope/sourcing were shaped via a David-driven brainstorm with cockpit input (Codex technical + Gemini governance), both source-verifying the artifacts. Resolutions, all locked above:
1. **Player Detail first** (lowest-risk, gate-free, foundational substrate) — three-way concur.
2. **Hybrid form**; inspector = neutral selector/preview (Codex: not a compact card; Gemini: presence-indicator) — David ruled **neutral presence indicator** (plain counts, no warning glyph).
3. **Scope (b)** active + prospects; modeled-only full card; non-modeled→degraded; Engine-A objective-only.
4. **Option A** evidence sourcing (additive, contract-checked) + **per-engine completeness audit**.
5. **Market = A-1** (divergence artifact + freshness caveat); live-FC deferred.
6. Verified: `counter_argument`/`risk_flags`/`top_drivers` absent from the PVO (Option A adds them); `market_overlay` null in PVO but populated in `universe_market_divergence_latest.json`.

### 8.1 Cockpit pressure-test round 1 (2026-06-06) — defects folded in
Codex + Gemini source-verified the spec; 8 findings (dedup ~5), all contract-precision/data-promise gaps (no blockers); all folded above:
- **Option A scope widened** — preserve `draft_class`/`nfl_draft_pick`/`nfl_draft_round`/`projection_1y-3y` too (not just evidence fields), or the DTO returns null (§2.1).
- **Naming** — `draft_capital`→`nfl_draft_pick`+`nfl_draft_round`; join key `sleeper_player_id`; market source→DTO mapping table (`market_overlay.overall_rank`/`position_rank`, `divergence.model_minus_market_delta`) (§2.2/§2.3).
- **Engine-A claim weakened** — available `top_drivers` strings + draft capital, NOT a typed raw-feature block (the batch lacks dominator/YPRR/target-share fields) (§2.2).
- **"Full card" reframed to a shell with per-section completeness/degradation** + the measured coverage counts recorded (§2.3): the evidence is honestly **thin, especially prospects** (Engine-A counter-argument 8/80, risk-flags 0/80). David ruled scope (b) stands — degradation handles it transparently; active players (the decision-bulk) are the better-covered cohort.
- **Verified by the cockpit:** additive-shape safe (all PVO readers `.get()`-only); Engine-A source carries no banned tier/confidence **fields**, but the evidence **text** can contain banned terms (the word "Elite" in rows `13269`/`13330`) — now closed by the §2.2 backend banned-term suppression guard; S4 byte-audit unaffected (`universe_pvo_batch.py` not byte-locked; `app/api/routes` outside the AST scan roots).

---

**Next after dual-CLEAR:** a build plan (`docs/superpowers/plans/2026-06-06-frontend-surface-3-player-detail.md`), then cockpit TDD on a branch cut from `df4b63d`. No dependency install, batch rebuild, or code until this spec is committed.
