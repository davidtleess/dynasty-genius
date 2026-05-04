---
title: Engineering Backlog
type: project-knowledge
last_updated: 2026-05-03
owner_default: Codex (engineering)
---

# Engineering Backlog

Holding pen for tickets that are not in the active sprint (`docs/next-sprint.md`) but are formally tracked for future pickup. Distinct from `next-sprint.md § Deferred`, which is for items explicitly out-of-scope for *this* sprint only.

## Ticket Format

```
### BACKLOG-NNN — Title
- **Filed:** YYYY-MM-DD
- **Filed by:** [conversation/source]
- **Owner (suggested):** [Codex / Claude / David]
- **Priority:** [P1 / P2 / P3]
- **Effort estimate:** [S / M / L / XL]
- **Depends on:** [other tickets, or "none"]
- **Description:** what + why
- **Acceptance criteria:** how we know it's done
```

---

## Open Tickets

### BACKLOG-001 — Automate 2027/2028 consensus board ingestion
- **Filed:** 2026-05-03
- **Filed by:** 2027 Class Tracker drafting session
- **Owner (suggested):** Codex
- **Priority:** P3
- **Effort estimate:** M
- **Depends on:** none
- **Description:** Manual maintenance of class-tracker consensus rankings is the single largest recurring cost in keeping `docs/class-trackers/*.md` current. Investigate ingesting the [NFL Mock Draft Database consensus big board](https://www.nflmockdraftdatabase.com/big-boards/2027/consensus-big-board-2027) on a weekly cron and writing a structured snapshot to `data/class_consensus/{class_year}/{YYYY-MM-DD}.json`. The class-tracker markdown files would then reference the latest snapshot rather than re-stating ranks inline.

  **Investigation scope before committing to a build:**
  1. Does NFLMockDraftDatabase expose a public API or a stable JSON endpoint? If not, is HTML scraping permissible per their ToS?
  2. If scraping is required, what is the cadence cap (robots.txt, rate limits) we must respect?
  3. Are there 2+ alternative consensus sources (PFF, ESPN, Draftsharks) we should ingest in parallel for cross-validation, per Framework Rule 4 (65/35 quant-qual blend principle applied to source diversification)?
  4. Storage: extend `docs/storage-strategy.md` with a `class_consensus` snapshot pattern, or live in a new `data/` subtree?

- **Acceptance criteria:**
  - A short investigation memo (`docs/research/2027-consensus-ingestion.md`) documenting feasibility, ToS posture, and recommended approach.
  - If ingestion is approved by David, a follow-up ticket (BACKLOG-NNN) is filed with implementation scope.
  - **No production scraping code is written under this ticket** — investigation only.

- **Out of scope:**
  - Player-level prospect data ingestion (handled separately under PlayerProfiler / RAS pipelines).
  - Live KTC integration (already deferred in `next-sprint.md`).

---

## Closed Tickets

_None yet._
