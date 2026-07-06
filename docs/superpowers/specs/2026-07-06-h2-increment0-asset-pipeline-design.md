# H2 Increment 0 — Asset Pipeline + AssetRow Primitive Extensions (Design Spec)

**Status:** DRAFT v2 — Claude-authored under the David-ratified rethink (`2026-07-06-h2-frontend-rethink-design.md` v3); v2 integrates Codex's 8 RED-design findings (paths/schema precision, cache-key pin, split failure seeds, evidence-contract wiring, axe true assertion, motion-seed deferral, team-color semantic guard). Awaiting Codex v2 confirm → Codex RED → GREEN → dual-CLEAR → David preview gate. NO tree mutation until David authorizes the build.
**Framing input:** Gemini Increment-0 framing pass (2026-07-06, ledger): manager moment = parallel visual recognition under morning cognitive fatigue; risks = familiarity bias, franchise halo, lane collision; seeds integrated in §4.
**Parent rulings honored:** hybrid proving slice (this increment builds the primitives that Increment 1 proves on the Daily Open); DG orthogonal position hues now + the measured Sleeper-adjacent candidate sheet (§4); lexicon stays gated (no named tier labels anywhere in this increment).

## 1. Scope

Three deliverables, no visible surface change yet (the Daily Open flip is Increment 1):

**A. Governed asset pipeline** — `scripts/build_player_asset_cache.py` (name provisional):
- Mirrors Sleeper CDN headshots (`sleepercdn.com/content/nfl/players/thumb/{sleeper_player_id}.jpg`) into a gitignored local store. **Cache key = `sleeper_player_id` (Codex F2 resolution):** the asset source is Sleeper and every universe player carries one, while `dg_player_id` is NULLABLE today (`app/services/roster_auditor.py:199` falls back `dg_player_id or sleeper_player_id`). Render-time lookup goes through the identity layer's dg→sleeper mapping; the asset layer never invents identity (north-star rule).
- **Exact paths (Codex F1):** cache root `app/data/assets/headshots/{sleeper_player_id}.jpg` (gitignored); manifest `app/data/assets/headshot_manifest.json` with schema `{schema_version, fetched_at, source_url, sha256, http_status, bytes}` per entry; team map `app/config/team_colors.json` (checked in, not cached).
- Fetch-time only mirroring; the app NEVER hotlinks at render time (offline-safe; private single-user use keeps trademark exposure in the low-risk class per research).
- NEW irreplaceable-store ruling: the cache is REBUILDABLE from public sources → `backup_manifest.json` EXCLUSIONS entry `{path: "app/data/assets/", reason: "rebuildable from public Sleeper CDN; not irreplaceable"}` — keeps the backup amendment's coverage law honest.
- 32-team color map: static, checked-in JSON (`app/config/team_colors.json`): `{team: {primary, secondary}}` in OKLCH, with a per-theme contrast-resolution rule (auto-select secondary or adjust L/C when primary fails 3:1 as an accent against the active surface — Gemini seed).

**B. Primitive extensions** (per rethink v3 §5 / Codex R1–R3):
- `PlayerIdentity`: NEW props — headshot rendering (`imageSrc` resolved from the local cache), team mark, positional rank. Fallback chain: headshot → initials-on-position-hue disc → neutral silhouette; a broken image NEVER renders. Team mark = small color dot or avatar ring — NOT a left-border stripe (impeccable side-stripe ban overrides Gemini's 3px-border suggestion) and NEVER a row background fill.
- `SpreadBar`: lane prop (`lane: "model" | "market"`) with token-law tests; default stays model (backward compatible); market lane consumes `--dg-market` family only.
- NEW compact row-value treatment: `MetricCell` emphasis variant (one step larger, heavier, tabular numerals) — ValueHero explicitly stays OUT of 32px rows (Codex R2).
- Team accent is driven by canonical `team_id` from our DB, never by headshot image metadata (Gemini stale-jersey seed).

**C. Position-hue candidate sheet** (evidence artifact for David, not code):
- For each Sleeper-adjacent candidate hue: OKLCH values, angular distance to model 255 / market 75 (law: ≥35°), banned-arc check (red/green ranges), AA contrast on both theme surfaces, side-by-side screenshot samples vs current DG hues.
- Deliverable: a one-page comparison document; David chooses; NO token change in this increment.

## 2. Explicitly OUT of scope

Daily Open changes (Increment 1); any named tier labels (roadmap Steps 1–3); any new API surface; Sleeper transaction ingest (edge board E6); logo files (colors + abbreviations only).

## 3. Contracts & invariants

- All committed tests run over temp fixtures + dependency injection — no gitignored cache required in CI (the What-Changed CI lesson).
- Asset script is fail-closed: missing identity mapping → skip + count in the run report (never guess); network failure follows seed 2's split invariant exactly (prior cache → existing bytes + `stale`/`refetch_failed` mark; no prior cache → fallback chain + degraded/missing-asset report); no deletes of previously cached assets without explicit flag.
- `decision_supported=false` untouched everywhere; no copy changes in this increment beyond alt-text (alt text = player name only, no editorializing).
- Evidence bundle NON-EXEMPT, wired into the EXISTING contract (Codex F5/F6): the primitive capture page is a real Vite-served route captured by Playwright under the shipped browser-evidence discipline — **DECIDED (Codex F5 preference, adopted): folded into `frontend/e2e/visual-smoke.spec.ts`** (preserves the current evidence contract hardcoded in `playwright.config.ts` and the browser-evidence-gate RED; a multi-spec generalization is a separate deliberate infrastructure step if ever wanted). Named artifact paths (desktop/mobile/focus/axe + primitive-delta notes); no gitignored `app/data` reads in committed tests. **axe=0 is a TRUE ASSERTION for the capture page** — the current harness records `violation_count` without asserting; the RED must fail when `violation_count != 0`.

## 4. Falsification seeds (RED input — Gemini framing + research + Codex R1–R3 and F1–F8)

1. Player with no headshot (rookie/prospect/DEF) → initials disc in position hue, then silhouette; layout byte-stable across all three fallback classes.
2. CDN timeout/offline at fetch time — TWO cases (Codex F3): (a) NO prior cache → render fallback chain + degraded/missing-asset report; (b) prior cache exists → existing bytes served + entry marked `stale`/`refetch_failed`. RED uses an injected HTTP fetcher + temp dirs; NO live Sleeper calls in committed tests.
3. Corrupt/zero-byte image — TWO layers (Codex F4): (a) build-time validation rejects zero-byte/non-image bytes and marks for refetch; (b) render-time `onError` swaps to the fallback chain with no broken-image glyph ever painted.
4. Team primary fails contrast on dark surface → secondary/adjusted accent auto-selected; assert specific known-bad teams.
5. Traded player: DB team ≠ jersey in photo → accent follows DB `team_id`.
6. Identity mapping missing sleeper_id for a canonical player → skipped + reported, not guessed.
7. `SpreadBar lane="market"` renders zero `--dg-model` tokens (and vice versa); token-law scan extended.
8. PlayerIdentity with all-new props omitted → renders exactly as today (backward compatibility with every existing call site).
9. Hue-sheet candidates: any candidate within 35° of either lane or inside a banned arc is flagged FAIL in the sheet itself.
10. Initials disc for names with non-ASCII/single names/long names → stable 2-char rule disclosed.
11. axe on the capture page: img alt semantics, contrast, focus order — `violation_count == 0` ASSERTED (F6).
12. ~~Reduced-motion~~ DEFERRED to Increment 1 (Codex F7: vacuous here — Increment 0 introduces no shimmer/skeleton; the seed rides with Increment 1's loading states).
13. Team-color semantic guard (Codex F8): real NFL palettes may sit in red/green arcs, so the verdict-hue token ban does NOT run against `team_colors.json`; instead assert team colors are IDENTITY-ONLY — never consumed by model/market/status/delta styles, never row background fills, never named red/green in UI copy or class names.

## 5. Compounding lens

Daily-login value: none directly (infrastructure) — honest answer; the value lands in Increment 1, which this unblocks. Refresh cadence: asset cache refresh weekly off-season / on roster-change triggers in-season (headshots/teams change slowly; cadence matched to real change rate). Compounding: the canonical-id-keyed asset cache + team map become permanent identity infrastructure every future surface reuses.
