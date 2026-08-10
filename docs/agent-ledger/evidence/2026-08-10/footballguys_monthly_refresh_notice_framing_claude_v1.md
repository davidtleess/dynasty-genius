# Footballguys monthly refresh notice — framing v1 (Claude, implementing lane)

Date: 2026-08-10 · **Layer 1 (ingest — freshness surfacing for a manual paid source)**; layers 1–2,
so the `05` §3 Rule-2 check does not apply.

**David's ruling, verbatim (2026-08-10):** *"keep it as a paid source of mine - have a reminder or
refresh notice come up once a month"*.

**Scope: framing only, per the `02` framing-first rule (this is a new David-facing notice).** No
RED, no build, no scheduler install, no provider contact, no model input. The pilot's decision
gates are untouched: horizon FAILED, cohort floor FAILED, ingestion RED CLOSED, comparison not
opened — **a refresh reminder is not a use of the data and does not reopen any of them.**

## 1. The concrete manager moment

David pays for Footballguys. The bundle is a **manual first-party download** (Draft Dominator app →
CSVs inside it); ToS bars scraping, so no job can fetch it. Without a surfaced nudge, the paid
subscription silently decays into stale local files. The moment served: **David logs in, and when
his last Footballguys drop is older than a month, the product tells him so** — same daily-login
surface that already carries capture health, nothing new to check.

## 2. What exists to build on (measured, cited)

- `app/config/capture_cadence.json` — governed per-store cadence declarations (`expected_cadence`,
  grace, warn thresholds) consumed by the capture-health surface. Currently DB-backed stores with
  `daily` cadence; **a monthly manual-drop file store is a new shape for it** (no scheduled_time,
  no density floor — those concepts are meaningless for a manual monthly drop and must not be
  faked).
- The manual-feed drop pattern (PFF/PlayerProfiler inbox-drop) — the 2026-08-08 cadence-engine
  session; **the PlayerProfiler/PFF manual-drop cadence item is still an open David item**, so this
  framing must not silently pre-decide that design; it names the overlap and stops there.
- The B21/PFF declared-provenance intake pattern if David's drop is ever formally ingested — **out
  of scope here**; this notice needs only a recorded "last drop" timestamp, not an intake.

## 3. Design question the RED must settle (not pre-decided here)

**What is the truth source for "last drop"?** Candidates: (a) a David-declared marker written at
drop time (explicit, honest, one manual step); (b) mtime/hash of a watched inbox path (zero-step
but infers provenance from filesystem state — the anti-pattern `pff_intake.py` exists to avoid);
(c) piggyback on a future formal intake (couples the reminder to an unbuilt system). The framing
leans to (a) as the only provenance-honest option but **the challenge round should pressure this.**

## 4. Mislead / nudge risks (the notice must not lie)

1. **A reminder is not a staleness verdict on the data.** Provider off-season median gap is 7 days
   (n=159, provider-published changelog); David chose monthly. The notice must say "your last
   download is N days old; monthly refresh due" — **never** "data is stale/unreliable" and never
   imply the provider updated (we cannot know without fetching).
2. **No fake precision.** In-season median (4 days) is WEAK (n=8) and must not appear.
3. **No verdict language.** "Refresh due" is a cadence fact; "you should re-download now to fix X"
   is a directive the No-Verdict Line bars. `decision_supported=False` on any payload.
4. **Absence surfaces honestly.** If no drop was ever recorded, the state is "no drop recorded",
   not a fabricated age.

## 5. Falsification seeds for the RED

- no marker at all → `no_drop_recorded`, never a synthetic date, never a crash
- marker in the future / malformed / wrong shape → fail-closed named reason
- exactly 30/31 days, month boundaries, DST, timezone (config is America/New_York)
- season-awareness: David said monthly, flat — the RED should pin that it does NOT quietly go
  weekly in-season without a new David word
- notice must not appear when age < threshold; must appear at threshold+grace; idempotent across
  repeated reads
- banned-language scan on the notice payload (no buy/sell/must/should)
- the new store entry must not break existing capture-health stores (schema widening is a contract
  change → this cockpit cycle)
- backup-manifest law: a marker file under `app/data/` that cannot be regenerated → manifest entry
  lands in the same change set, or the marker lives where it is already covered

## 6. Compounding lens

Daily-login value: the reminder rides the existing login surface. Refresh cadence: matched to
David's chosen monthly, season-flat until he says otherwise. Compounding: each drop appends to the
provider's local vintage series (drop dates + hashes), which is exactly the record a future intake
or delta study (David's open Q2) would need — capture-and-accumulate, not overwrite.

## 7. Out of scope

Formal `adp.csv` intake · any comparison or delta work (David's Q2 is a separate open question) ·
scheduler installs (none needed: the notice computes age at read time on existing surfaces) ·
any change to the pilot's failed gates.

**PLEASE CHALLENGE (Codex): the §3 truth-source lean, the §5 seed set's gaps, whether the
capture_cadence.json widening is the right home versus a separate manual-feeds registry (given the
open PFF/PlayerProfiler item), and anything this framing pre-decides that is David's.**
