# League Pulse — Increment 2: Read-Only UI Surface — Design Spec

**Date:** 2026-06-22
**Status:** v2 — round-1 findings integrated (Codex SPEC-F1/F2/F3, Gemini-concurred). Awaiting Round 2 dual-CLEAR. NO RED until dual-CLEAR + David approval.

> **Round-1 resolution (v1→v2):** §4 tightened to match the backend DTO allowlists exactly (no generic/wildcard rendering). **F1** card `score_components` now per-lane (model-native `_MODEL_NATIVE_SCORE`; overlay `_OVERLAY_SCORE`, `league_pulse_models.py:73,87`). **F2** model-native evidence = the exact five DTO keys (`league_pulse_models.py:64-71`), no wildcard. **F3** PartnerRanking evidence adds `position_scores` (deterministic QB/RB/WR/TE numeric formatter) — the per-position evidence behind `matched_positions` on the centerpiece. +3 matrix rows (§8). Gemini found no additional defect on the §5 market-overlay separation or §6 framing.
**Authored by:** Claude Code (Codex technical-reviews; Gemini governance-reviews)
**Phase:** Phase 12 (Frontend) decision-surface sequence — League Pulse Increment 2 (read-only UI over the Inc1 contract)
**Predecessor:** Increment 1 (backend read-only contract) — MERGED `dea4c4c`. Consumes `LeaguePulseResponse` as-is; **no backend/API/OpenAPI/Zod change.**
**Frontend HOLD:** David lifted the binding Phase-12 HOLD **scoped to this read-only League Pulse surface only** (2026-06-22). The rest of the HOLD stands; this lift authorizes no other frontend build, **no new runtime dependencies, no react-router.**
**Governance:** constitution / north-star / operating-loop / code-hygiene — all v1.0.0.

---

## 1. Goal
Wire the existing empty **"League Pulse"** nav slot in `AppShell` into a **read-only,
honesty-first** UI over `GET /api/league/pulse`. Renders the typed `LeaguePulseResponse`
(Inc1 generated client) so David can see the league landscape for trade targeting — team
postures, the "who-to-target" partner rankings, team-value overview, and opportunity cards —
**without** any verdict, recommendation, or decision-grade framing, and with the market-derived
content **visually quarantined** as a descriptive overlay (NOT a validated edge,
`[[feedback_divergence_is_unvalidated]]`).

## 2. Scope
**In:** new isolated `frontend/src/league-pulse/` surface; manual `fetch("/api/league/pulse")`
+ generated `zLeaguePulseResponse.parse`; honest state machine; AppShell render branch.
**Out (hard boundary):** any backend/API/OpenAPI/Zod regen (Inc1 frozen); new runtime deps;
react-router; sort/filter/group (a separate later increment); live refresh; player-inspector
integration; any new derived prioritization/scoring in the client.

## 3. Layout (Q2 — cockpit-converged)
Single read-only surface, top→bottom:
1. **Honesty / status band** (§6 header) — as-of `captured_at`, artifact-state caveat,
   EXPERIMENTAL/not-decision-grade disclaimer, dropped counts, source-artifact summary.
2. **Partner Rankings** (centerpiece, but **labeled market-influenced context — not a
   validated edge**, §5).
3. **Team Postures** table (compact context).
4. **Team Value Overview** (compact).
5. **Opportunity Cards** — two visually separate sections: **Model-native** then
   **Market Overlay** (§5).
Empty arrays render **section-level empty states**, never hide the whole surface.

## 4. Per-section field allowlists (deterministic formatters — Codex omitted-risk)
`evidence` / `score_components` / `positional_summary` / `future_picks` are open `record`
types; the UI renders ONLY an explicit allowlist per section via deterministic formatters —
**never a raw object dump**. Unknown keys are ignored (not rendered).
- **TeamPosture:** `posture_label`, `score` (1-dp), `components` (labeled known keys:
  `starter_weighted_xvar_z`, `age_window_score`, `early_pick_balance_score`,
  `development_stash_score`), `caveats`.
- **TeamValue:** `value_views` (`starter_weighted_xvar`, `lineup_xvar`, `depth_credit_xvar`,
  `total_xvar_capped`, `top_n_xvar`); `age_profile` (`value_weighted_age`, `median_age`,
  `pct_value_over_28`); `positional_summary` per QB/RB/WR/TE (`z_score`, `surplus_label`);
  `future_picks` (`owned_count`, `outgoing_count`, `pick_value_status`). **No raw player list**
  (Inc1 excludes it).
- **PartnerRanking:** `counterparty_team_name`/`counterparty_roster_id`, `partner_score`,
  `matched_positions`, `score_components` (exactly `complementarity_score`,
  `divergence_density_score`, `activity_recency_score`, `posture_alignment_score`), `evidence`
  (exactly `perspective_posture`, `counterparty_posture`, `divergence_row_count`, **and
  `position_scores`** rendered via a strict QB/RB/WR/TE numeric formatter — F3, the per-position
  evidence behind `matched_positions`; unknown nested keys suppressed); `market_influenced`
  badge + `caveats`.
- **Card / MarketCard:** `card_id`, `card_type`, `opportunity_score`, `rationale_primary`,
  `rationale_secondary` (already neutral, backend-mapped), `caveats`; and:
  - **`score_components` per lane (F1)** — model-native renders **exactly** `fit_score`,
    `feasibility_score`; overlay renders **exactly** `fit_score`, `divergence_score`,
    `feasibility_score`. No other key rendered (matches `_MODEL_NATIVE_SCORE` / `_OVERLAY_SCORE`).
  - **evidence per card-type allowlist** — model-native: **exactly** `position`,
    `perspective_position_z`, `counterparty_position_z`, `perspective_surplus_label`,
    `counterparty_surplus_label` (F2 — exact five, NO wildcard); overlay: `signal`,
    `signal_status`, `model_minus_market_delta`, `market_percentile`, `model_percentile`,
    `xvar`, `raw_xvar`, `lineup_role`, `asset_roster_id`.
  - Overlay cards also render `recommended_drop` (`full_name`, `position`, `cut_priority`,
    `ir_compliance_status`, `cut_rationale`).

## 5. Market-overlay visual honesty (Q3 — governance crux)
The Q3=B labeling is made **visually unmistakable**, never blended with model-native:
- **Opportunity cards** split into two clearly headed sections: a **Model-native** section
  and a separate **Market Overlay** section. The Market Overlay section carries a persistent
  caveat banner — *"Market overlay: descriptive market signal, not a validated edge"* — and
  each overlay card surfaces its `market_overlay_unvalidated_divergence` caveat.
- **Partner Rankings** render a visible **"market-influenced"** badge (every ranking has
  `market_influenced=true`) plus a section note that the partner score is partly market-derived
  (`partner_score_market_influenced` caveat). It is presented as **context**, never a buy/sell
  instruction or validated ranking.
- No model-native section ever shows a market evidence/score field (the Inc1 contract already
  guarantees this; the UI does not re-introduce it).

## 6. State machine + honesty header (Q5 + Q4)
- States: `loading → ready / unavailable / parse-error` (mirror RosterAudit; **no 422** — the
  Inc1 route is 200 or 503). Non-OK (incl. 503 `league_pulse_artifact_unavailable` /
  `league_pulse_dependency_unavailable`) → `unavailable`; fetch/JSON/Zod failure → `parse-error`.
  Never blank.
- `status="degraded"` is **NOT** a failure — it stays in `ready` view; the header renders the
  artifact-state banner. (Backend is always artifact-state, so this is the normal case.)
- **Header (Q4):** "League Pulse" title + **EXPERIMENTAL / not decision-grade** disclaimer;
  **"as of `<captured_at>`"** + the `league_pulse_artifact_state_<date>` caveat; `dropped`
  counts (any non-zero → a "n records withheld" note); `source_artifacts` summary;
  `decision_supported=false` surfaced as a non-grade marker.
- **Banned-language (Q4):** all static UI copy is neutral and passes the FE banned-language
  linter — no buy/sell/target/fade, no "sell now"/"target X" imperative phrasing. Use
  "counterparty fit", "partner context", "market overlay", "opportunity cards". Backend-mapped
  rationale tokens (already neutral) are rendered as-is.

## 7. Component structure (Q6)
New `frontend/src/league-pulse/`:
- `LeaguePulse.tsx` (container: fetch + `zLeaguePulseResponse.parse` + state machine)
- `LeaguePulseHeader.tsx` (honesty/status band)
- `LeaguePulseStates.tsx` (loading / unavailable / parse-error)
- `PartnerRankings.tsx`, `TeamPostureTable.tsx`, `TeamValueOverview.tsx`, `OpportunityCards.tsx`
- `fixtures.ts`, `LeaguePulse.css`, per-component `*.test.jsx`
- AppShell: `import { LeaguePulse }` + `{activeSurface === "League Pulse" && <LeaguePulse />}`.
Manual `fetch` + generated Zod parse (no callable client — matches RosterAudit, no new dep).

## 8. Acceptance criteria & falsification matrix
AC: read-only surface renders all sections from the typed response; market overlay visually
separated + caveated + partner-rankings market-influenced badge; honest header (as-of,
EXPERIMENTAL, dropped, decision_supported); state machine never blank; section empty states;
neutral banned-language-clean copy; per-section field allowlists (no raw evidence dump); no
backend/Zod change; FE gate (typecheck/biome/vitest/banned-language/build) green.

Falsification matrix (each → a RED test):
- **ready-nominal:** 200 + valid payload → all sections render; counts match arrays.
- **degraded stays in-view:** `status="degraded"` → ready view + artifact-state banner (not a failure).
- **unavailable:** 503 → `unavailable` state (never blank); covers both 503 error codes.
- **parse-error:** malformed JSON / Zod parse failure → `parse-error` state.
- **market-overlay separation:** overlay cards render in the Market Overlay section with the
  unvalidated caveat; a model-native card never appears there and shows no market field.
- **partner market-influenced:** every partner ranking shows the market-influenced badge +
  caveat; never framed as a validated/decision-grade ranking.
- **empty sections:** empty `partner_rankings` / `*_cards` / `team_*` → section empty state, surface still renders.
- **dropped surfaced:** non-zero `dropped.*` → header "withheld" note.
- **field allowlist:** an unknown/extra key in `evidence`/`score_components` → NOT rendered (no raw dump).
- **card score allowlist (F1):** a fixture injects an unexpected `score_components` key into both a model-native and an overlay card; `zLeaguePulseResponse.parse` succeeds, but `OpportunityCards` renders only the per-lane allowlisted keys (model-native `fit_score`/`feasibility_score`; overlay +`divergence_score`).
- **model-native evidence exactness (F2):** an extra key ending in `_position_z`/`_surplus_label` but not one of the five backend DTO keys is NOT rendered.
- **partner position_scores formatter (F3):** `evidence.position_scores` renders only QB/RB/WR/TE numeric entries; unknown nested keys suppressed.
- **banned-language:** all static copy scanned → clean (FE linter).
- **decision_supported:** surfaced as non-grade; no verdict/recommendation rendered anywhere.
- **AppShell wiring:** selecting "League Pulse" renders the surface.

## 9. Build sequence (post-approval only)
spec dual-CLEAR (Codex technical + Gemini governance) → David approves → Codex RED → Claude
GREEN → dual-CLEAR per task → David-authorized commit → zero-divergence audit → closeout
(FE gate). No RED before dual-CLEAR + David approval. Likely task cut: **T1** container + state
machine + AppShell wiring + states + fixtures; **T2** honesty header; **T3** Partner Rankings
(market-influenced labeling); **T4** Team Postures + Team Value overview; **T5** Opportunity
Cards (model-native / market-overlay split + recommended_drop). Each Codex-RED → Claude-GREEN.
Closeout = FE gate green + full-branch CLEAR (no Python/backend change expected).
