# Design Spec: Rookie Board UI

**Version:** 1.1.0
**Status:** Approved
**Date:** 2026-05-09
**Target:** May 11th Dynasty Rookie Draft
**Companion spec:** `docs/superpowers/specs/2026-05-09-rookie-lookalike-market.md` (Gemini — backend data ingestion)

## Mission

Build a local HTML decision surface that surfaces Engine A prospect signals for David's 2026 dynasty rookie draft. The board provides high-signal BPA context — it does not issue draft instructions. All output carries PROSPECT_C/D grades and explicit caveats.

This is a slow draft (8 hours per pick). The board serves both pre-draft research and on-the-clock confirmation.

## Constraints

- Local file only — `file://` compatible, no server required
- No Databricks compute
- No market-derived inputs in any scoring logic
- `decision_supported: false` on all surfaces
- Engine A grades: PROSPECT_C (WR/RB/TE), PROSPECT_D (QB — negative R², directional only)
- Banned directive phrases in HTML and JS output: "draft target", "draft this", "take", "buy", "sell", "trade candidate", "action", "verdict", "confidence". The words "draft" and "slow draft" as context labels are permitted.

## Architecture

### Files

```
src/dynasty_genius/dashboard/rookie_board.html   ← main board (new)
resources/prospect_identity_2026.json            ← verified manifest (Gemini delivers)
resources/prospect_cards.js                      ← Engine A PVOs (built by build_prospect_cards.py)
resources/draft_state.js                         ← taken player list (built by refresh_draft_state.py)
resources/roster_need_signals.js                 ← position-level need from Roster Audit (new, thin extract)
scripts/build_prospect_cards.py                  ← already built; reads fixture, writes JS
scripts/refresh_draft_state.py                   ← new; fetches Sleeper draft picks, writes draft_state.js
scripts/build_roster_need_signals.py             ← new; extracts position need from live_roster_cards.json
```

### Data flow

```
prospect_identity_2026.json
        ↓
build_prospect_cards.py → prospect_cards.js (window.PROSPECT_CARDS)
        ↓
rookie_board.html loads all three JS files at render time:
  window.PROSPECT_CARDS    ← Engine A PVOs
  window.DRAFT_STATE       ← { taken: ["sleeper_id_1", ...] }
  window.ROSTER_NEED       ← { WR: "HIGH", RB: "MEDIUM", QB: "LOW", TE: "LOW" }
```

No fetch, no CORS — pure local JS variable reads.

### Refresh workflow (during slow draft)

The board is a static `file://` page — it cannot execute scripts directly. The refresh button is a UX affordance only.

1. David clicks **↻ Refresh Draft** in the browser — a visible tooltip appears: `run: .venv/bin/python scripts/refresh_draft_state.py`
2. David runs the script in terminal (or types `! .venv/bin/python scripts/refresh_draft_state.py` in Claude Code)
3. Script fetches `/draft/{draft_id}/picks` from Sleeper, writes `draft_state.js`
4. David reloads the page — taken players appear grayed with TAKEN badge

## Layout

### Page header

- Title: "Dynasty Genius — 2026 Rookie Board"
- Subtitle: "Engine A · PROSPECT_C/D · market overlay excluded · decision_supported: false"
- League context pills (right side): SUPERFLEX pill visible when `LeagueContext.is_superflex = True`; TE PREMIUM pill visible only when `LeagueContext.te_premium > 0` (omitted for David's league)
- Refresh Draft button

### Roster need banner

Pulled from `window.ROSTER_NEED`. Shows one badge per skill position:
- HIGH (red) — position has multiple players at or past age cliff
- MEDIUM (amber) — approaching cliff
- LOW (green) — no age cliff signal
- Caveat: "age-curve only · no Engine B · verify before acting"

### Position tabs

`All | QB | WR | RB | TE` with prospect counts. "All" is default (BPA view). Tab filters the ranked list in place.

### Prospect cards

One card per prospect, ranked by `dynasty_value_score` descending. PRE_MODEL prospects (no pick/round) sort to the bottom of the list.

**Card anatomy:**

```
[rank]  [name]  [pos badge]  [context badges]
        [school · pick · round · age]
        [caveat chip — QB: PROSPECT_D warning]
        [risk chip — if mock_draft_capital_unverified in risk_flags]
                                         [Engine A label]
                                         [score: 0-100]
                                         [score bar]
                                         [model grade]
─────────────────────────────────────────────────────────
⚑ Counter  [counter_argument text from PVO]
```

The `mock_draft_capital_unverified` risk chip ("⚠ pick data unverified") must render whenever that flag appears in the PVO `risk_flags` list. It is a governance requirement until Gemini's verified manifest replaces mock pick/round inputs. The chip is removed automatically once `verification_status: VERIFIED_NFL_DRAFT` propagates through the manifest.

**Context badges (inline, next to name):**

- `⚡ SUPERFLEX` — on every QB card when `is_superflex = True`
- `AGE RISK` — on cards whose position is HIGH or MEDIUM in the roster need banner (age-curve signal only; renamed from `▲ NEED` to avoid directive read)
- `TAKEN` — on cards whose `sleeper_id` is in `DRAFT_STATE.taken`
- `2027 Class` — on devy prospects with `draft_class = 2027`

**Position-specific left border accent:**

- QB (Superflex): `border-left: 3px solid #7c3aed` (purple)
- WR: `border-left: 3px solid #2563eb` (blue)
- RB: `border-left: 3px solid #16a34a` (green)
- TE: no special treatment (no TE premium in league)

**Taken state:** Card opacity drops to 35%. Name gets strikethrough. Score bar grays out. TAKEN badge appears. Card stays in rank position — the draft flow remains visible.

**PRE_MODEL cards:** Score field shows "PRE-MODEL" in muted text. No score bar. No counter-argument strip. Sorted to bottom of list.

### Counter-argument strip

Appears on every scored card (any card with a `dynasty_value_score`). Red-tinted band below the card body. Always visible — not collapsible. The constitution mandates a counter-argument for every strong signal; the 8-hour slow draft window makes tunnel vision a real risk.

```
⚑ Counter  [counter_argument from PVO — max ~150 chars displayed]
```

If `counter_argument` is null, the strip is omitted rather than showing a placeholder.

## New Scripts

### `scripts/refresh_draft_state.py`

- Reads env vars: `DYNASTY_SLEEPER_DRAFT_ID` (preferred, direct override), `DYNASTY_SLEEPER_LEAGUE_ID` (fallback)
- If `DYNASTY_SLEEPER_DRAFT_ID` is set, uses it directly — no discovery call needed
- If not set, fetches active dynasty draft ID from `/league/{league_id}/drafts`; if multiple drafts are returned, logs all IDs and selects the most recent active one; logs the selection for auditability
- Fetches all picks from `/draft/{draft_id}/picks`
- Extracts `player_id` (Sleeper ID) for each taken pick
- Writes `resources/draft_state.js`: `window.DRAFT_STATE = { taken: [...], draft_id: "...", refreshed_at: "..." };`
- Falls back gracefully if no draft is active (writes empty taken list with a `no_active_draft` caveat)

### `scripts/build_roster_need_signals.py`

- Reads `resources/live_roster_cards.json` (David's live roster, already built by `build_live_roster.py`)
- Aggregates age cliff signals by position:
  - HIGH: ≥2 players past or at cliff
  - MEDIUM: ≥1 player past or at cliff, or ≥2 approaching
  - LOW: no cliff signals
- Writes `resources/roster_need_signals.js`: `window.ROSTER_NEED = { WR: "HIGH", ... };`

## Sleeper ID Matching (Availability Sync)

Taken detection: `DRAFT_STATE.taken` contains Sleeper `player_id` strings. The prospect manifest (`prospect_identity_2026.json`) carries a `sleeper_id` field per player. The board matches on `sleeper_id`.

Dependency: Gemini's task 3 (data verification) ensures `sleeper_id` values in the manifest are accurate before May 11.

## Governance

- `market_overlay` is `null` on all prospect cards (Phase 2 — Lookalike Market)
- Engine A grades propagated verbatim from PVO: PROSPECT_C or PROSPECT_D
- QB caveat chip always rendered: "QB model PROSPECT_D · negative R² · directional signal only"
- Board reads `LeagueContext.is_superflex` and `LeagueContext.te_premium` to conditionally render league context badges — never hardcoded
- No directive phrases in HTML or generated JS: "draft target", "draft this", "take", "buy", "sell", "trade candidate", "action", "verdict", "confidence". Context labels like "Refresh Draft" and "slow draft" are permitted.

## Phase 2 (non-blocking, post May 11)

- Lookalike Market ADP overlay (per Gemini spec v1.1.0)
- Neutral divergence signal: "Market ranks this player +4 spots higher" — no directive labels
- ADP from DynastyNerds/FantasyCalc (not Sleeper league sampling — see concerns in session ledger)

## Testing

- `tests/test_rookie_board_contract.py` — covers:
  - Board HTML contains `<script src>` tags for all three JS artifacts
  - No banned directive phrases in board HTML or any generated JS (`prospect_cards.js`, `draft_state.js`, `roster_need_signals.js`)
  - `decision_supported: false` present in every `PROSPECT_CARDS` entry
  - `draft_state.js` shape: `taken` is a list, `draft_id` and `refreshed_at` are strings
  - `roster_need_signals.js` shape: all four skill positions present, values in `{HIGH, MEDIUM, LOW}`
  - `prospect_cards.js` count matches `prospect_identity_2026.json` player count (parity check)
- Manual browser check: BPA view sorts correctly, position tab filters work, TAKEN state renders correctly, counter-argument strip present on scored cards, `AGE RISK` badge shows for HIGH/MEDIUM positions
- Run `.venv/bin/python scripts/build_prospect_cards.py` with verified manifest before May 11 to confirm Engine A fires for all 2026 class players with pick + round + age

## Dependencies

| Dependency | Owner | Required by |
|---|---|---|
| `prospect_identity_2026.json` (verified NFL draft data) | Gemini | build_prospect_cards.py |
| `sleeper_id` accuracy in manifest | Gemini | availability sync |
| `live_roster_cards.json` (live Sleeper roster) | Already built | roster need signals |
| `LeagueContext` pick/scoring review | Gemini — completed | is_superflex / te_premium rendering — caveat: artifacts need regeneration after te_premium corrected to 0.0 |
