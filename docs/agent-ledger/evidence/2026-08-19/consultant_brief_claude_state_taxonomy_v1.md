# Consultant brief — CLAUDE CONSULTANT · independent state taxonomy

From Claude (write lane, DG cockpit) · `[w#r1-r2-group]` · 2026-08-19
**Read-only engagement. Design deliverable. No product code, no tests, no artifacts, no commits.**

You are outside the DG cockpit. Your output is **advisory input** — it is not a CLEAR and it does not
authorize work. The binding review lanes remain the in-cockpit Claude and Codex seats (`02`
§Falsification #4).

## Deliberate omission

I have my own answer to the question below and I am **not** giving it to you. `02` §No-anchor framing
bans pre-recommending a solution to a review lane, and it costs me nothing to obey it here: if your
taxonomy and mine converge independently, that is worth something; if I tell you mine first, your
agreement is worth nothing. Do not ask me for it before you draft.

## Bootstrap

Run the DG bootstrap reading order before you answer: `docs/governance/02-agent-operating-loop.md`,
`00-product-constitution.md` (especially §Descriptive Tools Issue No Verdicts — the No-Verdict Line),
`05-layer-doctrine.md` in full, then `AGENT_SYNC.md` from line 1 to the `⏹ END CURRENT BOARD` marker.
Repo: `/Users/davidleess/dynasty-genius-product`.

## The measured facts — reproduce these yourself, do not take them from me

Artifact: `app/data/valuation_runtime/universe_pvo_runtime.json` (`captured_at 2026-08-18T13:30:03Z`,
12,222 rows). Code: `src/dynasty_genius/pvo_assembler.py:412-465`, `app/api/routes/players.py:40,249,265-291`.

1. 583 rows are `identity_status = resolved` (the modeled cohort). 503 carry a `projection_2y`; 468
   carry a `dynasty_value_score`.
2. **115 rows have a null `dynasty_value_score` and a present `projection_2y`.** 114 of them carry
   `dvs_engine = "A"` and the caveat *"Insufficient professional season data — Engine A prospect score
   used as prior"*. **Zero of those 114 have an `nfl_draft_round`** — no Engine A prior existed, so
   none was used. The 115th has `dvs_engine = None`.
3. `players.py:249` computes `modeled` from `engine_path` alone. A row with `engine_path = ENGINE_B`
   and a null score is therefore reported as `model_status = "modeled"` with `degradation = None`.
4. The other branch returns `model_status = "experimental"` and *"No active model score for this
   player category."* Tank Dell — 26, WR, HOU, 3 years experience, on David's roster — takes this
   branch as `dg_status = PRE_MODEL`, while 241 WRs are in the modeled cohort.
5. On David's own 27-player roster, three cells are blank: Garrett Wilson (`ENGINE_B`, projection
   11.255), Braelon Allen (`ENGINE_B`, projection 4.899), Tank Dell (`PRE_MODEL`, no projection).
6. Elsewhere, Ashton Jeanty (DVS 75.3) and Rasheen Ali (20.7) render blank because a Roster Audit gate
   deliberately suppresses actives — the score exists and is withheld on purpose.

## Your question

**What is the complete set of states this system actually occupies between "we have a score" and "we
have nothing", and what must each one say to David?**

Deliver:

1. **The enumerated state set**, derived from the code and the artifact — not from a plausible-sounding
   taxonomy. For each state: its machine-checkable predicate, how many rows occupy it today (measure
   it), and the one sentence it should say to a fantasy manager.
2. **Which states are indistinguishable today** and what each costs David when confused with another.
3. **The naming trap.** `00`'s No-Verdict Line bans a descriptive surface from emitting a verdict. A
   state name like "insufficient data" can be heard as *avoid this player* when the deficiency is
   ours, not his. Name every candidate label you reject and why.
4. **Where my framing would be wrong.** You will be shown
   `r1_r2_group_framing_claude_v1.md` **only after you deliver** — at that point, list every place your
   independent taxonomy disagrees with it. Those disagreements are the actual value of this engagement.

## Constraints

- Descriptive only. No buy/sell/hold, no tier labels, no recommended ordering. Read `00` §No-Verdict
  Line before naming anything.
- No new governance layer, registry, or review protocol. David has ruled repeatedly against process
  artifacts on this thread.
- Cite `file:line`, a query, or a reproduced count for every claim. Uncited is worth nothing here —
  that is how a wrong diagnosis survived eleven days on this exact ticket.
- Do not read, write, or touch `/Users/davidleess/frontend-studio` (standing wall TW29-WALL-35).
