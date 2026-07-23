# 02 Amendment — Cockpit Spokesperson (single David-facing voice)

- Status: DRAFT v3 for Codex re-review (sole binding reviewer per the 2026-07-16 Gemini re-role ruling). Commit = David's word; per David 2026-07-16 the ratification grant is contingent on a CLEAN review — v3's changes are material, so the delta returns to David before this is treated as ratified. v3 integrates Codex's round-2 NOT-CLEAR (7 findings: version target, retired-lane references, no-suppression tie-break + complaint path, fallback split-brain, source-precedence contract conflict, overflow completeness, enforcement mapping). v2 had integrated round-1.
- Author: Claude Code
- Date: 2026-07-14 (v3: 2026-07-16)
- **Depends on:** the 2026-07-16 Gemini re-role amendment (`docs/superpowers/specs/2026-07-16-gemini-ops-telemetry-rerole-02-amendment.md`) — this draft's Gemini references use the re-role's ops/telemetry lane and OPS ALARM construct. Whichever amendment lands second carries the reconciliation edit.
- Target: `docs/governance/02-agent-operating-loop.md` (authority: workflow). Takes the next free minor version on ratification (v1.3.0 or v1.4.0, coordinated with the re-role amendment by landing order — 02 is already at v1.2.0 via PR #153).
- Source directive: David, 2026-07-14 (verbatim intent): "I want ONE voice, not three. Claude (pane 1) is now the cockpit spokesperson." Supersedes the per-agent `>>> DAVID:` last-line rule (itself the replacement for the rescinded `~/cockpit/NEEDS-DAVID.md` file queue).

## Problem

David receives David-facing asks (rulings, approvals, reviews) from three agents in three panes. Three voices for one decision-maker means duplicated, conflicting, or unprioritized asks, and no single place that shows "the one thing the team needs from you." The prior mechanisms (shared file queue, then a per-agent last-line convention) let every agent address David directly; that is the noise this amendment removes.

## Amendment

### 1. New subsection under "Cockpit Process" (after "Roles, default reviewers, and escalation")

> ### David-facing spokesperson (single voice)
>
> **Claude Code is the cockpit's single David-facing spokesperson.** David-facing asks — anything requiring a David-only action (a ruling, an approval, a review, a restart, a sequencing decision) — reach David through Claude alone, as one prioritized voice.
>
> Process:
> 1. The cockpit aligns as a team on what is ready for David's review and what needs his approval, via the normal convergence loop (the framing pass per §Strategy/UX framing first → adversarial review → each lane's own position). Codex and Gemini route their David-facing asks to Claude through normal cockpit messaging (`scripts/tmux_msg.py`), not to David directly.
> 2. Claude consolidates the asks and, alone, messages David. The message's LAST line — with nothing after it — begins `>>> DAVID:` followed by a short numbered list of what the team needs, in the plainest possible words. When the team needs nothing from David, no `>>> DAVID:` block is emitted.
> 3. So the bottom of Claude's pane always shows either work-in-progress or the single consolidated list of what David owes the team.
>
> **Ordering rule (mechanical, never merits).** Undisputed asks are listed in the team's converged priority order. A DISPUTED ask (any ask a lane maintains against another lane's position) is ordered by the requesting lane's own stated priority, ties broken by message timestamp — the spokesperson never re-ranks a disputed ask on its merits. Each lane's position is quoted or linked (message timestamp or ledger line), never paraphrased into convergence — the same consolidator rule as §Falsification #3.
>
> **Exceptions (the complete set of legitimate direct-to-David agent output):**
> 1. Harness permission prompts in an agent's own pane — answered where they occur (local tool-authorization, not David-facing product asks).
> 2. A source-cited OPS ALARM (per the Gemini re-role amendment: a failed/missed scheduled run, data-integrity signal, freshness breach, or threshold crossing, cited to a marker/log/artifact path) surfaces immediately; it is not held for spokesperson batching. It routes to David *through* Claude without delay, relayed verbatim and unsuppressed (see no-suppression below). If Claude is unavailable, the alarming agent may state it directly under the fallback rules below — for Gemini, constrained to the fact-cited alarm itself, never a judgment ask.
> 3. A suppression or misattribution concern about the spokesperson itself: any agent that believes its ask was dropped, softened, or misstated may message David directly, labeled `suppression concern — <agent> <timestamp>`, without routing through Claude. This is the independent complaint path; it is expected to be rare and is always ledgered by the raising agent.
>
> **No suppression or merging of disputed asks.** Where the lanes have not converged, Claude presents each lane's ask in its own words (quote-or-link, per the ordering rule) and flags the divergence; it may not drop, soften, merge-away, or re-rank a lane's ask on the merits. Consolidation orders mechanically and de-duplicates; it never adjudicates.
>
> **Unavailable-Claude fallback (binding, single fallback voice).** Claude is unavailable when it is visibly crashed/absent, or when a delivery-verified cockpit message to it has gone unanswered for 10 minutes. On that trigger, **Codex is the designated fallback spokesperson** — not "any agent" — and its direct messages to David are labeled `spokesperson unavailable — fallback voice Codex <timestamp>`. Gemini in fallback may surface only fact-cited ops alarms, same label grammar. Fallback lapses on the recovery handshake: Claude posts an explicit resumption message to both agents, after which direct messaging stops. Simultaneous direct voices outside these rules are a cockpit-process violation.
>
> **Message grammar.** Every spokesperson message to David keeps the standard cockpit sender-first-line (`From Claude (spokesperson) — <subject>`) and ends with the `>>> DAVID:` block as its last line when — and only when — a David action is needed. The Morning Brief follows the same grammar (it is a companion to, not an exception from, the sender-first-line rule).
>
> **Scope and limits.** Spokesperson is a *routing and consolidation* duty, not authority. Claude does not decide, rank away, or suppress another lane's ask on the merits — it aligns the team and presents the converged list faithfully, preserving each lane's position where the team has not converged (an unresolved cross-domain divergence is presented to David as a divergence, per the escalation rules, never silently resolved). Claude's existing non-authority over technical questions (Codex's domain) and product rulings (David's) is unchanged; governance divergence escalates to David per the reviewer-lane rules as amended by the Gemini re-role amendment. The spokesperson role is behavioral and does not alter the Authority Order or reviewer lanes.

### 1b. Same subsection — the Morning Brief (standing)

> **The Morning Brief.** At the start of every cockpit session, after Claude completes its governance bootstrap and before other substantive work, Claude's first act as spokesperson is a brief to David in the spokesperson pane. It states, in the plainest words:
> - what shipped since the previous session,
> - what is in flight,
> - what is blocked,
> - and what needs David — where the correct and common answer is "nothing needs you."
>
> The brief targets **ten logical lines** — newline-delimited content lines, not terminal-wrapped display rows. The ceiling disciplines the narrative; it never trims the ask set: **every item requiring a David action appears, compactly, even when that breaks the ceiling** — David-action completeness beats the line target. Non-David-action detail (in-flight work, blockers the crew is handling) is what compresses: it is summarized in the brief and carried in full in today's ledger, and when the brief summarizes an overflow set, those items must actually be in the ledger — written in a companion ledger entry in the same session if not already there (a state-doc append, permitted post-bootstrap). Blockers the crew is handling are reported as blockers, never converted into "needs you" items. The brief ends with the `>>> DAVID:` line ONLY when something genuinely needs David; when nothing does, it says so and stops.
>
> **Sources and discrepancies (the brief must not state a false current claim).** The brief is drawn from the durable sources — the daily ledger, `AGENT_SYNC.md` (the current shared state board, per this document's AGENT_SYNC.md Format section, unchanged), and directly observed repository/runtime state — never chat memory, so it survives restarts. Every runtime observation the brief relies on is cited with what was read and when (marker path + timestamp), since live state is not durable unless the observation is recorded. Where the sources disagree (e.g., a stale AGENT_SYNC banner vs the ledger or a fresh marker), the brief carries the discrepancy as an explicit flagged line rather than silently picking a winner; a material discrepancy is itself David-visible. This amendment does not change the state-board contract — AGENT_SYNC.md remains state, the ledger remains detail.

### 2. Edit to "Agent Roles" — Claude Code bullet

Append to the existing Claude Code role description:

> Claude Code is additionally the cockpit's single David-facing spokesperson (see Cockpit Process → David-facing spokesperson): it consolidates the team's aligned David-facing asks and is the only agent that addresses David with them. This is a routing/consolidation duty, not decision authority.

### 3. Edit to "Agent Roles" — Gemini and Codex

Add one sentence to each of the Gemini and Codex role descriptions:

> David-facing asks are routed to Claude (the spokesperson) through normal cockpit messaging, not addressed to David directly; harness permission prompts in the agent's own pane are the one exception.

## Enforcement mapping (honest: what is and is not mechanical)

- **Mechanical on landing:** `scripts/validate_governance.py` gains a required-phrase pin (`"David-facing spokesperson"`) + test, the same lock pattern as the material-visual-direction clause (PR #127 precedent).
- **Procedural (ledger-auditable, not machine-checked):** single-voice conduct, the `>>> DAVID:` last-line grammar, the ten-line/completeness rule, fallback trigger + labels, recovery handshake, no-suppression. Each brief and each fallback event is ledgered, which is the audit surface. `scripts/tmux_msg.py` performs no sender/grammar checks today (`:66`, `:93`).
- **Named follow-up (not this amendment):** a RED extending mechanical checks (e.g., message-grammar lint in tmux_msg, fallback-state marker) if the procedural regime proves leaky. Deferring it is a scope choice, stated here so it is not mistaken for coverage.

## Out of scope

- No change to Authority Order or analytical/technical ruling authority. Reviewer-lane composition is governed by the 2026-07-16 Gemini re-role amendment, not this one.
- Does not govern non-David-facing cockpit traffic (agent-to-agent review remains unchanged).
- Does not make Claude an arbiter of other lanes' positions — divergence still escalates to David per existing rules.
- Does not change the AGENT_SYNC.md state-board contract (explicitly reaffirmed in the brief's sources clause).

## Falsification seeds (for the reviewers)

1. Does "spokesperson" leak into authority — could Claude use consolidation to suppress a Codex/Gemini ask it disagrees with? (The scope/limits clause must prevent this; check it is airtight.)
2. Exceptions completeness: is the three-item exception set (permission prompts · source-cited OPS ALARM per the re-role amendment · suppression concern) the *complete* set of legitimate direct-to-David agent output? Verify the OPS ALARM routing (through Claude; direct only under fallback, fact-cited) reconciles with the re-role amendment's A2, and that the suppression-concern path cannot be abused as a general bypass (it requires the named label + a ledger entry by the raiser).
3. Single-voice vs. independent-principal: does routing asks through Claude weaken each agent's duty to hold its own position (§Falsification #3, no broker mode)? The amendment must preserve independent positions inside the converged list.
4. Fallback soundness: is the trigger (visible crash OR a delivery-verified message unanswered 10 minutes) detectable without ambiguity, is Codex-as-sole-fallback-voice sufficient (what if BOTH Claude and Codex are down?), and does the recovery handshake reliably end split-voice states?
5. Does the `>>> DAVID:` last-line-only rule conflict with the ledger/postflight requirements or the message-format rules (sender ID on first line)? Confirm the two coexist.
6. Morning Brief vs the bootstrap-is-not-implementation rule: the brief is a read-and-report act after bootstrap (the overflow companion ledger entry is a permitted state-doc append) — confirm neither constitutes "pre-work," and that the sources-and-discrepancies clause is workable when a session opens with a stale AGENT_SYNC banner.
7. Ceiling-yields rule: with David-action completeness now beating the ten-line target, can the brief degrade into an unbounded list (the old noise problem returning through the completeness door)? Check the compression pressure on non-David items is strong enough to keep briefs short in practice.
8. Ordering rule: is "requesting lane's own stated priority, ties by timestamp" gameable (a lane inflating its stated priority to jump the list), and is that acceptable given David sees the inflation?
