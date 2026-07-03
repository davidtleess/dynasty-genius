# System Trust & Freshness UI Card — Design Spec

**Date:** 2026-07-03 · **Author:** Claude (implementation lead) · **Status:** DRAFT v2 — round-1 findings integrated (Codex 8 patches; Gemini 2 safeguards + 1 out-of-scope companion ticket); pending round-2 cockpit confirmation
**Build name:** System Trust & Freshness UI card (AGENT_SYNC priority list). **David-facing name:** "System Diagnostics" (see §4 — the David-facing label must never say "Trust").

## 0. Objective and charter trace

The FE face of the completed trust stack (#107 provenance → #108 capture health → #109/#111 tier readiness → #112 whole-app light). Priority-list item ratified by David 2026-07-03 ("go to kick off").

**North-Star question served:** the daily PIT capture must be trustworthy *and David must be able to see that at a glance*. Gemini framing: at 9:45 AM ET, before acting on any surface, David's 5-second question is "are these numbers from last night's real ingest, or did my laptop sleep and I'm looking at 3-day-old data?" Today that answer lives only in a JSON endpoint. This card puts it in the shell.

**Compounding lens:** daily-login value = the first thing checked every login; refresh cadence = per page load (the backend rollup is cheap and in-process); compounding = the card renders whatever the trust stack learns to report — new report rows appear as config grows, no FE change (data-driven rows).

## 1. Scope

**FE-only render increment. No backend/contract change** (Codex scope read, 2026-07-03: `GET /api/health` already serves everything needed; generated Zod boundary — `zSystemHealthResponse` / `zSystemHealthErrorResponse` — already committed via PR #112 codegen).

- NEW `frontend/src/system-health/SystemHealthCard.tsx` + `SystemHealthCard.css`
- M `frontend/src/shell/AppShell.tsx`: mount the card in the shell header region **adjacent to, not inside,** `TrustStrip` (TrustStrip is model-grade/source-freshness — a different trust axis; merging them conflates model credibility with pipeline liveness, the exact mislead risk in §4)
- NOT in scope: any change to `app/`, `frontend/openapi.json`, generated clients; a deep trust-stack panel inside Model Trust Console (later increment if David wants it); drill-down FE surfaces for the three subsystem endpoints (they have no FE pages — v1 renders their ids/statuses with the endpoint path as disclosed text metadata, no dead links).
- **Out-of-scope companion ticket (Gemini R1, David-gated, separate PR):** `roster_capacity` and `league_opportunity` are manual producers reading `stale` on the live payload today. Per the PR #113 principle (config models the artifact's CHANGE cadence, not a poll schedule), their `app/config/report_freshness.json` entries may deserve recalibration (weekly / extended grace / seasonal `dormant_ok`). The card renders honest amber meanwhile — the fix is config truth, never watered-down UI.

## 2. Real-shape grounding (live in-process probe, 2026-07-03 ~10:31 ET)

`GET /api/health` → 200: `overall_status="ok"`, `worst_affected_tier=null`, `checked_at` ISO-UTC, `config_version=1`, `disclaimer` (exact Literal copy), `decision_supported=false`, 3 subsystem rows (`model_provenance`/`capture_health` core_substrate, `tier_readiness` daily_diagnostics; `basis="adapter_status:ok"`), 6 report rows. Real row shape: `{artifact_id, status, tier, basis, artifact_path, producer, observed_at, age_seconds, disclosures[], decision_supported}` — e.g. `pvo_refresh` `fresh`/`mtime_fresh` with disclosure `timestamp_source:mtime_fallback`; `feature_refresh` currently `dormant`/`dormant_ok_offseason` (PR #113). Enums (models file lines 30–41): overall `ok|degraded`; tier `core_substrate|daily_diagnostics|auxiliary`; report status `fresh|freshness_overdue|stale|corrupt_or_empty|dormant|missing`; subsystem `ok|degraded|unavailable`. **Nullable/absence realities the FE must handle:** `worst_affected_tier` null when ok; `observed_at`/`age_seconds` null for missing/dormant/corrupt rows.

## 3. Rendering contract

**States (TrustStrip precedent):** `loading` → "Loading system diagnostics…"; `unavailable` → neutral copy "System diagnostics unavailable — pipeline status unknown" (fired by network error, non-200-non-503, 200 that fails `zSystemHealthResponse.safeParse`, 503 whether or not its body parses as `zSystemHealthErrorResponse` — the 503 body's sanitized `message` MAY be shown only if the body parses with `zSystemHealthErrorResponse` (the model is `{error, message, decision_supported}` — Codex R1); raw/unparsed error text NEVER renders); `ready` → the card.

**Collapsed (the 5-second light):**
- Title "System Diagnostics", subtitle "pipeline & data freshness — not model accuracy".
- Root status rendered as the **verbatim enum value**; when `degraded`, the `worst_affected_tier` leads the line prominently — "degraded · core_substrate affected" — before any counts (Gemini R1 safeguard: a core failure must not read benign inside a mostly-fresh count). **Per-status counts are MANDATORY in the collapsed view whenever `reports.length > 0`** (Codex R1 #3: honesty may not be pushed into the expanded details), covering every present status by exact enum or exact humanized text, e.g. "6 reports: 3 fresh · 1 dormant · 2 stale". **No editorial aggregate copy** — never "All Systems Fresh" (with `ok` + an overdue/dormant row, "all fresh" is a lie; verbatim enum + counts cannot overclaim). `reports: []` renders "no report freshness rows reported" — never fabricated healthy counts (Codex R1 #5).
- The 3 subsystem guards as compact chips: id + verbatim status.
- `checked_at` rendered as relative age with the absolute ISO on hover/title.

**Expanded (details disclosure element):** one row per report — `artifact_id`, verbatim `status`, `basis`, tier, relative age (or "no observable timestamp" when `observed_at` null), `producer` + `artifact_path` as plain disclosed metadata, `disclosures[]` verbatim. Rows are data-driven from the payload (no hardcoded artifact list). **Expected-subsystem coverage:** the FE keeps the expected trio `[model_provenance, capture_health, tier_readiness]`; a trio member absent from the payload renders an explicit "not reported — unverified" row (Gemini seed F), never silently omitted; `subsystems: []` renders the entire trio that way (Codex R1 #5). **Duplicate subsystem ids render ALL rows** (never a silent first/last-winner collapse — a `capture_health ok` + `capture_health unavailable` conflict must be visible; Codex R1 #4). Extra/unknown subsystem ids render verbatim (forward-compatible).

**Timestamp honesty (Codex R1 #6):** `checked_at`/`observed_at` are strings the Zod boundary cannot semantically validate. An unparsable date string renders the absolute raw string plus "timestamp unavailable" — never `Invalid Date`/`NaN`. A future timestamp or negative `age_seconds` must not render a misleading negative/absurd relative age; fall back to the absolute value verbatim.

**Severity styling (round-1 converged):** neutral grayscale base like every DG surface. Exactly ONE severity hue (amber): `degraded`/`stale`/`missing`/`corrupt_or_empty`/`unavailable` states get an amber accent + explicit text. **No green anywhere** — a green glow is the "validated" illusion (Gemini mislead risk #1); `ok`/`fresh` stay neutral. `dormant` = gray badge "dormant (off-season expected)". `freshness_overdue` = distinct "overdue (within grace)" pending treatment — neither fresh-neutral nor degraded-amber. **Tier-mapped intensity (Gemini R1):** `core_substrate` degradation = prominent amber; `daily_diagnostics` = muted amber; **`auxiliary` rows never carry the severity accent** — they render their verbatim status neutrally as info (mirrors the backend rollup, which never lets auxiliary drive `overall_status`). **Token discipline (Codex R1 #2):** this card must NOT use the `--dg-market` token family (market semantics ≠ warning semantics); use a local warning class or the existing warning-appropriate token. **Testability contract (Codex R1 #2):** severity/status are asserted via rendered text plus stable data attributes — `data-health-status="<verbatim enum>"` and `data-severity="degraded"` (present on stale/missing/corrupt/degraded core+daily rows, absent on dormant/fresh/overdue and ALL auxiliary rows) — never via CSS class-name assertions. Text always carries the meaning (never color alone, a11y).

**A11y:** card `role="status"` with `aria-label="System diagnostics"`; expanded rows in a table or definition list; status text never conveyed by color alone.

## 4. No-Verdict Line and overclaim cordon

- This card reports **pipeline completion, artifact freshness, and provenance verification — never model accuracy, player value, or any verdict**. No player identifiers exist in the payload; none may be introduced.
- The exact backend `disclaimer` Literal is rendered verbatim in the card (collapsed or expanded footer — visible without interaction). `decision_supported=false` is asserted at the parse boundary (Zod literal) and disclosed in rendered text.
- David-facing labels: "System Diagnostics" / "Pipeline Liveness" / "Data Freshness". BANNED **in headline/nav/status labels and badges**: "System Trust", "Model Status", "Model Validity", "Accuracy", "Verified", "Trust Score" (Gemini overclaim check — the *build* name says Trust & Freshness; the *surface* must not). **Explicit exemptions (Codex R1 #7):** the exact backend `disclaimer` Literal (which itself contains "model accuracy") and protective NEGATION copy such as the subtitle "not model accuracy" — the ban targets affirmative labeling, never the constitutionally required caveat text.
- Banned-language vitest gate applies to the new component (buy/sell/hold/keep/cut/start/sit word-boundaried — the `\b` lesson from `position`/`starter` false-matches).
- Dormant renders calm (alert-blindness risk: off-season dormancy is HEALTHY, PR #113 precedent); stale/missing/corrupt render visibly degraded — the two must never share a treatment.

## 5. Falsification seeds (RED contract input — merged Gemini A–F + Codex angles; Codex owns the RED)

1. 503 (body parseable as `zSystemHealthErrorResponse`) → unavailable panel, sanitized `message` only, no crash, no raw leak.
2. 503 with UNPARSEABLE body / network reject / fetch throw → same unavailable state.
3. 200 with shape drift (missing field, wrong type, disclaimer text drift from the Literal) → safeParse fails → unavailable, never partial render.
4. Unknown future enum value (overall_status / report status / subsystem status / tier) → fail closed via Zod → unavailable; never renders as healthy.
5. `overall_status=ok` with a `freshness_overdue` row and a `dormant` row → collapsed light shows verbatim "ok" + MANDATORY per-status counts (collapsed, not details-only); NOT "all fresh"; overdue row shows "within grace" pending treatment, not green-fresh, not degraded-amber.
6. `dormant`+`dormant_ok_offseason` → neutral gray, does NOT visually degrade the card; `stale`/`missing`/`corrupt_or_empty` → visibly degraded. Distinct treatments asserted via `data-health-status` + `data-severity` attributes and rendered text — never CSS class names. An `auxiliary`-tier stale row carries NO `data-severity="degraded"` (info-only, mirrors backend rollup).
7. `overall_status=degraded` + `worst_affected_tier=core_substrate` vs `daily_diagnostics` → tier leads the collapsed line ("degraded · core_substrate affected"); core tier treatment ≥ daily tier severity (asserted via data attributes).
8. Expected subsystem absent from payload → explicit "not reported — unverified" row; `subsystems: []` → all three trio rows "not reported — unverified"; DUPLICATE expected subsystem ids → ALL rows rendered (no silent first/last-winner); unknown extra subsystem id → rendered verbatim (no crash).
9. `observed_at`/`age_seconds` null (missing/dormant/corrupt) → "no observable timestamp", no NaN/Invalid-Date render. `reports: []` → "no report freshness rows reported", zero fabricated counts.
9b. Zod-valid-but-semantically-bad timestamps: unparsable `checked_at`/`observed_at` date string → raw absolute string + "timestamp unavailable", never `Invalid Date`; future timestamp / negative `age_seconds` → absolute value verbatim, never a negative/absurd relative age.
10. Exact disclaimer Literal + `decision_supported=false` present in rendered accessible text.
11. Long `artifact_id`/`basis`/`producer`/`artifact_path` strings → no shell-header overflow (CSS containment).
12. AppShell mount: card present in header region alongside TrustStrip; TrustStrip untouched and its tests still green.
13. `checked_at` relative-age rendering injects/mocks the clock (no `Date.now()` flake) and echoes the absolute timestamp verbatim in title text (the T3 `checked_at` verbatim-echo lesson).
14. Banned-language scan green over the new component (word-boundaried).

## 6. Test & CI constraints

RED is fixture-only over mocked `fetch` — a committed test must never depend on the live route, a running server, or gitignored `app/data/**` artifacts (CI-independence rule, charter §5). Real-shape smoke against the live in-process route happens pre-CLEAR as a temp check, not a committed test. Gates: focused vitest slice → full FE vitest + tsc + biome + banned-language + build → `scripts/verify_sprint_closeout.py --base origin/main` ENFORCE PASS before push/PR (two-step ship discipline; CI gates the merge).

## 7. Task plan (single-cycle build)

- **T1 (Codex RED):** `frontend/src/system-health/SystemHealthCard.test.tsx` (+ AppShell mount assertions) encoding §5. **Fixture strategy (Codex R1 #8):** the nominal fixture is a MINIMAL SYNTHETIC payload mirroring the §2 real schema — stable timestamps, all nullable realities represented — NOT a verbatim live-payload copy (today's exact six-row/status mix is brittle). A captured live payload may serve as an optional secondary real-shape fixture; the live probe's binding role is spec evidence + the pre-CLEAR smoke, not the unit-test oracle.
- **T2 (Claude GREEN):** component + css + AppShell mount; self-probe matrix before routing.
- **T3 (ship):** full gate + closeout ENFORCE PASS → dual-CLEAR → David authorizes push/PR → CI-green → David authorizes merge → zero-divergence → close the loop.

Branch (on David's word): `feature/system-health-ui-card`.
