# H2 I2a — The Visual Flip + Daily Open (increment spec)

**Date:** 2026-07-05 · **Author:** Claude (implementation lead) · **Status:** DRAFT v1 — under the ratified vision (v3 §3/§5.1/§6-I2); three-way-converged split (Codex boundary + Gemini concurrence). David opened I2; **the preview gate is his** — nothing merges before he has seen it.
**Scope:** I2a only. I2b (the capped batch `GET /api/pit/player-series` slice + the Hard-Right-Edge sparkline primitive) is a separate cycle owning backend + SVG together per Codex's RED implication.

## 1. What activates (the first visible redesign)

1. **Theme:** `index.html` sets `<html data-theme="dark">` statically — default-dark, **NO toggle** (deferred to I5 per the vision; Codex + Gemini concur). No FOUC, no CLS, no URL/localStorage state.
2. **Type:** @fontsource latin subsets imported at the app entry; token updates — `--dg-font-sans` → "IBM Plex Sans" stack, `--dg-font-mono` → "IBM Plex Mono" stack (with `font-variant-numeric: tabular-nums` where values render), NEW `--dg-font-display` → "Archivo" stack for surface titles/the daily-open headline.
3. **Light theme retained:** `:root` keeps the light values; dark wins via the attribute. Hue meaning unchanged (the I1 guard discipline carries).

## 2. The daily open (What-Changed composition; Gemini framing)

- **The tape** (top strip): substrate facts ONLY, never movement/trend claims (Codex) — capture streak + last capture (from `GET /api/system/capture-health`) · model vintage/status (from `GET /api/system/model-provenance`) — both consumed through `useEndpointResource`; degraded states render the standard honest treatments.
- **Mover rows:** 32px density rows, mono tabular values, signed neutral deltas (shipped convention), Archivo section headlines.
- **Reserved chart slots — HONEST EMPTY (the Codex boundary):** the layout reserves the sparkline cell with a quiet "series pending" treatment; **no sparkline path may render without real series data** — a RED row asserts no `<path>`/fake trend exists in I2a. The Hard Right Edge arrives only with I2b's real data.
- **Motion:** the single orchestrated daily-open stagger (~150ms, regions settle top-down); `prefers-reduced-motion` collapses to none. No delta pulses.
- All H1 copy/disclosure/caveat contracts carry unchanged; mitigation tripwires byte-untouched.

## 3. I1 guard amendments (Codex-owned, explicit — the verify-lock-release rule)

Two I1-scoped guards were written as "in I1" contracts and now amend deliberately, not silently:
- `tokensI1.test.js` "ships no theme toggle or dark-scope activation in I1" → permits exactly ONE sanctioned activation point (`index.html` root attribute), still bans toggles/other activation sites.
- `fontPipeline.test.js` "not globally activated" → flips to assert the sanctioned activation (entry imports present, latin subsets only, tokens reference the families) while keeping OFL/subset/no-network rows.
Both amendments live in the I2a RED with the ratified-vision basis recorded.

## 4. Falsification seeds

1. `data-theme="dark"` present at boot; NO toggle control exists; no other file sets the attribute.
2. Both token scopes still hue-guarded; System Health isolation intact; banned-language/AST linter green.
3. Fonts: subsets load from the bundle (no network); tabular numerals applied to value cells; fallback stacks render before font load without layout collapse.
4. Tape: real endpoint shapes via `useEndpointResource`; capture-health degraded/absent → honest degraded tape, never fabricated streak; provenance 503 → tape slot degrades, page survives.
5. **No sparkline path renders anywhere in I2a** (no `<path>` in the reserved slots; quiet state copy present).
6. Stagger respects `prefers-reduced-motion`; no motion on delta values.
7. Full FE gate + closeout; visual-diff sanity: the ONLY intended visual deltas are theme/type/tape/composition (no copy or semantics drift).
8. **The David preview gate:** GREEN + dual-CLEAR → local preview served to David → his word → commit/push/PR/merge chain.

## 5. Review log
- v1 (2026-07-05): drafted from the converged split (Codex boundary: no fake sparklines, toggle deferred; Gemini: tape substrate-facts framing, honest empty slots).
