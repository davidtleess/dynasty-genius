---
title: SF-QB Ordering-Knob Calibration — Design Spec
status: APPROVED design (David, 2026-05-26) — full scope (league-chain + seed + NFL join)
date: 2026-05-26
author: Claude Code (brainstormed with David)
parent: docs/superpowers/specs/2026-05-26-draft-pick-valuation-design.md (Phase 24; SF-QB knob deferred-calibration follow-up)
governance_hold: Frontend remains on the Phase 12 HOLD; backend only.
---

# SF-QB Ordering-Knob Calibration

## 0. What we're building

The Phase 24 pick-value curve assumes "FF rookie-draft order ≈ NFL skill-position order."
That's weakest for **QBs in Superflex**, where managers draft QBs earlier than their NFL skill
rank. `apply_sf_qb_ordering(board, k_slots, round_threshold_pick)` already exists to promote QBs
by `k_slots` before slot aggregation, but it's **off** (`sf_qb_promote_slots=0`) — uncalibrated.

This builds a **calibration script** that measures, across real SF rookie drafts, how many slots
earlier QBs actually went vs their NFL-skill rank, and recommends a single global `K`. On David's
approval of the computed K, we set `sf_qb_promote_slots=K` and regenerate the curve.

## 1. Metric (David-approved)

Per QB drafted in a real SF rookie draft:
`promotion = nfl_skill_rank − ff_slot` (positive = drafted earlier than NFL-skill order), where
**`ff_slot` is the overall 1-based pick number (1..36)** and `nfl_skill_rank` is the 1-based
position in the class's first-36 NFL-skill order — both on the same 1..36 scale.
`K = clamp(round_half_up(median(promotions across the whole corpus)), 0, 3)`, where
**`round_half_up(m) = math.floor(m + 0.5)`** — NOT Python's built-in `round()`, whose banker's
rounding would map `0.5 → 0` and `2.5 → 2` (plausible with this thin, even-sized matched-QB
sample and `.5` medians — Codex MEDIUM). **median** (robust to a single outlier in a small
sample), **global** (one K for all qualifying QBs), clamped to [0, 3]; **empty promotions → K=0
+ caveat**. `round_threshold_pick` stays at its permissive default (all QBs qualify) for v1.

## 2. Calibration corpus (David-approved: league-chain + seed)

- **David's league rookie drafts (live Sleeper, read-only):** from `league_id 1314363401744416768`,
  chain `previous_league_id` (→ `1183088915091423232` → …), collect each season's drafts, filter to
  **rookie drafts** (`settings.rounds ≤ 6` excludes the inaugural startup) that are also
  **`status == "complete"`** (skip partially-drafted/in-progress and low-round supplemental drafts),
  pull picks → `(ff_slot, player, position)` from pick metadata. **Each emitted board carries an
  explicit `draft_class` from `draft.season` (fallback `league.season`)** so it joins to the correct
  NFL-skill-rank map (Codex LOW). `settings.rounds`/`type` are the gate; name/metadata are recorded
  as evidence only.
- **Seed drafts:** the ~3 usable real SF rookie drafts from `docs/strategies/Rookie Draft Seed Data.md`
  (2022 Draft A, 2024 Draft B, 2025 Draft F) transcribed once into `resources/seed_rookie_drafts.json`
  (`{class, slot, player_name, position}` rows). Best-ball / TEP / non-strict drafts excluded.

Realistic corpus ≈ 5 boards → **thin**; the artifact + curve provenance carry a thin-sample caveat.

## 3. NFL-skill-rank resolver

Per draft class, the **NFL-skill order** = the first-36 QB/RB/WR/TE by NFL draft pick; each player's
`nfl_skill_rank` = its 1-based position in that order.
- **2026:** from `resources/prospect_cards.json` (`nfl_draft_pick` + `position`).
- **2022–2025:** from `app/data/training/prospects_with_outcomes.csv` (`season`, `pick`, `position`,
  `pfr_player_name`).
QBs in each draft are matched to the NFL data **by normalized name** (lowercase, strip punctuation/
suffixes). Unmatched QBs are **excluded** and counted in the artifact (never guessed).

## 4. Components / data flow

- `scripts/calibrate_sf_qb_knob.py`:
  1. `_fetch_league_rookie_drafts()` — Sleeper chain + rookie-draft filter → list of draft boards.
     Wrapped behind a **monkeypatchable seam** so tests inject boards without live calls.
  2. `_load_seed_drafts()` — read `resources/seed_rookie_drafts.json`.
  3. `_nfl_skill_ranks(draft_class)` — build the rank map from prospect_cards / outcomes CSV.
  4. `_qb_promotions(boards, rank_maps)` — pure function: list of per-QB promotions (+ unmatched count).
  5. `_recommend_k(promotions)` — pure: `clamp(round_half_up(median), 0, 3)` (half-up per §1, NOT
     banker's `round`; empty → 0).
  6. Write artifact `app/data/backtest/phase24/sf_qb_knob_calibration_<ts>.json`:
     `{n_drafts, n_qbs_matched, n_qbs_unmatched, per_draft: [...], promotions, median_raw,
     recommended_k, caveats: ["sf_qb_calibration_thin_sample", ...]}` and print the recommendation.

Pure helpers (4–5) are unit-tested on fixtures; the live fetch is integration behind the seam.

## 5. Apply (gated on David's approval of K)

After David approves the computed K: set `_SF_QB_PROMOTE_SLOTS = K` in
`scripts/build_draft_pick_value_curve.py`, regenerate `draft_pick_value_curve_v1.json`, and add an
`sf_qb_calibration` provenance block (K, n_drafts, median, thin-sample caveat) to the artifact's
`source`. **This curve-regen step is NOT in the v1 PR** unless K turns out > 0 and David approves it
in the same pass — the v1 deliverable is the calibration script + artifact + recommended K.

## 6. Governance

- **Read-only Sleeper** (public API, no auth, no Databricks); no writes to the league.
- **No market/ADP/analyst data into Engine A/B training** — calibration consumes draft results +
  NFL draft capital only; it does not touch model training. (The SF rookie-draft data is *manager
  behavior*, used only to set a curve-ordering knob, not a model feature.)
- Curve values stay `decision_supported=False`; pick caveats already cover `sf_qb_ordering_assumption`
  when the knob is active; add `sf_qb_calibration_thin_sample`.
- No Engine A/B pkl/manifest/contract change; frontend HOLD intact.

## 7. v1 scope

**In:** `calibrate_sf_qb_knob.py` (fetch seam + seed loader + NFL-rank resolver + pure promotion/K
helpers + artifact); `resources/seed_rookie_drafts.json` (curated); unit tests on the pure helpers;
the recommended-K artifact.
**Gated/next:** setting `_SF_QB_PROMOTE_SLOTS=K` + curve regen (only after David approves the
computed K).
**Out (deferred):** per-round K; broader corpus / ADP; auto-recalibration scheduling.

## 8. Contract / unit-test intent

- `_qb_promotions`: given boards + rank maps, returns correct per-QB `nfl_skill_rank − ff_slot`;
  unmatched QBs excluded + counted; non-QB picks ignored.
- `_recommend_k`: `clamp(round_half_up(median), 0, 3)` — incl. **tie cases `median 0.5 → 1` and
  `2.5 → 3`** (half-up, not banker's), a negative-median case → 0, a large-median case → 3, and an
  empty-promotions case → 0 (+ caveat).
- Rookie-draft filter: `rounds ≤ 6` **and `status == "complete"`** selected; a 15-round startup
  excluded; an in-progress (`status != complete`) draft excluded; emitted board carries the correct
  `draft_class` from `draft.season`.
- Name normalization matches across `Jr.`/punctuation/case; a genuinely-absent QB → unmatched.
- Live fetch behind a monkeypatchable seam (tests inject boards; no network in unit tests).
- Artifact shape: required keys + thin-sample caveat present.

## 9. Counter-argument (Rule 5 — mandatory)

1. **~5 drafts is too thin for a stable median.** A different K could be justified with more data.
   Mitigation: clamp to [0,3], median (not mean), explicit `sf_qb_calibration_thin_sample` caveat,
   and the knob is re-runnable as the league accrues drafts. K may well be 0 or 1 — which is a
   legitimate, honest result, not a failure.
2. **"FF order = NFL skill order" baseline is itself approximate** (landing spot, age, dynasty
   profile reshuffle non-QBs too). The knob only corrects the QB axis, the largest known SF
   distortion; other reshuffles remain folded into the historical curve. Disclosed.
3. **Name-matching across sources is fuzzy.** Mitigation: QB-only (few, distinctive names),
   normalize, and **exclude + count** unmatched rather than guess; the artifact surfaces the match
   rate so a low rate is visible.
