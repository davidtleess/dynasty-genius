# DG-168 handoff checkpoint — 2026-09-06

Written so this branch survives a session restart. Nothing here is landed and nothing
has reached David.

## Branch state

`ticket/DG-168`, four commits on top of `origin/main`:

    fbbf1908  make the asset number durable (it existed only in /tmp)
    7997c653  the dominance screen, and the translation was pointing the wrong way
    6a0018ac  pin the market read to the LIVE file, not the worktree copy
    1d843d00  the format translation fails closed on an unmeasured source

⚠ **`scripts/dg168/rookie_probability.py` IS COMMITTED, in `1d843d00`, and should not
be.** A coordination message asked for it to be left uncommitted as another lane's
concern; by then `git add -A scripts/dg168` had already swept it in. It is on an
unlanded branch so it affects nobody, but it is in the history and saying so is
cheaper than a silent rewrite. Removing it is one `git rm` and a commit if Lane A
wants the file to itself.

## What is validated

* **The screen finds 111 contradictions** on live data — 55 overpaid, 55 underpaid,
  spread WR 23 / RB 15 / TE 9 / QB 8.
* **The tight-end result is robust to the translation.** Run three ways — no refuter,
  translation as refuter, translation *inverted* — the same five tight ends top the
  list every time. That matters because an earlier version's loudest finding WAS an
  artifact of the translation.
* **Point-in-time consistent**: board and market both 2026-09-05.
* **Practical margins, not epsilons**: 10% price band, 15% required edge on each axis.
* **Fails closed on an unmeasured market source** rather than defaulting to 1.0.

## What depends on DG-169

The factors (TE 1.96, QB 1.95, WR 1.45, RB 0.98) are Bob's and are keyed to
**FantasyCalc's** baseline. Live overlay is 397/397 fantasycalc at one timestamp, so
the single table is correct today. A second source needs its own measured row.

## What still needs tests

* **No test exists for the screen at all.** The mechanics have been exercised by hand.
  At minimum: a fixture pair that must be found, a fixture pair the format explains
  that must be discarded, and a pair below the margin that must not fire.
* **No test pins the fail-closed behaviour** of `translation_for()`.
* **No point-in-time leakage test** — nothing asserts the board and market vintages
  match, and a mismatched pair would produce confident nonsense.

## What is NOT proven, and must be labelled

Every pair is a **hypothesis**, not a realised edge. Nothing here has been graded
against an outcome. The screen finds the market contradicting itself on facts we
measured; whether we or the market are right is a season away.

⚠ And the overpaid tight ends all produce within a point of replacement, so the
finding rests on **our** tight-end bar. Thirteen tight ends clear the bar by more
than 1.0 and McBride clears it by 7.5, so the position is not uniformly compressed —
but a reader should know the claim depends on a number we chose.

## Next action

Write the three tests above. Then, and only then, put the handful of sentences to
David — with rookies excluded pending Lane A, and every pair labelled a hypothesis.
