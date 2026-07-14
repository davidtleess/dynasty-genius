# Wake-Ordering Guard — Spec v13 (STANDALONE; post-RED round 12, 2026-07-14)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store seconds before the fresh capture landed and degraded honestly. **Mechanism (RED-CLEAR, rounds 2–10): bounded polling of the transactional FC SQLite store.** The capture report is rejected as a sentinel. Implementation and schedule are David-gated; this document is the complete normative contract and supersedes v0–v12 entirely. v9's pointer model is REMOVED (it created a dual commit); **the marker is the single commit object.**

## Named build fixes (real defects found by this RED cycle)
- **BF-1** reader labels all source-date inequality as prior (future dates included) — classifier split required.
- **BF-2** player/trade consumers read latest files unvalidated — the G4 loader is the fix.
- **BF-3** `build_universe_market_divergence.py` / `refresh_league_intelligence.py` write governed artifacts directly — retired under G0.
- **BF-4** history writer silently skips missing IDs and last-write-wins duplicates — G7 validation.
- **BF-5** outer-refresh backup/restore can mix chain vintages — cross-stage restoration banned (G8).
- **BF-6** history writer truthiness-coerces `decision_supported` — the SQL column must be the literal integer 0; truthy/None/float input = FATAL.
- **BF-7** `run_pvo_refresh.py:371` stamps `source_as_of` with now_fn() — a BUILD time, not lineage; a "newer" PVO can carry an OLD Sleeper snapshot.
- **BF-8** `league_pulse_assembler.py:306` takes the MAX stage timestamp — an older market section can sit under a newer page date.
- **BF-9** the runner reuses its START clock sample for `finished_at` — terminal timestamps must be sampled at terminal write.
- **BF-10** the FC adapter serves cache beyond TTL with no typed fetched_at — truthful price-basis copy needs `fetched_at` + `cache_state`.

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
- **TWO INDEPENDENTLY STABLE MARKER SLOTS (r12-1):** `marker_committed.json` and `marker_attempt.json` are BOTH config-pinned stable paths (neither resolved from the other; the ok schema carries no attempt locator). Committed is replaced only by ok markers (the serving truth); attempt by EVERY terminal. **First-run:** before the first guarded commit the loader returns `no_committed_generation`; surfaces render their absent-data contract (or the flagged migration fallback).
- **Serve-stale-DISCLOSED + END-USER FAIL-CLOSE (r12-2):** the loader returns `committed_finished_at` + `latest_attempt` (status/reason/finished_at); internal last-good use requires disclosure. **Consumer overlays fail closed by CADENCE:** `now − committed_finished_at > STALE_AFTER` (config; default 26h) OR a degraded-and-newer attempt ⇒ the market lane DASHES/NULLS per composition v3.14 with the age rendered. A crash that writes no attempt cannot look fresh — staleness derives from committed age alone. Consumers discarding these fields fail the build RED.
- **G-ORDER (total):** history transaction → artifact files (temp+rename; INERT until referenced) → generation-addressed report → **iff ok: COMMITTED marker, THEN attempt marker** (a failed committed rename ⇒ the attempt records `publish_failed`, never a false ok — r12-3); degraded runs write attempt only. State table: B/B ok · committed=B/attempt=A-old (attempt-write crash post-commit ⇒ health `attempt_lagged`, self-heals) · A/B-degraded (handled failure) · A/A (pre-attempt crash ⇒ the cadence rule governs). "Every terminal" scopes to runs REACHING terminal handling; crashes are covered by cadence. Crash anywhere pre-commit: the previous committed marker serves the previous generation, retention-protected.
- **GC protocol (r12-7 — the index is a DERIVED CACHE, honestly):** the `generations` index (generation_id, `commit_seq` monotonic int, paths) is REBUILT at each owning start from the markers + directory listing (a crash between marker and index can neither lose nor invent a committed generation); ordering = commit_seq, never wall time. Prune = older than newest-3 by commit_seq AND unreferenced by either marker AND ≥24h grace; both markers re-read immediately before acting; deletion = QUARANTINE (rename the whole generation to `.trash/<gen>/`) then unlink — partial GC states are recovered at the next owning start, not denied. GC failure = log+nonzero; temp/orphan sweep in the same pass. Reader retry: ENOENT ⇒ DISCARD the entire first snapshot, re-read the committed marker + BOTH companions fresh, once; a second miss fails close.
- **`#148` config (schema-complete, r12-13):** `verification_mode: "marker_committed"` + BOTH stable marker paths. Fact fields (exact): `committed_generation_id`, `committed_age_seconds`, `latest_attempt_status/reason/finished_at`, `verification_result` (the G4 enum, pinned precedence), nullable `price_fetch`. Companion paths/hashes resolve FROM the committed marker. Per-surface field/presence/HTTP tables live in the G4 caller contracts.

## G4 — Verified loader + caller contracts
- The loader reads the marker (shared strict validator first), verifies status=ok, opens the marker-named artifact paths, recomputes both output hashes from the exact returned bytes. Any failure → the caller's pinned contract.
- **PVO coherence — THE SAFEST RULE (r12-6): ANY exact PVO-byte mismatch between the served PVO and the marker's input digest ⇒ the stored gap is NULLED (`gap_basis_stale`) until recomputed.** PVO consumes more than the Sleeper snapshot (prospect cards, identity, runtime Engine-B features/model — build_universe_pvo_batch.py:28-32,83-92,122-131), so lineage alone cannot certify sameness; byte equality is the only sufficient test absent full upstream-digest authentication (a named optional extension with pinned precedence). Direction (by snapshot lineage) informs the MESSAGE only; older additionally fail-closes the lane (`pvo_regressed`). Normal daily window ≈ 10 minutes (09:30 → 09:40).
- **Trade honesty (r12-11):** trade surfaces never recompute captured digests; they compare BASES via the loader. The adapter gains typed `fetched_at` + `cache_state` ∈ {fresh, cached_within_ttl, stale_cache_served} (BF-10). Dual-stamp both bases; the gap context renders ONLY when the price basis EQUALS the marker's captured-market basis; any other state (newer/older/stale_cache/malformed) ⇒ SUPPRESS the gap context, serve pricing alone with its true cache_state. "Live" is banned.
- **Caller contracts (exact):** the status enum is CLOSED: {ok, stale_disclosed, no_committed_generation, legacy_unguarded, marker_malformed, generation_mismatch, output_hash_mismatch, companion_unreadable, producer_failure, gap_basis_stale, pvo_regressed, pvo_pending_lineage, chain_mixed}. Precedence = that order (first failure wins). Field locations: top-level `market_lane_status` (enum value) + `market_lane_reason` (producer_failure only) + `as_of` object ({pair, pvo, price_fetch} aware-UTC ISO). Players → HTTP 200, market-lane fields null, statuses as above. **Trade's combined endpoint (prices + divergence context) is NEVER 503:** pricing always serves; the divergence context inside it is suppressed with `divergence_status` carrying the enum. Divergence-ONLY endpoints → HTTP 503 `{error: "divergence_unavailable", status: <enum>}`. Health → the named base. Pulse/opportunity → stage-local vintages (G8).

## G5 — Ownership (carried)
`fcntl.flock(LOCK_EX | LOCK_NB)` on a stable never-unlinked path, held from BEFORE any canonical I/O (config validation included) through terminal. Contention errno set {EWOULDBLOCK/EAGAIN} ⇒ silent/log/exit-nonzero (contention code); any other acquisition failure ⇒ silent/log/exit-nonzero (lock-error code). No no-lock path touches shared state.

## G6 — Terminal schemas (strict discriminated union; shared validator module)
- **Marker `ok` (exact, closed):** `status="ok"` · `schema_version` · `attempt_id` (== `generation_id`, uuid4) · confined `latest_path`/`coverage_path`/`report_path` · `latest_sha256`/`coverage_sha256`/`report_sha256` · the three input digests · `input_pvo_source_as_of` · **`input_pvo_snapshot_captured_at`** · `input_pvo_kind` · `finished_at` (aware UTC, **sampled at the terminal write — BF-9**) · `retries_used` int≥0 non-bool · `decision_supported=false`. NO `reason`. **Report bytes EXCLUDE `report_sha256`** (marker-only; no self-reference) and mirror every OTHER duplicated field.
- **Every run has `attempt_id` (uuid4; on ok runs attempt_id == generation_id).** Report filename = `..._report_attempt_<attempt_id>.json` always (ok runs' reports are thereby generation-addressed automatically).
- **Marker `degraded` (exact presence table):** `attempt_id` · nonempty `reason` · `retries_used` · `target_snapshot_date` · `terminal_classification` ∈ {retryable_exhausted, fatal_source, fatal_config, pvo_failed, cross_midnight, history_failed, build_failed, validation_failed, publish_failed, report_write_failed, internal_error} · `report_path`+`report_sha256` PRESENT iff the attempt report was written, NULL iff terminal_classification == report_write_failed · every output/input field explicitly null · aware-UTC `finished_at` · `decision_supported=false`. Nothing optional, nothing extra — the shared validator enforces the exact field set for BOTH shapes; "mirroring" is defined as this same table applied to reports.
- **Reports mirror every duplicated field** (status, generation, digests, retries, finished_at, decision flag, provisional=true). **Report role: AUDIT-ONLY** — pair service never touches it; refusal-on-disagreement binds REPORT CONSUMERS exclusively (r10-9).
- Validator-before-precedence: malformed ⇒ `marker_malformed`; valid degraded ⇒ `producer_failure:<reason>`, companions skipped; valid ok ⇒ full verification. One marker attempt; attempt-failure ⇒ log + exit nonzero, previous marker canonical.

## G7 — History (exact-set, authenticated, adoptable)
- One transaction: validate candidates (nonempty unique normalized string IDs; payload strict-JSON: duplicate-key rejection via object_pairs_hook, parse_constant rejection, recursive finiteness walk catching 1e9999; the SQL COLUMN `decision_supported` = the EXACT integer 0 (None/0.0/True/"0" FATAL) — while the PAYLOAD's OWN `decision_supported` JSON field, where present, must be JSON `false` (payloads legitimately contain thousands of other boolean falses; the two laws are SPLIT — r11-9. LANDED (the formal round-11 verdict reviewed the earlier 2c733de3 bytes; strict duplicate-key rejection, the payload-field law, one-transaction snapshot reads, and the V3 comment are all in the current extractor))) → DELETE(day) → INSERT full set → upsert `history_day_meta` (`capture_date` PK, `generation_id`, `content_sha256`, `row_count`, `written_at_utc`, `legacy` bool — strict union: live rows have uuid4+legacy=false; legacy rows have NULL+legacy=true).
- **content_sha256 = the landed MANIFEST V3 algorithm, byte-identical between spec and extractor (cross-verified this round: 2026-07-09:81853281…, 2026-07-11:721c0f91…):** one canonical enclosing JSON array of raw stored tuples `[player_id, capture_date, decision_supported, payload_json-as-stored-string]`, sorted by player_id, canonical encoding. Whitespace/duplicate-key payload mutations change the digest because the STORED STRING is hashed.
- **guard_meta + ACTIVATION LATCH (r12-8):** `effective_from_date` lives in committed config BEFORE any guarded run (the runner never writes config). Recreation ambiguity is resolved IRREVERSIBLY: after the first successful guarded commit, a SECOND David-gated config commit sets `activated: true`. Pre-latch: db absent + config present ⇒ bootstrap. Post-latch: db or singleton missing ⇒ FAIL-CLOSE (activation is external and irreversible). Disagreement ⇒ fail-close; INSERT-only singleton. Migration retirement is latch-ordered: scan green → retire unsuffixed → rescan (the fallback cannot re-enable post-retirement). Backfill = pre-effective dates only.
- Legacy days (pre-effective, meta legacy=true or absent): readable, flagged `pre-guard legacy`. Post-effective missing/invalid meta: fail-close.

## G8 — Chain disclosure (the refresh is a DAG)
- **Stage graph pinned (r12-12, the REAL closed DAG — every edge):** Roots (model lane): Sleeper snapshot · prospect cards · identity · runtime Engine-B features/model — market data NEVER upstream of the model (constitutional). Root (market lane): FC capture. Edges: {snapshot, prospect, identity, engine-B} → PVO · {FC capture, PVO} → divergence · {snapshot, PVO} → roster-cut & team-matrix · {team-matrix} → posture · {team-matrix, divergence, posture, roster-cut} → opportunity · {posture, team-matrix, opportunity} → league pulse (Pulse does NOT read divergence directly). Digest domain per edge = the exact bytes consumed. **Section DTO (executable):** every Pulse section carries {source_stage, stage_generation_or_asof, section_status}; a stale edge suppresses that section's market-derived overlay and renders its own vintage — never the page-max date (BF-8).
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
| 50 | migration fallback | legacy_unguarded flagged; retirement latch-ordered (scan→retire→rescan) |
| 51 | first guarded run FAILS | no_committed_generation; absent contracts |
| 52 | committed-rename failure on an ok run | attempt records publish_failed — never a false ok |
| 53 | attempt-write crash post-commit | attempt_lagged; self-heals |
| 54 | crash before any attempt marker | cadence rule dashes the lane when exceeded |
| 55 | NESTED decision_supported=true | recursive walk FAILS CLOSED (LANDED; the top-level check was probe-broken) |
| 56 | same snapshot, different PVO bytes | gap NULLED (byte-equality rule) |
| 57 | stale cache beyond TTL on the price fetch | cache_state=stale_cache_served; gap suppressed |
| 58 | reconcile-vs-evidence two-connection race | ONE snapshot spans selection/reconcile/rows/payloads (LANDED) |
| 59 | non-ASCII payload fixture | digest stable under the PINNED byte rules (UTF-8, ensure_ascii=False, sort_keys, separators, allow_nan=False) |
| 60 | index missing/extra vs committed truth | start-time rebuild reconciles from markers + directory |
| 61 | partial GC crash | re-quarantined next start; recovered, not denied |
| 62 | post-activation db/marker loss | fail-close (the latch is external, irreversible) |
