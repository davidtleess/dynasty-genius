# Wake-Ordering Guard — Spec v15 (STANDALONE FULL REWRITE; post-RED round 14, 2026-07-14)

Problem (2026-07-12): the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read seconds-stale market data and degraded honestly. **Mechanism (RED-CLEAR throughout): bounded polling of the transactional FC SQLite store.** Implementation/schedule are David-gated. This document supersedes v0–v14; every prior version's matrix is void — the matrix below is regenerated from THIS contract.

## Build fixes (real defects this RED cycle found; each is its own build item)
BF-1 prior/future date mislabel · BF-2 unvalidated pair readers · BF-3 bypass writers · BF-4 history key silent-skip · BF-5 cross-stage restore rollback · BF-6 decision_supported truthiness coercion · BF-7 PVO source_as_of = build time, not lineage · BF-8 Pulse max-timestamp masking · BF-9 finished_at reuses the start clock · BF-10 untyped price cache staleness.

## G1 — Retry loop (unchanged since r7; carried whole)
Canonical `target_snapshot_date` (YYYY-MM-DD from aware-UTC at start). Classify every read: ==target FRESH · <target RETRYABLE (only) · >target FATAL · missing/corrupt FATAL. Config `WINDOW=1800`/`INTERVAL=60`, exact non-bool positive ints, INTERVAL ≤ WINDOW. Per wake: UTC-rollover check → monotonic deadline check (≥ ⇒ FINAL read) → read+classify → clipped sleep from the POST-read monotonic sample. Post-read UTC/monotonic resample decides finality and the date law in either wall-jump direction; a read returning past midnight terminates; a read past deadline IS final, classified normally. Publish-time UTC gate before the first artifact write. `retries_used` = reads after the first.

## G2 — PVO consumption
Re-resolved + re-verified after the market gate; verified-bytes consumption (hash and load the same bytes). `source_as_of` non-null/parseable/aware/UTC/on-target-day, else pvo_failed. The marker records `input_pvo_sha256`, `input_pvo_coverage_sha256`, `input_market_rows_sha256`, `input_pvo_source_as_of`, `input_pvo_snapshot_captured_at` (true lineage — BF-7), `input_pvo_kind`. Market-rows digest: ONE canonical JSON array (UTF-8, sort_keys, ensure_ascii=False, separators(",",":"), allow_nan=False) ordered by `player_key` (nonempty string; missing/dup/wrong-type/nonfinite ⇒ FATAL).

## G3 — Commit model
Generation directory `generations/<commit_seq>_<generation_id>/` holds latest+coverage (INERT until referenced). **Publication order: history transaction → artifact files → iff ok: COMMITTED marker → ATTEMPT marker; degraded: ATTEMPT marker only. Reports write after ALL markers, or not at all.**
- Markers: two independently stable config-pinned paths. Committed = ok-only serving truth; attempt = every handled terminal. `commit_seq` (monotonic int) persists in both (committed = prior+1; attempt carries its candidate).
- **Marker-pair reduction (exhaustive, by seq then attempt_id):** committed.seq > attempt.seq ⇒ attempt_lagged (benign; post-commit crash before attempt write). committed.seq == attempt.seq ∧ same attempt_id ⇒ normal (ok run fully recorded). committed.seq == attempt.seq ∧ different attempt_id ⇒ commit_race_anomaly (health alarm; impossible under G5 single-flight unless identity was violated — surfaced, never inferred away). committed.seq < attempt.seq ∧ attempt degraded ⇒ current failure, last-good serves w/ dashing rules. committed.seq < attempt.seq ∧ attempt ok ⇒ publish_incomplete (an ok attempt without its commit: the committed rename failed after the attempt should NOT exist — under the pinned order this state is impossible; if observed ⇒ health alarm, serve committed).
- **Reports are AUDIT-ONLY and OUTSIDE producer terminal truth (r14-1):** written last, named by attempt_id, mirroring the terminal markers; a report-write failure is LOG + nonzero exit ONLY — it is not a marker state, not a terminal_classification, and no marker references any report field. Report consumers validate by attempt_id + the shared validator against the markers.
- GC: whole-generation quarantine = one rename to `.trash/`; ordering = the dirname seq; retention = the current-committed directory + anything younger than GRACE_GC(24h) mtime; placement in the total order: GC runs at owning start, BEFORE the new run's history transaction, under the same lock; GC failure = log + nonzero, run continues (pruning is never load-bearing). Partial quarantine re-quarantines next start. Reader ENOENT ⇒ discard the whole snapshot, re-read committed + both companions once; second miss fails close.

## G4 — Verified loader + closed status law
- Loader: shared strict validator FIRST (malformed ⇒ marker_malformed) → status precedence → for ok: open the generation dir's files, recompute both hashes from returned bytes (mandatory).
- **ONE closed lane-status enum (every emitter uses only these):** `ok` · `ok_stale` (schedule-overdue; serve-with-dash) · `no_committed_generation` · `legacy_unguarded` · `evidence_lost` (post-activation committed loss) · `marker_malformed` · `generation_mismatch` · `output_hash_mismatch` · `companion_unreadable` · `producer_failure` (carries `reason`) · `gap_basis_stale` · `pvo_regressed`. **Warnings (separate field `lane_warnings[]`, never lane status):** `pvo_pending_lineage`, `pvo_content_anomaly`, `attempt_lagged`, `clock_anomaly`, `chain_mixed`, `commit_race_anomaly`.
- **PVO branches (exhaustive; status first, warnings second):** PVO unresolvable/unverified ⇒ companion_unreadable. Bytes EQUAL ⇒ ok (+pvo_pending_lineage warning iff lineage differs). Bytes DIFFER ∧ current lineage OLDER ⇒ pvo_regressed. Bytes DIFFER ∧ lineage same ⇒ gap_basis_stale + pvo_content_anomaly warning. Bytes DIFFER ∧ lineage newer ⇒ gap_basis_stale.
- **Cadence (ONE authority — r14-3):** `wake_ordering_guard.json` carries `schedule` ("09:40 America/New_York daily") and `grace_minutes` (30). `report_freshness.json`'s legacy `grace_hours` is MIGRATED to reference this config (a build item with an equality test binding loader, health, and the launchd plist). `due = next occurrence after committed_finished_at`; `overdue = now > due + grace` ⇒ ok_stale (dash + prior vintage displayed). Degraded-and-newer attempt ⇒ dash immediately. `committed_finished_at > now` ⇒ clock_anomaly warning + dash.
- **Caller table (state × behavior):** players: HTTP 200; market-lane numerics null except under ok/ok_stale; `market_lane_status` + `lane_warnings` + `as_of {pair, pvo, price_fetch?}`; ok_stale renders values + dash styling + age. trade combined route: pricing per G6-price; divergence context only under ok (not ok_stale — a stale gap never renders as current context); `divergence_status` carries the enum. divergence-only endpoints: 503 {error, status} for non-ok/non-ok_stale. health: the enum value + warnings as named bases. Pulse/opportunity: per-section (G8). Manager copy per state is a build-RED table seeded from these semantics.

## G5 — Ownership (carried whole)
flock LOCK_EX|LOCK_NB on a stable path, held BEFORE any canonical I/O through terminal; contention {EWOULDBLOCK,EAGAIN} ⇒ silent/log/exit-nonzero; other acquisition errors ⇒ silent/log/exit-nonzero (distinct code). No no-lock path writes shared state.

## G6 — Terminal schemas (strict two-shape union; ONE shared validator module)
- ok: status/schema_version/commit_seq/attempt_id(=generation_id, uuid4)/generation_dir/latest_sha256/coverage_sha256/three input digests/input_pvo_source_as_of/input_pvo_snapshot_captured_at/input_pvo_kind/finished_at (aware UTC, terminal-sampled — BF-9)/retries_used(int≥0 non-bool)/decision_supported=false. NO reason, NO report fields.
- degraded: status/schema_version/commit_seq(candidate)/attempt_id/reason(nonempty)/terminal_classification ∈ {retryable_exhausted, fatal_source, fatal_config, pvo_failed, cross_midnight, history_failed, build_failed, validation_failed, publish_failed, internal_error}/target_snapshot_date/retries_used/finished_at/decision_supported=false; ALL output/input fields explicitly null. (report_write_failed is GONE — reports are outside terminal truth.)
- Reports mirror the terminal marker's fields + status, written last, attempt_id-named, audit-only.
- **G6-price (r14-8):** the price result is DISCRIMINATED: {available: price, source_fetched_at, checked_at, cache_state ∈ {fresh, cached_within_ttl, stale_cache_served}} | {unavailable: reason ∈ {cold_unavailable, corrupt, future_stamp, naive_stamp}} — **unavailable NEVER coerces to zero; totals/derived values over unavailable inputs are null with copy "price unavailable", never 0.**

## G7 — History (exact-set, authenticated, computable authority)
- One transaction: validate candidates (nonempty unique normalized string IDs; strict-parsed payloads — duplicate keys rejected, non-finite rejected, numerics bounded; SQL `decision_supported` = exact integer 0; the payload's own decision_supported fields = exact JSON false, recursively) → DELETE(day) → INSERT full set → upsert `history_day_meta` {capture_date TEXT PK, generation_id TEXT|NULL, content_sha256 TEXT(64), row_count INT, written_at_utc TEXT, legacy BOOL, **surface_committed BOOL default false**}.
- **Computable authority (r14-7):** after the COMMITTED marker succeeds, the runner sets `surface_committed=true` for its day (post-commit, best-effort; a crash leaves false). Pending = `surface_committed=false` on a non-legacy day — historical committed days keep true regardless of later generations; Daily movement can distinguish pending from historical success by THIS column, not by generation comparison.
- content_sha256 = MANIFEST V3 (the landed, cross-verified algorithm; byte rules as G2). Readers recompute count+hash in ONE snapshot; mismatch or missing-meta-post-effective ⇒ fail-close. Legacy (pre-effective) days readable, flagged. Evidence extractor status: strict-parse-everywhere + universe validation + one-transaction reads LANDED (sha ae643112…).

## G8 — Chain provenance (executable)
DAG (constitutional; market never upstream of the model): {snapshot, prospect, identity, engine-B} → PVO · {FC, PVO} → divergence · {snapshot, PVO} → roster-cut, team-matrix · {team-matrix} → posture · {team-matrix, divergence, posture, roster-cut} → opportunity · {posture, team-matrix, opportunity} → pulse. **Per-SUBSECTION dependency closure (r14-9):** every Pulse section and Opportunity subsection (incl. partner rankings) declares its closure = the LIST of {stage, expected_vintage, observed_vintage, status}; `market_provenance` = true iff any transitive ancestor is the market lane; a stale/failed market edge suppresses that subsection's market-derived content while model-native subsections serve. Top-level Pulse `captured_at` is RETIRED (each section self-stamps). Raw enums/schema versions are receipt-only.

## G9 — Bootstrap, activation, migration (one ordered lifecycle — r14-10)
Committed config (effective_from_date) → deploy loader+validator (fallback `legacy_unguarded`) → consumers migrate → first guarded run (bootstrap mints `db_instance_id`; failure here RETAINS the fallback — the fallback retires only later) → first guarded COMMIT → the LATCH: a David-gated config commit recording {activated, activation_generation_id, db_instance_id} — **witnessed by git history; a config rollback is detectable because the latch commit exists in the repo log and disagreement between config, db singleton, and marker chain fails closed** → scan green → retire unsuffixed artifacts → rescan. Post-latch: db/singleton absent or db_instance_id mismatch ⇒ fail-close; committed-marker loss ⇒ `evidence_lost` (distinct from first-run: model/roster facts serve, market/gap/movement dash, PRIOR VINTAGE displayed when known from the attempt marker or history meta, ops detail behind the receipt — copy never claims "no read yet" when evidence existed).

## Absence UX (r14-11, three distinct states)
`legacy_unguarded`: unsuffixed data serves, flagged, receipt explains migration. `no_committed_generation` (first-ever): model facts serve; market/gap/movement dash; copy "no verified market read yet"; as_of carries only the PVO vintage. `evidence_lost` (post-activation): same dashing; copy "market history verification unavailable"; prior vintage shown when known; health alarm.

## Verification matrix (regenerated from THIS contract; every row cites its section)
| # | Setup | Expected | § |
|---|-------|----------|---|
| 1 | immediate fresh | ok markers, retries 0 | G1 |
| 2 | stale→fresh | ok, retries N | G1 |
| 3 | stale through window (final read stale) | degraded retryable_exhausted; committed untouched | G1 |
| 4 | final-at-deadline read fresh | proceeds | G1 |
| 5 | future/corrupt/missing store any read | degraded fatal_source | G1 |
| 6 | bad config shapes (bool/float/str/neg/INT>WIN) | degraded fatal_config, no run body | G1 |
| 7 | rollover at each stage; straddling read; publish gate; wall jumps | cross_midnight; monotonic unaffected | G1 |
| 8 | PVO swap/prior-day/malformed/naive as_of | pvo_failed | G2 |
| 9 | market rows bad player_key/nonfinite | fatal_source | G2 |
| 10 | kill at EACH publication boundary (5 points) | previous committed serves; reduction table names each state | G3 |
| 11 | committed-rename failure on ok run | no attempt written yet (order); prior committed serves; log+nonzero | G3 |
| 12 | attempt-write crash post-commit | attempt_lagged warning; self-heals | G3 |
| 13 | equal-seq different-attempt-id markers | commit_race_anomaly alarm; committed serves | G3 |
| 14 | report write fails (after markers) | log+nonzero only; markers stand; no terminal state change | G3 |
| 15 | GC: retention/quarantine/partial/failure | current+<24h kept; one-rename quarantine; re-quarantine; run continues | G3 |
| 16 | reader ENOENT race | whole-snapshot discard, one retry, then fail-close | G3 |
| 17 | tampered artifact bytes / malformed marker fields | output_hash_mismatch / marker_malformed | G4 |
| 18 | valid degraded marker | producer_failure:<reason>; companions skipped | G4 |
| 19 | PVO branch table (all five branches) | statuses/warnings exactly as pinned | G4 |
| 20 | overdue by schedule (missed 09:40, checked 10:11+) | ok_stale; dash + prior vintage + age | G4 |
| 21 | degraded-and-newer attempt | immediate dash | G4 |
| 22 | committed_finished_at in the future | clock_anomaly warning + dash | G4 |
| 23 | each caller × each status | the caller table exactly; trade context only under ok | G4 |
| 24 | lock contention / acquisition error / owner crash | distinct nonzero codes; kernel release | G5 |
| 25 | marker field-by-field malformation (both shapes) | shared validator rejects | G6 |
| 26 | price unavailable (each reason) | null totals/derived, "price unavailable", NEVER 0 | G6 |
| 27 | stale cache served | cache_state=stale_cache_served rendered | G6 |
| 28 | history dup/missing/blank keys; SQL ds≠int0; nested ds≠false; dup payload keys; 1e9999 as Decimal AND huge int | rollback / FATAL per law (all landed in the evidence extractor) | G7 |
| 29 | day-content flip incl. ds column | V3 digest breaks (cross-verified 81853281/721c0f91) | G7 |
| 30 | crash after history, before commit | meta.surface_committed=false ⇒ pending; evidence usable; converges next same-day success | G7 |
| 31 | historical committed day after later generations | surface_committed=true persists; never re-flagged pending | G7 |
| 32 | meta missing post-effective / recompute mismatch | fail-close | G7 |
| 33 | refless/live/ref-pinned extractor modes + WAL swap during read | one-snapshot law holds (landed); manifest verified | G7 |
| 34 | mid-chain failure | per-subsection closure names stale edges; model-native serves; market-derived suppresses | G8 |
| 35 | Pulse page date | top-level captured_at absent; sections self-stamped | G8 |
| 36 | lifecycle: pre-latch db loss / post-latch db loss / instance-id mismatch / config rollback | re-bootstrap / fail-close / fail-close / git-witness disagreement fails closed | G9 |
| 37 | first guarded run fails during migration | fallback RETAINED (retires only post-latch sequence) | G9 |
| 38 | three absence states | distinct statuses, copy, nullables; evidence_lost shows prior vintage | UX |
| 39 | unsanctioned writer/reader (AST scan incl. config lane) | fails; allowlist exact | G0* |
| 40 | schedule-config equality (loader vs health vs plist) | one authority; migration test binds them | G4 |

*G0 (single canonical writer, AST-level scan, per-object allowlists incl. the docs extractor by path, config consumers first-class) carried verbatim from v13 — unchanged this round.
