# Track 2 shape-before-code artifact — Studio Batch A (S1, S12a, S3)

- Status: DRAFT composition artifact for cockpit review (the DESIGN.md shape-before-code gate). No code until this is read.
- Author: Claude Code · 2026-07-14
- Inputs: Gemini Track 2 framing (2026-07-14); PRODUCT.md / DESIGN.md (canonical row, two-lane truth, no-verdict, layered caveats, scaffolding-hide, signature elements).
- Scope: the three design-touching Batch A items. The mechanical Batch A items (S7, S9a, S12b, S12c) and the contract items (S2 done, S12d pending) are NOT here.

---

## S1 — Player evidence card, two-lane facts

**Today:** `ValuationTwoLane.tsx` renders model + market fields as adjacent unlabeled spans → one concatenated string (`ENGINE_BACTIVE_B75.331.3…`, raw ISO stamp + caveat slugs fused). Unreadable.

**5-second answer:** "What does our model say this player is worth, and what does the market say — and how fresh is each?" — two clearly separate lanes, each a small labeled fact set with one focal value.

**Focal hierarchy (per lane):**
1. The lane's focal value — model: DVS (0–100) as the Archivo focal number; market: market value — one hero number per lane, weight/size dominant.
2. Supporting facts as a labeled definition list (label ↔ value), never bare spans: model = engine, grade, xVAR, xVAR percentile, 1y projection; market = platform, overall rank, position rank, volume.
3. Provenance/vintage + caveats ride in the existing ReceiptTrigger/CaveatBlock primitive (the layered-caveats law) — not as a hero line. ISO stamp → friendly relative string ("captured this morning"); caveat slugs → descriptive manager prose.

**Lane order & isolation:** model lane (blue) first/left, market lane (amber) second/right — model is the product's voice; market is the overlay. Blue frames the model object, amber the market object; position/delta hues stay orthogonal (accent-subordination). No red/green, no verdict hue, no signed-delta color highlight.

**States (fail-closed, designed):**
- Model-absent (rookie/pre-model): lane shows "Model valuation pending" — not a zero, not a dash-soup.
- Market-absent (uncovered): "Market coverage incomplete" — the lane is present but honestly empty.
- Both present: full two-lane read.

**Desktop:** two side-by-side lane cards (or two columns of one card), focal number top-left of each, labeled facts beneath, receipts row at the bottom.
**Mobile:** lanes stack vertically (model above market), each keeps its focal number + labeled facts; caveats collapse into the receipt drawer; no horizontal overflow.

**Overclaim guard:** `decision_supported=false` holds; the card exposes model snapshot vintage via the receipt, never implies the model "arrived."

---

## S12a — Shared form-control vocabulary

**Today:** native white `<input>/<select>/<button>` on the dark theme (Trade Lab, Roster Audit) — jarring, unthemed, no shared vocabulary.

**5-second answer:** controls feel native to the film-room charcoal — same shape, same focus grammar, everywhere.

**Design decision (the shared primitive):**
- Surface: `--dg-surface-raised` fill, `--dg-border` 1px, `--dg-text` ink, 4px control radius (per the radius vocabulary).
- States (all required, no half-set): default · hover (border-strong) · focus (the governed 2px `--dg-focus` ring, offset 2 — one focus grammar) · disabled (muted, reduced contrast, `cursor: not-allowed`) · invalid (structural `--dg-caveat`, NOT high-chroma red — no verdict hue).
- Placeholder text hits the 4.5:1 contrast floor (not muted-gray default).
- Button copy: operational verbs (Gemini direction), final wording mine; any label change treated as material.

**Falsification:** long option lists scroll *inside a themed container* (`overflow: auto`), never expand the page grid (this is also the League Pulse S6 lesson, applied preventively); empty/no-match search fails closed to "No matching assets found."

**Scope:** these are the Trade Lab + Roster Audit controls in the Batch A blast radius; the primitive is defined once and reused (compose from `frontend/src/ui/`, don't rebuild locally).

---

## S3 — Remove-asset control on trade chips

**Today:** an added asset chip is inert (click opens the inspector); `removeAsset` exists in `tradeState.ts` but is unwired — the only recovery is clearing localStorage.

**5-second answer:** "I can take this player back out and try a different one" — trade building is iterative.

**Two affordances, distinct:**
- **Remove (surgical):** a small remove control ON each chip (× affordance), keyboard-operable, focus-visible, aria-labelled ("Remove <name> from <side>"). Localized to the one asset.
- **Clear side (reset):** a section-level control on each side. Distinct from remove; resets that side.

**Critical behavior — the invalidation invariant (broadened, Codex 2026-07-14):** ANY mutation of the proposal after a run — remove, clear-side, AND add — immediately invalidates the rendered comparison and returns the panel to its pre-run state, rather than showing metrics for a proposal that no longer matches. This is not remove-specific: `TradeLab.tsx` `select()` currently changes the proposal after a run without clearing either lane (a pre-existing stale-result defect that add-after-run exposes), so the S3 fix must close the whole invariant, not just removal. (Ties to S2: reaching empty on both sides disables the compare control and stops reconciliation; one-sided/remaining assets stay comparable.)

**Falsification:** empty boundary disables compare (S2 contract); long player names truncate/ellipsis, never wrap illegibly or push the remove control off-row.

**Overclaim guard:** sandbox-only — remove/clear affects the what-if draft, never implies committing a transaction to the roster.

---

## Open questions for the cockpit read

1. S1: is DVS the right per-lane focal for the model lane, or xVAR? (DVS is the 0–100 David-facing scale; xVAR is engine-native. Leaning DVS as focal, xVAR as a supporting fact.)
2. S3: remove control as an always-visible × vs. hover/focus-revealed — always-visible is more discoverable and mobile-safe; leaning always-visible.
3. S12a: do we define the control primitive as new `frontend/src/ui/` components this slice, or theme in place and extract later? (Leaning: theme via shared CSS this slice, extract to a primitive as a named follow-up, to keep the Batch A slice bounded.)
