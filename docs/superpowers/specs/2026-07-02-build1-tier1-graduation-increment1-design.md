# BUILD-1 Tier-1 Graduation — Increment 1: Readiness Registry + Roster Capacity — Design Spec

**Status:** THREE-WAY CLEAR (Codex spec CLEAR for RED v3; Gemini advisory no-concerns) + **DAVID DECIDE-1 RATIFIED option (a)-as-amended (2026-07-02)**. Build authorized on branch `feature/build1-tier1-readiness`; per-task commits David-gated.
**Priority source:** `AGENT_SYNC.md` priority #2 (BUILD-1); product report Team Perspectives §2 (two-tier ladder, DECIDE-1 refinement). Unblocked by DEBT-6 (PR #107 provenance + PR #108 capture-health — both now live preconditions).
**Plan:** `docs/superpowers/plans/2026-07-02-build1-tier1-graduation-increment1-plan.md`.

## 0. Scope & standing constraints

**In scope (Increment 1):** the Tier-1 READINESS machinery + the first graduated surface:
1. Checked-in **tier-readiness registry** `app/config/tier_readiness.json` — surface_id as the primary unit (Codex: per-route fragments, per-artifact misses what David consumes), declaring route_ids, producer artifacts, gate components, evidence references, and live preconditions. A declarative readiness registry, NOT a prose certification.
2. Pure **readiness evaluator** — registry + injected live-guard statuses + component evidence states → per-surface runtime tier status.
3. Read-only **`GET /api/system/tier-readiness`** (system namespace, sibling of model-provenance/capture-health). Live-guard adapters are IN-PROCESS injectable functions over the provenance/capture-health assemblies — no HTTP self-calls, no TestClient recursion, deterministic test seams (Codex R9).
4. **CI tripwire** — a committed contract test that FAILS when any registered surface loses a contract-level precondition.
5. **First graduated surface: `roster_capacity`** (BOTH lanes independently: narrow, recently hardened, descriptive by design, David's real 27/26 off-season pain point, zero verdict exposure; Trust Console rejected first — the readiness system must not evaluate itself first).

**OUT of Increment 1:** Tier-2 machinery entirely (no `decision_supported=true` pathway exists in this build — the flag stays `Literal[False]` everywhere); UI badge rendering (later FE slice; copy contract IS specced §3.4); graduating any second surface; Slice-1c freshness rollup.

**Standing constraints:** No-Verdict Line (Tier-1 is DIAGNOSTIC grade — never flips `decision_supported`, never adds directive copy); read-only; real-shape discipline (evidence refs must point at REAL artifacts/tests or the component reports honestly); CI-safe (no committed test depends on gitignored stores — Codex boundary 4: CI validates contract + temp fixtures; LIVE guard status affects runtime status only).

## 1. What David gets (Gemini framing)

Today every surface carries the same generic "unvalidated prototype" umbrella. Tier-1 splits it: a **Diagnostic Grade** surface *reports verified input hygiene and live preconditions* (R1 — never a guarantee): audited input hygiene (zero duplication/leakage), model-input fidelity wiring (MIF breaker armed), disclosed+unclamped uncertainty, AND live substrate integrity (the DEBT-6 guards green). Ungraduated surfaces read plainly as "Prototype / Unvalidated Overlay" — structural skepticism is an intended outcome, not a bug.

## 2. Registry — `app/config/tier_readiness.json`

```json
{
  "registry_version": 1,
  "surfaces": [
    {
      "surface_id": "roster_capacity",
      "display_name": "Roster Capacity",
      "declared_tier": "tier_1_candidate",
      "route_ids": ["/api/roster/capacity"],
      "producer_artifacts": ["app/data/roster_capacity/roster_capacity_latest.json"],
      "live_preconditions": ["model_provenance_ok", "capture_health_ok"],
      "gate_components": [
        { "component": "audit_hygiene", "evidence": ["tests/contract/test_roster_capacity_route.py", "scripts/scan_league_opportunity_no_verdict.py"], "expectation": "cordon + leakage/dup gates enforced on this path" },
        { "component": "deterministic_range_disclosure", "evidence": ["tests/contract/test_roster_capacity_route.py"], "expectation": "ranges signed + unclamped + basis-disclosed; DETERMINISTIC envelope bounds — the component name must never claim calibrated/statistical uncertainty without real calibration evidence (Codex R3)" },
        { "component": "mif_breaker", "evidence": ["src/dynasty_genius/realized_outcome/scorer.py", "tests/contract (realized-outcome scorer MIF tests — exact paths pinned in RED)"], "expectation": "wired; active-role deviation < 15% when evaluable; off-season = a schema/config presence PROBE (scorer + store classes importable) returning insufficient_data honestly — never default-pass, never crash on missing SQLite (Codex R4 + Gemini); if the specific evidence path cannot be pinned, the component sits insufficient_data" },
        { "component": "no_directive_copy", "evidence": ["frontend gate banned-language linter"], "expectation": "zero directive tokens on the graduated path" }
      ],
      "ratified_by": "David",
      "ratified_date": null
    }
  ]
}
```

Loader fail-closed (503 family): absent/malformed/schema-invalid/empty/duplicate surface_id/unknown component or precondition id/evidence path escaping repo root. Strict models (`extra="forbid"`, `strict=True`), `decision_supported: Literal[False]` on every response model.

## 3. Runtime contract — `GET /api/system/tier-readiness`

Per surface: `tier_status ∈ { diagnostic_grade_active, diagnostic_grade_active_limited, preconditions_degraded, not_graduated }` — `_limited` is MANDATORY whenever any component is `insufficient_data` (Codex R2 + Gemini: the headline itself discloses dormancy). Root-level machine-readable limits on every surface node: `insufficient_data_count: int`, `insufficient_data_components: list[str]`, `all_components_evaluable: bool` + per-component `component_status ∈ { pass, insufficient_data, fail, not_applicable }` (each with a disclosed `basis` string) + `live_preconditions` echo (current provenance/capture-health readings) + `decision_supported: false`.

- **3.1 Integrity cascade (Gemini seed A — the DEBT-6 guards become live preconditions):** `model_provenance_ok` requires the provenance assembly `overall_status == ok`; `capture_health_ok` requires capture-health `overall_status == ok`. ANY degradation → `tier_status = preconditions_degraded` immediately (fail-closed at request time). No diagnostic-grade metrics on top of broken substrate.
- **3.2 Component evaluation:** `fail` on any component → `not_graduated` (a later data-driven failure AUTO-DOWNGRADES). `insufficient_data` (e.g. MIF off-season, in-season calibration) does NOT block activation but is MANDATORY-disclosed (count + names at root of the surface node). Unknown/unclassified component status → treated as `fail` (fail-closed default, mirrors the caveat-class rule). `not_applicable` is permitted ONLY for components the registry explicitly marks `optional: true`; on a required component it is treated as `fail` — never a silent pass (Codex R6).
- **3.2b Ratification gate (Codex R5):** `ratified_date: null` → the surface can NEVER reach `diagnostic_grade_active`/`_limited`; it reports `not_graduated` with basis `awaiting_david_ratification` even when every check passes. David's DECIDE-1 ruling stamps the date.
- **3.3 Evidence honesty:** every `evidence` path is checked for existence at request time; a missing evidence ref → that component `fail` (never silent). Evidence claims beyond existence (e.g. "cordon enforced") are pinned by the CI tripwire, not runtime. **Producer artifacts (Codex R8):** `producer_artifacts` are gitignored `_latest` files — absence/staleness contributes a RUNTIME component/live status (honest degraded), never a loader/config error and never a CI failure (committed tests stay temp-only).
- **3.4 Language contract:** badge vocabulary = "Diagnostic Grade" / "Input Verified"; **banned on this surface — in copy AND in field/enum names (Codex R10, e.g. no `certification_status`): Certified, Validated, Trusted, Approved, safe, recommended** (+ the standing directive-token set); runtime naming stays `tier_readiness`/`tier_status`/`readiness`/`diagnostic_grade`. Honest-line copy is STATUS-AWARE (Codex R1 — it may never assert calibration/MIF as achieved while those components are `insufficient_data`): active-limited example: `"Diagnostic grade (limited): verified input hygiene and live pipeline preconditions. N components await in-season data and are not yet evaluated. This rating does not predict active-season accuracy and does not evaluate transaction suitability."` `decision_supported=false` recursive; registry corruption → sanitized fixed 503.

## 4. DECIDE-1 ratification point (David's bar — the one open ruling)

**(a) Claude POV (specced, R2-amended):** Tier-1 ACTIVATES as **`diagnostic_grade_active_limited`** — the headline status itself carries the limitation — with zero `fail` components + all live preconditions green + wiring/hygiene components `pass`, while data-dependent components (`mif_breaker` trip-evaluation, in-season calibration) sit `insufficient_data` with root-level machine-readable disclosure — honoring the ladder's "no data-accrual wait"; the breaker auto-downgrades the moment real data fails it.
**(b) Stricter alternative:** all components must `pass` → nothing graduates before ~Sept 2026.
Codex boundary 2 supports (a)'s honesty mechanics — restated post-R1/R3 (R13): diagnostic readiness covers hygiene/provenance/freshness/MIF wiring + deterministic range disclosure; data-dependent checks sit `insufficient_data` until evaluable. Gemini seed B demands only never-default-pass-on-null, which (a) satisfies via disclosed `insufficient_data`. **RATIFIED: David ruled option (a)-as-amended, 2026-07-02 — Tier-1 activates as `diagnostic_grade_active_limited` with root-disclosed dormant components and automatic downgrade on real data failure. `ratified_date: 2026-07-02` stamps the roster_capacity registry entry at T4.**

## 5. Falsification seeds (carry into RED)
1. Healthy: registry valid + preconditions green + components pass/insufficient → `diagnostic_grade_active_limited` (plain `_active` REQUIRES zero insufficient_data — R11), root disclosures present, `decision_supported=false` recursive.
2. **Integrity cascade:** provenance `degraded` OR `blocked` → `preconditions_degraded`; capture-health precondition keys on `store_status == ok` per store (Class-A calendar-immaturity caveats coexist with ok and do NOT break the badge; any Class-B degradation DOES — Gemini calibration); recovery restores without restart (computed per request).
3. **MIF null (Gemini B):** breaker input missing/NaN → `insufficient_data` + disclosure, NEVER `pass` (off-season = presence probe, no crash on missing SQLite); breaker evaluable + deviation ≥15% → `fail` → `not_graduated`.
3b. **Ratification gate (R5):** all-pass surface with `ratified_date: null` → `not_graduated` / `awaiting_david_ratification`.
3c. **Headline honesty (R2):** any `insufficient_data` → `tier_status = diagnostic_grade_active_limited` + root `insufficient_data_count`/`_components`/`all_components_evaluable=false`; plain `diagnostic_grade_active` REQUIRES all components evaluable.
4. Unknown component status / unknown component id → fail-closed (`fail` / loader reject respectively).
5. Missing evidence file → component `fail`, surface `not_graduated`, path named in basis.
6. **Unclamped invariant (Gemini C):** the readiness registry references the RED-locked signed/unclamped range tests; tripwire fails if those tests are deleted/renamed (evidence existence).
7. **Directive tokens (Gemini D):** banned badge vocabulary (Certified/Validated/Trusted/Approved) anywhere in the tier-readiness response → RED fails; standing banned-language scan covers the graduated path.
8. Registry family: absent/malformed/schema-invalid/empty/duplicate/unknown-ids/evidence-path-escape → sanitized fixed 503 (no paths/tracebacks).
9. CI tripwire (Codex R7 + Gemini): stamped surface with a route_id not mounted in `app.main` → committed test FAILS; every evidence path exists; graduated-path response models remain `extra="forbid"` + recursive `decision_supported=false` with NO nested verdict fields; signed/unclamped range tests present; no target nomination; banned-language coverage on the path. Existence alone can never pass `audit_hygiene`.
10. No Tier-2 pathway: no field in any model can express `decision_supported=true`; injection rejected.
11. CI shape: gitignored stores/artifacts absent → tier-readiness still 200 (live preconditions read as degraded honestly); committed tests use temp registries + injected guard statuses only.

## 6. Kickoff round resolutions (2026-07-02)
- First surface = Roster Capacity (both lanes independent). Registry+runtime (not computed-only); surface_id primary unit; CI tripwire for contract, runtime for live status (Codex 1/3/4). Off-season calibration honesty (Codex 2 + Gemini §4): no claims from dormant September machinery; RC ranges disclosed as deterministic envelope bounds. Badge language + prototype shadow labels (Gemini §2). Seeds A–D adopted (§5.2/3/6/7).
