# DEBT-6 Model Reproducibility — Slice 1: Model-Provenance Endpoint — Design Spec

**Status:** DRAFT — cockpit framing three-way CLEAR (Claude + Codex + Gemini, 2026-07-01); grounded against the real serving path. **Execution HELD pending Codex RED + David per-step authorization.** No tree mutation authorized by this draft.
**Priority source:** `AGENT_SYNC.md` → "Next-Session Priority List (2026-07-01)" #1; product report `/Users/davidleess/dynasty-genius/docs/product-report-2026-06-30.md` (Team Perspectives — 2026-07-01, DEBT-6).
**Plan:** `docs/superpowers/plans/2026-07-01-debt6-model-provenance-slice1-plan.md`.

---

## 0. Scope & standing constraints

**In scope (Slice 1):** a single read-only endpoint `GET /api/system/model-provenance` that, at request time, computes the observed content hash of each served model artifact on disk and compares it against a **checked-in registry of expected hashes** (`app/config/model_registry.json`). It classifies each artifact's `observed_status` (a technical fact) and maps a `severity` (what the current environment should do about it), so laptop-reality-vs-repo-reality divergence is **impossible to hide**.

**Explicitly OUT of Slice 1 (later DEBT-6 slices, do not build here):**
- Capture-health / freshness gap detector over the daily PIT stores (`fc_forward_capture.db` first) — **Slice 1b**, a separate contract (model identity ≠ time-series completeness; Codex: do not combine).
- Any UI surface (the eventual "System Trust & Freshness" card — Gemini-named — is a later frontend slice).
- Off-laptop / always-on scheduler migration; Databricks serving decision; cloud secrets/ownership.
- Committing model **bytes** into git (fresh-clone *prediction* reproducibility — a later DEBT-6 slice; provenance **hashes** already make divergence non-hideable, so the "availability" gap is deferred, not a blocker).

**Standing constraints:**
- **No-Verdict Line.** This surface is descriptive system status, never a player/trade verdict. `decision_supported=false` at every artifact node and at the response root.
- **System Integrity vs Data Freshness split (Gemini).** A missed capture is a *caveat* (contextual modifier); a corrupted/mismatched model is an *integrity* failure (engineering attention). They must never share visual/severity weight — that is the alarm-fatigue guard.
- **Read-only.** No writes, no mutation of any model artifact or manifest.
- **Real-shape discipline.** The registry mirrors the REAL served artifacts and the REAL resolver selection (§2), not synthetic fixtures.

---

## 1. Why (the concrete divergence this closes)

Grounded in the real serving path (verified 2026-07-01):

| Artifact class | Path | Git | Resolver | Fresh-clone behavior (the hidden divergence) |
|---|---|---|---|---|
| Engine A position models | **`latest.json["run_dir"]/{QB,RB,TE,WR}_model.pkl`** (run-dir-resolved — NOT the root `app/data/models/{pos}_model.pkl`) | **tracked** (active run committed) | `EngineAScorer._load()` (`src/dynasty_genius/scoring/engine_a.py:80`) | reproducible |
| Engine B v2 | `engine_b/runs/20260513T012309Z/{qb,rb,wr}_v2.pkl`, `runs/20260626T165649Z/te_v3.pkl` (via `engine_b/v2_manifest.json`) | **gitignored** | `engine_b_service._load_v2_bundles()` | **silently falls back to v1 bundle** (`engine_b_service.py:123`) |
| Head A v3 (TE) | `head_a/runs/20260524T140748Z/te_v3.pkl` (via `head_a/v3_manifest.json`) | **gitignored** | `EngineAV3Scorer._load()` | **silently returns False / None (v3 skipped)** (`engine_a.py:171`) |

**Engine A path correction (Codex R1):** the active served bytes are `latest.json["run_dir"]/{pos}_model.pkl` (the current pointer resolves `run_dir` = `app/data/models/runs/20260502T153931Z`), NOT the root-level `app/data/models/{pos}_model.pkl`. The registry must key Engine A entries on the run-dir-resolved path (or store them logically resolved through `latest.json.run_dir`) so it cannot certify root pkls while the scorer serves different run-dir bytes. Root-level pkls, if present, are NOT active-serving and must never be classified `ok`-active.

A fresh clone therefore serves v1 while David's laptop serves v2/te_v3 — with **no signal anywhere**. Peer agents validating in separate worktrees audit a different model reality than David uses. Slice 1 makes that state observable and fail-closed. There is no existing artifact-byte provenance to reuse: model *version strings* (`latest.json.model_version`, `"head_a_te_v3_ridge"`), *output* hashes (`WhatChangedVintage.semantic_output_hash/provenance_hash`), and *data-artifact* hashes (`feature_source` CSV sha256, `pvo_source` JSON sha256) all exist, but nothing hashes the model `.pkl` bytes against a checked-in expectation.

---

## 2. The checked-in registry — `app/config/model_registry.json`

A new **runtime policy artifact**, checked in, updated ONLY inside a David-authorized model-promotion PR (never a daily-producer side effect → never a stale tripwire). `app/config/` is created for it (no top-level `config/` convention exists; `app/data/` is overloaded with gitignored producer output and would blur "producer output" vs "repo authority"; `docs/` prose drifts).

**Entry schema (per artifact):**
```json
{
  "registry_version": 1,
  "artifacts": [
    {
      "artifact_id": "engine_a:QB",
      "path_resolution": "latest_run_dir",
      "path": "QB_model.pkl",
      "governing_pointer": "app/data/models/latest.json",
      "sha256": "<expected hex>",
      "kind": "tracked_seed",
      "promotion_status": "active",
      "required_by_env": ["development", "ci", "serving", "production"],
      "approved_by": "David",
      "approved_date": "2026-07-01",
      "updated_by_commit": "<sha>"
    },
    {
      "artifact_id": "engine_b:qb_v2",
      "path_resolution": "literal",
      "path": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
      "governing_pointer": "app/data/models/engine_b/v2_manifest.json",
      "sha256": "<expected hex>",
      "kind": "local_operational",
      "promotion_status": "active",
      "required_by_env": ["serving", "production"],
      "approved_by": "David",
      "approved_date": "2026-07-01",
      "updated_by_commit": "<sha>"
    }
  ]
}
```

- `path_resolution` (optional; default `literal`): `literal` (use `path` verbatim) | `latest_run_dir` (Engine A — `path` is the **filename only** e.g. `QB_model.pkl`; `resolved_path = <governing_pointer.run_dir> / path` at request time, so the registry tracks the actually-served run and stale-path certification is impossible by construction — Codex R6b).
- `governing_pointer` (optional): the manifest/pointer file the resolver reads to SELECT this artifact (Engine A → `latest.json`; Engine B → `v2_manifest.json`; Head A → `v3_manifest.json`). Drives the computed `pointer_status` (§3.5) so a hash-matching artifact whose selecting pointer is missing/malformed/mismatched is NOT reported clean. Omit for artifacts with no governing pointer (`pointer_status: not_applicable`).
- `kind`: `tracked_seed` (bytes in git; CI can verify) | `local_operational` (bytes gitignored; expected-absent in CI, present on David's serving host).
- `required_by_env`: environments in which the artifact MUST be present-and-matching to serve. A `local_operational` artifact is typically NOT required in `ci`/`development` (expected-absent) but IS required in `serving`/`production`.
- `promotion_status`: `active` (currently served) | `candidate` | `parked` (e.g. the parked WR/RB rookie board work — present but not the active path).
- Expected `sha256`: for `tracked_seed`, deterministically computable in CI from the committed bytes; for `local_operational`, stamped from David's promoted bytes at promotion time. **Populating/updating a hash is a promotion assertion → David-authorized** (plan task T-seed).

**Registry coverage (Slice 1):** the real active-served artifacts above — Engine A `{QB,RB,TE,WR}_model.pkl` (tracked_seed), Engine B v2 `{qb,rb,wr}_v2.pkl` + `te_v3.pkl` (local_operational), Head A `te_v3.pkl` (local_operational). Parked/candidate artifacts may be listed with `promotion_status` set accordingly but do not gate `overall_status`.

---

## 3. Endpoint contract — `GET /api/system/model-provenance`

- New route file `app/api/routes/system_model_provenance.py`; `APIRouter(prefix="/system", tags=["system"])`; wired in `app/main.py` with `app.include_router(system_model_provenance.router, prefix="/api")`.
- `_ROOT = Path(__file__).resolve().parents[3]` (repo convention). Registry path `_ROOT / "app" / "config" / "model_registry.json"`, injectable for tests.
- Pydantic v2 response model, `response_model=ModelProvenanceResponse`, `ConfigDict(extra="forbid")` on all models, `decision_supported: Literal[False]`.

**Response schema (Codex-shaped):**
```json
{
  "overall_status": "ok | degraded | blocked",
  "environment": "development | ci | serving | production",
  "registry_version": 1,
  "artifacts": [
    {
      "artifact_id": "engine_b:qb_v2",
      "path": "app/data/models/engine_b/runs/20260513T012309Z/qb_v2.pkl",
      "expected_kind": "tracked_seed | local_operational",
      "promotion_status": "active | candidate | parked",
      "observed_status": "ok | local_override | unregistered_local | hash_mismatch | missing_required | local_artifact_missing_ci | expected_hash_missing",
      "pointer_status": "referenced | pointer_missing | pointer_malformed | pointer_mismatch | not_applicable",
      "severity": "info | caveat | integrity",
      "load_verification_status": "not_verified | verified",
      "serving_allowed": true,
      "decision_supported": false
    }
  ],
  "decision_supported": false
}
```

### 3.1 Environment resolution
`environment` is read from env var `DG_RUNTIME_ENV ∈ {development, ci, serving, production}`. If unset: infer `ci` when a `CI` truthy env var is present, else `development`. `serving`/`production` are set explicitly by the deploy host. (RED locks the resolution precedence; env is injectable in tests.)

### 3.2 `observed_status` — the technical fact (per artifact)
The on-disk path is first resolved per `path_resolution` (§2 — `latest_run_dir` for Engine A). Then computed by streaming the file's sha256 at request time and comparing to the registry `sha256`:
- **registry `sha256` is `null`** (expected hash not yet seeded) → `expected_hash_missing` — the registry declares the artifact but has no approved hash to verify against; **never `ok`** (§3.4).
- **present + hash matches** → `ok`
- **present + hash differs**, `kind=tracked_seed` → `hash_mismatch`
- **present + hash differs**, `kind=local_operational` → `local_override` (local bytes differ from last-promoted expected — normal for in-progress local work in dev; NOT benign for active+required serving bytes — see §3.3)
- **absent**, `kind=tracked_seed` (a tracked model missing) → `missing_required`
- **absent**, `kind=local_operational` in `ci`/`development` (expected-absent) → `local_artifact_missing_ci`
- **absent**, `kind=local_operational` in `serving`/`production` where `required_by_env` includes it → `missing_required`
- **a `.pkl` found under the served model roots that is NOT in the registry** → `unregistered_local` (scoped reverse-scan; see §3.5)

### 3.3 `severity` — environment's judgment (the alarm-fatigue guard)
`severity` is a function of `(observed_status, environment, expected_kind, promotion_status, on_serving_path)` — NOT part of the fact:
- `ok` → `info`
- `local_override` → `info` in `development` (or for non-active `candidate` work); **`integrity` in `serving`/`production` for an `active`+required artifact** (Codex R4 — a mismatch from David-approved bytes in serving is *unapproved serving reality*, not a caveat), unless an explicit env-scoped `allow_local_override: true` exists. `caveat` only for non-required/candidate serving artifacts.
- `local_artifact_missing_ci` → `caveat` (degraded, **never** a test failure)
- `expected_hash_missing` → `integrity` for `active`+required in `serving`/`production` (§3.4); `caveat` for `local_operational` absent-in-CI with null hash; `info`/`caveat` for `candidate`/`parked` (never overall-blocking).
- `unregistered_local` → `info` when NOT on a pointer-resolved serving path (stray/old run); `integrity` when it sits at a pointer-resolved path in `serving`/`production` (§3.5)
- `hash_mismatch` → `integrity` **always** (see fail-closed §3.4)
- `missing_required` → `integrity`

### 3.4 `serving_allowed` + `overall_status` — fail-closed semantics
- `hash_mismatch` on a `tracked_seed`, `active` artifact → `serving_allowed=false`, contributes `blocked` to `overall_status`, **even in `development`** — UNLESS an explicit dev-only registry flag `allow_local_override: true` is set on that entry. (You cannot silently serve tampered/corrupted tracked bytes.)
- `local_override` on an `active`+required artifact in `serving`/`production` → `serving_allowed=false`, `blocked` (Codex R4), unless `allow_local_override: true`.
- `expected_hash_missing` on an `active`+required artifact in `serving`/`production` → `serving_allowed=false`, `blocked` (an unverifiable expected hash is not a pass). In `ci`/`development`, `expected_hash_missing` for a `local_operational` absent artifact → `serving_allowed=true`, contributes at most `degraded`.
- `missing_required` → `serving_allowed=false`, contributes `blocked`.
- `unregistered_local` at a pointer-resolved serving path in `serving`/`production` → `serving_allowed=false`, `blocked`.
- `pointer_status ∈ {pointer_missing, pointer_malformed, pointer_mismatch}` on an `active`+required artifact in `serving`/`production` → `serving_allowed=false`, `blocked` (even if `observed_status=ok`); in `ci`/`development` a missing gitignored governing manifest → `caveat`/200.
- `local_artifact_missing_ci`, `local_override`(dev / candidate), `ok` → `serving_allowed=true`.
- An artifact contributes `ok` to `overall_status` **only if `observed_status=ok` AND `pointer_status ∈ {referenced, not_applicable}`** (Codex R6).
- `overall_status` = `blocked` if any `active`+required artifact is blocked; else `degraded` if any `caveat`-level deviation exists; else `ok`. `candidate`/`parked` artifacts never drive `overall_status`.

### 3.5 Pointer-resolved-path determination (honest scope — Codex R2)
**Slice 1 determines POINTER reference, not actual resolver selection.** Reading the pointers (`app/data/models/latest.json`, `engine_b/v2_manifest.json`, `head_a/v3_manifest.json`) answers "does a pointer reference this path?" — it does NOT prove the running service selected these exact bytes, because the real resolvers silently fall back (Engine B → v1 bundle; Head A → None). Claiming resolver selection from manifests alone would be dishonest. Therefore every artifact node carries **`load_verification_status`** = `not_verified` in Slice 1 (pointer-based provenance); a future slice may add a shared read-only load probe that mirrors the resolvers to earn `verified`.

This scope is sufficient for the core goal: the gitignored-artifact divergence is caught by registry-expected-path **presence + hash** (an absent expected `qb_v2.pkl` surfaces as `local_artifact_missing_ci`/`missing_required` regardless of resolver selection), so non-hideability does not depend on selection proof.

**`pointer_status` — governing-pointer health (Codex R6).** A hash-matching artifact whose *selecting pointer* is broken must NOT be reported clean (e.g. Head A `te_v3.pkl` present + hash-ok but `v3_manifest.json` missing → the real scorer returns None; Engine A run pkl hash-ok but `latest.json` missing/malformed → the real scorer can't resolve). For each artifact with a `governing_pointer`, compute:
- `referenced` — pointer file present, parseable, and references this artifact's resolved path/run.
- `pointer_missing` — governing_pointer file absent.
- `pointer_malformed` — present but unparseable / schema-invalid.
- `pointer_mismatch` — parseable but references a different run/path than the registry entry (e.g. `latest.json.run_dir` ≠ the entry's expected run).
- `not_applicable` — no `governing_pointer` declared.

Severity/fail-closed for `pointer_status` mirrors the artifact rules: for an `active`+required artifact in `serving`/`production`, `pointer_missing`/`pointer_malformed`/`pointer_mismatch` → `integrity`/`serving_allowed=false`/`blocked`. In `ci`/`development` a missing **gitignored** manifest (Engine B/Head A) → `caveat`/200 (matches the gitignored-artifact discipline — CI legitimately lacks it). An artifact is reported clean (contributes `ok`) **only if `observed_status=ok` AND `pointer_status ∈ {referenced, not_applicable}`** (§3.4).

The pointer set is used only to scope `unregistered_local` severity: an `unregistered_local` `.pkl` at a pointer-resolved path in serving/production → `integrity`; an orphaned off-path `.pkl` → `info`. Reads are read-only; a missing gitignored manifest is handled as a `local_artifact_missing_ci`-class signal on that engine, not a crash.

**Reverse-scan scope (Codex R5):** scan ONLY the known served roots and pointer-resolved run dirs (`app/data/models/` top level, the active `latest.json` run dir, the `v2_manifest`/`v3_manifest` run dirs) — NOT a blanket `app/data/models/**` walk (which would flag every historical run pkl). Any old off-path `.pkl` that is scanned is **strictly `info`, never degrades `overall_status`**. The scan must not walk `tests/` fixtures.

### 3.6 Endpoint-level failure (registry itself)
The registry is REQUIRED checked-in config. If it is **absent** or **malformed JSON** or **schema-invalid** → the endpoint returns **503** (fail-closed; a provenance endpoint with no source of truth must not pretend health). This differs from realized-outcome's 200-inactive: an absent scorecard is a healthy off-season state, but an absent provenance registry is a misconfiguration. Non-finite/garbage never silently passes.

---

## 4. Guardrails (inseparable from the build)
- Read-only: no writes to any model artifact, manifest, or the registry from the endpoint.
- No import of model-training code; provenance computes hashes by streaming file bytes only.
- No network. No dependence on gitignored artifacts being present (their absence is a first-class `observed_status`, not an error).
- `decision_supported=false` at every artifact node and root; No-Verdict language only (status is descriptive, never "good/bad model", never buy/sell/start/sit).
- CI-safe: with all `local_operational` artifacts absent (the CI reality) and the registry present, the endpoint returns **200** with `overall_status` reflecting `local_artifact_missing_ci` caveats — CI must stay green. RED asserts this exact CI shape (the gitignored-route CI lesson: never assume gitignored artifacts exist).

---

## 5. Falsification matrix seeds (carry into Codex RED)
All via injected temp registry + temp artifact paths + injected environment (DI), never touching real `app/data/`:
1. tracked_seed present, hash matches → `ok`/`info`/`serving_allowed=true`; `overall_status=ok`.
2. tracked_seed present, hash differs → `hash_mismatch`/`integrity`/`serving_allowed=false`; `overall_status=blocked` — **assert blocked even when environment=development** (no `allow_local_override`).
3. tracked_seed present, hash differs, `allow_local_override=true`, env=development → downgraded (not blocked) — the ONLY escape hatch.
4. tracked_seed absent → `missing_required`/`integrity`/`blocked`.
5. local_operational absent, env=ci → `local_artifact_missing_ci`/`caveat`/`serving_allowed=true`; endpoint returns **200**, `overall_status` ≤ `degraded` (NOT a 503, NOT a test failure).
6. local_operational present, hash differs, env=development → `local_override`/`info` (no false alarm on David's local research).
7. local_operational present, hash differs, **active+required, env=serving → `local_override`/`integrity`/`serving_allowed=false`/`blocked`** (Codex R4 — unapproved serving reality, NOT a caveat); with `allow_local_override=true` → downgraded. Non-required/candidate serving mismatch → `caveat`.
8. local_operational absent, env=serving, required_by_env includes serving → `missing_required`/`integrity`/`blocked`.
9. stray `.pkl` under a served root, not in registry, NOT at a pointer-resolved path → `unregistered_local`/`info`; assert it does NOT degrade `overall_status`.
10. stray `.pkl` at a pointer-resolved path, env=production → `unregistered_local`/`integrity`/`serving_allowed=false`/`blocked`.
11. registry file absent → **503**. registry malformed JSON → **503**. registry schema-invalid → **503**.
12. every artifact node and the root carry `decision_supported=false`; `extra="forbid"` rejects any unknown field (verdict-field fail-closed).
13. environment resolution: `DG_RUNTIME_ENV` explicit wins; unset + `CI` set → `ci`; unset + no `CI` → `development`.
14. registry `sha256: null`, active+required, env=serving → `expected_hash_missing`/`integrity`/`serving_allowed=false`/`blocked` (Codex R3 — unverifiable expected hash is never `ok`).
15. registry `sha256: null`, local_operational absent, env=ci → `expected_hash_missing`/`caveat`/**200** (not 503, not a test failure).
16. registry `sha256: null`, `candidate`/`parked` → `info`/`caveat`, never `overall_status=blocked`.
17. Engine A entry with `path_resolution: latest_run_dir` (Codex R1): `path` is the filename `QB_model.pkl`; the endpoint hashes `<latest.json.run_dir>/QB_model.pkl`, matches → `ok`; a root-level `app/data/models/QB_model.pkl` with different bytes must NOT be classified `ok`-active (off the served path → `unregistered_local`/`info` at most). Assert certifying the root pkl cannot mask a run-dir divergence.
18. every artifact node carries `load_verification_status: not_verified` in Slice 1 (Codex R2 — pointer provenance, no false claim of resolver selection).
19. **pointer health (Codex R6):** Head A `te_v3.pkl` present + hash-matches, but `head_a/v3_manifest.json` absent → `observed_status=ok` BUT `pointer_status=pointer_missing`; active+required serving → `integrity`/`serving_allowed=false`/`blocked` (NOT overall `ok`); ci/dev with the gitignored manifest absent → `caveat`/200.
20. Engine A run pkl hash-matches, but `latest.json` absent → `pointer_status=pointer_missing` (can't resolve); malformed `latest.json` → `pointer_malformed`; `latest.json.run_dir` points to a different run than the entry's expected run → `pointer_mismatch`. Active+required serving → integrity/blocked; hash-ok must not certify `ok`-active while the pointer is broken.
21. an artifact with no `governing_pointer` → `pointer_status=not_applicable`; hash-ok → contributes `ok` normally.

---

## 6. Resolved (cockpit, 2026-07-01 — Codex + Gemini concur)
- Ranking: DEBT-6 #1 (unanimous), before Tier-1 graduation (#2) and BUILD-4 Superflex-QB (#3).
- Slice boundary: provenance endpoint ALONE; fc-gap detector is Slice 1b (do not combine — different contracts).
- Registry at `app/config/model_registry.json` (Codex, repo-grounded); endpoint `/api/system/model-provenance` (unanimous — noun/resource convention; `/api/health` reserved for Slice-1b freshness/liveness; not folded into `/api/trust-surface`).
- `observed_status` (fact) strictly separated from `severity` (env judgment) in the schema (Codex refinement).
- `hash_mismatch` on tracked active bytes blocks even in dev unless `allow_local_override` (Codex fail-closed tightening).
- System-Integrity-vs-Data-Freshness severity split is the alarm-fatigue guard (Gemini); grace-period / dormant-off-season semantics belong to Slice 1b's freshness detector, not this endpoint.
- Runtime-computed observed hash vs checked-in expected registry — NOT a producer-written manifest (which would self-certify) (Codex).
- Eventual UI name: "System Trust & Freshness" (Gemini) — later slice, noted not built.
- Gemini Governance & Product-Edge CLEAR (2026-07-01): severity split, No-Verdict recursion, and registry-503 all endorsed.

**Codex REDLINE resolutions (2026-07-01), all incorporated:**
- **R1 — Engine A path:** register the run-dir-resolved path (`path_resolution: latest_run_dir`), not the root pkl, so the endpoint cannot certify root bytes while `EngineAScorer._load()` serves `latest.json["run_dir"]/{pos}_model.pkl` (seed 17).
- **R2 — resolver selection honesty:** Slice 1 does POINTER provenance only; every node carries `load_verification_status: not_verified`; no claim of actual resolver selection. Core divergence is still caught via expected-path presence+hash (seed 18, §3.5).
- **R3 — `expected_hash_missing`:** added as a first-class `observed_status`; `sha256: null` is never `ok` — integrity/blocked for active+required serving, caveat-200 for absent local_operational in CI, non-blocking for candidate/parked (seeds 14–16).
- **R4 — serving local_override:** an `active`+required `local_operational` hash mismatch in serving/production is `integrity`/`blocked` (unapproved serving reality), not a caveat; dev stays `info` (seed 7).
- **R5 — reverse-scan scope:** scoped to served roots + pointer-resolved run dirs, never a blanket `**` walk; off-path pkls are strictly `info` and never degrade `overall_status`; the scan skips `tests/` fixtures (seed 9, §3.5).
- **R6 — pointer/manifest health first-class (2026-07-01, second pass):** added `governing_pointer` (registry) + `pointer_status` (computed response: `referenced|pointer_missing|pointer_malformed|pointer_mismatch|not_applicable`). A hash-matching artifact whose selecting pointer is broken is NOT reported clean — active+required serving pointer break → integrity/blocked; ci/dev gitignored-manifest-absent → caveat/200 (seeds 19–21). Fixed the `latest_run_dir` ambiguity: `path` is the filename, `resolved_path = governing_pointer.run_dir / path` (R6b).
