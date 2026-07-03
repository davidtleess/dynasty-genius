# DEBT-6 Slice 1c — Whole-App Health Rollup — Build Plan

**Spec:** `docs/superpowers/specs/2026-07-02-debt6-health-rollup-slice1c-design.md`.
**Branch:** `feature/debt6-health-rollup` (on David's authorization).
**Status:** DRAFT — HELD pending cockpit redline CLEAR + Codex RED + per-step authorization.

## Build sequence (Codex RED → Claude GREEN → dual-CLEAR → David-gated commit → zero-divergence, per task)
- **T1 — Config + models + loader:** `app/api/routes/system_health_models.py` (strict models; `ReportFreshnessConfig` family with tier/dormancy/min-size/timestamp-field; response models incl `worst_affected_tier`, `disclaimer`, recursive `decision_supported: Literal[False]`); fail-closed `load_report_freshness` (503 family incl unknown tier + path confinement). RED: loader family + extra-forbid + vocabulary.
- **T2 — Pure freshness evaluator + tier rollup:** artifact facts (exists/size/timestamps injected) + config + clock → per-artifact status (`fresh|freshness_overdue|stale|corrupt_or_empty|dormant|missing`) with disclosed bases; tier aggregation to `overall_status` + `worst_affected_tier` (C never degrades). RED: spec §4 evaluator rows via constructed inputs.
- **T3 — Adapters + route + wiring:** three subsystem adapters (injectable, guard-of-guards fail-closed to `unavailable`); artifact reader (repo-root-confined, mtime + embedded-timestamp extraction, size floor); `system_health.py` route `GET /api/health` + `app/main.py`. RED: HTTP layer incl seed D 200-never-500, sanitized 503, disclaimer copy.
- **T4 — REAL `app/config/report_freshness.json` + OpenAPI codegen + full closeout:** real coverage per spec §1 (verify each real artifact path + producer script); live smoke (expect honest current reality); `verify_sprint_closeout --base origin/main` ENFORCE PASS; push/PR checkpoint.

## Redline round resolved (2026-07-02, Codex R1–R5)
- R1 trust-surface DROPPED from freshness coverage (promotion cadence ≠ freshness; cadence enum stays daily|weekly) · R2/R4 real paths + per-artifact timestamp table pinned in spec §1 (pvo mtime-only; league_opportunity at the corrected `app/data/valuation/` tracked path) · R3 report artifact = the freshness observable · R5 `/api/health` under the `system` tag.
