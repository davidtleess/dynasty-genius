# Loop-control machinery finding — F18 terminal-deny forecloses the disposal→reinit path

**Found:** 2026-08-13/14, empirically, during TW0813-SCORER-1. **Lane:** Claude.
**Routes to:** the active loop-control remediation workstream (Codex, six open BLOCKERs per
[w#lc-judge-review-2]). Finding only — no fix from this lane.

## The defect

`dg-cockpit/autonomy/claude/dg-engineering/scripts/pre-tool-use.mjs:49-73` (spec F18) denies
every Write/Edit/MultiEdit and every non-allowlisted Bash command whenever the worktree's
`run.json` carries ANY `terminalState` — with no `init` carve-out and no unblock verb (the
sole exception is a Judge-ruled commit on READY_FOR_GATE+SHIP). `createRun` itself persists
`{fresh: true}` and would replace a terminal run, but the hook denies the command before it
executes. Consequently a stale abandoned run disposed as `BLOCKED` — the only truthful
terminal available when historical required checks are absent — converts a cleanup into a
worktree-wide, David-gated outage for every hook-active lane. No route to the Judge exists
for this state: no cap and no detector fired, and referral routing is locked to the counters
(David's word, 2026-08-12 evening).

## Observed sequence (all timestamps from artifacts)

1. Codex disposed its abandoned Footballguys v22 run (`ba1a6467…`) as terminal `BLOCKED` at
   `2026-08-14T03:02:20Z`, predicting init was unblocked.
2. Claude's `dg-autonomy init` was denied by the hook; so were `shasum`, `sed -n`, all Writes
   (including this lane's ledger/evidence appends and wire message files), and all python —
   the F18 allowlist is `ls/cat/head/tail/grep/rg/wc/stat/file/pwd/du/df/which/diff`,
   read-only git, and `dg-autonomy status|verdict` (`core/lib/policy.mjs:206-230`).
3. The asymmetry: Codex could still write (its hook activation is itself an open David gate,
   board OPEN GATES), so the review conversation continued while the implementing lane was
   frozen; round recording was deferred-and-disclosed.
4. Exit required David's own keystroke renaming the file
   (`run.json → run.codex-v22-disposed.json.bak`, verified on disk 2026-08-14; Tower
   TW0813-AUTONOMY-2 confirmed he ran it himself).

## Suggested remediation shapes (for the owning workstream, not decided here)

Either (a) an explicit `init` carve-out when the existing run's terminal state is a disposal
(distinguish "terminal awaiting David on THIS run's dispute" from "terminal, disposed"), or
(b) a disposal verb that archives `run.json` to a dated `.bak` — the exact operation David
performed by hand — so cleanup never freezes the worktree. Preserving the disposed record
matters (retroactive-mutability was already a Codex BLOCKER); the rename form does that.
