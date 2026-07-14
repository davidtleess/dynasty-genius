---
target: frozen Value Board static comp v4.6
total_score: 27
p0_count: 0
p1_count: 5
timestamp: 2026-07-13T18-18-11Z
slug: comps-2026-07-13-value-board-static-comp-v4-6-html
---
# Value Board Static Comp v4.6 Critique

## Method

- Verified the frozen comp, inspector, extractor, and all 12 capture bytes.
- Viewed every capture directly before source inspection in the first fresh visual lane; a second capture pass converged but disclosed mandatory-ledger exposure.
- Ran pinned, live, and invalid-pin extractor paths; reconciled exact counts, ranks, ties, deltas, FA scopes, and movement; ran Ruff and diff checks.
- Exercised natural load, receipt routes, synchronized tabs, FA radios, mobile sheet focus, native inspector focus, 390/320 geometry, and Axe in local Playwright.

## Nielsen Snapshot

| Heuristic | Score (0-4) | Evidence |
|---|---:|---|
| System status | 4 | Healthy/degraded freshness and coverage are explicit. |
| Match to fantasy workflow | 3 | Macro answer is excellent; identity remains fallback-only. |
| User control | 2 | Receipt and inspector routes are misleading or dead. |
| Consistency | 3 | Lane/rank grammar is strong; receipt behavior diverges by surface. |
| Error prevention | 1 | A player's metric can reveal another player's evidence. |
| Recognition over recall | 3 | Rows scan well, but initials require reading every identity. |
| Flexibility and efficiency | 3 | Tabs/radios now synchronize; custom sheet keyboard containment fails. |
| Minimal design | 3 | Dense hierarchy is disciplined; visible build scaffolding leaks into the receipt. |
| Error recovery | 2 | Wrong receipt data has no correction or recovery path. |
| Help and documentation | 3 | Receipts are detailed, but the inspector promises an unavailable receipt. |
| **Total** | **27/40** | **Not clear.** |

## What Works

- The Jul-11 numeric fixture, movement decomposition, scopes, ranks, ties, and rounding reproduce.
- Natural load stays at the top with the integrated sheet closed.
- Value-first accessible names, synchronized tabs, FA state switching, 44px metric targets, reduced-motion handling, degraded dashes, and standalone native-dialog open/close behavior pass.
- The 390px mobile rows, desktop hierarchy, macro-first story, lane colors, and visible sparkline range are strong.
- `no FantasyCalc read` remains the correct source-bounded wording.

## Priority Findings

### P1: Wrong-player receipts and visible scaffolding

Every metric still routes to the sole Xavier Legette receipt. Clicking Ashton Jeanty's `-14pp` focuses a Legette receipt with `+28pp`. Renaming it an exemplar does not repair interaction fidelity, and “in the build, every metric opens its own” is visible implementation scaffolding on a product surface.

### P1: Broken custom-sheet focus loop

The sheet no longer auto-opens, but its trap computes all buttons, including stubs removed from the tab order. `Tab` from Close escapes to `body`; `Shift+Tab` can programmatically focus disabled Full inspector. The sheet is neither a contained local modal nor an honest nonmodal drawer.

### P1: Root-vintage pin is fail-labeled, not fail-closed

Pinned extraction synthesizes snapshot date from `DG_AS_OF`, source time from a row, marks root `captured_at` unavailable, exits successfully, and continues emitting healthy facts. Contract v3.14 requires all three freshness facts from root metadata and a degraded state when any is missing. The comp's 12:43 PM clock is true in the tracked Jul-11 artifact, but the advertised pin cannot reproduce it.

### P1: Standalone inspector receipt is inoperable

The enabled market-history info button has no handler. The footer promises a receipt “on any value,” although focal and neighbor values are spans and no receipt UI exists. The two aria-disabled tray actions remain keyboard stops.

### P1: Identity and category parity remain below gate

Both capture passes scored identity 6 and parity 6. Initials discs and plain team text are the fallback state, not the ratified headshot/team-mark grammar. This remains David-gated but still blocks visual green.

## Secondary Findings

- Tucker Kraft still has an on-metric receipt and a second visible action-cell receipt despite the builder's deletion claim.
- The copy change regresses Mac Jones's 320px Daily row to 93.66px with a 35.88px wrapped detail band; the 390px row remains 81.78px/24px. No 320 Daily capture shows the regression.
- The bottom-sheet caption calls Full inspector “one tap deeper” although the control is disabled.
- Desktop first use still says `2pp` before the next sentence defines percentile points.
- At 320px, identity type remains 12/11px and Search wraps.

## Visual Gate

- Fresh capture pass A: 7.43 mean; identity 6, parity 6.
- Pass B converged at 7.43, but disclosed mandatory-ledger exposure to pass A; this cannot upgrade the failed gate.
- Required mean 8, per-dimension floor 7, and zero-P1 threshold are not met.

## Verdict

Dual NOT-CLEAR. The honesty and numerical substrate are strong, but receipt truth, keyboard containment, pinned freshness provenance, inspector operability, and the ratified identity ceiling remain blockers.
