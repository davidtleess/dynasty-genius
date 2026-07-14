---
target: Value Board static comp v4 and inspector v2
total_score: 24
p0_count: 0
p1_count: 8
timestamp: 2026-07-13T12-41-34Z
slug: value-board-static-comp-v4
---
# Value Board Static Comp V4 - Dual-Lane Critique

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of system status | 3 | Fresh and stale states are legible, but the stale-cause sentence is false. |
| 2 | Match system / real world | 2 | `pts`, `ranks differ`, and the xVAR definition contradict the underlying measures. |
| 3 | User control and freedom | 1 | The inspector cannot be dismissed and most apparent controls are inert. |
| 4 | Consistency and standards | 2 | Signed deltas, tie disclosure, no-read copy, and two-line mobile grammar drift by scope. |
| 5 | Error prevention | 2 | The stale pause is strong, but MoverHero and hidden FA distances can nudge. |
| 6 | Recognition rather than recall | 2 | Initials-only identity and unexplained 23/24 populations slow recognition. |
| 7 | Flexibility and efficiency | 2 | Dense rows scan well, but search, tabs, toggles, and thumb rails do not operate. |
| 8 | Aesthetic and minimalist design | 3 | Clean lane discipline; defensive prose and weak identity keep it comp-like. |
| 9 | Error recovery | 3 | The stale path is explained, but inspector exit and retry/navigation are absent. |
| 10 | Help and documentation | 4 | Receipts and the market sparkline are strong, despite incorrect xVAR/rounding copy. |
| **Total** | | **24/40** | **Material revision required** |

## Overall Verdict

**Dual NOT CLEAR.** The 2026-07-11 counts, ranks, movement arithmetic, free-agent population, and 18-day market capture reconcile. The remaining failures are contract and manager-trust failures rather than data availability problems.

## Priority Issues

### [P1] Daily Open violates the MoverHero law

`Mac Jones moved most` promotes a canonical-id tiebreak among three equal 4pp movers into a system-nominated single-player story. The first viewport must lead with the roster-level answer and keep the declared-sort mover list below it.

### [P1] Comparison units and semantics are false

The pixels and extractor render `pts` instead of percentile points (`pp`), including grammatically invalid `1 pts`. McCarthy's QB30/QB30 row says `ranks differ`; the pools differ, while the labels match. The open unsigned-chip change also conflicts with the still-ratified signed-delta contract.

### [P1] The receipt misdefines the model

xVAR is a transformed, WR-equivalent value above a position replacement baseline, not projected fantasy points against a replacement starter. The receipt also says the displayed gap rounds from lane percentiles; it rounds once from stored `model_minus_market_delta`, while endpoints round separately.

### [P1] Mobile and controls remain illustrative, not operational

Mover rows have separate `l1`, `l2`, and `l2b` blocks and wrap to four visual lines. The thumb rail is not sticky. Search, tabs, FA toggles, and disclosure affordances have no operating semantics. At 200% text, phone and inspector content clips at 390px and 320px.

### [P1] The inspect and waiver workflows stop short

The inspector dialog has no close/back affordance or focus-return contract. Free Agents announces the nearest distances below replacement but omits those distances from the player rows, so a manager cannot compare waiver proximity.

### [P1] Contract details still vary by scope

Roster/mobile Jeanty drops the `x2` tie cardinality; Braelon uses summary copy (`not covered by DG`) in place of the row state (`DG read unavailable`); mobile bar ARIA points users to a receipt instead of stating the stored gap; stale rows retain last-known comparisons where the contract calls for unavailable market cells.

### [P1] The evidence bundle cannot clear mobile

Capture `06` is a 1440px bottom-of-page slice of inline phone frames, not a native 390px or 320px first viewport. It cannot prove sticky controls, reflow, horizontal-overflow safety, or the mobile bottom-sheet inspector.

## Strengths

- The 468/340/191 universe, 9/6/9/3 roster, 223/223 FA, 14/23 movement, and tie source data reconcile.
- The blue/amber lanes, true-coordinate paired marks, within-band treatment, and explicit stale timestamps are visually disciplined.
- The inspector's 18-read market sparkline and neighbor context are grounded, useful, and clearly separated from the two-day margin window.

## Persona Red Flags

**David, morning manager:** the system picks Mac Jones, hides the 23-versus-24 population transition, and does not show the FA distances promised by its headline.

**First-time manager:** `pts` can mean fantasy points, xVAR points, or percentile points; equal QB30 labels beside `ranks differ` look broken.

**Keyboard/mobile user:** controls do not form a usable interaction model, 200% text clips, and the inspector is a trap state.

## Deterministic Evidence

The Impeccable detector returned two em-dash warnings and one false-positive numbered-marker advisory. Axe found four real empty action-column headers; composite-comp landmark findings were scaffold effects. Browser probes separately found non-operable controls, non-sticky rails, 200% clipping, and an undersized 12x17 sparkline receipt target.
