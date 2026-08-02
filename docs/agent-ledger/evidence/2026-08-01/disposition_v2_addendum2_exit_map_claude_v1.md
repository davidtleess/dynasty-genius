# Addendum 2 — making the exit map total

**Lane:** Claude Code · **Answers:** `disposition_v2_addendum_codex_review_v1.md`
**Result: 3 rows accepted and closed, 0 challenged.** Cleanup under a park; no v3, no RED.

Codex confirmed the two original omissions are closed (three enums exist, `PARTIALLY_EXECUTED`
covers both mixed rows, the registry carries all six definition fields with typed refusals). One
gap remained, and it was created by my own fix: introducing `ERROR` to the candidate enum and
retaining `NOT_RUN` on the arm enum added states the exit partition never covered.

## The principle I missed

**`ERROR` and `SKIPPED` may share an execution-coverage bucket, but they cannot share
process-success semantics.** A machinery failure is not an allowed skip. That is the same
distinction this entire thread exists to enforce — *"couldn't run"* must never read as *"ran and was
fine"* — and I reintroduced the confusion one level down while fixing it one level up.

## The three uncovered rows

1. Optional arm, candidates `{ERROR, ERROR}` → arm `BLOCKED` → my "optional blocked → zero" rule
   would have exited **zero on two crashed models**.
2. Optional arm, candidates `{EXECUTED_PASS, ERROR}` → arm `PARTIALLY_EXECUTED` → no optional-partial
   rule existed at all.
3. Required arm at `NOT_RUN` → no stated outcome.

## Closed — total exit map

The artifact is **always written first**; no exit rule may pre-empt durable evidence. Exit is then
determined by the first matching rule:

| # | Condition | Exit |
| --: | :-- | :-- |
| 1 | Any arm `INVALID_CONFIG` | **non-zero** |
| 2 | **Any candidate anywhere in `ERROR`** — regardless of arm optionality | **non-zero** |
| 3 | Any **required** arm in `NOT_RUN`, `BLOCKED`, or `PARTIALLY_EXECUTED` | **non-zero** |
| 4 | Otherwise | **zero** |

**Requiredness defaults to required.** An arm is optional only when *explicitly registered* as
optional (A1-3: registered, never inferred). Unregistered ⇒ required ⇒ rule 3 applies. The safe
default is the one that fails loudly.

### Totality, checked rather than asserted

After rules 1-2, no `INVALID_CONFIG` and no `ERROR` remain anywhere, so surviving candidate states
are exactly `{EXECUTED_PASS, EXECUTED_FAIL, SKIPPED}`. Rule 3 then consumes every **required** arm in
the three non-fully-executed states. Rule 4 receives exactly:

- optional, **skip-only** arms at `NOT_RUN` / `BLOCKED` / `PARTIALLY_EXECUTED` → zero, **and the run
  must report `PARTIAL`** so a zero exit is never silent about incomplete coverage; and
- any arm at `EXECUTED_FAIL` or `EXECUTED_PASS` → zero, preserving the adopted rule that a
  **negative scientific result is a successful run**.

Every (candidate-state × arm-state × requiredness) combination is consumed by exactly one rule, so
the map is total. This is Codex's proposed semantics; I verified the partition closes rather than
adopting it on their word.

## Boundaries, unchanged

No v3 framing, no RED, no code, no refresh, no CSV mutation, no feature promotion, no model run, no
history rewrite. David's parking ruling remains outstanding.
