# Wake-Ordering Guard — Spec v6 (STANDALONE; post-RED round 6, 2026-07-13)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store seconds before the fresh capture landed and degraded honestly (`market_source_prior_date`). **Mechanism (RED-CLEAR rounds 2–4): bounded polling of the transactional FC SQLite store.** The capture report is REJECTED as a sentinel. Implementation and schedule changes are David-gated; this document is the complete, self-contained normative contract for the build RED — it supersedes drafts v0–v5 and imports nothing.

## Named build-fix prerequisites (defects found by this spec's RED cycle)
- **BF-1:** the current reader labels ALL source-date inequality as `market_source_prior_date`; the classifier must split prior vs future before the guard lands.
- **BF-2:** player/trade consumers read `*_latest.json` directly with no marker/coverage validation; a **centralized verified loader** (G4) is required or generation checking is bypassable.
- **BF-3 (writer bypass):** `scripts/build_universe_market_divergence.py:44` → `universe_market_divergence.py:309-326` rewrites BOTH latest files directly (no lock, no generation, no marker), and `scripts/refresh_league_intelligence.py:32` invokes it. **G0 pins ONE canonical writer**; every other write path is retired or redirected through it.

## G0 — Single canonical writer + surface inventory
- The owning runner (`run_market_divergence_refresh.py` under G5 ownership) is the ONLY process that may write the pair, the marker, the report, or the day's history. The builder module becomes a pure function returning artifacts; its direct-write entry points are RETIRED (`build_universe_market_divergence.py` becomes a thin invocation of the canonical runner or is deleted; `refresh_league_intelligence.py` migrates).
- **Direct-reader inventory to migrate to G4** (traced by the RED): `app/api/routes/players.py:150`, `src/dynasty_genius/trade_lab/market_reconciler.py:676`, `scripts/build_league_opportunity_map.py:22,50`, plus any reader a build-time grep for the latest-file basenames finds. The build RED includes that grep as a test (no unsanctioned readers remain).

## G1 — Retry state machine
- Pin `target_snapshot_date` = timezone-aware **UTC** date at process start; never re-derived.
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
- Both output artifacts are stamped with it pre-rename. Rename order: latest, then coverage.
- **Commit = the ok marker.** The run is committed only when `marker.generation_id == latest.generation_id == coverage.generation_id`. After rename-2 but before the marker, the pair is PROVISIONAL — the standing marker still names generation A, so health/consumers treat the B-pair as uncommitted.
- The marker records the generation id AND the output hashes (G2) — binding the committed pair to exact bytes.
- Restart reconciliation: the next owning run publishes its own full generation (renames + marker); any provisional predecessor is simply superseded.

## G4 — Enforcement surface (build scope, BF-2)
- A **centralized verified loader** is the only sanctioned read path for the pair: it checks marker status == ok AND the three-way generation match AND **recomputes BOTH output hashes from the exact bytes it returns**, requiring well-formed hashes on the marker (missing/malformed hash = refuse). Hash verification is MANDATORY — same-generation tampering must fail. Mismatch → the degraded/absent contract of the calling surface. The health check applies the identical recompute.
- **#148 health extension (executable schema):** `report_freshness.json`'s market-divergence entry gains `companion_artifacts: [latest_path, coverage_path]` and `verify: {generation_field: "generation_id", output_hash_fields: ["latest_sha256", "coverage_sha256"]}`. The checker (`system_health_models.py`) opens the marker AND both companions, verifies the three-way `generation_id` match, and recomputes both artifact hashes against the marker's recorded values. New failure bases (exact): `generation_mismatch`, `output_hash_mismatch`, `marker_hash_malformed` — these are the REDs for matrix rows 14/15/23/25/26.

## G5 — Ownership
- Lock: **`fcntl.flock` with `LOCK_EX | LOCK_NB`** on a **stable, never-unlinked** lock file path (config-pinned; created once, never deleted by runs), held on an open fd from acquisition through terminal publication; kernel releases on any process death. No age heuristics, no stealing.
- **Ordering: the lock is acquired BEFORE any canonical I/O whatsoever** — including config validation. Matrix row 7's config-error marker is written only by a run that holds the lock; a no-lock run cannot write even an error marker.
- Contention errno set (pinned): `EWOULDBLOCK`/`EAGAIN` (equal on Darwin/Linux); anything else is lock-error.
- `EWOULDBLOCK` (live owner) → canonically SILENT (no marker, no report), structured log, **exit nonzero** (distinct code: contention).
- Any OTHER acquisition failure (permissions/IO/missing dir) → also canonically SILENT (ownership was not obtained; another owner may exist), structured log, **exit nonzero** (distinct code: lock-error). **No no-lock path ever writes shared state.**

## G6 — Terminal contract (marker-last, schema-compatible)
- Write ordering: shared report first, **marker last** — the marker is the commit point and canonical truth.
- **Schema compatibility (#148): the field is `reason`**, not `failure_reason` (a mismatch surfaces as `producer_failure:unreported`). Terminal statuses use the registered vocabulary (`ok`, plus failure statuses with `reason`).
- Report-write failure → the terminal marker records failed w/ `reason=report_write_failed` (single marker write, still last). A report-first "success" is PROVISIONAL until the ok marker with the same generation commits it.
- **One atomic marker attempt** (temp + rename). If the marker write ITSELF fails: no retry loop — structured log to stderr and **exit nonzero**; the standing (previous) marker remains canonical and the run reads as uncommitted. "Every terminal path gets a marker" is thereby qualified: every path ATTEMPTS exactly one marker; attempt-failure degrades to log+nonzero.
- **Marker schema — two strict shapes, status ∈ {`ok`, `degraded`} EXACTLY:**
  - `ok`: `generation_id` (UUID4), `latest_sha256` + `coverage_sha256` (lowercase 64-hex), the three input digests (G2), NO `reason` field, aware-UTC ISO `finished_at`, `retries_used` (int, bool rejected), `decision_supported=false`.
  - `degraded`: nonempty `reason`, attempt metadata (`retries_used`, target date, classification at terminal), **outputs explicitly `null`** (a failure that produced no outputs carries no generation/hashes — v5's requirement was internally impossible), same `finished_at`/`decision_supported` rules.
  - Matrix rows 16/23 SPLIT: pre-gate marker failure (no outputs; the prior A pair remains servable under its own ok marker) vs after-output success-marker failure (B pair on disk, A marker standing → the loader refuses B by generation mismatch).
- **Report schema + verified report-reader contract:** the report carries `generation_id`, both output hashes, and `provisional=true` — and the flag is PHYSICALLY PERMANENT (marker-last performs no rewrite). Commit is therefore a READER property: any report consumer validates a same-generation ok marker (and its hashes) before treating the report as committed; without it the report is display-only provisional. Marker/report `retries_used` agreement is claimed only where both writes succeed (marker authoritative otherwise).
- Pre-gate failures (config error, FATAL classification, PVO fail-close) follow the same single-attempt marker contract.

## G7 — History exact-set reconciliation (independently authoritative)
- The day's history write is ONE transaction: validate → `DELETE WHERE capture_date = day` → INSERT the full candidate set → write `history_day_meta`. Replaying `{A,B}` as `{A}` leaves exactly `{A}`. Executed once per owning invocation, inside the publication phase (after the gate, before the marker).
- **Key validation BEFORE the DELETE:** every candidate must carry a nonempty, unique `sleeper_player_id`; a missing or duplicate key aborts the transaction (rollback, fail-close terminal) — the current code's silent-skip/last-write-wins behavior (RED probe: upsert_count=2, stored 1) is a named build fix (**BF-4**).
- **Per-day batch metadata (pinned):** the SAME transaction that replaces the day writes a `history_day_meta` row: `(capture_date, generation_id, content_sha256, row_count, written_at_utc)`. Detectability is carried by THIS table (not the marker, which records only pair outputs): a crash-after-history window shows `history_day_meta.generation_id != marker.generation_id` — a queryable fact.
- **Reader contract:** live history readers (the extractor's unpinned mode, movement derivations) verify the day's row count + content hash against `history_day_meta` before use; mismatch = fail-close. (Ref-pinned evidence additionally uses DG_MOVEMENT_HASHES; that manifest remains mandatory only there.)
- **Claims, narrowed:** the transaction guarantees ATOMIC EXACT-SET REPLACEMENT; convergence to a named generation is established by `history_day_meta` after the next successful owning run — not asserted about failed restarts (a failed restart that reaches G7 replaces the day again under its own generation, recorded in the same metadata).

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
| 16 | Marker write fails | log + exit nonzero; previous marker canonical; run uncommitted |
| 17 | Report write fails | marker failed w/ reason=report_write_failed |
| 18 | {A,B}→{A} same-day history replay | exact set {A} (transactional delete+insert) |
| 19 | Lock contention (live owner) | silent, log, exit nonzero (contention code); no shared writes |
| 20 | Lock acquisition error (non-contention) | silent, log, exit nonzero (lock-error code); no shared writes |
| 21 | Owner crash mid-poll | kernel releases lock; next run acquires; no stale-lock handling needed |
| 22 | Restart after any kill point | at-most-once per invocation; boundaries idempotent (rename atomicity, G7 exact-set, single marker) |
| 23 | Verified loader vs each mixed state (14/15/16) | refuses/degrades per surface contract |
| 24 | retries_used marker/report agreement | equal where both written; marker authoritative otherwise |
| 25 | Same-generation output tampering (bytes altered post-commit) | verified loader + health recompute FAIL the hash check |
| 26 | Marker hashes missing/malformed | loader refuses; health degraded |
| 27 | Crash after history, before marker | surface stays generation A; history holds B (authoritative per G7); next run converges the day; pinned evidence manifests unaffected |
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
