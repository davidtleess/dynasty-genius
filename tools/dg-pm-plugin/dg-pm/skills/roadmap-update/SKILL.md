---
name: roadmap-update
description: Update AGENT_SYNC.md and the David-sequenced priority board. Use when a thread ships or merges, a new priority or named ticket arrives, priorities re-sequence after new information, or an accrual-gated wake needs recording. Maintains the current-thread banner, the priority board, named tickets, and deferred/accrual-gated items.
argument-hint: "<what changed or what to add>"
---

# Roadmap update (AGENT_SYNC + the priority board)

> Sources are DG's own artifacts — see [SOURCES.md](../../SOURCES.md). DG has no Jira/Linear; the roadmap lives in `AGENT_SYNC.md` and the David-sequenced priority board.

DG's "roadmap" is `AGENT_SYNC.md` — a dense living status doc, most-recent state at the top — plus the per-session `docs/agent-ledger/`. David sequences; nothing is "scheduled" or "committed to build" without his word. Your job is to keep the top of AGENT_SYNC an honest, current snapshot the next agent can trust after a cold boot.

## Workflow

### 1. Read the current state first
- Read the top status banners of `AGENT_SYNC.md` and today's ledger. Understand what thread is active, what shipped, what's David-gated.
- Never overwrite a banner you don't understand — DG banners encode blockers, gates, and superseded history deliberately.

### 2. Classify the update
- **Shipped/merged** → add or update a banner: PR #, merge SHA, CI status, what's now live, branch disposition (retained/deleted = David's word), and the honest residual ("proven green" only if a real run/drill earned it, not just code-merged).
- **New priority or named ticket** → add it to the priority board. Mark whether it's David-ratified, David-named-soon, or a parked idea. Do not promote an idea to "authorized build."
- **Re-sequence** → reorder with a one-line reason; preserve the prior order as superseded context if it carried decisions.
- **Accrual-gated wake** → record the trigger and the earliest honest date (e.g. "~Sept: realized-outcome rich UI; ~Dec: Gate-4/divergence track records"). Never promise outcome-validated claims before outcomes accrue.

### 3. Preserve the DG conventions
- **Most-recent at top.** New banners go above older ones; supersede rather than delete when history carried a decision.
- **Every material step routes through the cockpit** (Gemini frames → Codex RED → Claude GREEN → dual-CLEAR → David authorizes). `dual-CLEAR` = Claude + Codex, the two binding lanes; Gemini is advisory/non-binding and never issues a CLEAR. Say so where relevant.
- **Name the gate.** If something is blocked (RED not cleared, David word pending, accrual pending), say exactly what unblocks it.
- **Branch/commit discipline.** Retained branches are listed with "delete = David's word." Commits/merges are David-authorized.

## Roadmap formats DG actually uses

- **Current thread** — the one active build/investigation, with its plan-of-record path.
- **Named priorities** — David-ratified or David-named-soon items (e.g. the PVO-scale solutioning session), with the decision vs. build distinction explicit.
- **Deferred + accrual-gated** — parked ideas and time-gated wakes. Ideas stay descriptive; none is a verdict or an authorized build.
- **Shipped + live** — historical banners kept for cold-boot context (PR, SHA, what's live, residual).

## Prioritization

David sequences, but you can *surface* tradeoffs honestly (never decide):
- **Blast radius** — universe-wide model-output changes (largest) vs. surface-scoped vs. docs.
- **Reversibility** — additive/versioned first; in-place model-output mutation needs its own spec+RED.
- **Accrual reality** — is the payoff gated on time (forward-capture accrual) that nothing buildable accelerates? Say so plainly.
- **Compounding value** — does it add daily-login value / compound a benchmark? DG builds are growing assets.

## Output

Edit `AGENT_SYNC.md` in place (targeted edits, not a rewrite) and, if a session is closing, add the matching ledger entry via `dg-pm:david-update`. Bump `Last updated`. **The edit is content; committing it is a David-authorized action** — offer the branch+PR, don't commit unprompted.

## Tips

- The top of AGENT_SYNC is a cold-boot briefing. If a fresh agent couldn't act correctly from it alone, it's not done.
- Don't let "priority elevated" harden into "build authorized." Keep the decision/build line bright — it's a recurring DG failure mode.
- Record what's *unproven* as loudly as what shipped. An honest blocker is more useful than an optimistic banner.
