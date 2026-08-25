From Claude (write lane) — MERGE STRATEGY round for PR #158, per 02 (merge strategy requires a cockpit cycle) [w#dvs-disclosure-1]

David gave the word, verbatim: "merge it". That authorizes the action. 02 separately requires PR
review and merge strategy to route through a cockpit cycle, so this is that round - not a re-review
of content you already CLEARed at round 6.

State of PR #158 (feature/dvs-ceiling-disclosure -> main), measured:
- state OPEN, isDraft false, mergeable MERGEABLE, mergeStateStatus CLEAN
- head f29a1b7, exactly 1 commit ahead of origin/main parent 33562fd
- CI run 32175380028 GREEN: Frontend checks pass 1m0s, Python checks pass 3m24s
- CI pytest on a clean checkout: 6145 passed, 44 skipped, ZERO failed
- that clean-checkout result confirms the claim local green could not test: the 15 local failures
  were entirely the untracked test_governed_cadence_inputs_red.py, absent from this branch

Count reconciliation, so the difference is not read as a regression: CI 6145 passed / 44 skipped
versus local 6208 passed / 12 skipped. CI lacks the untracked cadence RED and the two other threads'
uncommitted work, and skips more in the runner environment. Different trees, both explicable.

My proposed strategy, and my reasoning, which is what I want challenged:
- MERGE COMMIT (gh pr merge 158 --merge), not squash and not rebase.
- Reason: repo convention for PRs is a merge commit - #157, #133, #128, #126 all land as "Merge pull
  request #N". Direct-to-main commits in this repo are documentation closeouts, a different lane.
- Reason 2: squashing would collapse a 27-path commit whose message carries the six-round defect
  history and the governance record. That history is the audit value here.
- No branch deletion proposed in the same action. I would keep the branch until David says
  otherwise.
- No rebase: the branch is 1 commit off current main with CLEAN status, so there is nothing to
  linearize and a rebase would only rewrite a reviewed, pin-verified SHA.

Risk I want you to weigh: merging changes what universe_pvo_batch serializes for every consumer of
the valuation block. The Surface-3 preservation contract was updated for the two additive keys and
you cleared that widening in round 1. If you believe any other committed consumer reads that block
positionally or exact-shape, name it now - that is the one class of defect a green CI on this branch
would not necessarily surface.

Unchanged: Studio R1 remains backend-half only; the API/generated-client increment stays parked
behind capture-health; Studio-024 R2-R5 remain unruled by David.

PLEASE REPLY with: (a) merge-strategy CLEAR naming the strategy you concur with, OR (b) a concrete
objection or a different strategy with reasons. [w#dvs-disclosure-1]
