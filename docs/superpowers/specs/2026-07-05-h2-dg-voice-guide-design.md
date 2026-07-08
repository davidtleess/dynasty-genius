# H2 DG Voice Guide — Design Spec

**Date:** 2026-07-05 · **Author:** Codex (technical reviewer), integrating Gemini PM draft · **Status:** DRAFT v0.3 — Gemini acknowledged; pending Claude final reset-package reconciliation and David ratification.
**Program:** Horizon 2 frontend reset.
**Related artifacts:** `docs/superpowers/specs/2026-07-05-h2-frontend-reset-design.md`; `docs/superpowers/plans/2026-07-05-world-class-frontend-capability-plan.md`; `docs/strategies/2026-07-05-world-class-frontend-research-brief.md`.

## 1. Principle

Every character on the Dynasty Genius screen speaks to David as a competitive dynasty manager, not an engineer reading backend state. Data contracts, exact values, and raw identifiers remain preserved for auditability, but they live in receipts, title attributes, diagnostics, and copied audit values.

Primary UI copy is football, fantasy, and dynasty-manager prose.

## 2. Vocabulary Map

These backend or system terms are banned from primary visible UI labels. Receipts, title attributes, developer diagnostics, and copied audit text may carry exact terms when they preserve auditability.

| Backend / system term | Primary manager-language replacement |
| --- | --- |
| `model_vintage`, Model Vintage | Projection Update; Model Edition |
| `registry_version`, Registry Version | System Version; Platform Build |
| `capture_streak`, Capture Streak | Days Synced; Daily Market Sync |
| `last_capture`, Last Capture | Prices Captured; Last Price Update |
| Database / SQLite Store / capture store | League Ledger; Market Feed |
| Settlement | Finalized; Synced |
| structural_context | Roster Posture |
| `decision_supported` | Descriptive only; not decision-grade |
| caveat tokens | Active Caveats; Context Notes |
| artifact | Build File; Data Cache |
| schema | Data Format; Verification Rules |
| snake_case values | translated prose or Title Case label |

## 3. Daily Tape Lines

The old substrate language was:

```text
Registry version: 4 / Model vintage: ok / Capture streak: 32 / Status: ok
```

The manager-language tape uses these patterns instead:

- **Healthy sync:** `Market Sync Active: 32 consecutive days tracked · Projection Update: July 5, current · Status: Synced`
- **Degraded sync:** `Partial Market Sync: some inputs are being verified · Player values use the latest verified football inputs · Status: Degraded`
- **Stale prices:** `Market Sync Delayed: market prices last captured yesterday · Player values still come from football inputs, not market prices · Status: Delayed`
- **Offline feed:** `Market Feed Offline: league connection unavailable · Showing the last verified roster values · Status: Offline`
- **Quiet day:** `Market Sync Active: projections are current · League Activity: Quiet, no player values shifted in the last 24 hours · Status: Synced`

The exact raw source timestamp remains available in a title attribute or receipt.

Market-sync copy describes the freshness of the market overlay only. It must never imply that market prices feed player-value calculations.

## 4. Caveat And Status Tone

Tone is objective, un-alarmist, and specific.

Do:

- state what is known;
- state what is unavailable;
- state what fallback is being used;
- keep disclosure language neutral.

Do not:

- use panic words such as `critical`, `danger`, or `corrupt`;
- use color-emotion words such as red/green in copy;
- imply a player action;
- turn data state into a recommendation.

Example:

```text
Sleeper connection offline. Showing cached roster data from July 5.
```

## 5. Metric Name Posture

Default until David ratifies otherwise: primary copy translates the metric, while the technical symbol lives in the receipt/title.

- Primary phrase: `value over a replacement starter`
- Receipt/title: `xVAR — Value Above Replacement`
- Primary phrase: `share of roster value`
- Receipt/title: `DVS — Dynasty Value Share`

Open David decision: whether xVAR and DVS become taught product vocabulary that may appear as compact primary table labels, or remain receipt/title symbols only.

## 6. Enforcement

The rendered-copy tripwire scans primary visible text and fails on:

- snake_case;
- route names;
- raw backend tokens;
- ratified system nouns from the blocklist;
- literal `decision_supported`.

Exemptions:

- receipt bodies;
- title attributes;
- developer zone diagnostics;
- copied audit values;
- test fixtures that explicitly assert the tripwire.

## 7. Self-Review

- Placeholder scan: no unfinished placeholder markers.
- Governance check: No-Verdict line preserved; `decision_supported` maps to the existing disclosure, not to "Audit Ready."
- Market-wall check: no tape line states or implies that market prices feed player-value calculations.
- Scope check: voice guide only; no runtime implementation.
