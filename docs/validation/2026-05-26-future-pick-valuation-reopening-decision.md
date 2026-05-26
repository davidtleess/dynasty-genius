# Future-Pick Valuation Reopening — Decision (Phase 24)

**Status: APPROVED (David, 2026-05-26)** — Codex (engineering) + Gemini (PM/governance) consulted.

**Transition:** Phase 17.3 `PICK_VALUE_STATUS = "deferred"` (future picks reconstructed for
ownership, **no numeric value**) → **`"active_v1_historical"`** (future picks valued in xVAR).

Spec: `docs/superpowers/specs/2026-05-26-draft-pick-valuation-design.md` ·
Plan: `docs/superpowers/plans/2026-05-26-draft-pick-valuation.md`

---

## Context

Phase 17.3 deliberately left future draft picks **unvalued** (`PICK_VALUE_STATUS = "deferred"`;
Team Value Matrix asserted `future_picks_present_unvalued`). Phase 24 reopens that lock to value
dynasty rookie picks in **xVAR** — the same unit players use — so trades mixing players and picks
reduce to one comparable number, replacing the prior fake-player `value_draft_pick`.

Reopening a deliberately-locked ruling is an escalation trigger (operating loop §Escalation).
**David approved the reopening 2026-05-26.** Gemini (PM) ruled it an **in-flight correction that
aligns pick math with the existing Phase 17 starting-lineup rule**, not a constitutional override.

## Decision

Value future/unknown dynasty rookie picks in xVAR via a **historical realized-value-by-slot
curve** (v1):

- **Source:** `app/data/training/prospects_with_outcomes.csv`, mature classes **2015–2022**
  (recent classes lack realized Year-2+3 PPG).
- **Bridge:** "first 36 skill players in NFL draft order = the FF rookie board"; each player's
  realized `y24_ppg → DVS → xVAR` with their actual position constants.
- **Option-value floor (Option A):** per player `priced_xvar = max(0, xVAR)`; slot expected
  value = **mean** of priced samples. A busted pick is benched/cut and contributes 0, never
  negative — aligning with the Phase 17 "best legal starting lineup" guardrail. (Adopted after
  the first real-data build produced negative round-2/3 prices; Codex + Gemini consensus.)
- **Reconstructed future picks** know only `(season, round)` → valued via the **round-only
  generic tier** (`round_N_generic`), resolution `round_tier`.
- **SF-QB ordering knob:** off (`0`) in v1; calibration against real Sleeper rookie-draft
  history deferred.

## Guardrails (binding)

- Pick values are **NFL-derived historical expectations, not market-measured prices**.
- **`decision_supported = False`** on every pick value (coercion-locked).
- Caveats on every pick value: `pick_value_historical_expected`,
  `pick_value_floored_at_replacement`, `pick_value_thin_sample`, and (reconstructed picks)
  `generic_future_pick_round_only`.
- Pick values are **excluded from team-strength / posture aggregates**
  (`starter_weighted_xvar` stays players-only); surfaced in the `future_picks` block only.
- **No market/analyst/ADP data enters Engine A/B training** — the valuation module is model-blind
  (guard test `test_pick_valuation_inference_only`).
- **Deferred:** near-class named projection (consensus-mock NFL capital + rookie ADP), aggregate
  ADP ingestion, pick-appreciation-over-time, Regime A (drafted-class per-prospect valuation),
  and any decision-rule / accept-floor logic.

## Consultation trail

- Brainstorm + spec: Claude with David; Codex + Gemini consulted (CLEAR/APPROVED).
- Plan: Codex review (5 findings patched → CLEAR).
- Option A correction: Codex (engineering) + Gemini (governance) consensus; recorded in spec §4.

## Governance confirmation

- **Constitution "frontend comes last":** preserved — this is backend only; frontend HOLD intact.
- **Market/model separation:** preserved — pick valuation is overlay/inference; no training input.
- **Banned David-facing output patterns:** none — quantitative signals only, no verdict language.
- **Active model artifacts:** unchanged — no Engine A/B pkl, manifest, or contract change.
