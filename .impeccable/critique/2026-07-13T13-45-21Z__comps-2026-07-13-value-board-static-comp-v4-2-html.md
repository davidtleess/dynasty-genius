---
target: Value Board static comp v4.2
total_score: 29
p0_count: 0
p1_count: 8
timestamp: 2026-07-13T13-45-21Z
slug: comps-2026-07-13-value-board-static-comp-v4-2-html
---
Method: two independent unanchored visual passes, plus a separate contract/data and browser-accessibility pass.

## Design Health

| Dimension | Pass A | Pass B |
|---|---:|---:|
| First-viewport story | 8/10 | 8/10 |
| Fantasy-native identity | 6/10 | 6/10 |
| Information hierarchy | 7/10 | 9/10 |
| Density | 8/10 | 8/10 |
| Color discipline | 9/10 | 9/10 |
| Mobile integrity | 6/10 | 6/10 |
| Benchmark parity | 6/10 | 7/10 |
| **Mean** | **7.1/10** | **7.6/10** |

## Anti-Patterns Verdict

The comp does not read as generic AI dashboard work. The two-lane color system, dense ranking grammar, and restrained container treatment are deliberate. The detector's numbered-section warning is a false positive from dates and ranks. Em-dash cadence remains a warning in builder and receipt prose, but it is not the release blocker.

## Verdict

DUAL NOT CLEAR. Data, exact-decimal rounding, degraded-state truth, free-agent scope math, and the standalone inspector lifecycle are grounded. The frozen comp still fails the project's zero-P1 visual gate through broken mobile geometry, conflated receipt/inspector controls, inert interaction semantics, an Axe-critical ARIA error, and prototype-grade player identity.

## Priority Issues

1. **P1 - The main comp's controls still claim behavior they do not implement.** Tabs and radios do not change state; the integrated mobile sheet's close button and Escape do not dismiss it; its "swipe down" copy has no gesture implementation. The standalone inspector is a real dialog, but that does not make the integrated sheet operable.
2. **P1 - Mobile conflates the metric receipt with the player inspector.** Every mobile row has only an inspector chevron labeled "metric receipt inside," removing the contract's distinct one-tap metric control.
3. **P1 - Mobile geometry is not stable across the supplied native viewports.** A fixed 44rem phone is 704px tall inside the 390x664 viewport, leaving most of the 44px thumb targets below the first viewport. At 320px, several rows wrap to 102-145px and three visual bands.
4. **P1 - The 200% reflow claim is false.** At 320px with 200% text, the integrated sheet is 254px wide but has 354px scroll width; the standalone dialog is 256px wide with 359px scroll width, and its name overlaps the close control.
5. **P1 - Axe is not zero.** `aria-selected` is illegal on the selected plain `div.mrow`, producing a critical violation; four blank action-column headers produce additional violations.
6. **P1 - Player recognition remains below the fantasy-category bar.** Initials discs and plain team text provide neither headshots nor the required team-color recognition mark.
7. **P1 - The inspector still cannot complete a football decision.** Its first viewport explains valuation math and price history but gives no role, usage, injury, depth-chart, or news context; the named adapter follow-up is still a capability gate.

## Persona Red Flags

**David, morning manager:** gets the macro answer immediately, but loses one-handed Search/Scope at common iPhone height and must leave the product to understand the football cause behind a move.

**First-time dynasty manager:** sees disciplined model/market lanes, but has to decode `pp`, signed gap direction, and missing mobile ordering/context before the row becomes actionable.

**Keyboard/screen-reader user:** encounters focusable tabs/radios that do nothing, an integrated pseudo-dialog that cannot close, a removed direct metric receipt, and an Axe-critical ARIA state on a plain div.

## Minor Observations

- Free-agent sample rows skip overall ranks without an ellipsis or Showing-N cue, so the 223-row state reads truncated.
- Mover rows say "gap widened/narrowed" instead of the contract's side-explicit "DG/market lead grew" form, making the signed current value carry extra decoding work.
- The receipt calls xVAR points above a generic position baseline, while the producer defines WR-equivalent points above replacement.

## Working Well

- Declared source SHAs match, the extractor runs cleanly, and Ruff passes.
- Universe, roster, movement, ties, exact rounding, and both free-agent scopes reproduce from the live artifacts.
- Degraded market cells correctly dash rather than presenting stale values as fresh.
- The standalone native dialog opens with close focus, closes by Escape or click, and returns focus to its opener.
- Desktop hierarchy, true-coordinate bars, receipts, and blue/amber lane isolation are strong.

## Questions to Consider

- Can the phone shell use the actual viewport height instead of a fixed 44rem canvas so the thumb rail is always fully reachable?
- Is density worth removing the direct metric receipt when the product's trust model depends on one-tap provenance?
- What is the smallest factual team mark that can ship before the headshot pipeline without weakening lane-color discipline?
