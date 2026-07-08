# H2 Increment 1 — The Designed Daily Open (Proving Slice)

**Status:** DRAFT v3 — series schema + baseline_roster_rows pinned (Codex round-2); section order = model-first (Gemini nudge finding, adopted). Claude-authored under the David-ratified rethink v3 (hybrid ruling: primitives → Daily Open proof → Asset Board). Awaiting cockpit dual review → Codex RED → GREEN → impeccable critique → David preview. NO tree mutation until David authorizes the build.
**Inputs:** Gemini Increment-1 framing pass (2026-07-06, ledger) — all four parts integrated below; Codex pre-spec pins — all adopted; Increment-0 primitives (dual-cleared, uncommitted) + the LIVE asset cache (261/273 rostered headshots, 19MB local).
**The bar:** this is the surface David judged twice and failed twice. It ships to his eyes only after the impeccable critique flow scores it against the DN benchmark. The preview package = live surface + captures + benchmark-delta.

## 1. What it is

The Daily What-Changed surface rebuilt as a **tape of AssetRows** — David's morning open. First five seconds answer, in order (Gemini framing): (1) is the data fresh, (2) did anything move, (3) WHO moved and by how much — faces first, numbers focal, receipts one press away.

## 2. Composition (all Increment-0 primitives, now with real assets)

- **Header:** "Daily What-Changed — Descriptive Tape · Superflex · PPR" + capture freshness stamp. Stale ≥26h (the 02 law's threshold) → non-urgent amber caveat badge with the age stated.
- **Changed rows as AssetRows:** rank-in-cohort · PlayerIdentity (REAL cached headshot via the local pipeline, initials fallback for the 11 rookies — byte-stable row dimensions both ways) · focal delta (MetricCell row-focal) · model lane and market lane columns with EQUAL visual weight — the inactive lane renders an explicit flat dash/0, never blank, never the other lane's color · sparkline over the real PIT series terminating at the Hard Right Edge · quiet utilization driver text (subordinated, neutral) · ReceiptTrigger.
- **Team-color binding — full drift contract (Codex F1):** generator `scripts/generate_team_color_module.py` reads `app/config/team_colors.json` → committed output `frontend/src/generated/teamColors.ts` carrying `schema_version` + `source_sha256` of the JSON; a contract test canonically regenerates and FAILS on any divergence (the committed-openapi drift-gate pattern — one source of truth, enforced). Frontend imports ONLY the generated module. Applied as avatar ring/dot accents only; per-theme contrast rule auto-selects secondary/adjusted (axe-verified).
- **Row data source path (Codex F2):** the what-changed REPORT PRODUCER is extended (not the FE): each delta row gains optional-nullable `team_id` (from the sleeper snapshot `players[].player.team` via the existing identity join) and per-lane series with a PINNED schema (Codex round-2): `model_series` and `market_series`, each `{basis: string, points: [{date: "YYYY-MM-DD", value: number}]} | null` — points strictly ascending by date, min 2 / max 30 (the 30-day named window), lane ownership carried by the field name (a row never mixes lanes in one series), and the Hard Right Edge basis = the LAST point's date (the SVG terminates there; empty grid beyond; the last date must be ≤ the report's capture date — a future-dated point is a producer defect). Fail-closed at every step: unresolved identity → `team_id: null` → neutral ring; absent/short/malformed series → `null` → the existing SeriesSlot pending state (never a fabricated line). Old artifacts stay loadable (fields optional); committed tests monkeypatch the report path (CI never reads gitignored data).
- **Sections (order = Gemini nudge finding, adopted):** MODEL movement first (the rational anchor), market movement second (the overlay, read against the model), new caveats third — counts-first, rows behind each; suppressed named-drop slice stays suppressed (existing law). Rationale: market-first would anchor the morning read on crowd noise before the model's evaluation — against the Prime Directive.

## 3. Key states (each a RED seed)

1. **Quiet day (Codex round-2 resolution — producer extension adopted):** the producer gains a named optional `baseline_roster_rows` section — David's roster as AssetRow-shape rows (identity + current values, flat lanes, no deltas). Quiet state = the designed message ("No valuation deltas observed since the last capture (checked {time})") + those rows. `baseline_roster_rows` absent (old artifacts, CI fixtures) → message alone, no fabricated rows. The existing counts/summaries baseline sections are untouched.
2. **Single mover:** structure holds; the row does not balloon.
3. **Stale (basis pinned, Codex F3):** staleness = the report's own `generated_at` age ≥26h (the surface judges its own data truth; system-level capture-health stays the separate trust surface — no duplication); missing/unparseable `generated_at` → treated stale + caveat. Effect: header badge + stale-desaturation class on rows.
4. **All-market day / all-model day:** inactive lane flat-dash across every row; zero cross-lane color bleed (token-law scan).
5. **Rookie rows:** initials disc, identical row height/alignment to photo rows.
6. **Missing/malformed artifact:** existing fail-closed patterns untouched (monkeypatched paths in CI — never a gitignored read in committed tests).

## 4. Evidence + critique gate (BEFORE David)

Playwright bundle folded into `visual-smoke.spec.ts`: desktop/mobile/**primitive-specific focus** (Codex's raised standard) captures + axe `violation_count==0` asserted. THEN the impeccable **critique** flow runs on the live surface with real data — scored, defects fixed, re-scored — and a benchmark-delta vs the DN screenshots written. Only then does the preview go to David. Overclaim check (Gemini): descriptive tape, no adds/cuts/buys/sells, no extrapolation past the Hard Right Edge, `decision_supported=false` untouched.

## 5. Out of scope

Asset Board (composes after David's visual CLEAR here); named tier bands (roadmap Steps 1–3); named-drop slice; Inspector rebuild (existing inspector remains; its redesign rides the Asset Board increment).
