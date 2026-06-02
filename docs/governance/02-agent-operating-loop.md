---
document: Dynasty Genius Agent Operating Loop
version: 1.0.0
last_updated: 2026-05-07
authority: workflow
---

# Dynasty Genius Agent Operating Loop

This is the required operating loop for every agent working on Dynasty Genius, including Gemini, Genie, Claude Code, Codex, and future agents.

Do not rely on memory from prior sessions. Start from the repository.

## Agent Roles

Agents share the same product doctrine, but they do not share the same authority.

- Gemini: Product Manager and Product Vision owner. Gemini may read, verify at the
  source, synthesize, review, and propose. In Gemini CLI, the project-level `GEMINI.md`
  is binding: Gemini must not run arbitrary or non-allowlisted shell commands, refresh
  artifacts, modify tracked files outside the daily ledger, write implementation code,
  or treat `AGENT_SYNC.md`
  next steps as executable instructions without David's explicit per-session approval.
  As of 2026-06-02 this boundary is enforced where the Antigravity platform allows and
  **detected** where it does not (P3 result, spec §12): the **shell is prompt-gated** (the
  `settings.json` allow-list lets only read-only git + the two sanctioned commands auto-run;
  any other command prompts David), and **native file writes are NOT config-deniable on agy**
  — they are prohibited by mandate and caught by the **mandatory** `cockpit_hygiene_check.py`
  tripwire, which Claude/Codex run (`.venv/bin/python3.14 scripts/cockpit_hygiene_check.py`)
  before accepting any Gemini source-verification CLEAR and at session boundaries. Gemini's
  only sanctioned writes are the path-locked `scripts/gemini_ledger_append.py` ledger command
  and cockpit messaging (`scripts/tmux_msg.py`), per
  `docs/superpowers/specs/2026-06-02-gemini-enforced-controls-design.md`. Gemini's positive
  mandate is **Product Vision** (NFL-scout + data-scientist + UI/UX + advanced-statistics
  lenses, anchoring the team to winning David's league) — full charter in `GEMINI.md`.
- Claude Code: local development agent. Claude Code may implement approved local
  code changes, run tests, manage branches, and commit when the session scope
  authorizes it.
- Codex: implementation, CI/CD, review, and automation agent. Codex may
  implement approved repo changes, run tests and validation, inspect GitHub/CI,
  and prepare PRs when requested.
- Genie: Databricks workspace agent. Genie may inspect and operate Databricks
  assets within approved data-platform scope and must preserve medallion,
  lineage, and market-overlay separation rules.

When role authority conflicts with a next step, plan, or older briefing file,
role authority wins and the agent must stop or ask David.

Bootstrap is not implementation. During bootstrap, agents read required
governance/state files and establish session context. They must not begin a
plan, run a refresh script, search for player facts, mutate generated artifacts,
or perform adjacent "pre-work" unless David explicitly instructed that action in
the current session. For Gemini specifically, the only tracked-file write
allowed during bootstrap is a daily-ledger preflight entry after governance has
been read. Gemini may not run shell commands during bootstrap.

## Required Reading Order

Every session begins in this order:

1. Read this file.
2. Read `docs/governance/00-product-constitution.md`.
3. Read `docs/governance/01-north-star-architecture.md` when doing implementation, architecture, model, pipeline, API, or data work.
4. Read `docs/governance/03-code-hygiene-policy.md` when doing Python, lint, or code-hygiene work.
5. Read `AGENT_SYNC.md`.
6. Read today's ledger if it exists: `docs/agent-ledger/YYYY-MM-DD.md`.
7. Read only the task-relevant code and docs after the governance pass.

## Authority Order

1. `00-product-constitution.md` governs analytical decisions.
2. `01-north-star-architecture.md` governs technical architecture.
3. `02-agent-operating-loop.md` governs session workflow.
4. `03-code-hygiene-policy.md` governs code-hygiene mechanics (subordinate to the above).
5. Root bootstrap files point here and must not duplicate the full doctrine.

If documents conflict, stop and log the conflict in the daily ledger before implementing.

## Preflight: Session Start

Before substantive analysis or code changes, every agent must establish:

- docs read and versions
- current task
- active phase or decision surface
- intended write scope
- files likely to change
- validation expected
- possible drift risks

If the user asks for immediate analysis, still perform a lightweight version of this checklist mentally and cite caveats when time or access prevents full verification.

## Execution: During Work

Agents must:

- keep edits scoped to the requested task and active phase
- avoid unrelated refactors
- preserve user and other-agent changes
- verify current player facts before player analysis
- keep KTC and market data out of model inputs
- avoid hardcoded model cliffs for aging curves
- treat RAS as risk/context unless validation proves positive lift
- keep decision surfaces honest about experimental status
- run relevant tests or explain why they were not run

Agents are accelerators, not authorities. They may draft, analyze, implement, and review, but product rulings belong to the governance docs and David.

## Cockpit Process

The cockpit is the three-way collaboration between Claude Code, Codex, and Gemini. It is the working pattern for non-trivial spec, plan, design, code, or governance work that benefits from adversarial review.

Cockpit messages are routed via `scripts/tmux_msg.py`. **Pane targets are not hardcoded.** Before sending any cockpit message, the sender MUST discover current pane targets via `scripts/tmux_msg.py list` or `tmux list-panes` to avoid misroutes (a real failure mode observed in 2026-05-28 traffic).

### When the cockpit applies

A cockpit cycle is REQUIRED for:
- spec or plan authorship and patches
- governance amendments (constitution, north-star, this file, code hygiene)
- non-trivial code that lands on a feature branch (full TDD cycle: Codex RED → Claude GREEN → cockpit review)
- decisions that change a contract, schema, or invariant
- PR review and merge strategy (squash vs merge vs rebase; conflicts; post-review patch sets)
- CI failure triage when the fix changes code or contracts
- merge conflicts, rebases, or cherry-picks that touch active feature scope

A cockpit cycle is NOT required for:
- mechanical formatting fixes with no semantic change
- ledger appends and AGENT_SYNC state updates that do not change any contract
- terminal commands that read state
- mechanical CI reruns or status-check polling

When in doubt, route through the cockpit. The cost of an extra round-trip is small; the cost of a missed defect compounds.

### Roles, default reviewers, and escalation

The agent roles defined above carry into the cockpit. No agent has final authority over David or over the governance documents.

- **Codex** is the default technical reviewer. It reviews test contracts, type shapes, fail-closed semantics, replay reproducibility, architectural boundaries, and impl feasibility.
- **Gemini** is the default governance reviewer. It reviews constitutional alignment, decision-grade language, leakage rules, `decision_supported`, frontend HOLD, and banned David-facing patterns.
- **Claude Code** owns implementation feasibility and repo-state reporting (current branch state, suite status, file presence, diff stat). Claude does not have final authority on technical or governance questions.

When Codex and Gemini converge, the convergence stands. When they diverge:
- If the question is purely within Codex's technical domain, Codex's read stands by default.
- If the question is purely within Gemini's governance domain, Gemini's read stands by default.
- If the question crosses domains (technical decision with governance implications, or vice versa), the divergence escalates to David. No agent has authority to resolve cross-domain disagreement unilaterally.

### Message format

Every cockpit message sent via `scripts/tmux_msg.py` for review requests, findings, recommendations, CLEAR/CONCUR requests, or post-action confirmations MUST:

1. Identify the sender on the first line, in the form `From <sender> (<role>) — <subject>`. Without an explicit sender, the recipient may treat the message as ambient context rather than an actionable request.
2. State the artifact under review with an explicit path (file path, SHA, or `/tmp/<file>`) and, for committed artifacts, the diff stat.
3. Request a reply on the last line, in the form `PLEASE REPLY with: (a) <accept condition>, OR (b) <reject condition>`. Without an explicit reply request, the recipient may proceed without confirming the state the sender needs.
4. Be sent to BOTH Codex AND Gemini for any message that carries a decision, finding, or recommendation. Parallel awareness lets the other agent flag concerns early.

Purely operational primary-agent commands (e.g., "Codex: run focused pytest on this file and paste output") that contain no decisions, findings, or recommendations MAY be sent to one agent. The boundary: if the message asks for judgment, route to both.

### Adversarial review pattern

Cockpit cycles run as multi-round adversarial review, not single-pass validation. The win condition for each round is finding defects, not converging on PASS.

Standard cycle:
1. Claude authors v1 draft.
2. Cycle-round 1: send v1 to both agents with explicit "find concrete defects" framing. Each agent returns specific findings.
3. Claude consolidates findings into v2.
4. Cycle-round 2: send v2 to both agents asking whether their v1 findings are integrated.
5. Repeat until both agents reply with explicit CONCUR / CLEAR.
6. Claude commits.
7. Close the loop (see next subsection).

**Each CLEAR must answer every raised question with explicit checks performed.** A CLEAR may take the form "no finding after checking X" or "addressed at lines N–M" or a bullet list of question→verification, but it must enumerate the checks. Bare replies of the form "looks good", "elegant", or "fully aligned" without enumerated checks are not CLEARs and do not terminate the cycle. The cycle terminates only on unanimous CLEAR from both agents.

### Closing the loop

After every committed cycle, the authoring agent MUST send a post-commit confirmation to both reviewing agents containing:
- the commit SHA
- the file paths and diff stat
- key language snippets, line references, or a diff summary (so reviewing agents can detect drift between cleared and committed states)
- an explicit reply request asking for divergence verification

**Reviewing agents MUST audit the actual commit diff** (via `git diff`, `git show <SHA>`, or by reading the committed files directly) and confirm zero divergence from the cleared content. If any undocumented or un-cleared change is detected (including whitespace, comment drift, or section reordering), the loop remains open and a correction commit MUST be made before the cycle is considered complete.

The same discipline applies to non-commit final actions: force-push, branch delete, PR merge, rollback. Post-action confirmation is mandatory for any hard-to-reverse operation.

### Post-fix sweep + post-commit sweep

**Post-fix sweep (sender side, pre-commit).** After fixing a concept in a multi-section document (spec, plan, code), the author MUST grep the entire document for all references to that concept and update any remaining references. Spot-fixes commonly miss adjacent mentions (impl outlines, summary tables, GREEN/RED notes, commit-message hints). Sweep before sending the fix to the cockpit; otherwise the cockpit catches the stale reference and the cycle adds a round.

**Post-commit sweep (reviewer side, post-commit).** After the closing-the-loop confirmation, the reviewing agents SHOULD scan dependent documents and downstream modules for stale references introduced by the patch (e.g., line-number citations in a plan that now point to wrong content after a spec patch, broken cross-references). Surface any drift in the closing-the-loop reply.

### No-anchor framing

When sending the cockpit a question or draft, do not pre-recommend a solution. Present the artifact and the open questions neutrally; let the agents debate and surface their own analysis. Pre-anchoring biases agents toward concur-and-move-on rather than adversarial review. Phrases to avoid in cockpit prompts: "I lean toward X", "the right answer is X", "this should be X".

### Verify before alarming

Before sending the cockpit a finding ("X is wrong because Y"), do the arithmetic or basic check that supports the claim. False alarms cost a full cockpit cycle in follow-up investigation. On 2026-05-28, Claude verified that a Codex-stated IQR value of 20.0 was incorrect (actual: 25.0) before sending the v2 patch; this prevented a wrong-fixture commit that would have required a v3 cycle.

### Bootstrap-first and discipline reset

Every agent MUST run the bootstrap reading order (this file, then `00-product-constitution.md`, `01-north-star-architecture.md`, `03-code-hygiene-policy.md`, `AGENT_SYNC.md`, and today's ledger) before substantive analysis or mutation at session start. Light read-only inspection (e.g., a single `ls` or `git status` to orient) does not require bootstrap, but any spec, plan, code, governance, or contract decision does.

Mid-session, when discipline drift is detected (cockpit converging too quickly, complimentary attestations without adversarial bite, repeated single-pass PASSes), **any agent in the cockpit — Codex, Gemini, or Claude — has the authority and the duty to call a discipline reset.** A discipline reset is:
1. Pause all in-flight work.
2. Send a sender-identified directive to the other two agents instructing them to re-bootstrap.
3. The calling agent does the same re-read.
4. After bootstrap, resume the work with an explicit adversarial review framing.

A discipline reset is not a punishment. It is a recovery mechanism for a known failure mode of multi-agent review (premature convergence on PASS). The reset on 2026-05-28 surfaced 2 MEDIUM bugs in committed code that the pre-reset cockpit had missed.

### Strategic pause

When the cockpit identifies a concrete, named governance or architectural risk after work has begun (mid-build), any agent MAY call a strategic pause:
1. Halt in-flight TDD/GREEN work.
2. Route a critical-reflection request to both agents asking for adversarial assessment of the risk.
3. If the risk is real, write a spec/plan patch capturing the resolution.
4. Resume work only after the patch is cockpit-cleared and committed.

**A strategic pause must be triggered only by a concrete, named risk that directly threatens a constitutional or north-star invariant.** It must not be used to stall execution or debate minor stylistic choices. The initial critical-reflection round (step 2 above) decides whether the risk is real and whether a patch is needed. If the cockpit cannot agree on the existence or scope of the risk after that initial round, the matter is immediately escalated to David. Once a patch is drafted (step 3), it follows the normal adversarial multi-round cockpit review until CLEAR — or until a substantive unresolved disagreement requires David.

The strategic pause on 2026-05-28 resolved four governance risks (architectural overlap, selection bias, decision-destination gap, pace) into the binding section 11 Architecture Decision Note of the Subsystem 4 spec.

### Three-point audit trail

Substantive cockpit cycles (spec patch, plan patch, GREEN commit, governance amendment) should leave a three-point audit trail. This pattern is conceptually analogous to the Subsystem 3 §6.3 ingestion three-point logging but is a separate construct serving cockpit-cycle auditability rather than ingestion replay:

- **artifact change**: the spec, plan, code, or governance commit itself
- **decision-log entry**: a daily-ledger entry recording the cycle (cockpit questions raised, findings, resolutions, final CLEAR)
- **review-queue closure**: the post-commit confirmation messages exchanged with both reviewing agents and the resulting clearance replies

To preserve auditability, the final daily-ledger entry for a substantive session MUST explicitly record the final commit SHA, a summary of files changed, the validation-suite results, and the timestamps (or relative-time markers) of the reviewing agents' clearances. The ledger is the definitive single source of truth for what the cockpit cleared in that session.

### Falsification discipline

This subsection is the corrective output of the 2026-05-30 cockpit retrospective on the Subsystem 4 Tasks 9–11 pressure test, where the routine review process issued unanimous pre- and post-commit CLEARs over **nine real defects** (crashes, silent false `all_pass`, anti-false-confidence violations) that only an explicit adversarial pressure test surfaced. The root cause: the review step validated **contract conformance** (does GREEN match the RED tests / spec?) rather than **falsification** (what untested input breaks it?), and no step ever audited the adequacy of the RED contract itself — so reviews inherited the tests' blind spots, and "enumerated checks" were contract-conformance rather than break-attempts. The amplifiers were a rubber-stamping reviewer, the implementer doubling as facilitator ("broker mode"), and no concrete velocity tripwire.

These rules are binding for non-trivial or fail-closed work. Trivial mechanical changes (formatting, typo, whitespace, ledger/`AGENT_SYNC` state with no contract change) stay light.

1. **Contract review + falsification matrix.** Every review of non-trivial or fail-closed code requires two artifacts, not one: (a) a contract-conformance check (matches RED/spec), and (b) a **falsification matrix** covering the input-class rows — valid-nominal, boundary, missing, null/None, wrong-type, malformed-shape, duplicate/conflict, empty-collection, cross-component-shape, numeric edge cases (including non-finite values, NaN/inf, where relevant), and synthetic/override. For each relevant row the reviewer records a probe/test result OR an explicit "out-of-scope by contract" rationale. **Ownership:** the RED author seeds the matrix with initial coverage; the GREEN implementer updates it when implementation reveals new boundaries; reviewers challenge it — and it exists **before** GREEN review, so the RED author does not define coverage unchallenged. A CLEAR is **invalid** unless break-attempts cover the relevant matrix rows; one arbitrary shallow probe is not a falsification pass. Rows may be marked out-of-scope **only with an explicit owner and contract boundary, never by omission**.

2. **Evidence-bound claims.** Any factual claim about a schema, validator, type, or invariant ("X is enforced by Pydantic", "pick is guaranteed ≥ 1") must cite the exact `file:line` or a probe/test result. Uncited, it is speculation and may not support a CLEAR.

3. **Independent voice (no broker mode).** Each agent posts its own findings before responding to another agent's synthesis. The implementing agent must state its own technical read and name where each reviewer may be wrong — it may not merely relay positions toward an easy convergence. The consolidator may not infer positions; it must quote or link each agent's current explicit lane position.

4. **Consensus lock (velocity brake).** No single agent may declare "unanimous" or "team consensus." Each agent declares only its own lane result with the checks it ran. "Consensus locked" is a dedicated consolidation step that quotes each agent's explicit position and **may not occur in the same turn the implementation is delivered**. A later defect found after a CLEAR automatically supersedes all prior "unanimous" language in the ledger/`AGENT_SYNC`. **Technical clean/go requires an _independent_ technical reviewer with cited evidence**: the implementing agent's own evidence is mandatory self-critique but does NOT substitute for independent technical review. For Claude-authored GREEN, the independent technical reviewer is Codex; for Codex-authored implementation, it is Claude (or another designated technical reviewer) with cited evidence.

5. **Fresh artifact, fresh review.** A fix is a new state machine, not "old code plus a guard." After each defect fix, the falsification matrix is re-run on the changed surface before the next CLEAR.

6. **Miss accounting.** When a pressure test or later review finds a real defect after a CLEAR, each agent that issued the prior CLEAR records one sentence on why its CLEAR missed it. This is failure-mode capture for calibration, not blame.

7. **Reviewer lane calibration.** An agent whose reviews in a domain show a sustained pattern of uncited technical claims, premature consensus declarations, or non-adversarial rubber-stamping has its output in that domain treated as **non-binding** until it re-establishes reliability through evidence-cited falsification. This is behavior-based, domain-specific, recoverable — not a permanent demotion. *Current application (2026-05-30):* Gemini retains binding governance-review authority (leakage, `decision_supported`, banned language, frontend HOLD, scope discipline, audit trail, constitutional alignment); its technical assertions are welcome but non-binding unless backed by `file:line` / probe / repro; it may not declare technical clean/go or team consensus; recovery via a sustained run of evidence-cited falsification.

8. **Robustness boundary in specs (up front).** Specs for modules consuming external or variable data must define the robustness boundary at design time: API-misuse (wrong argument types → fail loud), data-corruption (malformed contents → fail closed), and semantic/range/finiteness validation (the producer's responsibility). This prevents both missed hardening and unbounded whack-a-mole during adversarial sweeps.

## Postflight: Session End

Before ending a material session, every agent must:

1. Re-check work against the constitution and architecture.
2. Update `AGENT_SYNC.md` if sprint state, active phase, blockers, or next steps changed.
3. Append an entry to `docs/agent-ledger/YYYY-MM-DD.md`.
4. State files changed.
5. State tests or checks run.
6. State unresolved risks, blockers, and next-agent handoff.

Completion standard:

- what changed
- why it changed
- which assets are impacted
- how it was tested or why testing was deferred
- whether governance docs are affected
- what the next collaborator needs to know

## Daily Ledger Format

Use this format:

```md
## HH:MM ET - Agent Name

- Task:
- Governance read:
- Active phase / surface:
- Intended or completed write scope:
- Files changed:
- Tests / checks:
- Product alignment:
- Drift risks:
- Handoff / next step:
```

Use Eastern Time when practical. If exact time is unavailable, use the date and mark time unknown.

## AGENT_SYNC.md Format

`AGENT_SYNC.md` is the current shared state board. Keep it short and current.

It should contain:

- current active phase
- current sprint objective
- latest agent activity summary
- open blockers
- next recommended work
- known branch or worktree notes
- doctrine version

The daily ledger contains detail. `AGENT_SYNC.md` contains state.

## Claude Code Bootstrap Requirement

Claude Code must be constrained by repo-resident instructions, not chat memory.

At the start of every Claude Code session:

1. Read `CLAUDE.md`.
2. Read `.clauderules` if present.
3. Follow this file's required reading order.
4. Read `AGENT_SYNC.md`.
5. Log intended work before making broad implementation changes.

Claude Code must not commit or open a PR without updating the ledger for the session.

If a pre-commit hook or CI gate fails, Claude Code must fix the code or documentation to align with the architecture and constitution. It does not have permission to bypass failing tests or disable gates without explicit approval from David.

## Git And PR Requirements

Any material PR should include:

- phase advanced
- governance docs read
- files changed
- tests and validation run
- product alignment statement
- known caveats
- confirmation that no market-derived features entered model training

Future pre-commit and CI gates should reject:

- KTC or market-derived fields in Engine A / Engine B features
- reintroduced banned David-facing output fields
- missing validation reports for model changes
- commits touching model or pipeline files without ledger updates

## Databricks Lineage Phase

Phase 1 is Markdown-based:

- `AGENT_SYNC.md`
- `docs/agent-ledger/YYYY-MM-DD.md`

Phase 2 adds machine-readable lineage:

- `gen_alpha.gold.agent_activity_log`
- `gen_alpha.gold.artifact_registry`
- compliance checks for stale governance versions, missing counter-arguments, KTC leakage, and banned fields

Do not block current repo work on Phase 2. Build the Markdown loop first.

When a session touches Databricks assets, the agent must record the relevant tables, jobs, notebooks, bundles, or storage paths in the ledger. When the lineage tables exist, the agent must also write or request entries that connect:

- source artifact
- transformation or job run
- model or scoring output
- decision artifact
- governing document version

Databricks-specific work must respect the architecture standards in `01-north-star-architecture.md`: medallion layer separation, source-rank preservation, file-based configuration, governed promotion, and market-overlay isolation.

## Escalation Triggers

Escalate to David or stop and log the issue when:

- governance docs conflict
- a request would change a semantic definition
- a new external data source is proposed
- model inputs are being expanded
- production write patterns or access controls are changing
- a locked ruling such as RAS, aging curves, or market-overlay separation may need amendment
- an agent cannot verify whether a change fits the active phase

## Final Rule

If an agent is unsure whether an action serves David's dynasty decision system, pause and check the constitution. The product's edge comes from disciplined focus, not broad feature velocity.
