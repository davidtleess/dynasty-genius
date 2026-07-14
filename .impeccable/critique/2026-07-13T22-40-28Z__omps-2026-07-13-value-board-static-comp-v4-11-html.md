---
target: frozen Value Board static comp v4.11
total_score: 30
p0_count: 0
p1_count: 4
timestamp: 2026-07-13T22-40-28Z
slug: omps-2026-07-13-value-board-static-comp-v4-11-html
---
Method: dual-agent (A: v411_visual_fresh · B: v411_technical; integrity corroboration: v411_integrity_fuzz; bounded root browser/data fallback)

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of system status | 4 | Healthy/degraded freshness and missing reads are explicit. |
| 2 | Match system / real world | 3 | Manager prose is strong; percentile points and rank-pool distinctions still require learning. |
| 3 | User control and freedom | 2 | Main paths work, but the 200%-text degraded phone becomes a keyboard-inaccessible nested scroll region. |
| 4 | Consistency and standards | 4 | Row, lane, receipt, and scope patterns are coherent. |
| 5 | Error prevention | 3 | Pinned evidence now fails closed, but live movement accepts same-count payload/ID divergence. |
| 6 | Recognition rather than recall | 2 | Initials-only identity and multiple rank populations increase recall. |
| 7 | Flexibility and efficiency | 3 | Keyboard paths work; investigation remains row-by-row. |
| 8 | Aesthetic and minimalist design | 3 | Strong hierarchy; fallback identity retains a table/tool feel. |
| 9 | Error recovery | 3 | Stale/no-read paths explain limits and preserve context. |
| 10 | Help and documentation | 3 | Receipts are unusually complete, but football causality is absent. |
| **Total** |  | **30/40** | **Good foundation; technical NOT-CLEAR and not visual GREEN.** |

## Anti-Patterns Verdict

This is not generic AI slop. The macro-first answer, model/market lane isolation, dense row grammar, and honest degraded state are deliberate. The main aesthetic deficit is category incompleteness: initials discs and plain team text keep a disciplined product from reading as a best-in-category fantasy surface.

The deterministic scanner returned em-dash warnings and a numbered-marker advisory. Builder-history prose inflates the dash count; the marker result is a false positive from dates/version text. No reliable browser overlay was created. Standalone Playwright, Axe, source, and all supplied captures were used.

## Overall Impression

The manager-facing composition is stable and Braelon's duplicate affordance is genuinely fixed. The remaining non-gated problems are evidence integrity and one 200%-text keyboard path: cardinality is being treated as content equality, and the manifest parser silently overwrites duplicate day entries.

## What's Working

- The first viewport answers scale, lane, and roster impact before rows.
- Blue model and amber market objects remain structurally and semantically isolated.
- Braelon has one truthful no-read receipt plus a distinct inspector route; ordinary receipt, radio, tab, modal, reduced-motion, and responsive paths remain stable.

## Priority Issues

1. **P1 — Live endpoint reconciliation proves only cardinality.** `comp-v33-extract.py:401-420` compares date and row count, then trusts history payloads. With 12,201 rows preserved, changing a latest-day delta exited 0 and changed the movement tape while the board still showed the unmodified artifact row; replacing one history ID also exited 0. Compare the latest history ID set and canonical row content to the live artifact before emitting movement.
2. **P1 — The 320px/200%-text degraded phone is not keyboard-scrollable.** `.phone` is an overflow region (`v4.11:110`); the degraded frame (`:538-553`) has no enabled focusable descendant after the comp stub pass (`:638-640`). A fresh Axe 4.12 run reports `scrollable-region-focusable` on `.phone:nth-child(2)`. Make the region focusable with an accessible label or avoid the nested scroll container in the testable artifact.
3. **P1 — Fantasy identity remains below the ratified floor.** Every player uses an initials disc; no headshot fallback chain or team-color recognition mark is composed. Land the David-gated identity pipeline before visual GREEN.
4. **P1 — Why It Moved remains arithmetic, not football context.** The inspector gives price and gap history but explicitly lacks current role/usage/news evidence. Ship the source-retention/why-context capability before calling the investigation complete.
5. **P2 — Manifest parsing is last-write-wins.** `comp-v33-extract.py:483-486` silently overwrites duplicate day keys. `Jul-09:bad,Jul-09:<correct>,Jul-11:<correct>` exits 0 and prints VERIFIED. Reject duplicate keys and validate exactly two `YYYY-MM-DD:64-lower-hex` entries before any evidence output.

## Persona Red Flags

- **David, dynasty manager:** can identify the relevant disagreement and movement quickly, but a same-count history mismatch can make the movement explanation contradict the board's current row.
- **Jordan, first-time manager:** understands the macro answer but lacks player-face/team recognition and must decode multiple rank pools.
- **Sam, keyboard/low-vision user:** ordinary controls work, but the degraded mobile fixture cannot be reached as a scroll region at 200% text.

## Minor Observations

- The FA radio focus outline extends outside an `overflow:hidden` group and is clipped by about 3px at 390px and 320px/200%; the focus remains perceptible, so this is secondary to the Axe failure above.
- At 320px, names are 12px and supporting data 11px. Containment passes, but readability remains a deliberate trade.

## Questions to Consider

Questions skipped: the live-integrity, parser, and keyboard-scroll fixes are contract-determined; David already owns identity and football-context sequencing.
