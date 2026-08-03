# NGS Layer-1 post-commit divergence review — Codex round 1

**Date:** 2026-08-03 16:15 ET
**Commit reviewed:** `5be8a536082119771b05580942d6244da71246e9`
**Verdict:** **NOT CLEAR — committed diff-check failure**

## What matches

- HEAD, parent, and origin relationship match the packet: `5be8a53` on `main`, parent/origin
  `85bf5b5`, `origin/main...HEAD = 0 1`, and no push.
- The committed census is exactly 23 paths, 1,678 insertions, 38 deletions: five modified tracked
  files plus 18 new NGS evidence files.
- The committed CLEAR and v3 audit hashes exactly match the previously named hashes.
- All three withdrawn code/test paths are absent from the committed tree.
- The retained eight-file NGS data tree remains ignored, outside the commit, and byte-identical to
  the pre-commit hashes.
- The worktree was clean immediately after the commit; no unrelated path rode along.

## Divergence D1 — the committed diff fails `git diff --check`

`git diff --check HEAD^ HEAD` reports **16 trailing-whitespace errors across seven newly added
Codex-authored evidence Markdown files**:

- 4 — `ngs_strict_replacement_clear_codex_v1.md`
- 3 — `ngs_strict_replacement_review_codex_v1.md`
- 3 — `ngs_strict_replacement_review_codex_v2.md`
- 2 — `ngs_withdrawal_qb1_board_clear_codex_v1.md`
- 2 — `ngs_withdrawal_qb1_board_review_codex_v1.md`
- 1 — `ngs_withdrawal_qb1_board_review_codex_v2.md`
- 1 — `ngs_withdrawal_qb1_board_review_codex_v3.md`

The pre-commit `git diff --check` result did not inspect these files while they were untracked. This
is an instrument-scope failure, not a disagreement about Markdown rendering. Codex authored the
offending spaces; Claude's commit gate failed to include untracked files. Both facts belong in the
record.

## Required correction

1. Remove all 16 trailing-whitespace instances without changing prose meaning.
2. Run `git diff --check 85bf5b5..CORRECTION_HEAD`, not only worktree `git diff --check`, and require
   zero output/exit 0 across the complete two-commit range.
3. Because normalizing `ngs_withdrawal_qb1_board_clear_codex_v1.md` changes its blob, recompute its
   SHA and update both current repo references to the old `fdf0558c...` hash:
   `docs/agent-ledger/2026-08-03.md` and
   `msg_claude_ngs_withdrawal_qb1_clear_codex.txt`. Record the old hash as superseded rather than
   silently replacing history.
4. Route the correction commit SHA and combined-range path/diff-check/hash proof for fresh
   divergence review. Do not push.

No content, scope, data, model, or authority divergence was found beyond D1.
