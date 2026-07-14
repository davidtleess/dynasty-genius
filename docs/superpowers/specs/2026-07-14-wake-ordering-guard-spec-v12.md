# Wake-Ordering Guard — Spec v12 (STANDALONE; post-RED round 11-formal, 2026-07-14)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store seconds before the fresh capture landed and degraded honestly. **Mechanism (RED-CLEAR, rounds 2–10): bounded polling of the transactional FC SQLite store.** The capture report is rejected as a sentinel. Implementation and schedule are David-gated; this document is the complete normative contract and supersedes v0–v11 entirely. v9's pointer model is REMOVED (it created a dual commit); **the marker is the single commit object.**

## Named build fixes (real defects found by this RED cycle)
- **BF-1** reader labels all source-date inequality as prior (future dates included) — classifier split required.
- **BF-2** player/trade consumers read latest files unvalidated — the G4 loader is the fix.
- **BF-3** `build_universe_market_divergence.py` / `refresh_league_intelligence.py` write governed artifacts directly — retired under G0.
- **BF-4** history writer silently skips missing IDs and last-write-wins duplicates — G7 validation.
- **BF-5** outer-refresh backup/restore can mix chain vintages — cross-stage restoration banned (G8).
- **BF-6** history writer truthiness-coerces `decision_supported` — the SQL column must be the literal integer 0; truthy/None/float input = FATAL.
- **BF-7** `run_pvo_refresh.py:371` stamps `source_as_of` with now_fn() — a BUILD time, not lineage; a "newer" PVO can carry an OLD Sleeper snapshot.
- **BF-8** `league_pulse_assembler.py:306` takes the MAX stage timestamp — an older market section can sit under a newer page date.

## G0 — Single canonical writer + enforcement scan
- The owning runner (`scripts/run_market_divergence_refresh.py`) is the ONLY writer of governed objects: generation-addressed artifacts, the marker, generation-addressed reports, the history db (incl. `history_day_meta`, `guard_meta`).
- **Scan contract (r11-12):** scope = `app/`, `src/`, `scripts/`, AND `docs/` (so the allowlisted extractor is inside the scanned set), tests excluded; the scan is AST-LEVEL, distinguishing reads from writes: WRITE operations (open modes w/a/x, rename/replace/unlink/rmtree, sqlite non-SELECT) on governed paths are legal ONLY in the runner; READ operations only in the allowlist (loader; the extractor `docs/design-comps/comp-v33-extract.py` read-only; the backup reader via the config lane, read-only). A config scan (json/plist/yaml under `app/config/`, `ops/`) covers config-driven access; CONFIG CONSUMERS are first-class allowlist entries: the launchd plists (invoke the runner only), report_freshness.json (names the committed marker), backup_manifest.json (read-only backup lane). Any other reference fails.
- **Migration sequence (pinned):** deploy order = (1) config anchor committed; (2) loader module + shared validator land with a LEGACY FALLBACK (pre-first-commit, the loader serves today's unsuffixed artifacts flagged `legacy_unguarded`); (3) consumers migrate to the loader; (4) the first guarded owning run publishes generation-addressed artifacts + attempt/committed markers; (5) the legacy fallback and unsuffixed artifacts retire after the first commit; (6) the scan test turns on. Each step is separately shippable and David-gated.

## G1 — Retry state machine (carried, complete)
- `target_snapshot_date` = canonical `YYYY-MM-DD` derived ONCE from an aware-UTC datetime at process start.
- Classify every read: `== target` FRESH · `< target` RETRYABLE (only this) · `> target` FATAL · missing/corrupt/ambiguous FATAL.
- Config `WINDOW=1800s`, `INTERVAL=60s`; exact non-bool positive ints, INTERVAL ≤ WINDOW; violation = config-error terminal.
- Loop per wake: (1) fresh UTC sample — date ≠ target ⇒ cross-midnight terminal; (2) resample monotonic; ≥ deadline ⇒ FINAL read; (3) else read+classify; (4) sleep `min(INTERVAL, deadline − now_mono)` from the POST-read sample. Post-read UTC+monotonic resample decides finality and the date gate in EITHER wall-jump direction; a read returning past midnight terminates; a read completing past the deadline IS final (classified normally — FRESH proceeds). Large overshoot ⇒ one final read. `retries_used` = reads after the first. A publish-time UTC gate runs immediately before the first artifact write.

## G2 — PVO contract (basis recorded)
- Re-resolved and re-verified AFTER the market gate; **verified-bytes consumption** (hash and load the same bytes/fd).
- `source_as_of`: non-null, parseable, aware, UTC-normalized, ON the target UTC day; else PVO fail-close.
- **The marker records the consumed basis AS LINEAGE (r11-2, BF-7):** `input_pvo_source_as_of` = the PVO's build stamp, AND `input_pvo_snapshot_captured_at` = the underlying SLEEPER SNAPSHOT vintage (true model lineage), plus `input_pvo_kind` and the three input digests. Cadence comparisons use the SNAPSHOT lineage: a PVO rebuilt today from an old snapshot is `pvo_pending_lineage` — the divergence comparison is marked pending/suppressed, never legitimized by two build dates.
- Canonical digest inputs: exact PVO bytes; exact PVO-coverage bytes; market rows as ONE canonical JSON array (UTF-8, sort_keys, ensure_ascii=False, separators, allow_nan=False), ordered by `player_key` (nonempty string; missing/duplicate/wrong-type/nonfinite = FATAL).

## G3 — Commit model: THE MARKER IS THE COMMIT (single point)
- Artifacts are **generation-addressed**: `..._latest_<generation_id>.json`, `..._coverage_<generation_id>.json` (uuid4 per owning invocation, regenerated on restart). No un-suffixed governed artifact exists.
- **TWO MARKER SLOTS (r11-5 — crashes and handled failures must expose ONE freshness semantics):** `marker_committed.json` (atomically replaced ONLY by ok markers — the serving truth) and `marker_attempt.json` (atomically replaced by EVERY terminal, ok or degraded — the attempt truth). Serving/loaders read committed ONLY; health reads BOTH. A handled degraded failure updates attempt and leaves committed serving the last good generation — exactly like a crash does; EVERY terminal class applies this same freshness rule.
- **Serve-stale-DISCLOSED (the round-11 ruling: never serve last-known AS FRESH):** the loader's return carries `committed_finished_at` and `latest_attempt` (status+reason+finished_at); every surface MUST render the committed age and, when the latest attempt is degraded or newer, the stale/degraded disclosure (the shipped market_source_prior_date behavior, generalized). A consumer that discards these fields fails the build RED.
- **G-ORDER (total):** history transaction → artifact files (temp+rename each; INERT until referenced) → generation-addressed report → attempt marker; iff ok, committed marker LAST. The committed marker names `latest_path`/`coverage_path`/`report_path` (confined; exact generation basename patterns; no traversal/symlinks) + all hashes. **A generation exists for consumers ONLY through the committed marker.** Crash anywhere pre-commit: the previous committed marker serves the previous generation, retention-protected. No pointer, no dual commit, no mixed-pair state.
- **GC protocol (computable — r11-6):** a `generations` index table (generation_id, finished_at, artifact paths) written with each committed marker gives durable ordering; "previous" = the prior row. Only the owning runner prunes under the G5 lock: candidates = generations older than the newest 3 AND unreferenced by committed/attempt markers AND past a ≥24h grace; the runner RE-READS both markers immediately before each unlink; deletion is whole-generation (files, then the index row); GC failure = log + exit nonzero, never a partial generation. Temp files older than a day are swept in the same pass. Reader retry: marker-snapshot → ENOENT ⇒ re-read the committed marker ONCE, retry, fail-close on a second miss.
- `#148` config change: the health entry gains `verification_mode: "marker_committed"` and names the COMMITTED-marker path only; companions, hashes, and the attempt-marker path resolve FROM marker fields. The checker's fact fields and base precedence are the G4 enum in its pinned order.

## G4 — Verified loader + caller contracts
- The loader reads the marker (shared strict validator first), verifies status=ok, opens the marker-named artifact paths, recomputes both output hashes from the exact returned bytes. Any failure → the caller's pinned contract.
- **Composite PVO coherence (computable via G2 basis):** compare the currently-served PVO's `source_as_of`+bytes to the marker's recorded basis. Current PVO SAME bytes ⇒ coherent. Current PVO NEWER (by SNAPSHOT LINEAGE, not build stamp) ⇒ the current model renders and **the divergence comparison is SUPPRESSED/NULLED (`gap_basis_stale`) until the next divergence run recomputes it** — a stored gap computed against a prior model is never presented as the current model’s gap, however clearly dual-stamped (round-11 ruling). The normal daily window is ~10 minutes (09:30 PVO → 09:40 divergence); multi-day windows surface the same way, longer. Current OLDER ⇒ `pvo_regressed`, fail-close. SAME `source_as_of`, DIFFERENT bytes ⇒ `pvo_mismatch`, fail-close. One-side unreadable ⇒ fail-close. Current PVO itself unverified ⇒ that surface's PVO contract governs (never served as coherent).
- **Trade honesty (r11-3):** trade surfaces never recompute captured-market digests from their own cache shapes (row populations/shapes differ by design). They obtain the divergence context THROUGH the loader (which verified the pair) and compare VINTAGES: the marker's market-input basis vs the price-fetch's own as-of. Dual-stamp both ("price as fetched X (cache ≤ TTL) · gap basis as of Y" — "live" is banned as overclaiming a possibly-cached response); loader failure or missing basis ⇒ SUPPRESS the gap context, serve pricing alone.
- **Caller contracts (exact):** the status enum is CLOSED: {ok, marker_malformed, generation_mismatch, output_hash_mismatch, companion_unreadable, producer_failure, pvo_regressed, pvo_mismatch, pvo_pending_lineage, chain_mixed}. Precedence = that order (first failure wins). Field locations: top-level `market_lane_status` (enum value) + `market_lane_reason` (producer_failure only) + `as_of` object ({pair, pvo, price_fetch} aware-UTC ISO). Players → HTTP 200, market-lane fields null, statuses as above. **Trade's combined endpoint (prices + divergence context) is NEVER 503:** pricing always serves; the divergence context inside it is suppressed with `divergence_status` carrying the enum. Divergence-ONLY endpoints → HTTP 503 `{error: "divergence_unavailable", status: <enum>}`. Health → the named base. Pulse/opportunity → stage-local vintages (G8).

## G5 — Ownership (carried)
`fcntl.flock(LOCK_EX | LOCK_NB)` on a stable never-unlinked path, held from BEFORE any canonical I/O (config validation included) through terminal. Contention errno set {EWOULDBLOCK/EAGAIN} ⇒ silent/log/exit-nonzero (contention code); any other acquisition failure ⇒ silent/log/exit-nonzero (lock-error code). No no-lock path touches shared state.

## G6 — Terminal schemas (strict discriminated union; shared validator module)
- **Marker `ok`:** `generation_id` uuid4 · `latest_path`/`coverage_path`/`report_path` (confined) · `latest_sha256`/`coverage_sha256`/`report_sha256` · `input_pvo_sha256`/`input_pvo_coverage_sha256`/`input_market_rows_sha256` · `input_pvo_source_as_of`/`input_pvo_kind` · aware-UTC `finished_at` · `retries_used` int≥0 non-bool · `decision_supported=false`. NO `reason`.
- **Every run has `attempt_id` (uuid4; on ok runs attempt_id == generation_id).** Report filename = `..._report_attempt_<attempt_id>.json` always (ok runs' reports are thereby generation-addressed automatically).
- **Marker `degraded` (exact presence table):** `attempt_id` · nonempty `reason` · `retries_used` · `target_snapshot_date` · `terminal_classification` ∈ {retryable_exhausted, fatal_source, fatal_config, pvo_failed, cross_midnight, history_failed, build_failed, validation_failed, publish_failed, report_write_failed, internal_error} · `report_path`+`report_sha256` PRESENT iff the attempt report was written, NULL iff terminal_classification == report_write_failed · every output/input field explicitly null · aware-UTC `finished_at` · `decision_supported=false`. Nothing optional, nothing extra — the shared validator enforces the exact field set for BOTH shapes; "mirroring" is defined as this same table applied to reports.
- **Reports mirror every duplicated field** (status, generation, digests, retries, finished_at, decision flag, provisional=true). **Report role: AUDIT-ONLY** — pair service never touches it; refusal-on-disagreement binds REPORT CONSUMERS exclusively (r10-9).
- Validator-before-precedence: malformed ⇒ `marker_malformed`; valid degraded ⇒ `producer_failure:<reason>`, companions skipped; valid ok ⇒ full verification. One marker attempt; attempt-failure ⇒ log + exit nonzero, previous marker canonical.

## G7 — History (exact-set, authenticated, adoptable)
- One transaction: validate candidates (nonempty unique normalized string IDs; payload strict-JSON: duplicate-key rejection via object_pairs_hook, parse_constant rejection, recursive finiteness walk catching 1e9999; the SQL COLUMN `decision_supported` = the EXACT integer 0 (None/0.0/True/"0" FATAL) — while the PAYLOAD's OWN `decision_supported` JSON field, where present, must be JSON `false` (payloads legitimately contain thousands of other boolean falses; the two laws are SPLIT — r11-9. LANDED (the formal round-11 verdict reviewed the earlier 2c733de3 bytes; strict duplicate-key rejection, the payload-field law, one-transaction snapshot reads, and the V3 comment are all in the current extractor))) → DELETE(day) → INSERT full set → upsert `history_day_meta` (`capture_date` PK, `generation_id`, `content_sha256`, `row_count`, `written_at_utc`, `legacy` bool — strict union: live rows have uuid4+legacy=false; legacy rows have NULL+legacy=true).
- **content_sha256 = the landed MANIFEST V3 algorithm, byte-identical between spec and extractor (cross-verified this round: 2026-07-09:81853281…, 2026-07-11:721c0f91…):** one canonical enclosing JSON array of raw stored tuples `[player_id, capture_date, decision_supported, payload_json-as-stored-string]`, sorted by player_id, canonical encoding. Whitespace/duplicate-key payload mutations change the digest because the STORED STRING is hashed.
- **guard_meta durability, CONFIG-FIRST (r11-10):** `effective_from_date` lives in committed config (`app/config/wake_ordering_guard.json`, content David-gated) BEFORE any guarded run; the runner may only INITIALIZE the db singleton FROM that authority (never write the config). States pinned: config absent ⇒ the guard refuses to run (pre-deployment); db absent w/ config present ⇒ initialize (bootstrap); both present + equal ⇒ normal; disagreement ⇒ fail-close (restored/recreated db detected); db mutation attempts ⇒ the singleton is INSERT-only (no UPDATE path exists). Backfill (`--backfill-legacy`, owner-run) targets ONLY pre-effective dates; post-effective backfill is BANNED.
- Legacy days (pre-effective, meta legacy=true or absent): readable, flagged `pre-guard legacy`. Post-effective missing/invalid meta: fail-close.

## G8 — Chain disclosure (the refresh is a DAG)
- **Stage graph pinned (CONSTITUTIONALLY ORDERED — v10's arrow was wrong and is retracted):** TWO INDEPENDENT ROOTS. Root M (model lane): Sleeper snapshot → runtime features → PVO — market data NEVER appears upstream of the model (constitutional law). Root K (market lane): FC capture. The lanes JOIN ONLY at divergence construction (model outputs + market overlay). Downstream: divergence → opportunity map; divergence + stage artifacts → league pulse. The build RED enumerates every edge from refresh_league_intelligence.py with its digest domain (the exact bytes consumed). No ellipses; the graph is closed.
- Cross-stage file restoration is BANNED (BF-5). After a mid-chain failure the chain MAY be mixed; the chain-coherence health fact walks the DAG edges and reports `chain_mixed` naming every stale edge and both vintages. Downstream surfaces carry SECTION-LOCAL vintages: League Pulse's max-timestamp page date (BF-8) is replaced by per-section as-ofs, and a stale market section suppresses its market overlay rather than borrowing the page date.

## Verification matrix (explicit; setup → expected terminal → canonical checks)
| # | Setup | Expected |
|---|-------|----------|
| 1 | store fresh at first read | proceed; retries_used=0; committed+attempt ok markers |
| 2 | stale then fresh mid-window | proceed; retries_used=N |
| 3 | stale through window; final read stale | degraded(retryable_exhausted); committed marker UNTOUCHED |
| 4 | final at-deadline read fresh | proceed to publication |
| 5 | future source_date any read | degraded(fatal_source) immediately |
| 6 | corrupt/missing store any read (incl. mid-window turn) | degraded(fatal_source) immediately |
| 7 | config bool/float/string/negative/INTERVAL>WINDOW | degraded(fatal_config); no run body |
| 8 | UTC rollover at each loop stage + read straddling midnight + publish-time gate | degraded(cross_midnight); nothing published |
| 9 | wall jumps both directions | monotonic deadline unaffected; post-read UTC law enforced |
| 10 | large oversleep | exactly one final read |
| 11 | PVO swapped during wait | re-verify consumes new bytes or pvo_failed |
| 12 | PVO hash-valid, prior-day as_of | pvo_failed |
| 13 | PVO as_of malformed/missing/naive | pvo_failed |
| 14 | PVO rebuilt now from an OLD Sleeper snapshot | marker records lineage; consumers see pvo_pending_lineage |
| 15 | market rows: missing/dup/blank/non-string player_key or nonfinite | degraded(fatal_source) |
| 16 | crash before artifacts / between files / pre-report / pre-attempt-marker / pre-committed-marker | previous committed marker serves previous generation (five distinct kills, one outcome) |
| 17 | committed-marker attempt write fails | log+nonzero; previous committed canonical; attempt marker reflects the run |
| 18 | handled degraded failure | attempt updated; committed untouched; serving identical to crash case |
| 19 | GC: candidate selection (newest-3/referenced/grace) | never prunes protected generations |
| 20 | GC: marker re-read before unlink; whole-generation delete; GC failure | no partial generations; log+nonzero |
| 21 | reader ENOENT after prune race | one marker re-read + retry; second miss fails close |
| 22 | loader vs tampered artifact bytes | output-hash recompute refuses |
| 23 | loader vs malformed marker (each field of both shapes) | shared validator rejects; marker_malformed |
| 24 | valid degraded marker | health producer_failure:<reason>; companions skipped |
| 25 | PVO newer (incl. multi-day) by lineage | model serves current; gap SUPPRESSED w/ gap_basis_stale until recomputed |
| 26 | PVO older | pvo_regressed; fail-close |
| 27 | PVO same as_of different bytes | pvo_mismatch; fail-close |
| 28 | one companion unreadable | companion_unreadable |
| 29 | trade combined endpoint w/ divergence unavailable | 200; pricing serves; divergence_status carries the enum; dual-stamped when present |
| 30 | players w/ each failure enum | 200; null lane; market_lane_status exact |
| 31 | divergence-only endpoint failure | 503 {divergence_unavailable, status} |
| 32 | report consumer: field disagreement or report_sha256 mismatch | commitment refused (consumers only) |
| 33 | lock contention / acquisition-error / owner crash | silent-nonzero ×2 (distinct codes); kernel release |
| 34 | degraded run whose attempt report wrote | report_path+sha present on the degraded marker |
| 35 | report_write_failed | report fields null; classification exact |
| 36 | history replay {A,B}→{A} | exact set {A}; meta updated |
| 37 | history candidates: dup/missing/blank keys | transaction rollback; degraded(history_failed) |
| 38 | SQL decision column ≠ int 0 (True/None/0.0/"0") | FATAL (BF-6) |
| 39 | payload decision_supported present ≠ false | FATAL; other payload booleans UNAFFECTED (the split law) |
| 40 | payload dup keys / NaN / Infinity / 1e9999 | strict parse rejects |
| 41 | any stored-column flip on a hashed day | MANIFEST V3 digest breaks (cross-verified 81853281/721c0f91) |
| 42 | concurrent exact-set replacement during evidence read | single-transaction snapshot; no A-manifest/B-payload mix |
| 43 | legacy (pre-effective) day | readable; flagged pre-guard legacy |
| 44 | post-effective day missing meta | fail-close |
| 45 | guard config absent / db-config disagreement / db recreated | refuse-to-run / fail-close / fail-close |
| 46 | post-effective backfill attempt | refused |
| 47 | mid-chain failure | chain_mixed names stale edges; no restoration; stages keep own generations |
| 48 | League Pulse w/ a stale market edge | section-local as-ofs; market overlay suppressed (BF-8) |
| 49 | AST scan: write op outside the runner / read outside allowlist / config-driven access | fail / fail / visible+allowlisted |
| 50 | migration: pre-first-commit loader fallback | serves unsuffixed flagged legacy_unguarded; retires after first commit |
