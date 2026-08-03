# COLD-START CLEAR — current handoff board

**Recorded:** 2026-08-03 13:32 EDT

**Reviewed surface:** actual diffs in `AGENT_SYNC.md`, `AGENTS.md`, and `CLAUDE.md`

## Verdict

**CLEAR.** A memoryless agent now receives one current board, one first task, and an executable
landing-state test. Historical boards cannot compete with current authority, and neither a fixed
calendar date nor a remembered pytest exclusion controls execution.

## Enumerated checks

1. Current board starts below the standing Studio wall and ends at an explicit
   `END CURRENT BOARD`; both bootstrap files instruct agents to stop reading there.
2. The committed-handoff precondition is exact: tracked tree clean, with only the three duplicate
   NGS code/test paths untracked. Any other state stops execution and preserves unknown work.
3. Opening work is Step 1 only and read-only: strict-replacement evidence before removal.
4. Independent CLEAR—not self-review—is the transition to the already-authorized withdrawal.
5. Calendar-date logic is withdrawn. The authoring agent lands the board and stops; the next fresh
   bootstrap opens Step 1 regardless of date.
6. The duplicate gitignored data tree remains outside withdrawal authority.
7. Displayed commands are labelled starter measurements and explicitly do not claim to close the
   full per-family/season, export-hash, identity, registry, and focused-contract gate.
8. The false pytest exclusion is removed. Zero collection errors is the invariant; 4,335 is marked
   historical pre-withdrawal evidence rather than a future expected count.
9. CFBD promotion remains Step 2 behind framing/RED/GREEN; bakeoff/model/feature use remains
   deferred. QB-1 remains scheduled only, with execution unauthorized and H2 rushing UNDER TEST.

## Remaining transition

These protections become the real cold-start state only when the handoff documents are committed.
Until then, the landing gate correctly returns STOP. Commit/push authority remains David's.
