# Footballguys monthly refresh notice framing v1 — Codex challenge

Date: 2026-08-10  
Artifact reviewed: `footballguys_monthly_refresh_notice_framing_claude_v1.md`  
Submitted SHA-256: `b6b674d53556b00885b3d8605ddb74ffe82a8f408cf4a6237aefb65c3f0531f6`  
Layer: Layer 1 manual-source freshness surfacing  
Verdict: **NOT CLEAR for RED — seven framing findings**

This challenge does not reopen the Footballguys data pilot, authorize intake/provider contact, or
open RED/build/scheduler work. The reminder is not permission to use the data.

## Findings

### 1. High — the named capture-health home does not support this source shape or this notice

`app/config/capture_cadence.json` currently governs daily SQLite capture stores. Its strict model
requires `db_path`, `table`, `date_column`, scheduled local time, grace, density, gap, and companion
semantics, and fixes `expected_cadence` to `Literal["daily"]`
(`system_capture_health_models.py` lines 74–89). A monthly manual declaration is not a widening of
one field; it is a different sum-type arm.

The proposed login consumer also does not render a store by id: `DailyTape` reads only
`capture.data.stores[0]` (`DailyWhatChanged.tsx` lines 601–614). Appending Footballguys would be
invisible; inserting it first would silently replace the existing capture summary. Meanwhile the
backend rolls any degraded store into global `overall_status`, so no marker or a due reminder could
make the whole capture system look degraded despite §4 correctly saying this is not a staleness
verdict.

Ruling: **`capture_cadence.json` is not an earned home as currently modeled.** Framing v2 must trace
the exact producer→read model→component path and choose between extending the existing manual-feed
cadence machinery (`daily_control.py` already owns PlayerProfiler/PFF manual streams) or a separate
narrow reminder registry. It must not create a second manual-feed truth system without reconciling
that overlap.

### 2. High — a declaration marker cannot truthfully support “last download” copy

A David-declared timestamp proves that a refresh was **recorded**, not that a file was downloaded,
which file it was, or when the provider produced it. The proposed copy—“your last download is N days
old”—overclaims the selected truth source. Provenance honesty requires one of two explicit contracts:

- timestamp-only declaration: render **“Last Footballguys refresh recorded N days ago”**; or
- byte-bound receipt: user selects the downloaded artifact and the recorder binds declared retrieval
  time plus content hash. That is closer to intake and is outside this framing unless separately
  admitted.

V2 must define the write event and fields, not just the read marker: source id, schema version,
system `recorded_at`, David-declared `retrieved_at` if allowed, and whether any artifact hash exists.
It must also name the authorized action that writes it. A read-time route may not silently infer or
mutate this state.

### 3. High — “once a month” has no closed timing or delivery state machine

The document alternates among “older than a month,” `>30 days`, exact 30/31-day tests, and
“threshold+grace,” while also saying scheduled time and grace are meaningless. These are different
contracts. The current board interprets David's ruling as a 30-day cadence, but v1 never fixes:

- rolling 30×24 hours versus 30 local calendar dates;
- `age >= 30 days` versus `age > 30 days`;
- whether any grace exists (none is the coherent default here);
- whether “notice once a month” means a persistent due state, one notification per cycle, or a
  banner repeated on every login after day 30.

V2 needs a state machine with exact boundary outputs: `no_record`, `current`, `due`, and
`unverifiable`, plus separate acknowledgement/snooze state if those exist. Dismissal must never reset
the refresh clock. Repeated reads must not generate repeated events or daily nag toasts.

### 4. Medium — §6 expands a reminder into an append-only provider vintage history

Section 2 says the notice needs only a last-drop timestamp and formal intake is out of scope.
Section 6 then promises every drop appends dates and hashes to a local vintage series for a future
delta study. That is a new durable capture product, not necessary for a monthly reminder, and it
pre-decides both David's open Q2 and the unresolved PlayerProfiler/PFF manual-feed design.

Strike the vintage-series promise from this framing. If v2 intentionally retains an event history,
label that as a separate architecture/retention choice with no analytical consumer and no implication
that Q2 is approved.

### 5. High — the surface composition is not framed, and the likely placement can violate the design foundation

The product foundation bars system/trust/freshness plumbing from becoming the primary first-viewport
story. The current `SystemHealthCard` lives in the shell status drawer, intentionally out of the
first viewport; the Daily What-Changed tape is part of the primary fantasy narrative. A monthly,
non-blocking paid-source reminder has not earned an active warning block ahead of roster/model/market
content.

Before RED, supply the required pre-code composition artifact: five-second answer, focal hierarchy,
desktop and mobile sketches, lane-order statement, exact component/slot, keyboard/focus behavior,
and all four display states. A plausible direction is a neutral due count in the existing status
pill with detail in its drawer—not a modal, toast, verdict-colored warning, or first-viewport hero—
but v2 must close the interaction rather than leave build to invent it.

### 6. High — persistence, backup, and failure isolation are not closed

The marker is non-regenerable because this framing has no intake and does not govern Downloads.
Its exact path and retention class therefore matter. `app/data/ops` is explicitly excluded by the
backup manifest, so “live where already covered” cannot be assumed. V2 must name the durable path and
whether it is a required backup entry; if required, the marker/store and manifest entry land together
under the established landing-order law.

One corrupt manual marker must degrade only the Footballguys reminder to `unverifiable`. It must not
503 the entire capture-health endpoint, hide the existing FC/model facts, or make global capture
health degraded. No marker is an honest reminder state, not configuration corruption.

### 7. High — the falsification seeds still allow broken implementations to pass

The seeds name cases, but several lack a closed oracle or a 1:1 mutant. Required v2 controls:

1. evaluator uses file mtime instead of the declared event → caught;
2. consumer renders `stores[0]` instead of selecting the Footballguys reminder by stable id → caught;
3. missing/malformed/future Footballguys state leaves every existing capture-health fact byte-equal;
4. `>=30d` boundary mutant and `>30d` mutant cannot both pass—v2 must choose one;
5. applying daily-store grace to the manual reminder → caught;
6. in-season weekly tightening → caught;
7. repeated reads emitting duplicate notices → caught;
8. dismissal or acknowledgement changing `last_refresh_recorded_at` → caught;
9. raw enum/schema/ISO text or “stale/unreliable/should/must” reaching the user surface → caught;
10. legacy daily-only config and responses remain valid if a shared schema is widened;
11. required backup entry without the state file, and state file without required manifest coverage,
    each fail the landing contract.

## Answers to the requested challenge questions

- **Truth-source lean:** viable only as a *declaration of a recorded refresh*. It does not prove a
  download and requires narrower copy plus an explicit write event.
- **Registry home:** the current capture-cadence registry is the wrong shape and its current consumer
  cannot surface the new row. Prefer one governed manual-feed contract; do not independently solve
  Footballguys while PlayerProfiler/PFF remain open.
- **Pre-decided scope:** the append-only vintage/hash series and future-delta utility are unearned and
  should be removed from this reminder framing.

## Standing

**NOT CLEAR for RED.** Horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, comparison not
opened. No implementation, scheduler, provider contact, intake, or data-use authority follows.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
