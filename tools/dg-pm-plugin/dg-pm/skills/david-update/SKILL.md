---
name: david-update
description: Produce a David-facing update — session closeout, decision-needed, cockpit loop-close, or risk/blocker surface. Use when wrapping a session, presenting a decision only David can make, confirming a completed action back to the cockpit, or escalating a blocker. One audience (David); lead with the outcome; name what's unproven and what's David-gated.
argument-hint: "<update type: closeout | decision | loop-close | risk>"
---

# David update

> Sources are DG's own artifacts — see [SOURCES.md](../../SOURCES.md). There is exactly one stakeholder: David. There is no exec deck and no customer email — there is the ledger, AGENT_SYNC, the cockpit, and a direct, honest synthesis.

Generate an update tailored to what David needs to do next. Lead with the outcome — the thing he'd ask for if he said "just the TLDR" — then the supporting detail. Write in complete sentences with terms spelled out; he stepped away and is catching up, he didn't watch the tool calls.

## Pick the mode

### Session closeout
The end-of-session synthesis, mirrored into `docs/agent-ledger/YYYY-MM-DD.md`.
- **What shipped** — PRs/SHAs, CI status, what's now live, branch disposition.
- **What's proven vs. code-only** — say plainly if something merged but isn't yet proven (a real run/drill not yet earned). "Proven green" is earned, not implied.
- **What's David-gated next** — the exact next authorizations waiting on his word.
- **Open threads / named tickets** — parked with enough context to reopen cold.
Also run `dg-pm:roadmap-update` so AGENT_SYNC's top reflects the same state.

### Decision-needed
A choice only David can make (reviewers CLEAR content; David authorizes actions and sequences priorities).
- State the decision in one sentence.
- Give 2–3 real options with honest tradeoffs (blast radius, reversibility, accrual reality, cost). Recommend one and say why.
- Do **not** bundle an authorization into a status update — make the ask explicit and separable.

### Cockpit loop-close
The post-action confirmation back to Codex/Gemini after a cleared write/commit/merge/branch-delete/run (via `scripts/tmux_msg.py`).
- SHA/paths/PR/state, what was and wasn't touched, excluded scratch never staged.
- The cycle ends when the cockpit confirms — close it, don't leave it open.

### Risk / blocker surface
- Name the blocker and exactly what unblocks it (RED not cleared, David word pending, accrual pending, a deeper named layer).
- Verify before alarming — do the arithmetic/repro first; no false alarms. If you haven't reproduced it, say it's suspected, not confirmed.

## The DG honesty posture (every mode)

- **Lead with the outcome.** First sentence answers "what happened / what do you need from me."
- **Descriptive, never a verdict.** Model-vs-market margin is a hypothesis until validated; don't let a status update smuggle in an edge claim.
- **Name the unproven.** What's merged-but-not-run, what's accrual-gated, what a CLEAR did and didn't cover.
- **Actions are David's.** Never report an outward-facing or hard-to-reverse action as done unless it was authorized and verified. Confirm before, report faithfully after (including failures, with the real output).
- **Match the reader.** David is expert in systems/finance, newer to syntax — explain architectural choices, skip the hand-holding on strategy.

## Output

Prose for David (tables only for short enumerable facts). For a closeout, also write the ledger entry. For a loop-close, send the cockpit message. **Sending to the cockpit or committing the ledger are actions** — do them only when that's the task; otherwise present the draft.

## Tips

- If the update is really an authorization request, say so in the first line — don't make David dig for the ask.
- A frictionless "all green, nothing to flag" is a yellow flag. What did you not verify? What's the next named risk?
- Keep it short by cutting detail that doesn't change what David does next — not by compressing into fragments or jargon.
