# DG-168 handoff checkpoint — 2026-09-06

Written so this branch survives a session restart. Nothing here is landed and nothing
has reached David.

## Branch state

`ticket/DG-168`, four commits on top of `origin/main`:

    fbbf1908  make the asset number durable (it existed only in /tmp)
    7997c653  the dominance screen, and the translation was pointing the wrong way
    6a0018ac  pin the market read to the LIVE file, not the worktree copy
    1d843d00  the format translation fails closed on an unmeasured source
    2d91f244  this handoff checkpoint
    a375d543  tests — and the first one found the refuter discarding every
              contradiction it exists to find

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

## Tests (added after this checkpoint was first written)

`tests/contract/test_dg168_dominance_screen.py`, eight tests. **The first one found a
real defect within a second of existing**: `format_explains` tested whether translation
preserved the SIGN of the price difference, but the pairs this screen exists to find are
priced within 10% of each other, so for two players at the SAME price it returned
"explained" every time and discarded them. **The refuter was throwing away every
contradiction the screen was built to find**, and a day of hand-running had not noticed.

That was the second time that function was wrong, in the opposite direction from the
first. Correct form: the format explains a gap when the DOMINANT player's position
carries the larger correction. Live run went 111 pairs -> 146 once identical-price pairs
stopped being discarded.

Writing the tests also corrected my own reasoning — the fixture I first wrote asserted a
receiver beating a tight end should be discarded, and it should be kept.

## What still needs tests

* **No point-in-time leakage test** — nothing asserts the board and market vintages
  match, and a mismatched pair would produce confident nonsense.
* **Nothing enforces that rookies stay out of the screen.** Greg's ruling 2026-09-06:
  rookies get a number on the board but do NOT enter dominance pairs, because for a
  rookie one axis is a probability and a wrong probability turns a hedged number into a
  confident false claim about a trade. Currently held out only by the input file.

## What is NOT proven, and must be labelled

Every pair is a **hypothesis**, not a realised edge. Nothing here has been graded
against an outcome. The screen finds the market contradicting itself on facts we
measured; whether we or the market are right is a season away.

⚠ And the overpaid tight ends all produce within a point of replacement, so the
finding rests on **our** tight-end bar. Thirteen tight ends clear the bar by more
than 1.0 and McBride clears it by 7.5, so the position is not uniformly compressed —
but a reader should know the claim depends on a number we chose.

## Next action

Two tests remain (point-in-time vintage match, and rookies held out structurally rather
than by input). Then, and only then, put the handful of sentences to David — rookies
excluded pending independent reproduction of `P(ever qualifies)`, and every pair
labelled a hypothesis rather than an edge.

Separately filed: **DG-176**, the 23-and-under quarterback and tight-end coverage hole
that leaves Mendoza — third on David's roster — with no cell. Rookie pricing neither
caused it nor fixes it, and it would be buried inside this ticket.
