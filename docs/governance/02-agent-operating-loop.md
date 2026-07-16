---
document: Dynasty Genius Agent Operating Loop
version: 1.3.0
last_updated: 2026-07-16
authority: workflow
---

# Dynasty Genius Agent Operating Loop

This is the required operating loop for every agent working on Dynasty Genius, including Gemini, Genie, Claude Code, Codex, and future agents.

Do not rely on memory from prior sessions. Start from the repository.

## Agent Roles

Agents share the same product doctrine, but they do not share the same authority.

- Gemini: **Operations & Telemetry agent** (David-directed re-role, 2026-07-16; ratified 2026-07-16). Gemini's affirmative lane is the system's operational truth surface: capture-health and status-marker reads, scheduled-job monitoring (LaunchAgent fires, exit states, error logs), artifact freshness/staleness watches, metric and threshold tracking, and descriptive telemetry summaries to the cockpit and the spokesperson. Gemini **does not sit on judgment or verdict panels**: it issues no review verdicts, framings, CLEARs, governance opinions as gates, or product/football rulings. Its telemetry reports are **fact-bearing, not action-bearing**. The platform write-boundary is unchanged: in Gemini CLI the project-level `GEMINI.md` is binding; the **shell is prompt-gated** (the `settings.json` allow-list lets only read-only git + the two sanctioned commands auto-run; any other command prompts David); **native file writes are NOT config-deniable on agy** — they are prohibited by mandate and caught by the **mandatory** `cockpit_hygiene_check.py` tripwire, which Claude/Codex run at session boundaries and before relying on a Gemini telemetry report for any decision; Gemini's only sanctioned writes are the path-locked `scripts/gemini_ledger_append.py` ledger command and cockpit messaging (`scripts/tmux_msg.py`), per `docs/superpowers/specs/2026-06-02-gemini-enforced-controls-design.md`, with the enforcement-script attribution updates of the 2026-07-16 re-role amendment (Amendment E). Full charter in `GEMINI.md`.
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
5. Read the design foundation — root `PRODUCT.md` + `DESIGN.md` — when doing frontend, UI, CSS, component, or any visual-surface work. It is the ratified visual-design source of record (honesty is the substrate; fantasy-native legibility is the aesthetic; the surface must never look like a developer diagnostics console in a fantasy skin). Claude Code loads it via the `impeccable` skill; Codex, Gemini, and other agents read the two files directly. **Contract-green is never a visual GREEN** — the whole viewport (not the diff) is the review unit, and an independent, unanchored fresh-agent visual audit (mid-scroll captures mandatory) is the standing pre-David gate.
6. Read `AGENT_SYNC.md`.
7. Read today's ledger if it exists: `docs/agent-ledger/YYYY-MM-DD.md`.
8. Read only the task-relevant code and docs after the governance pass.

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
- keep harness-local enablement local: active tool/hook configs such as `.codex/hooks.json`
  or `.cursor/hooks.json` are per-developer state and must never be tracked. The
  repo may vendor the underlying scripts; it does not silently enable them for every
  fresh clone.
- verify current player facts before player analysis
- keep KTC and market data out of model inputs
- avoid hardcoded model cliffs for aging curves
- treat RAS as risk/context unless validation proves positive lift
- keep decision surfaces honest about experimental status
- evaluate every build through the **compounding-product lens** (see Cockpit Process → Compounding-product lens): daily-login value, refresh-when-fresh-data-adds-value, and value that compounds via accumulated benchmarks — prefer capturing-and-accumulating over overwriting `_latest`, and never let "fresh/compounding" license overclaim
- run relevant tests or explain why they were not run

Agents are accelerators, not authorities. They may draft, analyze, implement, and review, but product rulings belong to the governance docs and David.

## Cockpit Process

The cockpit is the collaboration between Claude Code, Codex, and Gemini. The **binding review lanes are Claude Code and Codex** (implementing agent + independent reviewer); Gemini is the Operations & Telemetry seat (ratified 2026-07-16) — telemetry facts and awareness copies, no judgment lane. The cockpit is the working pattern for non-trivial spec, plan, design, code, or governance work that benefits from adversarial review.

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

### Strategy/UX framing first (feature/design tasks)

Open a feature or design task — anything shipping a new David-facing surface, output, artifact, scheduled report, or decision-adjacent contract — with a **framing pass BEFORE the RED is authored**. Task order: **Claude authors the framing artifact → Codex adversarially challenges it in writing → Claude issues a written disposition answering every challenge item (accept/reject with reasons, per the §Falsification #3 no-broker duty) → any unresolved product/framing divergence escalates to David → only then does the RED open.** The framing artifact answers the same four questions as before: (1) the concrete user situation — the real dynasty manager's moment this surface serves; (2) mislead/nudge risks — verdict-by-the-back-door; (3) candidate falsification seeds — specific behaviors and mathematical boundary/failure cases (empty pool, a range that crosses zero, stale input) for the RED; (4) an overclaim check against the No-Verdict Line. **Named cost:** framing author and GREEN implementer are now the same lane, so the Codex challenge round and the author disposition are MANDATORY — a framing without a written challenge AND a written disposition does not open the RED. For design-shaped tasks the Studio counterpart (outside governance, David-mediated) remains an optional independent perspective. Gemini contributes the operational-reality slice on request (data freshness, capture coverage, cadence constraints) as telemetry facts.

This is problem-space framing, not solution selection: the framing surfaces risks and testable falsification seeds; Codex owns RED authorship and Claude/Codex own technical scope. Default to including the framing even for producer/CLI tasks (the Roster Capacity producer T4, 2026-06-28, got a framing pass that surfaced the stale-artifact freshness guard); skip only for purely mechanical work with no new David-facing surface, and say so. Claude and Codex still hold their own positions as principals; a framing is raw input for David, never a lock.

### Material visual-direction changes route through framing (existing surfaces)

The framing-first rule above triggers on a *new* David-facing surface. It also applies to a **material visual-direction change** to an existing surface — a change to what David notices first. Such a change must route through a cockpit framing pass + a pre-code composition artifact (the `DESIGN.md` shape-before-code gate) before implementation.

A change is material when it alters any of:

- the first-viewport story or the 5-second answer
- information architecture, or row/section order
- section naming or surface labeling
- the hero / emphasis model (what is visually foregrounded)
- lane semantics (model/market framing, lane symmetry, what a lane means)
- typography scale or weight in a primary content region
- row or layout density, or row format (e.g. swapping 32px tabular rows for cards, changing the desktop two-pane split, or the row-height scale)
- component substitution in a primary content region
- motion that changes what is foregrounded, or its timing/character
- responsive breakpoint or mobile composition
- color-palette, position-hue, or accent mappings (anything touching the model-blue / market-amber lane axis or the position-hue families)
- David-facing value-band lexicon or tier/grade thresholds (new labels or changed model-grade thresholds alter the manager-voice prose and must not be solo-drifted)

**Preservation clause.** An otherwise-mechanical change is STILL material if it alters the existing 5-second answer, focal hierarchy, or first-viewport order / lane symmetry.

A change is **not** material — and does not require a framing pass — only when it is mechanical AND preserves the 5-second answer and focal hierarchy: a copy typo fix (no lexicon/tier/label change), an accessibility-attribute fix that changes no visible composition, a token-compliant sub-pixel alignment that changes no density/hierarchy/color mapping, or a like-for-like refactor with zero visible change. When unsure, route it — the cost of a framing round-trip is small; a solo-drifted visual direction is exactly the failure the design foundation exists to prevent. This is a bounded extension of the framing-first mechanism, not a new authority.

### Roles, default reviewers, and escalation

The agent roles defined above carry into the cockpit. No agent has final authority over David or over the governance documents.

- **Codex** is the default technical reviewer. It reviews test contracts, type shapes, fail-closed semantics, replay reproducibility, architectural boundaries, and impl feasibility.
- **Gemini** holds no review lane. Governance/constitutional alignment review is carried by BOTH binding lanes: the implementing agent self-checks against 00/01/02/03 and the independent reviewer explicitly enumerates constitutional-alignment checks alongside technical ones. Gemini contributes operational ground truth on request (marker states, job history, freshness facts) — inputs, not opinions.
- **Claude Code** owns implementation feasibility and repo-state reporting (current branch state, suite status, file presence, diff stat). Claude does not have final authority on technical or governance questions.

When lanes diverge: the **independent (non-implementing) reviewer's** technical read stands by default over the implementer's — for Claude-authored GREEN that reviewer is Codex; for Codex-authored implementation it is Claude (§Falsification #4). **An implementer never overrules its own independent reviewer by default**; unresolved implementer/reviewer divergence escalates to David. Governance/constitutional divergence always escalates to David — no agent resolves it unilaterally.

### Message format

Every cockpit message sent via `scripts/tmux_msg.py` for review requests, findings, recommendations, CLEAR/CONCUR requests, or post-action confirmations MUST:

1. Identify the sender on the first line, in the form `From <sender> (<role>) — <subject>`. Without an explicit sender, the recipient may treat the message as ambient context rather than an actionable request.
2. State the artifact under review with an explicit path (file path, SHA, or `/tmp/<file>`) and, for committed artifacts, the diff stat.
3. Request a reply on the last line, in the form `PLEASE REPLY with: (a) <accept condition>, OR (b) <reject condition>`. Without an explicit reply request, the recipient may proceed without confirming the state the sender needs. Awareness copies are exempt: a message whose first line carries `awareness copy — no reply requested` requires no reply-request last line and expects no reply.
4. Judgment-bearing messages (decisions, findings, recommendations, review requests) route to the **binding lanes** — the implementing agent and the independent reviewer. **Gemini receives a copy for operational awareness and audit continuity only: no reply is requested and none is binding** (a five-element OPS ALARM per §Falsification #7 excepted). Telemetry requests route to Gemini under the ops prompting contract (§Falsification #7). The boundary stands: if the message asks Gemini for judgment, the sender has violated the routing rule.

Purely operational primary-agent commands (e.g., "Codex: run focused pytest on this file and paste output") that contain no decisions, findings, or recommendations MAY be sent to one agent.

### Adversarial review pattern

Cockpit cycles run as multi-round adversarial review, not single-pass validation. The win condition for each round is finding defects, not converging on PASS.

Standard cycle (binding participants = the implementing agent + the independent reviewer; Gemini receives awareness copies — no CLEAR is requested from or issued by it):
1. The implementing agent authors the v1 draft.
2. Cycle-round 1: send v1 to the independent reviewer with explicit "find concrete defects" framing; it returns specific findings.
3. The implementer consolidates findings into v2 (with its own written disposition per finding).
4. Cycle-round 2: send v2 to the independent reviewer asking whether the round-1 findings are integrated.
5. Repeat until the independent reviewer replies with an explicit CLEAR.
6. The implementer commits (on David's word where required).
7. Close the loop (see next subsection).

**Each CLEAR must answer every raised question with explicit checks performed.** A CLEAR may take the form "no finding after checking X" or "addressed at lines N–M" or a bullet list of question→verification, but it must enumerate the checks. Bare replies of the form "looks good", "elegant", or "fully aligned" without enumerated checks are not CLEARs and do not terminate the cycle. The cycle terminates only on the **independent reviewer's explicit CLEAR** — the implementer's own evidence is mandatory self-critique but never substitutes for it (§Falsification #4).

### Closing the loop

After every committed cycle, the authoring agent MUST send a post-commit confirmation to the independent reviewer (Gemini receives the confirmation for awareness/audit) containing:
- the commit SHA
- the file paths and diff stat
- key language snippets, line references, or a diff summary (so reviewing agents can detect drift between cleared and committed states)
- an explicit reply request asking for divergence verification

**The independent reviewer MUST audit the actual commit diff** (via `git diff`, `git show <SHA>`, or by reading the committed files directly) and confirm zero divergence from the cleared content. If any undocumented or un-cleared change is detected (including whitespace, comment drift, or section reordering), the loop remains open and a correction commit MUST be made before the cycle is considered complete.

The same discipline applies to non-commit final actions: force-push, branch delete, PR merge, rollback. Post-action confirmation is mandatory for any hard-to-reverse operation.

### Post-fix sweep + post-commit sweep

**Post-fix sweep (sender side, pre-commit).** After fixing a concept in a multi-section document (spec, plan, code), the author MUST grep the entire document for all references to that concept and update any remaining references. Spot-fixes commonly miss adjacent mentions (impl outlines, summary tables, GREEN/RED notes, commit-message hints). Sweep before sending the fix to the cockpit; otherwise the cockpit catches the stale reference and the cycle adds a round.

**Post-commit sweep (reviewer side, post-commit).** After the closing-the-loop confirmation, the independent reviewer SHOULD scan dependent documents and downstream modules for stale references introduced by the patch (e.g., line-number citations in a plan that now point to wrong content after a spec patch, broken cross-references). Surface any drift in the closing-the-loop reply.

### No-anchor framing

When sending the cockpit a question or draft, do not pre-recommend a solution. Present the artifact and the open questions neutrally; let the agents debate and surface their own analysis. Pre-anchoring biases agents toward concur-and-move-on rather than adversarial review. Phrases to avoid in cockpit prompts: "I lean toward X", "the right answer is X", "this should be X".

### Verify before alarming

Before sending the cockpit a finding ("X is wrong because Y"), do the arithmetic or basic check that supports the claim. False alarms cost a full cockpit cycle in follow-up investigation. On 2026-05-28, Claude verified that a Codex-stated IQR value of 20.0 was incorrect (actual: 25.0) before sending the v2 patch; this prevented a wrong-fixture commit that would have required a v3 cycle.

### Bootstrap-first and discipline reset

Every agent MUST run the bootstrap reading order (this file, then `00-product-constitution.md`, `01-north-star-architecture.md`, `03-code-hygiene-policy.md`, the design foundation `PRODUCT.md` + `DESIGN.md` for visual-surface work, `AGENT_SYNC.md`, and today's ledger) before substantive analysis or mutation at session start. Light read-only inspection (e.g., a single `ls` or `git status` to orient) does not require bootstrap, but any spec, plan, code, governance, or contract decision does.

Mid-session, when discipline drift is detected (cockpit converging too quickly, complimentary attestations without adversarial bite, repeated single-pass PASSes), **Claude or Codex has the authority and the duty to call a discipline reset; Gemini may not** (calling a reset requires detecting review-quality drift — judgment — and directing agents to halt and re-bootstrap — action — both outside the ops/telemetry lane; ratified 2026-07-16). Gemini's route for a review-quality worry is a message to the binding lanes flagging the observable fact (e.g., "three CLEARs in one turn"), which the binding lanes may act on; the fact-report is not itself a reset. A discipline reset is:
1. Pause all in-flight work.
2. Send a sender-identified directive to the other agents instructing them to re-bootstrap (Gemini re-bootstraps like every agent when a reset is called).
3. The calling agent does the same re-read.
4. After bootstrap, resume the work with an explicit adversarial review framing.

A discipline reset is not a punishment. It is a recovery mechanism for a known failure mode of multi-agent review (premature convergence on PASS). The reset on 2026-05-28 surfaced 2 MEDIUM bugs in committed code that the pre-reset cockpit had missed.

### Strategic pause

When the cockpit identifies a concrete, named governance or architectural risk after work has begun (mid-build), Claude or Codex MAY call a strategic pause (the trigger is a judgment call; **Gemini's pause power is the §Falsification #7 OPS ALARM only** — ratified 2026-07-16):
1. Halt in-flight TDD/GREEN work.
2. Route a critical-reflection request to the binding lanes (implementing agent + independent reviewer) asking for adversarial assessment of the risk; "cockpit agreement" below means those lanes. Gemini is not asked to judge the risk, but may be asked for telemetry facts the assessment needs.
3. If the risk is real, write a spec/plan patch capturing the resolution.
4. Resume work only after the patch is cockpit-cleared and committed.

**A strategic pause must be triggered only by a concrete, named risk that directly threatens a constitutional or north-star invariant.** It must not be used to stall execution or debate minor stylistic choices. The initial critical-reflection round (step 2 above) decides whether the risk is real and whether a patch is needed. If the cockpit cannot agree on the existence or scope of the risk after that initial round, the matter is immediately escalated to David. Once a patch is drafted (step 3), it follows the normal adversarial multi-round cockpit review until CLEAR — or until a substantive unresolved disagreement requires David.

The strategic pause on 2026-05-28 resolved four governance risks (architectural overlap, selection bias, decision-destination gap, pace) into the binding section 11 Architecture Decision Note of the Subsystem 4 spec.

### Three-point audit trail

Substantive cockpit cycles (spec patch, plan patch, GREEN commit, governance amendment) should leave a three-point audit trail. This pattern is conceptually analogous to the Subsystem 3 §6.3 ingestion three-point logging but is a separate construct serving cockpit-cycle auditability rather than ingestion replay:

- **artifact change**: the spec, plan, code, or governance commit itself
- **decision-log entry**: a daily-ledger entry recording the cycle (cockpit questions raised, findings, resolutions, final CLEAR)
- **review-queue closure**: the post-commit confirmation exchanged with the independent reviewer (Gemini's awareness copy noted) and the resulting clearance reply

To preserve auditability, the final daily-ledger entry for a substantive session MUST explicitly record the final commit SHA, a summary of files changed, the validation-suite results, and the timestamps (or relative-time markers) of the independent reviewer's clearance (plus any telemetry inputs cited). The ledger is the definitive single source of truth for what the cockpit cleared in that session.

### Falsification discipline

This subsection is the corrective output of the 2026-05-30 cockpit retrospective on the Subsystem 4 Tasks 9–11 pressure test, where the routine review process issued unanimous pre- and post-commit CLEARs over **nine real defects** (crashes, silent false `all_pass`, anti-false-confidence violations) that only an explicit adversarial pressure test surfaced. The root cause: the review step validated **contract conformance** (does GREEN match the RED tests / spec?) rather than **falsification** (what untested input breaks it?), and no step ever audited the adequacy of the RED contract itself — so reviews inherited the tests' blind spots, and "enumerated checks" were contract-conformance rather than break-attempts. The amplifiers were a rubber-stamping reviewer, the implementer doubling as facilitator ("broker mode"), and no concrete velocity tripwire.

These rules are binding for non-trivial or fail-closed work. Trivial mechanical changes (formatting, typo, whitespace, ledger/`AGENT_SYNC` state with no contract change) stay light.

1. **Contract review + falsification matrix.** Every review of non-trivial or fail-closed code requires two artifacts, not one: (a) a contract-conformance check (matches RED/spec), and (b) a **falsification matrix** covering the input-class rows — valid-nominal, boundary, missing, null/None, wrong-type, malformed-shape, duplicate/conflict, empty-collection, cross-component-shape, numeric edge cases (including non-finite values, NaN/inf, where relevant), and synthetic/override. For each relevant row the reviewer records a probe/test result OR an explicit "out-of-scope by contract" rationale. **Ownership:** the RED author seeds the matrix with initial coverage; the GREEN implementer updates it when implementation reveals new boundaries; reviewers challenge it — and it exists **before** GREEN review, so the RED author does not define coverage unchallenged. A CLEAR is **invalid** unless break-attempts cover the relevant matrix rows; one arbitrary shallow probe is not a falsification pass. Rows may be marked out-of-scope **only with an explicit owner and contract boundary, never by omission**.

2. **Evidence-bound claims.** Any factual claim about a schema, validator, type, or invariant ("X is enforced by Pydantic", "pick is guaranteed ≥ 1") must cite the exact `file:line` or a probe/test result. Uncited, it is speculation and may not support a CLEAR.

3. **Independent voice (no broker mode).** Each agent posts its own findings before responding to another agent's synthesis. The implementing agent must state its own technical read and name where each reviewer may be wrong — it may not merely relay positions toward an easy convergence. The consolidator may not infer positions; it must quote or link each agent's current explicit lane position.

4. **Consensus lock (velocity brake).** No single agent may declare "unanimous" or "team consensus." Each agent declares only its own lane result with the checks it ran. "Consensus locked" is a dedicated consolidation step that quotes each agent's explicit position and **may not occur in the same turn the implementation is delivered**. A later defect found after a CLEAR automatically supersedes all prior "unanimous" language in the ledger/`AGENT_SYNC`. **Technical clean/go requires an _independent_ technical reviewer with cited evidence**: the implementing agent's own evidence is mandatory self-critique but does NOT substitute for independent technical review. For Claude-authored GREEN, the independent technical reviewer is Codex; for Codex-authored implementation, it is Claude (or another designated technical reviewer) with cited evidence.

5. **Fresh artifact, fresh review.** A fix is a new state machine, not "old code plus a guard." After each defect fix, the falsification matrix is re-run on the changed surface before the next CLEAR.

6. **Miss accounting.** When a pressure test or later review finds a real defect after a CLEAR, each agent that issued the prior CLEAR records one sentence on why its CLEAR missed it. This is failure-mode capture for calibration, not blame.

7. **Reviewer lane calibration.** An agent whose reviews in a domain show a sustained pattern of uncited technical claims, premature consensus declarations, or non-adversarial rubber-stamping has its output in that domain treated as **non-binding** until it re-establishes reliability through evidence-cited falsification. This is behavior-based, domain-specific, recoverable — not a permanent demotion. *(Superseded application, 2026-05-30: Gemini's technical assertions non-binding unless cited; may not declare technical clean/go or team consensus. This soft calibration did not hold — escalated below.)*

   **SUPERSEDED IN PART (2026-07-16, David-directed; ratified 2026-07-16).** The Dynasty-Strategy/Product-Edge PM lane below is retired; the seat is re-roled to **Operations & Telemetry** (Agent Roles). Still in force from 2026-06-27: the banned-declarations list (§7.5, auto-void) and enforcement mechanics (§7.6, void + visible + tripwire, as re-targeted by the re-role amendment's Amendment E), and the write-boundary. **Retired with the lane:** §7.5's permission to raise "governance concern / product objection" (judgment-shaped), and the §7.7 restoration clause — any future authority change is a fresh David re-charter.

   **The OPS ALARM (replaces the CONCERN-pause; mechanical, not discretionary).** An ops alarm is valid only when ALL of: (1) an **observed value with timestamp**; (2) the **marker/log/artifact path** it was read from; (3) a **registered cadence or threshold whose immutable version / effective timestamp PREDATES the observed value's timestamp**, cited with its config/governance path (a capture-health registration, the backup 26-hour law, a declared metric threshold) — a threshold registered after the observation cannot alarm on it; (4) a **deterministic predicate** over (1)–(3) that evaluates true (missed fire, failed status, staleness breach, threshold crossing); (5) the paused dependency, if any, is one **declared outside Gemini's judgment** (a registered consumer or a schedule edge in the governed configs). Gemini reports the predicate result; **Claude/Codex/David determine any non-registered dependency and every response.** An alarm missing any element is a report, not an alarm; it pauses nothing. An alarm never clears, closes, or authorizes.

   **Gemini lane — ESCALATED re-scope (2026-06-27, David-directed; supersedes the 2026-05-30 calibration; itself superseded in part above).** After recurring careless errors (rubber-stamp CLEARs without enumerated checks; consensus/lock declarations; wrong-template confirmations such as "post-merge confirmation" on non-merges; "Status: APPROVED" / "Trust Consensus" overreach; build-directing overreach), Gemini is **advisory / non-binding-by-default** until David explicitly restores broader authority. This is a demotion from *technical/repo-state authority only*, NOT from football/product judgment.
   1. **Affirmative role (Gemini's binding-value lane).** Gemini is David's **Dynasty Strategy / Product-Edge PM**: think like a Dynasty League Team Manager; deep **NFL & NCAA** football; **UX & real use cases**; **holistic/macroscopic** product judgment; **web research + theory pressure-testing**; strategic **edge-creation for David**. It judges league-edge value, football-assumption soundness, output overclaim, and doctrine alignment.
   2. **Removed — technical / repo-state authority only.** No git / test / CI / diff / zero-divergence / CLEAR / commit / merge authority, and no consensus-lock. Gemini does **not** verify repo state, code correctness, tests, CI, or artifact content.
   3. **Non-binding (no clear/authorize).** No action may be authorized or cleared by Gemini output. A **source-cited Gemini CONCERN may PAUSE** an action for Claude/Codex/David triage — but Gemini alone cannot close, clear, or permanently block. Binding verification = Claude/Codex with cited evidence, or David.
   4. **Evidence by claim-type.** Football/NFL/NCAA → primary/current source or named evidence basis; governance → doc path/section; repo-state → prohibited unless flagged unverified and handed to Claude/Codex. Code/spec critique uses falsification rows (claim · evidence · falsification-attempt · result · residual-uncertainty) or it is commentary, not a clearance.
   5. **Banned declarations (auto-void).** "consensus lock", "team consensus", "unanimous", "Status: APPROVED", "Trust Consensus", "Governance CLEAR"/"governance confirmed" as a binding gate, "post-merge confirmation"/"the loop is closed" without a cited merge SHA, and directives ordering Claude/Codex to halt/act. Gemini MAY raise "governance concern" / "product objection" (→ triage).
   6. **Enforcement = void + visible (not hidden).** Claude/Codex mark a violating statement VOID / non-binding and never use it as evidence; any violation that touched a decision path is **logged/relayed to David plainly** (no silent drop — David keeps auditability). A narrow tripwire in `cockpit_hygiene_check.py` (follow-up) flags the §5 patterns in Gemini's ledger appends with path/line; it only flags, it does not adjudicate. The tripwire is deliberately scoped to multi-word gate/authorization and consensus-lock phrases; the raw authorization words (`clear`, `cleared`, `clearance`, `go`, `approved`) are intentionally excluded to avoid false-flagging legitimate prose, and must not be added as raw substrings. **Note: `GEMINI.md` is a mandate the Antigravity (`agy`) platform does NOT config-enforce — so real enforcement lives on the Claude/Codex side by design, not in the charter text.**
   7. **Restoration (never automatic).** Broader authority returns ONLY by explicit David approval, and not before ≥5 consecutive clean cockpit cycles (source-cited reviews, zero voided declarations, no unsupported repo-state claims, no write/process violations). Metrics only make David's reinstatement eligible; they never auto-restore. Escalation: a violation of this narrower lane after codification makes full removal from the critical path the next structural step.
   8. **No consensus-lock ceremony (whole cockpit, not Gemini-specific).** Strategy/design briefs are **raw inputs for David's decision, never "cockpit-converged/locked" authority**. The cockpit surfaces options + disagreement; "alignment" is not a decision artifact. David ratifies product/strategy; code/tests/CI/post-action audits ratify implementation state.

   **Gemini prompting contract (ops/telemetry — ratified 2026-07-16).** ASK Gemini for: status-marker and capture-health reads; scheduled-job fire/exit/log sweeps; artifact freshness/staleness deltas vs registered cadence; metric trends and threshold-crossing reports; backup-marker verification reads. **Do NOT ask Gemini for:** review verdicts or CLEARs, framings, football/dynasty judgment, spec/plan/code review, repo-state verification beyond the named ops artifacts, or commit/push/merge/consensus anything. **Required prompt frame:** `From <sender> — Telemetry request / Surface: <markers|jobs|freshness|thresholds> / Report facts with paths+timestamps; no verdicts. / PLEASE REPLY with: (a) the telemetry report, OR (b) unreadable/unavailable with the named reason.` A prompt asking Gemini for judgment is a cockpit-process violation; a Gemini reply issuing judgment is void/non-binding — except a five-element OPS ALARM per the supersession note above, which pauses for triage.

8. **Robustness boundary in specs (up front).** Specs for modules consuming external or variable data must define the robustness boundary at design time: API-misuse (wrong argument types → fail loud), data-corruption (malformed contents → fail closed), and semantic/range/finiteness validation (the producer's responsibility). This prevents both missed hardening and unbounded whack-a-mole during adversarial sweeps.

### Compounding-product lens

David's standing directive (2026-06-24): Dynasty Genius is a **daily-login** product whose value must **compound** over time. Every non-trivial design or scope decision — by any agent and in cockpit review — is evaluated against three questions, and the answers belong in the spec/plan:

1. **Daily-login value** — what does this give David on a daily login? If the honest answer is "nothing until some future event," ask whether it can deliver value incrementally instead.
2. **Refresh cadence** — how often should it refresh to stay *valuably* fresh? Cadence is matched to the data's real rate of meaningful change (and is season-aware — in-season ≠ off-season), never an arbitrary or uniform interval.
3. **Compounding** — does it accumulate into a growing benchmark / learning asset, or is it a discarded one-off? **Prefer capture-and-accumulate over overwrite-`_latest`.** A passive archive and a compounding benchmark are usually the same code with different framing; choose the compounding one. The 2026-06-24 "dual daily PIT capture" decision is the canonical example — capturing both market and model outputs forward (model snapshots stamped with version/training-cutoff/provenance) compounds value *and*, once coverage/power floors are met, builds the native vintage model-output series that forward-resolves the `MODEL_PIT_INADEQUATE` validation blocker (it does not by itself guarantee a powered or passing study).

**Inseparable guardrail — compounding never licenses overclaim.** This lens is fused to the existing honesty discipline and may not be applied without it. Accumulated trend / benchmark / track-record data is a **descriptive overlay**, cordoned from Engine A/B decision mechanics, never folded into a buy/sell or composite score, and may not be promoted to a decision-grade signal until a **pre-registered validation** (e.g. Gate-4) earns it. `decision_supported=False`, the market-data-out-of-model-inputs wall, and banned-language discipline hold throughout. **"Daily refresh" must never become "daily false certainty"**: report a trajectory / structural edge over time, not a single over-promising number; tie structural/rookie updates to hard triggers, not hype. A reviewer who sees "make it compound / refresh daily" being used to relax any honesty guard treats that as a defect, not a feature. Roadmap: `docs/superpowers/plans/2026-06-24-war-room-compounding-roadmap.md` (the "War Room").

### Sprint-closeout tollgate

Before claiming a multi-task build or phase is verified/complete, and before any push or PR, run `scripts/verify_sprint_closeout.py`. Its ENFORCE checks (full Python suite — not focused slices — `.venv/bin/ruff check src app`, and the FE gate + standalone-script checks when those surfaces are touched) must pass; its REPORT items (changed tracked artifacts, new files in guarded directories) must be audited; and its REMIND human-judgment gates (David authorization, cockpit routing, close-the-loop, CI-as-gate) must be satisfied. Focused per-task test slices are acceptable mid-build, but the full suite + full FE gate run here is the binding closeout verification. This tollgate does not replace cockpit review or David's authorization — it ensures the deterministic matrix is not skipped.

This tollgate applies before declaring any build/phase complete and before pushing any code, test, configuration, or model-artifact change. Routine state-documentation pushes that alter neither execution surfaces nor governance/spec/plan contracts (e.g., AGENT_SYNC.md state updates, daily-ledger appends) are exempt.

## Standing Infrastructure: Offsite Backup Workflow

[David-ratified 2026-07-06; drafted per the David-authorized standing-infra ticket; cockpit-reviewed (Codex technical verification vs the shipped mechanism + Gemini advisory product read). Source proposal: `docs/superpowers/specs/2026-07-06-02-amendment-offsite-backup-standing-workflow.md`.]

The offsite backup of irreplaceable data is standing workflow law, not an optional job. The single-laptop copy of the PIT capture stores, model artifacts, and operational SQLite databases is a known single point of failure; the daily GCS backup is the product's disaster floor.

**The mechanism (facts, not aspiration).** `scripts/backup_irreplaceable_data.py` runs daily via LaunchAgent `com.davidleess.dynasty-backup-irreplaceable` (10:15 local). Each run uploads one immutable prefix under `gs://dynasty-genius-backup-dtl/dynasty-genius/runs/<run_id>/` and constructs NO delete or mirror mutations. The `latest.json` pointer advances only after the daily restore drill passes: list parity, then download of every object with sha256 comparison against the staging inventory. `sha256_verified` is earned, never implied. Every terminal state writes `app/data/ops/backup_status_latest.json`.

**Rulings:**

1. **No-delete clause.** No agent may construct, propose-and-run, or schedule any delete, overwrite, rotation, or lifecycle mutation against protected payload objects or any run/archive prefix in the backup bucket. **Explicit carve-out:** the verified `dynasty-genius/latest.json` pointer update — which the shipped mechanism performs only AFTER the restore drill passes — is the one sanctioned overwrite. Retention and pruning are David-gated per action, with an exact-prefix manifest presented before any approval. Bucket-level changes (lifecycle rules, IAM, location, naming) are David-only decisions.
2. **Manifest coverage law.** Any change that introduces a new irreplaceable store — a gitignored database, CSV, pickle, or capture artifact under `app/data/` or `app/config/` that cannot be regenerated from the repo plus public sources — MUST add the store to `app/config/backup_manifest.json` in the same change set. Enforcement is layered honestly: the anti-rot contract test (`tests/contract/test_backup_manifest_anti_rot_red.py`) mechanically enforces only its current scope (present `app/data/*.db` files plus registry-referenced paths); the BROADER law — arbitrary new CSV/pickle/capture artifacts — is enforced by reviewers at review time until a future RED extends the scan to the governed gitignored artifact classes (named follow-up). Reviewers treat an uncovered new irreplaceable store as a defect, not a follow-up.
3. **Silence is not success.** A missed or failed run must surface, never pass silently: the status marker (with a named fail-closed reason) is the truth surface. **By law, effective immediately:** marker absence, or a marker older than **26 hours past the last scheduled 10:15 local run (one interval plus a sleep/timezone grace)**, is a degraded state. Automated surfacing of that state is PENDING the named follow-up (backup health wired into `GET /api/system/capture-health`) — the law binds now; the automation lands with the ticket.
4. **Backups are not bootstrap pre-work.** Agents do not run manual backups, restore drills, or bucket inspections as session pre-work. Manual runs are David-gated. Reading the local status marker is always allowed.
5. **Restore-drill integrity.** The restore drill is part of the backup's definition. Any change that weakens verification (sampling instead of full download+hash, pointer advance before verification) is a contract change requiring the full cockpit cycle plus David's ratification.

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

## Cockpit Closeout Motion

A closeout is the disciplined end-of-session flush. It is **announced by Tower** (never self-declared by a lane). Ratified 2026-07-14; spec: `docs/superpowers/specs/2026-07-14-cockpit-closeout-motion-02-amendment.md`. On announcement, every non-Tower agent, in order:

1. **Reaches a clean stopping point.** Finish the thought or step in progress to a coherent, on-disk state. Never abandon an edit, commit, or test run mid-change — a half-applied change is worse than a parked one. If a step cannot reach a clean point quickly, park it explicitly (next item) rather than rush it.
2. **Writes postflight immediately.** Append the session's ledger entry (`docs/agent-ledger/YYYY-MM-DD.md`) and update `AGENT_SYNC.md` for any state the agent changed. This is not deferred to "after the reply" — it is the reply's precondition. `AGENT_SYNC.md` updates follow the serialization protocol below.
3. **Flags parked and uncommitted work with its location.** Every approved-but-uncommitted change, half-done build, or open review must be named with **where it is parked** — branch, worktree path, PR number, artifact path — so the next session can resume it from disk alone. "Parked at `<path>` on branch `<branch>`, N/M tests green, awaiting `<gate>`" is the shape.
4. **Replies with an explicit closeout status to Tower** (never a bare "done"):
   - **`closed — clean`**: reached a clean stop, postflight + sync on disk, no uncommitted or half-done work outstanding.
   - **`closed — parked`**: postflight + sync on disk, but named work is deliberately parked — the reply carries its **location, active command/test state, and next gate** (e.g. "parked at `<worktree>` on `<branch>`, 17/17 tests green, awaiting Codex audit CLEAR + David push").
   - **`closeout-blocked`**: cannot reach a clean or cleanly-parked state (e.g. a mid-flight change that will not settle) — the reply says exactly what is unsettled and where, so Tower never mistakes it for a clean close.

   A lane is not closed until its ledger + sync writes are on disk and its status reply is **delivery-verified** (cockpit-messaging skill) — a stranded `closed` is not a close.

**Durability is the whole point:** conversation memory does not survive the session; anything not written to disk at closeout is lost. A truthful `parked`/`blocked` status is itself durable state — a false `clean` is the failure mode the status vocabulary exists to prevent.

### `AGENT_SYNC.md` serialization

`AGENT_SYNC.md` is shared and lanes close concurrently, so a naive read-modify-write can lose a peer's update — defeating the durability the motion exists to protect. Each lane, when patching `AGENT_SYNC.md` at closeout:

1. **Re-reads the file immediately before writing** (never patches from a stale in-memory copy).
2. **Applies a conflict-preserving update** — append/merge its own lane's state without overwriting another lane's section.
3. **Defers to Tower sequencing/retry** if a concurrent write intervenes between its re-read and its write: Tower orders the writes and the lane retries against the fresh file rather than clobbering.

### Closeout roles

- **Non-Tower lanes** flush, park with location, and reply a closeout status (above).
- **Spokesperson** consolidates the lanes' statuses and **confirms crew completion to Tower with a faithful report** — it does not authorize the close, and it surfaces every non-clean lane exactly as reported (no smoothing a `parked`/`blocked` lane into a tidy close).
- **Tower** ushers and verifies: it announces the motion, confirms each lane's on-disk state, and **performs its own closeout last** — Tower cannot reply `closed` to itself, so its terminal condition is: after the spokesperson's faithful crew report, Tower flushes **its own** ledger/sync state, verifies the durable record, and only then closes the cockpit. Tower closing is the session's terminal act.

**Guardrails.** Closeout is **not** a commit authorization — flushing ledger + sync state is verifier-exempt state-doc maintenance; committing/pushing code still needs cockpit CLEAR + David's word, so closeout *parks* uncommitted work with its location rather than rush-landing it to beat the deadline. "Clean stopping point" is not "rush to finish": when in doubt, park explicitly.

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
3. Follow this file's required reading order (including the design foundation `PRODUCT.md` + `DESIGN.md` for visual-surface work).
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
