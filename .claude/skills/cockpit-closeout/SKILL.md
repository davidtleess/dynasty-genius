---
name: cockpit-closeout
description: Use when a Dynasty Genius cockpit closeout is announced, when ending a material session, or when about to report a closeout status — covers the durability gate, the disclosure rows, the cross-lane audit, and which status word a lane is allowed to claim.
---

# Cockpit Closeout

Run this whenever Tower announces a closeout, or before reporting any closeout status.

**Governing fact:** conversation memory does not survive the session. Anything not
**committed** is at risk; anything only in `/tmp` or a session scratchpad is already lost.

**The rule this skill exists to enforce:** on 2026-07-25 a lane reported `closed — clean`
while the session's entire postflight record sat uncommitted in a working tree, the
closeout order asserted four repo facts and was wrong on all four, ~30 evidence artifacts
existed only under `/tmp`, and a known dangling citation shipped inside the "clean" close.
None of it was caught by the code gate, because the code gate was green.

## Order of operations

Do these in order. Steps 1–3 are the precondition for step 4, not a follow-up to it.

### 1. Reach a clean stopping point

Finish the step in progress to a coherent on-disk state. Never abandon an edit, commit,
or test run mid-change — a half-applied change is worse than a parked one. If it will not
settle quickly, **park it explicitly**. Rushing to finish is not closing.

### 2. Write postflight, then COMMIT it

Append the session entry to `docs/agent-ledger/YYYY-MM-DD.md` and update `AGENT_SYNC.md`
for state this lane changed (re-read `AGENT_SYNC.md` immediately before writing; merge,
never clobber a peer's section).

Then **commit them**. State-doc flushes are verifier-exempt maintenance — committing them
does not need a fresh David word, and leaving them uncommitted is the failure this rule
was written from. Code, tests, config, specs, and governance still need cockpit CLEAR +
David's word; those get **parked**, not rush-landed to beat the deadline.

### 3. Run the durability gate

```bash
.venv/bin/python3.14 scripts/verify_closeout.py
```

It is read-only. Its exit code decides **which status word you are allowed to use**:

- **exit 0** → you may report `closed — clean`.
- **exit 1** → you may **not** claim clean. Report `closed — parked` (or
  `closeout-blocked`) naming every ENFORCE reason. **This is a successful closeout.**
  A truthful `parked` is the point of the vocabulary; a false `clean` is the failure.

What it enforces, and the defect each one comes from:

| ENFORCE check | Defect it prevents |
|---|---|
| `durable-record` | CLOSED declared with the ledger + board uncommitted |
| `working-tree` | "confirm six uncommitted files" when there were eight |
| `ephemeral-locators` | evidence cited at `/tmp`, a scratchpad, or a hardcoded `/Users/...` |

(`citations` is REPORT, not ENFORCE — see below.)

Its REPORT blocks (`repo-facts`, `pushed-ci`, `session-commits`, `background`) are the
facts your status reply must carry. Paste them; do not recollect them.

**No exemptions on `ephemeral-locators`.** The rule is simply: never write a
session-scoped or machine-bound locator into the closeout record. To discuss one,
describe it — "a session-scoped temp path" — rather than reproducing it. The waiver
system that used to live here was deleted (David, 2026-07-26): it generated more defects
than the check it guarded.

**Citations are a REPORT, not a gate.** Unresolved repo paths and `commit <sha>`
references are listed for you to audit. A genuine dangling citation is a real defect —
the 07-25 close shipped one — but whether a path-shaped string is a binding citation or
a quoted example is not decidable from prose, so a human decides it, not a regex.

### 4. Reply with a status, never a bare "done"

- **`closed — clean`** — gate exit 0, nothing uncommitted, nothing half-done, no open
  post-commit audit.
- **`closed — parked`** — postflight committed, but named work is deliberately parked.
  The reply carries each item's **location, state, and next gate**: "parked at `<path>`
  on `<branch>`, 17/17 green, awaiting Codex CLEAR + David push".
- **`closeout-blocked`** — cannot reach a clean or cleanly-parked state; say exactly what
  is unsettled and where.

Delivery-verify the reply (`cockpit-messaging` skill). **A stranded `closed` is not a close.**

## The disclosure rows

The standard closeout used to ask only "uncommitted / half-done / background". On
2026-07-25 it took a special David-ordered accountability probe to surface ten carried
items — including a placeholder written into a production `__init__.py`, a 12× rewrite of
a numerical core taken on the lane's own judgment, and a contradiction between two of
David's own rulings resolved unilaterally. **Those questions are now standard.** Answer
each with a concrete item or `NONE` — never silence:

1. **Authority.** What decision did I take that was arguably David's or another lane's to
   make? (a ruling conflict resolved alone, scope beyond the word given, a contract widened)
2. **Unverified claims.** Which load-bearing numbers or claims did I use but not
   independently check? Name each with its provenance lane.
3. **Deferred work.** What authorized work did I quietly park? Filing it as a future
   ticket is still deferring it.
4. **Never told to David.** What am I carrying that has not reached him — including
   things that feel too small or too awkward to mention?
5. **Open loops.** For every commit this session: is its independent post-commit
   divergence audit CLEAR, or open with an owner? **An open audit means `parked`.**
6. **Background.** For each process the gate lists: did THIS session create it? A
   pre-existing process is not yours to stop, but it is yours to disclose.

## Cross-lane closeout audit

**A lane may not audit its own close.** On 2026-07-25 self-evidence failed repeatedly
(a 27/27 self-probe missed six defects that independent review found) and the independent
lane caught it every time — including, during the rescue itself, six dead `/tmp` citations
and a reproducer that only ran on one machine.

So: each binding lane's closeout claims are verified by **the other binding lane** —
Claude audits Codex's, Codex audits Claude's — against the repo, not against the prose.
Tower ushers and sequences; Gemini receives awareness copies (Operations & Telemetry seat,
no judgment lane). The audit is cheap: run the gate, read the REPORT blocks, check the
disclosure rows for `NONE`s that look too tidy.

## Verify the verifier

A closeout **order** is prose written from conversation memory; repo state is a fact.
On 2026-07-25 the order asserted HEAD, which files were committed, what stayed
uncommitted, and a reviewer's clearance — and was wrong on all four.

**Never confirm a repo-state assertion you have not read from the repo yourself.** If a
closeout order states a SHA, a file's committed status, or a lane's clearance, check it
and correct it in your reply. Verdicts are verified against the ledger, never against
pane text.

## Flush vs terminal close

The 2026-07-25 close reopened four times — each a legitimate new David word, and a lane
does not refuse those. But a close that reopens four times is a pause with a ceremony
attached, and the word stops meaning anything.

- A **flush** is repeatable and cheap: postflight written, committed, gate run, status
  reported. Do it as often as the session needs.
- A **terminal close** happens once and ends the session.

New David work after a flush **reopens the session** — say so plainly and re-flush. Do not
spend the word `closed` on a close you expect to reopen.

## When the wire is down

Delivery is not durability. If a report cannot be delivery-verified, **the repo is the
delivery channel** — commit the artifact and cite its committed path. Hand-carrying a
`/tmp` path is how ~30 artifacts nearly left the session with no durable trace.
