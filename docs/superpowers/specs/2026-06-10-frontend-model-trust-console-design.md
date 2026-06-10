# Frontend Surface — Model Trust Console (v1) — Design Spec

- **Date:** 2026-06-10
- **Status:** v5 — holistic anti-overclaim fixes per full-spec review (MET/UNMET gate labels, TrustTruthPanel rename, `overall_grade` subordinate+qualified, `.pass` class ban); re-routing to cockpit
- **Review history:**
  - v1 REJECTED by Codex (4 verified findings: gitignored trust substrate, backtest↔model-card provenance mismatch, T3 not independently GREEN-able, false "R² low/negative" claim). v2 added Option A substrate-publication phase + fixed all four.
  - v2 REJECTED by Codex (4 verified internal contradictions: §2 "no artifact change" vs §3a publish/regenerate; T1 audit depended on T2's DTO → not independently GREEN-able; stale "latest-valid selection" language; missing-vs-stale model-card conflation). v3 resolves all four.
  - v3 REJECTED by Codex (1 residual: §10 stale "(T1)" provenance-audit ref contradicting the T1/T2 split). v4 corrects it.
  - v4 HOLISTIC REJECT (David-ordered full-spec pass): Codex — gate labels "Pass/Fail" contradict the recorded `MET`/`UNMET` decision; `TrustVerdictPanel` collides with §8 `.verdict` ban + "Truth Panel" name. Claude — `overall_grade` is a report-card overclaim vector (both agents missed it). v5 resolves all (gate labels → MET/UNMET/DEFERRED/INSUFFICIENT; `TrustTruthPanel` rename; `overall_grade` subordinate+qualified).
  - Substrate approach = Option A; tri-lane no-blocker (Codex independent; Gemini concurring — see §11).
- **Author:** Claude (impl), with tri-lane scoping (Codex technical/repo, Gemini governance/product)
- **Surface:** Phase 12 Frontend — Decision Surface formerly slotted "Backtest Harness"
- **Stack:** Vite + React + TS, FastAPI-served (Stack A); Hey/Zod generated client; Biome; Vitest/RTL
- **Predecessors:** Surface-1 (shell + TrustStrip), Surface-2 (Trade Lab), Surface-3 (Player Detail) — all shipped on `main`

---

## 0. Context & Purpose

Every shipped surface (Trade Lab, Player Detail) renders the model's numbers stamped
`Experimental` / `decision_supported=False`. Today that stamp is a black box: David sees
"Unvalidated" without *why* or *how much*. The **Model Trust Console** makes the trust basis
**legible**: per position (QB/RB/WR/TE), how much the model's valuations have earned trust,
where the model is weak, and why the decision surfaces remain `decision_supported=False`.

This is the constitutional **trust layer made visible** (`00-product-constitution.md`:
backtesting is a trust layer, not optional QA; no decision-grade confidence before validation
justifies it). It answers **"can I trust this model output for this position?"** — explicitly
**not** "what move should I make?"

### Honest ground truth this surface must convey (G3 run, recorded in `docs/validation/2026-05-31-step5b2-g3-ecr-validation.md`)
The model is **consensus-competitive but edge-UNPROVEN**: Engine B is statistically *tied*
with DynastyProcess ECR expert consensus; per-fold NDCG-diff at primary-k is tiny and **every
BCa CI includes 0**; only WR "passes" G3 at 3/4 by point estimate and even that is
statistically unconfirmed. The console's prime directive is to make this **unmissable** — it
exists to *prevent the other surfaces' numbers from being over-trusted*, not to celebrate them.

---

## 1. Scope

### Resolved design decisions (tri-lane unanimous, 2026-06-10)
- **D1 — Nav rename.** Rename the AppShell `SURFACES` slot **"Backtest Harness" → "Model
  Trust."** The label is the first contract David reads; "Backtest Harness" overclaims (implies
  a runner/operator surface) for a strictly read-only v1. Narrow label correction only:
  `AppShell` `SURFACES`, the Surface-1 nav test (`AppShell.test.jsx`), and the primary-surface
  label in `01-north-star-architecture.md`. **Not** a broader architecture or historical
  phase/spec-name rewrite.
- **D2 — Model-card typed.** Include model-card essentials in v1 via a new **curated typed
  `ModelCardResponse` DTO** (the current `/model-card` route returns `dict[str, Any]` →
  generated Zod is `record<string, unknown>`, which would recreate raw-shape leakage). The DTO
  carries v1 essentials only — **not** the full 9-section `ModelCard` internals.
- **D3 — Tracked, provenance-matched substrate (Option A).** The trust-surface endpoint today
  reads the **gitignored** `app/data/backtest/runs/` (`.gitignore:71`) — 0 artifacts tracked,
  so the route 404s in CI / a clean clone, and the latest backtest run and the tracked model
  card come from **different runs** (provenance-incoherent). v1's **first phase publishes a
  curated, provenance-matched substrate** to a tracked governed path before any frontend work
  (see §3a). Rejected: B (fixture-only — knowingly ships a CI-dead trust surface) and C
  (same as A but split into a separate project for no gain).

### In scope (v1)
1. Read-only **Model Trust** surface rendered in `<main>` when the (renamed) surface is active.
2. Position tabs **QB / RB / WR / TE** over `GET /api/trust-surface/{position}`.
3. **Truth Panel** — fixed G3 verdict + non-dismissible `decision_supported=False` +
   subordinate/qualified `overall_grade` (§4.1) + `experimental` status.
4. **Gate Matrix** — G1–G4 as neutral **`MET` / `UNMET` / `DEFERRED` / `INSUFFICIENT DATA`**
   labels (recorded governance decision; `MET` = point-estimate state, **not** decision support).
5. **Fold table** — compact per-fold metrics, point estimate **+ BCa CI + "(inc. 0)"** marker.
6. **Model-card essentials** — `intended_use` / `out_of_scope_uses` / `caveats` /
   `known_failure_modes` via the new typed DTO.
7. **QB reliability callout** — the model's weakest position, surfaced prominently for QB.
8. **Provenance footer** — `run_id` / `run_date` / `model_version` / `model_artifact_hash` /
   `git_sha` / `market_source_label` / snapshot dates.
9. **Curated frontend view-model** (anti-leakage; UI never binds the raw `BacktestResult`-superset shape).

### Deferred (v2+, explicitly NOT in v1)
- Running / re-running / selecting backtests; scheduler controls; market-archive uploads
  (this is a read-only console).
- Full 9-section model-card accordion (subgroup analysis, ethical considerations, metrics,
  features/coefficients, calibration sections).
- Calibration **charts**/curves; ECE visualizations.
- Divergence-ledger browser; subpopulation/axis exploration; Task-C emotional-market framing.
- Any player-level actionability, buy/sell/favors labels, roster recommendations, or
  surfacing divergence as trade advice.
- Cross-position comparison; trend-over-time.

---

## 2. Architecture

### Surface mounting
The renamed **"Model Trust"** entry in `AppShell.SURFACES` renders `<TrustConsole />` in
`<main>` when active (mirrors how `activeSurface === "Trade Lab"` renders `<TradeLab />`). No
router; no new nav mechanism.

### Component tree (all read-only, `frontend/src/trust/`)
```
TrustConsole.tsx            // surface root: position tabs, fetch, Zod-validate, map, render/degrade
 ├─ TrustTruthPanel.tsx     // fixed G3 verdict copy + non-dismissible decision_supported banner + qualified grade + experimental
 ├─ GateMatrix.tsx          // G1-G4 neutral status labels
 ├─ FoldTable.tsx           // per-fold compact table: estimate + BCa CI + "(inc. 0)"
 ├─ ModelCardEssentials.tsx // intended_use / out_of_scope_uses / caveats / known_failure_modes
 ├─ QbReliabilityCallout.tsx// QB-only model_reliability warning
 └─ ProvenanceFooter.tsx    // run_id / hashes / source / dates
trustViewModel.ts           // curated mapper: zod responses -> TrustConsoleViewModel (anti-leakage)
TrustConsole.css            // slate/neutral visual system (no green/red, no badge checkmarks)
```

### Backend (additive; substrate publication in §3a)
- **Substrate (§3a):** publish 4 provenance-matched `BacktestResult` + `manifest.json` to the
  tracked `trust_surface/latest/`; repoint the route to read the published path.
- `app/api/routes/trust_surface.py`: add `response_model=ModelCardResponse` to
  `GET /{position}/model-card`, serving the **published, provenance-aligned** model-card source
  (see §3 source order).
- `ModelCardResponse` Pydantic DTO (curated subset — see §3).
- **No change to `model_card.py` or any model/training code.** This phase *does* add tracked
  trust-substrate artifacts (the point of Option A); it does not touch the model or its training.

---

## 3. Backend: `ModelCardResponse` DTO (curated)

Maps from the existing `ModelCard` (`src/dynasty_genius/eval/model_card.py`) — verified fields
`intended_use: str`, `out_of_scope_uses: List[str]`, `caveats: List[str]`,
`known_failure_modes: List[str]`.

```python
class ModelCardResponse(BaseModel):
    position: Literal["QB", "RB", "WR", "TE"]
    backtest_run_id: str | None        # provenance of the card's source run
    generated_at: str | None
    is_experimental: bool              # for honest degradation
    intended_use: str
    out_of_scope_uses: list[str]
    caveats: list[str]
    known_failure_modes: list[str]
```

- **Excluded** (v1): metrics, features/coefficients, subgroups, calibration, ethical
  considerations — the full 9-section internals. Re-introducing any requires a separate
  spec-cleared decision.
**Source order (single source of truth).** `/model-card` serves the **published, provenance-
aligned** model-card produced in T2 — either (i) a curated `ModelCardResponse` artifact at
`trust_surface/latest/` (the fallback path), or (ii) the in-memory `ModelCard` for the position
**iff** its provenance equals the published `BacktestResult`. The T2 publication audit guarantees
this alignment, so a stale/mismatched card cannot reach runtime.

**Missing vs. stale (distinct states).**
- **Missing** card (`model_card_available=False` / no published card): the `/model-card` route
  degrades (404 or typed "unavailable" — pinned by test in T2) and the UI renders "Model card
  unavailable." Independent **runtime** degradation.
- **Stale/mismatched** published card (provenance ≠ published `BacktestResult`): **fails the T2
  publication audit** and blocks the frontend (build-time). Never a runtime state.

---

## 3a. Substrate publication (Option A — resolves findings 1 & 2)

The frontend is **blocked** until this phase is published and **green in CI**.

### Published path (tracked — no `.gitignore` change)
Only `app/data/backtest/runs/` (+ `phase16/19/20`) is ignored; `app/data/backtest/trust_surface/`
is **not**, so no `.gitignore` edit is needed (do not touch `.gitignore`). Publish, per position:
```
app/data/backtest/trust_surface/latest/backtest_result_{QB,RB,WR,TE}.json   # 4 curated, schema-valid BacktestResult
app/data/backtest/trust_surface/latest/manifest.json                        # provenance manifest (below)
```
Raw `runs/` stays ignored/local. **Do not** un-ignore or commit `runs/` wholesale.

### Provenance manifest (`manifest.json`)
Per position: `source_validation_note`, `run_id`, `run_date`, `git_sha`, `model_version`,
`model_artifact_hash`, `market_source` / `market_source_label`, `publication_timestamp`, and a
`decision_supported` descriptive flag (absent-or-false). These are **descriptive trust
provenance, not decision artifacts**; the UI renders them as provenance, never as grade trophies.

### Model-card provenance alignment
Each `ModelCardResponse` must be **provenance-aligned** to its published `BacktestResult` for the
same position. Preferred: regenerate model cards from the published runs (`generate_model_cards.py`).
**Fallback** (if regeneration is non-deterministic or depends on run-local side files): directly
publish a curated `ModelCardResponse` JSON artifact into `trust_surface/latest/` under the same
provenance contract — **never** mix stale tracked `model_cards/` with the new published runs.

### Route repoint
`trust_surface.py` reads the **published path** (`trust_surface/latest/`) by default; **keep the
monkeypatch seams** the existing tests use. (Raw-runs reading may remain as a local-only fallback
but must not be the CI/clean-clone path.)

### Publication audit (gate — must pass before any frontend task)
Split across the two substrate tasks so each is **independently GREEN-able** (the
`ModelCardResponse` DTO does not exist until T2):

**T1 audit — `BacktestResult` + manifest** (fail-loud):
1. All 4 positions present; `BacktestResult.load()` succeeds for each.
2. No market-derived model inputs; `decision_supported` absent/false and descriptive on each
   published `BacktestResult` + the manifest.
3. **Stat/diff guard:** the publication step emits a compact file-count/size diff so broad
   `runs/` contents cannot accidentally land in the tracked path.

**T2 audit — model-card provenance + DTO** (fail-loud; the DTO exists by now):
4. **Provenance equality** trust-surface ⟷ model-card on `position`, `run_id`/`backtest_run_id`,
   `model_version`, `model_artifact_hash` (and `git_sha` where present). Any mismatch → **fail
   loudly**; a stale/mismatched card never reaches runtime.
5. `ModelCardResponse` maps **curated fields only** — no full 9-section leakage; `decision_supported`
   absent/false on the model-card source.

---

## 4. Component specifications

All metric fields below are **verified against `src/dynasty_genius/eval/backtest_artifact.py`**
and the generated `zTrustSurfaceResponse`.

### 4.1 TrustTruthPanel
(Component named `TrustTruthPanel` — **no "verdict" in authored frontend identifiers/classes/tests**;
"G3 verdict" appears only as the prose name of the recorded validation finding.)
- **Fixed G3 verdict copy** — a single canonical, banned-language-safe constant whose wording is
  finalized in implementation from `docs/validation/2026-05-31-step5b2-g3-ecr-validation.md` (not
  free-typed per render). Draft: "Consensus-competitive, edge unproven. Engine B is statistically
  tied with DynastyProcess ECR expert consensus; per-fold NDCG-diff bootstrap confidence intervals
  include zero." **No global R² claim** in the fixed copy — the published artifacts' `r2_oos` is
  positive/small-sample, not "low/negative" (finding 4); R² is shown **per fold** in the fold
  table (§4.3) with its caveats, never asserted as a global statement.
- Non-dismissible `decision_supported=False` state (reuse the Surface-2/3 banner pattern).
- `overall_grade` is **subordinate to the verdict and explicitly qualified** — neutral text
  rendered *below* the verdict with a fixed qualifier ("internal model grade — not a market-edge
  or decision-support claim"), never a colored/graded badge and never the lede. If the actual
  grade vocabulary still reads as a success tier (confirm at T6), **demote it to the provenance
  footer** (§10).
- `experimental` true → "Experimental — not validated."

### 4.2 GateMatrix (`promotion_gate` → `GateResult`)
Renders the four verified gate fields as neutral **`MET` / `UNMET` / `DEFERRED` /
`INSUFFICIENT DATA`** text labels (low-chroma slate; no green/red, no checkmark glyphs):
| Gate | Field | Rendered states |
|---|---|---|
| G1 Rank correlation | `g1_rank_correlation_pass: bool` | MET / UNMET |
| G2 RMSE stability | `g2_rmse_stability_pass: bool` | MET / UNMET |
| G3 Market superiority | `g3_market_superiority_pass: True\|False\|"deferred"` | MET / UNMET / DEFERRED |
| G4 Divergence validity | `g4_divergence_validity_pass: True\|False\|"deferred"\|"insufficient_data"` | MET / UNMET / DEFERRED / INSUFFICIENT DATA |

`MET` is a **point-estimate gate state, not decision support** — never styled as
success/celebration. The CI-includes-zero semantics (§4.3) dominate interpretation even where a
gate reads `MET` (e.g. WR G3).

### 4.3 FoldTable (`folds[]` → `FoldResult`)
Compact table; **every CI rendered in the same weight/size next to its point estimate**, with a
neutral **"(inc. 0)"** marker when the interval contains zero. Verified columns:
- Fold identity (fold index / test season / sample sizes — exact `FoldResult` identity fields
  confirmed at implementation; the production-faithfulness test gates any mismatch).
- `kendall_tau` + `kendall_tau_bca_ci95`
- `spearman_rho` + `spearman_rho_bca_ci95` (a.k.a. `rank_ic`)
- `rmse`
- `r2_oos` (Optional) — if null, render the fixed-token `r2_oos` caveat (e.g. `r2_oos_unavailable`), not a fabricated value.
- `ndcg_diff_primary_k` (Optional) + `ndcg_diff_bca_ci95` (Optional)

### 4.4 ModelCardEssentials (`ModelCardResponse`)
Renders `intended_use` (paragraph), `out_of_scope_uses`, `caveats`, `known_failure_modes`
(lists), full text (no truncation). These are the surface's **safety instructions**. Missing
card → "Model card unavailable."

### 4.5 QbReliabilityCallout (`model_reliability`, QB only)
If `position === "QB"` and `model_reliability` present, render a prominent neutral callout with
the reliability figures (e.g. OOS R², Spearman) framed as **elevated uncertainty**, not a defect
badge. Other positions: omitted.

### 4.6 ProvenanceFooter
`run_id` / `run_date` (from the selected artifact), `model_version`, `model_artifact_hash`,
`git_sha`, `market_source_label`, `market_snapshot_dates` — small, copyable, neutral.

---

## 5. Data flow & curated view-model

1. `TrustConsole` holds `activePosition` (default QB). On mount/tab-change: fetch
   `GET /api/trust-surface/{position}` and `GET /api/trust-surface/{position}/model-card`.
2. Validate each at the Zod boundary (`zTrustSurfaceResponse`, new `zModelCardResponse`).
3. Map validated responses → **`TrustConsoleViewModel`** (curated; only the fields §4 needs).
   The UI components consume the view-model, **never** the raw response objects. This is the
   anti-leakage boundary: the broad `BacktestResult`-superset shape stops at `trustViewModel.ts`.
4. Render sections, or a degraded state (§6).

---

## 6. Degradation (honest, fail-safe)

- Trust-surface non-ok / invalid / throw → "Trust data unavailable" (TrustStrip pattern).
- `experimental=true` → "Experimental — not validated" framing across the panel.
- Gate `deferred` / `insufficient_data` → neutral `DEFERRED` / `INSUFFICIENT DATA`, **never** `MET`.
- `folds` empty / metric null → "not available" / fixed-token caveat; never fabricated.
- `divergence_validity` null → G4 reflects deferred/insufficient honestly.
- `model_card_available=false` or `/model-card` unavailable → "Model card unavailable."
- Each section degrades **independently** (a missing model-card never blanks the gate matrix).

---

## 7. Guardrails (constitutional)

- **Anti-overclaim is the prime directive.** No success styling; gates as neutral
  `MET`/`UNMET`/`DEFERRED`; CIs-include-zero dominate; the "edge unproven" verdict is the lede;
  `overall_grade` subordinate + qualified (§4.1).
- **No decision-grade language.** No buy/sell/favors/recommendation/start/sit/opportunity;
  `decision_supported=False` non-dismissible. The frontend banned-language linter is extended
  to `frontend/src/trust/`.
- **Neutral visual system.** Slate/low-chroma; **no green/red**, no badge/checkmark glyphs.
  Per two-lane discipline, model=blue / market=amber are **lane-identity only**, never
  positive/negative deltas.
- **Anti-leakage.** UI binds the curated view-model only; the typed `ModelCardResponse`
  replaces the untyped `record<string, unknown>`.
- **Published-substrate determinism.** `trust_surface.py` reads the **tracked published**
  `trust_surface/latest/` artifacts (not the gitignored `runs/`); the UI surfaces
  `run_id`/`run_date`/hashes (from the manifest) so provenance is visible, and tests pin the
  published selection so a future artifact change can't silently alter what David sees.
- **Provenance integrity.** Trust-surface and model-card must be the **same run** (publication
  audit, §3a); a mismatch **fails loudly**, never renders as one coherent record. Manifest fields
  are provenance, never grades/trophies.
- No Engine A/B feature/training/model change; no new market-derived inputs; read-only.

---

## 8. Testing strategy (cockpit TDD: Codex RED → Claude GREEN → dual-CLEAR)

- **Publication audit RED (split per §3a):** **T1 audit** (4 positions present, `load()` ok, no
  market-derived input, `decision_supported` absent/false, stat/diff guard) and **T2 audit**
  (provenance-equality trust-surface ⟷ model-card, curated-only DTO). Each fail-loud + independently GREEN-able.
- **Production-faithfulness RED (required):** for the typed `/model-card` endpoint **and** the
  console, one fixture-level test **+ one real-artifact smoke across QB/RB/WR/TE over the tracked
  published `trust_surface/latest/*` artifacts** (CI-real — not the gitignored `runs/`). This
  institutionalizes the Surface-3 lesson (T3a/T4/T6/T8 each hid a fixture-vs-reality gap).
- **OpenAPI drift + client regen:** `ModelCardResponse` lands in `openapi.json` + generated
  Zod; **assert the old `record<string, unknown>` shape is gone** from the `/model-card` route.
- **Anti-overclaim assertions:** no `.green`/`.red`/`.verdict`/`.pass`/success-colored classes
  on gates; no checkmark glyphs; gate labels are `MET`/`UNMET`/`DEFERRED`/`INSUFFICIENT DATA`;
  `overall_grade` rendered with its non-decision qualifier; CI "(inc. 0)" rendered where
  intervals contain zero; `decision_supported=false` present & non-dismissible; banned-language
  gate clean over `frontend/src/trust/`.
- **Degradation tests:** experimental, deferred/insufficient gates, null folds/R²/divergence,
  model-card-unavailable — each renders the honest state, no fabrication.
- **Determinism test:** **published-path** artifact selection pinned (`trust_surface/latest/`,
  not the gitignored-runs latest-by-`run_date`); provenance fields rendered.
- Backend: full Python suite green; **S4 byte-audit** unaffected (no inviolate path touched).

---

## 9. Build sequence (for the implementation plan)

**Substrate phase (T1–T3) gates the frontend — T4+ does not start until T1–T3 are green in CI.**

1. **T1 — Substrate publication (BacktestResult).** Publish 4 curated `BacktestResult` +
   `manifest.json` to `app/data/backtest/trust_surface/latest/`; repoint `trust_surface.py` to
   the published path (keep monkeypatch seams); the **T1 publication audit** (§3a: positions
   present / `load()` / `decision_supported` / stat-diff). (Backend/data; RED = the T1 audit.
   **No `.gitignore` change.** Independently GREEN-able — does **not** reference `ModelCardResponse`.)
2. **T2 — `ModelCardResponse` DTO + provenance-aligned model-card.** Publish the provenance-
   aligned model-card source (regenerate cards, or the curated-artifact fallback) **and** add
   `response_model=ModelCardResponse` on `GET /{position}/model-card`; the **T2 publication audit**
   (§3a: provenance-equality + curated-only). (The model-card provenance checks live here, after
   the DTO exists.)
3. **T3 — OpenAPI + client regen**; assert the old `record<string, unknown>` shape is gone for
   `/model-card`; **real-artifact smoke over the tracked published files green in CI** for all 4
   positions. (← frontend unblocks here.)
4. **T4 — Nav rename** "Backtest Harness" → "Model Trust" (`SURFACES` + `AppShell.test.jsx` +
   `01-north-star-architecture.md` label) **+ a minimal `<TrustConsole/>` placeholder** so the
   render wiring typechecks/builds independently (finding 3).
5. **T5 — `trustViewModel.ts`** curated mapper + Zod boundary + `TrustConsole` shell (tabs,
   fetch, degrade) + `TrustConsole.css` neutral visual system (slate; no green/red, no checkmark
   glyphs) — fills the placeholder.
6. **T6 — `TrustTruthPanel`** (fixed verdict copy + non-dismissible banner + subordinate/qualified
   grade + experimental; no "verdict" in authored identifiers).
7. **T7 — `GateMatrix`** (neutral G1–G4).
8. **T8 — `FoldTable`** (estimate + BCa CI + "(inc. 0)"; null R²/metric caveats).
9. **T9 — `ModelCardEssentials` + `QbReliabilityCallout` + `ProvenanceFooter`.**
10. **T10 — Verification/closeout** (full FE gates + Python suite + S4 byte-audit + ledger/AGENT_SYNC).

(Each task: Codex RED → Claude GREEN → dual-CLEAR → commit → zero-divergence audit. Frontend
tasks T4–T10 do not start until the T1–T3 substrate is CI-green.)

---

## 10. Open questions / risks

- **Model-card regeneration determinism** — if `generate_model_cards.py` is non-deterministic or
  pulls run-local side files, T2 uses the **curated `ModelCardResponse` artifact fallback** (§3a)
  under the same provenance contract. The **T2** publication audit fails loudly on any provenance
  mismatch rather than silently rendering.
- **Fold identity field names** — `FoldResult` identity columns (index/season/sample) confirmed
  at **T8** against the model; the production-faithfulness smoke gates any mismatch.
- **`/model-card` unavailable contract** — 404 vs typed "unavailable" body; pinned by test in **T2**.
- **Nav rename blast radius** — must stay a narrow label correction; the Surface-1 nav test is
  the canary (any broader breakage means the rename overreached).
- **`overall_grade` semantics** — v1 rule is **subordinate + qualified** (§4.1). At T6, confirm
  the actual grade vocabulary; if any value still reads as a success tier despite the qualifier,
  **demote it to the provenance footer** (not deferred — footer-demotion is the explicit fallback).

---

## 11. Review-process note (cockpit independence)

The substrate decision (Option A) and this v2 carry **Codex's independent technical falsification
+ Gemini concurring** — not two blind-independent passes. Gemini's review pane surfaces Codex's
responses, so on the scoping and substrate polls Gemini *consolidated* Codex's analysis rather
than reaching it independently. Recorded for honest weighting: treat the tri-lane "unanimity"
here as **one independent technical pass + a governance concurrence**, plus Claude's own
independent agreement on the merits. No bearing on correctness — every finding was verified
against repo state — but it is why this spec does not claim "two independent confirmations."
```
