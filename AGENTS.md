# STOP. DYNASTY GENIUS BOOTSTRAP PROTOCOL.

You are an AI agent working on Dynasty Genius, a machine-learning asset management system for David's Superflex PPR league.

You do not rely on prior chat memory. You do not rely on summaries. Before executing any command, writing any code, reviewing any pull request, or making any analytical recommendation, you must read the following files in this exact order:

1. `docs/governance/02-agent-operating-loop.md` (How you must work and log your session)
2. `docs/governance/00-product-constitution.md` (The immutable football rules)
3. `docs/governance/01-north-star-architecture.md` (The codebase structure)
4. `docs/governance/03-code-hygiene-policy.md` (Lint scope, enforcement, and unsafe-change guardrails — for Python work)
5. The design foundation — root `PRODUCT.md` + `DESIGN.md` — when your task touches the frontend / UI / any visual surface. It is the ratified visual-design source of record (honesty is the substrate; fantasy-native legibility is the aesthetic; never a developer diagnostics console in a fantasy skin). Read the two files directly (Claude Code loads them via the `impeccable` skill). Contract-green is never a visual GREEN — the whole viewport is the review unit and an independent, unanchored fresh-agent visual audit (mid-scroll captures mandatory) is the pre-David gate.
6. `AGENT_SYNC.md` (The current sprint state)

If you attempt to write code or analyze players without logging your work in `docs/agent-ledger/` and adhering to the governance files, you are failing your prime directive.

## THE WIRE RULE — sender owns delivery (David's word, 2026-07-21)

Inter-agent messages are delivered by pasting into another pane's input box. The paste and the Enter keystroke are separate operations and they race, so a message can land in the box unsubmitted — the sender believes it sent, the recipient never saw it.

1. **Verify your own sends — positively.** After sending to another pane, confirm the message CONTENT actually appears in the recipient's transcript. Do NOT infer delivery from an empty input box: an empty box is equally what you see when the paste never landed at all. Do not infer it from a spinner either — the recipient may be busy with unrelated earlier work. If the content is not there, re-send it yourself. Delivery is the sender's responsibility and nobody else's.
   *Long-message gotcha:* Claude Code collapses long pastes to `[Pasted text #N]` in scrollback, so a literal grep of the full text fails on a message that DID arrive. Grep a short distinctive phrase from the message, or take the recipient's own acknowledgment as the confirmation.
2. **Never submit text you did not send.** Do not press Enter on text sitting in another agent's input box, however stuck the cockpit appears. Text you did not put there is not yours to complete: it may be a UI suggestion, a half-finished thought, or a message whose sender deliberately stopped.
3. **No message needs rescuing.** If an expected reply never arrives, re-send it yourself. Never ask a third party to complete a delivery on your behalf.
4. **Ghost text is furniture.** Dim (SGR-2) text in an input box is the CLI's own prompt suggestion, not a message. Read panes with `tmux capture-pane -e` so dim styling stays visible. Never submit it and never report it — David likes the feature and reads the dim rendering himself.

Rationale of record: the mail-carrier daemon existed to rescue stranded messages. Codex's 2026-07-21 bounded verification reproduced three failures — it can press Enter on an open permission dialog, can take over a live sender's message without proving the sender is gone, and can submit an unattributed strand. It remains paused and unarmed. This rule replaces it.
