# Build Plan — Frontend Surface 1: App Shell + ⌘K + Trust Strip

**Status: DRAFT (for cockpit dual-CLEAR)**
**Date:** 2026-06-03 · **Author:** Claude Code · **Type:** build plan (cockpit TDD)
**Spec:** `docs/superpowers/specs/2026-06-03-frontend-design-spec.md` (committed `df23839`)
**ADR:** `docs/validation/2026-05-25-frontend-stack-consensus-decision.md` (+ 2026-06-03 hold-lift addendum)

---

## 0. Scope & gate

Surface 1 is the **proving ground** for the three structural contracts, the palette/token system, the data-contract seam, and governance-in-CI — **before** any stateful surface (Trade Lab is surface 2). Deliverable: a running Stack-A app shell with a left-rail nav, a sticky **Trust strip**, a hand-rolled **⌘K** command palette, and a right-side inspector slot — rendering read-only over FastAPI.

**This plan authorizes the first dependency install** (at T1), within the locked bounds and the **correct package shape** (Codex finding 2):
- **runtime `dependencies` = `react`, `react-dom`, `zod`** (the actual browser runtime).
- **build/dev `devDependencies` = `vite`, `typescript`, `@biomejs/biome`, `vitest`** at T1; **`@hey-api/openapi-ts` added at T5** (not T1 — preserves "codegen after the shell", Codex finding 1).
- all **exact-pinned, no `^`/`~`**; **no Tailwind, no charting libs, no TanStack, no cmdk** (hand-rolled or ADR-deferred). `rookie_board.html` untouched.

## 1. Workspace layout (proposed — cockpit to confirm)

```
frontend/                      # new; the only JS/TS tree
  package.json                 # exact-pinned deps; "type": "module"
  vite.config.ts
  tsconfig.json                # strict, noUncheckedIndexedAccess, exactOptionalPropertyTypes, verbatimModuleSyntax
  biome.json                   # frontend-only; Ruff stays canonical for Python
  index.html
  src/
    main.tsx, App.tsx
    styles/tokens.css          # OKLCH CSS custom properties (no Tailwind)
    shell/ (AppShell, LeftRail, TrustStrip, Inspector)
    command/ (CommandPalette ⌘K)
    contracts/ (types: DecisionEvidenceCard, TwoLane, Experimental — type-level)
    lib/ (api client; Hey API generated output lands here later)
  tests/ (Vitest)
ci: banned-language linter script (authored-source + rendered-string scoped)
```
FastAPI serves `frontend/dist/` as a **scoped fallback** (see T1). Hey API generated client is a build artifact under `src/lib/` — never hand-edited.

## 2. TDD task sequence (each: Codex RED → Claude GREEN → dual-CLEAR → commit → loop-close)

- **T1 — Scaffold + scoped FastAPI static mount.** Init the Vite+React+TS workspace; pin **`dependencies` = react/react-dom/zod**, **`devDependencies` = vite/typescript/@biomejs/biome/vitest** (NOT Hey API — that's T5); tsconfig strict; Biome config. Wire FastAPI to serve `frontend/dist/` as a fallback mounted **last**.
  - **RED (Python, pytest) — explicit shapes (Codex finding 3):** `/openapi.json` → JSON OpenAPI (not SPA); `/docs` + `/redoc` → FastAPI docs HTML; an unknown `/api/*` → API **404 JSON** (not SPA `index.html`); built asset paths → the asset or an asset 404 (not `index.html`); app paths (`/`, `/roster`) → SPA `index.html` **only after `dist/` exists**; `rookie_board.html` (standalone `serve_rookie_board.py`) unaffected. *(First `npm install` happens here.)*
  - **GREEN:** the scaffold + a `StaticFiles`/catch-all wired with the exclusion ordering. Existing pytest suite stays green.

- **T2 — Design tokens + palette discipline.** `tokens.css` (OKLCH custom properties): model=blue, market=amber (+cliff amber), **no green/red verdict colors**, orthogonal position hues, DVS 0–100 scale, typography/spacing.
  - **RED (Vitest):** required tokens present; a guard test asserts **no verdict green/red token** exists and the model/market hues are distinct from position hues.

- **T3 — App shell layout.** `AppShell` = persistent left-rail nav (~7–8 page placeholders), sticky top **Trust strip slot**, right collapsible inspector.
  - **RED (Vitest):** renders the three regions; nav persists across route placeholders; inspector toggles.

- **T4 — ⌘K command palette (hand-rolled).** Opens on ⌘K, keyboard-navigable, fuzzy-filters a command registry, runs a command; no `cmdk` dep.
  - **RED (Vitest):** ⌘K opens it; typing filters; Enter runs the focused command; Esc closes.

- **T5 — Trust strip + the data-contract seam.** Per the ADR, **Hey API codegen is wired here** (first real data need): `@hey-api/openapi-ts` (pinned, dev-only) generates TS+Zod from FastAPI OpenAPI into `src/lib/`; the Trust strip renders **model grade + source freshness** read-only from the generated client (model-card / trust-surface route family), validated at the SDK boundary.
  - **RED (Vitest):** given a mocked endpoint shape, the strip renders grade + freshness and shows the **`decision_supported`/Experimental** state; an unavailable/stale response degrades visibly (never implies confidence).

- **T6 — Banned-language CI linter.** A linter (Node or Python) scanning **authored FE source + UI-rendered string literals**, **excluding** `src/lib/` generated output; flags the constitution's banned David-facing patterns. Wired into the pre-commit/CI gate.
  - **RED:** a seeded banned label in a fixture component fails the linter; the generated client carrying a banned-shaped *field name* does NOT.

- **T7 — Surface-1 verification.** Full FE check (Vitest + Biome + tsc) green; the banned-language linter green; the **Python suite still green** (mount change safe); the three contracts present as types; ⌘K + Trust strip + shell demonstrably honor the Experimental/`decision_supported` treatment.

## 3. Verification gates (every task)

`tsc --noEmit` + Biome + Vitest (frontend) · the relevant Python contract test (T1) · full `pytest` stays green · `git diff --check` + cockpit hygiene · S4 byte-audit unaffected (no backend source touched beyond the additive mount). No banned language; `decision_supported` honored; model/market never blended.

## 4. Resolved (cockpit, 2026-06-03 — Codex + Gemini concur)

1. **Workspace dir:** `frontend/` (keeps JS tooling out of `app/`; clean Biome/CI scoping).
2. **Exact pinned versions:** latest stable at scaffold time, **exact-pinned, no `^`/`~`**; resolved/recorded in `package.json` at the T1 commit. (`dependencies` = react/react-dom/zod; `devDependencies` = vite/typescript/@biomejs/biome/vitest; `@hey-api/openapi-ts` added at T5.)
3. **Hey API timing:** **T5, not T1** (codegen after the shell).
4. **CI:** a **separate `frontend-checks` job** (Biome + Vitest + `tsc`) — the existing Python/Ruff/pytest job stays unchanged.
5. **Toolchain pin:** `package.json#packageManager` + `.node-version` (no mise).

---

**On dual-CLEAR:** Codex authors the T1 RED (the FastAPI mount-exclusion contract test) and we begin the loop. The first `npm install` is part of T1 GREEN — the first time JS tooling enters the repo.
