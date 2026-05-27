---
title: SF-QB Calibration Corpus Expansion (Increment 2) — Design Spec
status: APPROVED design (David, 2026-05-27) — reviewed by Codex (5 must-fixes folded in) + Gemini (governance CONFIRMED)
date: 2026-05-27
author: Claude Code (brainstormed with David; design-reviewed by Codex + Gemini)
parent: docs/superpowers/specs/2026-05-26-sf-qb-knob-calibration-design.md (original calibration); Follow-up B convergence in docs/agent-ledger/2026-05-27.md
governance_hold: Frontend remains on the Phase 12 HOLD; backend only. NOISE_BAND lock untouched.
---

# SF-QB Calibration Corpus Expansion (Increment 2)

## 0. What we're building

The SF-QB knob calibration (`scripts/calibrate_sf_qb_knob.py`) currently draws its corpus from
David's own league chain (`previous_league_id`) plus a small seed fixture — ~6 real SF rookie drafts,
which produced the honest but thin **K = 0** (median promotion 0.0). This increment lets the same
script ingest **curated bring-your-own (BYO) Sleeper rookie-draft IDs**, each **hard-gated** as a
genuine **Superflex + 12-team + completed rookie** draft, so the corpus can be thickened with
additional real SF rookie drafts beyond David's league.

It **extends the existing script and board path** — no new module, no market-source abstraction. The
output stays the recommended-K artifact. **Setting `sf_qb_promote_slots = K` and regenerating the
pick-value curve remain gated on David's explicit approval in a later session — NOT in this increment.**

## 1. Scope & non-goals

**In scope:**
- `resources/sf_rookie_draft_ids.json` — curated BYO Sleeper draft-ID list.
- New pure gate helpers + a monkeypatchable BYO fetch seam in `scripts/calibrate_sf_qb_knob.py`.
- `main()` integration (chain + seed + BYO) and additive artifact provenance (`format_meta`, `rejected`).
- Unit tests on the gate helpers and the accept/reject paths.

**Non-goals (do NOT do these):**
- **No K application / no curve regeneration / no `draft_pick_value_curve_v1.json` change.** The deliverable is the calibration script + recommended-K artifact only.
- **MFL aggregate ADP remains explicitly barred from calibration** (1QB/TEP blend would bias the QB axis).
- No new market-source abstraction; no Engine A/B training input; no model pkl/manifest/contract change.
- No frontend change (Phase 12 HOLD); no NOISE_BAND change.

## 2. Input contract — curated BYO draft-ID file

`resources/sf_rookie_draft_ids.json`:
```json
{ "note": "Curated real SF (12-team) rookie draft IDs for SF-QB knob calibration corpus.",
  "draft_ids": ["1234567890", "0987654321"] }
```
- A missing file **or** empty `draft_ids` → the script behaves exactly as today (chain + seed only). **Backward-compatible no-op.**
- `draft_ids` are **de-duplicated, order-preserving** (Codex must-fix #4) before fetch; a dropped duplicate is recorded as `duplicate_draft_id` in skipped provenance. Each remaining ID is fetched and gated.

## 3. The gate (the heart of this increment)

For a BYO `draft_id`: `get_draft(draft_id)` → `get_league(draft["league_id"])` → gate (§3.1) → build the
board from `get_draft_picks(draft_id)` (§3.2). All Sleeper reads are **read-only** and behind the
monkeypatchable seam (§4). Every BYO id ends as an accepted board **or** a recorded rejection — never a
silent drop.

### 3.1 Draft+league gate helpers (pure, unit-tested)
`gate_byo_draft(draft, league)` evaluates **only draft- and league-level** properties — it has **no picks
argument**, so pick-level checks (`malformed_picks`, the cap) live in §3.2 (Codex final-pass #4).
- `is_superflex(league) -> bool`: `"SUPER_FLEX" in (league.get("roster_positions") or [])`. **Exact token** — never fuzzy text from draft metadata.
- `is_twelve_team(league) -> bool`: `int(league.get("total_rosters")) == 12`. **Coerce defensively**; non-int/missing → False.
- `league_format_metadata(league) -> dict`: `{superflex, total_rosters, ppr, te_premium}` where
  `ppr = (league.get("scoring_settings") or {}).get("rec")` and
  `te_premium = ((league.get("scoring_settings") or {}).get("bonus_rec_te") or 0) > 0`.
  **Field name is `scoring_settings`, not `scoring`.** Metadata/caveat only — never a gate.
- `gate_byo_draft(draft, league) -> (accepted: bool, reason: str | None, format_meta: dict)`:
  - **Rookie gate (defensive — Codex final-pass #6):** require `status == "complete"` AND `rounds ≤ 6`. Parse `settings.rounds` defensively: a missing/non-integer `rounds` → reject `malformed_draft_settings` rather than letting `int(rounds)` raise. (`is_rookie_draft` stays unchanged for the chain; the BYO gate guards the coercion, treating a non-int as `malformed_draft_settings` and an int > 6 / non-complete as `not_rookie`.)
  - **Superflex + 12-team:** `is_superflex(league)` AND `is_twelve_team(league)`.
  - **Draft type:** reject `draft.get("type") == "auction"` → `unsupported_draft_type` (snake/linear keep meaningful overall `pick_no`; do **not** require `type == "linear"`).
  - **Reasons from this helper:** `not_rookie`, `malformed_draft_settings`, `not_superflex`, `not_12_team`, `unsupported_draft_type`. `format_meta` recorded whenever the league was fetched.

### 3.2 Board construction + first-36 cap (separate from the gate)
`_build_byo_board(draft_id, draft, league, picks)` runs only for drafts that passed §3.1, and owns the
pick-level concerns (Codex final-pass #1, #2, #4, #5-class):
1. **draft_class (fail-closed — Codex final-pass #2):** `draft_class = int(draft.get("season") or league.get("season"))`. Missing/non-integer → reject `invalid_draft_class` (never let `int(...)` abort the run).
2. **malformed picks (whole-draft, fail-closed):** if **any** pick has a missing/non-integer `pick_no`, reject the whole draft `malformed_picks` (don't partially include).
3. **first-36 cap (Codex final-pass #1):** sort picks by integer `pick_no` ascending; keep only `ff_slot = pick_no <= _BOARD_SIZE (36)`. QBs after pick 36 are **invisible to `qb_promotions` — neither matched nor unmatched.**
4. **cap provenance (Codex final-pass #5):** the board carries `n_picks_raw`, `n_picks_used`, `n_picks_excluded_after_36` so the artifact explains why a pick-40 QB is uncounted.

### 3.3 Fail-closed fetch
Missing `draft["league_id"]` → reject `missing_league_id`. Any `get_draft` / `get_league` /
`get_draft_picks` exception → reject `fetch_failed`.

### 3.4 Cross-source de-duplication + rank-map availability
- **BYO id already in David's chain (Codex final-pass #3):** chain boards and BYO boards both carry a non-breaking `draft_id`. A BYO id already collected via the `previous_league_id` chain is skipped with reason `duplicate_existing_draft` (prevents double-counting the same draft). De-dup *within* the BYO file (`duplicate_draft_id`, §2) is separate from this *cross-source* check.
- **Rank-map availability (Codex final-pass #1-data):** a board whose `draft_class` has **no NFL skill-rank map** — a future class like 2027, a class outside `prospects_with_outcomes.csv` / `prospect_cards.json` coverage, or `nfl_skill_ranks(class)` returning empty — is rejected `rank_map_unavailable` and **excluded from `boards`, `per_draft`, `n_drafts`, matched/unmatched, `promotions`, and the K math**, so a data-coverage miss never masquerades as a name-match miss that inflates the unmatched denominator. This check runs in `main()` once `rank_maps` are built (it applies to any board; chain/seed classes are known-covered).

## 4. Components & data flow

- `_load_byo_draft_ids() -> (ids, duplicate_ids)`: read `resources/sf_rookie_draft_ids.json`; missing/empty → `([], [])`; de-dupe order-preserving; return unique ids + the dropped within-file duplicates (recorded `duplicate_draft_id`).
- `gate_byo_draft` / `_build_byo_board` per §3.1–3.2.
- `async _collect_byo_boards(draft_ids, chain_draft_ids) -> (boards, rejections)`: per id — skip if in `chain_draft_ids` → `duplicate_existing_draft`; else fetch draft + league (fail-closed §3.3), `gate_byo_draft` (§3.1), then `_build_byo_board` (§3.2). Accept → `{draft_class, draft_id, source: f"sleeper_draft:{id}", format_meta, n_picks_raw, n_picks_used, n_picks_excluded_after_36, picks: [{ff_slot, player_name, position}]}`. Reject → `{draft_id, reason, format_meta?}`.
- `_fetch_byo_drafts(draft_ids, chain_draft_ids) -> (boards, rejections)`: **monkeypatchable seam** wrapping `asyncio.run(_collect_byo_boards(...))` — mirrors `_fetch_league_rookie_drafts`; tests inject without network.
- Chain boards gain a **non-breaking `draft_id`** field (from `d["draft_id"]`) so cross-source de-dup (§3.4) and provenance work.
- `main()`: collect chain + seed; build `chain_draft_ids`; collect BYO (passing `chain_draft_ids`); `boards = chain + seed + byo`; build `rank_maps = {class: nfl_skill_ranks(class)}`; **move any `rank_map_unavailable` board to `rejected`** (§3.4); then `qb_promotions` + `recommend_k` on the surviving boards. **The promotion/K math is unchanged** — only the corpus grows.

## 5. Artifact (additive, transparency-preserving)

Same shape as today, plus:
- Each BYO board's `per_draft` entry carries its `format_meta` (`superflex`, `total_rosters`, `ppr`, `te_premium`) and the cap provenance `n_picks_raw` / `n_picks_used` / `n_picks_excluded_after_36`.
- A new top-level **`rejected`** list: `[{draft_id, reason, format_meta?}]` covering every gated-out, duplicate, invalid-class, or rank-map-unavailable id. **Full reason set:** `not_rookie`, `malformed_draft_settings`, `not_superflex`, `not_12_team`, `unsupported_draft_type`, `malformed_picks`, `invalid_draft_class`, `missing_league_id`, `fetch_failed`, `duplicate_draft_id`, `duplicate_existing_draft`, `rank_map_unavailable`. **Never silently dropped.**
- The `n_qbs_matched == sum(per_draft matched)` invariant holds because `per_draft` uses the **capped** boards and **excludes** rank-map-unavailable boards — capped/excluded picks are neither matched nor unmatched.
- `sf_qb_calibration_thin_sample` caveat stays until the corpus is genuinely larger (a count threshold is out of scope for v1; the caveat remains).

## 6. Governance

- **Read-only Sleeper** (public API, no auth, no Databricks); no writes to any league.
- **No market/ADP into calibration** — consumes draft results (manager behavior) + NFL draft capital only, to set a curve-ordering knob, never an Engine A/B feature. **MFL aggregate stays barred.**
- **Diagnostic-only:** producing a new `sf_qb_knob_calibration_*.json` does NOT mutate `sf_qb_promote_slots` or regenerate the curve. K application + regen are gated on David's explicit, recorded approval in a later session.
- No banned David-facing verdict language; `decision_supported` semantics unaffected (no pick output changes here); frontend HOLD + NOISE_BAND lock untouched; no model pkl/manifest/contract change.

## 7. Testing / contract intent

Pure helpers + accept/reject paths, on fixtures via the monkeypatchable seam (no network):
- `is_superflex`: SUPER_FLEX present → True; QB-only / missing roster_positions → False.
- `is_twelve_team`: `total_rosters` 12 → True; 10 / "12" coercion / missing → correct (int-coerced; missing → False).
- `league_format_metadata`: reads `scoring_settings.rec` and `scoring_settings.bonus_rec_te > 0`; absent scoring → `ppr=None`, `te_premium=False`.
- `gate_byo_draft` (draft+league only): accepts SF+12T+complete-rookie; rejects with the exact reason for each of not_rookie / **malformed_draft_settings (non-int `settings.rounds`)** / not_superflex / not_12_team / unsupported_draft_type(auction). (It does **not** emit `malformed_picks` — no picks argument.)
- `_build_byo_board`: **invalid_draft_class** (missing/non-int `draft.season` and `league.season`); **malformed_picks** (any non-int `pick_no` → whole-draft reject); **first-36 cap** — a 6-round (72-pick) 12-team SF rookie board keeps only `pick_no <= 36`, a QB at pick 40 is excluded and counted **neither matched nor unmatched**, and `n_picks_raw/n_picks_used/n_picks_excluded_after_36` are set correctly; picks sorted by `pick_no`.
- **Within-file de-dupe:** a `draft_ids` list with a repeat fetches once; the duplicate appears in `rejected` as `duplicate_draft_id`.
- **Cross-source de-dupe:** a BYO id already present in `chain_draft_ids` is skipped with `duplicate_existing_draft` and not double-counted.
- **Rank-map availability:** a BYO board with `draft_class` 2027 (or any class with an empty `nfl_skill_ranks`) is rejected `rank_map_unavailable` and excluded from `n_drafts`/matched/unmatched/promotions; it does NOT inflate the unmatched count.
- **Fail-closed:** monkeypatched fetch raising → `fetch_failed`; draft missing `league_id` → `missing_league_id`; neither aborts the run.
- **Backward-compat:** missing/empty `resources/sf_rookie_draft_ids.json` → identical behavior to today (chain + seed only); BYO additions don't change the chain/seed contributions.
- **`main()` artifact:** includes `rejected` (with the §5 reason set) and per-draft `format_meta` + cap-provenance for BYO; aggregate `n_qbs_matched` still equals the sum across `per_draft` after capping + rank-map exclusion.

## 8. Counter-argument (Rule 5 — mandatory)

1. **Wider corpus invites format contamination.** Mitigation: the SF + 12-team hard gate is exactly the axis that biases QB promotion (1QB drafts) and the slot scale (team count); the first-36 cap protects the 1..36 metric; PPR/TEP are recorded, not gated, because they have only second-order effects on QB draft *position*. Every inclusion is auditable via `format_meta`.
2. **BYO drafts are someone else's leagues — quality varies.** Mitigation: curated, version-controlled, reviewable IDs (not arbitrary scraping); fail-closed rejection with reasons; read-only; and the K result remains diagnostic, gated on David's approval before it can move the curve.
3. **A bigger corpus could shift K off 0 and tempt premature curve change.** Mitigation: this increment cannot apply K — it only reports it. Any change to `sf_qb_promote_slots` is a separate, explicitly-approved step, with the thin-sample caveat persisting until the corpus is genuinely robust.
