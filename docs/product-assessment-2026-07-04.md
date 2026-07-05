---
title: Dynasty Genius — Product Assessment Findings & Remediation Workboard
date: 2026-07-04
author: Claude (implementation lead), four-audit synthesis; Codex ran an independent parallel assessment (see ledger 19:40); Gemini product audit same day
audience: David + cockpit
status: assessment + proposed workboard — David directive 2026-07-04: "fix all the weak spots and gaps … build a world class front end UI." Board order below is PROPOSED, pending cockpit convergence + David ratification.
basis: main @ f1bebea; audits over src/, app/, frontend/, docs/validation; load-bearing claims spot-verified in source
---

# Assessment verdict (one paragraph)

Governance/honesty machinery: world-class and demonstrably effective (TE contamination catch, ~90 defects pre-ship this session, QB gates held). Engineering: strong, with specific fixable debts. Analytics: honest, consensus-competitive, edge UNPROVEN (every enrichment gate held negative; divergence ledgers empty; verdicts accrual-gated ~Sept/~Dec). UX: the weakest layer vs the daily-login ambition — the app boots to an empty placeholder and speaks internal jargon to its one user. The trust substrate is built; the marginal return has shifted from more rigor to usability + data protection.

# Findings register (all verified; file refs)

## F-DATA (top strategic risk)
- **F1. Single-laptop SPOF over irreplaceable data.** Capture DBs (`fc_forward_capture.db`, `model_forward_capture.db`), training CSVs, model pkls are gitignored and exist only on this Mac. DEBT-6 detects loss; nothing prevents it. A dead disk erases the PIT evidence base for the Dec-2026 edge test.

## F-CODE (live correctness)
- **F2. Stale-cache risk:** `app/api/routes/players.py:129-160` — `lru_cache(maxsize=1)` artifact loaders, no invalidation, under daily 09:15/09:45 refreshes; every other route re-reads per request.
- **F3. Silent scoring-path failure:** `src/dynasty_genius/pvo_assembler.py:286` swallows Engine B inference exceptions (`except Exception: engine_b_resolved = None`), no logging; no logging framework anywhere in `app/` (`engine_b_service.py:39` uses print).
- **F4. No-Verdict API gap:** `app/api/routes/trade.py:105-108` serves verdict-shaped evaluator fields; the line is held only by FE non-render. Everywhere else it is contract-enforced.
- **F5. TE v3 report labeling:** `scripts/train_engine_b.py:115-170` — deployed artifact's `validation_report_te.json` is in-sample (`promotion_warranted: null`). Promotion rested on the earlier holdout-validated recipe; the on-disk report implies more than it shows. Relabel/annotate.
- **F6. Duplication with drift:** 503-guard kernel hand-rolled 8× with inconsistent envelopes; `_has_non_finite` copy-pasted; FE fetch/state machine copy-pasted 5×.
- **F7. Cruft:** unmounted `leagues.py`/`rosters.py` stubs; empty `src/dynasty_genius/{agent,pipelines,valuation}/` packages; ~100 accumulated one-shot scripts; `src`→`app` layering inversion (`pvo_assembler.py:14-17`); trust_surface.py relative path + bare excepts; `app/models/` near-vestigial.

## F-UX (daily-login gap)
- **F8. Empty landing:** default surface = "Rookie Board", a parked placeholder with no render branch (`AppShell.tsx:35-52,120-129`); 3/11 nav slots render title-only (Rookie Board, Waiver Radar, Research Assistant).
- **F9. Dev utility in user nav:** Project Tracker sits in the primary rail.
- **F10. Jargon as user copy:** literal `decision_supported=false` (`RosterCapacitySandbox.tsx:104`), `cut_priority` column header, `maturity_pct: unset`, `density_baseline_insufficient`-class tokens, raw ISO dates, unformatted numbers.
- **F11. Caveat-first IA:** disclaimers stacked before content (TradeLab.tsx:121-132; LeaguePulse.tsx:80-98). Honesty is required; the ordering is not.
- **F12. Missing product affordances:** no home/dashboard, no router (state lost on refresh), zero media queries (no responsive/dark mode), no charts/sparklines despite trend-shaped PIT data, no global player search (inspector reachable only via Trade Lab), TrustStrip hardcoded QB, unlabeled value spans (`ValuationTwoLane.tsx:48-57` — invalid dl markup).

## F-MODEL (standing truths, not new work)
- Engine B consensus-competitive, edge unproven (G3 tie vs ECR, BCa CIs straddle zero); Engine A = 3-feature capital re-ranker, enrichments failed gates; blend constants documented-not-fitted; RAS/PFF adapters run on mock fixtures (source inventory overstates). Discipline unchanged: market wall, No-Verdict, pre-registered gates, accrual-gated verdicts.

# Proposed remediation board (cockpit to converge; David ratifies)

- **HORIZON 0 — protect + correctness (small, first):**
  0a. Offsite encrypted daily backup of capture DBs + training CSVs + model pkls (F1). Hours of work; removes the only unrecoverable failure mode.
  0b. Fix F2 (cache invalidation or per-request read, matching sibling routes).
  0c. Fix F3 minimally (log the swallowed exception; introduce logging in app/).
  0d. Triage F4 + F5 (contract-level guard for trade payloads; TE report annotation) — David-gated tickets.
- **HORIZON 1 — daily-login UX increment (governance-clean):**
  1a. Landing surface → Daily What-Changed (F8).
  1b. Rail cleanup: parked slots hidden or explicitly "parked" (F8) + Project Tracker out of primary rail (F9). [= Gemini Tasks 1–2]
  1c. Humanize caveat/status copy via a token→manager-language layer; format numbers/dates (F10). [= Gemini Task 3]
  1d. Caveat placement: below the data they caveat, single instance (F11) — copy/order only, no honesty reduction.
- **HORIZON 2 — world-class UI program (David directive):**
  Full design vision spec BEFORE code: Gemini strategy/UX framing (real user situations, mislead risks, falsification seeds, overclaim check) → design-system direction (typography/layout/dark mode/responsive/router) → trend visualization over the accruing PIT series → global player search + player cards as first-class → per-surface rebuild increments, each cockpit-TDD. No-Verdict Line holds throughout; neutral-palette contract renegotiated only explicitly (banned-hue tests stay unless David re-rules).
- **HORIZON 3 — code health (opportunistic/dedicated):**
  Shared guard kernel (F6), shared FE fetch hook, cruft cleanup (F7), logging framework rollout, mypy adoption decision.
- **STANDING:** data/model discipline unchanged; in-season edge-seeking posture — watch accruing captures for divergence signals as 2026 data lands (~Sept realized outcomes, ~Dec Gate-4).

# Status log

- 2026-07-04: David ratified direction ("fix all the weak spots and gaps … world class front end UI"); findings routed to both lanes; board order pending cockpit convergence + David's per-horizon authorization.
- 2026-07-04 (later): **three-way converged.** Codex CONFIRMED F2 (players.py:129-155 — three `lru_cache(maxsize=1)` loaders called at :240/:261, no production invalidation; fix = drop caching on the two volatile artifact loaders or mtime-aware keys; banned-vocab may stay cached) and F3 (pvo_assembler.py:282-287 broad except → silent downgrade; engine_b_service.py:39,74,83,91 print-based; fix = logger.exception with player/position/season context + caveat marker, never a user-facing verdict). Codex board position: H0 leads; H1 may run in parallel as a design/spec lane only; **F4/F5 reclassified as David-gated follow-up tickets, not first-slice work (adopted)**; plus a named backlog item: sklearn artifact/runtime reproducibility. No other workboard defects found. Gemini (advisory): concurred H0→H1; H2 framing guard — PIT trend visualizations must be labeled descriptive/experimental with `decision_supported=false` adjacent to the chart, never presented as a predictive trend indicator. **Awaiting David: (i) board ratification, (ii) commit authorization for this doc + AGENT_SYNC, (iii) H0 branch + kickoff authorization.**
