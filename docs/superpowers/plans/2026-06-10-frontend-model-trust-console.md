# Model Trust Console v1 Implementation Plan

> **For agentic workers:** This project executes plans through the **tmux cockpit TDD loop** (Codex authors RED tests → Claude greens → Codex technical + Gemini governance dual-CLEAR → commit → zero-divergence audit), NOT the superpowers subagent model. Each task gives the **RED contract** (the behaviors Codex's failing tests must assert) and the **GREEN target** (the implementation Claude writes). Steps use checkbox (`- [ ]`) syntax. **This plan must itself be cockpit dual-CLEARED before T1.**

**Status: DRAFT v5 (for cockpit dual-CLEAR)**
**Date:** 2026-06-10 · **Author:** Claude Code
**Review:**
- v1 REJECTED (Codex, 4 verified): T1 "5 files" guard vs T2 fallback; "newest valid" source nondeterminism; unpinned `/model-card` missing contract vs T3 smoke; overbroad "no verdict anywhere". v2: phase-scoped 9-file allowlist, pinned source `run_id`s, pinned 4×200 `ModelCardResponse` (curated artifact; 404 synthetic-only), scoped verdict ban + "truth-led".
- v2 REJECTED (Codex, 3 verified): openapi snapshot path (`frontend/openapi.json`, not `src/lib/api/`); existing `test_trust_surface_v2.py` 9-section model-card assertion + `model_card_available` source contradict T2; T1 market-input audit under-specified. v3 resolves all — corrected path, T2 updates the existing test + repoints `model_card_available`, exact market-input boundary (feature_coefficients/feature-list token check; market_source/snapshot/ndcg_*_market allowed).
- v3 REJECTED (Codex, 1 verified HIGH): the curated `ModelCardResponse` artifact lacked the `model_version`/`model_artifact_hash` the T2 audit compares. v4 (option A): the published artifact is the internal **`PublishedModelCardSource`** (`model_card_source_{POS}.json` = curated fields + provenance); the audit reads source provenance; the route filters to the public curated `ModelCardResponse`.
- v4 REJECTED (Codex, 1 verified MEDIUM): the T2 route source-order bullet still named the old public-DTO artifact (stale v3 wording). v5 rewrites it to the `PublishedModelCardSource` source + filter, audit-reads-provenance-before-filter in both paths.

**Goal:** A read-only **Model Trust Console** — per-position (QB/RB/WR/TE) legibility of how much the model's valuations have earned trust, over a tracked, provenance-matched trust substrate.

**Architecture:** Backend substrate phase (T1–T3) publishes 4 provenance-matched `BacktestResult` + a manifest to a tracked governed path and repoints the existing trust-surface route to it; a curated typed `ModelCardResponse` DTO replaces the untyped model-card body. The frontend (T4–T10) is a new `frontend/src/trust/` surface that fetches the two typed endpoints, maps them through a curated view-model (anti-leakage), and renders a truth-led, anti-overclaim console.

**Tech Stack:** Python 3.14 / FastAPI / Pydantic v2 (backend); Vite + React + TS, Hey/Zod generated client, Vitest/RTL, Biome (frontend).

**Spec:** `docs/superpowers/specs/2026-06-10-frontend-model-trust-console-design.md` (committed `9f0191c` on `main`, v5, cockpit dual-CLEARED).

**Decomposition provenance:** the T1–T10 sequence was cockpit-reviewed across spec v1→v5 (2 substantive rejects: CI-dead substrate → Option A publication phase; internal contradictions; + a holistic anti-overclaim pass). Substrate T1–T3 **gate** the frontend (T4–T10 do not start until T1–T3 are CI-green).

---

## Standing constraints (do not relitigate — from the spec)
- **Read-only, additive, `decision_supported=False`** everywhere; **no Engine A/B feature/training/model change**; no new market-derived model inputs.
- **Anti-overclaim is the prime directive.** Neutral slate visuals; **no green/red, no checkmark glyphs, no `.green`/`.red`/`.verdict`/`.pass`/success classes**; gate labels are `MET`/`UNMET`/`DEFERRED`/`INSUFFICIENT DATA` (`MET` = point-estimate state, not decision support); CIs-include-zero dominate; the "edge unproven" verdict is the lede; `overall_grade` subordinate + qualified; **no "verdict" in authored frontend identifiers** ("G3 verdict" only as the prose name of the recorded finding).
- **Provenance integrity:** trust-surface and model-card must be the **same run** (publication audit, §3a); a mismatch fails the audit + blocks the frontend, never silent-renders.
- **Anti-leakage:** UI binds the curated `TrustConsoleViewModel` only, never the raw `BacktestResult`-superset shape.
- **No `.gitignore` change** (`app/data/backtest/trust_surface/` is not ignored).
- **Commit placement:** this plan + the spec live on `main`; **all code AND published artifacts land on the feature branch**, never on the `main` docs commits.

---

## Preflight (before T1)

- [ ] **Create the feature branch** (base: latest `origin/main`, currently `9f0191c`):
  ```bash
  git checkout main && git pull
  git checkout -b feature/frontend-model-trust-console
  ```
- [ ] **Confirm baseline green** (so later regressions are attributable):
  ```bash
  .venv/bin/python3.14 -m pytest -q          # full Python suite (≈1885 passed)
  cd frontend && npm run typecheck && npm run lint && npx vitest run && npm run banned-language && npm run build
  ```
- [ ] **Pin the source runs** (deterministic — **NOT** "newest valid"): the operator explicitly chooses one source `run_id` per position from the local (gitignored) `app/data/backtest/runs/`, **records the 4 pinned `run_id`s here + in the T1 commit message**, and passes them as explicit input to `publish_trust_surface.py`. The T1 audit asserts the output `manifest.json` `run_id`s **equal the pinned input** — publication never auto-selects by run-date (the spec replaced latest-by-run_date with a pinned published substrate).

---

## File structure

**Backend (substrate)**
- Create: `scripts/publish_trust_surface.py` — publishes the 4 curated `BacktestResult` + `manifest.json` to `app/data/backtest/trust_surface/latest/`; emits the stat/diff guard report. Pure, deterministic, re-runnable.
- Create (9 published artifacts — tracked): `app/data/backtest/trust_surface/latest/{backtest_result_{QB,RB,WR,TE}.json, model_card_source_{QB,RB,WR,TE}.json, manifest.json}` — T1 writes the 4 results + manifest; T2 adds the 4 `model_card_source` artifacts (the phase allowlist). `model_card_source_{POS}.json` is the **internal `PublishedModelCardSource`** shape (the curated public fields **+** provenance `model_version`/`model_artifact_hash`/`git_sha`); the route **filters** it to the public `ModelCardResponse`.
- Modify: `app/api/routes/trust_surface.py` — read the published path by default (keep monkeypatch seams); add `response_model=ModelCardResponse` to `/{position}/model-card`.
- Create: `app/api/schemas/trust_console.py` (or co-located) — `ModelCardResponse` DTO.
- Create: `scripts/validate_trust_publication.py` — the T1 + T2 publication audits (importable comparator + CLI).
- Test: `tests/contract/test_trust_publication_audit.py`, `tests/contract/test_model_card_response_route.py`, `tests/contract/test_openapi_drift_contract.py` (existing — must stay green).

**Frontend (`frontend/src/trust/`)**
- Create: `TrustConsole.tsx`, `TrustConsole.css`, `trustViewModel.ts`, `TrustTruthPanel.tsx`, `GateMatrix.tsx`, `FoldTable.tsx`, `ModelCardEssentials.tsx`, `QbReliabilityCallout.tsx`, `ProvenanceFooter.tsx`.
- Modify: `frontend/src/shell/AppShell.tsx` (rename slot + render `<TrustConsole/>`), `frontend/src/shell/AppShell.test.jsx` (nav label), `frontend/openapi.json` + `frontend/src/lib/api/{types.gen.ts,zod.gen.ts,index.ts}` (regen — snapshot is at `frontend/openapi.json`, NOT under `src/lib/api/`).
- Modify: `docs/governance/01-north-star-architecture.md` (primary-surface label "Backtest Harness" → "Model Trust", narrow correction only).
- Test (Vitest): co-located `*.test.jsx` per component.

---

## SUBSTRATE PHASE — T1–T3 gate the frontend (T4+ blocked until these are CI-green)

## Task 1 — Substrate publication (`BacktestResult` + manifest) + T1 audit + route repoint

**RED contract (Codex authors — `tests/contract/test_trust_publication_audit.py`, T1 portion):** the audit comparator over `app/data/backtest/trust_surface/latest/` **fails loud** when: (1) any of the 4 positions' `backtest_result_{POS}.json` is missing or `BacktestResult.load()` raises; (2) any published `BacktestResult` or `manifest.json` carries `decision_supported=True`, **or a market-derived model INPUT leak** — with an **exact boundary** (so the check is deterministically authorable): **allowed** (market comparison/provenance, *not* leakage) = `market_source`, `market_source_label`, `market_snapshot_dates`, fold `ndcg_at_*_market`; **disallowed → fail** = any fold `feature_coefficients` key, or any model feature-list entry, whose token matches `market`/`fantasycalc`/`ktc`/`adp`/`ecr` (case-insensitive); (3) the publish step's **stat/diff guard** finds any file in the tracked path outside the **T1 allowlist** {`backtest_result_{QB,RB,WR,TE}.json`, `manifest.json`} (broad `runs/` contents leaking). The guard is an **allowlist, phase-scoped** (not a fixed count): T1 allows those 5; T2 extends the allowlist with the 4 `model_card_source_{POS}.json`, so the **post-T2 allowed set = exactly 9 files**. It **passes** for a well-formed publication of the phase's allowed set. The T1 audit **must not reference `ModelCardResponse`** (it does not exist until T2). Additionally a **route test** (extend `tests/contract/test_trust_surface_route.py`): `GET /api/trust-surface/{POS}` reads the **published path** (`trust_surface/latest/`) — assert it returns the published `run_id` for each position from a fixture-published dir (monkeypatched), and 404s honestly when the published dir is empty.

**GREEN target (Claude):**
- `scripts/publish_trust_surface.py`: take the **explicitly pinned source `run_id`s** (one per position) as input, copy each pinned run's `backtest_result_{POS}.json` into `trust_surface/latest/`, write `manifest.json` with per-position `source_validation_note`, `run_id`, `run_date`, `git_sha`, `model_version`, `model_artifact_hash`, `market_source`/`market_source_label`, `publication_timestamp`, `decision_supported` (absent-or-false) — emit a compact file-list/size diff against the phase allowlist. Deterministic: **no "newest valid" selection** (pinned input only); no `Date.now()`-style nondeterminism beyond the explicit `publication_timestamp` input. The T1 audit asserts the manifest `run_id`s == the pinned input.
- `app/api/routes/trust_surface.py`: change `RUNS_DIR` default read to `app/data/backtest/trust_surface/latest/` (glob `backtest_result_{POS}.json` there); **keep the existing monkeypatch seam** so existing tests still inject a temp dir. Raw-runs reading may remain only as a documented local fallback, never the CI path.
- `scripts/validate_trust_publication.py`: the importable T1-audit comparator + a CLI entry.
- Publish the 4 real artifacts + `manifest.json` into the tracked path (on the feature branch).

- [ ] **Step 1 — Codex authors the T1-audit + route RED;** run focused → expect FAIL (audit/route not implemented; published dir absent).
- [ ] **Step 2 — Claude GREEN:** write `publish_trust_surface.py` + the audit comparator + repoint the route; run the publish step to populate `trust_surface/latest/`.
- [ ] **Step 3 — verify:** focused contract tests pass; `.venv/bin/python3.14 -m pytest tests/contract/test_trust_publication_audit.py tests/contract/test_trust_surface_route.py -q` PASS; full Python suite green; **S4 byte-audit unaffected** (`tests/contract/test_subsystem_4_audit.py`).
- [ ] **Step 4 — cockpit dual-CLEAR** (Codex technical + Gemini governance) → **Step 5 — commit** (artifacts + script + route + audit; record the 4 chosen `run_id`s) → zero-divergence audit.

---

## Task 2 — `ModelCardResponse` DTO + provenance-aligned model-card + T2 audit

**RED contract (`tests/contract/test_model_card_response_route.py` + the T2 audit portion):** `GET /api/trust-surface/{POS}/model-card` returns a typed `ModelCardResponse` with exactly the curated fields `position`, `backtest_run_id`, `generated_at`, `is_experimental`, `intended_use`, `out_of_scope_uses`, `caveats`, `known_failure_modes` — and **no** metrics/features/subgroups/calibration/ethical (no 9-section leakage). The **T2 publication audit** fails loud on any **provenance inequality** between the published `BacktestResult` and the served model-card on `position` / `run_id`↔`backtest_run_id` / `model_version` / `model_artifact_hash` (and `git_sha` where present); a **stale/mismatched** card fails the audit (build-time), never renders. **v1 PINNED contract:** the published substrate provides 4 provenance-aligned `model_card_source_{POS}.json` (the internal **`PublishedModelCardSource`** shape = the curated public fields **+** provenance `model_version`/`model_artifact_hash`/`git_sha`). The **T2 audit reads the SOURCE artifact's provenance** (`model_version`/`model_artifact_hash`/`git_sha`/`backtest_run_id`) for the equality check above — those fields live on the source artifact, **not** the public DTO. The route maps the source → public `ModelCardResponse` (dropping the provenance fields), so `/model-card` returns **200 `ModelCardResponse` for all 4 positions** (the T3 real-artifact smoke validates all 4 as 200 + Zod-valid against the public DTO). **Missing-card degradation = 404** (the existing route contract), exercised by a **synthetic** route/UI test only (a fixture with no published card), never over the real published artifacts. `decision_supported` absent/false on the model-card source. **Existing-test update (required):** `tests/contract/test_trust_surface_v2.py::test_get_model_card_200_returns_valid_model_card` currently asserts the **9-section `ModelCard`** body (`model_version`, etc.) — T2 rewrites it to assert the **curated `ModelCardResponse`** fields only (and that the 9-section keys are gone). **Consistency:** `model_card_available` on `GET /api/trust-surface/{POS}` must reflect the **published `model_card_source_{POS}.json`** — assert `/trust-surface` `model_card_available=true` ⟺ `/model-card` returns 200 (no "unavailable but 200" split).

**GREEN target:**
- `ModelCardResponse` Pydantic DTO (curated subset above) in `app/api/schemas/trust_console.py`.
- `/{position}/model-card`: `response_model=ModelCardResponse`; serve the **published, provenance-aligned** source — (i) the published `model_card_source_{POS}.json` (`PublishedModelCardSource`) at `trust_surface/latest/`, **filtered** to the public `ModelCardResponse` (8 curated fields), else (ii) the in-memory `ModelCard` for the position **iff** its provenance equals the published `BacktestResult`, likewise filtered to the same public DTO. In **both** paths the **T2 audit reads the source's provenance** (`model_version`/`model_artifact_hash`/`git_sha`/`backtest_run_id`) **before** the public-DTO filter — provenance is never lost to the audit.
- **Pinned model-card source (v1 default):** publish `model_card_source_{POS}.json` (the internal **`PublishedModelCardSource`** shape: the 8 curated public fields **+** provenance `model_version`/`model_artifact_hash`/`git_sha`) into `trust_surface/latest/` for each position, generated from the pinned published `BacktestResult` + the position's model-card safety text, with `backtest_run_id`/`model_version`/`model_artifact_hash`/`git_sha` == the published `BacktestResult`. The route reads this source and **filters to the public `ModelCardResponse`** (the 8 curated fields only — provenance fields are audit-internal, never in the public DTO/OpenAPI). Deterministic + co-located (resolves file-set + all-4-200 + the provenance audit). (`generate_model_cards.py` regen is an alternative only if deterministic; the published source artifact is the default.)
- Repoint `model_card_available` on `GET /api/trust-surface/{POS}` (currently computed from `MODEL_CARDS_DIR/{POS}_model_card.json`, `trust_surface.py`) to the **published `model_card_source_{POS}.json`**, so it agrees with `/model-card` returning 200; rewrite the `test_trust_surface_v2.py` model-card test to the curated `ModelCardResponse` shape.
- Extend `scripts/validate_trust_publication.py` with the T2 audit (provenance-equality + curated-only).

- [ ] **Step 1 — Codex authors the T2 RED;** focused → FAIL (untyped `dict[str,Any]` today; no provenance audit).
- [ ] **Step 2 — Claude GREEN:** DTO + `response_model` + source-order + provenance-aligned publication + T2 audit.
- [ ] **Step 3 — verify:** focused PASS; provenance-equality holds for all 4 positions over the published artifacts; full Python suite green.
- [ ] **Step 4 — dual-CLEAR → Step 5 — commit** (DTO + route + aligned card source + T2 audit) → zero-divergence.

---

## Task 3 — OpenAPI snapshot + Hey/Zod client regen + real-artifact smoke

**RED contract:** the committed `frontend/openapi.json` (the snapshot location) includes `ModelCardResponse`; the regenerated `zod.gen.ts`/`types.gen.ts` expose `ModelCardResponse` + `zModelCardResponse`; **assert the old `record<string, unknown>` shape is GONE** for the `/model-card` route in the generated client; `tests/contract/test_openapi_drift_contract.py` stays green (snapshot == live schema). **Real-artifact smoke:** a CI-real test consuming the **tracked published** `trust_surface/latest/*` artifacts validates `GET /api/trust-surface/{POS}` + `/model-card` for **all 4 positions** at the Zod boundary (this is the surface's production-faithfulness gate — and the point at which the frontend unblocks).

- [ ] **Step 1 — verify drift RED:** after T2, `.venv/bin/python3.14 -m pytest tests/contract/test_openapi_drift_contract.py -q` → FAIL (live schema now carries `ModelCardResponse`; committed snapshot does not).
- [ ] **Step 2 — regenerate:** `npm --prefix frontend run openapi-gen`; commit the regenerated client as a build artifact (no hand-edit).
- [ ] **Step 3 — verify:** drift test PASS; the "old shape gone" assertion PASS; real-artifact smoke PASS ×4 in CI.
- [ ] **Step 4 — dual-CLEAR → Step 5 — commit** (regenerated client). **← frontend unblocks here.**

---

## FRONTEND PHASE — T4–T10 (only after T1–T3 are CI-green)

## Task 4 — Nav rename + minimal `TrustConsole` placeholder

**RED contract (`AppShell.test.jsx` + a new `TrustConsole.test.jsx`):** the primary nav exposes a **"Model Trust"** item (the former "Backtest Harness" slot — assert the old label is gone and the new one present); selecting it renders `<TrustConsole/>` in `<main>`; the placeholder `TrustConsole` mounts a minimal shell (a heading "Model Trust" + position tabs QB/RB/WR/TE) so it **typechecks/builds independently** of T5. **No "verdict" in new/changed authored frontend trust identifiers/classes/tests** (the spec scope — the RED targets authored `frontend/src/trust/` + AppShell wiring only; existing generated/API/comment text and "G3 verdict" validation-finding prose are out of scope).

**GREEN target:** rename the `SURFACES` entry in `AppShell.tsx`; update the Surface-1 nav test; add the `01-north-star-architecture.md` label correction (narrow); render `<TrustConsole/>` when active; create a minimal `TrustConsole.tsx` placeholder. Keep blast radius narrow (the Surface-1 nav test is the canary).

- [ ] Step 1 RED (FAIL: no "Model Trust" nav / no TrustConsole) → Step 2 GREEN → Step 3 verify (full vitest, no Surface-1/2/3 regression; tsc/biome/banned-language) → Step 4 dual-CLEAR → Step 5 commit.

---

## Task 5 — `trustViewModel.ts` + `TrustConsole` shell + `TrustConsole.css`

**RED contract:** `trustViewModel.ts` maps validated `zTrustSurfaceResponse` + `zModelCardResponse` → a curated `TrustConsoleViewModel` exposing **only** the fields §4 needs (UI never sees the raw response); `TrustConsole` holds `activePosition` (default QB), fetches both endpoints per position on mount/tab-change, validates at the Zod boundary, and renders a **degraded** state ("Trust data unavailable") on non-ok/invalid/throw; each section degrades **independently**. `TrustConsole.css` is the neutral slate system (no green/red, no checkmark glyphs).

**GREEN target:** the mapper + the shell (tabs/fetch/degrade) filling the T4 placeholder + the CSS.

- [ ] Step 1 RED → Step 2 GREEN → Step 3 verify → Step 4 dual-CLEAR → Step 5 commit.

---

## Task 6 — `TrustTruthPanel`

**RED contract:** renders the **fixed G3 verdict copy** (a single canonical constant — finalize wording from `docs/validation/2026-05-31-step5b2-g3-ecr-validation.md`; **no global R² claim**), a **non-dismissible** `decision_supported=False` state, `experimental` ("Experimental — not validated"), and `overall_grade` **subordinate + qualified** (neutral text below the verdict with the fixed qualifier "internal model grade — not a market-edge or decision-support claim"; never a badge/lede). **Never** a colored grade, success styling, or a "verdict" identifier/class. (If the grade vocabulary reads as a success tier, demote to the provenance footer — confirm at this task.)

**GREEN target:** `TrustTruthPanel.tsx`.

- [ ] Step 1 RED → Step 2 GREEN → Step 3 verify (banned-language + anti-overclaim assertions clean) → Step 4 dual-CLEAR → Step 5 commit.

---

## Task 7 — `GateMatrix` (MET/UNMET)

**RED contract:** renders the four `GateResult` fields as neutral text labels: `g1_rank_correlation_pass`/`g2_rmse_stability_pass` (bool) → `MET`/`UNMET`; `g3_market_superiority_pass` (`True|False|"deferred"`) → `MET`/`UNMET`/`DEFERRED`; `g4_divergence_validity_pass` (`True|False|"deferred"|"insufficient_data"`) → `MET`/`UNMET`/`DEFERRED`/`INSUFFICIENT DATA`. **No** green/red, **no** checkmark glyph, **no** `.green`/`.red`/`.verdict`/`.pass`/success-colored class on any gate; a `MET` is never styled as success. Assert (e.g. WR) that a `MET` G3 still sits under the CI-includes-zero framing (the matrix does not imply edge).

**GREEN target:** `GateMatrix.tsx`.

- [ ] Step 1 RED → Step 2 GREEN → Step 3 verify → Step 4 dual-CLEAR → Step 5 commit.

---

## Task 8 — `FoldTable`

**RED contract:** renders the per-fold `FoldResult` rows with point estimate **and its BCa CI in the same weight/size**, plus a neutral **"(inc. 0)"** marker when the interval contains zero, for: `kendall_tau`+`kendall_tau_bca_ci95`, `spearman_rho`+`spearman_rho_bca_ci95`, `rmse`, `r2_oos` (Optional — render the fixed-token `r2_oos` caveat when null, never a fabricated value), `ndcg_diff_primary_k`+`ndcg_diff_bca_ci95` (Optional). Fold identity columns (index/test-season/sample sizes) read from `FoldResult`; the real-artifact smoke gates any identity field-name mismatch. Empty `folds` → "not available", no fabrication.

**GREEN target:** `FoldTable.tsx`.

- [ ] Step 1 RED → Step 2 GREEN → Step 3 verify → Step 4 dual-CLEAR → Step 5 commit.

---

## Task 9 — `ModelCardEssentials` + `QbReliabilityCallout` + `ProvenanceFooter`

**RED contract:** `ModelCardEssentials` renders `intended_use` (paragraph) + `out_of_scope_uses`/`caveats`/`known_failure_modes` (lists), **full text, no truncation**; missing card → "Model card unavailable" (independent runtime degradation). `QbReliabilityCallout` renders **only when `position === "QB"`** and `model_reliability` present — neutral "elevated uncertainty" framing (e.g. OOS R², Spearman), not a defect badge; omitted for other positions. `ProvenanceFooter` renders `run_id`/`run_date`/`model_version`/`model_artifact_hash`/`git_sha`/`market_source_label`/snapshot dates as small, neutral, copyable provenance — never grades/trophies.

**GREEN target:** the three components.

- [ ] Step 1 RED → Step 2 GREEN → Step 3 verify → Step 4 dual-CLEAR → Step 5 commit.

---

## Task 10 — Verification / closeout

**RED contract:** none new (verification task).

- [ ] **Full FE gate:** `cd frontend && npm run typecheck && npm run lint && npx vitest run && npm run banned-language && npm run build` — all green; banned-language clean over `frontend/src/trust/`.
- [ ] **Anti-overclaim sweep:** no `.green`/`.red`/`.verdict`/`.pass`/success classes or checkmark glyphs in `frontend/src/trust/`; gate labels MET/UNMET/DEFERRED/INSUFFICIENT only; `overall_grade` qualifier present; `decision_supported=false` non-dismissible.
- [ ] **Full Python suite** green; **S4 byte-audit** unaffected; the **publication audit** (T1+T2) green over the tracked published artifacts.
- [ ] **Closeout docs:** daily ledger + `AGENT_SYNC` Active-Phase update.
- [ ] **PR + final CI** (David-gated): push the feature branch, open the PR, confirm both CI jobs green; mark-ready/merge on David's call (preserved commits per precedent).

---

## Guardrails recap (every task)
- `decision_supported=False` recursive; read-only; no Engine A/B model/training change; no new market-derived input.
- Anti-overclaim: neutral slate, no green/red/checkmark/`.verdict`/`.pass`; MET/UNMET gate labels; CIs-include-zero dominate; `overall_grade` subordinate+qualified; no "verdict" in authored FE identifiers.
- Provenance integrity: trust-surface ⟷ model-card same run (audit fails loud on mismatch); curated view-model anti-leakage boundary.
- Production-faithfulness: every backend/UI surface gets a fixture test **and** a real-artifact smoke over the tracked published files (the Surface-3 fixture-vs-reality lesson).
- Commit placement: code + published artifacts on the feature branch; this plan + spec on `main`. Each task: Codex RED → Claude GREEN → dual-CLEAR → commit → zero-divergence audit.
