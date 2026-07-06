# Product

> Distilled from the David-ratified design corpus: `docs/superpowers/specs/2026-07-05-h2-ui-vision-design.md` (v3, ratified), `docs/superpowers/specs/2026-07-05-h2-frontend-reset-design.md` (v1.6, ratified), `docs/strategies/2026-07-05-dynastynerds-visual-benchmark.md`, `docs/superpowers/specs/2026-07-05-h2-dg-voice-guide-design.md`, and `docs/governance/00-product-constitution.md`. Those documents govern on any conflict; this file is a working summary for design tooling. Untracked working file — not committed without David's word.

## Register

product

## Users

One user: David — a dynasty fantasy football manager (Superflex PPR, 12-team league) with 15 years of enterprise-software judgment. Daily-login context: the morning check of what changed overnight in his league's market prices and his model's outputs. He is in a decision workflow (trade, cut, waiver, draft) and the product's job is to surface verified facts, ranges, and provenance — never to decide for him.

## Product Purpose

Dynasty Genius is a private, single-league asset-management terminal: a daily point-in-time record of one league's reality wired to a model that refuses to lie about what it knows. Success = David makes dynasty decisions that look correct 3–7 years out, trusting the surface because every number carries a receipt.

## Brand Personality

Private trading terminal. Dense, calm, fast, credible. The jaw-drop is credibility, not chrome. Three words: serious, honest, instrumental. The screen speaks dynasty-manager prose; technical precision lives one layer down in receipts and title attributes.

## Anti-references

- Generic dashboard gloss: glassmorphism, backdrop blurs, gradient chrome (explicitly rejected in the ratified vision).
- Dark-terminal-with-acid-accent template aesthetics.
- Consumer fantasy-app cheerleading: green/red verdict colors, urgency motion, pulsing deltas, "BUY NOW" energy.
- SaaS hero-metric cards and identical card grids.
- Backend-report UI: raw schema nouns, snake_case tokens, ISO timestamps in visible copy.

## Design Principles

1. **Honesty is the aesthetic.** The Hard Right Edge (history terminates at the last verified capture; empty grid beyond), receipts on every number, disclosed bases for every rank/band. Beauty never outranks a caveat.
2. **No verdicts, ever.** Descriptive surfaces issue no buy/sell/hold, no recommended action, no verdict hues. Direction is data (signed, neutral), not judgment. `decision_supported=false` until validation earns otherwise.
3. **Two-lane truth.** Model (blue) and market (amber) are structurally and visually isolated, symmetric in weight; a market swing must never read as a model signal.
4. **Bloomberg-grade density, benchmark-anchored.** 32px data rows, 8px grid, mono tabular numerals; the Dynasty Nerds screenshots are the parity floor, translated through DG law.
5. **The shipped app is the design artifact.** Screenshot evidence and the implementer's own visual audit gate every visual GREEN; the bar is "truly exceptional," per David's standing directive.

## Accessibility & Inclusion

Keyboard-first: every receipt/disclosure focusable and operable (Enter/Esc/touch; hover is enhancement only). Visible focus via the governed `--dg-focus` grammar in both themes. `prefers-reduced-motion` honored by every motion class. axe violations = 0 on shipped surfaces; contrast at WCAG AA minimums. No information carried by color alone (constitutionally reinforced — hue is never allowed to carry verdict meaning anyway).
