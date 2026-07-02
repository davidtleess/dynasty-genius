# DEBT-6 Slice 1 — Model-Provenance Endpoint — Build Plan

**Spec:** `docs/superpowers/specs/2026-07-01-debt6-model-provenance-slice1-design.md`.
**Branch:** `feature/debt6-model-provenance` (to be created on David's authorization).
**Status:** DRAFT — **execution HELD pending Codex RED + David per-step authorization.** No tree mutation, no branch, no commit authorized by this draft. Cockpit framing three-way CLEAR (2026-07-01).

## 0. Cockpit-converged decisions ratified into this plan
- Slice 1 = provenance endpoint ALONE; fc-gap freshness detector is a separate Slice 1b (Codex: different contracts, don't combine).
- Registry `app/config/model_registry.json` is checked-in required config; endpoint 503s if it is absent/malformed (unlike realized-outcome's 200-inactive — a missing provenance source of truth is a misconfiguration, not a healthy state).
- `observed_status` (technical fact) is separated from `severity` (environment judgment) in the schema.
- Runtime-computed observed hash vs checked-in expected registry (no producer-written manifest — that self-certifies).
- **Populating an expected `sha256` is a promotion assertion → David-authorized** (T5, separated from the code build).
- Two separated, individually David-gated actions: (a) the code build (T1–T4) commit; (b) registry hash seeding (T5) — a "these bytes are approved" declaration.

## 1. Build sequence
Each task: **Codex RED (failing tests first, test-only) → Claude GREEN → adversarial dual-CLEAR → David-authorized commit → both-lane post-commit zero-divergence.** Focused test slices per task; full closeout gate at T4 (the focused-slice verification-gap lesson: run the full suite + FE + openapi-drift + inviolate audits before ship).

### T1 — Registry loader + schema + environment resolution
- New `app/api/routes/system_model_provenance_models.py` (Pydantic v2, `ConfigDict(extra="forbid")`): `RegistryArtifact` (incl `path_resolution: Literal["literal","latest_run_dir"]` default `literal`, `governing_pointer: str | None`, `sha256: str | None`, `allow_local_override: bool` default false), `ModelRegistry`, `ArtifactProvenance` (with `observed_status`, `pointer_status`, `severity`, `load_verification_status`, `serving_allowed`, `decision_supported: Literal[False]`), `ModelProvenanceResponse` (`overall_status`, `environment`, `registry_version`, `artifacts`, `decision_supported: Literal[False]`), `ModelProvenanceErrorResponse`. `observed_status` enum includes `expected_hash_missing`; `pointer_status` enum `referenced|pointer_missing|pointer_malformed|pointer_mismatch|not_applicable`.
- Registry loader: read `_ROOT / "app" / "config" / "model_registry.json"` (injectable path); absent/malformed/schema-invalid → raise a typed error mapped to 503 (spec §3.6).
- Environment resolver (spec §3.1): `DG_RUNTIME_ENV` explicit precedence; unset+`CI`→`ci`; unset+no-CI→`development`; injectable.
- **RED (Codex):** loader happy path over a temp registry; absent/malformed/schema-invalid → typed error; environment resolution precedence (seed 13); `extra="forbid"` rejects unknown fields (seed 12).

### T2 — Provenance classifier (the observed_status + severity + serving_allowed engine)
- Pure function `classify_artifact(entry, observed_bytes_present, observed_hash, environment, on_pointer_path) -> ArtifactProvenance`. Streamed sha256 helper (chunked, no full-file load). Resolves `path_resolution: latest_run_dir` against an injected `latest.json` run_dir before hashing (Codex R1).
- Implements the §3.2 status table (incl `expected_hash_missing` for `sha256: null`), §3.3 severity table (incl **R4**: active+required `local_operational` mismatch in serving/production → `integrity`/`blocked`, dev → `info`), §3.4 fail-closed `serving_allowed`, `allow_local_override` escape hatch.
- **RED (Codex):** falsification seeds 1–8, 14–17 via constructed inputs, no disk. Assert seed 2 blocks in development; seed 3 is the only tracked downgrade; seed 5 is caveat-not-failure; **seed 7** active+required serving mismatch → integrity/blocked (R4); **seeds 14–16** `expected_hash_missing` semantics (R3); **seed 17** Engine A `latest_run_dir` resolution — root pkl never `ok`-active (R1).

### T3 — Pointer health (`pointer_status`) + pointer-path scoping + unregistered-local reverse scan
- Read-only readers for `latest.json`, `engine_b/v2_manifest.json`, `head_a/v3_manifest.json`. Compute **`pointer_status`** per artifact with a `governing_pointer` (Codex R6): `referenced|pointer_missing|pointer_malformed|pointer_mismatch|not_applicable`; resolve `path_resolution: latest_run_dir` as `governing_pointer.run_dir / path` (filename). An artifact is clean only if `observed_status=ok` AND `pointer_status ∈ {referenced, not_applicable}`; broken pointer on active+required serving → integrity/blocked, gitignored-manifest-absent in ci/dev → caveat/200.
- Pointer set also scopes `unregistered_local` severity (spec §3.5 — POINTER reference, NOT claimed resolver-selection; every node carries `load_verification_status: not_verified`, Codex R2).
- **Scoped** reverse scan (Codex R5): only served roots + pointer-resolved run dirs, never a blanket `app/data/models/**` walk, never `tests/` fixtures; `.pkl` not in the registry → `unregistered_local`; off-path → strictly `info`, never degrades `overall_status`.
- **RED (Codex):** seed 9 (stray off-path → info, does not degrade overall), seed 10 (stray at pointer-resolved path, production → integrity/blocked), seed 18 (`load_verification_status: not_verified`), **seeds 19–21 (pointer health: hash-ok pkl + missing/malformed/mismatched governing pointer must NOT yield overall `ok` for active+required serving; `not_applicable` when no governing_pointer)**; missing-manifest handled gracefully via temp dirs; assert the scan does not walk historical run pkls or test fixtures.

### T4 — Endpoint wiring + response assembly + OpenAPI codegen + full closeout
- `system_model_provenance.py` route: assemble per-artifact provenance + `overall_status` (spec §3.4), `response_model=ModelProvenanceResponse`; 503 on registry failure. Wire into `app/main.py`.
- Regenerate the frontend OpenAPI client (`cd frontend && npm run openapi-gen`) so `tests/contract/test_openapi_drift_contract.py` stays green (drift gate).
- **RED (Codex):** end-to-end route over a temp registry + temp artifact tree via dependency-injected paths — seeds 1–21 at the HTTP layer; **the CI-shape case (seeds 5/15/19, guardrails §4): registry present + all local_operational artifacts + gitignored manifests absent (incl `sha256: null` entries) → 200, overall_status ≤ degraded, never 503, never a test failure.** Registry-absent/malformed/schema-invalid → 503 (seed 11).
- **Full closeout gate (T4, not deferred):** `.venv/bin/python3.14 -m pytest` (full, minus the known-excluded collection-error files per AGENT_SYNC) + `uvx ruff check src app` + FE vitest/biome/tsc + openapi-drift + `.venv/bin/python3.14 scripts/verify_sprint_closeout.py --base origin/main`.

### T5 — Registry hash seeding (SEPARATE, David-authorized promotion assertion)
- Compute the REAL sha256 of each currently-promoted on-disk artifact and write the expected hashes into `app/config/model_registry.json`. This declares "these exact bytes are approved" → **requires David's explicit authorization**, not bundled with the T1–T4 code commit.
- **Engine A entries use `path_resolution: latest_run_dir`** (Codex R1): the seed script resolves `latest.json["run_dir"]`, hashes `{run_dir}/{pos}_model.pkl` (the actually-served bytes), and records that run-dir-relative path — never the root-level `app/data/models/{pos}_model.pkl`.
- For `tracked_seed` artifacts, hashes are reproducible from committed bytes; for `local_operational` (gitignored) artifacts, hashes are stamped from David's serving-host bytes and recorded with `approved_by/approved_date/updated_by_commit`.
- A committed registry may ship in T4 with tracked_seed hashes populated and local_operational entries present-but-hash-pending (an explicit `sha256: null` → `observed_status: expected_hash_missing`, unverifiable, never silently `ok`; spec seeds 14–16) if David prefers to stage the promotion assertion; RED must cover the `sha256: null` case as fail-closed-not-ok.

## 2. Closeout gate
Full pytest (minus known exclusions) + `uvx ruff check src app` + FE gate + openapi-drift contract + `verify_sprint_closeout.py --base origin/main` ENFORCE PASS. Real-shape smoke: hit the live route in the current (development, local_operational present) environment and confirm a sane `overall_status` reflecting reality. Both-lane post-commit zero-divergence.

## 3. Guardrails (spec §4, inseparable)
Read-only; no model-training imports; no network; no dependence on gitignored artifacts being present; `decision_supported=false` everywhere; No-Verdict language; CI-safe (200 with local_operational absent + registry present).

## 4. Falsification matrix seeds
Carry spec §5 seeds 1–21 verbatim into the RED. GREEN self-probes the adversarial input classes (missing fields, wrong types, path traversal on the injected registry path / `governing_pointer`, non-hex sha256, unknown `kind`/`promotion_status`/`environment`/`path_resolution`/`pointer_status` values) BEFORE routing to Codex (the GREEN adversarial-input-hardening lesson).

## 5. Open micro-decisions for the RED to pin (flagged, not pre-decided)
- Exact `DG_RUNTIME_ENV` var name + whether `production` collapses to `serving` for severity purposes (spec treats them together for `serving_allowed`; RED may keep them distinct in the enum).
- Whether T5 ships in T4's commit with `tracked_seed` hashes only (local_operational `sha256: null`) or is fully deferred to a separate David-gated commit — David's call at T4 CLEAR.
- Depth of the reverse scan roots (spec §3.5: **served roots + pointer-resolved run dirs**, NOT a blanket `app/data/models/**` walk; RED confirms the scan does not walk historical run pkls or `tests/` fixtures).
