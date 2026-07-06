# Design

> Captured from the shipped visual system: `frontend/src/styles/tokens.css` (semantic OKLCH tokens, both theme scopes), `frontend/src/styles/motion.css` (Carbon-derived motion tokens), `frontend/src/ui/ui.css` (the DG primitive library). Governing law: H2 vision spec v3 §3 (tokens) + §8 (aesthetic cordon), reset spec v1.6. Untracked working file — not committed without David's word.

## Theme

Film-room charcoal, dark-first (`[data-theme="dark"]` on `index.html`). Hue meaning is constitutional and identical across themes — themes may shift lightness/chroma only. A light scope exists with the same hues.

## Color (OKLCH only; tokens only — raw color literals are test-banned in governed files)

- Canvas: `--dg-bg` `oklch(0.16 0.010 250)` dark · surfaces `--dg-surface` / `--dg-surface-raised` step up in lightness.
- Ink: `--dg-text` `oklch(0.92 0.005 250)` · `--dg-text-muted` `oklch(0.68 0.008 250)`.
- Borders: `--dg-border` / `--dg-border-strong`.
- **Model lane (the product's voice): blue** `--dg-model` family, hue 255.
- **Market lane (overlay only): amber** `--dg-market` family, hue 75.
- Structural warnings only: `--dg-caveat` / `--dg-cliff` (amber family). **No green/red anywhere. No verdict hues.**
- Focus: `--dg-focus` high-contrast ring, both themes.
- Position categoricals (`--dg-pos-*`) orthogonal to both lanes; DVS neutral ramp `--dg-dvs-floor/ceiling`.

## Typography (self-hosted @fontsource, latin subsets; no network fonts)

- Display: **Archivo** (`--dg-font-display`) — surface titles, big ranks, band-divider labels.
- Body: **IBM Plex Sans** (`--dg-font-sans`).
- Data: **IBM Plex Mono** (`--dg-font-mono`) with `font-variant-numeric: tabular-nums` — every numeral column aligns; numerals right-aligned.
- Fixed rem scale: `--dg-text-sm` 0.8125rem · `--dg-text-base` 0.9375rem · `--dg-text-lg` 1.125rem. Tight ratio, product register.

## Layout

- Cockpit grid: rail · trust strip · main · inspector drawer. 12-col / 8px baseline grid; spacing tokens `--dg-space-1..4` (0.25–1rem).
- **Density: 32px data rows** (~"80% of Bloomberg"). Wide content scrolls in its own container; the page never scrolls sideways. Structural responsive behavior (collapse, reflow) below 768px.

## Components

Compose from `frontend/src/ui/` primitives — never rebuild locally: ReceiptTrigger, CaveatBlock, MetricCell, ValueHero, PlayerIdentity, SpreadBar, ValueBandDivider, GradedBar, DailyTape, DisclosureLine, SeriesSlot, ChartFrame. Radius vocabulary: 4px controls/blocks, 6px region containers, 3px chips. One focus grammar: 2px `--dg-focus` outline, offset 2.

## Motion (plain CSS, Carbon-derived tokens; no motion runtime)

- Tokens: `--dg-duration-fast-01/02` (70/110ms) · `moderate-01/02` (150/240ms) · `slow-01/02` (400/700ms) · `chart-stage` (1000ms); `--dg-ease-productive-standard/entrance/exit`.
- Allowed: hover/focus feedback, receipt reveal, drawer, row settle, ONE orchestrated daily-open entrance (David-previewed), staged chart updates over real data.
- Forbidden: pulsing deltas, urgency shimmer, bounce/stretch, drawing past the Hard Right Edge, motion implying confidence or action.
- Every motion class carries a `prefers-reduced-motion: reduce` override.

## Signature elements (spend boldness here only)

The **Hard Right Edge** on every trend line; **receipts** (focusable provenance on every number); the **daily tape** (capture streak · last capture · model vintage, in manager prose). Everything else stays quiet.
