# DVS clamp-disclosure commit `f29a1b7` divergence audit — Codex v1

Date: 2026-08-18
Thread: `w#dvs-disclosure-1`
Verdict: **COMMIT DIVERGENCE CLEAR — exact reviewed implementation landed; one non-blocking commit-wide diff-check qualification**

## Commit boundary

- Full commit: `f29a1b7424f5143838a4125338358f20ed0677c0`.
- Parent: `33562fdafd9b4c554078d69fa63cf2b4eef5491c`, exactly `origin/main` at audit time.
- Branch: `feature/dvs-ceiling-disclosure`; no remote branch contains the commit.
- Exact boundary: 27 paths, +1,859 / -4. The path census matches the receipt: three production
  files, four contract files, `AGENT_SYNC.md`, the daily ledger, and 18 DVS evidence artifacts.
- The parked capture-health, wire-health, generated-client, plist, `.mcp.json`, and governed-cadence
  paths remain outside the commit and present in the worktree. `git stash list` is empty.

## Exact reviewed pins

Committed blob SHA-256 values independently recomputed through `git show f29a1b7:<path>`:

- `pvo_assembler.py`: `8baf25c73f014af2edb255558dd13b00b32524fd7ae5b5ec57bd8216ce102898`
- `engine_a.py`: `77a48c513b2c515588bfac90c4607841aa63806a80593fe56e540cfaff5fcf1e`
- `universe_pvo_batch.py`: `188307a5f6fd42d720bdf4f764d057886b6d126b110c66db2736696b03aa854d`
- `test_dvs_clamp_truth_red.py`: `7f1cad1b227fe23a06b746d94a4c8d69b70bd69328325f15fa1da0bf3e580535`
- `test_dvs_clamp_connected_red.py`: `7feecf04927624038c689b80ff145b2707642725c558e75a3f6a1da5f315bcd6`
- Round-6 verdict: `fe580af8da19895ece1c47077d629803da4016b45048992887992856ffaba26a`

These are the reviewed pins exactly. No whitespace, comment, ordering, or executable drift exists
between the cleared implementation and the commit.

## Fresh checks

- Clamp bundle plus Surface-3 preservation: **23 passed**, with the same existing sklearn
  estimator-version warning and no failure.
- The linked-worktree hook correction is valid: `git rev-parse --git-path hooks/pre-commit` resolves
  `/Users/davidleess/dynasty-genius/.git/hooks/pre-commit`, and that file is executable.
- No active dg-autonomy run exists.
- No commit, amend, push, PR, merge, cleanup, or product mutation was performed by this audit.

## Non-blocking qualification: whole-commit `git diff --check`

`git diff --check f29a1b7^ f29a1b7` exits 2 on **14 trailing-space reports across seven committed
Markdown evidence files**: the `Date` and `Thread` hard-break lines in review v1-v6, plus the
`Artifact` and `SHA-256` hard-break lines in the Round-5 NOT-CLEAR wire.

This does **not** establish commit divergence: those bytes are part of the exact hash-pinned review
artifacts that were cleared and landed unchanged, and no production or test line is affected. It
does qualify the earlier broad phrase “git diff --check clean”: that measurement did not include
then-untracked evidence files, so it was scoped rather than whole-change-set evidence. Rewriting the
seven frozen artifacts now would change their cited SHA-256 pins and is not a gate-safe mechanical
cleanup. The correct disposition is to record the scope limitation, not silently rewrite evidence.

## Verdict

**COMMIT DIVERGENCE CLEAR.** `f29a1b7` faithfully lands the reviewed backend/artifact increment and
its disclosed evidence boundary. The DVS cycle remains closed at the commit gate. Studio R1 remains
half-closed; push and PR remain David's separate gates. The commit-wide diff-check qualification is
recorded as evidence hygiene, not a blocker or authorization for an amendment.
