# H2 Task 5 Daily Open Benchmark Delta

**Date:** 2026-07-05 · **Author:** Claude (implementation lead) · **Scope:** reset Task 5 — the restarted Daily What-Changed ("the daily open") on `feature/horizon2-i2-daily-open`.
**Governing law:** reset spec v1.6 §6 Task 5 + §7 seeds 28–31; DN visual benchmark (`docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`); H2 vision v3 aesthetic cordon.

## Dynasty Nerds reference

The applicable benchmark screenshots are David's 14 captures (2026-07-05, viewed directly by all three agents): primarily the **rankings** table (row grammar: identity → focal value → uncertainty → trend → chrome) and secondarily the **analyzer** two-pane structure (comparison feed + subordinate inspector). The daily open is a *delta feed*, not a rankings board, so the comparison below is against the DN row/pane grammar those benchmark screenshot(s) establish, translated through DG law (No-Verdict, two-lane isolation, receipts).

## DG evidence bundle

Captured from the final running state (route-mocked, deterministic preview):

- `frontend/artifacts/visual/daily-open-desktop.png` (1280px)
- `frontend/artifacts/visual/daily-open-mobile.png` (390px)
- `frontend/artifacts/visual/daily-open-focus-capture.png` (keyboard position on the rail)
- `frontend/artifacts/visual/axe-report.json` — `violation_count: 0`

## Primitive-library usage

The surface restarted from `frontend/src/ui/` (Task 2): `CaveatBlock`, `ChartFrame`, `DisclosureLine`, `MetricCell`, `PlayerIdentity`, `SeriesSlot`, `ValueHero`, plus the voice-guide `DailyTape`. Local shims (`tape`, `series-slot`, `value`, `mover-row` classes) deleted from the surface CSS; `DailyWhatChanged.css` now owns only the desk composition (masthead, two-pane grid, rail panels, 32px rows, baseline subordination) on the 8px grid, tokens-only. I2a code copied selectively, never merged wholesale.

## Census-zero blast radius

Task-3 audits green on the regenerated baselines: `what-changed/DailyWhatChanged.css` raw colors 0 hex / 0 oklch / 0 rgb; all five blast-radius files (CommandPalette, AppShell, TrustStrip, SystemHealthCard, DailyWhatChanged) at zero raw color values. No dark-on-dark, white-box, or ghost-token findings in the captures.

## Benchmark parity

Rows checked against the DN grammar (✓ = parity or better; → = constitutional translation; ◦ = deferred, disclosed):

- ✓ **one title** — the dated masthead ("Sunday, July 5") is the only `<h2>`; the shell names the surface.
- ✓ **desk-header tape** — manager-prose substrate facts ("Market Sync Active: 12 consecutive days tracked · Projection Update · Status: Synced"), raw values in the title layer. DN has no provenance tape at all — this exceeds the benchmark.
- ✓ **two-column desktop grid** — change feed + subordinate **right rail** (feed diagnostics, receipts, movement-history slot), mirroring the analyzer's compare-then-inspect split.
- ✓ **single-column mobile** — the shell stacks below 768px (wrapped nav row → trust strip → full-width feed). This fix also retired the Task-1 debt finding (trust-strip one-word-per-line collapse / rail squat).
- ✓ **PlayerIdentity rows** — identity leads every mover row at the 32px density constant; accessible initials fallback (headshots await the David-gated asset-pipeline decision).
- ✓ **MetricCell signed deltas** — mono tabular numerals, right-trailing, signed and neutral (no green/red, no arrows: the DN → DG translation).
- ✓ **SeriesSlot pending** — honest "Series pending" cells; **No fake PIT lines** anywhere; the sparkline column lights up only when the I2b PIT-series API exists (Hard Right Edge contract).
- ✓ **updated stamps** — Generated timestamp (human-readable, raw ISO in `title`), capture window, and model window in the rail receipts; DN's "Rankings updated" stamp, exceeded with receipts.
- ✓ **zero-mover prose** — quiet days render manager prose ("No player movement on this tape — market values held steady overnight"), never empty chart boxes or false motion.
- ✓ **exact-zero neutral dash** — an exact 0 delta renders as "—" (not movement), `-0` keeps its honest sign; disclosed via title note.
- ✓ **experimental grade declared plainly** — the trust strip states MODEL GRADE EXPERIMENTAL with the non-edge qualifier above the surface; the disclosure line sits in the desk header and every baseline section.

Intentional divergences from DN (ours is the law): no verdict colors or trend arrows; divergence counts carry the unvalidated-overlay caveat; named drop candidates suppressed; value-band dividers N/A on a delta feed (rankings-board scope).

## Visual audit

Implementer final-state audit (design-lead checklist: hierarchy, contrast, alignment, spacing rhythm, wraps, overlap, dead space, density, focus visibility, benchmark parity), performed directly on the recaptured bundle:

- Cycle 1 named ONE defect: the mobile trust-strip one-word-per-line collapse over the fixed 14rem rail (shell blast radius). Fixed (`TrustStrip.css` wrap + `AppShell.css` sub-768px stack), recaptured, re-audited.
- Cycle 2 (via the `tsc` gate + capture read): the What-Changed feed has no team data, and `PlayerIdentity` rendered an empty bordered team chip as a stray dash artifact. Fixed fail-safe in the primitive — the chip renders only for a non-empty team (the pinned primitive RED still passes; a team-supplying surface is unaffected). Recaptured.
- Cycle 3 (final): hierarchy reads top-down (date → tape → feed → subordinate baseline → rail); axe 0; focus ring visible on the rail capture; rows aligned at 32px; no overlap, no clipped text on either viewport.
- **Named defects remaining: None.**
- Recorded observations for later increments (not Task-5 defects): the shell header (trust strip + System Diagnostics card, shipped PR #114) leaves top-right dead space on wide desktop — an I4/I5 re-skin question; ValueHero's masthead cut could take a larger display size when the primitive grows a size variant; headshots/team-color chips remain behind the asset-pipeline decision (reset spec §8.10).

## David preview gate

**David preview status: PENDING — commit blocked until David preview.** Per reset spec §6 Task 5 and inviolate §3.8, this restart is a broad visual flip: the screenshot bundle above goes to David alongside the corresponding Dynasty Nerds benchmark screenshot for the parity ruling, and no commit happens before his word. Codex technical CLEAR is also outstanding (two stale pre-Task-5 pinned suites routed for amendment).
