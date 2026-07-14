---
target: Value Board static comp v4.1
total_score: 29
p0_count: 0
p1_count: 11
timestamp: 2026-07-13T13-13-09Z
slug: comps-2026-07-13-value-board-static-comp-v4-1-html
---
Method: dual-agent (A: v41_visual · B: v41_mobile_a11y), with a separate contract/data verifier.

## Design Health

| Dimension | Score |
|---|---:|
| First-viewport story | 8/10 |
| Fantasy-native identity | 6/10 |
| Information hierarchy | 8/10 |
| Density | 8/10 |
| Color discipline | 9/10 |
| Mobile integrity | 6/10 |
| Benchmark parity | 6/10 |
| **Mean** | **7.3/10** |

## Verdict

NOT CLEAR. The morning answer, two-lane color discipline, receipts, and gap-to-market story are substantially improved. The artifact still misses the required visual gate because mobile is not a persistent app shell, the inspector is not a working bottom sheet, player recognition remains initials-only, and several trust contracts regress in the actual markup.

## Priority Issues

1. **P1 - Degraded-state truth regressed.** The banner blames the market source although our refresh ordering caused the failure; it shows stale comparison values where the contract calls for dashes; and it calls the model current while printing the prior-day model build.
2. **P1 - Mobile is not a fixed two-line, sticky-control layout.** Rows occupy three or more visual bands; the Daily thumb rail begins below the first viewport; 200% text clips multiple frames.
3. **P1 - Controls claim behavior they do not implement.** The inspector close control does not close on click or Esc and cannot return focus. Tabs/radios do not change state. Search buttons misuse `role=search`, producing critical accessible-name failures.
4. **P1 - Value contracts remain incomplete.** Jeanty's desktop roster tie loses `x2`; Gabriel's ARIA subtracts native ranks across denominators; stored-gap ARIA uses unsigned raw decimals instead of signed display pp; desktop FA rows omit their under-line distances and call the basis a replacement starter.
5. **P1 - Category parity remains gated.** No headshots or team recognition marks, no integrated mobile bottom sheet, and no role/usage/news context to complete a waiver or inspection decision.

## Persona Red Flags

**David, morning manager:** gets the macro answer quickly, but cannot reach Search/Board without scrolling the Daily stack and cannot dismiss the long inspector after its header leaves view.

**First-time dynasty manager:** can read the bars, but a bare `-14pp` and native-rank collisions still need explanation; unsigned raw-decimal screen-reader copy makes the metric harder, not easier.

**Keyboard/screen-reader user:** encounters landmark-role search buttons, inert tabs/radios, a dialog without lifecycle management, and a close control with no visible focus.

## Working Well

- The macro reconciles 23 prior-day comparisons, Ali newly comparable, and 24 comparable today.
- Signed percentile points, true lane colors, scope counts, and the Legette receipt/sparkline are grounded in the live artifacts.
- Normal-size 390px and 320px frames have no horizontal overflow; product-scoped contrast checks pass.
