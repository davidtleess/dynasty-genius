# Frontend Surface-3 Player Detail Implementation Plan

> **For agentic workers:** This project executes plans through the **tmux cockpit TDD loop** (Codex authors RED tests → Claude greens → dual-CLEAR → commit → loop-close), NOT the superpowers subagent model. Each task below gives the **RED contract** (the behaviors Codex's failing tests must assert) and the **GREEN target** (the implementation Claude writes). Steps use checkbox (`- [ ]`) syntax for tracking. **This plan must itself be cockpit dual-CLEARED before T1.**

**Status: DRAFT v1 (for cockpit dual-CLEAR)**
**Date:** 2026-06-06 · **Author:** Claude Code

**Spec:** `docs/superpowers/specs/2026-06-06-frontend-surface-3-player-detail-design.md` (committed `cee87f2`, v2 amendment, cockpit dual-CLEARED).

**Decomposition provenance:** the 10-task sequence below was cockpit-reviewed pre-authoring (Codex technical REJECT→fixes + Gemini governance CONCUR; two rounds). Folded: a dedicated OpenAPI/codegen task (T5), audit-script TDD split from production regen (T3a/T3b), fixture-monkeypatched endpoint RED (T4), entry-point wiring (T6), and the full **five-artifact** regen/audit scope incl. `universe_pvo_coverage_latest.json`.

---

## Standing constraints (do not relitigate — from the spec)
- **Backend additive, read-only, `decision_supported=False`** everywhere; no Engine A/B feature/training/model change.
- **Market overlay-only**, never a model input; **no green/red verdict hues**; banned David-facing patterns stay banned (rookie `confidence`/`dynasty_tier`, trade `verdict`, roster `action`).
- **Two-lane separation** (model = blue / market = amber) physically separate, never blended; **uniform-neutral divergence** (direction via label text only, no directional brand color).
- Runtime-dep budget unchanged (React + ReactDOM + Zod); no new runtime lib.
- **Commit placement:** this plan + the spec live on `main`; **all code AND regenerated artifacts land on the feature branch**, never on the `main` docs commits.

---

## Preflight (before T1)

- [ ] **Create the feature branch.** Code + artifacts land on a branch, not `main` (spec/plan docs are already on `main`).
  ```bash
  git checkout main && git pull
  git checkout -b feature/frontend-surface-3-player-detail   # base: latest origin/main (ecc7597 at plan authoring; rebase to current main before T1)
  ```
- [ ] **Confirm baseline green** (so later regressions are attributable):
  ```bash
  .venv/bin/python3.14 -m pytest tests/test_counter_arguments.py tests/test_phase17_universe_pvo_batch.py tests/contract/test_openapi_drift_contract.py -q
  cd frontend && npm run test && npm run typecheck && cd ..
  ```
  Expected: all pass.
- [ ] **Snapshot pre-regen artifacts** (for the T3 audit baseline — read-only copies, NOT committed):
  `resources/prospect_cards.json`, `resources/prospect_cards.js`, `app/data/valuation/universe_pvo_latest.json`, `app/data/valuation/universe_pvo_coverage_latest.json`, `docs/validation/phase15-2026-rookie-rank-refresh.md`.

---

## File structure

**Backend (Python):**
- `src/dynasty_genius/decision_logic/counter_arguments.py` — modify (T1)
- `tests/test_counter_arguments.py` — modify (T1)
- `src/dynasty_genius/universe_pvo_batch.py` — modify, Option-A preservation (T2)
- `tests/contract/test_surface3_pvo_preservation.py` — new (T2)
- `scripts/validate_surface3_regen_integrity.py` — new (T3a)
- `tests/test_surface3_regen_integrity.py` — new (T3a)
- `app/api/routes/players.py` — implement (T4); `app/main.py` — mount router (T4)
- `tests/contract/test_surface3_player_detail_endpoint.py` — new (T4)

**Regenerated artifacts (feature branch only, T3b — five tracked + two run-specific):**
- tracked: `resources/prospect_cards.json`, `resources/prospect_cards.js`, `app/data/valuation/universe_pvo_latest.json`, `app/data/valuation/universe_pvo_coverage_latest.json`, `docs/validation/phase15-2026-rookie-rank-refresh.md`
- run-specific (NOT committed): `app/data/valuation/universe_pvo_<run_id>.json`, `app/data/valuation/universe_pvo_coverage_<run_id>.json`

**Frontend (TS):**
- `frontend/openapi.json` + `frontend/src/lib/api/{types.gen,zod.gen,index}.ts` — regenerate (T5)
- `frontend/src/shell/AppShell.tsx` — modify, shell state + wiring (T6)
- `frontend/src/player/PlayerInspector.tsx` — new in T6 (minimal placeholder), completed in T7
- `frontend/src/player/{PlayerDetailPage,PlayerDetailCard,ValuationTwoLane,EvidenceSection}.tsx` — new (T8)
- `frontend/src/player/*.test.{jsx,tsx}` — new (T6/T7/T8)

---

## Task 1 — Issue-1 source rewrite (vocabulary-safe counter-arguments)

**RED contract (Codex authors):** `generate_counter_argument` for the high-value QB and TE templates returns the vocabulary-safe wording and contains **no banned standalone word** (`elite`/`starter`/`depth`/`bust`) and **no tier-family** term (`top-tier`, `dynasty tier`); the downside thesis is preserved (the assertion still names the rushing/efficiency risk for QB and the TD-dependency/scheme risk for TE).

- [ ] **Step 1 — failing test.** Update `tests/test_counter_arguments.py:59` (and any sibling assertion) to assert the new strings: QB → `"Premium valuation assumes continued high-level rushing or outlier passing efficiency; …"`; TE → `"… premium status is difficult to maintain …"`. Add an assertion that the returned string contains none of `banned_vocabulary.json` `banned_standalone_words`.
- [ ] **Step 2 — verify failure.** `.venv/bin/python3.14 -m pytest tests/test_counter_arguments.py -v` → FAIL (old "Elite" strings still returned).
- [ ] **Step 3 — implement.** In `counter_arguments.py`: line 33 `"Elite valuation"` → `"Premium valuation"`; line 39 `"elite status"` → `"premium status"`. No other text/logic change.
- [ ] **Step 4 — verify pass.** `.venv/bin/python3.14 -m pytest tests/test_counter_arguments.py -v` → PASS.
- [ ] **Step 5 — commit.** (Feature branch.)

---

## Task 2 — Option-A evidence preservation in `universe_pvo_batch.py`

**RED contract:** the rebuilt PVO row preserves **all 10 DTO-backed fields** — `counter_argument`, `risk_flags`, `top_drivers`, `caveats`, `draft_class`, `nfl_draft_pick`, `nfl_draft_round`, `projection_1y`, `projection_2y`, `projection_3y` — sourced from the assembled PVO; **every previously-read key is byte-identical**; the existing Trade Lab + asset-catalog suites stay green against a fixture-built artifact.

- [ ] **Step 1 — failing test.** `tests/contract/test_surface3_pvo_preservation.py`: build a small fixture PVO via the batch row-assembly path; assert the 10 keys present and equal to the source PVO; assert — against a **golden expected-shape fixture encoded in the test** (NOT a live "pre-change serializer", which won't exist post-implementation) — that the exact set of existing JSON paths (`dynasty_value_score`, `xvar`, `engine_path`, `sleeper_player_id`, …) is unchanged AND that exactly the 10 new keys appear (no other new key).
- [ ] **Step 2 — verify failure.** Run the new test → FAIL (keys dropped).
- [ ] **Step 3 — implement.** Extend the row-assembly loop in `universe_pvo_batch.py` to copy the 10 fields from the assembled PVO (`.get()` access; additive only). Do not alter any existing field.
- [ ] **Step 4 — verify pass + no regression.** Run the new test + `tests/test_phase17_universe_pvo_batch.py` + the Trade Lab/asset-catalog contract suites → PASS. Fix only test fixtures if a now-present key trips an exact-shape assertion (no logic change).
- [ ] **Step 5 — commit.**

---

## Task 3a — Integrity-audit **script** (TDD on synthetic fixtures)

**RED contract:** `scripts/validate_surface3_regen_integrity.py` exposes a pure comparator that, given pre/post artifact pairs, **fails loud** (non-zero / raises) on: (1) model-field value drift (e.g. a changed `dvs`/`xvar` float); (2) **key-set closure** violation (a new un-allowlisted key in post); (3) identity mismatch (changed `sleeper_id`/`player_id` for prospect_cards; `sleeper_player_id`/`dg_player_id` for universe_pvo); (4) provenance/lineage drift (`source_versions`/`source_season`/`source_snapshot_captured_at`/`lineage`); (5) `.js` embedded payload ≠ `.json`; (6) **any** coverage-count delta — the 10 preserved row keys are evidence fields and MUST NOT move `universe_pvo_coverage_latest.json`, so `total_players`/`counts_by_engine_path`/`decision_supported_true_count`/`market_overlay_present_count`/route lists must be **byte-identical (zero delta)**; any movement fails the audit (no "explained-delta" escape). It **passes** when the only diffs are the allowlist: `counter_argument` text on the cleaned QB/TE rows, `universe_pvo`'s 10 new keys, and timestamp/run-id fields (`captured_at` top+row, `assembled_at`, `pipeline_run_id`).

- [ ] **Step 1 — failing tests.** `tests/test_surface3_regen_integrity.py` with **small synthetic JSON/JS/report fixtures** (a handful of rows). One passing-case fixture (only allowlisted diffs) + one fixture per failure mode above. **No dependency on the 12k-row production rebuild.**
- [ ] **Step 2 — verify failure.** Run → FAIL (module missing).
- [ ] **Step 3 — implement** `scripts/validate_surface3_regen_integrity.py`: load pre/post per artifact; assert per-artifact identity sets; key-set closure (post keys == pre keys ∪ allowlisted-new); byte-equality on every non-allowlisted path; `.js` payload deserializes equal to `.json`; **coverage-count zero-delta** assertion (no explained-delta escape — any movement fails). Allowlist + STABLE-provenance pins are constants in the script (single source of truth).
- [ ] **Step 4 — verify pass.** Run → PASS (all fixtures).
- [ ] **Step 5 — commit.**

---

## Task 3b — Production 3-step regen + audited hard-stop gate  *(BLOCKED until T1 + T2 green)*

**RED contract:** none new (execution task). The gate is the T3a validator run on the real artifacts.

- [ ] **Step 1 — run the strict 3-step sequence:**
  ```bash
  # (T1 source rewrite + T2 preservation already merged on the branch)
  .venv/bin/python3.14 scripts/refresh_prospect_cards.py
  .venv/bin/python3.14 scripts/build_universe_pvo_batch.py
  ```
- [ ] **Step 2 — run the audited validator** (`validate_surface3_regen_integrity.py`) over the **five tracked artifacts** (`prospect_cards.json`, `prospect_cards.js`, `universe_pvo_latest.json`, `universe_pvo_coverage_latest.json`, `phase15-2026-rookie-rank-refresh.md`) vs the Preflight snapshots.
- [ ] **Step 3 — HARD STOP on any out-of-allowlist drift** (model-field/ranking/provenance, AND any **non-zero coverage delta**). **Escalate to David**; do not commit drifted artifacts. (Drift = feature/model/data movement since last build → would ripple into Regime-A / MFL / SF-QB.)
- [ ] **Step 4 — run-specific hygiene.** Confirm `universe_pvo_<run_id>.json` + `universe_pvo_coverage_<run_id>.json` are NOT staged (gitignored or removed by an approved cleanup step). Only the `*_latest` + prospect_cards + report move forward.
- [ ] **Step 5 — commit** the five tracked regenerated artifacts (audit clean) with the audit summary in the message.

---

## Task 4 — Backend endpoint `GET /api/players/{sleeper_id}`

**RED contract:** the endpoint returns a typed `PlayerDetailResponse` (never the raw PVO row); **modeled** row → full-shell with per-section completeness/degradation; **non-modeled** → typed degraded Experimental (`model=null`, `evidence=null`); source→DTO mapping applied (`market_rank_overall`←`overall_rank`, etc.); **a synthetic injected banned-term evidence string is suppressed + the element degraded** (`evidence_suppressed_banned_term`); market lane from A-1 with freshness caveat, degrades independently; `decision_supported` recursively False; **tests monkeypatch the NAMED module-level loader seams** — `_load_player_detail_artifacts()` (the cached PVO index) and `_load_market_divergence_artifact()` — with small fixtures (modeled / non-modeled / missing-market / synthetic-banned); **no production-artifact dependency**.

- [ ] **Step 1 — failing tests.** `tests/contract/test_surface3_player_detail_endpoint.py`: monkeypatch the named seams `_load_player_detail_artifacts` / `_load_market_divergence_artifact`; cases per the contract above; assert raw PVO keys never leak; assert no banned *fields* emitted; assert `decision_supported` recursively False.
- [ ] **Step 2 — verify failure.** Run → FAIL (route 404 / module empty).
- [ ] **Step 3 — implement** `app/api/routes/players.py`: Pydantic `PlayerDetailResponse`/`PlayerModelLane`/`PlayerMarketLane`/`PlayerEvidence`; cached module-level loaders named `_load_player_detail_artifacts()` (PVO index) + `_load_market_divergence_artifact()` (the monkeypatch seams, like Trade Lab `_load_reconcile_artifacts`); curate→DTO mapping; per-section `completeness` flags; backend banned-term scan of emitted evidence strings (suppress+degrade); `decision_supported=False` coercion-lock. Mount `players.router` in `app/main.py` (`include_in_schema` per existing API convention).
- [ ] **Step 4 — verify pass.** Run the new test → PASS.
- [ ] **Step 5 — commit.**

---

## Task 5 — OpenAPI snapshot + Hey/Zod client regen

**RED contract:** the committed `frontend/openapi.json` includes the `PlayerDetailResponse` schema; the regenerated `frontend/src/lib/api/{types.gen,zod.gen,index}.ts` expose `PlayerDetailResponse` + `zPlayerDetailResponse`; `tests/contract/test_openapi_drift_contract.py` stays green (snapshot matches the live app schema).

- [ ] **Step 1 — verify drift RED.** After T4 (endpoint live), run `.venv/bin/python3.14 -m pytest tests/contract/test_openapi_drift_contract.py -q` → expect **FAIL** (the live schema now carries `PlayerDetailResponse`; committed `frontend/openapi.json` does not yet). This preserves TDD discipline for the OpenAPI seam.
- [ ] **Step 2 — regenerate.** `cd frontend && npm run openapi-gen` (or the project's documented codegen command). Commit the regenerated client as a build artifact (no hand-edit).
- [ ] **Step 3 — verify drift guard PASS.** `.venv/bin/python3.14 -m pytest tests/contract/test_openapi_drift_contract.py -q` → PASS. `cd frontend && npm run typecheck` → PASS.
- [ ] **Step 4 — commit.**

---

## Task 6 — Shell state + entry-point wiring

**RED contract:** `AppShell` owns `selectedSleeperId` + inspector open/closed; selecting an **AssetSearch** result sets `selectedSleeperId` and opens the inspector; a **Trade Lab player chip** can set the same state; inspector open/close behaves predictably (close clears the open state, not the selection, per spec). Without this the surface is unreachable.

- [ ] **Step 1 — failing tests** (`frontend/src/player/shellState.test.jsx`): assert the state transitions above via the shell + a stubbed AssetSearch/chip.
- [ ] **Step 2 — verify failure.** `cd frontend && npx vitest run src/player/shellState.test.jsx` → FAIL.
- [ ] **Step 3 — implement.** Add `selectedSleeperId` + inspector-open state to `AppShell.tsx`; wire AssetSearch result + Trade Lab chip handlers to set it; render a **minimal `PlayerInspector` placeholder** (identity line + "Open full evidence card" action only — enough to mount/open/close) so **T6 is independently GREEN-able** without depending on T7. **T7 fleshes out the neutral-preview content into this placeholder.** No router/URL deep-link in v1.
- [ ] **Step 4 — verify pass.** Run → PASS + typecheck.
- [ ] **Step 5 — commit.**

---

## Task 7 — `PlayerInspector` (neutral preview)

**RED contract:** renders ONLY identity (name/position/team/age/draft capital), `model_status` + market availability, and a **neutral presence indicator** (plain counts: `"3 caveats · counter-argument available"`); **unmodeled categories are labeled explicitly** ("No active model score" / "Unmodeled category"), status-only; an "Open full evidence card" action; the universal `decision_supported=false` state. **Never** renders a grade, edge, delta, recommendation, truncated evidence text, subjective tier, or warning glyph.

- [ ] **Step 1 — failing tests** (`frontend/src/player/PlayerInspector.test.jsx`): assert presence-counts render; assert absence of grade/edge/delta/glyph/truncated-text; assert explicit unmodeled-category label on a non-modeled fixture.
- [ ] **Step 2 — verify failure.** Run → FAIL — the **T6 placeholder renders but lacks neutral-preview behavior** (presence counts, unmodeled-category labels, and absence of grade/edge/delta not yet implemented). (NOT "module missing" — T6 already created the file.)
- [ ] **Step 3 — implement** `frontend/src/player/PlayerInspector.tsx` per the contract — **completing the minimal T6 placeholder** into the full neutral preview (Zod-validated fetch at the boundary; reuse the TrustStrip degradation pattern).
- [ ] **Step 4 — verify pass.** Run → PASS + typecheck + banned-language check.
- [ ] **Step 5 — commit.**

---

## Task 8 — Full Decision-Evidence-Card page

**RED contract:** `PlayerDetailPage` fetches `GET /api/players/{sleeper_id}`, validates at the Zod boundary, renders the full card or the degraded Experimental state; `ValuationTwoLane` renders **two physically separate** tracks (model blue / market amber, never blended) + a **uniform-neutral slate** divergence element (direction via label text only, no directional brand color); `EvidenceSection` shows top drivers, risk flags (constitutional age-cliff amber), caveats, and the **full** counter-argument (no truncation); per-element auto-Experimental on null fields; market track degrades independently; `decision_supported=false` banner present + non-dismissible.

- [ ] **Step 1 — failing tests** (`frontend/src/player/PlayerDetailPage.test.jsx`): two-lane separation (distinct `data-lane` regions); no blended delta; uniform-neutral divergence (no directional-color class; label text conveys direction); full counter-argument rendered; non-modeled→Experimental; per-element degradation; banner present + non-dismissible.
- [ ] **Step 2 — verify failure.** Run → FAIL.
- [ ] **Step 3 — implement** `PlayerDetailPage.tsx`, `PlayerDetailCard.tsx`, `ValuationTwoLane.tsx`, `EvidenceSection.tsx`; render from `AppShell` `<main>` on the player surface.
- [ ] **Step 4 — verify pass.** Run → PASS + typecheck + banned-language check.
- [ ] **Step 5 — commit.**

---

## Task 9 — Verification / closeout

- [ ] **Frontend gates:** `cd frontend && npm run typecheck && npx biome check && npx vitest run && npm run build` → all green; banned-language gate green over the new components.
- [ ] **Backend:** `.venv/bin/python3.14 -m pytest` (full suite, per `AGENT_SYNC` exclusion list) → green.
- [ ] **S4 byte-audit gate:** run `tests/contract/test_subsystem_4_audit.py` — confirm the new endpoint + batch change + regen touch **no** S4 inviolate path (confirm, don't assume).
- [ ] **Regen audit recap:** confirm the T3b audit report is recorded; no out-of-allowlist drift; run-specific artifacts not committed.
- [ ] **Closeout:** ledger entry + `AGENT_SYNC` state update; PR with phase advanced, governance reads, files changed, tests run, product-alignment statement, no-market-leakage confirmation.

---

## Guardrails recap (every task)
- `decision_supported=False` recursive; no banned David-facing fields/patterns; banned-language CI linter covers new components; backend banned-term scan covers evidence **text**.
- Two-lane physical separation; uniform-neutral divergence; market overlay-only.
- No Engine A/B feature/training/model change; no market data in model inputs.
- Frontend on the feature branch; spec/plan on `main`; regenerated artifacts on the branch behind the T3 audit; run-specific artifacts never committed.

**Next after dual-CLEAR:** Preflight → T1. No code, regen, or dependency install until this plan is committed to `main`.
