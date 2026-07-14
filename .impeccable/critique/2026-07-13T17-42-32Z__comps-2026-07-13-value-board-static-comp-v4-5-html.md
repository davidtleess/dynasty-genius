---
target: frozen Value Board static comp v4.5
total_score: 26
p0_count: 0
p1_count: 6
timestamp: 2026-07-13T17-42-32Z
slug: comps-2026-07-13-value-board-static-comp-v4-5-html
---
# Value Board Static Comp v4.5 Critique

## Method

- Frozen HTML, inspector, extractor, and all 12 capture bytes verified against the supplied hashes and inventory.
- Two unanchored visual passes reviewed every capture before inspecting the implementation.
- Root browser pass exercised natural load, tabs, FA radios, receipts, mobile sheet focus, keyboard behavior, 320/390 layouts, 200% text, and the standalone inspector.
- Pinned and live extractor runs, invalid-pin fail-close, Ruff, Axe, and `git diff --check` completed.

## Nielsen Snapshot

| Heuristic | Score (0-4) | Evidence |
|---|---:|---|
| System status | 4 | Freshness, degraded state, and coverage are unusually explicit. |
| Match to fantasy workflow | 3 | Player-first copy is strong; `pp` is undefined in the desktop opening view. |
| User control | 2 | Several displayed routes are stubs; the composed sheet opens on load and captures focus. |
| Consistency | 3 | Lane, rank, and no-read language are strong; receipt behavior is inconsistent by surface. |
| Error prevention | 2 | Universal receipt routing silently opens the wrong player's data. |
| Recognition over recall | 3 | Values and lane direction scan well; initials-only identity limits recognition. |
| Flexibility and efficiency | 2 | Tab scope desynchronizes and most disabled controls remain keyboard stops. |
| Minimal design | 3 | Dense rows are controlled; the detached receipt reads like an audit panel. |
| Error recovery | 2 | Wrong-player receipt and dead workflow routes provide no recovery explanation. |
| Help and documentation | 2 | Receipts explain the metric, but not per-row truth; inspector context remains future capability. |
| **Total** | **26/40** | **Not visually or behaviorally clear.** |

## What Works

- Data, rank, tie, rounding, movement, FA-scope, and no-read contracts reproduce from the 2026-07-11 pin.
- Degraded rendering fails closed; no stale market value is shown as fresh.
- No-verdict color discipline, true-coordinate bars, density, and desktop hierarchy are strong.
- Normal 320/390 geometry, 44px metric targets, FA state synchronization, native inspector dialog behavior, and Axe checks pass.
- `no FantasyCalc read` is the correct source-bounded product wording and should remain.

## Priority Findings

### P1: Receipt integrity

Every metric chip routes to the single Xavier Legette exemplar. Clicking Ashton Jeanty's `-14pp` opens a receipt titled Xavier Legette with `+28pp`; focus remains on the now-offscreen Jeanty control. Daily desktop receipt controls are separate disabled action buttons, and Sean Tucker retains duplicate receipt affordances.

### P1: Accessible metric names

All metric controls replace their visible value with the generic accessible name `Metric receipt`, so voice users cannot target `-14pp`, `+28pp`, or `within band` by label. The mobile mover value has no neighboring bar sentence to recover the lost meaning.

### P1: Modal and keyboard truth

The mobile sheet auto-opens and focuses its close button during page load, scrolling the document to the bottom instead of the composed top. Its `aria-modal` claim is local to the phone frame: controls elsewhere in the document remain interactive and can receive focus while the sheet stays open. Seventy-one `aria-disabled` controls remain tabbable, including dead actions inside the focus trap.

### P1: Navigation state

Each tablist updates only itself. Navigating universe to roster and back leaves the destination tablist's selected state stale, so the same visible frame can advertise contradictory active tabs.

### P1: Pinned freshness provenance

The extractor reconstructs root `captured_at` from the first row timestamp when pinning. That produces `2026-07-11T15:08:18Z`, not the governed root build clock `2026-07-11T16:43:14Z`. The pin reproduces values but cannot truthfully reproduce root freshness metadata; root metadata must be persisted with history or fail closed.

### P1: Workflow and identity ceiling

The selected-row inspector, trade tray, and most visible commands are dead comp stubs. The two fresh visual passes score identity and parity at 6 because the repeated initials discs still make player recognition slower than category products. This remains David-gated, but it still blocks visual green.

## Secondary Findings

- Desktop copy uses `pp` before defining it; a first-time manager can read it as fantasy points.
- Mobile Mac Jones copy says `its lead grew`, leaving the antecedent ambiguous; use `the market lead grew`.
- The receipt card is narrow and detached below the board, leaving dead horizontal space and reading like an internal audit panel.
- At 320px, player names fall to 12px and metadata to 11px; the layout fits but scan quality drops.
- Large saturated position discs compete with the deliberately quiet model/market lane marks.
- The inspector sparkline has no visible range or min/max, so its cropped scale can overstate volatility.
- Receipt flash motion has no `prefers-reduced-motion` override.

## Visual Gate

- Fresh pass A: 7.6 mean; identity 7, parity 6.
- Fresh pass B: 7.3 mean; identity 6, parity 6.
- Required whole-viewport threshold is not met.

## Verdict

Dual NOT-CLEAR. The data and honesty substrate are strong, but receipt correctness, keyboard/modal truth, pinned freshness provenance, and the identity/workflow ceiling must be resolved before this comp can be treated as implementation-ready.
