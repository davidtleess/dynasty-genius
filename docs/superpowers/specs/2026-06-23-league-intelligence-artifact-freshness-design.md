# League Pulse Artifact Freshness — Design Spec

- Status: **v3 — round-2 F3 fix (side-effect-free preflight probe; no staged-17.4). Codex F1/F2/F4/F5/F6 + Gemini D1/D2/D3 confirmed integrated at round 2. Awaiting final dual-CLEAR. David rulings: Q2, Q3, Y, abort-on-cold AND abort-on-stale. NO RED / NO live run until dual-CLEAR + David approval.**

> **Round-2 resolution (v2→v3):** F3 — §3 reopened the seam by offering "or a staged 17.4". A staged 17.4 calls `fetch_with_cache` (`fantasycalc_adapter.py:86-96`) which can mutate `app/cache/fantasycalc` + write staged outputs BEFORE preflight passes. v3 strikes the staged-17.4 option: the §3 probe is strictly read-only (no 17.4, no `fetch_with_cache`, no cache write); staged-output/abort/restore stays in §5 for post-preflight failures only. All other findings confirmed integrated at round 2.
- Authorship: Claude Code authors; Codex technical-reviews; Gemini governance-reviews
- Date: 2026-06-23
- Governance: constitution 1.0.0, north-star 1.0.0, operating-loop 1.0.0, code-hygiene 1.0.0
- Sequence context: David-selected next initiative after League Pulse shipped. Makes the live League Pulse surface (currently 2026-05-24 data) reflect the CURRENT league.

## 0. Round-1 resolution (v1 → v2)
- **D1 (David-ruled): stale-cache → ABORT** (not "proceed-with-caveat"). A stale FantasyCalc
  cache stamps the new divergence artifact with TODAY's `captured_at`, so the frozen Inc2
  honesty header shows "As of [Today]" over month-old market data — an active lie. Stale market
  is treated exactly like cold-empty: **if we cannot fetch FRESH market data, we do not commit
  a freshness update.** → §3/§5/§8. (Resolves the Codex "stale-OK" vs Gemini "stale-abort"
  cross-domain split via David.)
- **F1 (HIGH): roster-cut handoff shape** — `build_roster_cut_report.py:107-110` writes a
  WRAPPER `{run_id, captured_at, roster_cut_report}`; `RosterCutResult` (`roster_cut_engine.py:93`)
  is the INNER object. T2 unwraps `payload["roster_cut_report"]` → `RosterCutResult.model_validate`,
  fail-closed if missing/malformed; **no inline-engine fallback.** → §2.
- **F2 (HIGH): staged-output + atomic-promote** — builders also write timestamped run-specific
  artifacts; `*_latest`-only restore leaves orphans. → §5.
- **F3 (MED/HIGH): real cold/stale market seam** — `fetch_with_cache` only flags
  `market_data_unavailable` AFTER fetching; need a pre-run classification probe. → §3.
- **F4 (MED): non-vacuous drop-pairing** — zero WAIVER cards must not pass vacuously. → §4.
- **F5 / D3: explicit market-bleed assertion** (mathematical, not prose). → §4.
- **F6: test-backed acceptance-report schema.** → §8.
- **D2: physical shape-drift gate** (instantiate app + `model_validate`). → §4.

## 1. Authorization & scope
David authorized re-running the Phase 17/18 league-intelligence pipeline so League Pulse +
the divergence reports reflect the current league. **David rulings:** Q2 live fetches
(Sleeper + FantasyCalc) authorized; Q3 modifying the git-TRACKED `app/data` artifacts
authorized (review by acceptance-parity report, not line-diff); Y expand to restore WAIVER
drop-pairing; **abort on cold-market AND on stale-cache (D1).**

**In scope:** (T1) preflight + acceptance/parity **verifier** with a locked report schema;
(T2) Y-wiring — roster-cut orchestrator step + `roster_cut_result` into the 17.5 builder;
(T3) the **gated operational run** + acceptance report + committing the refreshed artifacts.

**Out of scope (hard boundary):** model retraining; Engine A/B feature change; `.pkl` change;
new data source; OpenAPI/Zod/contract change (response SHAPE frozen — Inc1 — only VALUES
refresh); frontend change. Market divergence stays a descriptive overlay, never a model input.
Engine B is INFERENCE-only over the fresh snapshot.

## 2. Pipeline + Y-expansion
Orchestrator `scripts/refresh_league_intelligence.py` (subprocess, fail-fast): 17.1 Sleeper
snapshot → 17.2 PVO → 17.3 matrix → 18.3 posture → 17.4 market divergence → 17.5 opportunity.

**Y-expansion (David-ruled):**
- Insert a **Phase-21 roster-cut step** (`scripts/build_roster_cut_report.py`, snapshot+PVO →
  `roster_cut_report_latest.json`) AFTER 17.2 and BEFORE 17.5 (dependency-correct — Codex
  confirmed).
- Modify `scripts/build_league_opportunity_map.py` to load `roster_cut_report_latest.json`,
  **unwrap `payload["roster_cut_report"]`, `RosterCutResult.model_validate` it (fail-closed if
  the key is missing/malformed — NO inline-engine fallback, F1)**, and pass it as
  `roster_cut_result=` to `build_league_opportunity_map(...)` (the function already supports it,
  `league_opportunity_map.py:362,503`). WAIVER cards regain `recommended_drop`.

Live fetches: 17.1 Sleeper public API (`DYNASTY_SLEEPER_LEAGUE_ID`); 17.4 FantasyCalc
(`api.fantasycalc.com/values/current`). **No Databricks.**

## 3. Preflight contract (T1 — before any mutation)
MUST pass before the run, else ABORT (no mutation):
- working tree clean for target tracked artifacts; all builder scripts import; output dirs
  writable; required inputs present (`resources/prospect_cards.json`, `ff_playerids`, Engine B
  bundle, Sleeper league id resolvable); current artifacts' `schema_version` match expected;
  League Pulse route currently parses the existing artifacts.
- **Market-source classification probe (F3) — strictly SIDE-EFFECT-FREE (Codex/Gemini round 2).**
  BEFORE the run, classify FantasyCalc as `live`/`fresh-cache`/`stale-cache`/`cold-empty` via a
  **read-only** helper: read `app/cache/fantasycalc` cache state + TTL and run a lightweight API
  reachability probe. It MUST NOT invoke the 17.4 builder, MUST NOT call `fetch_with_cache`, and
  MUST NOT write/refresh/trash any cache or artifact (a failed preflight leaves
  `app/cache/fantasycalc/market_values.json` and all artifacts byte-unchanged — safe-abort).
  **`stale-cache` OR `cold-empty` → ABORT (D1).** Only `live` or `fresh-cache` proceed.
  Staged-output/abort/restore (§5) applies ONLY to post-preflight builder/acceptance failures.

## 4. Acceptance / parity contract (T1 — after the run; safety gate AND review mechanism)
A refresh is VALID only if ALL hold (else FAIL → do not commit):
- **Shape-drift gate (D2, physical — not assumed):** the T1 verifier MUST programmatically
  instantiate the FastAPI app, call `GET /api/league/pulse` against the newly generated
  artifacts (TestClient), and run `LeaguePulseResponse.model_validate(response.json())` — **any
  validation error is a hard FAIL.** Per-artifact `schema_version` unchanged; zero OpenAPI/Zod
  drift.
- **Market-bleed (D3/F5, mathematical):** the verifier scans the assembled League Pulse
  response and asserts known market keys (`market_percentile`, `model_minus_market_delta`,
  `model_percentile`, `divergence_score`, `xvar`, `raw_xvar`, `signal`, `signal_status`,
  `asset_roster_id`, `lineup_role`) appear ONLY within `market_overlay_cards`, and NEVER within
  `model_native_cards` / `team_postures` / `team_values` / `partner_rankings` evidence/score.
- **Drop-pairing (F4, non-vacuous):** `WAIVER_CANDIDATE` card count > 0 AND each carries a
  non-null `recommended_drop`. Zero WAIVER cards or any null `recommended_drop` → FAIL /
  manual-review (never a silent vacuous pass). `recommended_drop` carries `decision_supported=False`.
- **Counts/sanity:** `team_count == 12`; roster join non-empty; non-zero PVO rows; non-zero
  partner_rankings + cards.
- **Decision framing:** recursive `decision_supported=True` count == 0 across all generated JSON.
- **Banned-language:** word-boundary scan clean over JSON + MD + the assembled response.
- **Freshness:** `captured_at` advances to today; `source_artifacts` consistent (no mixed
  stale/fresh inputs); market data is `live`/`fresh-cache` (stale/cold already aborted in §3).
- **Guardrails (§6):** no `.pkl`/Engine A/B/training change in the diff.

## 5. Failure / abort handling (T3) — staged-output + atomic-promote (F2)
- **Cold-market OR stale-cache** (preflight §3) → **ABORT**, no mutation. (D1)
- **Structural builder failure** (`CalledProcessError`) → **ABORT** the chain.
- **No half-state ever committed (F2):** builders run against a **staged output location**;
  the refreshed `*_latest` + timestamped run artifacts are **atomically promoted** to the
  tracked `app/data` paths ONLY after the full chain + acceptance (§4) PASS. On any abort, the
  staged outputs are discarded and the tracked paths are byte-unchanged. (If staged-output is
  infeasible for a builder, the fallback is: back up prior `*_latest`, run, and on failure
  restore `*_latest` AND delete every failed-run timestamped artifact
  [`team_value_matrix_<run>`, `league_opportunity_<run>.json/.md`, `roster_cut_report_<run>.json/.md`],
  then assert `git status --porcelain` clean for the target paths.)
- **Reproducibility:** `run_id`/`captured_at` make the run **provenance-tracked / replayable**,
  NOT byte-deterministic.

## 6. Guardrails
Engine B INFERENCE only (17.2 scores over the fresh snapshot — no retraining); NO Engine A/B
feature change; NO `.pkl` model-bundle change; market divergence overlay-only (FantasyCalc
never a model input); `decision_supported=False` recursive; NO OpenAPI/Zod/contract change.

## 7. Tracked-artifact commit + review-by-report (Q3)
The refresh COMMITS the regenerated tracked artifacts (multi-MB: pvo ~22MB, divergence ~23MB,
snapshot ~7MB, + matrix/posture/opportunity/roster-cut). Review is **acceptance-report-based,
not line-diff** (David-authorized). The commit bundles the §8 machine-readable refresh report.
This commit intentionally reverses the per-initiative "no app/data change" discipline —
explicitly, this once, for freshness.

## 8. Acceptance-report schema (F6 — T1-locked, test-backed)
The T1 verifier emits a machine-readable report whose schema is locked by tests. Required
fields (a missing field is a T1 FAIL): per-step status; **market-source classification**
(`live`/`fresh-cache` — stale/cold would have aborted); per-artifact path + **content hash +
byte size**; `captured_at` before/after deltas; counts (team_count, pvo_rows, card counts by
lane, WAIVER+recommended_drop count); each acceptance check pass/fail (shape-drift, market-bleed,
drop-pairing, decision_supported, banned-language, freshness, guardrails); rollback/guardrail
diff summary (confirming no `.pkl`/Engine A/B path touched).

## 9. Acceptance criteria & falsification matrix (T1/T2 code — TDD)
T1 verifier + T2 Y-wiring are RED-testable with fixtures; T3 is the gated operational run
(verified by the §8 report, not RED/GREEN).

Falsification matrix (each → a RED test for T1/T2):
- **preflight nominal** (inputs present, schema versions match, route parses, market live/fresh) → proceed.
- **preflight stale-cache** (expired TTL + API unreachable) → ABORT (D1), no run.
- **preflight cold-empty** (no cache + API unreachable) → ABORT, no run.
- **preflight missing input** → fail loud, no run.
- **roster-cut handoff (F1):** wrapper-shaped `roster_cut_report_latest.json` parses ONLY via
  inner `payload["roster_cut_report"]`; top-level `RosterCutResult.model_validate` is RED;
  missing inner object aborts before 17.5.
- **drop-pairing present (Y/F4):** WAIVER cards carry non-null `recommended_drop`; zero WAIVER
  → manual-review/FAIL; null `recommended_drop` → FAIL; non-WAIVER cards never carry it.
- **shape-drift gate (D2):** a generated response that violates `LeaguePulseResponse` →
  model_validate hard FAIL.
- **market-bleed (D3/F5):** a model-native card with `market_percentile`/`model_minus_market_delta`/`divergence_score` → FAIL.
- **decision_supported leak** (a True survives) → FAIL.
- **banned-language** (a banned token in JSON/MD/response) → FAIL.
- **counts** (team_count != 12 / zero PVO / empty required section) → FAIL.
- **atomic-promote/rollback (F2):** a mid-chain builder failure leaves the tracked paths
  byte-unchanged and no orphan `<run>` artifacts; `git status` clean for target paths.
- **report schema (F6):** a report missing market-classification / hash-or-size / a failed-check
  detail → T1 FAIL.

## 10. Build sequence (post-approval only)
spec dual-CLEAR → David approves → **T1** preflight+acceptance verifier (+ locked report schema)
(Codex RED → Claude GREEN → dual-CLEAR → David-authorized commit) → **T2** Y-wiring (roster-cut
step + 17.5 `roster_cut_result` unwrap, RED → GREEN → dual-CLEAR → commit) → **T3** GATED LIVE
RUN: execute under the T1 verifier, produce the §8 report, and — only on a PASS — atomically
promote + commit the refreshed tracked artifacts + report (David authorizes the run + commit;
abort cleanly on cold/stale-market or structural failure). No live run before T1/T2 are CLEARed
and David authorizes T3.
