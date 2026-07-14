# E1 — Breakout Base-Rate Tables: Pre-Registration Spec (DRAFT v0)

**Board position:** edge-patterns E1 (dual-cleared backlog; David ordered base-rate tables first).
**Discipline rule (standing, from the edge-patterns board):** hypotheses are REGISTERED before any table is computed. No ad-hoc mining; a table that wasn't pre-registered doesn't render, period. This spec IS the registration vehicle.

## 1. What gets registered (per hypothesis)
- **Cohort definition** in manager-recognizable terms (e.g. "WRs drafted rounds 1–2, seasons 1–3") with the EXACT filter predicate over our data fields.
- **Breakout definition** — the outcome event, defined once (candidate: top-24 positional finish PPR; alternatives listed at registration, one chosen BEFORE computation).
- **Data window** and its honesty bounds (which seasons our data actually covers; no silent survivorship).
- **Minimum cell size** — below it, the cell renders "sample too small (n=X)", never a rate.
- **What the table may claim** — descriptive base rates only; the No-Verdict line holds; no player-level "will break out" statements.

## 2. Registration ledger
Each registered hypothesis gets an entry here (id, date, registrant, predicate hash) BEFORE the computing script runs. The computing script fail-closes on any hypothesis not in the ledger — same enforcement pattern as the comp extractor's manifest.

## 3. Credibility standards (Gemini Position 2, 2026-07-13 — screened, bases: Harstad age-curve studies, TPRR/YPRR profile patterns)
- **Mathematical breakout thresholds** (a defined outcome event, not vibes) — consistent with §1's registered breakout definition.
- **Draft-capital segmentation** as the primary cohort axis (managers recognize it; it is our own constitutional first factor).
- **Denominator honesty**: every cell prints raw counts AND a confidence band — "75% (3 of 4 qualifiers; 95% CI [19%, 99%])" — so small-sample fragility confronts the reader. SPEC PIN: Wilson score interval (registration names the method once; no method shopping).
- **Anti-mining**: the registered predicate set is LOCKED in a configuration file before the historical extractor runs — matching §2's fail-closed ledger exactly (independent convergence with the comp-extractor manifest pattern).

## 3b. Candidate hypothesis slate (to be filled at the PVO/E1 working session; DAVID selects registrations)
Seeds from the framing: 3rd-year-WR folklore vs a draft-capital-segmented WR breakout table; RB rounds 1–2 seasons 1–3; TE year-3 (the "TE cliff" folklore test). Each becomes a registered predicate or dies — none render otherwise.

## 4. Verification lane
Codex RED on: predicate correctness, cell-size enforcement, survivorship/censoring honesty (players still mid-window), and the renderer's suppression contract.

## 5. What this is NOT
Not a projection model, not an Engine input, not a verdict surface. Market data stays out of model inputs (constitutional). Tables are descriptive context for the inspector's why-slot region, David-sequenced.
