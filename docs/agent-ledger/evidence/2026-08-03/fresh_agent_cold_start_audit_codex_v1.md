# Fresh-agent cold-start audit — current board routing

**Recorded:** 2026-08-03

**Layer served:** cross-layer operating state, routing first to Layer 1 NGS disposition

**Final write scope:** `AGENT_SYNC.md`, `AGENTS.md`, `CLAUDE.md`, this evidence record, cockpit
message records, and append-only daily-ledger entries

## Method

I discarded conversational handoff as authority and followed the repository bootstrap in order:
governance `02`, `00`, `05`, `01`, `03`, the complete `AGENT_SYNC.md`, and today's ledger. I then
checked the live worktree, branch divergence, the board's cited planning artifact, and repository
callers for the canonical and duplicate NGS routes.

## Live handoff reproduced

- `HEAD` was `ef0e156099549f9c2d709ba043859a64c36eb210`, with `0/0` divergence from `origin/main`.
- The only untracked paths were the three board-named duplicate NGS files:
  `scripts/run_nfl_nextgen_capture.py`,
  `src/dynasty_genius/capture/nfl_nextgen_capture.py`, and
  `tests/contract/test_nfl_nextgen_capture.py`.
- Production callers use `load_nextgen_from_export` from the tracked canonical
  `src/dynasty_genius/nflverse_usage.py`; the duplicate adapter is referenced only by its own
  untracked CLI and contract test.
- The cited planning artifact agrees that this is a disposition/CLEAR cycle, not a new feature
  implementation, and that the duplicate data tree must remain preserved.

## Cold-start defect

The current board was substantively correct, but it was followed by more than one thousand lines
of older boards and phase notes containing stale “next”, “open”, and “live” directives. The current
board said `READ FIRST` but did not say where current authority ended. It also lacked an operational
first transition: a fresh agent could read the withdrawal recommendation as permission to delete
before producing the strict-replacement proof, or begin CFBD framing concurrently because both are
authorized work.

## Repair

The current board now contains a cold-start router that:

1. pins the expected three-path handoff and requires ownership reconciliation on any difference;
2. makes the first pass read-only;
3. names independent CLEAR as the transition from proof to authorized withdrawal;
4. preserves the duplicate data tree and forbids unrelated concurrent work; and
5. finishes with an explicit `END CURRENT BOARD` marker declaring all lower boards historical.

No NGS file, data tree, CFBD artifact, active CSV, model, consumer, or execution surface changed.
The next agent's first deliverable is the strict-replacement audit, not a deletion or a new RED.

## Independent cold-start rounds and final disposition

Claude independently ran a blank-slate bootstrap twice. The first round found additional defects:
the old `CLAUDE.md` invented a nonexistent two-file pytest exclusion; `AGENT_SYNC.md` navigation
did not tell a reader where current authority ended; a solo agent could mistake its own pane for an
independent reviewer; and the NGS gate remained prose-only. The second round tested the repairs and
caught a false-positive caller instruction.

The review then rejected a proposed calendar-date gate. A session boundary is not a date boundary;
the final board uses task state instead:

- the closeout agent commits the handoff and stops;
- a clean tracked tree with only the three NGS paths untracked proves the handoff landed;
- any other dirty state stops execution and requires ownership reconciliation; and
- the next fresh bootstrap starts with the read-only Step-1 audit, regardless of date.

The final package also:

- mirrors `END CURRENT BOARD` navigation into both `AGENTS.md` and `CLAUDE.md`;
- removes the false pytest exclusion and makes zero collection errors—not a fixed test count—the
  invariant;
- labels the displayed commands `STARTER MEASUREMENTS` and enumerates the strict-replacement gate
  portions they do not prove; and
- requires a reviewer from a different lane, preventing self-CLEAR.

Two post-fix sweep residues were corrected: `date test` became `task-state test`, and the fixed
4,335 count in `CLAUDE.md` became historical pre-withdrawal evidence only. Final verdict:
**COLD-START CLEAR**, conditional only on landing the handoff documents so the state gate passes.
