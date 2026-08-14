# TW0813-SCORER-1 GREEN review — Codex v1

**Verdict:** NOT CLEAR. Three BLOCKERs and two WARNs were found in green-review round 1.
The 27 authored RED rows are sound and GREEN satisfies them, but the post-GREEN
falsification pass found missing fail-closed contracts at external-data boundaries.

## Pins and attributed diff

- `scripts/run_realized_outcome_scoring.py` SHA-256
  `1f4c3684857a75a406d985c8ad7c2159ea81ce0c6aef3685caea6655f6cc02d5` — matched.
- `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py` SHA-256
  `e0b9f23449c57de47a942b6b51ff3448badea7e423aeb99d5efec48a96689009` — matched.
- Wiring RED `723545885e652a3cbcc004b04a398f6904022024a2eece4841bddd6af63a0137`,
  scorer unit pin `b7b0d85d3e49545df8222329b37782b175a0970404f18346656f736da10cc7f9`,
  and revised legacy pins `de3b57dd1d0b8fac10211d107518980f2f22e7f991d8b84660be37116f2eb05d`
  / `7c2264b59ffac5a80ad5d0f67938715b19b8b0da8ee803d7f2f0193119b8c64f`
  all matched.
- The scorer-core delta is the v4-authorized behavior only: settled zero-game
  `status_unverified` members retain membership, withhold the floor, remain ungraded and
  rank-ineligible; verified statuses preserve the existing floor.
- The shared worktree contains unrelated capture-health, frontend, delivery, cadence-RED,
  and launchd work. None was attributed to or modified by this review.

## Findings

### G1 — BLOCKER — fail-closed terminal-state contract

`run_scoring()` catches exceptions raised *by* `schedule_loader` at
`scripts/run_realized_outcome_scoring.py:309-312`, but does not validate or catch the returned
schedule at `:313-325`. Hermetic corrupt-provider probes returned:

```text
games=[None]       -> AttributeError, marker=False
games="bad"        -> AttributeError, marker=False
schedule=[]        -> AttributeError, marker=False
```

This is neither the promised named failure nor a terminal marker. A scheduler cannot
distinguish corrupt provider shape from an interrupted process, defeating the health contract.
GREEN needs a schedule-envelope/row-shape validator (or a bounded catch around status/age
evaluation) that returns a named failed state and writes the marker. RED must pin malformed
root, `games`, and game-row shapes, plus marker presence.

### G2 — BLOCKER — PFR identity conflicts silently misroute utilization

The new consumer creates a `pfr_to_gsis` dict at
`scripts/run_realized_outcome_scoring.py:528-534` using unconditional last-write-wins. The
canonical reader is conflict-safe for its indexed directions, but PFR is a new direction here.
A two-GSIS/one-PFR fixture was accepted and its `0.75` snap share was silently assigned to the
second GSIS.

This is present in the real pinned substrate, not merely hypothetical: the current crosswalk has
7,952 GSIS rows, 7,771 distinct PFR IDs, and three PFR collisions:

```text
CartKy01 -> 00-0032430, 00-0032606
HarrAl00 -> 00-0031612, 00-0031830
MillSt00 -> 00-0029885, 00-0031059
```

The usage store contains historical `player_snap_count` rows for `CartKy01`. There are no 2026
rows for these three IDs today, so the declared 2026 week-1 result happens to avoid immediate
corruption; the adapter remains non-deterministically wrong for a governed identity conflict.
GREEN must reject/count ambiguous PFR IDs rather than assign them. RED must pin the collision.

### G3 — BLOCKER — prediction-time utilization is not semantically validated

`_parse_prediction_utilization()` at
`scripts/run_realized_outcome_scoring.py:653-674` validates container/type/role only. It accepts
`NaN`, `Inf`, `snap_share=-0.1`, and `snap_share=1.1`. The last value proceeds end-to-end into
eligible MIF as an apparently healthy metric:

```text
{'snap_share': {'status': 'ok', 'delta': -0.6000000000000001}}
```

That contradicts framing v2 §5.2 / v3 GREEN scope's parsed-and-validated per-field utilization
contract and lets an impossible snap share become a scored diagnostic. GREEN must reject
non-finite values for all numeric fields and enforce the known `[0,1]` domain for `snap_share`
with named failures; RED must add these numeric edges.

### G4 — WARN — declaration timestamp format is under-validated

`datetime.fromisoformat()` at `scripts/run_realized_outcome_scoring.py:635` accepts date-only
`"2026-08-13"` as `declared_at`. Framing v2 §5.2 explicitly calls for invalid timestamp-format
seeds, while the governed declaration uses an offset-bearing timestamp. Pin an actual timestamp
contract (at minimum date+time; preferably timezone-aware) instead of accepting a date as the
declaration time.

### G5 — WARN — provider-contact authority boundary was crossed

The active run scope says `no provider contact` and `no live nflreadpy in TDD`. The implementing
lane disclosed one live `_default_schedule_loader(2026, 1)` provider GET during verification.
The action was read-only and the disclosure is durable; it is still outside the run's stated
authority. Do not repeat it. This review deliberately used only hermetic fixtures and local
read-only stores.

## Post-GREEN falsification matrix

| Family | Independent check | Result |
|---|---|---|
| Pins / scope | Six artifact hashes; relevant diff; shared-tree attribution | Matched / bounded |
| Authored RED + revised legacy | Wiring RED, scorer unit, run contract, offseason honesty | 67 passed |
| Related contracts | Store, identity bridge, route, capture-health registration | 52 passed |
| Full repository | Full `pytest -q` | 5,938 passed, 15 failed, 12 skipped, 9 xfailed; all 15 are the standing untracked governed-cadence RED |
| Static / syntax | Ruff on four touched files; strict `py_compile` on two product files | Clean |
| Frozen declaration / denominators | Read source and existing tests; pins retain declared/eligible/exclusion coverage | Authored contracts pass |
| Identity provenance | Canonical-reader delegation, frozen DG preservation, pull-time/SHA/version stamping | Authored contracts pass |
| Identity corruption | Synthetic PFR collision + real pinned-crosswalk census | **BLOCKER G2** |
| Util numeric boundaries | `NaN`, `Inf`, `-0.1`, `1.1`; eligible MIF propagation | **BLOCKER G3** |
| Provider corruption | Malformed schedule root, `games`, and row shapes; terminal marker check | **BLOCKER G1** |
| Nonfinal boundary | Day 14/day 15, scheduled/explicit, absent/malformed gameday, zero-game offseason | Authored contracts pass |
| Declaration robustness | Wrong JSON shapes/types/duplicates plus date-only timestamp mutation | Existing seeds pass; **WARN G4** |
| Coverage / zero graded | Result, scorecard, marker denominators; zero-graded failure | Authored contracts pass |
| No-verdict / consumer ban | Recursive `decision_supported=False`; no `ff_opportunity` consumption; no recommendation vocabulary | Pass |
| Read-only / side effects | `mode=ro`, temp cleanup, no git invocation; no live provider call in this review | Pass; disclosed prior boundary is **WARN G5** |

Recorded 2026-08-14 01:08 EDT. No product code was changed by this review.
