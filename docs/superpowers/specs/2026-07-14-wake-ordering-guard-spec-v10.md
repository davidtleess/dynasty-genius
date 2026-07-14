# Wake-Ordering Guard — Spec v10 (STANDALONE FULL REWRITE; post-RED round 10, 2026-07-14)

**Problem (observed 2026-07-12):** the 09:40 divergence runner and the 09:00 FC capture coalesce on wake; the runner read the market store seconds before the fresh capture landed and degraded honestly. **Mechanism (RED-CLEAR, rounds 2–10): bounded polling of the transactional FC SQLite store.** The capture report is rejected as a sentinel. Implementation and schedule are David-gated; this document is the complete normative contract and supersedes v0–v9 entirely. v9's pointer model is REMOVED (it created a dual commit); **the marker is the single commit object.**

## Named build fixes (real defects found by this RED cycle)
- **BF-1** reader labels all source-date inequality as prior (future dates included) — classifier split required.
- **BF-2** player/trade consumers read latest files unvalidated — the G4 loader is the fix.
- **BF-3** `build_universe_market_divergence.py` / `refresh_league_intelligence.py` write governed artifacts directly — retired under G0.
- **BF-4** history writer silently skips missing IDs and last-write-wins duplicates — G7 validation.
- **BF-5** outer-refresh backup/restore can mix chain vintages — cross-stage restoration banned (G8).
- **BF-6** history writer truthiness-coerces `decision_supported` — literal integer 0 required; truthy/None/float input = FATAL.

## G0 — Single canonical writer + enforcement scan
- The owning runner (`scripts/run_market_divergence_refresh.py`) is the ONLY writer of governed objects: generation-addressed artifacts, the marker, generation-addressed reports, the history db (incl. `history_day_meta`, `guard_meta`).
- **Scan contract:** production Python under `app/`, `src/`, `scripts/` (tests/docs excluded) for code references to governed basenames/globs AND a config scan (json/plist/yaml under `app/config/`, `ops/`) for governed paths — config-driven access (the backup reader via `backup_manifest.json:5`) is visible to the config scan and allowlisted read-only. Per-object allowlists: artifacts+marker+reports → runner + loader (`src/dynasty_genius/market_divergence_loader.py`, to be created); history db → runner, the evidence extractor (allowlisted BY PATH: `docs/design-comps/comp-v33-extract.py`, read-only), the backup reader (read-only). Any other hit fails the test.

## G1 — Retry state machine (carried, complete)
- `target_snapshot_date` = canonical `YYYY-MM-DD` derived ONCE from an aware-UTC datetime at process start.
- Classify every read: `== target` FRESH · `< target` RETRYABLE (only this) · `> target` FATAL · missing/corrupt/ambiguous FATAL.
- Config `WINDOW=1800s`, `INTERVAL=60s`; exact non-bool positive ints, INTERVAL ≤ WINDOW; violation = config-error terminal.
- Loop per wake: (1) fresh UTC sample — date ≠ target ⇒ cross-midnight terminal; (2) resample monotonic; ≥ deadline ⇒ FINAL read; (3) else read+classify; (4) sleep `min(INTERVAL, deadline − now_mono)` from the POST-read sample. Post-read UTC+monotonic resample decides finality and the date gate in EITHER wall-jump direction; a read returning past midnight terminates; a read completing past the deadline IS final (classified normally — FRESH proceeds). Large overshoot ⇒ one final read. `retries_used` = reads after the first. A publish-time UTC gate runs immediately before the first artifact write.

## G2 — PVO contract (basis recorded)
- Re-resolved and re-verified AFTER the market gate; **verified-bytes consumption** (hash and load the same bytes/fd).
- `source_as_of`: non-null, parseable, aware, UTC-normalized, ON the target UTC day; else PVO fail-close.
- **The marker records the consumed basis:** `input_pvo_source_as_of` (aware UTC ISO), `input_pvo_kind` (the pvo_source route/kind string), and the three input digests — making downstream cadence comparisons COMPUTABLE (r10-3).
- Canonical digest inputs: exact PVO bytes; exact PVO-coverage bytes; market rows as ONE canonical JSON array (UTF-8, sort_keys, ensure_ascii=False, separators, allow_nan=False), ordered by `player_key` (nonempty string; missing/duplicate/wrong-type/nonfinite = FATAL).

## G3 — Commit model: THE MARKER IS THE COMMIT (single point)
- Artifacts are **generation-addressed**: `..._latest_<generation_id>.json`, `..._coverage_<generation_id>.json` (uuid4 per owning invocation, regenerated on restart). No un-suffixed governed artifact exists.
- **G-ORDER (total):** history transaction → write artifact files (temp+rename each, but they are INERT until referenced) → write generation-addressed report → ONE atomic marker write (temp+rename). The marker names `latest_path`, `coverage_path`, `report_path` (all confined: governed directory, exact generation basename patterns, no traversal/symlinks) + all hashes. **A generation exists for consumers ONLY through the marker.** Crash anywhere pre-marker: the previous marker serves the previous generation, whose files are retention-protected. There is no pointer, no dual commit, no mixed-pair state.
- **GC protocol:** only the owning runner prunes, under the G5 lock; keep the last N=3 generations MINIMUM plus anything referenced by the current or previous marker; grace ≥ 24h before any prune; reader retry: a loader that snapshots the marker and hits ENOENT on a pruned file re-reads the marker ONCE and retries (the r10 probe's race), failing close on a second miss.
- `#148` config change: the health entry names the MARKER path only; companion paths are resolved FROM the marker's fields (static companion paths are impossible under generation addressing — r10-2).

## G4 — Verified loader + caller contracts
- The loader reads the marker (shared strict validator first), verifies status=ok, opens the marker-named artifact paths, recomputes both output hashes from the exact returned bytes. Any failure → the caller's pinned contract.
- **Composite PVO coherence (computable via G2 basis):** compare the currently-served PVO's `source_as_of`+bytes to the marker's recorded basis. Current PVO SAME bytes ⇒ coherent. Current `source_as_of` NEWER ⇒ normal turnover (`pvo_newer=true`, both as-ofs surfaced; multi-day-newer allowed with the same disclosure). Current OLDER ⇒ `pvo_regressed`, fail-close. SAME `source_as_of`, DIFFERENT bytes ⇒ `pvo_mismatch`, fail-close. One-side unreadable ⇒ fail-close. Current PVO itself unverified ⇒ that surface's PVO contract governs (never served as coherent).
- **Trade honesty (r10-4):** any surface attaching captured-market gap context to LIVE FantasyCalc prices must reconcile `input_market_rows_sha256` via the loader AND dual-stamp both vintages ("live price as of X · gap basis as of Y"); reconciliation failure ⇒ SUPPRESS the gap context (serve the live price alone). No single-stamped mixed-vintage response exists.
- **Caller contracts (exact):** players → HTTP 200, market-lane fields explicitly null + `market_lane_status: <base>` (never an empty lane resembling genuinely-empty); trade gap-context → suppressed as above; trade divergence endpoints → HTTP 503 with `{error: "divergence_unavailable", base: <base>}`; health → the named base; opportunity/pulse helpers → each stage's own degraded contract with its vintage stamped (G8).

## G5 — Ownership (carried)
`fcntl.flock(LOCK_EX | LOCK_NB)` on a stable never-unlinked path, held from BEFORE any canonical I/O (config validation included) through terminal. Contention errno set {EWOULDBLOCK/EAGAIN} ⇒ silent/log/exit-nonzero (contention code); any other acquisition failure ⇒ silent/log/exit-nonzero (lock-error code). No no-lock path touches shared state.

## G6 — Terminal schemas (strict discriminated union; shared validator module)
- **Marker `ok`:** `generation_id` uuid4 · `latest_path`/`coverage_path`/`report_path` (confined) · `latest_sha256`/`coverage_sha256`/`report_sha256` · `input_pvo_sha256`/`input_pvo_coverage_sha256`/`input_market_rows_sha256` · `input_pvo_source_as_of`/`input_pvo_kind` · aware-UTC `finished_at` · `retries_used` int≥0 non-bool · `decision_supported=false`. NO `reason`.
- **Marker `degraded`:** nonempty `reason` · typed attempt metadata (`retries_used`, `target_snapshot_date`, `terminal_classification` ∈ {retryable_exhausted, fatal_source, fatal_config, pvo_failed, cross_midnight, history_failed, build_failed, validation_failed, publish_failed, report_write_failed, internal_error}) · **`report_path`+`report_sha256` for its attempt report IF that write succeeded, explicitly null if the failure IS report_write_failed** (r10-9) · all output/input fields explicitly null · same finished_at/decision rules.
- **Reports mirror every duplicated field** (status, generation, digests, retries, finished_at, decision flag, provisional=true). **Report role: AUDIT-ONLY** — pair service never touches it; refusal-on-disagreement binds REPORT CONSUMERS exclusively (r10-9).
- Validator-before-precedence: malformed ⇒ `marker_malformed`; valid degraded ⇒ `producer_failure:<reason>`, companions skipped; valid ok ⇒ full verification. One marker attempt; attempt-failure ⇒ log + exit nonzero, previous marker canonical.

## G7 — History (exact-set, authenticated, adoptable)
- One transaction: validate candidates (nonempty unique normalized string IDs; payload strict-JSON: duplicate-key rejection via object_pairs_hook, parse_constant rejection, recursive finiteness walk catching 1e9999; `decision_supported` = the EXACT integer 0 — None/0.0/False/empty all FATAL, recursively checked at write and read) → DELETE(day) → INSERT full set → upsert `history_day_meta` (`capture_date` PK, `generation_id`, `content_sha256`, `row_count`, `written_at_utc`, `legacy` bool — strict union: live rows have uuid4+legacy=false; legacy rows have NULL+legacy=true).
- **content_sha256 = the landed MANIFEST V3 algorithm, byte-identical between spec and extractor (cross-verified this round: 2026-07-09:81853281…, 2026-07-11:721c0f91…):** one canonical enclosing JSON array of raw stored tuples `[player_id, capture_date, decision_supported, payload_json-as-stored-string]`, sorted by player_id, canonical encoding. Whitespace/duplicate-key payload mutations change the digest because the STORED STRING is hashed.
- **guard_meta durability (r10-8):** `effective_from_date` is anchored in TWO places written at first bootstrap — the db singleton row AND a git-tracked config file (`app/config/wake_ordering_guard.json`). Readers require agreement; disagreement or absence-after-bootstrap = fail-close (a recreated db row cannot silently re-legacy post-guard days). Backfill (`--backfill-legacy`, owner-run) may target ONLY pre-effective dates — post-effective backfill is BANNED.
- Legacy days (pre-effective, meta legacy=true or absent): readable, flagged `pre-guard legacy`. Post-effective missing/invalid meta: fail-close.

## G8 — Chain disclosure (the refresh is a DAG)
- Stage graph pinned: FC capture → PVO → divergence → {opportunity map, league pulse, …} (edges enumerated in the build RED from refresh_league_intelligence.py). Each stage's committed marker records its upstream input digests (digest domains: the exact bytes it consumed).
- Cross-stage file restoration is BANNED (BF-5). After a mid-chain failure the chain MAY be mixed; the chain-coherence health fact walks the DAG edges and reports `chain_mixed` naming every stale edge and both vintages — the honest, disclosed degraded state. Downstream surfaces stamp their own stage vintage.

## Verification matrix (55 rows, reorganized for the single-commit model)
G1 timing (9): immediate-fresh · stale→fresh · exhaustion (final read classified) · final-read-fresh-proceeds · future-fatal · corrupt-fatal (incl. mid-window transition) · config shapes (bool/float/string) · cross-midnight each stage incl. straddling reads + publish-time gate · wall jumps both directions.
G2 PVO (6): swap-during-wait · prior-day valid · malformed/missing/naive as_of · basis recorded on marker · seed/no-as-of build rejection · nonfinite/dup player_key FATAL.
G3 commit/GC (8): crash before artifacts · between artifact writes · after artifacts pre-report · after report pre-marker (all four: previous marker serves previous generation) · marker attempt failure (log+nonzero, prior canonical) · GC never prunes marker-referenced/previous or within grace · reader ENOENT retry-once protocol · orphan pruning.
G4 loader/callers (12): hash recompute refusal (tamper) · malformed marker hashes · marker_malformed precedence · valid-degraded producer_failure w/ companions skipped · pvo turnover normal (incl. multi-day) · pvo_regressed · pvo_mismatch (same as_of, different bytes) · one-side unreadable · trade dual-stamp + suppression · players null-lane contract · trade 503 contract · report-consumer field-disagreement refusal.
G5 (3): contention silent-nonzero · acquisition-error silent-nonzero · owner-crash kernel release.
G6 (4): each malformed marker field · degraded w/ successful attempt report (path+hash present) · report_write_failed (nulls) · duplicated-field mirror check.
G7 history (9): exact-set replay {A,B}→{A} · duplicate/missing/blank keys rollback · non-integer-0 decision flag FATAL (each laundering shape: True/None/0.0/"0") · nested NaN/Infinity/1e9999 rejection · duplicate JSON keys rejection · full-tuple digest breaks on any column flip · legacy read flagged · post-effective missing meta fail-close · guard_meta db/config disagreement fail-close · post-effective backfill refused.
G8 chain (4): mid-chain failure ⇒ chain_mixed named edges · no restoration anywhere · stage vintage stamping · DAG edge digest verification.
