# DEBT-6 Slice 1c: Whole-App Health Rollup (`/api/health`) — Design Spec

**Status:** THREE-WAY CLEAR (Codex spec CLEAR for RED v3; Gemini CLEAR). Build authorized by David on branch `feature/debt6-health-rollup` (2026-07-02); per-task commits David-gated.
**Prior:** Slice 1 (provenance, PR #107), 1b (capture health, PR #108), BUILD-1 Increments 1–2 (tier readiness, PRs #109/#111). This slice ships the reserved `/api/health` aggregator + the one uncovered layer: report-artifact freshness.
**Plan:** `docs/superpowers/plans/2026-07-02-debt6-health-rollup-slice1c-plan.md`.

## 0. Scope
**In:** `GET /api/health` — the first-glance whole-app light: composes IN-PROCESS (R9 injectable adapters, no HTTP self-calls) over the three existing system assemblies (model-provenance, capture-health, tier-readiness) + a NEW **report-freshness layer** over the daily/weekly `_latest` producer artifacts, driven by checked-in config. **Out (Codex):** launchctl/LaunchAgent introspection (the artifact IS the observable); report backfill; any change to the three existing system endpoints or producers; UI card (later FE slice).

## 1. Report-freshness config — `app/config/report_freshness.json`
Mirrors the capture-cadence pattern (strict loader, fail-closed 503 family: absent/malformed/schema/empty/duplicate/unknown-tier/path-escape). Per artifact: `artifact_id`, `path` (repo-relative POSIX, confined), `producer` (script path, evidence-style existence), `cadence: daily|weekly` (R1: no `manual` — promotion-cadence artifacts are out of freshness scope), `scheduled_time_local`, `grace_hours`, **`tier: core_substrate|daily_diagnostics|auxiliary`** (Gemini's amber-blindness fix), `min_size_bytes` (seed A floor), `timestamp_field` (optional embedded created_at key), `dormant_ok: bool` + `season_windows` reuse (explicit config, never inferred — Codex; realized-outcome off-season = `dormant`, never stale). Root: `timezone` (IANA), `config_version`.

**Initial coverage — REAL artifacts, path/producer/timestamp pinned (Codex R2/R3/R4; all paths verified on disk 2026-07-02 EXCEPT realized_outcome, which is intentionally absent/gitignored off-season — exactly why it carries `dormant_ok`). The REPORT artifact is the freshness observable (R3); payload companions are out of Slice 1c. Trust-surface artifacts are DROPPED from freshness coverage (R1 — manual promotion cadence is not freshness; already guarded via provenance/tier-readiness):**

| artifact_id | path | producer | cadence/tier | timestamp_field |
|---|---|---|---|---|
| pvo_refresh | `app/data/model_capture/pvo_refresh_latest_report.json` | `scripts/run_pvo_refresh.py` | daily 09:30, **A** | none — mtime only (no top-level timestamp; disclosed fallback) |
| feature_refresh | `app/data/features_runtime/feature_refresh_latest_report.json` | `scripts/run_feature_refresh.py` | daily 09:15, B | `generated_at` |
| what_changed | `app/data/what_changed/what_changed_latest_report.json` | `scripts/run_what_changed_report.py` | daily 09:45, B | `generated_at` |
| roster_capacity | `app/data/roster_capacity/roster_capacity_latest.json` | `scripts/run_roster_capacity_audit.py` | daily, B | `created_at` |
| league_opportunity | `app/data/valuation/league_opportunity_latest.json` (TRACKED — corrected path) | league-opportunity producer | daily, **C** | `captured_at` |
| realized_outcome | `app/data/realized_outcome/scorecard_latest.json` (corrected at T4 — the route/producer/LaunchAgent truth; the draft table guessed a stale filename) | `scripts/run_realized_outcome_scoring.py` | weekly Tue, C, `dormant_ok` off-season | none — mtime only when present |

## 2. Freshness semantics (pure evaluator)
- **Timestamp precedence (Codex):** embedded `timestamp_field` wins when present+valid; absent → file mtime with `mtime_fallback` disclosed; present-but-malformed → `degraded` for that artifact (never a silent fallback).
- **Timezone-aware everywhere** (seed B): comparisons in the config IANA zone via the injected clock; DST-safe.
- **Grace honesty (seed C):** past scheduled time but within grace AND no new artifact → `freshness_overdue` (disclosed, not yet degraded); past grace → `stale` (tier-weighted). Never a flat "healthy" during an overdue window.
- **Empty-shell floor (seed A):** fresh-by-time but `size < min_size_bytes` (or unparseable when `timestamp_field` declared) → `corrupt_or_empty`, degraded per tier.
- **Dormancy:** `dormant_ok` + season window → `dormant` status, never stale, basis disclosed.

## 3. Rollup contract — `GET /api/health` (OpenAPI tag: `system` — Codex R5)
Root: `overall_status: ok|degraded` (**never blocked — observability, not a gate**; resolves the Gemini "critical" float toward the standing freshness rule) + **`worst_affected_tier: core_substrate|daily_diagnostics|auxiliary|null`** (machine-readable red-vs-amber for the UI without a gating state) + per-subsystem nodes (`model_provenance`, `capture_health`, `tier_readiness` — status echoes + adapter fail-closed: any adapter exception → that subsystem `unavailable` → degraded, 200, never a 500 — seed D guard-of-guards) + `reports[]` (per-artifact status/basis/age/disclosures) + mandatory **`disclaimer`** (Gemini copy): "System health reflects pipeline completion, artifact freshness, and model provenance verification. It does not evaluate model accuracy or guarantee trade edge." + `decision_supported: false` recursive.
- **Tier aggregation (Gemini):** Tier-A deviation → `degraded` + `worst_affected_tier=core_substrate`; Tier-B → `degraded` + `daily_diagnostics`; **Tier-C staleness NEVER degrades the root** — quiet `info` disclosures only. Subsystem `unavailable`/degraded maps: provenance/capture = A; tier-readiness = B.
- Only the endpoint's OWN config family 503s (sanitized fixed body). Strict models, `extra="forbid"`, banned-vocabulary rules carry over.

## 4. Seeds (RED)
Gemini A (empty-shell), B (tz/DST), C (grace overdue), D (guard-of-guards 200) + healthy-all-green; per-tier rollup rows (C-stale stays ok; B-stale degrades amber; A-stale degrades core); dormant realized-outcome; malformed embedded timestamp degrades; mtime-fallback disclosed; weekly cadence window; config 503 family + path confinement; disclaimer exact-copy + recursive false + no banned vocabulary; injectable clock boundary rows.

## 5. Resolved (kickoff)
Codex boundaries all adopted (thin in-process /api/health; config-driven artifact-observed; timestamp precedence; explicit dormancy; ok|degraded root with own-config-503-only; scope exclusions). Gemini tiering adopted with the root-enum resolution above; disclaimer verbatim; seeds A–D encoded.
