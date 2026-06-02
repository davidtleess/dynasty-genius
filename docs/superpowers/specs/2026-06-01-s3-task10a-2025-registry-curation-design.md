# S3 Task 10A — Curated-Real 2025 Prospect Registry + Bridge — Design Spec

- **Date:** 2026-06-01
- **Status:** DESIGN (pre-implementation). Cockpit unanimous (Codex technical CONVERGE + 6 pins; Gemini governance CONFIRM; corrected 10A-remains-blocked boundary ACK'd by both).
- **Objective:** Backtest-A operational readiness. Curate a **real, frozen, provenance-cited 2025 S3 confirmed-prospect registry + bridge** so the §11.2b preflight's registry-side arms pass — the agent-executable companion to a real run. **Source research:** `docs/strategies/2025 college prospect data sources.md`.
- **Scope (locked):** registry + bridge ONLY. **10A does NOT make the preflight `ready` — the `ingest` arm stays blocked** (no 2025 mock-draft consensus snapshots; those are **Task 10B**, separate, and must NOT mint the registry).

## 1. 10A success criterion (honest, bounded)

The 10A deliverable is the **registry/bridge selection-bias side clean**: over the **confirmed** 2025 cohort, `_confirmed_class_selection_bias(registry, bridge, 2025)` → `confirmed_class_unbridged_count == 0` and `orphan_bridges_detected == []` (or the only residual is the explicitly-intended review/block items). This is the primary 10A verification.

Because there are **no 2025 mock-draft snapshots yet**, the §11.2b preflight is **not `ready`**, and the precise behavior depends on the snapshots arg (the preflight's `presence` check treats a missing/empty snapshots dir as a **presence** block, and short-circuits `ingest`/`alignment`/`static_coverage` to `not_checked` when `presence` blocks):
- **No snapshots dir** → `presence` = **blocked** (`snapshots_dir_missing_or_empty`); `ingest`/`alignment`/`static_coverage` = `not_checked`; `ready` = **False**.
- **Minimal placeholder snapshots dir** (exists + ≥1 file, but ingests to zero usable picks) → `presence`/`alignment`/`static_coverage` = **ok**, `ingest` = **blocked** (`ingest_zero_usable_picks`), `ready` = **False**.

Either way **`ready` = False** is the *correct, complete* 10A outcome — `ready=True` is a 10B deliverable. (Do not claim "preflight presence ok" without the placeholder dir.)

## 2. Source stack (3 layers; registry independent of draft truth)

- **L1 — CFBD `/roster?year=2025` (v2, free Bearer key): college-identity substrate.** Supplies the integer athlete `id` → `cfbd_athlete_id` **and** `source_record_id`; `firstName`+`lastName` → `raw_name`/`full_name`; `position`; `team` → `current_school`. One-time **frozen** pull (free tier 1000/mo is irrelevant). If all-team omission isn't accepted, fall back to a teams-list + per-team pulls.
- **L2 — `nflreadpy.load_draft_picks(2025)`: drafted-cohort truth + ID augmentation.** Supplies `gsis_id`, `pfr_player_id`, **`cfb_player_id`** (the sports-reference college slug, delivered *inside* the nflverse file — **no Sports Reference scraping**, so the ToS/anti-scrape concern is moot). `gsis_id` is blank for players who never log an NFL snap (expected; nullable).
- **L3 — UDFA trackers (NFL.com + PFF + Spotrac): undrafted cohort membership.** `source_record_id` = the stable tracker URL (+ anchor). **Two-source corroboration required** for any UDFA addition *unless* the source is an official team/NFL transaction release (official outranks aggregators).
- **`sleeper_id` (optional):** via `load_ff_playerids()` (DynastyProcess crosswalk, keyed on `mfl_id`; join on `gsis_id`). **ID-crosswalk ONLY — no market/ADP/value field from that table enters S3/Backtest-A.**

## 3. Fixture contract (`resources/prospect_fixtures/2025_fantasy_prospects.json`)

Rows are source-shaped `NormalizedCollegeProspectRow` (`extra="forbid"`). `cfbd_athlete_id` and `source_record_id` are **stringified** (the schema fields are `str | None`; the CFBD athlete `id` is an integer → cast to str). Cross-IDs (`gsis_id`/`pfr_id`/`sleeper_id`) are **null in the input fixture** — the S4 bridge establishes `gsis_id`; UDFA `gsis_id`/`sleeper_id` come from the nflverse/DynastyProcess tables only where the player is rostered. The fixture carries **identity only — zero rankings/ADP/draft-grades/mock-slot values** (no market leakage). Per-row `id_provenance` in the **input fixture** names the source of the **populated** fields only — the CFBD identity side (e.g. `cfbd_athlete_id: CFBD /roster v2 #<id>`, plus name/position/`current_school`). Because the cross-IDs (`gsis_id`/`pfr_id`/`sleeper_id`) are **null in the input fixture**, their provenance (e.g. `gsis_id: nflreadpy load_draft_picks 2025 via PFR`; `sleeper_id: DynastyProcess load_ff_playerids join on gsis_id`) is recorded at the later **bridge / crosswalk** step that populates them — NOT in the input fixture.

## 4. Bridge procedure (drafted) + fail-closed

Match CFBD roster → `load_draft_picks(2025)` on **normalized name + position-group + normalized school**, using a curated **school-alias map** (e.g. "Ole Miss"↔"Mississippi", "Miami"↔"Miami (FL)"). **Fail-closed:** any CFBD miss or ambiguous multi-match becomes a **review/block row — never a fuzzy-filled or memory-filled registry identity.** If the drafted-skill unmatched rate exceeds ~5%, use CFBD `/draft/picks` `collegeAthleteId` → roster `id` (CFBD-internal, deterministic) before any looser matching. UDFAs match tracker name+school → `load_players()`/`load_ff_playerids()` to backfill IDs where rostered.

## 5. Cohort (evidence-defined, not a quota)

All drafted 2025 QB/RB/WR/TE (+ drafted FB/ATH only when fantasy-position-relevant) + notable UDFAs with two-source corroboration. Expected size **~150–200**, but the number is **not a pass/fail gate**. CFBD `class_year` is **low-confidence** (ambiguous numeric field) → store with a provenance caveat if present; **never** use it to include/exclude. `prior_schools` is **out of scope** absent a David-authorized `/player/portal` pull; `current_school` = the CFBD roster team at snapshot time.

## 6. Frozen-snapshot reproducibility

Persist each raw input + a content hash, keyed by `source_snapshot_id` (retrieval UTC ISO-8601 + endpoint/query + v2 + SHA-256 of canonicalized payload + row count): the CFBD `/roster` response; the pinned nflverse `load_draft_picks` release tag + file hash; the `load_ff_playerids()` snapshot date + hash; the UDFA tracker URLs + page hashes. Frozen so every registry row is regenerable; the content hash detects CFBD silent backfills.

## 7. Roles

- **Agent-executable:** the frozen pulls (given the key), fixture generation with provenance, the ingest CLI, bridge discovery, preflight runs, and review/block-queue reporting.
- **David-manual / prerequisite:** obtaining the free CFBD key; the **S3 identity-confirmation step** (see below); and every bridge `confirm`/`udfa`/`reject`/`defer` decision. **Agents never fabricate acceptance decisions** (and never bulk-confirm S3 rows unless David explicitly authorizes a deterministic reviewed batch).

**S3 confirmation lifecycle (required, easy to miss).** `ingest_college_prospect_fixture.py::_mint_and_insert` mints registry rows as `verification_status="provisional"`. But `build_prospect_nfl_bridge.py` selects S3 prospects with `draft_class == draft_year AND verification_status == "confirmed"` — so discovery over a freshly-ingested fixture would load **zero** prospects. Therefore a **David-manual S3 identity confirmation** (via `scripts/promote_review_candidate.py` — `confirm`/`reject`/`defer`/`merge`/`split`) is a distinct step that runs **between ingest and bridge discovery**, separate from the later bridge promotion (`promote_bridge_candidate.py`).

## 8. Guardrails

`decision_supported=False` untouched; the §11.2 `cohort_selection_bias_caveat` + `metric_universe` honored (the ~150–200 cohort is a non-random sample — disclosed, not hidden); model-blind; no Engine A/B change; frontend HOLD; Databricks local-first (CFBD/nflverse are free/public, not Databricks). No `edge`/banned terminology.

## 9. Out of scope

Task 10B mock-consensus snapshot sourcing (separate; the `ingest` arm + a real run depend on it); `/player/portal` transfer history; CFBD-driven cohort *membership* (CFBD is identity-only); any market/value data.
