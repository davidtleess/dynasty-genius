# BUILD-1 Tier-1 Graduation — Increment 2 — Build Plan

**Spec:** `docs/superpowers/specs/2026-07-02-build1-tier1-increment2-design.md`.
**Branch:** `feature/build1-tier1-increment2` (on David's authorization).
**Status:** DRAFT — HELD pending cockpit redline CLEAR + David's per-surface ratifications + Codex RED + per-step authorization.

## Single task cycle (registry + tests only)
**T1 — Codex RED → Claude GREEN → dual-CLEAR → David ratifies both graduations (stamps) → David-gated commit/push/PR → merge on CI green → zero-divergence.**
- RED: extend `tests/contract/test_system_tier_readiness_t4.py` (or a sibling `_t5.py`, Codex's call) with spec §2 rows — 3-surface registry contract, per-surface semantic tokens, R5 null-ratification behavior over temp registries.
- GREEN: add the two `app/config/tier_readiness.json` entries (spec §1; `ratified_date: null` until David's stamps). NO other module changes (machinery-diff guard).
- Verification: tier slice + drift gate + full closeout ENFORCE PASS; live smoke pre-stamp (`awaiting_david_ratification` ×2 + roster_capacity `_limited`) and post-stamp (three `_limited`, dormant mif each, preconditions green).

## Deferred/held (documented, not built)
Trade Lab (FE mitigation precondition in spec §0) · League Pulse (held indefinitely) · What-Changed volatility baselines (surface enhancement, not a gate).
