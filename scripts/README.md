# scripts/

Lightweight shell helpers for repeatable agent sessions. Bash + git only;
`gh` optional. Both scripts are agent-neutral — usable by Claude, Codex, or
the human directly.

## Why

Every agent session should start from a known-clean canonical state and
finish with an honest read of what landed. These scripts encode the
session-start preflight and the session-close diagnostic so we stop relying
on memory and ad-hoc cleanup.

## `agent_start.sh` — session-start preflight + branch creation

```
scripts/agent_start.sh <branch> --step <ID> [--base-commit <SHA>] [--worktree] [--dry-run]
```

**Refuses** to proceed if:

- cwd is not the canonical repo
- working tree has modified or staged files
- main can't fast-forward
- the branch already exists locally or remotely
- another `claude/step-<same-ID>-*` or `codex/step-<same-ID>-*`
  branch exists (parallel-work conflict; step IDs use hyphens in branch names,
  e.g. `step-0-2` for Step 0.2)
- `--base-commit` is given and main HEAD doesn't match

**Warns** (non-blocking) if:

- branch name doesn't match `<agent>/step-<X-Y>-<kebab>` or `<agent>/<kebab>`
  for `claude` / `codex`
- another worktree under `.claude/worktrees/` has uncommitted changes
- the step's heading can't be located in `docs/agent-execution-plan.md`

**Output:** a copy-paste-ready prompt block with canonical path, branch,
base commit, step scope (pulled from `docs/agent-execution-plan.md`),
cross-cutting guardrails, and the close-check command.

`--worktree` creates the branch in a fresh worktree under
`.claude/worktrees/<branch-shortname>` instead of the canonical repo. Use
only when you genuinely need a parallel filesystem checkout — most steps
don't.

`--dry-run` runs every check and prints the would-be prompt block, but
makes no changes.

### Example

```
scripts/agent_start.sh claude/step-0-2-tests-scaffolding --step 0.2 --base-commit b8c01ac
```

## `agent_close_check.sh` — session-close diagnostic

```
scripts/agent_close_check.sh [--branch <BRANCH>] [--run-tests] [--check-pr]
                             [--memory-scan --step <STEP_ID>]
```

Reports:

1. **Branch state** — modified, staged, untracked counts.
2. **Sync vs origin/main** — ahead, behind, content-equivalence merged check
   (handles squash-merge).
3. **Test results** *(opt-in via `--run-tests`)* — runs
   `PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp pytest -q`.
4. **Pull request** *(opt-in via `--check-pr`)* — uses `gh` if installed and
   authenticated; falls back to a pre-filled compare URL.
5. **Worktrees** — `git worktree list`, with stale (merged) worktrees flagged.
6. **Branch hygiene** — every `claude/*` / `codex/*` branch local + remote, marked
   `merged` / `open` / `merged (local-only)` with suggested deletion commands.
7. **Scratch file scan** — `/tmp/*commit*.txt`, `pr_body*`, `step*.txt`
   younger than 24h, with suggested `rm` command.
8. **Memory follow-ups** *(opt-in via `--memory-scan --step <STEP_ID>`)* —
   greps known agent-memory dirs for entries mentioning the step. Best-effort
   only; never affects the final verdict.

**Final verdict** is one of: `READY TO HAND BACK`, `READY TO PUSH / OPEN PR`,
`READY FOR CLEANUP`, `WORK INCOMPLETE`, `NEEDS REBASE`. Computed from repo
truth only.

### Hard rule: zero side effects

This script never deletes branches, removes worktrees, removes files,
creates PRs, or rebases. It prints suggested commands for the human to run.

### Memory scan is opt-in by design

Memory directories are agent-specific (Claude under
`~/.claude/projects/...`, Codex under `~/.codex/memory`) and are not repo
truth. The close-check stays agent-neutral by default. When you opt in:

- Both known dirs are scanned if they exist.
- Unreadable or absent dirs are skipped silently.
- Memory matches are labelled "best effort, not source of truth."
- The final verdict ignores memory scan results entirely.

## Canonical repo override

Both scripts assume `git rev-parse --show-toplevel` resolves to
`/Users/davidleess/dynasty-genius`. To override (e.g., for testing in a
different checkout):

```
DYNASTY_GENIUS_REPO=/path/to/elsewhere scripts/agent_close_check.sh
```

## Verifying the scripts

```
bash -n scripts/agent_start.sh scripts/agent_close_check.sh   # syntax check
scripts/agent_start.sh test-branch --step 0.2 --dry-run       # safe smoke test
```
