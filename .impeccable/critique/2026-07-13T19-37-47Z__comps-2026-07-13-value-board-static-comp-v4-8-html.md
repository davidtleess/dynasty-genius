---
target: Value Board static comp v4.8 frozen round-10
total_score: 26
p0_count: 0
p1_count: 4
timestamp: 2026-07-13T19-37-47Z
slug: comps-2026-07-13-value-board-static-comp-v4-8-html
---
Method: dual-agent (A: v47_visual_fresh capture-first · B: v47_technical_a11y runtime)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 4 | Healthy and degraded freshness remain explicit and manager-readable. |
| 2 | Match System / Real World | 2 | Dynamic receipts turn ages into ranks and negative gaps back into sign-decoding copy. |
| 3 | User Control and Freedom | 3 | Tabs, radios, dialogs, Esc, and focus return work; no-read routes are inconsistent. |
| 4 | Consistency and Standards | 2 | One DOM-scraping handler cannot preserve truth across table, mover, mobile, and missing-lane rows. |
| 5 | Error Prevention | 2 | The receipt accepts ambiguous visible text as typed rank data; live extraction can mix date endpoints. |
| 6 | Recognition Rather Than Recall | 2 | Initials-only identity remains below the fantasy-category bar. |
| 7 | Flexibility and Efficiency | 3 | The 200%-text sheet is repaired, but mover receipts and disabled continuation routes dead-end. |
| 8 | Aesthetic and Minimalist Design | 3 | Strong density and lane discipline; identity still reads prototype-grade. |
| 9 | Error Recovery | 3 | The degraded fixture remains honest and the close/focus lifecycles pass. |
| 10 | Help and Documentation | 2 | Receipt denominators and both no-read explanations are incomplete or wrong. |
| **Total** | | **26/40** | **Acceptable visual system; trust boundary remains unsafe.** |

## Anti-Patterns Verdict

The surface does not read as a generic AI dashboard. Its compact roster grammar, two-lane percentile bars, and degraded-state honesty are product-specific. It still reads as a polished prototype because initials discs carry identity everywhere and the inspector's football-reason slot is explicitly future tense.

The deterministic scan reported 30 em-dashes in the comp, 8 in the inspector, and one numbered-marker advisory. The marker hit is a date/fixture false positive; most dash count comes from builder notes. Neither outranks the verified receipt and identity defects. Direct capture inspection and local Playwright runtime evidence were used; no user-visible detector overlay was injected.

## Overall Impression

The five-second answer, density, color discipline, and degraded-state honesty remain strong. The immediate blocker is the receipt implementation: it scrapes divergent presentation grammars and therefore invents or drops evidence. The remaining product ceiling is the already named identity and football-context pipeline.

## What's Working

- The healthy first viewport answers what changed, separates `22/23` price movement from `14/23` gap movement, and names the comparison window.
- The degraded fixture removes stale market values and explains the local ordering failure without blaming the source.
- Axe is zero on both artifacts. The integrated sheet now remains contained and internally scrollable at 320x700 with 200% text; Close, focus trap, Esc, and focus return all pass.

## Priority Issues

### [P1] The live receipt still lacks a typed row contract

**Why it matters:** Roster receipts render ages as DG ranks (`DG 22`, `DG 27`, `DG 24`). Bam Knight's no-FantasyCalc control is marked disabled and removed from keyboard order while still pointer-active; its receipt then says there is no DG mark despite visible DG RB47 and prints an empty market rank. Braelon Allen's opposite missing-lane state has no receipt route. Movers still report no model mark, no market mark, and no ranks. Dynamic market receipts omit position and pool size, and desktop within-band receipts cannot disclose the stored gap.

**Fix:** Give every composed row one structured receipt payload containing player id, direction state, display and stored deltas, both endpoint percentiles, both population definitions/counts, scoped rank labels, underlying values, missing-lane reason, source, and rounding. Populate the card atomically from that payload and fail closed on absent required fields; do not parse `.tm`, style positions, or prose.

**Suggested command:** `$impeccable harden`

### [P1] Evidence pinning still overclaims and can mix dates

**Why it matters:** A ref-pin freezes the current-day artifact and root metadata, but movement still reads mutable SQLite. Altering a prior-day payload changes a nominally full-fidelity run without an integrity failure. In unpinned live mode, the movement endpoint is not checked against the artifact date, so a stale Jul-11 artifact can be combined with Jul-11-to-Jul-13 movement and exit successfully.

**Fix:** Scope the copy to artifact/root fidelity until both movement payloads are immutable, or publish/hash a per-day history export in the evidence manifest. In every mode require `movement_end_date == artifact.market_snapshot_date` before emitting movement facts.

**Suggested command:** `$impeccable harden`

### [P1] Fantasy-native identity remains below floor

**Why it matters:** Initials discs and plain team text slow recognition throughout desktop, mobile, and the inspector. Capture-first scoring keeps fantasy identity and category parity at 6/10.

**Fix:** Land the governed headshot -> initials -> silhouette fallback chain and a factual team-color micro-mark, then recapture every viewport. This remains David-gated.

**Suggested command:** `$impeccable polish`

### [P1] The screen still stops before the football reason and usable next step

**Why it matters:** The manager can see that Legette's market price fell and the gap grew, but the inspector says snaps/routes/targets will arrive later and both continuation actions are disabled. It answers what moved, not the football reason or the next investigation.

**Fix:** Complete the sanctioned context-retention adapter and wire at least the neutral Trade Lab or roster-context route before claiming the end-to-end workflow. This remains David-gated.

**Suggested command:** `$impeccable clarify`

### [P2] Receipt direction copy regresses to arithmetic

**Why it matters:** `-14pp (+ = our model higher)` forces a manager to invert a sign. The static exemplar already proves the clearer form: `market higher by 14 percentile points`.

**Fix:** Generate the direct lane sentence from signal state; keep the signed producer value as supporting evidence, not the prose headline.

**Suggested command:** `$impeccable clarify`

### [P2] 320px remains at the legibility floor

**Why it matters:** Names fall to 12px, metadata/metrics to 11px, position tokens disappear, and sparse sample frames leave a large empty body above the sticky rail. It contains correctly but does not yet feel category-leading.

**Fix:** Preserve the strongest identity token and a readable small-text floor; let short boards size to content in the production composition.

**Suggested command:** `$impeccable adapt`

## Persona Red Flags

**David (Dynasty Manager):** The morning answer is useful, but a Jaxson Dart receipt calls his age `DG 22`, while Bam Knight's receipt contradicts his visible DG rank. That breaks the evidence layer a dynasty manager would use to decide what to inspect next.

**Jordan (First-Time Manager):** Signed receipt copy still requires learning that plus means DG; initials-only rows make player recognition slower; the Why It Moved slot provides no current football context.

**Sam (Accessibility-Dependent User):** Ordinary metric controls, focus movement, dialog containment, Esc, reduced motion, and Axe pass. The newly enabled-looking Bam info control is removed from keyboard order via `aria-disabled`, so pointer and keyboard users receive different functionality.

## Minor Observations

- Ordinals, per-position model populations, generic versus Legette rounding, and the 200%-text sheet fix are real closures.
- Current Jul-9 and Jul-11 SQLite payloads match their tracked artifacts, so the frozen numbers reproduce today; the defect is the absence of an immutable guarantee.
- The detector's numbered-section advisory is not a product issue for this fixture document.

## Questions to Consider

- Why is the receipt reconstructing domain evidence from CSS and visible labels rather than consuming the same typed payload as the row?
- What single immutable manifest should bind the current artifact, prior movement day, and both root timestamps?
- Once David authorizes identity and context work, can the first production build ship both rather than treating either as post-parity polish?
