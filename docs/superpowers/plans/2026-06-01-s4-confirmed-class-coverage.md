# S4 Confirmed-Class Coverage Activation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: cockpit-TDD (Codex RED → Claude GREEN → dual CLEAR → commit → loop-closed) per `docs/governance/02-agent-operating-loop.md`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Activate the S4 §11.2 selection-bias gate's two dormant arms by computing the real `confirmed_class_unbridged_count` + `orphan_bridges_detected` (+ an actionable `confirmed_class_unbridged_uuids` listing) from the S3 confirmed-class universe vs the per-class bridge.

**Architecture:** A focused helper `_confirmed_class_selection_bias(s3_registry, bridge, draft_year)` performs the registry-vs-bridge analysis; `_compute_bridge_coverage` composes it into the coverage dict. `run_backtest_a` passes the already-loaded `s3_registry`/`bridge`/`draft_year`. The existing `evaluate_bridge_gates` hard-block (metrics→null) is unchanged — this only supplies its real inputs. Tighten-only; `decision_supported` untouched.

**Tech Stack:** Python 3.14, `.venv/bin/python3.14 -m pytest`, pydantic v2, ruff (`E4 E7 E9 F I`). Contract: foundational S4 spec §11.2 + §11.2a amendment (2026-06-01).

**Terminology guard:** do NOT use the word "edge" on word boundaries anywhere in code/tests/docstrings (governance).

---

## Task 1: `_confirmed_class_selection_bias` helper + `_compute_bridge_coverage` extension

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_mock_draft.py` (`_compute_bridge_coverage` ~L1370; add the helper above it)
- Test: `tests/contract/test_subsystem_4_runner.py` (or a focused coverage test) — Codex authors RED

- [ ] **Step 1 (RED, Codex):** assert the helper + extended coverage contract. `_compute_bridge_coverage(joined_outcomes, *, s3_registry, bridge, draft_year)` returns a dict whose `consensus_unbridged_count` is unchanged AND adds:
  (a) `confirmed_class_unbridged_count: int` + `confirmed_class_unbridged_uuids: list[str]` (sorted) — confirmed S3 prospects of `draft_year` (`verification_status=="confirmed"`, `draft_class==draft_year`) whose uuid is not in `bridged_uuids`; `bridged_uuids` counts ONLY entries with `entry.draft_year == draft_year`.
  (b) `orphan_bridges_detected: list[{"prospect_uuid": str, "reason": str}]`, deduped by `prospect_uuid`, reason by first-match order: `bridge_wrong_draft_year` (`entry.draft_year != draft_year`) → `not_in_registry` → `not_confirmed` → `wrong_draft_class` (`registry entry.draft_class != draft_year`).
  (c) Cases: matched universe (every confirmed prospect has a run-year confirm/udfa entry, every entry resolves) → count 0, uuids `[]`, orphans `[]`. One confirmed prospect with no entry → count 1 + its uuid listed. A `udfa`-decision entry counts as bridged (not unbridged). One entry per orphan reason → the right reason. A wrong-year entry for a confirmed prospect → that prospect still `unbridged` (wrong-year entry excluded from `bridged_uuids`) AND the entry appears as `bridge_wrong_draft_year` orphan. Empty registry + non-empty bridge → all entries orphans. Empty registry + empty bridge → does NOT block (no input-presence gate in this increment). Duplicate uuid entries collapse/dedupe. **`orphan_bridges_detected` is sorted by `prospect_uuid`** (assert deterministic order independent of `bridge.entries` order).
- [ ] **Step 2:** run → fail (helper missing / signature mismatch / defaulted `0`/`[]`).
- [ ] **Step 3 (GREEN, Claude):** implement:

```python
_OrphanReason = str  # "bridge_wrong_draft_year" | "not_in_registry" | "not_confirmed" | "wrong_draft_class"


def _confirmed_class_selection_bias(
    s3_registry: CollegeProspectRegistry,
    bridge: CollegeProspectBridge,
    draft_year: int,
) -> dict:
    """§11.2a registry-vs-bridge selection-bias analysis (fail-closed, no defaults)."""
    confirmed_class = {
        e.prospect_uuid: e
        for e in s3_registry.entries.values()
        if e.draft_class == draft_year and e.verification_status == "confirmed"
    }
    bridged_uuids = {
        entry.prospect_uuid
        for entry in bridge.entries
        if entry.draft_year == draft_year
    }
    unbridged = sorted(set(confirmed_class) - bridged_uuids)

    orphans: dict[str, _OrphanReason] = {}
    for entry in bridge.entries:
        if entry.prospect_uuid in orphans:
            continue  # dedupe by prospect_uuid (first/most-specific reason wins)
        if entry.draft_year != draft_year:
            orphans[entry.prospect_uuid] = "bridge_wrong_draft_year"
        elif entry.prospect_uuid not in s3_registry.entries:
            orphans[entry.prospect_uuid] = "not_in_registry"
        elif s3_registry.entries[entry.prospect_uuid].verification_status != "confirmed":
            orphans[entry.prospect_uuid] = "not_confirmed"
        elif s3_registry.entries[entry.prospect_uuid].draft_class != draft_year:
            orphans[entry.prospect_uuid] = "wrong_draft_class"
        # else: valid bridge entry — not an orphan

    return {
        "confirmed_class_unbridged_count": len(unbridged),
        "confirmed_class_unbridged_uuids": unbridged,
        "orphan_bridges_detected": [
            {"prospect_uuid": uuid, "reason": orphans[uuid]}
            for uuid in sorted(orphans)  # deterministic, entry-order-independent output
        ],
    }
```

  Then extend `_compute_bridge_coverage` to accept `*, s3_registry, bridge, draft_year` and merge the helper's three keys alongside the existing `consensus_unbridged_count` (drop the defaulted `confirmed_class_unbridged_count: 0` / `orphan_bridges_detected: []`). `CollegeProspectRegistry` is already imported (verify; add if not).
- [ ] **Step 4:** focused pass; `.venv/bin/ruff check src/dynasty_genius/eval/backtest_mock_draft.py` clean (no "edge"/"mock"/"adp" substring introduced).
- [ ] **Step 5:** commit `feat(s4): confirmed-class selection-bias coverage helper (§11.2a)`.

## Task 2: Wire `run_backtest_a` call-site + thread fields into the artifact + reconcile fixtures

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_mock_draft.py` (`run_backtest_a` `_compute_bridge_coverage(pairs)` call ~L1496)
- Test: `tests/contract/test_subsystem_4_runner.py` (integration REDs + blast-radius fixture reconciliation) — Codex authors RED

- [ ] **Step 1 (RED, Codex):** integration assertions on `run_backtest_a` (no public-signature change):
  (a) matched universe (existing happy-path fixtures, reconciled so confirmed-class == bridged) → `acceptance_criteria_failed` excludes `confirmed_class_unbridged`/`orphan_bridges_detected`; `metrics` non-null; coverage carries `confirmed_class_unbridged_count==0`, `confirmed_class_unbridged_uuids==[]`, `orphan_bridges_detected==[]`, serialized into `backtest_a_result.json`.
  (b) a confirmed prospect missing from the bridge → `acceptance_criteria_failed` contains `confirmed_class_unbridged`; `metrics is None`; the prospect's uuid in `confirmed_class_unbridged_uuids` (in the artifact).
  (c) an orphan bridge entry (one test per reason: `bridge_wrong_draft_year`, `not_in_registry`, `not_confirmed`, `wrong_draft_class`) → `acceptance_criteria_failed` contains `orphan_bridges_detected`; `metrics is None`; `orphan_bridges_detected` carries `{prospect_uuid, reason}`.
- [ ] **Step 2:** run → fail (call-site still passes only `pairs`; existing happy-path fixtures AND the old-orphan-shape tests now break — that is the blast radius, surfaced RED).
- [ ] **Step 3 (GREEN, Claude):** change the call-site to `_compute_bridge_coverage(pairs, s3_registry=s3_registry, bridge=bridge, draft_year=draft_year)` (all in scope at L1459-1460). **Blast-radius reconciliation (two classes — do NOT weaken assertions):**
  - **(i) metrics-producing fixtures** — `_write_runner_inputs_with_bridge_entries`, `_write_real_mode_e2e_runner_inputs`, and any minimal-input helper feeding a `metrics not None` assertion: add confirmed S3 registry entries (matching `draft_class==draft_year` + `prospect_uuid` + `verification_status="confirmed"`) for each run-year bridge entry, and ensure no extra confirmed prospect is left unbridged, so the universe is complete (zero unbridged/orphan) and those tests stay metrics-producing.
  - **(ii) old `list[str]` orphan-shape tests** — any test/helper that blesses the superseded bare-uuid shape must move to the new `list[{prospect_uuid, reason}]` shape: at minimum `tests/contract/test_subsystem_4_audit.py::test_artifact_emits_three_segmented_unbridged_counts` (asserts `orphan_bridges_detected == [UUID_A]`) and any metrics/runner helper that injects `orphan_bridges_detected=[UUID_A]` into a `bridge_coverage` override. Update them to assert/inject `[{"prospect_uuid": UUID_A, "reason": <reason>}]` (or otherwise assert the dict-row shape). Grep `orphan_bridges_detected` across `tests/` to enumerate every site before editing.
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4): activate confirmed-class/orphan selection-bias gate in run_backtest_a (§11.2a)`.

## Task 3: Audit + full-suite + ruff green (verification)

**Files:** none new (verification task).

- [ ] **Step 1:** `tests/contract/test_subsystem_4_audit.py` green (no allowlist/byte-lock/import-wall regression; no "mock"/"adp"/"edge" introduced).
- [ ] **Step 2:** full project suite `.venv/bin/python3.14 -m pytest -q` green; `.venv/bin/ruff check src app scripts` shows no NEW errors vs the pre-existing 45 E712 (untouched Engine A/B scripts).
- [ ] **Step 3:** if anything fails, fix RED-first (do NOT weaken the gate or the §11.2 caveat). Commit only if a fix was needed.

---

## Self-Review

**Spec coverage:** §11.2a inputs/threading → T1/T2; confirmed-class universe + run-year `bridged_uuids` → T1(a); actionable `confirmed_class_unbridged_uuids` → T1(a)/T2(b); 4 ordered orphan reasons incl. `bridge_wrong_draft_year` → T1(b)/T2(c); dedupe-by-uuid + duplicate scope decision → T1; fail-closed empty-registry → T1; gate-unchanged + artifact serialization → T2; blast-radius fixture reconciliation → T2(Step3). §11.2 caveat/`metric_universe` unchanged (not touched).

**Placeholder scan:** no TBD/TODO. Full RED bodies are Codex-authored per cockpit workflow; each task pins the binding assertions.

**Type/name consistency:** `_confirmed_class_selection_bias`, `confirmed_class_unbridged_count`, `confirmed_class_unbridged_uuids`, `orphan_bridges_detected`, reasons `{bridge_wrong_draft_year, not_in_registry, not_confirmed, wrong_draft_class}` used consistently; gate tokens (`confirmed_class_unbridged`, `orphan_bridges_detected`) match `evaluate_bridge_gates` (L816, unchanged).

**Scope:** single focused increment (one helper + one call-site + fixture reconciliation). Duplicate-entry gating explicitly OUT of scope (documented in §11.2a).
