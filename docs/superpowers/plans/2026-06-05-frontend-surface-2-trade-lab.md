# Frontend Surface-2 Trade Lab Implementation Plan

> **For agentic workers:** This project executes plans through the **tmux cockpit TDD loop** (Codex authors RED tests → Claude greens → dual-CLEAR → commit → loop-close), NOT the superpowers subagent model. Each task below gives the RED contract (the behaviors Codex's failing tests must assert) and the GREEN target (the implementation Claude writes). Steps use checkbox (`- [ ]`) syntax for tracking. This plan must itself be cockpit dual-CLEARED before T1.

**Goal:** Build the Phase-12 Surface-2 Trade Lab — a stateful React two-lane (Model View / Market Snapshot) trade evaluator over the existing cockpit-cleared trade backend, plus a thin backend contract layer (typed routes + asset catalog).

**Architecture:** Two parts. (A) A backend contract layer: declare typed request/response models on the trade routes (so the Hey/Zod codegen seam is real) and add a read-only `GET /api/trade/assets` catalog so the frontend never invents asset/pick payloads. (B) A React surface inside the existing Surface-1 AppShell: a stateful two-side builder → parallel calls to `/reconcile` (model) + `/reconcile/market` (market) → two physically separate panels + neutral divergence + coupled honest degradation. State is `fetch` + generated Zod client + `localStorage`; no TanStack.

**Tech Stack:** Python 3.14 / FastAPI / Pydantic (backend); React 19 + TypeScript (strict) + Zod 4 + Vite (frontend); Vitest + Testing Library + jsdom + Biome (frontend test/lint); pytest (backend). Generated client via `@hey-api/openapi-ts` (`npm run openapi-gen`).

**Spec:** `docs/superpowers/specs/2026-06-05-frontend-surface-2-trade-lab-design.md` (committed `a9cb190`, cockpit dual-CLEARED).

---

## Preflight (before T1)

- [ ] **Create the feature branch.** Code lands on a branch, not `main` (the spec/plan docs are already on `main`).

```bash
cd /Users/davidleess/dynasty-genius-product
git checkout -b feature/frontend-surface-2-trade-lab
```

- [ ] **Confirm baseline green** (so later regressions are attributable): `.venv/bin/python3.14 -m pytest tests/contract/test_phase15_trade_lab.py tests/contract/test_phase23_w2.py -q` and `cd frontend && npm run test && npm run typecheck`. Expected: all pass.

**Standing rules for every task:** no push to origin until a formal cockpit dual-CLEAR and David's go (in-flight TDD stays local); `decision_supported` stays False everywhere; no market-derived value enters any model payload; commit only the task's own files (the working tree has unrelated untracked docs — never `git add -A`).

---

## File structure

**Backend (new/modified):**
- Modify `app/api/routes/trade.py` — typed request models, `response_model` on 3 routes, handler normalization, the `GET /trade/assets` route.
- Create `src/dynasty_genius/trade_lab/asset_catalog.py` — pure catalog builder + `TradeAssetCatalogEntry` / `TradeAssetCatalogResponse` Pydantic models (keeps `trade.py` thin and the logic unit-testable).
- Test: `tests/contract/test_surface2_trade_typing.py` (T1), `tests/contract/test_surface2_asset_catalog.py` (T2).

**Frontend (new/modified):**
- Create `frontend/src/trade/tradeState.ts` — pure trade-state + `localStorage` helpers.
- Create `frontend/src/trade/AssetSearch.tsx`, `TradeSideBuilder.tsx`, `RunComparisonBar.tsx`, `ModelLanePanel.tsx`, `MarketLanePanel.tsx`, `DivergenceStrip.tsx`, `TradeLab.tsx` (+ `TradeLab.css`).
- Modify `frontend/src/shell/AppShell.tsx` — render `<TradeLab/>` in `<main>` when the active surface is "Trade Lab".
- Regenerate `frontend/src/lib/api/{types,zod}.gen.ts` via `npm run openapi-gen` after T1 and T2 (build artifacts, never hand-edited).
- Tests: `frontend/src/trade/*.test.jsx`.

---

## Task 1: Backend — typed request/response models + handler normalization

**Files:**
- Modify: `app/api/routes/trade.py:22-75`
- Test: `tests/contract/test_surface2_trade_typing.py`

RED contract (Codex authors): the trade routes carry typed request + response schemas in OpenAPI; `/analyze` is left untyped; typed requests still return 200 after handler normalization.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/contract/test_surface2_trade_typing.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_reconcile_declares_typed_response_schema():
    schema = app.openapi()
    resp = schema["paths"]["/api/trade/reconcile"]["post"]["responses"]["200"]
    ref = resp["content"]["application/json"]["schema"].get("$ref", "")
    assert ref.endswith("/TradeRosterReconciliation")

def test_market_declares_typed_response_schema():
    schema = app.openapi()
    resp = schema["paths"]["/api/trade/reconcile/market"]["post"]["responses"]["200"]
    ref = resp["content"]["application/json"]["schema"].get("$ref", "")
    assert ref.endswith("/TradeMarketReconciliation")

def test_evaluate_declares_typed_response_schema():
    schema = app.openapi()
    resp = schema["paths"]["/api/trade/evaluate"]["post"]["responses"]["200"]
    ref = resp["content"]["application/json"]["schema"].get("$ref", "")
    assert ref.endswith("/TradeEvaluation")

def test_analyze_is_not_typed_with_a_trade_model():
    # /analyze stays legacy dict — declaring a model would 500 at runtime.
    schema = app.openapi()
    resp = schema["paths"]["/api/trade/analyze"]["post"]["responses"]["200"]
    ref = resp["content"]["application/json"]["schema"].get("$ref", "")
    assert not ref.endswith(("/TradeEvaluation", "/TradeRosterReconciliation",
                             "/TradeMarketReconciliation"))

def test_evaluate_typed_request_still_returns_200():
    # Handler normalization: request body typed as list[TradeAsset]; no Model(**a) regression.
    body = {
        "side_a": [{"player_id": "1", "xvar": 10.0, "position": "WR"}],
        "side_b": [{"player_id": "2", "xvar": 9.5, "position": "RB"}],
    }
    r = client.post("/api/trade/evaluate", json=body)
    assert r.status_code == 200
    assert r.json()["decision_supported"] is False

def test_evaluate_request_items_ref_trade_asset():
    # Prove REQUEST typing, not just response typing — a 200 alone passes with loose dicts.
    schema = app.openapi()
    props = schema["components"]["schemas"]["TradeEvaluateRequest"]["properties"]
    assert props["side_a"]["items"]["$ref"].endswith("/TradeAsset")
    rprops = schema["components"]["schemas"]["TradeReconcileRequest"]["properties"]
    assert rprops["david_assets"]["items"]["$ref"].endswith("/TradeAsset")

def test_market_request_items_ref_market_asset_ref():
    schema = app.openapi()
    props = schema["components"]["schemas"]["MarketReconcileRequest"]["properties"]
    assert props["sent_assets"]["items"]["$ref"].endswith("/MarketAssetRef")
```

- [ ] **Step 2: Run to verify failure.** Run: `.venv/bin/python3.14 -m pytest tests/contract/test_surface2_trade_typing.py -v` — Expected: FAIL (response schemas are generic objects; no `$ref`).

- [ ] **Step 3: Implement — type the models + normalize handlers.** In `app/api/routes/trade.py`, change the request models to carry typed asset lists, add `response_model` to the 3 routes, and pass typed assets through (no `TradeAsset(**a)`):

```python
from src.dynasty_genius.trade_lab.evaluator import TradeAsset, TradeEvaluation, evaluate_trade
from src.dynasty_genius.trade_lab.reconciler import TradeRosterReconciliation, reconcile_trade_roster
from src.dynasty_genius.trade_lab.market_reconciler import MarketAssetRef  # used by trade_market typing (Task ref)

class TradeEvaluateRequest(BaseModel):
    side_a: list[TradeAsset]
    side_b: list[TradeAsset]

class TradeReconcileRequest(BaseModel):
    david_assets: list[TradeAsset]
    received_assets: list[TradeAsset]

@router.post("/reconcile", response_model=TradeRosterReconciliation)
def reconcile_trade_endpoint(request: TradeReconcileRequest) -> TradeRosterReconciliation:
    universe_pvo, sleeper_snapshot = _load_reconcile_artifacts()
    return reconcile_trade_roster(
        list(request.david_assets), list(request.received_assets),
        universe_pvo, sleeper_snapshot,
    )

@router.post("/evaluate", response_model=TradeEvaluation)
def evaluate_trade_endpoint(request: TradeEvaluateRequest) -> TradeEvaluation:
    return evaluate_trade(list(request.side_a), list(request.side_b))
```

In `app/api/routes/trade_market.py`: add the import `from src.dynasty_genius.trade_lab.market_reconciler import MarketAssetRef, TradeMarketReconciliation` (the file already imports `MarketAssetRef`; add `TradeMarketReconciliation`); set `MarketReconcileRequest.sent_assets`/`received_assets` to `list[MarketAssetRef]`; add `response_model=TradeMarketReconciliation`; and replace `[MarketAssetRef(**a) for a in request.sent_assets]` with `list(request.sent_assets)` (same for received). `/analyze` is left exactly as-is.

- [ ] **Step 4: Run to verify pass + no regression.** Run: `.venv/bin/python3.14 -m pytest tests/contract/test_surface2_trade_typing.py tests/contract/test_phase15_trade_lab.py tests/contract/test_phase23_w*.py tests/contract/test_trade_delta_status.py -v` — Expected: PASS. (These are the trade-route contract files that exist; the `test_phase23_w*` glob covers W1–W5.) If any prior test posted a minimal dict missing a now-required `TradeAsset`/`MarketAssetRef` field, fix the **test fixture** (not evaluation logic) to send a valid asset.

- [ ] **Step 5: Commit.**

```bash
git add app/api/routes/trade.py app/api/routes/trade_market.py tests/contract/test_surface2_trade_typing.py
git commit -m "feat(api): type trade route request/response models for the codegen seam

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Backend — asset catalog (`GET /api/trade/assets`)

**Files:**
- Create: `src/dynasty_genius/trade_lab/asset_catalog.py`
- Modify: `app/api/routes/trade.py` (add the route)
- Test: `tests/contract/test_surface2_asset_catalog.py`

RED contract: a pure `build_asset_catalog(...)` that filters rostered players + valid future picks, OOM-guards short queries, coerces `is_prospect` from roster status, prices picks via `value_pick()`, synthesizes unique `quantity_id`, excludes malformed pick rows and unrostered prospects, and never leaks market values into the model payload.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/contract/test_surface2_asset_catalog.py
from src.dynasty_genius.trade_lab.asset_catalog import build_asset_catalog
from src.dynasty_genius.trade_lab.draft_pick_valuation import load_curve
from src.dynasty_genius.trade_lab.evaluator import _PICK_CURVE_PATH

CURVE = load_curve(_PICK_CURVE_PATH)

def _pvo():
    # Real PVO shape: name/position nest under "player", xvar under "valuation";
    # sleeper_player_id + dvs_engine are top-level; roster info under "league_context".
    return {"players": [
        {"sleeper_player_id": "100", "dvs_engine": "B",
         "player": {"full_name": "Rostered Vet", "position": "WR"},
         "valuation": {"xvar": 22.5},
         "league_context": {"rostered": True, "roster_id": 1, "owner_display_name": "Woodbury Riders"}},
        {"sleeper_player_id": "200", "dvs_engine": "A",
         "player": {"full_name": "Rostered Rookie", "position": "RB"},
         "valuation": {"xvar": 14.0},
         "league_context": {"rostered": True, "roster_id": 4, "owner_display_name": "Free Kelly"}},
        {"sleeper_player_id": "300", "dvs_engine": "B",
         "player": {"full_name": "Free Agent", "position": "TE"},
         "valuation": {"xvar": 5.0},
         "league_context": {"rostered": False}},
    ]}

def _snapshot():
    return {"captured_at": "2026-05-24T17:19:44Z", "future_picks": [
        {"season": 2027, "round": 1, "current_roster_id": 1, "original_roster_id": 5},
        {"season": 2027, "round": 1, "current_roster_id": 1, "original_roster_id": 8},
        {"season": None, "round": None, "current_roster_id": None, "original_roster_id": None},
    ]}

def test_short_query_returns_empty_no_serialization():
    out = build_asset_catalog("ab", _pvo(), _snapshot(), CURVE, limit=50)
    assert out.results == []

def test_unrostered_player_excluded():
    out = build_asset_catalog("free", _pvo(), _snapshot(), CURVE, limit=50)
    assert all(e.label != "Free Agent" for e in out.results)

def test_rostered_rookie_is_player_not_prospect():
    out = build_asset_catalog("rookie", _pvo(), _snapshot(), CURVE, limit=50)
    e = next(e for e in out.results if e.label == "Rostered Rookie")
    assert e.model_payload.is_prospect is False
    assert e.market_ref.asset_kind == "player"

def test_future_pick_priced_and_prospect():
    out = build_asset_catalog("2027", _pvo(), _snapshot(), CURVE, limit=50)
    picks = [e for e in out.results if e.kind == "future_pick"]
    assert len(picks) == 2  # malformed null row excluded
    assert all(p.model_payload.xvar is not None for p in picks)        # priced, not None
    assert all(p.model_payload.is_prospect is True for p in picks)     # non-roster-consuming
    qids = {p.market_ref.quantity_id for p in picks}
    assert len(qids) == 2                                             # unique

def test_malformed_pick_row_excluded():
    out = build_asset_catalog("2027", _pvo(), _snapshot(), CURVE, limit=50)
    assert all(e.asset_id != "pick:None:rNone:origNone:ownerNone" for e in out.results)

def test_no_market_value_in_model_payload():
    out = build_asset_catalog("rostered", _pvo(), _snapshot(), CURVE, limit=50)
    for e in out.results:
        assert not any("market" in str(k).lower() for k in e.model_payload.model_dump())
    assert out.decision_supported is False

def test_entry_carries_roster_owner_name():
    out = build_asset_catalog("vet", _pvo(), _snapshot(), CURVE, limit=50)
    e = next(e for e in out.results if e.label == "Rostered Vet")
    assert e.roster_owner_name == "Woodbury Riders"

def test_limit_clamped_for_negative_and_large_values():
    assert build_asset_catalog("ros", _pvo(), _snapshot(), CURVE, limit=-1).results == []
    big = build_asset_catalog("ros", _pvo(), _snapshot(), CURVE, limit=500)
    assert len(big.results) <= 100
```

- [ ] **Step 2: Run to verify failure.** Run: `.venv/bin/python3.14 -m pytest tests/contract/test_surface2_asset_catalog.py -v` — Expected: FAIL (`ModuleNotFoundError: asset_catalog`).

- [ ] **Step 3: Implement the pure module.** `src/dynasty_genius/trade_lab/asset_catalog.py`:

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, field_validator
from src.dynasty_genius.trade_lab.evaluator import TradeAsset
from src.dynasty_genius.trade_lab.market_reconciler import MarketAssetRef
from src.dynasty_genius.trade_lab.draft_pick_valuation import value_pick

_MIN_Q = 3
_VALID_SEASONS = {2027, 2028, 2029}
_VALID_ROUNDS = {1, 2, 3}

class TradeAssetCatalogEntry(BaseModel):
    asset_id: str
    label: str
    kind: Literal["player", "future_pick"]
    position: str | None = None
    roster_owner_id: int | None = None
    roster_owner_name: str | None = None
    model_payload: TradeAsset
    market_ref: MarketAssetRef
    caveats: list[str] = []
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock(cls, _v: object) -> bool:
        return False

class TradeAssetCatalogResponse(BaseModel):
    query: str
    source_timestamp: str | None = None
    results: list[TradeAssetCatalogEntry] = []
    caveats: list[str] = []
    decision_supported: bool = False

    @field_validator("decision_supported", mode="before")
    @classmethod
    def _lock(cls, _v: object) -> bool:
        return False

def _is_num(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def build_asset_catalog(query, universe_pvo, sleeper_snapshot, pick_curve, *, limit=50):
    q = (query or "").strip()
    resp = TradeAssetCatalogResponse(
        query=q, source_timestamp=sleeper_snapshot.get("captured_at"),
        caveats=["future_picks_from_snapshot_not_live_sleeper"],
    )
    if len(q) < _MIN_Q:
        return resp
    ql, entries = q.lower(), []

    for p in universe_pvo.get("players", []):
        lc = p.get("league_context", {})
        if not lc.get("rostered"):
            continue                                   # unrostered excluded
        player = p.get("player", {})                   # real PVO nests name/position here
        name = player.get("full_name", "")
        if ql not in name.lower():
            continue
        sid = str(p["sleeper_player_id"])
        position = player.get("position")
        entries.append(TradeAssetCatalogEntry(
            asset_id=sid, label=name, kind="player", position=position,
            roster_owner_id=lc.get("roster_id"),
            roster_owner_name=lc.get("owner_display_name"),
            model_payload=TradeAsset(player_id=sid,
                                     xvar=p.get("valuation", {}).get("xvar"),  # nested
                                     position=position or "", is_prospect=False,
                                     dvs_engine=p.get("dvs_engine")),
            market_ref=MarketAssetRef(asset_kind="player", sleeper_id=sid, player_id=sid),
        ))

    for pk in sleeper_snapshot.get("future_picks", []):
        s, r = pk.get("season"), pk.get("round")
        if not (_is_num(s) and int(s) in _VALID_SEASONS
                and _is_num(r) and int(r) in _VALID_ROUNDS
                and _is_num(pk.get("current_roster_id"))
                and _is_num(pk.get("original_roster_id"))):
            continue                                   # malformed row excluded
        s, r = int(s), int(r)
        owner, orig = int(pk["current_roster_id"]), int(pk["original_roster_id"])
        label = f"{s} round {r} (via {orig})"
        if ql not in label.lower() and ql != str(s):
            continue
        qid = f"pick:{s}:r{r}:orig{orig}:owner{owner}"
        priced = value_pick(year=s, round_=r, curve=pick_curve)  # returns a PickValue model
        xvar, pick_caveats = priced.xvar, priced.caveats        # NOT a tuple — use fields
        entries.append(TradeAssetCatalogEntry(
            asset_id=qid, label=label, kind="future_pick", roster_owner_id=owner,
            model_payload=TradeAsset(player_id=qid, xvar=xvar, position="PICK",
                                     is_prospect=True),
            market_ref=MarketAssetRef(asset_kind="future_pick", year=s, round=r,
                                      quantity_id=qid),
            caveats=list(pick_caveats),
        ))

    entries.sort(key=lambda e: (-(e.model_payload.xvar or 0.0), e.label))
    safe_limit = max(0, min(int(limit), 100))          # clamp both bounds (negative + OOM)
    resp.results = entries[:safe_limit]
    return resp
```

> **Verified at source (cockpit round-1):** `value_pick()` returns a `PickValue` model (`draft_pick_valuation.py:197`) with `.xvar`/`.caveats` — not a tuple. PVO rows nest `player.full_name`/`player.position` and `valuation.xvar`; `sleeper_player_id` + `dvs_engine` are top-level; `league_context` carries `rostered`/`roster_id`/`owner_display_name`. The snippet above reflects these.

- [ ] **Step 4: Add the route to `trade.py`.**

```python
from src.dynasty_genius.trade_lab.asset_catalog import TradeAssetCatalogResponse, build_asset_catalog
from src.dynasty_genius.trade_lab.draft_pick_valuation import load_curve
from src.dynasty_genius.trade_lab.evaluator import _PICK_CURVE_PATH  # canonical curve path constant

@router.get("/assets", response_model=TradeAssetCatalogResponse)
def trade_assets(q: str = "", limit: int = 50) -> TradeAssetCatalogResponse:
    universe_pvo, sleeper_snapshot = _load_reconcile_artifacts()
    # limit is clamped inside build_asset_catalog (max(0, min(limit, 100))).
    return build_asset_catalog(q, universe_pvo, sleeper_snapshot,
                               load_curve(_PICK_CURVE_PATH), limit=limit)
```

- [ ] **Step 5: Run to verify pass.** Run: `.venv/bin/python3.14 -m pytest tests/contract/test_surface2_asset_catalog.py -v` — Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add src/dynasty_genius/trade_lab/asset_catalog.py app/api/routes/trade.py tests/contract/test_surface2_asset_catalog.py
git commit -m "feat(api): read-only trade asset catalog endpoint (GET /api/trade/assets)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Frontend — regenerate client, mount TradeLab, trade state + AssetSearch

**Files:**
- Regenerate: `frontend/src/lib/api/{types,zod}.gen.ts`
- Create: `frontend/src/trade/tradeState.ts`, `frontend/src/trade/AssetSearch.tsx`, `frontend/src/trade/TradeLab.tsx`, `frontend/src/trade/TradeLab.css`
- Modify: `frontend/src/shell/AppShell.tsx`
- Test: `frontend/src/trade/tradeState.test.js`, `frontend/src/trade/AssetSearch.test.jsx`

- [ ] **Step 1: Regenerate the typed client** (T1/T2 schemas now exist). Run: `cd frontend && npm run openapi-gen`. Expected: `types.gen.ts`/`zod.gen.ts` now include `TradeAssetCatalogResponse`, `TradeRosterReconciliation`, `TradeMarketReconciliation`, and a `zTradeAssetCatalogResponse` Zod schema. Commit the regenerated client as a build artifact (do not hand-edit).

- [ ] **Step 2: Write failing state tests** (`frontend/src/trade/tradeState.test.js`):

```js
import { describe, expect, it, beforeEach } from "vitest";
import { emptyTrade, addAsset, removeAsset, saveTrade, loadTrade } from "./tradeState";

describe("tradeState", () => {
  beforeEach(() => globalThis.localStorage?.clear?.());
  it("adds and keeps duplicate picks distinct by asset_id", () => {
    let t = emptyTrade();
    t = addAsset(t, "sent", { asset_id: "pick:2027:r1:orig5:owner1", label: "2027 1st" });
    t = addAsset(t, "sent", { asset_id: "pick:2027:r1:orig8:owner1", label: "2027 1st" });
    expect(t.sent).toHaveLength(2);
  });
  it("removes by asset_id without collapsing the other side", () => {
    let t = emptyTrade();
    t = addAsset(t, "received", { asset_id: "100", label: "Vet" });
    t = removeAsset(t, "received", "100");
    expect(t.received).toHaveLength(0);
  });
});
```

- [ ] **Step 3: Run to verify failure.** Run: `cd frontend && npx vitest run src/trade/tradeState.test.js` — Expected: FAIL (module missing).

- [ ] **Step 4: Implement `tradeState.ts`.**

```ts
export type CatalogEntry = { asset_id: string; label: string; [k: string]: unknown };
export type Side = "sent" | "received";
export type Trade = { sent: CatalogEntry[]; received: CatalogEntry[]; counterpartyRosterId: number | null };

const KEY = "dg.tradeLab.draft";
export const emptyTrade = (): Trade => ({ sent: [], received: [], counterpartyRosterId: null });

export function addAsset(t: Trade, side: Side, e: CatalogEntry): Trade {
  return { ...t, [side]: [...t[side], e] };
}
export function removeAsset(t: Trade, side: Side, assetId: string): Trade {
  return { ...t, [side]: t[side].filter((a) => a.asset_id !== assetId) };
}
export function saveTrade(t: Trade): void {
  try { globalThis.localStorage?.setItem(KEY, JSON.stringify(t)); } catch { /* ephemeral */ }
}
export function loadTrade(): Trade {
  try { const r = globalThis.localStorage?.getItem(KEY); if (r) return JSON.parse(r) as Trade; } catch { /* */ }
  return emptyTrade();
}
```

- [ ] **Step 5: Run to verify pass.** Run: `cd frontend && npx vitest run src/trade/tradeState.test.js` — Expected: PASS.

- [ ] **Step 6: Write failing AssetSearch test** (`frontend/src/trade/AssetSearch.test.jsx`):

```jsx
// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AssetSearch } from "./AssetSearch";

afterEach(() => vi.restoreAllMocks());

it("queries the catalog and calls onSelect with the chosen entry", async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: vi.fn().mockResolvedValue({
      query: "cha", source_timestamp: "2026-05-24T17:19:44Z", caveats: [],
      decision_supported: false,
      results: [{ asset_id: "100", label: "Chase", kind: "player", position: "WR",
                  model_payload: { player_id: "100", xvar: 22.5, position: "WR",
                                   is_prospect: false, decision_supported: false },
                  market_ref: { asset_kind: "player", sleeper_id: "100", player_id: "100",
                                decision_supported: false },
                  caveats: [], decision_supported: false }],
    }),
  });
  const onSelect = vi.fn();
  render(<AssetSearch onSelect={onSelect} />);
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "cha" } });
  await screen.findByText("Chase");
  fireEvent.click(screen.getByText("Chase"));
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ asset_id: "100" }));
});

it("does not query for inputs shorter than 3 characters", async () => {
  globalThis.fetch = vi.fn();
  render(<AssetSearch onSelect={vi.fn()} />);
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "ch" } });
  await waitFor(() => expect(globalThis.fetch).not.toHaveBeenCalled());
});
```

- [ ] **Step 7: Run to verify failure.** Run: `cd frontend && npx vitest run src/trade/AssetSearch.test.jsx` — Expected: FAIL (module missing).

- [ ] **Step 8: Implement `AssetSearch.tsx`** (mirror the TrustStrip fetch+Zod boundary pattern; guard <3 chars):

```tsx
import { useState } from "react";
import { zTradeAssetCatalogResponse } from "../lib/api/zod.gen";
import type { CatalogEntry } from "./tradeState";

export function AssetSearch({ onSelect }: { onSelect: (e: CatalogEntry) => void }) {
  const [results, setResults] = useState<CatalogEntry[]>([]);

  async function run(q: string) {
    if (q.trim().length < 3) { setResults([]); return; }
    try {
      const r = await fetch(`/api/trade/assets?q=${encodeURIComponent(q)}`);
      if (!r.ok) { setResults([]); return; }
      const parsed = zTradeAssetCatalogResponse.safeParse(await r.json());
      setResults(parsed.success ? (parsed.data.results as CatalogEntry[]) : []);
    } catch { setResults([]); }
  }

  return (
    <div className="dg-asset-search">
      <input type="search" aria-label="Search tradeable assets"
             onChange={(e) => void run(e.target.value)} />
      <ul>
        {results.map((e) => (
          <li key={e.asset_id}>
            <button type="button" onClick={() => onSelect(e)}>{e.label}</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 9: Mount TradeLab in the shell.** Create `TradeLab.tsx` (container rendering `<AssetSearch>` for now; expands in T4/T5) and render it from `AppShell.tsx` `<main>` when `activeSurface === "Trade Lab"`:

```tsx
// AppShell.tsx <main> body
<main className="dg-shell__main">
  <h1 className="dg-shell__title">{activeSurface}</h1>
  {activeSurface === "Trade Lab" && <TradeLab />}
</main>
```

- [ ] **Step 10: Run to verify pass + typecheck.** Run: `cd frontend && npx vitest run src/trade && npm run typecheck` — Expected: PASS.

- [ ] **Step 11: Commit.**

```bash
git add frontend/src/lib/api frontend/src/trade frontend/src/shell/AppShell.tsx
git commit -m "feat(frontend): mount Trade Lab surface; trade state + asset search

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Frontend — TradeSideBuilder ×2 + RunComparisonBar (parallel run)

**Files:**
- Create: `frontend/src/trade/TradeSideBuilder.tsx`, `frontend/src/trade/RunComparisonBar.tsx`
- Modify: `frontend/src/trade/TradeLab.tsx`
- Test: `frontend/src/trade/TradeLab.test.jsx`

RED contract: selecting assets fills two distinct sides (persisted), and "Run comparison" fires **two parallel POSTs** (`/api/trade/reconcile` with model payloads, `/api/trade/reconcile/market` with market refs) carrying the correct shapes; the optional counterparty selector adds `counterparty_roster_id` only when set.

- [ ] **Step 1: Write the failing test** (`TradeLab.test.jsx`):

```jsx
// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TradeLab } from "./TradeLab";

afterEach(() => { vi.restoreAllMocks(); globalThis.localStorage?.clear?.(); });

it("runs both lanes in parallel with the correct payload shapes", async () => {
  const calls = [];
  globalThis.fetch = vi.fn((url, init) => {
    calls.push({ url, body: init && JSON.parse(init.body) });
    if (String(url).includes("/api/trade/assets")) {
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({
        query: "cha", caveats: [], decision_supported: false, source_timestamp: null,
        results: [{ asset_id: "100", label: "Chase", kind: "player", position: "WR",
          model_payload: { player_id: "100", xvar: 22.5, position: "WR", is_prospect: false, decision_supported: false },
          market_ref: { asset_kind: "player", sleeper_id: "100", player_id: "100", decision_supported: false },
          caveats: [], decision_supported: false }] }) });
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ decision_supported: false }) });
  });

  render(<TradeLab />);
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "cha" } });
  fireEvent.click(await screen.findByText("Chase"));           // adds to "sent" (default side)
  fireEvent.click(screen.getByRole("button", { name: /run comparison/i }));

  await waitFor(() => {
    const urls = calls.map((c) => String(c.url));
    expect(urls.some((u) => u.endsWith("/api/trade/reconcile"))).toBe(true);
    expect(urls.some((u) => u.endsWith("/api/trade/reconcile/market"))).toBe(true);
  });
  const model = calls.find((c) => String(c.url).endsWith("/api/trade/reconcile"));
  expect(model.body.david_assets[0]).toMatchObject({ player_id: "100", is_prospect: false });
  const market = calls.find((c) => String(c.url).endsWith("/api/trade/reconcile/market"));
  expect(market.body.sent_assets[0]).toMatchObject({ asset_kind: "player", sleeper_id: "100" });
  expect(market.body).not.toHaveProperty("counterparty_roster_id"); // selector off by default → omitted/null
});
```

- [ ] **Step 2: Run to verify failure.** Run: `cd frontend && npx vitest run src/trade/TradeLab.test.jsx` — Expected: FAIL.

- [ ] **Step 3: Implement** `TradeSideBuilder` (renders a side's chips + remove), `RunComparisonBar` (run button + optional counterparty `<select>`), and wire `TradeLab` to own state (`loadTrade`/`saveTrade`), pass `model_payload` to the reconcile body and `market_ref` to the market body, fired with `Promise.all`. Build the market body as `{ sent_assets, received_assets, current_draft_year: 2026, format_key: "dynasty_sf_ppr", ...(counterpartyRosterId != null ? { counterparty_roster_id: counterpartyRosterId } : {}) }`. (Keep the lane *responses* in state for T5 to render.)

- [ ] **Step 4: Run to verify pass.** Run: `cd frontend && npx vitest run src/trade/TradeLab.test.jsx` — Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/trade
git commit -m "feat(frontend): two-side trade builder + parallel run comparison

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Frontend — two-lane panels + neutral divergence

**Files:**
- Create: `frontend/src/trade/ModelLanePanel.tsx`, `MarketLanePanel.tsx`, `DivergenceStrip.tsx`
- Modify: `frontend/src/trade/TradeLab.tsx`
- Test: `frontend/src/trade/lanes.test.jsx`

RED contract: the model and market lanes render in **two physically separate panels** with no shared/blended number; `favors`/`adjusted_favors` are never rendered; the divergence strip shows two separate lane facts + per-asset backend labels and never a single computed delta.

- [ ] **Step 1: Write the failing tests** (`lanes.test.jsx`): given a model reconciliation (`adjusted_favors: "david"`, side values) and a market reconciliation (`market_delta_for_david`, per-asset `divergence_context.signal_label: "model_higher_than_market"`), assert: (1) the model side value and market delta appear in **separate** containers (query by distinct `data-lane="model"` / `data-lane="market"` regions); (2) the strings `"david"` / `"favors"` / `"Favors"` are **absent** from the document; (3) the neutral label `model_higher_than_market` (or its display text) renders in the divergence strip; (4) no element contains a client-computed combined "vs" percentage that isn't one of the two backend lane numbers.

```jsx
// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ModelLanePanel } from "./ModelLanePanel";
import { MarketLanePanel } from "./MarketLanePanel";

it("renders model lane without surfacing favors/adjusted_favors", () => {
  render(<ModelLanePanel data={{ adjusted_favors: "david", adjusted_fairness_delta: 2.1,
    base_evaluation: { side_a: { side_value: 41.2 }, side_b: { side_value: 39.1 } },
    roster_penalty: { forced_cut_penalty_xvar: 3.1, forced_cut_candidates: [] },
    caveats: [], decision_supported: false }} />);
  expect(screen.queryByText(/favors/i)).toBeNull();
  expect(screen.queryByText(/\bdavid\b/i)).toBeNull();
  expect(screen.getByText(/41.2/)).toBeTruthy();
});

it("market lane renders neutral divergence label", () => {
  render(<MarketLanePanel data={{ market_delta_for_david: -520, market_sent_raw: 8420,
    market_received_raw: 7900, realism_warnings: [], coverage_gaps: [],
    source_timestamp: "2026-06-04T19:34:57Z",
    sent_assets: [{ label: "Chase", divergence_context: { signal_label: "model_higher_than_market" } }],
    caveats: [], decision_supported: false }} />);
  expect(screen.getByText(/model higher than market/i)).toBeTruthy();
});
```

- [ ] **Step 2: Run to verify failure.** Run: `cd frontend && npx vitest run src/trade/lanes.test.jsx` — Expected: FAIL.

- [ ] **Step 3: Implement the three components.** `ModelLanePanel` (blue, `data-lane="model"`): renders side values, parity state, forced-cut penalty + cut players, caveats — and **never reads `favors`/`adjusted_favors`**. `MarketLanePanel` (amber, `data-lane="market"`): raw sums, `market_delta_for_david`, realism warnings, coverage gaps, source timestamp, caveats. `DivergenceStrip`: renders the model lane delta and market lane delta as **two labelled facts** plus each asset's `divergence_context.signal_label` mapped to neutral display text (`model_higher_than_market` → "Model higher than market"); compute nothing. Wire all three into `TradeLab` below the builder.

> **Uncertainty treatment (spec §4) — honesty constraint:** the spec mandates point estimates carry uncertainty visuals, but the trade reconciliation responses are **point xVAR sums with no uncertainty band** in the current backend. The frontend must NOT invent a band (no client computation). v1 therefore renders the lane values as plain point estimates with the caveat copy the responses already carry, and the uncertainty *visual* (shaded band) is deferred until the backend supplies an uncertainty field. Flag this to the cockpit during plan review — if they want a band in v1, it is a backend increment, not a frontend invention.

- [ ] **Step 4: Run to verify pass.** Run: `cd frontend && npx vitest run src/trade/lanes.test.jsx` — Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/trade
git commit -m "feat(frontend): two-lane model/market panels + neutral divergence strip

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Frontend — coupled honest degradation + decision_supported visual

**Files:**
- Create: `frontend/src/trade/LaneDegradedState.tsx`
- Modify: `frontend/src/trade/TradeLab.tsx`
- Test: `frontend/src/trade/degradation.test.jsx`

RED contract: a 503 from the model lane renders **both** lanes unavailable (coupled — the market route 503s on the same missing artifacts); a stale-but-200 market response renders the market lane with caveats while the model lane stays available; a non-dismissible `decision_supported=false` banner is always present; neither degraded state implies the other lane is decision-grade.

- [ ] **Step 1: Write the failing tests** (`degradation.test.jsx`): three cases — (a) model `fetch` → `{ok:false, status:503}` and market → `{ok:false, status:503}` ⇒ both panels show an unavailable state, no side values rendered; (b) model → 200 valid + market → 200 with `caveats:["source_timestamp_is_fetch_time_not_publish_time"]` ⇒ model panel renders, market panel shows the caveat + stale treatment; (c) the `decision_supported` banner with text like "Not decision-grade" is always in the document and has no dismiss control.

- [ ] **Step 2: Run to verify failure.** Run: `cd frontend && npx vitest run src/trade/degradation.test.jsx` — Expected: FAIL.

- [ ] **Step 3: Implement.** Add per-lane state (`loading|ready|unavailable`) to `TradeLab`; on the run, set the model lane unavailable when its response is not ok, and the market lane unavailable when ITS response is not ok — they degrade by their own status (the coupling is a backend fact: when artifacts are missing both return 503, so both go unavailable naturally; when only FC is stale the market still returns 200 with caveats so only its caveats show). Render `LaneDegradedState` per lane and a permanent non-dismissible `decision_supported` banner in `TradeLab`.

- [ ] **Step 4: Run to verify pass.** Run: `cd frontend && npx vitest run src/trade/degradation.test.jsx` — Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add frontend/src/trade
git commit -m "feat(frontend): coupled honest lane degradation + decision_supported banner

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Governance — banned-language coverage, favors-non-render guard, full verification

**Files:**
- Modify (if needed): `frontend/scripts/check-banned-language.mjs` (scope), `frontend/src/shell/banned_vocabulary.json`
- Test: `frontend/src/trade/favors_guard.test.jsx`

RED contract: the banned-language linter scans the new `src/trade/` components; a frontend guard test proves `favors`/`adjusted_favors` values are never rendered; the full FE + Python gates are green; the S4 byte-audit is unaffected.

- [ ] **Step 1: Confirm linter scope.** Run: `cd frontend && npm run banned-language`. If `scripts/check-banned-language.mjs` does not already glob `src/trade/**`, extend its file glob to include it (the new components are authored source, not generated `src/lib/`). Re-run; Expected: PASS (no banned tokens in the neutral copy).

- [ ] **Step 2: Write a failing favors-guard test** (`favors_guard.test.jsx`): render `ModelLanePanel` with `adjusted_favors: "david"` and assert the rendered DOM text never contains `"david"`/`"favors"`/`"counterparty"` (defense-in-depth beyond the §3.3 rule — the linter can't catch a backend field name). Run to verify it passes against the T5 implementation (it should already hold; if it fails, the component is leaking the field — fix the component).

- [ ] **Step 3: Full frontend gate.** Run: `cd frontend && npm run typecheck && npm run lint && npm run test && npm run banned-language && npm run build`. Expected: all green.

- [ ] **Step 4: Full backend gate + S4 audit.** Run: `.venv/bin/python3.14 -m pytest tests/contract/test_surface2_trade_typing.py tests/contract/test_surface2_asset_catalog.py tests/contract/test_subsystem_4_audit.py -q` then the full suite `.venv/bin/python3.14 -m pytest -q` with **no `--ignore` flags unless a current blocker is explicitly documented in today's ledger or `AGENT_SYNC.md`** (do not carry forward a stale exclusion — Surface-1 state reports the full suite green). Expected: all pass; S4 inviolate-path baselines unaffected (we touched no S4 path).

- [ ] **Step 5: Commit.**

```bash
git add frontend/scripts frontend/src/trade frontend/src/shell/banned_vocabulary.json
git commit -m "test(frontend): banned-language coverage + favors-non-render guard for Trade Lab

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Verification gates (every task)
`tsc --noEmit` + Biome + Vitest (frontend) · the relevant pytest contract test (backend) · full `pytest` stays green at T1/T2 and T7 · `git diff --check` + scoped `git add` (never `-A`) · banned-language clean · `decision_supported` honored · model/market never blended · S4 byte-audit unaffected. No push to origin until cockpit dual-CLEAR + David's go.

## Out of scope (per spec §8)
Pick buckets / exact current-year slots; unrostered prospects; a backend-computed trade-level divergence number; TanStack; charting libs; generative UI; a price-only market route; any Engine A/B feature or evaluation-math change.

## Plan revisions (cockpit round 1 — 2026-06-05)
Codex + Gemini pressure-tested the plan; 8 source-verified fixes folded in:
1. **(HIGH)** `value_pick()` returns a `PickValue` model, not a tuple → use `.xvar`/`.caveats` (T2 impl + note).
2. **(HIGH)** PVO rows nest `player.full_name`/`player.position` and `valuation.xvar` → fixed extraction + test fixture (T2).
3. **(HIGH)** `load_curve()` requires the path → `load_curve(_PICK_CURVE_PATH)` in route + test (T2).
4. **(HIGH)** T1 RED tests now assert request-body `$ref` to `TradeAsset`/`MarketAssetRef` (response-typing alone didn't prove request typing).
5. **(MEDIUM)** `roster_owner_name` added to the entry model + extraction + test (spec §2.2 coverage).
6. **(MEDIUM)** limit clamp `max(0, min(int(limit), 100))` (negative-limit cap hole) + tests.
7. **(LOW)** T1 regression command uses real contract filenames (`test_phase23_w*` glob; the named `_w5a`/`_reconciler` files do not exist).
8. **(LOW)** explicit `TradeMarketReconciliation` import in `trade_market.py` (T1).
