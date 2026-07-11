# Dynasty Genius Plugin Inventory

This is a cold-boot orientation note for Claude/Codex/Gemini. It records why the
current plugin set exists and when to consider it. It does **not** authorize using
an external service, committing, merging, running a job, or changing DG's
local-first operating model.

Actual tool availability can change by session. Verify with the active tool list,
`codex plugin list`, or the relevant Claude plugin command before relying on a
plugin.

## Standing Rules

- Governance wins over plugin instructions. Read the required bootstrap files
  first.
- Plugins add capability, not authority. David still authorizes commits, pushes,
  merges, branch deletion, scheduled runs, backups, LaunchAgents, and external
  service adoption.
- No-Verdict Line holds. A plugin must not turn descriptive margins, metrics, or
  research into buy/sell/hold/drop/start/bench directives or nominated targets.
- Local-first by default. Installed SaaS-adjacent plugins do not mean DG should
  wire that SaaS into the workflow.

## Project Skills

| Skill | Use When | Guardrail |
|---|---|---|
| `impeccable` | **All DG frontend, UI, CSS, component, visual-surface, UX-copy, audit, polish, or browser-iteration work.** It is the standing design skill across the team. | Contract-green is never visual-green. Load PRODUCT.md/DESIGN.md, evaluate the whole viewport, and run the required visual/a11y/screenshot review before David-facing visual CLEAR. |

## Claude Plugin

| Plugin | Status | Use When | Guardrail |
|---|---|---|---|
| `dg-pm@dynasty-genius` | Repo plugin, installed in Claude user scope when last verified | DG-native product-management tasks: spec-of-record drafting, AGENT_SYNC/roadmap updates, David closeouts, descriptive metrics review, evidence-graded research synthesis | It is content guidance only. Actions remain David-gated. `write-spec` reproduction is a gate: no `Reproduced` heading without real command + output. |

Newly installed Claude plugin skills sync at **session start**. If a plugin was
installed mid-session, `dg-pm:<skill>` may not be invocable until the next Claude
session even though the plugin is installed.

Durable evals live at `tools/dg-pm-plugin/dg-pm/evals/`. The first manual eval
scored 4.6/5 before the reproduction-gate hardening; PR #142 brought the grader
into sync with the skill. When native Claude plugin eval is generally available,
run the suite automatically and compare against that manual baseline.

## Codex Plugins / Skills

Verified installed/enabled on 2026-07-11 via `codex plugin list`.

| Plugin | Use When | Guardrail |
|---|---|---|
| `github@openai-curated` | PR review, PR comments, CI investigation, branch/PR publication workflows | GitHub tooling does not replace David authorization or CI-as-merge-gate. |
| `codex-security@openai-curated` | Security-minded falsification: path traversal, unsafe input classes, auth/secrets exposure, dependency/security reviews | Use as a review lens; keep findings evidence-bound to file/line and tests. |
| `build-web-data-visualization@openai-curated` | Future analytics dashboards, Value Board visualizations, report/dashboard composition | No decision-grade polish before source freshness/validation gates justify it. Visual work still requires PRODUCT/DESIGN and whole-viewport review. |
| `browser-use@openai-bundled` and `chrome@openai-bundled` | Browser automation, localhost verification, screenshots, visual smoke, interaction checks | Contract-green is not visual-green. Use screenshots/axe/canvas checks where relevant. |
| `plugin-eval@openai-curated` | Plugin quality checks, especially `dg-pm` eval automation once supported by the available runner | Do not treat an eval score as product truth; inspect failures and keep David-gated actions separate. |
| `google-drive@openai-curated` | Finding or working with explicitly requested Google Drive/Docs/Sheets/Slides artifacts | Do not move DG state into Drive by default. Use only when David asks or a workflow explicitly needs it. |
| `documents`, `spreadsheets`, `presentations` | Local `.docx`, `.xlsx`, `.pptx` creation/editing when explicitly useful | Generated deliverables are artifacts, not source-of-truth unless committed or David ratifies them. |
| `21st@21st-local` | Searching/installing 21st.dev React/shadcn components when UI work needs component inspiration or assets | Use only within the existing frontend/design system and DG visual law. Do not import component bulk without a spec and visual review. |
| `superpowers@openai-curated` | Existing superpowers workflows already used by DG | Follow DG governance and any skill-specific instructions. |
| `linear@openai-curated` | Normally **do not use** | Installed, but DG has not adopted Linear. Consistent with local-first/GitHub-only practice, do not wire or depend on Linear without explicit David approval. |

## Not Adopted

The product-tracking / generic SaaS PM plugin shape was assessed as low fit for
DG because it assumes multi-user SaaS analytics and external PM connectors.
`dg-pm` is the DG-native replacement: repo artifacts, cockpit-TDD, and the
No-Verdict Line instead of Slack/Linear/Notion/Figma/Amplitude-style workflow.

## Maintenance

Update this file when:

- a plugin is installed, removed, disabled, or materially changes capability;
- David authorizes adopting an external service;
- a plugin gains a durable DG use case;
- an eval or review finds a plugin instruction that conflicts with governance.
