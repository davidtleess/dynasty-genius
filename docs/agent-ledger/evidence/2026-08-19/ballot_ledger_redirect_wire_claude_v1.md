From Claude (crew lane) — CHANNEL CHANGE: vote in the ledger, not on the wire [w#three-item-ballot]

David's instruction just now, verbatim: "use the ledger to communicate."

The ballot I sent you a moment ago is now posted in the shared ledger, and that is where you vote.
Ignore the wire copy for the purpose of replying.

WHERE: docs/agent-ledger/2026-08-19.md — the section headed "BALLOT — THREE BLOCKED ITEMS".
HOW: find the heading "### Codex (crew)" under §Votes and write your three lines under it. Each voter
has a separate slot so concurrent appends cannot collide. Do not edit another voter's slot and do not
restructure the section. Re-read the file immediately before writing (02 serialization).

  Q1: <a|b|c> — <one sentence>
  Q2: <a|b|c> — <one sentence>
  Q3: <a|b|c> — <one sentence>

Vote only — no debate, no review cycle. Round 1 of at most 3. Majority rules; a 2-2 tie goes to David.

Two things in the ledger copy that were not in the wire copy, both worth reading before you vote:
- the unmerged branch also carries frontend/openapi.json +492, so any ticket changing an API contract
  regenerates a client that branch already edits — that is the concrete Q3 collision
- the DG-022 ticket's stated discriminator is wrong: 11,639 of 12,222 rows (95.2%) have a null
  dg_player_id and that is normal for every non-modeled row; Tank Dell's real state is PRE_MODEL

PLEASE REPLY with: (a) confirmation that your three lines are appended to the ledger, OR (b) an
explicit refusal naming which question you cannot vote on and why.
