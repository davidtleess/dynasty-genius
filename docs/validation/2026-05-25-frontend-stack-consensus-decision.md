# Frontend Stack Consensus Decision (ADR)

**Status: APPROVED (David-Locked, Multi-Agent Consensus)**

**Date**: 2026-05-25
**Decision owner**: David
**Authoring agent**: Claude Code
**Type**: Architecture Decision Record — frontend direction (planning only)

---

## Scope & Standing Constraint

This ADR records the decisions from the 2026-05-25 frontend-stack alignment round.
It is **planning only**. The constitution's "Frontend comes last" ruling and the
north-star Phase 12 sequencing remain binding, and `AGENT_SYNC.md`'s frontend
**HOLD** stays in effect: no frontend build, no dependency installs, no merge of a
frontend design spec follows from this document. All future frontend-related work
references this ADR.

Source inputs:

- Operational playbook: `docs/strategies/UI Research/operational playbook/Operational Playbook- Agent-Driven Dynasty Fantasy Football App (FastAPI + React:TypeScript, 2026).md`
- Multi-agent recommendations: `docs/strategies/UI Research/recommendations/{claude,codex,gemini}-*.md`
- State-surfacing audit (Gemini PM, + Claude on-disk delta): `docs/standups/2026-05-25-stack-audit.md`

---

## Locked by Consensus (3-of-3 agent convergence)

1. **Stack A is the direction** when frontend work eventually begins —
   Vite + React + TypeScript served by FastAPI.
2. **No day-1 batch install of the full ecosystem.** "Minimal deps until earned"
   is the operating rule. Each new runtime dependency requires an ADR.
3. **No `codex-plugin-cc` Stop-hook auto-review gate.** Manual `/codex:review`
   only. The current tmux focus-swap cadence is deliberate and is working.
4. **Repo file layout stays as-is.** `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`
   remain thin pointers to `docs/governance/`; they do not absorb the playbook's
   policy. `docs/superpowers/specs/` and `docs/strategies/` are retained. No
   renames to the playbook's `docs/specs/` + `docs/decisions/` convention. (See
   the conflict resolution in the audit delta — moving doctrine into `AGENTS.md`
   would violate operating-loop §"Authority Order": root bootstrap files must not
   duplicate the full doctrine.)
5. **Cockpit primitives + ⌘K is the first surface when we build** — the proving
   ground before Trade Lab or any genuinely stateful surface.
6. **Hey API codegen is the contract path.** FastAPI OpenAPI → TS/Zod via
   `@hey-api/openapi-ts`. Generated code is a build artifact, never hand-edited —
   the same discipline already applied to `app/data/**`.
7. **Frontend remains Phase 12 / binding governance hold.** Nothing in this
   alignment exercise changes the build order.

## Secondary Decisions

- **Ruff stays canonical for Python; Biome is frontend-only.**
  `docs/governance/03-code-hygiene-policy.md` is unchanged. Biome will be
  configured for the future frontend directory only and never touches Python
  source.
- **Branch-and-PR discipline re-affirmed.** No direct-to-main commits going
  forward. Recent direct-to-main history (Phase 19 `2ffbf13`, `ab9f085`) is
  treated as exceptional, not precedent. If a situation seems to warrant a direct
  commit, raise it first.
- **Community-skill supply-chain rule adopted.** Any community skill (`jezweb`,
  `anivar`, `capraidev`, or any other upstream) is vendored-and-pinned under
  `.claude/skills/` at a specific git SHA. No upstream references in `CLAUDE.md`
  or `.claude/` config. If we adopt a skill, we own the version.
- **`rookie_board.html` — Option (c): retain as live-draft tool.** The static
  board stays until a specific React equivalent earns its way in via ADR +
  surface spec. It is treated as the production proof of the playbook's Section 7
  escape hatch (static HTML shell + vanilla JS). Displacing it requires explicit
  ADR justification; it is not a default replacement target. (On-disk note: it is
  served by the standalone `scripts/serve_rookie_board.py`, not the main FastAPI
  app — see audit delta.)

## Deferred (door open)

- **`@total-typescript/ts-reset` — defer, not adopt at bootstrap.** Rationale:
  - Hey API + the Zod plugin already validates API responses at the SDK boundary,
    which is where ts-reset's `.json() → unknown` override would have mattered most.
  - Strict TS flags (`strict`, `noUncheckedIndexedAccess`,
    `exactOptionalPropertyTypes`, `verbatimModuleSyntax`) capture ~80% of the wins
    without the friction.
  - The remaining ~20% is `JSON.parse()` use, rare in a typed OpenAPI-backed
    codebase; where it occurs (localStorage, config), Zod parsing is the right
    answer, not a blanket `unknown`.
  - Agents handle `unknown` poorly (cast-immediately or stall). With Claude Code
    and Codex writing most of the code, that friction is a real cost here.
  - Adopt later if a bug pattern emerges that ts-reset would have caught — one-line
    change to enable. No preemptive friction tax.

---

## Governance Confirmation

- **Changes the active phase or build order**: No — frontend remains Phase 12 / HOLD.
- **Constitution "frontend comes last"**: Preserved.
- **Model inputs / market-leakage surface touched**: No — documentation only.
- **Governance docs amended**: No — `03-code-hygiene-policy.md` and the bootstrap
  layout are explicitly unchanged.
- **Code or dependencies installed**: No.
