---
title: Subsystem 3 — Prospect Identity Substrate (Follow-up B Increment A) — Design Spec
status: APPROVED design (David, 2026-05-28) — unanimously cockpit-converged (Codex + Gemini) across 7 decisions + 6 refinements + 3 meta concerns
date: 2026-05-28
author: Claude Code (brainstormed with David; design-reviewed by Codex + Gemini across multiple rounds)
parent: docs/strategies/2026-05-28-increment-a-reconciliation-and-go-forward.md (Increment A reconciliation); docs/strategies/2026-05-28-increment-a-nfl-mock-aggregation-research-brief.md (brief)
governance_hold: Frontend remains on the Phase 12 HOLD; backend only. NOISE_BAND lock untouched.
---

# Subsystem 3 — Prospect Identity Substrate

## 0. What we're building

An **identity substrate** for **undrafted college prospects** — the registry, alias bridge, matcher
(discovery-only), and review-queue lifecycle that any later Increment-A consumer (mock aggregation,
backtest, Engine A near-class scoring) will join against. **Substrate-only**: ships with a manual
fixture as the v1 data source; CFBD adapter is a separate v2 increment.

Undrafted college prospects have **no Sleeper/MFL/NFL IDs yet** — only names, positions, and schools.
S3 establishes a stable internal identity (`prospect_uuid`) with **separate nullable provenance-tagged
source IDs** and a fail-closed matching pipeline that **never auto-resolves**. The substrate is
**class-agnostic** by design.

## 1. Scope & non-goals

**In scope (v1):**
- New sibling files under `app/data/identity/`: `college_prospect_registry.json`, `college_alias_bridge.json`, `college_identity_review_queue_<run_id>.jsonl`, `college_identity_coverage_matrix_<run_id>.json`, `college_identity_promotion_log.jsonl`, `college_identity_failure_report_<run_id>.md`.
- New module `src/dynasty_genius/identity/college_prospect_identity.py` — schema, ingestion, matcher (discovery-only), promotion script entry-points, `ConfirmedProspectUuid` typed wrapper.
- New `scripts/promote_review_candidate.py` — the only blessed write path for review decisions.
- New `scripts/ingest_college_prospect_fixture.py` — manual-fixture loader with the same atomicity contracts as the promotion script.
- New sibling `resolve_prospect_cfbd_athlete_id()` mirroring the existing three-stage resolver pattern. **Existing `prospect_identity_resolver.py` behavior unchanged.**
- Top-100 2027 prospects in the manual fixture; synthetic tests cover class-agnosticism.

**Explicit non-goals (do NOT do these in v1):**
- **No CFBD adapter** — v2 increment, opens with explicit ToS verification.
- **No mutation of existing `prospect_registry.json` / `composite_registry.json` / `prospect_alias_bridge.json`** — tests assert byte-unchanged.
- **No graduation-at-draft script** (college → NFL-side registry) — separate later increment.
- **No mock/ADP/market data in the registry** — identity only; mock sources can *discover* names needing resolution, they never enter the registry as identity truth.
- **No historical 2018–2026 backfill** — S4 backfill increment owns this.
- **No Engine A / Trade Lab / PVO / model-training changes.** Frontend HOLD intact.

## 2. v1 source contract — manual fixture with CFBD-shape forward-compat

Per the reconciliation Hybrid: ship the substrate on a **curated manual fixture** that mirrors **exactly** the row shape a future CFBD adapter will produce. Zero schema migration when v2 lands.

**Fixture file:** `resources/college_prospect_fixture_2027.json` — `{"metadata": {...}, "entries": [NormalizedCollegeProspectRow, ...]}`. **Top-100** 2027 prospects (covers 12-team × 3-round = 36 hard-relevant + sleeper/bust-out buffer).

**`NormalizedCollegeProspectRow` schema (the locked source-shaped contract):**
```jsonc
{
  "raw_name": "Arch Manning",              // exact text from source
  "normalized_name": "arch manning",       // via prospect_identity_resolver.normalize_name
  "full_name": "Arch Manning",             // display
  "position": "QB",
  "position_group": "QB",                  // see §5 taxonomy
  "draft_class": 2027,
  "class_year": "Junior",                  // optional
  "current_school": "Texas",
  "prior_schools": [],
  "cfbd_athlete_id": null,                 // nullable; provenance-tagged when set
  "cfb_player_id": null,                   // nullable
  "pfr_id": null, "gsis_id": null, "sleeper_id": null,  // nullable (post-draft IDs)
  "source": "manual_fixture",              // "manual_fixture" | "cfbd" | other
  "source_record_id": "fixture_2027_001",  // stable per-source row id
  "source_snapshot_id": "fixture_2027_v1", // snapshot identifier
  "id_provenance": {                       // per-ID source/method/timestamp
    "cfbd_athlete_id": null,
    "cfb_player_id": null,
    "pfr_id": null,
    "gsis_id": null,
    "sleeper_id": null
  },
  "notes": "optional reviewer/curator note"
}
```

**CFBD-shape contract test:** a fixture row built from CFBD's documented response fields validates that the substrate's ingestion accepts it byte-for-byte (no schema migration when v2 ships). Test runs without network; mocks the CFBD response shape.

## 3. File architecture — sibling files; existing artifacts untouched

All new files under `app/data/identity/`:
- `college_prospect_registry.json` — `{"metadata": {...}, "entries": [...]}` of registry records (§4).
- `college_alias_bridge.json` — `{"metadata": {...}, "entries": [...]}`; key = `(normalized_name, position_group OR position, draft_class, current_school?)`, target = `prospect_uuid` and/or `cfbd_athlete_id`. **Never `sleeper_id`.**
- `college_identity_review_queue_<run_id>.jsonl` — append-only review candidates (reasoning + flags).
- `college_identity_coverage_matrix_<run_id>.json` — per-run coverage stats.
- `college_identity_failure_report_<run_id>.md` — human-readable rollup.
- `college_identity_promotion_log.jsonl` — append-only **gold-standard** transaction log for all review decisions (can deterministically reconstruct registry + bridge by replay).

**Inviolate in v1 (contract test enforces byte-unchanged):** `app/data/identity/_runs/prospect_registry.json`, `app/data/identity/_runs/composite_registry.json`, `app/data/prospect_alias_bridge.json`. Graduation-at-draft into those is a separate later increment.

## 4. Identity model — HYBRID (two-tier storage + `ConfirmedProspectUuid` newtype)

### 4.1 `prospect_uuid` (the one storage-layer ID)
- **Opaque prefixed UUID4** — format `cpr_<uuid4>` (e.g., `cpr_3f7a9c2b-...`). **Never** a deterministic hash; the registry is the source of truth.
- Minted at **first ingestion (W1)**, after **ambiguity-before-mint** check (§4.3).
- Carries `verification_status: provisional | confirmed | deprecated`. Default `provisional` on mint; only graduates to `confirmed` via the promotion script (§6).

### 4.2 Registry entry shape
On top of the `NormalizedCollegeProspectRow` fields (§2), every registry entry adds:
- `prospect_uuid: str` (`cpr_<uuid4>`)
- `verification_status: "provisional" | "confirmed" | "deprecated"`
- `match_key: str` — deterministic hash of `(normalized_name, position_group, draft_class)`. **Lookup/grouping key only; NEVER an identity key.**
- `status_history: list[StatusHistoryEntry]` — append-only summary of state transitions (per-row cache of the promotion log).
- `merged_into_prospect_uuid: str | None` — redirect target for deprecated rows that merged into a survivor.
- `reviewer_id: str` (default `"davidleess"`) and `reviewer_metadata: dict[str, Any]` (empty v1) — captured at every confirm/merge/split/deprecate event.

### 4.3 Ambiguity-before-mint contract
On every ingestion attempt:
1. Compute `match_key` for the incoming row.
2. Look up existing registry rows with the same `match_key`.
3. **Zero matches**: mint a new `prospect_uuid` (`provisional`).
4. **Exactly one match** with the same `source_record_id` + `source_snapshot_id`: idempotent rerun → reuse existing `prospect_uuid` unchanged.
5. **Exactly one match** with a different `source_record_id`: **do NOT auto-merge**. Mint a new provisional `prospect_uuid`, emit review-queue entry flagged `common_name` linking the two; reviewer decides MERGE_INTO or keep separate.
6. **Multiple matches**: never auto-pick; mint a new provisional `prospect_uuid` and emit review-queue entry flagged `ambiguous_existing_candidates` with all candidates listed.

**Critical invariant:** `match_key` is a candidate **grouping** key, never an identity key. Two real Mike Williams WR 2027 keep two distinct `prospect_uuid`s sharing one `match_key` until review confirms otherwise.

### 4.4 `ConfirmedProspectUuid` typed wrapper (the API-boundary safety mechanism)

A Pydantic class / strict-type wrapper around the underlying `cpr_<uuid4>` string:

```python
class ConfirmedProspectUuid:
    def __init__(self, uuid_str: str, *, registry: CollegeProspectRegistry):
        row = registry.get(uuid_str)
        if row is None:
            raise UnknownProspectUuid(uuid_str)
        if row["verification_status"] != "confirmed":
            raise ProspectUuidNotConfirmed(uuid_str, row["verification_status"])
        if row.get("merged_into_prospect_uuid"):
            raise ProspectUuidDeprecatedMerged(uuid_str, row["merged_into_prospect_uuid"])
        self._value = uuid_str
```

**Python-honest framing:** this is **runtime validation at construction**, NOT compile-time enforcement. A developer who bypasses construction by passing a raw `str` violates the contract. The defenses (repo-honest for v1):
- **Contract tests** inspect public consumer signatures (via `inspect.signature` / type-hint introspection) and behavior to assert that every runtime resolver / consumer API requires a `ConfirmedProspectUuid` parameter, not a raw `str`. This is the v1-realistic enforcement: contract-tested, not gated by a tooling layer the repo doesn't yet run.
- **Documentation** in this spec and on every consumer's docstring: "never construct from raw string; always go through the resolver."
- Runtime `__init__` raises on every status that isn't `confirmed` — the real enforcement.
- **Future hardening (out of scope for v1, called out for visibility):** a repo-wide `mypy --strict` or `pyright` gate would lift the signature-check from contract tests into the static-checker layer. Introducing that gate is a repo-wide tooling addition, not a free win — it would need its own scoping increment.

### 4.5 Six locked spec contracts (binding)
1. Same `source_record_id` + same `source_snapshot_id` reruns idempotently to the same `prospect_uuid` row.
2. Same `match_key` + different `source_record_id` does **NOT** auto-merge; mint provisional + flag.
3. `ConfirmedProspectUuid` cannot be constructed from `provisional` or `deprecated` rows.
4. All runtime resolver / consumer APIs require `ConfirmedProspectUuid` (or explicitly return `unresolved`).
5. Confirm / deprecate / merge / split / redirect events are **append-only** to `status_history`; never destructive rewrites.
6. `match_key` is documented (in code + this spec) as a candidate grouping key, never an identity key.

### 4.6 Five provisional-leak safety contracts
1. `ConfirmedProspectUuid.__init__` rejects `provisional`, `deprecated`, **and** unknown UUIDs; follows redirects only if explicitly allowed.
2. Runtime resolver APIs never return raw `prospect_uuid` for `provisional`/`deprecated` rows — return `unresolved` instead.
3. Bridge entries pointing to a non-`confirmed` `prospect_uuid` **fail validation** at write time (promotion script rejects).
4. **`source_record_id` maps to at most one active `confirmed` `prospect_uuid`** (uniqueness invariant; validated post-promotion).
5. Promotion script validates the **whole identity graph** after mutation (registry, bridge, log all consistent) before atomic `os.replace`.

## 5. Matcher (discovery-only, fail-closed)

The matcher generates **candidate suggestions** for the review queue. It is **never** a resolver and **never** auto-resolves identity.

### 5.1 Algorithm
- **Primary:** Jaro-Winkler on `normalized_name` (library: `jellyfish`).
- **Secondary:** token-set ratio on the same normalized name (library: `rapidfuzz`).
- **Normalization (v1, exact):** identical to the existing `prospect_identity_resolver.normalize_name` — lowercase, strip non-alphanumeric-non-space chars, trim. **No suffix stripping in v1** (the existing function does not strip `Jr./Sr./II/III` and the non-goal in §1 keeps existing resolver behavior unchanged). Suffix variants (`Marvin Harrison Jr.` vs `Marvin Harrison`) are handled by **alias-bridge entries / review-queue confirmation**, not by a divergent matcher-only normalization. If suffix-stripping ever becomes desirable, it must be a deliberate later increment: introduce a new shared normalization helper, migrate both the existing Sleeper-side resolver and the new college-side resolver in the same PR, with explicit regression tests proving no existing Sleeper-overlay behavior breaks. **Not in scope for v1.**
- **No double-metaphone in v1.** Phonetic matching adds review-queue noise; revisit if review log shows repeated phonetic misses JW/token-set wouldn't catch.

### 5.2 Score composition (locked)
```python
name_base = 0.75 * jw_score + 0.25 * token_set_score        # blend, NOT max()
final_score = clamp(name_base + position_bonus + school_bonus, 0.0, 1.0)
```
- `position_bonus`: **`+0.10`** if `position_group` exact match else `0.0`.
- `school_bonus`: **`+0.05`** if `current_school` exact match OR overlap with `prior_schools`, else `0.0`.
- `draft_class` mismatch: **`final_score = 0.0`** (hard filter — never cross-class).
- `0.75`/`0.25` blend over `max(JW, token_set)`: token-set can over-credit reordered/shared tokens; the blend keeps JW dominant.

**All weights live in a versioned config block** in the module, not scattered hardcoded literals. They are **v1 defaults pending real review-log calibration** — tuning later is a config change, not a code change.

### 5.3 Position taxonomy + transitions
**Position-group whitelist (offense-only v1):**
- `WR ↔ TE` · `WR ↔ RB` · `FB ↔ RB` (only if `FB` exists in normalized taxonomy)

Cross-position transitions in the whitelist may surface as candidates **only if `final_score ≥ 0.90`**, and always carry the `cross_position_group` + `position_transition_allowed` flags. Defensive pairs (DE↔DT, EDGE↔OLB, CB↔S, ATH↔* etc.) added when defensive ingestion enters scope as a separate config + tests increment.

**Position-group hard-blocks (`final_score = 0`, never surface):**
- `QB ↔ anything else` (never)
- `OL` / `OT` / `OG` / `C` ↔ anything (never)
- `K` / `P` / `LS` ↔ anything (never)
- Any defensive group (`DL`, `DT`, `DE`, `EDGE`, `OLB`, `LB`, `CB`, `S`, `DB`) ↔ any offensive skill (`QB`, `RB`, `WR`, `TE`) (never)

The whitelist + hard-block list are **direction-insensitive** (normalized as sorted tuples / frozensets).

### 5.4 Review-queue surfacing
For each ingested source row, after `ambiguity-before-mint` (§4.3) emits a candidate-comparison need:
- **Candidate query (explicit shape):** since `match_key` includes `position_group` by construction, a literal same-`match_key` lookup misses whitelist neighbors. Instead the candidate query is: **existing registry rows where `normalized_name` matches AND `draft_class` matches AND `position_group` is either the same OR in the whitelist transition map for the incoming row's position_group.** Same-`match_key` is a subset of this query (when both positions match exactly); whitelist neighbors broaden it to allowed cross-group transitions only.
- Compute `final_score` for each row returned by that query.
- Surface **top-3 candidates above `final_score ≥ 0.80`** as review-queue entries.
- If best score is in **`0.80 ≤ score < 0.88`** → entry carries `low_confidence` flag.
- If top-2 candidates within margin `≤ 0.05` → entry carries `ambiguous_near_tie` + `common_name` flags.
- If `0` candidates above `0.80` → no review entry; proceed to mint a new provisional `prospect_uuid` (§4.3 step 3).

### 5.5 `source_id_conflict` hard block
If a new ingestion row shares `source_record_id` (or known `cfbd_athlete_id`) with a registry row but points to a different `prospect_uuid`: **hard block from normal candidate output**. Routes to a dedicated `source_id_conflict` queue for manual investigation. Never a fuzzy candidate.

### 5.6 Risk-flag enum
Every review-queue entry carries one or more:
- `common_name` — multiple existing candidates share `match_key`
- `cross_position_group` — whitelist transition (must be in §5.3 whitelist)
- `position_transition_allowed` — paired with `cross_position_group`
- `transfer_school` — `current_school` ≠ any `prior_schools` but name+position match
- `low_confidence` — score in `[0.80, 0.88)`
- `ambiguous_near_tie` — top-2 within 0.05 margin
- `name_token_mismatch` — JW high but token-set low, or vice versa
- `missing_school` — `current_school` empty
- `missing_position_group` — position couldn't be normalized to a group
- `missing_cfbd_coverage` — no `cfbd_athlete_id` available
- `class_boundary_blocked` — **diagnostic-only** count of cross-class hard-blocked candidates (not a review-queue entry; emitted in coverage matrix)

### 5.7 Audit-trail per candidate (locked)
Each review-queue row stores:
- `matcher_algorithm_version: str` (e.g., `cpr_matcher_v1.0.0`) — **pinned at write-time, never re-scored on algorithm change**.
- `match_score: float` (final)
- `score_breakdown: dict[str, float]` — JW base, token-set base, blended name, position bonus, school bonus, total
- `raw_match_features: dict[str, Any]` — raw `prospect_name`, `position`, `school`, `draft_class` at the moment of matching. **Mock sources edit text retroactively; raw-features-at-match-time preserves audit even when upstream drifts.**

## 6. Review-queue lifecycle — `promote_review_candidate.py`

### 6.1 The script is the only blessed write path
```
scripts/promote_review_candidate.py <review_id> <decision> [--reviewer <id>] [--evidence <text>] [--note <text>]
```
Hand-editing the registry, bridge, or log is **not** an equal path. Validation rejects manual edits that bypass the script.

### 6.2 Five reviewer decisions
- **`confirm`** — has two distinct shapes the script must distinguish on a `--target` flag:
  - **`confirm --target self`** (no candidate involved): the row itself is confirmed as a new standalone identity. Sets *its own* row's `verification_status = confirmed`; no bridge mapping written (the row IS the identity).
  - **`confirm --target <existing_prospect_uuid>`** (candidate match): this source row IS the same person as an existing registry row. Adds `college_alias_bridge.json` entry mapping `(match_key, source_record_id)` → `<existing_prospect_uuid>`; the **existing target row** becomes `verification_status = confirmed` (if not already); the incoming source row is treated as an alias-resolved alternate, not a separate confirmed identity.
  - Either way: archive the review row; append `promotion_log` event with both `target_prospect_uuid` and `source_prospect_uuid` (the incoming row's provisional UUID) so replay is unambiguous.
- **`reject`** — not a match. Review row marked rejected; source row stays as its own `provisional` (or becomes a new one via §4.3).
- **`defer`** — needs more info. Review row stays open with a note; no identity mutation.
- **`merge_into <survivor_prospect_uuid>`** — this prospect IS the same person as another existing `prospect_uuid` (typically spelling-drift convergence across sources). Emits merge ledger entry; deprecated UUID redirects via `merged_into_prospect_uuid`. **Requires non-empty `--evidence`** (symmetric with `split`; equal identity-collision risk if wrongly merged).
- **`split <new_full_name> <new_position> [...]`** — an existing `prospect_uuid` actually represents two distinct people. Mints a new `prospect_uuid` for the second; original retains UUID by primary-spelling / most-mock-data rule; "split from X" lineage in promotion log. **Requires non-empty `--evidence`** (Gemini's gate: distinct CFBD athlete IDs, birth dates, or other verified disambiguators).

### 6.3 Three-point logging (the "gold standard")
1. **`college_identity_promotion_log.jsonl`** — append-only, **single source of truth for review decisions**. Every promotion event captures: `event_id`, `review_id`, `decision`, `reviewer_id`, `reviewer_metadata`, `decided_at`, `source_record_id`, `source_snapshot_id`, `before_status`, `after_status`, `prospect_uuid(s) involved` (target + survivor + redirect targets), `evidence` (required for `merge_into`/`split`), `note`. **Replay semantics (precise):** the promotion log replays *over the genesis registry/bridge state* (the state produced by the most recent fixture ingestion) and deterministically reconstructs the current registry + bridge. Initial fixture ingestion is **not** itself a promotion-log event — it's the genesis state the log replays over. (A future increment could log ingestion events too, but v1 does not.)
2. **`registry.status_history`** — per-row append-only list of `{event_id, decision, after_status, decided_at, reviewer_id}` — local-inspection cache for `ConfirmedProspectUuid` construction checks.
3. **`review_queue` closure marker** — `decided_at` + `decision` + `event_id` appended on the original review-queue row.

### 6.4 Write order: validate-then-replace, per-file atomicity + recovery contract
**Honest about the boundary:** `os.replace` is **per-file atomic only**; a multi-file artifact set is **not cross-file transactional in v1**. A crash between two `os.replace` calls can leave the artifact set partially updated. The recovery contract below (idempotent rerun + post-run validation) is how we tolerate that without a cross-file transaction layer.

Concretely:
1. Build new content for **all** affected artifacts (`promotion_log`, `registry`, `bridge`, `review_queue` closure marker) in memory; serialize each to a sibling `*.tmp` file.
2. **Validate the full identity graph in memory before any replace** — `ConfirmedProspectUuid` would still construct cleanly for all confirmed rows; bridge targets all reference confirmed (non-deprecated) UUIDs; `source_record_id` uniqueness invariant holds; promotion-log-replay over the genesis-state would reproduce the new registry/bridge byte-for-byte. **Any validation failure aborts before any `os.replace`** — no artifact has changed on disk.
3. Apply `os.replace` to each artifact in **dependency-safe order**: `promotion_log` → `registry` → `bridge` → `review_queue` closure. Each call is per-file atomic. **No claim of cross-file atomicity.**
4. **Recovery contract** (covers the per-file crash window in step 3):
   - **Idempotent rerun** — same `review_id` + same decision → no-op. A crashed run can be safely re-invoked; the script detects which artifacts already reflect the event (via `event_id` lookup in `promotion_log` and `status_history`) and completes only the remaining replaces.
   - **Post-run validation** — the script's last action is a full identity-graph re-validation reading from the on-disk artifacts; any inconsistency surfaces immediately as a non-zero exit + explicit diagnostic (no silent partial state).
   - Conflicting rerun (e.g., previously `confirm`, now `reject`) → fail closed; requires explicit `--override` flag (future tool).
5. (Future hardening, out of scope for v1: a cross-file transaction layer — e.g., write-ahead log of intended replaces, or a single-file artifact bundle — would lift this to true multi-file atomicity. v1 accepts per-file atomicity + the recovery contract above.)

### 6.5 Ingestion follows the same atomicity contracts
The fixture-loader (`scripts/ingest_college_prospect_fixture.py`) and any future CFBD adapter follow the **same** write-tmp-rename + idempotency contract. Fixture-load → matcher candidates → review-queue write happens as one atomic artifact-set transaction. Inconsistent atomicity across write paths is a real risk; **the spec locks parity.**

## 7. v1 data load scope

- **Top-100 2027 prospects** in `resources/college_prospect_fixture_2027.json`. Covers fantasy-relevant 12T × 3-round dynasty rookie window (36 hard-relevant + sleeper/bust-out buffer that moves into top-36 over the cycle).
- **Historical 2018–2026 backfill: deferred** to S4's backtest data-load increment (where the backfill has a direct purpose and its own validation gates).
- **Class-agnosticism** is proven by **synthetic** unit tests (deliberately constructed multi-class edge cases) — *not* by populating real historical data.

## 8. Downstream consumption sketch (non-binding pseudocode)

**This section is non-binding pseudocode** illustrating how Engine A near-class scoring (deferred to a later increment) would consume `ConfirmedProspectUuid`. **Engine A is not changed in this spec.** `ConfirmedProspectUuid` is an **identity gate and lookup key, not a new model feature.**

```python
# Eventual Engine A near-class consumer (later increment):
def score_near_class_prospect(source_row: dict, registry: CollegeProspectRegistry) -> Optional[ProspectScore]:
    # 1. Resolve identity (fail-closed; raises if not confirmed)
    try:
        confirmed_uuid = resolve_prospect_cfbd_athlete_id(
            name=source_row["name"],
            position=source_row["position"],
            draft_class=source_row["draft_class"],
            registry=registry,
        )
    except (UnknownProspectUuid, ProspectUuidNotConfirmed, ProspectUuidDeprecatedMerged):
        return None  # unresolved → no Engine A score; overlay-only caveat

    # 2. Load confirmed registry row (features, NOT identity logic here)
    row = registry.get_confirmed(confirmed_uuid)

    # 3. Pass NORMAL feature inputs to existing Engine A scoring (no schema change)
    features = build_engine_a_features_from_row(row, projected_nfl_pick=source_row["projected_pick"])
    return engine_a.score_prospect(position=row["position"], features=features)
```
Key: `ConfirmedProspectUuid` gates the identity lookup; Engine A's existing `score_prospect` interface is unchanged.

## 9. Governance & guardrails

- **Read-only of any external source** in v1 (manual fixture); no network in tests.
- **No mock/ADP/market data in the identity registry.** Mock sources can *discover* names that need identity resolution; the registry stores only identity truth (names, positions, schools, source-IDs). Tested explicitly.
- **No Engine A/B / model-training feed.** Substrate is identity infrastructure; tests assert MFL-leakage-gate-style barriers extended to college-side IDs.
- **Frontend HOLD intact**; NOISE_BAND lock untouched; no model `.pkl` / manifest / contract changes.
- **Existing `prospect_identity_resolver.py` behavior unchanged** — `resolve_prospect_sleeper_id` continues to serve the Sleeper post-draft case identically; new `resolve_prospect_cfbd_athlete_id` is a sibling, not a refactor.
- **Existing `prospect_registry.json` / `composite_registry.json` / `prospect_alias_bridge.json` byte-unchanged** — contract test enforces.

## 10. Testing — organized by module (~50+ tests in v1)

Group tests by module per Codex's plan-organization recommendation. Build plan will follow this grouping.

### 10.1 Schema / registry
- `NormalizedCollegeProspectRow` shape validation (required + nullable fields, provenance per ID)
- Registry round-trip serialization
- `status_history` append-only invariant (no destructive rewrites)
- Empty/missing fixture file = no-op load
- CFBD-shape contract test: a fixture row built from documented CFBD response fields validates against the schema (no schema migration when v2 ships)

### 10.2 Matcher
- JW + token-set blend (0.75/0.25) over `max()` regression
- `+0.10` position bonus / `+0.05` school bonus, clamped [0,1]
- `draft_class` mismatch → score 0 (hard filter)
- Top-3 above 0.80; low-confidence band `[0.80, 0.88)`; `ambiguous_near_tie` margin
- `raw_match_features` captured at match time; `matcher_algorithm_version` pinned
- Synthetic multi-class behavior (class-agnosticism)

### 10.3 Whitelist / hard-block
- Whitelist surfaces: `WR↔TE`, `WR↔RB`, `FB↔RB` at `≥ 0.90` with `cross_position_group` + `position_transition_allowed` flags
- **Mike-Williams-QB-vs-WR regression**: `QB↔WR` hard-blocked even with perfect name + school match
- `OL/OT/OG/C ↔ anything` hard-blocked
- `K/P/LS ↔ anything` hard-blocked
- Any defensive group ↔ offensive skill hard-blocked
- Direction-insensitivity (`(WR, TE)` == `(TE, WR)` in whitelist lookup)

### 10.4 `ConfirmedProspectUuid`
- Construction succeeds only on `confirmed` rows
- Raises `UnknownProspectUuid`, `ProspectUuidNotConfirmed`, `ProspectUuidDeprecatedMerged` on the respective failures
- Redirects followed only when explicitly allowed
- Signature/introspection contract test that public runtime consumers require `ConfirmedProspectUuid`, not raw `str`; no `mypy`/`pyright` gate in v1.

### 10.5 Ingestion atomicity / idempotency
- Fixture loader uses write-tmp-rename
- Same `source_record_id` + `source_snapshot_id` re-ingest → no-op (idempotent)
- Same `match_key` + different `source_record_id` → new provisional `prospect_uuid`, `common_name` review entry, NOT auto-merge
- Multiple existing matches → `ambiguous_existing_candidates` review entry, no auto-pick

### 10.6 Promotion lifecycle (script)
- `confirm` happy path → `verification_status=confirmed`, bridge entry, status_history, promotion_log all in sync
- `reject` → review closed, no identity mutation
- `defer` → review stays open with note
- `merge_into` requires non-empty `--evidence` (test failure when omitted)
- `split` requires non-empty `--evidence` + surviving-key determinism
- Idempotent rerun (same `review_id` + same decision) → no-op
- Conflicting rerun (`confirm` then `reject`) → fail closed; requires `--override`
- Promotion log replay deterministically reconstructs registry + bridge

### 10.7 Audit / coverage / provisional-leak
- All 5 provisional-leak contracts (§4.6) — one test each
- **`source_record_id` ≤ 1 active confirmed `prospect_uuid`** invariant
- Bridge entry validation rejects non-confirmed targets
- Coverage matrix per-run counts reconcile (`matched + provisional + duplicate + ...` = `total_input_rows`)
- **Existing artifacts byte-unchanged contract test:** `prospect_registry.json`, `composite_registry.json`, `prospect_alias_bridge.json` SHA256 before/after any S3 script run is identical
- No mock/ADP/market field in any registry/bridge/review entry (leakage-gate-style assertion)

## 11. Forward notes (acknowledged, deferred)

- **Scale:** local-first JSON registry/bridge/review_queue is correctly sized for v1's ~100 prospects. **Revisit with SQLite or per-class partitioning if total registry rows exceed ~5k**, or if concurrent writes become a real issue. Not a v1 blocker.
- **Graduation-at-draft script** (college → NFL-side `prospect_registry.json` + `prospect_alias_bridge.json` with confirmed `sleeper_id`): deferred to a separate later increment. Spec records the intent; v1 does not write to those files.
- **CFBD adapter (v2 increment):** opens with explicit CFBD ToS verification for *identity-registry use* (the existing seasonal-feature ToS clearance does not cover this pattern); then emits the same `NormalizedCollegeProspectRow` shape locked in §2 — zero schema migration.
- **Defensive whitelist** (DE↔DT, EDGE↔OLB, CB↔S, ATH↔*, etc.) added in the defense-ingestion increment with its own config + tests.
- **Historical 2018–2026 backfill** for the S4 backtest harness lands with that increment.

## 12. Counter-argument (Rule 5 — mandatory)

1. **Substrate without a consumer might be premature.** Increment A's actual product use (Engine A near-class scoring) is a later increment. Why build identity now? *Mitigation:* the reconciliation (4-way triangulated) and both research reports agreed identity is the foundational dependency for both S1 (aggregation) and S4 (backtest), and it has the longest lead-time to get right. Building it first de-risks everything downstream. Substrate has clear unit-test coverage; it doesn't require a consumer to be valid.
2. **Manual fixture might bias the substrate to whatever I curate.** *Mitigation:* the CFBD-shape contract test forces the schema to accept exactly what a future CFBD adapter would produce; synthetic tests cover edge cases beyond the fixture; ingestion contracts are class-agnostic and source-agnostic by design.
3. **The "type safety" of `ConfirmedProspectUuid` is weaker than the cockpit initially treated it.** *Mitigation explicit in this spec (§4.4):* it's runtime validation at construction in Python, *not* compile-time. Defenses are layered: `__init__` raises; contract tests inspect public consumer signatures and behavior; docs warn against raw-string construction; `mypy`/`pyright` is future hardening out of scope for v1. Stronger than no protection; honest about what Python can enforce.
4. **`source_id_conflict` hard block might mask real data we want to see.** *Mitigation:* the conflict is routed to a dedicated investigation queue (not silently dropped); coverage matrix counts it; reviewer can manually inspect and decide (manual bridge entry, deprecation, or split).
5. **The test surface (~50+) is substantial for a "substrate-only" v1.** *Mitigation:* honest in §10; build plan organizes tests by module; the alternative (fewer tests) would risk the silent-identity-corruption failure mode the resolver docstring explicitly warns against ("wrong joins corrupt market overlay data silently, which is worse than a null overlay"). Test depth is the price of identity correctness.
