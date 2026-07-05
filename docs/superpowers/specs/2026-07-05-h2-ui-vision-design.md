# H2 — World-Class UI: Design Vision (the program spec)

**Date:** 2026-07-05 · **Author:** Claude (implementation lead) · **Status:** v3 — **RATIFIED by David 2026-07-05** (dual-CLEAR: Codex technical v3 CLEAR; Gemini advisory concurrence). Type taste-call decided: **Archivo + IBM Plex locked**. Increment 1 opened by David the same day. Each subsequent increment remains David-gated.
**Inputs synthesized:** Gemini product-edge framing (2026-07-05); Codex technical framing positions 1–5 (2026-07-05); frontend-design discipline; May UI-research corpus (13 docs, §9).
**Board item:** Horizon 2 (`docs/product-assessment-2026-07-04.md`, finding F12 and the David directive: "a world class front end UI — one that fantasy football gurus would drop their jaws if they saw").

## 1. The thesis

Dynasty Genius owns something no fantasy tool on earth has: **a daily point-in-time record of one league's reality, wired to a model that refuses to lie about what it knows.** The world-class move is not decoration — it is making that honesty *visible and tactile*. The product should feel like a **private trading terminal for one league**: dense, calm, fast, and so obviously serious that a guru's jaw drops at the *credibility*, not at chrome.

Two aesthetics rejected up front: generic dashboard gloss (glassmorphism/backdrop blurs — rejected: blurs data, dates fast, costs perf; Gemini's suggestion overruled with rationale), and dark-terminal-with-acid-accent (the template look). The identity comes from the product's own constitutional structure instead: **the two-lane axis IS the brand.**

## 2. The signature element: "The Hard Right Edge" + receipts

Every PIT trend surface renders history as a line that **terminates in a visible tick at the last verified capture — and the space to its right stays empty grid.** No fit curve, no arrow, no fade-out implying momentum (Gemini's extrapolation prohibition, elevated from a rule into the product's most recognizable visual). Paired with **receipts**: every number can disclose its provenance through a focusable receipt control (keyboard, touch, and press; hover as an enhancement, never the only path — the seed-9 contract) — capture date, source, vintage — and the landing header carries a thin **daily tape**: capture streak · last capture · model vintage. "Every number has a receipt" is the jaw-drop that is not a verdict; it is the one place we spend boldness. Everything else stays quiet.

## 3. Design tokens (the committed system; §Codex-1 invariants hold)

**Color (OKLCH; hue meaning is constitutional, themes change lightness/chroma only — Codex-4):**
| Token | Dark (default) | Role |
|---|---|---|
| `--dg-bg` | `oklch(0.16 0.010 250)` | film-room charcoal, slight cold cast |
| `--dg-surface` / `--dg-surface-raised` | `oklch(0.20 0.012 250)` / `oklch(0.24 0.014 250)` | cards, drawers |
| `--dg-text` / `--dg-text-muted` | `oklch(0.92 0.005 250)` / `oklch(0.68 0.008 250)` | copy |
| model lane (existing hue family) | `oklch(0.72 0.11 240)` | the model's voice — blue, unchanged meaning |
| market lane (existing hue family) | `oklch(0.75 0.12 75)` | the market's voice — amber, unchanged meaning |
| `--dg-caveat` (existing warning family) | amber, structural warnings ONLY | stale/cliff/overflow — never value judgment |
| `--dg-focus` | high-contrast ring | keyboard focus, both themes |

No green/red anywhere; signed deltas stay neutral typography (the shipped convention). Light theme = same hues, lifted lightness; `[data-theme]` scopes; guard tests evolve to parse BOTH scopes and keep enforcing hue families (Codex-4). System Health stays isolated from market tokens.

**Type (self-hosted @fontsource, latin subset — no network fonts, Codex-1; Gemini's Google-Fonts route overruled):**
- Display: **Archivo** (incl. condensed cuts) — sharp, athletic, scoreboard-adjacent without costume; surface titles, the daily-open headline, big ranks.
- Body: **IBM Plex Sans** — technical-instrument character, excellent density.
- Data: **IBM Plex Mono** with `font-variant-numeric: tabular-nums` — every number column aligns; values read like an instrument, not a paragraph.
- Scale: 8px baseline grid; large-thin display / semibold labels / mono values (Gemini's hierarchy, concretized).

**Layout:** the cockpit grid survives (rail · trust strip · main · inspector) — collapsible rail (icon mode < 768px), inspector as a URL-addressable drawer, fluid grid, density over whitespace: **32px data rows on a 12-col/8px grid, ~"80% of Bloomberg" density** (research §9.2). Wide content scrolls in its own container; the page never scrolls sideways.

**Motion:** ONE orchestrated moment — the daily open (landing regions settle with a ~150ms stagger; `prefers-reduced-motion` collapses it to none). Micro-interactions limited to receipt reveals and focus. **No urgency motion, no pulse on deltas** (Gemini mislead-risk: motion implying urgency is a nudge). Loading = skeletons, never spinners; **stale data renders desaturated (`saturate(0.6)`) with a dashed border** — staleness you cannot miss (research §9.4).

## 4. Architecture commitments (Codex positions adopted 1:1)

- **Routing (Codex-2, ownership per F1):** NO react-router. A typed internal adapter — `useUrlSurfaceState` over `history` + `URLSearchParams`, slug map, invalid slug → Daily What-Changed (Gemini seed 1), `popstate`, one `navigateSurface()` shared by rail/palette. **I1 scope = `?surface=` ONLY.** The `&player=<id>` param — including inspector hydration on reload (selected-player label + detail fetch) — is **I3 scope**, owned by the player-atom increment.
- **Charts (Codex-3):** hand-rolled SVG components (deterministic, jsdom-assertable: `<path d>`, axis labels, gap markers, an accessible summary). PIT gaps render AS GAPS; zero-crossing ranges unclamped; disclosure line adjacent to every chart; no trend language in tooltips/aria. uPlot reconsidered only if dense interactivity earns it; visx not a default.
- **Shared resource hook (Codex-5, H3 pulled forward as enabling infra):** `useEndpointResource<T>` — discriminated state, stale-request abort, generated-Zod validation at the boundary, sanitized unavailable/parse-error. No caching/retry until a surface proves the need. Trade Lab POSTs and typeahead stay separate initially.
- **Invariants (Codex-1):** token guards, SystemHealth CSS guard, banned-language AST linter, mitigation tripwires byte-pinned, generated client regenerated-only, no CDNs. The vision *expands* tokens; it never weakens a guard.

## 5. The surfaces (what each becomes; every one keeps its disclosure discipline)

1. **Daily What-Changed — "the daily open."** The morning-paper moment: the tape strip up top, mover lists with PIT sparklines (hard right edge), the two lanes visually distinct, empty days rendered as an honest quiet state ("No value fluctuations recorded today"). **No Divergence Strip here (F2): the What-Changed contract deliberately forbids model–market pairing inside its sections; the strip lives where paired lanes legitimately exist (player card, Trade Lab).**
2. **Player card / inspector — the atom of the product.** URL-addressable (`&player=` — I3); identity + aging-curve position; **two visually equal lanes** (model xVAR/drivers/grade vs market price/rank — symmetric weight, Gemini's balance rule); the first NEW **Divergence Strip** placement; receipts on every figure. **Structural-honesty contract — honest field mapping (F3):** signal = the PVO model lane (DVS/xVAR — present today); counter-argument = present today; **uncertainty range and an explicit horizon field do NOT exist in the current player DTO** — I3 begins with a David-gated card-contract slice (expose range + horizon via the existing projections/percentile machinery through OpenAPI/codegen) BEFORE the card renders the full contract. Degradation semantics: a missing field degrades **that module** to Experimental treatment (dashed caveat-amber); the whole card goes Experimental only when the signal itself is absent.
3. **Global search:** Cmd-K unified — surfaces AND the player universe in one palette; a prominent header affordance for the same.
4. **Roster Audit:** the density showcase — mono-aligned columns, group/sort persistent in URL, cliff badges in caveat-amber.
5. **Trade Lab:** the negotiation desk — symmetric send/receive, forced-cut ranges as spans, divergence rendered as *distance* (two lane markers with a measured gap) not as a directional signal.
6. **League Pulse:** the opportunity matrix (12 teams × positions). Value magnitude, if color-encoded at all, uses a single-hue neutral lightness ramp with a disclosed scale — categorical position colors and any gradient semantics are an **increment-4 design question, not a vision commitment** (Gemini's HSL position-color proposal held for later adjudication; green/red stays banned regardless).
7. **Model Trust + Accuracy Tracker:** the credibility room — model cards and gate matrices typeset like an audited filing; this is where "shows its homework" becomes an aesthetic.
8. Parked cards, System Diagnostics, Developer zone: restyled within the system, semantics untouched.

## 6. Program increments (each its own cockpit-TDD cycle; David gates each)

- **I1 — Foundation (guard/pipeline-only; ZERO visible change — F4):** semantic token aliases **mapping to today's exact visual values**; the `[data-theme="dark"]` scope lands as an **inert, test-guarded block with NO toggle shipped**; @fontsource packages installed, licensed, subset, and build-verified but **NOT globally activated**; `useEndpointResource`; `useUrlSurfaceState` (`?surface=` only). Acceptance: a pixel-identical app with new plumbing underneath.
- **I2 — The daily open (the visual flip):** the dark theme + type system ACTIVATE here (the first visible redesign, David-previewed before merge); What-Changed redesign + the tape + first SVG sparklines (hard right edge, gap rendering). No Divergence Strip (F2).
- **I3 — The player atom:** the card-contract API slice (range + horizon exposure, David-gated) → global search + player card/inspector redesign + `&player=` URL hydration + the first Divergence Strip.
- **I4 — The surfaces:** Roster Audit → Trade Lab → League Pulse → Trust/Tracker re-skins (order adjustable by David).
- **I5 — Polish:** responsive/mobile pass, motion moment, theme toggle UX, accessibility sweep.

## 7. Falsification seeds (vision-level; each increment adds its own)

1. Invalid `?surface=` slug → Daily What-Changed, no crash (Gemini S1).
2. Chart boundaries: zero-crossing, nulls, single-point series, PIT gaps → no NaN, no clamped axes, no interpolated fiction, gap markers present (Gemini S2 + Codex).
3. Token guards: both theme scopes parsed; no verdict hues/status words; hue families preserved; System Health isolation (Gemini S3 + Codex-4).
4. < 768px: rail collapses, tables adapt, no horizontal page scroll, no illegible truncation (Gemini S4).
5. Reload with `?player=` → inspector restored, selected-player label + detail hydrated (Gemini S5 — **I3-scope seed**, not I1).
6. `useEndpointResource`: stale-abort, parse-failure, unavailable, dependency refetch; no gitignored-artifact deps in tests (Codex-5).
7. Fonts: self-hosted only (no network requests in build output), latin subset, OFL-licensed.
8. `prefers-reduced-motion` honored everywhere; focus visible in both themes.
9. Receipts/tape never occlude a caveat; disclosure lines adjacent to every chart. **Receipts accessibility contract (F5):** the trigger is a focusable element with popover/disclosure semantics (`aria-expanded`, named "Provenance for <metric>"), opens/closes by keyboard (Enter/Esc) and touch tap — hover is an enhancement, never the only path; screen-reader announcement seeded in the I2 RED.
10. Mitigation tripwires + tier-readiness pass unmodified at every increment.

## 8. Mislead-proofing (the aesthetic cordon, binding)

Adopted verbatim as design law: history-only lines (no extrapolation, no fit curves, no forward arrows); no verdict colors — structural amber only for structural facts; symmetric lane weight everywhere both lanes appear; density ramps (if ever) disclosed and neutral-hue; no urgency motion; beauty never outranks a caveat.

## 9. May UI-research corpus reconciliation (13 docs synthesized)

**Validation:** the corpus independently converges on this vision's core — cockpit-not-consumer-app, strict two-lane separation, verdict-free signal axis (the "Wong blue↔amber" system = our shipped model-blue/market-amber), dark-first, monospace numerics, density in the Bloomberg lineage. The current AppShell already implements the corpus's cockpit skeleton (rail + trust strip + inspector drawer + Cmd-K).

**Carried forward (adopted into this vision):**
1. **The Divergence Strip** (Cockpit Style doc — "the single most important component"): one reusable 0–100 primitive — model tick + market tick + uncertainty band + neutral label — the two-lane constitution as a single glanceable element. Elevated into §5: first NEW placement in **I3 (player card)** where paired lanes legitimately exist; Trade Lab's existing strip restyles in I4; never inside What-Changed sections (F2).
2. **Density constants** (Cockpit Style): 32px data rows, 12-col/8px grid, ~"80% of Bloomberg" density target — adopted into §3 layout.
3. **The structural-honesty card contract** (Arch Recommendation): player/decision cards co-render four fields — signal, uncertainty range, counter-argument, horizon — with module-level Experimental degradation (dashed caveat-amber). Honesty enforced by layout, not policy. Adopted into §5.2 **with honest field mapping (F3): signal + counter-argument exist in the DTO today; range + horizon require the I3 card-contract API slice first — the contract is a vision commitment, not buildable-today.**
4. **Stale-data treatment** (corpus consensus): stale inputs render desaturated (`saturate(0.6)`) + dashed border — visual staleness that can't be missed. Skeletons, never spinners. Adopted into §3 motion + §8 cordon.
5. **Uncertainty as a render property** (Direction Spec / Arch Recommendation): ranges/bands never points; quantile-dotplot-primary for distributions — an **I4 adjudication input** alongside the heat-gradient question.

**Contradictions resolved:** lane-color chaos across docs (amber vs purple vs sage-green market; one doc's green = another's model) — settled by the SHIPPED blue/amber axis, which the strongest token doc endorses; light-vs-dark default — dark-first confirmed (corpus majority), light theme retained; player detail modal-vs-drawer — drawer/URL-addressable already shipped and stays; type pairing — corpus suggests Outfit/Inter/JetBrains Mono; this vision keeps **Archivo/Plex** for distinctiveness (Inter is the template default the design discipline warns against) — flagged as a David taste-call at vision ratification, either satisfies the system.

**Stale/rejected:** all four corpus stack recommendations (Next.js/Svelte/HTMX/vanilla) — superseded by the locked Vite+React ADR; Databricks-maximalist assumptions (violates local-first); `VerdictCard` / "Smash Accept" / artificial trade-delay patterns — cordon violations, rejected; **GenUI** — the sober catalog-composition proposal (LLM emits JSON over a closed Zod component catalog) is architecturally portable but both GenUI docs embed verdict components; deferred beyond H2 entirely, requiring an honesty-constraint redesign before any future consideration.

## 10. Review log

- v2 → v3 (2026-07-05): Codex F5-stale accepted — §2's signature description now carries the seed-9 receipt accessibility contract verbatim-aligned (the "hover/press" under-spec was a post-fix-sweep miss at the highest-visibility sentence).
- v1 → v2 (2026-07-05): Codex F1–F5 all accepted — player URL state disambiguated (I1 surface-only; `&player=` + hydration = I3; seed 5 re-scoped) (F1); Divergence Strip re-homed to I3 player card, What-Changed exclusion stated with the contract rationale, §9.1 corrected (F2); card-contract field mapping made honest (range/horizon = I3 API slice; module-level degradation semantics specified) (F3); I1 pinned to guard/pipeline-only with pixel-identical acceptance, the visual flip owned by I2 with David preview (F4); receipts accessibility contract added to seed 9 (F5).
- v1 (2026-07-05): synthesized from Gemini framing (terminal feel, routing, extrapolation prohibition, symmetric lanes, 5 seeds — glassmorphism and Google-Fonts overruled with rationale; positional heat gradients deferred to I4 adjudication) + Codex positions 1–5 (adopted 1:1) + frontend-design discipline (signature: Hard Right Edge + receipts; type: Archivo/Plex; boldness spent in exactly one place) + the 13-doc research corpus (§9: Divergence Strip, density constants, structural-honesty card contract, stale-desaturation adopted; lane-color chaos resolved by the shipped axis; GenUI deferred beyond H2; type taste-call flagged for David).
