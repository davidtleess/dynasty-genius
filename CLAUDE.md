# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# STOP. DYNASTY GENIUS BOOTSTRAP PROTOCOL.

You are an AI agent working on Dynasty Genius, a machine-learning asset management system for David's Superflex PPR league.

You do not rely on prior chat memory. You do not rely on summaries. Before executing any command, writing any code, reviewing any pull request, or making any analytical recommendation, you must read the following files in this exact order:

1. `docs/governance/02-agent-operating-loop.md` (How you must work and log your session)
2. `docs/governance/00-product-constitution.md` (The immutable football rules)
2a. **`docs/governance/05-layer-doctrine.md` — ALWAYS, EVERY SESSION.** Its **§1 is David's own words, verbatim**; **§2 onward is agent-authored codification** — cite them differently and never attribute the whole file to him. **Do not rely on any summary of it, including this one** — §1 forbids paraphrase, so its own words come only from the read. His ruling, quoted exactly: *"Steps 1 and 2 are the foundation - if we don't have this our app WILL NOT WORK. we shouldn't be wasting cycles until we've built this foundation."* **Obligations (pending — see ACTIVATION STATUS at the end of this item):** name the layer your work serves (primary/presenting; several if it spans them; `cross-layer`/`governance` is valid); work at layers 3-6 records the layers 1-2 dependency check — what you ran, what it showed, your conclusion. Priority is never authorization, and a conclusion is not a licence to fix. *(The precedence rule — that 05 outranks plans, specs, tickets and backlogs — is part of the same pending codification and is NOT yet in force.)* **ACTIVATION STATUS — read this before treating anything in this item as binding.** **`05` §1 is David's own words and stands on his authority.** But **the every-session read requirement AND the obligations stated above are BOTH agent-authored codification, PENDING DAVID'S RATIFICATION and NOT YET BINDING** — he never issued a read command; that delivery mechanism is ours. The lanes follow both voluntarily pending his word, but no agent may cite either as law, hold another agent to them, or block work on them until he ratifies. Ratification is tracked on `AGENT_SYNC.md`. **`05` itself is short — read `05` in full, do not skim it.** *(This sentence previously read "It is short; read it, do not skim it" directly after naming `AGENT_SYNC.md`, so "it" resolved to `AGENT_SYNC.md` — a 400 KB, 1,300-line file. A fresh-agent audit flagged the referent as ambiguous. The short file is `05`.)*
3. `docs/governance/01-north-star-architecture.md` (The codebase structure)
4. `docs/governance/03-code-hygiene-policy.md` (Lint scope, enforcement, and unsafe-change guardrails — for Python work)
5. **The design foundation — root `PRODUCT.md` + `DESIGN.md` — only if your task touches the frontend / UI / any visual surface** (anything under `frontend/`, React/TS, CSS, a route, or a component). It is the ratified visual-design source of record (honesty is the substrate; fantasy-native legibility is the aesthetic; the product must never look like a developer diagnostics console in a fantasy skin). Claude Code loads it via the `impeccable` skill; it is also item 5 of governance 02's Required Reading Order (Codex, Gemini, and other agents read the two files directly). **Contract-green is never a visual GREEN** — the whole viewport (not the diff) is the review unit, and an independent, unanchored fresh-agent visual audit with mid-scroll captures is the standing pre-David gate.
6. `AGENT_SYNC.md` (The current sprint state — contains active blockers and script run gates)
   **HOW TO READ IT — it is ~400 KB and append-at-top.** Read from line 1 **through the `⏹ END CURRENT BOARD` marker** and stop there. Everything below that marker is **historical context and is not live unless the current board reopens it** — reading further costs context and risks inheriting superseded commands. The **topmost dated block wins**. Several older blocks still say "READ FIRST" or "READ THIS BLOCK BEFORE ANYTHING BELOW IT" — **those are stale claims from when they were newest; precedence is by position, newest first.** If two blocks conflict, the higher one governs.

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

## Environment

The project uses Python 3.14. Always invoke the project venv explicitly:

```bash
.venv/bin/python3.14 -m pytest          # run tests
uvicorn app.main:app --reload           # run the API server
```

**Run the FULL suite. There is no exclusion list, and you must not invent one.**

The invariant is **zero collection errors** — never a fixed total, and never a predicted one. *(4,335 collected is a measurement of ONE TREE: the worktree at `292c582` with the three NGS paths still untracked. Any test added, removed or reparametrized changes it. Remeasure after any edit, report what you measured, and never treat a differing count as a regression without checking what changed.)*

```bash
.venv/bin/python3.14 -m pytest          # require: ZERO collection errors. Do NOT pin a test count.
```

*This paragraph previously read: "Two test files have pre-existing collection errors and must be
excluded from standard runs — check `AGENT_SYNC.md` for the current exclusion list." **Every part of
that was false.*** No such list has ever existed in `AGENT_SYNC.md`, and `--collect-only` reports
**zero** collection errors. The instruction caused a real defect on 2026-08-03: an agent hunted for
the list, applied an `--ignore` from a stale note, and reported the scoped result as "the full
suite." **If a run needs a filter, the filter must be justified from a measurement you took in this
session — never from a remembered or documented exclusion.**

## Developer Quick Reference

After completing the governance reads, see `docs/development/quick-reference.md` for the module map, key scripts, and architecture overview.
