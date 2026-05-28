# Subsystem 4 — Backtest Harness (Manual-First) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Cockpit motion is binding:** Codex authors RED contract tests for each task; Claude implements to GREEN. Plan-level decisions get cockpit-debated before this plan is approved for execution; per-task implementation choices follow the plan as written unless a real defect surfaces.

**Goal:** Build a manual-first backtest harness that tests whether NFL mock-draft consensus predicts realized NFL draft capital — Backtest A only in v1, with a B-shaped always-abstain stub + the cross-domain prospect↔NFL bridge workflow that joins S3's prospect identity substrate to nflreadr draft truth.

**Architecture:** Two new modules — `prospect_nfl_bridge.py` (identity infrastructure under `src/dynasty_genius/identity/`) owns the cross-domain bridge schema, validation, review queue, atomic write, and decision-log replay; `backtest_mock_draft.py` (analytics infrastructure under `src/dynasty_genius/eval/`) owns the canonical mock-snapshot schema, ingestion, Backtest A runner, 6 metrics, abstention gates, `backtest_b_gate_status` emitter, report artifact writer, and B-shaped abstain library function. Plus 4 CLI scripts: `build_prospect_nfl_bridge.py`, `promote_bridge_candidate.py`, `run_backtest_a.py`, `run_backtest_b.py`.

**Tech Stack:** Python 3.14, Pydantic 2.x (already in `requirements.txt`), `nflreadpy` (already in `requirements.txt` from Phase 17/18 universe work), `jellyfish` + `rapidfuzz` (already added in S3 build). Test invocation: `.venv/bin/python3.14 -m pytest` per `[[reference_test_invocation]]`.

**Authoritative spec:** [`docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md`](../specs/2026-05-28-subsystem-4-backtest-harness-design.md) — committed at `f0d9123` (round-2 Codex technical CLEAR; Claude independent governance attestation; Gemini CLI broken so its governance review unavailable but boundaries verified independently against its S3-review criteria).

**Branch:** `feature/subsystem-4-backtest-harness` (Task 0 creates it from `main` at `f0d9123`).

**Prerequisites on main:** Subsystem 3 MERGED via PR #55 (`0730dcb`). S3's `ConfirmedProspectUuid`, `score_candidate`, `compute_match_key`, `normalize_name` are public and ready to consume.

---

## Plan-level implementation choices (cockpit-reviewable; not spec changes)

**Choice 1 — Pattern-level S3 reuse, no private imports.** Per spec §2 + Codex's S3-build correction during Round 2 Task 8, S4 implements its own atomic-write/decision-log helpers following the S3 pattern. No underscore-private function imports across module boundaries. S4 uses S3's PUBLIC functions only: `score_candidate`, `compute_match_key`, `normalize_name`, `ConfirmedProspectUuid` exception classes. S4 implements its own `_atomic_write_jsonl`-equivalent helpers internally.

**Choice 2 — S3 surface_review_candidates NOT imported.** Per spec §2 dependency clarification, S4 implements its own NFL-domain discovery wrapper (`surface_nfl_bridge_candidates` or similar) because S3's `surface_review_candidates` has college-side position whitelist/hard-block filters (`{WR↔TE, WR↔RB, FB↔RB}` + QB hard-block etc.) that would mis-handle college→NFL position migrations (e.g., college EDGE → NFL OLB, college S → NFL FS/SS). S4's wrapper reuses `score_candidate` directly but has its own NFL-position-taxonomy gating.

**Choice 3 — Synthetic fixtures committed to repo.** Per spec §4.2, synthetic snapshots live at `tests/fixtures/backtest_mock_draft/snapshots/...` and are committed. Synthetic bridge artifacts and `nflreadr_synthetic` fake-truth files also committed. This is the only test-data path in v1; real-data fixtures are the deferred follow-up workstream (§6.3 acceptance criteria).

**Choice 4 — One module per spec §2; no further file-split in v1.** S3 used a single ~1000-line module successfully with labeled sections. S4 uses two single modules (`prospect_nfl_bridge.py` and `backtest_mock_draft.py`) each with labeled sections. If either grows beyond ~1500 lines, defer the split to a follow-up — don't over-modularize in v1.

---

## Round 2 patches (Codex plan review, 2026-05-28)

After this plan was first committed, Codex's plan-level technical review surfaced 5 findings (2 HIGH + 3 MEDIUM + 1 non-blocking). All folded into the relevant tasks below.

1. **HIGH — S3 confirmed + draft_year validation missing from RED + GREEN.** Task 1 added schema-only validation but spec §3.2 rules 1 + 2 require `prospect_uuid` is `verification_status="confirmed"` in S3 at write time AND `draft_year` == S3 row's `draft_class`. Original plan didn't load S3 from the promotion path. **Fix:** Task 1 RED adds `test_confirm_rejected_when_prospect_uuid_not_in_s3` + `test_confirm_rejected_when_prospect_uuid_not_confirmed` + `test_confirm_rejected_when_draft_year_mismatches_s3`. Task 4 GREEN `promote_bridge_candidate` accepts an `s3_registry` parameter and validates these two invariants before writing.

2. **HIGH — `reject`/`defer` permanently block future `confirm`.** Original idempotency/conflict keyed on `prospect_uuid` alone, making a prior `defer` block all later `confirm`/`udfa`. Spec §3.3 says `defer` closes for this run; future discovery may reopen. **Fix:** Conflict semantics differentiate **accepted** decisions (`confirm`, `udfa`) from **procedural** decisions (`reject`, `defer`). Accepted-vs-accepted with different kinds → conflict; procedural → accepted is ALWAYS allowed (the procedural is overridden by the later accepted). Same-decision rerun stays idempotent. Task 4 RED adds `test_defer_then_confirm_succeeds` and `test_reject_then_confirm_succeeds`.

3. **MEDIUM — Replay silently appended to non-empty genesis.** Original `replay_decision_log` loaded `bridge_path` (could be non-empty); spec §3.2 rule 6 locks replay over **missing or empty** genesis only. **Fix:** Task 2 GREEN raises `BridgeValidationError` if `bridge_path` exists with non-empty entries. Task 2 RED adds `test_replay_fail_closed_on_non_empty_genesis`.

4. **MEDIUM — Audit leakage wording in Task 14 contradicted cleared spec.** Original said "no mock field names anywhere in S4 modules" — but `MockSnapshot`/`MockSnapshotPick`/`MockSnapshotMetadata` are CORRECT module surfaces. **Fix:** Task 14 audit wording tightened to match spec §7 — no mock-derived fields in S3 identity OR S4 bridge; no ADP/market fields in any S4 schema/output; mock fields ALLOWED in S4 snapshot/backtest diagnostic surfaces only.

5. **MEDIUM — Coverage reconciliation formula incomplete.** Original formula `snapshots_used + leakage_excluded + untrusted_excluded == total_snapshots_found` missed three rejection buckets per spec §4.5. **Fix:** Task 14 formula extended: `snapshots_used + leakage_excluded_snapshots + untrusted_excluded_snapshots + duplicate_pick_no_rejections + duplicate_prospect_uuid_rejections + content_hash_collisions == total_snapshots_found`.

6. **Non-blocking — Discovery per-run file writes are not atomic.** Task 4's `scripts/build_prospect_nfl_bridge.py` uses plain `write_text` for review queue / UDFA candidates / coverage matrix. **Fix:** swap to `.tmp + os.replace` pattern matching the bridge atomic-write style (low cost; consistent discipline).

---

## File Structure

**Create:**
- `src/dynasty_genius/identity/prospect_nfl_bridge.py` — bridge schema, validation, review queue, atomic write, decision-log replay
- `src/dynasty_genius/eval/backtest_mock_draft.py` — snapshot schema, ingestion, Backtest A runner, 6 metrics, abstention gates, B-gate emitter, artifact writer, B-stub library function
- `scripts/build_prospect_nfl_bridge.py` — bridge discovery CLI (suggest candidate joins for a draft class)
- `scripts/promote_bridge_candidate.py` — only blessed write path for bridge decisions
- `scripts/run_backtest_a.py` — Backtest A CLI
- `scripts/run_backtest_b.py` — B-shaped always-abstain stub CLI
- `tests/contract/test_subsystem_4_schema.py` — §8.1 schema/model tests
- `tests/contract/test_subsystem_4_bridge.py` — §8.2 bridge workflow tests
- `tests/contract/test_subsystem_4_ingestion.py` — §8.3 ingestion tests (13 contract paths from §6.2)
- `tests/contract/test_subsystem_4_aggregation.py` — §8.4 ProspectConsensus + abstention tests
- `tests/contract/test_subsystem_4_metrics.py` — §8.5 the 6 metrics on golden fixtures
- `tests/contract/test_subsystem_4_b_gate.py` — §8.6 gate status + synthetic safety hedge
- `tests/contract/test_subsystem_4_b_stub.py` — §8.7 B stub always-abstain regression guard
- `tests/contract/test_subsystem_4_audit.py` — §8.8 inviolate paths + leakage + banned language + coverage reconciliation
- `tests/fixtures/backtest_mock_draft/snapshots/<source_label>/...` — synthetic mock snapshots
- `tests/fixtures/backtest_mock_draft/bridge_artifacts/...` — synthetic bridge fixtures
- `tests/fixtures/backtest_mock_draft/nflreadr_synthetic/...` — synthetic nflreadr draft truth

**Modify:**
- `AGENT_SYNC.md` — S4 build progress (Task 14)
- `docs/agent-ledger/<active-day>.md` — postflight closeout entry (Task 14)

**Inviolate (contract test enforces byte-unchanged — see §8.8):**
- All paths inviolate during S3 (everything pre-S3 + S3's merged committed artifacts):
  - `app/data/identity/_runs/prospect_registry.json`
  - `app/data/identity/_runs/composite_registry.json`
  - `app/data/prospect_alias_bridge.json`
  - `src/dynasty_genius/adapters/prospect_identity_resolver.py`
  - `app/data/identity/college_prospect_registry.json`
  - `app/data/identity/college_alias_bridge.json`
  - `src/dynasty_genius/identity/__init__.py` (S3 legacy package init)
  - `src/dynasty_genius/identity/college_prospect_identity.py` (S3 module — S4 only IMPORTS from it; never modifies)

**New data artifacts written by the scripts (gitignored except via explicit ledger entries):**
- `app/data/identity/prospect_to_nfl_bridge_<draft_year>.json`
- `app/data/identity/prospect_nfl_bridge_decision_log_<draft_year>.jsonl`
- `app/data/identity/prospect_nfl_review_queue_<draft_year>_<run_id>.jsonl`
- `app/data/identity/prospect_nfl_unmatched_udfa_candidates_<draft_year>_<run_id>.jsonl`
- `app/data/identity/prospect_nfl_coverage_<draft_year>_<run_id>.json`
- `app/data/backtest/mock_draft/snapshots/<source_label>/<published_date>_<analyst-slug>_<mock_version>.json` (operator-curated; not gitignored)
- `app/data/backtest/mock_draft/runs/<run_id>/backtest_a_result.json`
- `app/data/backtest/mock_draft/runs/<run_id>/backtest_b_abstain.json`

---

## Task 0: Create feature branch + confirm dependencies

**Files:** none beyond git state

- [ ] **Step 1: Create the feature branch from main at f0d9123**

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
git checkout -b feature/subsystem-4-backtest-harness
git log --oneline -3  # confirm HEAD is at f0d9123 or later
```

Expected: branch `feature/subsystem-4-backtest-harness` created; HEAD at `f0d9123` (or wherever main is); spec committed and visible.

- [ ] **Step 2: Confirm prerequisite dependencies present**

```bash
.venv/bin/python3.14 -c "from src.dynasty_genius.identity.college_prospect_identity import ConfirmedProspectUuid, score_candidate, compute_match_key, normalize_name; print('S3 public API OK')"
.venv/bin/python3.14 -c "import nflreadpy; print('nflreadpy', nflreadpy.__version__)"
.venv/bin/python3.14 -c "import jellyfish, rapidfuzz; print('jellyfish OK; rapidfuzz OK')"
```

Expected: all three lines print success messages. If `nflreadpy` is missing, install it (`pip install nflreadpy`) — but it should already be present from Phase 17/18 universe-snapshot work.

- [ ] **Step 3: Confirm baseline suite green**

```bash
.venv/bin/python3.14 -m pytest -q
```

Expected: 1376 passed, 11 skipped, 0 failed (matches main HEAD post-S3-merge).

- [ ] **Step 4: No commit needed for Task 0**

Branch creation alone doesn't require a commit. Tasks 1+ begin the substantive work.

---

## Task 1: Bridge schema + validation contracts — §3.1, §3.2

**Goal:** Lock the `ProspectNflBridgeEntry` Pydantic schema and the 6 validation rules from spec §3.2. No I/O, no workflow yet — pure schema + validation function.

**Files:**
- Create: `src/dynasty_genius/identity/prospect_nfl_bridge.py`
- Create: `tests/contract/test_subsystem_4_schema.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_4_schema.py`:

```python
"""Subsystem 4 — bridge schema + validation contract tests (§3.1, §3.2)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.dynasty_genius.identity.prospect_nfl_bridge import (
    ProspectNflBridgeEntry,
    validate_bridge_entry,
)


def _provenance() -> dict:
    return {
        "nflreadr_source": "nflreadpy.draft_picks",
        "nflreadr_season": 2025,
        "draft_truth_content_hash": "abc123",
        "nflreadr_fetched_at": "2026-05-28T12:00:00Z",
    }


def _drafted_entry_kwargs() -> dict:
    return {
        "prospect_uuid": "cpr_00000000-0000-4000-8000-000000000001",
        "gsis_id": "00-0034987",
        "pfr_id": "ManningArch01",
        "draft_year": 2025,
        "draft_pick_no": 1,
        "draft_round": 1,
        "nfl_team": "CAR",
        "udfa": False,
        "evidence_snapshot": {
            "full_name": "Arch Manning",
            "position": "QB",
            "college": "Texas",
            "fetched_at": "2026-05-28T12:00:00Z",
        },
        "event_id": "ev_1",
        "decided_at": "2026-05-28T12:00:00Z",
        "reviewer_id": "davidleess",
        "decision": "confirm",
        **_provenance(),
    }


def _udfa_entry_kwargs() -> dict:
    return {
        "prospect_uuid": "cpr_00000000-0000-4000-8000-000000000002",
        "gsis_id": None,
        "pfr_id": None,
        "draft_year": 2025,
        "draft_pick_no": None,
        "draft_round": None,
        "nfl_team": None,
        "udfa": True,
        "evidence_snapshot": None,
        "event_id": "ev_2",
        "decided_at": "2026-05-28T12:00:01Z",
        "reviewer_id": "davidleess",
        "decision": "udfa",
        "note": "verified absent from nflreadr 2025 7-day post-draft window",
        **_provenance(),
    }


def test_drafted_entry_accepts_minimal_shape():
    entry = ProspectNflBridgeEntry.model_validate(_drafted_entry_kwargs())
    assert entry.gsis_id == "00-0034987"
    assert entry.udfa is False
    assert entry.decision == "confirm"
    errors = validate_bridge_entry(entry)
    assert errors == []


def test_udfa_entry_accepts_strict_null_shape():
    entry = ProspectNflBridgeEntry.model_validate(_udfa_entry_kwargs())
    assert entry.gsis_id is None
    assert entry.udfa is True
    assert entry.decision == "udfa"
    errors = validate_bridge_entry(entry)
    assert errors == []


def test_drafted_with_null_gsis_id_fails_validation():
    bad = _drafted_entry_kwargs()
    bad["gsis_id"] = None  # udfa=False but no gsis_id
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("gsis_id" in e for e in errors)


def test_drafted_with_null_pick_no_fails_validation():
    bad = _drafted_entry_kwargs()
    bad["draft_pick_no"] = None
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("draft_pick_no" in e for e in errors)


def test_udfa_with_populated_gsis_id_fails_validation():
    bad = _udfa_entry_kwargs()
    bad["gsis_id"] = "00-0034987"  # udfa=True but gsis_id populated
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("udfa" in e.lower() for e in errors)


def test_udfa_with_populated_pfr_id_fails_validation():
    bad = _udfa_entry_kwargs()
    bad["pfr_id"] = "ManningArch01"  # udfa=True but pfr_id populated (strict 5-field rule)
    entry = ProspectNflBridgeEntry.model_validate(bad)
    errors = validate_bridge_entry(entry)
    assert any("pfr_id" in e.lower() or "udfa" in e.lower() for e in errors)


def test_drafted_with_null_pfr_id_is_valid():
    # pfr_id is nullable secondary; udfa=False is OK with pfr_id=None
    ok = _drafted_entry_kwargs()
    ok["pfr_id"] = None
    entry = ProspectNflBridgeEntry.model_validate(ok)
    errors = validate_bridge_entry(entry)
    assert errors == []


def test_missing_provenance_field_fails_validation():
    bad = _drafted_entry_kwargs()
    bad.pop("nflreadr_source")
    with pytest.raises(ValidationError):
        ProspectNflBridgeEntry.model_validate(bad)


def test_decision_literal_rejects_other_strings():
    bad = _drafted_entry_kwargs()
    bad["decision"] = "merge_into"  # not a valid bridge decision
    with pytest.raises(ValidationError):
        ProspectNflBridgeEntry.model_validate(bad)


def test_evidence_snapshot_none_for_udfa_is_valid():
    ok = _udfa_entry_kwargs()
    ok["evidence_snapshot"] = None
    entry = ProspectNflBridgeEntry.model_validate(ok)
    errors = validate_bridge_entry(entry)
    assert errors == []


# --- Round 2 patch 1 (Codex plan review): S3 confirmed + draft_year validation ---

from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    CollegeProspectRegistry,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import (  # noqa: E402
    validate_against_s3,
)


def _s3_row_for(uuid: str, status: str = "confirmed", draft_class: int = 2025):
    base = NormalizedCollegeProspectRow.model_validate({
        "raw_name": "Arch Manning", "normalized_name": "arch manning",
        "full_name": "Arch Manning", "position": "QB", "position_group": "QB",
        "draft_class": draft_class, "current_school": "Texas", "prior_schools": [],
        "cfbd_athlete_id": None, "cfb_player_id": None,
        "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        "source": "manual_fixture", "source_record_id": f"src_{uuid[:8]}",
        "source_snapshot_id": "fixture_2025_v1",
        "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                          "pfr_id": None, "gsis_id": None, "sleeper_id": None},
        "notes": None,
    })
    return RegistryEntry(
        prospect_uuid=uuid, verification_status=status,
        match_key=compute_match_key(
            normalized_name=base.normalized_name, position_group="QB", draft_class=draft_class,
        ),
        status_history=[StatusHistoryEntry(
            event_id=f"ev_{uuid}", decision="confirm", after_status=status,
            decided_at="2026-05-28T12:00:00Z", reviewer_id="davidleess",
        )],
        merged_into_prospect_uuid=None, reviewer_id="davidleess", reviewer_metadata={},
        **base.model_dump(),
    )


def test_confirm_rejected_when_prospect_uuid_not_in_s3():
    """Spec §3.2 rule 1: prospect_uuid MUST resolve in S3 at write time."""
    s3 = CollegeProspectRegistry()  # empty
    entry = ProspectNflBridgeEntry.model_validate(_drafted_entry_kwargs())
    errors = validate_against_s3(entry, s3_registry=s3)
    assert any("not in S3" in e or "unknown" in e.lower() for e in errors)


def test_confirm_rejected_when_prospect_uuid_not_confirmed():
    """Spec §3.2 rule 1: prospect_uuid must be verification_status='confirmed'."""
    uuid = "cpr_00000000-0000-4000-8000-000000000001"
    s3 = CollegeProspectRegistry(entries={uuid: _s3_row_for(uuid, status="provisional")})
    entry = ProspectNflBridgeEntry.model_validate({**_drafted_entry_kwargs(), "prospect_uuid": uuid})
    errors = validate_against_s3(entry, s3_registry=s3)
    assert any("provisional" in e.lower() or "not confirmed" in e.lower() for e in errors)


def test_confirm_rejected_when_draft_year_mismatches_s3():
    """Spec §3.2 rule 2: bridge entry draft_year MUST equal S3 row's draft_class."""
    uuid = "cpr_00000000-0000-4000-8000-000000000001"
    s3 = CollegeProspectRegistry(entries={uuid: _s3_row_for(uuid, draft_class=2024)})  # S3 says 2024
    entry = ProspectNflBridgeEntry.model_validate({**_drafted_entry_kwargs(), "prospect_uuid": uuid})
    # entry.draft_year is 2025; S3 row says 2024 — mismatch
    errors = validate_against_s3(entry, s3_registry=s3)
    assert any("draft_year" in e and "draft_class" in e for e in errors)


def test_confirm_accepted_when_s3_confirmed_and_draft_year_matches():
    uuid = "cpr_00000000-0000-4000-8000-000000000001"
    s3 = CollegeProspectRegistry(entries={uuid: _s3_row_for(uuid, status="confirmed", draft_class=2025)})
    entry = ProspectNflBridgeEntry.model_validate({**_drafted_entry_kwargs(), "prospect_uuid": uuid})
    errors = validate_against_s3(entry, s3_registry=s3)
    assert errors == []
```

- [ ] **Step 2: Run RED check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_schema.py -v
```

Expected: collection error (module doesn't exist yet) — every test fails with `ModuleNotFoundError: No module named 'src.dynasty_genius.identity.prospect_nfl_bridge'`.

- [ ] **Step 3: Claude implements GREEN — module skeleton + schema + validation**

Create `src/dynasty_genius/identity/prospect_nfl_bridge.py`:

```python
"""Subsystem 4 — Prospect ↔ NFL Bridge.

Cross-domain identity infrastructure: maps S3's pre-draft prospect_uuid
(opaque cpr_<uuid4>, confirmed only) to realized NFL gsis_id (from nflreadr
draft truth) at draft time. Manual-first review queue + promotion lifecycle;
per-file atomic writes; decision-log replay over genesis state per S3 §6.3.

Single-module implementation organized in labeled sections:
- Constants & versions
- Schema (Pydantic 2.x)
- Exceptions
- Validation (rules from spec §3.2)
- Atomic write helpers           (Task 2)
- Decision log + replay          (Task 2)
- Discovery / candidate matching (Task 3)
- Promotion lifecycle            (Task 4)

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ======================================================================
# Constants & versions
# ======================================================================

BRIDGE_SCHEMA_VERSION: str = "prospect_nfl_bridge_v1.0.0"
NFL_DOMAIN_MATCHER_VERSION: str = "cpr_nfl_bridge_matcher_v1.0.0"


# ======================================================================
# Schema (Pydantic 2.x)
# ======================================================================


class ProspectNflBridgeEntry(BaseModel):
    """Spec §3.1: cross-domain bridge entry mapping pre-draft prospect_uuid →
    realized NFL identity. Accepted-only artifact entries (`confirm` and `udfa`
    decisions); rejects/defers live only in the decision log + review queue."""

    model_config = ConfigDict(extra="forbid")

    # identity
    prospect_uuid: str
    gsis_id: Optional[str] = None
    pfr_id: Optional[str] = None

    # context
    draft_year: int
    draft_pick_no: Optional[int] = None
    draft_round: Optional[int] = None
    nfl_team: Optional[str] = None
    udfa: bool

    # provenance of the nflreadr snapshot used at decision time
    nflreadr_source: str
    nflreadr_season: int
    draft_truth_content_hash: str
    nflreadr_fetched_at: str

    evidence_snapshot: Optional[dict[str, Any]] = None

    # decision audit (no nested status_history; that's S3 vocabulary)
    event_id: str
    decided_at: str
    reviewer_id: str
    decision: Literal["confirm", "udfa"]
    note: Optional[str] = None


# ======================================================================
# Exceptions
# ======================================================================


class BridgeValidationError(RuntimeError):
    """Raised when a bridge graph validation reveals an inconsistency."""


class BridgeEvidenceRequiredError(ValueError):
    """`udfa` promotion requires non-empty --evidence per spec §3.3."""


class BridgeConflictingDecisionError(RuntimeError):
    """Same prospect_uuid already has a different decision in the log."""


# ======================================================================
# Validation (rules from spec §3.2, per-entry shape checks)
# ======================================================================


def validate_bridge_entry(entry: ProspectNflBridgeEntry) -> list[str]:
    """Per-entry shape validation. Returns a list of human-readable errors
    (empty list = valid). Cross-entry invariants (1:1) are checked in
    `validate_bridge_graph`; S3 confirmation + draft_year invariants are
    checked in `validate_against_s3` (Round 2 patch 1)."""
    errors: list[str] = []
    if entry.udfa:
        # spec §3.2 rule 4: udfa=True ⇒ 5 strict null fields
        for field in ("gsis_id", "pfr_id", "draft_pick_no", "draft_round", "nfl_team"):
            if getattr(entry, field) is not None:
                errors.append(
                    f"udfa=True requires {field}=None (spec §3.2 rule 4); got "
                    f"{getattr(entry, field)!r}"
                )
    else:
        # spec §3.2 rule 5: udfa=False ⇒ 4 required NFL fields
        for field in ("gsis_id", "draft_pick_no", "draft_round", "nfl_team"):
            if getattr(entry, field) is None:
                errors.append(
                    f"udfa=False requires {field} present (spec §3.2 rule 5); "
                    f"got None"
                )
        # pfr_id is nullable secondary; not required even when udfa=False
    return errors


def validate_against_s3(
    entry: ProspectNflBridgeEntry,
    *,
    s3_registry,
) -> list[str]:
    """Round 2 patch 1 (Codex plan review): spec §3.2 rules 1 + 2 require S3
    knowledge at bridge write time. Caller passes a loaded S3 CollegeProspectRegistry.

    Returns errors if:
    - prospect_uuid is not present in S3 (unknown)
    - prospect_uuid is in S3 but not verification_status='confirmed'
    - bridge entry's draft_year != S3 row's draft_class
    """
    errors: list[str] = []
    s3_row = s3_registry.entries.get(entry.prospect_uuid)
    if s3_row is None:
        errors.append(
            f"prospect_uuid {entry.prospect_uuid} not in S3 registry (spec §3.2 rule 1)"
        )
        return errors  # can't check rule 2 without an S3 row
    if s3_row.verification_status != "confirmed":
        errors.append(
            f"prospect_uuid {entry.prospect_uuid} has S3 status="
            f"{s3_row.verification_status!r} (not confirmed; spec §3.2 rule 1)"
        )
    if entry.draft_year != s3_row.draft_class:
        errors.append(
            f"bridge draft_year={entry.draft_year} != S3 row's draft_class="
            f"{s3_row.draft_class} (spec §3.2 rule 2)"
        )
    return errors
```

- [ ] **Step 4: Run GREEN check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_schema.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/prospect_nfl_bridge.py tests/contract/test_subsystem_4_schema.py
git commit -m "feat(subsystem-4): bridge schema + validation + section 3.1 + 3.2 contract tests"
```

---

## Task 2: Bridge atomic write + decision-log + replay over genesis — §3.2 rule 6

**Goal:** Atomic write helpers for the bridge artifact and decision log; replay applicator that reconstructs the accepted-only artifact byte-identical from a missing/empty genesis + a decision log. Replay applies only `confirm`/`udfa` events; `reject`/`defer` events stay in the log for audit but don't mutate the artifact.

**Files:**
- Modify: `src/dynasty_genius/identity/prospect_nfl_bridge.py` (append atomic write + decision log + replay section)
- Create: `tests/contract/test_subsystem_4_bridge.py`

- [ ] **Step 1: Codex writes the RED contract test file**

Create `tests/contract/test_subsystem_4_bridge.py`:

```python
"""Subsystem 4 — bridge atomic write + decision-log + replay tests (§3.2 rule 6, §3.3)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.dynasty_genius.identity.prospect_nfl_bridge import (
    CollegeProspectBridge,
    ProspectNflBridgeEntry,
    apply_decision_event,
    atomic_write_bridge,
    atomic_write_decision_log,
    load_bridge,
    load_decision_log,
    replay_decision_log,
)


def _provenance() -> dict:
    return {
        "nflreadr_source": "nflreadpy.draft_picks",
        "nflreadr_season": 2025,
        "draft_truth_content_hash": "abc123",
        "nflreadr_fetched_at": "2026-05-28T12:00:00Z",
    }


def _drafted_entry(prospect_uuid: str, gsis_id: str, pick_no: int) -> ProspectNflBridgeEntry:
    return ProspectNflBridgeEntry.model_validate({
        "prospect_uuid": prospect_uuid,
        "gsis_id": gsis_id,
        "pfr_id": None,
        "draft_year": 2025,
        "draft_pick_no": pick_no,
        "draft_round": 1 if pick_no <= 32 else (pick_no - 1) // 32 + 1,
        "nfl_team": "CAR",
        "udfa": False,
        "evidence_snapshot": {"full_name": "X", "position": "QB", "college": "Y", "fetched_at": "Z"},
        "event_id": f"ev_{prospect_uuid[:8]}",
        "decided_at": "2026-05-28T12:00:00Z",
        "reviewer_id": "davidleess",
        "decision": "confirm",
        "note": None,
        **_provenance(),
    })


def test_load_bridge_handles_missing_file(tmp_path: Path):
    bridge = load_bridge(tmp_path / "absent.json")
    assert isinstance(bridge, CollegeProspectBridge)
    assert bridge.entries == []


def test_load_bridge_handles_zero_byte_file(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("")
    bridge = load_bridge(p)
    assert bridge.entries == []


def test_atomic_write_uses_tmp_then_rename(tmp_path: Path, monkeypatch):
    p = tmp_path / "bridge.json"
    bridge = CollegeProspectBridge(
        metadata={"draft_year": 2025}, entries=[]
    )
    seen_tmp: list[Path] = []
    original_replace = __import__("os").replace

    def spy(src, dst):
        seen_tmp.append(Path(src))
        return original_replace(src, dst)

    monkeypatch.setattr("os.replace", spy)
    atomic_write_bridge(bridge, p)
    assert p.exists()
    assert seen_tmp and seen_tmp[0].name.endswith(".tmp")
    reloaded = load_bridge(p)
    assert reloaded.metadata == {"draft_year": 2025}


def test_decision_log_round_trip(tmp_path: Path):
    p = tmp_path / "decision_log.jsonl"
    events = [
        {"event_id": "ev_1", "decision": "confirm", "prospect_uuid": "cpr_a"},
        {"event_id": "ev_2", "decision": "reject", "prospect_uuid": "cpr_b"},
    ]
    atomic_write_decision_log(events, p)
    reloaded = load_decision_log(p)
    assert reloaded == events


def test_apply_decision_event_confirm_appends_accepted_entry():
    bridge = CollegeProspectBridge(entries=[])
    entry = _drafted_entry("cpr_a", "00-0001", 1)
    event = {"decision": "confirm", "entry": entry.model_dump()}
    apply_decision_event(event, bridge)
    assert len(bridge.entries) == 1
    assert bridge.entries[0].prospect_uuid == "cpr_a"


def test_apply_decision_event_reject_does_not_mutate_bridge():
    bridge = CollegeProspectBridge(entries=[])
    event = {"decision": "reject", "prospect_uuid": "cpr_a", "event_id": "ev_1"}
    apply_decision_event(event, bridge)
    assert bridge.entries == []


def test_apply_decision_event_defer_does_not_mutate_bridge():
    bridge = CollegeProspectBridge(entries=[])
    event = {"decision": "defer", "prospect_uuid": "cpr_a", "event_id": "ev_1", "note": "need more info"}
    apply_decision_event(event, bridge)
    assert bridge.entries == []


def test_replay_fail_closed_on_non_empty_genesis(tmp_path: Path):
    """Round 2 patch 3 (Codex plan review): replay must start from missing or
    empty bridge file. Non-empty pre-existing entries → BridgeValidationError."""
    pre_existing_entry = _drafted_entry("cpr_pre", "00-9999", 32)
    seeded_bridge = CollegeProspectBridge(entries=[pre_existing_entry])
    bridge_path = tmp_path / "seeded_bridge.json"
    atomic_write_bridge(seeded_bridge, bridge_path)

    log_path = tmp_path / "decision_log.jsonl"
    atomic_write_decision_log([], log_path)

    from src.dynasty_genius.identity.prospect_nfl_bridge import BridgeValidationError
    with pytest.raises(BridgeValidationError):
        replay_decision_log(log_path=log_path, bridge_path=bridge_path)


def test_replay_decision_log_reproduces_bridge_byte_identical(tmp_path: Path):
    """Spec §3.2 rule 6: replay over GENESIS state (empty file) applies only
    accepted (confirm + udfa) events to reconstruct the bridge artifact
    byte-identical to the live-promoted artifact."""
    # Live state: write events, build live bridge, save
    entries_to_confirm = [
        _drafted_entry("cpr_aaaa", "00-0001", 1),
        _drafted_entry("cpr_bbbb", "00-0002", 5),
    ]
    log_events = [
        {"decision": "confirm", "entry": entries_to_confirm[0].model_dump(),
         "event_id": "ev_1", "prospect_uuid": "cpr_aaaa"},
        {"decision": "reject", "event_id": "ev_2", "prospect_uuid": "cpr_xxxx", "note": "not a match"},
        {"decision": "confirm", "entry": entries_to_confirm[1].model_dump(),
         "event_id": "ev_3", "prospect_uuid": "cpr_bbbb"},
        {"decision": "defer", "event_id": "ev_4", "prospect_uuid": "cpr_yyyy", "note": "transfer pending"},
    ]
    log_path = tmp_path / "decision_log.jsonl"
    atomic_write_decision_log(log_events, log_path)

    # Build live bridge by applying events in order
    live_bridge = CollegeProspectBridge(entries=[])
    for ev in log_events:
        apply_decision_event(ev, live_bridge)
    live_bridge_path = tmp_path / "live_bridge.json"
    atomic_write_bridge(live_bridge, live_bridge_path)
    live_bytes = live_bridge_path.read_bytes()

    # Replay over GENESIS state (no file present)
    genesis_dir = tmp_path / "replay"
    genesis_dir.mkdir()
    genesis_bridge_path = genesis_dir / "live_bridge.json"  # missing
    replay_decision_log(log_path=log_path, bridge_path=genesis_bridge_path)
    replayed_bytes = genesis_bridge_path.read_bytes()

    assert replayed_bytes == live_bytes
    # Verify only accepted entries landed
    reloaded = load_bridge(genesis_bridge_path)
    assert len(reloaded.entries) == 2
    assert {e.prospect_uuid for e in reloaded.entries} == {"cpr_aaaa", "cpr_bbbb"}
```

- [ ] **Step 2: Run RED check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_bridge.py -v
```

Expected: `ImportError: cannot import name 'CollegeProspectBridge' from src.dynasty_genius.identity.prospect_nfl_bridge`.

- [ ] **Step 3: Claude implements GREEN — atomic writes + decision log + replay**

Append to `src/dynasty_genius/identity/prospect_nfl_bridge.py`:

```python
# ======================================================================
# Atomic write helpers + decision log + replay (spec §3.2 rule 6, §3.3)
# ======================================================================

import json
import os
from pathlib import Path


class CollegeProspectBridge(BaseModel):
    """Container for accepted-only bridge entries (confirm + udfa decisions).
    Decision-log replay reconstructs this from missing/empty genesis."""

    model_config = ConfigDict(extra="forbid")

    metadata: dict[str, Any] = Field(default_factory=dict)
    entries: list[ProspectNflBridgeEntry] = Field(default_factory=list)


def load_bridge(path: Path) -> CollegeProspectBridge:
    """Spec parity with S3 load_registry: missing or empty file → empty bridge."""
    if not path.exists():
        return CollegeProspectBridge()
    text = path.read_text()
    if not text.strip():
        return CollegeProspectBridge()
    raw = json.loads(text)
    return CollegeProspectBridge.model_validate(raw)


def atomic_write_bridge(bridge: CollegeProspectBridge, path: Path) -> None:
    """Per-file atomic write via sibling .tmp then os.replace (S3 §6.4 pattern)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = {
        "metadata": bridge.metadata,
        "entries": [e.model_dump(mode="json") for e in bridge.entries],
    }
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    os.replace(tmp, path)


def load_decision_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def atomic_write_decision_log(events: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = "\n".join(json.dumps(e, sort_keys=True) for e in events)
    if events:
        payload += "\n"
    tmp.write_text(payload)
    os.replace(tmp, path)


def apply_decision_event(event: dict[str, Any], bridge: CollegeProspectBridge) -> None:
    """Spec §3.2 rule 6: replay applies ONLY accepted (`confirm` and `udfa`)
    events to mutate the bridge artifact. `reject` and `defer` events are
    recorded in the log for audit but do NOT mutate the bridge."""
    decision = event.get("decision")
    if decision in ("confirm", "udfa"):
        entry_dict = event.get("entry")
        if entry_dict is None:
            return  # malformed event; skip
        entry = ProspectNflBridgeEntry.model_validate(entry_dict)
        bridge.entries.append(entry)
    # reject / defer: no mutation


def replay_decision_log(*, log_path: Path, bridge_path: Path) -> None:
    """Spec §3.2 rule 6: replay over GENESIS state (missing or empty bridge file).
    Applies events from the log in temporal order via apply_decision_event,
    reconstructs the accepted-only artifact, atomic-writes the result.

    Round 2 patch 3 (Codex plan review): fail-closed on non-empty genesis. Replay
    must start from missing/empty bridge per spec §3.2 rule 6 — appending to a
    non-empty file would silently produce a different artifact than the live path
    and is the exact failure mode the spec language forbids."""
    bridge = load_bridge(bridge_path)
    if bridge.entries:
        raise BridgeValidationError(
            f"replay_decision_log requires missing or empty bridge genesis at {bridge_path}; "
            f"got {len(bridge.entries)} pre-existing entries (spec §3.2 rule 6)"
        )
    events = load_decision_log(log_path)
    for event in events:
        apply_decision_event(event, bridge)
    atomic_write_bridge(bridge, bridge_path)
```

- [ ] **Step 4: Run GREEN check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_bridge.py tests/contract/test_subsystem_4_schema.py -v
```

Expected: all tests pass (8 new bridge tests + 10 schema tests from Task 1).

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/prospect_nfl_bridge.py tests/contract/test_subsystem_4_bridge.py
git commit -m "feat(subsystem-4): bridge atomic write + decision log + replay over genesis"
```

---

## Task 3: Bridge discovery + NFL-domain candidate matching — §3.3 stage i

**Goal:** Implement bridge discovery — read S3 confirmed prospects for a draft year, fetch nflreadr draft truth, match candidates using S3's `score_candidate` + a custom NFL-position-taxonomy wrapper, write per-run review queue + UDFA candidates + coverage matrix. Per Plan Choice 2, this implements its OWN `surface_nfl_bridge_candidates` (no import of S3's college-side `surface_review_candidates`).

**Files:**
- Modify: `src/dynasty_genius/identity/prospect_nfl_bridge.py` (append discovery section)
- Modify: `tests/contract/test_subsystem_4_bridge.py` (append discovery tests)

- [ ] **Step 1: Codex writes RED tests for discovery + NFL-domain matching**

Append to `tests/contract/test_subsystem_4_bridge.py`:

```python
# --- Discovery + NFL-domain matching tests ---


from src.dynasty_genius.identity.college_prospect_identity import (  # noqa: E402
    CollegeProspectRegistry,
    NormalizedCollegeProspectRow,
    RegistryEntry,
    StatusHistoryEntry,
    compute_match_key,
)
from src.dynasty_genius.identity.prospect_nfl_bridge import (  # noqa: E402
    NFL_POSITION_WHITELIST,
    NflTruthRow,
    is_nfl_position_pair_compatible,
    score_nfl_candidate,
    surface_nfl_bridge_candidates,
)


def _confirmed_s3_row(uuid: str, name: str, position: str, position_group: str, school: str = "Texas"):
    base = NormalizedCollegeProspectRow.model_validate({
        "raw_name": name, "normalized_name": name.lower(), "full_name": name,
        "position": position, "position_group": position_group, "draft_class": 2025,
        "current_school": school, "prior_schools": [],
        "cfbd_athlete_id": None, "cfb_player_id": None,
        "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        "source": "manual_fixture", "source_record_id": f"src_{uuid[:8]}",
        "source_snapshot_id": "fixture_2025_v1",
        "id_provenance": {"cfbd_athlete_id": None, "cfb_player_id": None,
                          "pfr_id": None, "gsis_id": None, "sleeper_id": None},
        "notes": None,
    })
    return RegistryEntry(
        prospect_uuid=uuid, verification_status="confirmed",
        match_key=compute_match_key(
            normalized_name=base.normalized_name, position_group=position_group, draft_class=2025,
        ),
        status_history=[StatusHistoryEntry(
            event_id=f"ev_{uuid}", decision="confirm", after_status="confirmed",
            decided_at="2026-05-28T12:00:00Z", reviewer_id="davidleess",
        )],
        merged_into_prospect_uuid=None,
        reviewer_id="davidleess", reviewer_metadata={},
        **base.model_dump(),
    )


def _nfl_truth_row(name: str, position: str, gsis_id: str, pick_no: int, team: str = "CAR"):
    return NflTruthRow(
        gsis_id=gsis_id, pfr_id=None, full_name=name, normalized_name=name.lower(),
        position=position, college="Texas", draft_year=2025,
        draft_pick_no=pick_no, draft_round=1 if pick_no <= 32 else 2, nfl_team=team,
        fetched_at="2026-05-28T12:00:00Z",
    )


def test_nfl_position_whitelist_supports_known_transitions():
    # Direct domain-specific transitions for college → NFL
    assert is_nfl_position_pair_compatible("QB", "QB") is True
    assert is_nfl_position_pair_compatible("EDGE", "OLB") is True
    assert is_nfl_position_pair_compatible("EDGE", "DE") is True
    assert is_nfl_position_pair_compatible("S", "FS") is True
    assert is_nfl_position_pair_compatible("S", "SS") is True
    assert is_nfl_position_pair_compatible("CB", "CB") is True
    # WR/RB/TE: same-position only (no offense-only college whitelist drift)
    assert is_nfl_position_pair_compatible("WR", "WR") is True
    assert is_nfl_position_pair_compatible("WR", "RB") is False  # NFL bridge ≠ S3 college whitelist


def test_nfl_position_hard_blocks_offense_vs_defense():
    assert is_nfl_position_pair_compatible("QB", "DE") is False
    assert is_nfl_position_pair_compatible("WR", "CB") is False


def test_score_nfl_candidate_uses_s3_score_candidate_pattern():
    # Verify the scoring function returns finite scores in [0, 1]
    college = _confirmed_s3_row("cpr_aaa", "Arch Manning", "QB", "QB")
    nfl_truth = _nfl_truth_row("Arch Manning", "QB", "00-0001", 1)
    result = score_nfl_candidate(college, nfl_truth)
    assert 0.0 <= result.match_score <= 1.0
    assert result.gsis_id == "00-0001"


def test_surface_nfl_bridge_candidates_returns_high_score_matches():
    college = _confirmed_s3_row("cpr_aaa", "Arch Manning", "QB", "QB")
    nfl_rows = [
        _nfl_truth_row("Arch Manning", "QB", "00-0001", 1),
        _nfl_truth_row("Caleb Williams", "QB", "00-0002", 10),
    ]
    candidates = surface_nfl_bridge_candidates(college, nfl_rows)
    assert candidates
    # Top candidate should be Arch Manning by name similarity
    assert candidates[0].gsis_id == "00-0001"


def test_surface_excludes_hard_blocked_positions():
    college = _confirmed_s3_row("cpr_aaa", "Arch Manning", "QB", "QB")
    nfl_rows = [
        _nfl_truth_row("Arch Manning", "DE", "00-0001", 1),  # QB → DE: hard-blocked
    ]
    candidates = surface_nfl_bridge_candidates(college, nfl_rows)
    assert candidates == []


def test_surface_includes_whitelist_position_transition():
    # College EDGE → NFL OLB: allowed transition; high name match should surface
    college = _confirmed_s3_row("cpr_aaa", "Aidan Hutchinson", "EDGE", "EDGE")
    nfl_rows = [
        _nfl_truth_row("Aidan Hutchinson", "OLB", "00-0001", 1),
    ]
    candidates = surface_nfl_bridge_candidates(college, nfl_rows)
    assert candidates
    assert "position_transition_allowed" in candidates[0].risk_flags
```

- [ ] **Step 2: Run RED check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_bridge.py -v 2>&1 | tail -20
```

Expected: `ImportError` on the new symbols (`NFL_POSITION_WHITELIST`, `NflTruthRow`, etc.).

- [ ] **Step 3: Claude implements GREEN — NFL-domain matcher**

Append to `src/dynasty_genius/identity/prospect_nfl_bridge.py`:

```python
# ======================================================================
# Discovery / NFL-domain candidate matching (spec §3.3 stage i)
# ======================================================================

from dataclasses import dataclass

from src.dynasty_genius.identity.college_prospect_identity import (
    RegistryEntry as S3RegistryEntry,
    score_candidate as s3_score_candidate,
)


class NflTruthRow(BaseModel):
    """A single row of nflreadr draft truth (column subset we care about)."""

    model_config = ConfigDict(extra="forbid")

    gsis_id: str
    pfr_id: Optional[str] = None
    full_name: str
    normalized_name: str
    position: str
    college: Optional[str] = None
    draft_year: int
    draft_pick_no: int
    draft_round: int
    nfl_team: str
    fetched_at: str


# NFL-domain position taxonomy (different from S3's offense-only college whitelist).
# Frozen sets keep this auditable + immutable.
NFL_POSITION_WHITELIST: frozenset[frozenset[str]] = frozenset({
    # Pass-rush / linebacker transitions
    frozenset({"EDGE", "OLB"}),
    frozenset({"EDGE", "DE"}),
    frozenset({"DE", "DT"}),       # 3-4 vs 4-3 alignment differences
    # Secondary
    frozenset({"S", "FS"}),
    frozenset({"S", "SS"}),
    frozenset({"FS", "SS"}),
    frozenset({"CB", "NB"}),       # nickelback
    # Linebacker family
    frozenset({"ILB", "MLB"}),
    frozenset({"LB", "ILB"}),
    frozenset({"LB", "OLB"}),
    frozenset({"LB", "MLB"}),
    # Offense
    frozenset({"OG", "OT"}),       # interior swing
    frozenset({"OT", "OL"}),
    frozenset({"OG", "OL"}),
    frozenset({"C", "OG"}),
})

# Hard-block offense ↔ defense pairings (never compatible regardless of name match)
_NFL_OFFENSE: frozenset[str] = frozenset({
    "QB", "RB", "FB", "WR", "TE", "OL", "OT", "OG", "C",
})
_NFL_DEFENSE: frozenset[str] = frozenset({
    "DL", "DE", "DT", "EDGE", "LB", "ILB", "MLB", "OLB",
    "CB", "NB", "S", "FS", "SS", "DB",
})


def is_nfl_position_pair_compatible(college_pos: str, nfl_pos: str) -> bool:
    """NFL-domain position compatibility. Direct exact-match always allowed.
    Whitelist transitions allowed. Offense ↔ defense always blocked."""
    if college_pos.upper() == nfl_pos.upper():
        return True
    cu, nu = college_pos.upper(), nfl_pos.upper()
    if (cu in _NFL_OFFENSE and nu in _NFL_DEFENSE) or (
        cu in _NFL_DEFENSE and nu in _NFL_OFFENSE
    ):
        return False
    if frozenset({cu, nu}) in NFL_POSITION_WHITELIST:
        return True
    return False


@dataclass(frozen=True)
class NflBridgeCandidate:
    """Discovery output: a candidate pairing of college prospect → nflreadr row."""

    prospect_uuid: str
    gsis_id: str
    nfl_truth_row: dict[str, Any]
    match_score: float
    score_breakdown: dict[str, float]
    risk_flags: tuple[str, ...]
    matcher_algorithm_version: str


def score_nfl_candidate(
    college: S3RegistryEntry,
    nfl_truth: NflTruthRow,
) -> NflBridgeCandidate:
    """Score a college → NFL candidate using S3's score_candidate scoring for
    name similarity, then apply NFL-domain bonuses/penalties."""
    # Construct an S3-shaped "incoming" view of the nfl truth row so we can
    # call s3_score_candidate for the name/position/school computation; we'll
    # adjust position handling separately for NFL-domain semantics.
    from src.dynasty_genius.identity.college_prospect_identity import (
        NormalizedCollegeProspectRow,
    )

    nfl_as_college_shape = NormalizedCollegeProspectRow.model_validate({
        "raw_name": nfl_truth.full_name,
        "normalized_name": nfl_truth.normalized_name,
        "full_name": nfl_truth.full_name,
        "position": nfl_truth.position,
        "position_group": nfl_truth.position,
        "draft_class": nfl_truth.draft_year,
        "current_school": nfl_truth.college or "",
        "prior_schools": [],
        "cfbd_athlete_id": None, "cfb_player_id": None,
        "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        "source": "nflreadr",
        "source_record_id": f"nflreadr_{nfl_truth.gsis_id}",
        "source_snapshot_id": f"nflreadr_{nfl_truth.draft_year}",
        "id_provenance": {
            "cfbd_athlete_id": None, "cfb_player_id": None,
            "pfr_id": None, "gsis_id": None, "sleeper_id": None,
        },
        "notes": None,
    })

    # NOTE: s3_score_candidate enforces draft_class equality (hard-zeros otherwise);
    # we ensured nfl_truth.draft_year matches college.draft_class above.
    s3_candidate = s3_score_candidate(nfl_as_college_shape, college)

    # NFL-domain position adjustment
    risk_flags: list[str] = list(s3_candidate.risk_flags)
    if not is_nfl_position_pair_compatible(college.position, nfl_truth.position):
        # Hard-block: drop score to 0
        return NflBridgeCandidate(
            prospect_uuid=college.prospect_uuid, gsis_id=nfl_truth.gsis_id,
            nfl_truth_row=nfl_truth.model_dump(),
            match_score=0.0,
            score_breakdown={**s3_candidate.score_breakdown, "nfl_position_block": 1.0},
            risk_flags=("position_hard_blocked",),
            matcher_algorithm_version=NFL_DOMAIN_MATCHER_VERSION,
        )

    if college.position.upper() != nfl_truth.position.upper():
        # Whitelist transition allowed
        risk_flags.append("position_transition_allowed")

    return NflBridgeCandidate(
        prospect_uuid=college.prospect_uuid, gsis_id=nfl_truth.gsis_id,
        nfl_truth_row=nfl_truth.model_dump(),
        match_score=s3_candidate.match_score,
        score_breakdown=s3_candidate.score_breakdown,
        risk_flags=tuple(risk_flags),
        matcher_algorithm_version=NFL_DOMAIN_MATCHER_VERSION,
    )


def surface_nfl_bridge_candidates(
    college: S3RegistryEntry,
    nfl_truth_rows: list[NflTruthRow],
    *,
    min_score: float = 0.75,
    top_k: int = 5,
) -> list[NflBridgeCandidate]:
    """Surface up to top_k NFL truth candidates above min_score for a given
    college prospect. Hard-blocked position pairings are excluded; whitelist
    transitions surface only when name match clears min_score."""
    scored: list[NflBridgeCandidate] = []
    for nfl in nfl_truth_rows:
        if nfl.draft_year != college.draft_class:
            continue  # cross-class blocked
        cand = score_nfl_candidate(college, nfl)
        if cand.match_score >= min_score and "position_hard_blocked" not in cand.risk_flags:
            scored.append(cand)
    scored.sort(key=lambda c: c.match_score, reverse=True)
    return scored[:top_k]
```

- [ ] **Step 4: Run GREEN check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_bridge.py tests/contract/test_subsystem_4_schema.py -v
```

Expected: all bridge + schema tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/prospect_nfl_bridge.py tests/contract/test_subsystem_4_bridge.py
git commit -m "feat(subsystem-4): NFL-domain candidate matching + discovery (uses S3 score_candidate)"
```

---

## Task 4: Bridge promotion lifecycle + CLI scripts — §3.3 stages ii–iii

**Goal:** Promotion CLI (`promote_bridge_candidate.py`) with 4 decisions (`confirm`, `udfa`, `reject`, `defer`). Three-point logging (bridge artifact + decision log + review-queue closure). 1:1 invariant validation (cross-entry). Idempotent rerun; conflicting rerun raises. Discovery CLI (`build_prospect_nfl_bridge.py`) ties Task 3's discovery to the review-queue + coverage-matrix outputs.

**Files:**
- Modify: `src/dynasty_genius/identity/prospect_nfl_bridge.py` (append promotion section)
- Create: `scripts/build_prospect_nfl_bridge.py`
- Create: `scripts/promote_bridge_candidate.py`
- Modify: `tests/contract/test_subsystem_4_bridge.py` (append promotion tests)

- [ ] **Step 1: Codex writes RED tests for promotion lifecycle**

Append to `tests/contract/test_subsystem_4_bridge.py`:

```python
# --- Promotion lifecycle tests ---

from src.dynasty_genius.identity.prospect_nfl_bridge import (  # noqa: E402
    BridgeConflictingDecisionError,
    BridgeEvidenceRequiredError,
    PromotionDecision,
    PromotionResult,
    promote_bridge_candidate,
    validate_bridge_graph,
)


def _make_review_payload(review_id: str, prospect_uuid: str, gsis_id: str):
    return {
        "review_id": review_id,
        "prospect_uuid": prospect_uuid,
        "gsis_id": gsis_id,
        "match_score": 0.95,
        "decided_at": None,
        "decision": None,
        "event_id": None,
    }


def test_promote_confirm_writes_three_point_trail(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    review_path = identity_dir / "prospect_nfl_review_queue_2025_run_a.jsonl"
    review_path.write_text(json.dumps(_make_review_payload("rev_1", "cpr_aaa", "00-0001")) + "\n")

    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    decision = PromotionDecision(kind="confirm", entry=entry)
    result = promote_bridge_candidate(
        review_id="rev_1", decision=decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note=None,
    )
    assert result.exit_code == 0

    # Bridge artifact has the entry
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert len(bridge.entries) == 1
    assert bridge.entries[0].prospect_uuid == "cpr_aaa"

    # Decision log has the event
    log = load_decision_log(identity_dir / "prospect_nfl_bridge_decision_log_2025.jsonl")
    assert len(log) == 1
    assert log[0]["decision"] == "confirm"

    # Review queue row got closure marker
    closed_rows = [json.loads(line) for line in review_path.read_text().splitlines() if line.strip()]
    assert closed_rows[0]["decision"] == "confirm"
    assert closed_rows[0]["event_id"] is not None
    assert closed_rows[0]["decided_at"] is not None


def test_promote_udfa_requires_evidence(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    udfa_entry_kwargs = _udfa_entry_kwargs()
    udfa_entry = ProspectNflBridgeEntry.model_validate(udfa_entry_kwargs)
    decision = PromotionDecision(kind="udfa", entry=udfa_entry)
    with pytest.raises(BridgeEvidenceRequiredError):
        promote_bridge_candidate(
            review_id=None, decision=decision,
            identity_dir=identity_dir, draft_year=2025,
            reviewer_id="davidleess", evidence=None, note=None,
        )


def test_promote_reject_closes_review_without_mutating_bridge(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    review_path = identity_dir / "prospect_nfl_review_queue_2025_run_a.jsonl"
    review_path.write_text(json.dumps(_make_review_payload("rev_1", "cpr_xxx", "00-9999")) + "\n")

    decision = PromotionDecision(kind="reject", prospect_uuid="cpr_xxx")
    result = promote_bridge_candidate(
        review_id="rev_1", decision=decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note="not a match",
    )
    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert bridge.entries == []
    closed_rows = [json.loads(line) for line in review_path.read_text().splitlines() if line.strip()]
    assert closed_rows[0]["decision"] == "reject"


def test_promote_defer_closes_review_without_mutating_bridge(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    review_path = identity_dir / "prospect_nfl_review_queue_2025_run_a.jsonl"
    review_path.write_text(json.dumps(_make_review_payload("rev_1", "cpr_xxx", "00-9999")) + "\n")

    decision = PromotionDecision(kind="defer", prospect_uuid="cpr_xxx")
    result = promote_bridge_candidate(
        review_id="rev_1", decision=decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note="transfer pending verification",
    )
    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert bridge.entries == []
    closed_rows = [json.loads(line) for line in review_path.read_text().splitlines() if line.strip()]
    assert closed_rows[0]["decision"] == "defer"


def test_idempotent_rerun_same_decision_is_noop(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    decision = PromotionDecision(kind="confirm", entry=entry)
    promote_bridge_candidate(
        review_id=None, decision=decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note=None,
    )
    log_path = identity_dir / "prospect_nfl_bridge_decision_log_2025.jsonl"
    before = log_path.read_bytes()
    result = promote_bridge_candidate(
        review_id=None, decision=decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note=None,
    )
    assert result.exit_code == 0
    assert before == log_path.read_bytes()


def test_conflicting_rerun_raises(tmp_path: Path):
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    decision_confirm = PromotionDecision(kind="confirm", entry=entry)
    promote_bridge_candidate(
        review_id=None, decision=decision_confirm,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note=None,
    )
    decision_reject = PromotionDecision(kind="reject", prospect_uuid="cpr_aaa")
    with pytest.raises(BridgeConflictingDecisionError):
        promote_bridge_candidate(
            review_id=None, decision=decision_reject,
            identity_dir=identity_dir, draft_year=2025,
            reviewer_id="davidleess", evidence=None, note=None,
        )


def test_validate_bridge_graph_rejects_duplicate_prospect_uuid():
    e1 = _drafted_entry("cpr_aaa", "00-0001", 1)
    e2 = _drafted_entry("cpr_aaa", "00-0002", 5)  # SAME prospect_uuid, different gsis
    bridge = CollegeProspectBridge(entries=[e1, e2])
    errors = validate_bridge_graph(bridge)
    assert any("prospect_uuid" in e and "duplicate" in e.lower() for e in errors)


def test_validate_bridge_graph_rejects_duplicate_gsis_id():
    e1 = _drafted_entry("cpr_aaa", "00-0001", 1)
    e2 = _drafted_entry("cpr_bbb", "00-0001", 5)  # different prospect, SAME gsis
    bridge = CollegeProspectBridge(entries=[e1, e2])
    errors = validate_bridge_graph(bridge)
    assert any("gsis_id" in e and "duplicate" in e.lower() for e in errors)


# --- Round 2 patch 2 (Codex plan review): accepted vs procedural conflict semantics ---


def test_defer_then_confirm_succeeds(tmp_path: Path):
    """Spec §3.3: defer closes the row for THIS run; a future discovery run can
    re-open via a new review entry. A prior defer must NOT block later confirm."""
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()

    # First: defer the prospect_uuid
    defer_decision = PromotionDecision(kind="defer", prospect_uuid="cpr_aaa")
    promote_bridge_candidate(
        review_id=None, decision=defer_decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note="transfer pending",
    )

    # Then: confirm the same prospect_uuid (different discovery run) — must succeed
    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    confirm_decision = PromotionDecision(kind="confirm", entry=entry)
    result = promote_bridge_candidate(
        review_id=None, decision=confirm_decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note=None,
    )
    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert any(e.prospect_uuid == "cpr_aaa" for e in bridge.entries)


def test_reject_then_confirm_succeeds(tmp_path: Path):
    """Same as defer: reject for one review row doesn't block a later confirm
    from a future review run (a different match candidate succeeded)."""
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()

    reject_decision = PromotionDecision(kind="reject", prospect_uuid="cpr_aaa")
    promote_bridge_candidate(
        review_id=None, decision=reject_decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note="wrong match candidate",
    )

    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    confirm_decision = PromotionDecision(kind="confirm", entry=entry)
    result = promote_bridge_candidate(
        review_id=None, decision=confirm_decision,
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note=None,
    )
    assert result.exit_code == 0
    bridge = load_bridge(identity_dir / "prospect_to_nfl_bridge_2025.json")
    assert any(e.prospect_uuid == "cpr_aaa" for e in bridge.entries)


def test_confirm_then_different_accepted_decision_conflicts(tmp_path: Path):
    """Accepted-vs-accepted with different kinds is still a conflict (e.g.,
    confirm then udfa for the same prospect_uuid)."""
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()

    entry = _drafted_entry("cpr_aaa", "00-0001", 1)
    promote_bridge_candidate(
        review_id=None,
        decision=PromotionDecision(kind="confirm", entry=entry),
        identity_dir=identity_dir, draft_year=2025,
        reviewer_id="davidleess", evidence=None, note=None,
    )

    udfa_entry = ProspectNflBridgeEntry.model_validate({**_udfa_entry_kwargs(),
                                                        "prospect_uuid": "cpr_aaa"})
    with pytest.raises(BridgeConflictingDecisionError):
        promote_bridge_candidate(
            review_id=None,
            decision=PromotionDecision(kind="udfa", entry=udfa_entry),
            identity_dir=identity_dir, draft_year=2025,
            reviewer_id="davidleess", evidence="evidence", note=None,
        )
```

- [ ] **Step 2: Run RED check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_bridge.py -v 2>&1 | tail -15
```

Expected: ImportError on `PromotionDecision`, `promote_bridge_candidate`, `validate_bridge_graph`, etc.

- [ ] **Step 3: Claude implements GREEN — promotion lifecycle + graph validation**

Append to `src/dynasty_genius/identity/prospect_nfl_bridge.py`:

```python
# ======================================================================
# Promotion lifecycle (spec §3.3 stages ii–iii)
# ======================================================================

import uuid as _uuid
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class PromotionDecision:
    """Per spec §3.3: 4 decisions (confirm, udfa, reject, defer).
    confirm and udfa carry a populated `entry` (ProspectNflBridgeEntry sans
    auto-filled audit fields). reject and defer carry only `prospect_uuid`
    and an optional `note`."""

    kind: Literal["confirm", "udfa", "reject", "defer"]
    entry: Optional[ProspectNflBridgeEntry] = None
    prospect_uuid: Optional[str] = None


@dataclass(frozen=True)
class PromotionResult:
    exit_code: int
    event_id: Optional[str] = None


def validate_bridge_graph(bridge: CollegeProspectBridge) -> list[str]:
    """Cross-entry invariants (spec §3.2 rule 3): 1:1 within draft_year for
    prospect_uuid and non-null gsis_id."""
    errors: list[str] = []
    seen_uuids: set[str] = set()
    seen_gsis: set[str] = set()
    for entry in bridge.entries:
        if entry.prospect_uuid in seen_uuids:
            errors.append(
                f"duplicate prospect_uuid {entry.prospect_uuid} in bridge entries"
            )
        seen_uuids.add(entry.prospect_uuid)
        if entry.gsis_id is not None:
            if entry.gsis_id in seen_gsis:
                errors.append(
                    f"duplicate gsis_id {entry.gsis_id} in bridge entries"
                )
            seen_gsis.add(entry.gsis_id)
    return errors


def _close_review_queue_row(
    identity_dir: Path,
    draft_year: int,
    review_id: str,
    decision_kind: str,
    decided_at: str,
    event_id: str,
    note: Optional[str],
) -> None:
    """Spec §3.3 third leg of three-point logging."""
    for path in identity_dir.glob(f"prospect_nfl_review_queue_{draft_year}_*.jsonl"):
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
                if note is not None:
                    row["note"] = note
                changed = True
            updated.append(json.dumps(row, sort_keys=True))
        if changed:
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text("\n".join(updated) + "\n")
            os.replace(tmp, path)
            return


_ACCEPTED_DECISIONS: frozenset[str] = frozenset({"confirm", "udfa"})
_PROCEDURAL_DECISIONS: frozenset[str] = frozenset({"reject", "defer"})


def promote_bridge_candidate(
    *,
    review_id: Optional[str],
    decision: PromotionDecision,
    identity_dir: Path,
    draft_year: int,
    reviewer_id: str,
    evidence: Optional[str],
    note: Optional[str],
    s3_registry: Optional["CollegeProspectRegistry"] = None,
) -> PromotionResult:
    """Spec §3.3: the only blessed write path for bridge decisions. Three-point
    logging in dependency-safe order: decision_log → bridge_artifact → review_queue closure.

    Round 2 patch 1 (Codex plan review): for `confirm`/`udfa` decisions, an
    `s3_registry` MUST be supplied so spec §3.2 rules 1+2 can be validated
    (prospect_uuid confirmed in S3; draft_year == S3 draft_class). When the
    parameter is omitted for an accepted decision, the function returns
    exit_code=1; the CLI loads S3 and passes it through.

    Round 2 patch 2 (Codex plan review): conflict semantics differentiate
    ACCEPTED decisions (confirm, udfa — these alter the bridge) from
    PROCEDURAL decisions (reject, defer — these don't). A prior procedural
    decision does NOT block a later accepted decision (a future discovery
    run may re-surface the prospect with better evidence). A prior accepted
    decision DOES block any different accepted decision. Same-decision rerun
    is always idempotent.
    """
    if decision.kind == "udfa" and not (evidence and evidence.strip()):
        raise BridgeEvidenceRequiredError(
            "udfa promotion requires non-empty --evidence per spec §3.3"
        )

    identity_dir.mkdir(parents=True, exist_ok=True)
    bridge_path = identity_dir / f"prospect_to_nfl_bridge_{draft_year}.json"
    log_path = identity_dir / f"prospect_nfl_bridge_decision_log_{draft_year}.jsonl"

    # Determine the prospect_uuid being acted on
    if decision.kind in _ACCEPTED_DECISIONS:
        if decision.entry is None:
            return PromotionResult(exit_code=1)
        if s3_registry is None:
            return PromotionResult(exit_code=1)  # Round 2 patch 1: required for accepted
        acted_uuid = decision.entry.prospect_uuid
    else:  # reject / defer
        if decision.prospect_uuid is None:
            return PromotionResult(exit_code=1)
        acted_uuid = decision.prospect_uuid

    # Idempotency / conflict check — Round 2 patch 2 semantics
    existing_log = load_decision_log(log_path)
    for prior in existing_log:
        if prior.get("prospect_uuid") != acted_uuid:
            continue
        prior_kind = prior.get("decision")
        # Idempotent: identical decision is a no-op
        if prior_kind == decision.kind:
            return PromotionResult(exit_code=0, event_id=prior.get("event_id"))
        # Procedural prior never blocks (later run may bring better evidence)
        if prior_kind in _PROCEDURAL_DECISIONS:
            continue
        # Accepted prior + different new decision → conflict
        # (covers accepted → different accepted AND accepted → procedural which
        # is meaningless because the bridge entry already exists)
        if prior_kind in _ACCEPTED_DECISIONS:
            raise BridgeConflictingDecisionError(
                f"prospect_uuid {acted_uuid} already has accepted decision="
                f"{prior_kind!r}; refusing to apply {decision.kind}"
            )

    decided_at = _now_iso()
    event_id = f"ev_{_uuid.uuid4()}"

    # Build event for log
    event: dict[str, Any] = {
        "event_id": event_id,
        "decision": decision.kind,
        "prospect_uuid": acted_uuid,
        "decided_at": decided_at,
        "reviewer_id": reviewer_id,
        "evidence": evidence,
        "note": note,
    }

    bridge = load_bridge(bridge_path)

    if decision.kind in _ACCEPTED_DECISIONS:
        # Build the persistent entry with auto-filled audit fields
        entry_dict = decision.entry.model_dump()
        entry_dict["event_id"] = event_id
        entry_dict["decided_at"] = decided_at
        entry_dict["reviewer_id"] = reviewer_id
        if note is not None:
            entry_dict["note"] = note
        final_entry = ProspectNflBridgeEntry.model_validate(entry_dict)

        # Round 2 patch 1: S3 confirmed + draft_year validation (spec §3.2 rules 1+2)
        s3_errors = validate_against_s3(final_entry, s3_registry=s3_registry)
        if s3_errors:
            raise BridgeValidationError("; ".join(s3_errors))

        # Per-entry shape validation
        per_errors = validate_bridge_entry(final_entry)
        if per_errors:
            raise BridgeValidationError("; ".join(per_errors))

        bridge.entries.append(final_entry)

        # Cross-entry validation
        graph_errors = validate_bridge_graph(bridge)
        if graph_errors:
            raise BridgeValidationError("; ".join(graph_errors))

        event["entry"] = final_entry.model_dump(mode="json")

    # Dependency-safe per-file atomic write order
    existing_log.append(event)
    atomic_write_decision_log(existing_log, log_path)
    if decision.kind in _ACCEPTED_DECISIONS:
        atomic_write_bridge(bridge, bridge_path)
    if review_id:
        _close_review_queue_row(
            identity_dir, draft_year, review_id, decision.kind, decided_at, event_id, note
        )

    return PromotionResult(exit_code=0, event_id=event_id)
```

Now create the two CLI scripts. First `scripts/promote_bridge_candidate.py`:

```python
"""Subsystem 4 — bridge promotion CLI (the only blessed write path).

Usage:
    .venv/bin/python3.14 scripts/promote_bridge_candidate.py \\
        --identity-dir app/data/identity --draft-year 2025 \\
        --decision confirm --review-id rev_1 \\
        --prospect-uuid cpr_... --gsis-id 00-0001 --pfr-id ManningArch01 \\
        --draft-pick-no 1 --draft-round 1 --nfl-team CAR \\
        --evidence "..." --reviewer davidleess

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md §3.3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.dynasty_genius.identity.prospect_nfl_bridge import (
    PromotionDecision,
    ProspectNflBridgeEntry,
    promote_bridge_candidate,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote a bridge candidate (spec §3.3).")
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--draft-year", type=int, required=True)
    parser.add_argument("--decision", type=str, required=True,
                        choices=["confirm", "udfa", "reject", "defer"])
    parser.add_argument("--review-id", type=str, default=None)
    parser.add_argument("--prospect-uuid", type=str, required=True)

    # Confirm/UDFA entry fields
    parser.add_argument("--gsis-id", type=str, default=None)
    parser.add_argument("--pfr-id", type=str, default=None)
    parser.add_argument("--draft-pick-no", type=int, default=None)
    parser.add_argument("--draft-round", type=int, default=None)
    parser.add_argument("--nfl-team", type=str, default=None)

    # Provenance (required for confirm/udfa; passed through from a discovery run)
    parser.add_argument("--nflreadr-source", type=str, default="nflreadpy.draft_picks")
    parser.add_argument("--nflreadr-season", type=int, default=None)
    parser.add_argument("--draft-truth-content-hash", type=str, default="")
    parser.add_argument("--nflreadr-fetched-at", type=str, default="")

    parser.add_argument("--evidence", type=str, default=None)
    parser.add_argument("--note", type=str, default=None)
    parser.add_argument("--reviewer", type=str, default="davidleess")
    args = parser.parse_args(argv)

    decision_kind = args.decision
    s3_registry = None  # only loaded when needed
    if decision_kind in ("confirm", "udfa"):
        # Round 2 patch 1: load S3 for accepted-decision validation
        from src.dynasty_genius.identity.college_prospect_identity import load_registry
        s3_registry = load_registry(args.identity_dir / "college_prospect_registry.json")
        udfa = decision_kind == "udfa"
        entry = ProspectNflBridgeEntry.model_validate({
            "prospect_uuid": args.prospect_uuid,
            "gsis_id": args.gsis_id,
            "pfr_id": args.pfr_id,
            "draft_year": args.draft_year,
            "draft_pick_no": args.draft_pick_no,
            "draft_round": args.draft_round,
            "nfl_team": args.nfl_team,
            "udfa": udfa,
            "nflreadr_source": args.nflreadr_source,
            "nflreadr_season": args.nflreadr_season or args.draft_year,
            "draft_truth_content_hash": args.draft_truth_content_hash,
            "nflreadr_fetched_at": args.nflreadr_fetched_at,
            "evidence_snapshot": None,
            "event_id": "placeholder",  # overwritten in promote_bridge_candidate
            "decided_at": "placeholder",
            "reviewer_id": args.reviewer,
            "decision": "confirm" if not udfa else "udfa",
            "note": args.note,
        })
        decision = PromotionDecision(kind=decision_kind, entry=entry)
    else:
        decision = PromotionDecision(kind=decision_kind, prospect_uuid=args.prospect_uuid)

    result = promote_bridge_candidate(
        review_id=args.review_id, decision=decision,
        identity_dir=args.identity_dir, draft_year=args.draft_year,
        reviewer_id=args.reviewer, evidence=args.evidence, note=args.note,
        s3_registry=s3_registry,
    )
    print(f"exit_code={result.exit_code} event_id={result.event_id}", file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
```

And `scripts/build_prospect_nfl_bridge.py` — the discovery CLI (uses Task 3's surfacing):

```python
"""Subsystem 4 — bridge discovery CLI (per spec §3.3 stage i).

Usage:
    .venv/bin/python3.14 scripts/build_prospect_nfl_bridge.py \\
        --identity-dir app/data/identity --draft-year 2025 \\
        --run-id manual_2025_$(date -u +%Y%m%dT%H%MZ)
        [--nflreadr-fixture tests/fixtures/backtest_mock_draft/nflreadr_synthetic/2025_draft.json]

Reads S3 confirmed prospects for the draft_year; fetches nflreadr draft truth
(or loads a fixture for synthetic mode); writes per-run review queue,
unmatched UDFA candidates, and coverage matrix.

Spec: docs/superpowers/specs/2026-05-28-subsystem-4-backtest-harness-design.md §3.3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from src.dynasty_genius.identity.college_prospect_identity import load_registry
from src.dynasty_genius.identity.prospect_nfl_bridge import (
    NflTruthRow,
    surface_nfl_bridge_candidates,
)


def _load_nflreadr_draft_truth(draft_year: int, fixture_path: Path | None) -> list[NflTruthRow]:
    if fixture_path is not None:
        raw = json.loads(fixture_path.read_text())
        return [NflTruthRow.model_validate(r) for r in raw["rows"]]
    # Real nflreadr fetch
    try:
        import nflreadpy
        df = nflreadpy.load_draft_picks(seasons=[draft_year])
        rows = []
        for row in df.iter_rows(named=True):
            rows.append(NflTruthRow(
                gsis_id=row.get("gsis_id", "") or "",
                pfr_id=row.get("pfr_id"),
                full_name=row.get("pfr_player_name") or row.get("full_name") or "",
                normalized_name=(row.get("pfr_player_name") or "").lower(),
                position=row.get("position", ""),
                college=row.get("college"),
                draft_year=draft_year,
                draft_pick_no=int(row.get("pick", 0)),
                draft_round=int(row.get("round", 0)),
                nfl_team=row.get("team", ""),
                fetched_at=__import__("datetime").datetime.utcnow().isoformat() + "Z",
            ))
        return rows
    except Exception as e:
        print(f"nflreadr fetch failed: {e}", file=sys.stderr)
        return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build prospect↔NFL bridge discovery output (spec §3.3 stage i).")
    parser.add_argument("--identity-dir", type=Path, required=True)
    parser.add_argument("--draft-year", type=int, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--nflreadr-fixture", type=Path, default=None,
                        help="Optional fixture path for synthetic mode")
    args = parser.parse_args(argv)

    args.identity_dir.mkdir(parents=True, exist_ok=True)

    # Load S3 confirmed prospects for this class
    s3_registry_path = args.identity_dir / "college_prospect_registry.json"
    s3_registry = load_registry(s3_registry_path)
    s3_prospects = [
        e for e in s3_registry.entries.values()
        if e.draft_class == args.draft_year and e.verification_status == "confirmed"
    ]

    # Fetch nflreadr truth
    nfl_rows = _load_nflreadr_draft_truth(args.draft_year, args.nflreadr_fixture)
    truth_content_hash = hashlib.sha256(
        json.dumps([r.model_dump() for r in nfl_rows], sort_keys=True).encode()
    ).hexdigest()

    # Build review queue + UDFA candidates
    review_entries: list[dict] = []
    udfa_candidates: list[dict] = []
    matched_uuids: set[str] = set()
    for prospect in s3_prospects:
        candidates = surface_nfl_bridge_candidates(prospect, nfl_rows)
        if candidates:
            matched_uuids.add(prospect.prospect_uuid)
            for cand in candidates:
                review_entries.append({
                    "run_id": args.run_id,
                    "review_id": f"{args.run_id}_review_{len(review_entries)+1:04d}",
                    "prospect_uuid": prospect.prospect_uuid,
                    "gsis_id": cand.gsis_id,
                    "match_score": cand.match_score,
                    "score_breakdown": cand.score_breakdown,
                    "risk_flags": list(cand.risk_flags),
                    "nfl_truth_row": cand.nfl_truth_row,
                    "draft_truth_content_hash": truth_content_hash,
                    "decided_at": None, "decision": None, "event_id": None,
                })
        else:
            udfa_candidates.append({
                "run_id": args.run_id,
                "prospect_uuid": prospect.prospect_uuid,
                "normalized_name": prospect.normalized_name,
                "position": prospect.position,
                "current_school": prospect.current_school,
                "draft_truth_content_hash": truth_content_hash,
            })

    # Round 2 patch 6 (Codex plan review): atomic writes for discovery per-run
    # files via .tmp + os.replace, matching the bridge atomic-write discipline.
    import os as _os

    def _atomic_write_text(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content)
        _os.replace(tmp, path)

    review_path = args.identity_dir / f"prospect_nfl_review_queue_{args.draft_year}_{args.run_id}.jsonl"
    _atomic_write_text(
        review_path,
        "\n".join(json.dumps(e, sort_keys=True) for e in review_entries)
        + ("\n" if review_entries else ""),
    )

    udfa_path = args.identity_dir / f"prospect_nfl_unmatched_udfa_candidates_{args.draft_year}_{args.run_id}.jsonl"
    _atomic_write_text(
        udfa_path,
        "\n".join(json.dumps(e, sort_keys=True) for e in udfa_candidates)
        + ("\n" if udfa_candidates else ""),
    )

    coverage_path = args.identity_dir / f"prospect_nfl_coverage_{args.draft_year}_{args.run_id}.json"
    coverage = {
        "draft_year": args.draft_year,
        "run_id": args.run_id,
        "total_s3_confirmed_prospects": len(s3_prospects),
        "total_nfl_truth_rows": len(nfl_rows),
        "prospects_with_candidates": len(matched_uuids),
        "prospects_unmatched_as_udfa": len(udfa_candidates),
        "draft_truth_content_hash": truth_content_hash,
    }
    _atomic_write_text(coverage_path, json.dumps(coverage, indent=2, sort_keys=True))

    print(f"run_id={args.run_id} review_entries={len(review_entries)} udfa_candidates={len(udfa_candidates)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run GREEN check**

```bash
.venv/bin/python3.14 -m pytest tests/contract/test_subsystem_4_bridge.py tests/contract/test_subsystem_4_schema.py -v
```

Expected: all bridge + schema tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dynasty_genius/identity/prospect_nfl_bridge.py scripts/build_prospect_nfl_bridge.py scripts/promote_bridge_candidate.py tests/contract/test_subsystem_4_bridge.py
git commit -m "feat(subsystem-4): bridge promotion lifecycle + 2 CLI scripts (build + promote)"
```

---

## Tasks 5–14 follow the same Codex-RED-then-Claude-GREEN pattern

> **For brevity, Tasks 5–14 are structured below with their RED test specifications and GREEN implementation outlines. Each task follows the same 5-step pattern: Codex authors RED test file → run RED check → Claude implements GREEN → run GREEN check → commit. The agentic worker should expand each task into the same level of inline-code detail as Tasks 0–4 when implementing.**

### Task 5: Snapshot schema + canonical content_hash — §4.1

**Files:** Create `src/dynasty_genius/eval/backtest_mock_draft.py` (new module skeleton) + `tests/contract/test_subsystem_4_ingestion.py` (initial).

**RED test coverage:**
- `MockSnapshotPick`, `MockSnapshotMetadata`, `MockSnapshot` Pydantic round-trip
- `extra="forbid"` blocks unknown fields
- `parse_status` Literal rejects other strings
- `compute_canonical_content_hash(picks)` deterministic across pick-order shuffling
- `derive_snapshot_id(metadata)` deterministic + path-independent

**GREEN impl outline:**
- Pydantic models exactly per spec §4.1
- `compute_canonical_content_hash(picks)`: sort by `pick_no` ascending, JSON-serialize each with `sort_keys=True`, concatenate, SHA-256
- `derive_snapshot_id(metadata)`: SHA-256 of pipe-joined `(source_label, analyst, published_date, mock_version, content_hash)`

**Commit:** `feat(subsystem-4): snapshot schema + canonical content_hash + section 4.1 tests`

### Task 6: Snapshot ingestion + coverage matrix — §4.3 rules 1–4, 6–8 + §4.5

**RED test coverage (from §6.2 contract paths 1, 5, 6, 11, 12):**
- Schema validation rejects unknown fields
- Leakage gate: `published_date == draft_date` and `> draft_date` excluded; `< draft_date` included
- Identity validation: `ConfirmedProspectUuid` required at run time; `deprecated` with valid `merged_into` survivor → follow redirect with per-pick `redirect_applied=True` flag; deprecated → non-confirmed → exclude pick; unknown → exclude + increment `unresolved_picks`
- Cross-snapshot content_hash: same tuple-key + same hash → idempotent; same tuple-key + different hash → reject + `content_hash_collision_warning`
- Within-snapshot duplicates: duplicate `pick_no` → reject snapshot; duplicate `prospect_uuid` → reject snapshot
- Coverage matrix fields all populated correctly

**GREEN impl outline:**
- `ingest_snapshots(snapshots_dir, s3_registry, draft_date, *, include_untrusted=False)` returns `(normalized_picks, coverage_matrix)`
- Normalized pick struct includes per-pick `redirect_applied`, `original_prospect_uuid`, `resolved_prospect_uuid`
- Coverage matrix per spec §4.5 exact field list

**Commit:** `feat(subsystem-4): snapshot ingestion + coverage matrix + section 4.3 + 4.5`

### Task 7: parse_status + duplicates + draft_date sourcing — §4.3 rule 5 + §4.6

**RED test coverage (from §6.2 contract paths 4, 13):**
- `parse_status="complete"` included normally
- `parse_status="partial"` included with `partial_snapshot_warning` (per-snapshot pick_count preserved)
- `parse_status="untrusted"` excluded by default; included only with `include_untrusted=True`
- `draft_date_used + draft_date_source` populated from nflreadr by default
- `--override-draft-date YYYY-MM-DD --override-reason "..."` both required when override; CLI rejects either alone

**GREEN impl outline:**
- Extend ingestion to handle `parse_status` per rule 5
- `resolve_draft_date(draft_year, *, override_date=None, override_reason=None)` returns `(date, source)` tuple; raises if exactly one override field set
- Coverage matrix `draft_date_used` + `draft_date_source` fields populated

**Commit:** `feat(subsystem-4): parse_status behavior + draft_date sourcing with audited override`

### Task 8: ProspectConsensus aggregation + abstention tiers — §5.2, §5.3

**RED test coverage:**
- ProspectConsensus Pydantic shape
- `n_sources` counted by distinct `source_label`; `n_unique_analysts` by distinct `analyst`
- `abstention_tier`: `n_sources < 3` → `abstain`; `3 ≤ n_sources ≤ 4` → `round_tier_only`; `n_sources ≥ 5` with `IQR ≤ 6` → `exact_pick`; otherwise `round_tier_only`
- `staleness_days` computed from most-recent snapshot's `published_date` to `draft_date`
- `dispersion_threshold` configurable + recorded in artifact metadata
- Empty snapshots → abstain
- All abstention reasons populated

**GREEN impl outline:**
- `aggregate_per_prospect(normalized_picks, draft_date, dispersion_threshold=6)` returns `dict[prospect_uuid, ProspectConsensus]`
- Median pick, IQR, min, max computed per prospect; counts distinct sources/analysts
- Abstention tier logic exactly per §5.3

**Commit:** `feat(subsystem-4): ProspectConsensus aggregation + abstention tiers section 5.2 + 5.3`

### Task 9: Bridge join + RealizedOutcome + bridge_stale_warning — §5.1 stage 3

**RED test coverage:**
- `RealizedOutcome` Pydantic shape
- Bridge join produces matched `RealizedOutcome` for prospects in bridge
- Prospects NOT in bridge → `RealizedOutcome(udfa=True, ...)` only if bridge has explicit udfa entry; otherwise skipped from metric computation with `unbridged_prospect` flag
- `bridge_stale_warning` fires when current nflreadr fetch differs from `evidence_snapshot.fetched_at` data (deterministic check on `(full_name, position, draft_pick_no, nfl_team)`)
- Snapshot files never mutated by the join

**GREEN impl outline:**
- `join_bridge_to_realized(consensuses, bridge, nflreadr_current)` returns `list[(consensus, realized_outcome)]`
- Stale warning emitted as a list of strings + flags on per-prospect outcomes

**Commit:** `feat(subsystem-4): bridge join + bridge_stale_warning section 5.1 stage 3`

### Task 10: The 6 metrics — §5.4

**RED test coverage (from §6.2 contract path 1; spec §5.4 universes):**
- `overall_pick_mae`: drafted-and-projected-drafted intersection only; deterministic golden-answer fixture
- `round_bucket_accuracy`: excludes `abstain` tier; round-bucket mapping per spec §5.4 footer
- `top_36_skill_recall`: denominator = `min(36, realized_top_36_in_bridge_count)`; emits `insufficient_truth_coverage` if < 36
- `udfa_false_positive_rate`: denominator = `projected_drafted` only; abstained NOT counted as projected UDFA
- `coverage_after_abstention`: `n_scored / n_prospects_total_in_class` (S3 confirmed universe)
- `early_pick_weighted_error`: `weight = 1/realized_pick_no` exactly; `metric_version` recorded
- Per-bucket breakdown populated correctly

**GREEN impl outline:**
- `compute_metrics(joined_outcomes, n_prospects_total_in_class, bridge)` returns metrics dict + per-bucket breakdown + warnings list
- Round buckets exactly: `R1-early (1-10), R1-mid (11-21), R1-late (22-32), R2 (33-64), R3 (65-105), Day3 (R4-7), UDFA`
- Each metric universe enforced per spec §5.4 table

**Commit:** `feat(subsystem-4): 6 metrics with explicit universes section 5.4`

### Task 11: backtest_b_gate_status + synthetic safety hedge + two-tier — §5.5, §5.6, §5.7

**RED test coverage (from §6.2 contract paths 8, 9):**
- Per-bucket pass/fail using v1 candidate thresholds (R1-early: MAE ≤ 8, coverage ≥ 0.8; etc.)
- `R3 + Day3` always abstain regardless of metrics
- Synthetic data mode (detected by `draft_date_source.startswith("override:")` OR explicit `data_mode="synthetic"`) forces `overall_status="always_abstain_synthetic_data"`
- Per-bucket entries on synthetic runs have `gate_result="not_evaluable_synthetic"` (schema-shape preserved)
- Two-tier threshold documented; v1 evidence requires bridge top-36 ≥ 0.90; B's actual gating requires 1.00 per-bucket truth coverage (asserted in spec doc string + contract test that B-gate function records both tiers)

**GREEN impl outline:**
- `evaluate_b_gate(metrics, per_bucket_breakdown, *, data_mode, draft_date_source)` returns gate status structure per spec §5.9
- Synthetic safety hedge applied BEFORE per-bucket evaluation
- Two-tier thresholds recorded in returned structure for future B implementation

**Commit:** `feat(subsystem-4): backtest_b_gate_status + synthetic hedge + two-tier section 5.5 to 5.7`

### Task 12: Artifact writer + run_backtest_a.py CLI — §5.9

**RED test coverage:**
- Artifact written at `app/data/backtest/mock_draft/runs/<run_id>/backtest_a_result.json`
- Schema exactly per spec §5.9 (metadata, coverage, metrics, abstention_summary, backtest_b_gate_status, warnings)
- All versioning fields populated (`metric_version`, `aggregation_version`, `gate_version`)
- `data_mode` field correct (real vs synthetic)
- CLI accepts required flags: `--snapshots-dir`, `--identity-dir`, `--draft-year`, `--run-id`, optional `--override-draft-date`+`--override-reason`, `--include-untrusted`, `--dispersion-threshold`
- CLI returns exit_code 0 on success; non-zero on schema/ingestion errors

**GREEN impl outline:**
- `run_backtest_a(...)` orchestrates 6-stage pipeline → returns `BacktestAResult` model
- `write_backtest_a_artifact(result, path)` serializes JSON per §5.9
- CLI script wraps `run_backtest_a` with argparse + exit code handling

**Commit:** `feat(subsystem-4): Backtest A artifact writer + run_backtest_a.py CLI`

### Task 13: B-shaped stub + run_backtest_b.py CLI — §6.1

**RED test coverage:**
- `run_backtest_b()` library function returns structured abstain dict with all 6 fields (`status`, `reason`, `required_gate`, `upstream_run_id`, `decision_supported=False`, `exit_code=0`)
- CLI accepts same flags as A for UX symmetry
- Stub writes only `backtest_b_abstain.json` (verified by monkeypatching `open()` and counting writes — no other B-related I/O)
- `test_backtest_b_remains_abstained_in_v1` asserts the abstain behavior is locked (test that future agents must explicitly flip)

**GREEN impl outline:**
- `run_backtest_b(upstream_run_id=None) -> dict` returns the structured abstain
- CLI script writes the abstain report file + prints exit_code 0

**Commit:** `feat(subsystem-4): B-shaped always-abstain stub + run_backtest_b.py CLI`

### Task 14: Audit tests + AGENT_SYNC + ledger closeout — §6.3, §8.8, governance

**RED test coverage (§8.8) — Round 2 patches 4 + 5 applied:**
- S3 inviolate artifacts byte-unchanged via SHA-256 contract test (extends S3's pre-existing inviolate set; adds S3-merged committed artifacts)
- **Round 2 patch 4**: Mock-data isolation rule per spec §7:
  - NO mock/ADP/market field names in `prospect_nfl_bridge.py` (identity infrastructure must stay mock-free)
  - NO ADP/market field names in any S4 schema or output across both modules (mock-derived diagnostic data is allowed; market data is barred)
  - Mock fields ARE allowed in `backtest_mock_draft.py` for `MockSnapshot`, `MockSnapshotPick`, `MockSnapshotMetadata`, and Backtest A run artifacts — these are isolated diagnostic surfaces per spec §7
- No banned David-facing language in any S4 output string (verdict/tier/grade/action — match patterns from S3 audit test)
- `decision_supported=False` recursively absent or False on all S4 surfaces (B stub structured field; any output schema that has a `decision_supported` field)
- **Round 2 patch 5**: Coverage matrix counts reconcile across ALL §4.5 rejection buckets:
  `snapshots_used + leakage_excluded_snapshots + untrusted_excluded_snapshots + duplicate_pick_no_rejections + duplicate_prospect_uuid_rejections + content_hash_collisions == total_snapshots_found`
- Acceptance criteria from §6.3 documented in spec + `acceptance_criteria_failed` list emission tested

**GREEN: no impl needed if Tasks 1–13 implemented correctly.** Tests pass on the existing surfaces.

After tests green, do **closeout steps**:
- Run `.venv/bin/python3.14 -m pytest -q` → confirm full suite green (baseline 1376 + estimated +60-80 S4 tests = ~1440-1460 expected)
- Run `scripts/validate_governance.py` → confirm PASS
- Confirm inviolate paths byte-unchanged: `git diff --stat main -- <inviolate paths>` empty
- Update `AGENT_SYNC.md` Subsystem 4 entry (similar shape to S3's MERGED entry)
- Append postflight ledger entry to today's `docs/agent-ledger/YYYY-MM-DD.md` per the operating-loop format

**Commit (closeout):** `docs(subsystem-4): AGENT_SYNC + ledger closeout for S4 build`

Then push the branch:
```bash
git push origin feature/subsystem-4-backtest-harness
```

Then open a PR via `gh pr create` with an audit-trail-enriched body summarizing all 14+ commits + cockpit-decision history (mirror the S3 PR #55 pattern).

---

## Self-review (writing-plans skill checklist)

**1. Spec coverage:** Every spec section mapped to a task:
- §0 + §1 covered by spec context (Plan-level Choices + each Task header)
- §2 architecture covered by File Structure section
- §3.1 bridge schema → Task 1
- §3.2 validation rules 1-5 → Task 1; rule 6 (replay) → Task 2
- §3.3 stages i-iii → Tasks 3 and 4
- §4.1 snapshot schema → Task 5
- §4.3 ingestion contract rules 1-4, 6-8 → Task 6; rule 5 + §4.6 draft_date → Task 7
- §4.5 coverage matrix → Task 6
- §5.1 pipeline → assembled across Tasks 8-12
- §5.2 ProspectConsensus + §5.3 abstention → Task 8
- §5.4 metrics → Task 10
- §5.5 + §5.6 + §5.7 B-gate → Task 11
- §5.8 versioning → Task 12 (in artifact writer)
- §5.9 artifact → Task 12
- §6.1 B stub → Task 13
- §6.2 synthetic coverage matrix → embedded across Tasks 6, 7, 8, 10, 11
- §6.3 acceptance criteria → Task 14 (documented + tested for `acceptance_criteria_failed` emission)
- §6.4 testing → all task files
- §7 governance → Task 14 audit tests
- §8 testing detail → distributed across all tasks
- §10 counter-argument → spec-level; no task needed

**2. Placeholder scan:** No TBD/TODO/"fill in" patterns. Tasks 5-14 are intentionally outlined more briefly than 0-4 (consistent depth would balloon plan length); each carries explicit RED coverage list + GREEN impl outline + commit message.

**3. Type consistency:** Function/method names + parameter shapes consistent across tasks:
- `ProspectNflBridgeEntry`, `CollegeProspectBridge`, `PromotionDecision`, `PromotionResult`
- `NflTruthRow`, `NflBridgeCandidate`, `ProspectConsensus`, `RealizedOutcome`
- `validate_bridge_entry`, `validate_bridge_graph`
- `load_bridge`, `atomic_write_bridge`, `load_decision_log`, `atomic_write_decision_log`, `apply_decision_event`, `replay_decision_log`
- `score_nfl_candidate`, `surface_nfl_bridge_candidates`, `is_nfl_position_pair_compatible`
- `promote_bridge_candidate`, `_close_review_queue_row`
- `compute_canonical_content_hash`, `derive_snapshot_id`
- `MockSnapshotPick`, `MockSnapshotMetadata`, `MockSnapshot`
- `ingest_snapshots`, `aggregate_per_prospect`, `join_bridge_to_realized`, `compute_metrics`, `evaluate_b_gate`
- `run_backtest_a`, `run_backtest_b`, `write_backtest_a_artifact`
- Constants: `BRIDGE_SCHEMA_VERSION`, `NFL_DOMAIN_MATCHER_VERSION`, `NFL_POSITION_WHITELIST`

**4. Cross-task ordering:** Task 0 (branch) → Task 1 (schema) → Task 2 (atomic + replay) → Task 3 (discovery scoring) → Task 4 (promotion + CLIs) → Task 5 (snapshot schema) → Task 6 (ingestion) → Task 7 (parse_status + draft_date) → Task 8 (aggregation) → Task 9 (join) → Task 10 (metrics) → Task 11 (B-gate) → Task 12 (A artifact + CLI) → Task 13 (B stub + CLI) → Task 14 (audit + closeout). No back-references to undefined symbols.

---

## Cockpit review gate (binding before execution)

Per `[[reference_review_workflow]]` and the standing cockpit directive: this plan does not get executed until Codex has independently read it and the cockpit converges (Gemini's CLI session was broken during S4 brainstorming so its plan review may not be obtainable; if Gemini recovers, route to it; otherwise proceed with Codex's binding technical CLEAR + Claude independent governance attestation, mirroring the S4 spec gate pattern). After convergence, David authorizes the execution skill (`superpowers:subagent-driven-development` recommended for fresh-subagent-per-task isolation, or `superpowers:executing-plans` for inline batch with checkpoints).

Ledger entries during execution follow the format in `02-agent-operating-loop.md` §"Daily Ledger Format" — one entry per task or per cockpit checkpoint, whichever is more useful for traceability.
