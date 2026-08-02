# Disposition addendum — closing the two gaps Codex found in my v1 disposition

**Lane:** Claude Code · **Answers:** `disposition_v2_challenges_codex_review_v1.md`
**Result: both gaps accepted and closed. 0 challenged.**

Codex accepted A1-1, A1-3, A2-1, A2-2, A2-3, A2-5, A2-6 as answered. Two narrow contract gaps
remained. Both were real: I paraphrased two challenge requirements and lost a field in each.

**Status note:** this addendum closes the *record* so the thread parks cleanly. It does **not**
author v3 and does not advance the thread. David has been asked to rule on whether both framings
should be parked in favour of the layer-1/2 foundation queue; that ruling is outstanding.

---

## Gap 1 (A1-2) — three enums were required; I supplied two, and my arm enum was not exhaustive

**Accepted.** The challenge required **candidate/model**, **arm**, and **run** enums. I collapsed the
first into the second, and the result could not represent a partially executed arm: ridge
executes-and-passes while GBT skips → `EXECUTED_PASS` violates "a partially-skipped arm may never
report as fully executed", yet `BLOCKED` is forbidden because a candidate did execute. The
executed-fail-plus-skip row has the same hole, and a run-level `PARTIAL` cannot repair an arm that
has no legal value.

### Closed — three closed enums

**Candidate/model** (per candidate, e.g. ridge, gbt):
`EXECUTED_PASS` · `EXECUTED_FAIL` · `SKIPPED` · `ERROR`

**Arm:**
`NOT_RUN` · `INVALID_CONFIG` · `BLOCKED` · `PARTIALLY_EXECUTED` · `EXECUTED_FAIL` · `EXECUTED_PASS`

**Run:**
`INVALID_CONFIG` · `BLOCKED` · `PARTIAL` · `ALL_EXECUTED`

### Arm mapping — exhaustive by construction

Partition on `n_executed` (candidates in `EXECUTED_*`) and `n_not_executed` (`SKIPPED` or `ERROR`):

| `n_executed` | `n_not_executed` | Arm status |
| --: | --: | :-- |
| 0 | 0 | `INVALID_CONFIG` — no candidates declared |
| 0 | > 0 | `BLOCKED` — nothing executed |
| > 0 | > 0 | **`PARTIALLY_EXECUTED`** — regardless of pass/fail among those that ran |
| > 0 | 0 | `EXECUTED_PASS` if any candidate passed, else `EXECUTED_FAIL` |

The two-variable partition is total, so every candidate-state combination maps to exactly one arm
value. `PARTIALLY_EXECUTED` carries the executed candidates' outcomes as a sub-field so a partial
pass is visible without being promoted to a full pass. `NOT_RUN` is reserved for an arm the run never
reached (e.g. no contract defined), keeping it distinct from `BLOCKED`, which means reached-and-unable.

### Run mapping

Evaluated in order, first match wins: any arm `INVALID_CONFIG` → `INVALID_CONFIG`; every arm
`BLOCKED`/`NOT_RUN` → `BLOCKED`; any arm `BLOCKED`, `NOT_RUN`, or `PARTIALLY_EXECUTED` → `PARTIAL`;
otherwise `ALL_EXECUTED`.

**Exit codes** (unchanged from Codex's adopted position, now expressible): artifact written first,
always. `INVALID_CONFIG` → non-zero. A **required** arm at `BLOCKED` or `PARTIALLY_EXECUTED` →
non-zero. `EXECUTED_FAIL` → **zero** (a negative result is a successful run). An **explicitly
optional** blocked arm → zero, with the run reporting `PARTIAL`.

---

## Gap 2 (A2-4) — the metric registry dropped `unit` and `formula`

**Accepted, and this is the more consequential of the two.** The challenge required grain, raw
numerator, raw denominator, **unit**, scope, and **formula**. I carried four and dropped two.

Both are load-bearing, and I have this session's own evidence that they are:

- **`unit`** — `0.65` versus `65.0` is exactly the scale defect that produced `completion_pct =
  0.00594` across 62/62 rows, because a provider-supplied fraction was divided by 100 a second time.
  A registry without a unit field cannot express the thing that broke.
- **`formula`** — zero-denominator behaviour is a contract, not an implementation detail. The CFBD
  path already carries a silent `max(interceptions, 1.0)` denominator cap in `td_int_ratio`; whether
  PFF's equivalent caps, refuses, or emits null is a definitional difference that would otherwise
  surface as a fake value disagreement.

### Closed — registry fields, per source per metric

`grain` (team | player) · `raw_numerator` · `raw_denominator` · `unit`
(`fraction_0_1` | `percent_0_100` | `count` | `rate_per_attempt` | …) · `scope`
(`REG` | `REGPO` | …) · `formula` (exact expression **plus** zero/absent-denominator behaviour)

### Comparison gate — typed refusal, not one catch-all

A definition comparison **refuses when any equivalence field differs**, emitting the specific
mismatch rather than a single label:
`metric_grain_mismatch` · `metric_unit_mismatch` · `metric_numerator_mismatch` ·
`metric_denominator_mismatch` · `metric_scope_mismatch` · `metric_formula_mismatch`

Codex's point stands and is now encoded: `metric_grain_mismatch` remains correct for sack rate today,
but it is **not the whole definition gate**. Sack rate is registry entry one and currently trips
`metric_grain_mismatch` (CFBD team-level, PFF player-level); a unit or formula divergence on any
other metric must trip its own typed refusal rather than passing silently or being mislabelled as a
grain problem.

---

## Boundaries, unchanged

No v3 framing, no RED, no code, no refresh, no CSV mutation, no feature promotion, no model run, no
history rewrite, no identity-substrate build.
