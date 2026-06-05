# Frontend Surface-2 Trade Lab — Design Spec

**Status: DRAFT (for cockpit dual-CLEAR)**
**Date:** 2026-06-05 · **Author:** Claude Code · **Type:** Design spec — the build contract for Phase-12 frontend Surface 2 (Trade Lab)

---

## 0. Scope & standing constraints

Surface 2 is the React realization of the deferred **Phase-23 "W5b"** two-panel Trade Lab (Model View / Market Snapshot). It is the **second** frontend surface and the **first stateful** one (David assembles a trade — the reason the stack chose React).

**Binding inputs (do not relitigate):**
- **Frontend design spec** `docs/superpowers/specs/2026-06-03-frontend-design-spec.md` (committed) — §2 the three structural contracts (Decision Evidence Card, **Two-Lane**, Experimental treatment); §3 the 13-point invariant backbone; §4 visual system (OKLCH tokens, **model = blue / market = amber**, **no verdict green/red**); §5 app shell + data contract (**FastAPI OpenAPI is the single source of truth**; Hey API codegen; frontend renders endpoint values only, never computes/invents); §6 build order (**Trade Lab = surface 2**); §7 governance-in-UI (banned-language CI linter; `decision_supported=false` universal + non-dismissible).
- **Surface-1** (shell + Trust strip + ⌘K + Hey/Zod codegen seam + banned-language CI) is COMPLETE + CI-green on `main` `c0e0abf`. Surface 2 mounts a new route inside the existing AppShell and reuses its tokens, Trust strip, and Experimental/`decision_supported` visual states.
- **Constitution & north-star:** market data is overlay-only and never a model input; `decision_supported=False` everywhere on this surface; no banned David-facing patterns (no `verdict`, side-totals-as-verdict, `confidence`/`tier`, `action` instructions); frontend HOLD was lifted 2026-06-03 (David-authorized phase-sequence exception) — this surface is read-only over FastAPI JSON.
- **Runtime-dep budget** stays React + ReactDOM + Zod (the four-dep stance); **no TanStack, no charting lib, no cmdk** in v1 — any new runtime dep needs its own ADR. `localStorage` only for state; no server-side UI-state store.

**This spec is planning only.** It authorizes no dependency install and no code. The build plan (`docs/superpowers/plans/`) and cockpit TDD follow after this spec is committed.

### 0.1 Locked product decisions (David, 2026-06-05)
1. **v1 scope** = full two-lane evaluator + a thin backend contract layer (typed routes + asset catalog endpoint) + the stateful React two-lane builder.
2. **Asset types** = rostered players + future **round-only** draft picks (2027–2029). **Rookies enter as rostered players, never a separate prospect class. Unrostered prospects are excluded** (they are free agents and cannot be traded in Sleeper).
3. **H1 degradation contract** = **coupled** (cockpit-unanimous; see §5). Missing model artifacts → both lanes unavailable. FantasyCalc stale/cold → market lane degrades alone.
4. **Asset endpoint** = `GET /api/trade/assets` in `trade.py` (cockpit-unanimous).

---

## 1. Architecture — two parts

Surface 2 = (A) a thin **backend contract layer** (Python; additive, read-only, `decision_supported=False`) + (B) the **Trade Lab React surface**. Both lanes' evaluation logic already exists and is cockpit-cleared (`reconciler.py`, `market_reconciler.py`, `evaluator.py`); we are adding **typing**, an **asset catalog**, and the **stateful UI** — no change to evaluation math, Engine A/B features, or the `decision_supported` lock.

```text
+------------------------------------------------------------------+
| React Trade Lab route (inside Surface-1 AppShell)                |
|  AssetSearch -> TradeSideBuilder x2 -> RunComparisonBar          |
|  -> ModelLanePanel (blue) | MarketLanePanel (amber)             |
|     + DivergenceStrip (neutral) + LaneDegradedState             |
+------------------------------------------------------------------+
| Generated Hey/Zod client (typed at the SDK boundary)            |
+------------------------------------------------------------------+
| FastAPI (read-only):                                            |
|  GET  /api/trade/assets            (NEW: catalog)               |
|  POST /api/trade/reconcile         (model lane; typed)          |
|  POST /api/trade/reconcile/market  (market lane; typed)         |
|  POST /api/trade/evaluate          (secondary; typed)           |
+------------------------------------------------------------------+
| Read-only artifacts: universe_pvo_latest.json,                 |
|  sleeper_universe_snapshot_latest.json, FantasyCalc cache,     |
|  draft_pick_valuation (Phase-24 value_pick)                    |
+------------------------------------------------------------------+
```

---

## 2. Backend contract layer (Part A)

### 2.1 Response + request typing (the codegen seam)
Today the trade routes return bare `dict`, so OpenAPI emits no schema and the Hey/Zod codegen types both responses **and** request bodies as `unknown` / `Array<{[key: string]: unknown}>` (verified in `frontend/src/lib/api/types.gen.ts`). A stateful builder constructs these requests, so the seam must be typed on **both** sides.

- **Type the responses** of `POST /api/trade/reconcile` (`TradeRosterReconciliation`), `POST /api/trade/reconcile/market` (`TradeMarketReconciliation`), and `POST /api/trade/evaluate` (`TradeEvaluation`) by declaring `response_model` (the Pydantic models already exist).
- **Type the request bodies** so the builder gets request-shape safety: `reconcile`/`evaluate` asset lists as `list[TradeAsset]`; `reconcile/market` asset lists as `list[MarketAssetRef]`.
- **Handler normalization is required, not just model declarations (D8 hardening).** The current handlers reconstruct assets via `TradeAsset(**a)` (`app/api/routes/trade.py:63-64`, `:72-73`) and `MarketAssetRef(**a)` (`trade_market.py`). Once the request body is typed, `a` is **already a model instance**, so `Model(**a)` breaks at runtime. The contract task MUST normalize the handlers (pass the typed assets through directly, or `a.model_dump()` before any reconstruction) and add focused route tests proving the typed request models still return 200. Typing without this handler change yields a green typecheck and a runtime error.
- **`POST /api/trade/analyze` is EXCLUDED** from this pass. It returns the legacy `analyze_trade_pvo` dict (`status`/`engine`/`reason`/`delta_status`/`uncertainty_note`, `app/services/trade_analyzer.py`), which matches **none** of the above models — declaring one would filter/validate the response and **500 at runtime**. `/analyze` stays untyped legacy; it is not used by Surface 2.
- **Behavior-change caveat (must verify):** declaring request models tightens input validation on cockpit-cleared routes. The contract task MUST run the full existing trade test suite and adjust only test fixtures (not evaluation logic) if any minimal-dict caller now 422s. Response-model declaration must not drop or rename any field the current callers rely on (FastAPI filters responses to the declared model).

### 2.2 Asset catalog endpoint — `GET /api/trade/assets`
A read-only catalog so the frontend **never invents asset or pick payloads**. Co-located in `trade.py` (picks are not players; keeps `players.py` clean).

**Request:** `GET /api/trade/assets?q=<substring>&limit=<int, default 50>`

**Hard input guards (fail-safe, not fail-loud):**
- **Minimum query length:** if `len(q.strip()) < 3`, return an **empty result list** (do not filter/serialize the ~12k-row universe). This prevents the empty/short-query OOM/CPU blowup.
- **Hard cap:** never return more than `limit` (default 50, capped at an absolute max e.g. 100) entries; results are deterministically ordered (e.g. by descending model xVAR then label).

**Source & filtering (read-only):**
- Players come from `universe_pvo_latest.json`, **filtered to `league_context.rostered == True`** — rostered players only; **unrostered prospects/free agents are never emitted** (they cannot be traded in Sleeper).
- Future picks come from `sleeper_universe_snapshot_latest.json` `future_picks` (rows owned by rosters; round-only, no bucket/slot), **after a hard shape gate (D-malformed fix):** a row is emitted only if `season` is numeric and in `{2027, 2028, 2029}`, `round` is numeric and in `{1, 2, 3}`, and `current_roster_id` / `original_roster_id` are numeric. The artifact contains at least one **non-tradeable summary row** with `season=null`/`round=null`/null roster ids (a deferred 2026-traded-pick caveat row); such rows are **excluded from `results`** (a naive emit would crash `value_pick(None, None)` or surface a non-tradeable caveat as a selectable asset). Their caveats may appear only at the response level, never as a selectable entry.
- The endpoint writes nothing (read-only contract test asserts the artifacts are byte-unchanged).

**Each entry is pre-shaped in BOTH payload forms:**
```text
TradeAssetCatalogEntry {
  asset_id: str           # stable id: sleeper_id (player) | synthesized quantity_id (pick)
  label: str              # "Ja'Marr Chase"  |  "2027 1st (via <orig owner>)"
  kind: "player" | "future_pick"
  position: str | None    # players only
  roster_owner_id: int | None
  roster_owner_name: str | None
  model_payload: TradeAsset       # see is_prospect + pick-pricing rules below
  market_ref: MarketAssetRef      # asset_kind + sleeper_id  |  year + round + quantity_id
  caveats: list[str]
  decision_supported: false       # coercion-locked
}
TradeAssetCatalogResponse {
  query: str
  source_timestamp: str | null    # snapshot captured_at (freshness disclosure)
  results: list[TradeAssetCatalogEntry]
  caveats: list[str]              # incl. "future_picks_from_snapshot_not_live_sleeper"
  decision_supported: false
}
```

**Three invariants the endpoint OWNS (each gets a dedicated contract test):**

1. **`is_prospect` is derived from roster status, not asset kind (H3 fix).** A **rostered** asset (including a rostered rookie scored by Engine A) is emitted with `model_payload.is_prospect = False` and `market_ref.asset_kind = "player"` so it **consumes a roster slot** in the forced-cut math. **Only future picks** carry `is_prospect = True` / non-roster-consuming. (Rationale: `market_reconciler._to_trade_asset()` sets `is_prospect = (asset_kind != "player")`, and `reconciler.py` treats `is_prospect=True` as non-roster-consuming; a rostered rookie mis-flagged would bypass the capacity/forced-cut penalty.)

2. **Future picks are priced, not artifact-verbatim (H2 fix).** Snapshot pick rows carry **no `xvar`**. An `xvar=None` model payload would be **silently excluded** from the model math (`evaluator.py` drops sub-/None-value assets). The endpoint therefore **prices each future pick via Phase-24 `draft_pick_valuation.value_pick()`** (round-only / generic-future) and attaches the caveats that function emits (`generic_future_pick_round_only`, `pick_value_historical_expected`, `pick_value_floored_at_replacement`, `pick_value_thin_sample`). "Verbatim" applies only to pick **identity/ownership**, never to the computed model value. Market-derived values never enter `model_payload` (leakage contract test). **Caveat provenance (D-caveat fix):** the **`slot-spread`** caveat is *not* a `value_pick()` output — it is emitted by the market lane's `resolve_pick_market_key()` (`market_reconciler.py`) and belongs to the `market_ref` / market overlay, not the model payload. The two caveat sources must not be conflated.

3. **`quantity_id` is backend-synthesized and unique (D3/D7).** Duplicate same-year/same-round picks are kept distinct via a deterministic `quantity_id = pick:{season}:r{round}:orig{original_roster_id}:owner{current_roster_id}`. Verified unique: each original owner has exactly one pick per season+round (0 collisions in the local snapshot artifact `captured_at` 2026-05-24 — 108 eligible picks, 108 unique ids — and structurally one-per-original-owner). The frontend selects these; it **never constructs `DP_`/`FP_` keys**.

---

## 3. Trade Lab React surface (Part B)

### 3.1 Components
- **`TradeLab`** — route container inside the AppShell. Owns trade state (`sent[]`, `received[]`, optional `counterpartyRosterId`), the run action, and `localStorage` persistence. No TanStack.
- **`AssetSearch`** — debounced input (min 3 chars) → `GET /api/trade/assets` → results dropdown → `onSelect` appends the chosen `TradeAssetCatalogEntry` to a side.
- **`TradeSideBuilder` ×2** ("David sends" / "David receives") — asset chips, remove; duplicate picks kept distinct by `asset_id`/`quantity_id` (never collapsed).
- **`RunComparisonBar`** — single "Run comparison" action; an **optional counterparty-roster selector** (default off = single-sided, matching the backend default), rendered with its honest three-state status (`not_requested` / `available` / `unavailable`).
- **`ModelLanePanel` (blue)** — renders `TradeRosterReconciliation`: per-side xVAR value, consolidation factor, parity-band state, the **forced-cut penalty** (with the cut players), caveats. Uncertainty treatment (range/band) per the §4 visual system.
- **`MarketLanePanel` (amber)** — renders `TradeMarketReconciliation`: per-side raw FantasyCalc sums, market cut cost, advisory **realism warnings**, coverage gaps, **source timestamp**, caveats.
- **`DivergenceStrip`** — see §3.3.
- **`LaneDegradedState`** — per-lane unavailable/stale treatment (see §5).
- **Reused from Surface-1:** AppShell, TrustStrip, OKLCH tokens (blue/amber, no verdict hues), the universal non-dismissible `decision_supported=false` / Experimental visual.

### 3.2 Lanes & data flow
1. `AssetSearch` (debounced, ≥3 chars) → catalog entries.
2. Selecting an entry appends it to `sent[]` or `received[]` (persisted to `localStorage`).
3. "Run comparison" fires **two parallel** requests, each validated at the Hey/Zod SDK boundary:
   - **Model lane → `POST /api/trade/reconcile`** with `{david_assets: sent.model_payload[], received_assets: received.model_payload[]}` (roster-aware; includes the forced-cut penalty — the richer "Model View").
   - **Market lane → `POST /api/trade/reconcile/market`** with `{sent_assets: sent.market_ref[], received_assets: received.market_ref[], current_draft_year, format_key, counterparty_roster_id?}`.
   - `POST /api/trade/evaluate` is typed for completeness but is **not** the primary call (it lacks roster context).
4. Each response renders into its **own physical panel** — never blended.

### 3.3 Divergence honesty — no client-computed trade-level number
The constitution forbids the frontend computing or blending values, and "no blended net delta" is the top governance trap. Therefore:
- `DivergenceStrip` shows the **two lane deltas as two separate facts**, side by side, **never merged/averaged/subtracted**: the model "model side difference" and the market "market side difference."
- It surfaces the backend's **per-asset** `MarketDivergenceContext.signal_label` (`model_higher_than_market` / `model_lower_than_market` / `inside_band` / `unavailable`) **verbatim**.
- It does **not** synthesize a trade-level "Model +14% vs Market" number — that would require a backend producer and is deliberately deferred (divergence is descriptive, not a validated edge).
- **`favors` / `adjusted_favors` are NOT rendered.** The reconciler returns directional labels (`"david"` / `"counterparty"`); rendering them is a binary verdict and is **banned**. The frontend ignores these fields entirely and renders only the adjusted value columns under uncertainty treatment. (The banned-language linter cannot catch a backend field *name*, so this is a spec rule enforced by a **frontend test** asserting those fields are never bound to output.)

---

## 4. Visual system
Reuse the Surface-1 OKLCH token system unchanged. **Model lane = blue track, Market lane = amber track**, physically separate. **No green/red verdict hues**; no status-colored glow/border/text to signal a "favored" side. Point estimates carry uncertainty treatment (range bar / shaded band). The forced-cut penalty and realism warnings render as neutral, caveated, advisory facts — never as instructions.

---

## 5. Error handling / honest degradation (the coupled contract)
The two lanes are **not** fully independent: `/api/trade/reconcile/market` loads the model artifacts as its first step (503 if missing) and runs `reconcile_trade_roster()` **before** any FantasyCalc fetch (`app/api/routes/trade_market.py`). The honest contract (cockpit-unanimous, Option (a)):

- **Missing model artifacts → BOTH lanes unavailable.** This is a coupled data dependency: the market route needs the model-native roster/cut artifacts to price the forced cuts. Returning an unadjusted market price here would itself be a **false-confidence violation** (a market delta that ignores roster-capacity constraints). The 503 is the honest fail-closed disclosure. The artifacts are local repo files (present), so this is a dev-environment edge case.
- **FantasyCalc stale/cold → market lane degrades ALONE.** `_fetch_fantasycalc_entries()` never raises; the market route returns **200 + caveats** (`source_timestamp_is_fetch_time_not_publish_time`, coverage gaps), and the **model lane is unaffected**. This is the real-world independent degradation.
- **Asset-search failure** → the search control shows an error; already-added assets and the run still work.
- `decision_supported=false` is universal and non-dismissible across the surface; a degraded lane renders in the Experimental/unavailable treatment and **never implies the surviving lane is decision-grade**.

---

## 6. Governance-in-UI (mechanical)
- **Banned-language CI linter** (existing TS-AST scanner, `frontend/src/shell/banned_vocabulary.json`) is extended to scan the new Trade Lab components; generated `src/lib/` output stays excluded.
- **`favors`/`adjusted_favors` non-render rule** enforced by a frontend test (see §3.3), since the linter cannot see a backend field name.
- **`decision_supported=false`** universal + non-dismissible.
- **Model/market separation** enforced by component structure (two panels), not copy.
- **Trust strip** continues to govern surface confidence globally.

---

## 7. Testing (cockpit TDD: Codex RED → Claude GREEN → dual-CLEAR)
**Backend (pytest contract tests):**
- `response_model` typing: OpenAPI emits typed schemas for `reconcile` / `reconcile/market` / `evaluate` (generated client no longer `unknown`); `/analyze` untouched; **typed request bodies still return 200 after handler normalization** (the `Model(**a)` regression); full existing trade suite stays green (fixtures adjusted only if request typing tightens validation).
- Asset endpoint: `len(q)<3` → empty; hard cap honored; rostered-only (no unrostered prospects); `is_prospect` roster-status coercion (rostered rookie = player; pick = prospect/non-roster); future picks priced via `value_pick()` (no `xvar=None`); **malformed/null-season pick rows excluded from `results`** (no `value_pick(None, None)` crash); `quantity_id` uniqueness on duplicate picks; market values absent from `model_payload`; read-only (artifacts byte-unchanged); `decision_supported=False`; freshness caveat present.

**Frontend (Vitest):**
- Builder add/remove/persist (`localStorage`); duplicate picks stay distinct.
- Run → two parallel calls with the correct request shapes.
- Two physically separate panels; **no blended net delta** anywhere; **`favors`/`adjusted_favors` never rendered**; neutral language only.
- Honest degradation: model-503 → both lanes unavailable; market-stale → market degrades alone, model unaffected; neither implies the other is decision-grade.
- `decision_supported` visual present + non-dismissible; picks 0-capacity and never trigger a forced cut.

**Governance / integration gates:** banned-language linter green on the new components; `tsc --noEmit` + Biome + Vitest green; **full Python suite green**; **run the S4 byte-audit as a gate** (`tests/contract/test_subsystem_4_audit.py`) — `trade.py` / `trade_market.py` / `main.py` / the new asset module are not S4 §11.1 inviolate paths, but confirm by running, do not assume.

---

## 8. Out of scope for v1 (deferred, named)
Early/mid/late pick **buckets** and exact current-year pick **slots** (the 2026 draft is complete; snapshot rows are round-only); **unrostered prospects**; a **backend-computed trade-level divergence** number; TanStack Query/Router; charting libraries; generative UI; a price-only market route (Option (c)); any change to Engine A/B features, evaluation math, or the `decision_supported` lock.

---

## 9. Resolved (cockpit, 2026-06-05 — Codex + Gemini concur after a pre-spec falsification round)
The /tmp design draft was adversarially pressure-tested; both agents returned evidence-cited defects. Resolutions, all folded above:
1. **H1 degradation** — Option (a) coupled (Gemini conceded its own Option (b) on a governance argument: an unadjusted market delta is a false-confidence violation). §5.
2. **Future-pick pricing** — `value_pick()`, not artifact-verbatim. §2.2(2).
3. **`is_prospect` coercion** from roster status. §2.2(1).
4. **OOM guard** — `len(q)>=3` + hard cap. §2.2.
5. **Unrostered-prospect filter**. §2.2.
6. **`favors`/`adjusted_favors` non-render** rule + frontend test. §3.3 / §6.
7. **`/analyze` excluded** from response_model typing (would 500). §2.1.
8. **Request bodies typed too**, with a validation-tightening verification gate. §2.1.
9. **`quantity_id`** backend-synthesized, verified unique. §2.2(3).
10. **Endpoint placement** — `GET /api/trade/assets` in `trade.py`. §2.2.
11. Gemini's snapshot duplicate-pick-collision concern was **verified away** (0 collisions in the local Sleeper snapshot artifact `captured_at` 2026-05-24; structurally one-pick-per-original-owner-per-season-round).

### 9.1 Second cockpit round (2026-06-05 — fresh-artifact CLEAR pass)
Codex returned 4 fresh defects against the consolidated spec; all folded in:
12. **Malformed future-pick row gate** — exclude `season=null`/non-numeric/out-of-range pick rows from `results` (a real null-summary row exists in the artifact; would crash `value_pick(None, None)`). §2.2 Source & filtering.
13. **Typed-request handler normalization** — typing the request body breaks `Model(**a)` reconstruction in the handlers; the contract task must normalize handlers + prove typed requests return 200. §2.1.
14. **`slot-spread` caveat provenance** — it comes from `resolve_pick_market_key()` (market lane), not `value_pick()`; do not conflate. §2.2(2).
15. **Freshness wording** — "live snapshot" → "local snapshot artifact (`captured_at`)". §9(11).

---

**Next after dual-CLEAR:** a build plan (`docs/superpowers/plans/2026-06-05-frontend-surface-2-trade-lab.md`) sequencing the backend contract layer → asset endpoint → stateful UI → governance/verification, then cockpit TDD. No dependency install or code until this spec is committed and the plan is cleared.
