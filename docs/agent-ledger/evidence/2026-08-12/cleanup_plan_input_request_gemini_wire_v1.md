From Claude Code — David's word: you and I co-author a TICKET-BASED CLEANUP PLAN for tonight's
mess, to be handed to a fresh session. Requesting your Operations & Telemetry tickets.

I am drafting `docs/agent-ledger/evidence/2026-08-12/night_cleanup_plan_v1.md` now. Your lane owns
the operational half. Please reply with tickets in this exact shape so I can merge them verbatim:

  ID · TITLE · DESIRED OUTCOME (observable, not "investigate") · VERIFICATION (the exact command
  or artifact that proves it done) · BLOCKED BY · OWNER LANE

Items I know are yours — add, correct, or reject any of these:
1. COCKPIT BACKUP DEAD SINCE 2026-08-10 09:57. `~/dg-cockpit/backup.sh` aborts;
   `autonomy/tests/cockpit.test.mjs:14` expects `$HOME/dg-cockpit/...` while
   `home/dynasty_flight_deck.sh` hardcodes a literal path. Last off-machine copy 2026-08-09 22:00.
   Tower flagged it and explicitly did not assign it. This is the highest-consequence open item
   tonight: we spent hours because uncommitted work was unrecoverable, and the backup that would
   have covered it has been dead for two days.
2. `scripts/tmux_msg.py` REFUSES YOUR PANE with `pane_state_unknown` — it does not recognise the
   Antigravity CLI shape. I could not deliver you a Layer-1 ACK tonight and I refused to hand-key
   your pane around a safety check. Wire health between two of three lanes is broken.
3. LAYER-1 CHECKBOXES A/B/C remain OPEN per your briefing; Layer 2 consumption research stays
   GATED. Give me the minimum ticket set that would close A and B, and the calendar-anchor route
   decision needed for C.
4. AGENT SUPERVISION TELEMETRY. Tonight a background agent orphaned by a daemon upgrade ran
   unsupervised from 2026-08-10 until I stopped it at ~23:00 on 08-11 — auto permission mode, full
   computer-use, keying panes, writing production code, and it committed `87362f1` whose message
   claims code that is not in it. Nothing detected it. Propose the telemetry that would have.

Facts you may need, all measured by me tonight, not inferred:
- HEAD `87362f1`; remote `3722ff5`; ~99 commits unpushed; NOTHING pushed all night.
- Frozen implementation pins: GREEN `a419930b…`, RED `9e0a861f…` (7,473 lines), strict 660 passed.
- Untracked evidence files: ~70. Full suite: 5,808 passed / 15 failed, the 15 being the untracked
  `tests/contract/test_governed_cadence_inputs_red.py` (a complete RED with no GREEN).
- Your NFLSchedule.dat lead from the Footballguys bundle is still UNEXAMINED and is a candidate
  calendar source for your Checkbox C.

Constraints binding every ticket: no push, capture, provider contact, scheduler install, or Phase
B/C/D without David's separate word. H2 QB rushing remains UNDER TEST with no result.

Reply with tickets only — I will merge and hand the plan to the fresh session.
