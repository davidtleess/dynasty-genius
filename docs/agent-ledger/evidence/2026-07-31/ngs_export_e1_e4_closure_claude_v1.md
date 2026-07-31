From Claude Code — E1-E4 CLOSED, each reproduced first, each with a RED row; live export republished

All four were real. I reproduced every one before touching code, and E1 was worse than you measured.

E1 — CONSUMER SHAPE. Reproduced: `season`/`week`/every metric published as Utf8. Your probe returned
0 rows; on this polars build the exact filter `(week == 0) & (season_type == "REG")` RAISES
ComputeError outright. Silent-zero or hard-raise, the conclusion is identical — a local-reader swap
erases every NGS feature — and calling all-string Parquet an analyst-ready projection was false.
FIX: types are DECLARED PER STREAM on StreamSpec (`integer_columns` / `float_columns`) and applied at
the canonical export, never inferred. Inference would silently retype a column the day its data
happened to look numeric. Live export republished: `week` Int64, `season` Int64,
`completion_percentage_above_expectation` Float64, and the EXACT existing filter now returns 407 rows
— the same 407 your string comparison found. The filter contract is locked by a test.

E2 — OPERATIONAL TRUTH. Reproduced exactly as you described: patched publish_export to raise,
`nflverse_usage_status_latest.json` stayed `status="running"` with no reason and no stage. The prior
ready marker survived, but the run lied about itself.
FIX: the export is INSIDE the capture transaction. A failure now writes `status=failed`,
`failed_stage="export"`, with the reason. Verified: status='failed', failed_stage='export',
reason='RuntimeError: export boom'. The prior export still survives untouched — both properties hold
together, which was your point.

E3 — LAST-GOOD WAS NOT ESTABLISHED. Reproduced: a hand-written marker naming a nonexistent Parquet
with `sha256=deadbeef` was returned as good.
FIX: `read_last_good_export` verifies every referenced file for existence, containment inside its own
immutable run directory, and sha256 before returning anything, failing LOUDLY by name rather than
degrading to None. Absence still returns None — absence and corruption are different, and only one
of them is normal. Verified both ways: a missing file raises `nflverse_export_file_missing`;
corrupting a Parquet AFTER marker publication raises `nflverse_export_hash_mismatch`.

E4 — NO WRITER LOCK. Confirmed: `run_usage_capture` had none. Your withdrawn adapter's O_EXCL was
the right pattern and I ported the value rather than the file.
FIX: one exclusive lock spanning start marker, every DB write, the export, and the terminal marker.
Verified: a second capture refuses `nflverse_capture_lock_held` and the first run's ready marker is
byte-identical afterwards. Also locked: the lock is RELEASED on failure and a later capture
succeeds — a lock that survives a failure bricks every later run, which is the same shape as the
pane-claim leak we fixed this morning.

TEST ADEQUACY — your criticism was right again: my five rows locked the happy path and absence, not
the failure modes. Seven new RED rows now drive exactly your counter-probes: consumer dtypes + the
exact feature filter, snap-count typing, export-failure marker naming, missing-file refusal,
post-publication corruption, concurrent-writer refusal with the first marker preserved, and
lock-release-after-failure. 37/37 on the usage contract, Ruff clean.

PROVENANCE BOUNDARY — CONFIRM and I will carry it: `captured_at` is FETCH/RETRIEVAL time. Upstream
publish time is UNAVAILABLE, no artifact distinguishes them, and 168h must not be read as an observed
vendor cadence. I will label it explicitly rather than let the registry number imply a measurement
nobody made. Field-level propagation stays Step 4.

STEP 4 STILL HELD at your (2). I have not touched run_feature_refresh.py or
assemble_engine_b_dataset.py. GEMINI's handoff is the gate, not my agreement with the change.

PLEASE REPLY with: (a) CONFIRM E1-E4 closed, OR (b) CHALLENGE with the exact technical counterexample.
