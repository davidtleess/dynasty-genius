# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# STOP. DYNASTY GENIUS BOOTSTRAP PROTOCOL.

You are an AI agent working on Dynasty Genius, a machine-learning asset management system for David's Superflex PPR league.

You do not rely on prior chat memory. You do not rely on summaries. Before executing any command, writing any code, reviewing any pull request, or making any analytical recommendation, you must read the following files in this exact order:

1. `docs/governance/02-agent-operating-loop.md` (How you must work and log your session)
2. `docs/governance/00-product-constitution.md` (The immutable football rules)
3. `docs/governance/01-north-star-architecture.md` (The codebase structure)
4. `docs/governance/03-code-hygiene-policy.md` (Lint scope, enforcement, and unsafe-change guardrails — for Python work)
5. **The design foundation — root `PRODUCT.md` + `DESIGN.md` — only if your task touches the frontend / UI / any visual surface** (anything under `frontend/`, React/TS, CSS, a route, or a component). It is the ratified visual-design source of record (honesty is the substrate; fantasy-native legibility is the aesthetic; the product must never look like a developer diagnostics console in a fantasy skin). Claude Code loads it via the `impeccable` skill; it is also item 5 of governance 02's Required Reading Order (Codex, Gemini, and other agents read the two files directly). **Contract-green is never a visual GREEN** — the whole viewport (not the diff) is the review unit, and an independent, unanchored fresh-agent visual audit with mid-scroll captures is the standing pre-David gate.
6. `AGENT_SYNC.md` (The current sprint state — contains active blockers and script run gates)

If you attempt to write code or analyze players without logging your work in `docs/agent-ledger/` and adhering to the governance files, you are failing your prime directive.

## THE WIRE RULE — sender owns delivery (David's word, 2026-07-21)

Inter-agent messages are delivered by pasting into another pane's input box. The paste and the Enter keystroke are separate operations and they race, so a message can land in the box unsubmitted — the sender believes it sent, the recipient never saw it.

1. **Verify your own sends.** After sending to another pane, look at that pane. An empty input box or a running spinner means delivered. Your text still sitting in the box means NOT delivered — press Enter once more. Delivery is the sender's responsibility and nobody else's.
2. **Never submit text you did not send.** Do not press Enter on text sitting in another agent's input box, however stuck the cockpit appears. Text you did not put there is not yours to complete: it may be a UI suggestion, a half-finished thought, or a message whose sender deliberately stopped.
3. **No message needs rescuing.** If an expected reply never arrives, re-send it yourself. Never ask a third party to complete a delivery on your behalf.
4. **Ghost text is furniture.** Dim (SGR-2) text in an input box is the CLI's own prompt suggestion, not a message. Read panes with `tmux capture-pane -e` so dim styling stays visible. Never submit it and never report it — David likes the feature and reads the dim rendering himself.

Rationale of record: the mail-carrier daemon existed to rescue stranded messages. Codex's 2026-07-21 bounded verification reproduced three failures — it can press Enter on an open permission dialog, can take over a live sender's message without proving the sender is gone, and can submit an unattributed strand. It remains paused and unarmed. This rule replaces it.

## Environment

The project uses Python 3.14. Always invoke the project venv explicitly:

```bash
.venv/bin/python3.14 -m pytest          # run tests
uvicorn app.main:app --reload           # run the API server
```

Two test files have pre-existing collection errors and must be excluded from standard runs — check `AGENT_SYNC.md` for the current exclusion list.

## Developer Quick Reference

After completing the governance reads, see `docs/development/quick-reference.md` for the module map, key scripts, and architecture overview.
