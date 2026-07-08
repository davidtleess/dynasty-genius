# H2 Increment 0 Primitive Capture Delta

**Increment:** 0 (asset pipeline + primitive extensions), spec `docs/superpowers/specs/2026-07-06-h2-increment0-asset-pipeline-design.md` v2.
**Status:** GREEN complete, evidence recorded; **commit blocked until David preview** of this bundle (the preview gate is the point — nothing visual ships sight-unseen).

## DG evidence bundle

Captured by the shipped Playwright contract (`frontend/e2e/visual-smoke.spec.ts`, fold-in per Codex F5 — no goldens, no gitignored reads):

- frontend/artifacts/visual/asset-primitive-capture-desktop.png
- frontend/artifacts/visual/asset-primitive-capture-mobile.png
- frontend/artifacts/visual/asset-primitive-capture-focus.png
- frontend/artifacts/visual/asset-primitive-capture-axe-report.json

## Asset pipeline behavior

`scripts/build_player_asset_cache.py` — contract tests green (13/13 incl. evidence gate): sleeper-keyed cache + provenance manifest (`headshot_manifest.v1`); identity skips reported never guessed; no-prior-cache network failure → missing-asset report; prior-cache failure → bytes preserved + `refetch_failed`; zero-byte/non-JPEG rejected (`invalid_image_ids`) with prior cache untouched; orphan assets preserved (no delete path exists). `app/config/team_colors.json` (32 teams, OKLCH primary/secondary) checked in; `backup_manifest.json` exclusions entry added (rebuildable store).

## Primitive extensions

- PlayerIdentity: cached-image rendering (local src only), onError → accessible fallback (no broken glyph), stable initials rule (unicode/single/long names), team mark (neutral ring in Increment 0 — color binding deferred; frontend may not read team_colors.json per RED ban), positional rank. Backward compatible: all prior call sites render unchanged.
- SpreadBar: `lane` prop (`model` default / `market`), lane-scoped accent property; CSS contract asserts the 500-char isolation windows — a market spread can never inherit model blue.
- MetricCell: `emphasis="row-focal"` variant — the one focal number per row, inside 32px density; ValueHero untouched and out of rows.

## Hue candidate sheet

Measured against token law (banned red ≤30/≥350, banned green 120–160, ≥35° from model 255 and market 75). sRGB→OKLab per Ottosson; community-replica Sleeper hexes (candidate family, unverified against Sleeper source):

| Candidate | OKLCH | dist model 255 | dist market 75 | Verdict |
|---|---|---|---|---|
| QB `#FF2A6D` | L0.65 C0.24 h10.2 | 115.2 | 64.8 | FAIL — banned red arc |
| RB `#00CEB8` | L0.76 C0.14 h181.5 | 73.5 | 106.5 | PASS |
| WR `#58A7FF` | L0.72 C0.15 h252.8 | **2.2** | 177.8 | FAIL — model collision |
| TE `#FFAE58` | L0.81 C0.14 h65.2 | 170.2 | **9.8** | FAIL — market collision |
| K `#BD66FF` | L0.68 C0.22 h307.7 | 52.7 | 127.3 | PASS |
| DEF `#7988A1` | L0.62 C0.04 h260.6 | **5.6** | 174.4 | FAIL — model collision |

**Sheet conclusion for David:** a "Sleeper-adjacent" family is largely not constructible under lane law — 4 of 6 hues are illegal (QB/WR/TE/DEF), and shifting them far enough to be legal destroys the muscle-memory familiarity that motivated them. The legal borrowable subset is RB teal + K purple. David's ruling (DG orthogonal hues now) stands as the evidence-supported end state; a partial adoption (RB teal only) is the one open styling question, deferred to Increment 1's critique round.

## Visual audit

Performed by the implementer on the actual captures (both viewports), per David's standing directive:
- Identity fallback chain shows three visibly distinct states (portrait image / initials disc / initials disc) — first-pass defect (1×1 JPEG rendering as a blank disc) found by eye and fixed with a visible SVG portrait stand-in.
- Lane isolation is visible, not just tested: model spread dot renders blue, market dot renders amber.
- Row-focal 94% clearly dominates its sibling metric at 32px density.
- Team mark reads as a neutral ring (second-pass fix: 8px→10px + stronger ring) — colorless by contract this increment.
- Mobile: rail stacks above content, all three sections readable, focal hierarchy intact.
- Named defects remaining: None.

## Axe result

`asset-primitive-capture-axe-report.json`: violation_count: 0 — asserted in-spec (`expect(axeResults.violations).toEqual([])`), not merely recorded. Daily-open bundle also green (2/2 Playwright).

## David preview gate

Commit blocked until David preview. This bundle (4 artifacts + this delta) is the preview package; on David's visual CLEAR the Increment-0 tree commits via the normal cycle (cockpit dual-CLEAR already in flight), and Increment 1 (the Daily-Open proving slice) opens per the ratified hybrid ruling.
