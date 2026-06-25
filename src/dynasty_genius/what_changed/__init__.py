"""War Room #2 — Daily "What Changed" diff.

A backend-first, descriptive day-over-day diff over the dual-capture PIT stores
(FantasyCalc market + model PVO) plus current structural context. Overlay only:
``decision_supported`` is always False, the model-vs-market divergence is
UNVALIDATED until a pre-registered validation, and no market field ever reaches a
model/PVO/feature/training path.

Design spec: docs/superpowers/specs/2026-06-24-war-room-2-daily-what-changed-diff-design.md
"""
