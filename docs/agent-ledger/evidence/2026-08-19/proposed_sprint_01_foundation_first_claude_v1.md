# PROPOSED — SPRINT 01 · foundation first

**Status: PROPOSAL. Not open. David sets the goal and the order — this is a draft for him to cut.**
Drafted by the crew Claude lane, 2026-08-19 07:1x ET, at David's word *"lets tackle the tickets as a
group — everything coordinated."* Board of record: `~/dg-build/BOARD.md` (DG 3.0).

*(Written here rather than `~/dg-build/sprints/` only because this lane's sandbox permits writes to
the product worktree alone. If David wants it on the board, it moves.)*

---

## Goal sentence

**Stop the product saying false things about itself, and make layers 1 and 2 complete enough that
layer-3 work means something.**

---

## The coordination finding this sprint is built on

**24 of the 30 tickets on the board are layer 3.** Six are not:

| Layer 1 — ingest | Layer 2 — curate |
| :-- | :-- |
| DG-012 news/injury/pressers as features | DG-013 as-of-date feature store |
| DG-020 more than four market snapshots | DG-022 players that can never be graded |
| DG-023 health calls good data "empty" | DG-029 is 2024 a gap or a design |

`05` §1.2, **David's own words, verbatim**: *"Steps 1 and 2 are the foundation - if we don't have this
our app WILL NOT WORK. we shouldn't be wasting cycles until we've built this foundation."* And §1.3,
his 2026-07-30 amendment: *"everything must start with a robust and complete layer 1 and 2."*

Turning eight lanes loose on a board that is 80% layer-3 would contradict his own standing rule at the
exact moment we finally have the people to obey it. **That is the whole argument for this sprint's
shape** — it is not a preference about tidiness.

**The one exception, and why:** DG-021 is layer 3 → 6 and belongs in the sprint anyway. It is the only
ticket on the board where **the product tells David something false** — 114 player cards state that an
Engine A prior was used when none exists, and the API reports them `modeled` with `degradation=None`
while the score is null. Everything else on the board is a number being worse than we would like. That
is a different category of defect and it outranks the layer rule on its own merit.

---

## Tickets in

| ID | Layer | Why it is in this sprint | Claim state as of 07:1x |
| :-- | :-- | :-- | :-- |
| **DG-021** | 3→6 | the only false statement to David's face | **claimed — CodexTeam20260819** |
| **DG-022** | 2 | rostered players that can never be graded, silently | worktree exists; lane field still `—` |
| **DG-023** | 1 | the health gate that graded a broken feed `fresh` — it built the store DG-021 and DG-029 are about | unclaimed |
| **DG-029** | 2 | until this is answered, nobody knows whether the store is whole | unclaimed |
| **DG-013** | 2 | as-of-date feature store — DG-026's train/test leak cannot be fixed without it | unclaimed |
| **DG-020** | 1 | four market snapshots is not a series; every market ticket downstream is blocked on it | unclaimed |

**Held back deliberately:** DG-012 (layer 1, but a new ingestion source — a large build, and `02`
§Escalation Triggers makes a new external data source David's call, not a lane's).

**Not in, and not by accident:** every layer-3 modelling ticket. DG-002, DG-014, DG-017, DG-025,
DG-026, DG-027, DG-030 are real and several are serious — DG-017 is already `confirmed`. They are next
sprint, on the foundation this one builds. David's "not before Week 1" ruling of 2026-08-18 also bars
market-superiority work (DG-018, DG-019) and any large unvalidated model push in late August.

---

## Why six and not twelve

`dg-land.sh` lands **one ticket at a time behind a lock**, rebasing and running the full suite each
time. Lanes are parallel; **landing is serial.** Past six or so concurrent tickets we are not building
faster, we are building a merge queue — and every lane that finishes early sits on an unlanded branch
rotting against trunk. Six is sized to the lock, not to the number of people available.

---

## Two facts every lane needs before it starts

1. **The 09:00–10:15 ET window.** Ten launchd jobs write to `app/data` in it. It is 07:1x now. Any
   lane needing a stable read of a shared store should take it in the next ninety minutes or wait
   until after 10:15.
2. **`app/data` and `.venv` are symlinked read-only** into every worktree. Writing through a symlink
   writes to the real 15 GB store. A ticket that genuinely needs to write asks for `--writable <path>`.

---

## Evidence this lane already has, and who should get it

Measured this morning against `app/data/valuation_runtime/universe_pvo_runtime.json`
(`captured_at 2026-08-18T13:30:03Z`, 12,222 rows) and source. Both items belong to lanes that are not
mine — they are handed over, not acted on.

**To the DG-021 lane (CodexTeam):** the ticket reproduces exactly. 115 rows carry a null
`dynasty_value_score` with a live `projection_2y`; 114 of them carry `dvs_engine="A"` plus the false
prior caveat; **0 of those 114 have an `nfl_draft_round`**, so no prior existed. The surface half is
`app/api/routes/players.py:40,249` — `modeled` is derived from `engine_path` **alone**, never from
whether a score exists, which is why a null score is served as `model_status="modeled"` with
`degradation=None`. Full framing, falsification seeds and the No-Verdict-Line check:
`docs/agent-ledger/evidence/2026-08-19/r1_r2_group_framing_claude_v1.md`.

**To whoever takes DG-022 — a correction to the ticket text.** It reads *"carry `dg_player_id: None`
in the served artifact."* True, but it is not the discriminator: **11,639 of 12,222 rows (95.2%) have
a null `dg_player_id`**, and that is normal for every non-modeled row. Tank Dell's actual state is
`dg_status = PRE_MODEL` — a 26-year-old rostered Houston WR with three years of experience, sitting
outside the 583-player modeled cohort with **no caveat and no risk flag**, while 241 WRs are modeled.
He is one of **10 rostered players** league-wide in that state. A DG-022 fix written against the null
id would pass its own test and miss the defect.

---

## Open question this sprint cannot answer for itself

**Where does a lane's ledger entry go?** `CLAUDE.md` and `02` §Postflight require every session to
append to `docs/agent-ledger/YYYY-MM-DD.md` **in the trunk**. The parallel-work protocol §1 says never
write to the trunk. With eight lanes running, all of them hit this today, and it is not a lane's
conflict to resolve alone (`02` §Authority Order: stop and log, do not silently pick the more
convenient rule). Raised for David.
