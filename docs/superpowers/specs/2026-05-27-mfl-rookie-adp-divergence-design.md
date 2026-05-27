---
title: MFL Rookie ADP Divergence Report (Follow-up B, Increment B) — Design Spec
status: APPROVED design (David, 2026-05-27) — reviewed by Codex (6 clarifications folded in) + Gemini (governance CLEAR)
date: 2026-05-27
author: Claude Code (brainstormed with David; design-reviewed by Codex + Gemini)
parent: docs/superpowers/specs/2026-05-27-mfl-rookie-adp-overlay-design.md (Increment 1 adapter); Follow-up B convergence in docs/agent-ledger/2026-05-27.md
governance_hold: Frontend remains on the Phase 12 HOLD; backend only. NOISE_BAND lock untouched.
---

# MFL Rookie ADP Divergence Report — Increment B

## 0. What we're building

A **standalone, read-only backend report** that turns the merged-but-dormant `MflAdpMarketSource`
(Increment 1) into a live, inspectable signal: where does the real-draft rookie market (MFL rookie
ADP) **disagree** with our model's rookie ranking (`xvar_class_rank` on `prospect_cards.json`)?

It mirrors the existing FantasyCalc `universe_market_divergence.py` report pattern — read model output
+ market data, write a **separate** divergence artifact — but **rookie-scoped** and **artifact-only**.
It **never** mutates `prospect_cards.json`, PVO, team-matrix, or trade artifacts, and adds no API
endpoint or frontend.

## 1. Scope & non-goals

**In scope:**
- New `src/dynasty_genius/mfl_rookie_adp_divergence.py` — pure builder + coverage + artifact writer (mirrors `universe_market_divergence.py`).
- New narrow adapter helper `fetch_rookie_adp_rows(season)` in `mfl_adp_adapter.py` returning `(normalized_rows, caveats)` — so the report gets the source caveats without changing the `MarketSource.fetch()` contract (Codex #1).
- New `scripts/build_mfl_rookie_adp_divergence.py` (mirrors `build_universe_market_divergence.py`).
- Tests incl. a **read-only state contract test** (Codex #5 / Gemini).

**Non-goals (do NOT do these):**
- **No API endpoint, no frontend** (Phase 12 HOLD). Artifact-only — unanimous team decision; an endpoint is a trivial later add once the artifact contract is stable.
- **No PVO / team-strength / trade / training feed.** This reads model output to compare; it never writes to or feeds any decision surface.
- **No mutation of `prospect_cards.json`** or any model/PVO artifact.
- MFL stays **barred from calibration** and from Engine A/B training (unchanged).
- No `MarketSource.fetch()` contract change.

## 2. Inputs

- **MFL rookie ADP:** `fetch_rookie_adp_rows(season)` (new helper) → `(rows, caveats)`. Internally it calls `fetch_adp_with_cache(season)` + `fetch_players_with_cache(season)`, joins by `mfl_id`, and applies `normalize_mfl_adp_entry`. `rows` are the normalized overlay rows (incl. `mfl_id, full_name, position, market_adp_rank, market_average_pick, …, decision_supported=False`, intrinsic blend caveats); `caveats` carries the transient channel (source publish age / `mfl_adp_timestamp_unavailable` / `stale_market_data` / `market_data_unavailable`). **The `MarketSource.fetch()` rows-only contract is untouched.**
- **Model ranking:** `prospect_cards.json`, filtered to `draft_class == season` (Codex #4). Fields used per card: `full_name`, `position`, `draft_class`, **`xvar_class_rank` (primary model rank)**, `dvs_class_rank` (secondary, emitted alongside), `xvar`, `dynasty_value_score`. Read-only.

## 3. Identity join (fail-closed — Codex #3, #4)

- **Season is explicit.** The script supplies `season` (defaults to `_current_season()`); the report joins **only** `prospect_cards` with `draft_class == season`. `adp_draft_class = season` is recorded. **Years are never mixed.**
- **Join key:** `(normalize_name(name), position)` within the season, using `prospect_identity_resolver.normalize_name` (the Phase 9.5 canonical normalizer).
- **Fail-closed on collisions:** if the same `(normalized_name, position)` key appears more than once on the **ADP side**, those rows go to `ambiguous` with reason `adp_identity_ambiguous` and are **not matched**; likewise duplicate keys on the **model side** → `model_identity_ambiguous`. Never guess a match.
- **Both unmatched sides tracked separately:** `unmatched_adp` (MFL rookie with no card) and `unmatched_model` (carded rookie with no ADP row).

## 4. Divergence metric

For each cleanly-matched rookie (both ranks are within-class ordinals, 1 = best):
- `model_rank = xvar_class_rank`; `rank_source = "xvar_class_rank_v1"`. If a matched card's `xvar_class_rank` is missing/`None`, the rookie is recorded `model_rank_unavailable` with **no fabricated gap** (Codex #2).
- `rank_gap = market_adp_rank − model_rank` — **documented convention: positive ⇒ model rates the rookie higher (earlier) than the market does.**
- `divergence_flag`:
  - `aligned` if `abs(rank_gap) <= aligned_band`
  - `model_higher_than_market` if `rank_gap > aligned_band`
  - `market_higher_than_model` if `rank_gap < -aligned_band`
  - `aligned_band` defaults to **3**, and is **recorded in artifact metadata** (Codex #2).
- Each matched row also carries `dvs_class_rank`, `xvar`, `dynasty_value_score`, `market_adp_rank`, `market_average_pick`, the source publish timestamp/freshness caveat, the intrinsic blend caveats, and `decision_supported=False`.
- **Neutral flag language only** — `aligned` / `model_higher_than_market` / `market_higher_than_model`. No `buy`/`sell`/`target`/`fade`/verdict words.

## 5. Components & data flow

- `mfl_adp_adapter.fetch_rookie_adp_rows(season=None) -> (list[dict], list[str])` — narrow helper (§2). Additive; no contract change.
- `src/dynasty_genius/mfl_rookie_adp_divergence.py`:
  - `build_mfl_rookie_adp_divergence(adp_rows, prospect_cards, *, season, captured_at, caveats, aligned_band=3) -> dict` — pure. Filters cards to `season`, builds fail-closed identity index, computes per-rookie divergence, assembles `matched` / `unmatched_adp` / `unmatched_model` / `ambiguous` + the coverage block (§6). `decision_supported=False` at top level and on every matched row.
  - `write_mfl_rookie_adp_divergence_artifacts(divergence, *, output_dir, run_id) -> dict[str,Path]` — writes `mfl_rookie_adp_divergence_latest.json`, `…_<run_id>.json`, and a human-readable `…_latest.md`. Mirrors `write_market_divergence_artifacts`.
- `scripts/build_mfl_rookie_adp_divergence.py` — `fetch_rookie_adp_rows(season)` → load `prospect_cards.json` → `build_…` → `write_…` to `app/data/valuation/`. Read-only Sleeper; prints the artifact paths + coverage summary.

## 6. Artifact shape

```jsonc
{
  "captured_at": "<iso8601>",
  "source": "mfl_rookie_adp",
  "adp_draft_class": 2026,
  "rank_source": "xvar_class_rank_v1",
  "aligned_band": 3,
  "decision_supported": false,
  "caveats": ["mfl_adp_format_blended_qb_count", "mfl_adp_te_premium_unfiltered", "<freshness…>"],
  "matched": [
    { "mfl_id": "...", "full_name": "...", "position": "QB",
      "market_adp_rank": 6, "market_average_pick": 7.1,
      "model_rank": 8, "dvs_class_rank": 5, "xvar": 0.0, "dynasty_value_score": 0.0,
      "rank_gap": -2, "divergence_flag": "aligned", "decision_supported": false }
  ],
  "model_rank_unavailable": [ { "mfl_id": "...", "full_name": "...", "position": "..." } ],
  "unmatched_adp": [ { "mfl_id": "...", "full_name": "...", "position": "..." } ],
  "unmatched_model": [ { "full_name": "...", "position": "...", "model_rank": 12 } ],
  "ambiguous": [ { "key": "...", "side": "adp|model", "reason": "adp_identity_ambiguous|model_identity_ambiguous" } ],
  "coverage": {
    "total_adp_rows": 0, "matched_count": 0, "unmatched_adp_count": 0,
    "unmatched_model_count": 0, "ambiguous_count": 0, "model_rank_unavailable_count": 0,
    "decision_supported_true_count": 0, "banned_language_present": []
  }
}
```
The coverage block (Codex #6) makes the first artifact useful even at imperfect coverage. `decision_supported_true_count` must be **0** and `banned_language_present` must be **`[]`** — both are self-checks the builder computes and the tests assert.

## 7. Governance & guardrails

- **Read-only state proof (Codex #5 / Gemini):** a contract test runs the builder + writer against fixtures and asserts (a) `prospect_cards.json` and a representative PVO artifact are **byte-identical** before/after, and (b) the **only** files written match `app/data/valuation/mfl_rookie_adp_divergence_*.{json,md}` — no writes to PVO / team-matrix / trade artifacts.
- `decision_supported=False` on the artifact and every matched row; `decision_supported_true_count == 0` asserted.
- **Banned-language guard:** the builder scans every emitted string field for banned verdict words; `banned_language_present` must be empty (asserted).
- MFL fields remain barred from training (existing leakage gate) and MFL is **barred from calibration** (unchanged). Read-only Sleeper (no auth, no Databricks).
- No model pkl/manifest/contract change; no endpoint; frontend HOLD + NOISE_BAND lock intact.

## 8. Testing / contract intent

Pure builder on fixtures (a small `prospect_cards` slice + a small MFL rows list); no network in tests.
- **Match + flags:** a rookie with `rank_gap` inside/outside `±aligned_band` → correct `aligned` / `model_higher_than_market` / `market_higher_than_model`; `rank_gap = market_adp_rank − model_rank` sign verified (positive = model higher).
- **`xvar_class_rank` primary:** `model_rank` comes from `xvar_class_rank`; `dvs_class_rank` emitted alongside; a card with `xvar_class_rank=None` → `model_rank_unavailable`, no gap.
- **Fail-closed identity:** duplicate `(normalized_name, position)` on the ADP side → `adp_identity_ambiguous`, not matched; duplicate on model side → `model_identity_ambiguous`; name normalization matches `Jr.`/punctuation/case via `prospect_identity_resolver.normalize_name`.
- **Season isolation:** cards from a different `draft_class` than `season` are excluded; `adp_draft_class` recorded; no cross-year matches.
- **Unmatched both sides:** MFL-only rookie → `unmatched_adp`; carded-only rookie → `unmatched_model`.
- **Coverage block:** counts reconcile (`matched + model_rank_unavailable + unmatched_adp + adp-ambiguous == total_adp_rows` on the ADP side); `decision_supported_true_count == 0`; `banned_language_present == []`.
- **Read-only state contract:** byte-identical `prospect_cards.json` + PVO; writes confined to the divergence artifact paths.
- **Adapter helper:** `fetch_rookie_adp_rows` returns `(rows, caveats)` and does not alter `MarketSource.fetch()` behavior (existing MFL adapter tests still pass).

## 9. Counter-argument (Rule 5 — mandatory)

1. **A divergence report invites "act on it" interpretation.** Mitigation: `decision_supported=False` everywhere, neutral flags only (no buy/sell), format-blend caveats propagated to JSON + MD, and the artifact is inspection-only — wired to nothing. It describes disagreement; it does not recommend action.
2. **Name+position joins are fuzzy.** Mitigation: fail-closed on ambiguity (never guess), reuse the Phase 9.5 canonical normalizer, season-scope the join, and surface match rate + both unmatched sides + ambiguous list in the coverage block so low coverage is visible, not hidden.
3. **Reading model output risks coupling.** Mitigation: read-only of `prospect_cards.json`; the byte-identical state contract test proves the report never mutates model/PVO state; output is a separate artifact path asserted by test.
4. **MFL's SF/TEP blend skews the market side.** Mitigation: the intrinsic `mfl_adp_format_blended_qb_count` / `mfl_adp_te_premium_unfiltered` caveats ride on the rows and propagate to the artifact; this is an overlay/inference signal, never a model input.
