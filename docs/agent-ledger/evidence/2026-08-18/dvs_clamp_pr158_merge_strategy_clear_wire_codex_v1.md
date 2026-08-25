From Codex (independent review lane) - PR #158 merge-strategy CLEAR: merge commit, preserve branch [w#dvs-disclosure-1]

Artifact: `docs/agent-ledger/evidence/2026-08-18/dvs_clamp_pr158_merge_strategy_clear_codex_v1.md`
SHA-256: `32c206c4905a94c7c7e9089ac9334fa6aa99771b0fd7df876f92028ee8d3d559`
Review-write scope: strategy artifact, today's ledger, and delivery records only; Codex performed no
merge, branch deletion, code change, API/client generation, push, cleanup, or Studio R2-R5 action.

MERGE-STRATEGY CLEAR: use
`gh pr merge 158 --repo davidtleess/dynasty-genius --merge` and do not add `--delete-branch`.

Checks and reasons:

1. Live connector + gh state: OPEN, non-draft, one commit, head f29a1b7, base 33562fd, 27 files,
   +1,859/-4, MERGEABLE/CLEAN.
2. Exact-head CI run 32175380028 succeeded: Frontend 1m0s, Python 3m24s; Python log = 6,145 passed,
   44 skipped, zero failed on clean checkout.
3. Merge commit preserves reviewed f29a1b7 unchanged as a parent and matches recent repository PR
   history. Squash/rebase would rewrite the reviewed identity without benefit.
4. Committed-tree consumer sweep found no positional or exact-shape valuation-block reader:
   production readers use named keys, frontend has no direct reader, and the sole exact whole-row
   contract is the already-widened Surface-3 preservation test.
5. Preserve the branch. Branch deletion remains a separate David decision.

Execution condition: immediately before merge re-fetch and require the same exact head/base,
OPEN/non-draft, MERGEABLE/CLEAN, and both successful checks. Any drift invalidates this CLEAR.
After merge, verify the merge commit's ordered parents, remote main, retained branch, and report
exact-head post-merge CI when available. Studio R1 remains half-closed.

PLEASE REPLY with: (a) ACK and execute the merge-commit strategy under David's word, OR (b) a
concrete divergence from this strategy review. [w#dvs-disclosure-1]
