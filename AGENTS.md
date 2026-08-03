# STOP. DYNASTY GENIUS BOOTSTRAP PROTOCOL.

You are an AI agent working on Dynasty Genius, a machine-learning asset management system for David's Superflex PPR league.

You do not rely on prior chat memory. You do not rely on summaries. Before executing any command, writing any code, reviewing any pull request, or making any analytical recommendation, you must read the following files in this exact order:

1. `docs/governance/02-agent-operating-loop.md` (How you must work and log your session)
2. `docs/governance/00-product-constitution.md` (The immutable football rules)
2a. `docs/governance/05-layer-doctrine.md` — **ALWAYS, EVERY SESSION. Read it; it is short.** **Do not rely on any summary of it, including this pointer** — §1 forbids paraphrase, so the doctrine's own words are supplied only by the mandatory read. §1 is David's words verbatim; §2 onward is agent-authored codification — cite them differently and never attribute the whole file to him. His ruling, quoted exactly: *"Steps 1 and 2 are the foundation - if we don't have this our app WILL NOT WORK. we shouldn't be wasting cycles until we've built this foundation."* **Obligations (pending — see ACTIVATION STATUS at the end of this item):** name the layer your work serves in every preflight; work at layers 3-6 records the layers 1-2 dependency check (what you ran, what it showed, your conclusion). Priority is never authorization, and a conclusion is not a licence to fix. **ACTIVATION STATUS — read this before treating anything in this item as binding.** **`05` §1 is David's own words and stands on his authority.** But **the every-session read requirement AND the obligations stated above are BOTH agent-authored codification, PENDING DAVID'S RATIFICATION and NOT YET BINDING** — he never issued a read command; that delivery mechanism is ours. The lanes follow both voluntarily pending his word, but no agent may cite either as law, hold another agent to them, or block work on them until he ratifies. Ratification is tracked on `AGENT_SYNC.md`.
3. `docs/governance/01-north-star-architecture.md` (The codebase structure)
4. `docs/governance/03-code-hygiene-policy.md` (Lint scope, enforcement, and unsafe-change guardrails — for Python work)
5. The design foundation — root `PRODUCT.md` + `DESIGN.md` — when your task touches the frontend / UI / any visual surface. It is the ratified visual-design source of record (honesty is the substrate; fantasy-native legibility is the aesthetic; never a developer diagnostics console in a fantasy skin). Read the two files directly (Claude Code loads them via the `impeccable` skill). Contract-green is never a visual GREEN — the whole viewport is the review unit and an independent, unanchored fresh-agent visual audit (mid-scroll captures mandatory) is the pre-David gate.
6. `AGENT_SYNC.md` (The current sprint state)
   **HOW TO READ IT.** The file is ~400 KB and **append-at-top**. Read from line 1 **through the
   `⏹ END CURRENT BOARD` marker** and stop there. Everything below that marker is **historical
   context and is not live unless the current board reopens it** — reading further costs context
   and risks inheriting superseded commands. Several older blocks still say "READ FIRST" or
   "READ THIS BLOCK BEFORE ANYTHING BELOW IT"; **those are stale claims from when they were
   newest.** Precedence is by position, newest first — if two blocks conflict, the higher governs.

If you attempt to write code or analyze players without logging your work in `docs/agent-ledger/` and adhering to the governance files, you are failing your prime directive.

## THE WIRE RULE — sender owns delivery (David's word, 2026-07-21)

Inter-agent messages are delivered by pasting into another pane's input box. The paste and the Enter keystroke are separate operations and they race, so a message can land in the box unsubmitted — the sender believes it sent, the recipient never saw it.

1. **Verify your own sends — positively.** After sending to another pane, confirm the message CONTENT actually appears in the recipient's transcript. Do NOT infer delivery from an empty input box: an empty box is equally what you see when the paste never landed at all. Do not infer it from a spinner either — the recipient may be busy with unrelated earlier work. If the content is not there, re-send it yourself. Delivery is the sender's responsibility and nobody else's.
   *Long-message gotcha:* Claude Code collapses long pastes to `[Pasted text #N]` in scrollback, so a literal grep of the full text fails on a message that DID arrive. Grep a short distinctive phrase from the message, or take the recipient's own acknowledgment as the confirmation.
2. **Never submit text you did not send.** Do not press Enter on text sitting in another agent's input box, however stuck the cockpit appears. Text you did not put there is not yours to complete: it may be a UI suggestion, a half-finished thought, or a message whose sender deliberately stopped.
3. **No message needs rescuing.** If an expected reply never arrives, re-send it yourself. Never ask a third party to complete a delivery on your behalf.
4. **Ghost text is furniture.** Dim (SGR-2) text in an input box is the CLI's own prompt suggestion, not a message. Read panes with `tmux capture-pane -e` so dim styling stays visible. Never submit it and never report it — David likes the feature and reads the dim rendering himself.

Rationale of record: the mail-carrier daemon existed to rescue stranded messages. Codex's 2026-07-21 bounded verification reproduced three failures — it can press Enter on an open permission dialog, can take over a live sender's message without proving the sender is gone, and can submit an unattributed strand. It remains paused and unarmed. This rule replaces it.

## UNDER TEST — QB rushing is a live hypothesis, not a finding (David's word, 2026-07-22)

The QB-1 study pre-registration (`docs/validation/2026-07-21-qb-1-study-registration.md`) registers QB **rushing production (H2)** as a hypothesis **under test**. The study has not run. There is no result.

Until the pre-registered study is executed and David rules on the registered result:

1. **Do not assert rushing as established.** Not in David-facing output, prose, specs, plans, briefs, or your own reasoning; not as a premise for a feature, threshold, tier, or recommendation. "Under test" is the only status it has.
2. **A registered hypothesis is not evidence for itself.** Do not cite the registration, its manifests, or any interim or partial output as support for rushing mattering. Pre-registration exists to stop exactly that.
3. **Know the ceiling.** The study's registered target is regular-season fantasy points per qualifying game under a pinned scoring rule, in a veteran cohort — **not "dynasty value."** Any result on one of the five registered contrasts involving H2 (§8) would, at most, support that corresponding registered comparison, under that contrast's registered status vocabulary and the study's inference contract and David's ruling — never a general "rushing is established" claim, never a marginal/conditional "rushing adds value on top of the other features" claim (no registered contrast tests it), and never the broader value construct without separate validation.
4. **Say the status out loud when you use it.** Naming rushing as a hypothesis under test is always allowed, and is the required form.
5. **Only execution-plus-ruling lifts this.** Not a partial run, not an interim table, not a plausible coefficient, not the passage of time.

Pre-existing rushing language and shipped model mechanics elsewhere in the repo are **not** cleared by this section. Full text: Addendum A at the foot of the registration document.
