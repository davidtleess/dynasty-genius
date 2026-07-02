# BUILD-1 Tier-1 Graduation — Increment 1 — Build Plan

**Spec:** `docs/superpowers/specs/2026-07-02-build1-tier1-graduation-increment1-design.md`.
**Branch:** `feature/build1-tier1-readiness` (created on David's authorization).
**Status:** DRAFT — HELD pending cockpit redline CLEAR + **David DECIDE-1 ratification (spec §4)** + Codex RED + per-step authorization.

## 0. Ratified working decisions (kickoff round 2026-07-02)
- Machinery + ONE surface (roster_capacity) in this increment; Tier-2 pathway explicitly unbuildable here.
- Checked-in `app/config/tier_readiness.json` (declarative readiness registry) + runtime evaluation; CI tripwire owns contract-level preconditions; live guard status owns runtime status (Codex).
- DEBT-6 surfaces are live preconditions (integrity cascade — Gemini seed A).
- Component statuses `{pass, insufficient_data, fail, not_applicable}` with disclosed bases; fail-closed default for unknowns; `insufficient_data` never blocks under DECIDE-1 option (a) but always discloses.
- Badge vocabulary: "Diagnostic Grade"/"Input Verified"; Certified/Validated/Trusted/Approved banned.

## 1. Build sequence (Codex RED → Claude GREEN → dual-CLEAR → David-gated commit → zero-divergence, per task)
### T1 — Registry schema + loader
`app/api/routes/system_tier_readiness_models.py`: strict models (registry + response; `TierStatus`, `ComponentStatus` enums; `decision_supported: Literal[False]`); fail-closed `load_tier_readiness` (absent/malformed/schema/empty/duplicate/unknown component+precondition ids/evidence-path escape → typed error, 503 family). RED: seeds 8, 10 + extra-forbid injections.

### T2 — Pure readiness evaluator
`evaluate_surface_readiness(surface_config, live_precondition_statuses, component_states, ...) -> SurfaceReadiness` — integrity cascade, component rules (§3.2), mandatory insufficient-data disclosure, fail-closed unknowns. RED: seeds 1–5, 10.

### T3 — Live adapters + route + wiring
Evidence-existence checks (repo-root-confined); adapters reading the provenance + capture-health assemblies (in-process, read-only, DI for tests); `system_tier_readiness.py` route (`GET /api/system/tier-readiness`, monkeypatchable `_REGISTRY_PATH`/`_REPO_ROOT`, sanitized fixed 503); `app/main.py` wiring. RED: seeds 1–2 at HTTP layer, 7 (banned vocabulary in response), 8, 11 (CI shape).

### T4 — CI tripwire + REAL registry + OpenAPI + full closeout
Committed tripwire test (route_ids mounted; graduated-path models extra-forbid + recursive false; evidence refs exist; no gitignored-store dependence); REAL `app/config/tier_readiness.json` (roster_capacity per spec §2, `ratified_date` from David's §4 ruling); OpenAPI codegen; `verify_sprint_closeout --base origin/main` ENFORCE PASS; real-state smoke (live route: expect `diagnostic_grade_active_limited` with root-disclosed insufficient-data components IF preconditions green — R11). Push/PR checkpoint.

## 2. Redline round resolved (2026-07-02 — Codex R1–R10 all incorporated; Gemini root-disclosure + calibrations adopted)
- R1 status-aware copy (no calibration claims while insufficient_data; "guarantees" language removed) · R2 `diagnostic_grade_active_limited` headline + root `insufficient_data_count`/`_components`/`all_components_evaluable` · R3 component renamed `deterministic_range_disclosure` · R4+Gemini MIF = presence probe off-season, specific evidence paths pinned in RED else insufficient_data · R5 `ratified_date: null` → never active (`awaiting_david_ratification`) · R6 `not_applicable` only on `optional: true` components · R7 tripwire semantic depth (mounted routes, recursive false, no nested verdicts, unclamped tests present, no target nomination, banned-language) · R8 gitignored producer artifacts = runtime status only · R9 in-process injectable adapters · R10 vocabulary ban covers field/enum names.
- Capture-health precondition = per-store `store_status == ok` (Class-A immaturity coexists; Class-B breaks the badge) — Gemini calibration adopted.
- REMAINING for RED: exact MIF evidence paths; `checked_at`/clock injection mirrors capture-health.
