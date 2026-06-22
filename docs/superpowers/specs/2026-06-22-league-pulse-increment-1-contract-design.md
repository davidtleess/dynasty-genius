# League Pulse — Increment 1: Backend Read-Only Contract (Design Spec)

- Status: **v2 — round-1 findings integrated (Codex C1–C4 + Gemini G1). Awaiting Round 2 dual-CLEAR. Q3=B + Q2 scope David-locked. NO RED until dual-CLEAR + David approval.**

## 0. Round-1 review resolution (v1 → v2)

All producer-code claims verified at `src/dynasty_genius/league_opportunity_map.py`:
- **C1 (mapper vs backstop):** `market_overlay_total` is present in EVERY valid team
  (`team_value_matrix` source) — so "drop on leak" would drop all teams. Fix: the explicit
  **allowlist mapper suppresses** `market_overlay_total` (it is simply not selected);
  `extra="forbid"` is only the **backstop** against a raw/unexpected pass-through, not the
  normal path → §4.
- **C2 (score_components leak):** `_base_card` (line 96-110) emits `score_components`
  verbatim and ROSTER emits `divergence_score: 0.0` (line 264-268). Per-card-type
  **score_components allowlist** added → §5.
- **C3 (recommended_drop):** WAIVER may carry `recommended_drop` = `_drop_summary` (line
  328-340: `cut_rationale`, `decision_supported`). Typed nested DTO added → §5.
- **C4 (TAXI not model-native):** TAXI evidence (line 436-441) carries
  `model_minus_market_delta` + `score_components.divergence_score` → **moved to the
  market-overlay lane** → §3/§5.
- **G1 (exhaustive token map):** unmapped rationale tokens must **drop or map to a safe
  generic fallback** — never render a raw token string → §5.
- Authorship: Claude Code authors; Codex technical-reviews; Gemini governance-reviews (David-assigned lanes)
- Date: 2026-06-22
- Governance: constitution 1.0.0, north-star 1.0.0, operating-loop 1.0.0, code-hygiene 1.0.0
- Sequence context: David-selected next initiative after W5b shipped. New decision surface (North Star §Decision Surfaces: "League Pulse"). Serves the constitution's "league-opponent trade targeting" decision.

## 1. Authorization & scope

David authorized League Pulse and ruled **Q3=B** (market-derived signals surfaced as a
**clearly-labeled, separated overlay** with the unvalidated-divergence caveat — not
excluded) and confirmed Codex's **Q2 v1 scope**. This spec defines **Increment 1 — the
backend read-only contract ONLY**, mirroring the Roster Audit Inc1 pattern
(`app/api/routes/roster_audit_models.py` + `roster.py`).

**In scope (Inc 1):**
- typed leak-proof DTO models (`app/api/routes/league_pulse_models.py`);
- a fail-closed loader/assembler over the 3 pre-built `*_latest` artifacts;
- the route `GET /api/league/pulse` (`app/api/routes/league_pulse.py`), mounted under `/api`;
- OpenAPI + generated-Zod regen for the new response;
- contract tests.

**Out of scope (hard boundary):** ANY frontend/UI code (Increment 2, gated on David's
scoped frontend-HOLD lift); any rebuild/refresh of the artifacts; any new model math,
scoring, scraper, or live fetch; any Engine A/B / market / training change; any write to the
artifacts. `decision_supported` stays `Literal[False]` recursively.

## 2. Read-only source artifacts (no rebuild)

Read ONLY these pre-built files (all `app/data/valuation/`):
- `team_posture_latest.json` (Phase 18.3 — `market_fields_absent=True`, CLEAN)
- `team_value_matrix_latest.json` (Phase 17.3 — contains `team_value_views.market_overlay_total`, **excluded by allowlist**)
- `league_opportunity_latest.json` (Phase 17.5 — `partner_rankings` + `cards`; market-derived content handled per Q3=B §5)

The surface is **artifact-state, not live-state** (these are dated 2026-05-24). It never
recomputes or refreshes; it maps already-computed values through a leak-proof allowlist.

## 3. Q2 v1 scope (David-locked) — what the response carries

Per Codex's confirmed scope (`perspective_roster_id=1`, David's league view):
1. **Team posture** (from `team_posture_latest.teams`): `roster_id`, owner display/team
   name, `posture.label` (CONTENDER/REBUILDING/ASCENDING/BALANCED/TRANSITIONAL), `score`,
   `components`, `caveats`.
2. **Team value overview** (from `team_value_matrix_latest.teams`): `team_value_views`
   (`starter_weighted_xvar`, `lineup_xvar`, `depth_credit_xvar`, `total_xvar_capped`,
   `top_n_xvar` — **EXCLUDE `market_overlay_total`**), `age_profile`, `positional_summary`
   per QB/RB/WR/TE, `future_picks` **summary only** (owned/outgoing counts + `pick_value_status`).
   **EXCLUDE the raw `players` list** in v1.
3. **Partner rankings** (from `league_opportunity_latest.partner_rankings`):
   `counterparty_roster_id`/name, `partner_score`, `matched_positions`, `score_components`,
   `evidence` (posture labels, `position_scores`, `divergence_row_count`). **Flagged
   market-influenced** (see §5 — `divergence_density_score` is market-derived).
4. **Opportunity cards** — split into two lanes (§5).

## 3a. Mapping discipline — allowlist-FIRST, `extra=forbid` is a backstop (C1)

Every section is built by an **explicit allowlist mapper** that selects known keys into the
typed DTO (the Roster Audit `_SCALARS`-style pattern: `data = {k: raw.get(k) for k in
ALLOWLIST}`). Fields not in a section's allowlist — notably `team_value_views.market_overlay_total`
and the raw `players` list — are **simply not selected**, so a normal valid artifact maps to
**200 with the team populated and the field omitted** (NO drop). `extra="forbid"` on the DTO
is the **fail-closed backstop** that only fires if mapper logic regresses and passes a raw
dict through — a backstop bug guard, not the routine market-field filter. Tests assert both:
(a) normal artifact → field omitted, team NOT dropped; (b) a raw pass-through → DTO rejects.

## 4. Response contract (typed, `extra="forbid"`, `decision_supported` Literal[False])

New module `app/api/routes/league_pulse_models.py`. All DTOs `model_config =
ConfigDict(extra="forbid")`; every model carries `decision_supported: Literal[False] = False`
with a coercion validator (Roster Audit pattern). Envelope:

```
LeaguePulseResponse:
  status: Literal["active", "degraded"]
  perspective_roster_id: int
  source_artifacts: LeaguePulseSources   # per-file schema_version + captured_at
  captured_at: str                        # most-recent / canonical artifact timestamp
  caveats: list[str]
  team_postures: list[LeaguePulseTeamPosture]
  team_values: list[LeaguePulseTeamValue]
  partner_rankings: list[LeaguePulsePartnerRanking]   # market_influenced=True
  model_native_cards: list[LeaguePulseCard]
  market_overlay_cards: list[LeaguePulseMarketCard]   # Q3=B labeled overlay
  dropped: LeaguePulseDropCounts          # per-section isolated-drop counts
  decision_supported: Literal[False]
```

Nested DTOs (`LeaguePulseTeamPosture`, `LeaguePulseTeamValue` with a `LeaguePulseValueViews`
that has **no** `market_overlay_total` field, `LeaguePulsePartnerRanking`, `LeaguePulseCard`,
`LeaguePulseMarketCard`, `LeaguePulseRecommendedDrop`) are explicit allowlist shapes — never
`**raw`. `market_overlay_total` and the raw `players` list are **suppressed by the mapper**
(not selected) so a valid team is NOT dropped (§3a, C1); `extra="forbid"` is the backstop
that rejects a raw pass-through bug.

## 5. Q3=B — labeled market overlay (separation + caveats)

Market-derived content is **included but clearly separated and labeled**, never blended with
model-native, and always caveated as descriptive-not-validated
(`[[feedback_divergence_is_unvalidated]]`).

- **Card lanes — per-card-type allowlist over BOTH `rationale.evidence` AND
  `score_components` (C2):**
  - `model_native_cards` — **`ROSTER_SURPLUS_DEFICIT_MATCH` only** (in the current artifact).
    - evidence allowlist: `position`, `perspective_position_z`, `counterparty_position_z`,
      `perspective_surplus_label`, `counterparty_surplus_label`.
    - score_components allowlist: `fit_score`, `feasibility_score` **only** —
      `divergence_score` is **excluded** (market-named). The mapper asserts the source
      `divergence_score == 0.0` for a model-native card; a **nonzero** `divergence_score`, OR
      any market evidence key (`market_percentile`, `model_minus_market_delta`,
      `model_percentile`), → **fail closed: drop + count** (a model-native card must be
      genuinely market-free). `opportunity_score` is admitted (for ROSTER its divergence term
      is 0, so the published composite is model-native-equivalent).
  - `market_overlay_cards` — **`WAIVER_CANDIDATE`, `DIVERGENCE_MODEL_HIGH`** (current) +
    `DIVERGENCE_MARKET_HIGH`, **`TAXI_ACTIVATION_CANDIDATE`** (C4 — TAXI moved here: its
    evidence carries `model_minus_market_delta` and `score_components.divergence_score`).
    Evidence allowlist admits market keys (`market_percentile`, `model_minus_market_delta`,
    `model_percentile`, `signal`, `signal_status`, `xvar`, `asset_roster_id`, `raw_xvar`,
    `lineup_role`); score_components may include `divergence_score`. Each card carries
    `market_overlay_unvalidated_divergence`; the lane is labeled in the envelope.
- **`WAIVER_CANDIDATE.recommended_drop` typed nested shape (C3):** optional
  `LeaguePulseRecommendedDrop` (`extra="forbid"`) — allowlist: `sleeper_player_id`,
  `full_name`, `position`, `cut_priority`, `ir_compliance_status`,
  `cut_rationale` (list, SAFE_TOKEN-filtered), `decision_supported: Literal[False]` (coerced).
  Unknown nested key or `decision_supported=True` in source → **fail closed** (drop the
  nested block + caveat, never surface a True). When absent in source, the field is `None`.
- **Card-type inventory (verified 2026-06-22):** `WAIVER_CANDIDATE` (17),
  `DIVERGENCE_MODEL_HIGH` (1), `ROSTER_SURPLUS_DEFICIT_MATCH` (2). TAXI / DIVERGENCE_MARKET_HIGH
  absent today (forward-compat). **Any unlisted `card_type` → fail closed: drop + count.**
- **Partner rankings** carry `market_influenced: Literal[True] = True` + caveat
  `partner_score_market_influenced` (`score_components.divergence_density_score` is
  market-derived even with no DIVERGENCE_* card shown — Codex's catch).
- **Token neutralization — EXHAUSTIVE map with safe fallback (G1 + Codex Q7-6):** raw
  rationale tokens (`primary`/`secondary`, e.g. `UNROSTERED_MODEL_MARKET_ASYMMETRY`,
  `FANTASYCALC_PERCENTILE_DIVERGENCE`, `TAXI_LONG_TERM_VALUE_PRESENT`) are rendered ONLY via a
  closed token→neutral-label map. A token **not in the map** is **dropped or mapped to a safe
  generic fallback label** (`opportunity_signal`) — a raw token string is **never** emitted.
  Raw tokens carrying a banned word (`buy`/`sell`/`target`/`fade`) are never rendered verbatim.
  A word-boundary banned-language scan over ALL emitted display strings is a contract test.

## 6. Fail-closed contract (mirror Roster Audit + League-Pulse extras)

- **Artifact-level (Codex Q7-1):** each of the 3 files must load + parse + match its
  expected `schema_version`; a missing / unreadable / schema-wrong required artifact →
  `LeaguePulseDependencyError` → **503**. Never fabricate.
- **Cross-artifact join integrity (Codex Q7-2):** posture, value, and ranking records must
  reference known `roster_id`s from a single canonical roster set; an unresolvable
  cross-reference drops that record (counted), and total join failure → 503.
- **Isolated drops → degraded-200:** a single unmappable team/card/ranking is dropped +
  counted in `dropped` with a caveat; `status="degraded"`. All-rows-unmappable in a required
  section → 503 (no silent empty success).
- **Staleness = graceful-degrade (David/Gemini ruling):** surface `captured_at` +
  `source_artifacts` and a descriptive caveat (`league_pulse_artifact_state_<date>`) — do
  **NOT** 503 purely because the artifact is old. No staleness threshold in v1.
- **SAFE_TOKENS allowlist (Codex Q7-5):** League-Pulse token set
  (`phase17_non_decision_grade`, `future_pick_values_deferred`, `posture_unclassified`,
  `phase18_heuristic_posture`, `market_overlay_unvalidated_divergence`,
  `waiver_status_from_sleeper_snapshot`, `partner_score_market_influenced`, …) via a
  `validate_tokens` that keeps only SAFE_TOKENS and drops the rest with an
  `evidence_suppressed_banned_term` caveat.
- **Recursive `decision_supported=False`** asserted over every nested DTO.

## 7. Route + wiring

`app/api/routes/league_pulse.py`: `GET /api/league/pulse` (`router = APIRouter(prefix=
"/league")`, mounted in `app/main.py` under `/api`), `response_model=LeaguePulseResponse`.
Monkeypatchable loader seams (`_load_team_posture`, `_load_team_value_matrix`,
`_load_league_opportunity`) for tests. 503 on `LeaguePulseDependencyError`; 200
active/degraded otherwise. Regenerate `openapi.json` + `frontend/src/lib/api/zod.gen.ts`
(`zLeaguePulseResponse`) — the only frontend artifact touched in Inc 1 (generated client, no
UI code).

## 8. Governance items (for Gemini)

1. Confirm Q3=B separation is honest: market content lives only in `market_overlay_cards` +
   the flagged `partner_rankings`, each caveated unvalidated; model-native sections carry no
   market keys (fail-closed).
2. Confirm token→neutral-label mapping + banned-language scan keep the surface descriptive
   (no buy/sell/target/fade; no decision-grade instruction).
3. Confirm `decision_supported=False` recursive + `market_overlay_total`/raw-players
   exclusion satisfy the North Star market-overlay-isolation + banned-field rules.

## 9. Open items for CLEAR

- **Staleness wording** — exact caveat string + whether to also emit a per-artifact age.
- **TAXI_ACTIVATION_CANDIDATE** — RESOLVED (C4): classified market-overlay (producer emits
  market fields); no longer open.
- **`future_picks` summary shape** — counts + `pick_value_status` only vs a small per-round
  rollup.
- **OpenAPI/Zod regen mechanics** — confirm the generation command + that no other client
  surface drifts.

## 10. Acceptance criteria & falsification matrix

AC: typed `extra=forbid` DTOs; allowlist mappers exclude `market_overlay_total` + raw players
by construction; per-card-type evidence allowlists; model-native lane rejects market keys
(fail-closed); market-overlay lane + partner_rankings carry the unvalidated caveat + labels;
banned tokens neutralized; recursive `decision_supported=False`; 503 on
missing/malformed/schema-wrong/all-unmappable; degraded-200 on isolated drops;
graceful-degrade (not 503) on stale artifact; no UI code; OpenAPI/Zod regen only.

Falsification matrix (each → a RED test):
- **valid-nominal**: all 3 artifacts present → 200 active; sections populated; counts correct.
- **market suppression NOT drop (C1)**: a normal team WITH `market_overlay_total` →
  **200, team present, field omitted, NOT dropped**; AND a raw-dict pass-through bug → DTO
  `extra=forbid` rejects (backstop). Raw `players` list in source → absent in response.
- **model-native lane purity — evidence AND score_components (C2)**: a
  `ROSTER_SURPLUS_DEFICIT_MATCH` card with `market_percentile` in evidence OR a **nonzero**
  `score_components.divergence_score` → dropped + counted; a nominal ROSTER card
  (`divergence_score==0.0`) → surfaced with `divergence_score` **omitted** from the response.
- **TAXI is market-overlay (C4)**: a `TAXI_ACTIVATION_CANDIDATE` (with
  `model_minus_market_delta`/`divergence_score`) → lands in `market_overlay_cards`, never
  `model_native_cards`.
- **recommended_drop typed (C3)**: a `WAIVER_CANDIDATE` with `recommended_drop` → typed
  nested block, `decision_supported` forced False, `cut_rationale` SAFE_TOKEN-filtered;
  a nested `decision_supported=True` or unknown nested key → fail closed (block dropped +
  caveat).
- **exhaustive token map (G1)**: an unmapped rationale token → safe fallback label
  (`opportunity_signal`) or dropped, never the raw string; a token containing `target` →
  neutralized; word-boundary scan over ALL display strings → clean.
- **market-overlay labeling**: a `DIVERGENCE_MODEL_HIGH`/`WAIVER_CANDIDATE` card → lands in
  `market_overlay_cards` with `market_overlay_unvalidated_divergence` caveat.
- **unknown card_type**: a card with an unlisted `card_type` → dropped + counted (fail-closed,
  never surfaced).
- **partner-rankings flag**: every partner ranking → `market_influenced=True` +
  `partner_score_market_influenced` caveat.
- **banned-token neutralization**: a rationale token containing `target` → mapped to neutral
  label; word-boundary scan over all display strings → clean.
- **missing artifact** (each of the 3) → 503.
- **schema-version mismatch** (each) → 503.
- **malformed/corrupt artifact** (non-JSON / wrong root type) → 503.
- **cross-artifact join failure**: a ranking referencing an unknown `roster_id` → dropped +
  counted; total join failure → 503.
- **isolated drop**: one unmappable team → degraded-200 + drop count + caveat; all teams
  unmappable → 503.
- **staleness**: an old `captured_at` → 200 with `league_pulse_artifact_state_<date>` caveat,
  NOT 503.
- **decision_supported**: a source record with `decision_supported=True` → coerced/forced
  False (or dropped); recursive scan → no True survives.
- **SAFE_TOKENS**: an unknown/banned caveat token in source → dropped with
  `evidence_suppressed_banned_term`.

## 11. Build sequence (post-approval only)

spec dual-CLEAR (Codex technical + Gemini governance) → David approves → Codex RED → Claude
GREEN → dual-CLEAR per task → David-authorized commit → zero-divergence audit →
close-the-loop. No RED before dual-CLEAR + David approval. Likely task cut: T1 DTO models +
SAFE_TOKENS + token→label map; T2 allowlist mappers (per-section + per-card-type) + fail-closed
assembler; T3 route + loader seams + OpenAPI/Zod regen; each Codex-RED → Claude-GREEN.
Increment 2 (read-only UI) is a SEPARATE spec, gated on David's scoped frontend-HOLD lift.
