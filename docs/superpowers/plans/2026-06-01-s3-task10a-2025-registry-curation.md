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
- [ ] **Step 6 (D5 follow-up — 2026-06-02 cockpit ruling; reconciles T1↔T2 single source of truth):** the freeze manifest must emit, alongside each structured `source_snapshot_id` dict, the **canonical pre-composed `source_snapshot_id_str`** (format `f"{source}:{retrieval_timestamp}:{endpoint}:{api_version}:{sha256}:{row_count}"`, where **`{source}` is the year-qualified artifact name** — the persisted file stem, e.g. `cfbd_roster_2025` — **not** the manifest dict key `cfbd_roster`; see spec §6). The Task-2 builder dereferences the manifest **by its dict key** and reads `["source_snapshot_id_str"]` verbatim — it never recomposes the string. Lock the format with a freeze contract test. *(Without this the builder `KeyError`s against a real frozen manifest — the string key is currently hand-supplied only in the Task-2 test fixture.)* **The spec authority for D5 is §6** (this plan step mirrors it).

## Task 2 — Fixture generation logic (agent-executable, cockpit-TDD)

**Files:** Create `src/dynasty_genius/identity/build_2025_prospect_fixture.py` (or a script module); Test: `tests/contract/test_s3_2025_fixture_builder.py`.

- [ ] **Step 1 (RED, Codex):** assert `build_2025_prospect_fixture(frozen_inputs) -> (rows, review_queue)`:
  - **cohort-truth-driven** (§4, §9; 2026-06-02 cockpit ruling): iterates the **drafted skill picks** (`load_draft_picks(2025)`, filtered to QB/RB/WR/TE + drafted FB/ATH only when fantasy-relevant) and locates each pick's CFBD `/roster` identity → `NormalizedCollegeProspectRow` (cross-IDs **null**), `cfbd_athlete_id`/`source_record_id` = **str(athlete id)** (schema is `str | None`), `current_school` = team. The builder takes a **generic expected-cohort list** (drafted-only in T2; UDFA union deferred to Task 3 — no logic rewrite).
  - **VALIDATES** deterministic match on the same join key (normalized name + position-group + normalized school via a curated school-alias map; `collegeAthleteId`→roster `id` fallback when drafted-skill unmatched > ~5%) and emits **review/block diagnostics keyed on the draft pick** — it does NOT pre-bridge and does NOT record accepted bridge matches (S4 bridge entries come ONLY via `build_prospect_nfl_bridge.py` + David promotion). Registry cross-IDs stay **null**.
  - **review-row taxonomy (keyed on the pick):** drafted pick with **0 CFBD matches** → `draft_truth_match_missing` (the pick — **never silently dropped**); **>1** → `draft_truth_match_ambiguous`; **1** → emit the row. **Undrafted CFBD rows + clearly-non-skill drafted positions → silently excluded (NOT review rows).** A drafted pick whose raw position won't map to a skill group (e.g. `ATH`), **incl. drafted `FB`**, → review row with reason **`unresolved_draft_pick_position`** (LOCKED 2026-06-02; FB never auto-→RB — spec §4). **Never fuzzy/memory fill.** **Inverse-collision (D-2, LOCKED 2026-06-02):** a single CFBD identity claimed by **>1** drafted skill pick (primary or fallback) **fails closed** → each involved pick → `draft_truth_match_ambiguous` review row, **none emitted** (reused reason, no new contract reason; preserves `(source, source_record_id)` uniqueness — spec §4).
  - **match-pipeline order (spec §4):** primary-key match → **if** drafted-skill unmatched > ~5% run the `collegeAthleteId`→roster `id` deterministic fallback → **then** final 0/1/>1 classification. Assert the fallback runs **before** classification (so a fallback-recoverable pick is not mis-flagged `draft_truth_match_missing`).
  - **robustness boundary (D4):** malformed top-level `frozen_inputs` shape → fails **loud** (caller/API misuse); a malformed individual source record → fails **closed** → `malformed_source_record` review row. **Covers BOTH sides (D-1, LOCKED 2026-06-02):** CFBD roster row missing `id`, **and** a drafted-pick row missing a required structural field (`season`/`position`/`pfr_player_name`/`college`/`pfr_player_id`), keyed `source_record_id = pfr_player_id` else `nflverse_draft_picks:<missing>` (nflverse draft pin is external/variable data → row contents fail closed per operating-loop §8 — spec §4). **Boundary fully locked (D-3, LOCKED 2026-06-02):** fail **loud** = `frozen_inputs` not a dict / missing required key / rows-container not a list; fail **closed** (`malformed_source_record`) = an individual record **not a dict** OR a dict missing a required field; **producer responsibility (out of scope)** = semantic value validity of present fields (e.g. `season` not int-coercible) — bounds the hardening, no whack-a-mole.
  - per-row `id_provenance` populated; `source_snapshot_id` set from the manifest (the manifest's pre-composed `source_snapshot_id_str` — T1 emits it, single source of truth); cohort is evidence-defined (no quota gate); `class_year` low-confidence (never include/exclude).
  - **zero market/ADP/grade fields** in any output row.
  - Build the test from small synthetic-but-source-shaped frozen inputs: a few drafted skill picks + their CFBD identities incl. **one alias-mismatch**, **one ambiguous (>1 CFBD match)**, **one drafted pick with NO CFBD match → asserts `draft_truth_match_missing` on the pick (silent-drop guard)**, **one undrafted skill CFBD row + one non-skill CFBD row → assert silent exclusion (no review row)**, **one drafted `ATH` (and/or `FB`) pick → asserts `unresolved_draft_pick_position` review row (not auto-admitted)**, **one fallback-recoverable pick (>5% path) → asserts it is NOT mis-flagged `draft_truth_match_missing`**, **one roster row missing `id` → asserts `malformed_source_record`**, **one drafted-pick row missing `season` (1:1 CFBD match otherwise) → asserts `malformed_source_record` (no crash, no emit) [D-1]**, **two drafted skill picks resolving to ONE CFBD identity → asserts both are `draft_truth_match_ambiguous` with no duplicate emitted `source_record_id` [D-2]**, **one non-dict draft-row element → asserts `malformed_source_record` (no `AttributeError`) [D-3]**, **one non-dict CFBD-row element (with an otherwise valid draft pick) → asserts fail-closed `malformed_source_record` (no `AttributeError`) [D-3]**.
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

**Spec coverage:** §2 stack → T1/T2; §3 fixture contract → T2; §4 match+fail-closed → T2/T6; §5 cohort → T2; §6 freezing → T1; §1 success criterion → T8; §7 roles incl. the S3 confirmation lifecycle (David: T0 key, T3 fixture review, **T5 S3 identity confirm via promote_review_candidate**, T7 bridge confirm/udfa; agents do the rest). The S3 provisional→confirmed step (T5) precedes discovery (T6) because discovery filters to `confirmed`. **Placeholder scan:** none (data values come from real frozen pulls at run time, never invented). **Type/name consistency:** `NormalizedCollegeProspectRow`, `source_snapshot_id`, `id_provenance`, `cfbd_athlete_id`, `build_2025_prospect_fixture`. **Scope:** 10A only; 10B snapshots + `/player/portal` + cohort-from-CFBD + any market data explicitly out (§9). No origin push until three-way CLEAR + David.
