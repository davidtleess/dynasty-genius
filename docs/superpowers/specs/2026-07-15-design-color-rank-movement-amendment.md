# DESIGN.md amendment — scoped rank-movement color exception (David-ruled)

**Status: DRAFT v8 — §3 selection RESOLVED (David, 2026-07-15 via Tower: CHIP-AS-UNIT); the
§8 post-selection addendum is drafted below and under cockpit review; implementation remains
gated on unanimous CLEAR + David's text ratification.
David ruled the substance 2026-07-15 (via Tower,
option (a) on Studio 001b N3): green/red legal for rank-movement arrows ONLY, never
value/margin/tier hues.** This spec codifies the ruling as a scoped exception to the design
foundation's color law; the text lands on main's `DESIGN.md` via PR after unanimous cockpit
CLEAR. Commit/push/merge = David's word.

## 1. Problem (measured)

`DESIGN.md` Color law: "Structural warnings only: `--dg-caveat` / `--dg-cliff`. **No green/red
anywhere. No verdict hues.**" Studio 001b N2/N3 ship rank-movement chips (`▲2` green / `▼3`
red) — the fantasy-standard idiom David explicitly chose with knowledge of the palette
discipline. Without an amendment, the ruling and the law contradict; a silent exception would
be exactly the solo-drift the foundation exists to prevent.

## 2. The amendment (proposed edit surface)

**Edit 1 — the Color law line.** Append the scoped exception:

> Structural warnings only: `--dg-caveat` / `--dg-cliff`. No green/red anywhere. No verdict
> hues. **Single David-ruled exception (2026-07-15): rank-movement delta arrows (`▲n`/`▼n`
> beside a rank) may use the dedicated `--dg-rank-up` / `--dg-rank-down` tokens — green/red is
> legal there and ONLY there. The exception never extends to value, margin, gap, tier, DVS,
> xVAR, percentile, heat, row fills, or any magnitude/quality encoding; a green/red anywhere
> but a rank-movement arrow remains a defect.**

**Edit 2 — token spec.** Add `--dg-rank-up` / `--dg-rank-down` to the OKLCH token family with
**both theme values defined (light AND dark), AA contrast ≥ 4.5:1 in each**, per the T2
contrast precedent; raw literals stay test-banned — tokens only. **Application scope
(RESOLVED per §3 — chip-as-unit):** the tokens color the movement glyph and its adjacent
signed numeral as one unit — never chip backgrounds, row fills, borders, or any container.
The exact DOM span and guard-test changes are finalized in the §8 addendum, cockpit-reviewed
before any implementation begins. **Basis-bound:** a component may consume
these tokens only when rendering a rank-movement basis field (`rank_delta`-class data); binding
them to any other delta is a defect regardless of visual similarity.

**Edit 3 — integrity-guardrails sweep (post-fix sweep rule).** The guardrail "rich color must
not weaken lane isolation or reintroduce verdict green/red" gains "(rank-movement arrows
excepted per the Color law)". Full-document grep for `green/red`, `green`, `red`, `verdict
hue` and update every reference — no stale absolute ban may survive the amendment.

## 3. Boundary (the hard line, in one test)

Green/red is legal iff the colored element is a **rank-movement indicator adjacent to a
rank**. The moment the hue touches worth, disagreement magnitude, quality, or any
model/market value — including coloring the rank number itself, a margin cell, a sparkline, a
tier chip, or a row — it is outside the ruling and remains banned. Direction never rides on
color alone (WCAG 1.4.1): the arrow glyph + signed number carry the meaning; color is
redundant emphasis.

**⚑ RESOLVED — DAVID RULED (2026-07-15, via Tower): CHIP-AS-UNIT.** The `▲2` pair — glyph +
signed movement numeral — is colored as one unit, matching the prototype he approved. (The
question had been live between two readings: Codex's literal glyph-only, Claude's
chip-as-unit from Studio 001b N3's own `▲2 (green)` specification; David's word settles it.)
Both lanes' shared floor is unchanged and binding: the RANK number itself and everything
beyond the chip stay neutral. The §8 addendum below finalizes the DOM span and guard tests
per the Edit-2 mandatory-addendum rule.

## 4. Out of scope

- Any change to lane hues (model-blue / market-amber), position hues, or the DVS neutral ramp.
- Any relaxation of the heat-ramp ban on the margin column (Value Board plan of record).
- Market-lane brightness-split encodings already shipped/specified (001 T2) — they remain
  valid alternatives, not superseded.

## 5. Falsification seeds (the review matrix)

1. A green/red rank-delta chip on the margin ("opportunities/disagreement") column — must FAIL
   (movement-of-rank only; disagreement is not movement).
2. Green/red on the rank number itself (not the arrow) — must FAIL (the exception names arrows).
3. A green ▲ on a VALUE change (`+120`) — must FAIL (value movement ≠ rank movement).
4. Tier chip colored by direction of tier change — must FAIL.
5. `▲2` rendered in green with no glyph fallback for color-blind users — must FAIL (1.4.1).
6. Raw `#22c55e`-style literal in a governed file — must FAIL (token discipline unchanged).
7. Reduced-motion/reduced-color? No motion change; color exception carries no animation.

## 6. Enforcement

The existing raw-color-literal test ban stays. The banned-hue scan (if any test enumerates
green/red hues in governed CSS) gains an allowlist for exactly the two new tokens. Visual
audits treat any out-of-boundary green/red as P0.

## 7. Digest coordination (self-referential rule)

`DESIGN.md` is a pinned corpus file in the governance digest. The amendment commit changes
`DESIGN.md`'s hash, so **the digest's pin table regenerates in the same change set** (mirror of
the 02-amendment rule; once the digest pin RED exists it enforces this mechanically). This
amendment also changes a **summarized** item — the digest's PRODUCT/DESIGN paragraph states
"no green/red anywhere, no verdict hues" — so the digest's Design summary text is updated to
carry the scoped exception in the same change set, per the 02-amendment lifecycle rule
(content re-review on any summarized-item delta, not pins alone).

## 8. Post-selection addendum (chip-as-unit — the mandatory Edit-2 finalization)

**DOM span (per authorized indicator, not per row).** The tokens may color one inline element
**per authorized rank-movement indicator** — a row may validly render several (e.g. overall
rank movement and position rank movement each carry a chip). Each colored node is a
`RankMoveChip` whose ENTIRE text content is the glyph + movement numeral pair (`▲2` / `▼3`)
and nothing else. The tokens apply to that node's text color only. A chip node must not
contain, wrap, or share a text node with the rank number, any value, name, or other content;
nesting a chip inside a colored container is a defect (the container takes no movement hue).
"Authorized indicator" = an element bound to a rank-movement basis field per guard 3.

**Component + selector allowlist (exact):** component `frontend/src/ui/RankMoveChip.tsx`
(**planned new file** — does not exist yet; created by the consuming surface build);
selectors `.dg-rank-move`, `.dg-rank-move--up`, `.dg-rank-move--down`. These are the ONLY
consumers of `--dg-rank-up` / `--dg-rank-down`.

**Content pattern (executable):** the chip node's `textContent` matches
`/^[▲▼][1-9][0-9]*$/` — one direction glyph, one positive integer, nothing else. Zero-delta
renders no chip (no `▲0`/`▼0`; the pattern's `[1-9]` head enforces it).

**Guard-test changes (named files; capabilities verified against the repo):**
1. Hue allowlist — `frontend/src/styles/tokens.test.js` AND `frontend/src/styles/
   tokensI1.test.js` (both parse OKLCH hue via `parseOklchHue`, the capability this guard
   needs): green/red hue-family values are legal only on `--dg-rank-up` / `--dg-rank-down`;
   any other token or rule in the banned hue ranges fails. `rawCssAudit.test.js` stays
   untouched — it audits raw literals, not hue families, and the raw-literal ban is unchanged.
2. `frontend/src/ui/uiCssContract.test.js` (real path — the DG primitive CSS contract):
   source scan asserting the two tokens are referenced only by the allowlisted
   `.dg-rank-move*` selectors; any other selector, component, or inline style fails.
3. `frontend/src/ui/RankMoveChip.test.tsx` (**planned new file**, beside the planned
   component): the chip renders only from a rank-movement basis prop (`rank_delta`-class
   field, typed); constructing it from value/margin/tier deltas is unrepresentable in the
   prop contract and the test asserts the type boundary plus a runtime rejection for
   basis-mislabeled data.
4. `frontend/src/ui/RankMoveChip.test.tsx` (planned): `textContent` matches the content
   pattern above for every rendered state; rank numbers, names, and values inside fail.
5. `frontend/src/styles/tokenContrast.test.js` (**planned new file** — no existing test
   asserts contrast): parses BOTH theme scopes for each of the two tokens and asserts
   AA ≥ 4.5:1 against the corresponding theme surface color.
6. `frontend/src/ui/RankMoveChip.test.tsx` (planned): WCAG 1.4.1 — the glyph is present in
   every rendered chip (meaning carried by glyph + numeral; color redundant), including
   under forced-colors rendering.

**Timing note:** guards 1, 2, and 5 land with the amendment PR (they bind the token layer,
which the amendment creates). Guards 3, 4, and 6 land with the first consuming-surface build
that creates `RankMoveChip` — named here so that build inherits them as REDs, not choices.

## 9. Sequence

Cockpit adversarial review (this spec incl. the §8 addendum) → unanimous CLEAR → David
ratifies text → branch off main, apply Edits 1–3 + sweep + digest pin AND Design-summary
regeneration (§7) → PR (guard tests 1, 2, 5 in the same PR per the §8 timing note; 3, 4, 6
are named REDs inherited by the first RankMoveChip build) → CI + Codex post-commit divergence
audit → close the loop.
