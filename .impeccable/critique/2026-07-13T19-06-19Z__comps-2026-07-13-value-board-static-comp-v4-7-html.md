---
target: Value Board static comp v4.7 frozen round-9
total_score: 26
p0_count: 0
p1_count: 4
timestamp: 2026-07-13T19-06-19Z
slug: comps-2026-07-13-value-board-static-comp-v4-7-html
---
Method: dual-agent (A: root technical/runtime · B: v47_visual_fresh capture-first)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 4 | Healthy/degraded freshness is unusually explicit. |
| 2 | Match System / Real World | 3 | Primary copy is manager-readable; dynamic receipts regress to sign decoding and bad ordinals. |
| 3 | User Control and Freedom | 3 | Tabs, radios, sheet, native dialog, Esc, and focus return work; many comp-only targets remain honestly disabled. |
| 4 | Consistency and Standards | 2 | The shared receipt loses row-specific facts across mover, roster, and mobile grammars. |
| 5 | Error Prevention | 2 | Stale Legette rounding survives every non-Legette receipt; extractor pin has fail-open paths. |
| 6 | Recognition Rather Than Recall | 2 | Initials-only identity remains below the category bar. |
| 7 | Flexibility and Efficiency | 2 | Dense rows scan well, but the integrated sheet loses its close/header region at 200% text. |
| 8 | Aesthetic and Minimalist Design | 3 | Strong lane discipline and hierarchy; identity still reads prototype-grade. |
| 9 | Error Recovery | 3 | Degraded state explains the ordering issue and refuses to invent movement. |
| 10 | Help and Documentation | 2 | Receipt population/denominator/rounding evidence is incomplete or wrong outside Legette. |
| **Total** | | **26/40** | **Acceptable; major trust and reflow defects remain.** |

## Anti-Patterns Verdict

The surface does not read as generic AI dashboard output. Its dense ranked-row grammar, true-coordinate two-lane bars, and honest degraded state are specific to the product. It does still read as a polished prototype rather than a fantasy-native destination because initials discs carry identity everywhere.

The deterministic scan reported em-dash warnings in both HTML files and a numbered-marker advisory in the comp. The marker hit is a date/fixture false positive; the em-dash count is dominated by builder notes and does not outrank the verified product findings. No browser overlay was injected; direct captures and runtime Playwright checks are the evidence.

## Overall Impression

The macro-first answer, color discipline, density, and degraded honesty are strong. The largest immediate opportunity is not another visual tweak: make every receipt factually belong to the row that opened it. The remaining visual opportunity is the already David-gated player-identity pipeline.

## What's Working

- The healthy first viewport answers the morning question immediately and decomposes `14/23`, `5 by 2pp+`, `22/23`, and Ali without turning one player into a recommendation.
- The degraded fixture removes stale market values, leaves only the current model lane, and explains why movement is paused.
- Model blue and market amber stay isolated across desktop, mobile, rows, bars, and the inspector; Axe is zero on both artifacts and the tested focus lifecycles pass.

## Priority Issues

### [P1] The live per-row receipt is not row-truthful

**Why it matters:** A receipt is the trust boundary. Jeanty, Rome, Kraft, Theo, Jaxson, Mac Jones, Keenan Allen, and mobile Jeanty all opened the card, but every non-Legette row retained Legette's `+27.6pp -> +28pp` rounding example. Mac Jones became `this player`; roster and mobile rows lost visible DG ranks; most rows lost population denominators. This can make a user trust the wrong evidence.

**Fix:** Populate a typed receipt payload per row rather than scraping presentation DOM. Update all fields atomically, including direction wording, stored delta, endpoint values, cohort populations, rank labels, underlying values, and rounding. Fail closed when required evidence is absent.

**Suggested command:** `$impeccable harden`

### [P1] Historical pinning still has fail-open provenance paths

**Why it matters:** `DG_AS_OF_REF` without `DG_AS_OF` silently ignores the ref and emits live Jul-13 data. Full-fidelity row/root data comes from Git, while movement comes from the mutable local SQLite store and does not assert `d_last == AS_OF`. The output is correct today but does not guarantee reproducibility.

**Fix:** Reject asymmetric pin arguments; require the requested date to exist as the movement pair endpoint; bind or hash both history endpoint payload sets to the declared evidence pin.

**Suggested command:** `$impeccable harden`

### [P1] Fantasy-native identity remains below the ratified floor

**Why it matters:** Initials discs and plain team text slow recognition on every capture and keep fantasy identity and category parity at 6/10. This is the difference between a credible data comp and a product David wants to scan daily.

**Fix:** Land the governed headshot -> initials -> silhouette chain and team-color micro-mark, then recapture all desktop/mobile/mid-scroll states. This remains David-gated.

**Suggested command:** `$impeccable polish`

### [P1] The integrated mobile sheet fails 200% text reflow

**Why it matters:** At 320x700 with root text at 200%, the absolute bottom sheet grows taller than its fixed, overflow-hidden phone. Its top moves above the phone and the handle, identity, and close control become unreachable. Keyboard containment does not compensate for visually clipped controls.

**Fix:** Make the sheet itself height-bounded and vertically scrollable inside a viewport-height phone, or use a native dialog/popover/portal layout whose close region remains sticky and reachable at 200% text.

**Suggested command:** `$impeccable adapt`

### [P2] Dynamic receipt copy is mechanically wrong

**Why it matters:** The DOM formatter emits `81th`, `83th`, and `21th`, and negative gaps become `-14pp (+ = our model higher)` instead of the direct `market higher by 14 percentile points`. The explanation layer adds decoding effort precisely where the user asked for clarity.

**Fix:** Use a tested ordinal formatter and manager-language direction copy generated from structured signal state.

**Suggested command:** `$impeccable clarify`

### [P2] 320px succeeds by shrinking below comfortable scan size

**Why it matters:** Names drop to 12px, metadata/metrics to 11px, and position text disappears. No content clips, but quick fantasy scanning becomes effortful and the sparse three-row board leaves a large empty body above the rail.

**Fix:** Preserve at least the governed small-text floor, prioritize the most useful identity token, and let compact boards size to content rather than manufacturing empty depth.

**Suggested command:** `$impeccable adapt`

## Persona Red Flags

**Alex (Power User):** The daily macro and dense rows are efficient, but opening a receipt for Jaxson or Mac Jones drops facts already visible on the row. Alex cannot audit quickly because the evidence surface changes shape by row grammar.

**Sam (Accessibility-Dependent User):** Keyboard, focus containment, Esc, native dialog, reduced motion, and Axe checks pass. At 200% text the integrated sheet clips its own header and close region, and focused receipts can still announce stale rounding or incomplete labels.

**David (Dynasty Manager):** The first viewport is useful, but initials-only identity slows player recognition and the Why It Moved slot still says context will arrive later. Headshots/team marks and retained role/injury/usage context remain the known capability ceiling.

## Minor Observations

- The full Git-backed Jul-11 pin currently reproduces all declared counts, freshness facts, ranks, ties, movement, and FA scopes.
- The standalone inspector's price-history disclosure, close/Esc/reopen lifecycle, and disabled tray treatment work.
- The detector's numbered-section advisory is not a product defect in this artifact.

## Questions to Consider

- Can the receipt consume the same typed producer/display payload as the row instead of reverse-engineering rendered text?
- Should a pin be considered valid unless root artifact and both movement endpoints share one immutable manifest?
- Once identity assets are authorized, which factual team micro-mark best improves recognition without competing with the model/market lanes?
