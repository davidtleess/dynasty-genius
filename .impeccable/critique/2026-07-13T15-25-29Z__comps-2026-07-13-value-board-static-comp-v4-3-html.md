---
target: Value Board static comp v4.3
total_score: 25
p0_count: 0
p1_count: 6
timestamp: 2026-07-13T15-25-29Z
slug: comps-2026-07-13-value-board-static-comp-v4-3-html
---
Method: two independent unanchored visual agents plus an isolated technical browser/data audit by the primary reviewer. Frozen artifacts were not edited.

## Design Health

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of system status | 2 | Historical/degraded vintage is not self-contained. |
| 2 | Match system / real world | 3 | Manager prose is strong; `pp` still needs decoding. |
| 3 | User control and freedom | 2 | Scope controls change selection without changing data. |
| 4 | Consistency and standards | 2 | Receipt and inspector controls collide in the integrated row. |
| 5 | Error prevention | 2 | A selected 97-player scope can continue to display 223-player data. |
| 6 | Recognition rather than recall | 3 | Identity is readable, but 320px removes team context and receipt affordance. |
| 7 | Flexibility and efficiency | 2 | Mobile content is clipped by a non-scrollable phone viewport. |
| 8 | Aesthetic and minimalist design | 4 | Desktop hierarchy, density, and lane discipline are strong. |
| 9 | Error recovery | 2 | Integrated sheet cannot be keyboard-reopened and has no complete focus model. |
| 10 | Help and documentation | 3 | Receipts are useful when discoverable. |
| **Total** | | **25/40** | **Acceptable; major interaction/mobile fixes remain.** |

## Anti-Patterns Verdict

The surface does not read as generic AI dashboard chrome. It is deliberate and fantasy-adjacent, with disciplined lane colors and dense rows. The remaining weakness is prototype behavior masquerading as finished controls. The detector reported em-dash cadence warnings and a false-positive numbered-section advisory; neither is a release blocker. Axe found one serious product-scoped violation: the integrated selected row is an interactive element containing a focusable metric button.

## What Works

- The macro-first Daily Open answers the morning question immediately.
- Model blue and market amber remain isolated without verdict red/green.
- The July 11 PIT fixture reconciles: 468 valued, 340 board, 191 disagreements, 24 roster rows, 97 board FAs, and 14/23 movement.
- Desktop board density, degraded dashes, true-coordinate marks, and standalone inspector are strong.

## Priority Issues

1. **P1: Scope controls present false state.** Tabs and FA radios only mutate `aria-selected`/`aria-checked`; table, counts, rows, and copy do not change. Selecting Market read (97) can leave Bam Knight's no-FantasyCalc row and 223-player copy visible.
2. **P1: Mobile content is clipped, not scrollable.** `.phone` sets `overflow-y:auto` and later overrides it with `overflow:hidden`. The 390 Daily phone is 562px high with 746px of content; the hidden content includes the 12-more route, coverage line, roster summary, and legend. At 200% text it reaches 2528px while remaining hidden.
3. **P1: Integrated row conflates inspector and metric receipt.** The selected `role=button` contains the metric button; Axe flags nested-interactive. Enter does not reopen it, while clicking the metric bubbles and opens the inspector.
4. **P1: Mobile row/target contract is missed.** Movers render as three visible bands (104.8px at 390; 96.6px at 320), not exactly two lines. Metric controls are 39.5px high at 390 and 35-38x36.6px at 320; the only visible info glyph is hidden at 320.
5. **P1: The evidence pipeline is not reproducible.** The extractor has no as-of input and now reads the July 13 latest artifact plus the latest two PIT days. It emits 336/195/94 and a July 11-to-13 window, while the comp claims July 11 via that extractor. It also hard-codes `market-read 97 subset` despite deriving 94 in the same run.
6. **P1: Historical/degraded truth is stale and contradictory.** On July 13, Frame 2 still says `today's real state (Sun Jul 12)`. The degraded copy says it is showing Saturday prices while the contract-correct rows actually dash them. Mobile abbreviates the pinned vintage to `market Sat` and the bottom sheet omits it.
7. **P2: Narrow identity loses required context.** The <=360 rule hides team abbreviations; capture 09 shows name plus position rank only. Headshots remain David-gated, but keeping a compact team mark is not.
8. **P2: Receipt affordances are duplicated on desktop.** The metric chip and action column both expose identical receipt controls; collision rows add a third information control.

## Persona Red Flags

- **David, morning manager:** can understand the first macro immediately, but cannot reach clipped movers/coverage on the phone and can accidentally select a scope whose rows do not change.
- **Sam, keyboard/low-vision user:** cannot keyboard-reopen the integrated row, encounters nested controls, and loses most phone content at 200% text.
- **Jordan, first-time manager:** cannot discover a receipt at 320 because its info glyph disappears; `moves` and `pp` arrive before their meaning is established.

## Questions

- Should the static artifact expose controls at all unless the corresponding content can change truthfully?
- Can the two-line mover contract be met by moving the current level into the first line rather than adding a third visual band?
- Is the extractor's `--as-of` pin now a prerequisite for every frozen evidence bundle rather than a follow-up?
