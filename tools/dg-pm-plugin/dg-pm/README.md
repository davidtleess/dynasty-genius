# Dynasty Genius — Product Management plugin (`dg-pm`)

Product-management skills reframed for **Dynasty Genius** — a single-user, local-first ML asset-management system for David's Superflex PPR league. This is not generic PM: every skill is wired to DG's real artifacts (AGENT_SYNC, the agent ledger, the governance files, the spec/plan dirs, memory, GitHub PRs/CI, the Codex/Gemini cockpit) and bound by DG's working law — the **No-Verdict Line**, **cockpit-TDD**, and **David authorizes every action**.

## Install

From the repo root:

```
/plugin marketplace add ./tools/dg-pm-plugin
/plugin install dg-pm@dynasty-genius
```

Then invoke a skill by name, e.g. `dg-pm:write-spec`, or describe the task and Claude selects it.

## Skills

| Skill | What it does | Maps to |
|---|---|---|
| `dg-pm:write-spec` | Author a DG **spec of record** — problem (measured), design, out-of-scope, **falsification seeds (the RED matrix)**, cockpit-TDD sequence, risks | `docs/superpowers/specs/` |
| `dg-pm:roadmap-update` | Maintain **AGENT_SYNC.md** and the David-sequenced priority board — current thread, named tickets, deferred + accrual-gated wakes | `AGENT_SYNC.md` |
| `dg-pm:david-update` | Produce a **David-facing update** — session closeout, decision-needed, cockpit loop-close, risk/blocker surface | `docs/agent-ledger/`, PR/CI state |
| `dg-pm:metrics-review` | Review DG's **operational + model metrics descriptively** — capture-health, provenance drift, realized-outcome accrual, margin/divergence trends. Never a verdict. | capture-health / provenance / realized-outcome surfaces |
| `dg-pm:synthesize-research` | Synthesize **research lanes** into an evidence-graded brief with falsification seeds and a recommended cockpit action | `docs/strategies/`, research corpus |

## What makes it DG-native (baked into every skill)

- **No-Verdict Line.** Outputs are descriptive. `decision_supported=false` end-to-end. No action directives (buy/sell/hold/start/bench), no verdicts, no nominated targets in running-software output. The margin (our value vs market value) is descriptive, never a proven edge until validated.
- **Cockpit-TDD is the spine.** Content flows: Claude specs → **Codex authors the RED** → Claude implements GREEN → dual-CLEAR → **David authorizes the action**. `write-spec` produces a spec that feeds exactly this loop, falsification-first. (**dual-CLEAR = Claude + Codex**, the two binding technical lanes; **Gemini is advisory/non-binding** and never issues a CLEAR.)
- **David authorizes actions; reviewers CLEAR content.** No commit, push, merge, branch-delete, run, schedule, backup, or LaunchAgent install without David's explicit word.
- **Local-first, honest.** DG's "sources" are its own repo artifacts, not external SaaS. See [SOURCES.md](SOURCES.md).
- **Governance-bound.** The immutable football rules and the operating loop (`docs/governance/00`–`04`) win over anything here.

## Attribution

Reframed from Anthropic's **product-management** plugin in [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) (Apache License 2.0). The workflow scaffolding is derivative; the DG governance, vocabulary, No-Verdict framing, cockpit-TDD sequencing, and source wiring are original modifications. See [NOTICE](NOTICE).
