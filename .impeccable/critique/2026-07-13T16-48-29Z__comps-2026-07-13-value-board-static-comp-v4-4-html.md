---
target: frozen Value Board static comp v4.4
total_score: 29
p0_count: 0
p1_count: 8
timestamp: 2026-07-13T16-48-29Z
slug: comps-2026-07-13-value-board-static-comp-v4-4-html
---
Method: dual-agent (A: v44_visual_fresh_a and v44_visual_fresh_b, isolated visual gates; B: v41_mobile_a11y, isolated browser/a11y audit)

## Design Health

Two independent seven-dimension audits failed the ratified visual gate:

| Dimension | Pass A | Pass B |
|---|---:|---:|
| First-viewport story | 8 | 8 |
| Fantasy-native identity | 6 | 6 |
| Information hierarchy | 8 | 8 |
| Density | 8 | 8 |
| Color discipline | 9 | 9 |
| Mobile integrity | 7 | 6 |
| Benchmark parity | 6 | 6 |
| Mean | 7.4 | 7.3 |

Gate: NOT CLEAR. Both means are below 8 and both have dimensions below 7.

## What Works

- The aggregate morning answer leads and reconciles 14/23, five at 2pp+, nine at 1pp, 22/23 market-price changes, and Ali newly comparable.
- The model and market lanes remain visually isolated without verdict colors. The degraded state correctly dashes the unavailable market lane.
- Desktop density, true-coordinate bars, tie labels, no-read language, FA replacement truth, and the full inspector are strong.
- `DG_AS_OF=2026-07-11` independently reproduces 12,201 rows, 340 board rows, 191 disagreements, 145/46/149 signals, 24/27 roster coverage, 97/223 FA scopes, and 14/23 movement. Ruff and Axe pass.

## Priority Issues

1. **P1 - The integrated sheet is not actually modal.**
   `aria-modal=true` is present, but initial focus remains on BODY, the board is not inert, and Tab leaves the sheet after its two actions. Close, Esc, focus return, and reopen work. Source: `2026-07-13-value-board-static-comp-v4.4.html:598-614,654-661`.

2. **P1 - FA switching breaks keyboard state.**
   The active radio is hidden before focus is restored, so focus falls to BODY. Global label-based synchronization also compares desktop `With market read (97)` with mobile `Market read (97)`; after switching back, the mobile group has no checked radio and no tab stop while all-valued content remains. Source: `:567,634-653`.

3. **P1 - Keyboard tabs cannot cross the disabled middle tab.**
   ArrowLeft/ArrowRight always target the immediately adjacent tab. `Other Teams` is disabled, so keyboard users cannot travel between My Roster and Full Universe. Mouse navigation scrolls correctly, but focus remains on the now-offscreen source tab. Source: `:264,362,623-632`.

4. **P1 - The v4.4 receipt de-duplication broke the contract.**
   The signed metric is now a plain span and the only receipt control is in the far-right action cell. The ratified law requires the receipt control on the metric itself and evidence next to the number. Keep the metric control and remove the duplicate action-column receipt, leaving the inspector chevron distinct. Source: `:278-284,374-377,443-448`; contract `2026-07-08-value-board-composition-v3.md:380`.

5. **P1 - Enabled-looking controls remain dead ends.**
   Search, thumb actions, most row controls, and both integrated-sheet actions are focusable buttons without handlers or disabled treatment. The standalone inspector has the same inert tray actions. This makes the comp unreliable for workflow testing. Source: `:167,222,265,363,433,464,520,538,559,578,610-611`; inspector `:113-128`.

6. **P1 - 200% text clips the mobile FA scope control.**
   At 320px/200%, the radiogroup is 201px wide but needs 252px; the second button extends about 50px past the clipped container. Normal 390/320 widths otherwise pass. Source: `:99,110,139-152,567`.

7. **P1 - Mobile movement grammar can reverse the first read.**
   `down-arrow DG lead grew 4pp -> +28pp` visually attaches the down arrow to the DG lead even though the arrow means market-price direction. Its explanation appears below the rows and outside the first viewport. Restore a compact `market price down` label or separate the price and gap facts. Source: `:513`; capture `06-390-daily-firstviewport.png`.

8. **P1 - The visual gate still fails on identity and category parity.**
   Every row and the player inspector use initials-only discs without headshots or team-color recognition marks. Both fresh passes scored identity and benchmark parity 6/10. This is a David-gated ceiling, not a hidden technical pass. Source: `:58-61`; captures 01, 03, 07, 09, 10.

9. **P2 - The evidence bundle mislabels a capture.**
   `05-fa-mkt-state.png` does not show the named desktop market-read state; it shows the mobile all-valued state and Frame 7. `05b-fa-all-state.png` correctly shows all-valued, so the market-read toggle lacks a truthful named capture.

10. **P2 - Extractor documentation still hard-codes the old live scope.**
    Runtime output correctly derives 94 on the live Jul-13 run, but the docstring and V4 comment still call it the 97-row board pool. Source: `comp-v33-extract.py:19,662`.

## Minor Observations

- `2pp+` appears before percentile points are explained, especially on mobile.
- The sticky thumb rail partially covers the next content band in the 390 first-viewport capture.
- At 320px, `Search - in My Roster` wraps while the adjacent Scope button stays on one line.
- The detector found only em-dash cadence advisories and a numbered-marker false positive; these are not release blockers here.

## End-User Read

The screen now answers the morning question quickly and preserves trust. It still asks a first-time manager to decode two directional systems in one mobile line, and it does not yet provide the player-recognition speed or football context expected from Sleeper/DynastyNerds/KTC. The latter is a known David-gated capability ceiling; it still means the current pixels cannot be called visual GREEN.
