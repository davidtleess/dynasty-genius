From Claude Code (implementing lane) — v21 GREEN ATTEMPT FAILED AND IS REVERTED. Tree restored.
Not contesting any contract.

I reproduced your frozen pin and baseline exactly first: RED `528afecd…`, 6,604 lines / 254,583
bytes; **602 = 24F + 578P, exit 1**. Confirmed.

I then attempted all four families and REGRESSED the module to **90 failed / 512 passed** — 66
inherited contracts broken, including v10_h2 central-sequence, v10_h3 attempt-sequence predicate,
v10_h4 read-clock validated-once, and even your own v21 exact-bootstrap-marker positive. I did not
thrash on it. I reverted all five edits and re-verified:

  GREEN back to `6fbac8af65c5f0c2eba92688a4ee7c600e0949b644262fc304a166076e2d14ca`
  census back to **24 failed / 578 passed** — your baseline, exactly.

The tree you review is the gated v20 GREEN, unchanged. Nothing of mine is left in it.

WHAT I GOT WRONG, so v21 does not repeat it:
1. My `read_model` entry-check on `now` collided with the v10_h4 contract, which validates the
   CLOCK dependency and expects a specific ordering. I short-circuited before that, so
   "validated once and reused" and the naive-clock case both changed behaviour. The `now`
   validation has to compose with the existing clock contract, not precede it.
2. My `_classify_attempt_sequence` was too broad — I keyed ghost detection off "name not in
   tables" using the acquisition store's table set, which also caught legitimate central-sequence
   states. The sequence contract needs to be scoped to `attempts` specifically.
3. Fixes 1 and 3 (the `_store_rows` read-all and the future-`user_version` refusal) may be sound
   on their own; I could not separate them from the regression before reverting and I will not
   claim them untested.

ON YOUR C1, WHICH I OWN: the NULL-blind `offering_id != '_bootstrap'` in `_store_rows` is the SAME
pattern I repaired in the migration path at v18-H3. I fixed the concept in one place and never
swept the codebase for the identical comparison. That is a post-fix-sweep failure, not bad luck,
and it is the second-highest-value thing you found tonight after the WAL-before-validate class.

I am NOT contesting any of the four contracts. All four ACCEPTED. I am out of working context to
land v21 responsibly tonight, and a half-repaired persistence layer left in the tree overnight is
worse than a clean v20. Keep RED v21 frozen at `528afecd…`; the next implementing session
reproduces 24F/578P and starts from the three notes above.

Separately in the tree, unrelated to this pair and NOT part of your review: David's approved
realized-outcome scorer wiring in `scripts/run_realized_outcome_scoring.py` (prediction loader
wired to the real capture store, 501 predictions, undeclared-freeze now fails visibly instead of
noop-as-success). 64 realized-outcome contract tests pass. Flagging it only so the dirty tree is
not a surprise.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D occurred. H2 QB rushing
remains UNDER TEST with no result.
