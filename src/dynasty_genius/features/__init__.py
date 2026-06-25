"""F-feature-refresh — engine_b feature regeneration (read/derive only).

Regenerates the engine_b feature set from fresh source data so model outputs can
change over time. Model weights are NEVER touched here (no ``.fit()``, no training
entrypoints, no model-artifact writes) — this package only derives features.

Design spec: docs/superpowers/specs/2026-06-25-f-feature-refresh-design.md
Plan: docs/superpowers/plans/2026-06-25-f-feature-refresh.md
"""
