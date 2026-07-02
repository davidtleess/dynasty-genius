# DEBT-6 Slice 1b: PIT Capture-Health / Gap Detector — Design Spec

**Status:** DRAFT — Gemini framing + Codex boundary pass received 2026-07-02; awaiting cockpit redline CLEAR. **Execution HELD pending spec CLEAR + Codex RED + David per-step authorization.** No tree mutation authorized by this draft beyond the spec/plan files themselves.
**Priority source:** `AGENT_SYNC.md` → priority list #1 item (b) (2026-07-01); charter §2. Slice 1 (model provenance) SHIPPED via PR #107 (`28c0a43`).
**Plan:** `docs/superpowers/plans/2026-07-02-debt6-capture-health-slice1b-plan.md`.

---

## 0. Scope & standing constraints

**In scope (Slice 1b):** a single read-only endpoint `GET /api/system/capture-health` that inspects the two daily point-in-time (PIT) capture stores and reports, per store, timeline completeness (missing dates, max contiguous gap), staleness (did today's capture land, with a grace window), and per-day row-density anomalies (a partial "empty-shell" capture counts as a gap) — so a laptop-sleep hole reads as *"comparison window degraded — N dates missing"* instead of silently distorting every downstream trend.

Stores covered (Codex silent-gap-risk order — both in this slice, one shared contract):
1. `app/data/fc_forward_capture.db` (`fc_forward_capture_raw`, date col `snapshot_date`) — the market-side PIT clock: unreconstructable, feeds Gate-4 (~Dec 2026 accrual).
2. `app/data/model_forward_capture.db` (`model_forward_capture_raw`, date col `capture_date`) — the model-side PIT clock.

**Explicitly OUT of Slice 1b (later slices / never):**
- Runtime/report freshness rollup (LaunchAgent last-run states, `*_latest` report artifact ages) — **Slice 1c**, a different surface class.
- Any UI card (the "System Trust & Freshness" surface — later FE slice; this ships the API truth first).
- Alerting/notifications/emails — the surface is pull-based (daily-login), not push.
- **Auto-repair or backfill — NEVER.** Missed PIT market days are irrecoverable by definition (real-time sentiment is lost); the detector must never imply otherwise (Gemini overclaim check).
- The legacy frozen archive `fc_snapshots.db` (read-only historical artifact; not a live clock).

**Standing constraints:**
- **Data-Freshness, not System-Integrity (Gemini split, carried from Slice 1).** A missed capture is a *caveat*; it never produces an integrity/blocked state. `overall_status ∈ {ok, degraded}` — this endpoint has NO `blocked` and never gates serving.
- **No-Verdict Line.** Descriptive facts only: dates, counts, gap sizes, threshold flags with disclosed bases. Never `gate_4_ready`, never "trusted for backtesting", never a recommendation. `decision_supported=false` recursively; `extra="forbid"` on every model.
- **Read-only.** SQLite opened read-only (`mode=ro` URI); the health check must NEVER create a missing db file or mutate a store.
- **Real-shape discipline.** Grounded 2026-07-02: both stores live, 9 contiguous dates 2026-06-24→2026-07-02, ~462 fc rows/day, 12,201 model rows/day; LaunchAgents daily (fc 09:00; model chain 09:15–09:45). Fixtures mirror these shapes; committed tests use temp SQLite only (Codex boundary).

---

## 1. Why (the failure this closes)

The daily PIT capture is the product's compounding asset and Gate-4's foundation. A closed laptop silently skips days; nothing today records that a hole exists. When the ~Dec 2026 model-vs-market study runs, silent holes either distort rolling statistics or quietly shrink power. The fc lane is worst: market sentiment not captured on a given day is gone forever. Slice 1 made *model identity* explicit; 1b makes *time-series completeness* explicit — the two halves of "the daily PIT capture must be trustworthy" (charter §1).

Gemini's daily-login answer this endpoint must give: **"Timeline complete (N consecutive days captured)" or "Degraded: N days missing between A and B (max contiguous gap M days) — historical trend calculations may be distorted."** A single 10-day hole damages Gate-4 rolling statistics far more than ten isolated 1-day blips → `max_contiguous_gap_days` is a first-class field, not just a flat count.

---

## 2. Checked-in cadence config — `app/config/capture_cadence.json`

Expectations are explicit, versioned, checked-in config (Codex: never inferred from plist text at request time; the plists are cited as the operational source). Mirrors the Slice-1 registry pattern: updated only by David-authorized PR, loader fail-closed.

```json
{
  "config_version": 1,
  "timezone": "America/New_York",
  "season_windows": { "in_season_months": [9, 10, 11, 12, 1] },
  "stores": [
    {
      "store_id": "fc_forward_capture",
      "db_path": "app/data/fc_forward_capture.db",
      "table": "fc_forward_capture_raw",
      "date_column": "snapshot_date",
      "source_filter": "fc_native",
      "expected_settings_hash": "e27351d720e9fcf0",
      "capture_start_date": "2026-06-24",
      "expected_cadence": "daily",
      "scheduled_time_local": "09:00",
      "grace_hours": 3,
      "density_floor_pct": 50,
      "density_baseline_window": 14,
      "warn_consecutive_missing": { "in_season": 1, "off_season": 3 },
      "window_risk_contiguous_days": 7,
      "companion_tables": []
    },
    { "store_id": "model_forward_capture", "db_path": "app/data/model_forward_capture.db", "table": "model_forward_capture_raw", "date_column": "capture_date", "source_filter": null, "expected_settings_hash": null, "capture_start_date": "2026-06-24", "expected_cadence": "daily", "scheduled_time_local": "09:45", "grace_hours": 3, "density_floor_pct": 50, "density_baseline_window": 14, "warn_consecutive_missing": { "in_season": 1, "off_season": 3 }, "window_risk_contiguous_days": 7, "companion_tables": [ { "table": "model_forward_prediction_snapshot", "date_column": "capture_date", "capture_start_date": "2026-06-28" } ] }
  ]
}
```

**Codex kickoff-redline incorporations (R1–R4):**
- **R1 — companion-table coverage.** Raw rows can land while a companion table's rows do not (the model PIT clock would look healthy while the realized-outcome input surface is broken). Each store may declare `companion_tables`; for each, the detector checks that every raw-present date **on or after the companion's own `capture_start_date`** has ≥1 companion row — a missing companion date emits `companion_rows_missing` (degrading). The companion start date matters: REAL shape 2026-07-02 — raw has 9 dates from 06-24 but `model_forward_prediction_snapshot` has 5 from 06-28 (its hook shipped later); without the per-companion start date the detector would false-alarm 4 permanent gaps.
- **R2 — `expected_settings_hash` (fc).** The fc store is keyed `(snapshot_date, source, settings_hash, player_key)`; counting only `source` could sum across settings hashes and mask a missing canonical series. When `expected_settings_hash` is set, timeline/density count only matching rows; observing any OTHER hash on a date emits `unexpected_settings_hash_detected` (degrading). Real shape: exactly one hash `e27351d720e9fcf0` across all 9 dates.
- **R3 — config path/identifier safety (fail-closed).** `db_path` must be relative and resolve inside the repo root (no absolute, no `..` escape); `table`/`date_column`/companion identifiers must match `^[A-Za-z_][A-Za-z0-9_]*$` (identifiers cannot be SQL-parameterized). Violations are config-invalid → **503**.
- **R4 — timezone.** Root `timezone` (IANA); "today", scheduled-time and grace arithmetic all evaluate in that zone (the LaunchAgents are local-time). RED pins UTC/local midnight-straddle and the exact grace boundary.

- `capture_start_date`: the timeline is judged from go-live, never before (pre-start dates are not "missing").
- Season-awareness is month-based and disclosed; it modulates only the *warn* threshold (off-season ≥3 consecutive missing before the warn flag; in-season 1) — the raw facts (missing dates, gaps) are always reported regardless (Gemini fatigue calibration: fewer warnings, never fewer facts).
- `window_risk_contiguous_days` (7): the disclosed threshold at which a contiguous gap is flagged as threatening rolling-window statistics. Named "window risk", NOT "gate4" — the field must not certify or invoke Gate-4 readiness (overclaim check).
- `density_floor_pct` + `density_baseline_window`: a present date whose row count < floor% of the trailing-median baseline is an **empty-shell capture** and is treated as missing (Gemini seed C). **Baseline anti-self-normalization (Codex R5):** the trailing median uses only PRIOR dates that are valid-dated, non-future, present, and not themselves sub-floor — never the date under evaluation. With < 3 eligible baseline dates the floor is not evaluable → `density_baseline_insufficient` caveat, never a gap (fail toward caveat, not toward false-missing).
- **Malformed date values (Codex R6):** rows whose date value does not parse as an ISO date are excluded from all timeline/staleness/density math and emit `invalid_dates_detected` (degrading) — never a crash, never silently `ok`.

Config absent / malformed JSON / schema-invalid / empty `stores` / duplicate `store_id` → typed error → **503** (own-config corruption must not pretend health; mirrors Slice-1 §3.6 and its empty-registry ruling).

## 3. Endpoint contract — `GET /api/system/capture-health`

New `app/api/routes/system_capture_health_models.py` (pure logic + Pydantic models, DI everywhere) + `system_capture_health.py` (thin route adapter) — the Slice-1 module pattern, per Codex's pure/service boundary. Wired in `app/main.py` under `/api`.

**Naming note (supersedes the Slice-1 "/api/health reserved" remark):** this ships as `/api/system/capture-health`, cohesive with `/api/system/model-provenance`. `/api/health` stays reserved for a future whole-app liveness rollup (Slice 1c: provenance + capture health + runtime/report freshness in one). Cockpit may redline.

```json
{
  "overall_status": "ok | degraded",
  "config_version": 1,
  "checked_at": "<ISO datetime>",
  "stores": [
    {
      "store_id": "fc_forward_capture",
      "store_status": "ok | degraded",
      "store_presence": "present | absent",
      "timeline": {
        "capture_start_date": "2026-06-24",
        "first_date": "2026-06-24", "last_date": "2026-07-02",
        "expected_days": 9, "present_days": 9,
        "missing_dates_count": 0, "missing_ranges": [], "missing_ranges_total": 0,
        "max_contiguous_gap_days": 0,
        "consecutive_days_current": 9
      },
      "staleness": { "last_capture_date": "2026-07-02", "expected_by": "<ISO>", "stale": false, "grace_hours": 3 },
      "density": { "floor_pct": 50, "baseline_median_rows": 462, "baseline_window": 14, "sub_floor_dates": [] },
      "flags": {
        "warn_missing": false, "warn_basis": "off_season>=3 consecutive",
        "window_risk": false, "window_risk_basis": ">=7 contiguous missing days"
      },
      "caveats": [],
      "decision_supported": false
    }
  ],
  "decision_supported": false
}
```

Semantics:
- **Timeline** runs `capture_start_date → today-or-yesterday` (today only counts as expected after `scheduled_time_local + grace_hours`, injectable clock — Gemini seed D). `missing_ranges` = list of `{from, to, days}` (display-capped at 20; totals always full-series + `missing_ranges_truncated` caveat — R8, no silent cap). Sub-floor dates are folded into missing/gaps AND listed separately under `density.sub_floor_dates` (disclosed double-accounting basis).
- **Staleness** (trailing edge) is distinct from **internal gaps** (holes inside the series) — both reported (Gemini: distinguish; a stale clock and a holed timeline are different failures).
- **Future-dated rows** (clock skew, Gemini seed B): excluded from `last_date`/staleness math; `future_dates_detected` caveat.
- **Duplicate dates** (re-runs, Gemini seed E): timeline uses DISTINCT dates; per-date density sums that date's rows post `source_filter`; never an error.
- **Store absent** (gitignored dbs — the fresh-clone/CI reality): `store_presence=absent`, `store_status=degraded`, `store_absent` caveat, **200** — CI must stay green with both stores missing (the CI-shape lesson; RED asserts this exact shape).
- **Store present but unreadable/malformed** (0-byte file, missing table/column, SQLite error — Gemini seed A): `store_status=degraded` with `store_unreadable` caveat, **200**; never a raw SQLite 500. Freshness never blocks; corruption of the store file itself is still surfaced as the strongest caveat this endpoint can emit, and the caveat text names the store so Slice-1c/integrity work can pick it up.
- **Caveat classes (R7 resolution — Gemini two-class model + Claude fail-closed default; supersedes the draft's open edge):**
  - **Class A — healthy-but-immature (coexists with `ok`):** `density_baseline_insufficient`, `pre_capture_window`. A contiguous, uncorrupted store that simply hasn't accrued enough calendar is physically healthy; degrading it manufactures a permanent early-life false alarm and dilutes `degraded` (reporting SICKER than reality is also an honesty failure — it trains David to ignore the surface, which is fail-open by outcome).
  - **Class B — anomalies/incompleteness (forces `degraded`):** everything else — `store_absent`, `store_unreadable`, `future_dates_detected`, `invalid_dates_detected`, `companion_rows_missing`, `unexpected_settings_hash_detected`, `missing_ranges_truncated`, any missing/sub-floor/stale state.
  - **Fail-closed default:** the Class-A list is CLOSED and enumerated in the spec; any caveat not explicitly classed A is Class B. A future caveat can only become Class A via a cockpit-cleared spec amendment.
- `store_status=ok` ⇔ present ∧ readable ∧ zero missing dates ∧ not stale ∧ zero sub-floor dates ∧ no Class-B caveat.
- `overall_status=degraded` iff any store is degraded; else `ok`. There is no `blocked`.
- **Truncation totals (Codex R8):** `missing_ranges` is capped at 20 entries for display, but `missing_dates_count`, `missing_ranges_total`, and `max_contiguous_gap_days` always reflect the FULL series, and truncation emits `missing_ranges_truncated` — a UI can never show 20 tiny gaps while hiding larger fragmentation.

## 4. Guardrails (inseparable)
- Read-only `mode=ro` URI open; NEVER create a missing db file; no writes anywhere; no network.
- No backfill/repair pathway, and no language implying missing PIT days are recoverable.
- `decision_supported=false` recursive; `extra="forbid"` everywhere; no verdict/certification vocabulary (`gate_4_ready`, `trusted`, `safe`, `recommended` all banned in fields AND caveat strings).
- Thresholds always ship with their disclosed basis strings (ranks-disclose-their-basis analog).
- Injectable: config path, repo root, clock (`now()`), and (for the reader) db path resolution — committed tests = temp SQLite + temp config only; real-store smoke is a session activity, never a committed CI dependency.
- CI-safe: both stores absent + valid config → 200, `overall_status=degraded`, both `store_absent`.

## 5. Falsification matrix seeds (carry into Codex RED)
1. Healthy contiguous store (fixture mirroring real shape: N days, ~462 rows/day) → `ok`, zero missing, `consecutive_days_current=N`.
2. Single interior 1-day hole, off-season → facts reported (`missing_dates_count=1`, `max_contiguous_gap_days=1`), `warn_missing=false` (off-season <3), `store_status=degraded` (facts degrade; warning is separate — fatigue calibration).
3. 3-day contiguous interior hole, off-season → `warn_missing=true` (>=3), basis disclosed.
4. 1-day hole, in-season month → `warn_missing=true` (in-season >=1).
5. 7-day contiguous hole → `window_risk=true`, basis disclosed; wording contains no Gate-4 certification.
6. Multiple disjoint ranges → correct `missing_ranges`, `max_contiguous_gap_days` = the max (not the sum, not the count).
7. Staleness: today expected after `scheduled_time_local+grace`; clock injected before the deadline → `stale=false` with yesterday captured; after the deadline with no today row → `stale=true`. Grace boundary exact-minute case pinned.
8. Empty-shell capture (Gemini C): a date with 2 rows vs baseline median 462 at 50% floor → treated as missing AND listed in `density.sub_floor_dates`.
9. Baseline insufficient (<3 present dates) → floor not applied, `density_baseline_insufficient` caveat, no false gaps.
10. Future-dated rows (Gemini B) → excluded from staleness/`last_date`, `future_dates_detected` caveat, not falsely healthy.
11. Duplicate dates (Gemini E) → distinct-date timeline, summed density, no error.
12. Store absent → 200/`degraded`/`store_absent` (CI shape: BOTH absent → 200; asserted end-to-end).
13. Store present but 0-byte / missing table / wrong column (Gemini A) → 200/`degraded`/`store_unreadable`, never a raw sqlite3 exception to the client.
14. Config absent / malformed / schema-invalid / empty stores / duplicate store_id → **503** sanitized body (mirror Slice-1: fixed message, no absolute paths, no tracebacks).
15. `decision_supported=false` root + every node; `extra="forbid"` rejects a `gate_4_ready` field injection.
16. `capture_start_date` in the future / after today → timeline `expected_days=0`, no missing, `pre_capture_window` caveat (pre-start is not a gap).
17. `source_filter` respected (rows of another source don't mask a missing `fc_native` day).
18. Read-only guarantee: absent store stays absent after the call (no file created); store bytes unchanged after a healthy call.
19. Banned-vocabulary scan over the response surface (fields + caveat strings + basis strings).
20. Season boundary: month at the in/off-season edge resolves per config months, disclosed in `warn_basis`.
21. **Companion coverage (R1):** raw dates 06-24→07-02 with companion rows only 06-28→07-02 and companion `capture_start_date=2026-06-28` → NO gap (the real shape today); a raw date ≥ companion start with zero companion rows → `companion_rows_missing`/degraded.
22. **Settings hash (R2):** rows on a date under a different `settings_hash` than expected do not mask a missing canonical day; any unexpected hash observed → `unexpected_settings_hash_detected`/degraded.
23. **Config safety (R3):** absolute `db_path`, `..`-escaping `db_path`, and non-identifier `table`/`date_column` (e.g. `raw; DROP TABLE x`) → config-invalid → sanitized 503.
24. **Timezone (R4):** clock injected at UTC-vs-local midnight straddle and at the exact grace boundary minute in `America/New_York` → staleness resolves in the config zone.
25. **Malformed dates (R6):** non-ISO date values excluded from all math + `invalid_dates_detected`/degraded; no crash.
26. **Baseline exclusions (R5):** a sub-floor or future or invalid date never enters the trailing-median baseline; consecutive early empty shells cannot self-normalize the floor down.
27. **Caveat classes (R7):** Class-A caveats (`density_baseline_insufficient`, `pre_capture_window`) coexist with `store_status=ok`; every other caveat forces `degraded`; an unclassified/new caveat string defaults to degrading (fail-closed default asserted).

## 6. Resolved so far (kickoff round, 2026-07-02)
- Gemini framing (a): daily-login single answer; season-aware warn thresholds; staleness ≠ timeline completeness; max-contiguous-gap first-class; irrecoverability honesty; seeds A–E → §5.
- Codex boundaries (a): pure module + thin route; versioned checked-in cadence config; states incl. absent/unreadable distinct from ok/degraded; configurable density floors (no eternal hardcoded row counts); temp-SQLite-only committed tests; no auto-backfill; `decision_supported=false`.
- Claude POV committed in this draft: both stores in one slice/contract; endpoint at `/api/system/capture-health` (supersedes the `/api/health` reservation — 1c gets the whole-app rollup); freshness has NO blocked state; facts always reported, thresholds only modulate warn flags; sub-floor days fold into gaps with disclosed basis.

**Redline round (2026-07-02):**
- **Codex R1–R8 ALL ACCEPTED into §2/§3/§5** (companion tables w/ per-companion start date — validated against the REAL 5-vs-9-date shape; `expected_settings_hash`; config path/identifier fail-closed validation; IANA timezone staleness; baseline anti-self-normalization; malformed-date caveat; caveat-mapping pin; truncation totals). Codex explicitly no-objection on all 7 Claude design calls.
- **R7 divergence + resolution:** Codex recommended any-caveat→degraded; Gemini recommended a two-class model (benign early-life caveats coexist with `ok`). Claude sided with Gemini's two-class model PLUS a fail-closed default (Class-A list closed/enumerated; unclassified caveats degrade) — reporting a healthy 2-day-old store as `degraded` is reporting sicker-than-reality and breeds the alarm fatigue that makes real gaps invisible. Pending Codex acceptance of the compromise; if Codex holds, the fork escalates to David (cross-domain seam).
- **Gemini (a→ready):** endpoint name concur; truncation-cap approach concur; two-class caveat mapping proposed (adopted); "ready for Codex RED".
