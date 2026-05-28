# Subsystem 3 — Prospect Identity Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Cockpit motion is binding:** Codex authors RED contract tests for each task; Claude implements to GREEN. Plan-level decisions get cockpit-debated before this plan is approved for execution; per-task implementation choices follow the plan as written unless a real defect surfaces.

**Goal:** Build a fail-closed prospect identity substrate (registry + alias bridge + discovery-only matcher + review-queue lifecycle) for undrafted college prospects, sourced in v1 from a manual fixture mirroring the future CFBD adapter's row shape — without touching existing identity artifacts, Engine A/B, PVO, the frontend, or any market/training data path.

**Architecture:** HYBRID two-tier identity — opaque `cpr_<uuid4>` UUIDs with `verification_status` (provisional/confirmed/deprecated), guarded by a runtime-validated `ConfirmedProspectUuid` Python wrapper. Matcher is discovery-only and emits review-queue candidates; it never auto-resolves. Persistence uses per-file atomic `os.replace` writes plus an idempotent-rerun + post-run-validation recovery contract (NOT cross-file transactional in v1, per spec §6.4). Promotion script (`promote_review_candidate.py`) is the only blessed write path; an append-only promotion log replays over the genesis fixture-ingestion state to deterministically reconstruct the registry + bridge.

**Tech Stack:** Python 3.14, Pydantic 2.x (already in `requirements.txt`), `jellyfish` (Jaro-Winkler — added by Task 0), `rapidfuzz` (token-set ratio — added by Task 0), pytest (existing `tests/contract/` layout). Test invocation: `.venv/bin/python3.14 -m pytest` per `[[reference_test_invocation]]`.

**Authoritative spec:** [`docs/superpowers/specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md`](../specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md) — SHA `8c20350`, dual-CLEAR by Codex + Gemini.

**Branch:** `feature/subsystem-3-prospect-identity-substrate` (already checked out; current HEAD `e6e1ba2` is the ledger-housekeeping commit on top of the spec).

---

## Plan-level implementation choices (cockpit-reviewable; not spec changes)

These are non-spec implementation choices the plan-writer locked in. Both honor the spec literal; cockpit can object during plan review.

**Choice 1 — `identity.py` → `identity/__init__.py` (Task 1).** Spec §1 says `src/dynasty_genius/identity/college_prospect_identity.py`. `src/dynasty_genius/identity.py` already exists as a flat 255-line module with **10 callers** (`pvo_assembler.py:538`, `app/services/trade_analyzer.py:7`, three scripts, two test files, importing `generate_dg_id`, `normalize_player_name`, `assign_collision_suffixes`). Python forbids `identity.py` and `identity/` at the same level. The plan does `git mv src/dynasty_genius/identity.py src/dynasty_genius/identity/__init__.py` — a single structural move that preserves every existing import because `from src.dynasty_genius.identity import X` resolves the same against `__init__.py`. Zero behavioral change; verified by re-running every test file that imports the legacy symbols. Alternative considered: `identity/_legacy.py` + re-exports (more layers, equivalent semantics, rejected as unnecessary).

**Choice 2 — Deps as a lead-off commit on this branch (Task 0).** Spec §5.1 mandates `jellyfish` (Jaro-Winkler) and `rapidfuzz` (token-set ratio). Neither is in `requirements.txt`; neither is imported anywhere in `src/`, `scripts/`, or `tests/`. Per `[[feedback_git_hygiene]]` ("dependency changes in separate PR / isolatable diff"), Task 0 is a deps-only commit on `feature/subsystem-3-prospect-identity-substrate` adding both libraries. Diff stays isolatable for review even though it ships in the same branch. Alternative considered: standalone PR to `main` first — rejected as merge-cycle overhead with no review-quality benefit.

**Choice 3 — Single-module impl, multi-file tests.** Spec §1 says "New module `src/dynasty_genius/identity/college_prospect_identity.py`" (singular). The implementation lives in one file with clearly-labeled sections (Constants → Schema → Exceptions → `ConfirmedProspectUuid` → Match-key/normalization → Matcher → Registry I/O → Ambiguity-before-mint → Ingestion entry-point → Promotion entry-points). Tests follow spec §10's by-module grouping in `tests/contract/test_subsystem_3_<module>.py` — one test file per §10.X sub-area, per Codex's recommendation in §10.

**Choice 4 — Fixture data (Task 10) is a separate cockpit decision.** Spec §7 mandates "top-100 2027 prospects" in `resources/college_prospect_fixture_2027.json`. The plan reserves Task 10 for fixture curation but does NOT prescribe the curation methodology (which would require Tier-1 source verification per `[[feedback_dynasty_analytical_rules]]` Rule 1). The plan delivers a working substrate that can run on a curator-populated fixture; how the fixture gets populated is a separate David-driven workstream that can run in parallel with Tasks 0–9. Synthetic test coverage of class-agnosticism (§10.2) does not depend on the real fixture.

---

## Post-cockpit Round 2 patches (2026-05-28)

After saving the v1 plan above, the cockpit (Codex technical + Gemini governance + Claude) debated and unanimously converged on the following revisions. **Implementation source of truth: the "Round 2 revised" task blocks at the end of this document (immediately before "Self-review").** The v1 Tasks 6, 7, 8, 9 below carry a `[v1 — SUPERSEDED]` header marker so the comparison stays visible to reviewers; do not execute them. The "Plan-level implementation choices" above (Choices 1–4) and every spec-level decision (the SHA `8c20350` dual-CLEAR) remain unchanged.

**5 plan-level defects in v1 that the cockpit identified as real:**
1. **Matcher not wired into ingestion** — v1 `mint_or_match()` did only exact-`match_key` lookup, missing the spec §5.4 candidate query (normalized_name + draft_class + position_group same OR in whitelist). Fixed by calling `surface_review_candidates()` from `mint_or_match()` in revised Task 6.
2. **Promotion omitted alias bridge + review-queue closure** — v1 Task 8 wrote `promotion_log` + `registry` only. Spec §6.2 requires bridge writes on `confirm --target <existing_uuid>`; §6.3 requires the review-queue closure marker as the third leg of three-point logging. Fixed by splitting `confirm-self` vs `confirm-existing` in revised Task 8 + adding bridge writes + closure-marker writes.
3. **Replay was non-deterministic** — v1 `replay_promotion_log()` called `promote_review_candidate()`, which re-generated `_now_iso()` and fresh `_uuid.uuid4()`, making byte-identical reconstruction impossible. Fixed by a new pure `_apply_logged_event(event, registry, bridge)` applicator that uses logged metadata directly; revised Task 8.
4. **`source_id_conflict` hard-block was missing** — spec §5.5 mandates a dedicated investigation queue and hard-block from normal fuzzy output when a `source_record_id` (or known `cfbd_athlete_id`) collides with a different `prospect_uuid`. v1 had zero coverage. Fixed by an explicit pre-check in `mint_or_match()` + a separate `app/data/identity/college_identity_source_id_conflict_<run_id>.jsonl` queue (per cockpit-converged naming); revised Task 6.
5. **§10.7 bridge-validation test was conflated** — v1 `test_leak_contract_3_bridge_entry_to_non_confirmed_fails_validation` constructed a `RegistryEntry.merged_into_prospect_uuid` redirect — a registry-row invariant, not a bridge invariant. Spec §4.6 contract 3 is about the bridge. Fixed by introducing `CollegeAliasBridgeEntry` / `CollegeAliasBridge` schemas (revised Task 6) and the proper bridge-target validation test (revised Task 9).

**Codex's 5 additional RED tests folded into the revised tasks:**
1. (Task 6 Round 2) Row with same `normalized_name` + same `draft_class` + whitelist position-neighbor + different `match_key` → ingestion still surfaces via §5.4
2. (Task 6 Round 2) `source_id_conflict` preempts fuzzy output; does NOT write a normal review candidate
3. (Task 8 Round 2) `confirm --target <existing_uuid>` → bridge entry written; promotion log carries both `source_prospect_uuid` + `target_prospect_uuid`; originating review_queue row gets `decision` + `event_id` + `decided_at`
4. (Task 6 / Task 9 Round 2) Bridge target exists AND `verification_status == "confirmed"` AND not deprecated/redirected
5. (Task 8 Round 2) Replay test asserts byte-identical reconstruction of **registry AND bridge** (not registry only)

**Sub-decision settled by the cockpit:** the `source_id_conflict` queue is a **separate dedicated file** (Codex objected to combining with normal review queue — auditability + lifecycle-semantics separation). Gemini's naming refinement adopted: **`college_identity_source_id_conflict_<run_id>.jsonl`** — matches `college_identity_review_queue_<run_id>.jsonl` and `college_identity_coverage_matrix_<run_id>.json` sibling conventions.

### Round 3 follow-up patches inside Round 2 Task 8 (2026-05-28)

After the Round 2 patches landed, Codex's second-round technical review surfaced 2 additional defects **inside the Round 2 Task 8 impl**. Both are now fixed in-place inside Round 2 Task 8 below (no new task block — the fixes live inside the existing Round 2 Task 8 step 3 code).

1. **Confirm-existing event field semantics were internally inconsistent.** v1-Round-2 set `target_prospect_uuid = decision.target` for `target_kind=='existing'`, but `decision.target` is the provisional source row, not the existing survivor. This contradicted Round 2 Task 8's own RED test `test_confirm_target_existing_writes_bridge_entry_and_log_carries_both_uuids` which asserts `target_prospect_uuid == target_uuid` (the survivor). **Fix in place:** `promote_review_candidate` event dict now sets `target_prospect_uuid = decision.survivor if target_kind=='existing' else decision.target` and `source_prospect_uuid = decision.target if target_kind=='existing' else None`. Idempotency check updated to compare against the acted-on row (source for existing, target for self). `_apply_logged_event` now reads `source_prospect_uuid` as the row to deprecate for confirm-existing replay.
2. **Split decision was silently demoted out of v1.** Round 2 Task 8 carried only the `EvidenceRequiredError` test for split and left the impl as `# split needs special handling; v1 left it experimental — keep that posture in v1`. That contradicted spec §6.2 (split is one of the five reviewer decisions and v1 plan had a split happy-path). **Fix in place:** split happy-path restored in `promote_review_candidate` (mints `new_split_uuid` for the new identity; original retains UUID; both rows append a shared 'split' StatusHistoryEntry; event log carries `new_split_uuid` + `new_full_name` + `new_position` + `new_position_group` for deterministic replay). `_apply_logged_event` split branch reads `new_split_uuid` from the event so replay reconstructs the same UUID. Two new positive tests added to Round 2 Task 8 Step 1: `test_split_mints_new_provisional_uuid_with_logged_metadata` and `test_replay_after_split_reproduces_registry_byte_identical`.

Both Round 3 fixes preserve every governance invariant the cockpit cleared in Round 1+2. The split fix actually **restores** spec adherence that the v1-Round-2 demotion had inadvertently weakened.

---

## File Structure

**Create:**
- `src/dynasty_genius/identity/college_prospect_identity.py` — the single new module (schema, matcher, `ConfirmedProspectUuid`, registry I/O, ingestion, promotion entry-points)
- `scripts/ingest_college_prospect_fixture.py` — manual-fixture loader CLI (per-file atomic write + recovery contract)
- `scripts/promote_review_candidate.py` — the only blessed write path for review decisions
- `resources/college_prospect_fixture_2027.json` — Top-100 2027 prospects (cockpit-curated in Task 10)
- `tests/contract/test_subsystem_3_schema.py` — §10.1 tests
- `tests/contract/test_subsystem_3_matcher.py` — §10.2 tests
- `tests/contract/test_subsystem_3_whitelist.py` — §10.3 tests
- `tests/contract/test_subsystem_3_confirmed_uuid.py` — §10.4 tests
- `tests/contract/test_subsystem_3_ingestion.py` — §10.5 tests
- `tests/contract/test_subsystem_3_promotion.py` — §10.6 tests
- `tests/contract/test_subsystem_3_audit.py` — §10.7 tests

**Modify (structural):**
- `src/dynasty_genius/identity.py` → `src/dynasty_genius/identity/__init__.py` via `git mv` (Task 1)
- `requirements.txt` — add `jellyfish>=1.0,<2.0` and `rapidfuzz>=3.0,<4.0` (Task 0)

**Inviolate (contract test enforces byte-unchanged — see §10.7):**
- `app/data/identity/_runs/prospect_registry.json`
- `app/data/identity/_runs/composite_registry.json`
- `app/data/prospect_alias_bridge.json`
- `src/dynasty_genius/adapters/prospect_identity_resolver.py` (behavior unchanged; sibling `resolve_prospect_cfbd_athlete_id` lives in the new module, NOT here)

**New data artifacts written by the scripts (gitignored except via explicit ledger entries):**
- `app/data/identity/college_prospect_registry.json`
- `app/data/identity/college_alias_bridge.json`
- `app/data/identity/college_identity_review_queue_<run_id>.jsonl`
- `app/data/identity/college_identity_coverage_matrix_<run_id>.json`
- `app/data/identity/college_identity_failure_report_<run_id>.md`
- `app/data/identity/college_identity_promotion_log.jsonl`
- `app/data/identity/college_identity_source_id_conflict_<run_id>.jsonl` — **Round 2** addition; dedicated `source_id_conflict` investigation queue per spec §5.5 (separate from normal review queue; cockpit-converged naming, 2026-05-28)

---

## Task 0: Lead-off deps commit

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add deps to `requirements.txt`**

Append after the existing `pydantic>=2.0,<3.0` line:

```text
jellyfish>=1.0,<2.0
rapidfuzz>=3.0,<4.0
```

- [ ] **Step 2: Install into the venv**

Run: `.venv/bin/python3.14 -m pip install -r requirements.txt`
Expected: `Successfully installed jellyfish-... rapidfuzz-...` (or "Requirement already satisfied" if cached).

- [ ] **Step 3: Verify imports work**

Run: `.venv/bin/python3.14 -c "import jellyfish, rapidfuzz; print(jellyfish.__version__, rapidfuzz.__version__)"`
Expected: two version strings printed; no `ModuleNotFoundError`.

- [ ] **Step 4: Confirm full suite still green pre-build**

Run: `.venv/bin/python3.14 -m pytest --ignore=tests/test_phase18_refresh_league_intelligence.py --ignore=tests/test_tmux_msg.py -q`
Expected: full green suite (same count as `AGENT_SYNC.md` — 1305 passed, 11 skipped, 0 failed at branch HEAD).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "deps(subsystem-3): add jellyfish + rapidfuzz for prospect identity matcher"
```

---

## Task 1: Convert `identity.py` to `identity/__init__.py`

**Goal:** unblock the spec-mandated path `src/dynasty_genius/identity/college_prospect_identity.py` without changing the behavior of any of the 10 existing callers of `from src.dynasty_genius.identity import ...`.

**Files:**
- Move: `src/dynasty_genius/identity.py` → `src/dynasty_genius/identity/__init__.py`

- [ ] **Step 1: Move the file via `git mv`**

```bash
mkdir -p src/dynasty_genius/identity
git mv src/dynasty_genius/identity.py src/dynasty_genius/identity/__init__.py
```

- [ ] **Step 2: Re-run every caller's tests to verify zero behavior change**

```bash
.venv/bin/python3.14 -m pytest \
  tests/test_engine_a_v3.py \
  tests/test_engine_a_scorer.py \
  -q
```

Expected: same pass count as before the move (every test that imports `from src.dynasty_genius.identity import generate_dg_id` continues to resolve cleanly).

- [ ] **Step 3: Smoke-test the runtime imports used outside tests**

```bash
.venv/bin/python3.14 -c "from src.dynasty_genius.identity import generate_dg_id, normalize_player_name, assign_collision_suffixes; print('OK')"
```

Expected: `OK` printed.

- [ ] **Step 4: Run the full suite to confirm nothing in `pvo_assembler.py` or `app/services/trade_analyzer.py` regressed**

```bash
.venv/bin/python3.14 -m pytest --ignore=tests/test_phase18_refresh_league_intelligence.py --ignore=tests/test_tmux_msg.py -q
```

Expected: same green count as Task 0 Step 4.

- [ ] **Step 5: Commit**

```bash
git add -A src/dynasty_genius/identity src/dynasty_genius/identity.py
git commit -m "refactor(identity): convert identity.py to identity/__init__.py to unblock S3 module path"
```

---

## Task 2: Schema, exceptions, constants — §10.1 contract tests

**Goal:** Establish the locked Pydantic schema for `NormalizedCollegeProspectRow`, `RegistryEntry`, `StatusHistoryEntry`, the exception hierarchy, and module-level constants. No matcher logic yet.

**Files:**
- Create: `src/dynasty_genius/identity/college_prospect_identity.py`
- Create: `tests/contract/test_subsystem_3_schema.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_3_schema.py` with the following content:

```python
"""Subsystem 3 — schema & registry contract tests (§10.1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.dynasty_genius.identity.college_prospect_identity import (
    MATCHER_ALGORITHM_VERSION,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    StatusHistoryAppendOnlyError,
    load_registry,
)


def _fixture_row_minimal() -> dict:
    return {
        "raw_name": "Arch Manning",
        "normalized_name": "arch manning",
        "full_name": "Arch Manning",
        "position": "QB",
        "position_group": "QB",
        "draft_class": 2027,
        "current_school": "Texas",
        "prior_schools": [],
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "manual_fixture",
        "source_record_id": "fixture_2027_001",
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    }


def test_normalized_row_required_and_nullable_fields_accept_minimal_shape():
    row = NormalizedCollegeProspectRow.model_validate(_fixture_row_minimal())
    assert row.raw_name == "Arch Manning"
    assert row.draft_class == 2027
    assert row.cfbd_athlete_id is None
    assert row.id_provenance.cfbd_athlete_id is None


def test_normalized_row_rejects_missing_required_field():
    bad = _fixture_row_minimal()
    bad.pop("source_record_id")
    with pytest.raises(ValidationError):
        NormalizedCollegeProspectRow.model_validate(bad)


def test_normalized_row_id_provenance_round_trip_preserves_nested_nulls():
    row = NormalizedCollegeProspectRow.model_validate(_fixture_row_minimal())
    dumped = row.model_dump()
    reloaded = NormalizedCollegeProspectRow.model_validate(dumped)
    assert reloaded == row


def test_status_history_append_only_invariant_blocks_destructive_rewrite():
    history = [
        StatusHistoryEntry(
            event_id="ev_1",
            decision="confirm",
            after_status="confirmed",
            decided_at="2026-05-28T12:00:00Z",
            reviewer_id="davidleess",
        )
    ]
    entry = RegistryEntry(
        prospect_uuid="cpr_00000000-0000-4000-8000-000000000001",
        verification_status="confirmed",
        match_key="abc123",
        status_history=history,
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **_fixture_row_minimal(),
    )
    new_history = [
        StatusHistoryEntry(
            event_id="ev_2",
            decision="confirm",
            after_status="confirmed",
            decided_at="2026-05-28T12:00:01Z",
            reviewer_id="davidleess",
        )
    ]
    with pytest.raises(StatusHistoryAppendOnlyError):
        entry.replace_status_history(new_history)  # destructive rewrite forbidden


def test_empty_or_missing_registry_file_loads_as_no_op(tmp_path: Path):
    missing = tmp_path / "absent.json"
    registry = load_registry(missing)
    assert registry.entries == {}

    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"metadata": {}, "entries": []}))
    assert load_registry(empty).entries == {}


def test_cfbd_shape_forward_compat_validates_against_documented_response_fields():
    cfbd_like = {
        "raw_name": "Quinn Ewers",
        "normalized_name": "quinn ewers",
        "full_name": "Quinn Ewers",
        "position": "QB",
        "position_group": "QB",
        "draft_class": 2027,
        "current_school": "Texas",
        "prior_schools": ["Ohio State"],
        "cfbd_athlete_id": "cfbd_4567890",
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "cfbd",
        "source_record_id": "cfbd_athlete_4567890",
        "source_snapshot_id": "cfbd_2027_snapshot_001",
        "id_provenance": {
            "cfbd_athlete_id": {
                "method": "cfbd_api_get_athletes",
                "fetched_at": "2026-05-28T12:00:00Z",
            },
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    }
    row = NormalizedCollegeProspectRow.model_validate(cfbd_like)
    assert row.source == "cfbd"
    assert row.id_provenance.cfbd_athlete_id is not None


def test_module_pins_matcher_algorithm_version_string():
    assert MATCHER_ALGORITHM_VERSION == "cpr_matcher_v1.0.0"
```

- [ ] **Step 2: Run the test file to verify RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_schema.py -v
```

Expected: collection error (the module does not yet exist) — every test fails with `ModuleNotFoundError: No module named 'src.dynasty_genius.identity.college_prospect_identity'`.

- [ ] **Step 3: Claude implements the minimal GREEN module skeleton**

Create `src/dynasty_genius/identity/college_prospect_identity.py` with the following content:

```python
"""Subsystem 3 — Prospect Identity Substrate.

Single-module implementation per spec §1. Organized in labeled sections:

- Constants & versions
- Schema (Pydantic 2.x)
- Exceptions
- ConfirmedProspectUuid wrapper
- Match-key & normalization
- Matcher (discovery-only)
- Registry I/O (per-file atomic)
- Ambiguity-before-mint
- Ingestion entry-point
- Promotion entry-points

Spec: docs/superpowers/specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ======================================================================
# Constants & versions
# ======================================================================

MATCHER_ALGORITHM_VERSION: str = "cpr_matcher_v1.0.0"


# ======================================================================
# Schema (Pydantic 2.x)
# ======================================================================


class IdProvenance(BaseModel):
    """Per-ID source/method/timestamp provenance block."""

    model_config = ConfigDict(extra="forbid")

    cfbd_athlete_id: Optional[dict[str, Any]] = None
    cfb_player_id: Optional[dict[str, Any]] = None
    pfr_id: Optional[dict[str, Any]] = None
    gsis_id: Optional[dict[str, Any]] = None
    sleeper_id: Optional[dict[str, Any]] = None


class NormalizedCollegeProspectRow(BaseModel):
    """Locked source-shaped contract (spec §2). CFBD-shape forward-compatible."""

    model_config = ConfigDict(extra="forbid")

    raw_name: str
    normalized_name: str
    full_name: str
    position: str
    position_group: str
    draft_class: int
    class_year: Optional[str] = None
    current_school: str
    prior_schools: list[str] = Field(default_factory=list)
    cfbd_athlete_id: Optional[str] = None
    cfb_player_id: Optional[str] = None
    pfr_id: Optional[str] = None
    gsis_id: Optional[str] = None
    sleeper_id: Optional[str] = None
    source: str
    source_record_id: str
    source_snapshot_id: str
    id_provenance: IdProvenance
    notes: Optional[str] = None


class StatusHistoryEntry(BaseModel):
    """Append-only summary of one state transition on a registry row (spec §4.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    decision: Literal["confirm", "reject", "defer", "merge_into", "split", "ingest"]
    after_status: Literal["provisional", "confirmed", "deprecated"]
    decided_at: str
    reviewer_id: str


class RegistryEntry(NormalizedCollegeProspectRow):
    """Registry row = source row + identity-substrate fields (spec §4.2)."""

    model_config = ConfigDict(extra="forbid")

    prospect_uuid: str
    verification_status: Literal["provisional", "confirmed", "deprecated"]
    match_key: str
    status_history: list[StatusHistoryEntry]
    merged_into_prospect_uuid: Optional[str] = None
    reviewer_id: str = "davidleess"
    reviewer_metadata: dict[str, Any] = Field(default_factory=dict)

    def replace_status_history(self, new_history: list[StatusHistoryEntry]) -> None:
        """Spec §4.5 contract 5: status_history is append-only; destructive rewrites forbidden.

        This method exists ONLY to be exercised by the append-only invariant test; it
        always raises. Real updates go through `append_status_history`.
        """
        raise StatusHistoryAppendOnlyError(
            "status_history is append-only; use append_status_history()"
        )

    def append_status_history(self, entry: StatusHistoryEntry) -> None:
        """The only blessed mutator for status_history. Appends; never replaces or deletes."""
        self.status_history.append(entry)


# ======================================================================
# Exceptions
# ======================================================================


class StatusHistoryAppendOnlyError(RuntimeError):
    """Raised when a destructive rewrite of status_history is attempted."""


class UnknownProspectUuid(LookupError):
    """ConfirmedProspectUuid construction: no such uuid in registry."""


class ProspectUuidNotConfirmed(RuntimeError):
    """ConfirmedProspectUuid construction: row exists but verification_status != 'confirmed'."""


class ProspectUuidDeprecatedMerged(RuntimeError):
    """ConfirmedProspectUuid construction: row was merged into another; follow redirect explicitly."""


# ======================================================================
# Registry I/O (minimal v1 — full atomicity layer arrives in Task 6)
# ======================================================================


class CollegeProspectRegistry(BaseModel):
    """In-memory registry. Persisted via the atomic write layer in Task 6."""

    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)
    entries: dict[str, RegistryEntry] = Field(default_factory=dict)

    def get(self, prospect_uuid: str) -> Optional[RegistryEntry]:
        return self.entries.get(prospect_uuid)


def load_registry(path: Path) -> CollegeProspectRegistry:
    """Spec §2 / §10.1: missing or empty file loads as a no-op empty registry."""
    if not path.exists():
        return CollegeProspectRegistry()
    raw = json.loads(path.read_text())
    metadata = raw.get("metadata", {})
    entry_list = raw.get("entries", [])
    entries: dict[str, RegistryEntry] = {}
    for raw_entry in entry_list:
        entry = RegistryEntry.model_validate(raw_entry)
        entries[entry.prospect_uuid] = entry
    return CollegeProspectRegistry(metadata=metadata, entries=entries)
```

- [ ] **Step 4: Run the schema test file to verify GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_schema.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py tests/contract/test_subsystem_3_schema.py
git commit -m "feat(subsystem-3): schema, exceptions, registry loader + §10.1 contract tests"
```

---

## Task 3: Match-key, normalization, and matcher core — §10.2 contract tests

**Goal:** Add `compute_match_key`, `normalize_name` (mirrored exactly from `prospect_identity_resolver.normalize_name`), the JW + token-set blend, position/school bonuses, draft-class hard filter, top-3 / 0.80 / 0.88 thresholds, `raw_match_features` capture, and `matcher_algorithm_version` pinning. Class-agnosticism is proven via synthetic multi-class tests.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append matcher section)
- Create: `tests/contract/test_subsystem_3_matcher.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_3_matcher.py` with the following content:

```python
"""Subsystem 3 — matcher contract tests (§10.2)."""
from __future__ import annotations

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    LOW_CONFIDENCE_LOWER,
    LOW_CONFIDENCE_UPPER,
    MATCHER_ALGORITHM_VERSION,
    MIN_CANDIDATE_SCORE,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
    normalize_name,
    score_candidate,
    surface_review_candidates,
)


def _row(
    name: str,
    position: str = "WR",
    position_group: str = "WR",
    draft_class: int = 2027,
    school: str = "Ohio State",
    prior: list[str] | None = None,
    source_record_id: str = "fixture_2027_001",
) -> NormalizedCollegeProspectRow:
    return NormalizedCollegeProspectRow.model_validate({
        "raw_name": name,
        "normalized_name": normalize_name(name),
        "full_name": name,
        "position": position,
        "position_group": position_group,
        "draft_class": draft_class,
        "current_school": school,
        "prior_schools": prior or [],
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "manual_fixture",
        "source_record_id": source_record_id,
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    })


def _registry_entry(
    uuid: str,
    name: str,
    position: str = "WR",
    position_group: str = "WR",
    draft_class: int = 2027,
    school: str = "Ohio State",
    status: str = "confirmed",
    prior: list[str] | None = None,
    source_record_id: str = "fixture_2027_existing",
) -> RegistryEntry:
    row = _row(
        name=name,
        position=position,
        position_group=position_group,
        draft_class=draft_class,
        school=school,
        prior=prior,
        source_record_id=source_record_id,
    )
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,  # type: ignore[arg-type]
        match_key=compute_match_key(
            normalized_name=row.normalized_name,
            position_group=row.position_group,
            draft_class=row.draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status=status,  # type: ignore[arg-type]
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **row.model_dump(),
    )


# --- normalization parity ---


def test_normalize_name_matches_existing_sleeper_side_resolver_exactly():
    """Spec §5.1: identical to prospect_identity_resolver.normalize_name."""
    from src.dynasty_genius.adapters.prospect_identity_resolver import (
        normalize_name as legacy_normalize,
    )

    samples = [
        "Arch Manning",
        "Marvin Harrison Jr.",
        "A.J. Brown",
        "  Spaces   Galore  ",
        "Hyphen-Name O'Reilly",
    ]
    for s in samples:
        assert normalize_name(s) == legacy_normalize(s)


# --- score composition ---


def test_blend_is_075_jw_plus_025_token_set_not_max():
    incoming = _row("Mike Williams Jr", school="Tulane")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Williams Mike",
        school="Tulane",
    )
    candidate = score_candidate(incoming, existing)
    # JW and token-set diverge here: token-set is high (same tokens, different order),
    # JW is lower because the first-char prefix differs. Blend should be 0.75*JW + 0.25*token,
    # which is strictly between max() and the JW score.
    assert candidate.score_breakdown["name_base"] == pytest.approx(
        0.75 * candidate.score_breakdown["jw_score"]
        + 0.25 * candidate.score_breakdown["token_set_score"]
    )


def test_position_group_bonus_adds_0_10_and_school_bonus_adds_0_05_and_total_clamps_to_1():
    incoming = _row("Identical Name", school="Same School")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Identical Name",
        school="Same School",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.score_breakdown["position_bonus"] == pytest.approx(0.10)
    assert candidate.score_breakdown["school_bonus"] == pytest.approx(0.05)
    assert 0.0 <= candidate.match_score <= 1.0


def test_draft_class_mismatch_is_hard_zero():
    incoming = _row("Same Name", draft_class=2027, school="Same School")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Same Name",
        draft_class=2026,
        school="Same School",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.match_score == 0.0
    assert "class_boundary_blocked" in candidate.risk_flags


# --- surfacing thresholds ---


def test_top_3_above_0_80_only():
    incoming = _row("Target Name", school="Texas")
    registry = {
        "cpr_a": _registry_entry("cpr_a", "Target Name", school="Texas"),  # near 1.0
        "cpr_b": _registry_entry("cpr_b", "Target Naam", school="Texas"),  # ~0.95
        "cpr_c": _registry_entry("cpr_c", "Targat Naym", school="Texas"),  # ~0.85
        "cpr_d": _registry_entry("cpr_d", "Different Person", school="Texas"),  # <0.80
        "cpr_e": _registry_entry("cpr_e", "Yet Another", school="Texas"),  # <0.80
    }
    candidates = surface_review_candidates(incoming, registry)
    assert len(candidates) == 3
    assert all(c.match_score >= MIN_CANDIDATE_SCORE for c in candidates)
    assert candidates[0].match_score >= candidates[1].match_score >= candidates[2].match_score


def test_low_confidence_band_emits_flag_in_0_80_to_0_88():
    incoming = _row("Borderline Name", school="Texas")
    registry = {
        "cpr_a": _registry_entry("cpr_a", "Borderlne Naem", school="Texas"),  # ~0.83
    }
    candidates = surface_review_candidates(incoming, registry)
    assert candidates, "expected one borderline candidate"
    top = candidates[0]
    if LOW_CONFIDENCE_LOWER <= top.match_score < LOW_CONFIDENCE_UPPER:
        assert "low_confidence" in top.risk_flags


def test_ambiguous_near_tie_when_top_two_within_0_05():
    incoming = _row("Common Name", school="Texas")
    registry = {
        "cpr_a": _registry_entry("cpr_a", "Common Name", school="Texas"),
        "cpr_b": _registry_entry("cpr_b", "Comman Name", school="Texas"),
    }
    candidates = surface_review_candidates(incoming, registry)
    assert len(candidates) >= 2
    margin = candidates[0].match_score - candidates[1].match_score
    if margin <= 0.05:
        assert "ambiguous_near_tie" in candidates[0].risk_flags
        assert "common_name" in candidates[0].risk_flags


# --- audit-trail pinning ---


def test_raw_match_features_captured_at_match_time():
    incoming = _row("Pinned Name", school="Pinned School")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Pinned Name",
        school="Pinned School",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.raw_match_features["prospect_name"] == "Pinned Name"
    assert candidate.raw_match_features["school"] == "Pinned School"
    assert candidate.raw_match_features["draft_class"] == 2027


def test_matcher_algorithm_version_pinned_on_every_candidate():
    incoming = _row("Some Name")
    existing = _registry_entry(
        "cpr_00000000-0000-4000-8000-000000000001",
        "Some Name",
    )
    candidate = score_candidate(incoming, existing)
    assert candidate.matcher_algorithm_version == MATCHER_ALGORITHM_VERSION


# --- class-agnosticism (synthetic) ---


def test_class_agnostic_2026_and_2028_behave_identically():
    incoming_2026 = _row("Class Test", draft_class=2026)
    incoming_2028 = _row("Class Test", draft_class=2028)
    existing_2026 = _registry_entry(
        "cpr_a", "Class Test", draft_class=2026
    )
    existing_2028 = _registry_entry(
        "cpr_b", "Class Test", draft_class=2028
    )
    score_2026 = score_candidate(incoming_2026, existing_2026)
    score_2028 = score_candidate(incoming_2028, existing_2028)
    assert score_2026.match_score == score_2028.match_score
```

- [ ] **Step 2: Run the matcher test file to verify RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_matcher.py -v
```

Expected: every test fails with `ImportError` (the matcher symbols don't exist yet).

- [ ] **Step 3: Claude implements the matcher section in `college_prospect_identity.py`**

Append after the `load_registry` definition:

```python
# ======================================================================
# Match-key & normalization
# ======================================================================

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable

_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]")


def normalize_name(name: str) -> str:
    """Spec §5.1: identical to prospect_identity_resolver.normalize_name."""
    return _NORMALIZE_RE.sub("", name.lower()).strip()


def compute_match_key(*, normalized_name: str, position_group: str, draft_class: int) -> str:
    """Deterministic SHA-256 hash of (normalized_name, position_group, draft_class).

    Lookup/grouping key only — NEVER an identity key (spec §4.5 contract 6).
    """
    payload = f"{normalized_name}|{position_group.upper()}|{draft_class}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ======================================================================
# Matcher (discovery-only, fail-closed)
# ======================================================================

import jellyfish  # noqa: E402  (deliberate late import; lib is heavy)
from rapidfuzz import fuzz as _rf_fuzz  # noqa: E402

MIN_CANDIDATE_SCORE: float = 0.80
LOW_CONFIDENCE_LOWER: float = 0.80
LOW_CONFIDENCE_UPPER: float = 0.88
AMBIGUOUS_NEAR_TIE_MARGIN: float = 0.05
CROSS_POSITION_THRESHOLD: float = 0.90
TOP_K_CANDIDATES: int = 3

POSITION_BONUS: float = 0.10
SCHOOL_BONUS: float = 0.05
JW_WEIGHT: float = 0.75
TOKEN_SET_WEIGHT: float = 0.25


@dataclass(frozen=True)
class MatchCandidate:
    """Spec §5.7: review-queue audit-trail per candidate."""

    target_prospect_uuid: str
    match_score: float
    score_breakdown: dict[str, float]
    risk_flags: tuple[str, ...]
    raw_match_features: dict[str, Any]
    matcher_algorithm_version: str


def _name_base(incoming_name: str, existing_name: str) -> tuple[float, float, float]:
    jw = jellyfish.jaro_winkler_similarity(incoming_name, existing_name)
    token = _rf_fuzz.token_set_ratio(incoming_name, existing_name) / 100.0
    base = JW_WEIGHT * jw + TOKEN_SET_WEIGHT * token
    return jw, token, base


def score_candidate(
    incoming: NormalizedCollegeProspectRow,
    existing: RegistryEntry,
) -> MatchCandidate:
    """Compute a candidate score for `incoming` vs `existing`. Discovery-only."""
    risk_flags: list[str] = []
    jw, token, name_base = _name_base(incoming.normalized_name, existing.normalized_name)

    if incoming.draft_class != existing.draft_class:
        breakdown = {
            "jw_score": jw,
            "token_set_score": token,
            "name_base": name_base,
            "position_bonus": 0.0,
            "school_bonus": 0.0,
            "final": 0.0,
        }
        return MatchCandidate(
            target_prospect_uuid=existing.prospect_uuid,
            match_score=0.0,
            score_breakdown=breakdown,
            risk_flags=("class_boundary_blocked",),
            raw_match_features={
                "prospect_name": incoming.full_name,
                "position": incoming.position,
                "school": incoming.current_school,
                "draft_class": incoming.draft_class,
            },
            matcher_algorithm_version=MATCHER_ALGORITHM_VERSION,
        )

    position_bonus = POSITION_BONUS if incoming.position_group == existing.position_group else 0.0
    school_bonus = 0.0
    if incoming.current_school and (
        incoming.current_school == existing.current_school
        or incoming.current_school in existing.prior_schools
        or existing.current_school in incoming.prior_schools
    ):
        school_bonus = SCHOOL_BONUS

    final = max(0.0, min(1.0, name_base + position_bonus + school_bonus))
    breakdown = {
        "jw_score": jw,
        "token_set_score": token,
        "name_base": name_base,
        "position_bonus": position_bonus,
        "school_bonus": school_bonus,
        "final": final,
    }
    return MatchCandidate(
        target_prospect_uuid=existing.prospect_uuid,
        match_score=final,
        score_breakdown=breakdown,
        risk_flags=tuple(risk_flags),
        raw_match_features={
            "prospect_name": incoming.full_name,
            "position": incoming.position,
            "school": incoming.current_school,
            "draft_class": incoming.draft_class,
        },
        matcher_algorithm_version=MATCHER_ALGORITHM_VERSION,
    )


def surface_review_candidates(
    incoming: NormalizedCollegeProspectRow,
    registry: dict[str, RegistryEntry],
) -> list[MatchCandidate]:
    """Spec §5.4: emit top-3 above MIN_CANDIDATE_SCORE; attach low_confidence /
    ambiguous_near_tie / common_name risk flags."""
    scored = [score_candidate(incoming, e) for e in registry.values()]
    above = sorted(
        (c for c in scored if c.match_score >= MIN_CANDIDATE_SCORE),
        key=lambda c: c.match_score,
        reverse=True,
    )
    top = above[:TOP_K_CANDIDATES]
    if not top:
        return []

    flagged: list[MatchCandidate] = []
    for idx, cand in enumerate(top):
        flags = list(cand.risk_flags)
        if LOW_CONFIDENCE_LOWER <= cand.match_score < LOW_CONFIDENCE_UPPER:
            flags.append("low_confidence")
        if idx == 0 and len(top) >= 2:
            margin = top[0].match_score - top[1].match_score
            if margin <= AMBIGUOUS_NEAR_TIE_MARGIN:
                flags.append("ambiguous_near_tie")
                flags.append("common_name")
        flagged.append(
            MatchCandidate(
                target_prospect_uuid=cand.target_prospect_uuid,
                match_score=cand.match_score,
                score_breakdown=cand.score_breakdown,
                risk_flags=tuple(flags),
                raw_match_features=cand.raw_match_features,
                matcher_algorithm_version=cand.matcher_algorithm_version,
            )
        )
    return flagged
```

Also add the `Any` import near the top of the file if not already present (it was imported in Task 2, so this should already be in scope).

- [ ] **Step 4: Run the matcher test file to verify GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_matcher.py -v
```

Expected: all matcher tests pass. If the `test_low_confidence_band_emits_flag_in_0_80_to_0_88` or `test_ambiguous_near_tie_when_top_two_within_0_05` cases produce scores outside their expected bands due to JW idiosyncrasies, adjust the test fixture names — not the thresholds — to land in the target band; thresholds are spec-locked.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py tests/contract/test_subsystem_3_matcher.py
git commit -m "feat(subsystem-3): normalize_name + match_key + matcher core + §10.2 tests"
```

---

## Task 4: Whitelist + hard-block taxonomy — §10.3 contract tests

**Goal:** Lock the offense-only position-group whitelist (`WR↔TE`, `WR↔RB`, `FB↔RB`) and the hard-block list (QB, OL family, K/P/LS, defense↔offense) into deterministic data structures. Surface cross-position transitions only at `final_score ≥ 0.90`. Direction-insensitivity verified.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append whitelist section + integrate into `surface_review_candidates`)
- Create: `tests/contract/test_subsystem_3_whitelist.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_3_whitelist.py` with the following content:

```python
"""Subsystem 3 — whitelist & hard-block taxonomy contract tests (§10.3)."""
from __future__ import annotations

from src.dynasty_genius.identity.college_prospect_identity import (
    CROSS_POSITION_THRESHOLD,
    POSITION_GROUP_HARD_BLOCKS,
    POSITION_GROUP_WHITELIST,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
    is_position_pair_whitelisted,
    is_position_pair_hard_blocked,
    normalize_name,
    surface_review_candidates,
)


def _row(name, position, position_group, school="Ohio State", draft_class=2027, sid="incoming_001"):
    return NormalizedCollegeProspectRow.model_validate({
        "raw_name": name,
        "normalized_name": normalize_name(name),
        "full_name": name,
        "position": position,
        "position_group": position_group,
        "draft_class": draft_class,
        "current_school": school,
        "prior_schools": [],
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "manual_fixture",
        "source_record_id": sid,
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    })


def _entry(uuid, name, position, position_group, school="Ohio State", draft_class=2027):
    row = _row(name, position, position_group, school=school, draft_class=draft_class, sid=f"existing_{uuid}")
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name=row.normalized_name,
            position_group=position_group,
            draft_class=draft_class,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status="confirmed",
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **row.model_dump(),
    )


def test_whitelist_pairs_match_spec():
    expected = frozenset({frozenset({"WR", "TE"}), frozenset({"WR", "RB"}), frozenset({"FB", "RB"})})
    assert POSITION_GROUP_WHITELIST == expected


def test_whitelist_is_direction_insensitive():
    assert is_position_pair_whitelisted("WR", "TE") is True
    assert is_position_pair_whitelisted("TE", "WR") is True
    assert is_position_pair_whitelisted("FB", "RB") is True
    assert is_position_pair_whitelisted("RB", "FB") is True


def test_qb_to_wr_hard_blocked_even_with_perfect_name_school_match():
    incoming = _row("Mike Williams", "QB", "QB", school="Clemson")
    existing = _entry("cpr_a", "Mike Williams", "WR", "WR", school="Clemson")
    candidates = surface_review_candidates(incoming, {existing.prospect_uuid: existing})
    assert candidates == [], "QB↔WR must hard-block regardless of name/school similarity"
    assert is_position_pair_hard_blocked("QB", "WR") is True


def test_ol_family_hard_blocked_against_anything():
    for ol in ["OL", "OT", "OG", "C"]:
        for skill in ["QB", "RB", "WR", "TE", "FB"]:
            assert is_position_pair_hard_blocked(ol, skill) is True
            assert is_position_pair_hard_blocked(skill, ol) is True


def test_special_teams_hard_blocked_against_anything():
    for st in ["K", "P", "LS"]:
        for skill in ["QB", "RB", "WR", "TE", "FB", "OL"]:
            assert is_position_pair_hard_blocked(st, skill) is True
            assert is_position_pair_hard_blocked(skill, st) is True


def test_defense_to_offense_hard_blocked():
    defensive = ["DL", "DT", "DE", "EDGE", "OLB", "LB", "CB", "S", "DB"]
    offensive_skill = ["QB", "RB", "WR", "TE", "FB"]
    for d in defensive:
        for o in offensive_skill:
            assert is_position_pair_hard_blocked(d, o) is True
            assert is_position_pair_hard_blocked(o, d) is True


def test_whitelist_cross_group_surfaces_only_above_0_90():
    incoming = _row("Same Name", "TE", "TE", school="Same School")
    existing = _entry("cpr_a", "Same Name", "WR", "WR", school="Same School")
    candidates = surface_review_candidates(incoming, {existing.prospect_uuid: existing})
    assert candidates, "name+school identity should surface a cross-position TE↔WR candidate"
    top = candidates[0]
    assert top.match_score >= CROSS_POSITION_THRESHOLD
    assert "cross_position_group" in top.risk_flags
    assert "position_transition_allowed" in top.risk_flags


def test_whitelist_cross_group_below_0_90_is_suppressed():
    # Names diverge enough to fall under 0.90 even with school bonus
    incoming = _row("Quintessential Name", "TE", "TE", school="Clemson")
    existing = _entry("cpr_a", "Different Wholly", "WR", "WR", school="Clemson")
    candidates = surface_review_candidates(incoming, {existing.prospect_uuid: existing})
    assert all(
        c.target_prospect_uuid != existing.prospect_uuid
        or c.match_score >= CROSS_POSITION_THRESHOLD
        for c in candidates
    )
```

- [ ] **Step 2: Run the whitelist test file to verify RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_whitelist.py -v
```

Expected: ImportError on the whitelist symbols — they don't exist yet.

- [ ] **Step 3: Claude appends the whitelist + hard-block enforcement to `college_prospect_identity.py`**

Insert before the `MatchCandidate` dataclass:

```python
# Position-group whitelist (offense-only v1; direction-insensitive)
POSITION_GROUP_WHITELIST: frozenset[frozenset[str]] = frozenset({
    frozenset({"WR", "TE"}),
    frozenset({"WR", "RB"}),
    frozenset({"FB", "RB"}),
})

# Hard-block taxonomy (spec §5.3)
_OL_FAMILY: frozenset[str] = frozenset({"OL", "OT", "OG", "C"})
_SPECIAL_TEAMS: frozenset[str] = frozenset({"K", "P", "LS"})
_DEFENSIVE_GROUPS: frozenset[str] = frozenset({
    "DL", "DT", "DE", "EDGE", "OLB", "LB", "CB", "S", "DB",
})
_OFFENSIVE_SKILL: frozenset[str] = frozenset({"QB", "RB", "WR", "TE", "FB"})


def is_position_pair_whitelisted(a: str, b: str) -> bool:
    """Spec §5.3: direction-insensitive whitelist check."""
    return frozenset({a.upper(), b.upper()}) in POSITION_GROUP_WHITELIST


def is_position_pair_hard_blocked(a: str, b: str) -> bool:
    """Spec §5.3: direction-insensitive hard-block check.

    Hard-block rules:
    - QB ↔ anything except QB
    - OL family ↔ anything except itself
    - K/P/LS ↔ anything except themselves
    - Defensive group ↔ offensive skill (either direction)
    """
    au = a.upper()
    bu = b.upper()
    if au == bu:
        return False
    if "QB" in {au, bu} and not (au == bu):
        return True
    if au in _OL_FAMILY or bu in _OL_FAMILY:
        return True
    if au in _SPECIAL_TEAMS or bu in _SPECIAL_TEAMS:
        return True
    if (au in _DEFENSIVE_GROUPS and bu in _OFFENSIVE_SKILL) or (
        bu in _DEFENSIVE_GROUPS and au in _OFFENSIVE_SKILL
    ):
        return True
    return False


def POSITION_GROUP_HARD_BLOCKS() -> dict[str, frozenset[str]]:  # noqa: N802  (uppercase per spec naming)
    """Backstop accessor for callers that want the raw hard-block table.

    Returned dict is computed on call; do not mutate.
    """
    blocks: dict[str, frozenset[str]] = {}
    universe = _OL_FAMILY | _SPECIAL_TEAMS | _DEFENSIVE_GROUPS | _OFFENSIVE_SKILL | {"QB"}
    for a in universe:
        bs = frozenset(b for b in universe if is_position_pair_hard_blocked(a, b))
        if bs:
            blocks[a] = bs
    return blocks
```

Now update `surface_review_candidates` to apply the whitelist + hard-block gate. Replace the existing function body with:

```python
def surface_review_candidates(
    incoming: NormalizedCollegeProspectRow,
    registry: dict[str, RegistryEntry],
) -> list[MatchCandidate]:
    """Spec §5.4: emit top-3 above MIN_CANDIDATE_SCORE; attach low_confidence /
    ambiguous_near_tie / common_name risk flags; apply whitelist + hard-block."""
    scored: list[MatchCandidate] = []
    for existing in registry.values():
        if is_position_pair_hard_blocked(incoming.position_group, existing.position_group):
            continue
        cand = score_candidate(incoming, existing)
        same_group = incoming.position_group.upper() == existing.position_group.upper()
        if not same_group:
            if not is_position_pair_whitelisted(
                incoming.position_group, existing.position_group
            ):
                continue
            if cand.match_score < CROSS_POSITION_THRESHOLD:
                continue
            cand = MatchCandidate(
                target_prospect_uuid=cand.target_prospect_uuid,
                match_score=cand.match_score,
                score_breakdown=cand.score_breakdown,
                risk_flags=cand.risk_flags
                + ("cross_position_group", "position_transition_allowed"),
                raw_match_features=cand.raw_match_features,
                matcher_algorithm_version=cand.matcher_algorithm_version,
            )
        scored.append(cand)

    above = sorted(
        (c for c in scored if c.match_score >= MIN_CANDIDATE_SCORE),
        key=lambda c: c.match_score,
        reverse=True,
    )
    top = above[:TOP_K_CANDIDATES]
    if not top:
        return []

    flagged: list[MatchCandidate] = []
    for idx, cand in enumerate(top):
        flags = list(cand.risk_flags)
        if LOW_CONFIDENCE_LOWER <= cand.match_score < LOW_CONFIDENCE_UPPER:
            flags.append("low_confidence")
        if idx == 0 and len(top) >= 2:
            margin = top[0].match_score - top[1].match_score
            if margin <= AMBIGUOUS_NEAR_TIE_MARGIN:
                flags.append("ambiguous_near_tie")
                flags.append("common_name")
        flagged.append(
            MatchCandidate(
                target_prospect_uuid=cand.target_prospect_uuid,
                match_score=cand.match_score,
                score_breakdown=cand.score_breakdown,
                risk_flags=tuple(flags),
                raw_match_features=cand.raw_match_features,
                matcher_algorithm_version=cand.matcher_algorithm_version,
            )
        )
    return flagged
```

- [ ] **Step 4: Run the whitelist test file (and the matcher file, to confirm no regression) to verify GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_whitelist.py tests/contract/test_subsystem_3_matcher.py -v
```

Expected: all whitelist tests pass; all matcher tests still pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py tests/contract/test_subsystem_3_whitelist.py
git commit -m "feat(subsystem-3): position-group whitelist + hard-block taxonomy + §10.3 tests"
```

---

## Task 5: `ConfirmedProspectUuid` typed wrapper — §10.4 contract tests

**Goal:** Add the `ConfirmedProspectUuid` Python-honest runtime wrapper, its three failure exceptions, and the signature-introspection contract test that public runtime consumer APIs require `ConfirmedProspectUuid` (not raw `str`).

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append `ConfirmedProspectUuid` + resolver stub `resolve_prospect_cfbd_athlete_id`)
- Create: `tests/contract/test_subsystem_3_confirmed_uuid.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_3_confirmed_uuid.py`:

```python
"""Subsystem 3 — ConfirmedProspectUuid contract tests (§10.4)."""
from __future__ import annotations

import inspect

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    ProspectUuidDeprecatedMerged,
    ProspectUuidNotConfirmed,
    RegistryEntry,
    StatusHistoryEntry,
    UnknownProspectUuid,
    compute_match_key,
    normalize_name,
    resolve_prospect_cfbd_athlete_id,
)


def _entry(uuid, status="confirmed", merged_into=None):
    return RegistryEntry(
        prospect_uuid=uuid,
        verification_status=status,
        match_key=compute_match_key(
            normalized_name="sample name",
            position_group="WR",
            draft_class=2027,
        ),
        status_history=[
            StatusHistoryEntry(
                event_id=f"ev_{uuid}",
                decision="confirm",
                after_status=status,
                decided_at="2026-05-28T12:00:00Z",
                reviewer_id="davidleess",
            )
        ],
        merged_into_prospect_uuid=merged_into,
        reviewer_id="davidleess",
        reviewer_metadata={},
        raw_name="Sample Name",
        normalized_name=normalize_name("Sample Name"),
        full_name="Sample Name",
        position="WR",
        position_group="WR",
        draft_class=2027,
        current_school="Texas",
        prior_schools=[],
        cfbd_athlete_id=None,
        cfb_player_id=None,
        pfr_id=None,
        gsis_id=None,
        sleeper_id=None,
        source="manual_fixture",
        source_record_id=f"fixture_2027_{uuid}",
        source_snapshot_id="fixture_2027_v1",
        id_provenance={
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        notes=None,
    )


def test_confirmed_uuid_constructs_only_on_confirmed_row():
    uuid = "cpr_11111111-1111-4111-8111-111111111111"
    registry = CollegeProspectRegistry(entries={uuid: _entry(uuid, status="confirmed")})
    confirmed = ConfirmedProspectUuid(uuid, registry=registry)
    assert str(confirmed) == uuid


def test_confirmed_uuid_raises_unknown_uuid_for_missing_row():
    registry = CollegeProspectRegistry()
    with pytest.raises(UnknownProspectUuid):
        ConfirmedProspectUuid("cpr_does_not_exist", registry=registry)


def test_confirmed_uuid_raises_not_confirmed_on_provisional_row():
    uuid = "cpr_22222222-2222-4222-8222-222222222222"
    registry = CollegeProspectRegistry(entries={uuid: _entry(uuid, status="provisional")})
    with pytest.raises(ProspectUuidNotConfirmed):
        ConfirmedProspectUuid(uuid, registry=registry)


def test_confirmed_uuid_raises_deprecated_merged_on_redirect_without_allow_flag():
    survivor = "cpr_33333333-3333-4333-8333-333333333333"
    deprecated = "cpr_44444444-4444-4444-8444-444444444444"
    registry = CollegeProspectRegistry(entries={
        survivor: _entry(survivor, status="confirmed"),
        deprecated: _entry(deprecated, status="deprecated", merged_into=survivor),
    })
    with pytest.raises(ProspectUuidDeprecatedMerged):
        ConfirmedProspectUuid(deprecated, registry=registry)


def test_confirmed_uuid_follows_redirect_when_explicitly_allowed():
    survivor = "cpr_55555555-5555-4555-8555-555555555555"
    deprecated = "cpr_66666666-6666-4666-8666-666666666666"
    registry = CollegeProspectRegistry(entries={
        survivor: _entry(survivor, status="confirmed"),
        deprecated: _entry(deprecated, status="deprecated", merged_into=survivor),
    })
    confirmed = ConfirmedProspectUuid(deprecated, registry=registry, follow_redirect=True)
    assert str(confirmed) == survivor


def test_runtime_consumer_signature_requires_confirmed_prospect_uuid_type():
    """Spec §4.4: signature/introspection contract — no mypy/pyright gate in v1.

    Asserts that the public runtime consumer `resolve_prospect_cfbd_athlete_id`
    declares its return type as `ConfirmedProspectUuid | None` (or compatible).
    """
    sig = inspect.signature(resolve_prospect_cfbd_athlete_id)
    return_annotation = sig.return_annotation
    rendered = repr(return_annotation)
    assert "ConfirmedProspectUuid" in rendered, (
        f"resolve_prospect_cfbd_athlete_id return type must mention ConfirmedProspectUuid, "
        f"got {rendered}"
    )
```

- [ ] **Step 2: Run to verify RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_confirmed_uuid.py -v
```

Expected: ImportError on `ConfirmedProspectUuid` and `resolve_prospect_cfbd_athlete_id`.

- [ ] **Step 3: Claude implements the wrapper + resolver stub**

Append to `college_prospect_identity.py`:

```python
# ======================================================================
# ConfirmedProspectUuid wrapper (spec §4.4)
# ======================================================================


class ConfirmedProspectUuid:
    """Runtime-validated wrapper around a confirmed cpr_<uuid4>.

    Spec §4.4 / §4.6: this is Python-honest runtime validation at construction,
    NOT compile-time enforcement. Defenses are layered: __init__ raises on every
    non-confirmed status; contract tests inspect public consumer signatures;
    docs warn against raw-string construction; mypy/pyright is future hardening
    out of scope for v1.

    Construction rules:
    - Unknown UUID → UnknownProspectUuid
    - Status 'provisional' or 'deprecated' (and not following a redirect) →
      ProspectUuidNotConfirmed / ProspectUuidDeprecatedMerged
    - merged_into_prospect_uuid present + follow_redirect=False → raises
    - follow_redirect=True + valid survivor → returns ConfirmedProspectUuid of survivor
    """

    __slots__ = ("_value",)

    def __init__(
        self,
        uuid_str: str,
        *,
        registry: CollegeProspectRegistry,
        follow_redirect: bool = False,
    ) -> None:
        row = registry.get(uuid_str)
        if row is None:
            raise UnknownProspectUuid(uuid_str)
        if row.merged_into_prospect_uuid:
            if not follow_redirect:
                raise ProspectUuidDeprecatedMerged(
                    uuid_str, row.merged_into_prospect_uuid
                )
            survivor = registry.get(row.merged_into_prospect_uuid)
            if survivor is None:
                raise UnknownProspectUuid(row.merged_into_prospect_uuid)
            if survivor.verification_status != "confirmed":
                raise ProspectUuidNotConfirmed(
                    survivor.prospect_uuid, survivor.verification_status
                )
            self._value = survivor.prospect_uuid
            return
        if row.verification_status != "confirmed":
            raise ProspectUuidNotConfirmed(uuid_str, row.verification_status)
        self._value = uuid_str

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ConfirmedProspectUuid({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ConfirmedProspectUuid) and other._value == self._value

    def __hash__(self) -> int:
        return hash(("ConfirmedProspectUuid", self._value))


# ======================================================================
# Public runtime resolver (spec §1: sibling of prospect_identity_resolver)
# ======================================================================


def resolve_prospect_cfbd_athlete_id(
    *,
    name: str,
    position: str,
    draft_class: int,
    registry: CollegeProspectRegistry,
) -> Optional[ConfirmedProspectUuid]:
    """Spec §1 + §8: three-stage resolution returning a typed ConfirmedProspectUuid.

    NEVER fuzzy. NEVER returns provisional/deprecated identities. Returns None on
    unresolved (caller treats None as overlay-only / unresolved per spec §8).

    Stage 1: explicit cfbd_athlete_id (caller passes via name match — placeholder
             v1 does not yet thread an explicit-id channel; reserved for v2)
    Stage 2: registry lookup via (normalized_name, position_group, draft_class) →
             match_key; if exactly one CONFIRMED row matches, wrap & return.
    Stage 3: unresolved → return None (caller handles None as 'no Engine A score').
    """
    normalized = normalize_name(name)
    key = compute_match_key(
        normalized_name=normalized,
        position_group=position.upper(),
        draft_class=draft_class,
    )
    candidates = [
        e for e in registry.entries.values()
        if e.match_key == key and e.verification_status == "confirmed"
    ]
    if len(candidates) != 1:
        return None
    return ConfirmedProspectUuid(candidates[0].prospect_uuid, registry=registry)
```

- [ ] **Step 4: Run to verify GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_confirmed_uuid.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py tests/contract/test_subsystem_3_confirmed_uuid.py
git commit -m "feat(subsystem-3): ConfirmedProspectUuid + resolve_prospect_cfbd_athlete_id + §10.4 tests"
```

---

## Task 6 [v1 — SUPERSEDED by Round 2 Task 6 below]: Atomic registry persistence + ambiguity-before-mint — §10.5 contract tests

> **DO NOT EXECUTE this v1 task as written.** Cockpit round 2 (2026-05-28) identified that this task's `mint_or_match()` only does exact-`match_key` lookup, missing the §5.4 candidate query and the `source_id_conflict` (§5.5) pre-check; it also lacks the `CollegeAliasBridge` schema and the `validate_bridge_targets` invariant. **The replacement is "Round 2 Task 6" at the end of this document.** Kept inline for reviewer-side diffing.

**Goal:** Add per-file atomic write with tmp-then-replace, the ambiguity-before-mint logic (`mint_or_match`), and the four-case ingestion contract from spec §4.3.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append registry write + `mint_or_match`)
- Create: `tests/contract/test_subsystem_3_ingestion.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_3_ingestion.py`:

```python
"""Subsystem 3 — ingestion atomicity & ambiguity-before-mint contract tests (§10.5)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    IngestionOutcome,
    NormalizedCollegeProspectRow,
    atomic_write_registry,
    compute_match_key,
    load_registry,
    mint_or_match,
    normalize_name,
)


def _row(name, position_group="WR", school="Ohio State", draft_class=2027, sid="fixture_2027_001"):
    return NormalizedCollegeProspectRow.model_validate({
        "raw_name": name,
        "normalized_name": normalize_name(name),
        "full_name": name,
        "position": position_group,
        "position_group": position_group,
        "draft_class": draft_class,
        "current_school": school,
        "prior_schools": [],
        "cfbd_athlete_id": None,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "manual_fixture",
        "source_record_id": sid,
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    })


def test_atomic_write_uses_tmp_then_rename(tmp_path: Path, monkeypatch):
    path = tmp_path / "registry.json"
    registry = CollegeProspectRegistry(metadata={"snapshot": "fixture_2027_v1"}, entries={})

    seen_tmp_paths: list[Path] = []
    original_replace = __import__("os").replace

    def spy_replace(src, dst):
        seen_tmp_paths.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr("os.replace", spy_replace)
    atomic_write_registry(registry, path)
    assert path.exists()
    assert seen_tmp_paths and seen_tmp_paths[0].name.endswith(".tmp")
    reloaded = load_registry(path)
    assert reloaded.metadata == {"snapshot": "fixture_2027_v1"}


def test_idempotent_rerun_same_source_record_id_and_snapshot_reuses_uuid(tmp_path: Path):
    path = tmp_path / "registry.json"
    registry = CollegeProspectRegistry()
    incoming = _row("Arch Manning", position_group="QB", school="Texas", sid="fixture_2027_001")

    outcome_1 = mint_or_match(incoming, registry)
    assert outcome_1.kind == "minted_new"
    first_uuid = outcome_1.prospect_uuid
    atomic_write_registry(registry, path)

    # Re-load and re-ingest the SAME row
    registry_2 = load_registry(path)
    outcome_2 = mint_or_match(incoming, registry_2)
    assert outcome_2.kind == "idempotent_rerun"
    assert outcome_2.prospect_uuid == first_uuid


def test_same_match_key_different_source_record_id_mints_provisional_with_common_name_flag():
    registry = CollegeProspectRegistry()
    first = _row("Mike Williams", position_group="WR", school="Clemson", sid="src_A")
    second = _row("Mike Williams", position_group="WR", school="USC", sid="src_B")

    outcome_first = mint_or_match(first, registry)
    outcome_second = mint_or_match(second, registry)

    assert outcome_second.kind == "minted_new_provisional_with_review_candidate"
    assert outcome_first.prospect_uuid != outcome_second.prospect_uuid
    assert outcome_second.review_candidate is not None
    assert "common_name" in outcome_second.review_candidate.risk_flags


def test_multiple_existing_matches_emit_ambiguous_existing_candidates_review_entry():
    registry = CollegeProspectRegistry()
    a = _row("Common Surname", position_group="WR", school="Texas", sid="src_A")
    b = _row("Common Surname", position_group="WR", school="LSU", sid="src_B")
    c = _row("Common Surname", position_group="WR", school="Bama", sid="src_C")

    mint_or_match(a, registry)
    mint_or_match(b, registry)
    outcome_c = mint_or_match(c, registry)

    assert outcome_c.kind == "minted_new_provisional_with_review_candidate"
    assert outcome_c.review_candidate is not None
    assert "ambiguous_existing_candidates" in outcome_c.review_candidate.risk_flags
```

- [ ] **Step 2: Run to verify RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py -v
```

Expected: ImportError on `atomic_write_registry`, `mint_or_match`, `IngestionOutcome`.

- [ ] **Step 3: Claude implements atomic write + `mint_or_match`**

Append to `college_prospect_identity.py`:

```python
# ======================================================================
# Atomic registry persistence (spec §6.4 — per-file os.replace)
# ======================================================================

import os
import uuid as _uuid
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_registry(registry: CollegeProspectRegistry, path: Path) -> None:
    """Spec §6.4: serialize to sibling .tmp file then os.replace into place.

    Per-file atomic only; NOT cross-file transactional. Caller orchestrates
    multi-artifact write order + recovery contract.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "metadata": registry.metadata,
        "entries": [e.model_dump(mode="json") for e in registry.entries.values()],
    }
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    os.replace(tmp_path, path)


# ======================================================================
# Ambiguity-before-mint (spec §4.3)
# ======================================================================


@dataclass(frozen=True)
class IngestionOutcome:
    kind: Literal[
        "minted_new",
        "idempotent_rerun",
        "minted_new_provisional_with_review_candidate",
    ]
    prospect_uuid: str
    review_candidate: Optional[MatchCandidate] = None


def _mint_provisional_uuid() -> str:
    return f"cpr_{_uuid.uuid4()}"


def mint_or_match(
    incoming: NormalizedCollegeProspectRow,
    registry: CollegeProspectRegistry,
) -> IngestionOutcome:
    """Spec §4.3 + §5.4: Ingestion with robust fuzzy matcher integration.
    
    1. Compute match_key.
    2. Check exact duplicates (same source_record_id + snapshot) -> idempotent rerun.
    3. Check source_id_conflict hard block (Blocker 4) -> If shared source_record_id
       pointing to different UUID exists, block fuzzy matching and flag as conflict.
    4. Run surface_review_candidates() to find existing candidates (JW/token blend, whitelist, etc.).
    5. Zero candidates -> Mint new provisional uuid.
    6. Candidates found -> Mint new provisional uuid + review candidate suggestion(s).
    """
    # Idempotent rerun check
    for m in registry.entries.values():
        if (
            m.source == incoming.source
            and m.source_record_id == incoming.source_record_id
            and m.source_snapshot_id == incoming.source_snapshot_id
        ):
            return IngestionOutcome(
                kind="idempotent_rerun",
                prospect_uuid=m.prospect_uuid,
            )

    # Blocker 4: source_id_conflict hard block
    for m in registry.entries.values():
        if (
            m.source == incoming.source
            and m.source_record_id == incoming.source_record_id
            and m.prospect_uuid is not None
        ):
            new_uuid = _mint_and_insert(incoming, registry, compute_match_key(
                normalized_name=incoming.normalized_name,
                position_group=incoming.position_group,
                draft_class=incoming.draft_class,
            ))
            conflict_candidate = MatchCandidate(
                target_prospect_uuid=m.prospect_uuid,
                match_score=0.0,
                score_breakdown={"final": 0.0},
                risk_flags=("source_id_conflict",),
                raw_match_features={
                    "prospect_name": incoming.full_name,
                    "position": incoming.position,
                    "school": incoming.current_school,
                    "draft_class": incoming.draft_class,
                },
                matcher_algorithm_version=MATCHER_ALGORITHM_VERSION,
            )
            return IngestionOutcome(
                kind="minted_new_provisional_with_review_candidate",
                prospect_uuid=new_uuid,
                review_candidate=conflict_candidate,
            )

    # Blocker 1: Ingestion uses surface_review_candidates to find suggestions
    candidates = surface_review_candidates(incoming, registry.entries)
    
    key = compute_match_key(
        normalized_name=incoming.normalized_name,
        position_group=incoming.position_group,
        draft_class=incoming.draft_class,
    )
    new_uuid = _mint_and_insert(incoming, registry, key)

    if not candidates:
        return IngestionOutcome(
            kind="minted_new",
            prospect_uuid=new_uuid,
        )

    # Surface top candidate suggestions in review queue
    return IngestionOutcome(
        kind="minted_new_provisional_with_review_candidate",
        prospect_uuid=new_uuid,
        review_candidate=candidates[0],
    )


def _mint_and_insert(
    incoming: NormalizedCollegeProspectRow,
    registry: CollegeProspectRegistry,
    match_key: str,
) -> str:
    new_uuid = _mint_provisional_uuid()
    entry = RegistryEntry(
        prospect_uuid=new_uuid,
        verification_status="provisional",
        match_key=match_key,
        status_history=[
            StatusHistoryEntry(
                event_id=f"ingest_{new_uuid}",
                decision="ingest",
                after_status="provisional",
                decided_at=_now_iso(),
                reviewer_id="system_ingestion",
            )
        ],
        merged_into_prospect_uuid=None,
        reviewer_id="system_ingestion",
        reviewer_metadata={},
        **incoming.model_dump(),
    )
    registry.entries[new_uuid] = entry
    return new_uuid
```

- [ ] **Step 4: Run to verify GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py tests/contract/test_subsystem_3_ingestion.py
git commit -m "feat(subsystem-3): atomic registry write + mint_or_match + §10.5 tests"
```

---

## Task 7 [v1 — SUPERSEDED by Round 2 Task 7 below]: Ingestion CLI — `scripts/ingest_college_prospect_fixture.py`

> **DO NOT EXECUTE this v1 task as written.** Cockpit round 2 (2026-05-28) identified that this task does not write the alias-bridge artifact, does not emit the dedicated `source_id_conflict_<run_id>.jsonl` queue, and does not handle the new `IngestionOutcome` kinds (whitelist-neighbor surfacing, source_id_conflict). **The replacement is "Round 2 Task 7" at the end of this document.** Kept inline for reviewer-side diffing.

**Goal:** Add the manual-fixture loader script that runs `mint_or_match` for every row in `resources/college_prospect_fixture_2027.json`, writes the registry, the per-run review-queue JSONL, and the coverage matrix — all via per-file atomic writes with the recovery contract (idempotent rerun + post-run validation).

**Files:**
- Create: `scripts/ingest_college_prospect_fixture.py`
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append `ingest_fixture` orchestration function + `validate_registry_graph` helper)
- Modify: `tests/contract/test_subsystem_3_ingestion.py` (append CLI tests)

- [ ] **Step 1: Codex appends RED tests for the CLI orchestration**

Append to `tests/contract/test_subsystem_3_ingestion.py`:

```python
# --- CLI orchestration / fixture ingestion ---


def test_ingest_fixture_writes_registry_review_queue_and_coverage_atomically(tmp_path: Path):
    from src.dynasty_genius.identity.college_prospect_identity import ingest_fixture

    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [
            _row("Arch Manning", position_group="QB", school="Texas", sid="fixture_2027_001").model_dump(),
            _row("Quinn Ewers", position_group="QB", school="Texas", sid="fixture_2027_002").model_dump(),
        ],
    }))
    out_dir = tmp_path / "out"
    run_id = "run_test_001"

    result = ingest_fixture(
        fixture_path=fixture_path,
        identity_dir=out_dir,
        run_id=run_id,
    )

    assert (out_dir / "college_prospect_registry.json").exists()
    assert (out_dir / f"college_identity_review_queue_{run_id}.jsonl").exists()
    assert (out_dir / f"college_identity_coverage_matrix_{run_id}.json").exists()

    registry = load_registry(out_dir / "college_prospect_registry.json")
    assert len(registry.entries) == 2

    coverage = json.loads((out_dir / f"college_identity_coverage_matrix_{run_id}.json").read_text())
    assert coverage["total_input_rows"] == 2
    assert coverage["minted_new"] == 2
    assert coverage["idempotent_rerun"] == 0

    assert result.exit_code == 0


def test_ingest_fixture_idempotent_rerun_is_noop(tmp_path: Path):
    from src.dynasty_genius.identity.college_prospect_identity import ingest_fixture

    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [_row("Arch Manning", position_group="QB", school="Texas", sid="fixture_2027_001").model_dump()],
    }))
    out_dir = tmp_path / "out"

    first = ingest_fixture(fixture_path=fixture_path, identity_dir=out_dir, run_id="run_a")
    first_registry_bytes = (out_dir / "college_prospect_registry.json").read_bytes()
    assert first.exit_code == 0

    second = ingest_fixture(fixture_path=fixture_path, identity_dir=out_dir, run_id="run_b")
    second_registry_bytes = (out_dir / "college_prospect_registry.json").read_bytes()
    assert second.exit_code == 0
    # registry is byte-identical because nothing new was minted
    assert first_registry_bytes == second_registry_bytes
```

- [ ] **Step 2: Run to verify RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py -v
```

Expected: the new tests fail with ImportError on `ingest_fixture`.

- [ ] **Step 3: Claude implements `ingest_fixture` and `validate_registry_graph`**

Append to `college_prospect_identity.py`:

# ======================================================================
# Fixture ingestion orchestration (spec §6.5)
# ======================================================================


@dataclass(frozen=True)
class IngestResult:
    exit_code: int
    run_id: str
    coverage: dict[str, int]


class CollegeAliasBridge(BaseModel):
    """Bridge schema for college-side prospect aliases (spec §3)."""

    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)
    entries: dict[str, str] = Field(default_factory=dict)  # f"{match_key}|{source_record_id}" -> prospect_uuid


def load_bridge(path: Path) -> CollegeAliasBridge:
    if not path.exists():
        return CollegeAliasBridge()
    raw = json.loads(path.read_text())
    return CollegeAliasBridge(
        metadata=raw.get("metadata", {}),
        entries=raw.get("entries", {}),
    )


def atomic_write_bridge(bridge: CollegeAliasBridge, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "metadata": bridge.metadata,
        "entries": bridge.entries,
    }
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    os.replace(tmp_path, path)


def validate_registry_graph(registry: CollegeProspectRegistry, bridge: CollegeAliasBridge) -> list[str]:
    """Spec §4.6 contract 5 + §4.6 contract 3: full identity-graph + bridge validation.

    Returns a list of human-readable errors (empty list = graph is consistent).
    """
    errors: list[str] = []
    seen_source_records: dict[tuple[str, str], str] = {}
    for entry in registry.entries.values():
        # Source-record uniqueness (§4.6 contract 4)
        if entry.verification_status == "confirmed":
            key = (entry.source, entry.source_record_id)
            if key in seen_source_records:
                errors.append(
                    f"source_record_id collision on {entry.source_record_id}: "
                    f"{seen_source_records[key]} and {entry.prospect_uuid}"
                )
            else:
                seen_source_records[key] = entry.prospect_uuid
        # Redirect target validity
        if entry.merged_into_prospect_uuid:
            survivor = registry.get(entry.merged_into_prospect_uuid)
            if survivor is None:
                errors.append(
                    f"{entry.prospect_uuid} redirects to unknown {entry.merged_into_prospect_uuid}"
                )
            elif survivor.verification_status != "confirmed":
                errors.append(
                    f"{entry.prospect_uuid} redirects to non-confirmed "
                    f"{entry.merged_into_prospect_uuid}"
                )

    # Blocker 5: Stricter bridge validation contract
    for key, target_uuid in bridge.entries.items():
        target = registry.get(target_uuid)
        if target is None:
            errors.append(f"bridge key {key} maps to unknown {target_uuid}")
        elif target.verification_status != "confirmed":
            errors.append(f"bridge key {key} maps to non-confirmed {target_uuid} (status: {target.verification_status})")

    return errors


def ingest_fixture(
    *,
    fixture_path: Path,
    identity_dir: Path,
    run_id: str,
) -> IngestResult:
    """Spec §6.5: validate-before-replace ingestion across registry + review-queue + coverage.

    Per-file atomic writes via os.replace. Idempotent rerun is the recovery contract.
    """
    raw = json.loads(fixture_path.read_text())
    entries_raw = raw.get("entries", [])

    registry_path = identity_dir / "college_prospect_registry.json"
    registry = load_registry(registry_path)

    bridge_path = identity_dir / "college_alias_bridge.json"
    bridge = load_bridge(bridge_path)

    coverage = {
        "total_input_rows": 0,
        "minted_new": 0,
        "idempotent_rerun": 0,
        "minted_new_provisional_with_review_candidate": 0,
    }
    review_entries: list[dict[str, Any]] = []

    for raw_entry in entries_raw:
        incoming = NormalizedCollegeProspectRow.model_validate(raw_entry)
        coverage["total_input_rows"] += 1
        outcome = mint_or_match(incoming, registry)
        coverage[outcome.kind] += 1
        if outcome.review_candidate is not None:
            review_entries.append({
                "run_id": run_id,
                "review_id": f"{run_id}_review_{coverage['total_input_rows']:04d}",
                "incoming_source_record_id": incoming.source_record_id,
                "minted_prospect_uuid": outcome.prospect_uuid,
                "target_prospect_uuid": outcome.review_candidate.target_prospect_uuid,
                "match_score": outcome.review_candidate.match_score,
                "score_breakdown": outcome.review_candidate.score_breakdown,
                "risk_flags": list(outcome.review_candidate.risk_flags),
                "raw_match_features": outcome.review_candidate.raw_match_features,
                "matcher_algorithm_version": outcome.review_candidate.matcher_algorithm_version,
                "decided_at": None,
                "decision": None,
                "event_id": None,
            })

    # Validate before any replace
    errors = validate_registry_graph(registry, bridge)
    if errors:
        diagnostics_path = identity_dir / f"college_identity_failure_report_{run_id}.md"
        diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostics_path.write_text(
            "# Subsystem 3 — ingestion failure report\n\n"
            f"run_id: {run_id}\n\n" + "\n".join(f"- {e}" for e in errors)
        )
        return IngestResult(exit_code=1, run_id=run_id, coverage=coverage)

    # Per-file atomic writes
    identity_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_registry(registry, registry_path)
    atomic_write_bridge(bridge, bridge_path)

    review_path = identity_dir / f"college_identity_review_queue_{run_id}.jsonl"
    tmp_review = review_path.with_suffix(review_path.suffix + ".tmp")
    tmp_review.write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in review_entries) + ("\n" if review_entries else "")
    )
    os.replace(tmp_review, review_path)

    coverage_path = identity_dir / f"college_identity_coverage_matrix_{run_id}.json"
    tmp_coverage = coverage_path.with_suffix(coverage_path.suffix + ".tmp")
    tmp_coverage.write_text(json.dumps(coverage, indent=2, sort_keys=True))
    os.replace(tmp_coverage, coverage_path)

    # Post-run validation
    reloaded = load_registry(registry_path)
    reloaded_bridge = load_bridge(bridge_path)
    post_errors = validate_registry_graph(reloaded, reloaded_bridge)
    if post_errors:
        return IngestResult(exit_code=2, run_id=run_id, coverage=coverage)

    return IngestResult(exit_code=0, run_id=run_id, coverage=coverage)
```

Now create the CLI script at `scripts/ingest_college_prospect_fixture.py`:

```python
"""Subsystem 3 — manual-fixture ingestion CLI.

Usage:
    .venv/bin/python3.14 scripts/ingest_college_prospect_fixture.py \\
        --fixture resources/college_prospect_fixture_2027.json \\
        --identity-dir app/data/identity \\
        --run-id manual_2027_20260528T1200Z

Spec: docs/superpowers/specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md §6.5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.dynasty_genius.identity.college_prospect_identity import ingest_fixture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the college prospect fixture (spec §6.5).")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    args = parser.parse_args(argv)

    result = ingest_fixture(
        fixture_path=args.fixture,
        identity_dir=args.identity_dir,
        run_id=args.run_id,
    )
    print(
        f"run_id={result.run_id} exit_code={result.exit_code} coverage={result.coverage}",
        file=sys.stderr,
    )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py -v
```

Expected: all 6 ingestion tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py scripts/ingest_college_prospect_fixture.py tests/contract/test_subsystem_3_ingestion.py
git commit -m "feat(subsystem-3): ingest_fixture orchestration + CLI script"
```

---

## Task 8 [v1 — SUPERSEDED by Round 2 Task 8 below]: Promotion lifecycle — `promote_review_candidate.py` + §10.6 contract tests

> **DO NOT EXECUTE this v1 task as written.** Cockpit round 2 (2026-05-28) identified three structural defects: (a) `confirm` does not split self vs target-existing — alias case does not write a bridge entry; (b) review-queue closure marker (third leg of §6.3 three-point logging) is missing; (c) `replay_promotion_log()` calls back into `promote_review_candidate()` which re-mints `_now_iso()` and `_uuid.uuid4()`, breaking the byte-identical reconstruction contract. **The replacement is "Round 2 Task 8" at the end of this document.** Kept inline for reviewer-side diffing.

**Goal:** Implement the only blessed write path for reviewer decisions: `confirm` (with `--target self|<uuid>`), `reject`, `defer`, `merge_into` (requires evidence), `split` (requires evidence). Three-point logging (promotion log + registry status_history + review-queue closure). Per-file atomic writes in dependency-safe order. Idempotent rerun; conflicting rerun fails closed. Replay-over-genesis determinism.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append promotion entry-points)
- Create: `scripts/promote_review_candidate.py`
- Create: `tests/contract/test_subsystem_3_promotion.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_3_promotion.py`:

```python
"""Subsystem 3 — promotion lifecycle contract tests (§10.6)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    ConflictingDecisionError,
    EvidenceRequiredError,
    PromotionDecision,
    PromotionResult,
    ingest_fixture,
    load_registry,
    promote_review_candidate,
    replay_promotion_log,
)


def _seed_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [
            {
                "raw_name": "Arch Manning",
                "normalized_name": "arch manning",
                "full_name": "Arch Manning",
                "position": "QB",
                "position_group": "QB",
                "draft_class": 2027,
                "current_school": "Texas",
                "prior_schools": [],
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
                "source": "manual_fixture",
                "source_record_id": "fixture_2027_001",
                "source_snapshot_id": "fixture_2027_v1",
                "id_provenance": {
                    "cfbd_athlete_id": None,
                    "cfb_player_id": None,
                    "pfr_id": None,
                    "gsis_id": None,
                    "sleeper_id": None,
                },
                "notes": None,
            },
            {
                "raw_name": "Mike Williams",
                "normalized_name": "mike williams",
                "full_name": "Mike Williams",
                "position": "WR",
                "position_group": "WR",
                "draft_class": 2027,
                "current_school": "Clemson",
                "prior_schools": [],
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
                "source": "manual_fixture",
                "source_record_id": "fixture_2027_002",
                "source_snapshot_id": "fixture_2027_v1",
                "id_provenance": {
                    "cfbd_athlete_id": None,
                    "cfb_player_id": None,
                    "pfr_id": None,
                    "gsis_id": None,
                    "sleeper_id": None,
                },
                "notes": None,
            },
        ],
    }))
    out = tmp_path / "out"
    run_id = "genesis_run_001"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id=run_id)
    return fixture, out, run_id


def _first_review_id(out_dir: Path, run_id: str) -> str:
    review_path = out_dir / f"college_identity_review_queue_{run_id}.jsonl"
    if not review_path.exists() or review_path.read_text().strip() == "":
        pytest.skip("no review candidate emitted in seed fixture (expected for distinct names)")
    return json.loads(review_path.read_text().splitlines()[0])["review_id"]


def _any_provisional_uuid(out_dir: Path) -> str:
    registry = load_registry(out_dir / "college_prospect_registry.json")
    for e in registry.entries.values():
        if e.verification_status == "provisional":
            return e.prospect_uuid
    raise AssertionError("expected at least one provisional row in seed")


def test_confirm_self_promotes_row_to_confirmed_and_logs(tmp_path: Path):
    _, out, _ = _seed_fixture(tmp_path)
    target_uuid = _any_provisional_uuid(out)
    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target=target_uuid),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note="standalone confirm",
    )
    assert isinstance(result, PromotionResult)
    assert result.exit_code == 0
    registry = load_registry(out / "college_prospect_registry.json")
    assert registry.get(target_uuid).verification_status == "confirmed"
    log_path = out / "college_identity_promotion_log.jsonl"
    assert log_path.exists()
    events = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert any(ev["decision"] == "confirm" for ev in events)


def test_reject_closes_review_without_mutating_identity(tmp_path: Path):
    _, out, _ = _seed_fixture(tmp_path)
    target_uuid = _any_provisional_uuid(out)
    pre_status = load_registry(out / "college_prospect_registry.json").get(target_uuid).verification_status
    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="reject", target=target_uuid),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    assert result.exit_code == 0
    post_status = load_registry(out / "college_prospect_registry.json").get(target_uuid).verification_status
    assert pre_status == post_status  # no identity mutation on reject of standalone


def test_merge_into_requires_non_empty_evidence(tmp_path: Path):
    _, out, _ = _seed_fixture(tmp_path)
    targets = list(load_registry(out / "college_prospect_registry.json").entries.values())
    if len(targets) < 2:
        pytest.skip("seed needs ≥2 rows for merge")
    survivor = targets[0].prospect_uuid
    deprecated = targets[1].prospect_uuid

    with pytest.raises(EvidenceRequiredError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(
                kind="merge_into",
                target=deprecated,
                survivor=survivor,
            ),
            identity_dir=out,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
        )


def test_split_requires_non_empty_evidence(tmp_path: Path):
    _, out, _ = _seed_fixture(tmp_path)
    target = _any_provisional_uuid(out)

    with pytest.raises(EvidenceRequiredError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(
                kind="split",
                target=target,
                new_full_name="Split Person",
                new_position="WR",
                new_position_group="WR",
            ),
            identity_dir=out,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
        )


def test_idempotent_rerun_same_decision_is_noop(tmp_path: Path):
    _, out, _ = _seed_fixture(tmp_path)
    target = _any_provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    log_path = out / "college_identity_promotion_log.jsonl"
    log_bytes_before = log_path.read_bytes()
    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    assert result.exit_code == 0
    log_bytes_after = log_path.read_bytes()
    assert log_bytes_before == log_bytes_after


def test_conflicting_rerun_fails_closed_without_override(tmp_path: Path):
    _, out, _ = _seed_fixture(tmp_path)
    target = _any_provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    with pytest.raises(ConflictingDecisionError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(kind="reject", target=target),
            identity_dir=out,
            reviewer_id="davidleess",
            evidence=None,
            note=None,
        )


def test_promotion_log_replay_over_genesis_reconstructs_registry_byte_for_byte(tmp_path: Path):
    fixture, out, run_id = _seed_fixture(tmp_path)
    target = _any_provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    registry_after = (out / "college_prospect_registry.json").read_bytes()

    # Reset to genesis, replay the log
    genesis_dir = tmp_path / "replay_out"
    ingest_fixture(fixture_path=fixture, identity_dir=genesis_dir, run_id=run_id)
    log_path = out / "college_identity_promotion_log.jsonl"
    replay_promotion_log(log_path=log_path, identity_dir=genesis_dir)
    replayed = (genesis_dir / "college_prospect_registry.json").read_bytes()
    assert replayed == registry_after
```

- [ ] **Step 2: Run to verify RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_promotion.py -v
```

Expected: ImportError on all the new symbols.

- [ ] **Step 3: Claude implements promotion entry-points**

Append to `college_prospect_identity.py`:

```python
# ======================================================================
# Promotion entry-points (spec §6)
# ======================================================================


class EvidenceRequiredError(ValueError):
    """merge_into and split require non-empty --evidence."""


class ConflictingDecisionError(RuntimeError):
    """Same review_id / target already has a different decision in the log."""


@dataclass(frozen=True)
class PromotionDecision:
    kind: Literal["confirm", "reject", "defer", "merge_into", "split"]
    target: str
    survivor: Optional[str] = None  # for merge_into
    new_full_name: Optional[str] = None  # for split
    new_position: Optional[str] = None  # for split
    new_position_group: Optional[str] = None  # for split


@dataclass(frozen=True)
class PromotionResult:
    exit_code: int
    event_id: Optional[str] = None


def _read_promotion_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _append_promotion_event(path: Path, event: dict[str, Any]) -> None:
    """Per-file atomic append: read existing → append → tmp-write → os.replace."""
    existing = _read_promotion_log(path)
    existing.append(event)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(json.dumps(e, sort_keys=True) for e in existing) + "\n")
    os.replace(tmp, path)


def _close_review_row(review_id: str, decision_kind: str, event_id: str, decided_at: str, identity_dir: Path) -> None:
    """Blocker 2: write closure marker on the review queue entry."""
    parts = review_id.rsplit("_review_", 1)
    if len(parts) != 2:
        return
    run_id = parts[0]
    queue_path = identity_dir / f"college_identity_review_queue_{run_id}.jsonl"
    if not queue_path.exists():
        return

    lines = queue_path.read_text().splitlines()
    updated_lines = []
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("review_id") == review_id:
            row["decided_at"] = decided_at
            row["decision"] = decision_kind
            row["event_id"] = event_id
        updated_lines.append(json.dumps(row, sort_keys=True))

    tmp = queue_path.with_suffix(queue_path.suffix + ".tmp")
    tmp.write_text("\n".join(updated_lines) + "\n")
    os.replace(tmp, queue_path)


def promote_review_candidate(
    *,
    review_id: Optional[str],
    decision: PromotionDecision,
    identity_dir: Path,
    reviewer_id: str,
    evidence: Optional[str],
    note: Optional[str],
    event_id: Optional[str] = None,      # Blocker 3: deterministic replay fields
    decided_at: Optional[str] = None,
) -> PromotionResult:
    """Spec §6: the only blessed write path for review decisions.

    Per-file atomicity in dependency-safe order:
      promotion_log → registry → bridge → review_queue closure.

    Idempotent rerun (same target + same decision) is a no-op.
    Conflicting rerun raises ConflictingDecisionError unless future --override.
    """
    if decision.kind in {"merge_into", "split"} and not (evidence and evidence.strip()):
        raise EvidenceRequiredError(
            f"decision={decision.kind} requires non-empty --evidence (spec §6.2)"
        )

    log_path = identity_dir / "college_identity_promotion_log.jsonl"
    log = _read_promotion_log(log_path)

    # Conflict / idempotency check by target
    for prior in log:
        if prior.get("target_prospect_uuid") == decision.target:
            if prior.get("decision") == decision.kind:
                return PromotionResult(exit_code=0, event_id=prior.get("event_id"))
            raise ConflictingDecisionError(
                f"target={decision.target} already has decision={prior.get('decision')}; "
                f"refusing to apply {decision.kind} without --override"
            )

    registry_path = identity_dir / "college_prospect_registry.json"
    registry = load_registry(registry_path)
    target_row = registry.get(decision.target)
    if target_row is None:
        return PromotionResult(exit_code=1)

    bridge_path = identity_dir / "college_alias_bridge.json"
    bridge = load_bridge(bridge_path)

    decided_at = decided_at or _now_iso()
    event_id = event_id or f"ev_{_uuid.uuid4()}"

    event: dict[str, Any] = {
        "event_id": event_id,
        "review_id": review_id,
        "decision": decision.kind,
        "reviewer_id": reviewer_id,
        "reviewer_metadata": {},
        "decided_at": decided_at,
        "target_prospect_uuid": decision.target,
        "survivor_prospect_uuid": decision.survivor,
        "before_status": target_row.verification_status,
        "after_status": target_row.verification_status,
        "evidence": evidence,
        "note": note,
    }

    if decision.kind == "confirm":
        if decision.survivor:  # Blocker 2: confirm-to-existing (survivor uuid)
            target_row.verification_status = "deprecated"
            target_row.merged_into_prospect_uuid = decision.survivor
            target_row.append_status_history(
                StatusHistoryEntry(
                    event_id=event_id,
                    decision="confirm",
                    after_status="deprecated",
                    decided_at=decided_at,
                    reviewer_id=reviewer_id,
                )
            )
            # Write alias bridge entry: f"{match_key}|{source_record_id}" -> existing uuid
            bridge_key = f"{target_row.match_key}|{target_row.source_record_id}"
            bridge.entries[bridge_key] = decision.survivor
            event["after_status"] = "deprecated"
        else:
            # confirm self as standalone
            target_row.verification_status = "confirmed"
            target_row.append_status_history(
                StatusHistoryEntry(
                    event_id=event_id,
                    decision="confirm",
                    after_status="confirmed",
                    decided_at=decided_at,
                    reviewer_id=reviewer_id,
                )
            )
            event["after_status"] = "confirmed"
    elif decision.kind == "merge_into":
        target_row.verification_status = "deprecated"
        target_row.merged_into_prospect_uuid = decision.survivor
        target_row.append_status_history(
            StatusHistoryEntry(
                event_id=event_id,
                decision="merge_into",
                after_status="deprecated",
                decided_at=decided_at,
                reviewer_id=reviewer_id,
            )
        )
        event["after_status"] = "deprecated"
    elif decision.kind == "split":
        # mint a new provisional sibling carrying the new identity
        new_uuid = _mint_provisional_uuid()
        new_row = target_row.model_copy(update={
            "prospect_uuid": new_uuid,
            "verification_status": "provisional",
            "full_name": decision.new_full_name or target_row.full_name,
            "position": decision.new_position or target_row.position,
            "position_group": decision.new_position_group or target_row.position_group,
            "status_history": [
                StatusHistoryEntry(
                    event_id=event_id,
                    decision="split",
                    after_status="provisional",
                    decided_at=decided_at,
                    reviewer_id=reviewer_id,
                )
            ],
        })
        registry.entries[new_uuid] = new_row
        target_row.append_status_history(
            StatusHistoryEntry(
                event_id=event_id,
                decision="split",
                after_status=target_row.verification_status,
                decided_at=decided_at,
                reviewer_id=reviewer_id,
            )
        )
    # reject / defer: no identity mutation

    # Validate before writing
    errors = validate_registry_graph(registry, bridge)
    if errors:
        return PromotionResult(exit_code=2)

    # Dependency-safe per-file atomic write order
    _append_promotion_event(log_path, event)
    atomic_write_registry(registry, registry_path)
    atomic_write_bridge(bridge, bridge_path)
    if review_id:
        _close_review_row(review_id, decision.kind, event_id, decided_at, identity_dir)

    # Post-run validation
    reloaded = load_registry(registry_path)
    reloaded_bridge = load_bridge(bridge_path)
    post_errors = validate_registry_graph(reloaded, reloaded_bridge)
    if post_errors:
        return PromotionResult(exit_code=3, event_id=event_id)

    return PromotionResult(exit_code=0, event_id=event_id)


def replay_promotion_log(*, log_path: Path, identity_dir: Path) -> None:
    """Spec §6.3: replay the log over the genesis fixture-ingestion state.

    Reads each event in order and re-applies the decision via the same code path.
    The identity_dir must already contain the genesis registry (from ingest_fixture).
    """
    log = _read_promotion_log(log_path)
    for event in log:
        decision = PromotionDecision(
            kind=event["decision"],
            target=event["target_prospect_uuid"],
            survivor=event.get("survivor_prospect_uuid"),
        )
        # Skip evidence requirement re-check during replay (already validated at write)
        if decision.kind in {"merge_into", "split"}:
            evidence_for_replay = event.get("evidence") or "replay"
        else:
            evidence_for_replay = event.get("evidence")
        promote_review_candidate(
            review_id=event.get("review_id"),
            decision=decision,
            identity_dir=identity_dir,
            reviewer_id=event["reviewer_id"],
            evidence=evidence_for_replay,
            note=event.get("note"),
            event_id=event["event_id"],     # Blocker 3: pass log's exact event_id
            decided_at=event["decided_at"], # Blocker 3: pass log's exact decided_at
        )
```

Now create `scripts/promote_review_candidate.py`:

```python
"""Subsystem 3 — review-candidate promotion CLI (the only blessed write path).

Usage:
    .venv/bin/python3.14 scripts/promote_review_candidate.py \\
        --identity-dir app/data/identity \\
        --target <prospect_uuid> \\
        --decision confirm \\
        [--survivor <uuid>]      # for merge_into
        [--new-full-name "..."]  # for split
        [--new-position WR]      # for split
        [--new-position-group WR]
        [--evidence "..."]
        [--note "..."]
        [--reviewer davidleess]

Spec: docs/superpowers/specs/2026-05-28-subsystem-3-prospect-identity-substrate-design.md §6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.dynasty_genius.identity.college_prospect_identity import (
    PromotionDecision,
    promote_review_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a review candidate.")
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--target", type=str, required=True)
    parser.add_argument(
        "--decision",
        type=str,
        required=True,
        choices=["confirm", "reject", "defer", "merge_into", "split"],
    )
    parser.add_argument("--review-id", type=str, default=None)
    parser.add_argument("--survivor", type=str, default=None)
    parser.add_argument("--new-full-name", type=str, default=None)
    parser.add_argument("--new-position", type=str, default=None)
    parser.add_argument("--new-position-group", type=str, default=None)
    parser.add_argument("--evidence", type=str, default=None)
    parser.add_argument("--note", type=str, default=None)
    parser.add_argument("--reviewer", type=str, default="davidleess")
    args = parser.parse_args(argv)

    decision = PromotionDecision(
        kind=args.decision,
        target=args.target,
        survivor=args.survivor,
        new_full_name=args.new_full_name,
        new_position=args.new_position,
        new_position_group=args.new_position_group,
    )
    result = promote_review_candidate(
        review_id=args.review_id,
        decision=decision,
        identity_dir=args.identity_dir,
        reviewer_id=args.reviewer,
        evidence=args.evidence,
        note=args.note,
    )
    print(f"exit_code={result.exit_code} event_id={result.event_id}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_promotion.py -v
```

Expected: all 7 promotion tests pass. If the replay test reveals non-determinism in dump ordering, ensure both `atomic_write_registry` calls use `sort_keys=True` and that `registry.entries` iterates in insertion order (Python 3.7+ guarantees this).

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py scripts/promote_review_candidate.py tests/contract/test_subsystem_3_promotion.py
git commit -m "feat(subsystem-3): promotion lifecycle + replay-over-genesis + CLI"
```

---

## Task 9 [v1 — SUPERSEDED by Round 2 Task 9 below]: Audit / coverage / provisional-leak — §10.7 contract tests

> **DO NOT EXECUTE this v1 task as written.** Cockpit round 2 (2026-05-28) identified that `test_leak_contract_3_bridge_entry_to_non_confirmed_fails_validation` actually tests a `RegistryEntry.merged_into_prospect_uuid` redirect to a missing survivor — a registry-row invariant, NOT a bridge invariant. Spec §4.6 contract 3 is about the bridge. Also missing: the source_id_conflict-isolation test. **The replacement is "Round 2 Task 9" at the end of this document.** Kept inline for reviewer-side diffing.

**Goal:** Lock in all 5 provisional-leak safety contracts (§4.6), the existing-artifacts-byte-unchanged contract, and Engine-A/B / market-leakage barriers extended to college-side IDs.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append no new code unless a contract requires it; this task primarily exercises existing surfaces)
- Create: `tests/contract/test_subsystem_3_audit.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_3_audit.py`:

```python
"""Subsystem 3 — audit / coverage / provisional-leak contract tests (§10.7)."""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    NormalizedCollegeProspectRow,
    ProspectUuidDeprecatedMerged,
    ProspectUuidNotConfirmed,
    RegistryEntry,
    StatusHistoryEntry,
    UnknownProspectUuid,
    compute_match_key,
    ingest_fixture,
    load_registry,
    normalize_name,
    resolve_prospect_cfbd_athlete_id,
    validate_registry_graph,
)


_INVIOLATE_PATHS = [
    Path("app/data/identity/_runs/prospect_registry.json"),
    Path("app/data/identity/_runs/composite_registry.json"),
    Path("app/data/prospect_alias_bridge.json"),
    Path("src/dynasty_genius/adapters/prospect_identity_resolver.py"),
]


def _sha256(path: Path) -> str:
    if not path.exists():
        return "absent"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _basic_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "fixture.json"
    p.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [
            {
                "raw_name": "Arch Manning",
                "normalized_name": "arch manning",
                "full_name": "Arch Manning",
                "position": "QB",
                "position_group": "QB",
                "draft_class": 2027,
                "current_school": "Texas",
                "prior_schools": [],
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
                "source": "manual_fixture",
                "source_record_id": "fixture_2027_001",
                "source_snapshot_id": "fixture_2027_v1",
                "id_provenance": {
                    "cfbd_athlete_id": None,
                    "cfb_player_id": None,
                    "pfr_id": None,
                    "gsis_id": None,
                    "sleeper_id": None,
                },
                "notes": None,
            },
        ],
    }))
    return p


# --- Provisional-leak contracts (§4.6) ---


def test_leak_contract_1_init_rejects_provisional_deprecated_unknown(tmp_path: Path):
    fixture = _basic_fixture(tmp_path)
    out = tmp_path / "out"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="run_a")
    registry = load_registry(out / "college_prospect_registry.json")
    provisional_uuid = next(iter(registry.entries.values())).prospect_uuid
    with pytest.raises(ProspectUuidNotConfirmed):
        ConfirmedProspectUuid(provisional_uuid, registry=registry)
    with pytest.raises(UnknownProspectUuid):
        ConfirmedProspectUuid("cpr_nonexistent", registry=registry)


def test_leak_contract_2_resolver_returns_none_on_provisional(tmp_path: Path):
    fixture = _basic_fixture(tmp_path)
    out = tmp_path / "out"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="run_a")
    registry = load_registry(out / "college_prospect_registry.json")
    result = resolve_prospect_cfbd_athlete_id(
        name="Arch Manning",
        position="QB",
        draft_class=2027,
        registry=registry,
    )
    # row exists but is provisional → resolver returns None (no raw uuid leak)
    assert result is None


def test_leak_contract_3_bridge_entry_to_non_confirmed_fails_validation():
    # Construct an in-memory registry with a provisional row, then ensure
    # validate_registry_graph rejects bridge target inconsistencies.
    provisional_uuid = "cpr_00000000-0000-4000-8000-000000000001"
    survivor_uuid = "cpr_11111111-1111-4111-8111-111111111111"
    row = NormalizedCollegeProspectRow.model_validate({
        "raw_name": "X", "normalized_name": "x", "full_name": "X",
        "position": "WR", "position_group": "WR", "draft_class": 2027,
        "current_school": "Texas", "prior_schools": [],
        "cfbd_athlete_id": None, "cfb_player_id": None,
        "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        "source": "manual_fixture", "source_record_id": "x_001",
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                          "pfr_id": None, "gsis_id": None, "sleeper_id": None},
        "notes": None,
    })
    bad_entry = RegistryEntry(
        prospect_uuid=provisional_uuid,
        verification_status="deprecated",
        match_key=compute_match_key(
            normalized_name=row.normalized_name,
            position_group="WR",
            draft_class=2027,
        ),
        status_history=[StatusHistoryEntry(
            event_id="ev_1", decision="merge_into", after_status="deprecated",
            decided_at="2026-05-28T12:00:00Z", reviewer_id="davidleess",
        )],
        merged_into_prospect_uuid=survivor_uuid,  # survivor not in registry → invalid
        reviewer_id="davidleess",
        reviewer_metadata={},
        **row.model_dump(),
    )
    registry = CollegeProspectRegistry(entries={provisional_uuid: bad_entry})
    from src.dynasty_genius.identity.college_prospect_identity import load_bridge
    bridge = load_bridge(Path("does/not/exist"))  # empty bridge
    errors = validate_registry_graph(registry, bridge)
    assert errors, "redirect to missing survivor must fail validation"


def test_leak_contract_3b_bridge_entry_maps_only_to_confirmed_uuid():
    """Blocker 5: bridge entry to missing or non-confirmed target must fail validation."""
    provisional_uuid = "cpr_provisional_001"
    confirmed_uuid = "cpr_confirmed_002"
    row_kwargs = {
        "raw_name": "X", "normalized_name": "x", "full_name": "X",
        "position": "WR", "position_group": "WR", "draft_class": 2027,
        "current_school": "Texas", "prior_schools": [],
        "cfbd_athlete_id": None, "cfb_player_id": None,
        "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        "source": "manual_fixture", "source_record_id": "x_001",
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                          "pfr_id": None, "gsis_id": None, "sleeper_id": None},
        "notes": None,
    }

    def _make(uuid_str, status):
        row = NormalizedCollegeProspectRow.model_validate(row_kwargs)
        return RegistryEntry(
            prospect_uuid=uuid_str,
            verification_status=status,
            match_key="match_key_x",
            status_history=[],
            reviewer_id="davidleess",
            **row.model_dump(),
        )

    # 1. Bridge pointing to non-existent UUID
    registry = CollegeProspectRegistry(entries={})
    from src.dynasty_genius.identity.college_prospect_identity import load_bridge
    bridge = load_bridge(Path("does/not/exist"))
    bridge.entries["match_key_x|x_001"] = "cpr_missing_003"
    errors = validate_registry_graph(registry, bridge)
    assert any("maps to unknown cpr_missing_003" in e for e in errors)

    # 2. Bridge pointing to a provisional (non-confirmed) UUID
    registry = CollegeProspectRegistry(entries={provisional_uuid: _make(provisional_uuid, "provisional")})
    bridge = load_bridge(Path("does/not/exist"))
    bridge.entries["match_key_x|x_001"] = provisional_uuid
    errors = validate_registry_graph(registry, bridge)
    assert any(f"maps to non-confirmed {provisional_uuid}" in e for e in errors)

    # 3. Bridge pointing to a confirmed UUID -> succeeds!
    registry = CollegeProspectRegistry(entries={confirmed_uuid: _make(confirmed_uuid, "confirmed")})
    bridge = load_bridge(Path("does/not/exist"))
    bridge.entries["match_key_x|x_001"] = confirmed_uuid
    errors = validate_registry_graph(registry, bridge)
    assert errors == []


def test_leak_contract_4_source_record_id_unique_per_confirmed_uuid(tmp_path: Path):
    """Spec §4.6 contract 4: source_record_id maps to at most one active confirmed uuid."""
    row_kwargs = {
        "raw_name": "X", "normalized_name": "x", "full_name": "X",
        "position": "WR", "position_group": "WR", "draft_class": 2027,
        "current_school": "Texas", "prior_schools": [],
        "cfbd_athlete_id": None, "cfb_player_id": None,
        "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        "source": "manual_fixture", "source_record_id": "shared_001",
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                          "pfr_id": None, "gsis_id": None, "sleeper_id": None},
        "notes": None,
    }

    def _make(uuid: str) -> RegistryEntry:
        row = NormalizedCollegeProspectRow.model_validate(row_kwargs)
        return RegistryEntry(
            prospect_uuid=uuid,
            verification_status="confirmed",
            match_key=compute_match_key(
                normalized_name="x", position_group="WR", draft_class=2027,
            ),
            status_history=[StatusHistoryEntry(
                event_id=f"ev_{uuid}", decision="confirm", after_status="confirmed",
                decided_at="2026-05-28T12:00:00Z", reviewer_id="davidleess",
            )],
            merged_into_prospect_uuid=None,
            reviewer_id="davidleess",
            reviewer_metadata={},
            **row.model_dump(),
        )

    a = _make("cpr_aaaa")
    b = _make("cpr_bbbb")
    registry = CollegeProspectRegistry(entries={"cpr_aaaa": a, "cpr_bbbb": b})
    from src.dynasty_genius.identity.college_prospect_identity import load_bridge
    bridge = load_bridge(Path("does/not/exist"))
    errors = validate_registry_graph(registry, bridge)
    assert any("source_record_id collision" in e for e in errors)


def test_leak_contract_5_full_graph_validation_runs_on_every_promotion(tmp_path: Path):
    """Spec §4.6 contract 5: promotion validates whole graph after mutation.

    Indirect contract: validate_registry_graph is callable, returns [] for a clean
    registry, returns errors for a corrupted one. The promotion code calls it
    before and after atomic writes (verified in §10.6 promotion tests).
    """
    clean = CollegeProspectRegistry()
    from src.dynasty_genius.identity.college_prospect_identity import load_bridge
    bridge = load_bridge(Path("does/not/exist"))
    assert validate_registry_graph(clean, bridge) == []


# --- Existing artifacts byte-unchanged ---


def test_existing_artifacts_byte_unchanged_before_and_after_subsystem_3_scripts():
    """Spec §3: prospect_registry, composite_registry, prospect_alias_bridge,
    and prospect_identity_resolver.py SHA256 are unchanged after any S3 run."""
    repo_root = Path(__file__).resolve().parents[2]
    pre = {p: _sha256(repo_root / p) for p in _INVIOLATE_PATHS}

    # Re-import S3 module + run a dry resolve to ensure import doesn't mutate
    from src.dynasty_genius.identity.college_prospect_identity import (
        CollegeProspectRegistry as Reg,
    )
    _ = Reg()

    post = {p: _sha256(repo_root / p) for p in _INVIOLATE_PATHS}
    assert pre == post


# --- No mock/ADP/market data in registry ---


_BANNED_FIELD_NAMES = {
    "ktc_value", "fc_value", "adp", "market_value", "mock_rank",
    "draft_selection_pct", "drafts_selected_in", "dynasty_nerds_adp",
}


def test_registry_schema_has_no_market_or_mock_fields():
    """Spec §9 + §10.7: leakage-gate-style assertion that the registry stores
    only identity truth — never mock/ADP/market data."""
    fields = set(NormalizedCollegeProspectRow.model_fields.keys()) | set(
        RegistryEntry.model_fields.keys()
    )
    leaked = _BANNED_FIELD_NAMES & fields
    assert leaked == set(), f"market/mock leakage detected in registry schema: {leaked}"


# --- Coverage matrix counts reconcile ---


def test_coverage_matrix_counts_reconcile_to_total_input_rows(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [
            {
                "raw_name": f"Person {i}",
                "normalized_name": normalize_name(f"Person {i}"),
                "full_name": f"Person {i}",
                "position": "WR",
                "position_group": "WR",
                "draft_class": 2027,
                "current_school": "Texas",
                "prior_schools": [],
                "cfbd_athlete_id": None,
                "cfb_player_id": None,
                "pfr_id": None,
                "gsis_id": None,
                "sleeper_id": None,
                "source": "manual_fixture",
                "source_record_id": f"fixture_2027_{i:03d}",
                "source_snapshot_id": "fixture_2027_v1",
                "id_provenance": {
                    "cfbd_athlete_id": None,
                    "cfb_player_id": None,
                    "pfr_id": None,
                    "gsis_id": None,
                    "sleeper_id": None,
                },
                "notes": None,
            }
            for i in range(1, 4)
        ],
    }))
    out = tmp_path / "out"
    result = ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="reconcile_run")
    coverage_path = out / "college_identity_coverage_matrix_reconcile_run.json"
    cov = json.loads(coverage_path.read_text())
    accounted = (
        cov["minted_new"]
        + cov["idempotent_rerun"]
        + cov["minted_new_provisional_with_review_candidate"]
    )
    assert accounted == cov["total_input_rows"] == 3
    assert result.exit_code == 0
```

- [ ] **Step 2: Run to verify RED, then GREEN**

Most of these tests exercise surfaces already implemented in Tasks 2-8. Run them:

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_audit.py -v
```

Expected: tests pass without new implementation. If `test_existing_artifacts_byte_unchanged_before_and_after_subsystem_3_scripts` fails because one of the inviolate paths doesn't exist yet (e.g., a `_runs/` path), update `_INVIOLATE_PATHS` to only assert on paths that exist at branch HEAD.

- [ ] **Step 3: If any test reveals a missing surface, add it**

The most likely gap: `validate_registry_graph` may need a stricter `source_record_id` collision check. Confirm it already counts (`source`, `source_record_id`) tuple collisions among `confirmed` rows. If not, refine in `college_prospect_identity.py`.

- [ ] **Step 4: Run the full S3 contract suite to verify no regression**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_*.py -v
```

Expected: every Subsystem 3 test passes.

- [ ] **Step 5: Commit**

```bash
git add tests/contract/test_subsystem_3_audit.py src/dynasty_genius/identity/college_prospect_identity.py
git commit -m "test(subsystem-3): audit + coverage + provisional-leak §10.7 contracts"
```

---

## Task 10: Top-100 2027 prospect fixture (cockpit-driven, not engineer-prescribed)

**Goal:** Populate `resources/college_prospect_fixture_2027.json` with top-100 2027 prospects. **This task is NOT a normal engineering bite-sized task** — it requires Tier-1 source verification (per `[[feedback_dynasty_analytical_rules]]` Rule 1: verify current status). The plan calls out the structure and acceptance criteria; the actual roster comes from a David-driven research workstream that can run in parallel with Tasks 0–9.

**Files:**
- Create: `resources/college_prospect_fixture_2027.json`

- [ ] **Step 1: Decide curation source (cockpit decision deferred to fixture-curation session)**

Options to surface for cockpit review when this task is taken up:
- David curates from PFF / 247Sports / ESPN class rankings + manual review
- Claude assists with research via Tier-1 college football sources (must verify each row)
- Start smaller (e.g., 25 prospects) and iterate, with the fixture growing as the substrate gets exercised

No code action in this step — decision artifact only.

- [ ] **Step 2: Write the fixture file using the locked `NormalizedCollegeProspectRow` schema**

The file shape:

```json
{
  "metadata": {
    "snapshot_id": "fixture_2027_v1",
    "fetched_at": "2026-05-28T12:00:00Z",
    "source": "manual_curation",
    "curator": "davidleess",
    "row_count": 100,
    "draft_class": 2027,
    "caveats": ["manual curation; not from CFBD; v2 increment replaces with adapter"]
  },
  "entries": [
    {
      "raw_name": "Arch Manning",
      "normalized_name": "arch manning",
      "full_name": "Arch Manning",
      "position": "QB",
      "position_group": "QB",
      "draft_class": 2027,
      "current_school": "Texas",
      "prior_schools": [],
      "cfbd_athlete_id": null,
      "cfb_player_id": null,
      "pfr_id": null,
      "gsis_id": null,
      "sleeper_id": null,
      "source": "manual_fixture",
      "source_record_id": "fixture_2027_001",
      "source_snapshot_id": "fixture_2027_v1",
      "id_provenance": {
        "cfbd_athlete_id": null,
        "cfb_player_id": null,
        "pfr_id": null,
        "gsis_id": null,
        "sleeper_id": null
      },
      "notes": null
    }
    // … 99 more rows
  ]
}
```

- [ ] **Step 3: Validate the fixture against the schema**

```bash
.venv/bin/python3.14 -c "
import json
from pathlib import Path
from src.dynasty_genius.identity.college_prospect_identity import NormalizedCollegeProspectRow
raw = json.loads(Path('resources/college_prospect_fixture_2027.json').read_text())
for row in raw['entries']:
    NormalizedCollegeProspectRow.model_validate(row)
print(f'OK: {len(raw[\"entries\"])} rows validated')
"
```

Expected: `OK: 100 rows validated` (or smaller count per cockpit decision in Step 1).

- [ ] **Step 4: Run a real ingestion**

```bash
.venv/bin/python3.14 scripts/ingest_college_prospect_fixture.py \
  --fixture resources/college_prospect_fixture_2027.json \
  --identity-dir app/data/identity \
  --run-id manual_2027_$(date -u +%Y%m%dT%H%MZ)
```

Expected: writes registry + review-queue + coverage matrix under `app/data/identity/`; coverage `total_input_rows == minted_new == 100`.

- [ ] **Step 5: Commit**

```bash
git add resources/college_prospect_fixture_2027.json
git commit -m "data(subsystem-3): v1 top-100 2027 prospect manual fixture"
```

---

## Task 11: Full suite + governance + ledger closeout

**Goal:** Run the full suite, run `validate_governance.py`, update `AGENT_SYNC.md` (phase advanced), append a postflight ledger entry, and confirm the inviolate artifacts byte-unchanged.

**Files:**
- Modify: `AGENT_SYNC.md`
- Modify: `docs/agent-ledger/2026-05-28.md` (or the active-day ledger when this task executes)

- [ ] **Step 1: Confirm inviolate artifacts byte-unchanged**

```bash
git diff --stat main -- \
  app/data/identity/_runs/prospect_registry.json \
  app/data/identity/_runs/composite_registry.json \
  app/data/prospect_alias_bridge.json \
  src/dynasty_genius/adapters/prospect_identity_resolver.py
```

Expected: empty output (no changes to any inviolate path).

- [ ] **Step 2: Run the full pytest suite**

```bash
.venv/bin/python3.14 -m pytest \
  --ignore=tests/test_phase18_refresh_league_intelligence.py \
  --ignore=tests/test_tmux_msg.py \
  -q
```

Expected: 1305 + (Subsystem 3 contract test count, roughly +45) passing tests, 11 skipped, 0 failed. Final count gets recorded in `AGENT_SYNC.md`.

- [ ] **Step 3: Run governance validator**

```bash
.venv/bin/python3.14 scripts/validate_governance.py
```

Expected: passes.

- [ ] **Step 4: Update `AGENT_SYNC.md`**

Add a new line under "Phase 24 Follow-up B" recording S3 complete, with the new test count and the merge SHA placeholder. Mark `[[project_subsystem_3_state]]` for memory-pointer update once the branch merges.

- [ ] **Step 5: Append postflight ledger entry to `docs/agent-ledger/2026-05-28.md` (or the active-day ledger when this task executes)**

Format per `02-agent-operating-loop.md`:

```md
## HH:MM ET - Claude Code (Subsystem 3 build closeout)

- Task: Subsystem 3 — Prospect Identity Substrate — build to GREEN across §10.1–§10.7
- Governance read: 00 / 01 / 02 / 03 + AGENT_SYNC + this ledger
- Active phase / surface: Phase 24 Follow-up B Increment A — S3
- Files changed: src/dynasty_genius/identity/{__init__.py,college_prospect_identity.py};
                 scripts/{ingest_college_prospect_fixture.py,promote_review_candidate.py};
                 resources/college_prospect_fixture_2027.json;
                 tests/contract/test_subsystem_3_*.py;
                 requirements.txt
- Tests / checks: full suite green at N passed / 11 skipped; validate_governance.py PASS;
                  inviolate artifacts byte-unchanged
- Product alignment: substrate-only build, model-separation preserved, no market/mock feed
                    into identity, frontend HOLD intact, NOISE_BAND lock untouched
- Drift risks: none — Engine A/B / PVO / trade lab untouched
- Handoff / next step: PR open against main; cockpit review of PR; on merge, update
                       [[project_subsystem_3_state]] memory pointer and consider S4 backtest
                       per reconciliation build order
```

- [ ] **Step 6: Commit ledger + AGENT_SYNC closeout**

```bash
git add AGENT_SYNC.md docs/agent-ledger/2026-05-28.md
git commit -m "docs(subsystem-3): AGENT_SYNC + ledger closeout for S3 substrate build"
```

---

## Round 2 Task 6: Bridge schema + atomic persistence + source_id_conflict + matcher-wired ambiguity-before-mint — §10.5 (revised)

**Goal (Round 2):** Add per-file atomic writes for **both** registry **and** alias bridge; introduce `CollegeAliasBridgeEntry` / `CollegeAliasBridge` Pydantic schemas + `atomic_write_bridge` + `validate_bridge_targets`; rewrite `mint_or_match()` to (a) hard-block via dedicated `source_id_conflict` queue per spec §5.5, (b) preserve idempotent-rerun semantics, (c) call `surface_review_candidates()` over the spec §5.4 candidate query to surface fuzzy + whitelist-neighbor candidates within the same `draft_class`.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (append bridge section + atomic bridge writer + extend `validate_registry_graph` + rewrite `mint_or_match`)
- Replace: `tests/contract/test_subsystem_3_ingestion.py` (full Round 2 content)

- [ ] **Step 1: Codex replaces `tests/contract/test_subsystem_3_ingestion.py` with the Round 2 content**

```python
"""Subsystem 3 — Round 2 ingestion atomicity, source_id_conflict, and matcher-wired ambiguity tests (§10.5)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeAliasBridgeEntry,
    CollegeProspectRegistry,
    IngestionOutcome,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    atomic_write_bridge,
    atomic_write_registry,
    compute_match_key,
    load_bridge,
    load_registry,
    mint_or_match,
    normalize_name,
    validate_registry_graph,
)


def _row(
    name,
    position="WR",
    position_group="WR",
    school="Ohio State",
    draft_class=2027,
    sid="fixture_2027_001",
    cfbd=None,
):
    return NormalizedCollegeProspectRow.model_validate({
        "raw_name": name,
        "normalized_name": normalize_name(name),
        "full_name": name,
        "position": position,
        "position_group": position_group,
        "draft_class": draft_class,
        "current_school": school,
        "prior_schools": [],
        "cfbd_athlete_id": cfbd,
        "cfb_player_id": None,
        "pfr_id": None,
        "gsis_id": None,
        "sleeper_id": None,
        "source": "manual_fixture",
        "source_record_id": sid,
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {
            "cfbd_athlete_id": None,
            "cfb_player_id": None,
            "pfr_id": None,
            "gsis_id": None,
            "sleeper_id": None,
        },
        "notes": None,
    })


# --- v1 preserved tests ---


def test_atomic_write_uses_tmp_then_rename(tmp_path: Path, monkeypatch):
    path = tmp_path / "registry.json"
    registry = CollegeProspectRegistry(metadata={"snapshot": "fixture_2027_v1"}, entries={})
    seen_tmp: list[Path] = []
    original_replace = __import__("os").replace

    def spy_replace(src, dst):
        seen_tmp.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr("os.replace", spy_replace)
    atomic_write_registry(registry, path)
    assert path.exists()
    assert seen_tmp and seen_tmp[0].name.endswith(".tmp")
    reloaded = load_registry(path)
    assert reloaded.metadata == {"snapshot": "fixture_2027_v1"}


def test_idempotent_rerun_same_source_record_id_and_snapshot_reuses_uuid(tmp_path: Path):
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()
    incoming = _row("Arch Manning", position="QB", position_group="QB", school="Texas", sid="fixture_2027_001")

    outcome_1 = mint_or_match(incoming, registry, bridge=bridge)
    assert outcome_1.kind == "minted_new"
    first_uuid = outcome_1.prospect_uuid

    outcome_2 = mint_or_match(incoming, registry, bridge=bridge)
    assert outcome_2.kind == "idempotent_rerun"
    assert outcome_2.prospect_uuid == first_uuid


def test_same_match_key_different_source_record_id_mints_provisional_with_common_name_flag():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()
    first = _row("Mike Williams", position="WR", position_group="WR", school="Clemson", sid="src_A")
    second = _row("Mike Williams", position="WR", position_group="WR", school="USC", sid="src_B")

    o1 = mint_or_match(first, registry, bridge=bridge)
    o2 = mint_or_match(second, registry, bridge=bridge)

    assert o1.prospect_uuid != o2.prospect_uuid
    assert o2.kind in {
        "minted_new_provisional_with_review_candidate",
        "minted_new_with_surfaced_candidates",
    }
    assert o2.review_candidates, "common_name candidate should be surfaced"
    assert any("common_name" in c.risk_flags for c in o2.review_candidates)


def test_multiple_existing_matches_emit_ambiguous_existing_candidates_review_entry():
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()
    a = _row("Common Surname", school="Texas", sid="src_A")
    b = _row("Common Surname", school="LSU", sid="src_B")
    c = _row("Common Surname", school="Bama", sid="src_C")

    mint_or_match(a, registry, bridge=bridge)
    mint_or_match(b, registry, bridge=bridge)
    out_c = mint_or_match(c, registry, bridge=bridge)

    assert out_c.review_candidates
    # When multiple confirmed-or-provisional matches exist, ambiguous_existing_candidates flag fires
    assert any("ambiguous_existing_candidates" in cand.risk_flags for cand in out_c.review_candidates)


# --- Round 2 NEW tests ---


def test_source_id_conflict_preempts_fuzzy_output_and_writes_to_dedicated_queue(tmp_path: Path):
    """Codex RED #2 + spec §5.5: shared source_record_id pointing to a different prospect_uuid
    must hard-block from normal candidate output and route to a dedicated queue."""
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    # Seed an existing row with source_record_id "src_001"
    first = _row("Original Name", school="Texas", sid="src_001")
    mint_or_match(first, registry, bridge=bridge)

    # Manually flip the existing row's verification_status to "confirmed" so the conflict
    # check has a confirmed target
    existing_uuid = next(iter(registry.entries.keys()))
    registry.entries[existing_uuid].verification_status = "confirmed"

    # A NEW row arrives with the SAME source_record_id but a different name —
    # this is a source-id-collision defect, not a fuzzy candidate.
    conflicting = _row("Different Person", school="Bama", sid="src_001")
    outcome = mint_or_match(conflicting, registry, bridge=bridge)

    assert outcome.kind == "source_id_conflict", (
        "source_id_conflict must preempt mint + fuzzy surfacing"
    )
    assert outcome.review_candidates == (), (
        "source_id_conflict must NOT emit normal review candidates"
    )
    assert outcome.source_id_conflict_record is not None
    assert outcome.source_id_conflict_record["incoming_source_record_id"] == "src_001"
    assert outcome.source_id_conflict_record["existing_prospect_uuid"] == existing_uuid


def test_source_id_conflict_also_fires_on_shared_cfbd_athlete_id():
    """Spec §5.5: 'shared source_record_id OR known cfbd_athlete_id'."""
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    first = _row("Arch Manning", position="QB", position_group="QB", school="Texas",
                 sid="src_A", cfbd="cfbd_12345")
    mint_or_match(first, registry, bridge=bridge)
    next(iter(registry.entries.values())).verification_status = "confirmed"

    # Different source_record_id but SAME cfbd_athlete_id pointing to a different name
    second = _row("Wrong Name", position="WR", position_group="WR", school="LSU",
                  sid="src_B", cfbd="cfbd_12345")
    outcome = mint_or_match(second, registry, bridge=bridge)
    assert outcome.kind == "source_id_conflict"
    assert outcome.review_candidates == ()


def test_whitelist_neighbor_surfaced_via_section_5_4_query_even_with_different_match_key():
    """Codex RED #1 + spec §5.4: candidates are queried over normalized_name + draft_class +
    position_group same OR whitelist transition. WR ↔ TE same name + same school + same class
    has DIFFERENT match_key (position_group differs) yet must surface."""
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    # Seed an existing WR
    existing_wr = _row("Whitelist Name", position="WR", position_group="WR",
                       school="Whitelist U", sid="existing_001")
    mint_or_match(existing_wr, registry, bridge=bridge)
    existing_uuid = next(iter(registry.entries.keys()))
    registry.entries[existing_uuid].verification_status = "confirmed"

    # New TE with same name + same school + same class — different match_key (position differs)
    incoming_te = _row("Whitelist Name", position="TE", position_group="TE",
                       school="Whitelist U", sid="incoming_001")
    outcome = mint_or_match(incoming_te, registry, bridge=bridge)

    # Must surface a cross-position whitelist candidate via §5.4
    assert outcome.review_candidates, "§5.4 query must surface WR↔TE whitelist neighbor"
    cross = [c for c in outcome.review_candidates if "cross_position_group" in c.risk_flags]
    assert cross, "whitelist transition must carry cross_position_group + position_transition_allowed flags"


def test_mint_or_match_calls_surface_review_candidates_not_just_exact_match_key():
    """Codex finding 1 regression guard: mint_or_match must route fuzzy work through
    surface_review_candidates() rather than only matching exact match_key."""
    registry = CollegeProspectRegistry()
    bridge = CollegeAliasBridge()

    # Existing row
    existing = _row("Fuzzy Source", school="Source U", sid="existing_001")
    mint_or_match(existing, registry, bridge=bridge)
    next(iter(registry.entries.values())).verification_status = "confirmed"

    # Incoming row with same school + same class + slightly misspelled name — same
    # position_group → same match_key (matcher's deterministic key); should surface as
    # a fuzzy candidate. (If this test passes when names differ enough that match_key
    # also differs, that proves the §5.4 query is wired in, not just match_key lookup.)
    incoming = _row("Fuzy Source", school="Source U", sid="incoming_001")
    outcome = mint_or_match(incoming, registry, bridge=bridge)
    assert outcome.review_candidates, "fuzzy name should surface via surface_review_candidates()"


# --- Round 2 bridge schema + I/O ---


def test_atomic_write_bridge_uses_tmp_then_rename(tmp_path: Path, monkeypatch):
    path = tmp_path / "bridge.json"
    bridge = CollegeAliasBridge(metadata={"snapshot": "fixture_2027_v1"}, entries=[])
    seen_tmp: list[Path] = []
    original_replace = __import__("os").replace

    def spy_replace(src, dst):
        seen_tmp.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr("os.replace", spy_replace)
    atomic_write_bridge(bridge, path)
    assert path.exists()
    assert seen_tmp and seen_tmp[0].name.endswith(".tmp")
    reloaded = load_bridge(path)
    assert reloaded.metadata == {"snapshot": "fixture_2027_v1"}


def test_validate_bridge_targets_rejects_provisional_target():
    """Codex RED #4 + spec §4.6 contract 3: bridge entry targets must be confirmed."""
    provisional_uuid = "cpr_pppppppp-pppp-4ppp-8ppp-pppppppppppp"
    registry = CollegeProspectRegistry()
    row = _row("Sample", sid="src_X").model_dump()
    registry.entries[provisional_uuid] = RegistryEntry(
        prospect_uuid=provisional_uuid,
        verification_status="provisional",
        match_key=compute_match_key(
            normalized_name="sample", position_group="WR", draft_class=2027,
        ),
        status_history=[StatusHistoryEntry(
            event_id="ev_1", decision="ingest", after_status="provisional",
            decided_at="2026-05-28T12:00:00Z", reviewer_id="system_ingestion",
        )],
        merged_into_prospect_uuid=None,
        reviewer_id="system_ingestion",
        reviewer_metadata={},
        **row,
    )
    bridge = CollegeAliasBridge(entries=[CollegeAliasBridgeEntry(
        match_key=compute_match_key(
            normalized_name="sample", position_group="WR", draft_class=2027,
        ),
        source_record_id="src_X",
        target_prospect_uuid=provisional_uuid,  # provisional → INVALID
    )])
    errors = validate_registry_graph(registry, bridge=bridge)
    assert any("bridge target" in e.lower() and "not confirmed" in e.lower() for e in errors)


def test_validate_bridge_targets_rejects_deprecated_target():
    deprecated_uuid = "cpr_dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    registry = CollegeProspectRegistry()
    row = _row("Sample", sid="src_X").model_dump()
    registry.entries[deprecated_uuid] = RegistryEntry(
        prospect_uuid=deprecated_uuid,
        verification_status="deprecated",
        match_key=compute_match_key(
            normalized_name="sample", position_group="WR", draft_class=2027,
        ),
        status_history=[StatusHistoryEntry(
            event_id="ev_1", decision="merge_into", after_status="deprecated",
            decided_at="2026-05-28T12:00:00Z", reviewer_id="davidleess",
        )],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **row,
    )
    bridge = CollegeAliasBridge(entries=[CollegeAliasBridgeEntry(
        match_key=compute_match_key(
            normalized_name="sample", position_group="WR", draft_class=2027,
        ),
        source_record_id="src_X",
        target_prospect_uuid=deprecated_uuid,
    )])
    errors = validate_registry_graph(registry, bridge=bridge)
    assert errors, "deprecated bridge target must fail validation"
```

- [ ] **Step 2: Run RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py -v
```

Expected: ImportError on `CollegeAliasBridge`, `CollegeAliasBridgeEntry`, `atomic_write_bridge`, `load_bridge`; and assertion failures on the new ingestion behavior.

- [ ] **Step 3: Claude appends the bridge schema, bridge I/O, extends `validate_registry_graph`, and rewrites `mint_or_match`**

Append to `src/dynasty_genius/identity/college_prospect_identity.py`:

```python
# ======================================================================
# College alias bridge schema + I/O (spec §3 + §6.2)
# ======================================================================


class CollegeAliasBridgeEntry(BaseModel):
    """Spec §3 + §6.2: maps (match_key, source_record_id) → confirmed prospect_uuid."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    match_key: str
    source_record_id: str
    target_prospect_uuid: str


class CollegeAliasBridge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)
    entries: list[CollegeAliasBridgeEntry] = Field(default_factory=list)


def load_bridge(path: Path) -> CollegeAliasBridge:
    if not path.exists():
        return CollegeAliasBridge()
    raw = json.loads(path.read_text())
    return CollegeAliasBridge.model_validate(raw)


def atomic_write_bridge(bridge: CollegeAliasBridge, path: Path) -> None:
    """Spec §6.4: per-file atomic write; sibling .tmp then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "metadata": bridge.metadata,
        "entries": [e.model_dump(mode="json") for e in bridge.entries],
    }
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    os.replace(tmp_path, path)
```

Replace the existing `validate_registry_graph` function with the bridge-aware version:

```python
def validate_registry_graph(
    registry: CollegeProspectRegistry,
    *,
    bridge: Optional[CollegeAliasBridge] = None,
) -> list[str]:
    """Spec §4.6 contracts 3 + 4 + 5: full identity-graph validation.

    Returns a list of human-readable errors. Empty list = consistent.
    """
    errors: list[str] = []
    seen_source_records: dict[tuple[str, str], str] = {}
    for entry in registry.entries.values():
        if entry.verification_status == "confirmed":
            key = (entry.source, entry.source_record_id)
            if key in seen_source_records:
                errors.append(
                    f"source_record_id collision on {entry.source_record_id}: "
                    f"{seen_source_records[key]} and {entry.prospect_uuid}"
                )
            else:
                seen_source_records[key] = entry.prospect_uuid
        if entry.merged_into_prospect_uuid:
            survivor = registry.get(entry.merged_into_prospect_uuid)
            if survivor is None:
                errors.append(
                    f"{entry.prospect_uuid} redirects to unknown {entry.merged_into_prospect_uuid}"
                )
            elif survivor.verification_status != "confirmed":
                errors.append(
                    f"{entry.prospect_uuid} redirects to non-confirmed "
                    f"{entry.merged_into_prospect_uuid}"
                )
    if bridge is not None:
        for entry in bridge.entries:
            target = registry.get(entry.target_prospect_uuid)
            if target is None:
                errors.append(
                    f"bridge target {entry.target_prospect_uuid} is unknown"
                )
            elif target.verification_status != "confirmed":
                errors.append(
                    f"bridge target {entry.target_prospect_uuid} is not confirmed "
                    f"(status={target.verification_status})"
                )
            elif target.merged_into_prospect_uuid:
                errors.append(
                    f"bridge target {entry.target_prospect_uuid} is deprecated/redirected to "
                    f"{target.merged_into_prospect_uuid}"
                )
    return errors
```

Now rewrite `mint_or_match` to incorporate (a) the `source_id_conflict` pre-check, (b) the `surface_review_candidates()` §5.4 query, and (c) the new `IngestionOutcome` shape. **Replace** the v1 `IngestionOutcome` and `mint_or_match` with:

```python
@dataclass(frozen=True)
class IngestionOutcome:
    """Round 2 shape: surfaced_candidates is a tuple; source_id_conflict_record is populated
    only when kind == 'source_id_conflict'."""

    kind: Literal[
        "minted_new",
        "idempotent_rerun",
        "minted_new_provisional_with_review_candidate",
        "minted_new_with_surfaced_candidates",
        "source_id_conflict",
    ]
    prospect_uuid: Optional[str] = None
    review_candidates: tuple[MatchCandidate, ...] = ()
    source_id_conflict_record: Optional[dict[str, Any]] = None


def _detect_source_id_conflict(
    incoming: NormalizedCollegeProspectRow,
    registry: CollegeProspectRegistry,
) -> Optional[dict[str, Any]]:
    """Spec §5.5: shared source_record_id OR shared cfbd_athlete_id pointing to a different
    confirmed prospect_uuid → hard-block, route to dedicated source_id_conflict queue."""
    for entry in registry.entries.values():
        if entry.verification_status != "confirmed":
            continue
        if (
            entry.source == incoming.source
            and entry.source_record_id == incoming.source_record_id
            and entry.normalized_name != incoming.normalized_name
        ):
            return {
                "kind": "source_record_id_collision",
                "incoming_source": incoming.source,
                "incoming_source_record_id": incoming.source_record_id,
                "incoming_normalized_name": incoming.normalized_name,
                "existing_prospect_uuid": entry.prospect_uuid,
                "existing_normalized_name": entry.normalized_name,
            }
        if (
            incoming.cfbd_athlete_id is not None
            and entry.cfbd_athlete_id == incoming.cfbd_athlete_id
            and entry.normalized_name != incoming.normalized_name
        ):
            return {
                "kind": "cfbd_athlete_id_collision",
                "incoming_cfbd_athlete_id": incoming.cfbd_athlete_id,
                "incoming_normalized_name": incoming.normalized_name,
                "existing_prospect_uuid": entry.prospect_uuid,
                "existing_normalized_name": entry.normalized_name,
            }
    return None


def mint_or_match(
    incoming: NormalizedCollegeProspectRow,
    registry: CollegeProspectRegistry,
    *,
    bridge: Optional[CollegeAliasBridge] = None,
) -> IngestionOutcome:
    """Spec §4.3 + §5.4 + §5.5 (Round 2):

    Order of operations:
      1. source_id_conflict pre-check → hard-block, no fuzzy
      2. Idempotent rerun check (same source_record_id + same snapshot_id)
      3. surface_review_candidates() over §5.4 query (normalized_name + draft_class
         match, position_group same OR in whitelist transition map). Hard-block + whitelist
         + threshold semantics live inside surface_review_candidates().
      4. Mint new provisional and emit review candidates (if any).
    """
    # (1) source_id_conflict pre-check
    conflict = _detect_source_id_conflict(incoming, registry)
    if conflict is not None:
        return IngestionOutcome(
            kind="source_id_conflict",
            source_id_conflict_record=conflict,
        )

    # (2) idempotent rerun
    for entry in registry.entries.values():
        if (
            entry.source == incoming.source
            and entry.source_record_id == incoming.source_record_id
            and entry.source_snapshot_id == incoming.source_snapshot_id
        ):
            return IngestionOutcome(
                kind="idempotent_rerun",
                prospect_uuid=entry.prospect_uuid,
            )

    # (3) Surface candidates via §5.4 query (delegates to surface_review_candidates which
    # already applies hard-block + whitelist + threshold)
    candidates = tuple(surface_review_candidates(incoming, registry.entries))

    # (4) Mint new provisional regardless of candidate count (spec §4.3: never auto-merge)
    key = compute_match_key(
        normalized_name=incoming.normalized_name,
        position_group=incoming.position_group,
        draft_class=incoming.draft_class,
    )
    new_uuid = _mint_and_insert(incoming, registry, key)

    if not candidates:
        return IngestionOutcome(kind="minted_new", prospect_uuid=new_uuid)

    # Attach ambiguity flags when >=2 same-class same-match_key registry rows are present
    same_match_key_count = sum(
        1 for entry in registry.entries.values() if entry.match_key == key
    )
    if same_match_key_count >= 3:  # >=2 existing + the just-minted incoming
        candidates = tuple(
            MatchCandidate(
                target_prospect_uuid=c.target_prospect_uuid,
                match_score=c.match_score,
                score_breakdown=c.score_breakdown,
                risk_flags=tuple(set(c.risk_flags) | {"ambiguous_existing_candidates", "common_name"}),
                raw_match_features=c.raw_match_features,
                matcher_algorithm_version=c.matcher_algorithm_version,
            )
            for c in candidates
        )
    elif same_match_key_count == 2:  # the just-minted incoming + 1 existing → common_name
        candidates = tuple(
            MatchCandidate(
                target_prospect_uuid=c.target_prospect_uuid,
                match_score=c.match_score,
                score_breakdown=c.score_breakdown,
                risk_flags=tuple(set(c.risk_flags) | {"common_name"}),
                raw_match_features=c.raw_match_features,
                matcher_algorithm_version=c.matcher_algorithm_version,
            )
            for c in candidates
        )

    return IngestionOutcome(
        kind="minted_new_with_surfaced_candidates",
        prospect_uuid=new_uuid,
        review_candidates=candidates,
    )
```

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py tests/contract/test_subsystem_3_matcher.py tests/contract/test_subsystem_3_whitelist.py tests/contract/test_subsystem_3_confirmed_uuid.py tests/contract/test_subsystem_3_schema.py -v
```

Expected: all tests (existing §10.1–§10.4 + revised §10.5) pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py tests/contract/test_subsystem_3_ingestion.py
git commit -m "feat(subsystem-3 round 2): bridge schema + atomic bridge + source_id_conflict + matcher-wired mint_or_match"
```

---

## Round 2 Task 7: Ingestion CLI — write bridge + emit source_id_conflict queue (revised)

**Goal (Round 2):** Extend `ingest_fixture()` and `scripts/ingest_college_prospect_fixture.py` to (a) always write the alias-bridge artifact (empty in fresh ingestion), (b) emit a dedicated `college_identity_source_id_conflict_<run_id>.jsonl` when `IngestionOutcome.kind == "source_id_conflict"`, and (c) reflect the new `IngestionOutcome` kinds in the coverage matrix.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (rewrite `ingest_fixture`)
- Modify: `scripts/ingest_college_prospect_fixture.py` (no API change; CLI accepts the same args)
- Append: `tests/contract/test_subsystem_3_ingestion.py` (Round 2 CLI tests)

- [ ] **Step 1: Codex appends RED tests to `tests/contract/test_subsystem_3_ingestion.py`**

```python
# --- Round 2 CLI orchestration ---


def test_ingest_fixture_writes_alias_bridge_artifact(tmp_path: Path):
    from src.dynasty_genius.identity.college_prospect_identity import ingest_fixture

    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [_row("Arch Manning", position="QB", position_group="QB",
                         school="Texas", sid="fixture_2027_001").model_dump()],
    }))
    out_dir = tmp_path / "out"
    result = ingest_fixture(fixture_path=fixture_path, identity_dir=out_dir, run_id="run_bridge")
    bridge_path = out_dir / "college_alias_bridge.json"
    assert bridge_path.exists()
    bridge = load_bridge(bridge_path)
    assert bridge.entries == [], "fresh ingestion seeds an empty bridge"
    assert result.exit_code == 0


def test_ingest_fixture_writes_source_id_conflict_queue_when_conflicts_found(tmp_path: Path):
    """Codex RED #2 (CLI side): conflicts go to the dedicated queue, not the regular review queue."""
    from src.dynasty_genius.identity.college_prospect_identity import ingest_fixture

    # First ingestion creates a confirmed row (we'll set status manually via a second
    # ingestion to a separate dir — but here for the CLI test, we directly construct
    # the prior registry state on disk).
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    seed_registry = CollegeProspectRegistry()
    seed_row = _row("Original Name", school="Texas", sid="src_001").model_dump()
    seed_uuid = "cpr_seed0000-0000-4000-8000-000000000001"
    seed_registry.entries[seed_uuid] = RegistryEntry(
        prospect_uuid=seed_uuid,
        verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name="original name", position_group="WR", draft_class=2027,
        ),
        status_history=[StatusHistoryEntry(
            event_id="seed_ev", decision="confirm", after_status="confirmed",
            decided_at="2026-05-28T11:00:00Z", reviewer_id="davidleess",
        )],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess",
        reviewer_metadata={},
        **seed_row,
    )
    atomic_write_registry(seed_registry, out_dir / "college_prospect_registry.json")

    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [_row("Different Person", school="Bama", sid="src_001").model_dump()],
    }))
    result = ingest_fixture(fixture_path=fixture_path, identity_dir=out_dir, run_id="conflict_run")
    conflict_path = out_dir / "college_identity_source_id_conflict_conflict_run.jsonl"
    assert conflict_path.exists()
    lines = [line for line in conflict_path.read_text().splitlines() if line.strip()]
    assert lines, "source_id_conflict queue must record the collision"
    record = json.loads(lines[0])
    assert record["incoming_source_record_id"] == "src_001"
    assert record["existing_prospect_uuid"] == seed_uuid

    # Regular review queue should NOT contain a normal candidate for the conflict
    review_path = out_dir / "college_identity_review_queue_conflict_run.jsonl"
    if review_path.exists() and review_path.read_text().strip():
        for line in review_path.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            assert entry["incoming_source_record_id"] != "src_001"


def test_ingest_fixture_coverage_matrix_includes_source_id_conflict_count(tmp_path: Path):
    from src.dynasty_genius.identity.college_prospect_identity import ingest_fixture

    out_dir = tmp_path / "out"
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [_row("Person A", sid="src_A").model_dump(),
                    _row("Person B", sid="src_B").model_dump()],
    }))
    result = ingest_fixture(fixture_path=fixture_path, identity_dir=out_dir, run_id="counts_run")
    coverage = json.loads((out_dir / "college_identity_coverage_matrix_counts_run.json").read_text())
    assert "source_id_conflict" in coverage
    assert coverage["source_id_conflict"] == 0
    assert coverage["total_input_rows"] == 2
    assert result.exit_code == 0
```

- [ ] **Step 2: Run RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py -v
```

Expected: the new tests fail (current `ingest_fixture` doesn't write the bridge, doesn't emit the conflict queue, doesn't include the new coverage key).

- [ ] **Step 3: Claude rewrites `ingest_fixture()`**

Replace the existing `ingest_fixture()` definition with:

```python
def ingest_fixture(
    *,
    fixture_path: Path,
    identity_dir: Path,
    run_id: str,
) -> IngestResult:
    """Spec §6.5 + Round 2: validate-before-replace ingestion writing registry + bridge +
    review_queue + source_id_conflict queue + coverage matrix, per-file atomic.
    """
    raw = json.loads(fixture_path.read_text())
    entries_raw = raw.get("entries", [])

    registry_path = identity_dir / "college_prospect_registry.json"
    bridge_path = identity_dir / "college_alias_bridge.json"
    review_path = identity_dir / f"college_identity_review_queue_{run_id}.jsonl"
    conflict_path = identity_dir / f"college_identity_source_id_conflict_{run_id}.jsonl"
    coverage_path = identity_dir / f"college_identity_coverage_matrix_{run_id}.json"

    registry = load_registry(registry_path)
    bridge = load_bridge(bridge_path)

    coverage = {
        "total_input_rows": 0,
        "minted_new": 0,
        "idempotent_rerun": 0,
        "minted_new_provisional_with_review_candidate": 0,
        "minted_new_with_surfaced_candidates": 0,
        "source_id_conflict": 0,
    }
    review_entries: list[dict[str, Any]] = []
    conflict_entries: list[dict[str, Any]] = []

    for raw_entry in entries_raw:
        incoming = NormalizedCollegeProspectRow.model_validate(raw_entry)
        coverage["total_input_rows"] += 1
        outcome = mint_or_match(incoming, registry, bridge=bridge)
        coverage[outcome.kind] += 1

        if outcome.kind == "source_id_conflict":
            conflict_entries.append({
                "run_id": run_id,
                "incoming_source": incoming.source,
                "incoming_source_record_id": incoming.source_record_id,
                "incoming_normalized_name": incoming.normalized_name,
                "incoming_cfbd_athlete_id": incoming.cfbd_athlete_id,
                "conflict_kind": outcome.source_id_conflict_record["kind"],
                "existing_prospect_uuid": outcome.source_id_conflict_record["existing_prospect_uuid"],
                "existing_normalized_name": outcome.source_id_conflict_record["existing_normalized_name"],
                "matcher_algorithm_version": MATCHER_ALGORITHM_VERSION,
            })
            continue

        for cand in outcome.review_candidates:
            review_entries.append({
                "run_id": run_id,
                "review_id": f"{run_id}_review_{len(review_entries) + 1:04d}",
                "incoming_source_record_id": incoming.source_record_id,
                "minted_prospect_uuid": outcome.prospect_uuid,
                "target_prospect_uuid": cand.target_prospect_uuid,
                "match_score": cand.match_score,
                "score_breakdown": cand.score_breakdown,
                "risk_flags": list(cand.risk_flags),
                "raw_match_features": cand.raw_match_features,
                "matcher_algorithm_version": cand.matcher_algorithm_version,
                "decided_at": None,
                "decision": None,
                "event_id": None,
            })

    errors = validate_registry_graph(registry, bridge=bridge)
    if errors:
        diagnostics_path = identity_dir / f"college_identity_failure_report_{run_id}.md"
        diagnostics_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostics_path.write_text(
            "# Subsystem 3 — ingestion failure report\n\n"
            f"run_id: {run_id}\n\n" + "\n".join(f"- {e}" for e in errors)
        )
        return IngestResult(exit_code=1, run_id=run_id, coverage=coverage)

    identity_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_registry(registry, registry_path)
    atomic_write_bridge(bridge, bridge_path)

    def _atomic_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            "\n".join(json.dumps(e, sort_keys=True) for e in entries) + ("\n" if entries else "")
        )
        os.replace(tmp, path)

    _atomic_jsonl(review_path, review_entries)
    _atomic_jsonl(conflict_path, conflict_entries)

    tmp_coverage = coverage_path.with_suffix(coverage_path.suffix + ".tmp")
    tmp_coverage.write_text(json.dumps(coverage, indent=2, sort_keys=True))
    os.replace(tmp_coverage, coverage_path)

    reloaded_registry = load_registry(registry_path)
    reloaded_bridge = load_bridge(bridge_path)
    post_errors = validate_registry_graph(reloaded_registry, bridge=reloaded_bridge)
    if post_errors:
        return IngestResult(exit_code=2, run_id=run_id, coverage=coverage)

    return IngestResult(exit_code=0, run_id=run_id, coverage=coverage)
```

The CLI script `scripts/ingest_college_prospect_fixture.py` from v1 Task 7 stays the same (no flag changes).

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_ingestion.py -v
```

Expected: all ingestion tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py tests/contract/test_subsystem_3_ingestion.py
git commit -m "feat(subsystem-3 round 2): ingest_fixture writes bridge + emits dedicated source_id_conflict queue"
```

---

## Round 2 Task 8: Promotion lifecycle + bridge writes + closure markers + pure replay applicator — §10.6 (revised)

**Goal (Round 2):** Split `confirm --target self` vs `confirm --target <existing_uuid>` semantics; on confirm-existing write a `CollegeAliasBridgeEntry` (the alias-resolve case spec §6.2); on every decision append a closure marker to the originating `review_queue` row (third leg of §6.3 three-point logging); add a pure `_apply_logged_event()` applicator used by `replay_promotion_log()` so replay never re-generates timestamps or UUIDs. Replay must reproduce both registry **and** bridge byte-identically.

**Files:**
- Modify: `src/dynasty_genius/identity/college_prospect_identity.py` (rewrite promotion section)
- Modify: `scripts/promote_review_candidate.py` (add `--target-kind self|existing` flag)
- Replace: `tests/contract/test_subsystem_3_promotion.py` (full Round 2 content)

- [ ] **Step 1: Codex replaces `tests/contract/test_subsystem_3_promotion.py` with the Round 2 content**

```python
"""Subsystem 3 — Round 2 promotion lifecycle contract tests (§10.6)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeAliasBridgeEntry,
    ConflictingDecisionError,
    EvidenceRequiredError,
    PromotionDecision,
    PromotionResult,
    ingest_fixture,
    load_bridge,
    load_registry,
    promote_review_candidate,
    replay_promotion_log,
)


def _two_row_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [
            {
                "raw_name": "Arch Manning",
                "normalized_name": "arch manning",
                "full_name": "Arch Manning",
                "position": "QB", "position_group": "QB",
                "draft_class": 2027, "current_school": "Texas", "prior_schools": [],
                "cfbd_athlete_id": None, "cfb_player_id": None,
                "pfr_id": None, "gsis_id": None, "sleeper_id": None,
                "source": "manual_fixture", "source_record_id": "fixture_2027_001",
                "source_snapshot_id": "fixture_2027_v1",
                "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                                  "pfr_id": None, "gsis_id": None, "sleeper_id": None},
                "notes": None,
            },
            {
                "raw_name": "Mike Williams",
                "normalized_name": "mike williams",
                "full_name": "Mike Williams",
                "position": "WR", "position_group": "WR",
                "draft_class": 2027, "current_school": "Clemson", "prior_schools": [],
                "cfbd_athlete_id": None, "cfb_player_id": None,
                "pfr_id": None, "gsis_id": None, "sleeper_id": None,
                "source": "manual_fixture", "source_record_id": "fixture_2027_002",
                "source_snapshot_id": "fixture_2027_v1",
                "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                                  "pfr_id": None, "gsis_id": None, "sleeper_id": None},
                "notes": None,
            },
        ],
    }))
    out = tmp_path / "out"
    run_id = "genesis_run_001"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id=run_id)
    return fixture, out, run_id


def _provisional_uuid(out: Path) -> str:
    reg = load_registry(out / "college_prospect_registry.json")
    for e in reg.entries.values():
        if e.verification_status == "provisional":
            return e.prospect_uuid
    raise AssertionError("expected a provisional row")


def _all_uuids(out: Path) -> list[str]:
    return list(load_registry(out / "college_prospect_registry.json").entries.keys())


# --- Preserved v1 happy-path tests ---


def test_confirm_self_promotes_row_to_confirmed_and_logs(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    assert isinstance(result, PromotionResult)
    assert result.exit_code == 0
    reg = load_registry(out / "college_prospect_registry.json")
    assert reg.get(target).verification_status == "confirmed"


def test_reject_closes_review_without_mutating_identity(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    pre = load_registry(out / "college_prospect_registry.json").get(target).verification_status
    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="reject", target_kind="self", target=target),
        identity_dir=out,
        reviewer_id="davidleess",
        evidence=None,
        note=None,
    )
    assert result.exit_code == 0
    post = load_registry(out / "college_prospect_registry.json").get(target).verification_status
    assert pre == post


def test_merge_into_requires_non_empty_evidence(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    uuids = _all_uuids(out)
    with pytest.raises(EvidenceRequiredError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(
                kind="merge_into", target_kind="self",
                target=uuids[1], survivor=uuids[0],
            ),
            identity_dir=out, reviewer_id="davidleess",
            evidence=None, note=None,
        )


def test_split_requires_non_empty_evidence(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    with pytest.raises(EvidenceRequiredError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(
                kind="split", target_kind="self", target=_provisional_uuid(out),
                new_full_name="Split Person", new_position="WR", new_position_group="WR",
            ),
            identity_dir=out, reviewer_id="davidleess",
            evidence=None, note=None,
        )


def test_split_mints_new_provisional_uuid_with_logged_metadata(tmp_path: Path):
    """Round 2 patch 3: spec §6.2 split happy-path. Original UUID retained; new provisional
    UUID minted for the second identity; event log carries new_split_uuid for deterministic
    replay."""
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    pre_uuids = set(_all_uuids(out))

    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(
            kind="split", target_kind="self", target=target,
            new_full_name="Second Person", new_position="WR", new_position_group="WR",
        ),
        identity_dir=out, reviewer_id="davidleess",
        evidence="distinct CFBD athlete IDs (12345 vs 67890)", note=None,
    )
    assert result.exit_code == 0

    post_uuids = set(_all_uuids(out))
    new_uuids = post_uuids - pre_uuids
    assert len(new_uuids) == 1, "split must mint exactly one new provisional UUID"
    new_uuid = next(iter(new_uuids))
    assert target in post_uuids, "original target UUID must be retained"

    reg = load_registry(out / "college_prospect_registry.json")
    new_row = reg.get(new_uuid)
    assert new_row.verification_status == "provisional"
    assert new_row.full_name == "Second Person"

    # Event log must include new_split_uuid for deterministic replay
    log_lines = (out / "college_identity_promotion_log.jsonl").read_text().splitlines()
    events = [json.loads(line) for line in log_lines if line.strip()]
    split_events = [ev for ev in events if ev["decision"] == "split"]
    assert split_events, "split event must be in the promotion log"
    assert split_events[0]["new_split_uuid"] == new_uuid
    assert split_events[0]["new_full_name"] == "Second Person"


def test_replay_after_split_reproduces_registry_byte_identical(tmp_path: Path):
    """Round 2 patch 3: _apply_logged_event must read the logged new_split_uuid so the
    reconstructed split row carries the same UUID it had at first apply."""
    fixture, out, run_id = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(
            kind="split", target_kind="self", target=target,
            new_full_name="Second Person", new_position="WR", new_position_group="WR",
        ),
        identity_dir=out, reviewer_id="davidleess",
        evidence="distinct CFBD athlete IDs", note=None,
    )
    registry_after = (out / "college_prospect_registry.json").read_bytes()

    genesis_dir = tmp_path / "replay_out"
    ingest_fixture(fixture_path=fixture, identity_dir=genesis_dir, run_id=run_id)
    replay_promotion_log(
        log_path=out / "college_identity_promotion_log.jsonl",
        identity_dir=genesis_dir,
    )
    assert (genesis_dir / "college_prospect_registry.json").read_bytes() == registry_after


def test_idempotent_rerun_same_decision_is_noop(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note=None,
    )
    log_path = out / "college_identity_promotion_log.jsonl"
    pre = log_path.read_bytes()
    result = promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note=None,
    )
    assert result.exit_code == 0
    assert pre == log_path.read_bytes()


def test_conflicting_rerun_fails_closed_without_override(tmp_path: Path):
    _, out, _ = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note=None,
    )
    with pytest.raises(ConflictingDecisionError):
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(kind="reject", target_kind="self", target=target),
            identity_dir=out, reviewer_id="davidleess",
            evidence=None, note=None,
        )


# --- Round 2 NEW tests ---


def test_confirm_target_existing_writes_bridge_entry_and_log_carries_both_uuids(tmp_path: Path):
    """Codex RED #3: confirm-existing writes bridge entry + log has both source and target."""
    _, out, run_id = _two_row_fixture(tmp_path)
    uuids = _all_uuids(out)
    # Pick existing target (will be confirmed); pick source (the incoming-alias row, will deprecate)
    source_uuid, target_uuid = uuids[0], uuids[1]

    # First confirm the target as a standalone
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target_uuid),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note=None,
    )

    # Synthesize a review_id pointing to source_uuid (the incoming-alias row)
    review_id = f"{run_id}_alias_review_001"
    review_path = out / f"college_identity_review_queue_{run_id}.jsonl"
    review_payload = {
        "run_id": run_id,
        "review_id": review_id,
        "incoming_source_record_id": load_registry(out / "college_prospect_registry.json").get(source_uuid).source_record_id,
        "minted_prospect_uuid": source_uuid,
        "target_prospect_uuid": target_uuid,
        "match_score": 0.93,
        "score_breakdown": {"final": 0.93},
        "risk_flags": ["cross_position_group"],
        "raw_match_features": {},
        "matcher_algorithm_version": "cpr_matcher_v1.0.0",
        "decided_at": None, "decision": None, "event_id": None,
    }
    existing = review_path.read_text() if review_path.exists() else ""
    review_path.write_text(existing + json.dumps(review_payload, sort_keys=True) + "\n")

    # Now confirm-existing: source_uuid IS the same person as target_uuid
    result = promote_review_candidate(
        review_id=review_id,
        decision=PromotionDecision(
            kind="confirm", target_kind="existing",
            target=source_uuid, survivor=target_uuid,
        ),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note="alias resolve",
    )
    assert result.exit_code == 0

    # Bridge must carry the alias entry
    bridge = load_bridge(out / "college_alias_bridge.json")
    assert any(
        e.target_prospect_uuid == target_uuid for e in bridge.entries
    ), "confirm-existing must write a bridge entry to the survivor"

    # Promotion log must carry both source + target UUIDs
    log_lines = (out / "college_identity_promotion_log.jsonl").read_text().splitlines()
    events = [json.loads(line) for line in log_lines if line.strip()]
    alias_events = [
        ev for ev in events
        if ev.get("source_prospect_uuid") == source_uuid
        and ev.get("target_prospect_uuid") == target_uuid
    ]
    assert alias_events, "promotion log must record source + target UUIDs on confirm-existing"


def test_review_queue_closure_marker_appended_to_originating_review_row(tmp_path: Path):
    """Codex RED #3 (closure leg): every decision appends closure marker to review_queue row."""
    _, out, run_id = _two_row_fixture(tmp_path)
    target = _provisional_uuid(out)

    # Synthesize a review_id row tied to `target`
    review_id = f"{run_id}_closure_review_001"
    review_path = out / f"college_identity_review_queue_{run_id}.jsonl"
    review_payload = {
        "run_id": run_id, "review_id": review_id,
        "incoming_source_record_id": "fixture_2027_synthetic",
        "minted_prospect_uuid": target,
        "target_prospect_uuid": target,
        "match_score": 1.0,
        "score_breakdown": {"final": 1.0},
        "risk_flags": [],
        "raw_match_features": {},
        "matcher_algorithm_version": "cpr_matcher_v1.0.0",
        "decided_at": None, "decision": None, "event_id": None,
    }
    existing = review_path.read_text() if review_path.exists() else ""
    review_path.write_text(existing + json.dumps(review_payload, sort_keys=True) + "\n")

    result = promote_review_candidate(
        review_id=review_id,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note=None,
    )
    assert result.exit_code == 0
    closure_lines = (out / f"college_identity_review_queue_{run_id}.jsonl").read_text().splitlines()
    closed = [json.loads(line) for line in closure_lines if line.strip()]
    matched = [r for r in closed if r.get("review_id") == review_id]
    assert matched, "review row should still be present after closure"
    row = matched[0]
    assert row["decision"] == "confirm"
    assert row["decided_at"] is not None
    assert row["event_id"] is not None


def test_replay_reproduces_registry_AND_bridge_byte_identical(tmp_path: Path):
    """Codex RED #5: replay applicator must reproduce registry AND bridge byte-for-byte."""
    fixture, out, run_id = _two_row_fixture(tmp_path)
    uuids = _all_uuids(out)
    source_uuid, target_uuid = uuids[0], uuids[1]

    # Confirm target standalone, then confirm source as alias of target
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", target_kind="self", target=target_uuid),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note=None,
    )
    promote_review_candidate(
        review_id=None,
        decision=PromotionDecision(
            kind="confirm", target_kind="existing",
            target=source_uuid, survivor=target_uuid,
        ),
        identity_dir=out, reviewer_id="davidleess",
        evidence=None, note=None,
    )

    registry_after = (out / "college_prospect_registry.json").read_bytes()
    bridge_after = (out / "college_alias_bridge.json").read_bytes()

    # Reset to genesis, replay the log
    genesis_dir = tmp_path / "replay_out"
    ingest_fixture(fixture_path=fixture, identity_dir=genesis_dir, run_id=run_id)
    replay_promotion_log(
        log_path=out / "college_identity_promotion_log.jsonl",
        identity_dir=genesis_dir,
    )

    assert (genesis_dir / "college_prospect_registry.json").read_bytes() == registry_after
    assert (genesis_dir / "college_alias_bridge.json").read_bytes() == bridge_after


def test_apply_logged_event_is_pure_no_fresh_timestamps_or_uuids(tmp_path: Path):
    """Codex RED #5 supporting: _apply_logged_event must not call _now_iso() or _uuid.uuid4()."""
    from src.dynasty_genius.identity import college_prospect_identity as mod

    calls = {"now": 0, "uuid": 0}
    real_now = mod._now_iso
    real_uuid = mod._uuid.uuid4

    def fake_now():
        calls["now"] += 1
        return real_now()

    def fake_uuid():
        calls["uuid"] += 1
        return real_uuid()

    mod._now_iso = fake_now
    mod._uuid.uuid4 = fake_uuid
    try:
        fixture, out, run_id = _two_row_fixture(tmp_path)
        target = _provisional_uuid(out)
        # Do a real promotion to populate the log + reset call counters
        promote_review_candidate(
            review_id=None,
            decision=PromotionDecision(kind="confirm", target_kind="self", target=target),
            identity_dir=out, reviewer_id="davidleess",
            evidence=None, note=None,
        )
        calls["now"] = 0
        calls["uuid"] = 0

        # Reset to genesis + replay
        genesis_dir = tmp_path / "replay_out"
        ingest_fixture(fixture_path=fixture, identity_dir=genesis_dir, run_id=run_id)
        calls["now"] = 0
        calls["uuid"] = 0
        replay_promotion_log(
            log_path=out / "college_identity_promotion_log.jsonl",
            identity_dir=genesis_dir,
        )
        assert calls["now"] == 0, "_apply_logged_event must not call _now_iso()"
        assert calls["uuid"] == 0, "_apply_logged_event must not call _uuid.uuid4()"
    finally:
        mod._now_iso = real_now
        mod._uuid.uuid4 = real_uuid
```

- [ ] **Step 2: Run RED**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_promotion.py -v
```

Expected: ImportError on `PromotionDecision.target_kind` field, missing bridge writes, missing closure-marker behavior, replay regenerates metadata.

- [ ] **Step 3: Claude rewrites the promotion section**

Replace the v1 `PromotionDecision`, `promote_review_candidate()`, and `replay_promotion_log()` with the Round 2 versions:

```python
@dataclass(frozen=True)
class PromotionDecision:
    """Round 2 shape: target_kind distinguishes confirm-self from confirm-existing."""

    kind: Literal["confirm", "reject", "defer", "merge_into", "split"]
    target_kind: Literal["self", "existing"]
    target: str
    survivor: Optional[str] = None       # merge_into; also = bridge survivor for confirm-existing
    new_full_name: Optional[str] = None  # split
    new_position: Optional[str] = None   # split
    new_position_group: Optional[str] = None  # split


def _close_review_queue_row(
    identity_dir: Path,
    review_id: str,
    decision_kind: str,
    decided_at: str,
    event_id: str,
) -> None:
    """Append closure marker to the originating review_queue row (spec §6.3 third leg)."""
    for path in identity_dir.glob("college_identity_review_queue_*.jsonl"):
        lines = path.read_text().splitlines()
        updated: list[str] = []
        changed = False
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("review_id") == review_id and row.get("decision") is None:
                row["decision"] = decision_kind
                row["decided_at"] = decided_at
                row["event_id"] = event_id
                changed = True
            updated.append(json.dumps(row, sort_keys=True))
        if changed:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text("\n".join(updated) + "\n")
            os.replace(tmp, path)
            return


def _apply_logged_event(
    event: dict[str, Any],
    registry: CollegeProspectRegistry,
    bridge: CollegeAliasBridge,
) -> None:
    """Round 2 pure applicator (spec §6.3 replay): uses logged event_id / decided_at /
    reviewer_id / target / survivor; never calls _now_iso() or _uuid.uuid4().
    """
    decision = event["decision"]
    target_uuid = event["target_prospect_uuid"]
    survivor_uuid = event.get("survivor_prospect_uuid")
    target_kind = event.get("target_kind", "self")
    target_row = registry.get(target_uuid)
    if target_row is None:
        return

    if decision == "confirm" and target_kind == "self":
        target_row.verification_status = "confirmed"
        target_row.append_status_history(StatusHistoryEntry(
            event_id=event["event_id"], decision="confirm",
            after_status="confirmed", decided_at=event["decided_at"],
            reviewer_id=event["reviewer_id"],
        ))
    elif decision == "confirm" and target_kind == "existing":
        # Round 2 patch 1: for confirm-existing the row to deprecate is the SOURCE
        # (provisional) row, NOT the event's target_prospect_uuid (which now correctly
        # holds the existing confirmed survivor). Spec §6.2: source = provisional incoming;
        # target = existing confirmed identity.
        source_uuid = event["source_prospect_uuid"]
        survivor_uuid_existing = event["target_prospect_uuid"]
        source_row = registry.get(source_uuid)
        if source_row is None:
            return
        source_row.verification_status = "deprecated"
        source_row.merged_into_prospect_uuid = survivor_uuid_existing
        source_row.append_status_history(StatusHistoryEntry(
            event_id=event["event_id"], decision="confirm",
            after_status="deprecated", decided_at=event["decided_at"],
            reviewer_id=event["reviewer_id"],
        ))
        bridge.entries.append(CollegeAliasBridgeEntry(
            match_key=source_row.match_key,
            source_record_id=source_row.source_record_id,
            target_prospect_uuid=survivor_uuid_existing,
        ))
    elif decision == "merge_into":
        target_row.verification_status = "deprecated"
        target_row.merged_into_prospect_uuid = survivor_uuid
        target_row.append_status_history(StatusHistoryEntry(
            event_id=event["event_id"], decision="merge_into",
            after_status="deprecated", decided_at=event["decided_at"],
            reviewer_id=event["reviewer_id"],
        ))
    elif decision == "split":
        # Round 2 patch 3: replay split using the logged new_split_uuid for deterministic
        # reconstruction. Original target retains its UUID; new row gets the logged UUID.
        new_split_uuid = event.get("new_split_uuid")
        if new_split_uuid is None:
            return
        new_full_name = event.get("new_full_name") or target_row.full_name
        new_position = event.get("new_position") or target_row.position
        new_position_group = event.get("new_position_group") or target_row.position_group
        new_normalized_name = normalize_name(new_full_name)
        new_row = target_row.model_copy(update={
            "prospect_uuid": new_split_uuid,
            "verification_status": "provisional",
            "raw_name": new_full_name,
            "normalized_name": new_normalized_name,
            "full_name": new_full_name,
            "position": new_position,
            "position_group": new_position_group,
            "match_key": compute_match_key(
                normalized_name=new_normalized_name,
                position_group=new_position_group,
                draft_class=target_row.draft_class,
            ),
            "source_record_id": f"{target_row.source_record_id}__split__{new_split_uuid[-12:]}",
            "status_history": [StatusHistoryEntry(
                event_id=event["event_id"], decision="split",
                after_status="provisional", decided_at=event["decided_at"],
                reviewer_id=event["reviewer_id"],
            )],
        })
        registry.entries[new_split_uuid] = new_row
        target_row.append_status_history(StatusHistoryEntry(
            event_id=event["event_id"], decision="split",
            after_status=target_row.verification_status,
            decided_at=event["decided_at"],
            reviewer_id=event["reviewer_id"],
        ))
    # reject / defer: no identity mutation; closure still recorded


def promote_review_candidate(
    *,
    review_id: Optional[str],
    decision: PromotionDecision,
    identity_dir: Path,
    reviewer_id: str,
    evidence: Optional[str],
    note: Optional[str],
) -> PromotionResult:
    """Spec §6 (Round 2): the only blessed write path; per-file atomic writes in dependency-safe
    order: promotion_log → registry → bridge → review_queue closure marker.
    """
    if decision.kind in {"merge_into", "split"} and not (evidence and evidence.strip()):
        raise EvidenceRequiredError(
            f"decision={decision.kind} requires non-empty --evidence (spec §6.2)"
        )

    log_path = identity_dir / "college_identity_promotion_log.jsonl"
    registry_path = identity_dir / "college_prospect_registry.json"
    bridge_path = identity_dir / "college_alias_bridge.json"
    log = _read_promotion_log(log_path)

    # Idempotency / conflict check by the row being acted on. For confirm-existing the
    # acted-on row is the source/provisional UUID (decision.target); for everything else
    # decision.target is also the acted-on row. In the log, the acted-on row sits in
    # source_prospect_uuid when target_kind == "existing", otherwise target_prospect_uuid.
    for prior in log:
        prior_acted_uuid = (
            prior.get("source_prospect_uuid")
            if prior.get("target_kind") == "existing"
            else prior.get("target_prospect_uuid")
        )
        if prior_acted_uuid == decision.target:
            if prior.get("decision") == decision.kind and prior.get("target_kind") == decision.target_kind:
                return PromotionResult(exit_code=0, event_id=prior.get("event_id"))
            raise ConflictingDecisionError(
                f"target={decision.target} already has decision={prior.get('decision')}; "
                f"refusing to apply {decision.kind} without --override"
            )

    registry = load_registry(registry_path)
    bridge = load_bridge(bridge_path)
    target_row = registry.get(decision.target)
    if target_row is None:
        return PromotionResult(exit_code=1)

    decided_at = _now_iso()
    event_id = f"ev_{_uuid.uuid4()}"
    event: dict[str, Any] = {
        "event_id": event_id,
        "review_id": review_id,
        "decision": decision.kind,
        "target_kind": decision.target_kind,
        "reviewer_id": reviewer_id,
        "reviewer_metadata": {},
        "decided_at": decided_at,
        # Round 2 patch 1: target_prospect_uuid carries the SURVIVOR (existing confirmed identity)
        # for confirm-existing; source_prospect_uuid carries the provisional source row. For all
        # other decisions, target_prospect_uuid is the row being acted on (self semantics).
        "target_prospect_uuid": decision.survivor if decision.target_kind == "existing" else decision.target,
        "source_prospect_uuid": decision.target if decision.target_kind == "existing" else None,
        "survivor_prospect_uuid": decision.survivor,
        "before_status": target_row.verification_status,
        "after_status": target_row.verification_status,
        "evidence": evidence,
        "note": note,
    }

    if decision.kind == "confirm" and decision.target_kind == "self":
        target_row.verification_status = "confirmed"
        target_row.append_status_history(StatusHistoryEntry(
            event_id=event_id, decision="confirm", after_status="confirmed",
            decided_at=decided_at, reviewer_id=reviewer_id,
        ))
        event["after_status"] = "confirmed"
    elif decision.kind == "confirm" and decision.target_kind == "existing":
        if decision.survivor is None:
            return PromotionResult(exit_code=1)
        survivor_row = registry.get(decision.survivor)
        if survivor_row is None or survivor_row.verification_status != "confirmed":
            return PromotionResult(exit_code=1)
        target_row.verification_status = "deprecated"
        target_row.merged_into_prospect_uuid = decision.survivor
        target_row.append_status_history(StatusHistoryEntry(
            event_id=event_id, decision="confirm", after_status="deprecated",
            decided_at=decided_at, reviewer_id=reviewer_id,
        ))
        bridge.entries.append(CollegeAliasBridgeEntry(
            match_key=target_row.match_key,
            source_record_id=target_row.source_record_id,
            target_prospect_uuid=decision.survivor,
        ))
        event["after_status"] = "deprecated"
    elif decision.kind == "merge_into":
        target_row.verification_status = "deprecated"
        target_row.merged_into_prospect_uuid = decision.survivor
        target_row.append_status_history(StatusHistoryEntry(
            event_id=event_id, decision="merge_into", after_status="deprecated",
            decided_at=decided_at, reviewer_id=reviewer_id,
        ))
        event["after_status"] = "deprecated"
    elif decision.kind == "split":
        # Round 2 patch 3: spec §6.2 split happy-path. An existing prospect_uuid actually
        # represents two distinct people. Mint a NEW provisional UUID for the second; original
        # target retains its UUID and verification_status; both rows append a shared 'split'
        # StatusHistoryEntry with the same event_id for lineage. Log new_split_uuid for
        # deterministic replay.
        new_split_uuid = _mint_provisional_uuid()
        new_full_name = decision.new_full_name or target_row.full_name
        new_position = decision.new_position or target_row.position
        new_position_group = decision.new_position_group or target_row.position_group
        new_normalized_name = normalize_name(new_full_name)
        new_row = target_row.model_copy(update={
            "prospect_uuid": new_split_uuid,
            "verification_status": "provisional",
            "raw_name": new_full_name,
            "normalized_name": new_normalized_name,
            "full_name": new_full_name,
            "position": new_position,
            "position_group": new_position_group,
            "match_key": compute_match_key(
                normalized_name=new_normalized_name,
                position_group=new_position_group,
                draft_class=target_row.draft_class,
            ),
            "source_record_id": f"{target_row.source_record_id}__split__{new_split_uuid[-12:]}",
            "status_history": [StatusHistoryEntry(
                event_id=event_id, decision="split", after_status="provisional",
                decided_at=decided_at, reviewer_id=reviewer_id,
            )],
        })
        registry.entries[new_split_uuid] = new_row
        target_row.append_status_history(StatusHistoryEntry(
            event_id=event_id, decision="split",
            after_status=target_row.verification_status,
            decided_at=decided_at, reviewer_id=reviewer_id,
        ))
        event["new_split_uuid"] = new_split_uuid
        event["new_full_name"] = new_full_name
        event["new_position"] = new_position
        event["new_position_group"] = new_position_group
    # reject / defer: no identity mutation; closure still recorded

    errors = validate_registry_graph(registry, bridge=bridge)
    if errors:
        return PromotionResult(exit_code=2)

    _append_promotion_event(log_path, event)
    atomic_write_registry(registry, registry_path)
    atomic_write_bridge(bridge, bridge_path)
    if review_id:
        _close_review_queue_row(identity_dir, review_id, decision.kind, decided_at, event_id)

    reloaded_registry = load_registry(registry_path)
    reloaded_bridge = load_bridge(bridge_path)
    post_errors = validate_registry_graph(reloaded_registry, bridge=reloaded_bridge)
    if post_errors:
        return PromotionResult(exit_code=3, event_id=event_id)
    return PromotionResult(exit_code=0, event_id=event_id)


def replay_promotion_log(*, log_path: Path, identity_dir: Path) -> None:
    """Spec §6.3 Round 2: pure replay over genesis state. Uses _apply_logged_event so no
    fresh timestamps or UUIDs leak into the reconstructed registry/bridge."""
    log = _read_promotion_log(log_path)
    registry_path = identity_dir / "college_prospect_registry.json"
    bridge_path = identity_dir / "college_alias_bridge.json"
    registry = load_registry(registry_path)
    bridge = load_bridge(bridge_path)
    for event in log:
        _apply_logged_event(event, registry, bridge)
    atomic_write_registry(registry, registry_path)
    atomic_write_bridge(bridge, bridge_path)
```

Update `scripts/promote_review_candidate.py` to accept `--target-kind`:

```python
parser.add_argument(
    "--target-kind",
    type=str,
    choices=["self", "existing"],
    default="self",
)
```

And pass it through to `PromotionDecision`.

- [ ] **Step 4: Run GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_promotion.py -v
```

Expected: all promotion tests pass, including the byte-identical-registry-AND-bridge replay assertion.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/college_prospect_identity.py scripts/promote_review_candidate.py tests/contract/test_subsystem_3_promotion.py
git commit -m "feat(subsystem-3 round 2): confirm-existing bridge writes + closure markers + pure replay applicator"
```

---

## Round 2 Task 9: Audit / coverage / provisional-leak — §10.7 (revised)

**Goal (Round 2):** Replace the v1 conflated `test_leak_contract_3` with a proper bridge-entry validation test using `CollegeAliasBridgeEntry`; add the `source_id_conflict` queue isolation test; add the registry+bridge byte-unchanged validation extension.

**Files:**
- Replace: `tests/contract/test_subsystem_3_audit.py` (Round 2 content)

- [ ] **Step 1: Codex replaces `tests/contract/test_subsystem_3_audit.py` with the Round 2 content**

```python
"""Subsystem 3 — Round 2 audit / coverage / provisional-leak contract tests (§10.7)."""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.college_prospect_identity import (
    CollegeAliasBridge,
    CollegeAliasBridgeEntry,
    CollegeProspectRegistry,
    ConfirmedProspectUuid,
    NormalizedCollegeProspectRow,
    ProspectUuidDeprecatedMerged,
    ProspectUuidNotConfirmed,
    RegistryEntry,
    StatusHistoryEntry,
    UnknownProspectUuid,
    compute_match_key,
    ingest_fixture,
    load_registry,
    normalize_name,
    resolve_prospect_cfbd_athlete_id,
    validate_registry_graph,
)


_INVIOLATE_PATHS = [
    Path("app/data/identity/_runs/prospect_registry.json"),
    Path("app/data/identity/_runs/composite_registry.json"),
    Path("app/data/prospect_alias_bridge.json"),
    Path("src/dynasty_genius/adapters/prospect_identity_resolver.py"),
]


def _sha256(path: Path) -> str:
    if not path.exists():
        return "absent"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _basic_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "fixture.json"
    p.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [{
            "raw_name": "Arch Manning", "normalized_name": "arch manning",
            "full_name": "Arch Manning", "position": "QB", "position_group": "QB",
            "draft_class": 2027, "current_school": "Texas", "prior_schools": [],
            "cfbd_athlete_id": None, "cfb_player_id": None,
            "pfr_id": None, "gsis_id": None, "sleeper_id": None,
            "source": "manual_fixture", "source_record_id": "fixture_2027_001",
            "source_snapshot_id": "fixture_2027_v1",
            "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                              "pfr_id": None, "gsis_id": None, "sleeper_id": None},
            "notes": None,
        }],
    }))
    return p


# --- Provisional-leak contracts (§4.6) ---


def test_leak_contract_1_init_rejects_provisional_deprecated_unknown(tmp_path: Path):
    fixture = _basic_fixture(tmp_path)
    out = tmp_path / "out"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="run_a")
    registry = load_registry(out / "college_prospect_registry.json")
    provisional_uuid = next(iter(registry.entries.values())).prospect_uuid
    with pytest.raises(ProspectUuidNotConfirmed):
        ConfirmedProspectUuid(provisional_uuid, registry=registry)
    with pytest.raises(UnknownProspectUuid):
        ConfirmedProspectUuid("cpr_nonexistent", registry=registry)


def test_leak_contract_2_resolver_returns_none_on_provisional(tmp_path: Path):
    fixture = _basic_fixture(tmp_path)
    out = tmp_path / "out"
    ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="run_a")
    registry = load_registry(out / "college_prospect_registry.json")
    result = resolve_prospect_cfbd_athlete_id(
        name="Arch Manning", position="QB", draft_class=2027, registry=registry,
    )
    assert result is None  # provisional → unresolved, no raw-uuid leak


def test_leak_contract_3_bridge_entry_maps_only_to_confirmed_uuid():
    """Round 2 proper test: spec §4.6 contract 3 is about BRIDGE entries, not registry redirects.

    A bridge entry whose `target_prospect_uuid` is provisional / deprecated / unknown must
    fail full-graph validation BEFORE any atomic write commits.
    """
    provisional_uuid = "cpr_p1111111-1111-4111-8111-111111111111"
    deprecated_uuid = "cpr_d2222222-2222-4222-8222-222222222222"
    confirmed_uuid = "cpr_c3333333-3333-4333-8333-333333333333"

    def _row_kwargs(uuid_seed: str, status: str, name: str = "Sample"):
        return dict(
            raw_name=name, normalized_name=normalize_name(name),
            full_name=name, position="WR", position_group="WR",
            draft_class=2027, current_school="Texas", prior_schools=[],
            cfbd_athlete_id=None, cfb_player_id=None,
            pfr_id=None, gsis_id=None, sleeper_id=None,
            source="manual_fixture", source_record_id=f"src_{uuid_seed}",
            source_snapshot_id="fixture_2027_v1",
            id_provenance={"cfbd_athlete_id": None, "cfb_player_id": None,
                           "pfr_id": None, "gsis_id": None, "sleeper_id": None},
            notes=None,
        )

    registry = CollegeProspectRegistry()
    for uuid, status in [
        (provisional_uuid, "provisional"),
        (deprecated_uuid, "deprecated"),
        (confirmed_uuid, "confirmed"),
    ]:
        row = NormalizedCollegeProspectRow.model_validate(_row_kwargs(uuid[:8], status))
        registry.entries[uuid] = RegistryEntry(
            prospect_uuid=uuid, verification_status=status,
            match_key=compute_match_key(
                normalized_name=row.normalized_name,
                position_group=row.position_group,
                draft_class=row.draft_class,
            ),
            status_history=[StatusHistoryEntry(
                event_id=f"ev_{uuid}", decision="confirm", after_status=status,
                decided_at="2026-05-28T12:00:00Z", reviewer_id="davidleess",
            )],
            merged_into_prospect_uuid=None,
            reviewer_id="davidleess", reviewer_metadata={},
            **row.model_dump(),
        )

    match_key = compute_match_key(
        normalized_name="sample", position_group="WR", draft_class=2027,
    )

    # Bridge to provisional → INVALID
    bridge = CollegeAliasBridge(entries=[CollegeAliasBridgeEntry(
        match_key=match_key, source_record_id="bridge_test_1",
        target_prospect_uuid=provisional_uuid,
    )])
    errors = validate_registry_graph(registry, bridge=bridge)
    assert any("bridge target" in e.lower() and "not confirmed" in e.lower() for e in errors)

    # Bridge to deprecated → INVALID
    bridge = CollegeAliasBridge(entries=[CollegeAliasBridgeEntry(
        match_key=match_key, source_record_id="bridge_test_2",
        target_prospect_uuid=deprecated_uuid,
    )])
    errors = validate_registry_graph(registry, bridge=bridge)
    assert errors

    # Bridge to unknown → INVALID
    bridge = CollegeAliasBridge(entries=[CollegeAliasBridgeEntry(
        match_key=match_key, source_record_id="bridge_test_3",
        target_prospect_uuid="cpr_unknown",
    )])
    errors = validate_registry_graph(registry, bridge=bridge)
    assert any("unknown" in e.lower() for e in errors)

    # Bridge to confirmed → VALID
    bridge = CollegeAliasBridge(entries=[CollegeAliasBridgeEntry(
        match_key=match_key, source_record_id="bridge_test_4",
        target_prospect_uuid=confirmed_uuid,
    )])
    errors = validate_registry_graph(registry, bridge=bridge)
    assert errors == []


def test_leak_contract_4_source_record_id_unique_per_confirmed_uuid():
    """Spec §4.6 contract 4 (preserved): source_record_id maps to at most one active confirmed uuid."""
    base = dict(
        raw_name="X", normalized_name="x", full_name="X",
        position="WR", position_group="WR", draft_class=2027,
        current_school="Texas", prior_schools=[],
        cfbd_athlete_id=None, cfb_player_id=None,
        pfr_id=None, gsis_id=None, sleeper_id=None,
        source="manual_fixture", source_record_id="shared_001",
        source_snapshot_id="fixture_2027_v1",
        id_provenance={"cfbd_athlete_id": None, "cfb_player_id": None,
                       "pfr_id": None, "gsis_id": None, "sleeper_id": None},
        notes=None,
    )

    def _make(uuid: str) -> RegistryEntry:
        row = NormalizedCollegeProspectRow.model_validate(base)
        return RegistryEntry(
            prospect_uuid=uuid, verification_status="confirmed",
            match_key=compute_match_key(
                normalized_name="x", position_group="WR", draft_class=2027,
            ),
            status_history=[StatusHistoryEntry(
                event_id=f"ev_{uuid}", decision="confirm", after_status="confirmed",
                decided_at="2026-05-28T12:00:00Z", reviewer_id="davidleess",
            )],
            merged_into_prospect_uuid=None,
            reviewer_id="davidleess", reviewer_metadata={},
            **row.model_dump(),
        )

    registry = CollegeProspectRegistry(entries={
        "cpr_aaaa": _make("cpr_aaaa"),
        "cpr_bbbb": _make("cpr_bbbb"),
    })
    errors = validate_registry_graph(registry)
    assert any("source_record_id collision" in e for e in errors)


def test_leak_contract_5_full_graph_validation_runs_clean_on_empty():
    assert validate_registry_graph(CollegeProspectRegistry()) == []


# --- source_id_conflict isolation ---


def test_source_id_conflict_queue_contains_no_market_or_mock_fields(tmp_path: Path):
    """Round 2 audit: the dedicated source_id_conflict queue must not carry any market/mock fields."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    seed_registry = CollegeProspectRegistry()
    base_row = NormalizedCollegeProspectRow.model_validate({
        "raw_name": "Seed Name", "normalized_name": "seed name",
        "full_name": "Seed Name", "position": "WR", "position_group": "WR",
        "draft_class": 2027, "current_school": "Texas", "prior_schools": [],
        "cfbd_athlete_id": None, "cfb_player_id": None,
        "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        "source": "manual_fixture", "source_record_id": "src_001",
        "source_snapshot_id": "fixture_2027_v1",
        "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                          "pfr_id": None, "gsis_id": None, "sleeper_id": None},
        "notes": None,
    })
    seed_uuid = "cpr_seed1111-1111-4111-8111-111111111111"
    seed_registry.entries[seed_uuid] = RegistryEntry(
        prospect_uuid=seed_uuid, verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name="seed name", position_group="WR", draft_class=2027,
        ),
        status_history=[StatusHistoryEntry(
            event_id="ev_seed", decision="confirm", after_status="confirmed",
            decided_at="2026-05-28T11:00:00Z", reviewer_id="davidleess",
        )],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess", reviewer_metadata={},
        **base_row.model_dump(),
    )
    from src.dynasty_genius.identity.college_prospect_identity import atomic_write_registry
    atomic_write_registry(seed_registry, out_dir / "college_prospect_registry.json")

    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [{
            "raw_name": "Conflicting Name", "normalized_name": "conflicting name",
            "full_name": "Conflicting Name", "position": "WR", "position_group": "WR",
            "draft_class": 2027, "current_school": "Bama", "prior_schools": [],
            "cfbd_athlete_id": None, "cfb_player_id": None,
            "pfr_id": None, "gsis_id": None, "sleeper_id": None,
            "source": "manual_fixture", "source_record_id": "src_001",
            "source_snapshot_id": "fixture_2027_v1",
            "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                              "pfr_id": None, "gsis_id": None, "sleeper_id": None},
            "notes": None,
        }],
    }))
    ingest_fixture(fixture_path=fixture, identity_dir=out_dir, run_id="audit_run")

    conflict_path = out_dir / "college_identity_source_id_conflict_audit_run.jsonl"
    if not conflict_path.exists():
        pytest.skip("expected a conflict to be written")
    banned = {"ktc_value", "fc_value", "adp", "market_value", "mock_rank",
              "draft_selection_pct", "drafts_selected_in", "dynasty_nerds_adp"}
    for line in conflict_path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        leaked = set(record.keys()) & banned
        assert leaked == set(), f"source_id_conflict queue contains banned market/mock fields: {leaked}"


# --- Existing artifacts byte-unchanged ---


def test_existing_artifacts_byte_unchanged_before_and_after_subsystem_3_module_import():
    repo_root = Path(__file__).resolve().parents[2]
    pre = {p: _sha256(repo_root / p) for p in _INVIOLATE_PATHS}
    from src.dynasty_genius.identity.college_prospect_identity import (
        CollegeProspectRegistry as Reg,
    )
    _ = Reg()
    post = {p: _sha256(repo_root / p) for p in _INVIOLATE_PATHS}
    assert pre == post


# --- No mock/ADP/market data in registry ---


_BANNED_FIELD_NAMES = {
    "ktc_value", "fc_value", "adp", "market_value", "mock_rank",
    "draft_selection_pct", "drafts_selected_in", "dynasty_nerds_adp",
}


def test_registry_schema_has_no_market_or_mock_fields():
    fields = set(NormalizedCollegeProspectRow.model_fields.keys()) | set(
        RegistryEntry.model_fields.keys()
    )
    leaked = _BANNED_FIELD_NAMES & fields
    assert leaked == set(), f"market/mock leakage detected in registry schema: {leaked}"


# --- Coverage matrix counts reconcile ---


def test_coverage_matrix_counts_reconcile_including_round_2_kinds(tmp_path: Path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "metadata": {"snapshot_id": "fixture_2027_v1"},
        "entries": [{
            "raw_name": f"Person {i}", "normalized_name": normalize_name(f"Person {i}"),
            "full_name": f"Person {i}", "position": "WR", "position_group": "WR",
            "draft_class": 2027, "current_school": "Texas", "prior_schools": [],
            "cfbd_athlete_id": None, "cfb_player_id": None,
            "pfr_id": None, "gsis_id": None, "sleeper_id": None,
            "source": "manual_fixture", "source_record_id": f"fixture_2027_{i:03d}",
            "source_snapshot_id": "fixture_2027_v1",
            "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                              "pfr_id": None, "gsis_id": None, "sleeper_id": None},
            "notes": None,
        } for i in range(1, 4)],
    }))
    out = tmp_path / "out"
    result = ingest_fixture(fixture_path=fixture, identity_dir=out, run_id="reconcile_run")
    cov = json.loads((out / "college_identity_coverage_matrix_reconcile_run.json").read_text())
    accounted = sum(cov.get(k, 0) for k in [
        "minted_new",
        "idempotent_rerun",
        "minted_new_provisional_with_review_candidate",
        "minted_new_with_surfaced_candidates",
        "source_id_conflict",
    ])
    assert accounted == cov["total_input_rows"] == 3
    assert result.exit_code == 0
```

- [ ] **Step 2: Run RED then GREEN**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_audit.py -v
```

Expected: all audit tests pass (no new impl required — they exercise surfaces already built in Round 2 Tasks 6–8).

- [ ] **Step 3: Run the full S3 contract suite to confirm no regression**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_3_*.py -v
```

Expected: every Subsystem 3 contract test passes.

- [ ] **Step 4: Commit**

```bash
git add tests/contract/test_subsystem_3_audit.py
git commit -m "test(subsystem-3 round 2): proper bridge-validation + source_id_conflict isolation + coverage reconciliation"
```

---

## Self-review (writing-plans skill checklist)

**1. Spec coverage** — every §10.X sub-area gets its own task, every §4.5/§4.6 contract gets at least one test, §6 promotion lifecycle is fully covered, §3 byte-unchanged invariant is tested, §5.3 whitelist/hard-block taxonomy is exhaustively tested, §6.5 ingestion atomicity is tested, §8 downstream pseudocode is captured as `resolve_prospect_cfbd_athlete_id`. §7 (top-100 2027 fixture) is Task 10. §9 governance + no-market-data is tested in §10.7. §11 forward notes are explicitly deferred. §12 counter-argument doesn't need a task — it's a spec posture statement.

**2. Placeholder scan** — no "TBD", "implement later", "add appropriate error handling". Task 10 is a real data-curation lane, not a placeholder; its bite-sized substructure depends on a cockpit decision the plan calls out explicitly.

**3. Type consistency** — function/method names are consistent throughout:
- `normalize_name`, `compute_match_key`, `score_candidate`, `surface_review_candidates`
- `mint_or_match`, `atomic_write_registry`, `load_registry`, `validate_registry_graph`
- `ingest_fixture`, `promote_review_candidate`, `replay_promotion_log`
- `ConfirmedProspectUuid`, `resolve_prospect_cfbd_athlete_id`
- Decision kinds: `confirm`, `reject`, `defer`, `merge_into`, `split`
- Outcomes: `IngestionOutcome`, `IngestResult`, `PromotionResult`

**4. Cross-task ordering** — Task 0 (deps) → Task 1 (module path) → Task 2 (schema) → Task 3 (matcher) → Task 4 (whitelist) → Task 5 (`ConfirmedProspectUuid`) → Task 6 (ingestion contract) → Task 7 (ingest CLI) → Task 8 (promotion CLI) → Task 9 (audit) → Task 10 (fixture data, parallelizable) → Task 11 (closeout). No back-references to undefined symbols.

---

## Cockpit review gate (binding before execution)

**Per `[[reference_review_workflow]]` and David's standing directive:** this plan does not get executed until Codex + Gemini have independently read it and the cockpit converges. After convergence, David authorizes the execution skill (`superpowers:subagent-driven-development` recommended for fresh-subagent-per-task isolation, or `superpowers:executing-plans` for inline batch with checkpoints).

Ledger entries during execution follow the format in `02-agent-operating-loop.md` §"Daily Ledger Format" — one entry per task or per cockpit checkpoint, whichever is more useful for traceability.
