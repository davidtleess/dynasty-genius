---
target: frozen Value Board static comp v4.12
total_score: 31
p0_count: 0
p1_count: 3
timestamp: 2026-07-13T23-25-10Z
slug: omps-2026-07-13-value-board-static-comp-v4-12-html
---
Method: dual-agent (A: v412_visual_fresh · B: v412_technical; QA corroboration: v412_integrity_fuzz; bounded root browser/data fallback)

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of system status | 4 | Healthy, degraded, and missing-read states are explicit. |
| 2 | Match system / real world | 3 | Manager prose is strong; percentile points and rank-pool distinctions still require learning. |
| 3 | User control and freedom | 3 | Keyboard scrolling, tabs, radios, sheets, and exits work in the tested states. |
| 4 | Consistency and standards | 4 | Row, lane, receipt, and scope patterns remain coherent. |
| 5 | Error prevention | 3 | Content and identity reconciliation now fails closed, but the declared exact manifest grammar is still permissive. |
| 6 | Recognition rather than recall | 2 | Initials-only identity and multiple rank populations increase recall. |
| 7 | Flexibility and efficiency | 3 | Keyboard paths work; investigation remains row-by-row. |
| 8 | Aesthetic and minimalist design | 3 | Strong hierarchy; fallback identity retains a table/tool feel. |
| 9 | Error recovery | 3 | Stale/no-read paths explain limits and preserve context. |
| 10 | Help and documentation | 3 | Receipts are unusually complete, but football causality is absent. |
| **Total** |  | **31/40** | **Good; end-user CLEAR-at-ceiling, technical NOT-CLEAR on one bounded parser contract.** |

## Anti-Patterns Verdict

This is not generic AI slop. The macro-first answer, model/market lane isolation, dense row grammar, and honest degraded state are deliberate. The remaining aesthetic deficit is category incompleteness: initials discs and plain team text keep a disciplined product from reading as a best-in-category fantasy surface.

The deterministic scanner returned two em-dash warnings (38 in the comp, 8 in the inspector) and one numbered-marker advisory. Builder-history prose inflates the dash count; the marker result is a false positive from dates/frame numbers. No reliable browser overlay was created because the in-app mutable browser surface was unavailable; standalone Playwright, Axe, source, and all supplied captures were used.

## Overall Impression

The manager-facing pixels are stable and the material provenance and zoom-accessibility failures are closed. The only new technical hold is narrow but real: the parser claims a literal manifest grammar that it does not enforce. That should be corrected in the extractor/build RED without reopening the visual composition.

## What's Working

- The first viewport answers roster scale, lane, and movement before individual rows.
- Blue model and amber market objects remain structurally and semantically isolated.
- Same-cardinality payload changes and one-for-one identity replacement now abort before the movement summary; the 320px/200%-text phones are focusable, labeled, keyboard-scrollable, and Axe-zero.

## Priority Issues

1. **P1 - Manifest grammar is canonicalized, not exact.** `comp-v33-extract.py:505-514` drops blank comma fields, strips surrounding whitespace, and validates a date only by length. Leading/doubled/trailing commas and whitespace pass; in an isolated selected-day fixture, `2026-07-1/` also passes with correct hashes. This contradicts the declared `YYYY-MM-DD:<64 lowercase hex>` contract and permits malformed capture dates. Parse exactly two nonempty raw tokens and validate/round-trip each date with `datetime.date.fromisoformat` before accepting hashes.
2. **P1 - Fantasy identity remains below the ratified floor.** Every player still uses an initials disc; no headshot fallback chain or team-color recognition mark is composed. Land the David-gated identity pipeline before visual GREEN.
3. **P1 - Why It Moved remains arithmetic, not football context.** The inspector gives price and gap history but explicitly lacks current role/usage/news evidence and usable continuation. Ship the source-retention/why-context capability before calling the investigation complete.
4. **P2 - The new phone-region focus state uses browser defaults.** `value-board-v4.12:638-642` makes the frames focusable, but the authored focus selector at `:82` excludes `.phone`; tested focus renders as a browser-dependent 1px auto outline instead of the governed 2px `--dg-focus`/2px-offset grammar. This does not break Axe or keyboard scrolling, but it is a portability and design-system residue.

## Persona Red Flags

- **David, dynasty manager:** can identify the relevant disagreement and movement quickly, but still lacks the football reason behind it and recognizable player imagery.
- **Jordan, first-time manager:** understands the macro answer but must decode multiple rank pools and rely on initials rather than category-familiar identity.
- **Sam, keyboard/low-vision user:** can now focus and scroll every nested phone at 200% text, but the newly focusable frame relies on a browser-default focus indicator rather than the product focus token.

## Minor Observations

- Eleven of thirteen captures are byte-identical to v4.11; frames 08 and 09 differ only in minute outer-border antialiasing, with no visible content or geometry drift.
- At 320px, names remain 12px and supporting data 11px. Containment passes, but readability remains a deliberate trade.

## Questions to Consider

Questions skipped: the parser and focus-state fixes are contract-determined; David already owns identity and football-context sequencing.
