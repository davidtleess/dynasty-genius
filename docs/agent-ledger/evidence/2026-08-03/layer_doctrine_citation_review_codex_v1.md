# Layer-doctrine citation repair review — one residual

**Date:** 2026-08-03  
**Reviewer:** Codex  
**Scope:** `docs/governance/05-layer-doctrine.md` only

Verified:

- §1 has no diff hunk and remains byte-untouched.
- The original content exists at line 51 of `AGENT_SYNC.md` in commit
  `fce0ccee67b0037efbea56c4968baa7f01b26da8` and at line 558 in the current worktree.
- Current line 120 is unrelated ACK-window text, proving the original live-line citation rotted.
- The repo sweep finds no other operative `AGENT_SYNC.md:<line>` citation in governance/bootstrap
  files; only the repair's historical explanation remains.
- Version/date bump and §2-onward pending-authority status are correct.
- Governance validation and `git diff --check` pass.

One residual blocks CLEAR: the replacement uses the seven-character abbreviation `fce0cce` while
claiming the citation is "rerunnable forever." A short object name can become ambiguous as Git
history grows. Use the full immutable object ID
`fce0ccee67b0037efbea56c4968baa7f01b26da8` in both the table row and the runnable command. The
quoted content should remain as the human-readable anchor.

Authority reading: David's direct "fix the 05 citation too" carries the previous land-it
disposition. Once the exact citation is CLEAR, no further commit/push word is required.

**Verdict:** NOT CLEAR on the full-SHA residual only.
