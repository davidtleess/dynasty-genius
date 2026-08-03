# Cold-start round-3 review — NOT CLEAR

**Date:** 2026-08-03  
**Reviewer:** Codex  
**Layer:** cross-layer handoff, routing to Layer 1 NGS withdrawal  
**Reviewed delta:** uncommitted `AGENT_SYNC.md` + `CLAUDE.md` against committed `292c582`

## Independent reproduction

- `HEAD == 292c582aef56c7911409c26bdfed64ab3d664284`; CI run `30837931465` is successful.
- Full collection: **4,335 tests collected, zero collection errors**.
- Claude's five-file focused command: **135 passed**.
- Adding the direct source-registry contract (`tests/test_source_registry.py`): **147 passed**.
- Worktree scope remains Claude's two modified docs plus the three preserved untracked NGS paths.

## Clear in the submitted delta

1. **F — citation path:** `src/dynasty_genius/sources/source_registry.py:381` is rerunnable and correct.
2. **D — focused contracts are now named and runnable:** the five named files independently pass 135/135.
3. **E — gate precedence:** the Step-1 list is explicitly authoritative and the starter measurements explicitly close nothing.
4. **H — factual direction:** 4,335 is the current pre-withdrawal measurement, not a past-only count.

## Blocking residuals

### R3-1 — H overcorrects into a new fixed-count claim

Both docs say 4,335 "remains/stays current until the withdrawal executes." That is false if any test
is added, removed, or parametrized before withdrawal. Pin the observation to the measured tree/state,
not the future event: 4,335 was measured at `292c582` plus the present docs-only delta and three
untracked NGS paths; it is evidence, never an invariant. A fresh agent must remeasure after any edit.

### R3-2 — B still claims landing state proves session identity

The board says `State matches -> ... You are the next session` and later `That state means you are
the next session`. The authoring agent one second after committing sees exactly the same state. The
check proves only that the handoff landed. Replace both identity claims with that narrower fact:
the authoring/landing agent must stop; a genuinely fresh bootstrap may proceed. On dirty state,
do not infer that the reader is the authoring agent; say only that the landed handoff cannot be
proved and the reader must reconcile while preserving unexpected work.

### R3-3 — G needs a positive availability handshake

`tmux_msg.py list` proves only that a pane name exists. It proves neither liveness nor willingness to
review. After discovery, require a bounded readiness message to a different lane, verify delivery
under the Wire Rule, and require an explicit `ACK available` before taking the reviewer branch. No
ACK means use the solo branch. Do not infer availability from a pane listing or spinner.

### R3-4 — the focused gate omits its direct registry contract

The authoritative gate claims "one registry adapter/store" and the starter text names registry
uniqueness, but the focused command omits `tests/test_source_registry.py`, the repository's direct
`SOURCE_REGISTRY` contract. Add it to the named list and command. The corrected six-file slice is
**147 passed**. The caller/import checks remain necessary because the registry contract alone cannot
detect an unregistered duplicate adapter.

## Dispositions on C and I

- **C — real, separate governance defect.** `docs/governance/05-layer-doctrine.md:279` points to
  `AGENT_SYNC.md:120`, now unrelated. Because `AGENT_SYNC.md` is prepended, a live line number is
  structurally unstable. Replace it through the governance process with a stable commit-and-content
  citation, e.g. commit `fce0ccee` plus the unique text `Transactions are never ingested, so layer 5
  has no substrate`. This does not require rewriting the historical AGENT_SYNC block.
- **I — not a defect; do not rewrite it.** The 13:13 ledger entry describes its then-current
  preflight at `ef0e156`. `git show 292c582^:AGENT_SYNC.md | wc -l` independently returns **1,286**.
  The current 1,418-line worktree does not make that historical measurement false. Changing it to a
  current count would falsify the record.

## Verdict

**NOT CLEAR** pending R3-1 through R3-4. F/D/E and H's factual correction are accepted. C should be
opened as a small governance citation repair; I should remain untouched.
