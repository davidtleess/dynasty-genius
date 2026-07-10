# Market-Divergence Capture-Health Registration — Design Spec

**Date:** 2026-07-09
**Status:** DRAFT — awaiting cockpit CLEAR, then David authorization to open the RED
**Authoring lane:** Claude (spec) · Codex (falsification + RED authorship) · Gemini (advisory, product prose)
**Depends on:** PR #133 (Phase-0b market source ownership), PR #134 (regenerated baseline)

---

## 0. Rulings

### 0.1 Settled in cockpit (2026-07-09)

| # | Question | Ruling | Lane |
|---|---|---|---|
| R1 | Which artifact carries the health signal? | The **status marker**, not the rich report | Claude proposed, Codex accepted |
| R2 | Which field is the liveness clock? | `finished_at` | both |
| R3 | How is producer failure surfaced? | **Opt-in status parsing** (option ii) | Codex ruled, Claude accepted |
| R4 | Schedule anchor | `09:40` (the committed plist), not 09:45 | Codex corrected Claude |
| R5 | Tier | `core_substrate` | both |
| R6 | Unify `degraded`/`aborted` vocabularies? | **No.** Split is meaningful; config names the field per artifact | both |
| R7 | F7 — `status: degraded` + **future** `finished_at` | **Status gate wins** → `producer_failed`. The producer already declared terminal failure; the clock-skew guard applies only after `status: ok` | Codex |
| R8 | `success_status` / `failure_reason_field` without `status_field` | **Reject at config load.** Silent no-op is the wrong boundary | Codex |
| R9 | Does any third path read the artifact JSON? | **No.** Reader opens JSON only when `timestamp_field` is set; new path opens when `timestamp_field` **or** `status_field` is set | Codex, confirmed |
| R10 | `config_version` `1 → 2` | **Warranted** — schema expansion, not content | Codex |
| R11 | `strict=True` + `extra="forbid"` vs new optional fields | Compatible, provided the fields are **declared on the model** | Codex |
| R12 | Frontend in the same slice? | **Yes.** RED-verified: generated Zod rejects the unknown status and the card degrades to `unavailable` | Claude found, Codex accepted |
| R13 | `SystemHealthCard.css` | **No forced churn.** Contract requires the severity attribute, not a CSS edit for its own sake | Codex amendment |

**Spec status: CLEAR** (Codex, 2026-07-09 23:24 ET). RED authored and verified red.

### 0.2 Open — requires David

- **D-a.** ~~One slice or backend-first?~~ **Resolved → one slice** (R12; a backend-only ship does not merely under-style, it prevents the row from rendering).
- **D-b.** Sequence against the other David-gated items: tomorrow's 09:00 capture → volatility-complete baseline run → backup/restore green pass → LaunchAgent install.
- **D-c.** ~~`config_version` bump~~ **Resolved → `1 → 2`** (R10).
- **D-e.** Authorize GREEN. The RED is open and red; implementation has **not** begun.

---

## 1. Problem

`app/config/report_freshness.json` registers **six** artifacts. `market_divergence` is not among them. The daily job that produces the model-vs-market margin — the surface David has named the core product thesis — is the one daily job whose health `/api/health` cannot observe.

If tomorrow's 09:40 run fails, `/api/health` stays exactly as green as it is now.

## 2. Evidence (measured, not argued)

All against the real adapter (`load_report_freshness` → `read_report_artifact_facts` → `evaluate_report_freshness`), synthetic artifacts in temp dirs, controlled `mtime` (`os.utime`) and `now`. Nothing committed was mutated.

### 2.1 The naive registration asserts health on failure

`timestamp_field: null`, anchor 09:40, grace 3, `now` = 10:00 local:

| report file | health status | basis |
|---|---|---|
| `status: "ok"` | `fresh` | `mtime_fresh` |
| `status: "aborted"`, `aborted_reason: "market_source_prior_date"` | **`fresh`** | `mtime_fresh` |

Identical. Two causes compose:

1. `system_health_models.py:459-466` — when `timestamp_field is None`, the adapter **never opens the file**. `ReportArtifactFact` carries only `exists`, `size_bytes`, `mtime`, `embedded_timestamp_value`. `status` is read **nowhere** in the module.
2. `run_market_divergence_refresh.py:486` `_abort()` → `_persist_report()` at `:498`. **A failed run rewrites the report, giving it a fresh mtime.**

Absence is safer than this. Absence is honest silence; the naive registration is a confident lie.

### 2.2 The market vintage is the wrong liveness clock (this kills Claude's first proposal)

Freshness is `timestamp >= _freshness_window_start(anchor)` where `anchor` = last scheduled run (`:361`). FantasyCalc publishes ≈09:28:30 local; the job anchor is 09:40. **The vintage always precedes the anchor by design.** One healthy successful run, keyed on `market_source_timestamp`:

| observed at | status |
|---|---|
| 10:00 local | `freshness_overdue` (`within_grace`) |
| 13:00 local | `stale` (`past_grace`) |
| 22:00 local | `stale` (`past_grace`) |

Red every afternoon on a healthy day. Not fixable by tuning `grace_hours` — the vintage ages while the anchor stands still. **Withdrawn.**

### 2.3 `market_snapshot_date` is unusable — but not for the reason first claimed

Claude asserted a date-only value would crash on tz-aware comparison. **False, retracted.** `:348-349` localizes a naive timestamp (`timestamp.replace(tzinfo=tz)`). It is unusable because midnight always precedes the 09:40 anchor → false-stale daily. Right conclusion, wrong reasoning.

### 2.4 The marker already carries both signals

`app/data/valuation_runtime/market_divergence_refresh_status_latest.json` (live, 281 bytes):

```json
{
  "coverage_sha256": "398d1754…",
  "decision_supported": false,
  "finished_at": "2026-07-09T22:43:16.797711+00:00",
  "latest_sha256": "745c2467…",
  "status": "ok"
}
```

Written on **every** terminal state — the runner's own contract (`run_market_divergence_refresh.py:24`, "writes a status marker on EVERY terminal state (silence-is-not-success)"). Success → `status: "ok"` + `finished_at` (`:614`). Abort → `_degraded()` at `:476` writes `status: "degraded"`, `reason`, `finished_at`; `_abort()` calls it at `:487`.

Measured, `timestamp_field: finished_at`, anchor 09:40, `now` = 22:00 local:

| marker | health status | basis |
|---|---|---|
| `status: "ok"` | `fresh` | `embedded_timestamp_fresh` |
| `status: "degraded"` | **`fresh`** | `embedded_timestamp_fresh` |

So `finished_at` is the **correct liveness clock** — it postdates the anchor and stays `fresh` at 22:00, exactly where the vintage went `stale`. And the marker is still **status-blind** without opt-in parsing. That hole is what §4 closes.

## 3. Rejected alternatives

| Option | Verdict | Why |
|---|---|---|
| Register report, `timestamp_field: null` | **Rejected** | §2.1 — green on failure |
| Register report, `timestamp_field: market_source_timestamp` | **Rejected** | §2.2 — red every afternoon |
| Register report, `timestamp_field: market_snapshot_date` | **Rejected** | §2.3 — false-stale daily |
| Add success-only `generated_at` to the report | **Rejected** | Duplicates `finished_at`; creates a second field whose success-only discipline must be preserved forever. Codex: "would duplicate an existing clock." |
| Abort writes `generated_at` + `status`, consumer gates on status | **Rejected** | Reinstates "job wrote a fresh file so health looks fresh," gated only on every future consumer remembering the status check |
| **Register the marker, `finished_at` + opt-in status parsing** | **ACCEPTED** | §4 — zero runner changes, fail-closed by construction |

## 4. Design

**Zero runner changes.** The runner already emits everything required.

### 4.1 Registry entry (7th artifact)

```json
{
  "artifact_id": "market_divergence",
  "path": "app/data/valuation_runtime/market_divergence_refresh_status_latest.json",
  "producer": "scripts/run_market_divergence_refresh.py",
  "cadence": "daily",
  "scheduled_time_local": "09:40",
  "grace_hours": 3,
  "tier": "core_substrate",
  "min_size_bytes": 64,
  "timestamp_field": "finished_at",
  "status_field": "status",
  "success_status": "ok",
  "failure_reason_field": "reason",
  "dormant_ok": false,
  "season_windows": { "in_season_months": [9, 10, 11, 12, 1] }
}
```

### 4.2 Evaluation order — the status gate precedes the freshness gate

This ordering is the whole design. A producer that failed is `producer_failed` **regardless of how fresh its timestamp is.**

```
if not exists                      -> missing
elif size < min_size_bytes         -> corrupt_or_empty (below_min_size)
elif status_field configured:
    payload.status absent / non-str-> corrupt_or_empty (malformed_status:<field>)
    payload.status != success_status-> producer_failed (producer_failure:<reason or "unreported">)
# only a producer that reported success reaches the freshness gate
<existing freshness logic, unchanged>
```

Fail-closed: a marker whose `status` cannot be read is `corrupt_or_empty`, never `fresh`.

### 4.3 New status value

`producer_failed` joins `ReportFreshnessStatus` and **`_DEGRADING_STATUSES`**. With `tier: core_substrate`, a failed daily run drives `overall_status = "degraded"`, `worst_affected_tier = "core_substrate"`.

## 5. Contract changes

### 5.1 Config (`app/config/report_freshness.json`)

- Three new **optional** fields on `ReportArtifactConfig` (`system_health_models.py:59`), defaulting to `None` so the existing six entries stay valid unchanged: `status_field`, `success_status`, `failure_reason_field`.
- `ReportArtifactConfig` is `_Strict` (`extra="forbid"`, `strict=True`). Defaults are compatible; **no coercion is introduced.**
- Validation: `success_status` and `failure_reason_field` are meaningless without `status_field` → reject at load (`_reject`) if either is set while `status_field is None`.
- **D-c:** propose `config_version: 1 → 2`.

### 5.2 API (`app/api/routes/system_health_models.py`)

- `ReportFreshnessStatus` gains `producer_failed`.
- `_DEGRADING_STATUSES` gains `producer_failed`.
- `read_report_artifact_facts` must parse the JSON when **either** `timestamp_field` **or** `status_field` is set, and `ReportArtifactFact` gains `status_value: str | None` and `failure_reason: str | None`.
- `evaluate_report_freshness` implements §4.2.
- `decision_supported: Literal[False]` unchanged everywhere. **No verdicts.**

### 5.3 Frontend — NOT optional

The status enum lives in **five** places, two of them **generated**. A backend-only ship would be honest in the API and **false-green in the UI** — and in fact the row never renders at all, because the Zod contract rejects the unknown status first (Codex, RED-verified: the card falls back to `unavailable`).

**Generated — never hand-edit.** `frontend/openapi-ts.config.ts` states the output is "a committed build artifact, never hand-edited."

| site | kind | consequence if `producer_failed` is omitted |
|---|---|---|
| `frontend/src/lib/api/zod.gen.ts:771` | generated | **Zod rejects the response; the whole card degrades to `unavailable`** |
| `frontend/src/lib/api/types.gen.ts:1939` | generated | type does not admit the status |

Regenerate with `npm run openapi-gen` (= `scripts/dump_openapi.py` → `frontend/openapi.json` → `openapi-ts`). The backend `Literal` change (§5.2) is the source of truth; the snapshot and both `.gen.ts` files follow from it. **Do not hand-edit them.**

**Hand-written — `frontend/src/system-health/SystemHealthCard.tsx`.**

| site | line | consequence if omitted |
|---|---|---|
| `REPORT_STATUS_ORDER` | `:26` | unknown status has no sort position |
| `DEGRADING_REPORT_STATUSES` | `:37` | **failed producer renders with no severity accent** |
| `reportStatusLabel` | `:274` | falls through to the raw enum string |

`SystemHealthCard.css`: **no forced churn** (Codex amendment). If the existing `data-severity="degraded"` rule already supplies the accent, the contract requires the *severity attribute*, not a CSS edit for its own sake.

**Manager prose, not backend language** (`DESIGN.md`; the card currently leaks raw enums such as `freshness_overdue (within grace)` — pre-existing, tracked separately, **not** widened here). Per Gemini's product ruling, the three states are three different sentences:

| state | manager prose |
|---|---|
| `producer_failed` | "Daily divergence sync failed. Showing margins from the last successful sync." |
| `stale` | "Market data is stable (N hours old). No new update published." |
| `corrupt_or_empty` | "Market data vintage is indeterminate. Freshness cannot be verified." |

Copy is advisory from Gemini and requires the `impeccable` skill + an unanchored visual audit before it reaches David. **Contract-green is never a visual GREEN.**

## 6. Falsification seeds (the RED must contain these)

Codex authors the RED. Each row must fail on `main` and pass only on the GREEN.

| # | Seed | Required behavior |
|---|---|---|
| F1 | marker `status: "degraded"`, `finished_at` fresh, mtime fresh | `producer_failed`, **never** `fresh` |
| F2 | marker `status: "ok"`, `finished_at` postdates anchor | `fresh` |
| F3 | marker `status: "ok"`, `finished_at` predates anchor, past grace | `stale` |
| F4 | marker absent | `missing` |
| F5 | marker present, `status` key absent, `status_field` configured | `corrupt_or_empty` (`malformed_status:status`) |
| F6 | marker `status: 123` (non-string) | `corrupt_or_empty`, **not** a coercion to `"123"` |
| F7 | marker `status: "degraded"`, `finished_at` **in the future** | fail-closed; status gate wins before the clock-skew guard |
| F8 | `success_status` set, `status_field` absent | config load **rejects** |
| F9 | `producer_failed` at `core_substrate` | `rollup_health_status` → `("degraded", "core_substrate")` |
| F10 | `producer_failed` at `auxiliary` | never degrades root (amber-blindness guard holds) |
| F11 | the existing six artifacts, unchanged config | byte-identical health output vs `main` (**no regression**) |
| F12 | seventh-artifact pin | `test_system_health_t4.py:89` updated **deliberately**, and asserts the marker path + `status_field` |
| F13 | frontend | a `producer_failed` row parses the generated Zod contract, appears in the collapsed counts, carries `data-severity="degraded"`, and renders manager prose — the raw enum `producer_failed` must **not** appear in the row text |
| F14 | generated client | `zod.gen.ts` / `types.gen.ts` regenerated via `npm run openapi-gen`, never hand-edited; `frontend/openapi.json` snapshot matches the backend schema |

**RED status (Codex-authored, independently re-run by Claude):**

| suite | result |
|---|---|
| `tests/contract/test_market_divergence_capture_health_registration_red.py` + `test_system_health_t4.py` | **13 failed / 3 passed** |
| `npm --prefix frontend run test -- SystemHealthCard.test.tsx` | **1 failed / 14 passed** — generated Zod rejects `producer_failed`, card falls back to `unavailable` |
| `ruff check` on touched Python tests | pass |

**Test-construction law** (`project_league_opportunity_no_verdict_reconcile`): the marker path is **gitignored** (`.gitignore:89`, `app/data/valuation_runtime/`) and therefore **absent in CI**. Tests MUST monkeypatch the path / drive the evaluator directly. **Never assert the live `/api/health` route status in a committed test.**

## 7. Out of scope

- Any runner change. `run_market_divergence_refresh.py` is not touched.
- Unifying the `degraded` (marker) / `aborted` (report) vocabularies — R6.
- The pre-existing raw-enum leak in `reportStatusLabel` for statuses other than `producer_failed`.
- The two genuinely stale reports (`roster_capacity` 215.6h, `league_opportunity` 223.4h) — real, unrelated, predate this work.
- Backup-marker health (`status=failed`, `missing_required:market_divergence_history.db`) — Codex's separate finding; gates the LaunchAgent install, not this slice.
- Gemini's "Not Monitored" row for genuinely unregistered subsystems — good idea, separate slice.

## 8. Sequence

1. Cockpit CLEAR on this spec (Codex technical, Gemini product prose).
2. **David authorizes** the RED.
3. Codex authors the RED (F1–F13). It must be **red on `main`**, and demonstrably so.
4. Claude implements GREEN: config → API → frontend, full gate mid-build (cross-boundary contract → `feedback_focused_slice_verification_gap`).
5. Claude self-probes the falsification matrix adversarially before routing (`feedback_green_adversarial_input_hardening`).
6. Codex independent review. Then, and only then, David authorizes commit/push/merge.

## 9. Risks

| Risk | Mitigation |
|---|---|
| **Semantic widening:** `report_freshness.json` currently points only at `*_report.json`. | Accepted (Codex). The schema field is `path`, not `report_path`; `ReportArtifactConfig` (`:60`) already describes a generic producer artifact. Document the widening explicitly; update the pin deliberately. |
| The pin test is updated *incidentally*, hiding a regression. | F12 asserts the seventh artifact's path and `status_field` by name. |
| Backend ships without frontend → UI false-green. | §5.3; **D-a** recommends one slice. |
| A future artifact sets `status_field` against a producer that writes the field on failure too. | The status gate precedes the freshness gate — it cannot be bypassed by a fresh timestamp. |
| `strict=True` rejects a valid config. | F11 pins byte-identical output for the untouched six. |
