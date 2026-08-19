"""Make every dg-work.sh worktree landable by dg-land.sh.

Anchored patch, refuses unless each anchor matches exactly once.

The two scripts contradict each other by construction: dg-work.sh symlinks the
shared store into each worktree, and dg-land.sh refuses on ANY dirty
`git status --porcelain`. Left alone, no ticket worktree can ever be landed.
"""

from __future__ import annotations

import sys
from pathlib import Path

TARGET = Path("/Users/davidleess/dg-build/bin/dg-work.sh")

# 1. Record which paths were actually symlinked (writable copies must NOT be excluded).
OLD_1 = """linked=0; copied=0; skipped=0
for p in "${SHARE_PATHS[@]}"; do"""

NEW_1 = """linked=0; copied=0; skipped=0
LINKED_PATHS=()
for p in "${SHARE_PATHS[@]}"; do"""

OLD_2 = """    ln -s "$src" "$dst"; linked=$((linked+1))"""

NEW_2 = """    ln -s "$src" "$dst"; linked=$((linked+1)); LINKED_PATHS+=("$p")"""

# 2. After the marker is written, clear both classes of false dirt.
OLD_3 = """# --- claim the ticket ---------------------------------------------------------"""

NEW_3 = '''# --- make the worktree landable ----------------------------------------------
# dg-work.sh symlinks the shared store; dg-land.sh refuses on ANY dirty status.
# Left alone the two contradict each other and NO ticket can ever land. Both
# kinds of false dirt are artifacts of this script, so this script clears them:
#
#   1. Some shared paths (app/data/backtest, identity, sources) contain TRACKED
#      files. Git does not traverse a symlinked directory, so every tracked file
#      under one reads as deleted -- ~72 phantom deletions per worktree.
#   2. The symlinks themselves read as untracked.
#
# Index state and a per-worktree exclude only. Nothing is written to the shared
# store, nothing is committed, and no shared git config is touched.
WT_GIT_DIR="$(git -C "$DEST" rev-parse --git-dir)"
mkdir -p "$WT_GIT_DIR/info"
{
  echo "# Written by dg-work.sh -- paths symlinked to the shared store."
  echo "# Untracked here by construction; excluded so dg-land.sh can run."
  echo ".dg-worktree.json"
  if [[ ${#LINKED_PATHS[@]} -gt 0 ]]; then printf '%s\\n' "${LINKED_PATHS[@]}"; fi
} >> "$WT_GIT_DIR/info/exclude"

# Tracked files hidden behind a symlinked directory: tell git to stop looking.
PHANTOM="$(git -C "$DEST" status --porcelain | grep '^ D ' | cut -c4- || true)"
if [[ -n "$PHANTOM" ]]; then
  printf '%s\\n' "$PHANTOM" | git -C "$DEST" update-index --skip-worktree --stdin
  echo "  landable : $(printf '%s\\n' "$PHANTOM" | wc -l | tr -d ' ') phantom deletions skip-worktree'd"
fi

# --- claim the ticket ---------------------------------------------------------'''


def main() -> int:
    source = TARGET.read_text()
    pairs = (
        ("linked-paths-array", OLD_1, NEW_1),
        ("linked-paths-append", OLD_2, NEW_2),
        ("landable-block", OLD_3, NEW_3),
    )
    for label, old, _new in pairs:
        hits = source.count(old)
        if hits != 1:
            print(f"REFUSED: anchor {label!r} matched {hits} times, expected 1")
            return 1
    for _label, old, new in pairs:
        source = source.replace(old, new)
    TARGET.write_text(source)
    print(f"patched {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
