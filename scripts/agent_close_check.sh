#!/usr/bin/env bash
# scripts/agent_close_check.sh — read-only session-close diagnostic.
#
# Reports branch state, sync vs origin/main, optional test results, optional
# PR status, worktrees, claude/* branch hygiene, /tmp scratch files, and
# (opt-in) memory follow-ups. Prints suggested cleanup commands but never
# executes any mutation.

set -uo pipefail

CANONICAL_REPO="${DYNASTY_GENIUS_REPO:-/Users/davidleess/dynasty-genius}"
AGENT_BRANCH_PREFIXES=("claude" "codex")

usage() {
  cat <<USAGE
Usage:
  scripts/agent_close_check.sh [--branch <BRANCH>] [--run-tests] [--check-pr]
                               [--memory-scan --step <STEP_ID>]

Options:
  --branch <BRANCH>     Branch to check (default: current).
  --run-tests           Run pytest with the canonical invocation.
  --check-pr            Query GitHub for PR status (requires gh auth).
  --memory-scan         Opt-in: scan known agent-memory dirs for follow-ups.
                        Best-effort only; never affects the final verdict.
  --step <STEP_ID>      Required when --memory-scan is given.
  -h, --help            Show this help.

Hard rule: this script is read-only. Suggested cleanup commands are printed
for the human to review and run; nothing is deleted, removed, or pushed.
USAGE
}

# ---- arg parse -------------------------------------------------------------

TARGET_BRANCH=""
RUN_TESTS=0
CHECK_PR=0
DO_MEMORY_SCAN=0
STEP_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --branch) TARGET_BRANCH="${2:-}"; shift 2 ;;
    --run-tests) RUN_TESTS=1; shift ;;
    --check-pr) CHECK_PR=1; shift ;;
    --memory-scan) DO_MEMORY_SCAN=1; shift ;;
    --step) STEP_ID="${2:-}"; shift 2 ;;
    -*) echo "ERROR: unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) echo "ERROR: unexpected arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# ---- preconditions ---------------------------------------------------------

toplevel="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$toplevel" ]]; then
  echo "ERROR: not in a git repo. Expected: $CANONICAL_REPO" >&2
  exit 2
fi
if [[ "$toplevel" != "$CANONICAL_REPO" ]]; then
  echo "WARN: current repo is $toplevel; canonical is $CANONICAL_REPO." >&2
fi

if [[ -z "$TARGET_BRANCH" ]]; then
  TARGET_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

# ---- verdicts (computed from repo truth only) ------------------------------

verdict_branch="clean"
verdict_sync="up-to-date"
verdict_tests="not-run"

# ---- header ----------------------------------------------------------------

head_sha="$(git rev-parse --short "$TARGET_BRANCH" 2>/dev/null || echo '?')"
head_subject="$(git log -1 --pretty=format:'%s' "$TARGET_BRANCH" 2>/dev/null || echo '?')"

cat <<HEADER
# Agent session-close check

Canonical repo: $CANONICAL_REPO
Branch under review: \`$TARGET_BRANCH\`
HEAD: $head_sha — $head_subject

HEADER

# ---- 1. Branch state -------------------------------------------------------

echo "## 1. Branch state"
echo

modified_files="$(git diff --name-only 2>/dev/null || true)"
staged_files="$(git diff --cached --name-only 2>/dev/null || true)"
untracked_files="$(git ls-files --others --exclude-standard 2>/dev/null || true)"

modified_count=$(printf '%s\n' "$modified_files" | grep -c . || true)
staged_count=$(printf '%s\n' "$staged_files" | grep -c . || true)
untracked_count=$(printf '%s\n' "$untracked_files" | grep -c . || true)

echo "- Modified (unstaged): $modified_count"
if [[ "$modified_count" -gt 0 ]]; then
  printf '%s\n' "$modified_files" | head -10 | sed 's/^/    - /'
fi
echo "- Staged: $staged_count"
if [[ "$staged_count" -gt 0 ]]; then
  printf '%s\n' "$staged_files" | head -10 | sed 's/^/    - /'
fi
echo "- Untracked: $untracked_count"
if [[ "$untracked_count" -gt 0 ]]; then
  printf '%s\n' "$untracked_files" | head -10 | sed 's/^/    - /'
fi

if [[ "$modified_count" -gt 0 ]] || [[ "$staged_count" -gt 0 ]] || [[ "$untracked_count" -gt 0 ]]; then
  verdict_branch="dirty"
fi

echo
echo "**verdict:** $verdict_branch"
echo

# ---- 2. Sync vs origin/main ------------------------------------------------

echo "## 2. Sync state vs origin/main"
echo

if ! git fetch origin main --quiet 2>/dev/null; then
  echo "_(fetch failed; using last-known origin/main)_"
fi

ahead="$(git rev-list --count "origin/main..$TARGET_BRANCH" 2>/dev/null || echo '?')"
behind="$(git rev-list --count "$TARGET_BRANCH..origin/main" 2>/dev/null || echo '?')"

echo "- Commits ahead of origin/main: $ahead"
if [[ "$ahead" =~ ^[0-9]+$ ]] && [[ "$ahead" -gt 0 ]]; then
  git log "origin/main..$TARGET_BRANCH" --oneline 2>/dev/null | sed 's/^/    - /'
fi
echo "- Commits behind origin/main: $behind"

# Use git cherry to detect content equivalence (handles squash-merge)
unique_unmerged="$(git cherry origin/main "$TARGET_BRANCH" 2>/dev/null | grep -c '^+' || true)"

if [[ "$unique_unmerged" == "0" ]] && [[ "$ahead" != "0" ]] && [[ "$ahead" =~ ^[0-9]+$ ]]; then
  verdict_sync="merged (commits incorporated by content into origin/main)"
elif [[ "$unique_unmerged" == "0" ]] && [[ "$ahead" == "0" ]]; then
  verdict_sync="up-to-date"
elif [[ "$behind" =~ ^[0-9]+$ ]] && [[ "$behind" -gt 0 ]]; then
  verdict_sync="needs-rebase or needs-merge"
elif [[ "$ahead" =~ ^[0-9]+$ ]] && [[ "$ahead" -gt 0 ]]; then
  verdict_sync="needs-push or needs-PR"
fi

echo
echo "**verdict:** $verdict_sync"
echo

# ---- 3. Test results -------------------------------------------------------

echo "## 3. Test results"
echo

if [[ $RUN_TESTS -eq 1 ]]; then
  if [[ -x ".venv/bin/pytest" ]]; then
    pytest_bin=".venv/bin/pytest"
  elif command -v pytest >/dev/null 2>&1; then
    pytest_bin="pytest"
  else
    pytest_bin=""
  fi

  if [[ -z "$pytest_bin" ]]; then
    echo "WARN: pytest not found (looked for .venv/bin/pytest then pytest on PATH); skipping."
    verdict_tests="pytest-not-installed"
  else
    echo "Running: PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp $pytest_bin -q"
    test_output="$(PYTHONPATH=. PYTHONPYCACHEPREFIX=.pycache_tmp "$pytest_bin" -q 2>&1)"
    test_exit=$?
    echo
    echo '```'
    printf '%s\n' "$test_output" | tail -20
    echo '```'
    if [[ $test_exit -eq 0 ]]; then
      verdict_tests="pass"
    else
      verdict_tests="fail (exit $test_exit)"
    fi
  fi
else
  echo "Skipped (run with --run-tests to include)."
fi

echo
echo "**verdict:** $verdict_tests"
echo

# ---- 4. Pull request -------------------------------------------------------

echo "## 4. Pull request"
echo

if [[ $CHECK_PR -eq 1 ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    echo "Skipped: \`gh\` CLI not installed."
  elif ! gh auth status >/dev/null 2>&1; then
    echo "Skipped: \`gh\` is installed but not authenticated. Run \`gh auth login\` once to enable."
  else
    pr_count="$(gh pr list --head "$TARGET_BRANCH" --state all --json number 2>/dev/null | grep -c 'number' || true)"
    if [[ "$pr_count" == "0" ]]; then
      echo "No PR found for \`$TARGET_BRANCH\`."
      repo_slug="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo '')"
      if [[ -n "$repo_slug" ]]; then
        echo "Suggested: open https://github.com/$repo_slug/compare/main...$TARGET_BRANCH?expand=1"
      fi
    else
      gh pr list --head "$TARGET_BRANCH" --state all 2>/dev/null | sed 's/^/    /'
    fi
  fi
else
  echo "Skipped (run with --check-pr to include)."
fi
echo

# ---- 5. Worktrees ----------------------------------------------------------

echo "## 5. Worktrees"
echo
echo '```'
git worktree list 2>/dev/null
echo '```'
echo

# Mark stale (fully-merged) worktrees
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  wt_path="$(echo "$line" | awk '{print $1}')"
  wt_branch="$(echo "$line" | grep -oE '\[.+\]$' | tr -d '[]' || true)"
  if [[ "$wt_path" == "$CANONICAL_REPO" ]] || [[ -z "$wt_branch" ]]; then continue; fi
  unique="$(git cherry origin/main "$wt_branch" 2>/dev/null | grep -c '^+' || true)"
  if [[ "$unique" == "0" ]]; then
    echo "- \`$wt_path\` on \`$wt_branch\` is fully merged into origin/main — candidate for cleanup."
  fi
done < <(git worktree list 2>/dev/null)
echo

# ---- 6. Branch hygiene -----------------------------------------------------

echo "## 6. Branch hygiene (claude/* and codex/* branches)"
echo

echo "### Local"
local_agent_branches=""
for prefix in "${AGENT_BRANCH_PREFIXES[@]}"; do
  local_agent_branches="$local_agent_branches"$'\n'"$(git for-each-ref --format='%(refname:short)' "refs/heads/$prefix/*" 2>/dev/null || true)"
done
local_agent_branches="$(printf '%s\n' "$local_agent_branches" | sed '/^$/d' | sort -u)"
if [[ -z "$local_agent_branches" ]]; then
  echo "_(none)_"
else
  while IFS= read -r br; do
    [[ -z "$br" ]] && continue
    unique="$(git cherry origin/main "$br" 2>/dev/null | grep -c '^+' || true)"
    if [[ "$unique" == "0" ]]; then
      remote_exists="$(git ls-remote --heads origin "$br" 2>/dev/null | wc -l | tr -d ' ')"
      if [[ "$remote_exists" -gt 0 ]]; then
        echo "- \`$br\` — merged. Suggested: \`git branch -d $br && git push origin --delete $br\`"
      else
        echo "- \`$br\` — merged (local-only). Suggested: \`git branch -d $br\`"
      fi
    else
      echo "- \`$br\` — open ($unique unique commit(s) not in origin/main)."
    fi
  done <<< "$local_agent_branches"
fi
echo

echo "### Remote"
remote_agent_branches=""
for prefix in "${AGENT_BRANCH_PREFIXES[@]}"; do
  remote_agent_branches="$remote_agent_branches"$'\n'"$(git ls-remote --heads origin "$prefix/*" 2>/dev/null | awk '{print $2}' | sed 's|refs/heads/||' || true)"
done
remote_agent_branches="$(printf '%s\n' "$remote_agent_branches" | sed '/^$/d' | sort -u)"
if [[ -z "$remote_agent_branches" ]]; then
  echo "_(none)_"
else
  while IFS= read -r br; do
    [[ -z "$br" ]] && continue
    unique="$(git cherry origin/main "origin/$br" 2>/dev/null | grep -c '^+' || true)"
    if [[ "$unique" == "0" ]]; then
      echo "- \`origin/$br\` — merged. Suggested: \`git push origin --delete $br\`"
    else
      echo "- \`origin/$br\` — open."
    fi
  done <<< "$remote_agent_branches"
fi
echo

# ---- 7. Scratch file scan --------------------------------------------------

echo "## 7. Scratch file scan (/tmp/)"
echo

scratch_files="$(find /tmp -maxdepth 2 -type f -mtime -1 \
  \( -name '*commit*.txt' -o -name 'pr_body*' -o -name 'step*.txt' \) \
  2>/dev/null | head -20 || true)"

if [[ -z "$scratch_files" ]]; then
  echo "No scratch files matching common agent patterns under /tmp."
else
  echo "Found:"
  printf '%s\n' "$scratch_files" | sed 's/^/  - /'
  echo
  rm_args="$(printf '%s\n' "$scratch_files" | tr '\n' ' ')"
  echo "Suggested cleanup:"
  echo "    rm $rm_args"
fi
echo

# ---- 8. Memory follow-ups (opt-in) -----------------------------------------

echo "## 8. Memory follow-ups"
echo

if [[ $DO_MEMORY_SCAN -eq 0 ]]; then
  echo "Memory scan: skipped (run with \`--memory-scan --step <STEP_ID>\` to include optional agent-memory follow-ups)."
else
  if [[ -z "$STEP_ID" ]]; then
    echo "WARN: --memory-scan requires --step <STEP_ID>; skipping."
  else
    echo "_Memory follow-ups (best effort, not source of truth)_"
    echo

    known_dirs=(
      "$HOME/.claude/projects/-Users-davidleess-dynasty-genius/memory"
      "$HOME/.codex/memory"
    )

    found_any=0
    matched_count=0
    for dir in "${known_dirs[@]}"; do
      if [[ ! -d "$dir" ]]; then continue; fi
      if [[ ! -r "$dir" ]]; then
        echo "Memory scan: skipped for $dir (directory unreadable)."
        continue
      fi
      found_any=1
      # match "step <ID>" or "step-<ID>" or "step.<ID>"
      matches="$(grep -ril -E "step[ ._-]?${STEP_ID}([^0-9.]|$)" "$dir" 2>/dev/null || true)"
      if [[ -n "$matches" ]]; then
        echo "Found in \`$dir\`:"
        while IFS= read -r f; do
          [[ -z "$f" ]] && continue
          echo "  - $(basename "$f")"
          grep -i -E "step[ ._-]?${STEP_ID}([^0-9.]|$)" "$f" 2>/dev/null | head -3 | sed 's/^/      > /'
          matched_count=$((matched_count + 1))
        done <<< "$matches"
      fi
    done

    if [[ $found_any -eq 0 ]]; then
      echo "Memory scan: skipped (no known memory directory found)."
    elif [[ $matched_count -eq 0 ]]; then
      echo "No memory entries mention step $STEP_ID."
    fi
  fi
fi
echo

# ---- final verdict (repo truth only) ---------------------------------------

echo "## Final verdict"
echo

if [[ "$verdict_branch" == "dirty" ]]; then
  echo "🟡 WORK INCOMPLETE — branch has uncommitted changes."
elif [[ "$verdict_sync" == merged* ]]; then
  echo "🟢 READY FOR CLEANUP — branch merged into origin/main; see Section 6 for suggested deletion commands."
elif [[ "$verdict_sync" == "needs-push or needs-PR" ]]; then
  if [[ "$verdict_tests" == "fail"* ]]; then
    echo "🟡 WORK INCOMPLETE — tests failing."
  else
    echo "🟢 READY TO PUSH / OPEN PR — see Section 4 for PR suggestion."
  fi
elif [[ "$verdict_sync" == "needs-rebase"* ]]; then
  echo "🟡 NEEDS REBASE — origin/main has moved ahead."
else
  echo "🟢 READY TO HAND BACK"
fi

# Memory scan never affects the verdict (per spec).
