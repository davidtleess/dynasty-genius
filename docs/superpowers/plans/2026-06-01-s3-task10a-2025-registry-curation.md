# S3 Task 10A — 2025 Prospect Registry + Bridge Curation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: cockpit-TDD for the code tasks (Codex RED → Claude GREEN → dual CLEAR → commit → loop-closed). Data-pull + David-manual steps are procedural (noted). Steps use checkbox (`- [ ]`). Spec: `docs/superpowers/specs/2026-06-01-s3-task10a-2025-registry-curation-design.md`.

**Goal:** A real, frozen, provenance-cited 2025 S3 confirmed-prospect registry + bridge that passes the §11.2b preflight's registry-side arms (presence/alignment/static_coverage). **Not** preflight-`ready` — the `ingest` arm stays blocked (10B).

**Constraints:** real sources only / no fabrication / no memory-fill; fail-closed (unmatched → review/block row); identity-only fixture (no market data); frozen with content hashes; no `edge`/`mock`/`adp` banned terms; **no push to origin until a three-way CLEAR + David's word**.

---

## Task 0 — Prerequisite (David): CFBD free API key

- [ ] David obtains the free CFBD v2 key (`collegefootballdata.com/key`, emailed) and provides it via env var `CFBD_API_KEY` (never committed; `.gitignore` covers env/secrets). No agent proceeds with the L1 pull until the key is available.

## Task 1 — Freeze the raw source inputs (agent-executable, read-only)

**Files:** Create `scripts/freeze_2025_prospect_sources.py`; persist frozen artifacts under `resources/prospect_fixtures/_frozen_2025/` (raw payloads + a `manifest.json` of `source_snapshot_id`s).

- [ ] **Step 1 (RED, Codex):** assert a `freeze_2025_prospect_sources` step that, given the CFBD key, writes: the raw CFBD `/roster?year=2025` JSON (per-team fallback if all-team omission fails) + SHA-256 + row count; a pin record of the nflverse `load_draft_picks(2025)` release tag + file hash; the `load_ff_playerids()` snapshot date + hash; and a UDFA-source manifest (tracker URLs). Each entry carries the `source_snapshot_id` shape (ts + endpoint + version + hash + rowcount). Test with a **mocked** CFBD client + a tiny fixture frame (no live network in the test).
- [ ] **Step 2-4:** GREEN (lazy `cfbd`/`nflreadpy` imports; no writes outside `_frozen_2025/`); focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s3-10a): frozen 2025 source-input capture + manifest`. **(Running it against the real CFBD key is a separate David-gated data step, not the commit.)**

## Task 2 — Fixture generation logic (agent-executable, cockpit-TDD)

**Files:** Create `src/dynasty_genius/identity/build_2025_prospect_fixture.py` (or a script module); Test: `tests/contract/test_s3_2025_fixture_builder.py`.

- [ ] **Step 1 (RED, Codex):** assert `build_2025_prospect_fixture(frozen_inputs) -> (rows, review_queue)`:
  - maps CFBD roster rows → `NormalizedCollegeProspectRow` (cross-IDs **null**), `cfbd_athlete_id`/`source_record_id` = **str(athlete id)** (schema is `str | None`), `current_school` = team, `position_group` mapped from raw position (QB/RB/WR/TE; ATH/FB resolved or sent to review).
  - **VALIDATES** deterministic CFBD↔draft matching (normalized name + position-group + normalized school via a curated school-alias map; `collegeAthleteId`→roster `id` fallback when drafted-skill unmatched > ~5%) and emits **review/block diagnostics** — it does NOT pre-bridge and does NOT record accepted bridge matches (S4 bridge entries come ONLY via `build_prospect_nfl_bridge.py` + David promotion). Registry cross-IDs stay **null**. **Ambiguous/miss → a review/block row, never fuzzy/memory fill.**
  - `>~5%` drafted-skill unmatched → use `collegeAthleteId`→roster `id` deterministic path (assert this fallback path).
  - per-row `id_provenance` populated; `source_snapshot_id` set from the manifest; cohort is evidence-defined (no quota gate); `class_year` low-confidence (never include/exclude).
  - **zero market/ADP/grade fields** in any output row.
  - Build the test from small synthetic-but-source-shaped frozen inputs (a few CFBD rows, a few draft rows incl. one alias-mismatch + one ambiguous → assert the review row).
- [ ] **Step 2-4:** GREEN; focused pass; ruff clean; no banned terms.
- [ ] **Step 5:** commit `feat(s3-10a): 2025 prospect fixture builder (provenance + fail-closed review rows)`.

## Task 3 — Produce the real frozen 2025 fixture (agent-executable data run + David review)

- [ ] **Step 1:** run Task 1 freeze against the real CFBD key (David-gated) → `_frozen_2025/`.
- [ ] **Step 2:** run Task 2 builder → `resources/prospect_fixtures/2025_fantasy_prospects.json` + a review/block queue of unmatched/ambiguous rows. UDFA layer added with two-source corroboration (official team release outranks aggregators).
- [ ] **Step 3 (David review):** David reviews the review/block queue + spot-checks rows against the cited sources before the fixture is accepted. Fixture committed only after David's sign-off + dual CLEAR.

## Task 4 — Ingest fixture → provisional registry (agent-executable)

- [ ] `ingest_college_prospect_fixture.py --fixture resources/prospect_fixtures/2025_fantasy_prospects.json --identity-dir <dir> --run-id <id>` → the 2025 `college_prospect_registry.json` with rows minted **`verification_status="provisional"`** (`_mint_and_insert` default) + the S3 review/block queue + coverage. (No rows are `confirmed` yet — that is Task 5.)

## Task 5 — S3 IDENTITY confirmation (David-manual; required before discovery)

- [ ] David confirms the provisional 2025 registry rows via `scripts/promote_review_candidate.py` (`confirm`/`reject`/`defer`/`merge`/`split`). **This is mandatory:** `build_prospect_nfl_bridge.py` selects only `verification_status == "confirmed"` rows, so an unconfirmed fixture yields zero discovery. **Agents do NOT bulk-confirm** unless David explicitly authorizes a deterministic reviewed batch. (Distinct from the later bridge promotion.)

## Task 6 — Bridge discovery over the confirmed registry (agent-executable)

- [ ] `build_prospect_nfl_bridge.py --identity-dir <dir> --draft-year 2025 --run-id <id>` (shared loader, real 2025 nflreadpy truth) → bridge review queue + UDFA candidates over the now-**confirmed** 2025 cohort.

## Task 7 — Bridge promotion (David-manual)

- [ ] David adjudicates each candidate: `confirm` / `udfa` / `reject` / `defer` → `promote_bridge_candidate.py` writes the bridge entries. **Agents do not fabricate these decisions.**

## Task 8 — Verification + closeout (agent-executable)

- [ ] **Step 1 (registry/bridge clean — primary 10A check):** `_confirmed_class_selection_bias(registry, bridge, 2025)` → `confirmed_class_unbridged_count == 0` and `orphan_bridges_detected == []` for the confirmed cohort (or the only residual is the intended review/block items).
- [ ] **Step 2 (preflight — honest not-ready):** `--snapshots-dir` is a REQUIRED CLI arg, so it is always passed (never omitted). Run `scripts/preflight_backtest_a.py --snapshots-dir <path> --identity-dir <dir> --draft-year 2025` either (a) with `<path>` = a **missing/empty** dir → `presence` blocked (`snapshots_dir_missing_or_empty`), `alignment`/`static_coverage` `not_checked`, `ready=False`; or (b) with `<path>` = a **minimal placeholder snapshots dir** (exists, ≥1 file, zero usable picks) → `presence`/`alignment`/`static_coverage` ok, `ingest` blocked (`ingest_zero_usable_picks`), `ready=False`. Either way `ready=False` is the correct 10A outcome; the emitted blocked-input list is the 10B handoff.
- [ ] **Step 3:** full suite + audit green; ruff clean. Commit only code/artifacts that are dual-CLEARED.

---

## Self-Review

**Spec coverage:** §2 stack → T1/T2; §3 fixture contract → T2; §4 bridge+fail-closed → T2/T6; §5 cohort → T2; §6 freezing → T1; §1 success criterion → T8; §7 roles incl. the S3 confirmation lifecycle (David: T0 key, T3 fixture review, **T5 S3 identity confirm via promote_review_candidate**, T7 bridge confirm/udfa; agents do the rest). The S3 provisional→confirmed step (T5) precedes discovery (T6) because discovery filters to `confirmed`. **Placeholder scan:** none (data values come from real frozen pulls at run time, never invented). **Type/name consistency:** `NormalizedCollegeProspectRow`, `source_snapshot_id`, `id_provenance`, `cfbd_athlete_id`, `build_2025_prospect_fixture`. **Scope:** 10A only; 10B snapshots + `/player/portal` + cohort-from-CFBD + any market data explicitly out (§9). No origin push until three-way CLEAR + David.
