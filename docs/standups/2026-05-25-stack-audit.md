# Frontend Stack Audit: 2026 Operational Playbook vs. Dynasty Genius Bootstrap

**Document Type:** Strategic Bootstrap Audit and State Alignment  
**Author:** Gemini (Product Manager)  
**Status:** Review Draft (For Collaborative Discussion)  
**Date:** 2026-05-25  

---

## 1. Executive Summary

This audit compares the current **Dynasty Genius** bootstrap state against the **2026 Operational Playbook** recommendations. 

Our current frontend bootstrap consists of a single, vanilla, hand-rolled file: [rookie_board.html](file:///Users/davidleess/dynasty-genius-product/src/dynasty_genius/dashboard/rookie_board.html), served by a simple FastAPI static routing structure. We have **no frontend framework, build tools, package manager, or CSS libraries** currently checked in. The codebase remains highly optimized for backend ML pipelines, data normalization, and localized Python logic.

This audit maps our baseline state to the playbook's recommendations to inform David's stack decisions and sequence planning.

---

## 2. Detailed Audit Table

### 2.1 Core Framework & Tooling

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **Vite + React + TypeScript Stack** | **❌ Not in place** | Current frontend is a single vanilla HTML file (`rookie_board.html`) served statically; no Node.js runtime, build tool, or frontend framework exists yet. |
| **pnpm 10 Package Manager** | **❌ Not in place** | No `package.json` or JS/TS package management is configured; Python dependencies are managed via pip (`requirements.txt`). |
| **mise Toolchain Pinning** | **❌ Not in place** | No `.mise.toml` or `.tool-versions` files exist in the repository root. |

### 2.2 API Codegen & Validation

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **Hey API (`@hey-api/openapi-ts`)** | **❌ Not in place** | No codegen pipelines are configured; the frontend currently has no TS types or schema validation. |
| **Zod v4 Validation at the Edge** | **❌ Not in place** | No client-side Zod validation; data models are validated exclusively on the backend using Pydantic. |

### 2.3 Routing & Server State

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **TanStack Router** | **❌ Not in place** | The current page has no routing layer; Trade Lab is not yet wired as a multi-page routing SPA. |
| **TanStack Query v5** | **❌ Not in place** | Renders are driven by manual, hand-written vanilla `fetch()` operations without a caching or query state layer. |

### 2.4 Styling & UI Elements

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **Tailwind v4 (`@theme inline`) + OKLCH Tokens** | **❌ Not in place** | The current board utilizes manual, basic CSS/HSL classes styled with browser defaults and inline stylesheets. |
| **shadcn/ui (New York Style) + Radix UI Primitives** | **❌ Not in place** | No component registry or Radix primitives exist in the repo; `rookie_board.html` renders raw, default HTML tags. |

### 2.5 Tables & Cockpit Primitives

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **TanStack Table v8 + TanStack Virtual** | **❌ Not in place** | Currently uses standard HTML `<table>` elements with custom vanilla JS client-side filter and sorting logic. |
| **cmdk (via shadcn Command Component)** | **❌ Not in place** | No global command palette or virtualized player selector is implemented. |

### 2.6 Analytical Charting

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **Three-tier Charting (Tremor / Recharts / Observable Plot / Visx)** | **❌ Not in place** | No visualization libraries are present in the frontend; analytical scoring results are rendered purely as numbers and textual cards. |

### 2.7 Quality Gates, Testing & Linting

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **Biome v2 (Linting & Formatting)** | **🔄 In place but different** | Frontend Biome is not set up; Python linting and imports are strictly managed by Ruff via `.pre-commit-config.yaml` and `pyproject.toml`. |
| **Vitest + Playwright + MSW (Testing Stack)** | **🔄 In place but different** | No frontend test harness is wired up; backend has a highly comprehensive Python `pytest` suite of 1,153 tests. |

### 2.8 Agent Coordination & Data Substrate

| Playbook Recommendation | Status | Notes / Current State |
|---|:---:|---|
| **`AGENTS.md` + `CLAUDE.md` / `GEMINI.md` thin imports** | **✅ Already in place** | All three files exist at root, enforce strict bootstrap order, and contain thin, agent-specific reference overrides. |
| **`openai/codex-plugin-cc` / TMUX Comms Helper** | **✅ Already in place** | Codex and Claude have authored `scripts/tmux_msg.py` and `tests/test_tmux_msg.py` to run explicit, safe, bracketed paste communication across TMUX panes. |
| **DuckDB + Local Parquet (Rejecting Remote Databricks)** | **✅ Already in place** | North Star Architecture successfully keeps the frontend read-only over served PVO JSON outputs from the local FastAPI backend, skipping any remote Databricks calls. |

---

## 3. Findings & Key Implications

1. **Day 1 Greenfield Readiness:** Because we currently have no frontend framework code, we are in a perfect position to build a pristine **Vite + React + TS** stack from scratch without having to migrate or tear down legacy JS files, build setups, or packages.
2. **Backend Integrity:** Our backend FastAPI route structure, identity resolution layer, and PVO generators are completely isolated and ready to serve structured endpoints.
3. **Consensus Infrastructure Ready:** Our TMUX-based multi-agent peer-review harness is fully functional. The only pending element is wiring it into our frontend development process.

---

## 4. Next Steps for Collaborative Review

This audit is presented strictly to surface state and identify mismatches. No design decisions are made in this document. 

David, once you have reviewed this audit, we stand ready to:
1. Finalize the stack selection (e.g. confirming **Vite + React + TS** served statically via FastAPI under a strict dependency budget).
2. Authorize the consolidation of our independent agent recommendations into a single, authoritative `Frontend Design` spec.
3. Establish the Phase 0 bootstrap script (configuring pnpm, Vite, shadcn, and the basic cockpit theme) as approved.

---

## 5. Claude Code — Delta & On-Disk Specificity Layer

**Author:** Claude Code (local development agent)
**Status:** Alignment round CLOSED 2026-05-25. Decisions locked at
`docs/validation/2026-05-25-frontend-stack-consensus-decision.md`. This section
extends Gemini's state-surfacing audit with on-disk specifics and corrections; it
does not redo the audit.

### 5.1 Corrections to on-disk claims

These refine Section 2/2.8 against the actual tree (verified 2026-05-25):

- **`rookie_board.html` is NOT served by the main FastAPI app.** There is no
  `StaticFiles` / `HTMLResponse` / `templates` mount in `app/`. It is served by a
  **standalone** `scripts/serve_rookie_board.py` (a `http.server`-based dev server
  with its own `/refresh` POST hook), and it loads data via relative file includes
  — `<script src="../../../resources/prospect_cards.js">`,
  `draft_state.js`, `roster_need_signals.js` — **not** FastAPI JSON endpoints.
  Implication: the playbook's "React served by FastAPI" integration genuinely does
  not exist yet; the live board is a separate mini-server reading bundled JS data
  resources. (Audit §2.1 "served by a simple FastAPI static routing structure" and
  §2.8 "read-only over served PVO JSON outputs from the local FastAPI backend"
  overstate the current wiring.)
- **DuckDB + Local Parquet is NOT in place as a data substrate** (audit §2.8 marks
  it ✅). No DuckDB runtime usage and no `.parquet` files or `read_parquet`/
  `to_parquet` calls were found in `app/`, `src/`, or `scripts/`; decision-grade
  artifacts are **JSON** (e.g. `app/data/valuation/*.json`) plus `.md` companions.
  (Narrowed per Codex review 2026-05-25: the source-registry *does* declare a
  `parquet_snapshot` cache policy — `src/dynasty_genius/sources/source_registry.py:52`
  enum, used at lines 92 and 328 — so the prior "no parquet anywhere" wording
  overclaimed; it is a declared cache-policy value, not a materialized substrate.)
  What is true: the local-first / no-remote-Databricks *intent* holds in the
  serving path, but the substrate is JSON, not DuckDB. The "reject Databricks →
  local DuckDB" recommendation is **net-new / not implemented**, not already in place.
- **`scripts/tmux_msg.py` ≠ `codex-plugin-cc`** (audit §2.8 conflates them). The
  tmux helper is our home-grown bracketed-paste pane-messaging script (currently
  untracked in git status); `codex-plugin-cc` is OpenAI's first-party Claude↔Codex
  bridge and was **explicitly declined** for its Stop-hook gate (manual
  `/codex:review` only — see ADR locked item 3).
- **Suite state**: latest recorded is **1,188 passed / 11 skipped** (AGENT_SYNC,
  Phase 23 W5a, 2026-05-25), not 1,153.

### 5.2 The AGENTS.md doctrine conflict — surfaced and resolved

The playbook wants `AGENTS.md` to *hold* the ~150-line operational policy with
`CLAUDE.md` as a thin `@import`. Our operating loop forbids exactly that:
§"Authority Order" states *"Root bootstrap files point here and must not duplicate
the full doctrine."* On disk, `AGENTS.md`, `CLAUDE.md`, and `.clauderules` are
already ~998-byte thin pointers into `docs/governance/{00..03}` + `AGENT_SYNC.md`;
`GEMINI.md` carries role-specific addenda. **Resolution (ADR locked item 4):**
keep the current layout. The playbook's *intent* (single source of truth + thin
per-agent layers) is already satisfied — it just lives in `docs/governance/`, not
in `AGENTS.md`. No churn.

### 5.3 `rookie_board.html` fate

**Decided — Option (c):** retain as the live-draft tool until a specific React
equivalent earns its way in via ADR + surface spec. It is the production proof of
the playbook's Section 7 escape hatch. Displacement requires explicit ADR
justification; not a default replacement target. (ADR secondary decision.)

### 5.4 Branch discipline — on-disk specifics

Recent **direct-to-main** commits exist in history: Phase 19 `2ffbf13` (W3/W4/W5
TE Head A v3 + scorer wiring) and `ab9f085` (AGENT_SYNC closeout). Branch-and-PR
discipline is **re-affirmed** going forward (ADR secondary decision); these are
treated as exceptional, not precedent.

### 5.5 Community-skill supply-chain rule

Any community skill (`jezweb`, `anivar`, `capraidev`, or any other upstream —
several are recommended in playbook §3f) is **vendored-and-pinned** under
`.claude/skills/` at a specific git SHA. No upstream references in `CLAUDE.md` or
`.claude/` config. If we adopt a skill, we own the version. (ADR secondary decision;
consistent with the project's dependency-discipline + git-hygiene standards.)

### 5.6 Net-new items that encode existing contracts (build-time, gated)

Three playbook items are net-new only as *UI encodings of contracts already
enforced in Python*, and are worth adopting when we build:

- **Two-lane model/market OKLCH tokens** ← the strict model/market separation
  doctrine (north-star "Market Overlay").
- **`decision_supported=false` as a visual state** ← the coercion-locked
  `decision_supported=False` enforced across Phase 23 schemas.
- **Banned-language CI gate on the UI** ← the banned-verdict-language guard
  already enforced on serialized Python output (Phase 23 `_safe_source_status`,
  banned-field contract tests).

### 5.7 Pushback retained from the alignment read

- Do not day-1 install the full TanStack ecosystem + community skills + MCP
  servers — contradicts the playbook's own "minimal deps until earned" budget
  (§5) and the longevity concern. Codified as ADR locked item 2.
- Reject `--dangerously-skip-permissions` (playbook §3e) — conflicts with the
  "ask before commands that modify the machine" standard and the operating-loop
  no-bypass clause.

