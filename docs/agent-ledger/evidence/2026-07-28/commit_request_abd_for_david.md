# TW28-COMMIT-1 — Thread 1 (A/B/D) commit request, for David

**For Tower to carry. Plain terms, no engineering.**
**Authority sought:** a fresh commit word. David's existing word was *"ship the honesty fix and commit the
file"*; he then said *"bring me the commit when the tollgate passes."* This is that request.
**Not sought here:** a push. That stays a separate word.

---

## 1. What is in this commit

Three things, all protective. None of them changes a number the app shows.

1. **The daily refresh can no longer publish a model-less board in silence.** If the file that connects
   the model's players to your league's players is missing or corrupted, the refresh now **stops and says
   why** in its status report. Before today it carried on and published a board with no model values that
   passed every internal check.

2. **Every player the refresh drops is now named.** Previously a player who couldn't be matched simply
   vanished with no record anywhere. The refresh now counts them and writes down who they were. On today's
   data that is the two players you already know about — Nick Kallerup and Ke'Shawn Williams.

3. **The connecting file itself is now permanently preserved in the project.** It was a single 3.8 MB file
   sitting on this laptop only, backed up nowhere, and losing it would have taken every model value on the
   board with it.

## 2. What changed since you said "ship the honesty fix and commit the file"

Four things. Two are scope you did not authorise at the time, which is why this asks again.

- **You split the work** ("split it"), so this commit is the protective half only.
- **Codex found two ways corrupted data could still slip through quietly**, and I fixed both. That
  hardening was **not** in your original word. In plain terms: a data file could have quietly swapped one
  player's identity for another's, and a file with damaged characters would have put unreadable technical
  gibberish into the status report instead of a clear reason.
- **A third instance of that same weakness exists elsewhere** — in the part that reads your league snapshot
  and rookie cards. **I did not fix it**, because it was outside what the review had scoped, and widening
  scope on my own judgment is not mine to do. It is written down as a follow-up.
- **The commit changes a project rule** so that this one file is version-controlled from now on, while
  everything beside it stays excluded as before.

## 3. Things in this commit you have not been told

**Two, and the first one matters most.**

**① This commit does NOT fix the wrong message on your player cards.** You authorised "the honesty fix,"
and the thing that most looked like a lie — a player card telling you *"no active model score for this
player category"* when his category is modelled — is **Thread 2, and it is not in here.** It is still being
argued over, correctly, because it is your on-screen wording. If you approve this commit, that false
sentence is still on your screen tomorrow morning. Also still untouched: the 113 players shown as
"Modeled" with no value, and the non-player entry that answers as if it were a person.

**② Your daily refresh can now fail loudly where it used to succeed quietly.** That is the point of the
fix, but it is a real operational change: if that connecting file ever goes missing or gets damaged, you
will get **no fresh board that morning** and a status report saying why, instead of a board that looks
normal and is empty underneath. I judged a visible failure better than an invisible one. If you would
rather it degrade some other way, that is your call and better made now than after a morning it fires.

## 4. What this commit is worth, stated without inflation

It closes the risk you named when you split the work: an app that publishes an empty board with no error.
It does **not** improve any valuation, fix any wording, or change any number you read. On today's data its
visible effect is two players' names appearing in a diagnostic record you don't normally look at.

## 5. Verification behind it — both gates are now real

- **The tollgate passed.** All three enforced checks green: full test suite, lint, and standalone-script
  loading. That is the condition you attached to this request.
- **The independent reviewer has signed off.** Its clearance landed on disk while the tollgate was
  running (11 enumerated checks, 43 tests run independently). Earlier today I told you this sign-off was
  outstanding — **it has since arrived, and I read it before writing this rather than reporting the older
  state.** It specifically cleared the two riskiest judgment calls I made: the way the new counting is
  carried, and my removal of an old guard, which it confirmed does not reopen the problem that guard
  covered.
- It reproduced the numbers on live data independently: 503 players scored, 501 matched, and exactly the
  two you know about dropped — both for the same reason.
- The connecting file still reads identically after the change, so **nothing about today's board moves.**
- **One audit item the tollgate flagged, checked rather than waved through:** it asks whether a newly
  tracked data file sits in a protected directory needing your separate authorisation. It does not — the
  project's storage rule protects four other directories, not this one. Worth knowing anyway: the
  project's own ignore file says artifacts in this folder "are committed only after David approval,"
  which is precisely why this is in front of you.

## 6. What is deliberately not here

The player-card wording, the 113 "Modeled" rows, the non-player entry, the question of how much missing
data should stop a refresh (still yours to decide), the identity rewrite, and the two tickets you parked.
