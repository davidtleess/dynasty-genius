# TMUX Agent Communication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small, explicit CLI helper that lets a local agent list tmux panes and send text to another agent pane safely.

**Architecture:** Implement `scripts/tmux_msg.py` as a focused wrapper over `tmux list-panes`, `tmux set-buffer`, `tmux paste-buffer`, and optional `tmux send-keys Enter`. Keep all tmux subprocess calls injectable so tests never write to live panes.

**Tech Stack:** Python stdlib (`argparse`, `subprocess`, `dataclasses`), pytest.

---

### Task 1: CLI Behavior Tests

**Files:**
- Create: `tests/test_tmux_msg.py`
- Create: `scripts/tmux_msg.py`

- [ ] **Step 1: Write failing tests**

Add tests that import `scripts.tmux_msg` and verify pane parsing, send command construction, and dry-run behavior without calling real tmux.

- [ ] **Step 2: Run tests to verify RED**

Run: `.venv/bin/python3.14 -m pytest tests/test_tmux_msg.py`

Expected: collection fails because `scripts.tmux_msg` does not exist.

- [ ] **Step 3: Implement the helper**

Create `scripts/tmux_msg.py` with:

- `list_panes()` for pane discovery
- `send_message()` for paste-only or paste-and-submit delivery
- `main()` with `list` and `send` subcommands

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/python3.14 -m pytest tests/test_tmux_msg.py`

Expected: all tests pass.

### Task 2: Live Dry-Run Verification

**Files:**
- Modify: `docs/agent-ledger/2026-05-25.md`

- [ ] **Step 1: Verify list command**

Run: `.venv/bin/python3.14 scripts/tmux_msg.py list`

Expected: prints the live `dynasty` panes.

- [ ] **Step 2: Verify dry-run send**

Run: `.venv/bin/python3.14 scripts/tmux_msg.py send dynasty:1.3 "Codex dry-run tmux communicator check" --submit --dry-run`

Expected: prints the tmux commands that would run; sends nothing.

- [ ] **Step 3: Log closeout**

Append the final checks and handoff to `docs/agent-ledger/2026-05-25.md`.
