# Wake-Ordering Guard — Spec v9 (STANDALONE; post-RED round 9, 2026-07-13)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store seconds before the fresh capture landed and degraded honestly (`market_source_prior_date`). **Mechanism (RED-CLEAR rounds 2–4): bounded polling of the transactional FC SQLite store.** The capture report is REJECTED as a sentinel. Implementation and schedule changes are David-gated; this document is the complete, self-contained normative contract for the build RED — it supersedes drafts v0–v8 and imports nothing.

## Named build-fix prerequisites (defects found by this spec's RED cycle)
- **BF-1:** the current reader labels ALL source-date inequality as `market_source_prior_date`; the classifier must split prior vs future before the guard lands.
- **BF-2:** player/trade consumers read `*_latest.json` directly with no marker/coverage validation; a **centralized verified loader** (G4) is required or generation checking is bypassable.
- **BF-3 (writer bypass):** `scripts/build_universe_market_divergence.py:44` → `universe_market_divergence.py:309-326` rewrites BOTH latest files directly (no lock, no generation, no marker), and `scripts/refresh_league_intelligence.py:32` invokes it. **G0 pins ONE canonical writer**; every other write path is retired or redirected through it.

## G0 — Single canonical writer + surface inventory
- The owning runner (`run_market_divergence_refresh.py` under G5 ownership) is the ONLY process that may write the pair, the marker, the report, or the day's history. The builder module becomes a pure function returning artifacts; its direct-write entry points are RETIRED (`build_universe_market_divergence.py` becomes a thin invocation of the canonical runner or is deleted; `refresh_league_intelligence.py` migrates).
- **BF-5 (rollback writers, WIDENED r8):** `run_league_intelligence_refresh.py` backs up and restores governed artifacts outside G5 (divergence: :66-80,253-264; and the outer orchestration :399-440 restores UPSTREAM latest artifacts after any later stage/acceptance failure — leaving divergence/history/marker at generation B while PVO latest reverts to A: a mixed CHAIN). **Orchestration boundary (pinned): every pipeline stage owns its artifacts; recovery is always that stage's own committed-generation mechanism; CROSS-STAGE FILE RESTORATION IS BANNED.** All restore paths in the outer refresh are retired.
- **Chain lineage (r9 P0-2, claim narrowed):** the ban prevents rollback-mixing; it does NOT make a partial-failure chain uniform — downstream stages (opportunity map; league_pulse.py:35-58) may hold an older vintage after a mid-chain failure. Each stage's committed marker records its upstream input digests; a **chain-coherence health fact** compares stage N inputs to stage N−1 committed outputs and reports `chain_mixed` — an HONEST WARN naming both vintages (mixed-but-disclosed is the correct degraded state). Row 46 expects: no restoration, each stage at its own last committed generation, chain_mixed reported.
- **Direct-reader inventory to migrate to G4:** `app/api/routes/players.py:150`, `app/api/routes/trade_market.py:98-103`, `src/dynasty_genius/trade_lab/market_reconciler.py:676`, `scripts/build_league_opportunity_map.py:22,50`.
- **Scan contract for rows 33/34 (pinned, ALL governed objects):** scope = production Python source under `app/`, `src/`, `scripts/` (tests/docs excluded); patterns = the basenames/paths of EVERY governed object — the pair, the marker, generation-addressed reports (glob), the history db. Per-object allowlist: pair+marker+reports → the canonical runner (`scripts/run_market_divergence_refresh.py`) and the G4 loader module (`src/dynasty_genius/market_divergence_loader.py`, to be created); history db → the runner, the evidence extractor (read-only), and the mandated backup reader (`backup_irreplaceable_data.py:186-218` via `backup_manifest.json:5`, read-only). The health checker and every API route reach governed objects ONLY through the loader/validator modules. The acceptance reader at `run_league_intelligence_refresh.py:301-303` migrates to the loader (inventory addition). Config FILES naming paths are data, not access — the scan targets code references (open/read/write/Path usage). Build-equivalent alternative: one boundary directory whose sole accessors are runner+loader.

## G1 — Retry state machine
- Pin `target_snapshot_date` = canonical `YYYY-MM-DD` string derived ONCE from an aware-UTC datetime at process start (bare dates carry no timezone; awareness lives in the derivation); never re-derived.
- Classification of every read (initial, polling, and final): `source_date == target` → FRESH (proceed); `source_date < target` → RETRYABLE (only this); `source_date > target` → FATAL (clock skew/misconfig; fail immediately); missing/corrupt/ambiguous/unreadable → FATAL.
- Config: `WINDOW=1800s`, `INTERVAL=60s` defaults; validated finite positive integers with `INTERVAL ≤ WINDOW`; violation = config-error terminal (G6) with no run.
- Loop, normative, per wake: (1) fresh UTC wall sample — if its date != target → CROSS-MIDNIGHT terminal ("target day unreachable"); (2) resample `now_mono`; if `now_mono ≥ deadline` (`deadline = start_mono + WINDOW`, in-process only, never persisted) → perform the FINAL read; (3) else read + classify; (4) sleep `min(INTERVAL, deadline − now_mono)` (never negative).
- **The final read is classified normally**: FRESH → proceed to publication; RETRYABLE → exhaustion terminal; FATAL → fatal terminal. Monotonic time is resampled immediately before and after each read (reads themselves may be slow).
- Large overshoot collapses to the final read — one read, one terminal, no extra cycles.
- **Blocking-read rule:** UTC and monotonic are resampled immediately AFTER every read completes; the clipped sleep is computed from the POST-read monotonic sample. The post-read UTC date must equal target in EITHER wall-jump direction (backward jumps too). A read that RETURNS after UTC midnight → cross-midnight terminal regardless of classification. A read completing past the monotonic deadline IS the final read by designation: FRESH proceeds, RETRYABLE exhausts, FATAL fails.
- **Publish-time date gate:** a FINAL UTC check runs immediately before rename-1 — a 23:59:59 fresh read followed by PVO verification/build work that crosses midnight must NOT publish (degraded terminal instead).
- `retries_used` = count of reads after the initial one (0 on immediate-fresh), recorded on every terminal.

## G2 — PVO contract
- Resolved and re-verified AFTER the market gate opens, immediately before consumption.
- **Verified-bytes consumption:** hash and load from the same read bytes/fd; hash-then-reopen-by-path is banned.
- `source_as_of`: non-null, parseable, timezone-aware, normalized to UTC, and ON the target UTC day; malformed/missing/prior-day = immediate PVO fail-close (not retryable).
- **Canonical hash inputs (pinned):** SHA-256 over (a) the exact consumed PVO bytes; (b) the exact consumed PVO-coverage bytes; (c) the market rows as ONE enclosing JSON array, canonical encoding pinned as UTF-8 with `sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False` (Python otherwise emits literal NaN — RED-probed), ordered by the FC store's stable unique key **`player_key`**, which must be a nonempty string; wrong-type/blank/duplicate keys and nonfinite numeric values = FATAL. **All three input digests are RECORDED on the ok marker and the report** (they bind inputs; the output hashes bind outputs). **Output hashes** (the published latest + coverage bytes, post-serialization) are computed at publish and recorded on the marker (G3) — input hashes alone do not bind outputs.

## G3 — Generation commit (three-way)
- `generation_id` = unique per OWNING invocation (uuid4), regenerated on every restart — never reused.
- **Pair bytes are GENERATION-ADDRESSED (r9-3):** `..._latest_<generation_id>.json` + `..._coverage_<generation_id>.json` are written fully, then ONE pointer file (naming both paths + the generation) is atomically renamed into place — the pair commit is a SINGLE atomic operation. A failed write before the pointer swap leaves the prior generation fully intact and servable (mixed pairs are structurally impossible; v8's rows 14/15/47 collapse to "pointer old or new"). Retention: keep last N generations; pointer- and marker-referenced generations are protected from pruning.
- **Commit = the ok marker.** The run is committed only when `marker.generation_id == latest.generation_id == coverage.generation_id`. After rename-2 but before the marker, the pair is PROVISIONAL — the standing marker still names generation A, so health/consumers treat the B-pair as uncommitted.
- The marker records the generation id AND the output hashes (G2) — binding the committed pair to exact bytes.
- Restart reconciliation: the next owning run publishes its own full generation (renames + marker); any provisional predecessor is simply superseded.

## G4 — Enforcement surface (build scope, BF-2)
- A **centralized verified loader** is the only sanctioned read path for the pair: marker status == ok AND the generation match (marker ↔ pointer ↔ artifacts) AND **both output hashes recomputed from the exact bytes returned** (missing/malformed marker hash = refuse). Mismatch → the calling surface's degraded/absent contract. The health check applies the identical recompute.
- **Input-basis coherence (r9 P0-1):** surfaces serving the divergence pair TOGETHER WITH a PVO read (players.py:135-152,241-262; trade_market.py:86-103,232-271) obtain PVO via a composite loader that compares the marker's `input_pvo_sha256`/`input_pvo_coverage_sha256` to the currently-loaded PVO bytes. Semantics per the real cadence: **PVO NEWER than the pair's inputs = NORMAL** (09:30 PVO precedes 09:40 divergence; the result carries `pvo_newer=true` and both as-ofs display honestly). **PVO OLDER = fail-close** (`pvo_regressed` — only restoration/rollback produces it). Rows 54/55.
- **#148 health extension (executable schema):** `report_freshness.json`'s market-divergence entry gains `companion_artifacts: [latest_path, coverage_path]` and `verify: {generation_field: "generation_id", output_hash_fields: ["latest_sha256", "coverage_sha256"]}`. The checker (`system_health_models.py`) runs the shared strict VALIDATOR FIRST: a marker failing the discriminated union ⇒ `marker_malformed` (a malformed non-ok can never masquerade as `producer_failure`). Then precedence: a VALID degraded marker ⇒ `producer_failure:<reason>`, companion verification SKIPPED. A VALID ok marker ⇒ open both companions, verify the three-way `generation_id` match, recompute both hashes. Config shape: EXACTLY two unique companion entries, each an aligned (path, hash-field) pair; paths repo-relative, symlink/traversal-confined. Failure bases (exact): `marker_malformed`, `generation_mismatch`, `output_hash_mismatch`, `companion_unreadable`, `chain_mixed`, `pvo_regressed`. **Caller-pinned mismatch results:** players → the surface's honest degraded/absent contract (corruption never renders as a genuinely-empty lane); trade endpoints → refuse; health → the named base. REDs: rows 14/15/23/25/26/42/44/54/55.

## G5 — Ownership
- Lock: **`fcntl.flock` with `LOCK_EX | LOCK_NB`** on a **stable, never-unlinked** lock file path (config-pinned; created once, never deleted by runs), held on an open fd from acquisition through terminal publication; kernel releases on any process death. No age heuristics, no stealing.
- **Ordering: the lock is acquired BEFORE any canonical I/O whatsoever** — including config validation. Matrix row 7's config-error marker is written only by a run that holds the lock; a no-lock run cannot write even an error marker.
- Contention errno set (pinned): `EWOULDBLOCK`/`EAGAIN` (equal on Darwin/Linux); anything else is lock-error.
- `EWOULDBLOCK` (live owner) → canonically SILENT (no marker, no report), structured log, **exit nonzero** (distinct code: contention).
- Any OTHER acquisition failure (permissions/IO/missing dir) → also canonically SILENT (ownership was not obtained; another owner may exist), structured log, **exit nonzero** (distinct code: lock-error). **No no-lock path ever writes shared state.**

## G6 — Terminal contract (marker-last, schema-compatible)
- Write ordering: shared report first, **marker last** — the marker is the commit point and canonical truth.
- **Schema compatibility (#148): the field is `reason`**, not `failure_reason` (a mismatch surfaces as `producer_failure:unreported`). Terminal statuses use the registered vocabulary (`ok`, plus failure statuses with `reason`).
- Report-write failure → the terminal marker is `status=degraded, reason=report_write_failed` (single write, still last; the strict union admits NO other statuses anywhere in this spec). A report-first "success" is PROVISIONAL until the same-generation ok marker commits it.
- **One atomic marker attempt** (temp + rename). If the marker write ITSELF fails: no retry loop — structured log to stderr and **exit nonzero**; the standing (previous) marker remains canonical and the run reads as uncommitted. "Every terminal path gets a marker" is thereby qualified: every path ATTEMPTS exactly one marker; attempt-failure degrades to log+nonzero.
- **Marker schema — two strict shapes, status ∈ {`ok`, `degraded`} EXACTLY:**
  - `ok`: `generation_id` (UUID4), `latest_sha256` + `coverage_sha256` (lowercase 64-hex), the three input digests (G2), **`report_path` (confined to the governed reports directory, exact generation-addressed basename, no traversal/symlink escape) + `report_sha256`**, NO `reason`, aware-UTC ISO `finished_at`, `retries_used` (int, bool rejected), `decision_supported=false`.
  - `degraded`: nonempty `reason`, **typed attempt metadata** (`retries_used`: non-bool int ≥ 0; `target_snapshot_date`: ISO date string; `terminal_classification`: enum {retryable_exhausted, fatal_source, fatal_config, pvo_failed, cross_midnight, history_failed, build_failed, validation_failed, publish_failed, report_write_failed, internal_error}), **outputs explicitly `null`**, same `finished_at`/`decision_supported` rules. The union admits NOTHING else — no generic "failure statuses" exist anywhere in this contract.
  - Matrix rows 16/23 SPLIT: pre-gate marker failure (no outputs; the prior A pair remains servable under its own ok marker) vs after-output success-marker failure (B pair on disk, A marker standing → the loader refuses B by generation mismatch).
- **Reports are GENERATION-ADDRESSED** (r8) — `..._report_<generation_id>.json` (ok) / `..._report_attempt_<uuid>.json` (degraded); the marker references its exact report path; prior reports untouched; atomic temp+rename inside the confined directory; stale temps swept only by the owning runner; the marker-referenced report retention-protected. **Report role PINNED: AUDIT-ONLY (r9-5)** — pair service via G4 requires marker + pointer + pair, never the report; report validation binds report CONSUMERS only.
- **Report schema — the same two strict shapes, FULLY MIRRORED (r9-4):** ok-shaped = `status=ok`, `generation_id`, both output hashes, all three input digests, `retries_used`, `finished_at`, `decision_supported=false`, `provisional=true`; degraded-shaped = `status=degraded`, nonempty `reason`, the typed attempt metadata, outputs/digests explicitly null, same timestamp/flag rules — every duplicated field exists on both sides for the row-49 comparison. The provisional flag is PHYSICALLY PERMANENT.
- **Commit is a READER property WITH INTEGRITY:** the ok marker records `report_sha256` over the exact written report bytes; a committed read hashes AND parses the same bytes, then compares EVERY duplicated field (generation_id, all input digests, both output hashes, retries_used) between marker and report — any disagreement refuses commitment (an honestly-hashed report with divergent fields must not pass). The PAIR is fetched through the G4 exact-byte loader. Marker/report `retries_used` agreement is claimed only where both writes succeed (marker authoritative otherwise).
- **Digest field names (exact, all lowercase-64):** `input_pvo_sha256`, `input_pvo_coverage_sha256`, `input_market_rows_sha256`, `latest_sha256`, `coverage_sha256`, `report_sha256`.
- `finished_at` is FRESHLY SAMPLED at the terminal write. **One shared strict validator** (single module) parses markers for loader AND health — duplicate implementations banned.
- Pre-gate failures (config error, FATAL classification, PVO fail-close) follow the same single-attempt marker contract.

## G-ORDER — One total publication order (pinned)
`history transaction (incl. history_day_meta) → rename-1 (latest) → rename-2 (coverage) → report write → marker write`. Every crash row references a boundary in THIS order; no alternative interleavings exist.

## G7 — History exact-set reconciliation (independently authoritative)
- The day's history write is ONE transaction: validate → `DELETE WHERE capture_date = day` → INSERT the full candidate set → write `history_day_meta`. Replaying `{A,B}` as `{A}` leaves exactly `{A}`. Executed once per owning invocation, inside the publication phase (after the gate, before the marker).
- **Key validation BEFORE the DELETE:** every candidate must carry a nonempty, unique `sleeper_player_id`; a missing or duplicate key aborts the transaction (rollback, fail-close terminal) — the current code's silent-skip/last-write-wins behavior (RED probe: upsert_count=2, stored 1) is a named build fix (**BF-4**).
- **Per-day batch metadata (pinned):** the SAME transaction writes `history_day_meta` (`capture_date` PRIMARY KEY, upserted; `generation_id`, `content_sha256`, `row_count`, `written_at_utc`). Detectability is carried by THIS table: a crash-after-history window shows `history_day_meta.generation_id != marker.generation_id` — queryable.
- **content_sha256, reproducible (pinned, FULL stored tuple):** SHA-256 over ONE enclosing JSON array of `[player_id, capture_date, decision_supported, payload_json]` — every stored column (r8 probe: an id+payload-only hash let a `decision_supported` flip pass). Sorted by `player_id`; canonical G2 encoding for the enclosing array. `payload_json` participates byte-identically AND is VALIDATED strictly at write AND read: `object_pairs_hook` REJECTS duplicate keys (last-wins banned — r9 probe), `parse_constant` rejects NaN/Infinity tokens, and a **recursive finiteness walk** rejects overflow forms (`1e9999` parses to inf without touching parse_constant — r9 probe). The shared validator module owns this schema. Keys: exact normalized nonempty strings (no surrounding whitespace) required BEFORE the DELETE. Readers compute from ONE SQLite snapshot (meta + rows in a single transaction).
- **Reader contract:** live history readers verify the day's row count + content hash against `history_day_meta` WHEN present (post-effective missing meta = fail-close); mismatch = fail-close. Ref-pinned evidence uses DG_MOVEMENT_HASHES — **MANIFEST V2 (r9-7, LANDED at extractor sha 3392e750…):** the digest covers player_id + capture_date + decision_supported + payload and FAIL-CLOSES on any non-zero decision flag; the old payload-only digests are retired (Codex's Jul-09 flip probe now breaks the manifest; regenerated 2026-07-09:c2174d57… / 2026-07-11:2a58f382…, round-tripped VERIFIED).
- **Writer constitutional guard (r9-7 = BF-6):** the history writer stores the LITERAL 0 and FAIL-CLOSES on any truthy `decision_supported` input (the current truthiness coercion at run_market_divergence_refresh.py:405-417 would honestly hash an initial true). The same strict validation runs at write AND read.
- **Legacy adoption w/ a DURABLE effective date (r9-6; live DB: 2026-07-09/11/13 × 12,201 rows, no meta):** the first owning run writes a one-row `guard_meta` table (`effective_from_date`, written ONCE under the G5 lock, never updated). Days BEFORE it lacking meta = LEGACY (readable, flagged `pre-guard legacy`, protected only by evidence manifests). Days ON/AFTER it with missing meta = **FAIL-CLOSE** (deleted meta cannot silently downgrade evidence — row 56). The optional backfill runs under G0/G5 ownership (`--backfill-legacy`), writing `generation_id=NULL, legacy=true` rows with honest checksums — never a fabricated owner. `history_day_meta` carries the `legacy` column; the shared validator owns its strict schema.
- **Claims, narrowed:** the transaction guarantees ATOMIC EXACT-SET REPLACEMENT; convergence to a named generation is established by `history_day_meta` after the next SUCCESSFUL owning run FOR THE SAME capture_date. Manifest honesty: replacing day-content A with B makes an unchanged A manifest ABORT — pinned evidence fail-closes rather than silently shifting; regenerating evidence requires a new manifest against the new content.

## Expected-result verification matrix (complete; every row = a build-RED test)
| # | Scenario | Expected |
|---|----------|----------|
| 1 | Immediate fresh | proceed; retries_used=0; ok marker w/ generation + output hashes |
| 2 | Stale then fresh mid-window | proceed; retries_used=N |
| 3 | Stale through window | final read RETRYABLE → exhaustion terminal; degraded path; retries_used recorded |
| 4 | Final-at-deadline read FRESH | proceeds to publication |
| 5 | Future source_date (any read) | FATAL terminal immediately |
| 6 | Corrupt/missing store (any read, incl. mid-window transition) | FATAL terminal immediately |
| 7 | Config invalid (zero/negative/INTERVAL>WINDOW) | config-error terminal; no run |
| 8 | Cross-midnight at any wake | degraded terminal "target day unreachable" |
| 9 | Wall-clock jump either direction | monotonic deadline unaffected; classification uses fresh wall samples |
| 10 | Large oversleep past deadline | exactly one final read then terminal |
| 11 | PVO swapped during wait | re-verification consumes new bytes or fails close; no verify/load gap (bytes-consumption) |
| 12 | PVO hash-valid but prior-day source_as_of | PVO fail-close |
| 13 | PVO source_as_of malformed/missing/naive | PVO fail-close |
| 14 | Kill after rename-1 (latest=B, coverage=A, marker=A) | health degraded (three-way mismatch); verified loader refuses; restart publishes clean C |
| 15 | Kill after rename-2 pre-marker (pair=B, marker=A) | pair PROVISIONAL; health keyed to marker generation A; restart publishes clean C |
| 16a | Marker-attempt failure PRE-GATE (no outputs) | log + exit nonzero; prior A pair + A ok marker fully servable |
| 16b | Success-marker failure AFTER outputs (B pair, A marker) | log + exit nonzero; loader refuses B (generation mismatch); A stays committed truth |
| 17 | Report write fails | marker failed w/ reason=report_write_failed |
| 18 | {A,B}→{A} same-day history replay | exact set {A} (transactional delete+insert) |
| 19 | Lock contention (live owner) | silent, log, exit nonzero (contention code); no shared writes |
| 20 | Lock acquisition error (non-contention) | silent, log, exit nonzero (lock-error code); no shared writes |
| 21 | Owner crash mid-poll | kernel releases lock; next run acquires; no stale-lock handling needed |
| 22 | Restart after any kill point | at-most-once per invocation; boundaries idempotent (rename atomicity, G7 exact-set, single marker) |
| 23 | Verified loader vs each mixed state (14/15/16a/16b) | 16a: serves A · 16b: refuses B · 14/15: refuses on three-way mismatch |
| 24 | retries_used marker/report agreement | equal where both written; marker authoritative otherwise |
| 25 | Same-generation output tampering (bytes altered post-commit) | verified loader + health recompute FAIL the hash check |
| 26 | Marker hashes missing/malformed | loader refuses; health degraded |
| 27 | Crash immediately after the history transaction, BEFORE rename-1 (G-ORDER boundary 1→2) | surface stays generation A; history holds B (authoritative per G7); meta shows B; an unchanged A manifest ABORTS (fail-close); the next SUCCESSFUL owning run for the SAME capture_date converges |
| 28 | Failed restart after row 27 | day converges on the NEXT successful owning run; no partial states |
| 29 | Read straddles UTC midnight (returns after) | cross-midnight terminal; no publish |
| 30 | Read completes past the monotonic deadline | that read IS final by designation; classified normally |
| 31 | Config error without lock ownership | silent, log, exit nonzero — no marker (lock precedes all canonical I/O) |
| 32 | Market rows with missing/duplicate/blank/wrong-type player_key, or nonfinite values | FATAL |
| 33 | Unsanctioned writer grep (latest-file basenames outside the canonical runner) | zero hits (G0) |
| 34 | Direct-reader grep post-migration | zero unsanctioned readers (G0/G4) |
| 35 | History candidate w/ duplicate or missing key | transaction rollback; fail-close terminal (BF-4 probe reproduced) |
| 36 | history_day_meta mismatch (count or hash) at a live reader | reader fail-close |
| 37 | Kill after report, before marker (normal success path) | report physically provisional; report-reader refuses w/o same-generation ok marker |
| 38 | Report reader on committed success | validates marker generation + hashes; treats report as committed |
| 39 | Wall-clock BACKWARD jump around a read | post-read UTC check enforces target date |
| 40 | Fresh read at 23:59:59, build crosses midnight | publish-time date gate blocks rename; degraded terminal |
| 41 | Timing config as bool/float/string ("60", 60.5, true) | config-error terminal (exact non-bool int) |
| 42 | Malformed marker shape (each field) | shared validator rejects; loader refuses; health per precedence |
| 43 | Malformed report / input-digest / companion / history-meta shapes | respective reader fail-closes |
| 44 | Degraded marker precedence | health = producer_failure:<reason>; companion checks SKIPPED |
| 45 | Report bytes mutated post-write | report_sha256 mismatch; commitment refused |
| 46 | Outer-refresh failure AFTER the divergence stage | NO restoration anywhere; each stage keeps its last committed generation; chain never mixes |
| 47 | rename-1 or rename-2 I/O FAILURE (not a kill) | run terminal degraded; three-way commit absent; loader serves prior A |
| 48 | Report/marker TEMP-file write interruption | temp discarded; canonical bytes untouched; per G6 single-attempt rules |
| 49 | Report fields honestly hashed but disagreeing with the marker | committed read compares every duplicated field; refused |
| 50 | Legacy history day (no meta row) | readable, flagged pre-guard legacy; evidence protected by manifests only |
| 51 | decision_supported flipped in a stored history row | full-tuple content hash mismatch; reader fail-close |
| 52 | NaN/Infinity token inside payload_json | payload validation rejects at write AND read |
| 53 | Same-capture-date convergence after any failure | the next successful owning run's exact-set + meta row establish the named generation |
| 54 | Normal next-PVO turnover (PVO newer than pair inputs) | composite loader serves both, pvo_newer=true, both as-ofs displayed |
| 55 | PVO OLDER than pair inputs (restoration/rollback) | pvo_regressed; fail-close |
| 56 | history_day_meta deleted for a post-effective day | fail-close (durable guard_meta effective date) |
| 57 | Truthy decision_supported input at the writer | FATAL (BF-6; literal constitutional 0 enforced) |
| 58 | Duplicate JSON keys or 1e9999 overflow in payload | strict parse rejects |
| 59 | Pointer-swap crash (new pair written, pointer old) | prior generation fully servable; orphans pruned later |
| 60 | Backup reader on the history db | allowlisted read-only; scan passes |
