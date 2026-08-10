# Phase A framing v2 — Footballguys manual-drop intake + monthly refresh notice (Claude)

Date: 2026-08-10 · **Layer 1 (ingest).** Supersedes the monthly-notice framing v1 (`b6b674d5…`) and
serves plan v2 Phase A. Folds: the seven notice-framing findings (accepted 7/7) + plan findings
1, 2, 7, 8. **Framing only — no RED, no build, no scheduler, no provider contact.**

**David's words served, verbatim:** *"keep it as a paid source of mine - have a reminder or refresh
notice come up once a month"* and *"determine how to plan and execute your recmmendation in #2"*.

## 1. Disposition of the seven notice findings (all accepted; how each lands here)

| # | Finding | Landed as |
| :-- | :-- | :-- |
| N1 | `capture_cadence.json` wrong shape; `stores[0]` consumer | §4: one governed **manual-feed contract** in the `daily_control.py` domain (which already owns the PlayerProfiler/PFF manual streams), consumed **by stable id**; no second truth system, no capture-cadence widening |
| N2 | declared ≠ downloaded | §3: **byte-bound receipt** — Phase A records raw-bytes SHA per role, so the copy earns *"Last Footballguys refresh **recorded** N days ago"*; "download" never appears |
| N3 | no closed timing/state machine | §5: exact machine, boundaries chosen and stated |
| N4 | vintage series unearned for a reminder | returns ONLY as intake design (§3), earned by David's Q2 order — the receipts log IS the series; no analytical consumer implied |
| N5 | surface composition unframed | §7: composition artifact is a named Phase-A deliverable BEFORE RED; committed direction: status-drawer detail + neutral pill count, never first-viewport |
| N6 | persistence/backup/failure isolation | §6, with the offsite question surfaced as **David's word** |
| N7 | seeds lack oracles/mutants | §8: Codex's eleven controls carried verbatim + plan-side mutants |

## 2. The bundle semantic contract (plan finding 1 — the Critical)

Every drop records an **exact-field semantic contract**: `product_family`, export name/version,
exact field names, format, scoring rule, and `horizon ∈ {seasonal_redraft, dynasty_startup,
unknown}` — supported only by a **provider-authentic evidence pointer** (captured export/UI
metadata, provider documentation) stored with hash + retrieval provenance. Prohibited inferences:
the empty `adp_sleeper-redraft` column, numeric shape, filename, David's declaration alone.
**`horizon=unknown` is a fully valid Phase-A state**: intake and reminder proceed; Phase C stays
closed; no horizon label may be emitted anywhere.

## 3. The atomic bundle receipt (plan finding 2 + N2/N4)

One drop = one **bundle**, never loose files:

- **Roles:** `adp` (required) · `identity_sidecar` (required — currently `projections.csv`, admitted
  for identity fields ONLY; projection values barred from model and overlay signal at the Phase-B
  boundary) · `changelog` (optional, cadence evidence).
- **Receipt fields:** `bundle_id` (hash over sorted per-role content hashes) · per-role
  `{filename, sha256, bytes}` · `source_id` · receipt `schema_version` · system `recorded_at` ·
  David-declared `retrieved_at` · the §2 semantic contract · role-completeness verdict.
- **Fail-closed:** missing/mismatched required role → bundle `identity_unverifiable`, unavailable
  to Phase C; cross-vintage pairing (roles from different downloads) has no representation — roles
  bind at receipt creation or not at all.
- **Append-only receipts log** = the vintage series (N4, earned). **Payload identity ≠ offering
  identity** (plan finding 7): identical bytes re-dropped is a new offering observation of the same
  content vintage, recorded as such, and is NOT `unverifiable`.

## 4. Registry home and read path (N1)

The reminder registers as a **manual-feed stream** in the `daily_control.py` machinery under a
stable id (`footballguys.bundle`), cadence class `monthly_manual` — a new arm of the existing
manual-feed contract, NOT a widening of the daily-SQLite capture-store schema. The read model
serves it as an **id-addressed entry separate from `stores[]`**, so the `stores[0]` consumer is
untouched; the login surface selects by id. **Failure isolation:** a corrupt/missing marker
degrades only this stream to `unverifiable`; existing capture-health facts stay byte-equal; global
`overall_status` does NOT inherit this stream's state (a paid-source reminder is not a capture
failure). Reconciliation duty: the contract shape is written so PlayerProfiler/PFF can adopt it,
and their open design is NOT pre-decided here — one contract, first tenant.

## 5. The state machines (N3 + plan finding 8 — orthogonal, never conflated)

**Acquisition freshness** (drives the reminder): `no_record` · `current` · `due` · `unverifiable`.
- Clock source: the latest receipt's **system `recorded_at`** (monotonic, ours); the declared
  `retrieved_at` is displayed but never drives the clock.
- **`due` ⇔ (today_local − recorded_local_date) ≥ 30 calendar days**, America/New_York, no grace
  (grace is a scheduled-job concept; a manual monthly reminder has none). Boundary: day 30 is due.
- **Season-flat.** No in-season tightening without a new David word.
- Delivery: a **persistent state, not an event** — no toasts, no notifications, no daily nags; the
  drawer shows it while true. No snooze/dismiss in v1 (nothing to reset; N3's "dismissal must not
  reset the clock" is satisfied by having no dismissal). A new receipt is the only reset.

**Intake readiness** (per bundle): `ready` · `review_required` · `failed` — schema/semantic/identity
gates. **A quarantined/failed bundle still resets acquisition freshness** (David did refresh; the
reminder's honest subject is his action) **while `latest_analysis_ready` is untouched** — proposed
answer to Codex's open question, for the challenge round.

**`latest_analysis_ready`** advances only when required roles + all gates pass. Replay is
idempotent (same bytes → same receipt id, no duplicate); writes are receipt-then-payload with
rollback on partial failure (no receipt ever cites absent bytes).

**Copy (exact, banned-language-scanned):** `Last Footballguys refresh recorded N days ago ·
monthly refresh due` / `No Footballguys refresh recorded` / `Footballguys refresh record
unreadable`. Never "stale", "unreliable", "should", "must", "download".

## 6. Persistence, backup, and the David word inside this framing (N6 + plan finding 8)

- **Receipts log:** `app/data/footballguys/receipts.jsonl` (append-only, small, non-regenerable) —
  **named backup-manifest entry, landing together with the first receipt** per the landing-order
  law. *(Not under `app/data/ops`, which the manifest excludes.)*
- **Raw payloads:** `app/data/footballguys/drops/<bundle_id>/` — **gitignored, local-durable.**
- **⚖ DAVID'S WORD REQUIRED, stated not assumed:** adding raw paid-provider payloads to the
  manifest creates a **new offsite remote copy of licensed content** in the GCS backup. Options for
  his ruling: (a) receipts+metadata offsite, raw payloads local-only (restoration = re-download
  from provider; recommended default until he says otherwise); (b) full payloads offsite. Phase A
  proceeds under (a) unless he rules (b); neither is decided here.

## 7. Surface composition (N5)

Named Phase-A deliverable, before any RED that touches a component: the pre-code composition
artifact (5-second answer, focal hierarchy, desktop+mobile sketches, lane order, exact
component/slot, keyboard/focus, all four states). **Committed direction now:** detail lives in the
existing status drawer beside `SystemHealthCard`; at most a neutral count in the existing status
pill; **never** a modal, toast, verdict-colored warning, or first-viewport block. The framing-first
rule for material visual change routes the composition artifact through its own review.

## 8. Falsification controls (N7 verbatim + Phase-A-relevant plan mutants — one broken implementation each)

1. evaluator uses file mtime instead of the declared event → caught
2. consumer renders `stores[0]` instead of selecting by stable id → caught
3. missing/malformed/future Footballguys state leaves every existing capture-health fact byte-equal
4. `≥30d` vs `>30d` boundary mutants cannot both pass — **≥ is chosen (§5)**
5. daily-store grace applied to the manual reminder → caught
6. in-season weekly tightening → caught
7. repeated reads emitting duplicate notices/events → caught
8. any acknowledgement path mutating `recorded_at` → caught (v1 has no such path; the mutant proves it)
9. raw enum/schema/ISO text or banned words reaching the surface → caught
10. legacy daily-only config/responses remain valid alongside the new arm
11. required-manifest/state landing-order violations in either direction → fail
12. bundle accepted with missing/mismatched identity sidecar → caught (plan finding 2)
13. `horizon=unknown` bundle emitting any horizon label anywhere → caught (plan finding 1)
14. same-bytes re-drop recorded as a new content vintage → caught (plan finding 7)
15. failed/quarantined intake advancing `latest_analysis_ready` → caught (plan finding 8)
16. future-dated `retrieved_at` accepted silently → caught (recorded, flagged `unverifiable`)

## 9. Out of scope

Phase B/C/D entirely · any delta or horizon claim · scheduler installs (age computes at read time) ·
provider contact · the PlayerProfiler/PFF designs (shape-compatible, not decided) · Studio.

**PLEASE CHALLENGE (Codex):** the §5 quarantine-resets-freshness proposal (your open question — is
the reminder's subject David's action or analytical usability?) · the §4 no-inheritance rule for
global `overall_status` · the §6(a) local-only raw retention default · the §3 role model (is
`changelog` worth a role?) · any seed still lacking a closed oracle.
