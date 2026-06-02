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

## 4. Match procedure (drafted) + fail-closed

**Cohort-truth-driven, not CFBD-driven** (clarified 2026-06-02 cockpit ruling, aligning this section with §5/§9: the drafted+UDFA cohort defines membership; CFBD is the identity substrate only — see §2). **Iterate the drafted skill picks** from `load_draft_picks(2025)` (filtered to QB/RB/WR/TE + drafted FB/ATH only when fantasy-position-relevant) and locate each pick's CFBD `/roster` identity on **normalized name + position-group + normalized school**, using a curated **school-alias map** (e.g. "Ole Miss"↔"Mississippi", "Miami"↔"Miami (FL)"). The join key is unchanged from a CFBD-first match; only the iteration driver and the review-row subject change.

**Match-pipeline order (explicit — final classification runs LAST, to avoid false `draft_truth_match_missing`):** (1) primary-key match (normalized name + position-group + normalized school); (2) **if** the drafted-skill unmatched rate exceeds ~5%, run the deterministic CFBD `/draft/picks` `collegeAthleteId` → roster `id` fallback before any looser matching; (3) **then** apply the per-pick final classification below. Never a fuzzy-filled or memory-filled registry identity.

**Final classification — fail-closed, keyed on the draft pick (evaluated after step 2):**
- a drafted skill pick with **0 CFBD matches** → `draft_truth_match_missing` review/block row carrying the **pick** (a genuine cohort member is surfaced for review, **never silently dropped**);
- **>1** CFBD match → `draft_truth_match_ambiguous`;
- exactly **1** → emit the `NormalizedCollegeProspectRow` (CFBD-sourced identity; cross-IDs **null** — no pre-bridge).

**Inverse-collision fail-closed (LOCKED 2026-06-02 — D-2, reused reason):** a single CFBD identity claimed by **>1** drafted skill pick (via primary match **or** `collegeAthleteId` fallback) **fails closed** — every involved pick becomes a `draft_truth_match_ambiguous` review row and **none is emitted** — preserving the registry `(source, source_record_id)` uniqueness invariant (`validate_registry_graph`). Reuses the existing reason (no new contract reason).

**Silent exclusion vs review (membership boundary):** **undrafted** CFBD roster rows and **clearly-non-skill drafted** positions (OL/DL/DB/ST/K/P) are **not** cohort members → **silently excluded (not review rows)**, per §9. A **drafted** pick whose position does not resolve to a skill group (e.g. `ATH`) is a cohort *candidate* under §5 → **review row** (fantasy-relevance is a David judgment), **not** silent exclusion. **Review reason (LOCKED 2026-06-02 — Codex technical + Gemini governance concur):** that review row carries reason **`unresolved_draft_pick_position`** — deliberately distinct from `unresolved_position_group` (which denotes a CFBD-roster-side position ambiguity), so the provenance shows the uncertainty originated draft-side. **Drafted `FB` is NOT auto-admitted as `RB`:** it fails closed to the same `unresolved_draft_pick_position` review row (raw position `FB`); admission is gated on manual review or explicit fantasy-relevance corroboration (expected-cohort / cross-ID presence), never a blanket map — modern FBs are overwhelmingly zero-fantasy-value, so auto-admission would pollute the RB registry and aging-curve baselines (Prime Directive: be right, not fast).

**Robustness boundary:** a malformed top-level `frozen_inputs` shape fails **loud** (caller/API misuse); a malformed *individual* source record fails **closed** → `malformed_source_record` review row. **This covers BOTH sides (LOCKED 2026-06-02 — D-1, completes the cleared boundary):** a CFBD roster row missing `id`, **and** a drafted-pick row missing a required structural field (`season`/`position`/`pfr_player_name`/`college`/`pfr_player_id`) — the latter keyed `source_record_id = pfr_player_id` if present else `nflverse_draft_picks:<missing>`. The nflverse draft pin is external/variable data, so malformed row *contents* fail closed (operating-loop §8); only the top-level shape is the fail-loud API-misuse boundary. **Boundary fully locked (2026-06-02 — D-3, operating-loop rule 8 "define up front"):** **fail loud** = `frozen_inputs` not a dict / missing a required key / a rows-container not a list (API misuse); **fail closed → `malformed_source_record`** = an individual record that is **not a dict** *or* a dict missing a required field; **producer responsibility (out of scope, NOT fail-closed)** = semantic value validity of present fields (e.g. `season` not int-coercible, implausible school) — this carve-out bounds the hardening and prevents whack-a-mole.

**UDFA cohort membership is added at Task 3, not Task 2** — the Task-2 builder takes a **generic expected-cohort list** (drafted-only in T2; drafted ∪ UDFA in T3, no logic rewrite). UDFAs match tracker name+school → `load_players()`/`load_ff_playerids()` to backfill IDs where rostered (Task 3).

## 5. Cohort (evidence-defined, not a quota)

All drafted 2025 QB/RB/WR/TE (+ drafted FB/ATH only when fantasy-position-relevant) + notable UDFAs with two-source corroboration. Expected size **~150–200**, but the number is **not a pass/fail gate**. CFBD `class_year` is **low-confidence** (ambiguous numeric field) → store with a provenance caveat if present; **never** use it to include/exclude. `prior_schools` is **out of scope** absent a David-authorized `/player/portal` pull; `current_school` = the CFBD roster team at snapshot time.

## 6. Frozen-snapshot reproducibility

Persist each raw input + a content hash, keyed by `source_snapshot_id` (retrieval UTC ISO-8601 + endpoint/query + v2 + SHA-256 of canonicalized payload + row count): the CFBD `/roster` response; the pinned nflverse `load_draft_picks` release tag + file hash; the `load_ff_playerids()` snapshot date + hash; the UDFA tracker URLs + page hashes. Frozen so every registry row is regenerable; the content hash detects CFBD silent backfills.

**D5 — canonical string, single source of truth (LOCKED 2026-06-02):** for **each** manifest entry Task 1 emits **both** the structured `source_snapshot_id` dict **and** a pre-composed canonical **`source_snapshot_id_str`** = `f"{source}:{retrieval_timestamp}:{endpoint}:{api_version}:{sha256}:{row_count}"`. **`{source}` is the year-qualified artifact name** (the persisted file stem, e.g. `cfbd_roster_2025`; the other entries follow the same pattern — `draft_picks_2025`, `ff_playerids_2025`, `udfa_sources_2025`) — **not** the bare manifest dict key (`cfbd_roster`, …). The Task-2 builder dereferences the manifest **by its dict key** and reads `["source_snapshot_id_str"]` **verbatim** — it never recomposes the string. The string format is locked by a Task-1 freeze contract test. *(Without this the builder `KeyError`s against a real frozen manifest — pre-patch the string key existed only in the Task-2 test fixture.)*

## 7. Roles

- **Agent-executable:** the frozen pulls (given the key), fixture generation with provenance, the ingest CLI, bridge discovery, preflight runs, and review/block-queue reporting.
- **David-manual / prerequisite:** obtaining the free CFBD key; the **S3 identity-confirmation step** (see below); and every bridge `confirm`/`udfa`/`reject`/`defer` decision. **Agents never fabricate acceptance decisions** (and never bulk-confirm S3 rows unless David explicitly authorizes a deterministic reviewed batch).

**S3 confirmation lifecycle (required, easy to miss).** `ingest_college_prospect_fixture.py::_mint_and_insert` mints registry rows as `verification_status="provisional"`. But `build_prospect_nfl_bridge.py` selects S3 prospects with `draft_class == draft_year AND verification_status == "confirmed"` — so discovery over a freshly-ingested fixture would load **zero** prospects. Therefore a **David-manual S3 identity confirmation** (via `scripts/promote_review_candidate.py` — `confirm`/`reject`/`defer`/`merge`/`split`) is a distinct step that runs **between ingest and bridge discovery**, separate from the later bridge promotion (`promote_bridge_candidate.py`).

## 8. Guardrails

`decision_supported=False` untouched; the §11.2 `cohort_selection_bias_caveat` + `metric_universe` honored (the ~150–200 cohort is a non-random sample — disclosed, not hidden); model-blind; no Engine A/B change; frontend HOLD; Databricks local-first (CFBD/nflverse are free/public, not Databricks). No `edge`/banned terminology.

## 9. Out of scope

Task 10B mock-consensus snapshot sourcing (separate; the `ingest` arm + a real run depend on it); `/player/portal` transfer history; CFBD-driven cohort *membership* (CFBD is identity-only); any market/value data.
