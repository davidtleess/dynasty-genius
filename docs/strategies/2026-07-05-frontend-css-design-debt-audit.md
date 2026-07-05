# Frontend CSS / Design Debt Audit

**Date:** 2026-07-05  
**Author:** Codex (technical reviewer)  
**Status:** DRAFT v0 — local evidence layer for H2 frontend reset.  
**Branch:** `feature/horizon2-i2-daily-open` with parked I2a work still dirty.

## 1. Purpose

Explain why David's I2a preview looked bad using current repo evidence, not taste language alone.

This audit is read-only evidence. It does not authorize a broad CSS rewrite.

## 2. Commands Run

```bash
find frontend/src -name '*.css' -maxdepth 4
rg -n "#[0-9A-Fa-f]{3,8}\\b|oklch\\(|rgb\\(|rgba\\(|hsl\\(|hsla\\(" frontend/src --glob '*.css' --count
rg -n "font-size:" frontend/src --glob '*.css' --count
rg -n "font-family:" frontend/src --glob '*.css' --count
rg -n "border-radius:" frontend/src --glob '*.css' --count
rg -n ":focus-visible|--dg-focus" frontend/src --glob '*.css' --count
rg -n "var\\(--dg-(bg|surface|surface-raised|border|text|text-muted|focus|caveat|font|motion)" frontend/src --glob '*.css' --count
```

## 3. Findings

### C1 — Raw Color Debt Is Widespread

Raw color literals or raw OKLCH values appear across 11 CSS files:

| File | Count |
|---|---:|
| `frontend/src/styles/tokens.css` | 31 |
| `frontend/src/trust/TrustConsole.css` | 26 |
| `frontend/src/what-changed/DailyWhatChanged.css` | 16 |
| `frontend/src/system-health/SystemHealthCard.css` | 15 |
| `frontend/src/roster-capacity/RosterCapacitySandbox.css` | 9 |
| `frontend/src/realized-outcome/RealizedOutcomeScorecard.css` | 7 |
| `frontend/src/league-pulse/LeaguePulse.css` | 5 |
| `frontend/src/player/PlayerDetail.css` | 5 |
| `frontend/src/roster/RosterAudit.css` | 2 |
| `frontend/src/project/ProjectTracker.css` | 1 |
| `frontend/src/trade/TradeLab.css` | 1 |

The tokens file is expected to define color values. The problem is that component CSS still carries raw light-era palettes. Examples include `#fafbfc`, `#eef0f3`, `#55606f`, `#1f2430`, and neutral OKLCH values outside semantic aliases.

**Why this made I2a bad:** setting `data-theme="dark"` changed global tokens, but many surface components kept local light backgrounds, borders, and copy colors. The result is not a designed dark theme; it is a theme collision.

### C2 — Semantic Token Consumption Is Thin And Uneven

Semantic token use appears in only a subset of files:

| File | Count |
|---|---:|
| `frontend/src/shell/AppShell.css` | 6 |
| `frontend/src/what-changed/DailyWhatChanged.css` | 4 |
| `frontend/src/league-pulse/LeaguePulse.css` | 4 |
| `frontend/src/shell/TrustStrip.css` | 4 |
| `frontend/src/command/CommandPalette.css` | 3 |
| `frontend/src/styles/tokens.css` | 3 |
| `frontend/src/roster/RosterAudit.css` | 2 |
| `frontend/src/shell/ParkedSurfaceCard.css` | 1 |
| `frontend/src/system-health/SystemHealthCard.css` | 1 |

Several major surfaces have little or no semantic-token consumption for visual structure.

**Why this made I2a bad:** the I1 semantic alias work was technically real but not yet load-bearing across the app.

### C3 — Font Scale Is Fragmented

`font-size:` appears in 14 CSS files, with many local literal sizes:

| File | Count |
|---|---:|
| `frontend/src/trust/TrustConsole.css` | 14 |
| `frontend/src/what-changed/DailyWhatChanged.css` | 13 |
| `frontend/src/roster-capacity/RosterCapacitySandbox.css` | 6 |
| `frontend/src/realized-outcome/RealizedOutcomeScorecard.css` | 5 |
| `frontend/src/system-health/SystemHealthCard.css` | 4 |
| `frontend/src/shell/AppShell.css` | 4 |
| `frontend/src/league-pulse/LeaguePulse.css` | 3 |
| `frontend/src/roster/RosterAudit.css` | 3 |
| other files | 1-2 each |

Many values are surface-local (`0.72rem`, `0.78rem`, `0.8rem`, `0.82rem`, `0.85rem`, `0.875rem`, `0.95rem`, `1rem`, `1.05rem`, `1.1rem`, `1.25rem`).

**Why this made I2a bad:** the app cannot feel like one premium terminal while every surface picks its own type rhythm.

### C4 — Focus System Is Effectively Missing

The focus scan finds only `frontend/src/styles/tokens.css` defining `--dg-focus`. No component CSS currently consumes `--dg-focus` or standardizes `:focus-visible` behavior.

**Why this made I2a bad:** a world-class dense-data instrument must show keyboard position and interaction affordance. DG has a focus token, but not a focus system.

### C5 — Radius And Motion Are Ad Hoc

`border-radius:` appears in eight component CSS files, with local values (`4px`, `6px`, `0.25rem`, `0.3rem`) rather than semantic radius tokens.

Motion is almost absent. The parked I2a work adds a `0.15s ease-out` daily settle animation in `DailyWhatChanged.css`, with reduced-motion handling, but there is no product-wide motion vocabulary.

**Why this made I2a bad:** isolated motion and local radii cannot create craft. They create isolated moments inside an inconsistent shell.

## 4. Diagnosis

The H2 visual failure is not that the color palette was wrong in isolation. The failure is that the app has no governed visual operating system.

The reset must therefore avoid a broad visual pass over existing surface CSS. Instead, it should:

1. add browser evidence before visual GREEN;
2. create DG primitives with strict token consumption;
3. add report-first CSS debt audits;
4. migrate touched surfaces through primitives and semantic tokens;
5. delay broad dark activation until token consumption is sufficient to avoid light/dark collisions.

## 5. Falsification Seeds For Reset Spec

1. If a visual GREEN claims dark theme readiness, raw light background values in touched component CSS must be absent or justified.
2. If a primitive is introduced under `frontend/src/ui/`, raw colors and local font families fail tests from day one.
3. If a visual change touches an interactive element, `:focus-visible` + `--dg-focus` behavior must be included.
4. If a surface gets a new animation, it must use motion tokens and reduced-motion handling.
5. If screenshot evidence shows a light panel on dark canvas, the visual GREEN is blocked even if DOM tests pass.

## 6. Reset Package Impact

This audit supports the order in `docs/superpowers/specs/2026-07-05-h2-frontend-reset-design.md`:

- browser evidence first;
- primitive layer second;
- report-first CSS token debt audit;
- constrained motion system;
- restarted daily open using parked I2a only as a parts donor.

## 7. Self-Review

- Evidence is from current repo scans and command output.
- Counts are file-level match counts, not semantic severity scores.
- The audit intentionally avoids code edits and broad refactor prescriptions.
