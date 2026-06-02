# Backtest-A Input-Readiness Preflight — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: cockpit-TDD (Codex RED → Claude GREEN → dual CLEAR → commit → loop-closed). Steps use checkbox (`- [ ]`) syntax.

**Goal:** A diagnostic-only `preflight_backtest_a_inputs(...)` (+ CLI) that reports whether real-mode Backtest-A inputs are present/valid/aligned/free of statically-determinable §11.2 hard-blocks, naming what's missing — per foundational S4 spec **§11.2b**.

**Architecture:** New function in `eval/backtest_mock_draft.py` (existing allowlisted eval file) + a typed `BacktestAPreflightReport` model + a thin CLI `scripts/preflight_backtest_a.py`. Reuses `_find_bridge_artifact`/`load_bridge`/`load_registry`/`ingest_snapshots`/`_confirmed_class_selection_bias`. **Read-only** (no aggregate/join/metrics/write); checks **accumulate**, not fail-fast.

**Tech Stack:** Python 3.14, pytest, pydantic v2, ruff (`E4 E7 E9 F I`). NO `edge`/`mock`/`adp` on word boundaries. `decision_supported` untouched.

---

## Task 1: `BacktestAPreflightReport` + `preflight_backtest_a_inputs`

**Files:**
- Modify: `src/dynasty_genius/eval/backtest_mock_draft.py`
- Test: `tests/contract/test_subsystem_4_preflight.py` (new) — Codex authors RED

- [ ] **Step 1 (RED, Codex):** assert the report model + the function contract:
  - **Model `BacktestAPreflightReport`** (pydantic BaseModel): `ready: bool`; `checks: list[<CheckRow>]` where each row is `{name: str, status: Literal["ok","blocked","not_checked"], detail: str}`; `blocking_reasons: list[str]`; `confirmed_class_unbridged_count: int`; `confirmed_class_unbridged_uuids: list[str]`; `orphan_bridges_detected: list[dict]`; `ingest_summary: {snapshot_files: int, schema_invalid: int, normalized_picks: int, draft_date_resolved: bool}` (`schema_invalid` from a per-file `MockSnapshot.model_validate` scan; `normalized_picks` = survivors from the dry ingest). **No decision-grade field** (no `decision_supported`/`verdict`/`pass`).
  - **`ready` is True iff no check has status `blocked`.**
  - **Cases** (build minimal real inputs in a tmp dir — snapshots/identity registry+bridge via the existing runner-test fixture helpers' shapes):
    - fully-ready inputs → `ready=True`; presence/ingest/alignment/coverage checks `ok`; `output_collision` + `live_truth_source` = `not_checked`.
    - missing `snapshots_dir` → `blocked` + reason; missing OR **zero-byte** bridge artifact → `blocked`; missing OR **zero-byte** `college_prospect_registry.json` → `blocked` (explicit `Path.exists()`+size, before loaders).
    - snapshots present but ALL schema-invalid → per-file `MockSnapshot.model_validate` scan reports `schema_invalid==N`, dry ingest yields zero surviving normalized picks → ingest check `blocked` ("zero usable picks") [Codex pin 1].
    - no resolvable draft-date (no `override_draft_date`; ingestion returns the sentinel `draft_date_source=="no_snapshots"` / `draft_date_used=="9999-12-31"`) → `blocked` [Codex pin 2].
    - bridge `metadata.draft_year` mismatch OR registry has zero confirmed entries for `draft_year` → alignment `blocked`.
    - a confirmed prospect with no bridge entry → coverage `blocked`, `confirmed_class_unbridged_count==1` + uuid listed.
    - an orphan bridge entry → coverage `blocked`, `orphan_bridges_detected` carries `{prospect_uuid, reason}`.
    - `run_id`+`output_root` given AND the run's `backtest_a_result.json` already exists → `output_collision` `blocked`; neither given → `not_checked` [Codex pin 4].
    - `live_truth_source` is ALWAYS `not_checked` — assert a `ready` report still has the live-truth check `not_checked` (ready excludes the live fetch) [Codex pin 5].
    - **Read-only:** assert no files are written under `output_root`/identity/snapshots during preflight.
- [ ] **Step 2:** run → fail (symbols missing).
- [ ] **Step 3 (GREEN, Claude):** implement. Sketch:

```python
class BacktestAPreflightCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    status: Literal["ok", "blocked", "not_checked"]
    detail: str


class BacktestAPreflightReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ready: bool
    checks: list[BacktestAPreflightCheck]
    blocking_reasons: list[str]
    confirmed_class_unbridged_count: int
    confirmed_class_unbridged_uuids: list[str]
    orphan_bridges_detected: list[dict]
    ingest_summary: dict  # {snapshot_files, schema_invalid, normalized_picks, draft_date_resolved}


def preflight_backtest_a_inputs(
    snapshots_dir, identity_dir, draft_year, *,
    override_draft_date=None, include_untrusted=False, run_id=None, output_root=None,
) -> BacktestAPreflightReport:
    checks: list[BacktestAPreflightCheck] = []
    # 1. explicit presence (missing + zero-byte) via Path.exists()+stat().st_size
    # 2a. per-file schema scan: MockSnapshot.model_validate(json.loads(f)) -> schema_invalid count
    # 2b. dry read-only ingest_snapshots(..., include_untrusted=include_untrusted) -> normalized_picks, coverage;
    #     block if not normalized_picks (zero usable);
    #     block if coverage["draft_date_source"] == "no_snapshots" and override_draft_date is None
    # 3. load_registry/load_bridge; bridge.metadata draft_year + >=1 confirmed entry
    # 4. _confirmed_class_selection_bias(...) -> block on unbridged>0 / orphans
    # 5. output collision: not_checked unless run_id+output_root both given
    # 6. live_truth_source: always not_checked
    ...
    ready = all(c.status != "blocked" for c in checks)
    return BacktestAPreflightReport(ready=ready, checks=checks, ...)
```
  No writes anywhere. `ingest_snapshots` requires `s3_registry`+`draft_date`; pass the loaded registry + `override_draft_date` (None lets ingestion resolve; the `no_snapshots` sentinel signals unresolved). Reuse `_confirmed_class_selection_bias`.
- [ ] **Step 4:** focused pass; ruff clean; no `edge`/`mock`/`adp` substring.
- [ ] **Step 5:** commit `feat(s4): Backtest-A input-readiness preflight (§11.2b)`.

## Task 2: CLI `scripts/preflight_backtest_a.py`

**Files:** Create `scripts/preflight_backtest_a.py`; Test: extend `tests/contract/test_subsystem_4_preflight.py`.

- [ ] **Step 1 (RED, Codex):** CLI (argparse: `--snapshots-dir --identity-dir --draft-year [--override-draft-date --include-untrusted --run-id --output-root]`; `--include-untrusted` is a `store_true` flag passed through to `preflight_backtest_a_inputs(..., include_untrusted=…)` so the CLI mirrors the function/run trust posture) — invoking it (a) prints the VERBATIM header `DESCRIPTIVE / DIAGNOSTIC — not decision-grade. No edge claim.` and the humble disclaimer (`Preflight checks INPUT READINESS only ... does NOT validate model predictions, market divergence, or represent decision-grade clearance.`); (b) prints the report (checks + blocking_reasons + coverage + ingest summary); (c) **exits 0 when `ready`, non-zero when blocked**; (d) asserts `--include-untrusted` reaches the function (e.g. monkeypatch/capture the kwarg). Test via `subprocess`/`main(argv)` over ready and blocked fixtures.
- [ ] **Step 2:** run → fail.
- [ ] **Step 3 (GREEN, Claude):** implement the CLI calling `preflight_backtest_a_inputs`, printing header+disclaimer+report, `return 0 if report.ready else 1`. (scripts/ is exempt from the eval allowlist; E402 per-file-ignore covers late imports.)
- [ ] **Step 4:** focused pass; ruff clean.
- [ ] **Step 5:** commit `feat(s4): preflight CLI with diagnostic header + disclaimer`.

## Task 3: Audit + full-suite + ruff green (verification)

- [ ] **Step 1:** `tests/contract/test_subsystem_4_audit.py` green — the new function lives in the allowlisted `backtest_mock_draft.py` (no new eval file); `AUTHORIZED_EVAL_FILES`/import-wall/AST-anti-laundering/mock-isolation all hold; no `edge`/`adp` introduced.
- [ ] **Step 2:** full project suite `.venv/bin/python3.14 -m pytest -q` green; ruff `src app scripts` shows no NEW errors vs the pre-existing 45 E712.
- [ ] **Step 3:** commit only if a fix was needed.

---

## Self-Review

**Spec coverage:** §11.2b component/placement → T1/T2; checks 1–6 (presence incl. zero-byte; dry-ingest zero-picks + draft-date block; alignment; static §11.2 coverage; output-collision not_checked-unless-both; live-truth not_checked) → T1 RED cases; report shape + no decision-grade field + `ready` semantics → T1; CLI header/disclaimer/exit → T2; allowlist-safe placement → T3. Codex's 5 pins all mapped.

**Placeholder scan:** none; RED bodies Codex-authored, binding assertions pinned.

**Type/name consistency:** `BacktestAPreflightReport`/`BacktestAPreflightCheck`, statuses `{ok, blocked, not_checked}`, `ready`/`blocking_reasons` (no `verdict`/`pass`), `preflight_backtest_a_inputs`.

**Scope:** read-only diagnostic + CLI only. No model/market/decision surface; `decision_supported` + the §11.2 caveat untouched. No new eval file (allowlist-safe).
