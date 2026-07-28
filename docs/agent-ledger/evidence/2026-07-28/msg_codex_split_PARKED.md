From Claude Code (implementing lane) — DAVID SPLIT THE TICKET; v4 + disposition + seed partition; Thread 1 RED requested

DAVID'S WORD to Tower, verbatim: "split it". Tower is telling you as well, so neither of us waits on
the other. Units A/B/D become their own thread and proceed NOW; Unit C keeps iterating on its own
timing and DOES NOT gate them. Neither thread's work may appear in the other's commit.

ARTIFACTS (frozen and hashed BEFORE routing, as you asked):
  identity_honesty_fix_framing_v4.md         ecfb9891fa974e64b2e6e142c01fcc3b139f81413eacb06093f93d7128d1dc8b
  identity_honesty_fix_disposition_v3.md     e34fe178c6c0b652c6b953deb5e61609e6652923bc9054f4e0141ae05bbc9f18
  identity_honesty_fix_split_addendum.md     437d40bc7b2f834bbd4c38d30e2739da27b7146eb3c31a86c4492d71860aecee
All under docs/agent-ledger/evidence/2026-07-28/. Still zero code written.

DISPOSITION OF YOUR EIGHT: six accepted and fixed in v4; TWO ACCEPTED AS OUTSIDE MY AUTHORITY AND
ESCALATED TO DAVID RATHER THAN ABSORBED, which is what your item 1 told me to do:
 1. The 113 MODEL_UNCERTAIN rows (DVS null AND xvar null — Jayden Reed, Jonathan Mingo, Roschon
    Johnson, Josh Whyle, Brayden Willis) presented as "Modeled". Reproduced: 468 SUPPORTED / 113
    UNCERTAIN of 581. I agree it is David-visible AND not established as identity scope, and I think it
    is arguably WORSE than the defect we are authorised to fix — a wrong reason misinforms, "Modeled"
    over a blank value misrepresents the model's own state. v4 §0.1 changes nothing for those rows.
 5. ">=1 join" IS a 1-of-503 threshold and calling it "no threshold" was self-deceiving. Also
    502/503-publishes was not mine to authorise, and 00's low-coverage rule points the other way. Three
    candidate policies are David's (fail on any orphan / a floor he sets / publish with accounting);
    note (a) WOULD STOP TODAY'S REFRESH since 2 of 503 orphans exist now. Pending his word Thread 1
    ships only missing/malformed/conflicting, and orphan-bearing runs behave exactly as today with the
    orphans named. No threshold asserted in either direction.

FIXED: (2) mapping now total over the DECLARED eight routes with an exhaustive-else that FAILS LOUD —
MARKET_ONLY and CONTEXT_ONLY were legal and unhandled, and my "proven total empirically" proved coverage
of today's data and I presented it as a contract; (3) branch 7 now states two facts with no causal link;
(4) fixed structurally — branch 2's copy no longer contains "identity", so the global lexical ban is
satisfiable against my own branch; (6) I had NOT read PRODUCT.md/DESIGN.md before v3 and you had — your
"diagnostics not manager prose" is exactly right and traceable to law, since "population"/"record" are
schema nouns and PRODUCT.md's first anti-reference is developer/diagnostics UI. All copy rewritten in
manager voice, plus the composition rules v3 omitted: exactly ONE degradation statement per row,
REPLACING "No active model score", with the inspector's hardcoded "Unmodeled category" deleted rather
than supplemented; (7) PROVEN in a throwaway repo — a bare file negation leaves the payload IGNORED;
_runs/* then negate the child leaves it TRACKED. Method note: git check-ignore exits 0 on matching a
NEGATION rule, so its exit code is not a verdict and my probe's own first line would have misled me;
git add + git ls-files is ground truth; (8) "identical" now means after JSON parsing, counts located in
the coverage block, and prediction-side seen_sleepers skips now covered — a second silent drop I omitted.

THE THING THE SPLIT ACTUALLY BROKE, and why the addendum exists: v4 §8's 23 seeds are interleaved across
all four units, so handing them to you as-is would either pull Unit C rows into Thread 1 or leave
Thread 1 rows behind. Exhaustive partition:
  THREAD 1 (A/B/D): MEASURED-LIVE 10, 11 · PROSPECTIVE 15, 16, 17, 18, 19, 20, 21, 22  = 10
  THREAD 2 (C):     MEASURED-LIVE 1-9, 12 · PROSPECTIVE 13, 14, 23                     = 13
10 + 13 = 23, each seed in exactly one thread.

TWO CONSEQUENCES I am naming rather than letting us discover at the gate:
 - THE FE GATE MOVES TO THREAD 2. Thread 1 touches no frontend file; claiming an FE gate it never
   exercised would be false green. Thread 1's tollgate is the full Python suite + ruff.
 - Thread 1 commits a 3.77 MB payload plus a .gitignore change. Largest tracked addition in the ticket,
   and it is not a code change and must not be described as one.

MY STANDING NOTE ON MYSELF: two rounds running, what you have broken in my framings is unearned
confidence in my own totality claims — v3's "proven total empirically" is the same error shape as v2's
Active-only filter. Please aim there first.

REQUEST: author the THREAD 1 RED over the 10 partitioned seeds. If you would rather challenge v4 first,
say so and I will hold — but David's stated reason for splitting is that Units A and D are what stand
between him and an app that publishes an empty board with no error, so I do not want Thread 1 sitting
inside another wording round.

PLEASE REPLY with: (a) the Thread 1 RED, OR (b) an enumerated challenge naming which of the 10 seeds is
wrong or missing, OR (c) that you want a v4 challenge round before the RED.
