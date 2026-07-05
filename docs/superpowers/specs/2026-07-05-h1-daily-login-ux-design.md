# H1 — Daily-Login UX Increment (Design)

**Date:** 2026-07-05 · **Author:** Claude (implementation lead) · **Status:** v4 — v2 integrated Codex F1–F6; v3 expanded the token contract to real shapes; v4 fixes the status-line sweep miss + the position-prefix regex capture contract. Re-review pending. Gemini framing received (2026-07-05); David ratified the board 2026-07-04 and opened H1 ("continue with horizon 1").
**Board items:** 1a–1d (`docs/product-assessment-2026-07-04.md`, findings F8–F11). FE-only; no backend/contract change; no new surface.

## 1. Problem (verified in source)

- The app boots to `SURFACES[0]` = "Rookie Board" — a parked placeholder with **no render branch** (`AppShell.tsx:35-52,120-129`). Three of eleven rail slots render title-only.
- Project Tracker (a dev utility) sits in the primary user rail.
- Internal tokens render as user copy: literal `decision_supported=false` in ≥5 components (`RealizedOutcomeScorecard.tsx:97`, `DailyWhatChanged.tsx:87,338`, `SystemHealthCard.tsx:144`, `PlayerDetailCard.tsx`, roster-capacity), `settlement_status:`/`maturity_pct:` meta lines (`RealizedOutcomeScorecard.tsx:95-96`), `cut_priority` column header, raw ISO timestamps.
- Trade Lab stacks two disclaimer paragraphs before content (`TradeLab.tsx:121-132`).

## 2. Scope

### 1a — Landing surface + rail order
- Default surface = **Daily What-Changed** ("what happened since yesterday" is the daily-login question — Gemini framing Q1 concurs, off-season and in-season).
- Rail order (active first, parked last): Daily What-Changed · Roster Audit · Trade Lab · Roster Capacity · League Pulse · Model Trust · Accuracy Tracker · Rookie Board (parked) · Waiver Radar (parked) · Research Assistant (parked).

### 1b — Parked surfaces + Project Tracker
- **Parked surfaces stay VISIBLE** (Gemini mislead-risk 3: hiding them hides honest gaps). Badge text is exactly **"Parked"** for all three; "Off-Season" is **REJECTED** (parked-ness here is evidence/priority-based, not seasonal — a seasonal badge would promise automatic return) [F1 resolved].
- **Per-surface parked-card table (authoritative copy facts — F2 resolved).** Card body = plain-language facts below; the evidence path renders as a small meta line (David reads the repo). Neutral tone, no dates promised, no verdict language:

| Surface | Card heading | Required body facts | Evidence meta line | Unpark condition (stated on card) |
|---|---|---|---|---|
| Rookie Board | "Rookie Board — parked" | Rookie valuation stands on the draft-capital + age prior and the ratified cohort-prior table; the college-enrichment path failed its pre-registered promotion gates (0 of 2 positions), so a richer board surface is parked rather than built on an unproven signal. The legacy `rookie_board.html` remains available outside the app. | `docs/validation/engine_a_v2_cfbd_backtest_report.md` | A David-ratified spec for a React rookie surface over the existing prior. |
| Waiver Radar | "Waiver Radar — parked" | This surface needs in-season usage signals (routes, snaps) that only accrue while games are played; building it now would ship an empty surface. | `docs/governance/01-north-star-architecture.md` (surface gates) | In-season 2026 usage accrual plus a David-ratified spec. |
| Research Assistant | "Research Assistant — parked" | A north-star surface with no active design yet — parked honestly rather than stubbed. | `docs/governance/01-north-star-architecture.md` (decision surfaces) | A David-prioritized design cycle. |

- **Project Tracker leaves the primary rail** → a visually separated "Developer" utility zone at the rail bottom (small, labeled). Still reachable there and via the command palette. Primary rail = David-facing surfaces only (Gemini seed 4).

### 1c — Copy translation + formatting (shared helpers, new `frontend/src/lib/copy.ts`)
- `describeStatusToken(token)` — `lib/copy.ts` is the single source of truth. **Initial map locked (F3 resolved):**
  - Exact keys: `insufficient_history`, `current_not_delta`, `freshness_unverifiable`, `density_baseline_insufficient`, `pre_capture_window`, `waiver_range_unavailable` (the bare no-colon status — real Roster Capacity shape).
  - Prefix classes (prefix translated; the raw suffix rendered verbatim in parentheses so precision is never lost): `waiver_range_unavailable:*` (colon caveat form, e.g. `:stale_snapshot`), `capacity_audit_blocked:*`, `league_pulse_artifact_state_*` (full real prefix — dated suffix like `2026-06-22` rendered verbatim; the bare `artifact_state_*` alias is NOT assumed).
  - Position-prefixed pattern class: `^([A-Z]{2,3})_waiver_range_unavailable_(.+)$` (real shape `WR_waiver_range_unavailable_recovery_unverifiable`) — capture group 1 (position code) and capture group 2 (suffix descriptor) both preserved verbatim in the translation: "WR waiver range unavailable (recovery_unverifiable)".
  - **Unmapped token → render the raw token string unchanged + console.warn** (fail-safe, never crash, never invent copy — Gemini seed 3).
  - Translations are mathematically descriptive, never permissive (framing mislead-risk 1: `density_baseline_insufficient` → "Waiver-pool valuation coverage is below the reporting floor; replacement-cost ranges cannot be verified" — NOT "thin but okay"). Every mapped string must pass the banned-language linter.
- Standard disclosure line, exact string LOCKED (F1 resolved): **"Descriptive only — not decision-grade."** The API field `decision_supported=false` is untouched (contract unchanged); the UI stops quoting the field name. **Disclosure baseline table (F4 resolved — count and adjacency preserved per location):**

| Rendered location (current literal) | Instances | H1 action |
|---|---|---|
| `DailyWhatChanged.tsx:87` (header sentence) | 1 | string swap |
| `DailyWhatChanged.tsx:338` (per-baseline-section stamp) | 5 (one per section) | string swap ×5, count pinned |
| `RosterCapacitySandbox.tsx:104` (header sentence) | 1 | string swap |
| `SystemHealthCard.tsx:144` (span) | 1 | string swap |
| `RealizedOutcomeScorecard.tsx:97` (meta line) | 1 | string swap |
| `LeaguePulseHeader.tsx:53` (grade line) | 1 | string swap — **explicitly allowed**: Codex-confirmed NOT pinned by `LeaguePulseMitigation.test.jsx` or the `test_system_tier_readiness_t4.py` registry tripwires; `LeaguePulseHeader.test.jsx` may be RED-amended. The mitigation block itself stays byte-untouched. |
| `PlayerDetailCard.tsx` (universal state; exact rendered string pinned at RED time) | 1 | string swap |

- `formatCaptureTimestamp(iso)` — deterministic (F5 resolved): `Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" })`; exact ISO preserved in a `title` attribute; `null`/`undefined` → "—"; unparseable string → rendered unchanged (no NaN dates). CI-stable regardless of host locale/timezone.
- Meta lines humanized: `settlement_status:` → "Settlement status: …" (value through `describeStatusToken`), `maturity_pct: unset` → "Data maturity: not yet started" / `N` → "Data maturity: N% of tracked weeks finalized". `cut_priority` header → "Cut exposure rank" with its already-disclosed basis line kept adjacent.
- Numbers: existing signed/`-0`/span conventions unchanged (backend owns precision; H1 does not reformat values, only labels/dates).

### 1d — Caveat placement (taxonomy locked — F6 resolved)
- **Region-level caveats** (get the standard block — high-contrast-neutral bordered, immediately below the region header, visible without scrolling, single instance per region; Gemini mislead-risk 2): surface-intro disclaimers (Trade Lab's two stacked paragraphs consolidate into ONE block) and artifact-level staleness / `aborted_reason` banners.
- **Row/local metadata — placement UNTOUCHED:** per-row status cells and chips, Roster Capacity pool-level caveats (`PoolRange`), What-Changed per-lane model-window/pvo caveats, SystemHealthCard report-row statuses and timestamps, and ALL mitigation blocks (inviolate, §3). H1 changes their *strings* only where the disclosure/token tables above say so, never their position or nesting.

## 3. INVIOLATE — explicitly out of scope (verify, don't trust)

- **League Pulse mitigation block + Trade Lab mitigation copy are contractually pinned graduation tripwires** (`LeaguePulseMitigation.test.jsx` ↔ `league_pulse_fe_mitigation_v1`; `TradeLabMitigation.test.jsx` ↔ `trade_lab_fe_mitigation_v1`; tier-readiness registry rows). H1 touches NEITHER string. Lock-verification is a RED row: both tripwire suites + the tier-readiness contract tests must pass unmodified on the H1 branch.
- No router, no responsive/dark-mode, no charts, no global search (Horizon 2). No backend or OpenAPI change. No banned-language linter relaxation — translated copy must pass the existing AST linter.
- Committed tests that pin the literal `decision_supported=false` UI string get **Codex-amended REDs preserving the disclosure semantics** (per-section count and adjacency) while updating the string — the honesty contract is the disclosure, not the field-name quotation.

## 4. Falsification seeds (for the RED)

1. Empty-diff day (off-season dead day): landing renders a clean "no changes recorded" state per region — no crash, no blank grid (existing per-region empties extend to the landing default; Gemini seed 1).
2. Stale artifact at landing: staleness caveat renders prominently adjacent to the header with the capture date (Gemini seed 2; existing staleness fields).
3. Unmapped status token: raw token rendered, console.warn, component tree intact (Gemini seed 3).
4. Primary rail contains exactly the David-facing surfaces; Project Tracker absent from primary, present in the Developer zone; command palette still reaches everything (Gemini seed 4).
5. Parked surface click → educational card, no banned-language tokens, no empty `<h1>`-only page anywhere in the rail.
6. Default landing = Daily What-Changed on fresh mount.
7. Disclosure line per the §1c baseline table — exact string, per-location instance counts (incl. the ×5 baseline-section stamps) — and zero remaining literal `decision_supported=false` / `cut_priority` / `maturity_pct:` / `settlement_status:` strings in rendered copy. `LeaguePulseHeader.test.jsx` amended; mitigation suites untouched (no seed-7/seed-8 conflict).
8. Tripwire lock-verification: `LeaguePulseMitigation.test.jsx`, `TradeLabMitigation.test.jsx`, and `test_system_tier_readiness_t4.py` pass UNMODIFIED on the H1 branch.
9. Timestamp helper: valid ISO → deterministic America/New_York en-US string + ISO in title attr; null → "—"; malformed → raw string unchanged (no NaN dates); assertion stable across host timezones.
10. Token classes over the REAL shapes: the bare `waiver_range_unavailable`, a colon caveat (`waiver_range_unavailable:stale_snapshot`), a position-prefixed form (`WR_waiver_range_unavailable_recovery_unverifiable`), a dated League Pulse artifact state (`league_pulse_artifact_state_2026-06-22`), one other exact key, and one unmapped token each behave per §1c (suffixes/dates preserved verbatim); every mapped string passes the banned-language linter.
11. Full FE gate (vitest + tsc + biome + banned-language + build) green.

## 5. Verification

Codex RED (component tests over fixtures, no gitignored deps) → Claude GREEN → dual-CLEAR → David gates → real-shape smoke against the live artifacts (landing renders today's real What-Changed; parked cards render; RC/scorecard copy humanized) → full closeout tollgate at PR.

## 6. Review log

- v1 (2026-07-05): drafted post-framing; integrates all four Gemini framing answers (What-Changed-as-landing concur; neutral-not-permissive translation; adjacent high-contrast caveats; parked-visible-with-badge) + the tripwire-inviolate catch from repo-state review.
- v3 → v4 (2026-07-05): Codex two narrow defects accepted — header status line updated (post-fix-sweep miss); position-prefix pattern corrected to an explicit capture contract `^([A-Z]{2,3})_waiver_range_unavailable_(.+)$` (the `_*` form matched zero-or-more underscores and captured nothing).
- v2 → v3 (2026-07-05): Codex NOT-CLEAR token-contract gap accepted — token classes expanded to the REAL rendered shapes (bare `waiver_range_unavailable`; colon form; position-prefixed `[A-Z]{2,3}_waiver_range_unavailable_*`; full `league_pulse_artifact_state_*` dated prefix — bare `artifact_state_*` alias dropped as unverified); seed 10 re-anchored to real shapes.
- v1 → v2 (2026-07-05): Codex F1–F6 all accepted — exact strings locked (badge "Parked", "Off-Season" rejected; disclosure line locked) (F1); authoritative per-surface parked-card table with evidence paths + unpark conditions (F2); token map enumerated with exact keys + prefix classes + single source of truth in `lib/copy.ts` (F3); disclosure baseline table with per-location counts + explicit LeaguePulseHeader allowance vs mitigation tripwires (F4); deterministic America/New_York timestamp contract (F5); region-vs-row caveat taxonomy, row placement untouched (F6). Seeds 7–9 tightened; seed 11 added.
