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

For a BYO `draft_id`: `get_draft(draft_id)` → `get_league(draft["league_id"])` → evaluate. All Sleeper
reads are **read-only** and behind the monkeypatchable seam (§4).

### 3.1 Pure gate helpers (unit-tested)
- `is_superflex(league) -> bool`: `"SUPER_FLEX" in (league.get("roster_positions") or [])`. **Exact token** — never fuzzy text from draft metadata (Codex).
- `is_twelve_team(league) -> bool`: `int(league.get("total_rosters")) == 12`. **Coerce defensively**; non-int/missing → False (Codex).
- `league_format_metadata(league) -> dict`: `{superflex, total_rosters, ppr, te_premium}` where
  `ppr = (league.get("scoring_settings") or {}).get("rec")` and
  `te_premium = ((league.get("scoring_settings") or {}).get("bonus_rec_te") or 0) > 0`.
  **Field name is `scoring_settings`, not `scoring`** (Codex must-fix #3). Metadata/caveat only — never a gate.
- `gate_byo_draft(draft, league) -> (accepted: bool, reason: str | None, format_meta: dict)`:
  - **Hard gate (all required):** `is_rookie_draft(draft)` (status == "complete" AND rounds ≤ 6) AND `is_superflex(league)` AND `is_twelve_team(league)`.
  - **Draft-type/shape gate (Codex must-fix #2):** reject `draft.get("type") == "auction"` → reason `unsupported_draft_type`. (Snake/linear both keep meaningful overall `pick_no`; do **not** require `type == "linear"`.)
  - **Reject reasons:** `not_rookie`, `not_superflex`, `not_12_team`, `unsupported_draft_type`, `malformed_picks`, `missing_league_id`, `fetch_failed`. `format_meta` is recorded for accepted AND rejected drafts where the league was fetched.

### 3.2 First-36 cap on board picks (Codex must-fix #1)
Rank maps and the curve are **first-36-skill-player** logic. A 4–6 round rookie draft can have
`pick_no > 36`. So when building a BYO board:
1. Drop any pick with missing/non-integer `pick_no` → if **any** are malformed, reject the whole draft with `malformed_picks` (don't partially include — Codex must-fix #2).
2. Sort picks by integer `pick_no` ascending.
3. Keep only picks with `ff_slot = pick_no <= _BOARD_SIZE (36)`.

This prevents late-round QBs from injecting large negative promotions that would bias K.

### 3.3 Fail-closed fetch (Codex must-fix #5)
Missing `draft["league_id"]` → reject `missing_league_id`. Any `get_draft`/`get_league` exception →
reject `fetch_failed`. **Never a silent drop** — every BYO id ends up either an accepted board or a
recorded rejection.

## 4. Components & data flow

- `_load_byo_draft_ids() -> list[str]`: read `resources/sf_rookie_draft_ids.json`; missing/empty → `[]`; de-dupe order-preserving; return ids (and the dropped duplicates for provenance).
- `async _collect_byo_boards(draft_ids) -> (boards, rejections)`: per id, fetch draft + league, `gate_byo_draft`, and on accept build a board: `{draft_class: int(draft["season"]), source: f"sleeper_draft:{id}", format_meta, picks: [{ff_slot, player_name, position}]}` (first-36-capped per §3.2). On reject, append `{draft_id, reason, format_meta?}`.
- `_fetch_byo_drafts(draft_ids) -> (boards, rejections)`: **monkeypatchable seam** wrapping `asyncio.run(_collect_byo_boards(...))` — mirrors `_fetch_league_rookie_drafts`; tests inject boards/rejections without network.
- `main()`: `boards = chain_boards + seed_drafts + byo_boards`; `rank_maps = {class: nfl_skill_ranks(class)}`; `qb_promotions`; `recommend_k`. **The promotion/K math is unchanged** — only the corpus grows.

## 5. Artifact (additive, transparency-preserving)

Same shape as today, plus:
- Each BYO board's `per_draft` entry carries its `format_meta` (`superflex`, `total_rosters`, `ppr`, `te_premium`).
- A new top-level **`rejected`** list: `[{draft_id, reason, format_meta?}]` — every gated-out or duplicate BYO id, with reason. Never silently dropped.
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
- `gate_byo_draft`: accepts SF+12T+complete-rookie; rejects with the exact reason for each of not_rookie / not_superflex / not_12_team / unsupported_draft_type(auction) / malformed_picks(non-int pick_no) / missing_league_id.
- **First-36 cap:** a 6-round (72-pick) 12-team SF rookie board keeps only `pick_no <= 36`; a QB at pick 40 is excluded; picks are sorted by `pick_no`.
- **De-dupe:** a `draft_ids` list with a repeat fetches once; the duplicate appears in `rejected`/skipped as `duplicate_draft_id`.
- **Fail-closed:** monkeypatched fetch raising → `fetch_failed` rejection; draft missing `league_id` → `missing_league_id`; neither aborts the run.
- **Backward-compat:** missing/empty `resources/sf_rookie_draft_ids.json` → identical behavior to today (chain + seed only); BYO additions don't change the chain/seed contributions.
- **`main()` artifact:** includes `rejected` and per-draft `format_meta` for BYO; aggregate `n_qbs_matched` still equals the sum across `per_draft` (existing consistency invariant holds with the larger corpus).

## 8. Counter-argument (Rule 5 — mandatory)

1. **Wider corpus invites format contamination.** Mitigation: the SF + 12-team hard gate is exactly the axis that biases QB promotion (1QB drafts) and the slot scale (team count); the first-36 cap protects the 1..36 metric; PPR/TEP are recorded, not gated, because they have only second-order effects on QB draft *position*. Every inclusion is auditable via `format_meta`.
2. **BYO drafts are someone else's leagues — quality varies.** Mitigation: curated, version-controlled, reviewable IDs (not arbitrary scraping); fail-closed rejection with reasons; read-only; and the K result remains diagnostic, gated on David's approval before it can move the curve.
3. **A bigger corpus could shift K off 0 and tempt premature curve change.** Mitigation: this increment cannot apply K — it only reports it. Any change to `sf_qb_promote_slots` is a separate, explicitly-approved step, with the thin-sample caveat persisting until the corpus is genuinely robust.
