#!/usr/bin/env bash
# scripts/agent_start.sh — start a new agent session on a clean branch off main.
#
# Verifies preconditions (canonical repo, clean working tree, fast-forward main,
# branch availability, no parallel work on the same step), creates the branch,
# and prints a copy-paste-ready prompt block for the agent.
#
# Zero side effects in --dry-run mode.

set -uo pipefail

CANONICAL_REPO="${DYNASTY_GENIUS_REPO:-/Users/davidleess/dynasty-genius}"
PLAYBOOK="docs/agent-execution-plan.md"
WORKTREE_DIR=".claude/worktrees"
AGENT_BRANCH_PREFIXES=("claude" "codex")

usage() {
  cat <<USAGE
Usage:
  scripts/agent_start.sh <branch-name> --step <STEP_ID> [--base-commit <SHA>]
                         [--worktree] [--dry-run]

Required:
  <branch-name>       e.g., claude/step-0-2-tests-scaffolding
  --step <ID>         Step number from $PLAYBOOK (e.g., 0.2).

Optional:
  --base-commit <SHA> Refuse to proceed unless main HEAD matches this SHA.
  --worktree          Create the branch in a new worktree under
                      $WORKTREE_DIR/ instead of the canonical repo.
  --dry-run           Run all checks and print the prompt block, but make
                      no changes (no fetch, no checkout, no branch create).
  -h, --help          Show this help.

Examples:
  scripts/agent_start.sh claude/step-0-2-tests-scaffolding --step 0.2
  scripts/agent_start.sh codex/step-0-2-tests-scaffolding --step 0.2
  scripts/agent_start.sh claude/step-0-2-tests-scaffolding --step 0.2 --base-commit b8c01ac
  scripts/agent_start.sh claude/step-0-2-tests-scaffolding --step 0.2 --dry-run
USAGE
}

# ---- arg parse -------------------------------------------------------------

BRANCH=""
STEP_ID=""
BASE_COMMIT=""
WANT_WORKTREE=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --step) STEP_ID="${2:-}"; shift 2 ;;
    --base-commit) BASE_COMMIT="${2:-}"; shift 2 ;;
    --worktree) WANT_WORKTREE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -*) echo "ERROR: unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)
      if [[ -z "$BRANCH" ]]; then
        BRANCH="$1"; shift
      else
        echo "ERROR: unexpected positional arg: $1" >&2
        usage >&2; exit 2
      fi
      ;;
  esac
done

if [[ -z "$BRANCH" ]] || [[ -z "$STEP_ID" ]]; then
  echo "ERROR: branch name and --step are required." >&2
  usage >&2
  exit 2
fi

# ---- helpers ---------------------------------------------------------------

say() { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
fail() { printf 'REFUSED: %s\n' "$*" >&2; exit 2; }
do_or_dry() {
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '[dry-run] would run: %s\n' "$*"
  else
    "$@"
  fi
}

# ---- preconditions ---------------------------------------------------------

# 1. cwd is canonical repo
toplevel="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$toplevel" ]]; then
  fail "not in a git repo. Expected: $CANONICAL_REPO"
fi
if [[ "$toplevel" != "$CANONICAL_REPO" ]]; then
  fail "current repo is $toplevel; canonical is $CANONICAL_REPO. cd there first."
fi
say "✓ cwd is canonical repo: $CANONICAL_REPO"

# 2. working tree clean (tracked files only; untracked OK)
if ! git diff --quiet || ! git diff --cached --quiet; then
  fail "working tree has modified or staged files. Commit or stash first."
fi
say "✓ working tree clean (tracked files; untracked OK)"

# 3. fetch + ff main
if [[ $DRY_RUN -eq 1 ]]; then
  say "[dry-run] would: git fetch origin main"
else
  if ! git fetch origin main --quiet; then
    fail "git fetch origin main failed."
  fi
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "main" ]]; then
  do_or_dry git checkout main
fi

if [[ $DRY_RUN -eq 1 ]]; then
  say "[dry-run] would: git pull --ff-only origin main"
else
  if ! git pull --ff-only origin main --quiet; then
    fail "git pull --ff-only failed; main has diverged. Resolve manually."
  fi
fi

main_head="$(git rev-parse main 2>/dev/null || git rev-parse origin/main)"
main_subject="$(git log -1 --pretty=format:'%s' "$main_head" 2>/dev/null || echo '?')"
say "✓ main is at: $main_head — $main_subject"

# 4. base-commit
if [[ -n "$BASE_COMMIT" ]]; then
  resolved_base="$(git rev-parse "$BASE_COMMIT" 2>/dev/null || true)"
  if [[ -z "$resolved_base" ]]; then
    fail "base commit '$BASE_COMMIT' could not be resolved."
  fi
  if [[ "$main_head" != "$resolved_base" ]]; then
    fail "main HEAD is $main_head, but --base-commit expected $resolved_base."
  fi
  say "✓ main HEAD matches expected base commit"
fi

# 5. branch must not exist locally or remotely
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  fail "local branch '$BRANCH' already exists."
fi
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  fail "remote branch 'origin/$BRANCH' already exists."
fi
say "✓ branch name '$BRANCH' is available"

# 6. naming convention (warning only)
if ! [[ "$BRANCH" =~ ^(claude|codex)/(step-[0-9]+-[0-9]+(-[0-9]+)?-[a-z0-9-]+|[a-z0-9-]+)$ ]]; then
  warn "branch name does not match '<agent>/step-<X-Y>-<kebab>' or '<agent>/<kebab>' convention."
fi

# 7. parallel-work conflict for the same step
step_branch_id="${STEP_ID//./-}"
parallel_local=""
for prefix in "${AGENT_BRANCH_PREFIXES[@]}"; do
  while IFS= read -r br; do
    [[ -z "$br" ]] && continue
    if [[ "$br" != "$BRANCH" ]]; then parallel_local="$parallel_local $br"; fi
  done < <(git for-each-ref --format='%(refname:short)' "refs/heads/$prefix/step-${step_branch_id}-*" 2>/dev/null)
done

parallel_remote=""
for prefix in "${AGENT_BRANCH_PREFIXES[@]}"; do
  while IFS= read -r br; do
    [[ -z "$br" ]] && continue
    br_short="${br#refs/heads/}"
    if [[ "$br_short" != "$BRANCH" ]]; then parallel_remote="$parallel_remote $br_short"; fi
  done < <(git ls-remote --heads origin "$prefix/step-${step_branch_id}-*" 2>/dev/null | awk '{print $2}')
done

if [[ -n "$parallel_local" ]] || [[ -n "$parallel_remote" ]]; then
  echo "REFUSED: another agent branch exists for step $STEP_ID:" >&2
  [[ -n "$parallel_local" ]] && echo "  local: $parallel_local" >&2
  [[ -n "$parallel_remote" ]] && echo "  remote: $parallel_remote" >&2
  exit 2
fi
say "✓ no parallel work on step $STEP_ID"

# 8. existing worktrees with uncommitted work (warning only)
if [[ -d "$WORKTREE_DIR" ]]; then
  while IFS= read -r wt_path; do
    [[ -z "$wt_path" ]] && continue
    if [[ -d "$wt_path" ]]; then
      dirty="$(git -C "$wt_path" status --porcelain 2>/dev/null | head -1)"
      if [[ -n "$dirty" ]]; then
        warn "worktree $wt_path has uncommitted changes."
      fi
    fi
  done < <(git worktree list --porcelain 2>/dev/null | awk '/^worktree / {print $2}' | grep -F "$WORKTREE_DIR" || true)
fi

# ---- step lookup from playbook --------------------------------------------

step_summary=""
if [[ -f "$PLAYBOOK" ]]; then
  step_summary="$(awk -v step="### Step $STEP_ID " '
    BEGIN { in_step=0 }
    index($0, step) == 1 { in_step=1; print; next }
    in_step && /^### Step / { exit }
    in_step && /^## / { exit }
    in_step { print }
  ' "$PLAYBOOK" 2>/dev/null || true)"
fi
if [[ -z "$step_summary" ]]; then
  warn "could not locate '### Step $STEP_ID ' in $PLAYBOOK. Scope summary will be empty."
fi

# ---- create branch (or worktree) ------------------------------------------

if [[ $WANT_WORKTREE -eq 1 ]]; then
  short_name="${BRANCH##*/}"
  worktree_path="$WORKTREE_DIR/$short_name"
  if [[ -e "$worktree_path" ]]; then
    fail "worktree path '$worktree_path' already exists."
  fi
  do_or_dry git worktree add -b "$BRANCH" "$worktree_path" main
  say "✓ created worktree at $worktree_path on branch $BRANCH"
else
  do_or_dry git checkout -b "$BRANCH" main
  say "✓ created branch $BRANCH (checked out in canonical repo)"
fi

# ---- prompt block ----------------------------------------------------------

cat <<PROMPT

────────────────────────────────────────────────────────────────────
AGENT PROMPT BLOCK — copy-paste below
────────────────────────────────────────────────────────────────────

## Step $STEP_ID

Canonical repo: $CANONICAL_REPO
Branch: $BRANCH
Base commit: $main_head$([[ -n "$BASE_COMMIT" ]] && echo " (verified)")
Step doc: $PLAYBOOK

Step summary:
$(if [[ -n "$step_summary" ]]; then echo "$step_summary" | sed 's/^/  /'; else echo "  (could not locate step heading in playbook)"; fi)

Cross-cutting guardrails (do not violate even if convenient):
  - No market data in Engine A or Engine B (KTC / FantasyCalc / DynastyNerds / ADP / consensus stay out of training)
  - RAS asymmetric: low-RAS may flag risk; high-RAS never boosts score
  - Trade verdict permanently removed; use delta_status only
  - Repo-relative paths only
  - Snapshots under app/data/cache/raw/, never root-level data/
  - TE model_grade=C with low_sample_holdout caveat; QB=D production-gated

Before reporting back to David:
  scripts/agent_close_check.sh --run-tests --check-pr

────────────────────────────────────────────────────────────────────
PROMPT
