# Design

> The HOW layer beneath `PRODUCT.md`. Captured from the shipped visual system
> (`frontend/src/styles/tokens.css`, `frontend/src/styles/motion.css`,
> `frontend/src/ui/ui.css`) and the foundation-redo synthesis
> (`docs/strategies/2026-07-07-design-foundation-redo-synthesis.md`). Governing law: H2 vision
> spec v3 §3 (tokens) + §8 (aesthetic cordon), reset spec v1.6, `00-product-constitution.md`.
> Working draft, tracked in-repo; changes committed only with David's word.

## Theme

Film-room charcoal, dark-first (`[data-theme="dark"]` on `index.html`); a light scope carries the same hues. Hue *meaning* is constitutional and identical across themes — themes shift lightness/chroma only. Dark elevation = lighter surface (a 4%→16% white overlay ramp), desaturated accents, AA 4.5:1 against the *elevated* surface, charts on their own dark palette.

## Color (OKLCH only; tokens only — raw color literals are test-banned in governed files)

- Canvas `--dg-bg` `oklch(0.16 0.010 250)` · surfaces `--dg-surface` / `--dg-surface-raised` step up in lightness.
- Ink `--dg-text` `oklch(0.92 0.005 250)` · `--dg-text-muted` `oklch(0.68 0.008 250)`.
- Borders `--dg-border` / `--dg-border-strong`. Whitespace + single-direction 1px rules over zebra (zebra collides with hover/selected).
- **Model lane (the product's voice): blue** `--dg-model` family, hue 255 — must actually frame model objects on the primary surface.
- **Market lane (overlay only): amber** `--dg-market` family, hue 75 — frames market objects only; never blended into a model reading.
- Structural warnings only: `--dg-caveat` / `--dg-cliff`. **No green/red anywhere. No verdict hues.**
- Position categoricals (`--dg-pos-*`) and the DVS neutral ramp (`--dg-dvs-floor/ceiling`) are orthogonal to both lanes and to delta color — three token families that must never collide.
- Focus: `--dg-focus` high-contrast ring, both themes.
- **Content-is-style:** the visual system is built from the data itself — team colors as micro-accents (rings/chips, never row-fills), lane hues on lane objects, and **type weight/size as the primary contrast lever.** This is what lets a striking surface keep the blue/amber isolation clean.
- **Accent-subordination law:** the lane hues (blue/amber) own the primary chroma on any row. Position categoricals and team marks render desaturated/muted — a small low-chroma dot or ring on neutral, never a saturated fill — and at most one non-lane accent carries real chroma per row. A dense row must never become a rainbow (5–6 saturated points) that drowns the model/market lanes.
- **Palette caveat:** the Sleeper position-hue *family* (QB pink/red, RB teal, WR blue, TE orange) is David's muscle memory and a high-confidence direction, but exact hexes must NOT enter the token spec without direct screenshot sampling (Codex cross-review gate). Position hues render as chips/badges/rings only.

## Typography (self-hosted @fontsource, latin subsets; no network fonts)

- Display: **Archivo** (`--dg-font-display`) — surface titles, the focal value number, band-divider labels.
- Body: **IBM Plex Sans** (`--dg-font-sans`).
- Data: **IBM Plex Mono** (`--dg-font-mono`), `font-variant-numeric: tabular-nums`, numerals right-aligned so columns compare digit-by-digit; consistent decimal precision per column. **Mono is for numeric values only** — non-numeric metadata (player names, position labels, team abbreviations, column headers) is Plex Sans. Monospacing text labels drags the surface back toward a terminal/diagnostics look (Gemini product-edge note).
- Fixed rem scale: `--dg-text-sm` 0.8125rem · `--dg-text-base` 0.9375rem · `--dg-text-lg` 1.125rem. The drama is weight-and-scale hierarchy — a big focal Archivo value against muted mono support columns — not color or chrome. `ValueHero` may take a larger display size than today; it is currently undersized versus the destination.

## Layout & the canonical row

- Cockpit grid: rail · trust strip · main · inspector drawer; 12-col / 8px baseline; spacing tokens `--dg-space-1..4` (0.25–1rem), paddings on a 4px grid (4/8/12). Wide content scrolls in its own container; the page never scrolls sideways. Two-pane "compare-then-inspect" is the desk signature.
- **Density: 32px data rows** (fantasy-native, not "too much"), 4–7 visible columns, depth behind tap/hover. The identity column freezes under horizontal scroll; the sparkline sits in the rightmost slot.
- **The row is a fixed grammar** (PRODUCT principle 2): `rank · position-rank chip · identity · ONE focal value · named-window trend · status/receipt chips`. Current value + delta travel together (`4,812 / +109 · +2.3%` — "+109 of what?" is never left unanswerable). No repeated per-row labels; the column header carries the label once and states the sort basis.
- **The Daily Open opens with a roster-level summary line** — the macro answer in manager prose before any rows ("Your roster overnight: model value +1.2%, market −0.4%" / "Quiet morning — no model changes, market held"). It answers "how did my roster do?" first; the individual rows are the drill-down beneath it.
- **First-viewport order is declared, not recency-driven.** On desktop and mobile the first viewport preserves the surface's declared order and lane symmetry; "top changed rows" is never a market-only recency lead, and system/trust/caveat plumbing is never the primary story (scaffolding-hide proportionality).
- **Layered caveats:** only high-priority blocking warnings (e.g., the ≥26h stale badge) render as active layout blocks in the primary viewport; minor disclaimers, model-basis notes, and diagnostics live in a collapsible caveats/provenance drawer or the inspector — the main viewport stays a clean fantasy narrative, never a status board.
- **Mobile is a first-class layout:** first screen = daily tape + roster summary + top changed rows (declared order); collapsed nav; a status pill replaces pinned panels; the inspector is a bottom sheet; two-line row cards; no horizontal overflow, no multi-thousand-px scroll.

## Components

Compose from `frontend/src/ui/` primitives — never rebuild locally: ReceiptTrigger, CaveatBlock, MetricCell, ValueHero, PlayerIdentity, SpreadBar, ValueBandDivider, GradedBar, DailyTape, DisclosureLine, SeriesSlot, ChartFrame. Radius vocabulary: 4px controls/blocks, 6px region containers, 3px chips. One focus grammar: 2px `--dg-focus` outline, offset 2. Every quiet/pending/failure state is a *designed* primitive state, never raw text.

## Motion (plain CSS, Carbon-derived tokens; no motion runtime)

- Tokens: `--dg-duration-fast-01/02` (70/110ms) · `moderate-01/02` (150/240ms) · `slow-01/02` (400/700ms) · `chart-stage` (1000ms); `--dg-ease-productive-standard/entrance/exit`.
- Two-tier policy: productive motion everywhere data-facing; expressive rationed to rare significant moments. Allowed: hover/focus feedback, receipt reveal, drawer, row settle, skeleton shimmer mirroring real layout, FLIP row-reorder for object constancy, a single non-looping settle that marks a row changed since the last capture (object-constancy cue only — reduced-motion-safe, no color shift, no size change, no confidence or urgency semantics; it says "new since your last visit," never "act on this"), staged (axes→marks→labels) chart updates over real data, and ONE orchestrated daily-open entrance (David-previewed) — narrowed: a data-state reveal tied to the changed rows, never decorative choreography; content is fully present and readable without the animation (never gated on it), productive timing, reduced-motion equivalent. This is the deliberate project-law exception to the impeccable product register's default "no orchestrated page-load sequence."
- Forbidden: pulsing/looping ambient motion in data regions, urgency shimmer, bounce/stretch, count-up on sort/filter (only on first hero reveal), drawing past the Hard Right Edge, motion implying confidence or action.
- Every motion class carries a `prefers-reduced-motion: reduce` override.

## Signature elements (spend boldness on these — visible, not reserved for honesty mechanisms)

Boldness goes to the elements that make the surface striking *and* legible: the **focal value number** as a real hero; **player identity** (faces, team-color marks); the **per-row uncertainty σ bar** with its printed number (a place DG *exceeds* the benchmark — fold CIs, not ranker disagreement); **inline sparklines** with an endpoint dot and printed current value, terminating at the **Hard Right Edge** (empty grid beyond); **tier/value-band dividers** with group total + league rank in the header (`QUARTERBACKS (5) — 10,140 (5/12)`); **hero moments** (player-highlight card, graded bars, Franchise Equity = roster value + owned valued picks + equity trend); and the **one daily-open entrance**. **A hero is never a system-nominated single player on a descriptive surface** — it is user-selected, David-supplied, aggregate, or lane-symmetric and non-actionable; a tool picking "the biggest mover" is the banned MoverHero pattern. Receipts, the daily tape, and the Hard Right Edge remain signatures too — but as designed elements, not the *only* place craft is allowed.

## Enforcement (best-in-class made testable, not vibes)

Three gates stand between an idea and a visual GREEN:

- **Shape before code (pre-build).** Before implementing any surface, produce a composition artifact: the 5-second answer (what the manager learns in five seconds), the focal hierarchy (what owns the eye), a desktop + mobile viewport sketch, and the lane-order statement. Composition is judged here — the scored audit must never be the first time it is judged.
- **Objective blockers (automated checks).** The scaffolding-hide law as a DOM/screenshot audit on user routes: fail on any visible raw schema token, snake_case key, database ID, ISO timestamp, or diagnostics/`Status:` plumbing outside approved receipt/drawer/dev surfaces. A viewport-first product test: the first screen is a fantasy/asset story, not system status. Receipt containment (provenance/health/raw IDs live behind approved primitives). Benchmark component grammar: AssetRow primitives present on rankings/daily-open surfaces. No naked diagnostics (SystemHealthCard, raw health labels) in primary content regions.
- **The unanchored scored audit (human/agent taste).** "Jaw-dropping" is gated by a mandatory independent fresh-agent visual audit: each of the seven rubric dimensions (first-viewport story, fantasy-native identity, information hierarchy, density, color discipline, mobile integrity, benchmark parity vs the Sleeper/DN/KTC bar) is scored 1–10. **Pass = two independent unanchored passes, each mean ≥ 8/10, no single dimension < 7, and zero P0/P1 findings.** The evidence bundle — desktop + mobile + mandatory mid-scroll captures + the scored rubric — is written to `docs/design-audits/YYYY-MM-DD-<surface>.md`. Fresh agents score; David ratifies the visual GREEN; any dimension below the floor blocks the ship. Not brittle aesthetic snapshots.

**Integrity guardrails (do not let aspiration break the frame):** aspiration words must not become verdicts; rich color must not weaken lane isolation or reintroduce verdict green/red; fantasy-native polish must not make unvalidated market data look decision-grade; hiding scaffolding must never hide caveats (translate to manager prose, never delete); the scored audit must stay unanchored and failure-seeking so it never rubber-stamps.
